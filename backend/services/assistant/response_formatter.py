"""
Response Formatter
==================
Wraps a raw answer string into the standard assistant response envelope:
  { answer, confidence, sources, suggested_actions, intent, vehicle_id }
"""
from __future__ import annotations
from services.assistant.intent_classifier import Intent


_ACTIONS: dict[str, list[str]] = {
    "fleet_summary":  ["View Fleet Dashboard", "Check Critical Vehicles", "Open Maintenance Calendar"],
    "vehicle_health": ["View Vehicle Details", "Run XAI Explanation", "Schedule Maintenance"],
    "failure_risk":   ["View SHAP Explanation", "Assign Technician", "Create Work Order"],
    "rul":            ["Schedule Service", "View Timeline", "Check Spare Parts"],
    "root_cause":     ["View XAI Report", "Assign Specialist Technician", "Order Parts"],
    "maintenance":    ["Open Calendar", "Create Work Order", "Assign Technician"],
    "technician":     ["View Technician Dashboard", "Confirm Assignment", "Check Workload"],
    "inventory":      ["View Inventory", "Forecast Spare Parts", "Place Order"],
    "calendar":       ["Open Calendar", "View Upcoming Jobs", "Reschedule"],
    "cost":           ["View Cost Analysis", "Compare Repair vs Failure Cost", "Generate Report"],
    "alerts":         ["View Alerts", "Prioritise Critical Vehicles", "Dispatch Technician"],
    "explanation":    ["View SHAP Chart", "Download XAI Report", "Compare Vehicles"],
    "greeting":       ["View Fleet Summary", "Check Alerts", "Open Dashboard"],
    "unknown":        ["View Dashboard", "Check Fleet Status"],
}

_SOURCES: dict[str, list[str]] = {
    "fleet_summary":  ["Fleet Repository", "Fleet Optimizer", "Health Model"],
    "vehicle_health": ["Health ML Model v2", "Maintenance Strategist"],
    "failure_risk":   ["Failure ML Model v2", "SHAP Service"],
    "rul":            ["NASA RUL Model", "RUL Engine"],
    "root_cause":     ["Root Cause ML Model", "XAI Service"],
    "maintenance":    ["Maintenance Strategist", "Calendar Service"],
    "technician":     ["Technician Assignment Engine", "Skill Matcher"],
    "inventory":      ["Spare Parts Service", "Parts Catalog"],
    "calendar":       ["Calendar Service", "Fleet Optimizer"],
    "cost":           ["Cost Analysis Service", "Failure Model"],
    "alerts":         ["Alert Engine", "Failure Model", "Health Model"],
    "explanation":    ["SHAP TreeExplainer", "Explanation Service"],
    "greeting":       ["TwinGuard AI"],
    "unknown":        ["TwinGuard AI"],
}


def format_response(
    answer: str,
    intent: Intent,
    context: dict,
    *,
    llm_used: bool = False,
) -> dict:
    vehicle = context.get("vehicle")
    confidence = _derive_confidence(intent, vehicle, llm_used)

    return {
        "answer":            answer,
        "confidence":        confidence,
        "intent":            intent.category,
        "vehicle_id":        intent.vehicle_id,
        "sources":           _SOURCES.get(intent.category, ["TwinGuard AI"]),
        "suggested_actions": _ACTIONS.get(intent.category, _ACTIONS["unknown"]),
        "llm_used":          llm_used,
        "data_snapshot":     _snapshot(vehicle) if vehicle else None,
    }


def _derive_confidence(intent: Intent, vehicle: dict | None, llm_used: bool) -> int:
    base = round(intent.confidence * 100)
    if vehicle:
        # Boost when ML models were active
        if vehicle.get("ml_model_used"):
            base = min(99, base + 5)
        if vehicle.get("health_source") == "Health ML Model":
            base = min(99, base + 3)
    if llm_used:
        base = min(99, base + 4)
    return max(40, base)


def _snapshot(v: dict) -> dict:
    return {
        "health_score":        v.get("health_score"),
        "failure_probability": v.get("failure_probability"),
        "rul_days":            v.get("remaining_useful_life_days"),
        "status":              v.get("status"),
        "priority":            v.get("priority"),
    }
