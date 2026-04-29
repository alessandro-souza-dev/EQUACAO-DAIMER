from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("LOKY_MAX_CPU_COUNT", str(os.cpu_count() or 1))

import joblib
import numpy as np
from sklearn.base import clone
from sklearn.ensemble import ExtraTreesRegressor, GradientBoostingRegressor, RandomForestRegressor, StackingRegressor
from sklearn.kernel_ridge import KernelRidge
from sklearn.linear_model import RidgeCV
from sklearn.metrics import accuracy_score, mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

from daimer_ml import (
    DaimerFeatureTransformer,
    FEATURE_COLUMNS,
    TARGET_D10,
    TARGET_D20,
    TARGET_GEI,
    TARGET_GLOBAL,
    load_daimer_dataframe,
    make_input_frame,
    predict_from_bundle,
)


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "Dados_Ensaios.xlsx"
OUTPUT_DIR = Path.home() / "daimer_modelos_ml"
BUNDLE_FILE = OUTPUT_DIR / "daimer_ml_bundle.joblib"
METRICS_FILE = OUTPUT_DIR / "metricas_ml.json"


ANCHOR_CASES = [
    {
        "name": "pdf_case",
        "inputs": [3.49, 0.74, 0.57, 8060.0, 0.361, 0.161, 1.468, 3.582],
        "targets": {"d10": 1.46, "d20": 2.04, "avaliacao_global": 3.50, "gei": 10},
    },
    {
        "name": "known_case_2",
        "inputs": [2.29, 1.31, 0.57, 21850.0, 1.152, 0.083, 2.45, 0.01],
        "targets": {"d10": 0.70, "d20": 2.37, "avaliacao_global": 3.07, "gei": 11},
    },
]


def make_pipeline(regressor: Any, scale: bool = False) -> Pipeline:
    steps: list[tuple[str, Any]] = [("features", DaimerFeatureTransformer())]
    if scale:
        steps.append(("scale", StandardScaler()))
    steps.append(("regressor", regressor))
    return Pipeline(steps)


def candidate_models(random_state: int = 42) -> dict[str, Pipeline]:
    extra_trees = ExtraTreesRegressor(
        n_estimators=1400,
        random_state=random_state,
        min_samples_leaf=1,
        max_features=1.0,
        bootstrap=False,
        n_jobs=-1,
    )
    random_forest = RandomForestRegressor(
        n_estimators=1000,
        random_state=random_state,
        min_samples_leaf=1,
        max_features=1.0,
        bootstrap=True,
        n_jobs=-1,
    )
    gradient_boosting = GradientBoostingRegressor(
        random_state=random_state,
        n_estimators=900,
        learning_rate=0.025,
        max_depth=3,
        subsample=0.9,
        loss="squared_error",
    )
    stack = StackingRegressor(
        estimators=[
            ("extra", ExtraTreesRegressor(n_estimators=500, random_state=random_state, n_jobs=-1)),
            ("forest", RandomForestRegressor(n_estimators=350, random_state=random_state, n_jobs=-1)),
            ("boost", GradientBoostingRegressor(random_state=random_state, n_estimators=450, learning_rate=0.03, max_depth=3)),
            ("knn", Pipeline([("scale", StandardScaler()), ("knn", KNeighborsRegressor(n_neighbors=5, weights="distance"))])),
        ],
        final_estimator=RidgeCV(alphas=np.logspace(-4, 4, 25)),
        passthrough=True,
        cv=5,
        n_jobs=-1,
    )
    return {
        "extra_trees": make_pipeline(extra_trees),
        "random_forest": make_pipeline(random_forest),
        "gradient_boosting": make_pipeline(gradient_boosting),
        "svr_rbf": make_pipeline(SVR(C=40.0, epsilon=0.01, gamma="scale"), scale=True),
        "kernel_ridge_rbf": make_pipeline(KernelRidge(alpha=0.03, kernel="rbf", gamma=0.18), scale=True),
        "knn_distance": make_pipeline(KNeighborsRegressor(n_neighbors=3, weights="distance"), scale=True),
        "stacking_ensemble": make_pipeline(stack),
    }


def oracle_model() -> Pipeline:
    return make_pipeline(KNeighborsRegressor(n_neighbors=1, weights="distance"), scale=True)


def regression_metrics(target_values: np.ndarray, predicted_values: np.ndarray) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(target_values, predicted_values)),
        "rmse": float(root_mean_squared_error(target_values, predicted_values)),
        "r2": float(r2_score(target_values, predicted_values)),
        "max_abs_error": float(np.max(np.abs(target_values - predicted_values))),
        "exact_0p01_rate": float(np.mean(np.round(target_values, 2) == np.round(predicted_values, 2))),
    }


def evaluate_model(model: Pipeline, feature_frame: Any, target_values: np.ndarray, rounded_integer: bool = False) -> dict[str, Any]:
    fitted_model = clone(model).fit(feature_frame, target_values)
    train_predictions = fitted_model.predict(feature_frame)
    splitter = KFold(n_splits=5, shuffle=True, random_state=42)
    cv_predictions = cross_val_predict(clone(model), feature_frame, target_values, cv=splitter, n_jobs=None)
    result = {
        "train": regression_metrics(target_values, train_predictions),
        "cv": regression_metrics(target_values, cv_predictions),
    }
    if rounded_integer:
        result["train"]["rounded_accuracy"] = float(accuracy_score(target_values, np.rint(train_predictions)))
        result["train"]["rounded_mae"] = float(mean_absolute_error(target_values, np.rint(train_predictions)))
        result["cv"]["rounded_accuracy"] = float(accuracy_score(target_values, np.rint(cv_predictions)))
        result["cv"]["rounded_mae"] = float(mean_absolute_error(target_values, np.rint(cv_predictions)))
    return {"model": fitted_model, "metrics": result}


def select_best_model(feature_frame: Any, target_values: np.ndarray, rounded_integer: bool = False) -> dict[str, Any]:
    evaluations = {}
    for model_name, model in candidate_models().items():
        print(f"training candidate={model_name}")
        evaluations[model_name] = evaluate_model(model, feature_frame, target_values, rounded_integer)
    best_name = min(evaluations, key=lambda name: evaluations[name]["metrics"]["cv"]["mae"])
    return {
        "best_name": best_name,
        "best_model": evaluations[best_name]["model"],
        "evaluations": {name: payload["metrics"] for name, payload in evaluations.items()},
    }


def anchor_predictions(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for anchor in ANCHOR_CASES:
        input_data = make_input_frame(*anchor["inputs"])
        production = predict_from_bundle(bundle, input_data, "production")
        oracle = predict_from_bundle(bundle, input_data, "oracle")
        rows.append({"name": anchor["name"], "target": anchor["targets"], "production": production, "oracle": oracle})
    return rows


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    dataframe = load_daimer_dataframe(DATA_FILE)
    valid_degree_rows = dataframe.dropna(subset=FEATURE_COLUMNS + [TARGET_D10, TARGET_D20, TARGET_GLOBAL]).copy()
    valid_gei_rows = valid_degree_rows.dropna(subset=[TARGET_GEI]).copy()

    degree_feature_frame = valid_degree_rows[FEATURE_COLUMNS]
    gei_feature_frame = valid_gei_rows[FEATURE_COLUMNS]

    targets = {
        "d10": (degree_feature_frame, valid_degree_rows[TARGET_D10].to_numpy(dtype=float), False),
        "d20": (degree_feature_frame, valid_degree_rows[TARGET_D20].to_numpy(dtype=float), False),
        "gei": (gei_feature_frame, valid_gei_rows[TARGET_GEI].to_numpy(dtype=float), True),
    }

    production_models = {}
    oracle_models = {}
    metrics = {
        "rows_degree": int(len(valid_degree_rows)),
        "rows_gei": int(len(valid_gei_rows)),
        "targets": {},
    }

    for target_name, (feature_frame, target_values, rounded_integer) in targets.items():
        print(f"\n=== target={target_name} ===")
        selected = select_best_model(feature_frame, target_values, rounded_integer)
        production_models[target_name] = selected["best_model"]

        oracle = oracle_model().fit(feature_frame, target_values)
        oracle_predictions = oracle.predict(feature_frame)
        oracle_models[target_name] = oracle

        metrics["targets"][target_name] = {
            "best_production_model": selected["best_name"],
            "candidate_metrics": selected["evaluations"],
            "oracle_train": regression_metrics(target_values, oracle_predictions),
        }
        if rounded_integer:
            metrics["targets"][target_name]["oracle_train"]["rounded_accuracy"] = float(
                accuracy_score(target_values, np.rint(oracle_predictions))
            )
            metrics["targets"][target_name]["oracle_train"]["rounded_mae"] = float(
                mean_absolute_error(target_values, np.rint(oracle_predictions))
            )

    bundle = {
        "version": 1,
        "feature_columns": FEATURE_COLUMNS,
        "production_models": production_models,
        "oracle_models": oracle_models,
        "metrics": metrics,
        "note": "production_models are selected by 5-fold CV; oracle_models use 1-NN and reproduce training rows exactly.",
    }
    metrics["anchor_predictions"] = anchor_predictions(bundle)

    joblib.dump(bundle, BUNDLE_FILE)
    METRICS_FILE.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nsaved_bundle={BUNDLE_FILE}")
    print(f"saved_metrics={METRICS_FILE}")
    print(json.dumps(metrics["anchor_predictions"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
