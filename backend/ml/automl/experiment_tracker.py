"""
Experiment Tracker
==================
Records every training run permanently.

Outputs
-------
    reports/experiments.csv      ← one row per run, never deleted
    reports/EXP0001.json         ← full detail for each experiment
    reports/EXP0002.json
    ...

Experiment IDs
--------------
    EXP0001, EXP0002, … EXP9999
    Auto-incremented. Never reused.

Usage
-----
    tracker    = ExperimentTracker()
    experiment = tracker.create_experiment(
        model_name   = "failure",
        algorithm    = "Extra Trees",
        dataset      = "AI4I 2020",
        task         = "Classification",
    )
    tracker.log_parameters(experiment, {"n_estimators": 300, "max_depth": 20})
    tracker.log_metrics(experiment, {"accuracy": 99.95, "f1": 99.5})
    exp_id = tracker.save_experiment(experiment, training_time=12.4, version="v3")
"""

import os
import csv
import json
from datetime import datetime


_REPORT_DIR = "reports"
_CSV_PATH   = os.path.join(_REPORT_DIR, "experiments.csv")

_CSV_COLUMNS = [
    "experiment_id",
    "date",
    "model_name",
    "algorithm",
    "version",
    "task",
    "primary_metric",
    "primary_score",
    "cv_score",
    "accuracy",
    "precision",
    "recall",
    "f1",
    "roc_auc",
    "r2",
    "mae",
    "rmse",
    "mape",
    "training_time_sec",
    "dataset",
    "best_params",
]


class ExperimentTracker:
    """
    Laboratory notebook for the AutoML pipeline.
    One instance is enough for all models — experiments from all
    model families are written to the same experiments.csv.
    """

    def __init__(self):
        os.makedirs(_REPORT_DIR, exist_ok=True)
        self._ensure_csv_header()

    # ------------------------------------------------------------------
    # Step 1 — Create a blank experiment record
    # ------------------------------------------------------------------
    def create_experiment(
        self,
        model_name: str,
        algorithm:  str,
        dataset:    str,
        task:       str,           # "Classification" | "Regression"
    ) -> dict:
        """
        Return an experiment dict that acts as a mutable log container.
        Callers fill it in via log_parameters() and log_metrics(),
        then finalise it with save_experiment().
        """
        return {
            "experiment_id": self._next_id(),
            "date":          datetime.now().strftime("%Y-%m-%d %H:%M"),
            "model_name":    model_name,
            "algorithm":     algorithm,
            "dataset":       dataset,
            "task":          task,
            "version":       None,
            "parameters":    {},
            "metrics":       {},
            "cv_score":      None,
            "training_time": None,
            "feature_importance": {},
        }

    # ------------------------------------------------------------------
    # Step 2 — Log parameters
    # ------------------------------------------------------------------
    def log_parameters(self, experiment: dict, params: dict):
        """
        Attach hyperparameter values to an experiment.

        Example:
            tracker.log_parameters(exp, {"n_estimators": 300, "max_depth": 20})
        """
        experiment["parameters"].update(params)

    # ------------------------------------------------------------------
    # Step 3 — Log metrics
    # ------------------------------------------------------------------
    def log_metrics(self, experiment: dict, metrics: dict):
        """
        Attach evaluation scores to an experiment.

        Example:
            tracker.log_metrics(exp, {"accuracy": 99.95, "f1": 99.5,
                                       "precision": 100.0, "recall": 99.0})
        """
        experiment["metrics"].update(metrics)

    # ------------------------------------------------------------------
    # Step 4 — Save experiment (CSV row + JSON file)
    # ------------------------------------------------------------------
    def save_experiment(
        self,
        experiment:       dict,
        training_time:    float,
        version:          str,
        cv_score:         float | None = None,
        feature_importance: dict       = None,
    ) -> str:
        """
        Finalise and persist an experiment.

        Writes one row to experiments.csv and one EXP{N}.json file.

        Returns
        -------
        experiment_id string, e.g. "EXP0003"
        """
        experiment["training_time"] = round(training_time, 2)
        experiment["version"]       = version
        if cv_score is not None:
            experiment["cv_score"]  = cv_score
        if feature_importance:
            experiment["feature_importance"] = feature_importance

        exp_id = experiment["experiment_id"]
        m      = experiment["metrics"]

        # ── CSV row ───────────────────────────────────────────────────
        primary_metric, primary_score = self._primary(experiment)

        with open(_CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=_CSV_COLUMNS)
            writer.writerow({
                "experiment_id":    exp_id,
                "date":             experiment["date"],
                "model_name":       experiment["model_name"],
                "algorithm":        experiment["algorithm"],
                "version":          version,
                "task":             experiment["task"],
                "primary_metric":   primary_metric,
                "primary_score":    primary_score,
                "cv_score":         cv_score if cv_score is not None else "",
                "accuracy":         m.get("accuracy",  m.get("Accuracy",  "")),
                "precision":        m.get("precision", m.get("Precision", "")),
                "recall":           m.get("recall",    m.get("Recall",    "")),
                "f1":               m.get("f1",        m.get("F1",        "")),
                "roc_auc":          m.get("roc_auc",   m.get("ROC-AUC",   "")),
                "r2":               m.get("r2",        m.get("R²",        "")),
                "mae":              m.get("mae",       m.get("MAE",       "")),
                "rmse":             m.get("rmse",      m.get("RMSE",      "")),
                "mape":             m.get("mape",      m.get("MAPE",      "")),
                "training_time_sec": experiment["training_time"],
                "dataset":          experiment["dataset"],
                "best_params":      json.dumps(experiment["parameters"]),
            })

        # ── Individual JSON file ──────────────────────────────────────
        json_path = os.path.join(_REPORT_DIR, f"{exp_id}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(experiment, f, indent=2, default=str)

        print(f"  📊  {exp_id} logged  →  {_CSV_PATH}")
        print(f"  📄  {exp_id} detail  →  {json_path}")
        return exp_id

    # ------------------------------------------------------------------
    # Step 5 — Load history
    # ------------------------------------------------------------------
    def load_history(self) -> list[dict]:
        """
        Return all experiments from experiments.csv as a list of dicts.
        Returns [] if the file is empty or missing.
        """
        if not os.path.exists(_CSV_PATH) or os.path.getsize(_CSV_PATH) == 0:
            return []
        with open(_CSV_PATH, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def load_experiment_json(self, exp_id: str) -> dict | None:
        """Load the full JSON detail for a specific experiment ID."""
        path = os.path.join(_REPORT_DIR, f"{exp_id}.json")
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _next_id(self) -> str:
        """
        Scan experiments.csv for the highest existing EXP number
        and return the next one formatted as EXP0001 … EXP9999.
        """
        history = self.load_history()
        if not history:
            return "EXP0001"
        nums = []
        for row in history:
            eid = row.get("experiment_id", "")
            if eid.startswith("EXP"):
                try:
                    nums.append(int(eid[3:]))
                except ValueError:
                    pass
        next_num = max(nums) + 1 if nums else 1
        return f"EXP{next_num:04d}"

    def _ensure_csv_header(self):
        """Write the CSV header if the file is new or empty."""
        if not os.path.exists(_CSV_PATH) or os.path.getsize(_CSV_PATH) == 0:
            with open(_CSV_PATH, "w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=_CSV_COLUMNS).writeheader()

    @staticmethod
    def _primary(experiment: dict) -> tuple[str, float]:
        """Derive the primary metric name and value from stored metrics."""
        m = experiment["metrics"]
        if "f1" in m or "F1" in m:
            return "F1", m.get("f1", m.get("F1", 0))
        if "r2" in m or "R²" in m:
            return "R²", m.get("r2", m.get("R²", 0))
        return "score", 0
