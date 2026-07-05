"""
Scenario Simulation Engine — "What-If Analysis"

Flow for every repair scenario:
    1. Clone current sensor snapshot
    2. Apply the targeted sensor fix (battery voltage / temperature / both)
    3. Pass modified sensors through Health ML → Failure ML → RUL ML
    4. Compute financial impact  (repair cost vs avoided failure cost)
    5. Return structured before/after/financial/recommendation dict

simulate_ignore_vehicle() instead runs the existing forecast_future()
for 7 / 15 / 30 days so the fleet manager can see the cost of inaction.
"""

from services.twin_prediction_service import (
    predict_future_health,
    predict_future_failure,
    predict_future_rul,
)

# ---------------------------------------------------------------------------
# Constants  (INR)
# ---------------------------------------------------------------------------
_COSTS = {
    "battery_replacement": 6_000,
    "cooling_repair":      8_000,
    "full_service":        18_000,
    "ignore":              0,
}

# Assumed total breakdown / towing / downtime cost if vehicle fails outright
_BREAKDOWN_COST = 1_10_000   # ₹1,10,000


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------
def _sensors(vehicle: dict) -> dict:
    """Extract the sensor fields the ML pipeline expects."""
    return {
        "health_score":        vehicle.get("health_score", 50),
        "failure_probability": vehicle.get("failure_probability", 50),
        "battery_voltage":     vehicle.get("battery_voltage", 12.0),
        "temperature":         vehicle.get("temperature", 50),
        "rpm":                 vehicle.get("rpm", 1500),
        "rul_days":            vehicle.get("rul_days",
                               vehicle.get("remaining_useful_life_days", 15)),
    }


def _run_ml(sensors: dict) -> dict:
    """Push a sensor snapshot through all three ML models."""
    health  = predict_future_health(sensors)
    failure = predict_future_failure(sensors)
    rul     = predict_future_rul(sensors)
    return {"health": health, "failure_probability": failure, "rul": rul}


def _status(health: int) -> str:
    if health < 25: return "Critical"
    if health < 60: return "Warning"
    return "Healthy"


def _before(vehicle: dict) -> dict:
    """Current state snapshot (what the vehicle looks like right now)."""
    return {
        "health":              vehicle.get("health_score", 50),
        "failure_probability": vehicle.get("failure_probability", 50),
        "rul":                 vehicle.get("rul_days",
                               vehicle.get("remaining_useful_life_days", 15)),
        "status":              _status(vehicle.get("health_score", 50)),
    }


def _financial(repair_cost: int, before_failure_prob: float,
               after_failure_prob: float) -> dict:
    """
    failure_cost_before  — what the vehicle is expected to cost if it breaks NOW
    failure_cost_after   — residual failure cost after the repair
    potential_savings    — reduction in expected failure cost minus repair spend
    """
    failure_before = round(_BREAKDOWN_COST * before_failure_prob / 100)
    failure_after  = round(_BREAKDOWN_COST * after_failure_prob  / 100)
    savings        = max(0, failure_before - failure_after - repair_cost)
    return {
        "repair_cost":       repair_cost,
        "failure_cost":      failure_before,   # cost if you do nothing
        "potential_savings": savings,
    }


# ---------------------------------------------------------------------------
# Public simulation functions
# ---------------------------------------------------------------------------
def simulate_battery_replacement(vehicle: dict) -> dict:
    """
    What if I replace the battery today?
    → battery_voltage reset to 12.8 V (new battery)
    → all other sensors unchanged
    → ML re-calculates health / failure_probability / RUL
    """
    snap    = _sensors(vehicle)
    snap["battery_voltage"] = 12.8          # new battery voltage

    after   = _run_ml(snap)
    cost    = _COSTS["battery_replacement"]
    fin     = _financial(cost,
                         vehicle.get("failure_probability", 50),
                         after["failure_probability"])

    return {
        "scenario":         "Battery Replacement",
        "before":           _before(vehicle),
        "after":            {**after, "status": _status(after["health"])},
        "financial_impact": fin,
        "recommendation":   (
            "Battery Replacement Recommended"
            if fin["potential_savings"] > 0
            else "Marginal benefit — monitor instead"
        ),
    }


def simulate_cooling_repair(vehicle: dict) -> dict:
    """
    What if I repair the cooling system today?
    → temperature reset to 75 °C (healthy operating range)
    → battery_voltage and RPM unchanged
    → ML re-calculates health / failure_probability / RUL
    """
    snap    = _sensors(vehicle)
    snap["temperature"] = 75                # cooling system restored

    after   = _run_ml(snap)
    cost    = _COSTS["cooling_repair"]
    fin     = _financial(cost,
                         vehicle.get("failure_probability", 50),
                         after["failure_probability"])

    return {
        "scenario":         "Cooling Repair",
        "before":           _before(vehicle),
        "after":            {**after, "status": _status(after["health"])},
        "financial_impact": fin,
        "recommendation":   (
            "Cooling Repair Recommended"
            if fin["potential_savings"] > 0
            else "Marginal benefit — monitor instead"
        ),
    }


def simulate_full_service(vehicle: dict) -> dict:
    """
    What if I do a full service today?
    → battery_voltage = 12.8 V
    → temperature     = 65 °C
    → rpm capped at   2 000 (engine de-stressed)
    → ML re-calculates health / failure_probability / RUL
    """
    snap    = _sensors(vehicle)
    snap["battery_voltage"] = 12.8
    snap["temperature"]     = 65
    snap["rpm"]             = min(snap["rpm"], 2000)   # de-stress engine

    after   = _run_ml(snap)
    cost    = _COSTS["full_service"]
    fin     = _financial(cost,
                         vehicle.get("failure_probability", 50),
                         after["failure_probability"])

    return {
        "scenario":         "Full Service",
        "before":           _before(vehicle),
        "after":            {**after, "status": _status(after["health"])},
        "financial_impact": fin,
        "recommendation":   "Full Service Recommended",
    }


def simulate_ignore_vehicle(vehicle: dict) -> dict:
    """
    What if I delay / ignore maintenance?
    → no sensor changes
    → runs the existing physics-based forecast for 7 / 15 / 30 days
    → uses Day-30 worst-case to compute the financial exposure
    """
    from engines.simulation_engine import forecast_future   # local import avoids circular

    forecast = forecast_future(vehicle)
    now      = _before(vehicle)

    # Day-30 represents the worst projected state
    day30 = forecast.get("day30", {})
    worst = {
        "health":              day30.get("health",              now["health"]),
        "failure_probability": day30.get("failure_probability", now["failure_probability"]),
        "rul":                 day30.get("rul_days",            now["rul"]),
    }

    failure_exposure = round(_BREAKDOWN_COST * worst["failure_probability"] / 100)

    return {
        "scenario":  "Ignore Vehicle",
        "before":    now,
        "after":     {**worst, "status": _status(worst["health"])},
        "forecast":  {
            "day7":  forecast.get("day7",  {}),
            "day15": forecast.get("day15", {}),
            "day30": forecast.get("day30", {}),
        },
        "financial_impact": {
            "repair_cost":       0,
            "failure_cost":      failure_exposure,   # expected cost if it breaks
            "potential_savings": 0,                  # no action = no savings
        },
        "recommendation": "Not Recommended — Failure Risk Increasing",
    }


# ---------------------------------------------------------------------------
# AI Scoring
# ---------------------------------------------------------------------------
def _calculate_score(health: int, failure_probability: float,
                     rul_days: int, potential_savings: int) -> float:
    """
    Weighted composite score used to rank every scenario.

    Weights:
        health              35 %  — higher is better
        (100 - failure)     30 %  — lower failure risk is better
        rul_days            20 %  — more life remaining is better
        savings / 1000      15 %  — financial return (normalised per ₹1k)
    """
    score = (
        health                          * 0.35 +
        (100 - failure_probability)     * 0.30 +
        rul_days                        * 0.20 +
        (potential_savings / 1000)      * 0.15
    )
    return round(score, 2)


# ---------------------------------------------------------------------------
# Compare all four scenarios
# ---------------------------------------------------------------------------
def compare_all_scenarios(vehicle: dict) -> dict:
    """
    Run all four scenarios, attach an AI score to each, pick the winner.

    Returned shape
    --------------
    {
        "vehicle_id": 88,
        "best_option": "Full Service",
        "reason": "...",
        "comparison": {
            "battery_replacement": { health, failure_probability,
                                     rul_days, potential_savings, ai_score },
            "cooling_repair":      { ... },
            "full_service":        { ... },
            "ignore_vehicle":      { ... }
        }
    }
    """
    raw = {
        "battery_replacement": simulate_battery_replacement(vehicle),
        "cooling_repair":      simulate_cooling_repair(vehicle),
        "full_service":        simulate_full_service(vehicle),
        "ignore_vehicle":      simulate_ignore_vehicle(vehicle),
    }

    comparison = {}
    for key, result in raw.items():
        health   = result["after"]["health"]
        failure  = result["after"]["failure_probability"]
        rul      = result["after"].get("rul", result["after"].get("rul_days", 0))
        savings  = result["financial_impact"]["potential_savings"]

        comparison[key] = {
            "scenario":            result["scenario"],
            "health":              health,
            "failure_probability": failure,
            "rul_days":            rul,
            "repair_cost":         result["financial_impact"]["repair_cost"],
            "potential_savings":   savings,
            "status":              result["after"]["status"],
            "recommendation":      result["recommendation"],
            "ai_score":            _calculate_score(health, failure, rul, savings),
        }

    # Winner = highest AI score (ignore_vehicle can win mathematically
    # only if the vehicle is already healthy — the score reflects that)
    best_key  = max(comparison, key=lambda k: comparison[k]["ai_score"])
    best      = comparison[best_key]

    return {
        "vehicle_id":  vehicle.get("vehicle_id"),
        "best_option": best["scenario"],
        "reason": (
            f"Highest health improvement with lowest failure probability "
            f"and maximum financial savings."
        ),
        "comparison": comparison,
    }
