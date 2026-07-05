"""
Digital Twin Simulation Engine
================================
Projects vehicle state at future checkpoints using non-linear, compounding
degradation physics — not simple linear increments.

Degradation cascade:
    Cooling degrades first (temperature rises non-linearly)
        → Battery under increased thermal + electrical load
            → Motor thermal stress accumulates
                → Electrical system instability
                    → Transmission stress from power fluctuations

This means Day 7 / Day 15 / Day 30 tell genuinely different stories.
"""
import math
from services.twin_prediction_service import (
    predict_future_health,
    predict_future_failure,
    predict_future_rul,
    predict_future_priority,
)

# ── Degradation rate constants ─────────────────────────────────────────────
# These control how aggressively each sensor degrades over time.
# Tuned so a degraded vehicle (health < 50) shows clear progression.

_TEMP_BASE_RATE   = 0.40   # °C/day base rate
_TEMP_ACCEL_COEFF = 0.012  # extra °C/day per °C above 80 (non-linear runaway)
_VOLT_BASE_RATE   = 0.035  # V/day base drain
_VOLT_ACCEL_COEFF = 0.008  # extra V/day per degree above 75°C (thermal battery stress)

# Component degradation rates per day (health points lost)
_COMP_RATES = {
    "cooling":      2.8,   # degrades fastest — drives cascade
    "battery":      1.8,   # accelerated by cooling failure
    "motor":        1.4,   # thermal stress from both
    "electrical":   1.1,   # voltage instability
    "brakes":       0.6,   # mechanical wear, slower
    "transmission": 0.5,   # slowest
}

# Cascade multipliers: when cooling health drops below threshold,
# other components degrade faster
_CASCADE_THRESHOLD = 50   # cooling health below this triggers cascade
_CASCADE_MULT      = 1.6  # 60% faster degradation for downstream components


def _project_temperature(temp0: float, days: int) -> float:
    """
    Non-linear temperature projection.
    Above 80°C the rate accelerates (cooling system losing efficiency).
    """
    t = temp0
    for _ in range(days):
        accel = _TEMP_ACCEL_COEFF * max(0, t - 80)
        t += _TEMP_BASE_RATE + accel
    return round(min(130.0, t), 1)


def _project_voltage(volt0: float, temp_at_day: float, days: int) -> float:
    """
    Non-linear voltage projection.
    High temperature accelerates battery drain (Arrhenius effect).
    """
    v = volt0
    for d in range(days):
        # Temperature at this intermediate day (linear approx for inner loop)
        t_mid = volt0 + (temp_at_day - volt0) * (d / max(1, days))
        thermal_accel = _VOLT_ACCEL_COEFF * max(0, t_mid - 75)
        v -= (_VOLT_BASE_RATE + thermal_accel)
    return round(max(8.0, v), 2)


def _project_component_health(
    component: str,
    health0: float,
    days: int,
    cooling_health_at_day: float,
) -> int:
    """
    Project a single component's health at `days` from now.
    Applies cascade multiplier if cooling is already degraded.
    """
    rate = _COMP_RATES[component]
    cascade = _CASCADE_MULT if (
        component != "cooling" and cooling_health_at_day < _CASCADE_THRESHOLD
    ) else 1.0
    # Non-linear: degradation accelerates as health drops below 60
    degraded = max(0, health0 - rate * cascade * days)
    # Extra acceleration below 60% health
    if health0 < 60:
        extra = (60 - health0) / 60 * rate * 0.5 * days
        degraded = max(0, degraded - extra)
    return max(5, round(degraded))


def _component_health_snapshot(vehicle: dict, days: int) -> dict:
    """
    Returns projected component health dict at `days` from now.
    Uses the component AI classes' physics to derive starting health,
    then applies degradation curves forward.
    """
    from services.component_ai.cooling_ai     import CoolingAI
    from services.component_ai.battery_ai     import BatteryAI
    from services.component_ai.motor_ai       import MotorAI
    from services.component_ai.electrical_ai  import ElectricalAI

    v0   = vehicle.get("battery_voltage", 12.0)
    t0   = vehicle.get("temperature", 50.0)
    rpm  = vehicle.get("rpm", 1500)

    # Current component health (day 0 baseline)
    cooling0     = CoolingAI(t0, rpm, v0).run()["health"]
    battery0     = BatteryAI(v0, t0, rpm).run()["health"]
    motor0       = MotorAI(rpm, t0, v0).run()["health"]
    electrical0  = ElectricalAI(v0, rpm, t0).run()["health"]

    # Cooling health at target day (drives cascade)
    cooling_at_day = _project_component_health("cooling", cooling0, days, cooling0)

    return {
        "Cooling":      cooling_at_day,
        "Battery":      _project_component_health("battery",      battery0,    days, cooling_at_day),
        "Motor":        _project_component_health("motor",        motor0,      days, cooling_at_day),
        "Electrical":   _project_component_health("electrical",   electrical0, days, cooling_at_day),
        "Brakes":       _project_component_health("brakes",       75,          days, cooling_at_day),
        "Transmission": _project_component_health("transmission", 80,          days, cooling_at_day),
    }


def _propagation_stage(health: int, failure: float, days: int) -> dict:
    """
    Returns the current failure propagation stage label and description.
    Stages progress as health drops and failure probability rises.
    """
    if failure >= 85 or health < 20:
        return {
            "stage": 4,
            "label": "System Failure",
            "description": "Failure propagation complete — multi-system breakdown imminent",
            "color": "#EF4444",
        }
    if failure >= 65 or health < 35:
        return {
            "stage": 3,
            "label": "Cascade Active",
            "description": "Failure spreading across systems — electrical instability detected",
            "color": "#F97316",
        }
    if failure >= 40 or health < 55:
        return {
            "stage": 2,
            "label": "Degradation",
            "description": "Primary system degrading — secondary components under stress",
            "color": "#FBBF24",
        }
    if failure >= 20 or health < 75:
        return {
            "stage": 1,
            "label": "Early Warning",
            "description": "Initial degradation signals detected — monitor closely",
            "color": "#A78BFA",
        }
    return {
        "stage": 0,
        "label": "Nominal",
        "description": "All systems operating within normal parameters",
        "color": "#34D399",
    }


def _estimate_repair_cost(health: int, failure: float, component_health: dict) -> dict:
    """Estimate repair cost and downtime based on degradation severity."""
    critical_count = sum(1 for h in component_health.values() if h < 35)
    warning_count  = sum(1 for h in component_health.values() if 35 <= h < 60)

    base_cost    = 2000
    cost_per_crit = 8000
    cost_per_warn = 2500
    repair_cost  = base_cost + critical_count * cost_per_crit + warning_count * cost_per_warn

    # Downtime: 1 day per critical component, 0.5 per warning
    downtime_hours = critical_count * 24 + warning_count * 12

    if failure >= 80:
        repair_cost    = round(repair_cost * 1.5)
        downtime_hours = round(downtime_hours * 1.4)

    return {
        "estimated_repair_cost": repair_cost,
        "downtime_hours":        max(4, round(downtime_hours)),
        "currency":              "INR",
    }


def _simulate(days, health, failure, battery, temperature, rpm, rul) -> dict:
    """
    Projects vehicle state at a future checkpoint `days` from now.
    Uses non-linear compounding degradation — not simple linear increments.
    """
    # Step 1 — project sensor values with non-linear physics
    future_temp    = _project_temperature(temperature, days)
    future_battery = _project_voltage(battery, future_temp, days)
    future_rul     = max(0, rul - days)

    # Step 2 — build simulated sensor snapshot
    simulated_sensors = {
        "health_score":        health,
        "failure_probability": failure,
        "battery_voltage":     future_battery,
        "temperature":         future_temp,
        "rpm":                 rpm,
        "rul_days":            future_rul,
    }

    # Step 3 — run ML models on simulated sensors
    future_health  = predict_future_health(simulated_sensors)
    future_failure = predict_future_failure(simulated_sensors)
    future_rul_ml  = predict_future_rul(simulated_sensors)
    priority       = predict_future_priority(future_health, future_failure, future_rul_ml)

    # Step 4 — apply additional physics-based health penalty on top of ML
    # This ensures visible progression even when ML output is stable
    temp_penalty  = max(0, (future_temp - 85) * 0.20)
    volt_penalty  = max(0, (11.5 - future_battery) * 3.5)
    day_penalty   = math.log1p(days) * 1.8   # logarithmic time decay
    total_penalty = temp_penalty + volt_penalty + day_penalty

    adjusted_health  = max(5,   round(future_health  - total_penalty))
    adjusted_failure = min(100, round(future_failure + total_penalty * 0.8))

    if adjusted_health < 25:
        status = "Critical"
    elif adjusted_health < 60:
        status = "Warning"
    else:
        status = "Healthy"

    return {
        "health":               adjusted_health,
        "failure_probability":  adjusted_failure,
        "battery_voltage":      future_battery,
        "temperature":          future_temp,
        "rpm":                  rpm,
        "rul_days":             future_rul_ml,
        "priority":             priority,
        "status":               status,
    }


def forecast_future(vehicle: dict) -> dict:
    """
    Returns Day1 / Day7 / Day15 / Day30 projections using
    non-linear compounding degradation model.
    """
    health      = vehicle.get("health_score", 50)
    failure     = vehicle.get("failure_probability", 50)
    battery     = vehicle.get("battery_voltage", 12.0)
    temperature = vehicle.get("temperature", 50)
    rpm         = vehicle.get("rpm", 1500)
    rul         = vehicle.get("rul_days", vehicle.get("rul", 15))

    args = (health, failure, battery, temperature, rpm, rul)

    return {
        "day1":  _simulate(1,  *args),
        "day7":  _simulate(7,  *args),
        "day15": _simulate(15, *args),
        "day30": _simulate(30, *args),
    }


def simulate_repair(vehicle: dict) -> dict:
    """Mode A — vehicle repaired today. Health/RUL restored, risk drops."""
    repaired = {
        **vehicle,
        "health_score":         95,
        "failure_probability":  5,
        "rul_days":             120,
        "temperature":          min(vehicle.get("temperature", 50), 70),
    }
    return {
        "mode":                "Repair Today",
        "health":              95,
        "failure_probability": 5,
        "rul_days":            120,
        "status":              "Operational",
        "forecast":            forecast_future(repaired),
    }


def simulate_ignore(vehicle: dict) -> dict:
    """Mode B — no repair. Projects degradation as-is."""
    return {
        "mode":     "No Repair",
        "forecast": forecast_future(vehicle),
    }
