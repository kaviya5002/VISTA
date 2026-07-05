"""
Natural Language Explanation Service
======================================
Converts SHAP top-5 contributors into human-readable sentences.
"""


def _severity(prob: float) -> str:
    if prob >= 85: return "critically high"
    if prob >= 65: return "high"
    if prob >= 40: return "elevated"
    return "low"


def _rul_urgency(rul: int) -> str:
    if rul <= 3:  return "failure is imminent within 72 hours"
    if rul <= 7:  return "the service window is closing within one week"
    if rul <= 14: return "service should be scheduled within two weeks"
    return "routine monitoring is sufficient"


def _factor_sentence(factor: dict) -> str:
    label  = factor["label"]
    impact = factor["impact"]
    dirn   = factor["direction"]
    sign   = "increases" if dirn == "increases_risk" else "reduces"

    templates = {
        "Tire Condition":        f"Tire condition {sign} failure risk by {impact}% — worn tires raise mechanical stress.",
        "Brake Condition":       f"Brake condition contributes {impact}% — degraded brakes elevate system load.",
        "Battery Status":        f"Battery status {sign} risk by {impact}% — weak battery reduces power reliability.",
        "Reported Issues":       f"Reported issues drive {impact}% of risk — unresolved faults compound failure probability.",
        "Maintenance History":   f"Maintenance history accounts for {impact}% — irregular servicing accelerates wear.",
        "Service History":       f"Service history contributes {impact}% — gaps in servicing increase component fatigue.",
        "Accident History":      f"Accident history adds {impact}% — prior damage weakens structural integrity.",
        "Odometer Reading":      f"Odometer reading contributes {impact}% — high mileage correlates with component wear.",
        "Mileage":               f"Mileage accounts for {impact}% of risk — higher mileage increases wear probability.",
        "Vehicle Age":           f"Vehicle age contributes {impact}% — older vehicles have higher baseline failure rates.",
        "Air Temperature":       f"Air temperature {sign} risk by {impact}% — elevated ambient heat accelerates degradation.",
        "Process Temperature":   f"Process temperature contributes {impact}% — thermal stress on components is elevated.",
        "Rotational Speed":      f"Rotational speed {sign} risk by {impact}% — sustained high RPM increases mechanical friction.",
        "Torque":                f"Torque contributes {impact}% — high torque places drivetrain under stress.",
        "Tool Wear":             f"Tool wear accounts for {impact}% — significant internal wear detected.",
        "Health Score":          f"Current health score drives {impact}% of priority — lower health demands urgent action.",
        "Failure Probability":   f"Failure probability contributes {impact}% to fleet priority ranking.",
        "Remaining Useful Life": f"Remaining useful life accounts for {impact}% — limited life remaining elevates urgency.",
    }

    return templates.get(label, f"{label} contributes {impact}% to the prediction ({dirn.replace('_', ' ')}).")


def generate_explanation(
    vehicle: dict,
    shap_result: dict,
) -> dict:
    """
    Convert SHAP output into a structured natural language explanation.

    Parameters
    ----------
    vehicle     : enriched vehicle dict (health_score, failure_probability, etc.)
    shap_result : output from shap_service.explain_vehicle()

    Returns
    -------
    dict with keys: summary, factors_text, recommendation, confidence_note
    """
    prob   = vehicle.get("failure_probability", 0)
    health = vehicle.get("health_score", 50)
    rul    = vehicle.get("remaining_useful_life_days", 15)
    status = vehicle.get("status", "Unknown")
    vid    = vehicle.get("vehicle_id", 0)

    failure_factors = shap_result.get("models", {}).get("failure", [])
    top_label       = failure_factors[0]["label"] if failure_factors else "sensor readings"
    second_label    = failure_factors[1]["label"] if len(failure_factors) > 1 else None

    # ── Summary sentence ──────────────────────────────────────────────────────
    if second_label:
        summary = (
            f"Vehicle {vid} failure risk is primarily driven by {top_label.lower()} "
            f"and {second_label.lower()}. "
            f"Predicted failure probability: {prob}% ({_severity(prob)})."
        )
    else:
        summary = (
            f"Vehicle {vid} failure risk is primarily driven by {top_label.lower()}. "
            f"Predicted failure probability: {prob}% ({_severity(prob)})."
        )

    # ── Per-factor sentences ──────────────────────────────────────────────────
    factors_text = [_factor_sentence(f) for f in failure_factors]

    # ── RUL note ──────────────────────────────────────────────────────────────
    rul_note = f"With {rul} day(s) of useful life remaining, {_rul_urgency(rul)}."

    # ── Recommendation ────────────────────────────────────────────────────────
    if prob >= 75 or rul <= 5:
        recommendation = "Immediate repair required — do not delay service."
    elif prob >= 50 or rul <= 14:
        recommendation = "Schedule maintenance within the next 7 days."
    elif prob >= 30:
        recommendation = "Monitor closely and plan service within 2 weeks."
    else:
        recommendation = "Continue routine monitoring — no immediate action needed."

    # ── Confidence note ───────────────────────────────────────────────────────
    shap_on = shap_result.get("shap_enabled", False)
    confidence_note = (
        "Explanation generated using SHAP TreeExplainer — "
        "values show this vehicle's specific contribution, not general feature importance."
        if shap_on else
        "Explanation generated using feature importance fallback — "
        "install shap for per-vehicle SHAP values."
    )

    return {
        "summary":         summary,
        "factors_text":    factors_text,
        "rul_note":        rul_note,
        "recommendation":  recommendation,
        "confidence_note": confidence_note,
    }
