"""
Twin Prediction Service — runs future simulated sensor values through all ML models.

Flow:
    Future simulated sensors
        → predict_future_health()
        → predict_future_failure()
        → predict_future_rul()
        → predict_future_priority()
"""
from services.health_model_service  import predict_health_with_model
from services.failure_model_service import predict_with_model
from services.rul_model_service     import predict_rul_with_model
from services.fleet_optimizer_service import predict_priority


def predict_future_health(sensors: dict) -> int:
    """
    Calls Health ML model with future simulated sensor values.
    Falls back to physics formula if model unavailable.
    """
    result = predict_health_with_model(sensors)
    if result is not None:
        return result

    # Physics fallback
    health      = sensors.get("health_score", 50)
    temperature = sensors.get("temperature", 50)
    battery     = sensors.get("battery_voltage", 12.0)
    rpm         = sensors.get("rpm", 1500)

    health_loss = (
        max(0, temperature - 90) * 0.15 +
        max(0, 12 - battery)     * 4.0  +
        max(0, rpm - 5000)       / 1500
    )
    return max(0, round(health - health_loss))


def predict_future_failure(sensors: dict) -> float:
    """
    Calls Failure ML model with future simulated sensor values.
    Falls back to physics formula if model unavailable.
    """
    result = predict_with_model(sensors)
    if result is not None:
        return result["ml_failure_probability"]

    # Physics fallback
    failure     = sensors.get("failure_probability", 50)
    temperature = sensors.get("temperature", 50)
    battery     = sensors.get("battery_voltage", 12.0)

    return min(100, round(
        failure +
        max(0, temperature - 90) * 0.25 +
        max(0, 12 - battery)     * 2.0
    ))


def predict_future_rul(sensors: dict) -> int:
    """
    Calls RUL ML model with future simulated sensor values.
    Falls back to direct subtraction if model unavailable.
    """
    result = predict_rul_with_model(sensors)
    if result is not None:
        return result

    # Physics fallback — RUL already decremented by days in simulate()
    return max(0, sensors.get("rul_days", 0))


def predict_future_priority(health: int, failure: float, rul: int) -> str:
    """
    Calls Fleet Optimizer ML model to assign maintenance priority label.
    Falls back to threshold rules if model unavailable.
    """
    # Estimate costs from health level (mirrors cost_analysis.py scaling logic)
    degradation    = (100 - health) / 100
    repair_cost    = round(500  * (1 + degradation * 0.5))
    failure_cost   = round(2000 * (1 + degradation * 0.3))
    potential_savings = failure_cost - repair_cost

    result = predict_priority(health, failure, rul, repair_cost, failure_cost, potential_savings)
    if result is not None:
        return result

    # Threshold fallback
    score = failure + (100 - health)
    if score >= 140:
        return "Immediate"
    elif score >= 100:
        return "Schedule"
    return "Monitor"
