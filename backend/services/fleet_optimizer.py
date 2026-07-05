from services.fleet_optimizer_service import batch_predict_priority

ACTION_MAP = {
    "Immediate": "Immediate Repair",
    "High":      "Urgent Maintenance",
    "Medium":    "Schedule Service",
    "Low":       "Monitor Vehicle"
}

PRIORITY_RANK = {
    "Immediate": 4,
    "High":      3,
    "Medium":    2,
    "Low":       1
}


def optimize_fleet(vehicles: list) -> list:
    # One model call for all 100 vehicles
    priorities = batch_predict_priority(vehicles)

    for i, vehicle in enumerate(vehicles):
        health    = vehicle["health_score"]
        fail_prob = vehicle["failure_probability"]
        rul       = vehicle["remaining_useful_life_days"]
        savings   = vehicle["potential_savings"]
        priority  = priorities[i]

        if priority:
            vehicle["fleet_optimizer_source"] = "Fleet Optimization ML Model"
        else:
            if   health < 35 or fail_prob > 85 or rul < 7:  priority = "Immediate"
            elif health < 50 or fail_prob > 60 or rul < 20: priority = "High"
            elif health < 70 or fail_prob > 35 or rul < 40: priority = "Medium"
            else:                                            priority = "Low"
            vehicle["fleet_optimizer_source"] = "Formula"

        vehicle["priority"]       = priority
        vehicle["fleet_action"]   = ACTION_MAP.get(priority, "Monitor Vehicle")
        vehicle["priority_score"] = round(
            fail_prob * 0.5 + (100 - health) * 0.35 + savings / 1000 * 0.15, 2
        )

    vehicles.sort(key=lambda x: PRIORITY_RANK.get(x["priority"], 0), reverse=True)
    return vehicles
