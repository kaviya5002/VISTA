from database import get_connection

conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id INTEGER PRIMARY KEY,
    battery_voltage REAL,
    temperature REAL,
    rpm INTEGER,
    speed INTEGER
)
""")

conn.commit()
conn.close()

print("Database Initialized")
