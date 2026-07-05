"""
Replay Service
==============
FastAPI router exposing:
  GET /replay/{vehicle_id}   — single-vehicle historical + forecast replay
  GET /replay/fleet          — fleet-wide replay with per-frame summaries

Query parameters (both endpoints):
  hours          int   = 24      history window
  forecast       bool  = true    append Digital Twin forecast frames
  forecast_days  int   = 7       forecast horizon (vehicle) / 3 (fleet)
  speed          float = 1.0     playback speed multiplier hint for frontend
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from services.fleet_repository import get_all_vehicles
from services.health_score import calculate_health
from services.failure_forecast import predict_failure
from services.root_cause import analyze_root_cause
from services.rul_engine import calculate_rul
from services.replay.replay_engine import build_vehicle_replay, build_fleet_replay
from services.replay.timeline_builder import build_summary, detect_events
from services.replay.history_collector import fetch_history

router = APIRouter(prefix="/replay", tags=["replay"])


def _enrich(vehicle: dict) -> dict:
    vehicle = calculate_health(vehicle)
    vehicle = predict_failure(vehicle)
    vehicle = analyze_root_cause(vehicle)
    vehicle = calculate_rul(vehicle)
    return vehicle


@router.get("/{vehicle_id}")
def replay_vehicle(
    vehicle_id: int,
    hours: int = Query(24, ge=1, le=720),
    forecast: bool = Query(True),
    forecast_days: int = Query(7, ge=1, le=30),
    speed: float = Query(1.0, ge=0.1, le=10.0),
):
    vehicles = get_all_vehicles()
    vehicle = next((v for v in vehicles if v["vehicle_id"] == vehicle_id), None)
    if not vehicle:
        return {"error": "Vehicle not found"}

    vehicle = _enrich(vehicle)
    payload = build_vehicle_replay(
        vehicle,
        hours=hours,
        include_forecast=forecast,
        forecast_days=forecast_days,
    )

    # Attach timeline summary
    rows = fetch_history(vehicle_id, hours=hours)
    events = detect_events(rows) if rows else payload.get("events", [])
    payload["summary"] = build_summary(rows, events)

    # Honour requested speed: scale frame_duration_ms
    base_ms = payload["playback"]["frame_duration_ms"]
    payload["playback"]["frame_duration_ms"] = max(16, int(base_ms / speed))
    payload["playback"]["requested_speed"] = speed

    return payload


@router.get("/fleet")
def replay_fleet(
    hours: int = Query(24, ge=1, le=720),
    forecast: bool = Query(True),
    forecast_days: int = Query(3, ge=1, le=14),
    speed: float = Query(1.0, ge=0.1, le=10.0),
):
    vehicles = get_all_vehicles()
    processed = [_enrich(v) for v in vehicles]

    payload = build_fleet_replay(
        processed,
        hours=hours,
        include_forecast=forecast,
        forecast_days=forecast_days,
    )

    base_ms = payload["playback"]["frame_duration_ms"]
    payload["playback"]["frame_duration_ms"] = max(16, int(base_ms / speed))
    payload["playback"]["requested_speed"] = speed

    # Attach per-vehicle event counts for fleet overview
    vehicle_events: dict[int, int] = {}
    for v in processed:
        vid = v["vehicle_id"]
        rows = fetch_history(vid, hours=hours)
        vehicle_events[vid] = len(detect_events(rows)) if rows else 0

    payload["vehicle_event_counts"] = vehicle_events
    return payload
