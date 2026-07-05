"""
Inventory Service — FastAPI router exposing:
  GET /inventory               → current stock levels
  GET /inventory/predictions   → 30-day demand forecast
  GET /inventory/purchase-plan → prioritised purchase recommendations
"""
from fastapi import APIRouter, Query
from data.parts_catalog import CATALOG, CATEGORY_COLORS
from services.inventory.inventory_repository import get_all_stock
from services.inventory.inventory_predictor import predict_demand
from services.inventory.stock_optimizer import optimize_stock
from services.inventory.purchase_planner import generate_purchase_plan

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _get_fleet_context():
    """Lazy import to avoid circular deps; returns (vehicles, calendar_events)."""
    from services.fleet_repository import get_all_vehicles
    from services.health_score import calculate_health
    from services.failure_forecast import predict_failure
    from services.root_cause import analyze_root_cause
    from services.rul_engine import calculate_rul
    from services.fleet_optimizer import optimize_fleet
    from services.calendar_service import generate_calendar

    vehicles = get_all_vehicles()
    processed = []
    for v in vehicles:
        v = calculate_health(v)
        v = predict_failure(v)
        v = analyze_root_cause(v)
        v = calculate_rul(v)
        processed.append(v)
    fleet = optimize_fleet(processed)
    calendar = generate_calendar(fleet)
    events = calendar.get("events", [])
    return fleet, events


@router.get("")
def get_inventory():
    """Current stock levels enriched with catalog metadata."""
    live_stock = get_all_stock()
    return [
        {
            "id":             p["id"],
            "name":           p["name"],
            "category":       p["category"],
            "category_color": CATEGORY_COLORS.get(p["category"], "#64748B"),
            "current_stock":  live_stock.get(p["id"], p["current_stock"]),
            "min_stock":      p["min_stock"],
            "unit_cost":      p["unit_cost"],
            "lead_time_days": p["lead_time_days"],
            "supplier":       p["supplier"],
        }
        for p in CATALOG
    ]


@router.get("/predictions")
def get_predictions():
    """30-day demand predictions per part using fleet ML + calendar signals."""
    vehicles, events = _get_fleet_context()
    live_stock = get_all_stock()
    predictions = predict_demand(vehicles, events)
    optimized = optimize_stock(predictions, live_stock)
    return {
        "forecast_horizon": "30 days",
        "parts": optimized,
        "summary": {
            "total_parts":    len(optimized),
            "shortage_parts": sum(1 for p in optimized if p["shortage"]),
            "healthy_parts":  sum(1 for p in optimized if p["status"] == "Healthy"),
            "critical_parts": sum(1 for p in optimized if p["status"] in ("Critical", "Out of Stock")),
        },
    }


@router.get("/purchase-plan")
def get_purchase_plan(budget: float = Query(None, description="Optional budget cap in ₹")):
    """Prioritised purchase plan considering lead times, stock levels, and demand."""
    vehicles, events = _get_fleet_context()
    live_stock = get_all_stock()
    predictions = predict_demand(vehicles, events)
    optimized = optimize_stock(predictions, live_stock)
    return generate_purchase_plan(optimized, budget=budget)
