"""
Assignment Engine
=================
Orchestrates the full technician assignment pipeline:

  1. Load technicians from repository (DB-backed)
  2. Rank by skill match (skill_matcher)
  3. Apply workload / capacity constraints (workload_optimizer)
  4. Select best technician and slot
  5. Return enriched assignment with calendar event reference and work order link

Single assignment  → assign_to_vehicle(vehicle, date_hint)
Fleet assignment   → assign_fleet(vehicles)
Reassignment       → reassign(vehicle_id, new_tech_id, new_date)
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from services.technician.technician_repository import (
    get_all, get_by_id, update_workload, workforce_summary,
)
from services.technician.skill_matcher import (
    rank_technicians, skill_gap, classify_repair, required_skill,
)
from services.technician.workload_optimizer import (
    WorkloadState, find_earliest_slot, rebalance_recommendations,
)
from services.repair_templates import get_template

# ── Priority → urgency offset (days) ─────────────────────────────────────────
_PRIORITY_OFFSET = {"Critical": 0, "High": 1, "Medium": 3, "Routine": 7}
_PRIORITY_ORDER  = {"Critical": 0, "High": 1, "Medium": 2, "Routine": 3}


def _priority_label(v: dict) -> str:
    p    = v.get("priority", "Low")
    fail = v.get("failure_probability", 0)
    h    = v.get("health_score", 100)
    if p == "Immediate" or fail > 85 or h < 30: return "Critical"
    if p == "High"      or fail > 60 or h < 50: return "High"
    if p == "Medium"    or fail > 35 or h < 70: return "Medium"
    return "Routine"


def _end_time(time_str: str, duration_h: int) -> str:
    h, m  = map(int, time_str.split(":"))
    end_h = h + duration_h
    return f"{end_h:02d}:{m:02d}" if end_h < 24 else "Next Day"


def _build_reasons(tech: dict, gap: dict, priority: str) -> list[str]:
    reasons = []
    if gap["match_score"] >= 80:
        reasons.append(f"{gap['required_skill']} specialist — direct skill match")
    if tech.get("rating", 0) >= 4.9:
        reasons.append(f"Top-rated technician ({tech['rating']}★)")
    elif tech.get("rating", 0) >= 4.7:
        reasons.append(f"Highly rated ({tech['rating']}★)")
    if tech.get("available"):
        reasons.append("Currently available")
    elif priority == "Critical":
        reasons.append("Assigned despite workload — Critical priority override")
    if tech.get("workload", 0) == 0:
        reasons.append("No active jobs — immediate availability")
    if tech.get("experience", 0) >= 8:
        reasons.append(f"{tech['experience']} years experience")
    return reasons[:4]


# ── Single vehicle assignment ─────────────────────────────────────────────────

def assign_to_vehicle(
    vehicle: dict,
    date_hint: date | None = None,
    state: WorkloadState | None = None,
) -> dict:
    """
    Assign the best available technician to a vehicle's maintenance task.

    Parameters
    ----------
    vehicle   : enriched vehicle dict
    date_hint : preferred start date (defaults to today + priority offset)
    state     : shared WorkloadState for fleet-level sessions (mutated in place)

    Returns
    -------
    Full assignment dict including technician details, slot, skill gap,
    calendar event reference, and work order link.
    """
    root_causes = vehicle.get("root_cause", [])
    template    = get_template(root_causes)
    task        = template["label"]
    duration_h  = template["duration"]
    priority    = _priority_label(vehicle)
    vid         = vehicle["vehicle_id"]

    # Repair classification
    repair_class = classify_repair(root_causes)

    # Load and rank technicians
    all_techs = get_all()
    ranked    = rank_technicians(all_techs, root_causes, task, priority)

    # Apply workload constraints
    own_state = state is None
    if own_state:
        state = WorkloadState()

    base_date = date_hint or (date.today() + timedelta(days=_PRIORITY_OFFSET[priority]))

    # Walk ranked list to find first technician with capacity
    chosen_tech = None
    chosen_date = None
    chosen_time = None
    chosen_gap  = None

    for tech in ranked:
        tid = tech["id"]
        # Critical jobs can override availability flag
        if not tech["available"] and priority != "Critical":
            continue
        d, t = find_earliest_slot(state, tid, base_date, priority)
        chosen_tech = tech
        chosen_date = d
        chosen_time = t
        chosen_gap  = tech["skill_gap"]
        break

    # Absolute fallback: highest-ranked regardless of availability
    if not chosen_tech:
        chosen_tech = ranked[0]
        chosen_date = base_date.isoformat()
        chosen_time = "08:00"
        chosen_gap  = chosen_tech["skill_gap"]

    # Commit to state
    state.assign(chosen_tech["id"], chosen_date)

    # Persist workload increment to DB only for single-vehicle calls
    if own_state:
        update_workload(chosen_tech["id"], +1)

    end_time = _end_time(chosen_time, duration_h)
    reasons  = _build_reasons(chosen_tech, chosen_gap, priority)

    # Alternatives (next 3 ranked, excluding chosen)
    alternatives = [
        {
            "technician_id": t["id"],
            "name":          t["name"],
            "skill_match":   t["skill_match"],
            "skills":        t["skills"][:2],
            "available":     t["available"],
            "rating":        t["rating"],
        }
        for t in ranked
        if t["id"] != chosen_tech["id"]
    ][:3]

    return {
        # ── Identity ──────────────────────────────────────────────────────
        "vehicle_id":        vid,
        "task":              task,
        "priority":          priority,
        "repair_category":   repair_class["category"],
        "repair_complexity": repair_class["complexity"],
        # ── Technician ────────────────────────────────────────────────────
        "technician_id":     chosen_tech["id"],
        "technician":        chosen_tech["name"],
        "technician_skills": chosen_tech["skills"],
        "technician_rating": chosen_tech["rating"],
        "technician_exp":    chosen_tech["experience"],
        "technician_shift":  chosen_tech["shift"],
        "technician_phone":  chosen_tech.get("phone", ""),
        "technician_avatar": chosen_tech.get("avatar", ""),
        # ── Scoring ───────────────────────────────────────────────────────
        "assignment_score":  round(chosen_tech["skill_match"], 1),
        "skill_gap":         chosen_gap,
        "reasons":           reasons,
        "alternatives":      alternatives,
        # ── Schedule ──────────────────────────────────────────────────────
        "scheduled_date":    chosen_date,
        "scheduled_time":    chosen_time,
        "estimated_end":     end_time,
        "duration_hours":    duration_h,
        # ── Integration refs ──────────────────────────────────────────────
        "calendar_event_id": f"maint-{vid}-{chosen_date}",
        "work_order_link":   f"/calendar/workorder/{vid}",
        "assigned_at":       datetime.utcnow().isoformat(),
    }


# ── Fleet assignment ──────────────────────────────────────────────────────────

def assign_fleet(vehicles: list[dict]) -> dict:
    """
    Assign technicians to all vehicles in priority order, sharing a single
    WorkloadState so capacity is respected across the whole fleet.

    Returns
    -------
    {
        assignments: [ assignment_dict, ... ],
        summary:     workforce_summary,
        rebalance:   [ recommendation, ... ],
        load_forecast: [ { date, total_jobs, total_capacity }, ... ],
    }
    """
    # Sort vehicles: Critical first
    def _urgency(v: dict) -> float:
        return (
            v.get("failure_probability", 0) * 0.5 +
            (100 - v.get("health_score", 100)) * 0.5
        )

    sorted_vehicles = sorted(vehicles, key=_urgency, reverse=True)

    state       = WorkloadState()
    assignments = []

    for v in sorted_vehicles:
        priority  = _priority_label(v)
        base_date = date.today() + timedelta(days=_PRIORITY_OFFSET[priority])
        a = assign_to_vehicle(v, date_hint=base_date, state=state)
        assignments.append(a)

    # Rebalance check for today
    today_str = date.today().isoformat()
    rebalance = rebalance_recommendations(state, today_str)

    ws = workforce_summary()
    # Compute avg repair hours from assignments
    avg_h = round(sum(a["duration_hours"] for a in assignments) / max(len(assignments), 1), 1)
    # Completion pct: assignments covered vs total vehicles
    completion = round((len(assignments) / max(len(sorted_vehicles), 1)) * 100, 1)

    # Normalise assignment keys to match frontend expectations
    for a in assignments:
        a["score"]            = a.pop("assignment_score", 0)
        a["estimated_start"]  = a.pop("scheduled_time", "08:00")
        a["estimated_finish"] = a.pop("estimated_end", "")

    return {
        "assignments": assignments,
        "summary": {
            "total_technicians": ws["total"],
            "available":         ws["available"],
            "working":           ws["working"],
            "off_duty":          ws["off_duty"],
            "total_assignments": len(assignments),
            "avg_repair_hours":  avg_h,
            "completion_pct":    completion,
        },
        "rebalance":     rebalance,
        "load_forecast": state.fleet_load_forecast(days=7),
    }


# ── Reassignment ──────────────────────────────────────────────────────────────

def reassign(
    vehicle: dict,
    new_tech_id: int,
    new_date: str,
    new_time: str | None = None,
    old_tech_id: int | None = None,
) -> dict:
    """
    Reassign a vehicle's maintenance task to a specific technician and date.
    Releases the old technician's workload slot if old_tech_id is provided.
    """
    tech = get_by_id(new_tech_id)
    if not tech:
        return {"error": f"Technician {new_tech_id} not found"}

    root_causes = vehicle.get("root_cause", [])
    template    = get_template(root_causes)
    task        = template["label"]
    duration_h  = template["duration"]
    priority    = _priority_label(vehicle)
    vid         = vehicle["vehicle_id"]

    time_str = new_time or "08:00"
    end_time = _end_time(time_str, duration_h)

    gap     = skill_gap(tech["skills"], task, root_causes)
    reasons = _build_reasons(tech, gap, priority)

    # Update DB workload
    if old_tech_id and old_tech_id != new_tech_id:
        update_workload(old_tech_id, -1)
    update_workload(new_tech_id, +1)

    return {
        "vehicle_id":        vid,
        "task":              task,
        "priority":          priority,
        "technician_id":     tech["id"],
        "technician":        tech["name"],
        "technician_skills": tech["skills"],
        "technician_rating": tech["rating"],
        "technician_exp":    tech["experience"],
        "technician_shift":  tech["shift"],
        "technician_phone":  tech.get("phone", ""),
        "assignment_score":  gap["match_score"],
        "skill_gap":         gap,
        "reasons":           reasons,
        "scheduled_date":    new_date,
        "scheduled_time":    time_str,
        "estimated_end":     end_time,
        "duration_hours":    duration_h,
        "calendar_event_id": f"maint-{vid}-{new_date}",
        "work_order_link":   f"/calendar/workorder/{vid}",
        "reassigned_at":     datetime.utcnow().isoformat(),
        "reassigned":        True,
    }
