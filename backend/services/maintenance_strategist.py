def _generate_reasoning(vehicle: dict) -> list:
    reasoning = []
    health       = vehicle["health_score"]
    fail_prob    = vehicle["failure_probability"]
    rul          = vehicle["remaining_useful_life_days"]
    root_causes  = vehicle.get("root_cause", [])
    voltage      = vehicle["battery_voltage"]
    temp         = vehicle["temperature"]
    rpm          = vehicle["rpm"]

    # Health
    if health < 30:
        reasoning.append(f"Health score is critically low ({health}%) — immediate intervention required.")
    elif health < 50:
        reasoning.append(f"Health score has degraded to {health}% — component failure likely soon.")
    elif health < 70:
        reasoning.append(f"Health score is at {health}% — early signs of wear detected.")

    # Failure probability
    if fail_prob > 90:
        reasoning.append(f"Failure probability is extremely high ({fail_prob}%) — failure imminent.")
    elif fail_prob > 70:
        reasoning.append(f"Failure probability is high ({fail_prob}%) — urgent attention needed.")
    elif fail_prob > 40:
        reasoning.append(f"Failure probability is elevated ({fail_prob}%) — monitor closely.")

    # RUL
    if rul <= 3:
        reasoning.append(f"Remaining Useful Life is critically low — only {rul} day(s) remaining.")
    elif rul <= 7:
        reasoning.append(f"Remaining Useful Life is {rul} days — service window is closing.")
    elif rul <= 20:
        reasoning.append(f"Remaining Useful Life is {rul} days — schedule service soon.")

    # Root cause
    for cause in root_causes:
        if cause not in ["No Failure", "No Issues Detected"]:
            reasoning.append(f"Root cause identified: {cause}.")

    # Sensor specifics
    if voltage < 11.5:
        reasoning.append(f"Battery voltage critically low at {voltage}V (minimum safe: 11.5V).")
    elif voltage < 12.0:
        reasoning.append(f"Battery voltage below optimal at {voltage}V.")

    if temp > 80:
        reasoning.append(f"Engine temperature critical at {temp}°C — risk of thermal failure.")
    elif temp > 60:
        reasoning.append(f"Engine temperature elevated at {temp}°C.")

    if rpm > 4500:
        reasoning.append(f"RPM at {rpm} — engine under critical stress.")
    elif rpm > 3500:
        reasoning.append(f"RPM running high at {rpm}.")

    if not reasoning:
        reasoning.append("All systems operating within normal parameters.")

    return reasoning


def _calculate_confidence(vehicle: dict) -> int:
    """
    Heuristic confidence based on agreement between ML model outputs.
    Higher confidence when multiple signals agree on severity.
    """
    health    = vehicle["health_score"]
    fail_prob = vehicle["failure_probability"]
    rul       = vehicle["remaining_useful_life_days"]
    priority  = vehicle.get("priority", "Low")

    # Base confidence from individual model sources
    health_conf     = 90 if vehicle.get("health_source")     == "Health ML Model"     else 70
    failure_conf    = 90 if vehicle.get("ml_model_used")                               else 70
    root_conf       = 90 if vehicle.get("root_cause_source") == "Root Cause ML Model" else 70
    rul_conf        = 85 if vehicle.get("rul_source")        == "NASA ML Model"        else 65
    optimizer_conf  = 95 if vehicle.get("fleet_optimizer_source") == "Fleet Optimization ML Model" else 70

    base = round(
        health_conf    * 0.20 +
        failure_conf   * 0.30 +
        root_conf      * 0.20 +
        rul_conf       * 0.15 +
        optimizer_conf * 0.15
    )

    # Boost confidence when multiple signals agree
    critical_signals = sum([
        health    < 40,
        fail_prob > 70,
        rul       < 10,
        priority  == "Immediate"
    ])
    if critical_signals >= 3:
        base = min(99, base + 5)

    return base


def _next_service(priority: str, rul: int) -> str:
    if priority == "Immediate" or rul <= 3:
        return "Within 24 Hours"
    elif priority == "High" or rul <= 7:
        return "Within 3 Days"
    elif priority == "Medium" or rul <= 20:
        return "Within 7 Days"
    else:
        return "Next Scheduled Service"


def _risk_level(health: int, fail_prob: int, priority: str) -> str:
    if priority == "Immediate" or health < 30 or fail_prob > 85:
        return "Critical"
    elif priority == "High" or health < 50 or fail_prob > 60:
        return "High"
    elif priority == "Medium" or health < 70 or fail_prob > 35:
        return "Medium"
    return "Low"


def ai_maintenance_strategy(vehicle: dict) -> dict:
    health       = vehicle["health_score"]
    rul          = vehicle["remaining_useful_life_days"]
    priority     = vehicle.get("priority", "Low")
    repair_cost  = vehicle["repair_now_cost"]
    failure_cost = vehicle["failure_cost"]
    savings      = vehicle["potential_savings"]
    fail_prob    = vehicle["failure_probability"]

    # Recommendation
    recommendation_map = {
        "Immediate": "Immediate Repair",
        "High":      "Urgent Maintenance",
        "Medium":    "Schedule Service",
        "Low":       "Continue Monitoring"
    }
    recommendation = recommendation_map.get(priority, "Continue Monitoring")

    confidence    = _calculate_confidence(vehicle)
    reasoning     = _generate_reasoning(vehicle)
    next_service  = _next_service(priority, rul)
    estimated_risk = _risk_level(health, fail_prob, priority)

    business_impact = {
        "repair_cost":              repair_cost,
        "failure_cost":             failure_cost,
        "potential_savings":        savings,
        "downtime_prevented_hours": max(2, int(fail_prob / 8))
    }

    vehicle["maintenance_recommendation"] = recommendation
    vehicle["confidence_score"]           = confidence
    vehicle["reasoning"]                  = reasoning
    vehicle["business_impact"]            = business_impact
    vehicle["next_service"]               = next_service
    vehicle["estimated_risk"]             = estimated_risk
    vehicle["expected_savings"]           = savings
    vehicle["rul_days"]                   = rul
    vehicle["strategist_source"]          = "AI Maintenance Strategist v2"

    return vehicle
