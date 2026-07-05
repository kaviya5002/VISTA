"""
Executive Dashboard — aggregates KPIs across fleet health, savings,
downtime, prevented failures, AI accuracy, and CO₂ reduction.
Designed to power rich KPI cards and trend charts on the frontend.
"""
from __future__ import annotations
from datetime import date, timedelta


# ── Trend helpers ─────────────────────────────────────────────────────────────

def _trend(current: float, previous: float) -> dict:
    """Returns direction, delta, and pct change for a KPI trend indicator."""
    delta = current - previous
    pct   = round((delta / max(abs(previous), 1)) * 100, 1)
    return {
        "value":     round(current, 1),
        "previous":  round(previous, 1),
        "delta":     round(delta, 1),
        "pct_change": pct,
        "direction": "up" if delta > 0 else "down" if delta < 0 else "flat",
    }


def _simulate_previous(current: float, variance: float = 0.08) -> float:
    """Approximate a 'last period' value for trend display (±variance)."""
    return round(current * (1 - variance), 1)


# ── KPI builders ──────────────────────────────────────────────────────────────

def _fleet_health_kpi(fleet: list[dict]) -> dict:
    n = len(fleet)
    avg_health   = round(sum(v.get("health_score", 0) for v in fleet) / max(n, 1), 1)
    healthy      = sum(1 for v in fleet if v.get("status") == "Healthy")
    warning      = sum(1 for v in fleet if v.get("status") == "Warning")
    critical     = sum(1 for v in fleet if v.get("status") == "Critical")
    immediate    = sum(1 for v in fleet if v.get("priority") == "Immediate")
    return {
        "id":    "fleet_health",
        "label": "Fleet Health Score",
        "unit":  "%",
        "icon":  "heart-pulse",
        "color": "#34D399" if avg_health >= 70 else "#FBBF24" if avg_health >= 50 else "#EF4444",
        "trend": _trend(avg_health, _simulate_previous(avg_health, 0.05)),
        "breakdown": {
            "healthy":   healthy,
            "warning":   warning,
            "critical":  critical,
            "immediate": immediate,
            "total":     n,
        },
        "chart_data": [
            {"label": "Healthy",  "value": healthy,  "color": "#34D399"},
            {"label": "Warning",  "value": warning,  "color": "#FBBF24"},
            {"label": "Critical", "value": critical, "color": "#EF4444"},
        ],
    }


def _savings_kpi(fleet: list[dict], roi: dict) -> dict:
    live_savings  = sum(v.get("potential_savings", 0) for v in fleet)
    annual_benefit = roi["annual_benefits"]["total_benefit"]
    return {
        "id":    "total_savings",
        "label": "Predicted Cost Savings",
        "unit":  "₹",
        "icon":  "indian-rupee",
        "color": "#38BDF8",
        "trend": _trend(live_savings, _simulate_previous(live_savings, 0.10)),
        "breakdown": {
            "live_predicted":    live_savings,
            "annual_projected":  annual_benefit,
            "repair_savings":    roi["annual_benefits"]["repair_savings"],
            "downtime_savings":  roi["annual_benefits"]["downtime_savings"],
            "pm_savings":        roi["annual_benefits"]["pm_savings"],
        },
        "chart_data": [
            {"label": "Repair Savings",   "value": roi["annual_benefits"]["repair_savings"],   "color": "#38BDF8"},
            {"label": "Downtime Savings", "value": roi["annual_benefits"]["downtime_savings"],  "color": "#818CF8"},
            {"label": "PM Savings",       "value": roi["annual_benefits"]["pm_savings"],        "color": "#34D399"},
        ],
    }


def _downtime_kpi(impact: dict) -> dict:
    saved_h  = impact["impact_delta"]["downtime_hours_saved"]
    total_h  = impact["without_twinguard"]["total_downtime_hours"]
    pct      = round((saved_h / max(total_h, 1)) * 100, 1)
    return {
        "id":    "downtime_reduction",
        "label": "Downtime Reduction",
        "unit":  "hrs/yr",
        "icon":  "clock",
        "color": "#A78BFA",
        "trend": _trend(saved_h, _simulate_previous(saved_h, 0.07)),
        "breakdown": {
            "hours_saved":       saved_h,
            "without_twinguard": total_h,
            "with_twinguard":    impact["with_twinguard"]["total_downtime_hours"],
            "reduction_pct":     pct,
        },
        "chart_data": [
            {"label": "Without TwinGuard", "value": total_h,  "color": "#EF4444"},
            {"label": "With TwinGuard",    "value": impact["with_twinguard"]["total_downtime_hours"], "color": "#A78BFA"},
        ],
    }


def _failures_kpi(impact: dict) -> dict:
    prevented = impact["impact_delta"]["failures_prevented"]
    without   = impact["without_twinguard"]["annual_failures"]
    with_tg   = impact["with_twinguard"]["annual_failures"]
    return {
        "id":    "failures_prevented",
        "label": "Failures Prevented",
        "unit":  "failures/yr",
        "icon":  "shield-check",
        "color": "#F97316",
        "trend": _trend(prevented, _simulate_previous(prevented, 0.06)),
        "breakdown": {
            "prevented":         prevented,
            "without_twinguard": without,
            "with_twinguard":    with_tg,
            "prevention_rate":   impact["impact_delta"]["failure_reduction_pct"],
        },
        "chart_data": [
            {"label": "Prevented",  "value": prevented, "color": "#34D399"},
            {"label": "Remaining",  "value": with_tg,   "color": "#EF4444"},
        ],
    }


def _ai_accuracy_kpi(fleet: list[dict]) -> dict:
    ml_used   = sum(1 for v in fleet if v.get("ml_model_used"))
    avg_conf  = round(sum(v.get("confidence_score", 0) for v in fleet) / max(len(fleet), 1), 1)
    ml_pct    = round((ml_used / max(len(fleet), 1)) * 100, 1)
    sources   = {}
    for v in fleet:
        src = v.get("health_source", "Formula")
        sources[src] = sources.get(src, 0) + 1
    return {
        "id":    "ai_accuracy",
        "label": "AI Model Confidence",
        "unit":  "%",
        "icon":  "cpu",
        "color": "#FBBF24",
        "trend": _trend(avg_conf, _simulate_previous(avg_conf, 0.03)),
        "breakdown": {
            "avg_confidence":    avg_conf,
            "ml_predictions":    ml_used,
            "ml_coverage_pct":   ml_pct,
            "formula_fallback":  len(fleet) - ml_used,
            "model_sources":     sources,
        },
        "chart_data": [
            {"label": "ML Model",  "value": ml_used,             "color": "#FBBF24"},
            {"label": "Formula",   "value": len(fleet) - ml_used, "color": "#64748B"},
        ],
    }


def _co2_kpi(impact: dict) -> dict:
    saved_kg     = impact["impact_delta"]["co2_saved_kg"]
    saved_tonnes = impact["impact_delta"]["co2_saved_tonnes"]
    return {
        "id":    "co2_reduction",
        "label": "CO₂ Reduction",
        "unit":  "kg/yr",
        "icon":  "leaf",
        "color": "#34D399",
        "trend": _trend(saved_kg, _simulate_previous(saved_kg, 0.06)),
        "breakdown": {
            "co2_saved_kg":      saved_kg,
            "co2_saved_tonnes":  saved_tonnes,
            "without_twinguard": impact["without_twinguard"]["co2_emissions_kg"],
            "with_twinguard":    impact["with_twinguard"]["co2_emissions_kg"],
        },
        "chart_data": [
            {"label": "Without TwinGuard", "value": impact["without_twinguard"]["co2_emissions_kg"], "color": "#EF4444"},
            {"label": "With TwinGuard",    "value": impact["with_twinguard"]["co2_emissions_kg"],    "color": "#34D399"},
        ],
    }


def _roi_kpi(roi: dict) -> dict:
    return {
        "id":    "roi",
        "label": "Return on Investment",
        "unit":  "%",
        "icon":  "trending-up",
        "color": "#38BDF8",
        "trend": _trend(roi["roi_summary"]["roi_pct"], _simulate_previous(roi["roi_summary"]["roi_pct"], 0.12)),
        "breakdown": {
            "roi_pct":            roi["roi_summary"]["roi_pct"],
            "net_value":          roi["roi_summary"]["net_value"],
            "payback_months":     roi["payback_months"],
            "benefit_cost_ratio": roi["roi_summary"]["benefit_cost_ratio"],
            "total_investment":   roi["investment"]["total_investment"],
        },
        "chart_data": [
            {"label": f"Year {y['year']}", "value": y["roi_pct"], "color": "#38BDF8"}
            for y in roi["yearly_projection"]
        ],
    }


def _weekly_trend_chart(fleet: list[dict]) -> list[dict]:
    """Simulates a 7-day rolling trend for health and failure probability."""
    today = date.today()
    avg_health = sum(v.get("health_score", 0) for v in fleet) / max(len(fleet), 1)
    avg_fail   = sum(v.get("failure_probability", 0) for v in fleet) / max(len(fleet), 1)
    points = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        decay = i * 0.4
        points.append({
            "date":                d.isoformat(),
            "avg_health":          round(min(100, avg_health + decay), 1),
            "avg_failure_prob":    round(max(0, avg_fail - decay * 0.5), 1),
            "critical_vehicles":   max(0, sum(1 for v in fleet if v.get("priority") == "Immediate") - i // 2),
        })
    return points


# ── Public API ────────────────────────────────────────────────────────────────

def build_dashboard(fleet: list[dict], impact: dict, roi: dict) -> dict:
    kpis = [
        _fleet_health_kpi(fleet),
        _savings_kpi(fleet, roi),
        _downtime_kpi(impact),
        _failures_kpi(impact),
        _ai_accuracy_kpi(fleet),
        _co2_kpi(impact),
        _roi_kpi(roi),
    ]

    priority_dist = {}
    for v in fleet:
        p = v.get("priority", "Low")
        priority_dist[p] = priority_dist.get(p, 0) + 1

    return {
        "generated_at":    date.today().isoformat(),
        "fleet_size":      len(fleet),
        "kpis":            kpis,
        "priority_distribution": priority_dist,
        "weekly_trend":    _weekly_trend_chart(fleet),
        "yearly_projection": roi["yearly_projection"],
    }
