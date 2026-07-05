"""
Spare Parts Forecasting Service
Maps fleet ML predictions → part demand → inventory status → purchase orders.
"""
from datetime import date, timedelta
from data.parts_catalog import CATALOG, CATEGORY_COLORS


# ── Demand mapping ────────────────────────────────────────────────────────────

def _matches(part: dict, root_causes: list[str]) -> bool:
    combined = " ".join(root_causes).lower()
    return any(kw in combined for kw in part["root_cause_keywords"])


def _demand_weight(vehicle: dict) -> float:
    """
    How many 'units' of demand does this vehicle contribute?
    Critical = 1.0, High = 0.7, Medium = 0.4, Routine = 0.2
    """
    p = vehicle.get("priority", "Low")
    fail = vehicle.get("failure_probability", 0)
    if p == "Immediate" or fail > 85:
        return 1.0
    if p == "High" or fail > 60:
        return 0.7
    if p == "Medium" or fail > 35:
        return 0.4
    return 0.2


def _week_bucket(vehicle: dict) -> int:
    """Which week (1–4) is this vehicle likely to need service?"""
    rul = vehicle.get("remaining_useful_life_days", 60)
    if rul <= 7:   return 1
    if rul <= 14:  return 2
    if rul <= 21:  return 3
    return 4


# ── Stock status ──────────────────────────────────────────────────────────────

def _stock_status(current: int, predicted: int, min_stock: int) -> str:
    remaining = current - predicted
    if remaining < 0:
        return "Out of Stock"
    if remaining < min_stock:
        return "Critical"
    if remaining < min_stock * 1.5:
        return "Low Stock"
    return "Healthy"


def _days_until_stockout(current: int, predicted: int, lead_time: int) -> int | None:
    """Days until stock drops below safety level, accounting for lead time."""
    remaining = current - predicted
    if remaining <= 0:
        return 0
    # Rough daily burn rate over 30 days
    daily_rate = predicted / 30 if predicted > 0 else 0
    if daily_rate == 0:
        return None
    days = int(remaining / daily_rate)
    return days


def _recommended_order(current: int, predicted: int, min_stock: int) -> int:
    """How many units to order: need + safety buffer − current stock."""
    safety = max(min_stock, int(predicted * 0.3))   # 30% safety buffer
    needed = predicted + safety - current
    return max(0, needed)


# ── Weekly forecast breakdown ─────────────────────────────────────────────────

def _weekly_demand(vehicles: list[dict], part: dict) -> list[int]:
    weeks = [0, 0, 0, 0]
    for v in vehicles:
        root = v.get("root_cause", [])
        if _matches(part, root):
            w = _week_bucket(v)
            weeks[w - 1] += _demand_weight(v)
    return [round(w) for w in weeks]


# ── AI insight sentence ───────────────────────────────────────────────────────

def _ai_insight(part: dict, predicted: int, remaining: int,
                days_out: int | None, rec_order: int) -> str:
    name = part["name"]
    if remaining < 0:
        return (
            f"{name} stock is already depleted. "
            f"Immediate order of {rec_order} units required. "
            f"Lead time: {part['lead_time_days']} days."
        )
    if days_out is not None and days_out <= part["lead_time_days"] + 2:
        return (
            f"{name} is expected to run out in approximately {days_out} days — "
            f"within supplier lead time of {part['lead_time_days']} days. "
            f"Order {rec_order} units immediately to avoid stockout."
        )
    if rec_order > 0:
        cost = rec_order * part["unit_cost"]
        return (
            f"Predicted demand of {predicted} units over 30 days will reduce {name} "
            f"below safety stock. Recommended order: {rec_order} units "
            f"(₹{cost:,}). Order within {max(1, (days_out or 14) - part['lead_time_days'])} days."
        )
    return (
        f"{name} stock is healthy. Current inventory covers predicted demand "
        f"with {remaining} units remaining after 30-day forecast."
    )


# ── Public API ────────────────────────────────────────────────────────────────

def get_inventory() -> list[dict]:
    """Return raw inventory catalog with supplier info."""
    return [
        {
            "id":            p["id"],
            "name":          p["name"],
            "category":      p["category"],
            "category_color": CATEGORY_COLORS.get(p["category"], "#64748B"),
            "current_stock": p["current_stock"],
            "min_stock":     p["min_stock"],
            "unit_cost":     p["unit_cost"],
            "lead_time_days": p["lead_time_days"],
            "supplier":      p["supplier"],
        }
        for p in CATALOG
    ]


def forecast_spare_parts(vehicles: list[dict]) -> dict:
    today = date.today()
    parts_forecast = []
    total_investment = 0
    critical_parts   = 0
    stockout_parts   = 0

    for part in CATALOG:
        weekly = _weekly_demand(vehicles, part)
        predicted_30d = sum(weekly)

        current   = part["current_stock"]
        min_stock = part["min_stock"]
        remaining = current - predicted_30d
        status    = _stock_status(current, predicted_30d, min_stock)
        days_out  = _days_until_stockout(current, predicted_30d, part["lead_time_days"])
        rec_order = _recommended_order(current, predicted_30d, min_stock)
        order_cost = rec_order * part["unit_cost"]
        insight   = _ai_insight(part, predicted_30d, remaining, days_out, rec_order)

        if status in ("Critical", "Out of Stock"):
            critical_parts += 1
        if status == "Out of Stock":
            stockout_parts += 1
        if rec_order > 0:
            total_investment += order_cost

        parts_forecast.append({
            "id":              part["id"],
            "name":            part["name"],
            "category":        part["category"],
            "category_color":  CATEGORY_COLORS.get(part["category"], "#64748B"),
            "current_stock":   current,
            "predicted_30d":   predicted_30d,
            "remaining_after": remaining,
            "min_stock":       min_stock,
            "status":          status,
            "days_until_stockout": days_out,
            "recommended_order":   rec_order,
            "order_cost":          order_cost,
            "unit_cost":           part["unit_cost"],
            "lead_time_days":      part["lead_time_days"],
            "weekly_forecast":     weekly,
            "ai_insight":          insight,
            "supplier":            part["supplier"],
        })

    # Sort: Out of Stock → Critical → Low Stock → Healthy
    STATUS_RANK = {"Out of Stock": 0, "Critical": 1, "Low Stock": 2, "Healthy": 3}
    parts_forecast.sort(key=lambda x: STATUS_RANK.get(x["status"], 4))

    # ── Category summary ──────────────────────────────────────────────────────
    categories: dict[str, dict] = {}
    for p in parts_forecast:
        cat = p["category"]
        if cat not in categories:
            categories[cat] = {
                "category": cat,
                "color": p["category_color"],
                "total_parts": 0,
                "critical": 0,
                "total_predicted": 0,
                "total_order_cost": 0,
            }
        categories[cat]["total_parts"]     += 1
        categories[cat]["total_predicted"] += p["predicted_30d"]
        categories[cat]["total_order_cost"] += p["order_cost"]
        if p["status"] in ("Critical", "Out of Stock"):
            categories[cat]["critical"] += 1

    # ── Fleet-wide AI summary ─────────────────────────────────────────────────
    total_parts   = len(parts_forecast)
    healthy_parts = sum(1 for p in parts_forecast if p["status"] == "Healthy")
    inventory_health = round((healthy_parts / total_parts) * 100) if total_parts else 0

    # Top 3 urgent recommendations
    urgent = [p for p in parts_forecast if p["recommended_order"] > 0][:3]
    ai_recommendations = [
        {
            "part":          p["name"],
            "order_qty":     p["recommended_order"],
            "order_cost":    p["order_cost"],
            "status":        p["status"],
            "days_left":     p["days_until_stockout"],
            "supplier":      p["supplier"]["name"],
            "lead_time":     p["lead_time_days"],
            "insight":       p["ai_insight"],
        }
        for p in urgent
    ]

    return {
        "forecast_date":      today.isoformat(),
        "forecast_horizon":   "30 days",
        "parts":              parts_forecast,
        "categories":         list(categories.values()),
        "summary": {
            "total_parts":        total_parts,
            "healthy_parts":      healthy_parts,
            "critical_parts":     critical_parts,
            "stockout_parts":     stockout_parts,
            "inventory_health":   inventory_health,
            "total_investment":   total_investment,
            "vehicles_analyzed":  len(vehicles),
        },
        "ai_recommendations": ai_recommendations,
    }
