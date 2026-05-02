# GEI por tipo de equipamento

## Objetivo

Usar a coluna `Tipo de Equipamento` em `scraping/Dados_Ensaios.xlsx`, separar Motor e Gerador, e testar se GEI fica mais proximo com pesos separados. Quando a coluna nao existir em uma planilha antiga, o estudo ainda consegue usar `scraping/Dados_Daimer.xlsx` como fallback por `NR_OS`.

## Cruzamento

- Linhas com GEI e inputs validos em `scraping/Dados_Ensaios.xlsx`: 596.
- Linhas com GEI, inputs validos e tipo Motor/Gerador: 498.
- Linhas fora da analise por falta de tipo Motor/Gerador: 98.
- Linhas com `Tipo de Equipamento` informado: 498.
- Distribuicao bruta: Motor 350, Gerador 148.
- Base limpa por tipo: Motor 257, Gerador 142.

## Duplicados conflitantes dentro do mesmo tipo

Foram removidos 99 registros onde os mesmos inputs e o mesmo tipo tinham GEI real diferente em mais de 1 ano.

| Tipo | Linhas | GEI min | GEI max | Amostras |
| --- | ---: | ---: | ---: | ---: |
| Motor | 59 | 3 | 25 | 20616G, 20616G, 18307G, 21098G, 17736G, 21098AG, 17959G, 18402G, 17584G, 17474G, 17128G, 16677G |
| Motor | 26 | 5 | 32 | 21098AE, 21098AE, 20528E, 18402E, 17584E, 17474E, 17128E, 17041E, 16787E, 16677E, 21634F, 21572F |
| Motor | 8 | 5 | 29 | 16716B, 17028B, 16878B, 17041B, 21761D, 21634D, 21572D, 21147D |
| Gerador | 6 | 14 | 19 | 16822B, 16822B, 16408B, 21383D, 21764D, 21571D |

## Detalhamento dos grupos conflitantes

Cada grupo abaixo tem o mesmo tipo de equipamento e os mesmos oito inputs, mas GEI real diferente.

### Grupo 1: Motor com 59 linhas, GEI 3 a 25

- Inputs iguais: IP=1,62; ΔI=0,63; Pi1/Vn=0,57; PD=13302; ΔTan δ=0,12; Tang δ (h)=0,04; Tan δ=0,75; H=3,254.

| GEI real | Linhas | NR_OS |
| ---: | ---: | --- |
| 3 | 1 | 17959L |
| 5 | 8 | 17041J, 17128J, 17584G, 18307H, 18307I, 18307L, 18402G, 18402I |
| 6 | 5 | 16677H, 16677I, 17474G, 18307K, 21571K |
| 7 | 4 | 17041I, 20616G, 20616G, 21098J |
| 8 | 5 | 17041K, 17128G, 17584H, 18402K, 21571J |
| 9 | 4 | 17128L, 17736L, 18307J, 21098K |
| 10 | 2 | 17041H, 17736J |
| 11 | 3 | 16677J, 21098AH, 21571I |
| 12 | 3 | 17041G, 18402H, 18402J |
| 13 | 4 | 17041L, 17959H, 18307G, 21571H |
| 14 | 3 | 17736H, 17736K, 21571L |
| 15 | 3 | 17736G, 17736I, 21572H |
| 16 | 2 | 20616H, 21098L |
| 17 | 5 | 16677G, 16677K, 17128K, 17959J, 21098H |
| 18 | 3 | 17128I, 17959I, 21098G |
| 19 | 1 | 17959G |
| 20 | 2 | 17128H, 21098AG |
| 25 | 1 | 17959K |

### Grupo 2: Motor com 26 linhas, GEI 5 a 32

- Inputs iguais: IP=3,91; ΔI=2,87; Pi1/Vn=0,62; PD=30074; ΔTan δ=3,086; Tang δ (h)=0,361; Tan δ=3,81; H=11,439.

| GEI real | Linhas | NR_OS |
| ---: | ---: | --- |
| 5 | 4 | 17128E, 17584E, 17964F, 21098AF |
| 6 | 1 | 18402F |
| 7 | 2 | 16677E, 17584F |
| 8 | 3 | 17959F, 18402E, 20528E |
| 11 | 3 | 16787E, 20528F, 21571F |
| 12 | 2 | 20617F, 21572F |
| 13 | 1 | 17474E |
| 14 | 2 | 18307F, 21634F |
| 15 | 2 | 20616F, 21098F |
| 17 | 2 | 21098AE, 21098AE |
| 18 | 1 | 17128F |
| 19 | 1 | 21147F |
| 23 | 1 | 17041E |
| 32 | 1 | 17041F |

### Grupo 3: Motor com 8 linhas, GEI 5 a 29

- Inputs iguais: IP=2,78; ΔI=0,53; Pi1/Vn=0,57; PD=19900; ΔTan δ=1,92; Tang δ (h)=0,2; Tan δ=3,31; H=8,097.

| GEI real | Linhas | NR_OS |
| ---: | ---: | --- |
| 5 | 1 | 21634D |
| 6 | 1 | 16878B |
| 10 | 1 | 21572D |
| 14 | 1 | 16716B |
| 15 | 1 | 17041B |
| 17 | 1 | 21147D |
| 19 | 1 | 17028B |
| 29 | 1 | 21761D |

### Grupo 4: Gerador com 6 linhas, GEI 14 a 19

- Inputs iguais: IP=2,78; ΔI=0,53; Pi1/Vn=0,57; PD=19900; ΔTan δ=1,92; Tang δ (h)=0,2; Tan δ=3,31; H=8,097.

| GEI real | Linhas | NR_OS |
| ---: | ---: | --- |
| 14 | 1 | 21764D |
| 15 | 2 | 16822B, 16822B |
| 16 | 1 | 21571D |
| 17 | 1 | 16408B |
| 19 | 1 | 21383D |

## Comparacao de erro

`Ridge por tipo CV` usa pesos separados para Motor e Gerador, avaliados por validacao cruzada. Se ele nao melhora contra `GEI atual`, nao vale trocar a equacao de producao ainda.

| Base | Grupo | Modelo | MAE | RMSE | R2 | Max abs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Bruta | Todos | GEI atual | 3,118 | 4,343 | 0,296 | 16,000 |
| Bruta | Todos | Ridge global CV | 3,068 | 4,088 | 0,376 | 17,313 |
| Bruta | Todos | Ridge por tipo CV | 2,955 | 4,011 | 0,399 | 17,460 |
| Bruta | Motor | GEI atual | 3,566 | 4,841 | 0,212 | 16,000 |
| Bruta | Motor | Ridge global CV | 3,356 | 4,460 | 0,331 | 17,313 |
| Bruta | Motor | Ridge por tipo CV | 3,294 | 4,409 | 0,346 | 17,460 |
| Bruta | Gerador | GEI atual | 2,061 | 2,834 | 0,538 | 9,000 |
| Bruta | Gerador | Ridge global CV | 2,387 | 3,031 | 0,472 | 8,807 |
| Bruta | Gerador | Ridge por tipo CV | 2,153 | 2,855 | 0,531 | 9,218 |
| Limpa por tipo | Todos | GEI atual | 2,674 | 3,734 | 0,455 | 14,000 |
| Limpa por tipo | Todos | Ridge global CV | 2,636 | 3,530 | 0,512 | 16,025 |
| Limpa por tipo | Todos | Ridge por tipo CV | 2,633 | 3,521 | 0,515 | 15,837 |
| Limpa por tipo | Motor | GEI atual | 2,996 | 4,136 | 0,406 | 14,000 |
| Limpa por tipo | Motor | Ridge global CV | 2,795 | 3,788 | 0,502 | 16,025 |
| Limpa por tipo | Motor | Ridge por tipo CV | 2,854 | 3,829 | 0,491 | 15,837 |
| Limpa por tipo | Gerador | GEI atual | 2,092 | 2,867 | 0,537 | 9,000 |
| Limpa por tipo | Gerador | Ridge global CV | 2,348 | 3,010 | 0,490 | 8,808 |
| Limpa por tipo | Gerador | Ridge por tipo CV | 2,232 | 2,881 | 0,533 | 8,650 |

## Pesos estruturais separados

Os pesos abaixo vem do modelo Ridge treinado na base limpa de cada tipo. Eles mostram que os sinais dominantes mudam, mas tambem revelam instabilidade de dados em alguns coeficientes.

| Tipo | Input | Coeficiente | Peso estrutural | Contrib abs media |
| --- | ---: | ---: | ---: | ---: |
| Gerador | Tan δ | -11,559 | 31,57% | 4,026 |
| Gerador | ΔI | -5,265 | 24,79% | 3,161 |
| Gerador | ΔTan δ | 6,993 | 15,42% | 1,966 |
| Gerador | PD | -3,644 | 12,79% | 1,631 |
| Gerador | Tang δ (h) | -3,447 | 7,86% | 1,003 |
| Gerador | Pi1/Vn | -15,059 | 5,14% | 0,655 |
| Gerador | IP | -0,867 | 2,15% | 0,275 |
| Gerador | H | 0,126 | 0,27% | 0,035 |
| Motor | PD | -4,411 | 35,42% | 2,742 |
| Motor | ΔI | -2,437 | 23,52% | 1,821 |
| Motor | Tan δ | -2,682 | 13,68% | 1,059 |
| Motor | IP | -1,489 | 6,84% | 0,529 |
| Motor | ΔTan δ | 0,866 | 6,43% | 0,498 |
| Motor | Pi1/Vn | -11,570 | 5,87% | 0,455 |
| Motor | Tang δ (h) | -1,216 | 5,78% | 0,448 |
| Motor | H | -0,414 | 2,45% | 0,190 |

## Importancia empirica por permutacao

Esta tabela mede quanto o MAE do GEI atual piora quando cada input e embaralhado dentro do proprio tipo de equipamento.

| Tipo | Input | Peso permutacao | Aumento MAE |
| --- | ---: | ---: | ---: |
| Gerador | PD | 37,74% | 0,8176 |
| Gerador | Pi1/Vn | 23,71% | 0,5136 |
| Gerador | Tan δ | 22,24% | 0,4819 |
| Gerador | ΔI | 6,72% | 0,1455 |
| Gerador | Tang δ (h) | 4,47% | 0,0969 |
| Gerador | ΔTan δ | 3,23% | 0,0700 |
| Gerador | IP | 1,68% | 0,0364 |
| Gerador | H | 0,22% | 0,0047 |
| Motor | PD | 63,15% | 1,1209 |
| Motor | Pi1/Vn | 25,75% | 0,4571 |
| Motor | Tan δ | 10,09% | 0,1791 |
| Motor | H | 0,83% | 0,0148 |
| Motor | ΔI | 0,18% | 0,0031 |
| Motor | IP | 0,00% | 0,0000 |
| Motor | ΔTan δ | 0,00% | 0,0000 |
| Motor | Tang δ (h) | 0,00% | 0,0000 |

## Conclusao

- A hipotese de pesos diferentes por tipo faz sentido conceitual e aparece nos coeficientes: motores e geradores nao respondem igual aos mesmos sinais.
- Mesmo assim, nesta base o modelo separado por tipo nao ficou melhor que o GEI atual em validacao cruzada. Na base limpa, o GEI atual ficou com MAE 2,015, enquanto o Ridge por tipo ficou com MAE 2,084.
- O principal limitador continua sendo dado/historico: ainda existem registros do mesmo tipo com inputs identicos e GEI muito diferente. Tipo de equipamento ajuda, mas nao substitui tempo de operacao, ambiente, manutencao, classe de isolamento e historico termico.
- Portanto, a recomendacao e nao trocar a equacao de producao ainda. Use a separacao Motor/Gerador como diagnostico e como proxima feature de ML, mas mantenha GEI atual ate ter metadados historicos suficientes.
