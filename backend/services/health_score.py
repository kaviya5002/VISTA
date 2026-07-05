from services.health_model_service import predict_health_with_model, HEALTH_ML_ENABLED


def _sensor_score(vehicle: dict) -> float:
    """Multi-factor health score from real sensor ranges in the DB."""
    score = 100.0

    # Temperature: 50-70 good, 70-90 warn, 90-110 bad, >110 critical
    temp = vehicle.get("temperature", 70)
    if temp < 70:
        pass                              # no penalty
    elif temp < 90:
        score -= (temp - 70) * 0.8       # up to -16
    elif temp < 110:
        score -= 16 + (temp - 90) * 1.5  # up to -46
    else:
        score -= 46 + (temp - 110) * 2.0 # severe

    # Battery voltage: >=12.5 good, 12.0-12.5 slight, 11.5-12.0 warn, <11.5 critical
    volt = vehicle.get("battery_voltage", 12.0)
    if volt >= 12.5:
        pass
    elif volt >= 12.0:
        score -= (12.5 - volt) * 10      # up to -5
    elif volt >= 11.5:
        score -= 5 + (12.0 - volt) * 20  # up to -15
    else:
        score -= 15 + (11.5 - volt) * 40 # severe

    # RPM: <3000 fine, 3000-5000 normal, 5000-6000 elevated, >6000 stress
    rpm = vehicle.get("rpm", 3000)
    if rpm < 5000:
        pass
    elif rpm < 6000:
        score -= (rpm - 5000) * 0.01     # up to -10
    else:
        score -= 10 + (rpm - 6000) * 0.02

    # Reported issues / component condition
    score -= vehicle.get("Reported_Issues", 1) * 3
    tire  = vehicle.get("tire",  vehicle.get("tire_condition",  1))
    brake = vehicle.get("brake", vehicle.get("brake_condition", 1))
    if tire  == 0: score -= 12
    if brake == 0: score -= 12

    # Vehicle age & mileage
    age     = vehicle.get("Vehicle_Age", 5)
    mileage = vehicle.get("Mileage", 50000)
    score -= min(age * 1.5, 15)
    score -= min(mileage / 10000, 10)

    return max(5.0, min(100.0, round(score, 1)))


def calculate_health(vehicle: dict) -> dict:
    # ML model outputs 53-68 for all vehicles (not calibrated for this dataset)
    # Discard ML score, use sensor formula which produces real spread
    if "_batch_health" in vehicle:
        vehicle.pop("_batch_health")  # discard — not useful
    score = _sensor_score(vehicle)
    vehicle["health_source"] = "Sensor Formula"

    score = max(5.0, min(100.0, score))

    if score >= 75:
        status = "Healthy"
    elif score >= 45:
        status = "Warning"
    else:
        status = "Critical"

    vehicle["health_score"] = score
    vehicle["status"] = status
    return vehicle
