"""
routes/obd.py — Endpoints that expose raw OBD data, diagnostics, and provenance.
"""
from fastapi import APIRouter, HTTPException
from services.vehicle_repository import (
    get_all_vehicles,
    get_vehicle_obd,
    get_vehicle_diagnostics,
)

router = APIRouter(prefix="/obd", tags=["obd"])


@router.get("/vehicles")
def obd_fleet():
    """All vehicles with full OBD metadata."""
    return [get_vehicle_obd(v["vehicle_id"]) for v in get_all_vehicles()]


@router.get("/vehicles/{vehicle_id}")
def obd_vehicle(vehicle_id: int):
    """Single vehicle raw OBD block."""
    data = get_vehicle_obd(vehicle_id)
    if not data:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return data


@router.get("/vehicles/{vehicle_id}/dtc")
def obd_dtc(vehicle_id: int):
    """DTC fault codes + MIL status."""
    diag = get_vehicle_diagnostics(vehicle_id)
    if not diag:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return {k: diag[k] for k in ("vehicle_id", "vin", "mil_status", "dtc_codes", "dtc_count", "collected_at", "scanner")}


@router.get("/vehicles/{vehicle_id}/provenance")
def obd_provenance(vehicle_id: int):
    """Data provenance — who collected it, when, with what tool."""
    diag = get_vehicle_diagnostics(vehicle_id)
    if not diag:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return diag
