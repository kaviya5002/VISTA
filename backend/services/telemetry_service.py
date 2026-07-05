"""
telemetry_service.py — Drop-in replacement for fleet_repository.
Reads from obd_repository (real vehicle JSON files) instead of SQLite.

Exposes the same function signatures as fleet_repository so callers
(main.py, twin_service.py) can switch with a one-line import change.
"""
from services.obd_repository import get_vehicle as _obd_get, get_all_vehicles as _obd_all
from services.obd_mapper import map_to_pipeline


def get_all_vehicles() -> list[dict]:
    """Load + map all real vehicle JSONs.  Mirrors fleet_repository.get_all_vehicles()."""
    return [map_to_pipeline(raw) for raw in _obd_all()]


def get_vehicle_by_id(vehicle_id: int) -> dict | None:
    """Load + map a single vehicle.  Mirrors fleet_repository.get_vehicle_by_id()."""
    raw = _obd_get(vehicle_id)
    return map_to_pipeline(raw) if raw else None


# Lightweight sensor-only slice used by WebSocket batch predictions
def get_fleet_sensors() -> list[dict]:
    """Returns only the 4 sensor fields needed by WS + batch ML models."""
    _SENSOR_KEYS = {"vehicle_id", "battery_voltage", "temperature", "rpm", "speed",
                    "Reported_Issues", "tire", "brake"}
    return [{k: v for k, v in map_to_pipeline(raw).items() if k in _SENSOR_KEYS}
            for raw in _obd_all()]
