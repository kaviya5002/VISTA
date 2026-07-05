"""
Inventory Predictor — estimates future spare part demand using:
  - Root Cause Analysis output
  - Failure Probability scores
  - Remaining Useful Life (RUL)
  - Maintenance Calendar scheduled events
"""
from data.parts_catalog import CATALOG


def _demand_weight(vehicle: dict) -> float:
    fail = vehicle.get("failure_probability", 0)
    if fail > 85 or vehicle.get("priority") == "Immediate": return 1.0
    if fail > 60 or vehicle.get("priority") == "High":      return 0.7
    if fail > 35 or vehicle.get("priority") == "Medium":    return 0.4
    return 0.2


def _week_from_rul(vehicle: dict) -> int:
    rul = vehicle.get("remaining_useful_life_days", 60)
    if rul <= 7:  return 1
    if rul <= 14: return 2
    if rul <= 21: return 3
    return 4


def _root_matches(part: dict, root_causes: list[str]) -> bool:
    combined = " ".join(root_causes).lower()
    return any(kw in combined for kw in part["root_cause_keywords"])


def _calendar_demand(part: dict, calendar_events: list[dict]) -> int:
    """Count parts needed from already-scheduled maintenance calendar events."""
    count = 0
    for event in calendar_events:
        parts_needed = event.get("extendedProps", {}).get("parts", [])
        for p in parts_needed:
            if any(kw in p.lower() for kw in part["root_cause_keywords"]):
                count += 1
                break
    return count


def predict_demand(vehicles: list[dict], calendar_events: list[dict] = None) -> list[dict]:
    """
    Returns per-part demand predictions for the next 30 days.
    Combines fleet ML signals (root cause, failure prob, RUL) with calendar.
    """
    calendar_events = calendar_events or []
    predictions = []

    for part in CATALOG:
        weekly = [0.0, 0.0, 0.0, 0.0]

        # Signal 1 & 2: Root Cause + Failure Probability weighted by RUL week
        for v in vehicles:
            root = v.get("root_cause", [])
            if _root_matches(part, root):
                w = _week_from_rul(v)
                weekly[w - 1] += _demand_weight(v)

        # Signal 3: Maintenance Calendar scheduled jobs
        cal_demand = _calendar_demand(part, calendar_events)
        weekly[0] += cal_demand  # calendar jobs are imminent (week 1)

        weekly_int = [round(x) for x in weekly]
        total_30d = sum(weekly_int)

        predictions.append({
            "part_id":        part["id"],
            "part_name":      part["name"],
            "category":       part["category"],
            "predicted_30d":  total_30d,
            "weekly_forecast": weekly_int,
            "demand_drivers": {
                "fleet_signals":    round(sum(weekly[:4]) - cal_demand),
                "calendar_jobs":    cal_demand,
            },
        })

    return predictions
