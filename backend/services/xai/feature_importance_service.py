"""
Feature Importance Service
===========================
Loads trained ML models, reads feature_importances_, maps raw feature
names to user-friendly labels, normalizes to percentages summing to 100,
and returns the top 5 contributing features per model.
"""
import os
import joblib
from fastapi import APIRouter

router = APIRouter(prefix="/xai", tags=["xai"])

@router.get("/feature-importance")
def feature_importance_endpoint():
    return get_feature_importances()

_ML_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "ml")

# ── Friendly label maps ───────────────────────────────────────────────────────
_AI4I_LABELS = {
    "Type":                        "Machine Type",
    "Air temperature [K]":         "Air Temperature",
    "Process temperature [K]":     "Process Temperature",
    "Rotational speed [rpm]":      "Rotational Speed",
    "Torque [Nm]":                 "Torque",
    "Tool wear [min]":             "Tool Wear",
    "TWF":                         "Tool Wear Failure",
    "HDF":                         "Heat Dissipation Failure",
    "PWF":                         "Power Failure",
    "OSF":                         "Overstrain Failure",
    "RNF":                         "Random Failure",
}

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
    "Type":                        "Machine Type",
    "Air temperature [K]":         "Air Temperature",
    "Process temperature [K]":     "Process Temperature",
    "Rotational speed [rpm]":      "Rotational Speed",
    "Torque [Nm]":                 "Torque",
    "Tool wear [min]":             "Tool Wear",
}

_FLEET_LABELS = {
    "health_score":        "Health Score",
    "failure_probability": "Failure Probability",
    "rul_days":            "Remaining Useful Life",
    "repair_cost":         "Repair Cost",
    "failure_cost":        "Failure Cost",
    "potential_savings":   "Potential Savings",
}

# ── Model registry ────────────────────────────────────────────────────────────
_MODELS = {
    "health": {
        "paths":       ["health_model_v2.pkl", "health_model.pkl"],
        "label_map":   _VM_LABELS,
        "feats_path":  "failure_features.pkl",   # same feature list as failure v2
        "ai4i_feats":  ["Type","Air temperature [K]","Process temperature [K]",
                        "Rotational speed [rpm]","Torque [Nm]","Tool wear [min]",
                        "TWF","HDF","PWF","OSF","RNF"],
    },
    "failure": {
        "paths":       ["failure_model_v2.pkl", "failure_model.pkl"],
        "label_map":   _VM_LABELS,
        "feats_path":  "failure_features.pkl",
        "ai4i_feats":  ["Type","Air temperature [K]","Process temperature [K]",
                        "Rotational speed [rpm]","Torque [Nm]","Tool wear [min]",
                        "TWF","HDF","PWF","OSF","RNF"],
    },
    "root_cause": {
        "paths":       ["root_cause_model.pkl"],
        "label_map":   _RC_LABELS,
        "feats_path":  None,
        "ai4i_feats":  ["Type","Air temperature [K]","Process temperature [K]",
                        "Rotational speed [rpm]","Torque [Nm]","Tool wear [min]"],
    },
    "fleet_priority": {
        "paths":       ["fleet_optimizer.pkl"],
        "label_map":   _FLEET_LABELS,
        "feats_path":  None,
        "ai4i_feats":  ["health_score","failure_probability","rul_days",
                        "repair_cost","failure_cost","potential_savings"],
    },
}


def _load_model(paths: list[str]):
    """Try each path in order, return (model, path) or (None, None)."""
    for p in paths:
        full = os.path.join(_ML_DIR, p)
        if os.path.exists(full):
            try:
                return joblib.load(full), p
            except Exception:
                continue
    return None, None


def _get_feature_names(model_key: str, model) -> list[str]:
    """Resolve feature names: saved list → sklearn attr → ai4i fallback."""
    cfg = _MODELS[model_key]

    # 1. Try saved feature list (v2 models)
    if cfg["feats_path"]:
        fp = os.path.join(_ML_DIR, cfg["feats_path"])
        if os.path.exists(fp):
            try:
                return joblib.load(fp)
            except Exception:
                pass

    # 2. Try sklearn feature_names_in_ attribute
    if hasattr(model, "feature_names_in_"):
        return list(model.feature_names_in_)

    # 3. Fallback to hardcoded ai4i feature list
    return cfg["ai4i_feats"]


def _normalize_top5(importances: list[float], names: list[str],
                    label_map: dict) -> list[dict]:
    """
    Pair names with importances, sort descending, take top 5,
    normalize those 5 to sum to 100%.
    """
    paired = sorted(zip(importances, names), reverse=True)
    top5   = paired[:5]

    total  = sum(imp for imp, _ in top5) or 1.0
    result = []
    for rank, (imp, raw_name) in enumerate(top5, start=1):
        pct = round((imp / total) * 100, 1)
        result.append({
            "rank":           rank,
            "feature":        raw_name,
            "label":          label_map.get(raw_name, raw_name.replace("_", " ").title()),
            "importance_pct": float(pct),
        })

    # Fix rounding so total is exactly 100
    diff = 100.0 - sum(r["importance_pct"] for r in result)
    if result:
        result[0]["importance_pct"] = float(round(result[0]["importance_pct"] + diff, 1))

    return result


# ── Pre-compute feature importances once at startup ───────────────────────────
_CACHED_IMPORTANCES: dict = {}


def _build_importances() -> dict:
    output = {}
    for model_key, cfg in _MODELS.items():
        model, loaded_path = _load_model(cfg["paths"])
        if model is None:
            output[model_key] = {"status": "unavailable", "reason": "Model file not found", "top5": []}
            continue
        if not hasattr(model, "feature_importances_"):
            output[model_key] = {
                "status": "fallback",
                "reason": f"{type(model).__name__} does not expose feature_importances_",
                "model":  type(model).__name__,
                "top5":   [],
            }
            continue
        try:
            importances   = list(model.feature_importances_)
            feature_names = _get_feature_names(model_key, model)
            if len(importances) != len(feature_names):
                feature_names = [f"feature_{i}" for i in range(len(importances))]
            top5 = _normalize_top5(importances, feature_names, cfg["label_map"])
            output[model_key] = {
                "status": "ok", "model": type(model).__name__,
                "loaded_from": loaded_path, "total_features": len(importances), "top5": top5,
            }
        except Exception as e:
            output[model_key] = {"status": "error", "reason": str(e), "top5": []}
    return output


# Run once at import time — result is reused for every request
_CACHED_IMPORTANCES = _build_importances()


def get_feature_importances() -> dict:
    """Return pre-computed feature importances (computed once at startup)."""
    return _CACHED_IMPORTANCES
