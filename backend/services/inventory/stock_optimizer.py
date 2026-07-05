"""
Stock Optimizer — detects shortages and computes optimal stock levels.
"""
from data.parts_catalog import CATALOG


_STATUS_RANK = {"Out of Stock": 0, "Critical": 1, "Low Stock": 2, "Healthy": 3}


def _status(current: int, predicted: int, min_stock: int) -> str:
    remaining = current - predicted
    if remaining < 0:           return "Out of Stock"
    if remaining < min_stock:   return "Critical"
    if remaining < min_stock * 1.5: return "Low Stock"
    return "Healthy"


def _days_to_stockout(current: int, predicted: int) -> int | None:
    remaining = current - predicted
    if remaining <= 0: return 0
    daily = predicted / 30 if predicted > 0 else 0
    return int(remaining / daily) if daily > 0 else None


def optimize_stock(predictions: list[dict], live_stock: dict[str, int]) -> list[dict]:
    """
    Cross-references demand predictions with live stock levels.
    Returns enriched list with status, shortage flags, and optimal reorder qty.
    """
    catalog_map = {p["id"]: p for p in CATALOG}
    results = []

    for pred in predictions:
        pid     = pred["part_id"]
        part    = catalog_map.get(pid, {})
        current = live_stock.get(pid, part.get("current_stock", 0))
        min_stk = part.get("min_stock", 0)
        p30     = pred["predicted_30d"]
        safety  = max(min_stk, round(p30 * 0.3))
        reorder = max(0, p30 + safety - current)
        status  = _status(current, p30, min_stk)
        days_out = _days_to_stockout(current, p30)

        results.append({
            **pred,
            "current_stock":       current,
            "min_stock":           min_stk,
            "safety_stock":        safety,
            "remaining_after_30d": current - p30,
            "status":              status,
            "shortage":            status in ("Out of Stock", "Critical"),
            "days_until_stockout": days_out,
            "recommended_reorder": reorder,
            "unit_cost":           part.get("unit_cost", 0),
            "lead_time_days":      part.get("lead_time_days", 0),
            "supplier":            part.get("supplier", {}),
        })

    results.sort(key=lambda x: _STATUS_RANK.get(x["status"], 4))
    return results
