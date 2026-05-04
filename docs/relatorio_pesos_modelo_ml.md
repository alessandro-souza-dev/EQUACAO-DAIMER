# Pesos aprendidos por input no modelo ML

## Metodo

Os pesos abaixo foram calculados por importancia por permutacao nos 8 inputs originais. O treino embaralha um input por vez, mede quanto o MAE piora no modelo `production` e normaliza esse impacto para 100% dentro de cada saida.

Esse metodo mede influencia preditiva aprendida pelo modelo, nao coeficiente fisico linear. Em modelos nao lineares, um input pode ter peso alto por efeito direto, interacao com outros inputs ou por atuar em regioes de threshold.

## Peso global medio

| Input | Peso medio |
| --- | ---: |
| `PD` | 21,32% |
| `Tang δ (h)` | 13,48% |
| `ΔTan δ` | 12,82% |
| `ΔI` | 12,67% |
| `H` | 12,06% |
| `Pi1/Vn` | 9,98% |
| `Tan δ` | 8,95% |
| `IP` | 8,72% |

## D10

| Input | Peso | Aumento medio do MAE | Correlação com previsão |
| --- | ---: | ---: | ---: |
| `PD` | 25,66% | 0.437925 | -0.3248 |
| `ΔI` | 16,84% | 0.287394 | -0.7023 |
| `ΔTan δ` | 15,43% | 0.263331 | -0.6215 |
| `Tang δ (h)` | 14,55% | 0.248329 | -0.4552 |
| `Pi1/Vn` | 13,04% | 0.222484 | 0.4168 |
| `Tan δ` | 10,05% | 0.171435 | -0.6432 |
| `IP` | 3,46% | 0.059050 | 0.2872 |
| `H` | 0,96% | 0.016382 | 0.0089 |

## D20

| Input | Peso | Aumento medio do MAE | Correlação com previsão |
| --- | ---: | ---: | ---: |
| `H` | 30,23% | 0.624648 | -0.7495 |
| `PD` | 17,98% | 0.371504 | 0.1474 |
| `Tang δ (h)` | 16,14% | 0.333542 | -0.2838 |
| `IP` | 14,50% | 0.299539 | 0.3629 |
| `ΔTan δ` | 10,22% | 0.211153 | -0.1517 |
| `Pi1/Vn` | 9,99% | 0.206336 | -0.2222 |
| `ΔI` | 0,71% | 0.014662 | -0.0449 |
| `Tan δ` | 0,23% | 0.004752 | -0.3700 |

## GEI

| Input | Peso | Aumento medio do MAE | Correlação com previsão |
| --- | ---: | ---: | ---: |
| `ΔI` | 20,45% | 1.761037 | 0.6859 |
| `PD` | 20,33% | 1.750221 | 0.2776 |
| `Tan δ` | 16,57% | 1.426512 | 0.6581 |
| `ΔTan δ` | 12,80% | 1.102222 | 0.5879 |
| `Tang δ (h)` | 9,74% | 0.838628 | 0.5036 |
| `IP` | 8,20% | 0.705745 | -0.2674 |
| `Pi1/Vn` | 6,91% | 0.594855 | -0.3794 |
| `H` | 5,00% | 0.430526 | 0.0427 |

## Leitura rapida

- `Peso`: porcentagem da importancia relativa dentro da saida.
- `Aumento medio do MAE`: quanto o erro aumenta quando aquele input e embaralhado.
- `Correlação com previsão`: sinal aproximado da relacao entre o input bruto e a previsao do modelo; valores positivos tendem a aumentar a saida, negativos tendem a reduzir, mas interacoes e thresholds podem inverter localmente.
