"""Provider-agnostic, one-call vision adapter for receiving inspection."""

import json

from inspection_agent import inspect_unit, pending_review


CHECKS = (
    "identity",
    "carton_count",
    "units_per_carton",
    "quantity",
    "carton_damage",
    "unit_damage",
    "colour",
    "variant",
    "components",
    "quality_flags",
)

FIELD_BY_CHECK = {
    "identity": "identity_match",
    "carton_count": "cartons_received",
    "units_per_carton": "units_per_carton_counted",
    "quantity": "qty_received",
    "carton_damage": "carton_damage",
    "unit_damage": "unit_damage",
    "colour": "observed_colour",
    "variant": "observed_variant",
    "components": "observed_components",
    "quality_flags": "quality_flags",
}


def _instruction():
    return (
        "Inspect the supplied receiving images and report only what is visibly "
        "supported. Return one observation for every named check. Do not make "
        "PASS or FAIL decisions. Use uncertainty when the images do not establish "
        "a value. Every evidence item must include source_ref and detail. "
        "Every evidence source_ref must exactly match a supplied image_ref. "
        "Only provide location data when it is visibly established; do not invent it."
    )


def _expected(unit):
    return {
        "po_number": unit.get("po_number"),
        "po_line": unit.get("po_line"),
        "supplier": unit.get("supplier"),
        "sku": unit.get("sku"),
        "asin": unit.get("asin"),
        "product_title": unit.get("product_title"),
        "colour": unit.get("spec_colour"),
        "variant": unit.get("spec_variant"),
        "components": unit.get("spec_components"),
        "cartons": unit.get("cartons_ordered"),
        "units_per_carton": unit.get("units_per_carton_ordered"),
        "quantity": unit.get("qty_ordered"),
    }


def _validate_response(response, image_refs):
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except json.JSONDecodeError as error:
            raise ValueError("Model response is not valid JSON") from error

    if not isinstance(response, dict):
        raise ValueError("Model response must be a JSON object")
    if not isinstance(image_refs, list) or not all(
        isinstance(image_ref, str) and image_ref for image_ref in image_refs
    ):
        raise ValueError("image_refs must contain non-empty strings")

    observations = response.get("observations")
    if not isinstance(observations, dict) or set(observations) != set(CHECKS):
        raise ValueError("Model response must contain exactly all required observations")

    validated = {}
    for check in CHECKS:
        observation = observations[check]
        if not isinstance(observation, dict):
            raise ValueError(f"Observation for {check} must be an object")
        if "observed_value" not in observation:
            raise ValueError(f"Observation for {check} is missing observed_value")
        if not isinstance(observation.get("uncertainty"), bool):
            raise ValueError(f"Observation for {check} has invalid uncertainty")
        if not isinstance(observation.get("reason"), str) or not observation["reason"].strip():
            raise ValueError(f"Observation for {check} is missing reason")

        value = observation["observed_value"]
        if not observation["uncertainty"]:
            if check == "identity":
                valid_value = value in ("yes", "no")
            elif check in {"carton_count", "units_per_carton", "quantity"}:
                valid_value = isinstance(value, int) and not isinstance(value, bool) and value >= 0
            elif check in {"carton_damage", "unit_damage"}:
                valid_value = value in ("none", "crushing", "water", "tears")
            elif check in {"colour", "variant"}:
                valid_value = isinstance(value, str) and bool(value.strip())
            else:
                valid_value = isinstance(value, list) and all(isinstance(item, str) for item in value)
            if not valid_value:
                raise ValueError(f"Observation for {check} has an invalid observed_value")

        evidence = observation.get("evidence", [])
        if not isinstance(evidence, list):
            raise ValueError(f"Evidence for {check} must be a list")
        clean_evidence = []
        for item in evidence:
            if not isinstance(item, dict):
                raise ValueError(f"Evidence for {check} must contain objects")
            if not isinstance(item.get("source_ref"), str) or not item["source_ref"]:
                raise ValueError(f"Evidence for {check} has invalid source_ref")
            if item["source_ref"] not in image_refs:
                raise ValueError(f"Evidence for {check} references an unavailable image")
            if not isinstance(item.get("detail"), str) or not item["detail"].strip():
                raise ValueError(f"Evidence for {check} is missing detail")

            clean_item = {
                "source_ref": item["source_ref"],
                "detail": item["detail"],
            }
            if "location" in item:
                location = item["location"]
                if not isinstance(location, dict) or set(location) != {"x", "y", "width", "height"}:
                    raise ValueError(f"Evidence for {check} has invalid location")
                if not all(
                    isinstance(location[key], (int, float))
                    and not isinstance(location[key], bool)
                    and 0 <= location[key] <= 1
                    for key in ("x", "y", "width", "height")
                ):
                    raise ValueError(f"Evidence for {check} has invalid location")
                clean_item["location"] = dict(location)
            clean_evidence.append(clean_item)

        validated[check] = {
            "observed_value": None if observation["uncertainty"] else observation["observed_value"],
            "uncertainty": observation["uncertainty"],
            "reason": observation["reason"],
            "evidence": clean_evidence,
        }
    return validated


def _apply_observations(unit, observations):
    enriched = dict(unit)
    for check, observation in observations.items():
        enriched[FIELD_BY_CHECK[check]] = observation["observed_value"]
    return enriched


def _attach_evidence(result, observations):
    for check, observation in observations.items():
        if check not in result["checks"]:
            continue
        sources = [item["source_ref"] for item in observation["evidence"]]
        result["checks"][check]["evidence"] = sources + [observation["reason"]]
        result["checks"][check]["evidence_items"] = observation["evidence"]
    result["model_observations"] = observations
    return result


class VisionInspectionAdapter:
    """Run exactly one model request, then delegate decisions to inspection_agent."""

    def __init__(self, model_client):
        self.model_client = model_client

    def inspect_unit(self, unit, image_refs):
        if not isinstance(image_refs, list) or not image_refs:
            return inspect_unit(
                _apply_observations(unit, {
                    check: {
                        "observed_value": None,
                        "uncertainty": True,
                        "reason": "No receiving image evidence was supplied",
                        "evidence": [],
                    }
                    for check in CHECKS
                })
            )

        payload = {
            "instruction": _instruction(),
            "expected": _expected(unit),
            "image_refs": image_refs,
            "required_checks": list(CHECKS),
        }
        try:
            response = self.model_client(payload)
            observations = _validate_response(response, image_refs)
        except Exception as error:
            return pending_review(unit, f"Vision/model inspection failed: {error}")

        return _attach_evidence(
            inspect_unit(_apply_observations(unit, observations)),
            observations,
        )


def inspect_receiving_unit(unit, image_refs, model_client):
    """Convenience entry point for one receiving unit and one model call."""
    return VisionInspectionAdapter(model_client).inspect_unit(unit, image_refs)