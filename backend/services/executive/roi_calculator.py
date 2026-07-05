"""
ROI Calculator — estimates financial return from TwinGuard deployment.
Accounts for maintenance savings, downtime reduction, and avoided failures.
"""
from __future__ import annotations

# TwinGuard platform cost model (annual, per-vehicle licensing + infra)
_PLATFORM_COST = {
    "per_vehicle_annual":  1200,   # ₹/vehicle/year SaaS licence
    "implementation_once": 150000, # one-time setup & integration
    "training_once":       25000,  # one-time staff training
}

# Downtime cost assumptions
_DOWNTIME_COST_PER_HOUR = 3500   # ₹ revenue/productivity lost per vehicle per hour


def calculate_roi(fleet: list[dict], impact: dict, years: int = 3) -> dict:
    n = len(fleet)

    # ── Annual platform cost ──────────────────────────────────────────────────
    annual_licence   = n * _PLATFORM_COST["per_vehicle_annual"]
    one_time_cost    = _PLATFORM_COST["implementation_once"] + _PLATFORM_COST["training_once"]
    total_investment = one_time_cost + annual_licence * years

    # ── Annual benefits ───────────────────────────────────────────────────────
    delta = impact["impact_delta"]
    annual_repair_savings    = impact["without_twinguard"]["repair_cost"] - impact["with_twinguard"]["repair_cost"]
    annual_pm_savings        = impact["without_twinguard"]["planned_maintenance_cost"] - impact["with_twinguard"]["planned_maintenance_cost"]
    annual_downtime_savings  = delta["downtime_hours_saved"] * _DOWNTIME_COST_PER_HOUR
    annual_total_benefit     = annual_repair_savings + annual_pm_savings + annual_downtime_savings

    # ── Live fleet predicted savings (immediate horizon) ─────────────────────
    live_savings = sum(v.get("potential_savings", 0) for v in fleet)

    # ── Multi-year projection ─────────────────────────────────────────────────
    yearly = []
    cumulative_benefit = 0.0
    cumulative_cost    = one_time_cost
    payback_month      = None

    for yr in range(1, years + 1):
        cumulative_benefit += annual_total_benefit
        cumulative_cost    += annual_licence
        net = cumulative_benefit - cumulative_cost
        roi_pct = round((net / max(cumulative_cost, 1)) * 100, 1)

        # Estimate payback month (first year only)
        if payback_month is None and net > 0:
            monthly_benefit = annual_total_benefit / 12
            months_to_break = (cumulative_cost - (cumulative_benefit - annual_total_benefit)) / max(monthly_benefit, 1)
            payback_month   = round((yr - 1) * 12 + months_to_break)

        yearly.append({
            "year":               yr,
            "annual_benefit":     round(annual_total_benefit),
            "annual_cost":        round(annual_licence),
            "cumulative_benefit": round(cumulative_benefit),
            "cumulative_cost":    round(cumulative_cost),
            "net_value":          round(net),
            "roi_pct":            roi_pct,
        })

    final_net = yearly[-1]["net_value"]
    final_roi = yearly[-1]["roi_pct"]

    return {
        "fleet_size":             n,
        "projection_years":       years,
        "investment": {
            "one_time_cost":      one_time_cost,
            "annual_licence":     annual_licence,
            "total_investment":   round(total_investment),
        },
        "annual_benefits": {
            "repair_savings":     round(annual_repair_savings),
            "pm_savings":         round(annual_pm_savings),
            "downtime_savings":   round(annual_downtime_savings),
            "total_benefit":      round(annual_total_benefit),
        },
        "live_predicted_savings": live_savings,
        "payback_months":         payback_month,
        "roi_summary": {
            "net_value":          final_net,
            "roi_pct":            final_roi,
            "benefit_cost_ratio": round(annual_total_benefit / max(annual_licence, 1), 2),
        },
        "yearly_projection":      yearly,
    }
