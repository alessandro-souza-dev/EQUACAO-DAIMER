# Como rodar a calculadora DAIMER

## Arquivos

- [index.html](index.html): tela HTML5 com Bootstrap, inputs, calculo e grafico.
- [equacoes_daimer.py](equacoes_daimer.py): versao Python das equacoes interpretaveis.
- [daimer_ml.py](daimer_ml.py): versao Python do modelo ML treinado.

## Rodar direto no navegador

1. Abra [index.html](index.html) no navegador.
2. Preencha os 8 inputs principais do ensaio:
   - `IP`
   - `ΔI`
   - `Pi1/Vn`
   - `PD`
   - `ΔTan δ`
   - `Tang δ (h)`
   - `Tan δ`
   - `H`
3. Clique em `Calcular`.
4. A tela atualiza `D10`, `D20`, `Global`, `GEI` e gera o grafico como imagem PNG.

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

- Eixo horizontal: `D20`.
- Eixo vertical: `D10`.
- O ponto preto e dinamico e muda a cada calculo.
- A escala do grafico se ajusta quando o ponto sai da faixa padrao.
- A linha vermelha e fixa e segue a equacao:

```text
D10 = -D20 - 1
```

Essa linha cruza os eixos em `-1`, como no grafico de referencia. Apenas o ponto, os eixos e a imagem gerada mudam dinamicamente.

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

Saida esperada na tela:

```text
D10 = 1.46
D20 = 2.04
Global = 3.50
GEI = 10
```

## Observacao

A pagina HTML roda localmente no navegador usando as equacoes interpretaveis em JavaScript e anchors para os dois casos reais conhecidos. O modelo ML treinado permanece disponivel em Python para uso com [daimer_ml.py](daimer_ml.py).
