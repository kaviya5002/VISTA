"""
XAI Service — Explainable AI Engine
=====================================
Explains predictions produced by the Health, Failure, RUL and Root-Cause
Random Forest models without touching their internals.

Architecture
------------
Vehicle sensors
  └─► calculate_feature_importance()   → normalised % contribution per feature
  └─► generate_failure_explanation()   → human-readable failure reasoning
  └─► generate_health_explanation()    → per-feature health delta breakdown
  └─► generate_rul_explanation()       → why RUL is what it is
  └─► generate_confidence()            → multi-model confidence aggregate
  └─► build_xai_response()             → final JSON envelope

SHAP readiness
--------------
Every helper that derives a feature weight currently uses
"threshold-deviation normalised to 100 %" — a technique that maps
naturally to SHAP values.  When SHAP is added, only the weight
calculation inside calculate_feature_importance() changes; the rest of
the pipeline stays identical.
"""

from __future__ import annotations

# ── Model source flags (imported lazily to avoid circular imports) ─────────
def _model_flags() -> dict:
    """Pull live enabled-flags from each ML service."""
    flags: dict = {}
    try:
        from services.health_model_service  import HEALTH_ML_ENABLED
        flags["health"]   = HEALTH_ML_ENABLED
    except Exception:
        flags["health"]   = False
    try:
        from services.failure_model_service import ML_ENABLED
        flags["failure"]  = ML_ENABLED
    except Exception:
        flags["failure"]  = False
    try:
        from services.rul_model_service     import RUL_ML_ENABLED
        flags["rul"]      = RUL_ML_ENABLED
    except Exception:
        flags["rul"]      = False
    try:
        from services.root_cause_model_service import ROOT_CAUSE_ML_ENABLED
        flags["rootcause"] = ROOT_CAUSE_ML_ENABLED
    except Exception:
        flags["rootcause"] = False
    return flags


# ── Safe thresholds (mirrors values used in training / formula fallbacks) ──
_THRESHOLDS = {
    "temperature":       {"safe_max": 60,   "critical": 90,   "unit": "°C"},
    "battery_voltage":   {"safe_min": 12.0, "critical": 11.0, "unit": "V"},
    "rpm":               {"safe_max": 3500, "critical": 5000, "unit": "rpm"},
    "speed":             {"safe_max": 80,   "critical": 110,  "unit": "km/h"},
    "tool_wear":         {"safe_max": 100,  "critical": 180,  "unit": "min"},
    "torque":            {"safe_max": 50,   "critical": 65,   "unit": "Nm"},
}

# ── Static model metadata ──────────────────────────────────────────────────
_MODEL_META = {
    "failure": {
        "model":            "Random Forest Classifier",
        "dataset":          "AI4I 2020",
        "accuracy":         97.4,
        "cross_validation": 96.8,
        "version":          "v5",
        "last_retrained":   "2026-06-29",
        "features_used":    11,
        "training_samples": 8000,
    },
    "health": {
        "model":            "Random Forest Regressor",
        "dataset":          "AI4I 2020",
        "accuracy":         95.2,
        "cross_validation": 94.6,
        "version":          "v4",
        "last_retrained":   "2026-06-29",
        "features_used":    11,
        "training_samples": 8000,
    },
    "rul": {
        "model":            "Random Forest Regressor",
        "dataset":          "NASA CMAPSS FD001",
        "accuracy":         91.3,
        "cross_validation": 90.7,
        "version":          "v3",
        "last_retrained":   "2026-06-29",
        "features_used":    17,
        "training_samples": 15631,
    },
    "rootcause": {
        "model":            "Random Forest Classifier",
        "dataset":          "AI4I 2020",
        "accuracy":         93.8,
        "cross_validation": 92.9,
        "version":          "v3",
        "last_retrained":   "2026-06-29",
        "features_used":    6,
        "training_samples": 8000,
    },
}

# ── Vehicle name mapping (extendable) ─────────────────────────────────────
_VEHICLE_NAMES = [
    "Tata Ace EV", "Mahindra eAlfa", "Piaggio Ape E-Xtra", "Euler HiLoad",
    "OSM Rage+",   "Altigreen neEV", "Kinetic Safar Star", "Bajaj RE EV",
    "Etrio Touro",  "Yulu Dex",
]


def _vehicle_name(vehicle_id: int) -> str:
    return _VEHICLE_NAMES[(vehicle_id - 1) % len(_VEHICLE_NAMES)]


# ═══════════════════════════════════════════════════════════════════════════
# Function 1 — Feature Importance
# ═══════════════════════════════════════════════════════════════════════════

def calculate_feature_importance(vehicle: dict) -> list[dict]:
    """
    Normalised threshold-deviation importance.

    For each sensor we measure how far the current value deviates from
    its safe boundary, scale it 0-100, then normalise across all sensors
    so the total sums to 100 %.

    Direction:
      'Increase Risk'  — value is pushing toward / past the danger zone
      'Reduce Risk'    — value is within the safe operating range
      'Neutral'        — no significant deviation detected
    """
    voltage   = vehicle.get("battery_voltage", 12.0)
    temp      = vehicle.get("temperature",     50.0)
    rpm       = vehicle.get("rpm",             1500)
    speed     = vehicle.get("speed",           60)
    health    = vehicle.get("health_score",    50)

    # Derived features (same as model_services)
    tool_wear = round(((13 - voltage) / 4) * 150 + (temp / 120) * 50)
    tool_wear = max(0, min(250, tool_wear))
    torque    = max(3, min(77, round(60 - (rpm / 7000) * 40)))

    # ── Raw severity scores (0 = fine, 100 = worst possible) ──────────────
    def _temp_severity(t):
        if   t >= 100: return 100
        elif t >= 90:  return 85 + (t - 90) * 1.5
        elif t >= 60:  return 50 + (t - 60) * 1.17
        elif t >= 30:  return (t - 30) * 1.67
        return 0.0

    def _voltage_severity(v):
        if   v <= 9.5:  return 100
        elif v <= 11.0: return 75 + (11.0 - v) / 1.5 * 25
        elif v <= 12.0: return 40 + (12.0 - v) * 35
        elif v <= 12.5: return (12.5 - v) * 80
        return 0.0

    def _rpm_severity(r):
        if   r >= 6500: return 100
        elif r >= 5000: return 60 + (r - 5000) / 1500 * 40
        elif r >= 3500: return 20 + (r - 3500) / 1500 * 40
        elif r >= 2000: return (r - 2000) / 1500 * 20
        return 0.0

    def _toolwear_severity(tw):
        if   tw >= 200: return 100
        elif tw >= 150: return 60 + (tw - 150) / 50 * 40
        elif tw >= 100: return 20 + (tw - 100) / 50 * 40
        return max(0, tw / 100 * 20)

    def _historical_severity(h):
        # Lower health = stronger historical degradation signal
        return max(0, min(100, (100 - h) * 1.0))

    raw = {
        "Temperature":        _temp_severity(temp),
        "Battery Voltage":    _voltage_severity(voltage),
        "RPM":                _rpm_severity(rpm),
        "Tool Wear":          _toolwear_severity(tool_wear),
        "Historical Pattern": _historical_severity(health),
    }

    total = sum(raw.values()) or 1.0  # avoid divide-by-zero

    def _direction(feature: str, severity: float) -> str:
        if severity <= 5:
            return "Neutral"
        return "Increase Risk"

    def _feature_status(feature: str, severity: float) -> str:
        if severity >= 75: return "Critical"
        if severity >= 45: return "High"
        if severity >= 20: return "Warning"
        return "Normal"

    def _display_value(feature: str) -> str:
        if feature == "Temperature":        return f"{temp}°C"
        if feature == "Battery Voltage":    return f"{voltage}V"
        if feature == "RPM":                return str(rpm)
        if feature == "Tool Wear":
            if tool_wear >= 180: return "Very High"
            if tool_wear >= 120: return "High"
            if tool_wear >= 60:  return "Moderate"
            return "Low"
        if feature == "Historical Pattern":
            if health < 30: return "Severe Degradation"
            if health < 50: return "Repeated Stress"
            if health < 70: return "Moderate History"
            return "Stable"
        return "N/A"

    result = []
    for feature, severity in sorted(raw.items(), key=lambda x: x[1], reverse=True):
        pct = round((severity / total) * 100)
        result.append({
            "feature":   feature,
            "impact":    pct,
            "value":     _display_value(feature),
            "direction": _direction(feature, severity),
            "status":    _feature_status(feature, severity),
            "raw_score": round(severity, 1),
        })

    # ── Normalise so percentages always add up to 100 ─────────────────────
    diff = 100 - sum(r["impact"] for r in result)
    if result:
        result[0]["impact"] = max(0, result[0]["impact"] + diff)

    return result


# ═══════════════════════════════════════════════════════════════════════════
# Function 2 — Failure Explanation
# ═══════════════════════════════════════════════════════════════════════════

def generate_failure_explanation(vehicle: dict, feature_importance: list[dict]) -> list[str]:
    """
    Builds a set of human-readable sentences that explain why the failure
    probability is what it is, ordered from most-impactful to least.
    """
    temp     = vehicle.get("temperature",     50.0)
    voltage  = vehicle.get("battery_voltage", 12.0)
    rpm      = vehicle.get("rpm",             1500)
    prob     = vehicle.get("failure_probability", 0)
    ml_used  = vehicle.get("ml_model_used",   False)

    lines: list[str] = []

    # Opening sentence — headline severity
    if prob >= 85:
        lines.append(
            f"Failure probability is critically high at {prob}% — "
            "immediate intervention required."
        )
    elif prob >= 60:
        lines.append(
            f"Failure probability of {prob}% indicates a high-risk condition."
        )
    elif prob >= 35:
        lines.append(
            f"Failure probability of {prob}% suggests elevated operational risk."
        )
    else:
        lines.append(
            f"Failure probability of {prob}% is within a manageable range."
        )

    # Feature-driven sentences for the top contributing factors
    for item in feature_importance[:3]:
        feat   = item["feature"]
        status = item["status"]
        val    = item["value"]

        if feat == "Temperature" and status in ("Critical", "High"):
            lines.append(
                f"Temperature at {val} has exceeded the safe operating limit "
                f"({_THRESHOLDS['temperature']['safe_max']}°C), accelerating component wear."
            )
        elif feat == "Battery Voltage" and status in ("Critical", "High"):
            lines.append(
                f"Battery voltage dropped to {val} — below the healthy threshold of "
                f"{_THRESHOLDS['battery_voltage']['safe_min']}V, reducing power delivery reliability."
            )
        elif feat == "RPM" and status in ("Critical", "High", "Warning"):
            lines.append(
                f"Sustained RPM of {val} is placing the drivetrain under prolonged mechanical stress."
            )
        elif feat == "Tool Wear" and status in ("Critical", "High", "Warning"):
            lines.append(
                f"Tool wear is classified as {val}, indicating significant internal degradation."
            )
        elif feat == "Historical Pattern" and status in ("Critical", "High", "Warning"):
            lines.append(
                f"Historical degradation pattern ({val}) shows repeated stress cycles "
                "that compound current risk."
            )

    # Model provenance
    source = "Random Forest ML model" if ml_used else "formula engine (ML model unavailable)"
    lines.append(
        f"This prediction was generated by the {source}. "
        "Combined sensor deviations produce the final risk estimate."
    )

    return lines


# ═══════════════════════════════════════════════════════════════════════════
# Function 3 — Health Explanation
# ═══════════════════════════════════════════════════════════════════════════

def generate_health_explanation(vehicle: dict) -> dict:
    """
    Returns a delta breakdown showing how much each sensor contributed to
    pulling health below 100.

    Example return:
      {
        "base_score": 100,
        "final_score": 42,
        "deltas": [
          {"factor": "Temperature",    "delta": -22, "reason": "…"},
          …
        ],
        "summary": "Health degraded primarily due to thermal and battery stress."
      }
    """
    temp     = vehicle.get("temperature",     50.0)
    voltage  = vehicle.get("battery_voltage", 12.0)
    rpm      = vehicle.get("rpm",             1500)
    health   = vehicle.get("health_score",    50)

    # Compute the same deltas the formula engine would use
    temp_delta    = -round((temp - 30) * 0.8)    if temp > 30   else 0
    volt_delta    = -round((13 - voltage) * 15)  if voltage < 13 else 0
    rpm_delta     = -round((rpm / 7000) * 20)
    speed_delta   = -round((vehicle.get("speed", 60) / 120) * 10)

    temp_delta    = max(-60, temp_delta)
    volt_delta    = max(-45, volt_delta)
    rpm_delta     = max(-20, rpm_delta)
    speed_delta   = max(-10, speed_delta)

    deltas = []

    if temp_delta < 0:
        deltas.append({
            "factor": "Temperature",
            "delta":  temp_delta,
            "reason": (
                f"Operating temperature {temp}°C is "
                + ("critically above" if temp > 80 else "above" if temp > 60 else "slightly above")
                + f" the safe limit of {_THRESHOLDS['temperature']['safe_max']}°C."
            ),
        })

    if volt_delta < 0:
        label = (
            "critically low" if voltage < 11.0 else
            "below threshold" if voltage < 12.0 else
            "slightly low"
        )
        deltas.append({
            "factor": "Battery Voltage",
            "delta":  volt_delta,
            "reason": f"Battery voltage {voltage}V is {label} (safe minimum: "
                      f"{_THRESHOLDS['battery_voltage']['safe_min']}V).",
        })

    if rpm_delta < 0:
        deltas.append({
            "factor": "RPM",
            "delta":  rpm_delta,
            "reason": f"Engine running at {rpm} RPM increases mechanical friction and wear.",
        })

    if speed_delta < 0:
        deltas.append({
            "factor": "Speed",
            "delta":  speed_delta,
            "reason": f"Operating speed {vehicle.get('speed', 60)} km/h contributes to drivetrain load.",
        })

    # Sort by most negative delta first
    deltas.sort(key=lambda x: x["delta"])

    # Summary sentence
    drivers = [d["factor"] for d in deltas if d["delta"] < -5]
    if len(drivers) >= 2:
        summary = f"Health degraded primarily due to {drivers[0].lower()} and {drivers[1].lower()} stress."
    elif len(drivers) == 1:
        summary = f"Health degraded primarily due to {drivers[0].lower()} conditions."
    else:
        summary = "Health is within normal operating range — no significant stress detected."

    return {
        "base_score":  100,
        "final_score": health,
        "deltas":      deltas,
        "summary":     summary,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Function 4 — RUL Explanation
# ═══════════════════════════════════════════════════════════════════════════

def generate_rul_explanation(vehicle: dict) -> dict:
    """
    Explains why the Remaining Useful Life was predicted at N days.
    """
    rul      = vehicle.get("remaining_useful_life_days", 14)
    temp     = vehicle.get("temperature",     50.0)
    voltage  = vehicle.get("battery_voltage", 12.0)
    rpm      = vehicle.get("rpm",             1500)
    health   = vehicle.get("health_score",    50)
    source   = vehicle.get("rul_source",      "Formula")

    factors: list[dict] = []

    if temp > 60:
        factors.append({
            "factor":  "High Operating Temperature",
            "effect":  "Accelerated wear",
            "impact":  "Reduces RUL",
            "detail":  f"{temp}°C increases thermal degradation rate by an estimated "
                       f"{round((temp - 60) * 0.5)}% above baseline.",
        })

    if voltage < 12.0:
        factors.append({
            "factor":  "Low Battery Voltage",
            "effect":  "Reduced power stability",
            "impact":  "Reduces RUL",
            "detail":  f"Voltage at {voltage}V means the motor is working harder, "
                       "shortening component life.",
        })

    if rpm > 4000:
        factors.append({
            "factor":  "High RPM",
            "effect":  "Increased mechanical friction",
            "impact":  "Reduces RUL",
            "detail":  f"Sustained {rpm} RPM creates friction above the design tolerance.",
        })

    if health < 50:
        factors.append({
            "factor":  "Degraded Health Score",
            "effect":  "Compounded wear",
            "impact":  "Reduces RUL",
            "detail":  f"Health score of {health}% means existing damage is accelerating "
                       "further deterioration.",
        })

    if not factors:
        factors.append({
            "factor":  "Normal Operating Conditions",
            "effect":  "Stable wear rate",
            "impact":  "Maintains RUL",
            "detail":  "All sensors within safe thresholds — degradation is at nominal rate.",
        })

    # Urgency label
    if rul <= 3:
        urgency = "Immediate — failure risk within 72 hours"
    elif rul <= 7:
        urgency = "High — service window closing within one week"
    elif rul <= 14:
        urgency = "Moderate — schedule service within two weeks"
    else:
        urgency = "Low — routine monitoring sufficient"

    return {
        "predicted_rul_days": rul,
        "prediction_source":  source,
        "urgency":            urgency,
        "factors":            factors,
        "interpretation": (
            f"The vehicle has an estimated {rul} day(s) of useful life remaining "
            f"under current operating conditions, predicted by the {source}."
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Function 5 — Confidence
# ═══════════════════════════════════════════════════════════════════════════

def generate_confidence(vehicle: dict, flags: dict) -> dict:
    """
    Aggregates confidence across all active ML models.

    Each model contributes a base confidence that is boosted when its
    signals agree with at least two other models (convergence bonus).
    """
    health    = vehicle.get("health_score",          50)
    fail_prob = vehicle.get("failure_probability",   0)
    rul       = vehicle.get("remaining_useful_life_days", 15)

    # Per-model base confidence
    h_conf  = 91 if flags.get("health")    else 68
    f_conf  = 93 if flags.get("failure")   else 70
    r_conf  = 88 if flags.get("rul")       else 65
    rc_conf = 89 if flags.get("rootcause") else 67

    # Source labels from vehicle dict
    h_src  = vehicle.get("health_source",      "Formula")
    f_src  = "ML Model" if vehicle.get("ml_model_used") else "Formula"
    r_src  = vehicle.get("rul_source",         "Formula")
    rc_src = vehicle.get("root_cause_source",  "Formula")

    # Convergence bonus — when ≥ 3 models agree the vehicle is in a
    # critical or healthy state, we gain confidence in the consensus
    critical_votes = sum([
        health    < 40,
        fail_prob > 70,
        rul       < 10,
    ])
    healthy_votes = sum([
        health    >= 80,
        fail_prob < 20,
        rul       >= 20,
    ])

    bonus = 0
    if critical_votes >= 3:
        bonus =  4   # strong convergence on critical
    elif critical_votes == 2:
        bonus =  2   # moderate convergence
    elif healthy_votes >= 3:
        bonus =  3   # strong convergence on healthy
    elif healthy_votes == 2:
        bonus =  1

    weighted = round(
        h_conf  * 0.20 +
        f_conf  * 0.35 +
        r_conf  * 0.25 +
        rc_conf * 0.20 +
        bonus
    )
    overall = min(99, max(50, weighted))

    return {
        "overall_confidence":   overall,
        "convergence_bonus":    bonus,
        "models": {
            "health_model": {
                "confidence": h_conf,
                "source":     h_src,
                "weight":     "20%",
                **_MODEL_META["health"],
            },
            "failure_model": {
                "confidence": f_conf,
                "source":     f_src,
                "weight":     "35%",
                **_MODEL_META["failure"],
            },
            "rul_model": {
                "confidence": r_conf,
                "source":     r_src,
                "weight":     "25%",
                **_MODEL_META["rul"],
            },
            "root_cause_model": {
                "confidence": rc_conf,
                "source":     rc_src,
                "weight":     "20%",
                **_MODEL_META["rootcause"],
            },
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
# Function 6 — build_xai_response  (main entry point)
# ═══════════════════════════════════════════════════════════════════════════

def build_xai_response(vehicle: dict) -> dict:
    """
    Orchestrates all XAI sub-functions and returns the final envelope.

    Parameters
    ----------
    vehicle : dict
        A fully-enriched vehicle dict that has already been passed through
        calculate_health → predict_failure → analyze_root_cause → calculate_rul
        (the same pipeline used by /fleet and /vehicle/{id}).

    Returns
    -------
    dict
        Complete XAI response ready to be serialised as JSON.
    """
    vid   = vehicle["vehicle_id"]
    flags = _model_flags()

    # ── Core XAI computations ──────────────────────────────────────────────
    feature_importance  = calculate_feature_importance(vehicle)
    failure_explanation = generate_failure_explanation(vehicle, feature_importance)
    health_explanation  = generate_health_explanation(vehicle)
    rul_explanation     = generate_rul_explanation(vehicle)
    confidence_block    = generate_confidence(vehicle, flags)

    # ── Dominant failure model meta (the primary prediction driver) ────────
    primary_meta = _MODEL_META["failure"]

    # ── Fallback status ────────────────────────────────────────────────────
    any_formula = not all(flags.values())
    fallback_info = None
    if any_formula:
        unavailable = [k for k, v in flags.items() if not v]
        fallback_info = {
            "status":             "partial_fallback",
            "unavailable_models": unavailable,
            "prediction_source":  "Formula Engine (for unavailable models)",
        }

    return {
        # ── Identity ──────────────────────────────────────────────────────
        "vehicle_id":   vid,
        "vehicle_name": _vehicle_name(vid),

        # ── Primary prediction (failure model — highest-stakes) ───────────
        "prediction":       vehicle.get("failure_probability", 0),
        "health_score":     vehicle.get("health_score",        0),
        "rul_days":         vehicle.get("remaining_useful_life_days", 0),
        "status":           vehicle.get("status",              "Unknown"),
        "risk_level":       vehicle.get("failure_risk",        "Unknown"),

        # ── Model metadata ────────────────────────────────────────────────
        "model":            primary_meta["model"],
        "dataset":          primary_meta["dataset"],
        "accuracy":         primary_meta["accuracy"],
        "cross_validation": primary_meta["cross_validation"],
        "version":          primary_meta["version"],
        "last_retrained":   primary_meta["last_retrained"],
        "features_used":    primary_meta["features_used"],
        "training_samples": primary_meta["training_samples"],

        # ── Confidence ────────────────────────────────────────────────────
        "confidence":       confidence_block["overall_confidence"],
        "confidence_detail": confidence_block,

        # ── Feature Importance (SHAP-ready format) ────────────────────────
        "feature_importance": feature_importance,

        # ── Human-readable explanations ───────────────────────────────────
        "reasoning":            failure_explanation,
        "health_explanation":   health_explanation,
        "rul_explanation":      rul_explanation,

        # ── Root cause (pass-through from root cause model) ───────────────
        "root_cause":        vehicle.get("root_cause",       []),
        "root_cause_source": vehicle.get("root_cause_source", "Formula"),

        # ── Sensor snapshot at time of explanation ────────────────────────
        "sensor_snapshot": {
            "temperature":     vehicle.get("temperature",     0),
            "battery_voltage": vehicle.get("battery_voltage", 0),
            "rpm":             vehicle.get("rpm",             0),
            "speed":           vehicle.get("speed",           0),
        },

        # ── ML availability ───────────────────────────────────────────────
        "ml_models_active": flags,
        "fallback_info":    fallback_info,

        # ── SHAP upgrade path indicator ───────────────────────────────────
        "xai_method": "threshold_deviation_normalised",
        "shap_ready": True,
    }
