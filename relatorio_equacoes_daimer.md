# Reconstrucao das equacoes DAIMER

## 1. Resumo executivo

### Alta confianca

- `Avaliacao Global = D10 + D20` em 388/388 linhas validas da planilha. O erro numerico maximo observado e da ordem de ponto flutuante.
- As saidas `D10`, `D20` e `Avaliacao Global` sao continuas e quantizadas em centesimos, nao simples classes discretas.
- O PDF confirma que os limites individuais sao referencias e que a diagnose real vem de um algoritmo/grafico global usando todos os parametros.
- O sinal operacional de `D10` e `D20` se comporta como uma margem/coordenada de diagnose: valores positivos sao coerentes com o quadrante bom do relatorio.

### Confianca media a alta

- `D10` e bem explicado por uma equacao log-normalizada com pequenas correcoes piecewise nos thresholds do relatorio.
- `D20` exige camada piecewise, principalmente em `H` e nos limiares de `Pi1/Vn`; a melhor forma compacta encontrada e estruturalmente plausivel, mas nao e identificavel como a equacao proprietaria exata.
- O valor `H = "-"` foi tratado como `H = 0`, com piso numerico `0,01` apenas para permitir `log10`.

### Nao identificavel com os dados atuais

- `GEI` nao fecha como funcao unica das 8 variaveis. O PDF diz que o grau de envelhecimento depende tambem de tempo de operacao, idade/historico e conservacao da isolacao. A planilha confirma isso: o melhor estimador somente pelas 8 variaveis ainda deixa erro medio de cerca de 2 anos.

### Apoio bibliografico final

A varredura dos PDFs em `papers/` nao encontrou coeficientes DAIMER ou uma equacao proprietaria equivalente. Ela reforcou, porem, que a estrutura adotada e tecnicamente plausivel: diagnostico por multiplas familias de fenomenos, incluindo descarga parcial, resistencia/polarizacao, perdas/relaxacao dieletrica, carga espacial, contaminacao/umidade e historico operacional. O resumo da varredura esta em `relatorio_papers.md`.

## 2. Equacoes propostas

Defina as margens logaritmicas. `D10` e `GEI` usam `log10`; `D20` e equivalente em `log20`, com coeficientes e thresholds convertidos da escala `log10` para preservar a calibracao:

```text
m_ip    = log10(IP / 2,0)
m_di    = log10(4,5 / DI)
m_pi    = log10(Pi1Vn / 0,57)
m_pd    = log10(17000 / PD)
m_dtd   = log10(1,0 / DeltaTanDelta)
m_tdh   = log10(0,05 / TangDeltaH)
m_td    = log10(4,0 / TanDelta)
m_h     = log10(7,0 / max(H, 0,01))
L(t, m) = max(0, t - m)
```

### Por que usar log10

Os inputs originais estao em escalas e unidades diferentes: resistencia/indice, porcentagem, grandezas eletricas e valores que podem ir de casas decimais ate dezenas de milhares. Por isso, a equacao nao soma os valores brutos diretamente.

Cada variavel primeiro vira uma razao contra uma referencia tecnica do relatorio. Essa razao remove a unidade direta e transforma o input em margem adimensional. Depois aplica-se `log10`, para que diferencas multiplicativas fiquem comparaveis entre si.

Exemplos:

```text
PD bruto = 8060              -> m_pd = log10(17000 / 8060)
IP bruto = 3,49              -> m_ip = log10(3,49 / 2,0)
TanDelta bruto = 1,468       -> m_td = log10(4,0 / 1,468)
```

Assim, a base comum da equacao e:

```text
input bruto -> razao contra referencia tecnica -> log10 -> termos piecewise -> soma ponderada
```

Os termos `L(t, m)` mantem a mesma base logaritmica, mas permitem mudar a inclinacao da equacao quando a margem passa por um threshold tecnico.

### D10

```text
D10 = 0,4809913308
    + 4,7352929414*m_pi
    + 2,0324724184*L(-0,187673132, m_pi)
    - 0,8935811025*L(0, m_td)
    - 0,8727027058*L(-0,477121255, m_td)
    + 0,7077394005*m_pd
    + 0,6615225327*m_di
    + 0,5940052636*m_dtd
    - 0,5846672503*L(-0,176091259, m_td)
    + 0,5503026270*m_tdh
    + 0,4195144391*m_td
    + 0,2327062135*m_ip
    - 0,0285128739*L(0, m_dtd)
    - 0,0217847299*L(-1, m_tdh)
    - 0,0150712128*L(0, m_tdh)
```

### D20

```text
D20 = 1,9128121224
    - 3,6469545900*m_pi
    - 2,9110938600*L(0, m_h)
    - 2,9049481900*L(-0,552841969, m_h)
    - 1,4854378800*L(-0,187673132, m_pi)
    + 1,3215025100*m_ip
    - 1,0768784700*L(-0,330993219, m_h)
    + 0,6708859000*m_tdh
    - 0,5033858900*m_pd
    + 0,4736325900*m_dtd
    + 0,2675978000*L(0, m_ip)
    - 0,2331994100*L(-0,602059991, m_dtd)
    + 0,1998861300*m_h
    + 0,1859391100*L(-0,176091259, m_td)
    + 0,1624229000*L(-1, m_tdh)
    + 0,0739883800*L(0, m_td)
    - 0,0296929400*m_di
```

### Avaliacao Global

```text
AvaliacaoGlobal = D10 + D20
```

### GEI

Estimador condicional pelas 8 variaveis:

```text
GEI_base = 16,1393406164
         - 1,1066262178*m_ip
         - 1,4344262661*m_di
         - 13,7550331430*m_pi
         - 3,1597643960*m_pd
         - 1,2180231156*m_dtd
         - 1,2565816597*m_tdh
         - 6,2872542582*m_td
         - 0,1106476897*m_h

GEI = round(max(0, min(TempoOperacao, GEI_base + tau_historico)))
```

Se `TempoOperacao` e `tau_historico` nao forem conhecidos, `GEI_base` e apenas uma aproximacao estrutural. A equacao exata do GEI nao e identificavel pelas 8 variaveis da planilha.

## 3. Interpretacao fisica

- `IP`: margem de polarizacao. Quanto maior que 2,0, melhor a resposta de isolamento; entra em D10 e D20 como margem positiva.
- `DI`: variacao de corrente no step voltage. Valores baixos indicam menor nao-linearidade de fuga; aparece principalmente em D10.
- `Pi1/Vn`: ponto de quebra normalizado. Abaixo de 0,57 ativa penalidades piecewise; abaixo de 0,37 ativa a regiao mais severa.
- `PD`: descargas parciais. Entra fortemente em D10, coerente com deterioracao por cavidades/ionizacao.
- `DeltaTanDelta`, `TangDeltaH` e `TanDelta`: descrevem perdas dielectricas, histerese e crescimento da dissipacao com tensao; aparecem em D10 e em ajustes de D20.
- `H`: harmonicas. A estrutura de D20 e dominada por penalidades nos limiares 7, 15 e 25, coerente com atividade ionica/contaminacao observada no PDF.
- Os termos `L(t, m)` sao as camadas piecewise: quando a margem passa para uma faixa pior que o threshold, a inclinacao da equacao muda.

## 4. Validacao

Planilha, 388 linhas validas para D10/D20/Global:

| Saida | MAE | RMSE | R2 | Erro maximo absoluto |
| --- | ---: | ---: | ---: | ---: |
| D10 | 0,024308 | 0,032790 | 0,999345 | 0,145514 |
| D20 | 0,095036 | 0,113986 | 0,985208 | 0,276252 |
| Avaliacao Global | 0,092763 | 0,110634 | 0,995482 | 0,256284 |

GEI, 363 linhas com alvo preenchido:

| Saida | MAE continuo | RMSE continuo | R2 | Acuracia apos round | MAE apos round |
| --- | ---: | ---: | ---: | ---: | ---: |
| GEI_base | 2,033737 | 2,730859 | 0,750951 | 0,187328 | 2,005510 |

Casos reais externos:

| Caso | D10 alvo | D10 pred | erro | D20 alvo | D20 pred | erro | Global alvo | Global pred | erro | GEI alvo | GEI pred sem historico | erro |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PDF | 1,46 | 1,44 | 0,02 | 2,04 | 1,97 | 0,07 | 3,50 | 3,42 | 0,08 | 10 | 11 | 1 |
| Caso 2 | 0,70 | 0,70 | 0,00 | 2,37 | 2,42 | 0,05 | 3,07 | 3,12 | 0,05 | 11 | 14 | 3 |

## 5. Codigo

As funcoes puras estao em `equacoes_daimer.py`:

- `calcular_d10(...)`
- `calcular_d20(...)`
- `calcular_avaliacao_global(...)`
- `calcular_gei(...)`

`calcular_gei` aceita `tempo_operacao_anos` e `ajuste_historico_anos` porque a propria documentacao tecnica indica dependencia de historico/tempo.

## 6. Honestidade metodologica

- `Avaliacao Global`: equacao real praticamente certa, pois e identidade exata na planilha e no PDF.
- `D10`: aproximacao estrutural plausivel de alta fidelidade; a forma log-normalizada com piecewise nos thresholds e fortemente sustentada pelos dados.
- `D20`: aproximacao estrutural plausivel de fidelidade boa; a familia log-piecewise e necessaria, mas a equacao exata proprietaria nao e unica com os dados atuais.
- `GEI`: impossivel fechar como funcao exclusiva das 8 variaveis. O modelo entregue e estimador condicional; a equacao real exige pelo menos uma variavel latente de tempo/historico.
