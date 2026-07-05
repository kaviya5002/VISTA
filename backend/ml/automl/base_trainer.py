"""
AutoML Base Trainer
===================
Class-based engine that runs the full enterprise ML pipeline:

    Dataset → Preprocess → CV → Hyperparameter Search
    → Train → Evaluate → Compare → Version → Track → Deploy

Usage
-----
Classification:
    trainer = AutoMLTrainer(
        X, y,
        model_name="failure",
        task="classification",
        feature_names=X.columns.tolist(),
        dataset_name="AI4I",
    )
    trainer.run()

Regression:
    trainer = AutoMLTrainer(
        X, y,
        model_name="health",
        task="regression",
        feature_names=X.columns.tolist(),
        dataset_name="AI4I",
    )
    trainer.run()

Output files (relative to cwd, run scripts from backend/ml/):
    models/{model_name}/v{N}.pkl
    models/{model_name}/best.pkl
    models/{model_name}/metadata.json
    reports/{model_name}_model_comparison.csv
    reports/{model_name}_feature_importance.png
    reports/experiments.csv
"""

import os
import json
import time
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
    r2_score, mean_absolute_error, mean_squared_error,
)

from hyperparameter_search import HyperParameterSearch
from model_registry       import ModelRegistry
from experiment_tracker   import ExperimentTracker

warnings.filterwarnings("ignore")


class AutoMLTrainer:
    """
    Full AutoML pipeline in a single class.

    Parameters
    ----------
    X            : feature DataFrame or array
    y            : target Series or array
    model_name   : "failure" | "health" | "rootcause" | "fleet" | "rul"
    task         : "classification" | "regression"
    feature_names: list of feature column names (for importance plot)
    dataset_name : human-readable dataset label logged to experiments.csv
    test_size    : fraction held out for final evaluation (default 0.2)
    cv_folds     : number of cross-validation folds (default 5)
    """

    def __init__(
        self,
        X,
        y,
        model_name:    str,
        task:          str,
        feature_names: list,
        dataset_name:  str  = "Unknown",
        test_size:     float = 0.2,
        cv_folds:      int   = 5,
    ):
        self.X             = X
        self.y             = y
        self.model_name    = model_name
        self.task          = task.lower()
        self.feature_names = feature_names
        self.dataset_name  = dataset_name
        self.test_size     = test_size
        self.cv_folds      = cv_folds

        # ── State (populated during run) ────────────────────────────────────
        self.X_train = self.X_test = self.y_train = self.y_test = None
        self.models:     dict  = {}   # {name: (estimator, params, cv_score)}
        self.results:    list  = []   # list of metric dicts
        self.best_model        = None
        self.best_score: float = -1.0
        self.best_name:  str   = ""
        self.best_params: dict = {}

    # ────────────────────────────────────────────────────────────────────────
    # Step 1 — Split
    # ────────────────────────────────────────────────────────────────────────
    def split_data(self):
        """Stratified train/test split for classification; plain for regression."""
        stratify = self.y if self.task == "classification" else None
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            self.X, self.y,
            test_size=self.test_size,
            random_state=42,
            stratify=stratify,
        )
        print(f"  Train: {len(self.X_train)}  Test: {len(self.X_test)}")

    # ────────────────────────────────────────────────────────────────────────
    # Step 2 — Hyperparameter-optimised training
    # ────────────────────────────────────────────────────────────────────────
    def train_models(self):
        """
        Instantiate HyperParameterSearch and call one method per algorithm.
        Each method runs RandomizedSearchCV internally and returns only the
        best fitted estimator — saving, evaluating, and logging happen later.
        self.models shape: {name: (estimator, best_params_dict, cv_score_placeholder)}
        """
        print(f"\n  Running hyperparameter search ({self.cv_folds}-fold CV)…")
        optimizer = HyperParameterSearch()
        self.models = {}

        if self.task == "classification":
            pairs = [
                ("Random Forest",     optimizer.optimize_random_forest),
                ("Extra Trees",       optimizer.optimize_extra_trees),
                ("Gradient Boosting", optimizer.optimize_gradient_boosting),
                ("AdaBoost",          optimizer.optimize_adaboost),
            ]
        else:
            pairs = [
                ("Random Forest",     optimizer.optimize_random_forest_reg),
                ("Extra Trees",       optimizer.optimize_extra_trees_reg),
                ("Gradient Boosting", optimizer.optimize_gradient_boosting_reg),
                ("AdaBoost",          optimizer.optimize_adaboost_reg),
            ]

        for name, method in pairs:
            print(f"\n  [{name}] Searching…")
            try:
                best_estimator = method(self.X_train, self.y_train)
                # Extract the winning params from the fitted estimator itself
                best_params = {
                    k: v for k, v in best_estimator.get_params().items()
                    if k in [
                        "n_estimators", "max_depth", "min_samples_split",
                        "min_samples_leaf", "bootstrap", "max_features",
                        "learning_rate", "subsample",
                    ]
                }
                # Placeholder cv_score=0 — actual final CV runs after select_best_model()
                self.models[name] = (best_estimator, best_params, 0)
            except Exception as exc:
                print(f"  [{name}] FAILED — {exc}")

    # ────────────────────────────────────────────────────────────────────────
    # Step 3 — Evaluate on held-out test set
    # ────────────────────────────────────────────────────────────────────────
    def evaluate_models(self):
        """
        Score every trained model on the hold-out test set.
        Populates self.results with one dict per model.
        """
        self.results = []
        n_classes = len(np.unique(self.y_train))
        multi     = n_classes > 2
        avg       = "weighted" if multi else "binary"

        for name, (model, params, _cv_score) in self.models.items():
            try:
                t0   = time.time()
                pred = model.predict(self.X_test)
                elapsed = round(time.time() - t0, 3)

                if self.task == "classification":
                    proba = model.predict_proba(self.X_test) \
                        if hasattr(model, "predict_proba") else None

                    acc  = round(accuracy_score(self.y_test, pred) * 100, 2)
                    prec = round(precision_score(self.y_test, pred,
                                                 average=avg, zero_division=0) * 100, 2)
                    rec  = round(recall_score(self.y_test, pred,
                                              average=avg, zero_division=0) * 100, 2)
                    f1   = round(f1_score(self.y_test, pred,
                                          average=avg, zero_division=0) * 100, 2)
                    auc  = None
                    if proba is not None:
                        try:
                            if multi:
                                auc = round(roc_auc_score(
                                    self.y_test, proba,
                                    multi_class="ovr", average="weighted") * 100, 2)
                            else:
                                auc = round(roc_auc_score(
                                    self.y_test, proba[:, 1]) * 100, 2)
                        except Exception:
                            pass

                    row = {
                        "Model":            name,
                        "Accuracy":         acc,
                        "Precision":        prec,
                        "Recall":           rec,
                        "F1":               f1,
                        "ROC-AUC":          auc if auc else "N/A",
                        "_primary":         f1,
                        "_primary_label":   "F1",
                        "_params":          params,
                        "_model":           model,
                        "_time":            elapsed,
                    }

                else:  # regression
                    r2   = round(r2_score(self.y_test, pred), 4)
                    mae  = round(mean_absolute_error(self.y_test, pred), 3)
                    rmse = round(np.sqrt(mean_squared_error(self.y_test, pred)), 3)
                    nonzero = np.asarray(self.y_test) != 0
                    mape = round(
                        np.mean(np.abs(
                            (np.asarray(self.y_test)[nonzero] - pred[nonzero])
                            / np.asarray(self.y_test)[nonzero]
                        )) * 100, 2
                    ) if nonzero.any() else None

                    row = {
                        "Model":          name,
                        "R²":             r2,
                        "MAE":            mae,
                        "RMSE":           rmse,
                        "MAPE":           mape if mape else "N/A",
                        "_primary":       r2,
                        "_primary_label": "R²",
                        "_params":        params,
                        "_model":         model,
                        "_time":          elapsed,
                    }

                self.results.append(row)

            except Exception as exc:
                print(f"  Evaluation failed for {name}: {exc}")

    # ────────────────────────────────────────────────────────────────────────
    # Step 4 — Cross-validation score for the best candidate
    # ────────────────────────────────────────────────────────────────────────
    def _cross_validate(self, model) -> float:
        """Run CV on the full dataset using the best model's fitted params."""
        scoring = "f1_weighted" if self.task == "classification" else "r2"
        cv_scores = cross_val_score(
            model, self.X, self.y,
            cv=self.cv_folds, scoring=scoring, n_jobs=-1,
        )
        return round(float(cv_scores.mean()) * 100, 3)

    # ────────────────────────────────────────────────────────────────────────
    # Step 5 — Select winner
    # ────────────────────────────────────────────────────────────────────────
    def select_best_model(self):
        """Pick the model with the highest primary score."""
        if not self.results:
            raise RuntimeError("No results — run evaluate_models() first.")

        best_row = max(self.results, key=lambda r: r["_primary"])
        self.best_model  = best_row["_model"]
        self.best_score  = best_row["_primary"]
        self.best_name   = best_row["Model"]
        self.best_params = best_row["_params"]

        print(f"\n  ✅  Winner: {self.best_name}  "
              f"({best_row['_primary_label']} = {self.best_score})")

    # ────────────────────────────────────────────────────────────────────────
    # Step 6 — Experiment tracking → Registry (correct order)
    # ────────────────────────────────────────────────────────────────────────
    def _track_and_save(self, cv_score: float, total_time: float) -> tuple[str, str]:
        """
        1. Log the experiment (tracker assigns EXP id)
        2. Save versioned model in registry (version id linked to EXP id)

        Returns (experiment_id, version_str)
        """
        task_label = "Classification" if self.task == "classification" else "Regression"

        # ── Step A: Experiment Tracker ────────────────────────────────
        tracker    = ExperimentTracker()
        experiment = tracker.create_experiment(
            model_name = self.model_name,
            algorithm  = self.best_name,
            dataset    = self.dataset_name,
            task       = task_label,
        )
        tracker.log_parameters(experiment, self.best_params)

        # Build metrics dict from the best result row
        best_row = next(r for r in self.results if r["Model"] == self.best_name)
        metrics  = {k.lower().replace("-", "_"): v
                    for k, v in best_row.items()
                    if not k.startswith("_") and k != "Model"}
        tracker.log_metrics(experiment, metrics)

        # Feature importance
        feat_imp = {}
        if hasattr(self.best_model, "feature_importances_"):
            feat_imp = dict(zip(
                self.feature_names,
                [round(float(x), 4)
                 for x in self.best_model.feature_importances_]
            ))

        exp_id = tracker.save_experiment(
            experiment,
            training_time = total_time,
            version       = "pending",   # filled in after registry assigns version
            cv_score      = cv_score,
            feature_importance = feat_imp,
        )

        # ── Step B: Model Registry ────────────────────────────────────
        primary_label = "F1" if self.task == "classification" else "R²"
        reg_meta = {
            "algorithm":        self.best_name,
            "score":            self.best_score,
            primary_label:      self.best_score,
            "cv_score":         cv_score,
            "dataset":          self.dataset_name,
            "params":           self.best_params,
            "training_time_sec": total_time,
        }
        for row in self.results:
            if row["Model"] == self.best_name:
                if self.task == "classification":
                    reg_meta.update({
                        "accuracy":  row.get("Accuracy"),
                        "precision": row.get("Precision"),
                        "recall":    row.get("Recall"),
                    })
                else:
                    reg_meta.update({
                        "MAE":  row.get("MAE"),
                        "RMSE": row.get("RMSE"),
                    })

        registry = ModelRegistry(self.model_name)
        version  = registry.save_new_version(
            self.best_model, reg_meta, experiment_id=exp_id
        )

        # Patch the JSON to replace "pending" with the real version
        json_record = tracker.load_experiment_json(exp_id)
        if json_record:
            json_record["version"] = version
            json_path = os.path.join("reports", f"{exp_id}.json")
            with open(json_path, "w") as f:
                json.dump(json_record, f, indent=2, default=str)

        return exp_id, version

    # ────────────────────────────────────────────────────────────────────────
    # Step 7 — Comparison report + feature importance chart
    # ────────────────────────────────────────────────────────────────────────
    def generate_report(self):
        """Save model comparison CSV and feature importance chart."""
        os.makedirs("reports", exist_ok=True)

        # Strip private keys before writing
        public_cols = [k for k in self.results[0].keys() if not k.startswith("_")]
        df = pd.DataFrame([
            {k: r[k] for k in public_cols} for r in self.results
        ])
        sort_col = "F1" if "F1" in df.columns else "R²"
        df = df.sort_values(sort_col, ascending=False)

        path = f"reports/{self.model_name}_model_comparison.csv"
        df.to_csv(path, index=False)

        print(f"\n{'─'*64}")
        print(df.to_string(index=False))
        print(f"{'─'*64}")
        print(f"  Comparison report → {path}")

        # Feature importance
        if hasattr(self.best_model, "feature_importances_"):
            imp = pd.Series(
                self.best_model.feature_importances_,
                index=self.feature_names
            ).sort_values(ascending=False)

            plt.figure(figsize=(10, 5))
            imp.plot(kind="bar", color="steelblue")
            plt.title(f"Feature Importance — {self.model_name} ({self.best_name})")
            plt.tight_layout()
            img_path = f"reports/{self.model_name}_feature_importance.png"
            plt.savefig(img_path)
            plt.close()
            print(f"  Feature importance → {img_path}")

    # ────────────────────────────────────────────────────────────────────────
    # Main entry point
    # ────────────────────────────────────────────────────────────────────────
    def run(self):
        """Execute the full pipeline end-to-end."""
        bar = "=" * 64
        task_label = "Classification" if self.task == "classification" else "Regression"
        print(f"\n{bar}")
        print(f"  AutoML  |  {self.model_name.upper()}  |  {task_label}")
        print(f"{bar}")

        total_start = time.time()

        self.split_data()
        self.train_models()
        self.evaluate_models()
        self.select_best_model()

        # Cross-validate the winner on the full dataset
        print(f"\n  Cross-validating winner ({self.cv_folds}-fold)…", end=" ", flush=True)
        cv_score = self._cross_validate(self.best_model)
        print(f"CV score = {cv_score}%")

        total_time = round(time.time() - total_start, 2)

        self.generate_report()

        # Experiment Tracker → Model Registry  (correct order)
        exp_id, version = self._track_and_save(cv_score, total_time)

        print(f"\n  Experiment : {exp_id}")
        print(f"  Version    : {version}")
        print(f"  Total time : {total_time}s")
        print(f"  All versions: {ModelRegistry(self.model_name).list_versions()}")
        print(bar)

        return self.best_model
