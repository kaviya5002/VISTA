from fastapi import APIRouter, HTTPException
from services.twin_service import get_twin, get_all_twins, get_component_twin
from services.vehicle_repository import get_all_vehicles, get_vehicle
from services.health_score import calculate_health
from services.failure_forecast import predict_failure
from services.rul_engine import calculate_rul
from engines.component_twin_engine import build_component_twin

router = APIRouter(prefix="/digital_twin", tags=["Digital Twin"])


@router.get("/component/{vehicle_id}")
def component_twin(vehicle_id: int):
    twin = get_component_twin(vehicle_id)
    if not twin:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return twin


@router.post("/component/{vehicle_id}/repair")
def component_repair(vehicle_id: int, payload: dict):
    """
    Simulate repairing one or more components.
    Body: { "components": ["battery", "motor", ...] }
    Returns the updated component twin as if those parts were replaced.
    """
    components = payload.get("components", [])
    vehicle = next((v for v in get_all_vehicles() if v["vehicle_id"] == vehicle_id), None)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    # Patch sensor values for repaired components
    if "battery" in components:
        vehicle["battery_voltage"] = 12.8
    if "motor" in components or "cooling" in components:
        vehicle["temperature"]     = min(vehicle.get("temperature", 50), 65)
        vehicle["rpm"]             = min(vehicle.get("rpm", 1500), 2000)
    if "brakes" in components:
        vehicle["speed"]           = min(vehicle.get("speed", 60), 60)

    vehicle = calculate_health(vehicle)
    vehicle = predict_failure(vehicle)
    vehicle = calculate_rul(vehicle)
    return build_component_twin(vehicle)


@router.get("/{vehicle_id}")
def digital_twin(vehicle_id: int):
    twin = get_twin(vehicle_id)
    if not twin:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return twin


@router.get("/")
def all_digital_twins():
    return get_all_twins()
