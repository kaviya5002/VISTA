from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.twin_service import _enrich
from services.vehicle_repository import get_all_vehicles, get_vehicle
from engines.scenario_engine import (
    simulate_battery_replacement,
    simulate_cooling_repair,
    simulate_full_service,
    simulate_ignore_vehicle,
    compare_all_scenarios,
)

router = APIRouter(tags=["Scenario Simulator"])

SCENARIO_MAP = {
    "battery_replacement": simulate_battery_replacement,
    "cooling_repair":      simulate_cooling_repair,
    "full_service":        simulate_full_service,
    "ignore":              simulate_ignore_vehicle,
}


class SimulateRequest(BaseModel):
    vehicle_id: int
    scenario:   str


class CompareRequest(BaseModel):
    vehicle_id: int


def _get_vehicle(vehicle_id: int) -> dict:
    vehicle = get_vehicle(vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return _enrich(vehicle)


# POST /simulate  — single scenario
@router.post("/simulate")
def simulate_scenario(req: SimulateRequest):
    fn = SCENARIO_MAP.get(req.scenario)
    if not fn:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scenario '{req.scenario}'. "
                   f"Valid options: {list(SCENARIO_MAP.keys())}"
        )
    vehicle = _get_vehicle(req.vehicle_id)
    return fn(vehicle)


# POST /simulate/compare  — all scenarios (body-based, used by frontend)
@router.post("/simulate/compare")
def compare_scenarios_post(req: CompareRequest):
    vehicle = _get_vehicle(req.vehicle_id)
    return compare_all_scenarios(vehicle)


# GET /scenario/compare/{vehicle_id}  — all scenarios (path-based, easy to call/test)
@router.get("/scenario/compare/{vehicle_id}")
def compare_scenarios_get(vehicle_id: int):
    vehicle = _get_vehicle(vehicle_id)
    return compare_all_scenarios(vehicle)
