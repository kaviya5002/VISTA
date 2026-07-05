"""
Technician Repository
=====================
SQLite-backed persistence for technician records.

Table: technicians
  id, name, skills (JSON), experience, rating,
  available, workload, shift, avatar, phone,
  max_jobs_per_day, specialisation

Seeded from the canonical TECHNICIANS list in technician_assignment_service
on first import so existing data is never lost.
"""
from __future__ import annotations

import json
from database import get_connection

# ── DDL ───────────────────────────────────────────────────────────────────────
_DDL = """
CREATE TABLE IF NOT EXISTS technicians (
    id               INTEGER PRIMARY KEY,
    name             TEXT    NOT NULL,
    skills           TEXT    NOT NULL DEFAULT '[]',
    experience       INTEGER NOT NULL DEFAULT 0,
    rating           REAL    NOT NULL DEFAULT 4.5,
    available        INTEGER NOT NULL DEFAULT 1,
    workload         INTEGER NOT NULL DEFAULT 0,
    shift            TEXT    NOT NULL DEFAULT 'Morning',
    avatar           TEXT    NOT NULL DEFAULT '',
    phone            TEXT    NOT NULL DEFAULT '',
    max_jobs_per_day INTEGER NOT NULL DEFAULT 3,
    specialisation   TEXT    NOT NULL DEFAULT 'General'
);
"""

_SHIFT_HOURS: dict[str, tuple[int, int]] = {
    "Morning":   (8,  16),
    "Afternoon": (12, 20),
    "Night":     (20, 4),
}


def _ensure_table() -> None:
    conn = get_connection()
    try:
        conn.execute(_DDL)
        conn.commit()
    finally:
        conn.close()


def _seed_if_empty() -> None:
    """Seed from the in-memory list if the table has no rows."""
    from services.technician_assignment_service import TECHNICIANS as _SRC

    conn = get_connection()
    try:
        count = conn.execute("SELECT COUNT(*) FROM technicians").fetchone()[0]
        if count > 0:
            return
        for t in _SRC:
            conn.execute(
                """
                INSERT OR IGNORE INTO technicians
                    (id, name, skills, experience, rating, available,
                     workload, shift, avatar, phone, max_jobs_per_day, specialisation)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    t["id"], t["name"],
                    json.dumps(t["skills"]),
                    t["experience"], t["rating"],
                    int(t["available"]), t["workload"],
                    t["shift"], t["avatar"], t["phone"],
                    3,                          # max_jobs_per_day default
                    t["skills"][0] if t["skills"] else "General",
                ),
            )
        conn.commit()
    finally:
        conn.close()


# Run at import time
_ensure_table()
_seed_if_empty()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row_to_dict(row) -> dict:
    d = dict(row)
    d["skills"]    = json.loads(d.get("skills", "[]"))
    d["available"] = bool(d["available"])
    d["shift_hours"] = _SHIFT_HOURS.get(d["shift"], (8, 16))
    d["status"] = (
        "Available" if d["available"] and d["workload"] < d["max_jobs_per_day"]
        else "Working" if d["workload"] > 0
        else "Off Duty"
    )
    return d


# ── Read ──────────────────────────────────────────────────────────────────────

def get_all() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM technicians ORDER BY id").fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_by_id(tech_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM technicians WHERE id = ?", (tech_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def get_available(shift: str | None = None) -> list[dict]:
    """Return technicians who are available and under capacity."""
    conn = get_connection()
    try:
        if shift:
            rows = conn.execute(
                """SELECT * FROM technicians
                   WHERE available = 1 AND workload < max_jobs_per_day AND shift = ?
                   ORDER BY workload ASC, rating DESC""",
                (shift,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM technicians
                   WHERE available = 1 AND workload < max_jobs_per_day
                   ORDER BY workload ASC, rating DESC"""
            ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


# ── Write ─────────────────────────────────────────────────────────────────────

def update_workload(tech_id: int, delta: int) -> dict | None:
    """Increment or decrement workload by delta. Returns updated record."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE technicians SET workload = MAX(0, workload + ?) WHERE id = ?",
            (delta, tech_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM technicians WHERE id = ?", (tech_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def set_availability(tech_id: int, available: bool) -> dict | None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE technicians SET available = ? WHERE id = ?",
            (int(available), tech_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM technicians WHERE id = ?", (tech_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def upsert(tech: dict) -> dict:
    """Insert or replace a technician record."""
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO technicians
                (id, name, skills, experience, rating, available,
                 workload, shift, avatar, phone, max_jobs_per_day, specialisation)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name, skills=excluded.skills,
                experience=excluded.experience, rating=excluded.rating,
                available=excluded.available, workload=excluded.workload,
                shift=excluded.shift, avatar=excluded.avatar,
                phone=excluded.phone, max_jobs_per_day=excluded.max_jobs_per_day,
                specialisation=excluded.specialisation
            """,
            (
                tech["id"], tech["name"],
                json.dumps(tech.get("skills", [])),
                tech.get("experience", 0), tech.get("rating", 4.5),
                int(tech.get("available", True)), tech.get("workload", 0),
                tech.get("shift", "Morning"), tech.get("avatar", ""),
                tech.get("phone", ""), tech.get("max_jobs_per_day", 3),
                tech.get("specialisation", tech.get("skills", ["General"])[0]),
            ),
        )
        conn.commit()
        return get_by_id(tech["id"])
    finally:
        conn.close()


# ── Workforce summary ─────────────────────────────────────────────────────────

def workforce_summary() -> dict:
    techs = get_all()
    total     = len(techs)
    available = sum(1 for t in techs if t["available"] and t["workload"] < t["max_jobs_per_day"])
    working   = sum(1 for t in techs if t["workload"] > 0)
    off_duty  = sum(1 for t in techs if not t["available"])
    avg_load  = round(sum(t["workload"] for t in techs) / max(total, 1), 2)
    capacity  = sum(t["max_jobs_per_day"] - t["workload"] for t in techs if t["available"])

    by_shift: dict[str, int] = {}
    for t in techs:
        by_shift[t["shift"]] = by_shift.get(t["shift"], 0) + 1

    return {
        "total":            total,
        "available":        available,
        "working":          working,
        "off_duty":         off_duty,
        "avg_workload":     avg_load,
        "remaining_capacity": capacity,
        "by_shift":         by_shift,
        "utilisation_pct":  round((working / max(total, 1)) * 100, 1),
    }
