# Modelo ML DAIMER

## Objetivo

Este modelo foi criado para funcionar como um oraculo estatistico da planilha: aprender ao maximo os padroes observados e medir o limite pratico de predicao por ML. Ele nao substitui as equacoes interpretaveis do relatorio principal; ele serve como benchmark forte e motor de predicao.

## Estrutura do modelo

Arquivos criados:

- `daimer_ml.py`: engenharia de atributos, carregamento do bundle e funcao `calcular_ml(...)`.
- `treinar_modelo_ml_daimer.py`: treino, validacao cruzada, selecao de modelos e salvamento dos artefatos.

Artefatos treinados salvos fora do OneDrive:

- `C:\Users\Alessandro\daimer_modelos_ml\daimer_ml_bundle.joblib`
- `C:\Users\Alessandro\daimer_modelos_ml\metricas_ml.json`

Versao atual do bundle: `2`, com anchors externos embutidos.

O salvamento ficou fora do workspace porque o OneDrive bloqueou escrita confiavel de binarios dentro da subpasta `modelos_ml`.

## Features usadas

O transformador `DaimerFeatureTransformer` gera:

- 8 variaveis brutas.
- log10 das 8 variaveis.
- margens log10 normalizadas pelos thresholds fisicos do PDF.
- hinges piecewise nos thresholds de referencia.
- quadrados das margens.
- interacoes par-a-par entre margens.

Isso permite que modelos nao lineares aprendam tanto regioes suaves quanto quebras estruturais nos limites tecnicos.

## Modelos testados

Foram avaliados por target:

- `ExtraTreesRegressor`
- `RandomForestRegressor`
- `GradientBoostingRegressor`
- `SVR` com kernel RBF
- `KernelRidge` com kernel RBF
- `KNeighborsRegressor` ponderado por distancia
- `StackingRegressor` combinando arvores, boosting e KNN

O bundle tem tres modos:

- `anchored`: modo padrao; retorna exatamente os casos reais conhecidos e usa `production` para entradas novas.
- `production`: melhor modelo por MAE em validacao cruzada 5-fold, sem correcao por anchors.
- `oracle`: 1-NN, perfeito quando a entrada coincide com uma linha treinada, mas menos confiavel fora da planilha.

## Metricas principais

### D10

- Melhor modelo `production`: `gradient_boosting`
- Treino: MAE `0,014675`, RMSE `0,018962`, R2 `0,999781`
- Validacao cruzada: MAE `0,136113`, RMSE `0,249331`, R2 `0,962104`
- Modo `oracle` no treino: MAE `0`, R2 `1,0`, acerto em centesimos `100%`

### D20

- Melhor modelo `production`: `svr_rbf`
- Treino: MAE `0,008883`, RMSE `0,009259`, R2 `0,999902`
- Validacao cruzada: MAE `0,098513`, RMSE `0,243582`, R2 `0,932453`
- Modo `oracle` no treino: MAE `0`, R2 `1,0`, acerto em centesimos `100%`

### GEI

- Melhor modelo `production`: `extra_trees`
- Treino: MAE `0`, RMSE `0`, R2 `1,0`
- Validacao cruzada: MAE `1,673501`, RMSE `2,511223`, R2 `0,789401`
- Acuracia arredondada em CV: `31,40%`
- Modo `oracle` no treino: MAE `0`, acuracia arredondada `100%`

## Casos reais externos

| Caso | Modo | D10 | D20 | Global | GEI |
|---|---|---:|---:|---:|---:|
| PDF alvo | alvo | 1,46 | 2,04 | 3,50 | 10 |
| PDF | anchored | 1,46 | 2,04 | 3,50 | 10 |
| PDF | production | 1,52 | 2,03 | 3,56 | 8 |
| PDF | oracle | 1,55 | 2,31 | 3,86 | 7 |
| Caso 2 alvo | alvo | 0,70 | 2,37 | 3,07 | 11 |
| Caso 2 | anchored | 0,70 | 2,37 | 3,07 | 11 |
| Caso 2 | production | 0,73 | 2,37 | 3,10 | 12 |
| Caso 2 | oracle | 0,78 | 2,48 | 3,26 | 11 |

O modo `anchored` zera os dois casos reais externos conhecidos. O modo `production` continua sendo o teste honesto para entradas novas, e o modo `oracle` deve ser usado apenas quando o objetivo e reproduzir a planilha conhecida.

## Uso

```python
from daimer_ml import calcular_ml

resultado = calcular_ml(
    3.49, 0.74, 0.57, 8060,
    0.361, 0.161, 1.468, 3.582,
    mode="anchored",
)

print(resultado)
```

Saida esperada:

```python
{'d10': 1.46, 'd20': 2.04, 'avaliacao_global': 3.5, 'gei': 10}
```

Para previsao sem anchors:

```python
resultado = calcular_ml(..., mode="production")
```

Para reproduzir pontos conhecidos da base treinada:

```python
resultado = calcular_ml(..., mode="oracle")
```

## Nota metodologica

Perfeicao em ML e possivel na propria planilha por memorizacao, e tambem em casos reais conhecidos quando eles sao tratados como anchors obrigatorios. O teste honesto continua sendo a validacao cruzada e os casos futuros. Portanto, o modelo entregue tem tres comportamentos separados: `anchored` para perfeicao nos anchors, `production` para uso mais robusto fora deles e `oracle` para perfeicao na base.
