"""
Twin State Manager
==================
In-memory store for every vehicle's digital twin.

Each vehicle slot holds:
    current   — latest scored snapshot
    previous  — snapshot from the cycle before
    history   — deque of up to 30 snapshots (one per broadcast tick)
    events    — list of auto-detected events (rapid degradation, overheating…)
    timeline  — ordered list of lifecycle milestones
    snapshot  — last manual/auto save

The WebSocket broadcast loop calls update_twin() every cycle.
All REST routes read from here — zero extra ML re-runs.
"""

from __future__ import annotations

import time
from collections import deque
from copy import deepcopy
from typing import Optional

_HISTORY_LEN = 30

# ── State store ───────────────────────────────────────────────────────────────
# { vehicle_id: TwinState }
_store: dict[int, "TwinState"] = {}


class TwinState:
    __slots__ = ("vehicle_id", "current", "previous", "history", "events", "timeline", "_snapshot")

    def __init__(self, vehicle_id: int):
        self.vehicle_id = vehicle_id
        self.current:   Optional[dict] = None
        self.previous:  Optional[dict] = None
        self.history:   deque[dict]    = deque(maxlen=_HISTORY_LEN)
        self.events:    list[dict]     = []
        self.timeline:  list[dict]     = []
        self._snapshot: Optional[dict] = None

    # ── State machine label ───────────────────────────────────────────
    @staticmethod
    def _lifecycle(health: int) -> str:
        if health >= 80: return "Healthy"
        if health >= 65: return "Degrading"
        if health >= 45: return "Warning"
        if health >= 25: return "Critical"
        return "Repair"

    # ── Update ────────────────────────────────────────────────────────
    def push(self, snap: dict) -> None:
        """Accept a new scored snapshot, advance state, record history."""
        self.previous = deepcopy(self.current)
        self.current  = deepcopy(snap)
        self.current["ts"] = time.time()
        self.history.append(deepcopy(self.current))

        # Lifecycle transition
        lc = self._lifecycle(snap.get("health", 100))
        prev_lc = self._lifecycle(self.previous.get("health", 100)) if self.previous else None
        if lc != prev_lc:
            self._add_timeline(f"State → {lc}", lc)

    # ── Events ────────────────────────────────────────────────────────
    def add_event(self, kind: str, message: str, severity: str = "Warning") -> None:
        self.events.append({
            "ts":       time.time(),
            "kind":     kind,
            "message":  message,
            "severity": severity,
        })
        self._add_timeline(kind, severity)

    # ── Timeline ──────────────────────────────────────────────────────
    def _add_timeline(self, label: str, severity: str) -> None:
        self.timeline.append({
            "ts":       time.time(),
            "label":    label,
            "severity": severity,
        })

    # ── Snapshot ──────────────────────────────────────────────────────
    def save_snapshot(self) -> None:
        self._snapshot = deepcopy(self.current)

    def restore(self) -> Optional[dict]:
        return deepcopy(self._snapshot)


# ── Public API ────────────────────────────────────────────────────────────────

def create_twin(vehicle_id: int) -> TwinState:
    state = TwinState(vehicle_id)
    state._add_timeline("Twin Created", "Info")
    _store[vehicle_id] = state
    return state


def update_twin(vehicle_id: int, snap: dict) -> TwinState:
    if vehicle_id not in _store:
        create_twin(vehicle_id)
    _store[vehicle_id].push(snap)
    return _store[vehicle_id]


def get_twin(vehicle_id: int) -> Optional[TwinState]:
    return _store.get(vehicle_id)


def delete_twin(vehicle_id: int) -> None:
    _store.pop(vehicle_id, None)


def snapshot(vehicle_id: int) -> None:
    """Persist current state to the in-memory snapshot slot."""
    if vehicle_id in _store:
        _store[vehicle_id].save_snapshot()


def restore(vehicle_id: int) -> Optional[dict]:
    state = _store.get(vehicle_id)
    return state.restore() if state else None


def broadcast(fleet_snaps: list[dict]) -> None:
    """Called by the WebSocket loop — updates every vehicle at once."""
    for snap in fleet_snaps:
        update_twin(snap["vehicle_id"], snap)
