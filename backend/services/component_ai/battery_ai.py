"""
Battery AI — Intelligence layer for the Battery Digital Twin
=============================================================
The Battery Twin calls this brain instead of calling the generic ML models
directly. Each method models a specific failure mode with multi-factor
physics, then feeds a refined sensor snapshot to the ML pipeline.

Methods
-------
predict_capacity()        — State of Charge / capacity fade from voltage + temperature
predict_voltage_drop()    — Voltage degradation rate under load
predict_thermal_runaway() — Thermal runaway probability (temp + voltage interaction)
predict_rul()             — Battery RUL using Arrhenius-inspired degradation curve
run()                     — Aggregates all four into a single component intelligence result
"""

from services.twin_prediction_service import (
    predict_future_health,
    predict_future_failure,
    predict_future_rul,
)


class BatteryAI:
    # Thresholds
    _NOMINAL_V   = 12.6
    _MIN_V       = 9.0
    _MAX_V       = 13.2
    _THERMAL_MAX = 60.0     # °C — above this, capacity fade accelerates

    def __init__(self, voltage: float, temperature: float, rpm: int):
        self.voltage     = voltage
        self.temperature = temperature
        self.rpm         = rpm

    # ------------------------------------------------------------------ #
    # 1. Capacity / State-of-Charge model
    # ------------------------------------------------------------------ #
    def predict_capacity(self) -> dict:
        """
        Multi-factor capacity model:
            - Voltage contributes 60 % of capacity signal
            - Temperature stress reduces effective capacity
            - Interaction term captures combined degradation
        """
        v_factor    = (self.voltage - self._MIN_V) / (self._MAX_V - self._MIN_V)
        t_penalty   = max(0, (self.temperature - self._THERMAL_MAX) / 60) * 0.25
        interaction = max(0, (self._NOMINAL_V - self.voltage) * (self.temperature / 80)) * 0.05
        capacity    = max(0.0, min(1.0, v_factor - t_penalty - interaction))
        return {
            "capacity_pct":     round(capacity * 100, 1),
            "v_factor":         round(v_factor, 3),
            "thermal_penalty":  round(t_penalty, 3),
        }

    # ------------------------------------------------------------------ #
    # 2. Voltage drop model
    # ------------------------------------------------------------------ #
    def predict_voltage_drop(self) -> dict:
        """
        Voltage drop rate under load:
            - Base drop from nominal (12.6 V)
            - RPM load amplifies drop (higher RPM = higher current draw)
            - Temperature accelerates electrochemical degradation
        """
        base_drop    = max(0, self._NOMINAL_V - self.voltage)
        load_factor  = self.rpm / 7000                             # 0–1 normalised
        temp_factor  = max(0, (self.temperature - 40) / 80)
        drop_rate    = round(base_drop * (1 + load_factor * 0.4 + temp_factor * 0.3), 3)
        severity     = "Critical" if drop_rate > 1.5 else "High" if drop_rate > 0.8 else "Normal"
        return {
            "drop_rate":    drop_rate,
            "load_factor":  round(load_factor, 3),
            "severity":     severity,
        }

    # ------------------------------------------------------------------ #
    # 3. Thermal runaway probability
    # ------------------------------------------------------------------ #
    def predict_thermal_runaway(self) -> dict:
        """
        Thermal runaway risk:
            - Exponential rise above 70 °C (Arrhenius relationship)
            - Low voltage + high temperature = highest risk (combined stress)
        """
        temp_risk = max(0, (self.temperature - 70) / 40) ** 2 * 60
        volt_risk = max(0, (11.5 - self.voltage) * 8)
        combined  = min(100, temp_risk + volt_risk)
        risk_label = "Critical" if combined > 60 else "High" if combined > 30 else "Low"
        return {
            "thermal_runaway_prob": round(combined, 1),
            "risk_label":           risk_label,
        }

    # ------------------------------------------------------------------ #
    # 4. RUL model (Arrhenius-inspired degradation)
    # ------------------------------------------------------------------ #
    def predict_rul(self) -> int:
        """
        Battery RUL using temperature-accelerated degradation:
            Base RUL set by voltage band; temperature > 60 °C halves RUL
            (Arrhenius rule: every 10 °C above 60 °C roughly halves lifetime).
        """
        if self.voltage >= 12.4:   base = 30
        elif self.voltage >= 12.0: base = 20
        elif self.voltage >= 11.5: base = 12
        elif self.voltage >= 11.0: base = 6
        else:                       base = 2

        over_temp  = max(0, (self.temperature - 60) / 10)
        temp_factor = 2 ** over_temp           # doubles every 10 °C over threshold
        return max(1, round(base / temp_factor))

    # ------------------------------------------------------------------ #
    # 5. Confidence score
    # ------------------------------------------------------------------ #
    def _confidence(self) -> int:
        """Higher confidence when multiple sensors agree on severity."""
        severe_voltage = self.voltage < 11.5
        severe_temp    = self.temperature > 75
        if severe_voltage and severe_temp: return 97
        if severe_voltage or severe_temp:  return 91
        return 84

    # ------------------------------------------------------------------ #
    # 6. Aggregated run — called by BatteryTwin
    # ------------------------------------------------------------------ #
    def run(self) -> dict:
        """
        Combines all four models into a refined sensor snapshot,
        then passes it to the shared Health / Failure / RUL ML models.

        Returns the complete Battery intelligence payload.
        """
        capacity  = self.predict_capacity()
        vdrop     = self.predict_voltage_drop()
        thermal   = self.predict_thermal_runaway()
        rul       = self.predict_rul()

        # Refined health score: capacity-weighted + thermal penalty
        refined_health = round(
            capacity["capacity_pct"] * 0.60 +
            max(0, 100 - thermal["thermal_runaway_prob"]) * 0.25 +
            max(0, 100 - vdrop["drop_rate"] * 20) * 0.15
        )

        sensors = {
            "health_score":        max(5, min(100, refined_health)),
            "failure_probability": thermal["thermal_runaway_prob"],
            "battery_voltage":     self.voltage,
            "temperature":         self.temperature,
            "rpm":                 self.rpm,
            "rul_days":            rul,
        }

        ml_health  = predict_future_health(sensors)
        ml_failure = predict_future_failure(sensors)
        ml_rul     = predict_future_rul(sensors)

        # Blend component AI with ML output
        final_health  = round(refined_health * 0.55 + ml_health  * 0.45)
        final_failure = round(thermal["thermal_runaway_prob"] * 0.40 + ml_failure * 0.60, 1)
        final_rul     = min(rul, ml_rul)          # conservative: take minimum

        return {
            "health":              max(5, min(100, final_health)),
            "failure_probability": round(min(100, final_failure), 1),
            "rul":                 final_rul,
            "confidence":          self._confidence(),
            "models": {
                "capacity":       capacity,
                "voltage_drop":   vdrop,
                "thermal_runaway": thermal,
            },
        }
