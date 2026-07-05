"""
Purchase Planner — generates purchase recommendations considering:
  - Supplier lead times
  - Minimum / safety stock thresholds
  - Budget constraints
  - Predicted demand from inventory predictor
"""
from datetime import date, timedelta
from data.parts_catalog import CATALOG


def _urgency_label(days_out: int | None, lead_time: int) -> str:
    if days_out is None:        return "Planned"
    if days_out <= 0:           return "Immediate"
    if days_out <= lead_time:   return "Urgent"
    if days_out <= lead_time * 2: return "Soon"
    return "Planned"


def _order_by_date(urgency: str, lead_time: int) -> str:
    today = date.today()
    offsets = {"Immediate": 0, "Urgent": 1, "Soon": 3, "Planned": 7}
    return (today + timedelta(days=offsets.get(urgency, 7))).isoformat()


def generate_purchase_plan(
    optimized_stock: list[dict],
    budget: float = None,
) -> dict:
    """
    Returns a prioritised purchase plan.
    `budget` (optional) caps total spend; lower-priority items are deferred.
    """
    catalog_map = {p["id"]: p for p in CATALOG}
    orders = []
    total_cost = 0.0
    deferred = []

    # Sort: Immediate → Urgent → Soon → Planned
    urgency_rank = {"Immediate": 0, "Urgent": 1, "Soon": 2, "Planned": 3}
    items = sorted(
        [s for s in optimized_stock if s["recommended_reorder"] > 0],
        key=lambda x: (
            urgency_rank.get(
                _urgency_label(x["days_until_stockout"], x["lead_time_days"]), 3
            ),
            -(x["recommended_reorder"] * x["unit_cost"])
        )
    )

    for item in items:
        qty       = item["recommended_reorder"]
        unit_cost = item["unit_cost"]
        line_cost = qty * unit_cost
        lead_time = item["lead_time_days"]
        days_out  = item["days_until_stockout"]
        urgency   = _urgency_label(days_out, lead_time)
        order_by  = _order_by_date(urgency, lead_time)
        supplier  = item.get("supplier", {})

        order = {
            "part_id":       item["part_id"],
            "part_name":     item["part_name"],
            "category":      item["category"],
            "qty":           qty,
            "unit_cost":     unit_cost,
            "total_cost":    line_cost,
            "urgency":       urgency,
            "order_by":      order_by,
            "expected_delivery": (
                date.fromisoformat(order_by) + timedelta(days=lead_time)
            ).isoformat(),
            "days_until_stockout": days_out,
            "current_stock": item["current_stock"],
            "predicted_30d": item["predicted_30d"],
            "supplier_name": supplier.get("name", "Unknown"),
            "supplier_contact": supplier.get("contact", ""),
            "lead_time_days": lead_time,
        }

        if budget is not None and total_cost + line_cost > budget:
            deferred.append({**order, "deferred_reason": "budget_exceeded"})
        else:
            orders.append(order)
            total_cost += line_cost

    summary = {
        "total_orders":    len(orders),
        "total_cost":      round(total_cost, 2),
        "deferred_count":  len(deferred),
        "immediate_count": sum(1 for o in orders if o["urgency"] == "Immediate"),
        "urgent_count":    sum(1 for o in orders if o["urgency"] == "Urgent"),
        "budget":          budget,
        "budget_remaining": round(budget - total_cost, 2) if budget else None,
    }

    return {
        "plan_date":  date.today().isoformat(),
        "orders":     orders,
        "deferred":   deferred,
        "summary":    summary,
    }
