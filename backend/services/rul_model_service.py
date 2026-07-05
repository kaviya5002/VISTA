import os
import joblib
import numpy as np
import pandas as pd

_ML_DIR      = os.path.join(os.path.dirname(__file__), "..", "ml")
_MODEL_PATH  = os.path.join(_ML_DIR, "models", "rul", "best.pkl")
_SCALER_PATH = os.path.join(_ML_DIR, "rul_scaler.pkl")
_LEGACY_PATH = os.path.join(_ML_DIR, "rul_model.pkl")

try:
    _mp         = _MODEL_PATH if os.path.exists(_MODEL_PATH) else _LEGACY_PATH
    _rul_model  = joblib.load(_mp)
    _rul_scaler = joblib.load(_SCALER_PATH)
    RUL_ML_ENABLED = True
    _label = "AutoML" if os.path.exists(_MODEL_PATH) else "Legacy"
    print(f"RUL Model loaded ({_label}): {_mp}")
except Exception as e:
    _rul_model  = None
    _rul_scaler = None
    RUL_ML_ENABLED = False
    print("RUL Model not loaded:", e)

_RUL_COLS = [
    "op1", "op2", "s2", "s3", "s4", "s6", "s7", "s8", "s9",
    "s11", "s12", "s13", "s14", "s15", "s17", "s20", "s21"
]


def _vehicle_to_rul_row(v: dict) -> list:
    health  = v.get("health_score", 50)
    temp    = v.get("temperature", 50)
    voltage = v.get("battery_voltage", 12.0)
    rpm     = v.get("rpm", 1500)
    return [
        (voltage - 9) / (14 - 9) * 0.006 - 0.003,
        (temp - 20) / (120 - 20) * 0.006 - 0.003,
        640  + (rpm / 7000) * 10,
        1580 + (temp / 120) * 30,
        1400 + (temp / 120) * 20,
        21.6 + (1 - health / 100) * 2,
        550  + (1 - health / 100) * 10,
        2388 + (rpm / 7000) * 5,
        9000 + (rpm / 7000) * 500,
        47   + (1 - health / 100) * 5,
        521  + (temp / 120) * 5,
        2388 + (rpm / 7000) * 3,
        8100 + (1 - health / 100) * 200,
        8.4  + (1 - health / 100) * 0.5,
        390  + (rpm / 7000) * 10,
        39   - (1 - health / 100) * 5,
        23   + (temp / 120) * 2,
    ]


def predict_rul_with_model(vehicle: dict) -> int | None:
    if not RUL_ML_ENABLED or _rul_model is None:
        return None
    df      = pd.DataFrame([_vehicle_to_rul_row(vehicle)], columns=_RUL_COLS)
    scaled  = _rul_scaler.transform(df)
    rul_raw = _rul_model.predict(scaled)[0]
    return max(1, min(30, round((rul_raw / 125) * 30)))


def batch_predict_rul(vehicles: list[dict]) -> list[int | None]:
    """Predict RUL for all vehicles in one model call."""
    if not RUL_ML_ENABLED or _rul_model is None or _rul_scaler is None:
        return [None] * len(vehicles)
    df     = pd.DataFrame([_vehicle_to_rul_row(v) for v in vehicles], columns=_RUL_COLS)
    scaled = _rul_scaler.transform(df)
    raws   = _rul_model.predict(scaled)
    return [max(1, min(30, round((r / 125) * 30))) for r in raws]
