from services.rul_model_service import predict_rul_with_model, RUL_ML_ENABLED


def calculate_rul(vehicle: dict) -> dict:
    # Use batch-injected result if available (skips model call entirely)
    if "_batch_rul" in vehicle:
        vehicle["remaining_useful_life_days"] = vehicle.pop("_batch_rul")
        vehicle["rul_source"] = "NASA ML Model"
        return vehicle

    # ── ML Model Prediction ───────────────────────────────────────────────────
    ml_rul = predict_rul_with_model(vehicle)

    if ml_rul is not None:
        vehicle["remaining_useful_life_days"] = ml_rul
        vehicle["rul_source"] = "NASA ML Model"
    else:
        health = vehicle["health_score"]
        vehicle["remaining_useful_life_days"] = max(1, round((health / 100) * 30))
        vehicle["rul_source"] = "Formula"

    return vehicle
