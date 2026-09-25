import unittest

from vision_adapter import CHECKS, VisionInspectionAdapter


UNIT = {
    "record_id": "RCV-1",
    "unit_id": "UNIT-1",
    "sku": "BLUE-BOTTLE-001",
    "product_title": "Blue Bottle",
    "spec_colour": "blue",
    "spec_variant": "standard",
    "spec_components": ["bottle", "cap"],
    "cartons_ordered": 2,
    "units_per_carton_ordered": 12,
    "qty_ordered": 24,
}
IMAGE_REFS = ["receiving/front.jpg", "receiving/open-carton.jpg"]


def response_for(values=None, uncertain=None):
    values = values or {}
    uncertain = uncertain or set()
    defaults = {
        "identity": "yes",
        "carton_count": 2,
        "units_per_carton": 12,
        "quantity": 24,
        "carton_damage": "none",
        "unit_damage": "none",
        "colour": "blue",
        "variant": "standard",
        "components": ["bottle", "cap"],
        "quality_flags": [],
    }
    return {
        "observations": {
            check: {
                "observed_value": values.get(check, defaults[check]),
                "uncertainty": check in uncertain,
                "reason": f"Observed {check} in receiving image",
                "evidence": [{"source_ref": IMAGE_REFS[0], "detail": "visible"}],
            }
            for check in CHECKS
        }
    }


class CountingClient:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def __call__(self, payload):
        self.calls.append(payload)
        if self.error:
            raise self.error
        return self.response


class VisionAdapterTests(unittest.TestCase):
    def test_successful_response_runs_all_checks_from_one_call(self):
        client = CountingClient(response_for())
        result = VisionInspectionAdapter(client).inspect_unit(UNIT, IMAGE_REFS)

        self.assertEqual(len(client.calls), 1)
        self.assertEqual(set(result["checks"]), set(CHECKS))
        self.assertEqual(result["overall_verdict"], "PASS")
        self.assertEqual(result["checks"]["quantity"]["evidence"][0], IMAGE_REFS[0])

    def test_valid_detailed_evidence_is_preserved_on_its_check(self):
        response = response_for()
        response["observations"]["quantity"]["evidence"] = [{
            "source_ref": IMAGE_REFS[1],
            "detail": "Opened carton label and all visible units support count 24",
        }]
        client = CountingClient(response)

        result = VisionInspectionAdapter(client).inspect_unit(UNIT, IMAGE_REFS)

        self.assertEqual(
            result["checks"]["quantity"]["evidence_items"],
            response["observations"]["quantity"]["evidence"],
        )
        self.assertNotIn("quantity", result["checks"]["carton_count"]["evidence_items"][0]["detail"])

    def test_malformed_response_fails_open(self):
        client = CountingClient({"observations": {"identity": {}}})
        result = VisionInspectionAdapter(client).inspect_unit(UNIT, IMAGE_REFS)

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["findings"][0]["type"], "pending_review")

    def test_type_invalid_response_fails_open(self):
        response = response_for(values={"quantity": "twenty-four"})
        client = CountingClient(response)

        result = VisionInspectionAdapter(client).inspect_unit(UNIT, IMAGE_REFS)

        self.assertEqual(result["status"], "pending")

    def test_json_string_response_is_supported(self):
        import json

        client = CountingClient(json.dumps(response_for()))
        result = VisionInspectionAdapter(client).inspect_unit(UNIT, IMAGE_REFS)

        self.assertEqual(result["status"], "complete")

    def test_model_failure_fails_open_without_blocking_receiving(self):
        client = CountingClient(error=TimeoutError("timed out"))
        result = VisionInspectionAdapter(client).inspect_unit(UNIT, IMAGE_REFS)

        self.assertEqual(len(client.calls), 1)
        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["record_id"], UNIT["record_id"])

    def test_missing_visual_evidence_is_uncertain_without_a_model_call(self):
        client = CountingClient(response_for())
        result = VisionInspectionAdapter(client).inspect_unit(UNIT, [])

        self.assertEqual(len(client.calls), 0)
        self.assertEqual(result["overall_verdict"], "UNCERTAIN")
        self.assertEqual(result["checks"]["identity"]["verdict"], "UNCERTAIN")

    def test_ambiguous_observation_is_uncertain(self):
        client = CountingClient(response_for(uncertain={"colour"}))
        result = VisionInspectionAdapter(client).inspect_unit(UNIT, IMAGE_REFS)

        self.assertEqual(result["checks"]["colour"]["verdict"], "UNCERTAIN")
        self.assertIsNone(result["model_observations"]["colour"]["observed_value"])

    def test_evidence_cannot_reference_an_unavailable_image(self):
        response = response_for()
        response["observations"]["identity"]["evidence"][0]["source_ref"] = "missing.jpg"
        client = CountingClient(response)

        result = VisionInspectionAdapter(client).inspect_unit(UNIT, IMAGE_REFS)

        self.assertEqual(result["status"], "pending")

    def test_malformed_evidence_fails_open(self):
        response = response_for()
        response["observations"]["identity"]["evidence"] = [{
            "source_ref": IMAGE_REFS[0],
        }]
        client = CountingClient(response)

        result = VisionInspectionAdapter(client).inspect_unit(UNIT, IMAGE_REFS)

        self.assertEqual(result["status"], "pending")

    def test_uncertain_observation_keeps_evidence_without_definite_value(self):
        response = response_for(uncertain={"colour"})
        response["observations"]["colour"]["evidence"][0]["detail"] = (
            "Image is too dark to establish the product colour"
        )
        client = CountingClient(response)

        result = VisionInspectionAdapter(client).inspect_unit(UNIT, IMAGE_REFS)

        self.assertEqual(result["checks"]["colour"]["verdict"], "UNCERTAIN")
        self.assertIsNone(result["model_observations"]["colour"]["observed_value"])
        self.assertEqual(
            result["checks"]["colour"]["evidence_items"][0]["detail"],
            "Image is too dark to establish the product colour",
        )

    def test_valid_optional_location_is_preserved(self):
        response = response_for()
        response["observations"]["identity"]["evidence"][0]["location"] = {
            "x": 0.1,
            "y": 0.2,
            "width": 0.5,
            "height": 0.4,
        }
        client = CountingClient(response)

        result = VisionInspectionAdapter(client).inspect_unit(UNIT, IMAGE_REFS)

        self.assertEqual(
            result["checks"]["identity"]["evidence_items"][0]["location"],
            response["observations"]["identity"]["evidence"][0]["location"],
        )

    def test_invalid_optional_location_fails_open(self):
        response = response_for()
        response["observations"]["identity"]["evidence"][0]["location"] = {
            "x": 1.2,
            "y": 0.2,
            "width": 0.5,
            "height": 0.4,
        }
        client = CountingClient(response)

        result = VisionInspectionAdapter(client).inspect_unit(UNIT, IMAGE_REFS)

        self.assertEqual(result["status"], "pending")


if __name__ == "__main__":
    unittest.main()