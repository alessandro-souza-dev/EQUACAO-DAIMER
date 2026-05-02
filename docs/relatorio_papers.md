# Varredura final dos papers

## Objetivo

Esta varredura verificou se os PDFs em `../papers/` poderiam alterar ou reforcar a reconstrucao DAIMER antes do fechamento do projeto.

Conclusao direta: os papers nao trazem a equacao DAIMER nem coeficientes/thresholds equivalentes aos usados na planilha. Eles agregam como suporte tecnico externo para a arquitetura adotada: diagnostico por multiplos sinais, normalizacao por referencia, termos nao lineares e necessidade de calibracao supervisionada quando houver casos reais.

## Arquivos analisados

| Arquivo | Paginas | Tema principal | O que agrega ao DAIMER |
| --- | ---: | --- | --- |
| `047-054_海老沼康光_高電圧電力機器における絶縁劣化検出法の動向.pdf` | 8 | Revisao de metodos de deteccao de degradacao de isolamento em equipamentos de alta tensao | Classifica os metodos em descarga parcial, resistencia de isolamento, relaxacao dieletrica e carga espacial; isso sustenta a leitura multi-sinal de `PD`, `IP`, `Tan delta`/perdas e termos associados a contaminacao/carga. |
| `2003_10J110_115.pdf` | 6 | Avaliacao de degradacao de isolamento em motores de alta tensao por descarga parcial | E o paper mais proximo do uso DAIMER em motores: analisou cerca de 150 motores em operacao, mostrou que `PD` online capta tendencia de envelhecimento, mas que a medicao online nao correlaciona diretamente com ensaio offline e varia com temperatura/ambiente. Reforca calibracao supervisionada por contexto. |
| `Honbun-4797.pdf` | 154 | Diagnostico de degradacao em equipamentos de chaveamento/distribuicao | Reforca que contaminacao, umidade, descarga e diagnostico de vida remanescente entram como fenomenos acoplados, nao como uma unica medida isolada. |
| `k14055_thesis.pdf` | 147 | Descargas parciais e gases de decomposicao em cabos OF | Reforca que `PD` e um marcador forte de degradacao, mas dependente de meio isolante, estado quimico e historico. |
| `kou_k_562.pdf` | 116 | Descarga parcial em transformadores a oleo e diagnostico avancado | Reforca que `PD` depende de condicoes de operacao, envelhecimento, umidade e estado do material; isto apoia a aba de calibracao supervisionada. |
| `o244.pdf` | 164 | Efeito de descarga parcial e carga em sistemas isolantes polimericos | Reforca o papel de carga espacial/residual, corrente de perda CA, nao linearidade e fase; isso apoia termos piecewise e interacoes no modelo. |
| `texeng_te1_03.pdf` | 5 | Diagnostico e reparo para extensao de vida de motores eletricos | Muito relevante para a interpretacao pratica: discute migracao de diagnostico em motores de alta tensao, classe de isolamento B/F, compatibilidade com dados historicos, resistencia de isolamento, `tan delta` e `Qmax`. Reforca que thresholds dependem do tipo de isolamento e do historico do ativo. |

## Impacto na equacao

Nao foi encontrado nos papers nenhum conjunto de coeficientes que substitua as equacoes atuais de `D10`, `D20` ou `GEI`.

O que os papers reforcam:

- `PD` deve permanecer como variavel de alta importancia, especialmente para degradacao/deterioracao.
- `IP` e grandezas relacionadas a resistencia/polarizacao fazem sentido como eixo de saude do isolamento.
- `Tan delta`, `DeltaTan delta` e `Tang delta (h)` pertencem ao grupo de perdas/relaxacao dieletrica, coerente com o uso em margens logaritmicas.
- Contaminacao, umidade, carga espacial e efeitos de operacao aparecem como fenomenos acoplados; isso ajuda a explicar por que `D20` precisa de termos piecewise e por que `GEI` nao fecha perfeitamente sem historico.
- A literatura favorece diagnostico por familia de fenomenos, nao por uma unica variavel dominante.
- Os papers especificos de motores reforcam que `PD`, `tan delta`, resistencia de isolamento e `Qmax` devem ser tratados com contexto: classe de isolamento, temperatura, ambiente e comparabilidade entre dados historicos influenciam a leitura.

## Impacto no ML

Os papers confirmam que o modelo ML deve continuar usando uma engenharia de atributos rica:

- variaveis brutas;
- razoes contra referencias tecnicas;
- `log10` para colocar grandezas diferentes numa mesma base adimensional;
- termos piecewise/hinge para thresholds;
- interacoes entre margens.

Eles tambem sustentam a estrategia de `calibracao supervisionada`: novos casos reais podem corrigir residuais locais sem fingir que a equacao proprietaria foi identificada diretamente.

Em especial, os papers de motores indicam que os mesmos parametros podem mudar de faixa esperada quando muda o tipo de isolamento ou o metodo de medicao. Isso favorece manter uma equacao-base interpretavel e usar calibracao supervisionada para ajustar o ativo/frota.

## Decisao final

Agrega documentacao e justificativa fisica, mas nao altera a melhor equacao atual.

Portanto, a versao final permanece:

- equacoes interpretaveis em `../equacoes_daimer.py`;
- explicacao estrutural em `relatorio_equacoes_daimer.md`;
- modelo ML e pesos em `relatorio_modelo_ml.md` e `relatorio_pesos_modelo_ml.md`;
- calibracao supervisionada na aba HTML para aprender com novos matches reais.

Observacao: dois PDFs adicionais estavam locais e nao rastreados pelo Git (`2003_10J110_115.pdf` e `texeng_te1_03.pdf`). Eles foram considerados nesta varredura, mas os binarios nao precisam ser adicionados ao repositorio para preservar o projeto leve e evitar versionamento desnecessario de artigos.
