"""
Electrical AI — Intelligence layer for the Electrical Digital Twin
==================================================================
Methods
-------
predict_alternator()      — Charging output health from voltage + RPM
predict_wiring()          — Wiring degradation from voltage drop + heat
predict_load_balance()    — Electrical load vs supply balance
run()                     — Aggregates all three
"""

from services.twin_prediction_service import (
    predict_future_health,
    predict_future_failure,
    predict_future_rul,
)


class ElectricalAI:
    _CHARGE_MIN = 13.5
    _CHARGE_MAX = 14.8

    def __init__(self, battery_voltage: float, rpm: int, temperature: float):
        self.voltage = battery_voltage
        self.rpm     = rpm
        self.temp    = temperature

    # ------------------------------------------------------------------ #
    # 1. Alternator health model
    # ------------------------------------------------------------------ #
    def predict_alternator(self) -> dict:
        """
        At running RPM (> 1000), alternator should output 13.5–14.8 V.
        Under- or over-charging both indicate alternator or regulator faults.
        """
        if self.rpm < 800:
            return {"alternator_health": 100, "state": "Idle", "fault_prob": 0}

        if self.voltage < self._CHARGE_MIN:
            gap   = self._CHARGE_MIN - self.voltage
            fault = min(100, gap * 25)
            state = "Undercharging"
        elif self.voltage > self._CHARGE_MAX:
            gap   = self.voltage - self._CHARGE_MAX
            fault = min(100, gap * 30)
            state = "Overcharging"
        else:
            fault = 0
            state = "Normal"

        return {
            "alternator_health": max(5, round(100 - fault)),
            "state":             state,
            "fault_prob":        round(fault, 1),
        }

    # ------------------------------------------------------------------ #
    # 2. Wiring degradation
    # ------------------------------------------------------------------ #
    def predict_wiring(self) -> dict:
        """
        Wiring insulation degrades with temperature.
        Voltage drop across connectors indicates resistance increase.
        """
        temp_deg  = max(0, (self.temp - 70) / 50) * 40
        v_drop    = max(0, (13.0 - self.voltage)) * 8
        deg_pct   = min(100, temp_deg + v_drop)
        return {
            "wiring_integrity": max(0, round(100 - deg_pct, 1)),
            "degradation_pct":  round(deg_pct, 1),
        }

    # ------------------------------------------------------------------ #
    # 3. Load balance
    # ------------------------------------------------------------------ #
    def predict_load_balance(self) -> dict:
        """
        At high RPM, electrical demand increases.
        Low voltage under load = supply can't meet demand.
        """
        demand  = min(1.0, self.rpm / 6000)
        supply  = min(1.0, max(0, (self.voltage - 11.0) / 3.0))
        balance = round((supply - demand * 0.6) * 100, 1)
        return {
            "load_balance":  max(-100, min(100, balance)),
            "overloaded":    balance < -10,
        }

    def _confidence(self) -> int:
        return 90 if self.voltage < 12.0 else 82

    def run(self) -> dict:
        alt   = self.predict_alternator()
        wire  = self.predict_wiring()
        load  = self.predict_load_balance()
        rul   = 30 if self.voltage >= 13.0 else 18 if self.voltage >= 12.0 else 8

        overload_penalty = 20 if load["overloaded"] else 0
        refined_health = round(
            alt["alternator_health"]       * 0.45 +
            wire["wiring_integrity"]       * 0.35 +
            max(0, 100 - alt["fault_prob"] - overload_penalty) * 0.20
        )

        sensors = {
            "health_score":        max(5, min(100, refined_health)),
            "failure_probability": alt["fault_prob"],
            "battery_voltage":     self.voltage,
            "temperature":         self.temp,
            "rpm":                 self.rpm,
            "rul_days":            rul,
        }

        ml_health  = predict_future_health(sensors)
        ml_failure = predict_future_failure(sensors)
        ml_rul     = predict_future_rul(sensors)

        return {
            "health":              max(5, min(100, round(refined_health * 0.55 + ml_health  * 0.45))),
            "failure_probability": round(min(100, alt["fault_prob"] * 0.40 + ml_failure * 0.60), 1),
            "rul":                 min(rul, ml_rul),
            "confidence":          self._confidence(),
            "models": {
                "alternator":   alt,
                "wiring":       wire,
                "load_balance": load,
            },
        }
