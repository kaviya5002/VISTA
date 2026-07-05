"""
Model Registry
==============
Versioned model storage under models/{model_name}/.

Directory layout (example after three training runs for "failure"):

    models/
      failure/
        v1.pkl          ← each training run adds one versioned file
        v1.json         ← metadata for that specific version
        v2.pkl
        v2.json
        v3.pkl
        v3.json
        best.pkl        ← copy of the highest-scoring version
        metadata.json   ← registry index: current_best, latest_version, total

Usage
-----
    registry = ModelRegistry("failure")
    version  = registry.save_new_version(model, metadata)   # → "v3"
    best     = registry.load_best_model()
    registry.rollback_version("v2")
    history  = registry.list_versions()
"""

import os
import json
import shutil
import joblib
from datetime import date


class ModelRegistry:
    """
    One instance per model family.

    Parameters
    ----------
    model_name : "failure" | "health" | "rootcause" | "fleet" | "rul"
    base_dir   : root directory that contains the model sub-folders
                 (default "models" — relative to the script's cwd)
    """

    def __init__(self, model_name: str, base_dir: str = "models"):
        self.model_name = model_name
        self.model_dir  = os.path.join(base_dir, model_name)
        self.create_model_folder()

    # ------------------------------------------------------------------
    # Step 1 — Folder management
    # ------------------------------------------------------------------
    def create_model_folder(self):
        """Create the model sub-directory if it does not already exist."""
        os.makedirs(self.model_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Step 2 — Version resolution
    # ------------------------------------------------------------------
    def get_latest_version(self) -> str | None:
        """
        Return the highest existing version string (e.g. "v7"),
        or None if no versions have been saved yet.
        """
        nums = self._existing_version_numbers()
        return f"v{max(nums)}" if nums else None

    def _next_version(self) -> str:
        nums = self._existing_version_numbers()
        return f"v{max(nums) + 1}" if nums else "v1"

    def _existing_version_numbers(self) -> list[int]:
        nums = []
        for f in os.listdir(self.model_dir):
            if f.startswith("v") and f.endswith(".pkl"):
                try:
                    nums.append(int(f[1:-4]))
                except ValueError:
                    pass
        return nums

    # ------------------------------------------------------------------
    # Step 3 — Save a new version
    # ------------------------------------------------------------------
    def save_new_version(self, model, metadata: dict,
                         experiment_id: str = "") -> str:
        """
        Persist a trained model as the next version.

        Writes:
            models/{name}/v{N}.pkl   — the fitted estimator
            models/{name}/v{N}.json  — version-level metadata
            models/{name}/best.pkl   — updated if this version is best
            models/{name}/metadata.json — registry index updated

        Parameters
        ----------
        model         : fitted scikit-learn estimator
        metadata      : dict with at least {"algorithm": str, "score": float}
                        "score" is F1 (classification) or R² (regression)
        experiment_id : EXP-formatted ID from experiment_tracker

        Returns
        -------
        version string, e.g. "v3"
        """
        version = self._next_version()

        # ── Save versioned model ──────────────────────────────────────
        pkl_path = self._pkl_path(version)
        joblib.dump(model, pkl_path)

        # ── Save per-version metadata JSON ────────────────────────────
        version_meta = {
            "version":       version,
            "algorithm":     metadata.get("algorithm", "unknown"),
            "score":         metadata.get("score", 0),
            "cv_score":      metadata.get("cv_score"),
            "dataset":       metadata.get("dataset", ""),
            "training_time": metadata.get("training_time_sec"),
            "experiment_id": experiment_id,
            "params":        metadata.get("params", {}),
            "metrics":       {k: v for k, v in metadata.items()
                              if k not in {"algorithm", "score", "cv_score",
                                           "dataset", "training_time_sec",
                                           "params", "model_name", "trained_on"}},
            "created":       str(date.today()),
        }
        self._write_json(self._json_path(version), version_meta)

        # ── Update best.pkl if this version outperforms current best ──
        current_score = self._current_best_score()
        if version_meta["score"] >= current_score:
            self.update_best_model(version)
        else:
            print(f"  📦  {self.model_name} {version} archived "
                  f"(score={version_meta['score']:.4f} < "
                  f"current best {current_score:.4f})")

        # ── Update registry-level metadata.json ──────────────────────
        self._update_registry_index()

        print(f"  💾  {self.model_name} {version} saved → {pkl_path}")
        return version

    # ------------------------------------------------------------------
    # Step 4 — Promote a version to best
    # ------------------------------------------------------------------
    def update_best_model(self, version: str):
        """
        Copy {version}.pkl to best.pkl and record in metadata.json.
        Called automatically by save_new_version, but also usable
        directly for rollback.
        """
        src = self._pkl_path(version)
        dst = self._best_path()
        if not os.path.exists(src):
            raise FileNotFoundError(f"Version {version} not found: {src}")
        shutil.copy2(src, dst)
        print(f"  ✅  {self.model_name} best → {version}  ({dst})")

    # ------------------------------------------------------------------
    # Step 5 — Metadata I/O
    # ------------------------------------------------------------------
    def save_metadata(self, data: dict):
        """Write (overwrite) the registry-level metadata.json."""
        self._write_json(self._meta_path(), data)

    def load_metadata(self) -> dict:
        """
        Return the registry-level metadata.json.
        Returns a safe default dict if the file does not exist yet.
        """
        path = self._meta_path()
        if not os.path.exists(path):
            return {
                "current_best":    None,
                "latest_version":  None,
                "total_models":    0,
                "last_updated":    None,
            }
        return self._read_json(path)

    def load_version_metadata(self, version: str) -> dict | None:
        """Return the per-version JSON for a specific version, or None."""
        path = self._json_path(version)
        return self._read_json(path) if os.path.exists(path) else None

    # ------------------------------------------------------------------
    # Step 6 — List versions
    # ------------------------------------------------------------------
    def list_versions(self) -> list[str]:
        """Return all version strings sorted oldest → newest."""
        nums = sorted(self._existing_version_numbers())
        return [f"v{n}" for n in nums]

    def list_versions_with_scores(self) -> list[dict]:
        """
        Return a list of dicts with version + score for every saved model.
        Useful for the /models/history/{name} API endpoint.

        Example:
            [{"version": "v1", "score": 98.8, "algorithm": "Random Forest"},
             {"version": "v2", "score": 99.95, "algorithm": "Extra Trees"}]
        """
        result = []
        for v in self.list_versions():
            vm = self.load_version_metadata(v) or {}
            result.append({
                "version":       v,
                "algorithm":     vm.get("algorithm"),
                "score":         vm.get("score"),
                "cv_score":      vm.get("cv_score"),
                "experiment_id": vm.get("experiment_id"),
                "created":       vm.get("created"),
            })
        return result

    # ------------------------------------------------------------------
    # Step 7 — Load
    # ------------------------------------------------------------------
    def load_best_model(self):
        """Load and return best.pkl. Returns None if not available."""
        path = self._best_path()
        return joblib.load(path) if os.path.exists(path) else None

    def load_version(self, version: str):
        """Load a specific version by name, e.g. load_version('v2')."""
        path = self._pkl_path(version)
        if not os.path.exists(path):
            raise FileNotFoundError(f"{self.model_name} {version} not found")
        return joblib.load(path)

    # ------------------------------------------------------------------
    # Step 8 — Rollback
    # ------------------------------------------------------------------
    def rollback_version(self, version: str):
        """
        Restore a previous version as best.pkl without retraining.

        Example use-case:
            v7 scored 99.95%  →  v8 scores 98.10%  →  rollback to v7

        Updates best.pkl and metadata.json to reflect the rollback.
        """
        meta = self.load_version_metadata(version)
        if meta is None:
            raise ValueError(f"No metadata found for {self.model_name} {version}. "
                             f"Available: {self.list_versions()}")

        self.update_best_model(version)

        # Patch the registry index to record the rollback
        index = self.load_metadata()
        index["current_best"] = version
        index["last_updated"] = str(date.today())
        self.save_metadata(index)

        print(f"  ↩️   {self.model_name} rolled back to {version} "
              f"(score={meta.get('score')})")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _pkl_path(self, version: str) -> str:
        return os.path.join(self.model_dir, f"{version}.pkl")

    def _json_path(self, version: str) -> str:
        return os.path.join(self.model_dir, f"{version}.json")

    def _best_path(self) -> str:
        return os.path.join(self.model_dir, "best.pkl")

    def _meta_path(self) -> str:
        return os.path.join(self.model_dir, "metadata.json")

    def _current_best_score(self) -> float:
        """Read the score of the current best version from metadata.json."""
        index = self.load_metadata()
        best_v = index.get("current_best")
        if not best_v:
            return -1.0
        vm = self.load_version_metadata(best_v)
        return float(vm.get("score", -1)) if vm else -1.0

    def _update_registry_index(self):
        """Rebuild and persist the registry-level metadata.json."""
        versions = self.list_versions()
        # current_best = version with highest score
        best_v     = None
        best_score = -1.0
        for v in versions:
            vm = self.load_version_metadata(v) or {}
            s  = float(vm.get("score", -1))
            if s > best_score:
                best_score = s
                best_v     = v

        index = {
            "current_best":   best_v,
            "latest_version": versions[-1] if versions else None,
            "total_models":   len(versions),
            "last_updated":   str(date.today()),
        }
        self.save_metadata(index)

    @staticmethod
    def _write_json(path: str, data: dict):
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    @staticmethod
    def _read_json(path: str) -> dict:
        with open(path) as f:
            return json.load(f)
