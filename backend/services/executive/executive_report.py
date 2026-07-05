"""
Executive Report — generates structured executive summaries and business insights
suitable for C-suite reporting, board presentations, and investor briefings.
"""
from __future__ import annotations
from datetime import date


_RISK_LABEL = {
    "Immediate": "Critical",
    "High":      "High",
    "Medium":    "Medium",
    "Low":       "Low",
}


def _fleet_status_sentence(fleet: list[dict]) -> str:
    n         = len(fleet)
    critical  = sum(1 for v in fleet if v.get("priority") in ("Immediate", "High"))
    avg_h     = round(sum(v.get("health_score", 0) for v in fleet) / max(n, 1))
    avg_f     = round(sum(v.get("failure_probability", 0) for v in fleet) / max(n, 1))
    if critical == 0:
        return (f"All {n} vehicles are operating within acceptable parameters. "
                f"Average fleet health is {avg_h}% with a {avg_f}% mean failure probability.")
    return (f"Of {n} vehicles monitored, {critical} require urgent attention. "
            f"Fleet average health is {avg_h}% with a {avg_f}% mean failure probability.")


def _financial_sentence(roi: dict, impact: dict) -> str:
    savings  = roi["annual_benefits"]["total_benefit"]
    net      = roi["roi_summary"]["net_value"]
    payback  = roi["payback_months"]
    cost_pct = impact["impact_delta"]["cost_reduction_pct"]
    return (f"TwinGuard delivers ₹{savings:,} in annual benefits through repair savings, "
            f"downtime reduction, and optimised preventive maintenance — a {cost_pct}% reduction "
            f"in total maintenance spend. Net {roi['projection_years']}-year value: ₹{net:,}. "
            f"Estimated payback period: {payback} months.")


def _operational_sentence(impact: dict) -> str:
    prevented = impact["impact_delta"]["failures_prevented"]
    hours     = impact["impact_delta"]["downtime_hours_saved"]
    pct_down  = impact["impact_delta"]["downtime_reduction_pct"]
    return (f"AI-driven predictive maintenance prevents {prevented} unplanned failures annually, "
            f"saving {hours} hours of vehicle downtime — a {pct_down}% reduction versus "
            f"reactive maintenance operations.")


def _sustainability_sentence(impact: dict) -> str:
    tonnes = impact["impact_delta"]["co2_saved_tonnes"]
    kg     = impact["impact_delta"]["co2_saved_kg"]
    return (f"By reducing unplanned breakdowns and unnecessary towing events, TwinGuard eliminates "
            f"approximately {kg:,} kg ({tonnes} tonnes) of CO₂ emissions annually, "
            f"supporting fleet sustainability and ESG reporting targets.")


def _top_risks(fleet: list[dict], n: int = 5) -> list[dict]:
    urgent = sorted(
        [v for v in fleet if v.get("priority") in ("Immediate", "High")],
        key=lambda v: v.get("failure_probability", 0),
        reverse=True,
    )[:n]
    return [
        {
            "vehicle_id":          v["vehicle_id"],
            "priority":            v.get("priority"),
            "health_score":        v.get("health_score"),
            "failure_probability": v.get("failure_probability"),
            "rul_days":            v.get("remaining_useful_life_days"),
            "root_cause":          v.get("root_cause", [])[:2],
            "recommended_action":  v.get("maintenance_recommendation", "Inspect"),
            "potential_savings":   v.get("potential_savings", 0),
        }
        for v in urgent
    ]


def _strategic_recommendations(fleet: list[dict], roi: dict, impact: dict) -> list[dict]:
    recs = []
    critical_n = sum(1 for v in fleet if v.get("priority") == "Immediate")
    if critical_n > 0:
        recs.append({
            "priority": "Critical",
            "action":   f"Dispatch {critical_n} vehicle(s) for immediate repair",
            "impact":   f"Prevents ₹{critical_n * 22000:,} in potential failure costs",
            "timeline": "Within 24 hours",
        })

    high_n = sum(1 for v in fleet if v.get("priority") == "High")
    if high_n > 0:
        recs.append({
            "priority": "High",
            "action":   f"Schedule urgent maintenance for {high_n} vehicle(s)",
            "impact":   f"Reduces failure probability by up to 60% per vehicle",
            "timeline": "Within 3 days",
        })

    payback = roi["payback_months"]
    if payback and payback <= 12:
        recs.append({
            "priority": "Strategic",
            "action":   "Expand TwinGuard coverage to full fleet",
            "impact":   f"ROI payback in {payback} months; {roi['roi_summary']['roi_pct']}% 3-year ROI",
            "timeline": "Next quarter",
        })

    co2 = impact["impact_delta"]["co2_saved_tonnes"]
    recs.append({
        "priority": "Sustainability",
        "action":   "Report CO₂ reduction in ESG disclosures",
        "impact":   f"{co2} tonnes CO₂ avoided annually through predictive maintenance",
        "timeline": "Next reporting cycle",
    })

    return recs


# ── Public API ────────────────────────────────────────────────────────────────

def generate_executive_report(fleet: list[dict], impact: dict, roi: dict) -> dict:
    return {
        "report_date":   date.today().isoformat(),
        "report_title":  "TwinGuard Executive Performance Report",
        "fleet_size":    len(fleet),
        "executive_summary": {
            "fleet_status":    _fleet_status_sentence(fleet),
            "financial":       _financial_sentence(roi, impact),
            "operational":     _operational_sentence(impact),
            "sustainability":  _sustainability_sentence(impact),
        },
        "headline_metrics": {
            "avg_fleet_health":       round(sum(v.get("health_score", 0) for v in fleet) / max(len(fleet), 1), 1),
            "failures_prevented":     impact["impact_delta"]["failures_prevented"],
            "annual_cost_savings":    roi["annual_benefits"]["total_benefit"],
            "downtime_hours_saved":   impact["impact_delta"]["downtime_hours_saved"],
            "co2_saved_tonnes":       impact["impact_delta"]["co2_saved_tonnes"],
            "roi_pct":                roi["roi_summary"]["roi_pct"],
            "payback_months":         roi["payback_months"],
            "net_3yr_value":          roi["roi_summary"]["net_value"],
        },
        "top_risks":                  _top_risks(fleet),
        "strategic_recommendations":  _strategic_recommendations(fleet, roi, impact),
        "financial_detail": {
            "investment":      roi["investment"],
            "annual_benefits": roi["annual_benefits"],
            "yearly_projection": roi["yearly_projection"],
        },
        "operational_detail": {
            "without_twinguard": impact["without_twinguard"],
            "with_twinguard":    impact["with_twinguard"],
            "delta":             impact["impact_delta"],
        },
    }
