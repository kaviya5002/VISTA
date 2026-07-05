"""
Hyperparameter Search
=====================
Finds the best hyperparameter configuration for each algorithm using
RandomizedSearchCV.  This file has one responsibility only:
    Given X_train, y_train  →  return the best fitted estimator.

It never trains the full pipeline, never saves models, never evaluates
on a test set.  Those are the responsibilities of base_trainer.py,
model_registry.py, and experiment_tracker.py respectively.

Why RandomizedSearch over GridSearch
--------------------------------------
GridSearch on Random Forest alone:
    4 trees × 5 depths × 3 splits × 3 leaves × 2 bootstrap × 2 features
    = 720 combinations × 5 CV folds = 3 600 fits.

RandomizedSearch with n_iter=25:
    25 combinations × 5 CV folds = 125 fits.
    Empirically reaches ≥ 95 % of GridSearch quality at ~3 % of the time.

Scoring
-------
Classification  →  f1_weighted   (not accuracy — dataset is imbalanced)
Regression      →  r2
"""

import time
import warnings
from math import prod
from sklearn.model_selection import RandomizedSearchCV

warnings.filterwarnings("ignore")

_CV    = 5
_JOBS  = -1


def _safe_n_iter(param_dist: dict, requested: int) -> int:
    """
    Cap n_iter at the total number of unique grid combinations so
    RandomizedSearchCV never wastes time sampling duplicates.
    """
    total = prod(len(v) for v in param_dist.values())
    return min(requested, total)


def _run_search(estimator, param_dist: dict, X_train, y_train,
                scoring: str, n_iter: int) -> RandomizedSearchCV:
    """Build, fit, and return a RandomizedSearchCV object."""
    search = RandomizedSearchCV(
        estimator           = estimator,
        param_distributions = param_dist,
        n_iter              = n_iter,
        scoring             = scoring,
        cv                  = _CV,
        refit               = True,
        n_jobs              = _JOBS,
        random_state        = 42,
        verbose             = 0,
    )
    search.fit(X_train, y_train)
    return search


class HyperParameterSearch:
    """
    One public method per algorithm family.
    Every method follows the same contract:

        Input  : X_train, y_train
        Output : best fitted sklearn estimator  (search.best_estimator_)

    The caller (base_trainer) is responsible for:
        - Evaluating the returned model on a held-out test set
        - Saving the model through the registry
        - Logging the experiment
    """

    # ------------------------------------------------------------------ #
    # ── Classification                                                   #
    # ------------------------------------------------------------------ #
    def optimize_random_forest(self, X_train, y_train):
        """
        Search over trees / depth / split / leaf / bootstrap.
        Uses f1_weighted scoring to handle class imbalance.
        Returns: best fitted RandomForestClassifier
        """
        from sklearn.ensemble import RandomForestClassifier

        param_dist = {
            "n_estimators":      [100, 200, 300, 500],
            "max_depth":         [10, 20, 30, 40, None],
            "min_samples_split": [2, 5, 10],
            "min_samples_leaf":  [1, 2, 4],
            "bootstrap":         [True, False],
            "max_features":      ["sqrt", "log2"],
            "class_weight":      ["balanced"],
        }
        n_iter = _safe_n_iter(param_dist, 25)

        search = RandomizedSearchCV(
            estimator          = RandomForestClassifier(random_state=42, n_jobs=_JOBS),
            param_distributions= param_dist,
            n_iter             = n_iter,
            scoring            = "f1_weighted",
            cv                 = _CV,
            refit              = True,
            n_jobs             = _JOBS,
            random_state       = 42,
            verbose            = 0,
        )
        search.fit(X_train, y_train)
        self._report("Random Forest", search)
        return search.best_estimator_

    def optimize_extra_trees(self, X_train, y_train):
        """
        Search over trees / depth / split / leaf / bootstrap.
        Returns: best fitted ExtraTreesClassifier
        """
        from sklearn.ensemble import ExtraTreesClassifier

        param_dist = {
            "n_estimators":      [100, 200, 300, 500],
            "max_depth":         [10, 20, 30, 40, None],
            "min_samples_split": [2, 5, 10],
            "min_samples_leaf":  [1, 2, 4],
            "bootstrap":         [True, False],
            "max_features":      ["sqrt", "log2"],
            "class_weight":      ["balanced"],
        }
        n_iter = _safe_n_iter(param_dist, 25)

        search = RandomizedSearchCV(
            estimator          = ExtraTreesClassifier(random_state=42, n_jobs=_JOBS),
            param_distributions= param_dist,
            n_iter             = n_iter,
            scoring            = "f1_weighted",
            cv                 = _CV,
            refit              = True,
            n_jobs             = _JOBS,
            random_state       = 42,
            verbose            = 0,
        )
        search.fit(X_train, y_train)
        self._report("Extra Trees", search)
        return search.best_estimator_

    def optimize_gradient_boosting(self, X_train, y_train):
        """
        Search over estimators / depth / learning rate / subsample.
        Returns: best fitted GradientBoostingClassifier
        """
        from sklearn.ensemble import GradientBoostingClassifier

        param_dist = {
            "n_estimators":      [100, 200, 300],
            "max_depth":         [3, 5, 7],
            "learning_rate":     [0.01, 0.05, 0.10, 0.20],
            "subsample":         [0.7, 0.8, 0.9, 1.0],
            "min_samples_split": [2, 5],
        }
        n_iter = _safe_n_iter(param_dist, 25)

        search = RandomizedSearchCV(
            estimator          = GradientBoostingClassifier(random_state=42),
            param_distributions= param_dist,
            n_iter             = n_iter,
            scoring            = "f1_weighted",
            cv                 = _CV,
            refit              = True,
            n_jobs             = _JOBS,
            random_state       = 42,
            verbose            = 0,
        )
        search.fit(X_train, y_train)
        self._report("Gradient Boosting", search)
        return search.best_estimator_

    def optimize_adaboost(self, X_train, y_train):
        """
        Search over estimators / learning rate.
        Returns: best fitted AdaBoostClassifier
        """
        from sklearn.ensemble import AdaBoostClassifier

        param_dist = {
            "n_estimators":  [50, 100, 200, 300],
            "learning_rate": [0.01, 0.05, 0.1, 0.5, 1.0],
        }
        # AdaBoost only has 4×5=20 unique combinations — cap accordingly
        n_iter = _safe_n_iter(param_dist, 20)

        search = RandomizedSearchCV(
            estimator          = AdaBoostClassifier(random_state=42),
            param_distributions= param_dist,
            n_iter             = n_iter,
            scoring            = "f1_weighted",
            cv                 = _CV,
            refit              = True,
            n_jobs             = _JOBS,
            random_state       = 42,
            verbose            = 0,
        )
        search.fit(X_train, y_train)
        self._report("AdaBoost", search)
        return search.best_estimator_

    # ------------------------------------------------------------------ #
    # ── Regression variants (same grids, scoring=r2)                    #
    # ------------------------------------------------------------------ #
    def optimize_random_forest_reg(self, X_train, y_train):
        """Returns: best fitted RandomForestRegressor"""
        from sklearn.ensemble import RandomForestRegressor

        param_dist = {
            "n_estimators":      [100, 200, 300, 500],
            "max_depth":         [10, 20, 30, 40, None],
            "min_samples_split": [2, 5, 10],
            "min_samples_leaf":  [1, 2, 4],
            "bootstrap":         [True, False],
            "max_features":      ["sqrt", "log2"],
        }
        n_iter = _safe_n_iter(param_dist, 25)

        search = RandomizedSearchCV(
            estimator          = RandomForestRegressor(random_state=42, n_jobs=_JOBS),
            param_distributions= param_dist,
            n_iter             = n_iter,
            scoring            = "r2",
            cv                 = _CV,
            refit              = True,
            n_jobs             = _JOBS,
            random_state       = 42,
            verbose            = 0,
        )
        search.fit(X_train, y_train)
        self._report("Random Forest", search)
        return search.best_estimator_

    def optimize_extra_trees_reg(self, X_train, y_train):
        """Returns: best fitted ExtraTreesRegressor"""
        from sklearn.ensemble import ExtraTreesRegressor

        param_dist = {
            "n_estimators":      [100, 200, 300, 500],
            "max_depth":         [10, 20, 30, 40, None],
            "min_samples_split": [2, 5, 10],
            "min_samples_leaf":  [1, 2, 4],
            "bootstrap":         [True, False],
            "max_features":      ["sqrt", "log2"],
        }
        n_iter = _safe_n_iter(param_dist, 25)

        search = RandomizedSearchCV(
            estimator          = ExtraTreesRegressor(random_state=42, n_jobs=_JOBS),
            param_distributions= param_dist,
            n_iter             = n_iter,
            scoring            = "r2",
            cv                 = _CV,
            refit              = True,
            n_jobs             = _JOBS,
            random_state       = 42,
            verbose            = 0,
        )
        search.fit(X_train, y_train)
        self._report("Extra Trees", search)
        return search.best_estimator_

    def optimize_gradient_boosting_reg(self, X_train, y_train):
        """Returns: best fitted GradientBoostingRegressor"""
        from sklearn.ensemble import GradientBoostingRegressor

        param_dist = {
            "n_estimators":      [100, 200, 300],
            "max_depth":         [3, 5, 7],
            "learning_rate":     [0.01, 0.05, 0.10, 0.20],
            "subsample":         [0.7, 0.8, 0.9, 1.0],
            "min_samples_split": [2, 5],
        }
        n_iter = _safe_n_iter(param_dist, 25)

        search = RandomizedSearchCV(
            estimator          = GradientBoostingRegressor(random_state=42),
            param_distributions= param_dist,
            n_iter             = n_iter,
            scoring            = "r2",
            cv                 = _CV,
            refit              = True,
            n_jobs             = _JOBS,
            random_state       = 42,
            verbose            = 0,
        )
        search.fit(X_train, y_train)
        self._report("Gradient Boosting", search)
        return search.best_estimator_

    def optimize_adaboost_reg(self, X_train, y_train):
        """Returns: best fitted AdaBoostRegressor"""
        from sklearn.ensemble import AdaBoostRegressor

        param_dist = {
            "n_estimators":  [50, 100, 200, 300],
            "learning_rate": [0.01, 0.05, 0.1, 0.5, 1.0],
        }
        n_iter = _safe_n_iter(param_dist, 20)

        search = RandomizedSearchCV(
            estimator          = AdaBoostRegressor(random_state=42),
            param_distributions= param_dist,
            n_iter             = n_iter,
            scoring            = "r2",
            cv                 = _CV,
            refit              = True,
            n_jobs             = _JOBS,
            random_state       = 42,
            verbose            = 0,
        )
        search.fit(X_train, y_train)
        self._report("AdaBoost", search)
        return search.best_estimator_

    # ------------------------------------------------------------------ #
    # ── Internal helper                                                  #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _report(name: str, search: RandomizedSearchCV):
        """Print best CV score and winning parameters."""
        score = round(search.best_score_ * 100, 3)
        print(f"    ✓ {name:22s}  best CV score: {score}%")
        print(f"      params: {search.best_params_}")
