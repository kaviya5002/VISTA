from datetime import date, timedelta

# ── Lookup tables ─────────────────────────────────────────────────────────────

DURATION_MAP = {
    "Battery Degradation":    2,
    "Low Battery Voltage":    2,
    "Battery Below Optimal":  1,
    "Thermal Stress":         3,
    "Cooling System Stress":  3,
    "Elevated Temperature":   2,
    "Engine Stress":          5,
    "High RPM":               2,
    "Transmission Wear":      6,
    "Brake Wear":             2,
}

TASK_MAP = {
    "Battery Degradation":    "Battery Replacement",
    "Low Battery Voltage":    "Battery Replacement",
    "Battery Below Optimal":  "Battery Check",
    "Thermal Stress":         "Cooling System Overhaul",
    "Cooling System Stress":  "Cooling System Service",
    "Elevated Temperature":   "Thermal Inspection",
    "Engine Stress":          "Engine Overhaul",
    "High RPM":               "Engine Inspection",
    "Transmission Wear":      "Transmission Service",
    "Brake Wear":             "Brake Replacement",
}

TECHNICIANS = [
    "Ravi Kumar", "Akash Singh", "Priya Nair",
    "Suresh Patel", "Meena Sharma", "Arjun Das",
    "Kavitha Rao", "Deepak Verma",
]

PRIORITY_COLOR = {
    "Critical": "#EF4444",
    "High":     "#F97316",
    "Medium":   "#FBBF24",
    "Routine":  "#34D399",
}


# ── Core logic ────────────────────────────────────────────────────────────────

def _urgency_score(vehicle: dict) -> float:
    fail_prob = vehicle.get("failure_probability", 0)
    health    = vehicle.get("health_score", 100)
    rul       = vehicle.get("remaining_useful_life_days", 60)
    priority  = vehicle.get("priority", "Low")

    priority_score = {"Immediate": 100, "High": 70, "Medium": 40, "Low": 10}.get(priority, 10)
    rul_risk       = max(0, 100 - rul * 2)          # 0 RUL → 100 risk, 50 days → 0

    return (
        fail_prob    * 0.40 +
        (100 - health) * 0.30 +
        priority_score * 0.20 +
        rul_risk       * 0.10
    )


def _assign_date(urgency: float, base: date) -> date:
    if urgency >= 90:
        return base
    elif urgency >= 80:
        return base + timedelta(days=1)
    elif urgency >= 70:
        return base + timedelta(days=3)
    elif urgency >= 60:
        return base + timedelta(days=7)
    else:
        return base + timedelta(days=14)


def _priority_label(urgency: float) -> str:
    if urgency >= 90:
        return "Critical"
    elif urgency >= 70:
        return "High"
    elif urgency >= 50:
        return "Medium"
    return "Routine"


def _pick_task_and_duration(root_causes: list) -> tuple[str, int]:
    for cause in root_causes:
        if cause in TASK_MAP:
            return TASK_MAP[cause], DURATION_MAP.get(cause, 2)
    return "Routine Inspection", 1


def _assign_time(slot_index: int) -> str:
    """Spread jobs across the day: 08:00, 10:00, 13:00, 15:00, 17:00 …"""
    slots = ["08:00", "10:00", "13:00", "15:00", "17:00"]
    return slots[slot_index % len(slots)]


# ── Public API ────────────────────────────────────────────────────────────────

def generate_calendar(vehicles: list) -> dict:
    today = date.today()

    # Score and sort
    scored = []
    for v in vehicles:
        urgency = _urgency_score(v)
        scored.append((urgency, v))
    scored.sort(key=lambda x: x[0], reverse=True)

    # Track slots per day to spread time assignments
    day_slots: dict[str, int] = {}

    events = []
    for idx, (urgency, v) in enumerate(scored):
        root_causes = v.get("root_cause", [])
        task, duration = _pick_task_and_duration(root_causes)
        sched_date    = _assign_date(urgency, today)
        priority      = _priority_label(urgency)
        date_str      = sched_date.isoformat()

        slot_count    = day_slots.get(date_str, 0)
        time_str      = _assign_time(slot_count)
        day_slots[date_str] = slot_count + 1

        technician = TECHNICIANS[idx % len(TECHNICIANS)]

        events.append({
            "vehicle_id":      v["vehicle_id"],
            "date":            date_str,
            "time":            time_str,
            "task":            task,
            "duration":        f"{duration} hr{'s' if duration > 1 else ''}",
            "duration_hours":  duration,
            "priority":        priority,
            "priority_color":  PRIORITY_COLOR[priority],
            "urgency_score":   round(urgency, 1),
            "technician":      technician,
            "estimated_cost":  v.get("repair_now_cost", 500),
            "health_score":    v.get("health_score", 0),
            "failure_risk":    v.get("failure_probability", 0),
            "rul_days":        v.get("remaining_useful_life_days", 0),
            "root_causes":     root_causes,
            "recommendation":  v.get("maintenance_recommendation", "Inspect"),
            "reasoning":       v.get("reasoning", [])[:2],
            "status":          v.get("status", "Unknown"),
        })

    # ── AI summary ────────────────────────────────────────────────────────────
    critical_count = sum(1 for e in events if e["priority"] == "Critical")
    high_count     = sum(1 for e in events if e["priority"] == "High")
    this_week      = sum(1 for e in events if (date.fromisoformat(e["date"]) - today).days <= 7)
    total_cost     = sum(e["estimated_cost"] for e in events)
    total_savings  = sum(v.get("potential_savings", 0) for v in vehicles)
    downtime_hrs   = sum(e["duration_hours"] for e in events if e["priority"] in ("Critical", "High"))

    ai_summary = {
        "this_week_count":    this_week,
        "critical_count":     critical_count,
        "high_count":         high_count,
        "total_events":       len(events),
        "total_cost_estimate": total_cost,
        "expected_savings":   total_savings,
        "downtime_prevented": downtime_hrs,
        "insight": (
            f"{critical_count} vehicle(s) require immediate attention today. "
            f"{this_week} maintenance jobs scheduled this week. "
            f"Estimated savings: ₹{total_savings:,}."
        ),
    }

    return {"events": events, "ai_summary": ai_summary}
