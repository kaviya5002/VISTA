from database import get_connection

# Only the 7 sensor fields needed by WS + batch ML models
_SENSOR_COLS = (
    "vehicle_id, battery_voltage, temperature, rpm, speed, "
    "reported_issues, tire_condition, brake_condition"
)

# All fields needed for full pipeline (vehicle detail, /fleet endpoint)
_FULL_COLS = (
    "vehicle_id, battery_voltage, temperature, rpm, speed, "
    "mileage, vehicle_age, engine_size, odometer, reported_issues, "
    "service_history, accident_history, fuel_efficiency, insurance_premium, "
    "tire_condition, brake_condition, fuel_condition, transmission_ok, "
    "owner_count, maint_history, model_enc"
)


def get_fleet_sensors() -> list[dict]:
    """Lightweight query for WS + ML batch prediction — only sensor fields."""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(f"SELECT {_SENSOR_COLS} FROM vehicles")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_all_vehicles() -> list[dict]:
    """Full vehicle data for /fleet and /vehicle/{id} endpoints."""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(f"SELECT {_FULL_COLS} FROM vehicles")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    # Normalise column names to what services expect
    return [_normalise(r) for r in rows]


def get_vehicle_by_id(vehicle_id: int) -> dict | None:
    """Single vehicle full data."""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(f"SELECT {_FULL_COLS} FROM vehicles WHERE vehicle_id = ?", (vehicle_id,))
    row = cur.fetchone()
    conn.close()
    return _normalise(dict(row)) if row else None


def _normalise(r: dict) -> dict:
    """Map DB column names → field names expected by ML services."""
    r["Mileage"]           = r.pop("mileage",           50000)
    r["Vehicle_Age"]       = r.pop("vehicle_age",       5)
    r["Engine_Size"]       = r.pop("engine_size",       2.0)
    r["Odometer_Reading"]  = r.pop("odometer",          100000)
    r["Reported_Issues"]   = r.pop("reported_issues",   1)
    r["Service_History"]   = r.pop("service_history",   1)
    r["Accident_History"]  = r.pop("accident_history",  0)
    r["Fuel_Efficiency"]   = r.pop("fuel_efficiency",   15.0)
    r["Insurance_Premium"] = r.pop("insurance_premium", 15000)
    r["tire"]              = r.pop("tire_condition",    1)
    r["brake"]             = r.pop("brake_condition",   1)
    r["bat"]               = 0 if r.get("battery_voltage", 12) >= 12.5 else 1 if r.get("battery_voltage", 12) >= 11.0 else 2
    r["fuel"]              = r.pop("fuel_condition",    1)
    r["trans"]             = 1 - r.pop("transmission_ok", 1)
    r["owner"]             = r.pop("owner_count",       1)
    r["maint_hist"]        = r.pop("maint_history",     0)
    r["model_enc"]         = r.get("model_enc",         0)
    return r
