"""
Electrical System Digital Twin
================================
Delegates all intelligence to ElectricalAI (services/component_ai/electrical_ai.py).
"""
from models.digital_twins.base_twin import BaseComponentTwin
from services.component_ai.electrical_ai import ElectricalAI


class ElectricalTwin(BaseComponentTwin):

    def _ai(self) -> ElectricalAI:
        return ElectricalAI(
            battery_voltage = self.vehicle.get("battery_voltage", 12.0),
            rpm             = self.vehicle.get("rpm", 1500),
            temperature     = self.vehicle.get("temperature", 50),
        )

    def predict(self) -> dict:
        voltage = self.vehicle.get("battery_voltage", 12.0)
        rpm     = self.vehicle.get("rpm", 1500)
        result  = self._ai().run()
        return {
            "component":           "Electrical",
            "health":              result["health"],
            "failure_probability": result["failure_probability"],
            "rul":                 result["rul"],
            "confidence":          result["confidence"],
            "status":              self._status(result["health"]),
            "risk":                self._risk_label(result["failure_probability"]),
            "risk_color":          self._risk_color(result["health"]),
            "sensors": {
                "voltage":           voltage,
                "rpm":               rpm,
                "alternator_state":  result["models"]["alternator"]["state"],
                "wiring_integrity":  result["models"]["wiring"]["wiring_integrity"],
                "load_balance":      result["models"]["load_balance"]["load_balance"],
            },
            "sub_models": result["models"],
        }

    def simulate(self) -> dict:
        result = ElectricalAI(
            battery_voltage = 13.8,
            rpm             = self.vehicle.get("rpm", 1500),
            temperature     = self.vehicle.get("temperature", 50),
        ).run()
        return {"scenario": "Electrical Repair", **result,
                "status": self._status(result["health"]),
                "risk_color": self._risk_color(result["health"])}

    def forecast(self) -> dict:
        v    = self.vehicle.get("battery_voltage", 12.0)
        rpm  = self.vehicle.get("rpm", 1500)
        temp = self.vehicle.get("temperature", 50)
        return {
            "day7":  ElectricalAI(round(max(8.0, v - 7*0.02),  2), rpm, round(temp + 7*0.15,  1)).run(),
            "day15": ElectricalAI(round(max(8.0, v - 15*0.02), 2), rpm, round(temp + 15*0.15, 1)).run(),
            "day30": ElectricalAI(round(max(8.0, v - 30*0.02), 2), rpm, round(temp + 30*0.15, 1)).run(),
        }

    def explain(self) -> dict:
        ai     = self._ai()
        result = ai.run()
        alt    = ai.predict_alternator()
        wire   = ai.predict_wiring()
        load   = ai.predict_load_balance()
        reasons = []

        if alt["state"] not in ("Normal", "Idle"):
            reasons.append(f"Alternator {alt['state']} — fault probability {alt['fault_prob']}%")
        if wire["degradation_pct"] > 30:
            reasons.append(f"Wiring integrity {wire['wiring_integrity']}% — degradation at {wire['degradation_pct']}%")
        if load["overloaded"]:
            reasons.append(f"Electrical system overloaded — balance {load['load_balance']}")
        if not reasons:
            reasons.append(f"Charging system normal — alternator {alt['state']}")

        return {
            "component":  "Electrical",
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
