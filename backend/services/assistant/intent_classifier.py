"""
Intent Classifier
=================
Rule-based intent detection from natural language queries.
Returns an Intent dataclass with a category, optional vehicle_id, and confidence.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field


@dataclass
class Intent:
    category: str           # see INTENTS keys
    vehicle_id: int | None = None
    slots: dict             = field(default_factory=dict)
    confidence: float       = 1.0


# ── Intent definitions: (category, patterns) ─────────────────────────────────
_INTENTS: list[tuple[str, list[str]]] = [
    ("fleet_summary",       [r"\bfleet\b", r"\ball vehicles\b", r"\boverview\b", r"\bsummary\b"]),
    ("vehicle_health",      [r"\bhealth\b", r"\bcondition\b", r"\bstatus\b"]),
    ("failure_risk",        [r"\bfailure\b", r"\brisk\b", r"\bfail\b", r"\bbreakdown\b"]),
    ("rul",                 [r"\brul\b", r"\bremaining.?useful.?life\b", r"\bhow long\b", r"\blife left\b"]),
    ("root_cause",          [r"\broot.?cause\b", r"\bwhy\b", r"\bcause\b", r"\bdiagnos\b"]),
    ("maintenance",         [r"\bmaintenance\b", r"\bservice\b", r"\brepair\b", r"\bschedule\b"]),
    ("technician",          [r"\btechnician\b", r"\bmechanic\b", r"\bassign\b", r"\bwho.*(fix|repair|service)\b"]),
    ("inventory",           [r"\binventor\b", r"\bparts?\b", r"\bstock\b", r"\bspare\b"]),
    ("calendar",            [r"\bcalendar\b", r"\bschedule\b", r"\bupcoming\b", r"\bappointment\b"]),
    ("cost",                [r"\bcost\b", r"\bprice\b", r"\bexpense\b", r"\bsaving\b", r"\bbudget\b"]),
    ("alerts",              [r"\balert\b", r"\bwarning\b", r"\bcritical\b", r"\burgent\b"]),
    ("explanation",         [r"\bexplain\b", r"\bwhy\b", r"\bhow come\b", r"\bshap\b", r"\bxai\b"]),
    ("greeting",            [r"\bhello\b", r"\bhi\b", r"\bhey\b", r"\bhelp\b", r"\bwhat can you\b"]),
]

_VEHICLE_RE = re.compile(r"\bvehicle\s*#?(\d+)\b|\bv(\d+)\b|\bid\s*[:\-]?\s*(\d+)\b", re.I)


def _extract_vehicle_id(text: str) -> int | None:
    m = _VEHICLE_RE.search(text)
    if m:
        raw = m.group(1) or m.group(2) or m.group(3)
        return int(raw)
    return None


def classify(text: str) -> Intent:
    lower = text.lower()
    vehicle_id = _extract_vehicle_id(lower)

    scores: dict[str, int] = {}
    for category, patterns in _INTENTS:
        hits = sum(1 for p in patterns if re.search(p, lower))
        if hits:
            scores[category] = hits

    if not scores:
        return Intent(category="unknown", vehicle_id=vehicle_id, confidence=0.3)

    best = max(scores, key=lambda k: scores[k])
    total_hits = sum(scores.values())
    confidence = round(min(0.99, scores[best] / max(total_hits, 1) + 0.4), 2)

    return Intent(category=best, vehicle_id=vehicle_id, confidence=confidence)
