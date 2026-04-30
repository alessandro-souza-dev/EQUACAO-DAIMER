from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from daimer_ml import FEATURE_COLUMNS, TARGET_D10, TARGET_D20, TARGET_GEI, load_daimer_dataframe
from equacoes_daimer import LOG20_FACTOR, MIN_H, MIN_POSITIVE, calcular_d10, calcular_d20, calcular_gei


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "scraping" / "Dados_Ensaios.xlsx"
REPORT_FILE = BASE_DIR / "relatorio_analise_pesos_inputs.md"

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


def parse_float(value: object, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if np.isfinite(result) else default


def log_margin(value: float, reference: float, higher_is_better: bool, floor: float = MIN_POSITIVE, log_base: float = 10.0) -> float:
    observed = max(parse_float(value), floor)
    if higher_is_better:
        margin = np.log10(observed / reference)
    else:
        margin = np.log10(reference / observed)
    return float(margin / LOG20_FACTOR if log_base == 20.0 else margin)


def log20_threshold(threshold_log10: float) -> float:
    return threshold_log10 / LOG20_FACTOR


def log20_coefficient(coefficient_log10: float) -> float:
    return coefficient_log10 * LOG20_FACTOR


def hinge(threshold_margin: float, margin: float) -> float:
    return max(0.0, threshold_margin - margin)


def margins(row: pd.Series, log_base: float = 10.0) -> dict[str, float]:
    return {
        "ip": log_margin(row["IP"], 2.0, True, log_base=log_base),
        "delta_i": log_margin(row["ΔI"], 4.5, False, log_base=log_base),
        "pi1_vn": log_margin(row["Pi1/Vn"], 0.57, True, log_base=log_base),
        "pd": log_margin(row["PD"], 17000.0, False, log_base=log_base),
        "delta_tan_delta": log_margin(row["ΔTan δ"], 1.0, False, log_base=log_base),
        "tang_delta_h": log_margin(row["Tang δ (h)"], 0.05, False, log_base=log_base),
        "tan_delta": log_margin(row["Tan δ"], 4.0, False, log_base=log_base),
        "h": log_margin(row["H"], 7.0, False, MIN_H, log_base=log_base),
    }


def d10_contributions(row: pd.Series) -> dict[str, float]:
    margin = margins(row)
    return {
        "Pi1/Vn": 4.7352929414 * margin["pi1_vn"] + 2.0324724184 * hinge(-0.187673132, margin["pi1_vn"]),
        "Tan δ": (
            -0.8935811025 * hinge(0.0, margin["tan_delta"])
            - 0.8727027058 * hinge(-0.477121255, margin["tan_delta"])
            - 0.5846672503 * hinge(-0.176091259, margin["tan_delta"])
            + 0.4195144391 * margin["tan_delta"]
        ),
        "PD": 0.7077394005 * margin["pd"],
        "ΔI": 0.6615225327 * margin["delta_i"],
        "ΔTan δ": 0.5940052636 * margin["delta_tan_delta"] - 0.0285128739 * hinge(0.0, margin["delta_tan_delta"]),
        "Tang δ (h)": (
            0.5503026270 * margin["tang_delta_h"]
            - 0.0217847299 * hinge(-1.0, margin["tang_delta_h"])
            - 0.0150712128 * hinge(0.0, margin["tang_delta_h"])
        ),
        "IP": 0.2327062135 * margin["ip"],
        "H": 0.0,
    }


def d20_contributions(row: pd.Series) -> dict[str, float]:
    margin = margins(row, log_base=20.0)
    c = log20_coefficient
    t = log20_threshold
    return {
        "H": (
            c(-2.91109386) * hinge(t(0.0), margin["h"])
            + c(-2.90494819) * hinge(t(-0.552841969), margin["h"])
            + c(-1.07687847) * hinge(t(-0.330993219), margin["h"])
            + c(0.19988613) * margin["h"]
        ),
        "Pi1/Vn": c(-3.64695459) * margin["pi1_vn"] + c(-1.48543788) * hinge(t(-0.187673132), margin["pi1_vn"]),
        "IP": c(1.32150251) * margin["ip"] + c(0.26759780) * hinge(t(0.0), margin["ip"]),
        "Tang δ (h)": c(0.67088590) * margin["tang_delta_h"] + c(0.16242290) * hinge(t(-1.0), margin["tang_delta_h"]),
        "PD": c(-0.50338589) * margin["pd"],
        "ΔTan δ": c(0.47363259) * margin["delta_tan_delta"] + c(-0.23319941) * hinge(t(-0.602059991), margin["delta_tan_delta"]),
        "Tan δ": c(0.18593911) * hinge(t(-0.176091259), margin["tan_delta"]) + c(0.07398838) * hinge(t(0.0), margin["tan_delta"]),
        "ΔI": c(-0.02969294) * margin["delta_i"],
    }


def predict_row(row: pd.Series, target: str) -> float:
    args = [row[column] for column in FEATURE_COLUMNS]
    if target == "d10":
        return float(calcular_d10(*args))
    if target == "d20":
        return float(calcular_d20(*args))
    if target == "gei":
        return float(calcular_gei(*args))
    raise ValueError(target)


def metric_dict(errors: pd.Series | np.ndarray) -> dict[str, float]:
    values = np.asarray(errors, dtype=float)
    absolute = np.abs(values)
    return {
        "MAE": float(np.mean(absolute)),
        "RMSE": float(np.sqrt(np.mean(values**2))),
        "Mediana abs": float(np.median(absolute)),
        "P90 abs": float(np.quantile(absolute, 0.90)),
        "Max abs": float(np.max(absolute)),
    }


def contribution_table(frame: pd.DataFrame, contribution_fn) -> pd.DataFrame:
    contributions = pd.DataFrame([contribution_fn(row) for _, row in frame.iterrows()])
    mean_abs = contributions.abs().mean().sort_values(ascending=False)
    percent = mean_abs / mean_abs.sum() * 100.0
    return pd.DataFrame(
        {
            "Peso estrutural": percent,
            "Contrib abs media": mean_abs,
            "Contrib media assinada": contributions.mean().reindex(mean_abs.index),
        }
    )


def worsened_frame(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    changed = frame.copy()
    factor = 0.9 if column in HIGHER_IS_BETTER else 1.1
    changed[column] = changed[column] * factor
    changed[column] = changed[column].clip(lower=0.001)
    return changed


def sensitivity_10_percent(frame: pd.DataFrame, target: str) -> pd.Series:
    base = frame.apply(lambda row: predict_row(row, target), axis=1).to_numpy(dtype=float)
    results = {}
    for column in FEATURE_COLUMNS:
        changed = worsened_frame(frame, column)
        changed_prediction = changed.apply(lambda row: predict_row(row, target), axis=1).to_numpy(dtype=float)
        if target == "gei":
            results[column] = float(np.mean(changed_prediction - base))
        else:
            results[column] = float(np.mean(base - changed_prediction))
    return pd.Series(results).sort_values(key=lambda series: series.abs(), ascending=False)


def permutation_importance(frame: pd.DataFrame, target_column: str, prediction_column: str, target: str, repeats: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    baseline_mae = float(np.mean(np.abs(frame[prediction_column] - frame[target_column])))
    rows = []
    for column in FEATURE_COLUMNS:
        increases = []
        for _ in range(repeats):
            changed = frame.copy()
            changed[column] = rng.permutation(changed[column].to_numpy())
            changed_prediction = changed.apply(lambda row: predict_row(row, target), axis=1).to_numpy(dtype=float)
            changed_mae = float(np.mean(np.abs(changed_prediction - changed[target_column].to_numpy(dtype=float))))
            increases.append(max(0.0, changed_mae - baseline_mae))
        rows.append({"Input": column, "Aumento MAE": float(np.mean(increases))})
    result = pd.DataFrame(rows).sort_values("Aumento MAE", ascending=False)
    total = result["Aumento MAE"].sum()
    result["Peso permutacao"] = 0.0 if total <= 0 else result["Aumento MAE"] / total * 100.0
    return result


def spearman_table(frame: pd.DataFrame, target_column: str, prediction_column: str) -> pd.DataFrame:
    rows = []
    for column in FEATURE_COLUMNS:
        rows.append(
            {
                "Input": column,
                "Corr alvo": frame[column].corr(frame[target_column], method="spearman"),
                "Corr producao": frame[column].corr(frame[prediction_column], method="spearman"),
            }
        )
    result = pd.DataFrame(rows)
    return result.reindex(result["Corr alvo"].abs().sort_values(ascending=False).index)


def markdown_table(dataframe: pd.DataFrame, columns: list[str], formats: dict[str, str] | None = None) -> list[str]:
    formats = formats or {}
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---:" if column != columns[0] else "---" for column in columns) + " |"]
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


def top_errors(frame: pd.DataFrame, id_column: str, target_column: str, prediction_column: str, error_column: str, count: int = 8) -> pd.DataFrame:
    sample = frame.copy()
    sample["Erro abs"] = sample[error_column].abs()
    return sample.sort_values("Erro abs", ascending=False).head(count)[[id_column, target_column, prediction_column, error_column, "Erro abs"]]


def conflicting_duplicate_groups(frame: pd.DataFrame, id_column: str) -> tuple[set[int], pd.DataFrame]:
    rounded = frame.copy()
    for column in FEATURE_COLUMNS:
        rounded[column] = rounded[column].round(6)

    conflict_indexes: set[int] = set()
    groups = []
    for _, group in rounded.groupby(FEATURE_COLUMNS, dropna=False):
        if len(group) <= 1:
            continue
        d10_span = float(group[TARGET_D10].max() - group[TARGET_D10].min())
        d20_span = float(group[TARGET_D20].max() - group[TARGET_D20].min())
        gei_values = group[TARGET_GEI].dropna()
        gei_span = 0.0 if gei_values.empty else float(gei_values.max() - gei_values.min())
        if d10_span <= 0.05 and d20_span <= 0.05 and gei_span <= 1.0:
            continue

        conflict_indexes.update(group.index.tolist())
        sample_ids = ", ".join(group[id_column].astype(str).head(10).tolist())
        groups.append(
            {
                "Linhas": int(len(group)),
                "Amostras": sample_ids,
                "Faixa D10": f"{group[TARGET_D10].min():.2f} a {group[TARGET_D10].max():.2f}",
                "Faixa D20": f"{group[TARGET_D20].min():.2f} a {group[TARGET_D20].max():.2f}",
                "Faixa GEI": "--" if gei_values.empty else f"{gei_values.min():.0f} a {gei_values.max():.0f}",
            }
        )

    conflict_groups = pd.DataFrame(groups)
    if not conflict_groups.empty:
        conflict_groups = conflict_groups.sort_values("Linhas", ascending=False)
    return conflict_indexes, conflict_groups


def main() -> None:
    dataframe = load_daimer_dataframe(DATA_FILE)
    degree_rows = dataframe.dropna(subset=FEATURE_COLUMNS + [TARGET_D10, TARGET_D20]).copy().reset_index(drop=True)
    id_column = "NR_OS" if "NR_OS" in degree_rows.columns else degree_rows.columns[0]

    degree_rows["D10 producao"] = degree_rows.apply(lambda row: predict_row(row, "d10"), axis=1)
    degree_rows["D20 producao"] = degree_rows.apply(lambda row: predict_row(row, "d20"), axis=1)
    degree_rows["Erro D10"] = degree_rows["D10 producao"] - degree_rows[TARGET_D10]
    degree_rows["Erro D20"] = degree_rows["D20 producao"] - degree_rows[TARGET_D20]

    conflict_indexes, conflict_groups = conflicting_duplicate_groups(degree_rows, id_column)
    clean_degree_rows = degree_rows.drop(index=list(conflict_indexes)).reset_index(drop=True)

    gei_rows = degree_rows.dropna(subset=[TARGET_GEI]).copy().reset_index(drop=True)
    clean_gei_rows = clean_degree_rows.dropna(subset=[TARGET_GEI]).copy().reset_index(drop=True)
    gei_rows["GEI producao"] = gei_rows.apply(lambda row: predict_row(row, "gei"), axis=1)
    gei_rows["Erro GEI"] = gei_rows["GEI producao"] - gei_rows[TARGET_GEI]
    clean_gei_rows["GEI producao"] = clean_gei_rows.apply(lambda row: predict_row(row, "gei"), axis=1)
    clean_gei_rows["Erro GEI"] = clean_gei_rows["GEI producao"] - clean_gei_rows[TARGET_GEI]

    d10_contrib = contribution_table(clean_degree_rows, d10_contributions).reset_index(names="Input")
    d20_contrib = contribution_table(clean_degree_rows, d20_contributions).reset_index(names="Input")
    d10_sensitivity = sensitivity_10_percent(clean_degree_rows, "d10").reset_index()
    d20_sensitivity = sensitivity_10_percent(clean_degree_rows, "d20").reset_index()
    gei_sensitivity = sensitivity_10_percent(clean_gei_rows, "gei").reset_index()
    d10_sensitivity.columns = ["Input", "Queda media D10"]
    d20_sensitivity.columns = ["Input", "Impacto medio D20"]
    gei_sensitivity.columns = ["Input", "Aumento medio GEI"]

    d10_perm = permutation_importance(clean_degree_rows, TARGET_D10, "D10 producao", "d10")
    d20_perm = permutation_importance(clean_degree_rows, TARGET_D20, "D20 producao", "d20")
    gei_perm = permutation_importance(clean_gei_rows, TARGET_GEI, "GEI producao", "gei")

    metric_rows = pd.DataFrame(
        [
            {"Base": "Todos os graficos", "Saida": "D10", **metric_dict(degree_rows["Erro D10"])},
            {"Base": "Todos os graficos", "Saida": "D20", **metric_dict(degree_rows["Erro D20"])},
            {"Base": "Todos os graficos", "Saida": "GEI", **metric_dict(gei_rows["Erro GEI"])},
            {"Base": "Sem duplicados conflitantes", "Saida": "D10", **metric_dict(clean_degree_rows["Erro D10"])},
            {"Base": "Sem duplicados conflitantes", "Saida": "D20", **metric_dict(clean_degree_rows["Erro D20"])},
            {"Base": "Sem duplicados conflitantes", "Saida": "GEI", **metric_dict(clean_gei_rows["Erro GEI"])},
        ]
    )

    lines = [
        "# Analise conceitual e empirica dos pesos dos inputs",
        "",
        "## Leitura principal",
        "",
        "Nao existe um unico peso verdadeiro para cada input, porque as equacoes sao log-normalizadas, piecewise e os inputs estao correlacionados. Por isso, este relatorio separa tres leituras:",
        "",
        "- peso conceitual: papel fisico indicado pelos papers e pelo diagnostico de isolamento;",
        "- peso estrutural: tamanho medio da contribuicao de cada input dentro da equacao atual;",
        "- peso empirico: quanto o erro piora quando um input e embaralhado na planilha historica.",
        "",
        "## Base analisada",
        "",
        f"- Registros com D10/D20 validos: {len(degree_rows)}.",
        f"- Registros com GEI valido: {len(gei_rows)}.",
        "- Fonte: `scraping/Dados_Ensaios.xlsx`.",
        "",
        "## Integridade da planilha",
        "",
        f"Foram encontrados {len(conflict_indexes)} registros em {len(conflict_groups)} grupos de inputs duplicados com alvos diferentes. Esses registros foram mantidos nos graficos historicos porque fazem parte da planilha, mas foram removidos das tabelas de peso abaixo.",
        "",
    ]
    if not conflict_groups.empty:
        lines.extend(markdown_table(conflict_groups.head(8), ["Linhas", "Amostras", "Faixa D10", "Faixa D20", "Faixa GEI"]))
        lines.append("")
    lines.extend(
        [
        "## Erro dos graficos historicos",
        "",
        ]
    )
    lines.extend(markdown_table(metric_rows, ["Base", "Saida", "MAE", "RMSE", "Mediana abs", "P90 abs", "Max abs"], {"MAE": "{:.3f}", "RMSE": "{:.3f}", "Mediana abs": "{:.3f}", "P90 abs": "{:.3f}", "Max abs": "{:.3f}"}))
    lines.extend(
        [
            "",
            "Observacao importante: na aba historica do HTML, o oraculo so difere da producao quando a entrada coincide com um anchor cadastrado. Para a maior parte da planilha, a linha do oraculo fica igual a linha da producao; portanto, esses graficos ainda nao mostram um oraculo ML completo.",
            "",
            "Os pesos das secoes seguintes usam a base sem duplicados conflitantes. Isso evita atribuir peso fisico a linhas em que os mesmos inputs apontam para resultados diferentes.",
            "",
            "## D10 - degradacao/deterioracao",
            "",
            "Pelos papers, D10 deve ser lido como uma composicao de deterioracao eletrica do isolamento: descarga parcial, perdas dielectricas, polarizacao/resistencia e nao-linearidade de corrente. A equacao atual reflete isso: `Pi1/Vn`, familia `tan delta`, `PD`, `DeltaI` e `DeltaTan delta` carregam quase todo o peso; `H` praticamente nao participa de D10.",
            "",
            "### Peso estrutural na equacao D10",
            "",
        ]
    )
    lines.extend(markdown_table(d10_contrib, ["Input", "Peso estrutural", "Contrib abs media", "Contrib media assinada"], {"Peso estrutural": "{:.2f}%", "Contrib abs media": "{:.3f}", "Contrib media assinada": "{:.3f}"}))
    lines.extend(["", "### Sensibilidade D10: piora fisica de 10%", ""])
    lines.extend(markdown_table(d10_sensitivity, ["Input", "Queda media D10"], {"Queda media D10": "{:.4f}"}))
    lines.extend(["", "### Peso empirico D10 por permutacao", ""])
    lines.extend(markdown_table(d10_perm, ["Input", "Peso permutacao", "Aumento MAE"], {"Peso permutacao": "{:.2f}%", "Aumento MAE": "{:.4f}"}))

    lines.extend(
        [
            "",
            "## D20 - contaminacao",
            "",
            "Nos papers, contaminacao aparece acoplada a umidade, carga espacial, perdas, descarga e condicoes de superficie/ambiente. A planilha nao tem uma medida direta de umidade ou contaminante; por isso `H` funciona como proxy forte na equacao atual. Esta e a maior diferenca conceitual contra D10: D20 e menos uma leitura pura de descarga parcial e mais uma coordenada de contaminacao/superficie/historico eletrico.",
            "",
            "### Peso estrutural na equacao D20",
            "",
        ]
    )
    lines.extend(markdown_table(d20_contrib, ["Input", "Peso estrutural", "Contrib abs media", "Contrib media assinada"], {"Peso estrutural": "{:.2f}%", "Contrib abs media": "{:.3f}", "Contrib media assinada": "{:.3f}"}))
    lines.extend(["", "### Sensibilidade D20: piora fisica de 10%", "", "Valor positivo significa que D20 caiu quando o input piorou; valor negativo significa que D20 subiu. Sinais negativos aparecem porque D20 e uma coordenada de contaminacao, nao um peso causal linear isolado.", ""])
    lines.extend(markdown_table(d20_sensitivity, ["Input", "Impacto medio D20"], {"Impacto medio D20": "{:.4f}"}))
    lines.extend(["", "### Peso empirico D20 por permutacao", ""])
    lines.extend(markdown_table(d20_perm, ["Input", "Peso permutacao", "Aumento MAE"], {"Peso permutacao": "{:.2f}%", "Aumento MAE": "{:.4f}"}))

    lines.extend(
        [
            "",
            "## GEI e limite dos graficos atuais",
            "",
            "GEI continua sendo o alvo menos identificavel pelas 8 variaveis. Os papers reforcam que envelhecimento depende de tempo de operacao, ambiente, classe de isolamento, historico termico e conservacao. Por isso a equacao condicional acerta a tendencia, mas nao deve ser vendida como idade real sem variaveis historicas.",
            "",
            "### Sensibilidade GEI: piora fisica de 10%",
            "",
        ]
    )
    lines.extend(markdown_table(gei_sensitivity, ["Input", "Aumento medio GEI"], {"Aumento medio GEI": "{:.4f}"}))
    lines.extend(["", "### Peso empirico GEI por permutacao", ""])
    lines.extend(markdown_table(gei_perm, ["Input", "Peso permutacao", "Aumento MAE"], {"Peso permutacao": "{:.2f}%", "Aumento MAE": "{:.4f}"}))

    lines.extend(["", "## Maiores residuos vistos nos graficos", "", "### D10", ""])
    lines.extend(markdown_table(top_errors(degree_rows, id_column, TARGET_D10, "D10 producao", "Erro D10"), [id_column, TARGET_D10, "D10 producao", "Erro D10", "Erro abs"], {TARGET_D10: "{:.2f}", "D10 producao": "{:.2f}", "Erro D10": "{:.2f}", "Erro abs": "{:.2f}"}))
    lines.extend(["", "### D20", ""])
    lines.extend(markdown_table(top_errors(degree_rows, id_column, TARGET_D20, "D20 producao", "Erro D20"), [id_column, TARGET_D20, "D20 producao", "Erro D20", "Erro abs"], {TARGET_D20: "{:.2f}", "D20 producao": "{:.2f}", "Erro D20": "{:.2f}", "Erro abs": "{:.2f}"}))
    lines.extend(["", "### GEI", ""])
    lines.extend(markdown_table(top_errors(gei_rows, id_column, TARGET_GEI, "GEI producao", "Erro GEI"), [id_column, TARGET_GEI, "GEI producao", "Erro GEI", "Erro abs"], {TARGET_GEI: "{:.0f}", "GEI producao": "{:.0f}", "Erro GEI": "{:.0f}", "Erro abs": "{:.0f}"}))

    lines.extend(
        [
            "",
            "## Conclusao operacional",
            "",
            "- Para degradacao/D10, o conjunto mais defensavel e: `Pi1/Vn` + familia `tan delta` + `PD` + `DeltaI/DeltaTan delta`. Isso combina bem com a literatura de deterioracao dieletrica e descarga parcial.",
            "- Para contaminacao/D20, `H` e o eixo dominante na equacao atual; `IP`, `Pi1/Vn`, `PD` e `Tang delta (h)` entram como moduladores. Conceitualmente, isso deve ser tratado como proxy de contaminacao/umidade/superficie, nao como prova fisica direta de contaminante.",
            "- Os graficos de historico sao bons para ver erro global e outliers, mas nao bastam para revelar pesos. Para peso verdadeiro, o projeto precisa mostrar graficos de sensibilidade, barras de importancia e residuos por input.",
            "- O oraculo da aba historica precisa ser renomeado ou trocado por predicoes reais do bundle ML; do jeito atual, ele quase sempre sobrepoe a producao.",
            "",
        ]
    )

    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"Relatorio gerado: {REPORT_FILE}")


if __name__ == "__main__":
    main()