"""
Scheduler
=========
Allocates repair slots across technicians and days, optimising for:
  - Priority order (Critical first)
  - Technician skill match and capacity (max 3 jobs/day per tech)
  - Downtime spread (avoid clustering all Critical jobs on one day)
  - Business-hours slots (08:00–18:00)

Also handles POST /calendar/reschedule:
  - Accepts a drag-and-drop move (event_id, new_date, new_time)
  - Recalculates fleet risk, total downtime, and business impact delta
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import TypedDict

from services.technician_assignment_service import TECHNICIANS as _TECH_LIST, _composite_score
from services.repair_templates import get_template

# ── Constants ─────────────────────────────────────────────────────────────────
_MAX_JOBS_PER_TECH_PER_DAY = 3
_WORKING_SLOTS = ["08:00", "09:30", "11:00", "13:00", "14:30", "16:00", "17:30"]
_PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Routine": 3}
_PRIORITY_OFFSET = {"Critical": 0, "High": 1, "Medium": 3, "Routine": 7}


class ScheduleEntry(TypedDict):
    vehicle_id:    int
    event_id:      str
    priority:      str
    urgency_score: float
    date:          str
    time:          str
    end_time:      str
    duration_hours: int
    technician:    str
    technician_id: int
    task:          str
    skill_required: str


# ── Technician capacity tracker ───────────────────────────────────────────────

class _CapacityTracker:
    """Tracks how many jobs each technician has per day."""

    def __init__(self) -> None:
        # {tech_id: {date_str: job_count}}
        self._load: dict[int, dict[str, int]] = {
            t["id"]: {} for t in _TECH_LIST
        }

    def count(self, tech_id: int, date_str: str) -> int:
        return self._load[tech_id].get(date_str, 0)

    def available(self, tech_id: int, date_str: str) -> bool:
        return self.count(tech_id, date_str) < _MAX_JOBS_PER_TECH_PER_DAY

    def assign(self, tech_id: int, date_str: str) -> None:
        self._load[tech_id][date_str] = self.count(tech_id, date_str) + 1

    def daily_load(self, date_str: str) -> dict[int, int]:
        return {tid: self._load[tid].get(date_str, 0) for tid in self._load}


# ── Best technician for a job ─────────────────────────────────────────────────

def _best_tech(
    root_causes: list[str],
    task: str,
    priority: str,
    date_str: str,
    tracker: _CapacityTracker,
) -> tuple[dict, float]:
    """Return (technician_dict, score) for the best available technician."""
    candidates = []
    for tech in _TECH_LIST:
        if not tracker.available(tech["id"], date_str):
            continue
        live = {**tech, "workload": tracker.count(tech["id"], date_str)}
        score = _composite_score(live, root_causes, task, priority)
        candidates.append((score, tech))

    if not candidates:
        # All techs at capacity — pick least loaded ignoring cap
        for tech in _TECH_LIST:
            live = {**tech, "workload": tracker.count(tech["id"], date_str)}
            score = _composite_score(live, root_causes, task, priority)
            candidates.append((score, tech))

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1], candidates[0][0]


# ── Slot allocator ────────────────────────────────────────────────────────────

def _next_slot(date_str: str, day_slot_counts: dict[str, int]) -> str:
    idx = day_slot_counts.get(date_str, 0)
    return _WORKING_SLOTS[idx % len(_WORKING_SLOTS)]


def _end_time(time_str: str, duration_hours: int) -> str:
    h, m = map(int, time_str.split(":"))
    end_h = h + duration_hours
    return f"{end_h:02d}:{m:02d}" if end_h < 24 else "Next Day"


# ── Public: build optimised schedule ─────────────────────────────────────────

def build_optimised_schedule(
    scored_vehicles: list[tuple[float, str, dict]],
) -> list[ScheduleEntry]:
    """
    Parameters
    ----------
    scored_vehicles : [(urgency_score, priority_label, vehicle_dict), ...]
                      Pre-sorted highest urgency first.

    Returns
    -------
    List of ScheduleEntry dicts, one per vehicle.
    """
    today    = date.today()
    tracker  = _CapacityTracker()
    day_slots: dict[str, int] = {}
    entries: list[ScheduleEntry] = []

    for urgency, priority, v in scored_vehicles:
        root_causes = v.get("root_cause", [])
        template    = get_template(root_causes)
        task        = template["label"]
        duration_h  = template["duration"]

        # Base date from priority offset; push forward if day is overloaded
        base_date = today + timedelta(days=_PRIORITY_OFFSET[priority])
        sched_date = base_date
        # Spread: if this day already has ≥5 jobs, push one day
        while day_slots.get(sched_date.isoformat(), 0) >= 5:
            sched_date += timedelta(days=1)

        date_str   = sched_date.isoformat()
        time_str   = _next_slot(date_str, day_slots)
        day_slots[date_str] = day_slots.get(date_str, 0) + 1

        tech, score = _best_tech(root_causes, task, priority, date_str, tracker)
        tracker.assign(tech["id"], date_str)

        vid      = v["vehicle_id"]
        event_id = f"maint-{vid}-{date_str}"

        entries.append(ScheduleEntry(
            vehicle_id=vid,
            event_id=event_id,
            priority=priority,
            urgency_score=urgency,
            date=date_str,
            time=time_str,
            end_time=_end_time(time_str, duration_h),
            duration_hours=duration_h,
            technician=tech["name"],
            technician_id=tech["id"],
            task=task,
            skill_required=template["skill"],
        ))

    return entries


# ── Public: reschedule (drag-and-drop) ───────────────────────────────────────

def apply_reschedule(
    events: list[dict],
    event_id: str,
    new_date: str,
    new_time: str | None,
    all_vehicles: list[dict],
) -> dict:
    """
    Move one event to a new date/time and recalculate fleet-level impact.

    Parameters
    ----------
    events      : current FullCalendar event list (from generate_schedule)
    event_id    : the event being moved
    new_date    : ISO date string "YYYY-MM-DD"
    new_time    : "HH:MM" or None (keep original time)
    all_vehicles: enriched vehicle list for risk recalculation

    Returns
    -------
    {
        updated_event:   <patched FullCalendar event>,
        fleet_impact:    { risk_delta, downtime_delta, cost_delta, ... },
        conflict_warning: str | None,
    }
    """
    target = next((e for e in events if e["id"] == event_id), None)
    if not target:
        return {"error": f"Event {event_id!r} not found"}

    ep          = target["extendedProps"]
    old_date    = ep["date"]
    old_time    = ep["time"]
    duration_h  = ep["duration_hours"]
    priority    = ep["priority"]
    tech_id     = ep["technician_id"]

    # Resolve new time
    resolved_time = new_time or old_time
    h, m = map(int, resolved_time.split(":"))
    new_start = datetime.fromisoformat(f"{new_date}T{resolved_time}:00")
    new_end   = new_start + timedelta(hours=duration_h)

    # Check technician conflicts on the new date
    conflict_warning = None
    tech_jobs_on_day = sum(
        1 for e in events
        if e["id"] != event_id
        and e["extendedProps"].get("technician_id") == tech_id
        and e["extendedProps"].get("date") == new_date
    )
    if tech_jobs_on_day >= _MAX_JOBS_PER_TECH_PER_DAY:
        conflict_warning = (
            f"Technician {ep['technician']} already has "
            f"{tech_jobs_on_day} job(s) on {new_date}. "
            "Consider reassigning."
        )

    # Patch the event
    updated = {
        **target,
        "start": new_start.isoformat(),
        "end":   new_end.isoformat(),
        "extendedProps": {
            **ep,
            "date":           new_date,
            "time":           resolved_time,
            "original_start": ep.get("original_start", target["start"]),
            "rescheduled":    True,
            "rescheduled_at": datetime.utcnow().isoformat(),
        },
    }

    # Fleet impact delta
    days_moved   = (date.fromisoformat(new_date) - date.fromisoformat(old_date)).days
    risk_delta   = _risk_delta(priority, days_moved)
    cost_delta   = _cost_delta(ep, days_moved)
    downtime_delta = 0  # duration unchanged; only date shifted

    fleet_impact = {
        "event_id":        event_id,
        "vehicle_id":      ep["vehicle_id"],
        "moved_from":      f"{old_date} {old_time}",
        "moved_to":        f"{new_date} {resolved_time}",
        "days_moved":      days_moved,
        "risk_delta":      risk_delta,
        "cost_delta":      cost_delta,
        "downtime_delta":  downtime_delta,
        "priority":        priority,
        "recommendation":  _reschedule_recommendation(priority, days_moved),
    }

    return {
        "updated_event":   updated,
        "fleet_impact":    fleet_impact,
        "conflict_warning": conflict_warning,
    }


def _risk_delta(priority: str, days_moved: int) -> str:
    """Qualitative risk change when a job is delayed."""
    if days_moved <= 0:
        return "Reduced — earlier service"
    if priority == "Critical" and days_moved >= 1:
        return f"⚠ Increased — Critical job delayed {days_moved}d"
    if priority == "High" and days_moved >= 3:
        return f"⚠ Elevated — High priority delayed {days_moved}d"
    return "Minimal change"


def _cost_delta(ep: dict, days_moved: int) -> int:
    """Estimate additional cost exposure from delay."""
    if days_moved <= 0:
        return 0
    failure_cost = ep.get("business_impact", {}).get("failure_cost", 2000)
    # Each day of delay adds ~2% of failure cost as exposure
    return round(failure_cost * 0.02 * days_moved)


def _reschedule_recommendation(priority: str, days_moved: int) -> str:
    if days_moved < 0:
        return "✅ Moved earlier — risk reduced."
    if priority == "Critical" and days_moved > 0:
        return "🔴 Not recommended — Critical jobs should not be delayed."
    if priority == "High" and days_moved > 2:
        return "⚠ Caution — High priority job delayed significantly."
    if days_moved > 7:
        return "⚠ Long delay — reassess vehicle condition before rescheduling."
    return "✅ Reschedule accepted."
