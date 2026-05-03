# Pesos aprendidos por input no modelo ML

## Metodo

Os pesos abaixo foram calculados por importancia por permutacao nos 8 inputs originais. O treino embaralha um input por vez, mede quanto o MAE piora no modelo `production` e normaliza esse impacto para 100% dentro de cada saida.

Esse metodo mede influencia preditiva aprendida pelo modelo, nao coeficiente fisico linear. Em modelos nao lineares, um input pode ter peso alto por efeito direto, interacao com outros inputs ou por atuar em regioes de threshold.

## Peso global medio

| Input | Peso medio |
| --- | ---: |
| `PD` | 21,10% |
| `Tang δ (h)` | 13,70% |
| `ΔTan δ` | 12,86% |
| `ΔI` | 12,32% |
| `H` | 12,29% |
| `Pi1/Vn` | 10,28% |
| `Tan δ` | 8,74% |
| `IP` | 8,72% |

## D10

| Input | Peso | Aumento medio do MAE | Correlação com previsão |
| --- | ---: | ---: | ---: |
| `PD` | 25,41% | 0.432674 | -0.3933 |
| `ΔI` | 15,68% | 0.267055 | -0.7035 |
| `ΔTan δ` | 15,46% | 0.263325 | -0.6227 |
| `Tang δ (h)` | 15,24% | 0.259445 | -0.4576 |
| `Pi1/Vn` | 13,63% | 0.232031 | 0.4180 |
| `Tan δ` | 10,00% | 0.170245 | -0.6443 |
| `IP` | 3,48% | 0.059326 | 0.2879 |
| `H` | 1,10% | 0.018764 | 0.0102 |

## D20

| Input | Peso | Aumento medio do MAE | Correlação com previsão |
| --- | ---: | ---: | ---: |
| `H` | 30,55% | 0.625198 | -0.7508 |
| `PD` | 17,68% | 0.361813 | 0.1649 |
| `Tang δ (h)` | 15,84% | 0.324104 | -0.2833 |
| `IP` | 14,45% | 0.295685 | 0.3635 |
| `ΔTan δ` | 10,64% | 0.217829 | -0.1515 |
| `Pi1/Vn` | 9,87% | 0.201952 | -0.2227 |
| `ΔI` | 0,68% | 0.013935 | -0.0445 |
| `Tan δ` | 0,29% | 0.005955 | -0.3693 |

## GEI

| Input | Peso | Aumento medio do MAE | Correlação com previsão |
| --- | ---: | ---: | ---: |
| `ΔI` | 20,59% | 1.755249 | 0.6874 |
| `PD` | 20,20% | 1.721726 | 0.3551 |
| `Tan δ` | 15,94% | 1.358435 | 0.6567 |
| `ΔTan δ` | 12,47% | 1.063397 | 0.5896 |
| `Tang δ (h)` | 10,01% | 0.853556 | 0.5063 |
| `IP` | 8,22% | 0.700735 | -0.2674 |
| `Pi1/Vn` | 7,35% | 0.626335 | -0.3817 |
| `H` | 5,22% | 0.445418 | 0.0428 |

## Leitura rapida

- `Peso`: porcentagem da importancia relativa dentro da saida.
- `Aumento medio do MAE`: quanto o erro aumenta quando aquele input e embaralhado.
- `Correlação com previsão`: sinal aproximado da relacao entre o input bruto e a previsao do modelo; valores positivos tendem a aumentar a saida, negativos tendem a reduzir, mas interacoes e thresholds podem inverter localmente.
