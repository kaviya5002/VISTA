"""
Model Health
============
Summarises operational status for each model:
  - Deployment state and version
  - Live prediction counts (derived from fleet telemetry)
  - Score-based health rating
  - Retraining recommendations with justification
"""
from __future__ import annotations

from services.mlops.model_monitor import get_all_models, _is_deployed

# Minimum acceptable scores before a retraining recommendation is raised
_SCORE_THRESHOLDS = {
    "failure":   {"warn": 90.0,  "critical": 80.0},   # F1 %
    "health":    {"warn": 0.85,  "critical": 0.70},   # R²
    "rootcause": {"warn": 85.0,  "critical": 70.0},   # F1 %
    "fleet":     {"warn": 88.0,  "critical": 75.0},   # F1 %
    "rul":       {"warn": 0.80,  "critical": 0.65},   # R²
}

_RETRAIN_SCRIPTS = {
    "failure":   "python ml/automl/train_failure_automl.py",
    "health":    "python ml/automl/train_health_automl.py",
    "rootcause": "python ml/automl/train_rootcause_automl.py",
    "fleet":     "python ml/automl/train_fleet_automl.py",
    "rul":       "python ml/automl/train_rul_automl.py",  # placeholder
}


def _score_health(model_name: str, score: float | None) -> str:
    """Return 'healthy' | 'warning' | 'critical' | 'unknown'."""
    if score is None:
        return "unknown"
    thresh = _SCORE_THRESHOLDS.get(model_name, {"warn": 80.0, "critical": 60.0})
    if score >= thresh["warn"]:
        return "healthy"
    if score >= thresh["critical"]:
        return "warning"
    return "critical"


def _retrain_recommendation(model_name: str, card: dict) -> dict | None:
    """Return a retraining recommendation dict, or None if not needed."""
    reasons = []

    if not card["deployed"]:
        reasons.append("Model has not been trained yet")

    score = card.get("score")
    if score is not None:
        thresh = _SCORE_THRESHOLDS.get(model_name, {"warn": 80.0, "critical": 60.0})
        if score < thresh["critical"]:
            reasons.append(f"Score {score} is below critical threshold {thresh['critical']}")
        elif score < thresh["warn"]:
            reasons.append(f"Score {score} is below warning threshold {thresh['warn']}")

    if card.get("total_versions", 0) == 0:
        reasons.append("No versioned models in registry")

    if not reasons:
        return None

    urgency = "critical" if any("critical" in r.lower() or "not been trained" in r for r in reasons) else "recommended"
    return {
        "urgency":       urgency,
        "reasons":       reasons,
        "retrain_script": _RETRAIN_SCRIPTS.get(model_name, ""),
        "estimated_time": "5–15 minutes",
    }


def _prediction_count(model_name: str, fleet: list[dict]) -> dict:
    """
    Estimate live prediction counts from fleet data.
    Uses flags set by the existing model services during enrichment.
    """
    n = len(fleet)
    if model_name == "failure":
        ml_used = sum(1 for v in fleet if v.get("ml_model_used"))
        return {"total": n, "ml_predictions": ml_used, "formula_fallback": n - ml_used}
    if model_name == "health":
        ml_used = sum(1 for v in fleet if v.get("health_source") == "Health ML Model")
        return {"total": n, "ml_predictions": ml_used, "formula_fallback": n - ml_used}
    # rootcause, fleet, rul — all vehicles go through these models
    return {"total": n, "ml_predictions": n, "formula_fallback": 0}


# ── Public API ────────────────────────────────────────────────────────────────

def get_model_health(fleet: list[dict]) -> list[dict]:
    """
    Returns a health summary for every model family.
    `fleet` should be the enriched vehicle list from the fleet pipeline.
    """
    cards = get_all_models()
    summaries = []

    for card in cards:
        name   = card["name"]
        score  = card.get("score")
        health = _score_health(name, score)
        retrain = _retrain_recommendation(name, card)
        pred_counts = _prediction_count(name, fleet)

        summaries.append({
            "name":             name,
            "label":            card["label"],
            "task":             card["task"],
            "status":           card["status"],
            "health":           health,
            "version":          card["version"],
            "algorithm":        card["algorithm"],
            "score":            score,
            "cv_score":         card.get("cv_score"),
            "primary_metric":   card["primary_metric"],
            "deployed":         card["deployed"],
            "prediction_counts": pred_counts,
            "retrain_recommendation": retrain,
            "retrain_needed":   retrain is not None,
        })

    overall = _overall_health(summaries)
    return {"models": summaries, "overall": overall}


def _overall_health(summaries: list[dict]) -> dict:
    statuses = [s["health"] for s in summaries]
    if "critical" in statuses or "unknown" in statuses:
        level = "critical"
    elif "warning" in statuses:
        level = "warning"
    else:
        level = "healthy"

    deployed = sum(1 for s in summaries if s["deployed"])
    retrain_needed = sum(1 for s in summaries if s["retrain_needed"])

    return {
        "health":          level,
        "deployed_models": deployed,
        "total_models":    len(summaries),
        "retrain_needed":  retrain_needed,
    }
