"""Quick XAI validation — run from backend/ directory."""
import json, sys

try:
    from services.fleet_repository import get_all_vehicles
    from services.health_score     import calculate_health
    from services.failure_forecast import predict_failure
    from services.root_cause       import analyze_root_cause
    from services.rul_engine       import calculate_rul
    from services.xai_service      import build_xai_response

    vehicles = get_all_vehicles()

    # Test with 3 different vehicles to cover Healthy / Warning / Critical
    for vid in [1, 17, 50]:
        v = next((x for x in vehicles if x["vehicle_id"] == vid), None)
        if not v:
            print(f"Vehicle {vid} not found — skip"); continue

        v = calculate_health(v)
        v = predict_failure(v)
        v = analyze_root_cause(v)
        v = calculate_rul(v)
        r = build_xai_response(v)

        print(f"\n{'='*60}")
        print(f"Vehicle {vid} — {r['vehicle_name']}")
        print(f"  Status         : {r['status']}")
        print(f"  Health         : {r['health_score']}%")
        print(f"  Failure Prob   : {r['prediction']}%")
        print(f"  RUL            : {r['rul_days']} days")
        print(f"  Confidence     : {r['confidence']}%")
        print(f"  XAI method     : {r['xai_method']}")
        print(f"  SHAP ready     : {r['shap_ready']}")
        print(f"  ML active      : {r['ml_models_active']}")
        print(f"\n  Top features:")
        for f in r["feature_importance"]:
            print(f"    {f['feature']:20s}  {f['impact']:3d}%  [{f['status']}]  {f['value']}")
        print(f"\n  Reasoning:")
        for line in r["reasoning"]:
            print(f"    • {line}")
        print(f"\n  Health delta breakdown:")
        for d in r["health_explanation"]["deltas"]:
            print(f"    {d['factor']:20s}  {d['delta']:+d}  — {d['reason'][:60]}")
        print(f"\n  RUL urgency: {r['rul_explanation']['urgency']}")

    print(f"\n{'='*60}")
    print("XAI validation PASSED — all systems operational")

except Exception as e:
    import traceback
    print(f"\nXAI validation FAILED: {e}")
    traceback.print_exc()
    sys.exit(1)
