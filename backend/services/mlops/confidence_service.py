"""
Confidence Service
==================
Computes prediction confidence for each model type:
  - Classifiers  (failure, rootcause, fleet): predict_proba → max class prob + entropy
  - Regressors   (health, rul):               ensemble tree variance → prediction interval

All models are loaded lazily via the same paths used by the existing model services
so there is no duplication of joblib.load calls at import time.
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd
import joblib

_ML_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "ml")


# ── Lazy model loader (one load per process lifetime) ─────────────────────────

_loaded: dict = {}


def _load(key: str, *candidate_paths: str):
    if key not in _loaded:
        for p in candidate_paths:
            if os.path.exists(p):
                try:
                    _loaded[key] = joblib.load(p)
                    break
                except Exception:
                    pass
        else:
            _loaded[key] = None
    return _loaded[key]


def _failure_model():
    return _load(
        "failure",
        os.path.join(_ML_DIR, "models", "failure", "best.pkl"),
        os.path.join(_ML_DIR, "failure_model_v2.pkl"),
        os.path.join(_ML_DIR, "failure_model.pkl"),
    )


def _health_model():
    return _load(
        "health",
        os.path.join(_ML_DIR, "models", "health", "best.pkl"),
        os.path.join(_ML_DIR, "health_model_v2.pkl"),
        os.path.join(_ML_DIR, "health_model.pkl"),
    )


def _rootcause_model():
    return _load(
        "rootcause",
        os.path.join(_ML_DIR, "models", "rootcause", "best.pkl"),
        os.path.join(_ML_DIR, "root_cause_model.pkl"),
    )


def _fleet_model():
    return _load(
        "fleet",
        os.path.join(_ML_DIR, "models", "fleet", "best.pkl"),
        os.path.join(_ML_DIR, "fleet_optimizer.pkl"),
    )


def _rul_model():
    return _load(
        "rul",
        os.path.join(_ML_DIR, "models", "rul", "best.pkl"),
        os.path.join(_ML_DIR, "rul_model.pkl"),
    )


def _feats():
    return _load("feats", os.path.join(_ML_DIR, "failure_features.pkl"))


def _rul_scaler():
    return _load("rul_scaler", os.path.join(_ML_DIR, "rul_scaler.pkl"))


# ── Feature builders (mirrors existing model services exactly) ────────────────

def _vehicle_to_maintenance_features(vehicle: dict) -> dict:
    v = vehicle.get("battery_voltage", 12.0)
    t = vehicle.get("temperature", 50)
    r = vehicle.get("rpm", 1500)
    bat   = 0 if v >= 12.5 else 1 if v >= 11.0 else 2
    tire  = 0 if t < 40 else 1 if t < 70 else 2
    brake = 0 if r < 2000 else 1 if r < 4500 else 2
    return {
        "model_enc": 0, "Mileage": int(r * 10),
        "Vehicle_Age": max(1, int((100 - vehicle.get("health_score", 70)) / 10)),
        "Engine_Size": 2, "Odometer_Reading": int(r * 100),
        "Reported_Issues": min(5, int((100 - vehicle.get("health_score", 70)) / 20)),
        "Service_History": 1, "Accident_History": 1 if t > 80 else 0,
        "Fuel_Efficiency": max(5.0, 20.0 - (t / 120) * 10),
        "Insurance_Premium": 15000,
        "tire": tire, "brake": brake, "bat": bat,
        "fuel": 1, "trans": 0, "owner": 0, "maint_hist": 0,
    }


def _vehicle_to_rootcause_features(vehicle: dict) -> pd.DataFrame:
    voltage = vehicle.get("battery_voltage", 12.0)
    temp    = vehicle.get("temperature", 50)
    rpm     = vehicle.get("rpm", 1500)
    v_type    = 0 if voltage >= 12.5 else 1 if voltage >= 11.5 else 2
    air_temp  = 295 + (temp / 120) * 15
    proc_temp = air_temp + 10
    rot_speed = 1168 + (rpm / 7000) * (2886 - 1168)
    torque    = max(3, min(77, round(60 - (rpm / 7000) * 40)))
    tool_wear = max(0, min(250, round(((13 - voltage) / 4) * 150 + (temp / 120) * 50)))
    return pd.DataFrame([[v_type, air_temp, proc_temp, rot_speed, torque, tool_wear]],
                        columns=["Type", "Air temperature [K]", "Process temperature [K]",
                                 "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]"])


def _vehicle_to_fleet_features(vehicle: dict) -> np.ndarray:
    return np.array([[
        vehicle.get("health_score", 70),
        vehicle.get("failure_probability", 30),
        vehicle.get("remaining_useful_life_days", 15),
        vehicle.get("repair_now_cost", 5000),
        vehicle.get("failure_cost", 20000),
        vehicle.get("potential_savings", 15000),
    ]])


def _vehicle_to_rul_features(vehicle: dict) -> pd.DataFrame:
    health  = vehicle.get("health_score", 50)
    temp    = vehicle.get("temperature", 50)
    voltage = vehicle.get("battery_voltage", 12.0)
    rpm     = vehicle.get("rpm", 1500)
    op1  = (voltage - 9) / (14 - 9) * 0.006 - 0.003
    op2  = (temp - 20) / (120 - 20) * 0.006 - 0.003
    s2   = 640 + (rpm / 7000) * 10
    s3   = 1580 + (temp / 120) * 30
    s4   = 1400 + (temp / 120) * 20
    s6   = 21.6 + (1 - health / 100) * 2
    s7   = 550 + (1 - health / 100) * 10
    s8   = 2388 + (rpm / 7000) * 5
    s9   = 9000 + (rpm / 7000) * 500
    s11  = 47 + (1 - health / 100) * 5
    s12  = 521 + (temp / 120) * 5
    s13  = 2388 + (rpm / 7000) * 3
    s14  = 8100 + (1 - health / 100) * 200
    s15  = 8.4 + (1 - health / 100) * 0.5
    s17  = 390 + (rpm / 7000) * 10
    s20  = 39 - (1 - health / 100) * 5
    s21  = 23 + (temp / 120) * 2
    return pd.DataFrame([[op1, op2, s2, s3, s4, s6, s7, s8, s9,
                          s11, s12, s13, s14, s15, s17, s20, s21]],
                        columns=["op1", "op2", "s2", "s3", "s4", "s6", "s7", "s8", "s9",
                                 "s11", "s12", "s13", "s14", "s15", "s17", "s20", "s21"])


# ── Confidence helpers ────────────────────────────────────────────────────────

def _proba_confidence(proba: np.ndarray) -> dict:
    """Max-probability confidence + Shannon entropy for a single prediction."""
    max_prob = float(np.max(proba))
    # Normalised entropy: 0 = perfectly certain, 1 = maximally uncertain
    n = len(proba)
    entropy = float(-np.sum(proba * np.log(proba + 1e-12)) / np.log(n + 1e-12))
    return {
        "confidence":  round(max_prob * 100, 1),
        "uncertainty": round(entropy * 100, 1),
        "method":      "predict_proba",
    }


def _ensemble_variance_confidence(model, X: np.ndarray) -> dict:
    """
    For ensemble regressors (RF / ET / GB): collect per-tree predictions,
    compute std-dev as uncertainty, and derive a confidence score.
    """
    estimators = getattr(model, "estimators_", None)
    if estimators is None or len(estimators) == 0:
        return {"confidence": None, "uncertainty": None, "method": "unavailable"}

    preds = np.array([e.predict(X)[0] for e in estimators])
    mean  = float(np.mean(preds))
    std   = float(np.std(preds))
    # Confidence: 100% when std=0, drops as variance grows (capped at 0%)
    conf  = max(0.0, 100.0 - min(std, 100.0))
    return {
        "confidence":        round(conf, 1),
        "uncertainty":       round(std, 2),
        "prediction_mean":   round(mean, 2),
        "prediction_std":    round(std, 2),
        "prediction_interval_95": [
            round(mean - 1.96 * std, 2),
            round(mean + 1.96 * std, 2),
        ],
        "method": "ensemble_variance",
    }


# ── Public API ────────────────────────────────────────────────────────────────

def compute_confidence(vehicle: dict) -> dict:
    """
    Returns per-model confidence scores for a single vehicle.
    Each entry contains confidence %, uncertainty %, and method used.
    """
    results: dict[str, dict] = {}

    # ── Failure (classifier) ──────────────────────────────────────────────────
    model = _failure_model()
    if model is not None:
        try:
            row  = _vehicle_to_maintenance_features(vehicle)
            cols = _feats() or list(row.keys())
            feat = pd.DataFrame([row])[cols]
            proba = model.predict_proba(feat)[0]
            results["failure"] = _proba_confidence(proba)
        except Exception as e:
            results["failure"] = {"error": str(e)}
    else:
        results["failure"] = {"confidence": None, "method": "model_unavailable"}

    # ── Health (regressor) ────────────────────────────────────────────────────
    model = _health_model()
    if model is not None:
        try:
            row  = _vehicle_to_maintenance_features(vehicle)
            cols = _feats() or list(row.keys())
            feat = pd.DataFrame([row])[cols].values
            results["health"] = _ensemble_variance_confidence(model, feat)
        except Exception as e:
            results["health"] = {"error": str(e)}
    else:
        results["health"] = {"confidence": None, "method": "model_unavailable"}

    # ── Root Cause (classifier) ───────────────────────────────────────────────
    model = _rootcause_model()
    if model is not None:
        try:
            feat  = _vehicle_to_rootcause_features(vehicle)
            proba = model.predict_proba(feat)[0]
            results["rootcause"] = _proba_confidence(proba)
        except Exception as e:
            results["rootcause"] = {"error": str(e)}
    else:
        results["rootcause"] = {"confidence": None, "method": "model_unavailable"}

    # ── Fleet Priority (classifier) ───────────────────────────────────────────
    model = _fleet_model()
    if model is not None:
        try:
            feat  = _vehicle_to_fleet_features(vehicle)
            proba = model.predict_proba(feat)[0]
            results["fleet_priority"] = _proba_confidence(proba)
        except Exception as e:
            results["fleet_priority"] = {"error": str(e)}
    else:
        results["fleet_priority"] = {"confidence": None, "method": "model_unavailable"}

    # ── RUL (regressor) ───────────────────────────────────────────────────────
    model  = _rul_model()
    scaler = _rul_scaler()
    if model is not None and scaler is not None:
        try:
            feat   = _vehicle_to_rul_features(vehicle)
            scaled = scaler.transform(feat)
            results["rul"] = _ensemble_variance_confidence(model, scaled)
        except Exception as e:
            results["rul"] = {"error": str(e)}
    else:
        results["rul"] = {"confidence": None, "method": "model_unavailable"}

    # ── Aggregate ─────────────────────────────────────────────────────────────
    valid_confs = [v["confidence"] for v in results.values()
                   if isinstance(v.get("confidence"), (int, float))]
    overall = round(sum(valid_confs) / len(valid_confs), 1) if valid_confs else None

    return {
        "vehicle_id":         vehicle.get("vehicle_id"),
        "overall_confidence": overall,
        "models":             results,
    }
