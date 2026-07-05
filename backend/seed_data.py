import random
from database import get_connection

conn = get_connection()
cursor = conn.cursor()

for vehicle_id in range(1, 101):
    cursor.execute("""
    INSERT OR REPLACE INTO vehicles
    VALUES (?, ?, ?, ?, ?)
    """, (
        vehicle_id,
        round(random.uniform(9.0, 14.0), 2),    # voltage: wide range
        round(random.uniform(20, 120), 1),        # temperature: realistic spread
        random.randint(500, 7000),               # rpm: wide range
        random.randint(0, 120)                   # speed
    ))

conn.commit()
conn.close()

print("100 Vehicles Seeded with realistic sensor ranges")
