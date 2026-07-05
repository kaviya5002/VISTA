"""
profile_backend.py — Times each stage of the full fleet pipeline.
Run from: d:\\innovent\\backend
    py -3 profile_backend.py
"""
import time
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def t(label: str, start: float):
    ms = (time.perf_counter() - start) * 1000
    print(f"  {label:<30} {ms:>8.1f} ms")
    return time.perf_counter()

print("\n" + "="*52)
print("  BACKEND PIPELINE PROFILER")
print("="*52)

# ── 1. DB query ───────────────────────────────────────
print("\n[1] Database")
s = time.perf_counter()
from services.fleet_repository import get_all_vehicles, get_fleet_sensors
s = time.perf_counter()
vehicles = get_all_vehicles()
s = t(f"get_all_vehicles ({len(vehicles)} rows)", s)
sensors = get_fleet_sensors()
s = t(f"get_fleet_sensors ({len(sensors)} rows)", s)

# ── 2. Health model ───────────────────────────────────
print("\n[2] Health Model")
from services.health_model_service import batch_predict_health
s = time.perf_counter()
health_scores = batch_predict_health(vehicles)
s = t(f"batch_predict_health ({len(vehicles)} vehicles)", s)

# inject so downstream services skip model calls
for i, v in enumerate(vehicles):
    if health_scores[i] is not None:
        v["_batch_health"] = health_scores[i]

from services.health_score import calculate_health
s = time.perf_counter()
for v in vehicles:
    calculate_health(v)
s = t("calculate_health (all 100, rule-based)", s)

# ── 3. Failure model ──────────────────────────────────
print("\n[3] Failure Model")
from services.failure_model_service import batch_predict as batch_predict_failure
s = time.perf_counter()
failure_results = batch_predict_failure(vehicles)
s = t(f"batch_predict_failure ({len(vehicles)} vehicles)", s)

for i, v in enumerate(vehicles):
    if failure_results[i] is not None:
        v["_batch_failure"] = failure_results[i]

from services.failure_forecast import predict_failure
s = time.perf_counter()
for v in vehicles:
    predict_failure(v)
s = t("predict_failure (all 100, rule-based)", s)

# ── 4. Root cause model ───────────────────────────────
print("\n[4] Root Cause Model")
from services.root_cause_model_service import batch_predict_root_cause
s = time.perf_counter()
rc_results = batch_predict_root_cause(vehicles)
s = t(f"batch_predict_root_cause ({len(vehicles)} vehicles)", s)

from services.root_cause import analyze_root_cause
s = time.perf_counter()
for i, v in enumerate(vehicles):
    if rc_results[i] is not None:
        v["root_cause"]        = rc_results[i]
        v["root_cause_source"] = "Root Cause ML Model"
    else:
        analyze_root_cause(v)
s = t("analyze_root_cause fallback (rule-based)", s)

# ── 5. RUL model ──────────────────────────────────────
print("\n[5] RUL Model")
from services.rul_model_service import batch_predict_rul
s = time.perf_counter()
rul_results = batch_predict_rul(vehicles)
s = t(f"batch_predict_rul ({len(vehicles)} vehicles)", s)

from services.rul_engine import calculate_rul
s = time.perf_counter()
for i, v in enumerate(vehicles):
    if rul_results[i] is not None:
        v["remaining_useful_life_days"] = rul_results[i]
        v["rul_source"] = "NASA ML Model"
    else:
        calculate_rul(v)
s = t("calculate_rul fallback (rule-based)", s)

# ── 6. Fleet optimizer ────────────────────────────────
print("\n[6] Fleet Optimizer")
from services.failure_chain import predict_failure_chain
from services.cost_analysis import calculate_cost_impact
from services.maintenance_strategist import ai_maintenance_strategy

s = time.perf_counter()
for v in vehicles: predict_failure_chain(v)
s = t("predict_failure_chain (all 100)", s)

s = time.perf_counter()
for v in vehicles: calculate_cost_impact(v)
s = t("calculate_cost_impact (all 100)", s)

from services.fleet_optimizer import optimize_fleet
s = time.perf_counter()
optimized = optimize_fleet(vehicles)
s = t(f"optimize_fleet ({len(vehicles)} vehicles)", s)

# ── 7. Remaining pipeline ─────────────────────────────
print("\n[7] Maintenance Strategy")
s = time.perf_counter()
for v in vehicles: ai_maintenance_strategy(v)
s = t("ai_maintenance_strategy (all 100)", s)

# ── 8. JSON serialization ─────────────────────────────
print("\n[8] JSON Serialization")
s = time.perf_counter()
payload = json.dumps(optimized)
s = t(f"json.dumps ({len(payload):,} bytes)", s)

# ── TOTAL ─────────────────────────────────────────────
print("\n" + "="*52)
total_start = time.perf_counter()

s = time.perf_counter()
v2 = get_all_vehicles()
h  = batch_predict_health(v2)
f  = batch_predict_failure(v2)
rc = batch_predict_root_cause(v2)
r  = batch_predict_rul(v2)
for i, vv in enumerate(v2):
    if h[i]:  vv["_batch_health"]  = h[i]
    if f[i]:  vv["_batch_failure"] = f[i]
    calculate_health(vv); predict_failure(vv)
    if rc[i]: vv["root_cause"] = rc[i]
    else:     analyze_root_cause(vv)
    if r[i]:  vv["remaining_useful_life_days"] = r[i]
    else:     calculate_rul(vv)
    predict_failure_chain(vv)
    calculate_cost_impact(vv)
    ai_maintenance_strategy(vv)
opt = optimize_fleet(v2)
_ = json.dumps(opt)
total_ms = (time.perf_counter() - s) * 1000

print(f"  {'FULL PIPELINE (end-to-end)':<30} {total_ms:>8.1f} ms")
print("="*52 + "\n")
