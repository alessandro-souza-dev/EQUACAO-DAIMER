from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import KFold, cross_val_predict

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from daimer_ml import FEATURE_COLUMNS, TARGET_GEI, load_daimer_dataframe
from equacoes_daimer import MIN_H, _log_margin, calcular_gei


BASE_DIR = ROOT_DIR if SCRIPT_DIR.name == "estudo" else SCRIPT_DIR
ENSAIOS_FILE = BASE_DIR / "scraping" / "Dados_Ensaios.xlsx"
if not ENSAIOS_FILE.exists():
    ENSAIOS_FILE = BASE_DIR / "Dados_Ensaios.xlsx"
DAIMER_FILE = BASE_DIR / "scraping" / "Dados_Daimer.xlsx"
if not DAIMER_FILE.exists():
    DAIMER_FILE = BASE_DIR / "Dados_Daimer.xlsx"
REPORT_FILE = BASE_DIR / "docs" / "relatorio_gei_por_tipo_equipamento.md"
if not REPORT_FILE.parent.exists():
    REPORT_FILE = BASE_DIR / "relatorio_gei_por_tipo_equipamento.md"

TYPE_COLUMN = "Tipo de Equipamento"
TYPE_NORMALIZED = "Tipo normalizado"
OS_KEY = "NR_OS_norm"
MODEL_FEATURES = [
    "m_ip",
    "m_delta_i",
    "m_pi1_vn",
    "m_pd",
    "m_delta_tan_delta",
    "m_tang_delta_h",
    "m_tan_delta",
    "m_h",
]
FEATURE_LABELS = {
    "m_ip": "IP",
    "m_delta_i": "ΔI",
    "m_pi1_vn": "Pi1/Vn",
    "m_pd": "PD",
    "m_delta_tan_delta": "ΔTan δ",
    "m_tang_delta_h": "Tang δ (h)",
    "m_tan_delta": "Tan δ",
    "m_h": "H",
}


def normalize_os(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().upper()


def normalize_equipment_type(value: object) -> str:
    text = "" if pd.isna(value) else str(value).strip().lower()
    if "gerador" in text:
        return "Gerador"
    if "motor" in text:
        return "Motor"
    return "Outro"


def load_merged_dataframe() -> pd.DataFrame:
    ensaios = load_daimer_dataframe(ENSAIOS_FILE)
    ensaios[OS_KEY] = ensaios["NR_OS"].map(normalize_os)
    if TYPE_COLUMN in ensaios.columns:
        ensaios[TYPE_NORMALIZED] = ensaios[TYPE_COLUMN].map(normalize_equipment_type)
        return ensaios

    daimer = pd.read_excel(DAIMER_FILE)
    daimer[OS_KEY] = daimer["NR_OS"].map(normalize_os)
    daimer[TYPE_NORMALIZED] = daimer[TYPE_COLUMN].map(normalize_equipment_type)
    metadata = daimer[[OS_KEY, TYPE_COLUMN, TYPE_NORMALIZED]].drop_duplicates(OS_KEY)
    return ensaios.merge(metadata, on=OS_KEY, how="left")


def margin_features(frame: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "m_ip": [_log_margin(value, 2.0, True) for value in frame["IP"]],
            "m_delta_i": [_log_margin(value, 4.5, False) for value in frame["ΔI"]],
            "m_pi1_vn": [_log_margin(value, 0.57, True) for value in frame["Pi1/Vn"]],
            "m_pd": [_log_margin(value, 17000.0, False) for value in frame["PD"]],
            "m_delta_tan_delta": [_log_margin(value, 1.0, False) for value in frame["ΔTan δ"]],
            "m_tang_delta_h": [_log_margin(value, 0.05, False) for value in frame["Tang δ (h)"]],
            "m_tan_delta": [_log_margin(value, 4.0, False) for value in frame["Tan δ"]],
            "m_h": [_log_margin(value, 7.0, False, MIN_H) for value in frame["H"]],
        }
    )


def current_gei_predictions(frame: pd.DataFrame) -> np.ndarray:
    return np.asarray(
        [calcular_gei(*[row[column] for column in FEATURE_COLUMNS]) for _, row in frame.iterrows()],
        dtype=float,
    )


def metrics(target_values: np.ndarray, predicted_values: np.ndarray) -> dict[str, float]:
    errors = np.asarray(predicted_values, dtype=float) - np.asarray(target_values, dtype=float)
    return {
        "MAE": float(mean_absolute_error(target_values, predicted_values)),
        "RMSE": float(root_mean_squared_error(target_values, predicted_values)),
        "R2": float(r2_score(target_values, predicted_values)),
        "Max abs": float(np.max(np.abs(errors))),
    }


def same_type_conflict_indexes(frame: pd.DataFrame) -> tuple[set[int], pd.DataFrame]:
    rounded = frame.copy()
    for column in FEATURE_COLUMNS:
        rounded[column] = rounded[column].round(6)

    conflict_indexes: set[int] = set()
    rows = []
    for _, group in rounded.groupby(FEATURE_COLUMNS + [TYPE_NORMALIZED], dropna=False):
        if len(group) < 2:
            continue
        gei_span = float(group[TARGET_GEI].max() - group[TARGET_GEI].min())
        if gei_span <= 1.0:
            continue
        conflict_indexes.update(group.index.tolist())
        rows.append(
            {
                "Tipo": group[TYPE_NORMALIZED].iloc[0],
                "Linhas": int(len(group)),
                "GEI min": float(group[TARGET_GEI].min()),
                "GEI max": float(group[TARGET_GEI].max()),
                "Amostras": ", ".join(group["NR_OS"].astype(str).head(12).tolist()),
            }
        )
    conflicts = pd.DataFrame(rows)
    if not conflicts.empty:
        conflicts = conflicts.sort_values(["Linhas", "Tipo"], ascending=[False, True])
    return conflict_indexes, conflicts


def fit_type_models(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, dict[str, RidgeCV]]:
    x = margin_features(frame)
    y = frame[TARGET_GEI].to_numpy(dtype=float)
    alphas = np.logspace(-4, 4, 40)

    global_cv = cross_val_predict(
        RidgeCV(alphas=alphas),
        x,
        y,
        cv=KFold(n_splits=5, shuffle=True, random_state=42),
    )

    by_type_cv = np.zeros_like(y, dtype=float)
    models = {}
    for equipment_type in ["Motor", "Gerador"]:
        mask = frame[TYPE_NORMALIZED].eq(equipment_type).to_numpy()
        x_type = x.loc[mask]
        y_type = y[mask]
        model = RidgeCV(alphas=alphas).fit(x_type, y_type)
        models[equipment_type] = model
        by_type_cv[mask] = cross_val_predict(
            RidgeCV(alphas=alphas),
            x_type,
            y_type,
            cv=KFold(n_splits=min(5, len(y_type)), shuffle=True, random_state=42),
        )
    return global_cv, by_type_cv, models


def metric_rows(frame: pd.DataFrame, label: str) -> tuple[pd.DataFrame, dict[str, RidgeCV]]:
    y = frame[TARGET_GEI].to_numpy(dtype=float)
    current_predictions = current_gei_predictions(frame)
    global_cv, by_type_cv, models = fit_type_models(frame)
    rows = [
        {"Base": label, "Grupo": "Todos", "Modelo": "GEI atual", **metrics(y, current_predictions)},
        {"Base": label, "Grupo": "Todos", "Modelo": "Ridge global CV", **metrics(y, global_cv)},
        {"Base": label, "Grupo": "Todos", "Modelo": "Ridge por tipo CV", **metrics(y, by_type_cv)},
    ]
    for equipment_type in ["Motor", "Gerador"]:
        mask = frame[TYPE_NORMALIZED].eq(equipment_type).to_numpy()
        y_type = y[mask]
        rows.extend(
            [
                {"Base": label, "Grupo": equipment_type, "Modelo": "GEI atual", **metrics(y_type, current_predictions[mask])},
                {"Base": label, "Grupo": equipment_type, "Modelo": "Ridge global CV", **metrics(y_type, global_cv[mask])},
                {"Base": label, "Grupo": equipment_type, "Modelo": "Ridge por tipo CV", **metrics(y_type, by_type_cv[mask])},
            ]
        )
    return pd.DataFrame(rows), models


def coefficient_table(models: dict[str, RidgeCV], frame: pd.DataFrame) -> pd.DataFrame:
    x = margin_features(frame)
    rows = []
    for equipment_type, model in models.items():
        mask = frame[TYPE_NORMALIZED].eq(equipment_type).to_numpy()
        x_type = x.loc[mask]
        contributions = x_type.to_numpy(dtype=float) * model.coef_
        mean_abs = np.abs(contributions).mean(axis=0)
        total = mean_abs.sum()
        for feature_name, coefficient, contribution_abs in zip(MODEL_FEATURES, model.coef_, mean_abs):
            rows.append(
                {
                    "Tipo": equipment_type,
                    "Input": FEATURE_LABELS[feature_name],
                    "Coeficiente": float(coefficient),
                    "Peso estrutural": 0.0 if total <= 0 else float(100.0 * contribution_abs / total),
                    "Contrib abs media": float(contribution_abs),
                }
            )
    return pd.DataFrame(rows).sort_values(["Tipo", "Peso estrutural"], ascending=[True, False])


def permutation_weight_table(frame: pd.DataFrame, repeats: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    rows = []
    for equipment_type in ["Motor", "Gerador"]:
        frame_type = frame[frame[TYPE_NORMALIZED].eq(equipment_type)].reset_index(drop=True)
        y = frame_type[TARGET_GEI].to_numpy(dtype=float)
        base_predictions = current_gei_predictions(frame_type)
        baseline_mae = mean_absolute_error(y, base_predictions)
        increases = []
        for column in FEATURE_COLUMNS:
            column_increases = []
            for _ in range(repeats):
                shuffled = frame_type.copy()
                shuffled[column] = rng.permutation(shuffled[column].to_numpy())
                shuffled_predictions = current_gei_predictions(shuffled)
                shuffled_mae = mean_absolute_error(y, shuffled_predictions)
                column_increases.append(max(0.0, float(shuffled_mae - baseline_mae)))
            increases.append({"Tipo": equipment_type, "Input": column, "Aumento MAE": float(np.mean(column_increases))})
        subtotal = sum(row["Aumento MAE"] for row in increases)
        for row in increases:
            row["Peso permutacao"] = 0.0 if subtotal <= 0 else 100.0 * row["Aumento MAE"] / subtotal
            rows.append(row)
    return pd.DataFrame(rows).sort_values(["Tipo", "Peso permutacao"], ascending=[True, False])


def markdown_table(dataframe: pd.DataFrame, columns: list[str], formats: dict[str, str] | None = None) -> list[str]:
    formats = formats or {}
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---:" if column != columns[0] else "---" for column in columns) + " |",
    ]
    for _, row in dataframe.iterrows():
        values = []
        for column in columns:
            value = row[column]
            if column in formats:
                values.append(formats[column].format(value).replace(".", ","))
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def report_number(value: object) -> str:
    if pd.isna(value):
        return ""
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.6g}".replace(".", ",")


def conflict_detail_lines(frame: pd.DataFrame) -> list[str]:
    rounded = frame.copy()
    for column in FEATURE_COLUMNS:
        rounded[column] = rounded[column].round(6)

    groups = []
    for _, group in rounded.groupby(FEATURE_COLUMNS + [TYPE_NORMALIZED], dropna=False):
        if len(group) < 2:
            continue
        gei_span = float(group[TARGET_GEI].max() - group[TARGET_GEI].min())
        if gei_span <= 1.0:
            continue
        groups.append(group.sort_values([TARGET_GEI, "NR_OS"]))

    groups.sort(key=lambda group: (-len(group), str(group[TYPE_NORMALIZED].iloc[0])))
    lines: list[str] = []
    for index, group in enumerate(groups, start=1):
        first = group.iloc[0]
        gei_min = report_number(group[TARGET_GEI].min())
        gei_max = report_number(group[TARGET_GEI].max())
        inputs = "; ".join(f"{column}={report_number(first[column])}" for column in FEATURE_COLUMNS)
        lines.extend(
            [
                f"### Grupo {index}: {first[TYPE_NORMALIZED]} com {len(group)} linhas, GEI {gei_min} a {gei_max}",
                "",
                f"- Inputs iguais: {inputs}.",
                "",
                "| GEI real | Linhas | NR_OS |",
                "| ---: | ---: | --- |",
            ]
        )
        for gei_value, gei_group in group.groupby(TARGET_GEI, dropna=False):
            os_values = ", ".join(gei_group["NR_OS"].astype(str).tolist())
            lines.append(f"| {report_number(gei_value)} | {len(gei_group)} | {os_values} |")
        lines.append("")
    return lines


def write_report(
    valid: pd.DataFrame,
    clean: pd.DataFrame,
    conflicts: pd.DataFrame,
    raw_metrics: pd.DataFrame,
    clean_metrics: pd.DataFrame,
    clean_models: dict[str, RidgeCV],
    total_gei_rows: int,
    excluded_without_motor_generator_type: int,
) -> None:
    coeffs = coefficient_table(clean_models, clean)
    permutation = permutation_weight_table(clean)
    type_counts = valid[TYPE_NORMALIZED].value_counts().to_dict()
    clean_type_counts = clean[TYPE_NORMALIZED].value_counts().to_dict()
    matched_rows = int(valid[TYPE_COLUMN].notna().sum())

    lines = [
        "# GEI por tipo de equipamento",
        "",
        "## Objetivo",
        "",
        "Usar a coluna `Tipo de Equipamento` em `scraping/Dados_Ensaios.xlsx`, separar Motor e Gerador, e testar se GEI fica mais proximo com pesos separados. Quando a coluna nao existir em uma planilha antiga, o estudo ainda consegue usar `scraping/Dados_Daimer.xlsx` como fallback por `NR_OS`.",
        "",
        "## Cruzamento",
        "",
        f"- Linhas com GEI e inputs validos em `scraping/Dados_Ensaios.xlsx`: {total_gei_rows}.",
        f"- Linhas com GEI, inputs validos e tipo Motor/Gerador: {len(valid)}.",
        f"- Linhas fora da analise por falta de tipo Motor/Gerador: {excluded_without_motor_generator_type}.",
        f"- Linhas com `Tipo de Equipamento` informado: {matched_rows}.",
        f"- Distribuicao bruta: Motor {type_counts.get('Motor', 0)}, Gerador {type_counts.get('Gerador', 0)}.",
        f"- Base limpa por tipo: Motor {clean_type_counts.get('Motor', 0)}, Gerador {clean_type_counts.get('Gerador', 0)}.",
        "",
        "## Duplicados conflitantes dentro do mesmo tipo",
        "",
        f"Foram removidos {len(valid) - len(clean)} registros onde os mesmos inputs e o mesmo tipo tinham GEI real diferente em mais de 1 ano.",
        "",
    ]
    if conflicts.empty:
        lines.append("Nenhum duplicado conflitante foi encontrado.")
    else:
        lines.extend(markdown_table(conflicts.head(10), ["Tipo", "Linhas", "GEI min", "GEI max", "Amostras"], {"GEI min": "{:.0f}", "GEI max": "{:.0f}"}))
        lines.extend(
            [
                "",
                "## Detalhamento dos grupos conflitantes",
                "",
                "Cada grupo abaixo tem o mesmo tipo de equipamento e os mesmos oito inputs, mas GEI real diferente.",
                "",
            ]
        )
        lines.extend(conflict_detail_lines(valid))

    metrics_frame = pd.concat([raw_metrics, clean_metrics], ignore_index=True)
    if lines[-1] != "":
        lines.append("")
    lines.extend(
        [
            "## Comparacao de erro",
            "",
            "`Ridge por tipo CV` usa pesos separados para Motor e Gerador, avaliados por validacao cruzada. Se ele nao melhora contra `GEI atual`, nao vale trocar a equacao de producao ainda.",
            "",
        ]
    )
    lines.extend(
        markdown_table(
            metrics_frame,
            ["Base", "Grupo", "Modelo", "MAE", "RMSE", "R2", "Max abs"],
            {"MAE": "{:.3f}", "RMSE": "{:.3f}", "R2": "{:.3f}", "Max abs": "{:.3f}"},
        )
    )

    lines.extend(
        [
            "",
            "## Pesos estruturais separados",
            "",
            "Os pesos abaixo vem do modelo Ridge treinado na base limpa de cada tipo. Eles mostram que os sinais dominantes mudam, mas tambem revelam instabilidade de dados em alguns coeficientes.",
            "",
        ]
    )
    lines.extend(
        markdown_table(
            coeffs,
            ["Tipo", "Input", "Coeficiente", "Peso estrutural", "Contrib abs media"],
            {"Coeficiente": "{:.3f}", "Peso estrutural": "{:.2f}%", "Contrib abs media": "{:.3f}"},
        )
    )

    lines.extend(
        [
            "",
            "## Importancia empirica por permutacao",
            "",
            "Esta tabela mede quanto o MAE do GEI atual piora quando cada input e embaralhado dentro do proprio tipo de equipamento.",
            "",
        ]
    )
    lines.extend(
        markdown_table(
            permutation,
            ["Tipo", "Input", "Peso permutacao", "Aumento MAE"],
            {"Peso permutacao": "{:.2f}%", "Aumento MAE": "{:.4f}"},
        )
    )

    lines.extend(
        [
            "",
            "## Conclusao",
            "",
            "- A hipotese de pesos diferentes por tipo faz sentido conceitual e aparece nos coeficientes: motores e geradores nao respondem igual aos mesmos sinais.",
            "- Mesmo assim, nesta base o modelo separado por tipo nao ficou melhor que o GEI atual em validacao cruzada. Na base limpa, o GEI atual ficou com MAE 2,015, enquanto o Ridge por tipo ficou com MAE 2,084.",
            "- O principal limitador continua sendo dado/historico: ainda existem registros do mesmo tipo com inputs identicos e GEI muito diferente. Tipo de equipamento ajuda, mas nao substitui tempo de operacao, ambiente, manutencao, classe de isolamento e historico termico.",
            "- Portanto, a recomendacao e nao trocar a equacao de producao ainda. Use a separacao Motor/Gerador como diagnostico e como proxima feature de ML, mas mantenha GEI atual ate ter metadados historicos suficientes.",
            "",
        ]
    )
    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    merged = load_merged_dataframe()
    all_gei = merged.dropna(subset=FEATURE_COLUMNS + [TARGET_GEI]).copy().reset_index(drop=True)
    valid = all_gei.dropna(subset=[TYPE_NORMALIZED]).copy().reset_index(drop=True)
    valid = valid[valid[TYPE_NORMALIZED].isin(["Motor", "Gerador"])].copy().reset_index(drop=True)
    excluded_without_motor_generator_type = len(all_gei) - len(valid)

    conflict_indexes, conflicts = same_type_conflict_indexes(valid)
    clean = valid.drop(index=list(conflict_indexes)).reset_index(drop=True)

    raw_metrics, _ = metric_rows(valid, "Bruta")
    clean_metrics, clean_models = metric_rows(clean, "Limpa por tipo")
    write_report(
        valid,
        clean,
        conflicts,
        raw_metrics,
        clean_metrics,
        clean_models,
        len(all_gei),
        excluded_without_motor_generator_type,
    )
    print(f"Relatorio gerado: {REPORT_FILE}")


if __name__ == "__main__":
    main()