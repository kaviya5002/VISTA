"""
Component Twin Engine
=====================
Orchestrates all six component digital twins for a vehicle.

Flow
----
    vehicle dict
        ↓
    BatteryTwin.predict()   → battery state
    MotorTwin.predict()     → motor state
    CoolingTwin.predict()   → cooling state
    BrakeTwin.predict()     → brake state
    ElectricalTwin.predict()→ electrical state
    TransmissionTwin.predict() → transmission state
        ↓
    Record history → compute trend
        ↓
    Merge + aggregate vehicle health
        ↓
    Return component_twin payload
"""

from models.digital_twins.battery_twin      import BatteryTwin
from models.digital_twins.motor_twin        import MotorTwin
from models.digital_twins.cooling_twin      import CoolingTwin
from models.digital_twins.brake_twin        import BrakeTwin
from models.digital_twins.electrical_twin   import ElectricalTwin
from models.digital_twins.transmission_twin import TransmissionTwin

_WEIGHTS = {
    "battery":      0.25,
    "motor":        0.25,
    "cooling":      0.20,
    "brakes":       0.15,
    "electrical":   0.10,
    "transmission": 0.05,
}

_TWIN_CLASSES = {
    "battery":      BatteryTwin,
    "motor":        MotorTwin,
    "cooling":      CoolingTwin,
    "brakes":       BrakeTwin,
    "electrical":   ElectricalTwin,
    "transmission": TransmissionTwin,
}


def build_component_twin(vehicle: dict) -> dict:
    twin_instances = {k: cls(vehicle) for k, cls in _TWIN_CLASSES.items()}

    # ── 1. Run predictions and record health history ───────────────────
    twins = {}
    for key, inst in twin_instances.items():
        result = inst.predict()
        inst._record_health(result["component"], result["health"])
        result["trend"] = inst._trend(result["component"])
        twins[key] = result

    # ── 2. Explanations (confidence + reasons) ─────────────────────────
    explanations = [
        twin_instances[k].explain() for k in _TWIN_CLASSES
    ]

    # ── 3. Weighted vehicle health ─────────────────────────────────────
    scores = {key: result["health"] for key, result in twins.items()}
    vehicle_health = round(sum(scores[k] * w for k, w in _WEIGHTS.items()))

    # ── 4. Critical components ─────────────────────────────────────────
    critical = [
        twins[k]["component"]
        for k in twins
        if twins[k]["health"] < 45 or twins[k].get("failure_probability", 0) > 70
    ]

    # ── 5. Vehicle status ──────────────────────────────────────────────
    warning_components = [
        k for k in twins
        if 45 <= twins[k]["health"] < 75
    ]
    if vehicle_health < 25 or critical:
        vehicle_status = "Critical"
    elif vehicle_health < 75 or len(warning_components) >= 2:
        vehicle_status = "Warning"
    else:
        vehicle_status = "Healthy"

    return {
        "vehicle_id":          vehicle.get("vehicle_id"),
        "vehicle_health":      vehicle_health,
        "vehicle_status":      vehicle_status,
        "critical_components": critical,
        "component_scores": {
            twins[k]["component"]: scores[k] for k in scores
        },
        "battery":      twins["battery"],
        "motor":        twins["motor"],
        "cooling":      twins["cooling"],
        "brakes":       twins["brakes"],
        "electrical":   twins["electrical"],
        "transmission": twins["transmission"],
        "explanations": explanations,
    }


def build_component_forecasts(vehicle: dict) -> dict:
    return {
        "battery":      BatteryTwin(vehicle).forecast(),
        "motor":        MotorTwin(vehicle).forecast(),
        "cooling":      CoolingTwin(vehicle).forecast(),
        "brakes":       BrakeTwin(vehicle).forecast(),
        "electrical":   ElectricalTwin(vehicle).forecast(),
        "transmission": TransmissionTwin(vehicle).forecast(),
    }


def build_component_simulations(vehicle: dict) -> dict:
    return {
        "battery":      BatteryTwin(vehicle).simulate(),
        "motor":        MotorTwin(vehicle).simulate(),
        "cooling":      CoolingTwin(vehicle).simulate(),
        "brakes":       BrakeTwin(vehicle).simulate(),
        "electrical":   ElectricalTwin(vehicle).simulate(),
        "transmission": TransmissionTwin(vehicle).simulate(),
    }
