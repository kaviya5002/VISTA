"""
Timeline Service
================
Builds a human-readable lifecycle timeline for a vehicle from the
events and state transitions stored in TwinStateManager.

Timeline entry shape
--------------------
{
    "ts":        1718000000.0,   # unix timestamp
    "time":      "14:32:05",     # HH:MM:SS for display
    "label":     "State → Warning",
    "severity":  "Warning",       # Info | Warning | Critical
    "icon":      "🟡"
}
"""

from __future__ import annotations
from datetime import datetime
from services.twin_state_manager import get_twin

_ICONS = {
    "Info":     "ℹ️",
    "Warning":  "🟡",
    "Critical": "🔴",
    "Healthy":  "🟢",
    "Repair":   "🔧",
}


def get_timeline(vehicle_id: int) -> list[dict]:
    state = get_twin(vehicle_id)
    if not state:
        return []

    entries = []
    for item in state.timeline:
        sev  = item.get("severity", "Info")
        icon = _ICONS.get(sev, "⬤")
        # map well-known lifecycle labels to better icons
        label = item["label"]
        if "Healthy" in label:   icon = "🟢"
        elif "Repair" in label:  icon = "🔧"
        elif "Recovery" in label: icon = "✅"
        elif "Critical" in label: icon = "🔴"

        entries.append({
            "ts":       item["ts"],
            "time":     datetime.fromtimestamp(item["ts"]).strftime("%H:%M:%S"),
            "label":    label,
            "severity": sev,
            "icon":     icon,
        })

    # Most recent first
    return sorted(entries, key=lambda e: e["ts"], reverse=True)
