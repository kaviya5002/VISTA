"""
Twin Service — fetches a vehicle, runs all ML pipelines, builds digital twin.
"""
from services.vehicle_repository import get_all_vehicles, get_vehicle as get_vehicle_by_id
from services.health_score import calculate_health
from services.failure_forecast import predict_failure
from services.root_cause import analyze_root_cause
from services.rul_engine import calculate_rul
from services.cost_analysis import calculate_cost_impact
from services.fleet_optimizer import optimize_fleet
from engines.digital_twin_engine import build_digital_twin
from engines.component_twin_engine import build_component_twin


def _enrich(vehicle: dict) -> dict:
    vehicle = calculate_health(vehicle)
    vehicle = predict_failure(vehicle)
    vehicle = analyze_root_cause(vehicle)
    vehicle = calculate_rul(vehicle)
    vehicle = calculate_cost_impact(vehicle)
    priority = vehicle.get("failure_probability", 0) + (100 - vehicle.get("health_score", 100))
    if priority >= 140:
        vehicle["fleet_action"] = "Immediate Repair"
    elif priority >= 100:
        vehicle["fleet_action"] = "Schedule Maintenance"
    else:
        vehicle["fleet_action"] = "Monitor"
    return vehicle


def _find_vehicle(vehicle_id: int) -> dict | None:
    return get_vehicle_by_id(vehicle_id)


def get_twin(vehicle_id: int) -> dict | None:
    vehicle = _find_vehicle(vehicle_id)
    if not vehicle:
        return None
    return build_digital_twin(_enrich(vehicle))


def get_component_twin(vehicle_id: int) -> dict | None:
    vehicle = _find_vehicle(vehicle_id)
    if not vehicle:
        return None
    return build_component_twin(_enrich(vehicle))


def get_all_twins() -> list[dict]:
    vehicles  = get_all_vehicles()
    enriched  = [_enrich(v) for v in vehicles]
    optimized = optimize_fleet(enriched)
    return [build_digital_twin(v) for v in optimized]
