import os
import joblib
import pandas as pd

_ML_DIR      = os.path.join(os.path.dirname(__file__), "..", "ml")
_MODEL_PATH  = os.path.join(_ML_DIR, "models", "rootcause", "best.pkl")   # versioned
_LEGACY_PATH = os.path.join(_ML_DIR, "root_cause_model.pkl")              # pre-AutoML

try:
    _path  = _MODEL_PATH if os.path.exists(_MODEL_PATH) else _LEGACY_PATH
    _model = joblib.load(_path)
    ROOT_CAUSE_ML_ENABLED = True
    _label = "AutoML" if os.path.exists(_MODEL_PATH) else "Legacy"
    print(f"Root Cause Model loaded ({_label}): {_path}")
except Exception as e:
    _model = None
    ROOT_CAUSE_ML_ENABLED = False
    print("Root Cause Model not loaded:", e)


def predict_root_cause_with_model(vehicle: dict) -> list | None:
    if not ROOT_CAUSE_ML_ENABLED or _model is None:
        return None

    voltage = vehicle.get("battery_voltage", 12.0)
    temp    = vehicle.get("temperature", 50)
    rpm     = vehicle.get("rpm", 1500)

    v_type    = 0 if voltage >= 12.5 else 1 if voltage >= 11.5 else 2
    air_temp  = 295 + (temp / 120) * 15
    proc_temp = air_temp + 10
    rot_speed = 1168 + (rpm / 7000) * (2886 - 1168)
    torque    = max(3, min(77, round(60 - (rpm / 7000) * 40)))
    tool_wear = round(((13 - voltage) / 4) * 150 + (temp / 120) * 50)
    tool_wear = max(0, min(250, tool_wear))

    features = pd.DataFrame([[
        v_type, air_temp, proc_temp, rot_speed, torque, tool_wear
    ]], columns=[
        "Type",
        "Air temperature [K]",
        "Process temperature [K]",
        "Rotational speed [rpm]",
        "Torque [Nm]",
        "Tool wear [min]"
    ])

    prediction = _model.predict(features)[0]
    proba      = _model.predict_proba(features)[0]
    classes    = _model.classes_

    # Return top causes with probability > 15%
    causes = [
        classes[i] for i, p in enumerate(proba)
        if p > 0.15 and classes[i] != "No Failure"
    ]

    return causes if causes else [prediction]


def batch_predict_root_cause(vehicles: list[dict]) -> list[list | None]:
    """Predict root causes for all vehicles in one model call."""
    if not ROOT_CAUSE_ML_ENABLED or _model is None:
        return [None] * len(vehicles)

    rows = []
    for v in vehicles:
        voltage   = v.get("battery_voltage", 12.0)
        temp      = v.get("temperature", 50)
        rpm       = v.get("rpm", 1500)
        v_type    = 0 if voltage >= 12.5 else 1 if voltage >= 11.5 else 2
        air_temp  = 295 + (temp / 120) * 15
        proc_temp = air_temp + 10
        rot_speed = 1168 + (rpm / 7000) * (2886 - 1168)
        torque    = max(3, min(77, round(60 - (rpm / 7000) * 40)))
        tool_wear = max(0, min(250, round(((13 - voltage) / 4) * 150 + (temp / 120) * 50)))
        rows.append([v_type, air_temp, proc_temp, rot_speed, torque, tool_wear])

    df = pd.DataFrame(rows, columns=[
        "Type", "Air temperature [K]", "Process temperature [K]",
        "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]"
    ])
    predictions = _model.predict(df)
    probas      = _model.predict_proba(df)
    classes     = _model.classes_

    results = []
    for i in range(len(vehicles)):
        proba  = probas[i]
        causes = [classes[j] for j, p in enumerate(proba) if p > 0.15 and classes[j] != "No Failure"]
        results.append(causes if causes else [predictions[i]])
    return results
