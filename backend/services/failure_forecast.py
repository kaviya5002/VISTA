from services.failure_model_service import predict_with_model, ML_ENABLED


def predict_failure(vehicle: dict) -> dict:
    temp    = vehicle["temperature"]
    voltage = vehicle["battery_voltage"]
    rpm     = vehicle["rpm"]

    # Use batch-injected result if available
    if "_batch_failure" in vehicle:
        ml_result = vehicle.pop("_batch_failure")
    else:
        ml_result = predict_with_model(vehicle)

    if ml_result:
        # Blend ML probability with sensor formula for robustness
        formula_prob = (
            (temp / 120) * 40 +
            ((14 - voltage) / 5) * 20 +
            (rpm / 7000) * 40
        )
        formula_prob = min(round(formula_prob), 100)

        # Weight: 60% ML model, 40% sensor formula
        probability = round(ml_result["ml_failure_probability"] * 0.6 + formula_prob * 0.4)
        probability = min(probability, 100)

        vehicle["ml_model_used"]        = True
        vehicle["ml_failure_prediction"] = ml_result["ml_failure_prediction"]
        vehicle["ml_raw_probability"]   = ml_result["ml_failure_probability"]
    else:
        # ── Formula Fallback ──────────────────────────────────────────────────
        probability = (
            (temp / 120) * 40 +
            ((14 - voltage) / 5) * 20 +
            (rpm / 7000) * 40
        )
        probability = min(round(probability), 100)
        vehicle["ml_model_used"] = False

    # Estimated days to failure
    if probability >= 70:
        days = 5
    elif probability >= 50:
        days = 10
    elif probability >= 30:
        days = 20
    else:
        days = 30

    # Risk label
    if probability >= 60:
        risk = "High"
    elif probability >= 30:
        risk = "Medium"
    else:
        risk = "Low"

    vehicle["failure_probability"]    = probability
    vehicle["failure_risk"]           = risk
    vehicle["estimated_failure_days"] = days

    return vehicle
