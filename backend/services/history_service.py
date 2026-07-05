"""
History Service
===============
Queries the rolling history stored in TwinStateManager and returns
summary statistics useful for trend analysis and API responses.
"""

from __future__ import annotations
from services.twin_state_manager import get_twin


def get_history(vehicle_id: int) -> list[dict]:
    """Return the raw rolling history (up to 30 samples)."""
    state = get_twin(vehicle_id)
    if not state:
        return []
    return list(state.history)


def get_health_series(vehicle_id: int) -> list[dict]:
    """Return [{ts, health, status}, ...] — compact for charting."""
    return [
        {"ts": s["ts"], "health": s.get("health"), "status": s.get("status")}
        for s in get_history(vehicle_id)
    ]


def get_summary(vehicle_id: int) -> dict:
    """Min / max / avg / slope over the stored health series."""
    series = [s.get("health", 0) for s in get_history(vehicle_id) if s.get("health") is not None]
    if not series:
        return {"samples": 0}

    n = len(series)
    avg = round(sum(series) / n, 1)
    slope = _slope(series)

    return {
        "samples":   n,
        "min":       min(series),
        "max":       max(series),
        "avg":       avg,
        "latest":    series[-1],
        "slope":     slope,
        "direction": "Improving" if slope > 0.3 else "Degrading" if slope < -0.3 else "Stable",
    }


def _slope(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mx = (n - 1) / 2
    my = sum(values) / n
    num   = sum((i - mx) * (values[i] - my) for i in range(n))
    denom = sum((i - mx) ** 2 for i in range(n))
    return round(num / denom, 3) if denom else 0.0
