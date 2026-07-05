"""
Inventory Repository — manages spare part stock levels with persistence via SQLite.
Provides CRUD operations and stock deduction on work order completion.
"""
from database import get_connection
from data.parts_catalog import CATALOG


def _ensure_table():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                part_id      TEXT PRIMARY KEY,
                current_stock INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS inventory_transactions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                part_id      TEXT NOT NULL,
                delta        INTEGER NOT NULL,
                reason       TEXT,
                work_order_id TEXT,
                created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Seed from catalog if empty
        existing = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
        if existing == 0:
            conn.executemany(
                "INSERT OR IGNORE INTO inventory (part_id, current_stock) VALUES (?, ?)",
                [(p["id"], p["current_stock"]) for p in CATALOG]
            )
        conn.commit()


def get_all_stock() -> dict[str, int]:
    _ensure_table()
    with get_connection() as conn:
        rows = conn.execute("SELECT part_id, current_stock FROM inventory").fetchall()
    return {r["part_id"]: r["current_stock"] for r in rows}


def get_stock(part_id: str) -> int:
    stock = get_all_stock()
    return stock.get(part_id, 0)


def deduct_stock(part_id: str, qty: int, work_order_id: str = None, reason: str = "repair") -> int:
    """Deduct qty from stock. Returns new stock level. Clamps at 0."""
    _ensure_table()
    with get_connection() as conn:
        current = conn.execute(
            "SELECT current_stock FROM inventory WHERE part_id = ?", (part_id,)
        ).fetchone()
        if not current:
            return 0
        new_stock = max(0, current["current_stock"] - qty)
        conn.execute(
            "UPDATE inventory SET current_stock = ? WHERE part_id = ?", (new_stock, part_id)
        )
        conn.execute(
            "INSERT INTO inventory_transactions (part_id, delta, reason, work_order_id) VALUES (?, ?, ?, ?)",
            (part_id, -qty, reason, work_order_id)
        )
        conn.commit()
    return new_stock


def restock(part_id: str, qty: int, reason: str = "purchase") -> int:
    _ensure_table()
    with get_connection() as conn:
        conn.execute(
            "UPDATE inventory SET current_stock = current_stock + ? WHERE part_id = ?", (qty, part_id)
        )
        conn.execute(
            "INSERT INTO inventory_transactions (part_id, delta, reason) VALUES (?, ?, ?)",
            (part_id, qty, reason)
        )
        conn.commit()
        row = conn.execute("SELECT current_stock FROM inventory WHERE part_id = ?", (part_id,)).fetchone()
    return row["current_stock"] if row else 0


def get_transactions(part_id: str = None, limit: int = 50) -> list[dict]:
    _ensure_table()
    with get_connection() as conn:
        if part_id:
            rows = conn.execute(
                "SELECT * FROM inventory_transactions WHERE part_id = ? ORDER BY created_at DESC LIMIT ?",
                (part_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM inventory_transactions ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
    return [dict(r) for r in rows]
