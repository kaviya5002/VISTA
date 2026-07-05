from datetime import date, datetime
from services.repair_templates import get_template
from services.technician_assignment_service import assign_technician
from services.inventory.inventory_repository import deduct_stock, get_all_stock
from data.parts_catalog import CATALOG

VEHICLE_MODELS = {
    range(1,  21): "Tata Ace EV",
    range(21, 41): "Tata Nexon EV",
    range(41, 61): "Tata Tigor EV",
    range(61, 81): "Tata Tiago EV",
    range(81, 101): "Tata Punch EV",
}


def _vehicle_model(vid: int) -> str:
    for r, name in VEHICLE_MODELS.items():
        if vid in r:
            return name
    return "Tata EV"


def _priority_label(vehicle: dict) -> str:
    p = vehicle.get("priority", "Low")
    fail = vehicle.get("failure_probability", 0)
    health = vehicle.get("health_score", 100)
    if p == "Immediate" or fail > 85 or health < 30:
        return "Critical"
    if p == "High" or fail > 60 or health < 50:
        return "High"
    if p == "Medium" or fail > 35 or health < 70:
        return "Medium"
    return "Routine"


def _ai_summary(vehicle: dict, template: dict) -> str:
    fail_prob = vehicle.get("failure_probability", 0)
    health    = vehicle.get("health_score", 100)
    rul       = vehicle.get("remaining_useful_life_days", 60)
    root      = vehicle.get("root_cause", [])
    task      = template["label"]

    cause_str = root[0] if root else "component degradation"
    delay_risk = min(99, fail_prob + 14)

    lines = [
        f"AI analysis detects {cause_str.lower()} with {fail_prob}% failure probability "
        f"and a health score of {health}%.",
        f"Immediate {task.lower()} is recommended.",
        f"Delaying repair may increase failure probability from {fail_prob}% to {delay_risk}% "
        f"within 7 days.",
        f"Estimated repair downtime: {template['duration']} hour(s). "
        f"Remaining useful life: {rul} day(s).",
    ]
    return " ".join(lines)


def generate_work_order(vehicle: dict) -> dict:
    vid       = vehicle["vehicle_id"]
    root      = vehicle.get("root_cause", [])
    template  = get_template(root)
    priority  = _priority_label(vehicle)
    today     = date.today().isoformat()
    wo_id     = f"WO-{datetime.now().strftime('%Y%m%d')}-{vid:04d}"

    # AI technician assignment
    assignment = assign_technician(vehicle)
    technician = assignment["technician"]

    return {
        "work_order_id":    wo_id,
        "generated_at":     datetime.now().isoformat(timespec="seconds"),
        "vehicle_id":       vid,
        "vehicle_model":    _vehicle_model(vid),
        "priority":         priority,
        "status":           "Created",
        "scheduled_date":   today,
        # ── Repair details ────────────────────────────────────────────────
        "task":             template["label"],
        "duration":         f"{template['duration']} hr{'s' if template['duration'] > 1 else ''}",
        "duration_hours":   template["duration"],
        "technician":       technician,
        "technician_skill": template["skill"],
        "technician_score": assignment["score"],
        "technician_rating": assignment["technician_rating"],
        "assignment_reasons": assignment["reasons"],
        "estimated_start":  assignment["estimated_start"],
        "estimated_finish": assignment["estimated_finish"],
        "parts":            template["parts"],
        "tools":            template["tools"],
        "checklist":        template["checklist"],
        "instructions":     template["instructions"],
        # ── Diagnostics ───────────────────────────────────────────────────
        "health_score":     vehicle.get("health_score", 0),
        "failure_risk":     vehicle.get("failure_probability", 0),
        "rul_days":         vehicle.get("remaining_useful_life_days", 0),
        "root_causes":      root,
        "estimated_risk":   vehicle.get("estimated_risk", "Unknown"),
        "confidence_score": vehicle.get("confidence_score", 0),
        # ── Financials ────────────────────────────────────────────────────
        "estimated_cost":   vehicle.get("repair_now_cost", 500),
        "failure_cost":     vehicle.get("failure_cost", 0),
        "potential_savings": vehicle.get("potential_savings", 0),
        # ── AI summary ────────────────────────────────────────────────────
        "ai_summary":       _ai_summary(vehicle, template),
        "reasoning":        vehicle.get("reasoning", []),
        # ── QR payload (resolved by frontend/PDF) ─────────────────────────
        "qr_data":          f"twinguard://vehicle/{vid}/workorder/{wo_id}",
    }


_PART_NAME_TO_ID: dict[str, str] = {p["name"]: p["id"] for p in CATALOG}


def complete_work_order(work_order: dict) -> dict:
    """
    Call when a work order is marked completed.
    Deducts used parts from inventory and returns updated stock snapshot.
    """
    wo_id = work_order.get("work_order_id", "unknown")
    parts_used = work_order.get("parts", [])
    deductions = []
    for part_name in parts_used:
        part_id = _PART_NAME_TO_ID.get(part_name)
        if part_id:
            new_stock = deduct_stock(part_id, 1, work_order_id=wo_id, reason="work_order_completed")
            deductions.append({"part_id": part_id, "part_name": part_name, "new_stock": new_stock})
    return {"work_order_id": wo_id, "parts_deducted": deductions}
