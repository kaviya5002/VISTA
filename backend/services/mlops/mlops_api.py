"""
MLOps API
=========
FastAPI router exposing:
  GET /mlops/models              → model cards for all five model families
  GET /mlops/model/{name}        → single model card with full version history
  GET /mlops/confidence/{vehicle_id} → per-model prediction confidence for one vehicle
  GET /mlops/drift               → feature drift analysis across live fleet telemetry
"""
from __future__ import annotations

import time as _time
from fastapi import APIRouter, HTTPException

from services.fleet_repository import get_all_vehicles
from services.health_score import calculate_health
from services.failure_forecast import predict_failure
from services.root_cause import analyze_root_cause
from services.rul_engine import calculate_rul
from services.cost_analysis import calculate_cost_impact
from services.maintenance_strategist import ai_maintenance_strategy
from services.fleet_optimizer import optimize_fleet

from services.mlops.model_monitor import get_all_models, get_model
from services.mlops.model_health import get_model_health
from services.mlops.confidence_service import compute_confidence
from services.mlops.drift_detector import detect_drift

router = APIRouter(prefix="/mlops", tags=["mlops"])

_cache: dict = {}
_TTL = 30.0


def _cached(key: str, fn):
    now = _time.time()
    if key in _cache and (now - _cache[key]["at"]) < _TTL:
        return _cache[key]["data"]
    result = fn()
    _cache[key] = {"data": result, "at": now}
    return result


def _enrich(v: dict) -> dict:
    v = calculate_health(v)
    v = predict_failure(v)
    v = analyze_root_cause(v)
    v = calculate_rul(v)
    v = calculate_cost_impact(v)
    v = ai_maintenance_strategy(v)
    return v


def _get_fleet() -> list[dict]:
    return optimize_fleet([_enrich(v) for v in get_all_vehicles()])


# ── GET /mlops/models ─────────────────────────────────────────────────────────

@router.get("/models")
def list_models():
    """
    Model cards for all five model families (failure, health, rootcause, fleet, rul).
    Each card includes: algorithm, version, dataset, training date, CV score,
    all tracked metrics, version history, and deployment status.
    Also includes per-model health status and retraining recommendations.
    """
    def _build():
        fleet = _get_fleet()
        health_summary = get_model_health(fleet)
        cards = get_all_models()

        # Merge health info into each card
        health_by_name = {m["name"]: m for m in health_summary["models"]}
        for card in cards:
            h = health_by_name.get(card["name"], {})
            card["health"]                  = h.get("health", "unknown")
            card["retrain_needed"]          = h.get("retrain_needed", False)
            card["retrain_recommendation"]  = h.get("retrain_recommendation")
            card["prediction_counts"]       = h.get("prediction_counts", {})

        return {
            "models":  cards,
            "overall": health_summary["overall"],
        }

    return _cached("mlops_models", _build)


# ── GET /mlops/model/{name} ───────────────────────────────────────────────────

@router.get("/model/{name}")
def get_model_detail(name: str):
    """
    Full model card for a single model family.
    Includes complete version history, all experiment metrics, and health status.
    """
    card = get_model(name)
    if card is None:
        raise HTTPException(status_code=404, detail=f"Unknown model: '{name}'. "
                            f"Valid names: failure, health, rootcause, fleet, rul")

    def _build():
        fleet = _get_fleet()
        health_summary = get_model_health(fleet)
        health_by_name = {m["name"]: m for m in health_summary["models"]}
        h = health_by_name.get(name, {})
        card["health"]                 = h.get("health", "unknown")
        card["retrain_needed"]         = h.get("retrain_needed", False)
        card["retrain_recommendation"] = h.get("retrain_recommendation")
        card["prediction_counts"]      = h.get("prediction_counts", {})
        return card

    return _cached(f"mlops_model_{name}", _build)


# ── GET /mlops/confidence/{vehicle_id} ───────────────────────────────────────

@router.get("/confidence/{vehicle_id}")
def model_confidence(vehicle_id: int):
    """
    Per-model prediction confidence for a single vehicle.
    Classifiers: max predict_proba + Shannon entropy.
    Regressors:  ensemble tree variance → prediction interval.
    Returns overall_confidence (mean across models) and per-model breakdown.
    """
    vehicles = get_all_vehicles()
    vehicle  = next((v for v in vehicles if v["vehicle_id"] == vehicle_id), None)
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"Vehicle {vehicle_id} not found")

    vehicle = _enrich(vehicle)
    return compute_confidence(vehicle)


# ── GET /mlops/drift ──────────────────────────────────────────────────────────

@router.get("/drift")
def feature_drift():
    """
    Feature drift analysis comparing live fleet telemetry against training distributions.
    Uses PSI (Population Stability Index) per feature.
    Returns per-feature drift level, PSI score, z-score stats, and affected models.
    """
    def _build():
        fleet = _get_fleet()
        return detect_drift(fleet)

    return _cached("mlops_drift", _build)
