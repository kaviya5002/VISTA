"""
obd_repository.py — Single source of truth for real vehicle data.
Replaces telemetry_simulator.py.  Loads vehicle_N.json → returns dict.
"""
import json
import os

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "real_vehicles")
_VEHICLE_COUNT = 6


def _load(vehicle_id: int) -> dict | None:
    path = os.path.join(_DATA_DIR, f"vehicle_{vehicle_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_vehicle(vehicle_id: int) -> dict | None:
    """Load a single vehicle JSON.  Returns raw OBD dict or None."""
    return _load(vehicle_id)


def get_all_vehicles() -> list[dict]:
    """Load all vehicle JSONs in order.  Missing files are skipped."""
    return [v for i in range(1, _VEHICLE_COUNT + 1) if (v := _load(i)) is not None]
