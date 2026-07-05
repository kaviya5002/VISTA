from services.root_cause_model_service import predict_root_cause_with_model, ROOT_CAUSE_ML_ENABLED


def analyze_root_cause(vehicle: dict) -> dict:
    # Use batch-injected result if available (skips model call entirely)
    if "_batch_root_cause" in vehicle:
        vehicle["root_cause"] = vehicle.pop("_batch_root_cause")
        vehicle["root_cause_source"] = "Root Cause ML Model"
        return vehicle

    # ── ML Model Prediction ───────────────────────────────────────────────────
    ml_causes = predict_root_cause_with_model(vehicle)

    if ml_causes is not None:
        vehicle["root_cause"] = ml_causes
        vehicle["root_cause_source"] = "Root Cause ML Model"
        return vehicle

    # ── Formula Fallback ──────────────────────────────────────────────────────
    causes = []

    if vehicle["battery_voltage"] < 11.5:
        causes.append("Battery Degradation")
    elif vehicle["battery_voltage"] < 12.0:
        causes.append("Low Battery Voltage")
    elif vehicle["battery_voltage"] < 12.5:
        causes.append("Battery Below Optimal")

    if vehicle["temperature"] > 80:
        causes.append("Thermal Stress")
    elif vehicle["temperature"] > 60:
        causes.append("Cooling System Stress")
    elif vehicle["temperature"] > 45:
        causes.append("Elevated Temperature")

    if vehicle["rpm"] > 4500:
        causes.append("Engine Stress")
    elif vehicle["rpm"] > 3500:
        causes.append("High RPM")

    vehicle["root_cause"] = causes if causes else ["No Issues Detected"]
    vehicle["root_cause_source"] = "Formula"

    return vehicle
