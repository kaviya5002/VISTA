"""
Battery Digital Twin
====================
Delegates all intelligence to BatteryAI (services/component_ai/battery_ai.py).
The twin is responsible for: sensor ingestion, interface compliance, output shaping.
"""
from models.digital_twins.base_twin import BaseComponentTwin
from services.component_ai.battery_ai import BatteryAI


class BatteryTwin(BaseComponentTwin):

    def _ai(self) -> BatteryAI:
        return BatteryAI(
            voltage     = self.vehicle.get("battery_voltage", 12.0),
            temperature = self.vehicle.get("temperature", 50),
            rpm         = self.vehicle.get("rpm", 1500),
        )

    def predict(self) -> dict:
        voltage  = self.vehicle.get("battery_voltage", 12.0)
        temp     = self.vehicle.get("temperature", 50)
        result   = self._ai().run()

        return {
            "component":           "Battery",
            "health":              result["health"],
            "failure_probability": result["failure_probability"],
            "rul":                 result["rul"],
            "confidence":          result["confidence"],
            "status":              self._status(result["health"]),
            "risk":                self._risk_label(result["failure_probability"]),
            "risk_color":          self._risk_color(result["health"]),
            "sensors": {
                "voltage":       voltage,
                "temperature":   temp,
                "charge_level":  self._charge_level(voltage),
            },
            "sub_models": result["models"],
        }

    def simulate(self) -> dict:
        ai = BatteryAI(voltage=12.8,
                       temperature=min(self.vehicle.get("temperature", 50), 70),
                       rpm=self.vehicle.get("rpm", 1500))
        result = ai.run()
        return {"scenario": "Battery Replacement", **result,
                "status": self._status(result["health"]),
                "risk_color": self._risk_color(result["health"])}

    def forecast(self) -> dict:
        v    = self.vehicle.get("battery_voltage", 12.0)
        temp = self.vehicle.get("temperature", 50)
        rpm  = self.vehicle.get("rpm", 1500)
        return {
            "day7":  BatteryAI(round(max(8.0, v - 7*0.02), 2),  round(temp + 7*0.15, 1),  rpm).run(),
            "day15": BatteryAI(round(max(8.0, v - 15*0.02), 2), round(temp + 15*0.15, 1), rpm).run(),
            "day30": BatteryAI(round(max(8.0, v - 30*0.02), 2), round(temp + 30*0.15, 1), rpm).run(),
        }

    def explain(self) -> dict:
        voltage = self.vehicle.get("battery_voltage", 12.0)
        temp    = self.vehicle.get("temperature", 50)
        ai      = self._ai()
        result  = ai.run()
        thermal = ai.predict_thermal_runaway()
        vdrop   = ai.predict_voltage_drop()
        reasons = []

        if thermal["thermal_runaway_prob"] > 40:
            reasons.append(f"Thermal runaway risk {thermal['thermal_runaway_prob']}% — immediate attention")
        if vdrop["severity"] != "Normal":
            reasons.append(f"Voltage drop rate {vdrop['drop_rate']} V — {vdrop['severity']}")
        if voltage < 11.5:
            reasons.append(f"Critical voltage {voltage}V — near end of life")
        elif voltage < 12.4:
            reasons.append(f"Low voltage {voltage}V — charging issue possible")
        else:
            reasons.append(f"Voltage nominal ({voltage}V)")
        if temp > 70:
            reasons.append(f"Thermal stress {temp}°C — accelerates capacity fade")

        return {
            "component":  "Battery",
            "health":     result["health"],
            "confidence": result["confidence"],
            "risk_color": self._risk_color(result["health"]),
            "reasons":    reasons,
        }

    # ── Helpers ──────────────────────────────────────────────────────
    @staticmethod
    def _risk_color(health: int) -> str:
        if health >= 75: return "🟢"
        if health >= 45: return "🟡"
        return "🔴"

    @staticmethod
    def _charge_level(v: float) -> int:
        return max(0, min(100, round(((v - 11.0) / (13.2 - 11.0)) * 100)))
