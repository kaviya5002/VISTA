"""
Context Builder
===============
Collects structured data from all backend services based on the resolved intent.
Returns a plain dict that prompt_builder.py converts to readable text.
"""
from __future__ import annotations
from services.assistant.intent_classifier import Intent


def _process_vehicle(vehicle: dict) -> dict:
    from services.health_score import calculate_health
    from services.failure_forecast import predict_failure
    from services.root_cause import analyze_root_cause
    from services.rul_engine import calculate_rul
    from services.cost_analysis import calculate_cost_impact
    from services.maintenance_strategist import ai_maintenance_strategy

    vehicle = calculate_health(vehicle)
    vehicle = predict_failure(vehicle)
    vehicle = analyze_root_cause(vehicle)
    vehicle = calculate_rul(vehicle)
    vehicle = calculate_cost_impact(vehicle)
    vehicle = ai_maintenance_strategy(vehicle)
    return vehicle


def _get_vehicle(vehicle_id: int) -> dict | None:
    from services.fleet_repository import get_all_vehicles
    vehicles = get_all_vehicles()
    raw = next((v for v in vehicles if v["vehicle_id"] == vehicle_id), None)
    return _process_vehicle(raw) if raw else None


def _fleet_summary() -> dict:
    from services.fleet_repository import get_all_vehicles
    from services.fleet_optimizer import optimize_fleet

    vehicles = get_all_vehicles()
    processed = [_process_vehicle(v) for v in vehicles]
    optimized = optimize_fleet(processed)

    critical = [v for v in optimized if v.get("failure_probability", 0) > 75]
    avg_health = round(sum(v.get("health_score", 0) for v in optimized) / max(len(optimized), 1), 1)

    return {
        "total": len(optimized),
        "critical_count": len(critical),
        "avg_health": avg_health,
        "top_critical": [
            {
                "vehicle_id": v["vehicle_id"],
                "health_score": v.get("health_score"),
                "failure_probability": v.get("failure_probability"),
                "status": v.get("status"),
            }
            for v in critical[:5]
        ],
    }


def _get_technicians() -> list[dict]:
    from services.technician_assignment_service import get_all_technicians
    return get_all_technicians()


def _get_inventory() -> list[dict]:
    from services.spare_parts_service import get_inventory
    return get_inventory()


def _get_calendar() -> dict:
    from services.fleet_repository import get_all_vehicles
    from services.fleet_optimizer import optimize_fleet
    from services.calendar_service import generate_calendar

    vehicles = get_all_vehicles()
    processed = [_process_vehicle(v) for v in vehicles]
    return generate_calendar(optimize_fleet(processed))


def build_context(intent: Intent) -> dict:
    ctx: dict = {"intent": intent.category, "vehicle_id": intent.vehicle_id}

    try:
        if intent.category == "fleet_summary" or intent.vehicle_id is None and intent.category in (
            "alerts", "maintenance", "calendar",
        ):
            ctx["fleet"] = _fleet_summary()

        if intent.vehicle_id is not None:
            vehicle = _get_vehicle(intent.vehicle_id)
            ctx["vehicle"] = vehicle
            if vehicle is None:
                ctx["error"] = f"Vehicle {intent.vehicle_id} not found."

        if intent.category == "technician":
            ctx["technicians"] = _get_technicians()
            if intent.vehicle_id and ctx.get("vehicle"):
                from services.technician_assignment_service import assign_technician
                from services.fleet_optimizer import optimize_fleet
                ctx["assignment"] = assign_technician(optimize_fleet([ctx["vehicle"]])[0])

        if intent.category == "inventory":
            ctx["inventory"] = _get_inventory()

        if intent.category == "calendar":
            ctx["calendar"] = _get_calendar()

        if intent.category == "explanation" and intent.vehicle_id and ctx.get("vehicle"):
            from services.xai.shap_service import explain_vehicle
            from services.xai.explanation_service import generate_explanation
            shap = explain_vehicle(ctx["vehicle"])
            ctx["shap"] = shap
            ctx["explanation"] = generate_explanation(ctx["vehicle"], shap)

    except Exception as e:
        ctx["context_error"] = str(e)

    return ctx
