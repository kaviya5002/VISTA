"""
Transmission Digital Twin
==========================
Delegates all intelligence to TransmissionAI (services/component_ai/transmission_ai.py).
"""
from models.digital_twins.base_twin import BaseComponentTwin
from services.component_ai.transmission_ai import TransmissionAI


class TransmissionTwin(BaseComponentTwin):

    def _ai(self) -> TransmissionAI:
        return TransmissionAI(
            rpm             = self.vehicle.get("rpm", 1500),
            speed           = self.vehicle.get("speed", 60),
            temperature     = self.vehicle.get("temperature", 50),
            battery_voltage = self.vehicle.get("battery_voltage", 12.0),
        )

    def predict(self) -> dict:
        rpm   = self.vehicle.get("rpm", 1500)
        speed = self.vehicle.get("speed", 60)
        result = self._ai().run()
        return {
            "component":           "Transmission",
            "health":              result["health"],
            "failure_probability": result["failure_probability"],
            "rul":                 result["rul"],
            "confidence":          result["confidence"],
            "status":              self._status(result["health"]),
            "risk":                self._risk_label(result["failure_probability"]),
            "risk_color":          self._risk_color(result["health"]),
            "sensors": {
                "rpm":           rpm,
                "speed":         speed,
                "gear_wear":     result["models"]["gear_wear"]["gear_wear_pct"],
                "fluid_state":   result["models"]["fluid"]["fluid_state"],
                "clutch_slip":   result["models"]["clutch_slip"]["slip_state"],
            },
            "sub_models": result["models"],
        }

    def simulate(self) -> dict:
        result = TransmissionAI(
            rpm             = min(self.vehicle.get("rpm", 1500), 2500),
            speed           = self.vehicle.get("speed", 60),
            temperature     = 60,
            battery_voltage = self.vehicle.get("battery_voltage", 12.0),
        ).run()
        return {"scenario": "Transmission Service", **result,
                "status": self._status(result["health"]),
                "risk_color": self._risk_color(result["health"])}

    def forecast(self) -> dict:
        rpm   = self.vehicle.get("rpm", 1500)
        speed = self.vehicle.get("speed", 60)
        temp  = self.vehicle.get("temperature", 50)
        v     = self.vehicle.get("battery_voltage", 12.0)
        return {
            "day7":  TransmissionAI(rpm, speed, round(temp + 7*0.15,  1), round(max(8.0, v - 7*0.02),  2)).run(),
            "day15": TransmissionAI(rpm, speed, round(temp + 15*0.15, 1), round(max(8.0, v - 15*0.02), 2)).run(),
            "day30": TransmissionAI(rpm, speed, round(temp + 30*0.15, 1), round(max(8.0, v - 30*0.02), 2)).run(),
        }

    def explain(self) -> dict:
        ai     = self._ai()
        result = ai.run()
        gear   = ai.predict_gear_wear()
        fluid  = ai.predict_fluid()
        slip   = ai.predict_clutch_slip()
        reasons = []

        if slip["slip_state"] != "Normal":
            reasons.append(f"Clutch slip: {slip['slip_state']} — slip probability {slip['slip_prob']}%")
        if fluid["change_needed"]:
            reasons.append(f"Fluid degraded — {fluid['fluid_state']} (health {fluid['fluid_health']}%)")
        if gear["gear_wear_pct"] > 50:
            reasons.append(f"Gear wear {gear['gear_wear_pct']}% — RPM/speed ratio {gear['rpm_speed_ratio']}")
        if not reasons:
            reasons.append("Transmission operating normally")

        return {
            "component":  "Transmission",
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
