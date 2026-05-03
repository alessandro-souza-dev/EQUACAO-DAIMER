import pandas as pd
import sys
sys.path.insert(0, r'c:\Git_Repo\equacao daimer')
from daimer_ml import load_model_bundle, predict_from_bundle, make_input_frame, FEATURE_COLUMNS

# Carregar bundle uma unica vez
bundle = load_model_bundle()
print(f'[bundle] Carregado OK. Modelos: {list(bundle["production_models"].keys())}')

df = pd.read_excel(r'c:\Git_Repo\equacao daimer\scraping\Dados_Ensaios.xlsx')
print(f'Total de registos: {len(df)}')

# Normalizar virgulas para pontos nas colunas de features
for col in FEATURE_COLUMNS:
    if col in df.columns:
        df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Filtrar linhas que tenham todos os 8 parametros preenchidos
df_validos = df.dropna(subset=FEATURE_COLUMNS)
print(f'Registos com todos os parametros preenchidos: {len(df_validos)} (de {len(df)})')

resultados = []
for _, row in df_validos.iterrows():
    try:
        input_data = make_input_frame(
            ip=row['IP'],
            delta_i=row['ΔI'],
            pi1_vn=row['Pi1/Vn'],
            pd_value=row['PD'],
            delta_tan_delta=row['ΔTan δ'],
            tang_delta_h=row['Tang δ (h)'],
            tan_delta=row['Tan δ'],
            h=row['H'],
        )
        res = predict_from_bundle(bundle, input_data)
        resultados.append({
            'NR_OS': row['NR_OS'],
            'D10_ML': res['d10'],
            'D20_ML': res['d20'],
            'Global_ML': res['avaliacao_global'],
            'GEI_ML': res['gei'],
            'D10_Real': row.get('Grau de Deterioração (D10)'),
            'D20_Real': row.get('Grau de Contaminação (D20)'),
            'Global_Real': row.get('Avaliação Global'),
            'GEI_Real': row.get('Grau de Envelhecimento GEI (Anos)'),
        })
    except Exception as e:
        nr = row['NR_OS']
        print(f'  [erro] {nr}: {e}')

df_res = pd.DataFrame(resultados)
out = r'c:\Git_Repo\equacao daimer\scraping\resultados_ml.xlsx'
df_res.to_excel(out, index=False)
print(f'\nGuardado em {out}')
print(df_res.to_string())
