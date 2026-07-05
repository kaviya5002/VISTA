"""
Brake AI — Intelligence layer for the Brake Digital Twin
=========================================================
Methods
-------
predict_pad_wear()      — Pad thickness estimate from speed + temp history
predict_fade_risk()     — Brake fade probability under heat
predict_hydraulic()     — Hydraulic pressure integrity estimate
run()                   — Aggregates all three
"""

from services.twin_prediction_service import (
    predict_future_health,
    predict_future_failure,
    predict_future_rul,
)


class BrakeAI:
    def __init__(self, speed: float, temperature: float, rpm: int, battery_voltage: float):
        self.speed   = speed
        self.temp    = temperature
        self.rpm     = rpm
        self.voltage = battery_voltage

    # ------------------------------------------------------------------ #
    # 1. Pad wear model
    # ------------------------------------------------------------------ #
    def predict_pad_wear(self) -> dict:
        """
        Pad wear rate increases with speed^2 (kinetic energy absorbed)
        and degrades faster at high temperatures.
        """
        speed_wear = (self.speed / 120) ** 2 * 60
        temp_wear  = max(0, (self.temp - 60) / 60) * 20
        wear_pct   = min(100, speed_wear + temp_wear)
        remaining  = max(0, round(100 - wear_pct, 1))
        return {
            "wear_pct":           round(wear_pct, 1),
            "pad_remaining_pct":  remaining,
            "replace_soon":       remaining < 25,
        }

    # ------------------------------------------------------------------ #
    # 2. Brake fade risk
    # ------------------------------------------------------------------ #
    def predict_fade_risk(self) -> dict:
        """
        Brake fade occurs when friction material overheats.
        High speed + high ambient temperature compound the risk.
        """
        fade_prob = min(100,
            max(0, (self.temp  - 75) * 1.5) +
            max(0, (self.speed - 80) * 0.8)
        )
        return {
            "fade_prob":  round(fade_prob, 1),
            "fade_state": "Critical" if fade_prob > 70 else "High" if fade_prob > 40 else "Normal",
        }

    # ------------------------------------------------------------------ #
    # 3. Hydraulic integrity
    # ------------------------------------------------------------------ #
    def predict_hydraulic(self) -> dict:
        """
        Low battery voltage can indicate ABS/ESP pump stress.
        High temperature accelerates brake fluid boiling point drop.
        """
        fluid_risk = max(0, (self.temp - 80) * 0.8)
        elec_risk  = max(0, (12.0 - self.voltage) * 4)
        integrity  = max(0, round(100 - fluid_risk - elec_risk, 1))
        return {
            "hydraulic_integrity": integrity,
            "fluid_boil_risk":     round(fluid_risk, 1),
        }

    def _confidence(self) -> int:
        return 88 if self.speed > 90 or self.temp > 85 else 78

    def run(self) -> dict:
        pad      = self.predict_pad_wear()
        fade     = self.predict_fade_risk()
        hydraulic = self.predict_hydraulic()
        rul = 30 if self.speed < 70 else 20 if self.speed < 100 else 10

        refined_health = round(
            pad["pad_remaining_pct"]        * 0.40 +
            max(0, 100 - fade["fade_prob"]) * 0.35 +
            hydraulic["hydraulic_integrity"] * 0.25
        )

        sensors = {
            "health_score":        max(5, min(100, refined_health)),
            "failure_probability": fade["fade_prob"],
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
            "failure_probability": round(min(100, fade["fade_prob"] * 0.40 + ml_failure * 0.60), 1),
            "rul":                 min(rul, ml_rul),
            "confidence":          self._confidence(),
            "models": {
                "pad_wear":   pad,
                "fade_risk":  fade,
                "hydraulic":  hydraulic,
            },
        }
