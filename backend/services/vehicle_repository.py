"""
vehicle_repository.py — Single source of truth for all vehicle data.

Automatically discovers every vehicle_*.json inside data/vehicles/.
Adding vehicle_7.json requires zero code changes anywhere.

Real JSON schema (from OBD scanner):
  { vehicle: {...}, obd: {...}, diagnostics: {...}, ai: {...} }

Public API
----------
get_all_vehicles()          → list[dict]   pipeline-ready dicts
get_vehicle(id)             → dict | None  pipeline-ready dict
get_vehicle_obd(id)         → dict | None  raw OBD sensor block
get_vehicle_ai(id)          → dict | None  ML feature block
get_vehicle_diagnostics(id) → dict | None  DTC / MIL / provenance
reload_data()               → int          reloads from disk, returns count
"""
import glob
import json
import os

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "vehicles")

# ── In-memory store ───────────────────────────────────────────────────────────
_raw_store:      dict[int, dict] = {}
_pipeline_store: dict[int, dict] = {}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _derive_bat(voltage: float) -> int:
    if voltage >= 12.5:
        return 0
    if voltage >= 11.0:
        return 1
    return 2


def _to_pipeline(raw: dict) -> dict:
    """Flatten real scanner JSON into the normalised dict every ML service expects."""
    v    = raw.get("vehicle", {})
    obd  = raw.get("obd", {})
    diag = raw.get("diagnostics", {})
    ai   = raw.get("ai", {})

    voltage = obd.get("battery_voltage", 12.0)
    temp    = obd.get("coolant_temperature", 80.0)
    rpm     = obd.get("engine_rpm", 800)
    speed   = obd.get("vehicle_speed", 0)
    age     = v.get("vehicle_age", 5)
    odometer = v.get("odometer", 50000)

    # Derive ML condition flags from real OBD data
    dtc_count       = len(diag.get("dtc_codes", []))
    reported_issues = min(dtc_count, 5)                     # cap at 5
    service_history = 1 if dtc_count == 0 else 0            # clean history = no DTCs
    engine_load     = obd.get("engine_load", 20.0)
    fuel_level      = obd.get("fuel_level", 50.0)
    fuel_condition  = 0 if fuel_level < 10 else 1
    tire_condition  = 1                                      # not in OBD; default good
    brake_condition = 1                                      # not in OBD; default good
    transmission_ok = 1                                      # not in OBD; default good

    return {
        # ── Core sensors ────────────────────────────────────────────────────
        "vehicle_id":      v.get("vehicle_id", raw.get("vehicle_id")),
        "battery_voltage": voltage,
        "temperature":     temp,
        "rpm":             rpm,
        "speed":           speed,
        # ── Identity / provenance ────────────────────────────────────────────
        "vin":             v.get("vin", ""),
        "make":            v.get("manufacturer", ""),
        "model":           v.get("model", ""),
        "vehicle_name":    v.get("vehicle_name", ""),
        "year":            v.get("year", 0),
        "fuel_type":       v.get("vehicle_type", ""),
        "registration":    v.get("registration_number", ""),
        "owner_name":      v.get("owner", ""),
        "fleet":           v.get("fleet", ""),
        "data_source":     "Workshop OBD-II",
        # ── OBD extras ──────────────────────────────────────────────────────
        "dtc_codes":       diag.get("dtc_codes", []),
        "mil_status":      diag.get("mil_status", False),
        "fuel_level":      fuel_level,
        "engine_load":     engine_load,
        "oil_temperature": obd.get("oil_temperature", 0),
        "timing_advance":  obd.get("timing_advance", 0),
        # ── ML feature fields ────────────────────────────────────────────────
        "Mileage":           odometer,
        "Vehicle_Age":       age,
        "Engine_Size":       2.0,                            # not in OBD; reasonable default
        "Odometer_Reading":  odometer,
        "Reported_Issues":   reported_issues,
        "Service_History":   service_history,
        "Accident_History":  0,
        "Fuel_Efficiency":   15.0,
        "Insurance_Premium": 15000,
        "tire":              tire_condition,
        "brake":             brake_condition,
        "bat":               _derive_bat(voltage),
        "fuel":              fuel_condition,
        "trans":             1 - transmission_ok,
        "owner":             1,
        "maint_hist":        service_history,
        "model_enc":         0,
        # ── Pre-computed AI fields from scanner (used as fallback) ───────────
        "_scanner_health":   ai.get("health_score"),
        "_scanner_failure":  ai.get("failure_probability"),
        "_scanner_rul":      ai.get("remaining_useful_life"),
        "_scanner_status":   ai.get("status"),
        "_scanner_priority": ai.get("priority"),
    }


def _load_all() -> tuple[dict, dict]:
    raw_store:      dict[int, dict] = {}
    pipeline_store: dict[int, dict] = {}

    pattern = os.path.join(_DATA_DIR, "vehicle_*.json")
    for path in sorted(glob.glob(pattern)):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            vid = int(raw["vehicle"]["vehicle_id"])
            raw_store[vid]      = raw
            pipeline_store[vid] = _to_pipeline(raw)
        except Exception as exc:
            print(f"[vehicle_repository] skipping {path}: {exc}")

    return raw_store, pipeline_store


# ── Boot-time load ────────────────────────────────────────────────────────────
_raw_store, _pipeline_store = _load_all()


# ── Public API ────────────────────────────────────────────────────────────────

def reload_data() -> int:
    global _raw_store, _pipeline_store
    _raw_store, _pipeline_store = _load_all()
    return len(_raw_store)


def get_all_vehicles() -> list[dict]:
    return [_pipeline_store[k] for k in sorted(_pipeline_store)]


def get_vehicle(vehicle_id: int) -> dict | None:
    return _pipeline_store.get(vehicle_id)


def get_vehicle_obd(vehicle_id: int) -> dict | None:
    raw = _raw_store.get(vehicle_id)
    if raw is None:
        return None
    return {
        "vehicle_id": vehicle_id,
        "vin":        raw["vehicle"].get("vin"),
        **raw.get("obd", {}),
    }


def get_vehicle_ai(vehicle_id: int) -> dict | None:
    v = _pipeline_store.get(vehicle_id)
    if v is None:
        return None
    _AI_KEYS = {
        "vehicle_id", "battery_voltage", "temperature", "rpm", "speed",
        "Mileage", "Vehicle_Age", "Engine_Size", "Odometer_Reading",
        "Reported_Issues", "Service_History", "Accident_History",
        "Fuel_Efficiency", "Insurance_Premium",
        "tire", "brake", "bat", "fuel", "trans", "maint_hist", "model_enc",
    }
    return {k: v[k] for k in _AI_KEYS if k in v}


def get_vehicle_diagnostics(vehicle_id: int) -> dict | None:
    raw = _raw_store.get(vehicle_id)
    if raw is None:
        return None
    v    = raw.get("vehicle", {})
    diag = raw.get("diagnostics", {})
    return {
        "vehicle_id":      vehicle_id,
        "vin":             v.get("vin"),
        "make":            v.get("manufacturer"),
        "model":           v.get("model"),
        "year":            v.get("year"),
        "mil_status":      diag.get("mil_status", False),
        "dtc_codes":       diag.get("dtc_codes", []),
        "dtc_count":       len(diag.get("dtc_codes", [])),
        "pending_codes":   diag.get("pending_codes", []),
        "permanent_codes": diag.get("permanent_codes", []),
        "freeze_frame":    diag.get("freeze_frame", {}),
        "source":          "Workshop OBD-II",
        "data_source":     "Workshop OBD-II",
    }
