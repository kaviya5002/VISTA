"""
Cooling System Digital Twin
============================
Delegates all intelligence to CoolingAI (services/component_ai/cooling_ai.py).
"""
from models.digital_twins.base_twin import BaseComponentTwin
from services.component_ai.cooling_ai import CoolingAI


class CoolingTwin(BaseComponentTwin):

    def _ai(self) -> CoolingAI:
        return CoolingAI(
            temperature     = self.vehicle.get("temperature", 50),
            rpm             = self.vehicle.get("rpm", 1500),
            battery_voltage = self.vehicle.get("battery_voltage", 12.0),
        )

    def predict(self) -> dict:
        temp   = self.vehicle.get("temperature", 50)
        rpm    = self.vehicle.get("rpm", 1500)
        result = self._ai().run()

        return {
            "component":           "Cooling",
            "health":              result["health"],
            "failure_probability": result["failure_probability"],
            "rul":                 result["rul"],
            "confidence":          result["confidence"],
            "status":              self._status(result["health"]),
            "risk":                self._risk_label(result["failure_probability"]),
            "risk_color":          self._risk_color(result["health"]),
            "sensors": {
                "coolant_temperature":    temp,
                "fan_state":             result["models"]["fan_failure"]["fan_state"],
                "dissipation_efficiency": result["models"]["heat_dissipation"]["dissipation_efficiency"],
                "coolant_remaining":      result["models"]["coolant_loss"]["coolant_remaining_pct"],
            },
            "sub_models": result["models"],
        }

    def simulate(self) -> dict:
        result = CoolingAI(
            temperature     = 75,
            rpm             = self.vehicle.get("rpm", 1500),
            battery_voltage = self.vehicle.get("battery_voltage", 12.0),
        ).run()
        return {"scenario": "Cooling Repair", **result,
                "status": self._status(result["health"]),
                "risk_color": self._risk_color(result["health"])}

    def forecast(self) -> dict:
        temp = self.vehicle.get("temperature", 50)
        rpm  = self.vehicle.get("rpm", 1500)
        v    = self.vehicle.get("battery_voltage", 12.0)
        return {
            "day7":  CoolingAI(round(temp + 7*0.15, 1),  rpm, round(max(8.0, v - 7*0.02), 2)).run(),
            "day15": CoolingAI(round(temp + 15*0.15, 1), rpm, round(max(8.0, v - 15*0.02), 2)).run(),
            "day30": CoolingAI(round(temp + 30*0.15, 1), rpm, round(max(8.0, v - 30*0.02), 2)).run(),
        }

    def explain(self) -> dict:
        ai      = self._ai()
        result  = ai.run()
        coolant = ai.predict_coolant_loss()
        fan     = ai.predict_fan_failure()
        dissip  = ai.predict_heat_dissipation()
        reasons = []

        if fan["fan_state"] != "Normal":
            reasons.append(f"Fan state: {fan['fan_state']} — cooling gap {fan['cooling_gap']}°C")
        if coolant["refill_needed"]:
            reasons.append(f"Coolant low — {coolant['coolant_remaining_pct']}% remaining")
        if dissip["blockage_risk"] != "Low":
            reasons.append(f"Radiator blockage risk: {dissip['blockage_risk']} — efficiency {dissip['dissipation_efficiency']}%")
        if not reasons:
            reasons.append("Cooling system operating normally")

        return {
            "component":  "Cooling",
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
