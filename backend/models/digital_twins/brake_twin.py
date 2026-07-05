"""
Brake Digital Twin
==================
Delegates all intelligence to BrakeAI (services/component_ai/brake_ai.py).
"""
from models.digital_twins.base_twin import BaseComponentTwin
from services.component_ai.brake_ai import BrakeAI


class BrakeTwin(BaseComponentTwin):

    def _ai(self) -> BrakeAI:
        return BrakeAI(
            speed           = self.vehicle.get("speed", 60),
            temperature     = self.vehicle.get("temperature", 50),
            rpm             = self.vehicle.get("rpm", 1500),
            battery_voltage = self.vehicle.get("battery_voltage", 12.0),
        )

    def predict(self) -> dict:
        result = self._ai().run()
        return {
            "component":           "Brakes",
            "health":              result["health"],
            "failure_probability": result["failure_probability"],
            "rul":                 result["rul"],
            "confidence":          result["confidence"],
            "status":              self._status(result["health"]),
            "risk":                self._risk_label(result["failure_probability"]),
            "risk_color":          self._risk_color(result["health"]),
            "sensors": {
                "speed":           self.vehicle.get("speed", 60),
                "fade_risk":       result["models"]["fade_risk"]["fade_state"],
                "pad_remaining":   result["models"]["pad_wear"]["pad_remaining_pct"],
                "hydraulic":       result["models"]["hydraulic"]["hydraulic_integrity"],
            },
            "sub_models": result["models"],
        }

    def simulate(self) -> dict:
        result = BrakeAI(speed=60, temperature=55,
                         rpm=self.vehicle.get("rpm", 1500),
                         battery_voltage=self.vehicle.get("battery_voltage", 12.0)).run()
        return {"scenario": "Brake Service", **result,
                "status": self._status(result["health"]),
                "risk_color": self._risk_color(result["health"])}

    def forecast(self) -> dict:
        s = self.vehicle.get("speed", 60)
        t = self.vehicle.get("temperature", 50)
        r = self.vehicle.get("rpm", 1500)
        v = self.vehicle.get("battery_voltage", 12.0)
        return {
            "day7":  BrakeAI(s, round(t + 7*0.15, 1),  r, round(max(8.0, v - 7*0.02), 2)).run(),
            "day15": BrakeAI(s, round(t + 15*0.15, 1), r, round(max(8.0, v - 15*0.02), 2)).run(),
            "day30": BrakeAI(s, round(t + 30*0.15, 1), r, round(max(8.0, v - 30*0.02), 2)).run(),
        }

    def explain(self) -> dict:
        ai     = self._ai()
        result = ai.run()
        pad    = ai.predict_pad_wear()
        fade   = ai.predict_fade_risk()
        reasons = []

        if fade["fade_state"] != "Normal":
            reasons.append(f"Brake fade risk: {fade['fade_state']} ({fade['fade_prob']}%)")
        if pad["replace_soon"]:
            reasons.append(f"Brake pads critically worn — {pad['pad_remaining_pct']}% remaining")
        if not reasons:
            reasons.append("Brake system within normal parameters")

        return {
            "component":  "Brakes",
            "health":     result["health"],
            "confidence": result["confidence"],
            "risk_color": self._risk_color(result["health"]),
            "reasons":    reasons,
        }

    @staticmethod
    def _risk_color(health: int) -> str:
        if health >= 75: return "🟢"
        if health >= 45: return "🟡"
        return "🔴"
