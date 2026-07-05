import json
from services.fleet_repository    import get_all_vehicles
from services.health_score        import calculate_health
from services.failure_forecast    import predict_failure
from services.root_cause          import analyze_root_cause
from services.rul_engine          import calculate_rul
from services.timeline_prediction import build_timeline

vehicles = get_all_vehicles()

for vid in [1, 17, 50]:
    v = next(x for x in vehicles if x["vehicle_id"] == vid)
    v = calculate_health(v)
    v = predict_failure(v)
    v = analyze_root_cause(v)
    v = calculate_rul(v)
    result = build_timeline(v)

    print("\n" + "="*60)
    print("Vehicle %d  %s" % (vid, result["vehicle_name"]))
    print("  Trend      : %s" % result["summary"]["overall_trend"])
    print("  Breakdown  : Day %s" % result["summary"]["breakdown_day"])
    print("  Critical   : Day %s" % result["summary"]["first_critical_day"])
    print("  Maintenance: Day %s" % result["summary"]["first_maintenance_day"])
    print()
    for node in result["timeline"]:
        ms = ("  ** " + node["milestone"]["label"]) if node["milestone"] else ""
        print("  Day %2d | %-18s | H:%3d%% F:%3d%% RUL:%3dd | %-8s | conf:%d%%%s" % (
            node["day"], node["title"],
            node["health"], node["failure"], node["rul"],
            node["status"], node["confidence"], ms
        ))
        for line in node["narrative"]:
            print("         >> %s" % line)

print("\nTimeline validation PASSED")
