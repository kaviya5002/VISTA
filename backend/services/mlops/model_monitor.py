"""
Model Monitor
=============
Reads the Model Registry and Experiment Tracker to expose structured
model cards: algorithm, version, dataset, training date, CV score,
and all tracked metrics.

Uses the same ModelRegistry / ExperimentTracker classes as the AutoML pipeline.
Paths are resolved relative to backend/ml/ (the registry base_dir).
"""
from __future__ import annotations

import os
import sys

_ML_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "ml")

# Make automl importable without altering sys.path permanently
_AUTOML_DIR = os.path.join(_ML_DIR, "automl")


def _registry(model_name: str):
    """Return a ModelRegistry instance for the given model family."""
    sys.path.insert(0, _AUTOML_DIR)
    try:
        from model_registry import ModelRegistry
        # base_dir must point to ml/models/
        return ModelRegistry(model_name, base_dir=os.path.join(_ML_DIR, "models"))
    finally:
        sys.path.pop(0)


def _tracker():
    """Return an ExperimentTracker instance (reads ml/reports/experiments.csv)."""
    sys.path.insert(0, _AUTOML_DIR)
    try:
        # Tracker writes to cwd/reports — we need to run from ml/
        orig = os.getcwd()
        os.chdir(_ML_DIR)
        from experiment_tracker import ExperimentTracker
        tracker = ExperimentTracker()
        os.chdir(orig)
        return tracker
    finally:
        sys.path.pop(0)


# ── Known model families ──────────────────────────────────────────────────────

_MODEL_NAMES = ["failure", "health", "rootcause", "fleet", "rul"]

_MODEL_META = {
    "failure":   {"task": "classification", "label": "Failure Prediction",    "primary_metric": "F1"},
    "health":    {"task": "regression",     "label": "Health Score Prediction","primary_metric": "R²"},
    "rootcause": {"task": "classification", "label": "Root Cause Analysis",   "primary_metric": "F1"},
    "fleet":     {"task": "classification", "label": "Fleet Priority Ranking","primary_metric": "F1"},
    "rul":       {"task": "regression",     "label": "Remaining Useful Life", "primary_metric": "R²"},
}

# Legacy pkl paths (pre-AutoML) used to determine if a model is deployed
_LEGACY_PATHS = {
    "failure":   ["failure_model_v2.pkl", "failure_model.pkl"],
    "health":    ["health_model_v2.pkl",  "health_model.pkl"],
    "rootcause": ["root_cause_model.pkl"],
    "fleet":     ["fleet_optimizer.pkl"],
    "rul":       ["rul_model.pkl"],
}


def _is_deployed(model_name: str) -> bool:
    """True if any pkl file exists for this model (versioned or legacy)."""
    versioned = os.path.join(_ML_DIR, "models", model_name, "best.pkl")
    if os.path.exists(versioned):
        return True
    for fname in _LEGACY_PATHS.get(model_name, []):
        if os.path.exists(os.path.join(_ML_DIR, fname)):
            return True
    return False


def _build_model_card(model_name: str, tracker_history: list[dict]) -> dict:
    """Assemble a full model card from registry + experiment tracker."""
    reg   = _registry(model_name)
    index = reg.load_metadata()
    meta  = _MODEL_META[model_name]

    best_version = index.get("current_best") or index.get("latest_version")
    version_meta = reg.load_version_metadata(best_version) if best_version else {}
    all_versions = reg.list_versions_with_scores()

    # Pull matching experiment rows from tracker CSV
    experiments = [
        row for row in tracker_history
        if row.get("model_name") == model_name
    ]
    latest_exp = experiments[-1] if experiments else {}

    # Prefer registry version_meta, fall back to experiment tracker row
    algorithm    = version_meta.get("algorithm") or latest_exp.get("algorithm") or index.get("algorithm")
    score        = version_meta.get("score")     or latest_exp.get("primary_score")
    cv_score     = version_meta.get("cv_score")  or latest_exp.get("cv_score")
    dataset      = version_meta.get("dataset")   or latest_exp.get("dataset")   or index.get("dataset")
    trained_on   = version_meta.get("created")   or latest_exp.get("date")      or index.get("last_updated")
    experiment_id = version_meta.get("experiment_id") or latest_exp.get("experiment_id")

    # Collect all tracked metrics from version_meta["metrics"] + experiment row
    metrics: dict = {}
    if version_meta.get("metrics"):
        metrics.update({k: v for k, v in version_meta["metrics"].items() if v not in (None, "", "N/A")})
    for col in ("accuracy", "precision", "recall", "f1", "roc_auc", "r2", "mae", "rmse", "mape"):
        val = latest_exp.get(col)
        if val not in (None, "", "N/A"):
            metrics.setdefault(col, val)

    deployed = _is_deployed(model_name)

    return {
        "name":          model_name,
        "label":         meta["label"],
        "task":          meta["task"],
        "primary_metric": meta["primary_metric"],
        "algorithm":     algorithm,
        "version":       best_version,
        "dataset":       dataset,
        "trained_on":    trained_on,
        "score":         _safe_float(score),
        "cv_score":      _safe_float(cv_score),
        "metrics":       metrics,
        "experiment_id": experiment_id,
        "total_versions": index.get("total_models", len(all_versions)),
        "version_history": all_versions,
        "deployed":      deployed,
        "status":        "deployed" if deployed else "not_trained",
        "params":        version_meta.get("params", {}),
    }


def _safe_float(val) -> float | None:
    try:
        return round(float(val), 4) if val not in (None, "", "N/A") else None
    except (TypeError, ValueError):
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def get_all_models() -> list[dict]:
    """Return model cards for all five model families."""
    try:
        history = _tracker().load_history()
    except Exception:
        history = []
    return [_build_model_card(name, history) for name in _MODEL_NAMES]


def get_model(model_name: str) -> dict | None:
    """Return a single model card, or None if the name is unknown."""
    if model_name not in _MODEL_NAMES:
        return None
    try:
        history = _tracker().load_history()
    except Exception:
        history = []
    return _build_model_card(model_name, history)
