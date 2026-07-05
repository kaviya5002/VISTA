"""
Technician Service
==================
FastAPI router exposing:

  GET  /technicians                    — all technicians with live status
  GET  /technicians/{id}               — single technician detail
  GET  /technicians/capacity           — 7-day capacity forecast
  GET  /assignments                    — fleet-wide optimised assignments
  GET  /assignments/{vehicle_id}       — single vehicle assignment
  POST /assign                         — assign / reassign with calendar integration
"""
from __future__ import annotations

import time as _time
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from services.fleet_repository import get_all_vehicles
from services.health_score import calculate_health
from services.failure_forecast import predict_failure
from services.root_cause import analyze_root_cause
from services.rul_engine import calculate_rul
from services.cost_analysis import calculate_cost_impact
from services.maintenance_strategist import ai_maintenance_strategy
from services.fleet_optimizer import optimize_fleet

from services.technician.technician_repository import (
    get_all, get_by_id, set_availability, update_workload,
    workforce_summary, upsert,
)
from services.technician.skill_matcher import (
    rank_technicians, classify_repair, skill_gap,
)
from services.technician.workload_optimizer import capacity_forecast
from services.technician.assignment_engine import (
    assign_to_vehicle, assign_fleet, reassign,
)

router = APIRouter(prefix="/technicians", tags=["technicians"])


# ── GET /technicians/assignments (must be before /{tech_id}) ──────────────────

@router.get("/assignments", tags=["assignments"])
def fleet_assignments_inline():
    return fleet_assignments()


@router.get("/assignments/{vehicle_id}", tags=["assignments"])
def vehicle_assignment_inline(vehicle_id: int):
    return vehicle_assignment(vehicle_id)

# ── Cache (20 s TTL) ──────────────────────────────────────────────────────────
_cache: dict = {}
_TTL = 20.0


def _cached(key: str, fn):
    now = _time.time()
    if key in _cache and (now - _cache[key]["at"]) < _TTL:
        return _cache[key]["data"]
    result = fn()
    _cache[key] = {"data": result, "at": now}
    return result


def _invalidate(*keys: str) -> None:
    for k in keys:
        _cache.pop(k, None)


# ── Vehicle enrichment ────────────────────────────────────────────────────────

def _enrich(v: dict) -> dict:
    v = calculate_health(v)
    v = predict_failure(v)
    v = analyze_root_cause(v)
    v = calculate_rul(v)
    v = calculate_cost_impact(v)
    v = ai_maintenance_strategy(v)
    return v


def _get_enriched() -> list[dict]:
    return optimize_fleet([_enrich(v) for v in get_all_vehicles()])


# ── GET /technicians ──────────────────────────────────────────────────────────

@router.get("", response_model=None)
def list_technicians(shift: Optional[str] = Query(None)):
    """
    Returns all technicians with live status, workload, and skill summary.
    Optional ?shift=Morning|Afternoon|Night filter.
    """
    techs = get_all()
    if shift:
        techs = [t for t in techs if t["shift"] == shift]

    return {
        "technicians": techs,
        "summary":     workforce_summary(),
    }


# ── GET /technicians/capacity ─────────────────────────────────────────────────

@router.get("/capacity", response_model=None)
def technician_capacity(days: int = Query(7, ge=1, le=30)):
    """7-day (or custom) capacity forecast per technician per day."""
    return capacity_forecast(days=days)


# ── GET /technicians/{id} ─────────────────────────────────────────────────────

@router.get("/{tech_id}", response_model=None)
def get_technician(tech_id: int):
    tech = get_by_id(tech_id)
    if not tech:
        return {"error": f"Technician {tech_id} not found"}
    return tech


# ── GET /assignments (standalone, also called by inline routes above) ────────

@router.get("/assignments_data", include_in_schema=False)
def fleet_assignments():
    """
    Fleet-wide optimised assignments.
    Integrates with calendar schedule — each assignment includes
    calendar_event_id and work_order_link.
    """
    def _build():
        vehicles = _get_enriched()
        result   = assign_fleet(vehicles)

        # Attach calendar schedule context if available
        try:
            from services.calendar.calendar_router import _cache as _cal_cache
            cal_data = _cal_cache.get("calendar_v2", {}).get("data", {})
            sched_map = {s["vehicle_id"]: s for s in cal_data.get("schedule", [])}
            for a in result["assignments"]:
                sched = sched_map.get(a["vehicle_id"], {})
                if sched:
                    a["calendar_date"] = sched.get("date")
                    a["calendar_time"] = sched.get("time")
                    a["calendar_event_id"] = sched.get("event_id", a["calendar_event_id"])
        except Exception:
            pass

        return result

    return _cached("tech_fleet_assignments", _build)


# ── GET /assignments/{vehicle_id} ────────────────────────────────────────────

@router.get("/assignments_data/{vehicle_id}", include_in_schema=False)
def vehicle_assignment(vehicle_id: int):
    """Single vehicle assignment with full skill gap analysis."""
    vehicles = get_all_vehicles()
    vehicle  = next((v for v in vehicles if v["vehicle_id"] == vehicle_id), None)
    if not vehicle:
        return {"error": "Vehicle not found"}

    vehicle = _enrich(vehicle)
    return assign_to_vehicle(vehicle)


# ── POST /assign ──────────────────────────────────────────────────────────────

class AssignRequest(BaseModel):
    vehicle_id:   int
    tech_id:      Optional[int]  = None   # None = auto-select best
    date:         Optional[str]  = None   # "YYYY-MM-DD"; None = auto
    time:         Optional[str]  = None   # "HH:MM"; None = auto
    old_tech_id:  Optional[int]  = None   # for reassignment — releases old slot


@router.post("/assign", tags=["assignments"])
def assign(req: AssignRequest):
    """
    Assign or reassign a technician to a vehicle's maintenance task.

    - If tech_id is omitted, the engine auto-selects the best available technician.
    - If old_tech_id is provided, the old technician's workload is decremented.
    - Returns the full assignment with calendar event reference and work order link.
    - Invalidates the fleet assignments cache.
    """
    vehicles = get_all_vehicles()
    vehicle  = next((v for v in vehicles if v["vehicle_id"] == req.vehicle_id), None)
    if not vehicle:
        return {"error": "Vehicle not found"}

    vehicle = _enrich(vehicle)

    if req.tech_id:
        # Explicit reassignment to a specific technician
        from datetime import date as _date
        new_date = req.date or _date.today().isoformat()
        result   = reassign(
            vehicle,
            new_tech_id=req.tech_id,
            new_date=new_date,
            new_time=req.time,
            old_tech_id=req.old_tech_id,
        )
    else:
        # Auto-assign best available
        from datetime import date as _date
        date_hint = _date.fromisoformat(req.date) if req.date else None
        result    = assign_to_vehicle(vehicle, date_hint=date_hint)

    # Invalidate caches so next GET reflects the change
    _invalidate("tech_fleet_assignments")

    # Also patch the calendar cache if the event exists
    try:
        from services.calendar.calendar_router import _cache as _cal_cache
        cal_data = _cal_cache.get("calendar_v2", {}).get("data", {})
        event_id = result.get("calendar_event_id")
        for event in cal_data.get("events", []):
            if event["id"] == event_id:
                event["extendedProps"]["technician"]    = result["technician"]
                event["extendedProps"]["technician_id"] = result["technician_id"]
                break
    except Exception:
        pass

    return result


# ── Compatibility shim: /assignments router alias ─────────────────────────────
# Allows GET /assignments and GET /assignments/fleet to keep working
# alongside the new /technicians/assignments routes.

assignments_router = APIRouter(prefix="/assignments", tags=["assignments"])


@assignments_router.get("")
def compat_fleet_assignments():
    return fleet_assignments()


@assignments_router.get("/fleet")
def compat_fleet_assignments_fleet():
    return fleet_assignments()


@assignments_router.get("/{vehicle_id}")
def compat_vehicle_assignment(vehicle_id: int):
    return vehicle_assignment(vehicle_id)
