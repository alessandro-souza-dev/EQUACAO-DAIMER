"""
ESTUDO: LOG BASE 20 PARA D20 vs LOG BASE 10 (ATUAL)

Hipotese: o DAIMER pode ter projetado D20 com log base 20 (escala de contaminacao
0-20), enquanto D10 usa log base 10. Reajustamos a equacao D20 em ambos os espacos
e comparamos MAE / RMSE / R2 no conjunto de dados real.

Como rodar:
    python estudo_log20_d20.py
"""
from __future__ import annotations

from math import log10
from pathlib import Path

import numpy as np
import pandas as pd

from daimer_ml import load_daimer_dataframe, FEATURE_COLUMNS, TARGET_D20
from equacoes_daimer import calcular_d20

# Coluna D20 no Excel: D20 e o grau de contaminacao.
TARGET_D20_COL = TARGET_D20

# ---------------------------------------------------------------------------
# Configuracoes
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "scraping" / "Dados_Ensaios.xlsx"

LOG20_FACTOR = log10(20)  # ≈ 1.30103  — divisor para converter log10 em log20

MIN_POSITIVE = 1e-6
MIN_H = 0.01

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

# Thresholds tecnicos (valores reais das variaveis)
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


# ---------------------------------------------------------------------------
# Funcoes de margem
# ---------------------------------------------------------------------------

def _margin_log10(col: str, values: np.ndarray) -> np.ndarray:
    floor = MIN_H if col == "H" else MIN_POSITIVE
    v = np.maximum(values, floor)
    ref = REFERENCES[col]
    if col in HIGHER_IS_BETTER:
        return np.log10(v / ref)
    return np.log10(ref / v)


def _margin_log20(col: str, values: np.ndarray) -> np.ndarray:
    """log base 20: log10(x) / log10(20)"""
    return _margin_log10(col, values) / LOG20_FACTOR


def _hinge(threshold: float, margin: np.ndarray) -> np.ndarray:
    return np.maximum(0.0, threshold - margin)


def _threshold_margins_for_col(col: str, log_fn) -> list[float]:
    """Converte thresholds tecnicos para margens no espaco logaritmico dado."""
    ref = REFERENCES[col]
    margins = []
    for thr in THRESHOLDS[col]:
        dummy = np.array([thr], dtype=float)
        margins.append(log_fn(col, dummy)[0])
    return sorted(set(margins), reverse=True)


# ---------------------------------------------------------------------------
# Construcao da matriz de features piecewise para D20
# (mesma estrutura da equacao atual)
# ---------------------------------------------------------------------------

# Ordem das colunas da equacao D20 atual (inferida de equacoes_daimer.py)
D20_MARGIN_COLS = ["Pi1/Vn", "H", "H", "Pi1/Vn", "IP", "H",
                   "Tang δ (h)", "PD", "ΔTan δ", "IP",
                   "ΔTan δ", "H", "Tan δ", "Tang δ (h)", "Tan δ", "ΔI"]

D20_LOG10_THRESHOLDS = {
    "pi1_vn": [-0.187673132],
    "h": [0.0, -0.552841969, -0.330993219],
    "ip": [0.0],
    "delta_tan_delta": [-0.602059991],
    "tang_delta_h": [-1.0],
    "tan_delta": [-0.176091259, 0.0],
    "delta_i": [],
    "pd": [],
}

COL_MAP = {
    "IP": "ip", "ΔI": "delta_i", "Pi1/Vn": "pi1_vn", "PD": "pd",
    "ΔTan δ": "delta_tan_delta", "Tang δ (h)": "tang_delta_h",
    "Tan δ": "tan_delta", "H": "h",
}


def build_d20_features(df: pd.DataFrame, use_log20: bool) -> np.ndarray:
    """
    Constroi a matriz X de features para D20 (intercepto + margens + hinges)
    usando o espaco logaritmico indicado.

    Os thresholds de hinge sao os mesmos PONTOS FISICOS de ambos os casos;
    so a escala em que sao expressos muda.
    """
    log_fn = _margin_log20 if use_log20 else _margin_log10

    cols_needed = ["IP", "ΔI", "Pi1/Vn", "PD", "ΔTan δ", "Tang δ (h)", "Tan δ", "H"]
    margins = {}
    for col in cols_needed:
        margins[col] = log_fn(col, df[col].to_numpy(dtype=float))

    # Intercepto
    rows = len(df)
    X = [np.ones(rows)]

    # Termos lineares (ordem da equacao D20)
    for col in cols_needed:
        X.append(margins[col])

    # Hinges — thresholds tecnicos convertidos para o espaco correto
    for col in cols_needed:
        thr_list = _threshold_margins_for_col(col, log_fn)
        for thr in thr_list:
            X.append(_hinge(thr, margins[col]))

    return np.column_stack(X)


# ---------------------------------------------------------------------------
# Reajuste linear (minimos quadrados)
# ---------------------------------------------------------------------------

def refit_d20(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    return coef


def predict_d20(X: np.ndarray, coef: np.ndarray) -> np.ndarray:
    return X @ coef


def metrics(y_true: np.ndarray, y_pred: np.ndarray, label: str) -> dict:
    residuals = y_true - y_pred
    mae = float(np.mean(np.abs(residuals)))
    rmse = float(np.sqrt(np.mean(residuals**2)))
    ss_res = float(np.sum(residuals**2))
    ss_tot = float(np.sum((y_true - y_true.mean())**2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    max_err = float(np.max(np.abs(residuals)))
    med_err = float(np.median(np.abs(residuals)))
    print(f"\n{'='*55}")
    print(f"  {label}")
    print(f"{'='*55}")
    print(f"  MAE    : {mae:.6f}")
    print(f"  Mediana: {med_err:.6f}")
    print(f"  RMSE   : {rmse:.6f}")
    print(f"  R²     : {r2:.8f}")
    print(f"  Max err: {max_err:.6f}")
    return {"label": label, "MAE": mae, "Mediana": med_err, "RMSE": rmse, "R2": r2, "MaxErr": max_err}


# ---------------------------------------------------------------------------
# Analise de coeficientes
# ---------------------------------------------------------------------------

def print_coef_comparison(coef_log10: np.ndarray, coef_log20: np.ndarray, feature_names: list[str]) -> None:
    print(f"\n{'='*70}")
    print(f"  Comparacao de coeficientes (log10 vs log20 reajustados)")
    print(f"{'='*70}")
    print(f"{'Feature':<35} {'log10':>12} {'log20':>12} {'ratio':>10}")
    print(f"{'-'*70}")
    for name, c10, c20 in zip(feature_names, coef_log10, coef_log20):
        ratio = c10 / c20 if abs(c20) > 1e-12 else float("inf")
        print(f"  {name:<33} {c10:>12.6f} {c20:>12.6f} {ratio:>10.4f}")


def get_feature_names(df: pd.DataFrame, log_fn) -> list[str]:
    cols_needed = ["IP", "ΔI", "Pi1/Vn", "PD", "ΔTan δ", "Tang δ (h)", "Tan δ", "H"]
    names = ["intercept"]
    for col in cols_needed:
        names.append(f"m_{COL_MAP[col]}")
    for col in cols_needed:
        thr_list = _threshold_margins_for_col(col, log_fn)
        for thr in thr_list:
            names.append(f"hinge_{COL_MAP[col]}_{thr:.6f}")
    return names


# ---------------------------------------------------------------------------
# Analise dos coeficientes log20 em termos de log10 (conversao inversa)
# ---------------------------------------------------------------------------

def print_coef_log20_as_log10(coef_log20: np.ndarray, feature_names_log20: list[str]) -> None:
    """
    Mostra os coeficientes do modelo log20 reexpressos na escala log10.
    Um coeficiente log20 'c' equivale a 'c / log10(20)' em unidades de log10.
    """
    print(f"\n{'='*60}")
    print("  Coeficientes log20 convertidos para escala log10")
    print(f"{'='*60}")
    print(f"  (divide por log10(20) = {LOG20_FACTOR:.6f})")
    print(f"{'Feature':<35} {'log20 nativo':>14} {'em log10':>14}")
    print(f"{'-'*60}")
    for name, c20 in zip(feature_names_log20, coef_log20):
        if name == "intercept":
            print(f"  {name:<33} {c20:>14.8f} {'(igual)':>14}")
        else:
            c_in_log10 = c20 / LOG20_FACTOR
            print(f"  {name:<33} {c20:>14.8f} {c_in_log10:>14.8f}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if not DATA_FILE.exists():
        print(f"ERRO: arquivo de dados nao encontrado em {DATA_FILE}")
        return

    print(f"Carregando dados de: {DATA_FILE}")
    df = load_daimer_dataframe(DATA_FILE)
    mask = df[TARGET_D20_COL].notna() & df[FEATURE_COLUMNS].notna().all(axis=1)
    df = df[mask].copy().reset_index(drop=True)
    print(f"Registros validos para D20: {len(df)}")

    from daimer_ml import numeric_series
    df[TARGET_D20_COL] = numeric_series(df[TARGET_D20_COL])
    y = df[TARGET_D20_COL].to_numpy(dtype=float)

    # -----------------------------------------------------------------------
    # 1. Equacao ATUAL (coeficientes fixos de equacoes_daimer.py)
    # -----------------------------------------------------------------------
    y_atual = np.array([
        calcular_d20(
            row["IP"], row["ΔI"], row["Pi1/Vn"], row["PD"],
            row["ΔTan δ"], row["Tang δ (h)"], row["Tan δ"], row["H"],
            arredondar=False,
        )
        for _, row in df.iterrows()
    ])
    m_atual = metrics(y, y_atual, "D20 ATUAL (equacao fixa, log20 equivalente)")

    # -----------------------------------------------------------------------
    # 2. Reajuste por minimos quadrados — espaco log10
    # -----------------------------------------------------------------------
    X10 = build_d20_features(df, use_log20=False)
    coef10 = refit_d20(X10, y)
    y_pred10 = predict_d20(X10, coef10)
    m_log10 = metrics(y, y_pred10, "D20 REAJUSTADO — espaco log10")

    # -----------------------------------------------------------------------
    # 3. Reajuste por minimos quadrados — espaco log20
    # -----------------------------------------------------------------------
    X20 = build_d20_features(df, use_log20=True)
    coef20 = refit_d20(X20, y)
    y_pred20 = predict_d20(X20, coef20)
    m_log20 = metrics(y, y_pred20, "D20 REAJUSTADO — espaco log20")

    # -----------------------------------------------------------------------
    # 4. Comparacao direta de metricas
    # -----------------------------------------------------------------------
    print(f"\n{'='*55}")
    print("  RESUMO COMPARATIVO")
    print(f"{'='*55}")
    header = f"  {'Metrica':<10} {'Atual':>12} {'Reaj log10':>12} {'Reaj log20':>12}"
    print(header)
    print(f"  {'-'*52}")
    for key in ["MAE", "RMSE", "R2", "MaxErr"]:
        print(f"  {key:<10} {m_atual[key]:>12.6f} {m_log10[key]:>12.6f} {m_log20[key]:>12.6f}")

    delta_mae = m_log10["MAE"] - m_log20["MAE"]
    delta_rmse = m_log10["RMSE"] - m_log20["RMSE"]
    print(f"\n  Delta MAE  (log10 - log20) = {delta_mae:+.8f}")
    print(f"  Delta RMSE (log10 - log20) = {delta_rmse:+.8f}")
    if abs(delta_mae) < 1e-9:
        print("\n  CONCLUSAO: os dois espacos logaritmicos dao resultados")
        print("  IDENTICOS para um modelo linear reajustado. A mudanca")
        print("  de base e uma transformacao linear, portanto o R2 e MAE")
        print("  sao invariantes — so os coeficientes numericos mudam.")
    elif delta_mae > 1e-6:
        print("\n  CONCLUSAO: log20 MELHORA o ajuste (MAE menor).")
    else:
        print("\n  CONCLUSAO: log10 se sai melhor ou equivalente.")

    # -----------------------------------------------------------------------
    # 5. Comparacao de coeficientes
    # -----------------------------------------------------------------------
    fn10 = get_feature_names(df, _margin_log10)
    fn20 = get_feature_names(df, _margin_log20)
    print_coef_comparison(coef10, coef20, fn10)

    # -----------------------------------------------------------------------
    # 6. Coeficientes log20 convertidos para unidade log10
    # -----------------------------------------------------------------------
    print_coef_log20_as_log10(coef20, fn20)

    # -----------------------------------------------------------------------
    # 7. Distribuicao dos residuos
    # -----------------------------------------------------------------------
    res10 = y - y_pred10
    res20 = y - y_pred20
    print(f"\n{'='*55}")
    print("  Distribuicao dos residuos (D20 reajustado)")
    print(f"{'='*55}")
    for pct in [10, 25, 50, 75, 90, 95, 99]:
        v10 = float(np.percentile(np.abs(res10), pct))
        v20 = float(np.percentile(np.abs(res20), pct))
        print(f"  p{pct:<3}: log10={v10:.6f}  log20={v20:.6f}  diff={v10-v20:+.8f}")

    # -----------------------------------------------------------------------
    # 8. Checagem com os casos ancora do PDF
    # -----------------------------------------------------------------------
    ANCHOR_CASES = [
        {"name": "PDF case", "inputs": [3.49, 0.74, 0.57, 8060.0, 0.361, 0.161, 1.468, 3.582], "d20_ref": 2.04},
        {"name": "Caso 2",   "inputs": [2.29, 1.31, 0.57, 21850.0, 1.152, 0.083, 2.45, 0.01],  "d20_ref": 2.37},
    ]
    print(f"\n{'='*55}")
    print("  Casos ancora (comparacao)")
    print(f"{'='*55}")
    for case in ANCHOR_CASES:
        ip, di, pi, pd_v, dtd, tdh, td, h = case["inputs"]
        row_df = pd.DataFrame([{
            "IP": ip, "ΔI": di, "Pi1/Vn": pi, "PD": pd_v,
            "ΔTan δ": dtd, "Tang δ (h)": tdh, "Tan δ": td, "H": h,
        }])
        x10 = build_d20_features(row_df, use_log20=False)
        x20 = build_d20_features(row_df, use_log20=True)
        pred10 = float(predict_d20(x10, coef10)[0])
        pred20 = float(predict_d20(x20, coef20)[0])
        d20_atual = calcular_d20(ip, di, pi, pd_v, dtd, tdh, td, h, arredondar=False)
        ref = case["d20_ref"]
        print(f"  {case['name']}: ref={ref:.2f}  atual={d20_atual:.4f}  reaj_log10={pred10:.4f}  reaj_log20={pred20:.4f}")


if __name__ == "__main__":
    main()
