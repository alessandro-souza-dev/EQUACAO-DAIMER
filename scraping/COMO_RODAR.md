# Como rodar a calculadora DAIMER

## Arquivos

- [index.html](index.html): tela HTML5 com Bootstrap, inputs, calculo, grafico e calibracao supervisionada.
- [equacoes_daimer.py](equacoes_daimer.py): versao Python das equacoes interpretaveis.
- [daimer_ml.py](daimer_ml.py): versao Python do modelo ML treinado.

## Rodar direto no navegador

1. Abra [index.html](index.html) no navegador.
2. Na aba `Calculadora DAIMER`, preencha os 8 inputs principais do ensaio:
   - `IP`
   - `ΔI`
   - `Pi1/Vn`
   - `PD`
   - `ΔTan δ`
   - `Tang δ (h)`
   - `Tan δ`
   - `H`
3. Clique em `Calcular`.
4. A tela atualiza `D10`, `D20`, `Global`, `GEI` e gera os graficos de `Producao` e `Oraculo`.

Campos opcionais para GEI:

- `Tempo operação`: limita o GEI ao tempo maximo informado.
- `Ajuste GEI`: soma um ajuste historico em anos.

## Rodar com servidor local

Tambem e possivel abrir por um servidor simples:

```powershell
python -m http.server 8000
```

Depois acesse:

```text
http://localhost:8000/index.html
```

## Grafico

- Eixo horizontal: `D10` / degradacao.
- Eixo vertical: `D20` / contaminacao.
- O ponto preto e dinamico e muda a cada calculo.
- A escala do grafico se ajusta quando o ponto sai da faixa padrao.
- A linha vermelha e fixa e segue a equacao:

```text
D20 = -D10 - 1
```

Essa linha cruza os eixos em `-1`, como no grafico de referencia. Apenas o ponto, os eixos e a imagem gerada mudam dinamicamente.

## Calibracao supervisionada

Use a aba `Calibração supervisionada` quando houver um caso real confirmado com os 8 inputs e as saidas reais `D10`, `D20` e `GEI`.

Fluxo recomendado:

1. Preencha os inputs do ensaio ou clique em `Usar entradas da calculadora`.
2. Informe `D10 real`, `D20 real` e `GEI real`.
3. Clique em `Adicionar match e aprender`.
4. A pagina salva o match no navegador, recalibra o modelo supervisionado e mostra o erro medio antes/depois.
5. Confira os `Pesos supervisionados` para ver quais inputs passaram a influenciar a correcao de `D10`, `D20` e `GEI`.

A calibracao usa uma correcao por residuo em cima da equacao local. Quando os inputs batem exatamente com um match real salvo, a previsao supervisionada retorna o valor real salvo; para novos pontos, usa a correcao aprendida pelos matches.

Os botoes `Exportar JSON` e `Importar JSON` permitem guardar ou restaurar os matches supervisionados em outro navegador ou maquina.

## Saida

O botao `Baixar PNG` salva a imagem gerada do grafico atual.

Exemplo do caso PDF:

```text
IP = 3.49
ΔI = 0.74
Pi1/Vn = 0.57
PD = 8060
ΔTan δ = 0.361
Tang δ (h) = 0.161
Tan δ = 1.468
H = 3.582
```

Saida esperada no bloco `Oraculo` para o caso PDF:

```text
D10 = 1.46
D20 = 2.04
Global = 3.50
GEI = 10
```

## Observacao

A pagina HTML roda localmente no navegador usando as equacoes interpretaveis em JavaScript, anchors para os dois casos reais conhecidos e calibracao supervisionada armazenada em `localStorage`. O modelo ML treinado permanece disponivel em Python para uso com [daimer_ml.py](daimer_ml.py).
