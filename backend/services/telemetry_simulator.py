import random

def generate_vehicle(vehicle_id):
    return {
        "vehicle_id": vehicle_id,
        "battery_voltage": round(random.uniform(11.0, 13.0), 2),
        "temperature": round(random.uniform(30, 90), 1),
        "rpm": random.randint(800, 5000),
        "speed": random.randint(0, 120)
    }

def generate_fleet(size=100):
    return [generate_vehicle(i) for i in range(1, size + 1)]
