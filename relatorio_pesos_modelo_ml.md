# Pesos aprendidos por input no modelo ML

## Metodo

Os pesos abaixo foram calculados por importancia por permutacao nos 8 inputs originais. O treino embaralha um input por vez, mede quanto o MAE piora no modelo `production` e normaliza esse impacto para 100% dentro de cada saida.

Esse metodo mede influencia preditiva aprendida pelo modelo, nao coeficiente fisico linear. Em modelos nao lineares, um input pode ter peso alto por efeito direto, interacao com outros inputs ou por atuar em regioes de threshold.

## Peso global medio

| Input | Peso medio |
| --- | ---: |
| `PD` | 23,03% |
| `ΔTan δ` | 13,53% |
| `Tang δ (h)` | 13,08% |
| `Pi1/Vn` | 11,48% |
| `H` | 11,42% |
| `Tan δ` | 9,56% |
| `ΔI` | 9,52% |
| `IP` | 8,39% |

## D10

| Input | Peso | Aumento medio do MAE | Correlação com previsão |
| --- | ---: | ---: | ---: |
| `PD` | 27,03% | 0.430542 | -0.3707 |
| `ΔTan δ` | 16,57% | 0.263912 | -0.4923 |
| `Pi1/Vn` | 14,57% | 0.232133 | 0.4796 |
| `ΔI` | 14,00% | 0.223053 | -0.6196 |
| `Tang δ (h)` | 13,28% | 0.211443 | -0.4111 |
| `Tan δ` | 9,92% | 0.157994 | -0.5523 |
| `IP` | 2,53% | 0.040317 | 0.1808 |
| `H` | 2,10% | 0.033381 | -0.0159 |

## D20

| Input | Peso | Aumento medio do MAE | Correlação com previsão |
| --- | ---: | ---: | ---: |
| `H` | 27,26% | 0.514350 | -0.7068 |
| `PD` | 16,32% | 0.307902 | 0.1623 |
| `IP` | 15,51% | 0.292640 | 0.3835 |
| `Tang δ (h)` | 14,83% | 0.279824 | -0.2699 |
| `ΔTan δ` | 10,24% | 0.193145 | -0.1282 |
| `Pi1/Vn` | 8,33% | 0.157053 | -0.2955 |
| `Tan δ` | 4,19% | 0.078961 | -0.3360 |
| `ΔI` | 3,32% | 0.062625 | -0.0100 |

## GEI

| Input | Peso | Aumento medio do MAE | Correlação com previsão |
| --- | ---: | ---: | ---: |
| `PD` | 25,73% | 2.035097 | 0.3354 |
| `Tan δ` | 14,57% | 1.152373 | 0.5843 |
| `ΔTan δ` | 13,79% | 1.090605 | 0.4921 |
| `Pi1/Vn` | 11,53% | 0.911673 | -0.4203 |
| `ΔI` | 11,23% | 0.887864 | 0.6110 |
| `Tang δ (h)` | 11,13% | 0.880214 | 0.4610 |
| `IP` | 7,14% | 0.564762 | -0.1745 |
| `H` | 4,89% | 0.386486 | 0.0670 |

## Leitura rapida

- `Peso`: porcentagem da importancia relativa dentro da saida.
- `Aumento medio do MAE`: quanto o erro aumenta quando aquele input e embaralhado.
- `Correlação com previsão`: sinal aproximado da relacao entre o input bruto e a previsao do modelo; valores positivos tendem a aumentar a saida, negativos tendem a reduzir, mas interacoes e thresholds podem inverter localmente.
