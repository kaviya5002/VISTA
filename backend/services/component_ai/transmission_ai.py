"""
Transmission AI — Intelligence layer for the Transmission Digital Twin
=======================================================================
Methods
-------
predict_gear_wear()     — Gear mesh wear from RPM + speed ratio
predict_fluid()         — Transmission fluid health from temperature
predict_clutch_slip()   — Clutch slip probability from RPM / speed mismatch
run()                   — Aggregates all three
"""

from services.twin_prediction_service import (
    predict_future_health,
    predict_future_failure,
    predict_future_rul,
)


class TransmissionAI:
    def __init__(self, rpm: int, speed: float, temperature: float, battery_voltage: float):
        self.rpm     = rpm
        self.speed   = speed
        self.temp    = temperature
        self.voltage = battery_voltage

    # ------------------------------------------------------------------ #
    # 1. Gear wear model
    # ------------------------------------------------------------------ #
    def predict_gear_wear(self) -> dict:
        """
        Gear wear rate increases with high RPM and with mismatch between
        RPM and vehicle speed (indicates harsh gear changes).
        """
        rpm_wear   = max(0, (self.rpm - 3000) / 4000) * 50
        ratio      = self.rpm / max(self.speed, 1)
        mismatch   = max(0, ratio - 40) * 0.5       # ideal ratio ~40 at cruise
        wear_pct   = min(100, rpm_wear + mismatch)
        return {
            "gear_wear_pct":     round(wear_pct, 1),
            "gear_remaining":    max(0, round(100 - wear_pct, 1)),
            "rpm_speed_ratio":   round(ratio, 2),
        }

    # ------------------------------------------------------------------ #
    # 2. Fluid health model
    # ------------------------------------------------------------------ #
    def predict_fluid(self) -> dict:
        """
        Transmission fluid degrades exponentially above 90 °C.
        Below 70 °C: good. 70–90: degrading. Above 90: critical.
        """
        if self.temp < 70:
            health  = 100
            state   = "Good"
        elif self.temp < 90:
            health  = round(100 - (self.temp - 70) * 3, 1)
            state   = "Degrading"
        else:
            health  = max(5, round(40 - (self.temp - 90) * 2, 1))
            state   = "Critical"
        return {
            "fluid_health":  health,
            "fluid_state":   state,
            "change_needed": health < 40,
        }

    # ------------------------------------------------------------------ #
    # 3. Clutch slip
    # ------------------------------------------------------------------ #
    def predict_clutch_slip(self) -> dict:
        """
        Slip occurs when RPM/speed ratio deviates abnormally from expected
        gear ratio. High RPM with low speed = slipping.
        Not applicable when vehicle is stationary (speed == 0).
        """
        if self.speed < 5:          # parked / idling — slip not measurable
            return {"slip_prob": 0.0, "slip_state": "Normal"}
        expected_ratio = 30     # approximate idle/low gear ratio
        actual_ratio   = self.rpm / self.speed
        slip_index     = max(0, actual_ratio - expected_ratio)
        slip_prob      = min(100, slip_index * 1.5)
        return {
            "slip_prob":    round(slip_prob, 1),
            "slip_state":   "Critical" if slip_prob > 60 else "High" if slip_prob > 30 else "Normal",
        }

    def _confidence(self) -> int:
        return 85 if self.rpm > 5000 or self.temp > 85 else 76

    def run(self) -> dict:
        gear  = self.predict_gear_wear()
        fluid = self.predict_fluid()
        slip  = self.predict_clutch_slip()
        rul   = 30 if self.rpm < 3000 and self.temp < 70 else 22 if self.rpm < 4500 else 10

        refined_health = round(
            gear["gear_remaining"]             * 0.35 +
            fluid["fluid_health"]              * 0.40 +
            max(0, 100 - slip["slip_prob"])    * 0.25
        )

        sensors = {
            "health_score":        max(5, min(100, refined_health)),
            "failure_probability": slip["slip_prob"],
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
            "failure_probability": round(min(100, slip["slip_prob"] * 0.35 + ml_failure * 0.65), 1),
            "rul":                 min(rul, ml_rul),
            "confidence":          self._confidence(),
            "models": {
                "gear_wear":    gear,
                "fluid":        fluid,
                "clutch_slip":  slip,
            },
        }
