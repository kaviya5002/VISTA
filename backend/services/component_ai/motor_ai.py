"""
Motor AI — Intelligence layer for the Motor Digital Twin
=========================================================
Methods
-------
predict_efficiency()    — Mechanical efficiency from RPM + temperature
predict_overload()      — Overload probability from RPM + torque proxy
predict_temperature()   — Thermal state and risk of thermal cutout
predict_rul()           — Motor RUL from cumulative stress model
run()                   — Aggregates all four
"""

from services.twin_prediction_service import (
    predict_future_health,
    predict_future_failure,
    predict_future_rul,
)


class MotorAI:
    _NOMINAL_RPM  = 2500
    _MAX_RPM      = 7000
    _REDLINE      = 6000
    _OPTIMAL_TEMP = 60.0

    def __init__(self, rpm: int, temperature: float, battery_voltage: float):
        self.rpm     = rpm
        self.temp    = temperature
        self.voltage = battery_voltage

    # ------------------------------------------------------------------ #
    # 1. Mechanical efficiency model
    # ------------------------------------------------------------------ #
    def predict_efficiency(self) -> dict:
        """
        Efficiency drops at high RPM (friction losses) and high temperature
        (viscosity loss in lubricants). Modelled as dual Gaussian penalty.
        """
        rpm_loss  = max(0, (self.rpm - self._NOMINAL_RPM) / (self._MAX_RPM - self._NOMINAL_RPM)) * 30
        temp_loss = max(0, (self.temp - self._OPTIMAL_TEMP) / 60) * 20
        eff       = round(100 - rpm_loss - temp_loss, 1)
        return {
            "efficiency_pct": max(10, min(100, eff)),
            "rpm_loss":        round(rpm_loss, 2),
            "temp_loss":       round(temp_loss, 2),
        }

    # ------------------------------------------------------------------ #
    # 2. Overload probability
    # ------------------------------------------------------------------ #
    def predict_overload(self) -> dict:
        """
        Torque is estimated from RPM via inverse relationship.
        Overload occurs when mechanical stress index > threshold.
        """
        torque_est    = max(3, round(60 - (self.rpm / self._MAX_RPM) * 40))
        stress_index  = (self.rpm / self._REDLINE) * torque_est
        overload_prob = min(100, max(0, (stress_index - 30) * 2.5))
        return {
            "torque_estimate":  torque_est,
            "stress_index":     round(stress_index, 2),
            "overload_prob":    round(overload_prob, 1),
        }

    # ------------------------------------------------------------------ #
    # 3. Thermal model
    # ------------------------------------------------------------------ #
    def predict_temperature(self) -> dict:
        """
        Predicts thermal cutout risk.
        High RPM generates heat; low voltage forces the motor to draw
        higher current, increasing resistive heating.
        """
        rpm_heat   = max(0, (self.rpm - 3000) / 4000) * 40
        volt_heat  = max(0, (13.0 - self.voltage) * 3)
        total_heat = self.temp + rpm_heat + volt_heat
        cutout_risk = min(100, max(0, (total_heat - 90) * 3))
        return {
            "estimated_temp":  round(total_heat, 1),
            "cutout_risk":     round(cutout_risk, 1),
            "thermal_state":   "Critical" if total_heat > 110 else "High" if total_heat > 90 else "Normal",
        }

    # ------------------------------------------------------------------ #
    # 4. RUL model (cumulative stress)
    # ------------------------------------------------------------------ #
    def predict_rul(self) -> int:
        """
        RUL decreases non-linearly with RPM above nominal and temperature
        above optimal. High RPM + high temp = dramatic RUL reduction.
        """
        rpm_stress  = max(0, (self.rpm  - self._NOMINAL_RPM) / self._MAX_RPM)
        temp_stress = max(0, (self.temp - self._OPTIMAL_TEMP) / 100)
        stress      = rpm_stress * 0.6 + temp_stress * 0.4
        base        = 30
        return max(1, round(base * (1 - stress)))

    # ------------------------------------------------------------------ #
    # 5. Confidence
    # ------------------------------------------------------------------ #
    def _confidence(self) -> int:
        if self.rpm > self._REDLINE or self.temp > 100: return 95
        if self.rpm > 4500 or self.temp > 80:           return 88
        return 80

    # ------------------------------------------------------------------ #
    # 6. Aggregated run
    # ------------------------------------------------------------------ #
    def run(self) -> dict:
        eff      = self.predict_efficiency()
        overload = self.predict_overload()
        thermal  = self.predict_temperature()
        rul      = self.predict_rul()

        refined_health = round(
            eff["efficiency_pct"]                   * 0.50 +
            max(0, 100 - overload["overload_prob"]) * 0.30 +
            max(0, 100 - thermal["cutout_risk"])    * 0.20
        )

        sensors = {
            "health_score":        max(5, min(100, refined_health)),
            "failure_probability": overload["overload_prob"],
            "battery_voltage":     self.voltage,
            "temperature":         self.temp,
            "rpm":                 self.rpm,
            "rul_days":            rul,
        }

        ml_health  = predict_future_health(sensors)
        ml_failure = predict_future_failure(sensors)
        ml_rul     = predict_future_rul(sensors)

        final_health  = round(refined_health * 0.55 + ml_health  * 0.45)
        final_failure = round(overload["overload_prob"] * 0.35 + ml_failure * 0.65, 1)
        final_rul     = min(rul, ml_rul)

        return {
            "health":              max(5, min(100, final_health)),
            "failure_probability": round(min(100, final_failure), 1),
            "rul":                 final_rul,
            "confidence":          self._confidence(),
            "models": {
                "efficiency": eff,
                "overload":   overload,
                "thermal":    thermal,
            },
        }
