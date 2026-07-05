"""
History Collector
=================
Persists telemetry snapshots into the `vehicle_history` SQLite table.

Schema
------
vehicle_history(
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id      INTEGER  NOT NULL,
    recorded_at     TEXT     NOT NULL,   -- ISO-8601 UTC
    health_score    REAL,
    failure_prob    REAL,
    rul_days        REAL,
    temperature     REAL,
    battery_voltage REAL,
    rpm             INTEGER,
    speed           INTEGER,
    status          TEXT,
    priority        TEXT,
    root_cause      TEXT                 -- JSON array stored as string
)

Index: (vehicle_id, recorded_at) for fast range queries.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from database import get_connection

# ── One-time table + index creation ──────────────────────────────────────────

_DDL = """
CREATE TABLE IF NOT EXISTS vehicle_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id      INTEGER NOT NULL,
    recorded_at     TEXT    NOT NULL,
    health_score    REAL,
    failure_prob    REAL,
    rul_days        REAL,
    temperature     REAL,
    battery_voltage REAL,
    rpm             INTEGER,
    speed           INTEGER,
    status          TEXT,
    priority        TEXT,
    root_cause      TEXT
);
CREATE INDEX IF NOT EXISTS idx_vh_vehicle_time
    ON vehicle_history (vehicle_id, recorded_at);
"""


def ensure_table() -> None:
    conn = get_connection()
    try:
        for stmt in _DDL.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(stmt)
        conn.commit()
    finally:
        conn.close()


# Run at import time so the table always exists before any write.
ensure_table()


# ── Write ─────────────────────────────────────────────────────────────────────

def record_snapshot(vehicle: dict, ts: float | None = None) -> None:
    """
    Persist one telemetry snapshot for a vehicle.

    Parameters
    ----------
    vehicle : enriched vehicle dict (post ML pipeline)
    ts      : unix timestamp; defaults to now
    """
    recorded_at = datetime.fromtimestamp(
        ts or time.time(), tz=timezone.utc
    ).isoformat()

    root_cause_raw = vehicle.get("root_cause", [])
    root_cause_str = json.dumps(root_cause_raw) if isinstance(root_cause_raw, list) else str(root_cause_raw)

    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO vehicle_history
                (vehicle_id, recorded_at, health_score, failure_prob, rul_days,
                 temperature, battery_voltage, rpm, speed, status, priority, root_cause)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                vehicle["vehicle_id"],
                recorded_at,
                vehicle.get("health_score"),
                vehicle.get("failure_probability"),
                vehicle.get("remaining_useful_life_days", vehicle.get("rul_days")),
                vehicle.get("temperature"),
                vehicle.get("battery_voltage"),
                vehicle.get("rpm"),
                vehicle.get("speed"),
                vehicle.get("status"),
                vehicle.get("priority"),
                root_cause_str,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def record_fleet_snapshot(vehicles: list[dict], ts: float | None = None) -> None:
    """Batch-insert snapshots for every vehicle in one transaction."""
    now = ts or time.time()
    recorded_at = datetime.fromtimestamp(now, tz=timezone.utc).isoformat()

    rows = []
    for v in vehicles:
        rc = v.get("root_cause", [])
        rows.append((
            v["vehicle_id"],
            recorded_at,
            v.get("health_score"),
            v.get("failure_probability"),
            v.get("remaining_useful_life_days", v.get("rul_days")),
            v.get("temperature"),
            v.get("battery_voltage"),
            v.get("rpm"),
            v.get("speed"),
            v.get("status"),
            v.get("priority"),
            json.dumps(rc) if isinstance(rc, list) else str(rc),
        ))

    conn = get_connection()
    try:
        conn.executemany(
            """
            INSERT INTO vehicle_history
                (vehicle_id, recorded_at, health_score, failure_prob, rul_days,
                 temperature, battery_voltage, rpm, speed, status, priority, root_cause)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()


# ── Read ──────────────────────────────────────────────────────────────────────

def fetch_history(
    vehicle_id: int,
    *,
    hours: int = 24,
    limit: int = 500,
) -> list[dict]:
    """
    Return rows for `vehicle_id` within the last `hours` hours,
    newest-first, capped at `limit` rows.
    """
    from datetime import timedelta

    since = datetime.now(tz=timezone.utc) - timedelta(hours=hours)
    since_str = since.isoformat()

    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT * FROM vehicle_history
            WHERE vehicle_id = ? AND recorded_at >= ?
            ORDER BY recorded_at ASC
            LIMIT ?
            """,
            (vehicle_id, since_str, limit),
        )
        rows = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

    for r in rows:
        try:
            r["root_cause"] = json.loads(r["root_cause"] or "[]")
        except (json.JSONDecodeError, TypeError):
            r["root_cause"] = []
    return rows


def fetch_fleet_history(
    *,
    hours: int = 24,
    limit_per_vehicle: int = 100,
) -> dict[int, list[dict]]:
    """
    Return {vehicle_id: [rows]} for all vehicles within the last `hours`.
    """
    from datetime import timedelta

    since = (datetime.now(tz=timezone.utc) - timedelta(hours=hours)).isoformat()

    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT * FROM vehicle_history
            WHERE recorded_at >= ?
            ORDER BY vehicle_id ASC, recorded_at ASC
            """,
            (since,),
        )
        all_rows = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

    grouped: dict[int, list[dict]] = {}
    for r in all_rows:
        try:
            r["root_cause"] = json.loads(r["root_cause"] or "[]")
        except (json.JSONDecodeError, TypeError):
            r["root_cause"] = []
        vid = r["vehicle_id"]
        grouped.setdefault(vid, [])
        if len(grouped[vid]) < limit_per_vehicle:
            grouped[vid].append(r)

    return grouped


def purge_old_history(keep_days: int = 30) -> int:
    """Delete rows older than `keep_days`. Returns number of rows deleted."""
    from datetime import timedelta

    cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=keep_days)).isoformat()
    conn = get_connection()
    try:
        cur = conn.execute(
            "DELETE FROM vehicle_history WHERE recorded_at < ?", (cutoff,)
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()
