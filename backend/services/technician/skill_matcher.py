"""
Skill Matcher
=============
Maps repair types and root causes to technician skills with a
confidence score and gap analysis.

Used by assignment_engine.py and workload_optimizer.py to rank
technicians before capacity constraints are applied.
"""
from __future__ import annotations

# ── Skill → keyword mapping (single source of truth) ─────────────────────────
SKILL_KEYWORDS: dict[str, list[str]] = {
    "Battery":      ["battery", "voltage", "charging", "bms", "hv", "cell"],
    "HV Systems":   ["battery", "voltage", "hv", "high voltage", "bms"],
    "Electrical":   ["electrical", "wiring", "fuse", "relay", "voltage", "circuit"],
    "Diagnostics":  ["diagnostics", "obd", "scan", "fault", "code"],
    "Cooling":      ["cooling", "thermal", "temperature", "coolant", "overheat", "radiator"],
    "Thermal":      ["thermal", "temperature", "cooling", "heat"],
    "Motor":        ["motor", "engine", "rpm", "stress", "powertrain", "torque"],
    "Engine":       ["engine", "motor", "rpm", "compression"],
    "Powertrain":   ["motor", "engine", "transmission", "drivetrain", "torque"],
    "Transmission": ["transmission", "gear", "drivetrain", "gearbox", "shift"],
    "Drivetrain":   ["transmission", "gear", "drivetrain", "axle", "differential"],
    "Brake":        ["brake", "braking", "pad", "disc", "caliper", "abs"],
    "Suspension":   ["suspension", "shock", "spring", "strut", "bearing"],
    "General":      [],   # matches everything at a base confidence
}

# Repair task → required skill (primary)
TASK_SKILL_MAP: dict[str, str] = {
    "Battery Replacement":          "Battery",
    "Battery Check":                "Battery",
    "Cooling System Service":       "Cooling",
    "Cooling System Overhaul":      "Cooling",
    "Thermal Inspection":           "Thermal",
    "Motor / Engine Overhaul":      "Motor",
    "Engine Inspection":            "Engine",
    "Brake System Service":         "Brake",
    "Transmission Service":         "Transmission",
    "Electrical System Inspection": "Electrical",
    "General Inspection":           "General",
}

# Skill proficiency tiers (used for gap analysis)
_TIER: dict[str, int] = {
    "Battery": 3, "HV Systems": 3, "Electrical": 2,
    "Cooling": 2, "Thermal": 2,
    "Motor": 3, "Engine": 3, "Powertrain": 3,
    "Transmission": 3, "Drivetrain": 3,
    "Brake": 2, "Suspension": 1,
    "Diagnostics": 1, "General": 0,
}


# ── Core matching ─────────────────────────────────────────────────────────────

def match_score(tech_skills: list[str], root_causes: list[str], task: str) -> float:
    """
    Return 0–100 skill match score for a technician against a repair job.

    Scoring:
      - Each skill that matches a keyword in root_causes+task → +1.0
      - "General" skill → +0.4 (partial match for any job)
      - Normalised by number of skills, capped at 100
    """
    combined = " ".join(root_causes + [task]).lower()
    matched  = 0.0
    total    = len(tech_skills)

    for skill in tech_skills:
        keywords = SKILL_KEYWORDS.get(skill, [])
        if not keywords:
            matched += 0.4
        elif any(kw in combined for kw in keywords):
            matched += 1.0

    return min(100.0, round((matched / max(total, 1)) * 100, 1))


def required_skill(task: str, root_causes: list[str]) -> str:
    """Identify the primary skill required for a repair task."""
    if task in TASK_SKILL_MAP:
        return TASK_SKILL_MAP[task]
    # Fallback: scan root causes
    combined = " ".join(root_causes).lower()
    for skill, keywords in SKILL_KEYWORDS.items():
        if keywords and any(kw in combined for kw in keywords):
            return skill
    return "General"


def skill_gap(tech_skills: list[str], task: str, root_causes: list[str]) -> dict:
    """
    Analyse the gap between what the technician has and what the job needs.

    Returns
    -------
    {
        required_skill: str,
        has_required:   bool,
        match_score:    float,
        missing_skills: [str],
        tier_gap:       int,   # 0 = perfect, higher = bigger gap
        confidence:     "High"|"Medium"|"Low",
    }
    """
    req      = required_skill(task, root_causes)
    has_req  = req in tech_skills or req == "General"
    score    = match_score(tech_skills, root_causes, task)

    # Find all skills the job ideally needs
    combined = " ".join(root_causes + [task]).lower()
    ideal    = [s for s, kws in SKILL_KEYWORDS.items() if kws and any(kw in combined for kw in kws)]
    missing  = [s for s in ideal if s not in tech_skills]

    req_tier  = _TIER.get(req, 0)
    tech_tier = max((_TIER.get(s, 0) for s in tech_skills), default=0)
    tier_gap  = max(0, req_tier - tech_tier)

    confidence = "High" if score >= 75 else "Medium" if score >= 40 else "Low"

    return {
        "required_skill": req,
        "has_required":   has_req,
        "match_score":    score,
        "missing_skills": missing[:3],
        "tier_gap":       tier_gap,
        "confidence":     confidence,
    }


def rank_technicians(
    technicians: list[dict],
    root_causes: list[str],
    task: str,
    priority: str,
) -> list[dict]:
    """
    Rank a list of technician dicts by skill match score (desc).
    Each dict gets a `skill_match` key injected.

    Parameters
    ----------
    technicians : list of technician dicts (from repository or in-memory)
    root_causes : vehicle root cause list
    task        : repair task label
    priority    : "Critical"|"High"|"Medium"|"Routine"
    """
    ranked = []
    for t in technicians:
        score = match_score(t.get("skills", []), root_causes, task)
        gap   = skill_gap(t.get("skills", []), task, root_causes)
        ranked.append({
            **t,
            "skill_match":  score,
            "skill_gap":    gap,
        })

    # Sort: skill match desc, then rating desc, then workload asc
    ranked.sort(key=lambda x: (-x["skill_match"], -x.get("rating", 0), x.get("workload", 0)))
    return ranked


def classify_repair(root_causes: list[str]) -> dict:
    """
    Classify a repair job into a category and complexity tier.

    Returns
    -------
    {
        category:   str,
        complexity: "Simple"|"Moderate"|"Complex",
        min_experience_years: int,
    }
    """
    combined = " ".join(root_causes).lower()

    if any(kw in combined for kw in ["battery", "voltage", "hv", "bms"]):
        cat, tier = "Electrical / HV", 3
    elif any(kw in combined for kw in ["engine", "motor", "rpm", "powertrain"]):
        cat, tier = "Powertrain", 3
    elif any(kw in combined for kw in ["transmission", "gear", "drivetrain"]):
        cat, tier = "Drivetrain", 3
    elif any(kw in combined for kw in ["cooling", "thermal", "temperature"]):
        cat, tier = "Thermal / Cooling", 2
    elif any(kw in combined for kw in ["brake", "suspension"]):
        cat, tier = "Chassis / Safety", 2
    elif any(kw in combined for kw in ["electrical", "wiring", "fuse"]):
        cat, tier = "Electrical", 2
    else:
        cat, tier = "General", 1

    complexity_map = {1: "Simple", 2: "Moderate", 3: "Complex"}
    min_exp_map    = {1: 1, 2: 3, 3: 5}

    return {
        "category":              cat,
        "complexity":            complexity_map[tier],
        "min_experience_years":  min_exp_map[tier],
    }
