"""
Timeline Prediction Service
============================
Generates the complete AI-predicted future journey for a vehicle.

Every checkpoint is a complete AI assessment — not just repeated sensor values.
Each node includes:
    - health, failure, rul, status
    - component_health  (all 6 components projected forward)
    - propagation_stage (0–4 cascade stage)
    - ai_narrative      (stage-aware, changes reasoning at each checkpoint)
    - repair_cost + downtime_hours
    - milestone marker
    - confidence

The narrative changes its reasoning at each stage:
    Stage 0 → monitoring language
    Stage 1 → early warning language
    Stage 2 → degradation language
    Stage 3 → cascade / urgency language
    Stage 4 → breakdown / shutdown language
"""

from __future__ import annotations
from engines.simulation_engine import (
    _simulate,
    _component_health_snapshot,
    _propagation_stage,
    _estimate_repair_cost,
)

# ── Checkpoint schedule ────────────────────────────────────────────────────
_CHECKPOINTS = [
    (0,  "Current Status", "Today"),
    (1,  "Tomorrow",       "Day 1"),
    (3,  "3 Days",         "Day 3"),
    (7,  "One Week",       "Day 7"),
    (15, "Two Weeks",      "Day 15"),
    (30, "One Month",      "Day 30"),
]

# ── Milestone thresholds ───────────────────────────────────────────────────
_MILESTONES = [
    (lambda h, f, r: h < 20 or f >= 88,          "breakdown",    "Predicted Breakdown",       "#EF4444", "💥"),
    (lambda h, f, r: f >= 68 or h < 32,          "critical",     "Critical Warning",          "#F97316", "🚨"),
    (lambda h, f, r: f >= 40 or h < 55,          "maintenance",  "Maintenance Recommended",   "#FBBF24", "🔧"),
    (lambda h, f, r: h < 75 and h >= 55,         "health_drop",  "Health Dropping",           "#A78BFA", "📉"),
    (lambda h, f, r: r <= 5,                      "rul_critical", "End of Useful Life",        "#EF4444", "⏱️"),
    (lambda h, f, r: r <= 10 and r > 5,           "rul_low",      "RUL Running Low",           "#FBBF24", "⏳"),
]


def _detect_milestone(health: int, failure: float, rul: int) -> dict | None:
    for condition, mtype, label, color, icon in _MILESTONES:
        if condition(health, failure, rul):
            return {"type": mtype, "label": label, "color": color, "icon": icon}
    return None


# ── Stage-aware narrative engine ───────────────────────────────────────────

# Each entry: (stage, day_range, condition_fn) → narrative lines
# condition_fn receives (health, failure, temp, voltage, comp_health, health_delta, failure_delta)

def _ai_narrative(
    day: int,
    health: int,
    failure: float,
    rul: int,
    prev_health: int,
    prev_failure: float,
    temp: float,
    voltage: float,
    comp_health: dict,
    stage: int,
) -> list[str]:
    """
    Generates 2–3 sentences that tell a different story at each checkpoint.
    Reasoning changes based on propagation stage, not just sensor deltas.
    """
    lines: list[str] = []
    health_delta  = health - prev_health
    failure_delta = failure - prev_failure

    # ── Day 0: current state assessment ───────────────────────────────
    if day == 0:
        if stage == 0:
            lines.append("All systems operating within normal parameters.")
            lines.append("No immediate maintenance action required.")
        elif stage == 1:
            worst = min(comp_health, key=comp_health.get)
            lines.append(f"{worst} system showing early degradation signals.")
            lines.append("Recommend scheduling a diagnostic inspection.")
        elif stage == 2:
            worst = min(comp_health, key=comp_health.get)
            lines.append(f"Vehicle operating under stress — {worst} health at {comp_health[worst]}%.")
            lines.append("Cooling efficiency reduced, increasing load on battery and motor.")
        elif stage == 3:
            lines.append(f"Critical degradation detected — failure probability at {round(failure)}%.")
            lines.append("Multiple systems under stress. Immediate workshop visit recommended.")
        else:
            lines.append(f"Vehicle in critical state — health at {health}%, failure risk {round(failure)}%.")
            lines.append("Continued operation risks complete breakdown. Do not delay repair.")
        return lines

    # ── Day 1–3: early progression ─────────────────────────────────────
    if day <= 3:
        if stage <= 1:
            if health_delta <= -3:
                lines.append(f"Health declined {abs(health_delta)}% — degradation beginning.")
            else:
                lines.append("Degradation rate within expected range.")
            if temp > 85:
                lines.append(f"Coolant temperature at {temp}°C — cooling efficiency beginning to decrease.")
            elif temp > 75:
                lines.append(f"Temperature at {temp}°C — monitor cooling system.")
        elif stage == 2:
            lines.append(f"Cooling efficiency reduced — temperature rising to {temp}°C.")
            if voltage < 12.0:
                lines.append(f"Battery under increased electrical load at {voltage}V.")
            lines.append("First maintenance window recommended within this period.")
        elif stage >= 3:
            lines.append(f"Rapid health decline of {abs(health_delta)}% in {day} day(s).")
            lines.append(f"Elevated coolant temperature ({temp}°C) accelerating battery discharge.")
            lines.append("Urgent inspection required — failure cascade beginning.")
        return lines[:3]

    # ── Day 7: one week out ────────────────────────────────────────────
    if day == 7:
        if stage <= 1:
            lines.append(f"Health at {health}% — gradual degradation continuing.")
            if comp_health.get("Cooling", 100) < 65:
                lines.append(f"Cooling health dropped to {comp_health['Cooling']}% — monitor radiator.")
        elif stage == 2:
            lines.append(f"Cooling health at {comp_health.get('Cooling', '?')}% — dissipation efficiency reduced.")
            lines.append(f"Battery under increased electrical load — voltage at {voltage}V.")
            lines.append("First maintenance recommended before end of this week.")
        elif stage == 3:
            lines.append(f"Sustained overheating ({temp}°C) accelerating motor degradation.")
            lines.append(f"Motor health projected at {comp_health.get('Motor', '?')}% — thermal stress accumulating.")
            lines.append(f"Failure probability now {round(failure)}% — breakdown risk becoming significant.")
        else:
            lines.append(f"Motor health critical at {comp_health.get('Motor', '?')}% — thermal shutdown risk.")
            lines.append(f"Electrical instability detected — voltage at {voltage}V under load.")
            lines.append("Vehicle should not continue operation without immediate repair.")
        return lines[:3]

    # ── Day 15: two weeks out ──────────────────────────────────────────
    if day == 15:
        if stage <= 1:
            lines.append(f"Health at {health}% — degradation progressing slowly.")
            lines.append("Schedule preventive maintenance within the next two weeks.")
        elif stage == 2:
            lines.append(f"Motor operating under thermal stress — health at {comp_health.get('Motor', '?')}%.")
            lines.append(f"Electrical instability beginning — voltage declining to {voltage}V.")
            lines.append("Breakdown risk becoming significant without intervention.")
        elif stage == 3:
            lines.append(f"Failure propagation reaching electrical system — health at {comp_health.get('Electrical', '?')}%.")
            lines.append(f"Battery health at {comp_health.get('Battery', '?')}% — near end of charge life.")
            lines.append(f"Failure probability {round(failure)}% — immediate maintenance critical.")
        else:
            lines.append(f"Multi-system failure cascade active — {sum(1 for h in comp_health.values() if h < 35)} components critical.")
            lines.append(f"Predicted motor shutdown within days at current degradation rate.")
            lines.append("Vehicle must be taken out of service immediately.")
        return lines[:3]

    # ── Day 30: one month out ──────────────────────────────────────────
    if day == 30:
        if stage <= 1:
            lines.append(f"Health at {health}% after 30 days — degradation manageable.")
            lines.append("Routine maintenance sufficient to restore full health.")
        elif stage == 2:
            lines.append(f"30-day projection: health at {health}%, failure risk {round(failure)}%.")
            lines.append(f"Cooling and battery systems will require replacement if unserviced.")
            lines.append("Estimated repair cost increases significantly beyond this point.")
        elif stage == 3:
            lines.append(f"Predicted breakdown — health at {health}%, failure probability {round(failure)}%.")
            lines.append(f"Motor and electrical systems projected critical ({comp_health.get('Motor', '?')}% / {comp_health.get('Electrical', '?')}%).")
            lines.append("Immediate repair now prevents complete vehicle loss.")
        else:
            lines.append(f"Predicted complete motor shutdown — health at {health}%.")
            lines.append(f"All primary systems critical — vehicle should not continue operation.")
            lines.append("Failure propagation indicates high probability of irreversible damage.")
        return lines[:3]

    # ── Fallback for any other day ─────────────────────────────────────
    if health_delta <= -8:
        lines.append(f"Health declining by {abs(health_delta)}% — degradation accelerating.")
    if failure_delta >= 10:
        lines.append(f"Failure probability rising by {round(failure_delta)}% under current conditions.")
    if not lines:
        lines.append("Degradation progressing — monitor all systems.")
    return lines[:3]


def _confidence(day: int, health: int, failure: float, stage: int) -> int:
    """
    Confidence decreases with forecast distance.
    Increases when multiple signals converge on the same severity.
    """
    base  = 92
    decay = {0: 0, 1: 0, 3: 1, 7: 3, 15: 6, 30: 10}
    base -= decay.get(day, 10)

    # Convergence boost — high confidence when signals agree
    if health < 35 and failure > 65:
        base = min(98, base + 4)
    elif health >= 80 and failure < 20:
        base = min(98, base + 3)
    elif stage >= 3:
        base = min(98, base + 2)   # high confidence in critical predictions

    return max(58, base)


def _status_color(status: str) -> str:
    return {
        "Healthy":  "#34D399",
        "Warning":  "#FBBF24",
        "Critical": "#F87171",
    }.get(status, "#94A3B8")


def _build_node(
    day: int,
    title: str,
    date_label: str,
    state: dict,
    prev_state: dict,
    vehicle: dict,
) -> dict:
    health  = state["health"]
    failure = round(state["failure_probability"])
    rul     = state["rul_days"]
    status  = state["status"]
    temp    = state["temperature"]
    voltage = state["battery_voltage"]

    # Component health snapshot at this day
    comp_health = _component_health_snapshot(vehicle, day)

    # Propagation stage
    prop = _propagation_stage(health, failure, day)
    stage = prop["stage"]

    # Milestone
    milestone = _detect_milestone(health, failure, rul)

    # Stage-aware narrative
    narrative = _ai_narrative(
        day, health, failure, rul,
        prev_state["health"],
        prev_state["failure_probability"],
        temp, voltage,
        comp_health,
        stage,
    )

    # Repair cost + downtime
    cost_info = _estimate_repair_cost(health, failure, comp_health)

    # Recommended action
    if stage >= 4:
        action = "Take vehicle out of service immediately"
    elif stage == 3:
        action = "Emergency workshop visit required"
    elif stage == 2:
        action = "Schedule maintenance within 7 days"
    elif stage == 1:
        action = "Book diagnostic inspection"
    else:
        action = "Continue monitoring"

    return {
        "day":          day,
        "title":        title,
        "date_label":   date_label,
        "health":       health,
        "failure":      failure,
        "rul":          rul,
        "status":       status,
        "status_color": _status_color(status),
        "priority":     state.get("priority", "Low"),
        "confidence":   _confidence(day, health, failure, stage),
        "milestone":    milestone,
        "narrative":    narrative,
        "propagation":  prop,
        "component_health": comp_health,
        "repair_cost":  cost_info["estimated_repair_cost"],
        "downtime_hours": cost_info["downtime_hours"],
        "recommended_action": action,
        "sensors": {
            "temperature":     temp,
            "battery_voltage": voltage,
            "rpm":             state["rpm"],
        },
        "model":   "Random Forest",
        "dataset": "AI4I 2020 + NASA CMAPSS",
    }


def build_timeline(vehicle: dict) -> dict:
    """
    Main entry point — builds the complete progressive timeline for a vehicle.
    """
    vid      = vehicle["vehicle_id"]
    health0  = vehicle.get("health_score",                  50)
    failure0 = vehicle.get("failure_probability",           30)
    battery0 = vehicle.get("battery_voltage",               12.0)
    temp0    = vehicle.get("temperature",                   50.0)
    rpm0     = vehicle.get("rpm",                           1500)
    rul0     = vehicle.get("remaining_useful_life_days",
               vehicle.get("rul_days", 15))

    state0 = {
        "health":              health0,
        "failure_probability": failure0,
        "battery_voltage":     battery0,
        "temperature":         temp0,
        "rpm":                 rpm0,
        "rul_days":            rul0,
        "priority":            vehicle.get("priority", "Low"),
        "status":              vehicle.get("status", "Healthy"),
    }

    nodes: list[dict] = []
    prev_state = state0

    for day, title, date_label in _CHECKPOINTS:
        state = state0 if day == 0 else _simulate(
            days=day,
            health=health0,
            failure=failure0,
            battery=battery0,
            temperature=temp0,
            rpm=rpm0,
            rul=rul0,
        )
        node = _build_node(day, title, date_label, state, prev_state, vehicle)
        nodes.append(node)
        prev_state = state

    # ── Summary analytics ──────────────────────────────────────────────
    breakdown_day   = next((n["day"] for n in nodes if n["milestone"] and n["milestone"]["type"] == "breakdown"),   None)
    critical_day    = next((n["day"] for n in nodes if n["milestone"] and n["milestone"]["type"] == "critical"),    None)
    maintenance_day = next((n["day"] for n in nodes if n["milestone"] and n["milestone"]["type"] == "maintenance"), None)

    health_series = [n["health"] for n in nodes]
    drop = health_series[0] - health_series[-1]
    if drop >= 20:
        trend = "Rapidly Degrading"
    elif drop >= 8:
        trend = "Degrading"
    elif health_series[-1] > health_series[0]:
        trend = "Stable"
    else:
        trend = "Gradually Degrading"

    # Max propagation stage reached across all checkpoints
    max_stage = max(n["propagation"]["stage"] for n in nodes)

    _NAMES = [
        "Tata Ace EV", "Mahindra eAlfa", "Piaggio Ape E-Xtra", "Euler HiLoad",
        "OSM Rage+",   "Altigreen neEV", "Kinetic Safar Star", "Bajaj RE EV",
        "Etrio Touro",  "Yulu Dex",
    ]
    vehicle_name = _NAMES[(vid - 1) % len(_NAMES)]

    return {
        "vehicle_id":   vid,
        "vehicle_name": vehicle_name,
        "timeline":     nodes,
        "summary": {
            "current_status":        vehicle.get("status", "Healthy"),
            "current_health":        health0,
            "current_failure":       failure0,
            "breakdown_day":         breakdown_day,
            "first_critical_day":    critical_day,
            "first_maintenance_day": maintenance_day,
            "overall_trend":         trend,
            "health_at_day30":       health_series[-1],
            "failure_at_day30":      nodes[-1]["failure"],
            "max_propagation_stage": max_stage,
            "total_repair_cost_day30": nodes[-1]["repair_cost"],
            "downtime_hours_day30":    nodes[-1]["downtime_hours"],
        },
    }
