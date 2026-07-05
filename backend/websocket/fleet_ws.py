import asyncio
import json
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from websocket.websocket_manager        import manager
from services.vehicle_repository        import get_all_vehicles
from services.health_score              import calculate_health
from services.failure_forecast          import predict_failure
from services.rul_engine                import calculate_rul
from services.health_model_service      import batch_predict_health
from services.failure_model_service     import batch_predict as batch_predict_failure
from services.rul_model_service         import batch_predict_rul
import services.twin_state_manager as tsm
from services.event_engine              import process as run_events

router = APIRouter()

_INTERVAL    = 5.0   # check for changes every 5s
_CACHE_TTL   = 10.0  # rebuild ML scores every 10s

_fleet_cache:    list[dict] = []
_cache_built_at: float      = 0.0
_prev_snapshot:  dict[int, dict] = {}  # vehicle_id → last pushed values


def _build_fleet() -> list[dict]:
    global _fleet_cache, _cache_built_at
    now = time.time()
    if _fleet_cache and (now - _cache_built_at) < _CACHE_TTL:
        return _fleet_cache

    vehicles = get_all_vehicles()
    health_scores   = batch_predict_health(vehicles)
    failure_results = batch_predict_failure(vehicles)
    rul_results     = batch_predict_rul(vehicles)

    result = []
    for i, v in enumerate(vehicles):
        if health_scores[i]   is not None: v["_batch_health"]  = health_scores[i]
        if failure_results[i] is not None: v["_batch_failure"] = failure_results[i]
        calculate_health(v)
        predict_failure(v)
        rul = rul_results[i] if rul_results[i] is not None else max(1, round((v["health_score"] / 100) * 30))
        result.append({
            "vehicle_id":          v["vehicle_id"],
            "health":              v["health_score"],
            "failure_probability": v["failure_probability"],
            "temperature":         v["temperature"],
            "battery_voltage":     v["battery_voltage"],
            "rpm":                 v["rpm"],
            "speed":               v.get("speed", 0),
            "rul":                 rul,
            "status":              v["status"],
        })

    _fleet_cache    = result
    _cache_built_at = now
    return result


def _get_changed(fleet: list[dict]) -> list[dict]:
    """Return only vehicles whose values changed since last push."""
    global _prev_snapshot
    changed = []
    for v in fleet:
        vid  = v["vehicle_id"]
        prev = _prev_snapshot.get(vid)
        if prev != v:
            changed.append(v)
            _prev_snapshot[vid] = v.copy()
    return changed


def _ingest(fleet: list[dict]) -> None:
    for snap in fleet:
        state = tsm.update_twin(snap["vehicle_id"], snap)
        run_events(state)


@router.websocket("/ws/fleet")
async def fleet_websocket(ws: WebSocket):
    await manager.connect(ws)
    try:
        # Send full snapshot on connect
        fleet = _build_fleet()
        _ingest(fleet)
        # Mark all as seen so first diff is empty (client has full data)
        for v in fleet:
            _prev_snapshot[v["vehicle_id"]] = v.copy()
        await ws.send_text(json.dumps({"type": "snapshot", "data": fleet}))

        while True:
            await asyncio.sleep(_INTERVAL)
            fleet   = _build_fleet()
            changed = _get_changed(fleet)
            _ingest(changed if changed else fleet)
            if changed:
                # Push only changed vehicles — much smaller payload
                await manager.broadcast({"type": "patch", "data": changed})

    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)
