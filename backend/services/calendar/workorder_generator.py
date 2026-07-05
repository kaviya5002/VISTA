"""
Work Order Generator
====================
Generates complete work orders enriched with calendar scheduling context.
Extends the base work_order_service with:
  - Scheduled date/time from the calendar engine
  - Technician assigned via the smart scheduler (skill + capacity)
  - Full parts list, tools, checklist, and step-by-step instructions
  - Business impact (repair cost, failure cost, savings, ROI)
  - FullCalendar-compatible event reference
"""
from __future__ import annotations

from datetime import date, datetime

from services.repair_templates import get_template
from services.technician_assignment_service import assign_technician

# ── Vehicle model lookup ──────────────────────────────────────────────────────
_MODELS = {
    range(1,  21): "Tata Ace EV",
    range(21, 41): "Tata Nexon EV",
    range(41, 61): "Tata Tigor EV",
    range(61, 81): "Tata Tiago EV",
    range(81, 101): "Tata Punch EV",
}


def _model(vid: int) -> str:
    for r, name in _MODELS.items():
        if vid in r:
            return name
    return "Tata EV"


def _priority_label(v: dict) -> str:
    p    = v.get("priority", "Low")
    fail = v.get("failure_probability", 0)
    h    = v.get("health_score", 100)
    if p == "Immediate" or fail > 85 or h < 30: return "Critical"
    if p == "High"      or fail > 60 or h < 50: return "High"
    if p == "Medium"    or fail > 35 or h < 70: return "Medium"
    return "Routine"


def _ai_summary(v: dict, template: dict) -> str:
    fail  = v.get("failure_probability", 0)
    h     = v.get("health_score", 100)
    rul   = v.get("remaining_useful_life_days", 60)
    cause = (v.get("root_cause") or ["component degradation"])[0]
    delay = min(99, fail + 14)
    return (
        f"AI analysis detects {cause.lower()} with {fail}% failure probability "
        f"and health score {h}%. Immediate {template['label'].lower()} recommended. "
        f"Delaying repair may increase failure probability to {delay}% within 7 days. "
        f"Estimated downtime: {template['duration']} hr(s). RUL: {rul} day(s)."
    )


def _business_impact(v: dict, duration_h: int) -> dict:
    repair  = v.get("repair_now_cost", 500)
    failure = v.get("failure_cost", 2000)
    savings = v.get("potential_savings", failure - repair)
    return {
        "repair_cost":       repair,
        "failure_cost":      failure,
        "potential_savings": savings,
        "downtime_hours":    duration_h,
        "revenue_at_risk":   round(failure * 0.15),
        "roi":               round((savings / max(repair, 1)) * 100, 1),
    }


# ── Public API ────────────────────────────────────────────────────────────────

def generate_work_order(
    vehicle: dict,
    scheduled_date: str | None = None,
    scheduled_time: str | None = None,
) -> dict:
    """
    Generate a complete work order for a vehicle.

    Parameters
    ----------
    vehicle        : enriched vehicle dict (post ML pipeline)
    scheduled_date : ISO date from calendar engine; defaults to today
    scheduled_time : "HH:MM" from scheduler; defaults to "08:00"
    """
    vid        = vehicle["vehicle_id"]
    root       = vehicle.get("root_cause", [])
    template   = get_template(root)
    priority   = _priority_label(vehicle)
    today      = scheduled_date or date.today().isoformat()
    time_str   = scheduled_time or "08:00"
    wo_id      = f"WO-{datetime.now().strftime('%Y%m%d')}-{vid:04d}"

    assignment = assign_technician(vehicle)
    tech       = assignment["technician"]
    duration_h = template["duration"]

    # Compute end time
    h, m   = map(int, time_str.split(":"))
    end_h  = h + duration_h
    end_str = f"{end_h:02d}:{m:02d}" if end_h < 24 else "Next Day"

    return {
        # ── Identity ──────────────────────────────────────────────────────
        "work_order_id":    wo_id,
        "generated_at":     datetime.now().isoformat(timespec="seconds"),
        "vehicle_id":       vid,
        "vehicle_model":    _model(vid),
        "priority":         priority,
        "status":           "Scheduled",
        # ── Schedule ──────────────────────────────────────────────────────
        "scheduled_date":   today,
        "scheduled_time":   time_str,
        "estimated_start":  f"{today}T{time_str}:00",
        "estimated_end":    f"{today}T{end_str}:00" if end_h < 24 else f"{today}T23:59:00",
        "duration":         f"{duration_h} hr{'s' if duration_h > 1 else ''}",
        "duration_hours":   duration_h,
        # ── Repair details ────────────────────────────────────────────────
        "task":             template["label"],
        "skill_required":   template["skill"],
        "parts":            template["parts"],
        "tools":            template["tools"],
        "checklist":        template["checklist"],
        "instructions":     template["instructions"],
        # ── Technician ────────────────────────────────────────────────────
        "technician":           tech,
        "technician_id":        assignment["technician_id"],
        "technician_skills":    assignment["technician_skills"],
        "technician_rating":    assignment["technician_rating"],
        "technician_exp":       assignment["technician_exp"],
        "technician_shift":     assignment["technician_shift"],
        "technician_phone":     assignment["technician_phone"],
        "assignment_score":     assignment["score"],
        "assignment_reasons":   assignment["reasons"],
        "alternatives":         assignment["alternatives"],
        # ── Diagnostics ───────────────────────────────────────────────────
        "health_score":     vehicle.get("health_score", 0),
        "failure_risk":     vehicle.get("failure_probability", 0),
        "rul_days":         vehicle.get("remaining_useful_life_days", 0),
        "root_causes":      root,
        "estimated_risk":   vehicle.get("estimated_risk", "Unknown"),
        "confidence_score": vehicle.get("confidence_score", 0),
        # ── Financials ────────────────────────────────────────────────────
        "business_impact":  _business_impact(vehicle, duration_h),
        # ── AI narrative ──────────────────────────────────────────────────
        "ai_summary":       _ai_summary(vehicle, template),
        "reasoning":        vehicle.get("reasoning", []),
        # ── FullCalendar event reference ──────────────────────────────────
        "calendar_event_id": f"maint-{vid}-{today}",
        # ── QR payload ────────────────────────────────────────────────────
        "qr_data":          f"twinguard://vehicle/{vid}/workorder/{wo_id}",
    }


def generate_fleet_work_orders(vehicles: list[dict], schedule: list[dict]) -> list[dict]:
    """
    Batch-generate work orders for all vehicles, injecting scheduled
    date/time from the calendar schedule entries.

    Parameters
    ----------
    vehicles : enriched vehicle list
    schedule : list of ScheduleEntry dicts from scheduler.build_optimised_schedule
    """
    sched_map = {s["vehicle_id"]: s for s in schedule}
    orders = []
    for v in vehicles:
        entry = sched_map.get(v["vehicle_id"], {})
        orders.append(generate_work_order(
            v,
            scheduled_date=entry.get("date"),
            scheduled_time=entry.get("time"),
        ))
    return orders
