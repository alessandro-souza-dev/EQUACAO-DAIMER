# Analise conceitual e empirica dos pesos dos inputs

## Leitura principal

Nao existe um unico peso verdadeiro para cada input, porque as equacoes sao log-normalizadas, piecewise e os inputs estao correlacionados. Por isso, este relatorio separa tres leituras:

- peso conceitual: papel fisico indicado pelos papers e pelo diagnostico de isolamento;
- peso estrutural: tamanho medio da contribuicao de cada input dentro da equacao atual;
- peso empirico: quanto o erro piora quando um input e embaralhado na planilha historica.

## Base analisada

- Registros com D10/D20 validos: 638.
- Registros com GEI valido: 596.
- Fonte: `scraping/Dados_Ensaios.xlsx`.

## Integridade da planilha

Foram encontrados 109 registros em 3 grupos de inputs duplicados com alvos diferentes. Esses registros foram mantidos nos graficos historicos porque fazem parte da planilha, mas foram removidos das tabelas de peso abaixo.

| Linhas | Amostras | Faixa D10 | Faixa D20 | Faixa GEI |
| --- | ---: | ---: | ---: | ---: |
| 61 | 20616G, 20616G, 18307G, 21098G, 17736G, 21098AG, 17959G, 18402G, 17584G, 17474G | -0.88 a 4.35 | -1.61 a 3.45 | 3 a 25 |
| 34 | 21098AE, 21098AE, 20795E, 21192E, 20528E, 18402E, 17584E, 17474E, 17128E, 17041E | -1.52 a 4.69 | 0.59 a 3.70 | 5 a 32 |
| 14 | 16822B, 16822B, 16716B, 17028B, 16878B, 17041B, 16408B, 21761D, 21383D, 21764D | -1.66 a 2.35 | 0.23 a 3.48 | 5 a 29 |

## Erro dos graficos historicos

| Base | Saida | MAE | RMSE | Mediana abs | P90 abs | Max abs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Todos os graficos | D10 | 0,255 | 0,695 | 0,020 | 1,072 | 4,800 |
| Todos os graficos | D20 | 0,244 | 0,546 | 0,110 | 0,548 | 3,920 |
| Todos os graficos | GEI | 2,498 | 3,573 | 2,000 | 6,000 | 16,000 |
| Sem duplicados conflitantes | D10 | 0,024 | 0,033 | 0,020 | 0,050 | 0,150 |
| Sem duplicados conflitantes | D20 | 0,098 | 0,117 | 0,100 | 0,190 | 0,280 |
| Sem duplicados conflitantes | GEI | 1,992 | 2,710 | 2,000 | 4,000 | 12,000 |

Observacao importante: na aba historica do HTML, o oraculo so difere da producao quando a entrada coincide com um anchor cadastrado. Para a maior parte da planilha, a linha do oraculo fica igual a linha da producao; portanto, esses graficos ainda nao mostram um oraculo ML completo.

Os pesos das secoes seguintes usam a base sem duplicados conflitantes. Isso evita atribuir peso fisico a linhas em que os mesmos inputs apontam para resultados diferentes.

## D10 - degradacao/deterioracao

Pelos papers, D10 deve ser lido como uma composicao de deterioracao eletrica do isolamento: descarga parcial, perdas dielectricas, polarizacao/resistencia e nao-linearidade de corrente. A equacao atual reflete isso: `Pi1/Vn`, familia `tan delta`, `PD`, `DeltaI` e `DeltaTan delta` carregam quase todo o peso; `H` praticamente nao participa de D10.

### Peso estrutural na equacao D10

| Input | Peso estrutural | Contrib abs media | Contrib media assinada |
| --- | ---: | ---: | ---: |
| ΔI | 26,44% | 0,479 | 0,477 |
| PD | 24,17% | 0,438 | 0,252 |
| ΔTan δ | 14,17% | 0,257 | 0,178 |
| Tang δ (h) | 11,64% | 0,211 | -0,082 |
| Pi1/Vn | 9,47% | 0,171 | -0,143 |
| Tan δ | 9,43% | 0,171 | 0,105 |
| IP | 4,67% | 0,085 | 0,075 |
| H | 0,00% | 0,000 | 0,000 |

### Sensibilidade D10: piora fisica de 10%

| Input | Queda media D10 |
| --- | ---: |
| Pi1/Vn | 0,2102 |
| PD | 0,0294 |
| ΔI | 0,0274 |
| ΔTan δ | 0,0248 |
| Tan δ | 0,0244 |
| Tang δ (h) | 0,0236 |
| IP | 0,0108 |
| H | 0,0000 |

### Peso empirico D10 por permutacao

| Input | Peso permutacao | Aumento MAE |
| --- | ---: | ---: |
| PD | 28,79% | 0,5355 |
| Pi1/Vn | 16,00% | 0,2976 |
| ΔI | 15,60% | 0,2901 |
| ΔTan δ | 14,96% | 0,2782 |
| Tang δ (h) | 14,20% | 0,2642 |
| Tan δ | 8,00% | 0,1488 |
| IP | 2,44% | 0,0454 |
| H | 0,00% | 0,0000 |

## D20 - contaminacao

Nos papers, contaminacao aparece acoplada a umidade, carga espacial, perdas, descarga e condicoes de superficie/ambiente. A planilha nao tem uma medida direta de umidade ou contaminante; por isso `H` funciona como proxy forte na equacao atual. Esta e a maior diferenca conceitual contra D10: D20 e menos uma leitura pura de descarga parcial e mais uma coordenada de contaminacao/superficie/historico eletrico.

### Peso estrutural na equacao D20

| Input | Peso estrutural | Contrib abs media | Contrib media assinada |
| --- | ---: | ---: | ---: |
| IP | 26,67% | 0,475 | 0,434 |
| H | 21,47% | 0,382 | -0,260 |
| PD | 17,49% | 0,311 | -0,179 |
| Tang δ (h) | 14,09% | 0,251 | -0,094 |
| ΔTan δ | 11,42% | 0,203 | 0,143 |
| Pi1/Vn | 7,49% | 0,133 | 0,111 |
| ΔI | 1,21% | 0,021 | -0,021 |
| Tan δ | 0,16% | 0,003 | 0,003 |

### Sensibilidade D20: piora fisica de 10%

Valor positivo significa que D20 caiu quando o input piorou; valor negativo significa que D20 subiu. Sinais negativos aparecem porque D20 e uma coordenada de contaminacao, nao um peso causal linear isolado.

| Input | Impacto medio D20 |
| --- | ---: |
| Pi1/Vn | -0,1623 |
| H | 0,0651 |
| IP | 0,0590 |
| Tang δ (h) | 0,0281 |
| PD | -0,0205 |
| ΔTan δ | 0,0198 |
| Tan δ | -0,0008 |
| ΔI | -0,0008 |

### Peso empirico D20 por permutacao

| Input | Peso permutacao | Aumento MAE |
| --- | ---: | ---: |
| H | 31,15% | 0,5397 |
| PD | 17,98% | 0,3115 |
| Tang δ (h) | 15,06% | 0,2609 |
| IP | 14,94% | 0,2588 |
| Pi1/Vn | 11,62% | 0,2014 |
| ΔTan δ | 9,15% | 0,1586 |
| ΔI | 0,06% | 0,0011 |
| Tan δ | 0,04% | 0,0008 |

## GEI e limite dos graficos atuais

GEI continua sendo o alvo menos identificavel pelas 8 variaveis. Os papers reforcam que envelhecimento depende de tempo de operacao, ambiente, classe de isolamento, historico termico e conservacao. Por isso a equacao condicional acerta a tendencia, mas nao deve ser vendida como idade real sem variaveis historicas.

### Sensibilidade GEI: piora fisica de 10%

| Input | Aumento medio GEI |
| --- | ---: |
| Pi1/Vn | 0,6202 |
| Tan δ | 0,2343 |
| PD | 0,1131 |
| ΔI | 0,0323 |
| Tang δ (h) | 0,0283 |
| IP | 0,0263 |
| ΔTan δ | 0,0263 |
| H | 0,0000 |

### Peso empirico GEI por permutacao

| Input | Peso permutacao | Aumento MAE |
| --- | ---: | ---: |
| PD | 43,05% | 1,2492 |
| Tan δ | 24,84% | 0,7208 |
| Pi1/Vn | 20,05% | 0,5818 |
| ΔI | 4,50% | 0,1306 |
| ΔTan δ | 3,46% | 0,1003 |
| Tang δ (h) | 3,04% | 0,0882 |
| IP | 0,68% | 0,0198 |
| H | 0,39% | 0,0112 |

## Maiores residuos vistos nos graficos

### D10

| NR_OS | Grau de Deterioração (D10) | D10 producao | Erro D10 | Erro abs |
| --- | ---: | ---: | ---: | ---: |
| 17964F | 4,69 | -0,11 | -4,80 | 4,80 |
| 16677E | 3,58 | -0,11 | -3,69 | 3,69 |
| 21192E | 3,57 | -0,11 | -3,68 | 3,68 |
| 18402F | 3,41 | -0,11 | -3,52 | 3,52 |
| 17584E | 3,30 | -0,11 | -3,41 | 3,41 |
| 17736F | 3,13 | -0,11 | -3,24 | 3,24 |
| 16352E | 3,09 | -0,11 | -3,20 | 3,20 |
| 17959K | -0,88 | 2,01 | 2,89 | 2,89 |

### D20

| NR_OS | Grau de Contaminação (D20) | D20 producao | Erro D20 | Erro abs |
| --- | ---: | ---: | ---: | ---: |
| 18402J | -1,61 | 2,31 | 3,92 | 3,92 |
| 16677G | -1,49 | 2,31 | 3,80 | 3,80 |
| 17041L | -1,37 | 2,31 | 3,68 | 3,68 |
| 17041I | -0,69 | 2,31 | 3,00 | 3,00 |
| 20528E | 3,70 | 0,81 | -2,89 | 2,89 |
| 18402H | -0,57 | 2,31 | 2,88 | 2,88 |
| 17474E | 3,41 | 0,81 | -2,60 | 2,60 |
| 16481E | 3,39 | 0,81 | -2,58 | 2,58 |

### GEI

| NR_OS | Grau de Envelhecimento GEI (Anos) | GEI producao | Erro GEI | Erro abs |
| --- | ---: | ---: | ---: | ---: |
| 17959K | 25 | 9 | -16 | 16 |
| 17041F | 32 | 17 | -15 | 15 |
| 21761D | 29 | 15 | -14 | 14 |
| 17584E | 5 | 17 | 12 | 12 |
| 17128E | 5 | 17 | 12 | 12 |
| 17964F | 5 | 17 | 12 | 12 |
| 21634A | 32 | 20 | -12 | 12 |
| 21634A | 32 | 20 | -12 | 12 |

## Conclusao operacional

- Para degradacao/D10, o conjunto mais defensavel e: `Pi1/Vn` + familia `tan delta` + `PD` + `DeltaI/DeltaTan delta`. Isso combina bem com a literatura de deterioracao dieletrica e descarga parcial.
- Para contaminacao/D20, `H` e o eixo dominante na equacao atual; `IP`, `Pi1/Vn`, `PD` e `Tang delta (h)` entram como moduladores. Conceitualmente, isso deve ser tratado como proxy de contaminacao/umidade/superficie, nao como prova fisica direta de contaminante.
- Os graficos de historico sao bons para ver erro global e outliers, mas nao bastam para revelar pesos. Para peso verdadeiro, o projeto precisa mostrar graficos de sensibilidade, barras de importancia e residuos por input.
- O oraculo da aba historica precisa ser renomeado ou trocado por predicoes reais do bundle ML; do jeito atual, ele quase sempre sobrepoe a producao.
