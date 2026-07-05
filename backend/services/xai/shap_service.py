"""
SHAP Explainability Service
============================
Uses shap.TreeExplainer (cached globally) to explain per-vehicle predictions.
Returns top-5 positive SHAP contributors per model.
Gracefully falls back to feature_importances_ if SHAP is unavailable.
"""
import os
import joblib
import numpy as np
import pandas as pd

_ML_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "ml")

# ── SHAP availability ─────────────────────────────────────────────────────────
try:
    import shap
    SHAP_ENABLED = True
except ImportError:
    SHAP_ENABLED = False
    print("SHAP not installed — falling back to feature_importances_")

# ── Friendly label maps ───────────────────────────────────────────────────────
_VM_LABELS = {
    "model_enc":        "Vehicle Model",
    "Mileage":          "Mileage",
    "Vehicle_Age":      "Vehicle Age",
    "Engine_Size":      "Engine Size",
    "Odometer_Reading": "Odometer Reading",
    "Reported_Issues":  "Reported Issues",
    "Service_History":  "Service History",
    "Accident_History": "Accident History",
    "Fuel_Efficiency":  "Fuel Efficiency",
    "Insurance_Premium":"Insurance Premium",
    "tire":             "Tire Condition",
    "brake":            "Brake Condition",
    "bat":              "Battery Status",
    "fuel":             "Fuel Type",
    "trans":            "Transmission Type",
    "owner":            "Owner Type",
    "maint_hist":       "Maintenance History",
}
_RC_LABELS = {
    "Type":                    "Machine Type",
    "Air temperature [K]":     "Air Temperature",
    "Process temperature [K]": "Process Temperature",
    "Rotational speed [rpm]":  "Rotational Speed",
    "Torque [Nm]":             "Torque",
    "Tool wear [min]":         "Tool Wear",
}
_FLEET_LABELS = {
    "health_score":        "Health Score",
    "failure_probability": "Failure Probability",
    "rul_days":            "Remaining Useful Life",
    "repair_cost":         "Repair Cost",
    "failure_cost":        "Failure Cost",
    "potential_savings":   "Potential Savings",
}

# ── Global explainer cache (created once at startup) ──────────────────────────
_explainers: dict = {}
_models:     dict = {}
_feat_names: dict = {}


def _load():
    """Load all models and build SHAP explainers once."""
    global _explainers, _models, _feat_names

    specs = {
        "failure": {
            "files":      ["failure_model_v2.pkl", "failure_model.pkl"],
            "feats_file": "failure_features.pkl",
            "labels":     _VM_LABELS,
            "fallback_feats": None,
        },
        "health": {
            "files":      ["health_model_v2.pkl", "health_model.pkl"],
            "feats_file": "failure_features.pkl",
            "labels":     _VM_LABELS,
            "fallback_feats": None,
        },
        "root_cause": {
            "files":      ["root_cause_model.pkl"],
            "feats_file": None,
            "labels":     _RC_LABELS,
            "fallback_feats": ["Type","Air temperature [K]","Process temperature [K]",
                               "Rotational speed [rpm]","Torque [Nm]","Tool wear [min]"],
        },
        "fleet_priority": {
            "files":      ["fleet_optimizer.pkl"],
            "feats_file": None,
            "labels":     _FLEET_LABELS,
            "fallback_feats": ["health_score","failure_probability","rul_days",
                               "repair_cost","failure_cost","potential_savings"],
        },
    }

    for key, spec in specs.items():
        model = None
        for fname in spec["files"]:
            p = os.path.join(_ML_DIR, fname)
            if os.path.exists(p):
                try:
                    model = joblib.load(p)
                    break
                except Exception:
                    continue
        if model is None:
            continue

        _models[key] = model

        # Resolve feature names
        feats = None
        if spec["feats_file"]:
            fp = os.path.join(_ML_DIR, spec["feats_file"])
            if os.path.exists(fp):
                try:
                    feats = joblib.load(fp)
                except Exception:
                    pass
        if feats is None and hasattr(model, "feature_names_in_"):
            feats = list(model.feature_names_in_)
        if feats is None:
            feats = spec["fallback_feats"] or [f"f{i}" for i in range(len(model.feature_importances_))]
        _feat_names[key] = feats

        # Build SHAP TreeExplainer
        if SHAP_ENABLED:
            try:
                _explainers[key] = shap.TreeExplainer(model)
                print(f"SHAP TreeExplainer ready: {key}")
            except Exception as e:
                print(f"SHAP explainer failed for {key}: {e}")


# Run at import time
_load()


# ── Vehicle → feature vector ──────────────────────────────────────────────────
def _vehicle_to_vm_row(vehicle: dict) -> dict:
    """Map vehicle sensor dict to vehicle_maintenance_data feature space."""
    v = vehicle.get("battery_voltage", 12.0)
    t = vehicle.get("temperature", 50)
    r = vehicle.get("rpm", 1500)
    h = vehicle.get("health_score", 70)

    bat   = 0 if v >= 12.5 else 1 if v >= 11.0 else 2
    tire  = 0 if t < 40   else 1 if t < 70    else 2
    brake = 0 if r < 2000 else 1 if r < 4500  else 2

    return {
        "model_enc":        0,
        "Mileage":          int(r * 10),
        "Vehicle_Age":      max(1, int((100 - h) / 10)),
        "Engine_Size":      2,
        "Odometer_Reading": int(r * 100),
        "Reported_Issues":  min(5, int((100 - h) / 20)),
        "Service_History":  1,
        "Accident_History": 1 if t > 80 else 0,
        "Fuel_Efficiency":  max(5.0, 20.0 - (t / 120) * 10),
        "Insurance_Premium":15000,
        "tire":             tire,
        "brake":            brake,
        "bat":              bat,
        "fuel":             1,
        "trans":            0,
        "owner":            0,
        "maint_hist":       0,
    }


def _vehicle_to_rc_row(vehicle: dict) -> dict:
    v = vehicle.get("battery_voltage", 12.0)
    t = vehicle.get("temperature", 50)
    r = vehicle.get("rpm", 1500)
    v_type    = 0 if v >= 12.5 else 1 if v >= 11.5 else 2
    air_temp  = 295 + (t / 120) * 15
    proc_temp = air_temp + 10
    rot_speed = 1168 + (r / 7000) * (2886 - 1168)
    torque    = max(3, min(77, round(60 - (r / 7000) * 40)))
    tool_wear = round(((13 - v) / 4) * 150 + (t / 120) * 50)
    tool_wear = max(0, min(250, tool_wear))
    return {
        "Type":                    v_type,
        "Air temperature [K]":     air_temp,
        "Process temperature [K]": proc_temp,
        "Rotational speed [rpm]":  rot_speed,
        "Torque [Nm]":             torque,
        "Tool wear [min]":         tool_wear,
    }


def _vehicle_to_fleet_row(vehicle: dict) -> dict:
    return {
        "health_score":        vehicle.get("health_score", 70),
        "failure_probability": vehicle.get("failure_probability", 30),
        "rul_days":            vehicle.get("remaining_useful_life_days", 15),
        "repair_cost":         vehicle.get("repair_now_cost", 5000),
        "failure_cost":        vehicle.get("failure_cost", 15000),
        "potential_savings":   vehicle.get("potential_savings", 10000),
    }


def _make_df(row: dict, feats: list[str]) -> pd.DataFrame:
    return pd.DataFrame([row])[feats]


# ── Core SHAP computation ─────────────────────────────────────────────────────
def _shap_top5(key: str, df: pd.DataFrame, label_map: dict) -> list[dict]:
    """
    Compute SHAP values for one row, return top-5 contributors sorted by
    absolute impact, with sign preserved.
    """
    explainer = _explainers.get(key)
    model     = _models.get(key)
    feats     = _feat_names.get(key, df.columns.tolist())

    if explainer is None or model is None:
        return _fallback_top5(key, label_map)

    try:
        sv = explainer.shap_values(df)

        # For classifiers shap_values returns list[array] (one per class)
        # We want class-1 (failure / high priority)
        if isinstance(sv, list):
            vals = sv[1][0] if len(sv) > 1 else sv[0][0]
        else:
            # Regressor or single-output classifier
            vals = sv[0] if sv.ndim == 2 else sv

        # Pair with feature names
        pairs = list(zip(feats, vals.tolist()))

        # Sort by absolute value descending, keep top 5
        pairs.sort(key=lambda x: abs(x[1]), reverse=True)
        top5 = pairs[:5]

        total_abs = sum(abs(v) for _, v in top5) or 1.0
        result = []
        for rank, (raw, val) in enumerate(top5, 1):
            pct = round((abs(val) / total_abs) * 100, 1)
            result.append({
                "rank":      rank,
                "feature":   raw,
                "label":     label_map.get(raw, raw.replace("_", " ").title()),
                "shap_value": round(float(val), 4),
                "impact":    pct,
                "direction": "increases_risk" if val > 0 else "reduces_risk",
            })

        # Normalize to 100
        diff = 100.0 - sum(r["impact"] for r in result)
        if result:
            result[0]["impact"] = round(result[0]["impact"] + diff, 1)

        return result

    except Exception as e:
        print(f"SHAP compute error [{key}]: {e}")
        return _fallback_top5(key, label_map)


def _fallback_top5(key: str, label_map: dict) -> list[dict]:
    """Use feature_importances_ when SHAP fails."""
    model = _models.get(key)
    feats = _feat_names.get(key, [])
    if model is None or not hasattr(model, "feature_importances_"):
        return []
    imps   = model.feature_importances_
    paired = sorted(zip(feats, imps), key=lambda x: x[1], reverse=True)[:5]
    total  = sum(v for _, v in paired) or 1.0
    result = []
    for rank, (raw, val) in enumerate(paired, 1):
        pct = round((val / total) * 100, 1)
        result.append({
            "rank":       rank,
            "feature":    raw,
            "label":      label_map.get(raw, raw.replace("_", " ").title()),
            "shap_value": round(float(val), 4),
            "impact":     pct,
            "direction":  "increases_risk",
        })
    diff = 100.0 - sum(r["impact"] for r in result)
    if result:
        result[0]["impact"] = round(result[0]["impact"] + diff, 1)
    return result


# ── Public API ────────────────────────────────────────────────────────────────
def explain_vehicle(vehicle: dict) -> dict:
    """
    Generate SHAP explanations for all 4 models for a single vehicle.
    Returns dict keyed by model name, each with top-5 contributors.
    """
    vm_row    = _vehicle_to_vm_row(vehicle)
    rc_row    = _vehicle_to_rc_row(vehicle)
    fleet_row = _vehicle_to_fleet_row(vehicle)

    results = {}

    for key in ["failure", "health"]:
        feats = _feat_names.get(key)
        if feats:
            df = _make_df(vm_row, feats)
            results[key] = _shap_top5(key, df, _VM_LABELS)
        else:
            results[key] = _fallback_top5(key, _VM_LABELS)

    feats_rc = _feat_names.get("root_cause")
    if feats_rc:
        df_rc = _make_df(rc_row, feats_rc)
        results["root_cause"] = _shap_top5("root_cause", df_rc, _RC_LABELS)
    else:
        results["root_cause"] = _fallback_top5("root_cause", _RC_LABELS)

    feats_fl = _feat_names.get("fleet_priority")
    if feats_fl:
        df_fl = _make_df(fleet_row, feats_fl)
        results["fleet_priority"] = _shap_top5("fleet_priority", df_fl, _FLEET_LABELS)
    else:
        results["fleet_priority"] = _fallback_top5("fleet_priority", _FLEET_LABELS)

    return {
        "shap_enabled": SHAP_ENABLED,
        "models":       results,
    }
