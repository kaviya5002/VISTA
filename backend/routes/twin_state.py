"""
Twin State Routes
=================
GET /twin/state/{vehicle_id}    — current state + summary
GET /twin/history/{vehicle_id}  — rolling 30-sample history
GET /twin/events/{vehicle_id}   — auto-detected events
GET /twin/timeline/{vehicle_id} — lifecycle timeline
"""

from fastapi import APIRouter, HTTPException
from services.twin_state_manager import get_twin, snapshot, restore
from services.history_service    import get_history, get_health_series, get_summary
from services.timeline_service   import get_timeline

router = APIRouter(prefix="/twin", tags=["Twin State"])


def _require(vehicle_id: int):
    state = get_twin(vehicle_id)
    if not state or state.current is None:
        raise HTTPException(
            status_code=404,
            detail=f"No live state for vehicle {vehicle_id} — wait for first WebSocket tick"
        )
    return state


@router.get("/state/{vehicle_id}")
def twin_state(vehicle_id: int):
    state = _require(vehicle_id)
    return {
        "vehicle_id": vehicle_id,
        "current":    state.current,
        "previous":   state.previous,
        "summary":    get_summary(vehicle_id),
        "lifecycle":  state._lifecycle(state.current.get("health", 100)),
    }


@router.get("/history/{vehicle_id}")
def twin_history(vehicle_id: int):
    _require(vehicle_id)
    return {
        "vehicle_id":    vehicle_id,
        "samples":       get_history(vehicle_id),
        "health_series": get_health_series(vehicle_id),
        "summary":       get_summary(vehicle_id),
    }


@router.get("/events/{vehicle_id}")
def twin_events(vehicle_id: int):
    state = _require(vehicle_id)
    # Most recent first, cap at 50
    events = sorted(state.events, key=lambda e: e["ts"], reverse=True)[:50]
    return {"vehicle_id": vehicle_id, "count": len(events), "events": events}


@router.get("/timeline/{vehicle_id}")
def twin_timeline(vehicle_id: int):
    _require(vehicle_id)
    return {"vehicle_id": vehicle_id, "timeline": get_timeline(vehicle_id)}
