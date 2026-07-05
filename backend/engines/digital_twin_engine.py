"""
Digital Twin Engine — assembles current + future state into twin payload.
"""
from engines.simulation_engine import forecast_future, simulate_repair, simulate_ignore


def build_digital_twin(vehicle: dict) -> dict:
    current_state = {
        "health":               vehicle.get("health_score"),
        "battery":              vehicle.get("battery_voltage"),
        "temperature":          vehicle.get("temperature"),
        "rpm":                  vehicle.get("rpm"),
        "speed":                vehicle.get("speed"),
        "failure_probability":  vehicle.get("failure_probability"),
        "rul":                  vehicle.get("rul"),
        "root_cause":           vehicle.get("root_cause"),
        "priority":             vehicle.get("fleet_action", vehicle.get("maintenance_strategy")),
    }

    return {
        "vehicle_id":    vehicle["vehicle_id"],
        "current_state": current_state,
        "future_state":  forecast_future(vehicle),
        "simulations": {
            "repair_today": simulate_repair(vehicle),
            "ignore":       simulate_ignore(vehicle),
        },
    }
