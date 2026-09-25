"""
Receiving Manager - Headless Inspection Agent

Purpose:
    Turn one receiving record into an evidence-backed inspection result.

Important rules:
    - UNCERTAIN is a first-class verdict.
    - Never invent observed evidence.
    - FAIL means evidence shows the condition is not met.
    - UNCERTAIN means evidence is insufficient.
    - Model failures must fail open and produce PENDING_REVIEW.
    - All checks for one unit are represented in one inspection result.
"""


VALID_VERDICTS = {"PASS", "FAIL", "UNCERTAIN"}


def evidence(text):
    """Create a simple evidence item."""
    return [text]


def uncertain_result(reason, **extra):
    """Create a standard UNCERTAIN check result."""
    return {
        "verdict": "UNCERTAIN",
        "evidence": evidence(reason),
        "confidence": None,
        **extra,
    }


def pass_result(reason, **extra):
    """Create a standard PASS check result."""
    return {
        "verdict": "PASS",
        "evidence": evidence(reason),
        "confidence": None,
        **extra,
    }


def fail_result(reason, **extra):
    """Create a standard FAIL check result."""
    return {
        "verdict": "FAIL",
        "evidence": evidence(reason),
        "confidence": None,
        **extra,
    }


# ---------------------------------------------------------
# IDENTITY
# ---------------------------------------------------------

def check_identity(unit):
    identity = unit.get("identity_match")

    if identity == "yes":
        return pass_result(
            "Recorded identity match: yes"
        )

    if identity == "no":
        return fail_result(
            "Recorded identity match: no"
        )

    return uncertain_result(
        "Identity evidence is missing or marked uncertain"
    )


# ---------------------------------------------------------
# QUANTITY
# ---------------------------------------------------------

def check_quantity(unit):
    expected = unit.get("qty_ordered")
    observed = unit.get("qty_received")

    if expected is None or observed is None:
        return uncertain_result(
            "Expected or observed quantity is missing",
            expected=expected,
            observed=observed,
        )

    if observed == expected:
        return pass_result(
            f"Expected quantity: {expected}",
            expected=expected,
            observed=observed,
        )

    difference = observed - expected

    return fail_result(
        f"Expected quantity: {expected}; "
        f"observed quantity: {observed}; "
        f"quantity discrepancy: {difference}",
        expected=expected,
        observed=observed,
        discrepancy=difference,
    )


# ---------------------------------------------------------
# CARTON COUNT
# ---------------------------------------------------------

def check_carton_count(unit):
    expected = unit.get("cartons_ordered")
    observed = unit.get("cartons_received")

    if expected is None or observed is None:
        return uncertain_result(
            "Expected or observed carton count is missing",
            expected=expected,
            observed=observed,
        )

    if observed == expected:
        return pass_result(
            f"Expected cartons: {expected}; observed cartons: {observed}",
            expected=expected,
            observed=observed,
        )

    return fail_result(
        f"Expected cartons: {expected}; observed cartons: {observed}",
        expected=expected,
        observed=observed,
    )


# ---------------------------------------------------------
# UNITS PER CARTON
# ---------------------------------------------------------

def check_units_per_carton(unit):
    expected = unit.get("units_per_carton_ordered")
    observed = unit.get("units_per_carton_counted")

    if expected is None or observed is None:
        return uncertain_result(
            "Expected or observed units-per-carton count is missing",
            expected=expected,
            observed=observed,
        )

    if observed == expected:
        return pass_result(
            f"Expected units per carton: {expected}; "
            f"observed: {observed}",
            expected=expected,
            observed=observed,
        )

    return fail_result(
        f"Expected units per carton: {expected}; "
        f"observed: {observed}",
        expected=expected,
        observed=observed,
    )


# ---------------------------------------------------------
# CARTON DAMAGE
# ---------------------------------------------------------

def check_carton_damage(unit):
    damage = unit.get("carton_damage")

    if damage == "none":
        return pass_result(
            "No visible carton damage recorded",
            finding="none",
        )

    if damage in {"crushing", "water", "tears"}:
        return fail_result(
            f"Visible carton damage: {damage}",
            finding=damage,
        )

    return uncertain_result(
        "Carton condition is missing or marked uncertain",
        finding=damage,
    )


# ---------------------------------------------------------
# UNIT DAMAGE
# ---------------------------------------------------------

def check_unit_damage(unit):
    damage = unit.get("unit_damage")

    if damage == "none":
        return pass_result(
            "No visible unit damage recorded",
            finding="none",
        )

    if damage in {"crushing", "water", "tears"}:
        return fail_result(
            f"Visible unit damage: {damage}",
            finding=damage,
        )

    return uncertain_result(
        "Unit condition is missing or marked uncertain",
        finding=damage,
    )


# ---------------------------------------------------------
# VARIANT
# ---------------------------------------------------------

def check_variant(unit):
    expected = unit.get("spec_variant")
    observed = unit.get("observed_variant")

    # The expected value alone is NOT enough to claim PASS.
    if expected is None or observed is None:
        return uncertain_result(
            "Expected or observed variant information is insufficient",
            expected=expected,
            observed=observed,
        )

    if expected == observed:
        return pass_result(
            f"Expected variant: {expected}; "
            f"observed variant: {observed}",
            expected=expected,
            observed=observed,
        )

    return fail_result(
        f"Expected variant: {expected}; "
        f"observed variant: {observed}",
        expected=expected,
        observed=observed,
    )


# ---------------------------------------------------------
# COLOUR
# ---------------------------------------------------------

def check_colour(unit):
    expected = unit.get("spec_colour")
    observed = unit.get("observed_colour")

    if expected is None or observed is None:
        return uncertain_result(
            "Expected or observed colour information is insufficient",
            expected=expected,
            observed=observed,
        )

    if expected == observed:
        return pass_result(
            f"Expected colour: {expected}; "
            f"observed colour: {observed}",
            expected=expected,
            observed=observed,
        )

    return fail_result(
        f"Expected colour: {expected}; "
        f"observed colour: {observed}",
        expected=expected,
        observed=observed,
    )


# ---------------------------------------------------------
# COMPONENTS
# ---------------------------------------------------------

def check_components(unit):
    expected = unit.get("spec_components")
    observed = unit.get("observed_components")

    if expected is None or observed is None:
        return uncertain_result(
            "Expected or observed component information is insufficient",
            expected=expected,
            observed=observed,
        )

    expected_set = set(expected)
    observed_set = set(observed)

    missing = sorted(expected_set - observed_set)
    unexpected = sorted(observed_set - expected_set)

    if missing:
        return fail_result(
            f"Missing components: {', '.join(missing)}",
            expected=expected,
            observed=observed,
            missing=missing,
            unexpected=unexpected,
        )

    if unexpected:
        return fail_result(
            f"Unexpected components: {', '.join(unexpected)}",
            expected=expected,
            observed=observed,
            missing=[],
            unexpected=unexpected,
        )

    return pass_result(
        "All expected components were observed",
        expected=expected,
        observed=observed,
        missing=[],
        unexpected=[],
    )


# ---------------------------------------------------------
# QUALITY FLAGS
# ---------------------------------------------------------

def check_quality_flags(unit):
    raw_flags = unit.get("quality_flags", "")

    if raw_flags is None:
        raw_flags = ""

    if isinstance(raw_flags, str):
        flags = [
            flag.strip()
            for flag in raw_flags.split(";")
            if flag.strip()
        ]
    else:
        flags = list(raw_flags)

    if not flags:
        return pass_result(
            "No quality flags recorded",
            flags=[],
        )

    return fail_result(
        f"Quality flags detected: {', '.join(flags)}",
        flags=flags,
    )


# ---------------------------------------------------------
# MODEL FAILURE / FAIL OPEN
# ---------------------------------------------------------

def pending_review(unit, reason):
    """
    Fail-open behavior.

    If the vision/model layer fails, we preserve the receiving
    capture and mark the inspection as pending review.
    """

    return {
        "record_id": unit.get("record_id"),
        "unit_id": unit.get("unit_id"),
        "org_id": unit.get("org_id"),
        "captured_at": unit.get("captured_at"),
        "operator_id": unit.get("operator_id"),

        "status": "pending",
        "overall_verdict": "UNCERTAIN",

        "checks": {},

        "findings": [
            {
                "type": "pending_review",
                "reason": reason,
            }
        ],

        "decision_trace": {
            "what_received": {},
            "what_expected": {},
            "checks_performed": [],
            "findings": [
                {
                    "type": "pending_review",
                    "reason": reason,
                }
            ],
            "verdict": "UNCERTAIN",
            "why": (
                "Inspection is pending because the model or "
                "inspection service failed. The receiving record "
                "must not be blocked."
            ),
        },
    }


# ---------------------------------------------------------
# FINDINGS
# ---------------------------------------------------------

def build_findings(checks):
    findings = []

    for check_name, result in checks.items():

        verdict = result.get("verdict")

        if verdict == "FAIL":
            findings.append({
                "check": check_name,
                "type": "failure",
                "reason": result.get("evidence", []),
            })

        elif verdict == "UNCERTAIN":
            findings.append({
                "check": check_name,
                "type": "uncertain",
                "reason": result.get("evidence", []),
            })

    return findings


# ---------------------------------------------------------
# OVERALL VERDICT
# ---------------------------------------------------------

def calculate_overall_verdict(checks):
    verdicts = [
        result.get("verdict")
        for result in checks.values()
    ]

    if "FAIL" in verdicts:
        return "FAIL"

    if "UNCERTAIN" in verdicts:
        return "UNCERTAIN"

    return "PASS"


# ---------------------------------------------------------
# MAIN INSPECTION
# ---------------------------------------------------------

def inspect_unit(unit, model_error=None):
    """
    Inspect one receiving unit.

    model_error:
        Used by the future vision layer when its model call fails.

    The function intentionally supports structured observations now.
    The vision model can populate observed_* fields later.
    """

    # -----------------------------------------------------
    # FAIL OPEN
    # -----------------------------------------------------

    if model_error is not None:
        return pending_review(
            unit,
            f"Vision/model inspection failed: {model_error}"
        )

    # -----------------------------------------------------
    # ALL RECEIVING CHECKS
    # -----------------------------------------------------

    checks = {
        "identity": check_identity(unit),
        "carton_count": check_carton_count(unit),
        "units_per_carton": check_units_per_carton(unit),
        "quantity": check_quantity(unit),
        "carton_damage": check_carton_damage(unit),
        "unit_damage": check_unit_damage(unit),
        "colour": check_colour(unit),
        "variant": check_variant(unit),
        "components": check_components(unit),
        "quality_flags": check_quality_flags(unit),
    }

    overall_verdict = calculate_overall_verdict(checks)

    findings = build_findings(checks)

    # -----------------------------------------------------
    # EXPECTED / RECEIVED TRACE
    # -----------------------------------------------------

    what_expected = {
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

    what_received = {
        "sku": unit.get("observed_sku"),
        "asin": unit.get("observed_asin"),
        "product_title": unit.get("observed_product_title"),
        "colour": unit.get("observed_colour"),
        "variant": unit.get("observed_variant"),
        "components": unit.get("observed_components"),
        "cartons": unit.get("cartons_received"),
        "units_per_carton": unit.get("units_per_carton_counted"),
        "quantity": unit.get("qty_received"),
    }

    # -----------------------------------------------------
    # FINAL RECORD
    # -----------------------------------------------------

    return {
        "record_id": unit.get("record_id"),
        "unit_id": unit.get("unit_id"),
        "org_id": unit.get("org_id"),
        "captured_at": unit.get("captured_at"),
        "operator_id": unit.get("operator_id"),

        "status": "complete",

        "checks": checks,

        "overall_verdict": overall_verdict,

        "findings": findings,

        "decision_trace": {
            "what_received": what_received,
            "what_expected": what_expected,
            "checks_performed": list(checks.keys()),
            "findings": findings,
            "verdict": overall_verdict,

            "why": (
                "Overall verdict is FAIL because at least one "
                "check failed."
                if overall_verdict == "FAIL"
                else
                "Overall verdict is UNCERTAIN because available "
                "evidence is insufficient for at least one check."
                if overall_verdict == "UNCERTAIN"
                else
                "Overall verdict is PASS because all checks passed."
            ),
        },
    }