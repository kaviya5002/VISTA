"""
Executive Service — FastAPI router exposing:
  GET /executive/dashboard      → KPI cards, trend charts, yearly projection
  GET /executive/summary        → executive report with insights & recommendations
  GET /executive/business-impact → with/without TwinGuard comparison
"""
from __future__ import annotations

import time as _time
from fastapi import APIRouter

from services.fleet_repository import get_all_vehicles
from services.health_score import calculate_health
from services.failure_forecast import predict_failure
from services.root_cause import analyze_root_cause
from services.rul_engine import calculate_rul
from services.cost_analysis import calculate_cost_impact
from services.maintenance_strategist import ai_maintenance_strategy
from services.fleet_optimizer import optimize_fleet

from services.executive.business_impact import compute_business_impact
from services.executive.roi_calculator import calculate_roi
from services.executive.executive_dashboard import build_dashboard
from services.executive.executive_report import generate_executive_report

router = APIRouter(prefix="/executive", tags=["executive"])

_cache: dict = {}
_TTL = 30.0


def _cached(key: str, fn):
    now = _time.time()
    if key in _cache and (now - _cache[key]["at"]) < _TTL:
        return _cache[key]["data"]
    result = fn()
    _cache[key] = {"data": result, "at": now}
    return result


def _get_fleet() -> list[dict]:
    vehicles = get_all_vehicles()
    enriched = []
    for v in vehicles:
        v = calculate_health(v)
        v = predict_failure(v)
        v = analyze_root_cause(v)
        v = calculate_rul(v)
        v = calculate_cost_impact(v)
        v = ai_maintenance_strategy(v)
        enriched.append(v)
    return optimize_fleet(enriched)


def _build_all():
    fleet  = _get_fleet()
    impact = compute_business_impact(fleet)
    roi    = calculate_roi(fleet, impact)
    return fleet, impact, roi


@router.get("/dashboard")
def executive_dashboard():
    """
    Aggregated KPI cards with trend indicators and chart data.
    Covers: fleet health, cost savings, downtime reduction,
    failures prevented, AI accuracy, CO₂ reduction, and ROI.
    """
    def _build():
        fleet, impact, roi = _build_all()
        return build_dashboard(fleet, impact, roi)
    return _cached("exec_dashboard", _build)


@router.get("/summary")
def executive_summary():
    """
    Full executive report: narrative summary, headline metrics,
    top risks, strategic recommendations, and financial detail.
    """
    def _build():
        fleet, impact, roi = _build_all()
        return generate_executive_report(fleet, impact, roi)
    return _cached("exec_summary", _build)


@router.get("/business-impact")
def business_impact():
    """
    Side-by-side comparison of fleet operations with vs without TwinGuard.
    Includes failure counts, downtime, costs, CO₂, and live fleet signals.
    """
    def _build():
        fleet  = _get_fleet()
        return compute_business_impact(fleet)
    return _cached("exec_impact", _build)
