from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.twin import router as twin_router
from routes.simulate import router as simulate_router
from routes.twin_state import router as twin_state_router
from routes.xai import router as xai_router
from routes.obd import router as obd_router
from websocket.fleet_ws import router as ws_router
from services.timeline_prediction import build_timeline
from fastapi.responses import StreamingResponse
import io, time as _time

from services.vehicle_repository        import get_all_vehicles, get_vehicle as get_vehicle_by_id
from services.health_score              import calculate_health
from services.failure_forecast          import predict_failure
from services.root_cause                import analyze_root_cause
from services.rul_engine                import calculate_rul
from services.failure_chain             import predict_failure_chain
from services.cost_analysis             import calculate_cost_impact
from services.fleet_optimizer           import optimize_fleet
from services.maintenance_strategist    import ai_maintenance_strategy
from services.health_model_service      import batch_predict_health
from services.failure_model_service     import batch_predict as batch_predict_failure
from services.rul_model_service         import batch_predict_rul
from services.root_cause_model_service  import batch_predict_root_cause
from services.xai_service              import build_xai_response
from services.fleet_replay_service     import generate_fleet_replay, generate_vehicle_replay, compare_frames
from services.calendar_service         import generate_calendar
from services.work_order_service       import generate_work_order
from services.technician_assignment_service import get_all_technicians, assign_technician, assign_fleet
from services.spare_parts_service      import get_inventory, forecast_spare_parts
from services.history_service          import get_health_series, get_summary
from services.propagation_engine       import build_propagation

try:
    from services.work_order_pdf import generate_work_order_pdf
    WO_PDF_ENABLED = True
except ImportError:
    WO_PDF_ENABLED = False

from engines.component_twin_engine import (
    build_component_twin, build_component_forecasts, build_component_simulations,
)

try:
    from services.report_service import generate_vehicle_report
    REPORT_ENABLED = True
except ImportError:
    REPORT_ENABLED = False

app = FastAPI()
app.include_router(twin_router)
app.include_router(simulate_router)
app.include_router(twin_state_router)
app.include_router(xai_router)
app.include_router(obd_router)
app.include_router(ws_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# ── Cache ─────────────────────────────────────────────────────────────────────
_cache:         dict = {}   # key → {data, at}
_vehicle_cache: dict = {}   # vehicle_id → {data, at}
_FLEET_TTL   = 30.0         # /fleet, /dashboard, /alerts
_VEHICLE_TTL = 60.0         # /vehicle/{id}  — longer, single vehicle is stable
_HEAVY_TTL   = 60.0         # calendar, replay, assignments

def _cached(key: str, fn, ttl=_FLEET_TTL):
    now = _time.time()
    if key in _cache and (now - _cache[key]["at"]) < ttl:
        return _cache[key]["data"]
    result = fn()
    _cache[key] = {"data": result, "at": now}
    return result

def _cached_vehicle(vid: int, fn):
    now = _time.time()
    if vid in _vehicle_cache and (now - _vehicle_cache[vid]["at"]) < _VEHICLE_TTL:
        return _vehicle_cache[vid]["data"]
    result = fn()
    _vehicle_cache[vid] = {"data": result, "at": now}
    return result


# ── Pipeline helpers ──────────────────────────────────────────────────────────
def _needs(v: dict, key: str) -> bool:
    return key not in v

def _process_fleet_batch(vehicles: list) -> list:
    health_scores   = batch_predict_health(vehicles)
    failure_results = batch_predict_failure(vehicles)
    for i, v in enumerate(vehicles):
        if health_scores[i]   is not None: v["_batch_health"]  = health_scores[i]
        if failure_results[i] is not None: v["_batch_failure"] = failure_results[i]
        calculate_health(v)
        predict_failure(v)

    rc_results  = batch_predict_root_cause(vehicles)
    rul_results = batch_predict_rul(vehicles)
    for i, v in enumerate(vehicles):
        if rc_results[i]  is not None: v["root_cause"] = rc_results[i];  v["root_cause_source"] = "Root Cause ML Model"
        else: analyze_root_cause(v)
        if rul_results[i] is not None: v["remaining_useful_life_days"] = rul_results[i]; v["rul_source"] = "NASA ML Model"
        else: calculate_rul(v)

    for v in vehicles:
        predict_failure_chain(v)
        calculate_cost_impact(v)
        ai_maintenance_strategy(v)
    return vehicles

def _process_single(vehicle: dict) -> dict:
    if _needs(vehicle, "health_score"):               calculate_health(vehicle)
    if _needs(vehicle, "failure_probability"):        predict_failure(vehicle)
    if _needs(vehicle, "root_cause"):                 analyze_root_cause(vehicle)
    if _needs(vehicle, "remaining_useful_life_days"): calculate_rul(vehicle)
    if _needs(vehicle, "failure_chain"):              predict_failure_chain(vehicle)
    if _needs(vehicle, "repair_now_cost"):            calculate_cost_impact(vehicle)
    if _needs(vehicle, "maintenance_recommendation"): ai_maintenance_strategy(vehicle)
    return vehicle


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "VISTA Backend Running"}


@app.get("/cache/clear")
def clear_cache():
    """Dev helper — wipe all cached results so next request recomputes."""
    _cache.clear()
    _vehicle_cache.clear()
    return {"cleared": True}


@app.post("/vehicles/reload")
def reload_vehicles():
    """Hot-reload vehicle JSON files from disk without restarting the server."""
    from services.vehicle_repository import reload_data
    _cache.clear()
    _vehicle_cache.clear()
    count = reload_data()
    return {"reloaded": True, "vehicles_loaded": count}


@app.get("/dashboard")
def dashboard():
    """Pure DB aggregation — no ML. Returns in <5ms."""
    def _build():
        vehicles = get_all_vehicles()
        total    = len(vehicles)
        critical = sum(1 for v in vehicles if v.get("battery_voltage", 12) < 11.0 or v.get("temperature", 50) > 90)
        healthy  = sum(1 for v in vehicles if v.get("battery_voltage", 12) >= 12.5 and v.get("temperature", 50) <= 70)
        warning  = total - healthy - critical
        alerts = []
        for v in vehicles:
            if v["temperature"] > 100:
                alerts.append({"vehicle_id": v["vehicle_id"], "alert_type": "Critical Overheating",
                    "severity": "Critical", "message": f"Temperature {v['temperature']}°C", "action": "Immediate Repair"})
            if v["battery_voltage"] < 10:
                alerts.append({"vehicle_id": v["vehicle_id"], "alert_type": "Battery Failure Risk",
                    "severity": "Critical", "message": f"Voltage {v['battery_voltage']}V", "action": "Workshop Visit"})
            if v["rpm"] > 6500:
                alerts.append({"vehicle_id": v["vehicle_id"], "alert_type": "Engine Stress",
                    "severity": "High", "message": f"RPM {v['rpm']}", "action": "Urgent Inspection"})
        alerts.sort(key=lambda x: 0 if x["severity"] == "Critical" else 1)
        return {"total": total, "healthy": healthy, "warning": warning, "critical": critical, "alerts": alerts}
    return _cached("dashboard", _build, _FLEET_TTL)


@app.get("/alerts")
def alerts():
    def _build():
        vehicles = get_all_vehicles()
        out = []
        for v in vehicles:
            if v["temperature"] > 100:
                out.append({"vehicle_id": v["vehicle_id"], "alert_type": "Critical Overheating",
                    "severity": "Critical", "message": f"Temperature {v['temperature']}°C", "action": "Immediate Repair"})
            if v["battery_voltage"] < 10:
                out.append({"vehicle_id": v["vehicle_id"], "alert_type": "Battery Failure Risk",
                    "severity": "Critical", "message": f"Voltage {v['battery_voltage']}V", "action": "Workshop Visit"})
            if v["rpm"] > 6500:
                out.append({"vehicle_id": v["vehicle_id"], "alert_type": "Engine Stress",
                    "severity": "High", "message": f"RPM {v['rpm']}", "action": "Urgent Inspection"})
        out.sort(key=lambda x: 0 if x["severity"] == "Critical" else 1)
        return out
    return _cached("alerts", _build, _FLEET_TTL)


@app.get("/fleet")
def fleet():
    def _build():
        vehicles = get_all_vehicles()
        _process_fleet_batch(vehicles)
        return optimize_fleet(vehicles)
    return _cached("fleet", _build, _FLEET_TTL)


@app.get("/vehicle/{vehicle_id}")
def vehicle_detail(vehicle_id: int):
    def _build():
        vehicle = get_vehicle_by_id(vehicle_id)
        if not vehicle:
            return {"error": "Vehicle not found"}
        _process_single(vehicle)
        return optimize_fleet([vehicle])[0]
    return _cached_vehicle(vehicle_id, _build)


@app.get("/vehicle/{vehicle_id}/history")
def vehicle_history(vehicle_id: int):
    return {
        "vehicle_id": vehicle_id,
        "series":     get_health_series(vehicle_id),
        "summary":    get_summary(vehicle_id),
    }


@app.get("/vehicle/{vehicle_id}/timeline")
def vehicle_timeline(vehicle_id: int):
    def _build():
        vehicle = get_vehicle_by_id(vehicle_id)
        if not vehicle:
            return {"error": "Vehicle not found"}
        return build_timeline(_process_single(vehicle))
    return _cached(f"timeline_{vehicle_id}", _build, _VEHICLE_TTL)


@app.get("/vehicle/{vehicle_id}/propagation")
def vehicle_propagation(vehicle_id: int):
    def _build():
        vehicle = get_vehicle_by_id(vehicle_id)
        if not vehicle:
            return {"error": "Vehicle not found"}
        _process_single(vehicle)
        return build_propagation(vehicle)
    return _cached(f"prop_{vehicle_id}", _build, _VEHICLE_TTL)


@app.get("/component_twin/{vehicle_id}")
def component_twin(vehicle_id: int):
    def _build():
        vehicle = get_vehicle_by_id(vehicle_id)
        if not vehicle:
            return {"error": "Vehicle not found"}
        _process_single(vehicle)
        return build_component_twin(vehicle)
    return _cached(f"ctwin_{vehicle_id}", _build, _VEHICLE_TTL)


@app.get("/component_twin/{vehicle_id}/forecast")
def component_twin_forecast(vehicle_id: int):
    def _build():
        vehicle = get_vehicle_by_id(vehicle_id)
        if not vehicle:
            return {"error": "Vehicle not found"}
        _process_single(vehicle)
        return build_component_forecasts(vehicle)
    return _cached(f"ctwin_forecast_{vehicle_id}", _build, _VEHICLE_TTL)


@app.get("/component_twin/{vehicle_id}/simulate")
def component_twin_simulate(vehicle_id: int):
    def _build():
        vehicle = get_vehicle_by_id(vehicle_id)
        if not vehicle:
            return {"error": "Vehicle not found"}
        _process_single(vehicle)
        return build_component_simulations(vehicle)
    return _cached(f"ctwin_sim_{vehicle_id}", _build, _VEHICLE_TTL)


@app.get("/fleet/replay")
def fleet_replay():
    def _build():
        vehicles = get_all_vehicles()
        _process_fleet_batch(vehicles)
        frames = generate_fleet_replay(vehicles)
        return {"total_frames": len(frames), "frames": frames}
    return _cached("fleet_replay", _build, _HEAVY_TTL)


@app.get("/vehicle/{vehicle_id}/replay")
def vehicle_replay(vehicle_id: int):
    def _build():
        vehicle = get_vehicle_by_id(vehicle_id)
        if not vehicle:
            return {"error": "Vehicle not found"}
        _process_single(vehicle)
        frames = generate_vehicle_replay(vehicle)
        return {"vehicle_id": vehicle_id, "total_frames": len(frames), "frames": frames}
    return _cached(f"replay_{vehicle_id}", _build, _VEHICLE_TTL)


@app.get("/fleet/replay/compare")
def fleet_replay_compare(hour_a: int = 0, hour_b: int = 12):
    vehicles = get_all_vehicles()
    _process_fleet_batch(vehicles)
    frames = generate_fleet_replay(vehicles)
    return compare_frames(frames, hour_a, hour_b)


@app.get("/calendar")
def maintenance_calendar():
    def _build():
        vehicles = get_all_vehicles()
        _process_fleet_batch(vehicles)
        return generate_calendar(optimize_fleet(vehicles))
    return _cached("calendar", _build, _HEAVY_TTL)


@app.get("/inventory")
def inventory():
    return get_inventory()


@app.get("/spare-parts/forecast")
def spare_parts_forecast():
    def _build():
        vehicles = get_all_vehicles()
        _process_fleet_batch(vehicles)
        return forecast_spare_parts(optimize_fleet(vehicles))
    return _cached("spare_parts", _build, _HEAVY_TTL)


@app.get("/technicians")
def technicians():
    return _cached("technicians", get_all_technicians, _HEAVY_TTL)


@app.get("/assignment/{vehicle_id}")
def technician_assignment(vehicle_id: int):
    def _build():
        vehicle = get_vehicle_by_id(vehicle_id)
        if not vehicle:
            return {"error": "Vehicle not found"}
        _process_single(vehicle)
        return assign_technician(optimize_fleet([vehicle])[0])
    return _cached(f"assign_{vehicle_id}", _build, _VEHICLE_TTL)


@app.get("/assignments/fleet")
def fleet_assignments():
    def _build():
        vehicles = get_all_vehicles()
        _process_fleet_batch(vehicles)
        return assign_fleet(optimize_fleet(vehicles))
    return _cached("fleet_assignments", _build, _HEAVY_TTL)


@app.get("/workorder/{vehicle_id}")
def work_order(vehicle_id: int):
    def _build():
        vehicle = get_vehicle_by_id(vehicle_id)
        if not vehicle:
            return {"error": "Vehicle not found"}
        _process_single(vehicle)
        return generate_work_order(optimize_fleet([vehicle])[0])
    return _cached(f"wo_{vehicle_id}", _build, _VEHICLE_TTL)


@app.get("/workorder/{vehicle_id}/pdf")
def work_order_pdf(vehicle_id: int):
    if not WO_PDF_ENABLED:
        return {"error": "reportlab not installed"}
    vehicle = get_vehicle_by_id(vehicle_id)
    if not vehicle:
        return {"error": "Vehicle not found"}
    _process_single(vehicle)
    wo = generate_work_order(optimize_fleet([vehicle])[0])
    pdf_bytes = generate_work_order_pdf(wo)
    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=WorkOrder_{vehicle_id}_{wo['work_order_id']}.pdf"})


@app.get("/xai/{vehicle_id}")
def xai_explain(vehicle_id: int):
    def _build():
        vehicle = get_vehicle_by_id(vehicle_id)
        if not vehicle:
            return {"error": "Vehicle not found"}
        _process_single(vehicle)
        return build_xai_response(vehicle)
    return _cached(f"xai_{vehicle_id}", _build, _VEHICLE_TTL)


@app.get("/report/{vehicle_id}")
def vehicle_report(vehicle_id: int):
    if not REPORT_ENABLED:
        return {"error": "reportlab not installed. Run: pip install reportlab"}
    vehicle = get_vehicle_by_id(vehicle_id)
    if not vehicle:
        return {"error": "Vehicle not found"}
    _process_single(vehicle)
    vehicle = optimize_fleet([vehicle])[0]
    pdf_bytes = generate_vehicle_report(vehicle)
    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Vehicle{vehicle_id}_Report.pdf"})
