"""
db_migrate.py — Run once to expand vehicles table with all ML-relevant fields.
Usage: py -3 db_migrate.py  (from d:\\innovent\\backend)
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", "fleet.db")

NEW_COLS = [
    ("mileage",           "INTEGER DEFAULT 50000"),
    ("vehicle_age",       "INTEGER DEFAULT 5"),
    ("engine_size",       "REAL    DEFAULT 2.0"),
    ("odometer",          "INTEGER DEFAULT 100000"),
    ("reported_issues",   "INTEGER DEFAULT 1"),
    ("service_history",   "INTEGER DEFAULT 1"),
    ("accident_history",  "INTEGER DEFAULT 0"),
    ("fuel_efficiency",   "REAL    DEFAULT 15.0"),
    ("insurance_premium", "INTEGER DEFAULT 15000"),
    ("tire_condition",    "INTEGER DEFAULT 1"),
    ("brake_condition",   "INTEGER DEFAULT 1"),
    ("fuel_condition",    "INTEGER DEFAULT 1"),
    ("transmission_ok",   "INTEGER DEFAULT 1"),
    ("owner_count",       "INTEGER DEFAULT 1"),
    ("maint_history",     "INTEGER DEFAULT 0"),
    ("model_enc",         "INTEGER DEFAULT 0"),
]

conn   = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get existing columns
cursor.execute("PRAGMA table_info(vehicles)")
existing = {row[1] for row in cursor.fetchall()}

added = 0
for col, definition in NEW_COLS:
    if col not in existing:
        cursor.execute(f"ALTER TABLE vehicles ADD COLUMN {col} {definition}")
        added += 1

conn.commit()
conn.close()
print(f"Migration complete — {added} columns added to vehicles table.")
print("Existing columns were left untouched.")
