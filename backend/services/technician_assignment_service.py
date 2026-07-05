"""
AI Technician Assignment Engine
Scores every technician per job using:
  Skill Match ×40 + Availability ×20 + Experience ×15 + Rating ×15 + Workload ×10
"""
from datetime import datetime, timedelta
import random

# ── Technician database (in-memory; swap for SQLite later) ────────────────────
TECHNICIANS: list[dict] = [
    {
        "id": 1, "name": "Ravi Kumar",
        "skills": ["Battery", "Electrical", "HV Systems"],
        "experience": 7, "rating": 4.9,
        "available": True, "workload": 2,
        "current_jobs": [], "shift": "Morning",
        "avatar": "RK", "phone": "+91-98400-11001",
    },
    {
        "id": 2, "name": "Akash Singh",
        "skills": ["Cooling", "Motor", "Thermal"],
        "experience": 5, "rating": 4.8,
        "available": True, "workload": 1,
        "current_jobs": [], "shift": "Morning",
        "avatar": "AS", "phone": "+91-98400-11002",
    },
    {
        "id": 3, "name": "Priya Nair",
        "skills": ["Transmission", "Drivetrain", "Brake"],
        "experience": 8, "rating": 5.0,
        "available": False, "workload": 3,
        "current_jobs": [], "shift": "Morning",
        "avatar": "PN", "phone": "+91-98400-11003",
    },
    {
        "id": 4, "name": "Suresh Patel",
        "skills": ["Brake", "Suspension", "General"],
        "experience": 6, "rating": 4.7,
        "available": True, "workload": 0,
        "current_jobs": [], "shift": "Afternoon",
        "avatar": "SP", "phone": "+91-98400-11004",
    },
    {
        "id": 5, "name": "Meena Sharma",
        "skills": ["Electrical", "Battery", "Diagnostics"],
        "experience": 4, "rating": 4.6,
        "available": True, "workload": 1,
        "current_jobs": [], "shift": "Afternoon",
        "avatar": "MS", "phone": "+91-98400-11005",
    },
    {
        "id": 6, "name": "Arjun Das",
        "skills": ["Motor", "Engine", "Powertrain"],
        "experience": 9, "rating": 4.9,
        "available": False, "workload": 3,
        "current_jobs": [], "shift": "Morning",
        "avatar": "AD", "phone": "+91-98400-11006",
    },
    {
        "id": 7, "name": "Kavitha Rao",
        "skills": ["Cooling", "Thermal", "Electrical"],
        "experience": 6, "rating": 4.8,
        "available": True, "workload": 2,
        "current_jobs": [], "shift": "Afternoon",
        "avatar": "KR", "phone": "+91-98400-11007",
    },
    {
        "id": 8, "name": "Deepak Verma",
        "skills": ["General", "Brake", "Suspension"],
        "experience": 3, "rating": 4.5,
        "available": True, "workload": 0,
        "current_jobs": [], "shift": "Night",
        "avatar": "DV", "phone": "+91-98400-11008",
    },
    {
        "id": 9, "name": "Sanjay Iyer",
        "skills": ["Transmission", "Drivetrain", "Motor"],
        "experience": 10, "rating": 5.0,
        "available": True, "workload": 1,
        "current_jobs": [], "shift": "Morning",
        "avatar": "SI", "phone": "+91-98400-11009",
    },
    {
        "id": 10, "name": "Lakshmi Pillai",
        "skills": ["Battery", "HV Systems", "Diagnostics"],
        "experience": 5, "rating": 4.7,
        "available": False, "workload": 2,
        "current_jobs": [], "shift": "Afternoon",
        "avatar": "LP", "phone": "+91-98400-11010",
    },
    {
        "id": 11, "name": "Rahul Gupta",
        "skills": ["Engine", "Motor", "Cooling"],
        "experience": 7, "rating": 4.8,
        "available": True, "workload": 0,
        "current_jobs": [], "shift": "Night",
        "avatar": "RG", "phone": "+91-98400-11011",
    },
    {
        "id": 12, "name": "Anita Desai",
        "skills": ["General", "Electrical", "Diagnostics"],
        "experience": 4, "rating": 4.6,
        "available": True, "workload": 1,
        "current_jobs": [], "shift": "Night",
        "avatar": "AD2", "phone": "+91-98400-11012",
    },
]

# ── Skill → component keyword mapping ────────────────────────────────────────
SKILL_KEYWORDS: dict[str, list[str]] = {
    "Battery":      ["battery", "voltage", "charging", "bms", "hv"],
    "HV Systems":   ["battery", "voltage", "hv", "high voltage"],
    "Electrical":   ["electrical", "wiring", "fuse", "relay", "voltage"],
    "Diagnostics":  ["diagnostics", "obd", "scan"],
    "Cooling":      ["cooling", "thermal", "temperature", "coolant", "overheat"],
    "Thermal":      ["thermal", "temperature", "cooling"],
    "Motor":        ["motor", "engine", "rpm", "stress", "powertrain"],
    "Engine":       ["engine", "motor", "rpm"],
    "Powertrain":   ["motor", "engine", "transmission", "drivetrain"],
    "Transmission": ["transmission", "gear", "drivetrain"],
    "Drivetrain":   ["transmission", "gear", "drivetrain"],
    "Brake":        ["brake", "braking", "pad", "disc"],
    "Suspension":   ["suspension", "shock", "spring"],
    "General":      [],  # matches everything at base level
}

# ── Slot times ────────────────────────────────────────────────────────────────
SLOT_TIMES = ["08:00", "09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00", "17:00"]


# ── Scoring ───────────────────────────────────────────────────────────────────

def _skill_score(tech: dict, root_causes: list[str], task: str) -> float:
    """0–100: how well the technician's skills match the repair needed."""
    combined = " ".join(root_causes + [task]).lower()
    matched = 0
    total   = len(tech["skills"])
    for skill in tech["skills"]:
        keywords = SKILL_KEYWORDS.get(skill, [])
        if not keywords:                          # "General" — partial match
            matched += 0.4
        elif any(kw in combined for kw in keywords):
            matched += 1.0
    return min(100.0, (matched / max(total, 1)) * 100)


def _availability_score(tech: dict, priority: str) -> float:
    """Critical jobs ignore availability penalty; routine jobs prefer available."""
    if priority == "Critical":
        return 100.0 if tech["available"] else 60.0   # still usable in emergency
    return 100.0 if tech["available"] else 0.0


def _experience_score(tech: dict) -> float:
    """Normalise 0–10 years → 0–100."""
    return min(100.0, tech["experience"] * 10)


def _rating_score(tech: dict) -> float:
    """Normalise 0–5 stars → 0–100."""
    return (tech["rating"] / 5.0) * 100


def _workload_score(tech: dict) -> float:
    """Fewer current jobs = higher score. Max workload cap = 5."""
    return max(0.0, 100.0 - tech["workload"] * 20)


def _composite_score(tech: dict, root_causes: list[str], task: str, priority: str) -> float:
    skill   = _skill_score(tech, root_causes, task)
    avail   = _availability_score(tech, priority)
    exp     = _experience_score(tech)
    rating  = _rating_score(tech)
    workload = _workload_score(tech)
    return round(
        skill    * 0.40 +
        avail    * 0.20 +
        exp      * 0.15 +
        rating   * 0.15 +
        workload * 0.10,
        1
    )


def _build_reasons(tech: dict, skill_sc: float, priority: str) -> list[str]:
    reasons = []
    if skill_sc >= 80:
        matched = [s for s in tech["skills"] if s not in ("General",)]
        if matched:
            reasons.append(f"{matched[0]} specialist — direct skill match")
    if tech["rating"] >= 4.9:
        reasons.append(f"Top-rated technician ({tech['rating']}★)")
    elif tech["rating"] >= 4.7:
        reasons.append(f"Highly rated ({tech['rating']}★)")
    if tech["available"]:
        reasons.append("Currently available")
    elif priority == "Critical":
        reasons.append("Assigned despite workload — Critical priority override")
    if tech["workload"] == 0:
        reasons.append("No active jobs — immediate availability")
    elif tech["workload"] <= 1:
        reasons.append("Low current workload")
    if tech["experience"] >= 8:
        reasons.append(f"{tech['experience']} years experience")
    return reasons[:4]


def _estimate_times(duration_hours: int, workload: int) -> tuple[str, str]:
    """Estimate start/finish based on current workload."""
    base_hour = 8 + workload * 2          # each existing job adds ~2h delay
    start_h   = min(base_hour, 17)
    finish_h  = start_h + duration_hours
    start_str  = f"{start_h:02d}:00"
    finish_str = f"{finish_h:02d}:00" if finish_h < 24 else "Next Day"
    return start_str, finish_str


# ── Public API ────────────────────────────────────────────────────────────────

def get_all_technicians() -> list[dict]:
    return [
        {
            "id":           t["id"],
            "name":         t["name"],
            "skills":       t["skills"],
            "experience":   t["experience"],
            "rating":       t["rating"],
            "available":    t["available"],
            "workload":     t["workload"],
            "current_jobs": t["current_jobs"],
            "shift":        t["shift"],
            "avatar":       t["avatar"],
            "phone":        t["phone"],
            "status":       "Available" if t["available"] and t["workload"] < 3
                            else "Working" if t["workload"] > 0
                            else "Off Duty",
        }
        for t in TECHNICIANS
    ]


def assign_technician(vehicle: dict) -> dict:
    from services.repair_templates import get_template

    root_causes = vehicle.get("root_cause", [])
    template    = get_template(root_causes)
    task        = template["label"]
    duration    = template["duration"]
    priority    = vehicle.get("priority", "Low")
    if vehicle.get("failure_probability", 0) > 85 or vehicle.get("health_score", 100) < 30:
        priority = "Critical"

    # Score every technician
    scored = []
    for tech in TECHNICIANS:
        score      = _composite_score(tech, root_causes, task, priority)
        skill_sc   = _skill_score(tech, root_causes, task)
        scored.append((score, skill_sc, tech))

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_skill_sc, best = scored[0]

    start, finish = _estimate_times(duration, best["workload"])
    reasons       = _build_reasons(best, best_skill_sc, priority)

    # Runner-up alternatives
    alternatives = [
        {
            "name":  t["name"],
            "score": round(sc, 1),
            "skills": t["skills"][:2],
            "available": t["available"],
        }
        for sc, _, t in scored[1:4]
    ]

    return {
        "vehicle_id":        vehicle["vehicle_id"],
        "task":              task,
        "priority":          priority,
        "technician_id":     best["id"],
        "technician":        best["name"],
        "technician_skills": best["skills"],
        "technician_rating": best["rating"],
        "technician_exp":    best["experience"],
        "technician_shift":  best["shift"],
        "technician_phone":  best["phone"],
        "score":             best_score,
        "skill_score":       round(best_skill_sc, 1),
        "estimated_start":   start,
        "estimated_finish":  finish,
        "duration_hours":    duration,
        "reasons":           reasons,
        "alternatives":      alternatives,
        "workload_at_assign": best["workload"],
    }


def assign_fleet(vehicles: list[dict]) -> dict:
    """Assign technicians to all vehicles, tracking workload across assignments."""
    from services.repair_templates import get_template

    # Work on a mutable copy of workloads
    workload_tracker: dict[int, int] = {t["id"]: t["workload"] for t in TECHNICIANS}
    assignments = []

    # Sort by urgency so critical vehicles get first pick
    def urgency(v: dict) -> float:
        return v.get("failure_probability", 0) * 0.5 + (100 - v.get("health_score", 100)) * 0.5

    for vehicle in sorted(vehicles, key=urgency, reverse=True):
        root_causes = vehicle.get("root_cause", [])
        template    = get_template(root_causes)
        task        = template["label"]
        duration    = template["duration"]
        priority    = vehicle.get("priority", "Low")
        if vehicle.get("failure_probability", 0) > 85 or vehicle.get("health_score", 100) < 30:
            priority = "Critical"

        # Score with live workload tracker
        scored = []
        for tech in TECHNICIANS:
            live_tech = {**tech, "workload": workload_tracker[tech["id"]]}
            score     = _composite_score(live_tech, root_causes, task, priority)
            scored.append((score, live_tech))

        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best = scored[0]

        start, finish = _estimate_times(duration, best["workload"])
        workload_tracker[best["id"]] += 1          # increment for next assignment

        assignments.append({
            "vehicle_id":      vehicle["vehicle_id"],
            "task":            task,
            "priority":        priority,
            "technician":      best["name"],
            "technician_id":   best["id"],
            "score":           best_score,
            "estimated_start": start,
            "estimated_finish": finish,
            "duration_hours":  duration,
        })

    # ── Workforce summary ─────────────────────────────────────────────────────
    total_techs    = len(TECHNICIANS)
    available      = sum(1 for t in TECHNICIANS if t["available"] and t["workload"] < 3)
    working        = sum(1 for t in TECHNICIANS if t["workload"] > 0)
    off_duty       = total_techs - available - working
    avg_repair_hrs = round(sum(a["duration_hours"] for a in assignments) / max(len(assignments), 1), 1)
    completion_pct = round((available / total_techs) * 100) if total_techs else 0

    return {
        "assignments": assignments,
        "summary": {
            "total_technicians": total_techs,
            "available":         available,
            "working":           working,
            "off_duty":          max(0, off_duty),
            "total_assignments": len(assignments),
            "avg_repair_hours":  avg_repair_hrs,
            "completion_pct":    completion_pct,
        },
    }
