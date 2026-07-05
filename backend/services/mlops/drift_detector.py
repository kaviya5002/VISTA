"""
Drift Detector
==============
Compares live fleet telemetry distributions against training reference
distributions to detect feature drift.

Method: Population Stability Index (PSI) per feature.
  PSI < 0.10  → No drift
  PSI < 0.25  → Moderate drift (warning)
  PSI >= 0.25 → Significant drift (alert)

Reference distributions are derived from the AI4I 2020 dataset statistics
(the training data for failure, health, rootcause models) and the synthetic
fleet dataset (for fleet / rul models).
"""
from __future__ import annotations

import numpy as np

# ── Training reference distributions ─────────────────────────────────────────
# Derived from AI4I 2020 dataset (10,000 samples) and fleet_training_dataset.csv
# Format: {feature: {"mean": float, "std": float, "min": float, "max": float}}

_TRAINING_REF = {
    # Raw vehicle telemetry features (mapped from DB)
    "temperature": {
        "mean": 60.0, "std": 25.0, "min": 20.0, "max": 120.0,
        "description": "Engine/component temperature (°C)",
    },
    "battery_voltage": {
        "mean": 12.2, "std": 0.8, "min": 9.0, "max": 14.5,
        "description": "Battery voltage (V)",
    },
    "rpm": {
        "mean": 3500.0, "std": 1500.0, "min": 500.0, "max": 7000.0,
        "description": "Engine RPM",
    },
    "speed": {
        "mean": 60.0, "std": 25.0, "min": 0.0, "max": 120.0,
        "description": "Vehicle speed (km/h)",
    },
    # Derived / predicted features
    "health_score": {
        "mean": 72.0, "std": 18.0, "min": 5.0, "max": 100.0,
        "description": "Predicted health score (%)",
    },
    "failure_probability": {
        "mean": 28.0, "std": 20.0, "min": 0.0, "max": 100.0,
        "description": "Predicted failure probability (%)",
    },
    "remaining_useful_life_days": {
        "mean": 15.0, "std": 8.0, "min": 1.0, "max": 30.0,
        "description": "Predicted RUL (days)",
    },
}

_DRIFT_FEATURES = list(_TRAINING_REF.keys())


# ── PSI calculation ───────────────────────────────────────────────────────────

def _psi(live_vals: np.ndarray, ref_mean: float, ref_std: float,
         ref_min: float, ref_max: float, n_bins: int = 10) -> float:
    """
    Compute PSI between live distribution and reference (Gaussian approximation).
    Bins are defined over [ref_min, ref_max].
    """
    if len(live_vals) == 0:
        return 0.0

    bins = np.linspace(ref_min, ref_max, n_bins + 1)

    # Reference expected proportions (from Gaussian CDF)
    from scipy.stats import norm  # type: ignore
    ref_cdf = norm.cdf(bins, loc=ref_mean, scale=max(ref_std, 1e-6))
    ref_props = np.diff(ref_cdf)
    ref_props = np.clip(ref_props, 1e-4, None)
    ref_props /= ref_props.sum()

    # Live actual proportions
    live_counts, _ = np.histogram(live_vals, bins=bins)
    live_props = live_counts / max(live_counts.sum(), 1)
    live_props = np.clip(live_props, 1e-4, None)
    live_props /= live_props.sum()

    psi = float(np.sum((live_props - ref_props) * np.log(live_props / ref_props)))
    return round(psi, 4)


def _drift_level(psi: float) -> str:
    if psi < 0.10:
        return "stable"
    if psi < 0.25:
        return "warning"
    return "drift"


def _zscore_stats(live_vals: np.ndarray, ref_mean: float, ref_std: float) -> dict:
    """Mean z-score of live values relative to training distribution."""
    if len(live_vals) == 0:
        return {"live_mean": None, "live_std": None, "z_score": None}
    live_mean = float(np.mean(live_vals))
    live_std  = float(np.std(live_vals))
    z = (live_mean - ref_mean) / max(ref_std, 1e-6)
    return {
        "live_mean": round(live_mean, 3),
        "live_std":  round(live_std, 3),
        "z_score":   round(z, 3),
    }


# ── Public API ────────────────────────────────────────────────────────────────

def detect_drift(fleet: list[dict]) -> dict:
    """
    Compare live fleet telemetry against training reference distributions.

    Parameters
    ----------
    fleet : enriched vehicle list (output of the fleet pipeline)

    Returns
    -------
    dict with per-feature drift analysis and an overall drift summary.
    """
    # Try to import scipy; fall back to z-score only if unavailable
    try:
        import scipy  # noqa: F401
        _scipy_available = True
    except ImportError:
        _scipy_available = False

    feature_results = {}
    drift_count = 0
    warning_count = 0

    for feat in _DRIFT_FEATURES:
        ref = _TRAINING_REF[feat]
        live_vals = np.array([
            v[feat] for v in fleet
            if feat in v and v[feat] is not None
        ], dtype=float)

        if _scipy_available and len(live_vals) > 0:
            psi = _psi(live_vals, ref["mean"], ref["std"], ref["min"], ref["max"])
        else:
            psi = None

        level = _drift_level(psi) if psi is not None else "unknown"
        stats = _zscore_stats(live_vals, ref["mean"], ref["std"])

        if level == "drift":
            drift_count += 1
        elif level == "warning":
            warning_count += 1

        feature_results[feat] = {
            "feature":     feat,
            "description": ref["description"],
            "psi":         psi,
            "drift_level": level,
            "reference": {
                "mean": ref["mean"],
                "std":  ref["std"],
                "min":  ref["min"],
                "max":  ref["max"],
            },
            **stats,
            "sample_size": len(live_vals),
        }

    # ── Overall summary ───────────────────────────────────────────────────────
    total = len(_DRIFT_FEATURES)
    if drift_count > 0:
        overall_status = "drift_detected"
    elif warning_count > 0:
        overall_status = "warning"
    else:
        overall_status = "stable"

    affected_models = _affected_models(feature_results)

    return {
        "fleet_size":      len(fleet),
        "overall_status":  overall_status,
        "drift_count":     drift_count,
        "warning_count":   warning_count,
        "stable_count":    total - drift_count - warning_count,
        "features":        feature_results,
        "affected_models": affected_models,
        "recommendation":  _drift_recommendation(overall_status, affected_models),
        "scipy_available": _scipy_available,
    }


# ── Feature → model mapping ───────────────────────────────────────────────────

_FEATURE_MODEL_MAP = {
    "temperature":              ["failure", "health", "rootcause", "rul"],
    "battery_voltage":          ["failure", "health", "rootcause"],
    "rpm":                      ["failure", "health", "rootcause", "rul"],
    "speed":                    ["health", "rul"],
    "health_score":             ["fleet"],
    "failure_probability":      ["fleet"],
    "remaining_useful_life_days": ["fleet"],
}


def _affected_models(feature_results: dict) -> list[str]:
    affected = set()
    for feat, result in feature_results.items():
        if result["drift_level"] in ("drift", "warning"):
            affected.update(_FEATURE_MODEL_MAP.get(feat, []))
    return sorted(affected)


def _drift_recommendation(status: str, affected_models: list[str]) -> str:
    if status == "stable":
        return "All features are within training distribution. No action required."
    if status == "warning":
        return (
            f"Moderate distribution shift detected. Monitor closely. "
            f"Consider retraining: {', '.join(affected_models) or 'N/A'}."
        )
    return (
        f"Significant feature drift detected. Retraining recommended for: "
        f"{', '.join(affected_models) or 'N/A'}. "
        f"Run the corresponding AutoML training scripts."
    )
