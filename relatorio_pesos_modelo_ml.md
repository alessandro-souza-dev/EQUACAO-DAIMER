# Pesos aprendidos por input no modelo ML

## Metodo

Os pesos abaixo foram calculados por importancia por permutacao nos 8 inputs originais. O treino embaralha um input por vez, mede quanto o MAE piora no modelo `production` e normaliza esse impacto para 100% dentro de cada saida.

Esse metodo mede influencia preditiva aprendida pelo modelo, nao coeficiente fisico linear. Em modelos nao lineares, um input pode ter peso alto por efeito direto, interacao com outros inputs ou por atuar em regioes de threshold.

## Peso global medio

| Input | Peso medio |
| --- | ---: |
| `PD` | 22,97% |
| `Tang δ (h)` | 13,94% |
| `ΔTan δ` | 12,88% |
| `ΔI` | 12,25% |
| `H` | 11,13% |
| `Pi1/Vn` | 10,41% |
| `Tan δ` | 8,52% |
| `IP` | 7,90% |

## D10

| Input | Peso | Aumento medio do MAE | Correlação com previsão |
| --- | ---: | ---: | ---: |
| `PD` | 27,00% | 0,509337 | -0,4224 |
| `ΔTan δ` | 16,21% | 0,305778 | -0,6516 |
| `ΔI` | 16,12% | 0,304027 | -0,7162 |
| `Tang δ (h)` | 15,96% | 0,301028 | -0,4412 |
| `Pi1/Vn` | 13,52% | 0,255014 | 0,4663 |
| `Tan δ` | 7,66% | 0,144459 | -0,6034 |
| `IP` | 2,66% | 0,050231 | 0,2522 |
| `H` | 0,88% | 0,016680 | -0,0232 |

## D20

| Input | Peso | Aumento medio do MAE | Correlação com previsão |
| --- | ---: | ---: | ---: |
| `H` | 27,59% | 0,589075 | -0,7402 |
| `PD` | 16,91% | 0,360961 | 0,1550 |
| `Tang δ (h)` | 15,24% | 0,325384 | -0,2818 |
| `IP` | 14,23% | 0,303900 | 0,4148 |
| `ΔTan δ` | 9,97% | 0,212801 | -0,1683 |
| `Pi1/Vn` | 9,17% | 0,195780 | -0,2749 |
| `Tan δ` | 3,70% | 0,079081 | -0,3659 |
| `ΔI` | 3,18% | 0,067967 | -0,0480 |

## GEI

| Input | Peso | Aumento medio do MAE | Correlação com previsão |
| --- | ---: | ---: | ---: |
| `PD` | 25,00% | 2,345767 | 0,3986 |
| `ΔI` | 17,45% | 1,637642 | 0,6864 |
| `Tan δ` | 14,21% | 1,333317 | 0,6200 |
| `ΔTan δ` | 12,47% | 1,170719 | 0,6001 |
| `Tang δ (h)` | 10,61% | 0,995753 | 0,4796 |
| `Pi1/Vn` | 8,53% | 0,800728 | -0,4304 |
| `IP` | 6,81% | 0,638730 | -0,2415 |
| `H` | 4,92% | 0,461972 | 0,0564 |

## Leitura rapida

- `Peso`: porcentagem da importancia relativa dentro da saida.
- `Aumento medio do MAE`: quanto o erro aumenta quando aquele input e embaralhado.
- `Correlação com previsão`: sinal aproximado da relacao entre o input bruto e a previsao do modelo; valores positivos tendem a aumentar a saida, negativos tendem a reduzir, mas interacoes e thresholds podem inverter localmente.
