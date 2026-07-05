"""
Calendar Engine
===============
Generates a FullCalendar-compatible maintenance schedule from enriched
vehicle data (Health, Failure Probability, RUL, Fleet Priority, Cost).

Each event follows the FullCalendar EventObject shape:
  {
    id, title, start, end, allDay,
    backgroundColor, borderColor, textColor,
    extendedProps: { ...all domain fields }
  }

Also returns an `ai_summary` block and per-day `downtime_map` for
business-impact overlays.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from services.repair_templates import get_template
from services.technician_assignment_service import TECHNICIANS as _TECH_LIST

# ── Priority config ───────────────────────────────────────────────────────────
_PRIORITY_COLOR = {
    "Critical": {"bg": "#EF4444", "border": "#DC2626", "text": "#FFF"},
    "High":     {"bg": "#F97316", "border": "#EA580C", "text": "#FFF"},
    "Medium":   {"bg": "#FBBF24", "border": "#D97706", "text": "#000"},
    "Routine":  {"bg": "#34D399", "border": "#059669", "text": "#000"},
}

# Days-out from today for each urgency band
_SCHEDULE_OFFSET = {
    "Critical": 0,
    "High":     1,
    "Medium":   3,
    "Routine":  7,
}

# Slot times spread across the working day
_SLOTS = ["08:00", "09:30", "11:00", "13:00", "14:30", "16:00", "17:30"]


# ── Urgency scoring ───────────────────────────────────────────────────────────

def _urgency(v: dict) -> float:
    fail   = v.get("failure_probability", 0)
    health = v.get("health_score", 100)
    rul    = v.get("remaining_useful_life_days", 60)
    prio   = {"Immediate": 100, "High": 70, "Medium": 40, "Low": 10}.get(
        v.get("priority", "Low"), 10
    )
    rul_risk = max(0, 100 - rul * 2)
    return round(
        fail    * 0.40 +
        (100 - health) * 0.30 +
        prio    * 0.20 +
        rul_risk * 0.10,
        2,
    )


def _priority_label(urgency: float) -> str:
    if urgency >= 90: return "Critical"
    if urgency >= 70: return "High"
    if urgency >= 50: return "Medium"
    return "Routine"


def _business_impact(v: dict, duration_hours: int) -> dict:
    repair_cost  = v.get("repair_now_cost", 500)
    failure_cost = v.get("failure_cost", 2000)
    savings      = v.get("potential_savings", failure_cost - repair_cost)
    downtime_hrs = duration_hours
    revenue_risk = round(failure_cost * 0.15)          # 15% revenue exposure
    return {
        "repair_cost":       repair_cost,
        "failure_cost":      failure_cost,
        "potential_savings": savings,
        "downtime_hours":    downtime_hrs,
        "revenue_at_risk":   revenue_risk,
        "roi":               round((savings / max(repair_cost, 1)) * 100, 1),
    }


# ── FullCalendar event builder ────────────────────────────────────────────────

def _fc_event(
    vehicle: dict,
    urgency: float,
    priority: str,
    sched_date: date,
    time_str: str,
    template: dict,
    technician: str,
    technician_id: int,
    slot_index: int,
) -> dict:
    vid          = vehicle["vehicle_id"]
    duration_h   = template["duration"]
    start_dt     = datetime.fromisoformat(f"{sched_date.isoformat()}T{time_str}:00")
    end_dt       = start_dt + timedelta(hours=duration_h)
    colors       = _PRIORITY_COLOR[priority]
    event_id     = f"maint-{vid}-{sched_date.isoformat()}"

    return {
        # ── FullCalendar core fields ──────────────────────────────────────
        "id":              event_id,
        "title":           f"V{vid} — {template['label']}",
        "start":           start_dt.isoformat(),
        "end":             end_dt.isoformat(),
        "allDay":          False,
        "backgroundColor": colors["bg"],
        "borderColor":     colors["border"],
        "textColor":       colors["text"],
        # ── Extended props (accessible via event.extendedProps) ───────────
        "extendedProps": {
            "vehicle_id":       vid,
            "date":             sched_date.isoformat(),
            "time":             time_str,
            "task":             template["label"],
            "duration":         f"{duration_h} hr{'s' if duration_h > 1 else ''}",
            "duration_hours":   duration_h,
            "priority":         priority,
            "priority_color":   colors["bg"],
            "urgency_score":    urgency,
            "technician":       technician,
            "technician_id":    technician_id,
            "estimated_cost":   vehicle.get("repair_now_cost", 500),
            "health_score":     vehicle.get("health_score", 0),
            "failure_risk":     vehicle.get("failure_probability", 0),
            "rul_days":         vehicle.get("remaining_useful_life_days", 0),
            "root_causes":      vehicle.get("root_cause", []),
            "recommendation":   vehicle.get("maintenance_recommendation", "Inspect"),
            "reasoning":        vehicle.get("reasoning", [])[:3],
            "status":           vehicle.get("status", "Unknown"),
            "skill_required":   template["skill"],
            "parts":            template["parts"],
            "checklist":        template["checklist"],
            "business_impact":  _business_impact(vehicle, duration_h),
            "slot_index":       slot_index,
            # Drag-and-drop reschedule support
            "editable":         True,
            "original_start":   start_dt.isoformat(),
        },
    }


# ── Public API ────────────────────────────────────────────────────────────────

def generate_schedule(vehicles: list[dict]) -> dict:
    """
    Build the full maintenance schedule from enriched vehicle list.

    Returns
    -------
    {
        events:       [ FullCalendar EventObject, ... ],
        ai_summary:   { ... },
        downtime_map: { "YYYY-MM-DD": total_hours, ... },
        risk_map:     { "YYYY-MM-DD": "Critical"|"High"|"Medium"|"Routine" },
    }
    """
    today = date.today()

    # Score and sort highest urgency first
    scored = sorted(
        [(_urgency(v), v) for v in vehicles],
        key=lambda x: x[0],
        reverse=True,
    )

    # Track slots per day to avoid collisions
    day_slots:    dict[str, int]  = {}
    day_downtime: dict[str, float] = {}
    day_risk:     dict[str, str]  = {}
    events: list[dict] = []

    for idx, (urgency, v) in enumerate(scored):
        priority     = _priority_label(urgency)
        template     = get_template(v.get("root_cause", []))
        offset_days  = _SCHEDULE_OFFSET[priority]
        sched_date   = today + timedelta(days=offset_days)
        date_str     = sched_date.isoformat()

        slot_count   = day_slots.get(date_str, 0)
        time_str     = _SLOTS[slot_count % len(_SLOTS)]
        day_slots[date_str] = slot_count + 1

        # Round-robin technician assignment (scheduler.py does the smart version)
        tech         = _TECH_LIST[idx % len(_TECH_LIST)]
        technician   = tech["name"]
        tech_id      = tech["id"]

        event = _fc_event(v, urgency, priority, sched_date, time_str, template, technician, tech_id, slot_count)
        events.append(event)

        # Accumulate downtime and worst risk per day
        day_downtime[date_str] = day_downtime.get(date_str, 0) + template["duration"]
        existing_risk = day_risk.get(date_str, "Routine")
        risk_order    = ["Routine", "Medium", "High", "Critical"]
        if risk_order.index(priority) > risk_order.index(existing_risk):
            day_risk[date_str] = priority

    # ── AI summary ────────────────────────────────────────────────────────────
    critical_n  = sum(1 for e in events if e["extendedProps"]["priority"] == "Critical")
    high_n      = sum(1 for e in events if e["extendedProps"]["priority"] == "High")
    this_week_n = sum(
        1 for e in events
        if (date.fromisoformat(e["extendedProps"]["date"]) - today).days <= 7
    )
    total_cost  = sum(e["extendedProps"]["estimated_cost"] for e in events)
    total_save  = sum(e["extendedProps"]["business_impact"]["potential_savings"] for e in events)
    downtime_h  = sum(
        e["extendedProps"]["duration_hours"] for e in events
        if e["extendedProps"]["priority"] in ("Critical", "High")
    )

    ai_summary = {
        "this_week_count":     this_week_n,
        "critical_count":      critical_n,
        "high_count":          high_n,
        "total_events":        len(events),
        "total_cost_estimate": total_cost,
        "expected_savings":    total_save,
        "downtime_prevented":  downtime_h,
        "insight": (
            f"{critical_n} vehicle(s) require immediate attention. "
            f"{this_week_n} jobs scheduled this week. "
            f"Estimated savings: ₹{total_save:,}."
        ),
    }

    return {
        "events":       events,
        "ai_summary":   ai_summary,
        "downtime_map": {k: round(v, 1) for k, v in day_downtime.items()},
        "risk_map":     day_risk,
    }
