"""
AI Failure Propagation Engine
==============================
Uses root cause ML output + sensor data + component twin health
to compute a unique, probabilistic failure propagation path per vehicle.

Architecture:
  Root Cause ML → select starting node in knowledge graph
  → traverse graph weighted by sensor values + component health
  → output ordered chain with per-node probability, timeline, confidence, XAI
"""

import math

# ── Failure Knowledge Graph ────────────────────────────────────────────────
# Each node: { id, label, icon, category }
# Each edge: { from, to, base_weight }  (weight = base transition probability)

NODES = {
    # Power / Electrical
    "battery":          {"label": "Battery",              "icon": "🔋", "category": "electrical"},
    "voltage_drop":     {"label": "Voltage Drop",         "icon": "⚡", "category": "electrical"},
    "electrical_inst":  {"label": "Electrical Instability","icon": "⚡", "category": "electrical"},
    "controller_reset": {"label": "Controller Reset",     "icon": "🖥️", "category": "electrical"},
    "motor_shutdown":   {"label": "Motor Shutdown",       "icon": "🔴", "category": "motor"},

    # Thermal / Cooling
    "coolant_temp":     {"label": "Coolant Temp ↑",       "icon": "🌡️", "category": "cooling"},
    "cooling_eff":      {"label": "Cooling Efficiency ↓", "icon": "❄️", "category": "cooling"},
    "motor_temp":       {"label": "Motor Temperature ↑",  "icon": "🔥", "category": "motor"},
    "power_output":     {"label": "Power Output ↓",       "icon": "📉", "category": "motor"},
    "battery_drain":    {"label": "Battery Consumption ↑","icon": "🔋", "category": "electrical"},

    # Mechanical / Overstrain
    "mech_wear":        {"label": "Mechanical Wear ↑",    "icon": "⚙️", "category": "mechanical"},
    "torque_loss":      {"label": "Torque Loss",          "icon": "🔩", "category": "mechanical"},
    "rpm_fluctuation":  {"label": "RPM Fluctuation",      "icon": "📊", "category": "motor"},
    "motor_stress":     {"label": "Motor Stress",         "icon": "⚠️", "category": "motor"},

    # Brake / Safety
    "brake_wear":       {"label": "Brake Wear",           "icon": "🛑", "category": "brakes"},
    "abs_fault":        {"label": "ABS Fault",            "icon": "⚠️", "category": "brakes"},
    "wheel_stability":  {"label": "Wheel Instability",    "icon": "🔄", "category": "brakes"},
    "safety_risk":      {"label": "Safety Risk",          "icon": "🚨", "category": "safety"},

    # Transmission
    "gear_slip":        {"label": "Gear Slip",            "icon": "⚙️", "category": "transmission"},
    "motor_overload":   {"label": "Motor Overload",       "icon": "🔥", "category": "motor"},
    "battery_drain2":   {"label": "Battery Drain",        "icon": "🔋", "category": "electrical"},

    # Random / Unknown
    "sensor_fault":     {"label": "Sensor Fault",         "icon": "📡", "category": "sensors"},
    "data_anomaly":     {"label": "Data Anomaly",         "icon": "📊", "category": "sensors"},
    "system_check":     {"label": "System Check Required","icon": "🔍", "category": "general"},

    # Terminal nodes
    "vehicle_failure":  {"label": "Vehicle Failure",      "icon": "💥", "category": "terminal"},
    "vehicle_stops":    {"label": "Vehicle Stops",        "icon": "🛑", "category": "terminal"},
    "breakdown":        {"label": "Breakdown",            "icon": "💥", "category": "terminal"},
    "safety_incident":  {"label": "Safety Incident",      "icon": "🚨", "category": "terminal"},
}

# Propagation chains keyed by root cause
CHAINS = {
    "Power Failure": [
        "battery", "voltage_drop", "electrical_inst",
        "controller_reset", "motor_shutdown", "vehicle_stops",
    ],
    "Heat Dissipation": [
        "coolant_temp", "cooling_eff", "motor_temp",
        "power_output", "battery_drain", "vehicle_failure",
    ],
    "Overstrain": [
        "mech_wear", "torque_loss", "rpm_fluctuation",
        "motor_stress", "motor_shutdown", "breakdown",
    ],
    "Tool Wear": [
        "mech_wear", "torque_loss", "rpm_fluctuation",
        "motor_stress", "breakdown",
    ],
    "Random Failure": [
        "sensor_fault", "data_anomaly", "system_check",
        "electrical_inst", "vehicle_failure",
    ],
    "No Failure": [
        "battery", "voltage_drop", "cooling_eff",
        "system_check", "vehicle_failure",
    ],
    # Sensor-derived fallbacks
    "Battery Degradation": [
        "battery", "voltage_drop", "electrical_inst",
        "controller_reset", "motor_shutdown", "vehicle_stops",
    ],
    "Thermal Stress": [
        "coolant_temp", "cooling_eff", "motor_temp",
        "power_output", "battery_drain", "vehicle_failure",
    ],
    "Engine Stress": [
        "mech_wear", "torque_loss", "rpm_fluctuation",
        "motor_stress", "breakdown",
    ],
    "Brake Issue": [
        "brake_wear", "abs_fault", "wheel_stability",
        "safety_risk", "safety_incident",
    ],
    "Transmission Issue": [
        "gear_slip", "motor_overload", "battery_drain2",
        "motor_shutdown", "breakdown",
    ],
}

# Base transition probabilities between consecutive nodes in each chain
_BASE_PROBS = {
    "Power Failure":       [0.92, 0.85, 0.78, 0.68, 0.55],
    "Heat Dissipation":    [0.90, 0.83, 0.74, 0.63, 0.48],
    "Overstrain":          [0.88, 0.80, 0.71, 0.60, 0.44],
    "Tool Wear":           [0.86, 0.78, 0.68, 0.52],
    "Random Failure":      [0.75, 0.65, 0.55, 0.42],
    "No Failure":          [0.40, 0.30, 0.22, 0.14],
    "Battery Degradation": [0.92, 0.85, 0.78, 0.68, 0.55],
    "Thermal Stress":      [0.90, 0.83, 0.74, 0.63, 0.48],
    "Engine Stress":       [0.88, 0.80, 0.71, 0.52],
    "Brake Issue":         [0.85, 0.76, 0.65, 0.50],
    "Transmission Issue":  [0.82, 0.73, 0.62, 0.48],
}


def _sensor_multiplier(vehicle: dict, node_id: str) -> float:
    """Adjust transition probability based on live sensor values."""
    temp    = vehicle.get("temperature", 70)
    voltage = vehicle.get("battery_voltage", 12.0)
    rpm     = vehicle.get("rpm", 3000)
    health  = vehicle.get("health_score", 60)
    fp      = vehicle.get("failure_probability", 30)

    m = 1.0
    cat = NODES.get(node_id, {}).get("category", "")

    if cat == "electrical":
        # Low voltage amplifies electrical failures
        if voltage < 11.5:   m *= 1.30
        elif voltage < 12.0: m *= 1.15
        elif voltage >= 12.5: m *= 0.80

    if cat == "cooling" or cat == "motor":
        # High temp amplifies thermal failures
        if temp > 100:   m *= 1.35
        elif temp > 85:  m *= 1.20
        elif temp > 70:  m *= 1.08
        elif temp < 60:  m *= 0.75

    if cat == "mechanical":
        # High RPM amplifies mechanical wear
        if rpm > 5500:   m *= 1.25
        elif rpm > 4500: m *= 1.12
        elif rpm < 3000: m *= 0.85

    # Overall health and failure probability
    m *= (1.0 + (100 - health) / 200)   # low health → higher prob
    m *= (1.0 + fp / 200)               # high failure prob → higher prob

    return round(min(m, 1.0), 4)


def _node_probability(base: float, vehicle: dict, node_id: str) -> float:
    mult = _sensor_multiplier(vehicle, node_id)
    raw  = base * mult
    return round(min(max(raw, 0.05), 0.98), 2)


def _days_to_node(index: int, chain_len: int, rul: int) -> int:
    """Spread nodes across the RUL window."""
    if chain_len <= 1:
        return rul
    frac = index / (chain_len - 1)
    # Non-linear: early nodes happen sooner, terminal node at RUL
    day = round(rul * (frac ** 0.7))
    return max(day, index)  # at least 1 day per step


def _xai_factors(vehicle: dict, node_id: str) -> list[dict]:
    """Return top contributing sensor factors for a node."""
    temp    = vehicle.get("temperature", 70)
    voltage = vehicle.get("battery_voltage", 12.0)
    rpm     = vehicle.get("rpm", 3000)
    health  = vehicle.get("health_score", 60)
    fp      = vehicle.get("failure_probability", 30)
    rul     = vehicle.get("remaining_useful_life_days", 30)

    cat = NODES.get(node_id, {}).get("category", "")

    factors = []

    # Temperature contribution
    temp_contrib = round(max(0, (temp - 50) / 70 * 40))
    if temp_contrib > 5:
        factors.append({"name": "Temperature", "value": f"{temp}°C", "impact": temp_contrib})

    # Voltage contribution
    volt_contrib = round(max(0, (13.5 - voltage) / 2.5 * 35))
    if volt_contrib > 5:
        factors.append({"name": "Battery Voltage", "value": f"{voltage}V", "impact": volt_contrib})

    # RPM contribution
    rpm_contrib = round(max(0, (rpm - 2000) / 4000 * 25))
    if rpm_contrib > 5:
        factors.append({"name": "RPM", "value": str(rpm), "impact": rpm_contrib})

    # Health contribution
    health_contrib = round(max(0, (100 - health) / 100 * 30))
    if health_contrib > 5:
        factors.append({"name": "Health Score", "value": f"{health}%", "impact": health_contrib})

    # Failure probability
    fp_contrib = round(fp / 100 * 20)
    if fp_contrib > 3:
        factors.append({"name": "Failure Probability", "value": f"{fp}%", "impact": fp_contrib})

    # RUL urgency
    rul_contrib = round(max(0, (30 - rul) / 30 * 15))
    if rul_contrib > 2:
        factors.append({"name": "Remaining Life", "value": f"{rul}d", "impact": rul_contrib})

    # Sort by impact descending, take top 4
    factors.sort(key=lambda x: x["impact"], reverse=True)
    return factors[:4]


def _select_chain(vehicle: dict) -> tuple[str, list[str]]:
    """Pick the propagation chain based on root cause + sensor fallback."""
    root_causes = vehicle.get("root_cause", [])

    # Priority order: use first recognised root cause
    for rc in root_causes:
        if rc in CHAINS:
            return rc, CHAINS[rc]

    # Sensor-based fallback
    temp    = vehicle.get("temperature", 70)
    voltage = vehicle.get("battery_voltage", 12.0)
    rpm     = vehicle.get("rpm", 3000)
    tire    = vehicle.get("tire", vehicle.get("tire_condition", 1))
    trans   = vehicle.get("trans", 0)

    if voltage < 11.5:
        return "Battery Degradation", CHAINS["Battery Degradation"]
    if temp > 90:
        return "Thermal Stress", CHAINS["Thermal Stress"]
    if rpm > 5000:
        return "Engine Stress", CHAINS["Engine Stress"]
    if tire == 0:
        return "Brake Issue", CHAINS["Brake Issue"]
    if trans == 1:
        return "Transmission Issue", CHAINS["Transmission Issue"]
    if temp > 70:
        return "Heat Dissipation", CHAINS["Heat Dissipation"]

    return "No Failure", CHAINS["No Failure"]


def build_propagation(vehicle: dict) -> dict:
    """
    Main entry point. Returns full propagation payload for a vehicle.
    """
    chain_name, node_ids = _select_chain(vehicle)
    base_probs = _BASE_PROBS.get(chain_name, [0.80, 0.70, 0.58, 0.44, 0.32])

    rul    = vehicle.get("remaining_useful_life_days", 30)
    health = vehicle.get("health_score", 60)
    fp     = vehicle.get("failure_probability", 30)

    # Build node list with probabilities, timeline, confidence, XAI
    nodes_out = []
    for i, nid in enumerate(node_ids):
        node_meta = NODES.get(nid, {"label": nid, "icon": "⚙️", "category": "general"})

        # First node probability = failure_probability / 100 adjusted
        if i == 0:
            base = min(0.98, fp / 100 + 0.15)
        else:
            base = base_probs[min(i - 1, len(base_probs) - 1)]

        prob       = _node_probability(base, vehicle, nid)
        day        = _days_to_node(i, len(node_ids), rul)
        confidence = round(min(98, max(60, 95 - i * 4 + (fp / 20))))
        severity   = (
            "critical" if prob >= 0.75 else
            "high"     if prob >= 0.55 else
            "warning"  if prob >= 0.35 else
            "healthy"
        )

        nodes_out.append({
            "id":         nid,
            "label":      node_meta["label"],
            "icon":       node_meta["icon"],
            "category":   node_meta["category"],
            "probability": prob,
            "day":         day,
            "confidence":  confidence,
            "severity":    severity,
            "xai_factors": _xai_factors(vehicle, nid),
        })

    # AI reasoning sentences
    temp    = vehicle.get("temperature", 70)
    voltage = vehicle.get("battery_voltage", 12.0)
    rpm     = vehicle.get("rpm", 3000)

    reasoning = [
        f"Root cause analysis identified: {chain_name}.",
        f"Battery voltage at {voltage}V — {'critical' if voltage < 11.5 else 'degraded' if voltage < 12.0 else 'nominal'}.",
        f"Temperature at {temp}°C — {'exceeds safe threshold' if temp > 90 else 'elevated' if temp > 70 else 'within range'}.",
        f"RPM at {rpm} — {'high stress' if rpm > 5000 else 'elevated' if rpm > 4000 else 'normal'}.",
        f"Remaining useful life: {rul} days — {'urgent intervention required' if rul <= 7 else 'monitor closely' if rul <= 14 else 'schedule maintenance'}.",
        f"Fleet Optimizer confidence: {vehicle.get('confidence_score', 88)}%.",
    ]

    # Overall risk
    terminal_prob = nodes_out[-1]["probability"] if nodes_out else 0
    overall_risk  = (
        "Critical" if terminal_prob >= 0.50 else
        "High"     if terminal_prob >= 0.35 else
        "Medium"   if terminal_prob >= 0.20 else
        "Low"
    )

    return {
        "chain_name":    chain_name,
        "overall_risk":  overall_risk,
        "terminal_probability": terminal_prob,
        "rul":           rul,
        "nodes":         nodes_out,
        "reasoning":     reasoning,
        "vehicle_id":    vehicle.get("vehicle_id"),
        "health_score":  health,
        "failure_probability": fp,
    }
