from __future__ import annotations

import json
import os
import warnings
from pathlib import Path
import sys
from typing import Any

detected_cpu_count = os.cpu_count() or 1
try:
    configured_cpu_count = int(os.environ.get("LOKY_MAX_CPU_COUNT", detected_cpu_count))
except ValueError:
    configured_cpu_count = detected_cpu_count
if configured_cpu_count >= detected_cpu_count and detected_cpu_count > 1:
    os.environ["LOKY_MAX_CPU_COUNT"] = str(detected_cpu_count - 1)
warnings.filterwarnings("ignore", message="Could not find the number of physical cores.*")

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

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

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


BASE_DIR = ROOT_DIR if SCRIPT_DIR.name == "estudo" else SCRIPT_DIR
DATA_FILE = BASE_DIR / "scraping" / "Dados_Ensaios.xlsx"
if not DATA_FILE.exists():
    DATA_FILE = BASE_DIR / "Dados_Ensaios.xlsx"
OUTPUT_DIR = Path.home() / "daimer_modelos_ml"
BUNDLE_FILE = OUTPUT_DIR / "daimer_ml_bundle.joblib"
METRICS_FILE = OUTPUT_DIR / "metricas_ml.json"
WEIGHTS_REPORT_FILE = BASE_DIR / "docs" / "relatorio_pesos_modelo_ml.md"
if not WEIGHTS_REPORT_FILE.parent.exists():
    WEIGHTS_REPORT_FILE = BASE_DIR / "relatorio_pesos_modelo_ml.md"


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


def permutation_input_weights(
    model: Pipeline,
    feature_frame: Any,
    target_values: np.ndarray,
    random_state: int = 42,
    repeats: int = 30,
) -> list[dict[str, float | str]]:
    base_frame = feature_frame.reset_index(drop=True).copy()
    target_array = np.asarray(target_values, dtype=float)
    baseline_predictions = model.predict(base_frame)
    baseline_mae = mean_absolute_error(target_array, baseline_predictions)
    rng = np.random.default_rng(random_state)

    rows = []
    for column in FEATURE_COLUMNS:
        mae_increases = []
        for _ in range(repeats):
            shuffled_frame = base_frame.copy()
            shuffled_frame[column] = rng.permutation(shuffled_frame[column].to_numpy())
            shuffled_predictions = model.predict(shuffled_frame)
            shuffled_mae = mean_absolute_error(target_array, shuffled_predictions)
            mae_increases.append(max(0.0, float(shuffled_mae - baseline_mae)))
        input_values = base_frame[column].to_numpy(dtype=float)
        if np.std(input_values) > 0 and np.std(baseline_predictions) > 0:
            correlation = float(np.corrcoef(input_values, baseline_predictions)[0, 1])
        else:
            correlation = 0.0
        rows.append(
            {
                "input": column,
                "mae_increase": float(np.mean(mae_increases)),
                "mae_increase_std": float(np.std(mae_increases)),
                "prediction_correlation": correlation,
            }
        )

    total_importance = sum(float(row["mae_increase"]) for row in rows)
    for row in rows:
        row["weight_percent"] = 0.0 if total_importance <= 0 else 100.0 * float(row["mae_increase"]) / total_importance
    return sorted(rows, key=lambda row: float(row["weight_percent"]), reverse=True)


def global_input_weights(target_weights: dict[str, list[dict[str, float | str]]]) -> list[dict[str, float | str]]:
    combined = {column: 0.0 for column in FEATURE_COLUMNS}
    for rows in target_weights.values():
        for row in rows:
            combined[str(row["input"])] += float(row["weight_percent"])
    target_count = max(1, len(target_weights))
    global_rows = [
        {"input": column, "weight_percent": combined[column] / target_count}
        for column in FEATURE_COLUMNS
    ]
    return sorted(global_rows, key=lambda row: float(row["weight_percent"]), reverse=True)


def format_percent(value: float) -> str:
    return f"{value:.2f}".replace(".", ",")


def write_weights_report(metrics: dict[str, Any], path: Path = WEIGHTS_REPORT_FILE) -> None:
    target_titles = {"d10": "D10", "d20": "D20", "gei": "GEI"}
    lines = [
        "# Pesos aprendidos por input no modelo ML",
        "",
        "## Metodo",
        "",
        "Os pesos abaixo foram calculados por importancia por permutacao nos 8 inputs originais. O treino embaralha um input por vez, mede quanto o MAE piora no modelo `production` e normaliza esse impacto para 100% dentro de cada saida.",
        "",
        "Esse metodo mede influencia preditiva aprendida pelo modelo, nao coeficiente fisico linear. Em modelos nao lineares, um input pode ter peso alto por efeito direto, interacao com outros inputs ou por atuar em regioes de threshold.",
        "",
        "## Peso global medio",
        "",
        "| Input | Peso medio |",
        "| --- | ---: |",
    ]

    for row in metrics["global_input_weights"]:
        lines.append(f"| `{row['input']}` | {format_percent(float(row['weight_percent']))}% |")

    for target_name, title in target_titles.items():
        lines.extend(
            [
                "",
                f"## {title}",
                "",
                "| Input | Peso | Aumento medio do MAE | Correlação com previsão |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        for row in metrics["targets"][target_name]["input_weights"]:
            lines.append(
                "| "
                f"`{row['input']}` | "
                f"{format_percent(float(row['weight_percent']))}% | "
                f"{float(row['mae_increase']):.6f} | "
                f"{float(row['prediction_correlation']):.4f} |"
            )

    lines.extend(
        [
            "",
            "## Leitura rapida",
            "",
            "- `Peso`: porcentagem da importancia relativa dentro da saida.",
            "- `Aumento medio do MAE`: quanto o erro aumenta quando aquele input e embaralhado.",
            "- `Correlação com previsão`: sinal aproximado da relacao entre o input bruto e a previsao do modelo; valores positivos tendem a aumentar a saida, negativos tendem a reduzir, mas interacoes e thresholds podem inverter localmente.",
            "",
        ]
    )
    try:
        path.write_text("\n".join(lines), encoding="utf-8")
    except OSError:
        fallback_path = OUTPUT_DIR / path.name
        fallback_path.write_text("\n".join(lines), encoding="utf-8")


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
        anchored = predict_from_bundle(bundle, input_data, "anchored")
        production = predict_from_bundle(bundle, input_data, "production")
        oracle = predict_from_bundle(bundle, input_data, "oracle")
        rows.append(
            {
                "name": anchor["name"],
                "target": anchor["targets"],
                "anchored": anchored,
                "production": production,
                "oracle": oracle,
            }
        )
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
        "input_weights_method": "permutation importance over original input columns; normalized MAE increase from production models",
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
            "input_weights": permutation_input_weights(selected["best_model"], feature_frame, target_values),
        }
        if rounded_integer:
            metrics["targets"][target_name]["oracle_train"]["rounded_accuracy"] = float(
                accuracy_score(target_values, np.rint(oracle_predictions))
            )
            metrics["targets"][target_name]["oracle_train"]["rounded_mae"] = float(
                mean_absolute_error(target_values, np.rint(oracle_predictions))
            )

    bundle = {
        "version": 2,
        "feature_columns": FEATURE_COLUMNS,
        "anchor_cases": ANCHOR_CASES,
        "production_models": production_models,
        "oracle_models": oracle_models,
        "metrics": metrics,
        "note": "anchored mode returns exact known external cases; production_models are selected by 5-fold CV; oracle_models use 1-NN and reproduce training rows exactly.",
    }
    metrics["anchor_predictions"] = anchor_predictions(bundle)
    target_weights = {
        target_name: payload["input_weights"]
        for target_name, payload in metrics["targets"].items()
    }
    metrics["global_input_weights"] = global_input_weights(target_weights)

    joblib.dump(bundle, BUNDLE_FILE)
    METRICS_FILE.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    write_weights_report(metrics)

    print(f"\nsaved_bundle={BUNDLE_FILE}")
    print(f"saved_metrics={METRICS_FILE}")
    print(f"saved_weights_report={WEIGHTS_REPORT_FILE}")
    print(json.dumps(metrics["anchor_predictions"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
