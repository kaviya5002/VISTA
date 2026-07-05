"""
Event Engine
============
Runs after every twin state update and fires events when thresholds are crossed.

Detected events
---------------
- RapidDegradation   — health drops ≥ 5 pts in one tick
- Overheating        — temperature crosses 95 °C
- BatteryLow         — voltage drops below 11.0 V
- HighRPM            — RPM exceeds 6000
- CriticalHealth     — health falls below 25
- Recovery           — health rises ≥ 8 pts in one tick (after repair)
"""

from __future__ import annotations
from services.twin_state_manager import TwinState


def _check(state: TwinState) -> None:
    cur  = state.current
    prev = state.previous
    if cur is None:
        return

    health = cur.get("health", 100)
    temp   = cur.get("temperature", 0)
    volt   = cur.get("battery_voltage", 12.0)
    rpm    = cur.get("rpm", 0)

    # ── Rapid degradation ────────────────────────────────────────────
    if prev:
        delta = prev.get("health", health) - health
        if delta >= 5:
            state.add_event(
                "RapidDegradation",
                f"Health dropped {delta} pts ({prev['health']}% → {health}%)",
                "Critical" if delta >= 10 else "Warning",
            )
        # Recovery
        recovery = health - prev.get("health", health)
        if recovery >= 8:
            state.add_event("Recovery", f"Health recovered {recovery} pts → {health}%", "Info")

    # ── Temperature ───────────────────────────────────────────────────
    if temp >= 100:
        _fire_once(state, "Overheating", f"Temperature {temp}°C — critical", "Critical")
    elif temp >= 95:
        _fire_once(state, "HighTemperature", f"Temperature {temp}°C — warning", "Warning")

    # ── Battery voltage ───────────────────────────────────────────────
    if volt < 10.5:
        _fire_once(state, "BatteryCritical", f"Voltage {volt}V — near failure", "Critical")
    elif volt < 11.0:
        _fire_once(state, "BatteryLow", f"Voltage {volt}V — low", "Warning")

    # ── RPM ────────────────────────────────────────────────────────────
    if rpm > 6000:
        _fire_once(state, "HighRPM", f"RPM {rpm} — engine stress", "Warning")

    # ── Critical health ────────────────────────────────────────────────
    if health < 25:
        _fire_once(state, "CriticalHealth", f"Health {health}% — immediate action", "Critical")


def _fire_once(state: TwinState, kind: str, message: str, severity: str) -> None:
    """Only fire if the last event of this kind was > 60 s ago (avoid spam)."""
    import time
    for ev in reversed(state.events):
        if ev["kind"] == kind:
            if time.time() - ev["ts"] < 60:
                return
            break
    state.add_event(kind, message, severity)


def process(state: TwinState) -> None:
    """Entry point — call after every twin update."""
    _check(state)
