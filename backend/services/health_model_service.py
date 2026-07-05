import os
import joblib
import pandas as pd

_ML_DIR      = os.path.join(os.path.dirname(__file__), "..", "ml")
_V2_PATH     = os.path.join(_ML_DIR, "health_model_v2.pkl")
_LEGACY_PATH = os.path.join(_ML_DIR, "health_model.pkl")
_FEATS_PATH  = os.path.join(_ML_DIR, "failure_features.pkl")  # same feature set

try:
    _path  = _V2_PATH if os.path.exists(_V2_PATH) else _LEGACY_PATH
    _model = joblib.load(_path)
    _feats = joblib.load(_FEATS_PATH) if os.path.exists(_FEATS_PATH) else None
    HEALTH_ML_ENABLED = True
    print(f"Health Model loaded: {os.path.basename(_path)}")
except Exception as e:
    _model = None
    _feats = None
    HEALTH_ML_ENABLED = False
    print("Health Model not loaded:", e)


def _vehicle_to_row(vehicle: dict) -> dict:
    v = vehicle.get("battery_voltage", 12.0)
    bat = vehicle.get("bat", 0 if v >= 12.5 else 1 if v >= 11.0 else 2)
    return {
        "model_enc":        vehicle.get("model_enc", 0),
        "Mileage":          vehicle.get("Mileage", int(vehicle.get("rpm", 1500) * 10)),
        "Vehicle_Age":      vehicle.get("Vehicle_Age", 5),
        "Engine_Size":      vehicle.get("Engine_Size", 2),
        "Odometer_Reading": vehicle.get("Odometer_Reading", int(vehicle.get("rpm", 1500) * 100)),
        "Reported_Issues":  vehicle.get("Reported_Issues", vehicle.get("reported_issues", 1)),
        "Service_History":  vehicle.get("Service_History", 1),
        "Accident_History": vehicle.get("Accident_History", 0),
        "Fuel_Efficiency":  vehicle.get("Fuel_Efficiency", 15.0),
        "Insurance_Premium":vehicle.get("Insurance_Premium", 15000),
        "tire":             vehicle.get("tire", vehicle.get("tire_condition", 1)),
        "brake":            vehicle.get("brake", vehicle.get("brake_condition", 1)),
        "bat":              bat,
        "fuel":             vehicle.get("fuel", 1),
        "trans":            vehicle.get("trans", 0),
        "owner":            vehicle.get("owner", 1),
        "maint_hist":       vehicle.get("maint_hist", 0),
    }


def predict_health_with_model(vehicle: dict) -> float | None:
    if not HEALTH_ML_ENABLED or _model is None:
        return None
    row  = _vehicle_to_row(vehicle)
    cols = _feats if _feats else list(row.keys())
    feat = pd.DataFrame([row])[cols]
    score = _model.predict(feat)[0]
    return max(5, min(100, round(float(score), 1)))


def batch_predict_health(vehicles: list[dict]) -> list[float | None]:
    """Predict health for all vehicles in one model call."""
    if not HEALTH_ML_ENABLED or _model is None:
        return [None] * len(vehicles)
    rows = [_vehicle_to_row(v) for v in vehicles]
    cols = _feats if _feats else list(rows[0].keys())
    df   = pd.DataFrame(rows)[cols]
    scores = _model.predict(df)
    return [max(5, min(100, round(float(s), 1))) for s in scores]
