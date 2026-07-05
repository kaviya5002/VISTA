"""
obd_mapper.py — Translates a raw OBD vehicle JSON into the normalised dict
that every downstream ML service (health, failure, RUL, root-cause) expects.

The output schema is identical to fleet_repository._normalise() so the entire
AI pipeline works without any changes.
"""


def map_to_pipeline(raw: dict) -> dict:
    """
    raw  — one vehicle_N.json loaded by obd_repository
    returns — flat dict ready for calculate_health / predict_failure / etc.
    """
    obd     = raw.get("obd", {})
    profile = raw.get("vehicle_profile", {})

    voltage = obd.get("battery_voltage", 12.0)
    temp    = obd.get("coolant_temperature", 80.0)
    rpm     = obd.get("rpm", 800)
    speed   = obd.get("vehicle_speed", 0)

    v = {
        # ── Core sensors (used by component AI + dashboard alerts) ──────────
        "vehicle_id":      raw["vehicle_id"],
        "battery_voltage": voltage,
        "temperature":     temp,
        "rpm":             rpm,
        "speed":           speed,

        # ── OBD metadata (surfaced in reports + /obd endpoints) ─────────────
        "vin":             raw.get("vin", ""),
        "make":            raw.get("make", ""),
        "model":           raw.get("model", ""),
        "year":            raw.get("year", 0),
        "fuel_type":       raw.get("fuel_type", ""),
        "collected_at":    raw.get("collected_at", ""),
        "scanner":         raw.get("scanner", ""),
        "workshop":        raw.get("workshop", ""),
        "technician":      raw.get("technician", ""),
        "dtc_codes":       obd.get("dtc_codes", []),
        "mil_status":      obd.get("mil_status", False),
        "fuel_level":      obd.get("fuel_level", 0),
        "engine_load":     obd.get("engine_load", 0.0),
        "data_source":     raw.get("source", "Workshop OBD-II"),

        # ── ML feature fields (normalised names expected by ML models) ───────
        "Mileage":           profile.get("mileage", 50000),
        "Vehicle_Age":       profile.get("vehicle_age", 5),
        "Engine_Size":       profile.get("engine_size", 2.0),
        "Odometer_Reading":  raw.get("odometer_km", profile.get("mileage", 100000)),
        "Reported_Issues":   profile.get("reported_issues", 1),
        "Service_History":   profile.get("service_history", 1),
        "Accident_History":  profile.get("accident_history", 0),
        "Fuel_Efficiency":   profile.get("fuel_efficiency", 15.0),
        "Insurance_Premium": profile.get("insurance_premium", 15000),
        "tire":              profile.get("tire_condition", 1),
        "brake":             profile.get("brake_condition", 1),
        "bat":               0 if voltage >= 12.5 else (1 if voltage >= 11.0 else 2),
        "fuel":              profile.get("fuel_condition", 1),
        "trans":             1 - profile.get("transmission_ok", 1),
        "owner":             profile.get("owner_count", 1),
        "maint_hist":        profile.get("maint_history", 0),
        "model_enc":         profile.get("model_enc", 0),
    }
    return v
