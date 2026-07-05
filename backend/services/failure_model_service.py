import os
import joblib
import pandas as pd

_ML_DIR      = os.path.join(os.path.dirname(__file__), "..", "ml")
_V2_PATH     = os.path.join(_ML_DIR, "failure_model_v2.pkl")
_LEGACY_PATH = os.path.join(_ML_DIR, "failure_model.pkl")
_FEATS_PATH  = os.path.join(_ML_DIR, "failure_features.pkl")

try:
    _path  = _V2_PATH if os.path.exists(_V2_PATH) else _LEGACY_PATH
    _model = joblib.load(_path)
    _feats = joblib.load(_FEATS_PATH) if os.path.exists(_FEATS_PATH) else None
    ML_ENABLED = True
    print(f"Failure Model loaded: {os.path.basename(_path)}")
except Exception as e:
    _model = None
    _feats = None
    ML_ENABLED = False
    print("Failure Model not loaded:", e)


def _vehicle_to_row(vehicle: dict) -> dict:
    """Map vehicle dict to vehicle_maintenance_data feature space."""
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


def predict_with_model(vehicle: dict) -> dict | None:
    if not ML_ENABLED or _model is None:
        return None
    row = _vehicle_to_row(vehicle)
    cols = _feats if _feats else list(row.keys())
    features = pd.DataFrame([row])[cols]
    pred  = _model.predict(features)[0]
    proba = _model.predict_proba(features)[0][1]
    return {
        "ml_failure_prediction":  int(pred),
        "ml_failure_probability": round(proba * 100, 1),
    }


def batch_predict(vehicles: list[dict]) -> list[dict | None]:
    """Predict all vehicles in one model call — much faster than one-by-one."""
    if not ML_ENABLED or _model is None:
        return [None] * len(vehicles)
    rows = [_vehicle_to_row(v) for v in vehicles]
    cols = _feats if _feats else list(rows[0].keys())
    df   = pd.DataFrame(rows)[cols]
    preds  = _model.predict(df)
    probas = _model.predict_proba(df)[:, 1]
    return [
        {"ml_failure_prediction": int(p), "ml_failure_probability": round(pr * 100, 1)}
        for p, pr in zip(preds, probas)
    ]
