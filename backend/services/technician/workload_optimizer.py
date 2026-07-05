"""
Workload Optimizer
==================
Balances technician assignments across days and shifts by:
  - Tracking per-technician, per-day job counts
  - Respecting shift working hours (Morning / Afternoon / Night)
  - Enforcing max_jobs_per_day capacity from the repository
  - Spreading load to avoid overloading any single technician
  - Providing rebalancing recommendations when imbalance is detected

Used by assignment_engine.py to select the best slot for each job.
"""
from __future__ import annotations

from datetime import date, timedelta
from collections import defaultdict

from services.technician.technician_repository import get_all, _SHIFT_HOURS

# ── Constants ─────────────────────────────────────────────────────────────────
_WORKING_SLOTS: dict[str, list[str]] = {
    "Morning":   ["08:00", "09:30", "11:00"],
    "Afternoon": ["12:00", "13:30", "15:00", "16:30"],
    "Night":     ["20:00", "21:30", "23:00"],
}
_ALL_SLOTS = ["08:00", "09:30", "11:00", "13:00", "14:30", "16:00", "17:30"]
_MAX_DAY_SPREAD = 14   # never push a job more than 14 days out


# ── Capacity state ────────────────────────────────────────────────────────────

class WorkloadState:
    """
    Mutable workload tracker for a scheduling session.
    Initialised from the DB; mutations are local to the session.
    """

    def __init__(self) -> None:
        techs = get_all()
        # {tech_id: {date_str: job_count}}
        self._load: dict[int, dict[str, int]] = {t["id"]: {} for t in techs}
        # Seed today's load from current DB workload
        today = date.today().isoformat()
        for t in techs:
            self._load[t["id"]][today] = t["workload"]

        self._techs: dict[int, dict] = {t["id"]: t for t in techs}

    # ── Queries ───────────────────────────────────────────────────────────────

    def jobs_on_day(self, tech_id: int, date_str: str) -> int:
        return self._load.get(tech_id, {}).get(date_str, 0)

    def capacity_on_day(self, tech_id: int, date_str: str) -> int:
        tech = self._techs.get(tech_id)
        if not tech:
            return 0
        return max(0, tech["max_jobs_per_day"] - self.jobs_on_day(tech_id, date_str))

    def is_available(self, tech_id: int, date_str: str) -> bool:
        tech = self._techs.get(tech_id)
        if not tech or not tech["available"]:
            return False
        return self.capacity_on_day(tech_id, date_str) > 0

    def shift_slots(self, tech_id: int) -> list[str]:
        tech = self._techs.get(tech_id, {})
        return _WORKING_SLOTS.get(tech.get("shift", "Morning"), _ALL_SLOTS)

    def next_slot(self, tech_id: int, date_str: str) -> str:
        used  = self.jobs_on_day(tech_id, date_str)
        slots = self.shift_slots(tech_id)
        return slots[used % len(slots)]

    # ── Mutations ─────────────────────────────────────────────────────────────

    def assign(self, tech_id: int, date_str: str) -> None:
        if tech_id not in self._load:
            self._load[tech_id] = {}
        self._load[tech_id][date_str] = self.jobs_on_day(tech_id, date_str) + 1

    def release(self, tech_id: int, date_str: str) -> None:
        if tech_id in self._load and date_str in self._load[tech_id]:
            self._load[tech_id][date_str] = max(0, self._load[tech_id][date_str] - 1)

    # ── Reporting ─────────────────────────────────────────────────────────────

    def daily_summary(self, date_str: str) -> list[dict]:
        result = []
        for tid, tech in self._techs.items():
            jobs = self.jobs_on_day(tid, date_str)
            cap  = tech["max_jobs_per_day"]
            result.append({
                "technician_id":   tid,
                "technician":      tech["name"],
                "shift":           tech["shift"],
                "jobs_assigned":   jobs,
                "capacity":        cap,
                "remaining_slots": max(0, cap - jobs),
                "utilisation_pct": round((jobs / max(cap, 1)) * 100, 1),
            })
        result.sort(key=lambda x: -x["utilisation_pct"])
        return result

    def fleet_load_forecast(self, days: int = 7) -> list[dict]:
        today = date.today()
        rows  = []
        for i in range(days):
            d    = (today + timedelta(days=i)).isoformat()
            jobs = sum(self.jobs_on_day(tid, d) for tid in self._load)
            cap  = sum(t["max_jobs_per_day"] for t in self._techs.values() if t["available"])
            rows.append({
                "date":            d,
                "total_jobs":      jobs,
                "total_capacity":  cap,
                "utilisation_pct": round((jobs / max(cap, 1)) * 100, 1),
            })
        return rows


# ── Slot finder ───────────────────────────────────────────────────────────────

def find_earliest_slot(
    state: WorkloadState,
    tech_id: int,
    from_date: date,
    priority: str = "Routine",
) -> tuple[str, str]:
    """
    Find the earliest date + time slot for a technician starting from `from_date`.

    For Critical priority, override availability and use the first slot regardless.

    Returns (date_str, time_str).
    """
    for offset in range(_MAX_DAY_SPREAD):
        d     = (from_date + timedelta(days=offset)).isoformat()
        avail = state.is_available(tech_id, d)

        if avail or (priority == "Critical" and offset == 0):
            return d, state.next_slot(tech_id, d)

    # Fallback: use from_date even if over capacity
    d = from_date.isoformat()
    return d, state.next_slot(tech_id, d)


# ── Rebalancing ───────────────────────────────────────────────────────────────

def rebalance_recommendations(state: WorkloadState, date_str: str) -> list[dict]:
    """
    Identify overloaded technicians on a given day and suggest moves.

    Returns a list of recommendation dicts.
    """
    summary = state.daily_summary(date_str)
    overloaded  = [r for r in summary if r["utilisation_pct"] >= 100]
    underloaded = [r for r in summary if r["remaining_slots"] >= 2]

    recs = []
    for over in overloaded:
        for under in underloaded:
            if over["shift"] == under["shift"]:   # same shift preferred
                recs.append({
                    "action":       "reassign",
                    "from_tech":    over["technician"],
                    "from_tech_id": over["technician_id"],
                    "to_tech":      under["technician"],
                    "to_tech_id":   under["technician_id"],
                    "date":         date_str,
                    "reason":       (
                        f"{over['technician']} is at {over['utilisation_pct']}% capacity. "
                        f"{under['technician']} has {under['remaining_slots']} open slot(s)."
                    ),
                })
                break   # one recommendation per overloaded tech

    return recs


# ── Capacity forecast ─────────────────────────────────────────────────────────

def capacity_forecast(days: int = 7) -> dict:
    """
    Return a 7-day capacity forecast showing available slots per day.
    Uses a fresh WorkloadState seeded from the DB.
    """
    state = WorkloadState()
    today = date.today()
    rows  = []

    for i in range(days):
        d    = (today + timedelta(days=i)).isoformat()
        avail_slots = sum(
            state.capacity_on_day(tid, d)
            for tid in state._techs
            if state._techs[tid]["available"]
        )
        rows.append({
            "date":            d,
            "available_slots": avail_slots,
            "daily_load":      state.daily_summary(d),
        })

    return {
        "forecast_days": days,
        "days":          rows,
        "summary":       state.fleet_load_forecast(days),
    }
