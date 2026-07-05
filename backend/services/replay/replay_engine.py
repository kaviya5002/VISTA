"""
Replay Engine
=============
Reconstructs historical playback frames from persisted history rows,
then optionally appends Digital Twin forecast frames so the frontend
can animate past → present → future in one continuous sequence.

Frame shape (single vehicle)
-----------------------------
{
    "frame_index":   0,
    "recorded_at":   "2025-07-01T08:00:00+00:00",
    "time_label":    "01 Jul 08:00",
    "segment":       "history" | "forecast",
    "health":        82.3,
    "failure_prob":  18.4,
    "rul_days":      21.0,
    "temperature":   54.2,
    "battery_voltage": 12.31,
    "rpm":           1820,
    "speed":         55,
    "status":        "Healthy",
    "priority":      "Low",
    "root_cause":    ["High RPM"],
    "event_flag":    null | { kind, severity, message }
}

Fleet frame shape
-----------------
{
    "frame_index": 0,
    "recorded_at": "...",
    "time_label":  "...",
    "segment":     "history" | "forecast",
    "vehicles":    [ <single-vehicle frame without frame_index>, ... ],
    "summary":     { avg_health, healthy, warning, critical, total }
}
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from services.replay.history_collector import fetch_history, fetch_fleet_history
from services.replay.timeline_builder  import detect_events


# ── Helpers ───────────────────────────────────────────────────────────────────

def _time_label(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%d %b %H:%M")
    except Exception:
        return iso


def _row_to_frame(row: dict, index: int, event_map: dict[str, dict]) -> dict:
    ts = row.get("recorded_at", "")
    return {
        "frame_index":     index,
        "recorded_at":     ts,
        "time_label":      _time_label(ts),
        "segment":         "history",
        "health":          row.get("health_score"),
        "failure_prob":    row.get("failure_prob"),
        "rul_days":        row.get("rul_days"),
        "temperature":     row.get("temperature"),
        "battery_voltage": row.get("battery_voltage"),
        "rpm":             row.get("rpm"),
        "speed":           row.get("speed"),
        "status":          row.get("status"),
        "priority":        row.get("priority"),
        "root_cause":      row.get("root_cause", []),
        "event_flag":      event_map.get(ts),
    }


def _build_event_map(events: list[dict]) -> dict[str, dict]:
    """Map recorded_at → first event at that timestamp for O(1) lookup."""
    m: dict[str, dict] = {}
    for e in events:
        ts = e["recorded_at"]
        if ts not in m or e["severity"] == "Critical":
            m[ts] = {"kind": e["kind"], "severity": e["severity"], "message": e["message"]}
    return m


# ── Forecast overlay ──────────────────────────────────────────────────────────

def _forecast_frames(vehicle: dict, history_count: int, horizon_days: int = 7) -> list[dict]:
    """
    Generate forecast frames by running the simulation engine at hourly
    intervals for `horizon_days` days, starting from the vehicle's current state.
    Returns frames with segment="forecast".
    """
    from engines.simulation_engine import _simulate

    health  = vehicle.get("health_score",                50.0)
    failure = vehicle.get("failure_probability",         30.0)
    battery = vehicle.get("battery_voltage",             12.0)
    temp    = vehicle.get("temperature",                 50.0)
    rpm     = vehicle.get("rpm",                         1500)
    rul     = vehicle.get("remaining_useful_life_days",
              vehicle.get("rul_days", 15))

    now    = datetime.now(tz=timezone.utc)
    frames = []

    # Sample at every 2-hour step to keep payload lean
    step_hours = 2
    total_steps = (horizon_days * 24) // step_hours

    for step in range(1, total_steps + 1):
        days_ahead = (step * step_hours) / 24.0
        state = _simulate(days_ahead, health, failure, battery, temp, rpm, rul)

        ts  = (now + timedelta(hours=step * step_hours)).isoformat()
        idx = history_count + step - 1

        frames.append({
            "frame_index":     idx,
            "recorded_at":     ts,
            "time_label":      _time_label(ts),
            "segment":         "forecast",
            "health":          state["health"],
            "failure_prob":    round(state["failure_probability"], 1),
            "rul_days":        state["rul_days"],
            "temperature":     state["temperature"],
            "battery_voltage": state["battery_voltage"],
            "rpm":             state["rpm"],
            "speed":           vehicle.get("speed"),
            "status":          state["status"],
            "priority":        state["priority"],
            "root_cause":      vehicle.get("root_cause", []),
            "event_flag":      None,
        })

    return frames


# ── Simulation fallback (no DB history) ──────────────────────────────────────

def _simulate_history(vehicle: dict, hours: int) -> list[dict]:
    """
    When the DB has no rows, synthesise realistic history by reverse-projecting
    the current state backwards, then re-degrading forward.
    Mirrors the logic in fleet_replay_service but stores it in frame format.
    """
    _DEGRADE = {
        "Healthy":  {"health": -0.3, "temp": +0.4,  "voltage": -0.005, "rpm_drift": 10},
        "Warning":  {"health": -0.8, "temp": +0.9,  "voltage": -0.012, "rpm_drift": 25},
        "Critical": {"health": -1.8, "temp": +1.6,  "voltage": -0.025, "rpm_drift": 50},
    }

    def _status(h: float) -> str:
        return "Healthy" if h >= 80 else "Warning" if h >= 50 else "Critical"

    cur_h   = vehicle.get("health_score", 80)
    cur_t   = vehicle.get("temperature", 50)
    cur_v   = vehicle.get("battery_voltage", 12.0)
    cur_rpm = vehicle.get("rpm", 1500)
    cur_fp  = vehicle.get("failure_probability", 10)
    cur_rul = vehicle.get("remaining_useful_life_days", 20)

    h   = min(100, cur_h  + hours * 0.4)
    t   = max(20,  cur_t  - hours * 0.3)
    v   = min(13.0,cur_v  + hours * 0.008)
    fp  = max(0,   cur_fp - hours * 0.5)
    rul = min(60,  cur_rul + hours * 0.1)
    rpm = max(500, cur_rpm - 200)

    now    = datetime.now(tz=timezone.utc)
    frames = []

    for i in range(hours):
        st   = _status(h)
        rate = _DEGRADE.get(st, _DEGRADE["Healthy"])
        ts   = (now - timedelta(hours=hours - i)).isoformat()

        frames.append({
            "frame_index":     i,
            "recorded_at":     ts,
            "time_label":      _time_label(ts),
            "segment":         "history",
            "health":          round(max(5,  min(100, h)),  1),
            "failure_prob":    round(max(0,  min(100, fp)), 1),
            "rul_days":        round(max(1,  rul), 1),
            "temperature":     round(t, 1),
            "battery_voltage": round(v, 2),
            "rpm":             int(rpm),
            "speed":           vehicle.get("speed"),
            "status":          st,
            "priority":        vehicle.get("priority"),
            "root_cause":      vehicle.get("root_cause", []),
            "event_flag":      None,
        })

        h   += rate["health"]
        t   += rate["temp"]
        v   += rate["voltage"]
        rpm += rate["rpm_drift"]
        fp   = max(0, min(100, fp + abs(rate["health"]) * 1.5))
        rul  = max(1, rul + rate["health"] / 10)

    return frames


# ── Public API ────────────────────────────────────────────────────────────────

def build_vehicle_replay(
    vehicle: dict,
    *,
    hours: int = 24,
    include_forecast: bool = True,
    forecast_days: int = 7,
) -> dict:
    """
    Build the complete replay payload for a single vehicle.

    Returns
    -------
    {
        vehicle_id, frames, events, summary,
        playback: { total_frames, history_frames, forecast_frames,
                    recommended_speed_ms, frame_duration_ms }
    }
    """
    vid  = vehicle["vehicle_id"]
    rows = fetch_history(vid, hours=hours)

    if rows:
        events    = detect_events(rows)
        event_map = _build_event_map(events)
        hist_frames = [_row_to_frame(r, i, event_map) for i, r in enumerate(rows)]
    else:
        hist_frames = _simulate_history(vehicle, hours)
        events      = detect_events([])

    fc_frames: list[dict] = []
    if include_forecast:
        fc_frames = _forecast_frames(vehicle, len(hist_frames), forecast_days)

    all_frames = hist_frames + fc_frames

    # Playback metadata — frontend uses these to drive animation timing
    total   = len(all_frames)
    hist_n  = len(hist_frames)
    fc_n    = len(fc_frames)
    # Recommend ~30 s total playback: frame_duration = 30000 / total ms
    frame_ms = max(50, min(500, 30_000 // max(total, 1)))

    return {
        "vehicle_id": vid,
        "frames":     all_frames,
        "events":     events,
        "playback": {
            "total_frames":       total,
            "history_frames":     hist_n,
            "forecast_frames":    fc_n,
            "frame_duration_ms":  frame_ms,
            "recommended_speed":  1.0,   # multiplier; frontend scales frame_duration_ms
            "supports_speeds":    [0.25, 0.5, 1.0, 2.0, 4.0],
        },
    }


def build_fleet_replay(
    vehicles: list[dict],
    *,
    hours: int = 24,
    include_forecast: bool = True,
    forecast_days: int = 3,
) -> dict:
    """
    Build a fleet-level replay where each frame contains all vehicles' state
    at the same timestamp, plus aggregate summary stats.
    """
    # Fetch all history in one query
    all_history = fetch_fleet_history(hours=hours)

    # Build per-vehicle frame lists
    per_vehicle: dict[int, list[dict]] = {}
    for v in vehicles:
        vid  = v["vehicle_id"]
        rows = all_history.get(vid, [])

        if rows:
            events    = detect_events(rows)
            event_map = _build_event_map(events)
            per_vehicle[vid] = [_row_to_frame(r, i, event_map) for i, r in enumerate(rows)]
        else:
            per_vehicle[vid] = _simulate_history(v, hours)

        if include_forecast:
            fc = _forecast_frames(v, len(per_vehicle[vid]), forecast_days)
            per_vehicle[vid].extend(fc)

    # Align all vehicles to the same number of frames (pad with last known)
    max_frames = max((len(f) for f in per_vehicle.values()), default=0)

    def _pad(frames: list[dict], target: int) -> list[dict]:
        if not frames or len(frames) >= target:
            return frames
        last = {**frames[-1]}
        while len(frames) < target:
            frames.append({**last, "frame_index": len(frames)})
        return frames

    for vid in per_vehicle:
        per_vehicle[vid] = _pad(per_vehicle[vid], max_frames)

    # Pivot into fleet frames
    fleet_frames: list[dict] = []
    for fi in range(max_frames):
        vehicle_states = []
        for v in vehicles:
            vid = v["vehicle_id"]
            if fi < len(per_vehicle[vid]):
                frame = {k: val for k, val in per_vehicle[vid][fi].items() if k != "frame_index"}
                frame["vehicle_id"] = vid
                vehicle_states.append(frame)

        if not vehicle_states:
            continue

        healths  = [f["health"]       for f in vehicle_states if f.get("health")       is not None]
        statuses = [f["status"]        for f in vehicle_states if f.get("status")]
        segment  = vehicle_states[0].get("segment", "history")

        fleet_frames.append({
            "frame_index": fi,
            "recorded_at": vehicle_states[0].get("recorded_at", ""),
            "time_label":  vehicle_states[0].get("time_label", ""),
            "segment":     segment,
            "vehicles":    vehicle_states,
            "summary": {
                "avg_health": round(sum(healths) / len(healths), 1) if healths else 0,
                "healthy":    statuses.count("Healthy"),
                "warning":    statuses.count("Warning"),
                "critical":   statuses.count("Critical"),
                "total":      len(vehicle_states),
            },
        })

    total    = len(fleet_frames)
    frame_ms = max(80, min(600, 30_000 // max(total, 1)))

    return {
        "total_vehicles": len(vehicles),
        "frames":         fleet_frames,
        "playback": {
            "total_frames":      total,
            "frame_duration_ms": frame_ms,
            "recommended_speed": 1.0,
            "supports_speeds":   [0.25, 0.5, 1.0, 2.0, 4.0],
        },
    }
