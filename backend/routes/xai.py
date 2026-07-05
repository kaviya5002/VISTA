"""
XAI Route — /vehicle/{vehicle_id}/explain
==========================================
GET /vehicle/{vehicle_id}/explain

Full pipeline:
  vehicle_id
    └─► fleet_repository     → raw sensors
    └─► health_model_service → health score
    └─► failure_model_service→ failure probability
    └─► root_cause_model     → root cause
    └─► rul_model_service    → remaining useful life
    └─► xai_service          → complete explainability envelope
"""

from fastapi import APIRouter, HTTPException

from services.fleet_repository                      import get_all_vehicles
from services.health_score                          import calculate_health
from services.failure_forecast                      import predict_failure
from services.root_cause                            import analyze_root_cause
from services.rul_engine                            import calculate_rul
from services.cost_analysis                         import calculate_cost_impact
from services.xai_service                           import build_xai_response
from services.xai.feature_importance_service        import get_feature_importances
from services.xai.shap_service                      import explain_vehicle as shap_explain
from services.xai.explanation_service               import generate_explanation

router = APIRouter(tags=["XAI — Explainability"])


def _run_pipeline(vehicle: dict) -> dict:
    """
    Runs the exact same enrichment pipeline used by /fleet and /vehicle/{id},
    so XAI scores are always in sync with what the dashboard shows.
    """
    vehicle = calculate_health(vehicle)
    vehicle = predict_failure(vehicle)
    vehicle = analyze_root_cause(vehicle)
    vehicle = calculate_rul(vehicle)
    return vehicle


@router.get("/vehicle/{vehicle_id}/explain")
def explain_vehicle(vehicle_id: int):
    """
    Returns a complete XAI explanation for a single vehicle.

    Response includes:
      - Feature importance (normalised %, SHAP-ready)
      - Human-readable failure / health / RUL reasoning
      - Per-model confidence scores and metadata
      - Sensor snapshot at time of prediction
      - Fallback info when any ML model is unavailable
    """
    # ── 1. Fetch raw vehicle data ──────────────────────────────────────────
    vehicles = get_all_vehicles()
    vehicle  = next((v for v in vehicles if v["vehicle_id"] == vehicle_id), None)

    if vehicle is None:
        raise HTTPException(
            status_code=404,
            detail={
                "status":  "error",
                "reason":  f"Vehicle {vehicle_id} not found in fleet database.",
                "hint":    "Valid IDs are 1–100. Run seed_data.py if the DB is empty.",
            },
        )

    # ── 2. Enrich with ML predictions ─────────────────────────────────────
    try:
        vehicle = _run_pipeline(vehicle)
    except Exception as exc:
        # Return a graceful fallback instead of a 500 crash
        return {
            "vehicle_id":         vehicle_id,
            "status":             "fallback",
            "reason":             str(exc),
            "prediction_source":  "Formula Engine",
            "sensor_snapshot": {
                "temperature":     vehicle.get("temperature",     0),
                "battery_voltage": vehicle.get("battery_voltage", 0),
                "rpm":             vehicle.get("rpm",             0),
                "speed":           vehicle.get("speed",           0),
            },
        }

    # ── 3. Build XAI response ─────────────────────────────────────────────
    try:
        return build_xai_response(vehicle)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "xai_error",
                "reason": f"XAI service failed: {str(exc)}",
                "prediction_source": "XAI unavailable — use /vehicle/{id} for raw predictions",
            },
        )


@router.get("/xai/features/{vehicle_id}")
def feature_importances(vehicle_id: int):
    """
    Returns top-5 feature importances per model (health, failure,
    root_cause, fleet_priority), normalized to sum to 100%.
    Includes vehicle sensor snapshot and graceful fallbacks.
    """
    # Fetch + enrich vehicle so we can attach its sensor snapshot
    vehicles = get_all_vehicles()
    vehicle  = next((v for v in vehicles if v["vehicle_id"] == vehicle_id), None)

    if vehicle is None:
        raise HTTPException(
            status_code=404,
            detail={"error": f"Vehicle {vehicle_id} not found."},
        )

    try:
        vehicle = calculate_health(vehicle)
        vehicle = predict_failure(vehicle)
        vehicle = analyze_root_cause(vehicle)
        vehicle = calculate_rul(vehicle)
    except Exception:
        pass  # sensor snapshot still useful even if pipeline fails

    importances = get_feature_importances()

    return {
        "vehicle_id": vehicle_id,
        "sensor_snapshot": {
            "battery_voltage": vehicle.get("battery_voltage"),
            "temperature":     vehicle.get("temperature"),
            "rpm":             vehicle.get("rpm"),
            "speed":           vehicle.get("speed"),
            "health_score":    vehicle.get("health_score"),
            "failure_probability": vehicle.get("failure_probability"),
        },
        "feature_importances": importances,
    }


@router.get("/xai/shap/{vehicle_id}")
def shap_explain_vehicle(vehicle_id: int):
    """
    Returns SHAP-based per-vehicle explanation.
    Includes top-5 contributors per model, natural language explanation,
    prediction summary, and recommendation.
    """
    vehicles = get_all_vehicles()
    vehicle  = next((v for v in vehicles if v["vehicle_id"] == vehicle_id), None)

    if vehicle is None:
        raise HTTPException(status_code=404, detail={"error": f"Vehicle {vehicle_id} not found."})

    # Enrich vehicle through full pipeline
    try:
        vehicle = calculate_health(vehicle)
        vehicle = predict_failure(vehicle)
        vehicle = analyze_root_cause(vehicle)
        vehicle = calculate_rul(vehicle)
        vehicle = calculate_cost_impact(vehicle)
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": f"Pipeline failed: {str(e)}"})

    # SHAP explanation
    shap_result  = shap_explain(vehicle)
    explanation  = generate_explanation(vehicle, shap_result)

    # Flatten failure top_factors for easy frontend consumption
    top_factors = shap_result["models"].get("failure", [])

    return {
        "vehicle_id":          vehicle_id,
        "failure_probability": vehicle.get("failure_probability", 0),
        "health_score":        vehicle.get("health_score", 0),
        "rul_days":            vehicle.get("remaining_useful_life_days", 0),
        "status":              vehicle.get("status", "Unknown"),
        "confidence":          vehicle.get("confidence_score", 85),
        "top_factors":         top_factors,
        "all_models":          shap_result["models"],
        "shap_enabled":        shap_result["shap_enabled"],
        "explanation":         explanation["summary"],
        "factors_text":        explanation["factors_text"],
        "rul_note":            explanation["rul_note"],
        "recommendation":      explanation["recommendation"],
        "confidence_note":     explanation["confidence_note"],
        "sensor_snapshot": {
            "battery_voltage": vehicle.get("battery_voltage"),
            "temperature":     vehicle.get("temperature"),
            "rpm":             vehicle.get("rpm"),
            "speed":           vehicle.get("speed"),
        },
    }
