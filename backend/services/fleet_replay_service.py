"""
Fleet Replay Service
====================
Generates 24-hour historical snapshots for vehicles.
Uses TwinStateManager history if available, otherwise simulates
realistic degradation frames using sensor-based progression.
"""

from __future__ import annotations
import time
from datetime import datetime, timedelta
from services.twin_state_manager import get_twin


# ── Degradation rates per status ─────────────────────────────────────────────
_DEGRADE = {
    "Healthy":  {"health": -0.3, "temp": +0.4,  "voltage": -0.005, "rpm_drift": 10},
    "Warning":  {"health": -0.8, "temp": +0.9,  "voltage": -0.012, "rpm_drift": 25},
    "Critical": {"health": -1.8, "temp": +1.6,  "voltage": -0.025, "rpm_drift": 50},
}


def _status(health: float) -> str:
    if health >= 80: return "Healthy"
    if health >= 50: return "Warning"
    return "Critical"


def _frame(hour: int, health: float, temp: float, voltage: float,
           rpm: int, fail_prob: float, rul: float) -> dict:
    status = _status(health)
    ts = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
          + timedelta(hours=hour))
    return {
        "time":                ts.strftime("%H:%M"),
        "timestamp":           ts.isoformat(),
        "health":              max(5,  min(100, round(health, 1))),
        "failure_probability": max(0,  min(100, round(fail_prob, 1))),
        "rul":                 max(1,  round(rul)),
        "temperature":         round(temp, 1),
        "battery_voltage":     round(voltage, 2),
        "rpm":                 rpm,
        "status":              status,
    }


def generate_vehicle_replay(vehicle: dict) -> list[dict]:
    """
    Generate 24 hourly frames for a single vehicle.
    Tries live history first, falls back to simulation.
    """
    vid    = vehicle["vehicle_id"]
    state  = get_twin(vid)

    # ── Use live history if available ─────────────────────────────────────────
    if state and len(state.history) >= 6:
        frames = []
        for i, snap in enumerate(list(state.history)[-24:]):
            ts = datetime.fromtimestamp(snap.get("ts", time.time()))
            frames.append({
                "time":                ts.strftime("%H:%M"),
                "timestamp":           ts.isoformat(),
                "health":              snap.get("health", 80),
                "failure_probability": snap.get("failure_probability", 10),
                "rul":                 snap.get("rul", 20),
                "temperature":         snap.get("temperature", 50),
                "battery_voltage":     snap.get("battery_voltage", 12.0),
                "rpm":                 snap.get("rpm", 1500),
                "status":              snap.get("status", "Healthy"),
            })
        return frames

    # ── Simulate 24 hours of degradation ─────────────────────────────────────
    # Start from a slightly better state 24 hours ago
    current_health  = vehicle.get("health_score", 80)
    current_temp    = vehicle.get("temperature", 50)
    current_voltage = vehicle.get("battery_voltage", 12.0)
    current_rpm     = vehicle.get("rpm", 1500)
    current_fail    = vehicle.get("failure_probability", 10)
    current_rul     = vehicle.get("remaining_useful_life_days", 20)

    # Reverse-engineer starting point 24h ago
    start_health  = min(100, current_health  + 15)
    start_temp    = max(20,  current_temp    - 20)
    start_voltage = min(13.0,current_voltage + 0.3)
    start_fail    = max(0,   current_fail    - 20)
    start_rul     = min(30,  current_rul     + 5)

    frames = []
    h      = start_health
    t      = start_temp
    v      = start_voltage
    fp     = start_fail
    rul    = start_rul
    rpm    = max(500, current_rpm - 500)

    for hour in range(24):
        status = _status(h)
        rate   = _DEGRADE.get(status, _DEGRADE["Healthy"])

        frames.append(_frame(hour, h, t, v, rpm, fp, rul))

        # Progress degradation each hour
        h   += rate["health"]   + (0 if hour < 12 else rate["health"] * 0.5)
        t   += rate["temp"]     * (1.2 if hour > 16 else 1.0)
        v   += rate["voltage"]
        rpm += rate["rpm_drift"]
        fp   = max(0, min(100, fp + abs(rate["health"]) * 2))
        rul  = max(1, rul + rate["health"] / 10)

    return frames


def generate_fleet_replay(vehicles: list[dict]) -> list[dict]:
    """
    Generate 24 hourly frames for the entire fleet.
    Returns frames grouped by hour: [{time, vehicles: [...]}, ...]
    """
    # Build per-vehicle frames
    all_vehicle_frames: dict[int, list[dict]] = {}
    for vehicle in vehicles:
        vid = vehicle["vehicle_id"]
        all_vehicle_frames[vid] = generate_vehicle_replay(vehicle)

    # Pivot: group by hour index
    fleet_frames = []
    for hour in range(24):
        hour_vehicles = []
        for vid, frames in all_vehicle_frames.items():
            if hour < len(frames):
                frame = dict(frames[hour])
                frame["vehicle_id"] = vid
                hour_vehicles.append(frame)

        if hour_vehicles:
            # Summary stats for this hour
            healths  = [v["health"] for v in hour_vehicles]
            healthy  = sum(1 for v in hour_vehicles if v["status"] == "Healthy")
            warning  = sum(1 for v in hour_vehicles if v["status"] == "Warning")
            critical = sum(1 for v in hour_vehicles if v["status"] == "Critical")

            fleet_frames.append({
                "time":         hour_vehicles[0]["time"],
                "timestamp":    hour_vehicles[0]["timestamp"],
                "hour":         hour,
                "vehicles":     hour_vehicles,
                "summary": {
                    "avg_health": round(sum(healths) / len(healths), 1),
                    "healthy":    healthy,
                    "warning":    warning,
                    "critical":   critical,
                    "total":      len(hour_vehicles),
                }
            })

    return fleet_frames


def compare_frames(frames: list[dict], hour_a: int, hour_b: int) -> dict:
    """
    Compare two replay frames side by side.
    Returns delta for health, failure, temperature, voltage.
    """
    if hour_a >= len(frames) or hour_b >= len(frames):
        return {"error": "Invalid hour index"}

    fa = frames[hour_a]
    fb = frames[hour_b]

    sa = fa["summary"]
    sb = fb["summary"]

    return {
        "time_a":    fa["time"],
        "time_b":    fb["time"],
        "delta": {
            "avg_health":  round(sb["avg_health"] - sa["avg_health"], 1),
            "healthy":     sb["healthy"]  - sa["healthy"],
            "warning":     sb["warning"]  - sa["warning"],
            "critical":    sb["critical"] - sa["critical"],
        },
        "summary_a": sa,
        "summary_b": sb,
    }
