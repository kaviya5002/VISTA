import os
import joblib
import numpy as np

_ML_DIR       = os.path.join(os.path.dirname(__file__), "..", "ml")
_MODEL_PATH   = os.path.join(_ML_DIR, "models", "fleet", "best.pkl")      # versioned
_ENCODER_PATH = os.path.join(_ML_DIR, "models", "fleet", "encoder.pkl")   # versioned
_LEGACY_MODEL = os.path.join(_ML_DIR, "fleet_optimizer.pkl")
_LEGACY_ENC   = os.path.join(_ML_DIR, "fleet_priority_encoder.pkl")

try:
    _mp = _MODEL_PATH   if os.path.exists(_MODEL_PATH)   else _LEGACY_MODEL
    _ep = _ENCODER_PATH if os.path.exists(_ENCODER_PATH) else _LEGACY_ENC
    _model   = joblib.load(_mp)
    _encoder = joblib.load(_ep)
    FLEET_ML_ENABLED = True
    _label = "AutoML" if os.path.exists(_MODEL_PATH) else "Legacy"
    print(f"Fleet Optimizer loaded ({_label}): {_mp}")
except Exception as e:
    _model   = None
    _encoder = None
    FLEET_ML_ENABLED = False
    print("Fleet Optimizer not loaded:", e)


def predict_priority(
    health_score: float,
    failure_probability: float,
    rul_days: int,
    repair_cost: float,
    failure_cost: float,
    potential_savings: float
) -> str | None:
    if not FLEET_ML_ENABLED or _model is None:
        return None
    features   = np.array([[health_score, failure_probability, rul_days,
                             repair_cost, failure_cost, potential_savings]])
    prediction = _model.predict(features)[0]
    return _encoder.inverse_transform([prediction])[0]


def batch_predict_priority(vehicles: list[dict]) -> list[str | None]:
    """Predict priority for all vehicles in one model call."""
    if not FLEET_ML_ENABLED or _model is None:
        return [None] * len(vehicles)
    rows = np.array([
        [v["health_score"], v["failure_probability"],
         v["remaining_useful_life_days"], v["repair_now_cost"],
         v["failure_cost"], v["potential_savings"]]
        for v in vehicles
    ])
    predictions = _model.predict(rows)
    return list(_encoder.inverse_transform(predictions))
