from services.fleet_repository import get_all_vehicles
from services.health_score import calculate_health
from services.failure_forecast import predict_failure
from services.root_cause import analyze_root_cause
from services.rul_engine import calculate_rul

vehicles = get_all_vehicles()
print("Vehicles count:", len(vehicles))
v = dict(vehicles[0])
print("Raw vehicle:", v)
v = calculate_health(v)
print("After health:", v.get("health_score"), v.get("status"), v.get("health_source"))
v = predict_failure(v)
print("After failure:", v.get("failure_probability"), v.get("ml_model_used"))
v = analyze_root_cause(v)
print("After root cause:", v.get("root_cause"))
v = calculate_rul(v)
print("After RUL:", v.get("remaining_useful_life_days"), v.get("rul_source"))
print("FULL PIPELINE OK")
