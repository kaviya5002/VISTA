"""
Motor Digital Twin
==================
Delegates all intelligence to MotorAI (services/component_ai/motor_ai.py).
"""
from models.digital_twins.base_twin import BaseComponentTwin
from services.component_ai.motor_ai import MotorAI


class MotorTwin(BaseComponentTwin):

    def _ai(self) -> MotorAI:
        return MotorAI(
            rpm             = self.vehicle.get("rpm", 1500),
            temperature     = self.vehicle.get("temperature", 50),
            battery_voltage = self.vehicle.get("battery_voltage", 12.0),
        )

    def predict(self) -> dict:
        rpm    = self.vehicle.get("rpm", 1500)
        temp   = self.vehicle.get("temperature", 50)
        result = self._ai().run()

        return {
            "component":           "Motor",
            "health":              result["health"],
            "failure_probability": result["failure_probability"],
            "rul":                 result["rul"],
            "confidence":          result["confidence"],
            "status":              self._status(result["health"]),
            "risk":                self._risk_label(result["failure_probability"]),
            "risk_color":          self._risk_color(result["health"]),
            "sensors": {
                "rpm":          rpm,
                "temperature":  temp,
                "efficiency":   result["models"]["efficiency"]["efficiency_pct"],
                "torque_stress": result["models"]["overload"]["stress_index"],
            },
            "sub_models": result["models"],
        }

    def simulate(self) -> dict:
        result = MotorAI(
            rpm             = min(self.vehicle.get("rpm", 1500), 2000),
            temperature     = 65,
            battery_voltage = self.vehicle.get("battery_voltage", 12.0),
        ).run()
        return {"scenario": "Motor Service", **result,
                "status": self._status(result["health"]),
                "risk_color": self._risk_color(result["health"])}

    def forecast(self) -> dict:
        rpm  = self.vehicle.get("rpm", 1500)
        temp = self.vehicle.get("temperature", 50)
        v    = self.vehicle.get("battery_voltage", 12.0)
        return {
            "day7":  MotorAI(rpm, round(temp + 7*0.15, 1),  round(max(8.0, v - 7*0.02),  2)).run(),
            "day15": MotorAI(rpm, round(temp + 15*0.15, 1), round(max(8.0, v - 15*0.02), 2)).run(),
            "day30": MotorAI(rpm, round(temp + 30*0.15, 1), round(max(8.0, v - 30*0.02), 2)).run(),
        }

    def explain(self) -> dict:
        ai     = self._ai()
        result = ai.run()
        eff    = ai.predict_efficiency()
        over   = ai.predict_overload()
        therm  = ai.predict_temperature()
        reasons = []

        if over["overload_prob"] > 50:
            reasons.append(f"Motor overload risk {over['overload_prob']}% — stress index {over['stress_index']}")
        if therm["thermal_state"] != "Normal":
            reasons.append(f"Thermal state {therm['thermal_state']} — estimated {therm['estimated_temp']}°C")
        if eff["efficiency_pct"] < 70:
            reasons.append(f"Efficiency degraded to {eff['efficiency_pct']}%")
        else:
            reasons.append(f"Motor efficiency {eff['efficiency_pct']}%")

        return {
            "component":  "Motor",
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
