# RAG local dos papers

Esta pasta agora esta organizada para separar corpus, interface e artefatos do RAG.

## Estrutura

- `papers/rag_papers.py`: CLI principal e servidor da interface web.
- `papers/pdfs/`: lugar preferencial para novos PDFs.
- `papers/ui/`: interface web local.
- `papers/docs/`: documentacao.
- `papers/rag_index/`: artefatos do indice persistido.

## Observacao importante deste workspace

O OneDrive deste ambiente bloqueou a movimentacao de varios PDFs pelo terminal. Por isso:

- o RAG prioriza `papers/pdfs/`
- mas continua lendo automaticamente os PDFs que ainda estiverem na raiz de `papers`

Quando o ambiente permitir, novos PDFs devem ser colocados em `papers/pdfs/`.

## Interface web

No raiz do repositorio:

```powershell
python .\papers\rag_papers.py serve --open-browser
```

Se preferir abrir manualmente, use:

```powershell
python .\papers\rag_papers.py serve
```

Depois abra `http://127.0.0.1:8765`.

Por padrao a interface usa modo `live`, que e o mais confiavel neste workspace.

Na primeira consulta em modo `live`, o servidor monta o indice em memoria. Por isso a resposta inicial pode levar mais tempo; depois disso, as consultas no mesmo servidor tendem a ficar mais rapidas.

## Linha de comando

Pergunta em modo live:

```powershell
python .\papers\rag_papers.py ask "quais papers relacionam descarga parcial com degradacao de motores de alta tensao?" --live
```

Resposta em JSON:

```powershell
python .\papers\rag_papers.py ask "qual o papel de tan delta nos papers?" --json
```

Trechos recuperados:

```powershell
python .\papers\rag_papers.py ask "como os papers tratam contaminacao, umidade e carga espacial?" --show-chunks --live
```

## Indice persistido

Se o seu ambiente permitir escrita normal:

```powershell
python .\papers\rag_papers.py build
```

Reconstrucao forcada:

```powershell
python .\papers\rag_papers.py build --force
```

Tudo fica salvo em `papers/rag_index/`.

## Nota tecnica

O RAG usa TF-IDF por n-gramas de caracteres para suportar PDFs em portugues, ingles, japones e texto OCR imperfeito.