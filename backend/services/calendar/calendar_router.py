"""
Calendar Router
===============
Exposes:
  GET  /calendar                        — full FullCalendar-compatible schedule
  POST /calendar/reschedule             — drag-and-drop reschedule with impact recalc
  GET  /calendar/workorder/{vehicle_id} — detailed work order for one vehicle
"""
from __future__ import annotations

import time as _time
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from services.fleet_repository import get_all_vehicles
from services.health_score import calculate_health
from services.failure_forecast import predict_failure
from services.root_cause import analyze_root_cause
from services.rul_engine import calculate_rul
from services.cost_analysis import calculate_cost_impact
from services.maintenance_strategist import ai_maintenance_strategy
from services.fleet_optimizer import optimize_fleet

from services.calendar.calendar_engine import generate_schedule, _urgency, _priority_label
from services.calendar.scheduler import build_optimised_schedule, apply_reschedule
from services.calendar.workorder_generator import generate_work_order

router = APIRouter(prefix="/calendar", tags=["calendar"])

# ── In-memory schedule cache (30 s TTL) ──────────────────────────────────────
_cache: dict = {}
_TTL = 30.0


def _cached(key: str, fn):
    now = _time.time()
    if key in _cache and (now - _cache[key]["at"]) < _TTL:
        return _cache[key]["data"]
    result = fn()
    _cache[key] = {"data": result, "at": now}
    return result


# ── Vehicle enrichment pipeline ───────────────────────────────────────────────

def _enrich(v: dict) -> dict:
    v = calculate_health(v)
    v = predict_failure(v)
    v = analyze_root_cause(v)
    v = calculate_rul(v)
    v = calculate_cost_impact(v)
    v = ai_maintenance_strategy(v)
    return v


def _get_enriched_vehicles() -> list[dict]:
    raw = get_all_vehicles()
    enriched = [_enrich(v) for v in raw]
    return optimize_fleet(enriched)


# ── GET /calendar ─────────────────────────────────────────────────────────────

@router.get("")
def get_calendar():
    """
    Returns a FullCalendar-compatible event list plus AI summary,
    downtime map, and risk map.

    Response shape
    --------------
    {
        events:       [ FullCalendar EventObject, ... ],
        ai_summary:   { this_week_count, critical_count, ... },
        downtime_map: { "YYYY-MM-DD": hours },
        risk_map:     { "YYYY-MM-DD": "Critical"|"High"|... },
        schedule:     [ ScheduleEntry, ... ],   # for frontend table view
    }
    """
    def _build():
        vehicles = _get_enriched_vehicles()

        # Build optimised schedule (smart technician + slot allocation)
        scored = sorted(
            [(_urgency(v), _priority_label(_urgency(v)), v) for v in vehicles],
            key=lambda x: x[0],
            reverse=True,
        )
        schedule = build_optimised_schedule(scored)

        # Inject scheduler's date/time/technician back into vehicles for engine
        sched_map = {s["vehicle_id"]: s for s in schedule}
        for v in vehicles:
            entry = sched_map.get(v["vehicle_id"], {})
            v["_sched_date"] = entry.get("date")
            v["_sched_time"] = entry.get("time")
            v["_sched_tech"] = entry.get("technician")
            v["_sched_tech_id"] = entry.get("technician_id")

        result = generate_schedule(vehicles)
        result["schedule"] = schedule
        return result

    return _cached("calendar_v2", _build)


# ── POST /calendar/reschedule ─────────────────────────────────────────────────

class RescheduleRequest(BaseModel):
    event_id: str
    new_date: str                   # "YYYY-MM-DD"
    new_time: Optional[str] = None  # "HH:MM" — None keeps original time


@router.post("/reschedule")
def reschedule_event(req: RescheduleRequest):
    """
    Drag-and-drop reschedule handler.

    Moves the specified event to new_date/new_time, then returns:
      - updated_event   : patched FullCalendar event
      - fleet_impact    : risk delta, cost delta, recommendation
      - conflict_warning: technician overload warning if applicable

    Also invalidates the calendar cache so the next GET reflects the change.
    """
    # Get current schedule (from cache or rebuild)
    current = _cached("calendar_v2", lambda: get_calendar())
    events  = current.get("events", [])

    vehicles = _get_enriched_vehicles()

    result = apply_reschedule(
        events=events,
        event_id=req.event_id,
        new_date=req.new_date,
        new_time=req.new_time,
        all_vehicles=vehicles,
    )

    if "error" in result:
        return result

    # Patch the cached event list so subsequent GETs reflect the move
    updated_id = result["updated_event"]["id"]
    patched_events = [
        result["updated_event"] if e["id"] == updated_id else e
        for e in events
    ]
    if "calendar_v2" in _cache:
        _cache["calendar_v2"]["data"]["events"] = patched_events

    return result


# ── GET /calendar/workorder/{vehicle_id} ─────────────────────────────────────

@router.get("/workorder/{vehicle_id}")
def calendar_work_order(vehicle_id: int):
    """
    Returns a full work order for the vehicle, with scheduled date/time
    injected from the current calendar schedule.
    """
    vehicles = get_all_vehicles()
    vehicle  = next((v for v in vehicles if v["vehicle_id"] == vehicle_id), None)
    if not vehicle:
        return {"error": "Vehicle not found"}

    vehicle = _enrich(vehicle)

    # Pull scheduled date/time from cache if available
    sched_date = None
    sched_time = None
    cached_cal = _cache.get("calendar_v2", {}).get("data", {})
    for entry in cached_cal.get("schedule", []):
        if entry["vehicle_id"] == vehicle_id:
            sched_date = entry["date"]
            sched_time = entry["time"]
            break

    return generate_work_order(vehicle, sched_date, sched_time)
