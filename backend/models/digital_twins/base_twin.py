"""
Base Component Twin
===================
Every component twin (Battery, Motor, Cooling, Brake, Electrical, Transmission)
inherits from this class and implements the same four methods:

    predict()   — current health / failure / RUL from live sensors
    simulate()  — what-if: sensors changed to a repaired state
    forecast()  — physics-based degradation projection (7/15/30 days)
    explain()   — human-readable AI reasoning for the current state

The shared interface keeps the component_twin_engine.py orchestrator
completely generic — it calls the same four methods on every twin.
"""

from abc import ABC, abstractmethod
from collections import deque

# In-process rolling history: { (vehicle_id, component_name): deque[int] }
_HISTORY: dict[tuple, deque] = {}
_HISTORY_LEN = 30


class BaseComponentTwin(ABC):
    """
    Abstract base for all component digital twins.

    Parameters
    ----------
    vehicle : raw vehicle dict from the database / fleet_repository
    """

    def __init__(self, vehicle: dict):
        self.vehicle = vehicle

    # ------------------------------------------------------------------
    # Historical memory helpers
    # ------------------------------------------------------------------
    def _record_health(self, component: str, health: int) -> None:
        key = (self.vehicle.get("vehicle_id"), component)
        if key not in _HISTORY:
            _HISTORY[key] = deque(maxlen=_HISTORY_LEN)
        _HISTORY[key].append(health)

    def _get_history(self, component: str) -> list[int]:
        key = (self.vehicle.get("vehicle_id"), component)
        return list(_HISTORY.get(key, []))

    def _trend(self, component: str) -> dict:
        """Return slope and direction from rolling history."""
        history = self._get_history(component)
        if len(history) < 2:
            return {"slope": 0.0, "direction": "Stable", "history": history}
        n = len(history)
        # Simple linear regression slope
        mean_x = (n - 1) / 2
        mean_y = sum(history) / n
        slope = sum((i - mean_x) * (history[i] - mean_y) for i in range(n)) / \
                sum((i - mean_x) ** 2 for i in range(n))
        slope = round(slope, 3)
        direction = "Improving" if slope > 0.3 else "Degrading" if slope < -0.3 else "Stable"
        return {"slope": slope, "direction": direction, "history": history}

    # ------------------------------------------------------------------
    # Shared interface — every subclass must implement all four
    # ------------------------------------------------------------------
    @abstractmethod
    def predict(self) -> dict:
        """Return current health / failure_probability / rul / status."""

    @abstractmethod
    def simulate(self) -> dict:
        """Return predicted state after component repair/replacement."""

    @abstractmethod
    def forecast(self) -> dict:
        """Return degradation projection at day 7, 15, 30."""

    @abstractmethod
    def explain(self) -> dict:
        """Return AI-generated reasoning and confidence score."""

    # ------------------------------------------------------------------
    # Shared helpers available to every subclass
    # ------------------------------------------------------------------
    @staticmethod
    def _status(health: int) -> str:
        if health >= 75: return "Healthy"
        if health >= 45: return "Warning"
        return "Critical"

    @staticmethod
    def _risk_label(failure_prob: float) -> str:
        if failure_prob >= 75: return "High"
        if failure_prob >= 40: return "Medium"
        return "Low"

    @staticmethod
    def _clamp(value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))

    def _run_ml(self, sensors: dict) -> dict:
        """
        Push a sensor snapshot through Health / Failure / RUL ML models.
        Falls back to the physics formulas inside twin_prediction_service
        automatically when models are not available.
        """
        from services.twin_prediction_service import (
            predict_future_health,
            predict_future_failure,
            predict_future_rul,
        )
        health  = predict_future_health(sensors)
        failure = predict_future_failure(sensors)
        rul     = predict_future_rul(sensors)
        return {
            "health":              health,
            "failure_probability": failure,
            "rul":                 rul,
            "status":              self._status(health),
            "risk":                self._risk_label(failure),
        }

    def _degrade(self, sensors: dict, days: int) -> dict:
        """Apply physics-based degradation for `days` into the future."""
        future = {
            **sensors,
            "battery_voltage": round(max(8.0, sensors.get("battery_voltage", 12.0) - days * 0.02), 2),
            "temperature":     round(sensors.get("temperature", 50) + days * 0.15, 1),
        }
        return self._run_ml(future)
