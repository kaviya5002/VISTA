def calculate_cost_impact(vehicle):
    root_causes = vehicle.get("root_cause", [])
    health = vehicle["health_score"]

    # Base costs per component type
    repair_now = 0
    failure_cost = 0

    if "Battery Degradation" in root_causes:
        repair_now += 4000
        failure_cost += 18000
    elif "Low Battery Voltage" in root_causes:
        repair_now += 2500
        failure_cost += 10000
    elif "Battery Below Optimal" in root_causes:
        repair_now += 1000
        failure_cost += 4000

    if "Thermal Stress" in root_causes:
        repair_now += 5000
        failure_cost += 25000
    elif "Cooling System Stress" in root_causes:
        repair_now += 2000
        failure_cost += 9000
    elif "Elevated Temperature" in root_causes:
        repair_now += 800
        failure_cost += 3000

    if "Engine Stress" in root_causes:
        repair_now += 6000
        failure_cost += 30000
    elif "High RPM" in root_causes:
        repair_now += 1500
        failure_cost += 6000

    # Fallback for healthy vehicles
    if repair_now == 0:
        repair_now = 500
        failure_cost = 2000

    # Scale by health degradation — worse health = higher urgency cost
    degradation = (100 - health) / 100
    repair_now = round(repair_now * (1 + degradation * 0.5))
    failure_cost = round(failure_cost * (1 + degradation * 0.3))

    vehicle["repair_now_cost"] = repair_now
    vehicle["failure_cost"] = failure_cost
    vehicle["potential_savings"] = failure_cost - repair_now

    return vehicle
