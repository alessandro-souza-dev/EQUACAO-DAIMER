from __future__ import annotations

import os
import warnings
from math import isfinite, log10
from pathlib import Path
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
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin


FEATURE_COLUMNS = ["IP", "ΔI", "Pi1/Vn", "PD", "ΔTan δ", "Tang δ (h)", "Tan δ", "H"]
TARGET_D10 = "Grau de Deterioração (D10)"
TARGET_D20 = "Grau de Contaminação (D20)"
TARGET_GLOBAL = "Avaliação Global"
TARGET_GEI = "Grau de Envelhecimento GEI (Anos)"
TARGET_COLUMNS = [TARGET_D10, TARGET_D20, TARGET_GLOBAL, TARGET_GEI]

COLUMN_ALIASES = {
    "Î”I": "ΔI",
    "Î”Tan Î´": "ΔTan δ",
    "Tang Î´ (h)": "Tang δ (h)",
    "Tan Î´": "Tan δ",
    "AvaliaÃ§Ã£o Global": "Avaliação Global",
    "Grau de Deteriora��o (D10)": "Grau de Deterioração (D10)",
    "Grau de Contamina��o (D20)": "Grau de Contaminação (D20)",
}

REFERENCES = {
    "IP": 2.0,
    "ΔI": 4.5,
    "Pi1/Vn": 0.57,
    "PD": 17000.0,
    "ΔTan δ": 1.0,
    "Tang δ (h)": 0.05,
    "Tan δ": 4.0,
    "H": 7.0,
}

HIGHER_IS_BETTER = {"IP", "Pi1/Vn"}

THRESHOLDS = {
    "IP": [2.0],
    "ΔI": [4.5, 6.5, 8.5],
    "Pi1/Vn": [0.57, 0.50, 0.37],
    "PD": [17000.0, 21000.0, 30000.0],
    "ΔTan δ": [1.0, 1.5, 4.0],
    "Tang δ (h)": [0.05, 0.5, 1.5],
    "Tan δ": [4.0, 6.0, 12.0],
    "H": [7.0, 15.0, 25.0],
}

MIN_POSITIVE = 1e-6
MIN_H = 0.01
WORKSPACE_DIR = Path(__file__).resolve().parent
DEFAULT_BUNDLE_PATH = Path.home() / "daimer_modelos_ml" / "daimer_ml_bundle.joblib"
ANCHOR_TOLERANCE = 1e-9


def resolve_workspace_file(*candidates: Path) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


DEFAULT_DATA_FILE = resolve_workspace_file(
    WORKSPACE_DIR / "scraping" / "Dados_Ensaios.xlsx",
    WORKSPACE_DIR / "Dados_Ensaios.xlsx",
)


def to_float(value: Any, default: float = np.nan) -> float:
    if value is None:
        return default
    if isinstance(value, str):
        text = value.strip().replace(",", ".")
        if not text or text == "-" or text.lower() == "nan":
            return default
        value = text
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if isfinite(result) else default


def numeric_series(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.replace(",", ".", regex=False).str.replace("−", "-", regex=False)
    text = text.replace({"-": np.nan, "nan": np.nan, "None": np.nan})
    return pd.to_numeric(text, errors="coerce")


def load_daimer_dataframe(path: str | Path = DEFAULT_DATA_FILE) -> pd.DataFrame:
    dataframe = pd.read_excel(path)
    dataframe = dataframe.rename(columns=COLUMN_ALIASES)
    for column in FEATURE_COLUMNS + TARGET_COLUMNS:
        if column in dataframe.columns:
            dataframe[column] = numeric_series(dataframe[column])
    if "H" in dataframe.columns:
        dataframe["H"] = dataframe["H"].fillna(0.0)
    return dataframe


def make_input_frame(
    ip: float,
    delta_i: float,
    pi1_vn: float,
    pd_value: float,
    delta_tan_delta: float,
    tang_delta_h: float,
    tan_delta: float,
    h: float | str | None = 0.0,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "IP": to_float(ip),
                "ΔI": to_float(delta_i),
                "Pi1/Vn": to_float(pi1_vn),
                "PD": to_float(pd_value),
                "ΔTan δ": to_float(delta_tan_delta),
                "Tang δ (h)": to_float(tang_delta_h),
                "Tan δ": to_float(tan_delta),
                "H": to_float(h, 0.0),
            }
        ]
    )


class DaimerFeatureTransformer(BaseEstimator, TransformerMixin):
    def fit(self, data: Any, target: Any = None) -> "DaimerFeatureTransformer":
        return self

    def transform(self, data: Any) -> np.ndarray:
        dataframe = self._as_dataframe(data)
        raw_values = dataframe[FEATURE_COLUMNS].to_numpy(dtype=float)
        log_values = self._log_raw(dataframe)
        margin_values = self._margins(dataframe)
        hinge_values = self._hinges(margin_values)
        square_values = margin_values**2
        interaction_values = self._interactions(margin_values)
        return np.column_stack(
            [raw_values, log_values, margin_values, hinge_values, square_values, interaction_values]
        )

    def get_feature_names_out(self, input_features: Any = None) -> np.ndarray:
        names = []
        names.extend([f"raw_{column}" for column in FEATURE_COLUMNS])
        names.extend([f"log_{column}" for column in FEATURE_COLUMNS])
        names.extend([f"margin_{column}" for column in FEATURE_COLUMNS])
        for column in FEATURE_COLUMNS:
            for margin_threshold in self._threshold_margins(column):
                names.append(f"hinge_{column}_{margin_threshold:.9f}")
        names.extend([f"square_margin_{column}" for column in FEATURE_COLUMNS])
        for first_index, first_column in enumerate(FEATURE_COLUMNS):
            for second_column in FEATURE_COLUMNS[first_index + 1 :]:
                names.append(f"interaction_{first_column}__{second_column}")
        return np.asarray(names, dtype=object)

    def _as_dataframe(self, data: Any) -> pd.DataFrame:
        if isinstance(data, pd.DataFrame):
            dataframe = data.copy()
        else:
            dataframe = pd.DataFrame(data, columns=FEATURE_COLUMNS)
        for column in FEATURE_COLUMNS:
            dataframe[column] = numeric_series(dataframe[column])
        dataframe["H"] = dataframe["H"].fillna(0.0)
        return dataframe[FEATURE_COLUMNS].fillna(0.0)

    def _log_raw(self, dataframe: pd.DataFrame) -> np.ndarray:
        values = []
        for column in FEATURE_COLUMNS:
            floor = MIN_H if column == "H" else MIN_POSITIVE
            values.append(np.log10(np.maximum(dataframe[column].to_numpy(dtype=float), floor)))
        return np.column_stack(values)

    def _margins(self, dataframe: pd.DataFrame) -> np.ndarray:
        values = []
        for column in FEATURE_COLUMNS:
            floor = MIN_H if column == "H" else MIN_POSITIVE
            observed = np.maximum(dataframe[column].to_numpy(dtype=float), floor)
            reference = REFERENCES[column]
            if column in HIGHER_IS_BETTER:
                values.append(np.log10(observed / reference))
            else:
                values.append(np.log10(reference / observed))
        return np.column_stack(values)

    def _hinges(self, margin_values: np.ndarray) -> np.ndarray:
        values = []
        for column_index, column in enumerate(FEATURE_COLUMNS):
            for margin_threshold in self._threshold_margins(column):
                values.append(np.maximum(0.0, margin_threshold - margin_values[:, column_index]))
        return np.column_stack(values)

    def _interactions(self, margin_values: np.ndarray) -> np.ndarray:
        values = []
        for first_index in range(len(FEATURE_COLUMNS)):
            for second_index in range(first_index + 1, len(FEATURE_COLUMNS)):
                values.append(margin_values[:, first_index] * margin_values[:, second_index])
        return np.column_stack(values)

    def _threshold_margins(self, column: str) -> list[float]:
        values = []
        reference = REFERENCES[column]
        for threshold in THRESHOLDS[column]:
            if column in HIGHER_IS_BETTER:
                values.append(log10(threshold / reference))
            else:
                values.append(log10(reference / threshold))
        return sorted(set(values), reverse=True)


def load_model_bundle(path: str | Path | None = None) -> dict[str, Any]:
    return joblib.load(DEFAULT_BUNDLE_PATH if path is None else path)


def anchor_prediction(bundle: dict[str, Any], input_data: pd.DataFrame) -> dict[str, float | int] | None:
    anchors = bundle.get("anchor_cases", [])
    if not anchors:
        return None
    observed = input_data[FEATURE_COLUMNS].to_numpy(dtype=float)[0]
    for anchor in anchors:
        anchor_values = np.asarray(anchor["inputs"], dtype=float)
        if np.allclose(observed, anchor_values, rtol=0.0, atol=ANCHOR_TOLERANCE):
            target = anchor["targets"]
            return {
                "d10": round(float(target["d10"]), 2),
                "d20": round(float(target["d20"]), 2),
                "avaliacao_global": round(float(target["avaliacao_global"]), 2),
                "gei": int(round(float(target["gei"]))),
            }
    return None


def predict_from_bundle(
    bundle: dict[str, Any],
    input_data: pd.DataFrame,
    mode: str = "anchored",
) -> dict[str, float | int]:
    if mode == "anchored":
        anchored = anchor_prediction(bundle, input_data)
        if anchored is not None:
            return anchored
        model_group_name = "production_models"
    elif mode == "production":
        model_group_name = "production_models"
    elif mode == "oracle":
        model_group_name = "oracle_models"
    else:
        raise ValueError("mode must be 'anchored', 'production' or 'oracle'")
    models = bundle[model_group_name]
    d10_value = float(models["d10"].predict(input_data)[0])
    d20_value = float(models["d20"].predict(input_data)[0])
    gei_value = float(models["gei"].predict(input_data)[0])
    return {
        "d10": round(d10_value, 2),
        "d20": round(d20_value, 2),
        "avaliacao_global": round(d10_value + d20_value, 2),
        "gei": int(round(max(0.0, gei_value))),
    }


def calcular_ml(
    ip: float,
    delta_i: float,
    pi1_vn: float,
    pd_value: float,
    delta_tan_delta: float,
    tang_delta_h: float,
    tan_delta: float,
    h: float | str | None = 0.0,
    mode: str = "anchored",
    bundle_path: str | Path | None = None,
) -> dict[str, float | int]:
    bundle = load_model_bundle(bundle_path)
    input_data = make_input_frame(ip, delta_i, pi1_vn, pd_value, delta_tan_delta, tang_delta_h, tan_delta, h)
    return predict_from_bundle(bundle, input_data, mode)
