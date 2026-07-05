"""
Cooling AI — Intelligence layer for the Cooling Digital Twin
=============================================================
Methods
-------
predict_coolant_loss()      — Estimates coolant level from temperature trend
predict_heat_dissipation()  — Radiator efficiency from temp + RPM
predict_fan_failure()       — Fan fault probability from RPM + temp mismatch
predict_rul()               — Cooling RUL
run()                       — Aggregates all three
"""

from services.twin_prediction_service import (
    predict_future_health,
    predict_future_failure,
    predict_future_rul,
)


class CoolingAI:
    _OPTIMAL_TEMP  = 75.0
    _WARNING_TEMP  = 95.0
    _CRITICAL_TEMP = 110.0

    def __init__(self, temperature: float, rpm: int, battery_voltage: float):
        self.temp    = temperature
        self.rpm     = rpm
        self.voltage = battery_voltage

    # ------------------------------------------------------------------ #
    # 1. Coolant loss model
    # ------------------------------------------------------------------ #
    def predict_coolant_loss(self) -> dict:
        """
        High temperature above warning threshold indicates possible
        coolant loss. The excess temperature maps to estimated coolant
        remaining as a percentage.
        """
        excess         = max(0, self.temp - self._OPTIMAL_TEMP)
        loss_pct       = min(100, excess * 2.5)
        coolant_remain = max(0, round(100 - loss_pct, 1))
        return {
            "coolant_remaining_pct": coolant_remain,
            "loss_pct":              round(loss_pct, 1),
            "refill_needed":         coolant_remain < 30,
        }

    # ------------------------------------------------------------------ #
    # 2. Heat dissipation efficiency
    # ------------------------------------------------------------------ #
    def predict_heat_dissipation(self) -> dict:
        """
        Radiator efficiency degrades when:
          - Temperature exceeds warning level (blockage / fouling)
          - High RPM + high temp = insufficient dissipation rate
        """
        temp_ratio   = min(1.0, self.temp / self._CRITICAL_TEMP)
        load_ratio   = min(1.0, self.rpm / 7000)
        dissipation  = round((1 - temp_ratio * 0.6 - load_ratio * 0.2) * 100, 1)
        return {
            "dissipation_efficiency": max(5, dissipation),
            "blockage_risk":          "High" if dissipation < 40 else "Medium" if dissipation < 70 else "Low",
        }

    # ------------------------------------------------------------------ #
    # 3. Fan failure probability
    # ------------------------------------------------------------------ #
    def predict_fan_failure(self) -> dict:
        """
        Fan failure is indicated by:
          - High temperature despite moderate RPM (fan not keeping up)
          - Voltage drop causes fan motor to slow
        """
        expected_cooling = self.rpm / 7000 * 30     # expected °C reduction at this RPM
        actual_excess    = max(0, self.temp - self._OPTIMAL_TEMP)
        gap              = max(0, actual_excess - expected_cooling)
        volt_risk        = max(0, (12.0 - self.voltage) * 5)
        failure_prob     = min(100, gap * 2 + volt_risk)
        return {
            "fan_failure_prob": round(failure_prob, 1),
            "cooling_gap":      round(gap, 1),
            "fan_state":        "Faulty" if failure_prob > 60 else "Weak" if failure_prob > 30 else "Normal",
        }

    # ------------------------------------------------------------------ #
    # 4. Cooling RUL
    # ------------------------------------------------------------------ #
    def predict_rul(self) -> int:
        if self.temp < 80:   return 30
        if self.temp < 95:   return 18
        if self.temp < 105:  return 8
        return 2

    # ------------------------------------------------------------------ #
    # 5. Confidence
    # ------------------------------------------------------------------ #
    def _confidence(self) -> int:
        if self.temp >= self._CRITICAL_TEMP: return 96
        if self.temp >= self._WARNING_TEMP:  return 91
        return 83

    # ------------------------------------------------------------------ #
    # 6. Aggregated run
    # ------------------------------------------------------------------ #
    def run(self) -> dict:
        coolant  = self.predict_coolant_loss()
        dissip   = self.predict_heat_dissipation()
        fan      = self.predict_fan_failure()
        rul      = self.predict_rul()

        refined_health = round(
            coolant["coolant_remaining_pct"]         * 0.35 +
            dissip["dissipation_efficiency"]          * 0.40 +
            max(0, 100 - fan["fan_failure_prob"])     * 0.25
        )

        sensors = {
            "health_score":        max(5, min(100, refined_health)),
            "failure_probability": fan["fan_failure_prob"],
            "battery_voltage":     self.voltage,
            "temperature":         self.temp,
            "rpm":                 self.rpm,
            "rul_days":            rul,
        }

        ml_health  = predict_future_health(sensors)
        ml_failure = predict_future_failure(sensors)
        ml_rul     = predict_future_rul(sensors)

        final_health  = round(refined_health * 0.55 + ml_health  * 0.45)
        final_failure = round(fan["fan_failure_prob"] * 0.40 + ml_failure * 0.60, 1)
        final_rul     = min(rul, ml_rul)

        return {
            "health":              max(5, min(100, final_health)),
            "failure_probability": round(min(100, final_failure), 1),
            "rul":                 final_rul,
            "confidence":          self._confidence(),
            "models": {
                "coolant_loss":      coolant,
                "heat_dissipation":  dissip,
                "fan_failure":       fan,
            },
        }
