from __future__ import annotations

import argparse
import contextlib
import io
import json
import logging
import os
import re
import sys
import webbrowser
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha1
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast

import joblib
import pdfplumber
from scipy.sparse import spmatrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


BASE_DIR = Path(__file__).absolute().parent
PDF_DIR = BASE_DIR / "pdfs"
INDEX_DIR = BASE_DIR / "rag_index"
UI_DIR = BASE_DIR / "ui"
UI_INDEX_PATH = UI_DIR / "index.html"
PAGES_PATH = INDEX_DIR / "pages.jsonl"
CHUNKS_PATH = INDEX_DIR / "chunks.jsonl"
MANIFEST_PATH = INDEX_DIR / "manifest.json"
VECTORIZER_PATH = INDEX_DIR / "vectorizer.joblib"
MATRIX_PATH = INDEX_DIR / "matrix.joblib"

DEFAULT_CHUNK_SIZE = 1600
DEFAULT_OVERLAP = 250

logging.getLogger("pdfminer").setLevel(logging.ERROR)

DOMAIN_QUERY_EXPANSIONS = {
    "descarga parcial": ["partial discharge", "partial discharges", "pd"],
    "degradacao": ["degradation", "deterioration", "aging", "ageing"],
    "envelhecimento": ["aging", "ageing", "deterioration"],
    "motores": ["motors", "motor", "rotating machines"],
    "motor": ["motor", "motors", "rotating machines"],
    "alta tensao": ["high voltage", "high-voltage"],
    "isolamento": ["insulation", "dielectric insulation"],
    "geradores": ["generators", "generator", "hydrogenerators"],
    "gerador": ["generator", "generators", "hydrogenerator"],
    "vida util": ["remaining useful life", "rul", "service life"],
    "contaminacao": ["contamination", "surface condition"],
    "umidade": ["humidity", "moisture"],
    "carga espacial": ["space charge"],
    "tan delta": ["tan delta", "dissipation factor"],
}

JsonDict = dict[str, Any]
IndexMatrix = spmatrix
RuntimeIndex = tuple[list[JsonDict], TfidfVectorizer, IndexMatrix, JsonDict]

RUNTIME_INDEX_CACHE: dict[tuple[int, int], RuntimeIndex] = {}


@dataclass
class PageRecord:
    file_name: str
    relative_path: str
    page: int
    char_count: int
    text: str


@dataclass
class ChunkRecord:
    chunk_id: str
    file_name: str
    relative_path: str
    page: int
    start_char: int
    end_char: int
    char_count: int
    text: str
    search_text: str


def ensure_stdout_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        cast(Any, sys.stdout).reconfigure(encoding="utf-8")


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def coerce_positive_int(
    value: Any,
    default: int,
    minimum: int = 1,
    maximum: int | None = None,
) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


def coerce_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def expand_query(question: str) -> str:
    normalized_question = normalize_text(question)
    lowered = normalized_question.lower()
    expansions: list[str] = []
    for source_term, targets in DOMAIN_QUERY_EXPANSIONS.items():
        if source_term in lowered:
            expansions.extend(targets)
    if not expansions:
        return normalized_question
    return f"{normalized_question} {' '.join(expansions)}"


def iter_pdf_paths() -> list[Path]:
    pdf_paths: dict[str, Path] = {}

    if PDF_DIR.exists():
        for path in PDF_DIR.rglob("*.pdf"):
            if path.is_file():
                pdf_paths[str(path.resolve()).lower()] = path

    for path in BASE_DIR.glob("*.pdf"):
        if path.is_file():
            pdf_paths.setdefault(str(path.resolve()).lower(), path)

    return sorted(
        pdf_paths.values(),
        key=lambda path: (0 if PDF_DIR in path.parents else 1, path.as_posix().lower()),
    )


def count_pdf_locations() -> JsonDict:
    pdfs_dir_count = 0
    if PDF_DIR.exists():
        pdfs_dir_count = sum(1 for path in PDF_DIR.rglob("*.pdf") if path.is_file())
    root_pdf_count = sum(1 for path in BASE_DIR.glob("*.pdf") if path.is_file())
    return {
        "preferred_directory": PDF_DIR.relative_to(BASE_DIR).as_posix(),
        "pdfs_dir_count": pdfs_dir_count,
        "root_pdf_count": root_pdf_count,
    }


def has_persisted_index() -> bool:
    return any(
        path.exists()
        for path in [PAGES_PATH, CHUNKS_PATH, MANIFEST_PATH, VECTORIZER_PATH, MATRIX_PATH]
    )


def extract_pages(pdf_path: Path) -> tuple[list[PageRecord], list[dict[str, object]]]:
    relative_path = pdf_path.relative_to(BASE_DIR).as_posix()
    pages: list[PageRecord] = []
    page_errors: list[dict[str, object]] = []
    stderr_buffer = io.StringIO()
    with contextlib.redirect_stderr(stderr_buffer):
        with pdfplumber.open(pdf_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                try:
                    text = normalize_text(page.extract_text() or "")
                except KeyboardInterrupt:  # pragma: no cover - interactive interruption
                    raise
                except Exception as exc:  # pragma: no cover - depends on source PDF
                    page_errors.append(
                        {
                            "file_name": pdf_path.name,
                            "page": page_number,
                            "error": str(exc),
                        }
                    )
                    continue
                if not text:
                    continue
                pages.append(
                    PageRecord(
                        file_name=pdf_path.name,
                        relative_path=relative_path,
                        page=page_number,
                        char_count=len(text),
                        text=text,
                    )
                )
    return pages, page_errors


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[tuple[int, int, str]]:
    if not text:
        return []

    step = max(1, chunk_size - overlap)
    chunks: list[tuple[int, int, str]] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        hard_end = min(text_length, start + chunk_size)
        end = hard_end

        if hard_end < text_length:
            window_start = min(text_length, start + chunk_size // 2)
            best_break = max(
                text.rfind("\n\n", window_start, hard_end),
                text.rfind("\n", window_start, hard_end),
                text.rfind(". ", window_start, hard_end),
                text.rfind("; ", window_start, hard_end),
                text.rfind("。", window_start, hard_end),
            )
            if best_break > start:
                end = best_break + 1

        if end <= start:
            end = hard_end

        snippet = text[start:end].strip()
        if snippet:
            normalized_snippet = normalize_text(snippet)
            chunks.append((start, start + len(normalized_snippet), normalized_snippet))

        if hard_end >= text_length:
            break

        next_start = max(start + step, end - overlap)
        if next_start <= start:
            next_start = start + step
        start = next_start

    return chunks


def build_document_context(pages: list[PageRecord]) -> dict[str, str]:
    contexts: dict[str, str] = {}
    for page in pages:
        contexts.setdefault(
            page.file_name,
            normalize_text(f"{page.file_name} {page.text[:500]}"),
        )
    return contexts


def build_chunks(pages: list[PageRecord], chunk_size: int, overlap: int) -> list[ChunkRecord]:
    chunk_records: list[ChunkRecord] = []
    document_context = build_document_context(pages)
    for page in pages:
        context_text = document_context.get(page.file_name, page.file_name)
        for start_char, end_char, text in chunk_text(page.text, chunk_size=chunk_size, overlap=overlap):
            chunk_key = f"{page.relative_path}:{page.page}:{start_char}:{end_char}"
            chunk_records.append(
                ChunkRecord(
                    chunk_id=sha1(chunk_key.encode("utf-8")).hexdigest()[:16],
                    file_name=page.file_name,
                    relative_path=page.relative_path,
                    page=page.page,
                    start_char=start_char,
                    end_char=end_char,
                    char_count=len(text),
                    text=text,
                    search_text=normalize_text(f"{context_text} {text}"),
                )
            )
    return chunk_records


def write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def build_runtime_index(
    chunk_size: int,
    overlap: int,
) -> tuple[list[JsonDict], TfidfVectorizer, IndexMatrix, JsonDict]:
    pdf_paths = iter_pdf_paths()
    pages: list[PageRecord] = []
    extraction_errors: list[dict[str, str]] = []
    page_extraction_errors: list[dict[str, object]] = []
    empty_pdfs: list[str] = []

    for pdf_path in pdf_paths:
        try:
            extracted_pages, page_errors = extract_pages(pdf_path)
        except Exception as exc:  # pragma: no cover - defensive path
            extraction_errors.append({"file_name": pdf_path.name, "error": str(exc)})
            continue

        page_extraction_errors.extend(page_errors)

        if not extracted_pages:
            empty_pdfs.append(pdf_path.name)
            continue

        pages.extend(extracted_pages)

    chunks = build_chunks(pages, chunk_size=chunk_size, overlap=overlap)
    if not chunks:
        raise SystemExit("Nenhum texto extraivel foi encontrado nos PDFs da pasta papers.")

    texts = [chunk.search_text for chunk in chunks]
    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(3, 5),
        lowercase=True,
        strip_accents="unicode",
        sublinear_tf=True,
        max_features=120000,
    )
    matrix = cast(IndexMatrix, vectorizer.fit_transform(texts))

    page_records = [asdict(page) for page in pages]
    chunk_records = [asdict(chunk) for chunk in chunks]

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "base_dir": str(BASE_DIR),
        "pdf_locations": count_pdf_locations(),
        "pdf_count": len(pdf_paths),
        "pages_with_text": len(page_records),
        "chunk_count": len(chunk_records),
        "empty_pdfs": empty_pdfs,
        "extraction_errors": extraction_errors,
        "page_extraction_errors": page_extraction_errors,
        "settings": {
            "chunk_size": chunk_size,
            "overlap": overlap,
            "vectorizer": {
                "analyzer": "char",
                "ngram_range": [3, 5],
                "max_features": 120000,
            },
        },
    }
    return chunk_records, vectorizer, matrix, manifest


def get_cached_live_index(chunk_size: int, overlap: int) -> RuntimeIndex:
    cache_key = (chunk_size, overlap)
    cached = RUNTIME_INDEX_CACHE.get(cache_key)
    if cached is not None:
        return cached

    cached = build_runtime_index(chunk_size=chunk_size, overlap=overlap)
    RUNTIME_INDEX_CACHE[cache_key] = cached
    return cached


def build_index(chunk_size: int, overlap: int, force: bool) -> JsonDict:
    if has_persisted_index() and not force:
        raise SystemExit(
            "Indice ja existe em papers/rag_index. Use --force para reconstruir."
        )

    os.makedirs(INDEX_DIR, exist_ok=True)
    RUNTIME_INDEX_CACHE.clear()
    chunk_records, vectorizer, matrix, manifest = build_runtime_index(
        chunk_size=chunk_size,
        overlap=overlap,
    )
    page_records = load_runtime_pages()
    write_jsonl(PAGES_PATH, page_records)
    write_jsonl(CHUNKS_PATH, chunk_records)
    joblib.dump(vectorizer, VECTORIZER_PATH)
    joblib.dump(matrix, MATRIX_PATH)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest


def load_runtime_pages() -> list[JsonDict]:
    pdf_paths = iter_pdf_paths()
    pages: list[PageRecord] = []
    for pdf_path in pdf_paths:
        try:
            extracted_pages, _page_errors = extract_pages(pdf_path)
        except Exception:  # pragma: no cover - defensive path
            continue
        pages.extend(extracted_pages)
    return [asdict(page) for page in pages]


def load_index() -> tuple[list[JsonDict], TfidfVectorizer, IndexMatrix, JsonDict]:
    required_paths = [CHUNKS_PATH, VECTORIZER_PATH, MATRIX_PATH, MANIFEST_PATH]
    missing = [path.name for path in required_paths if not path.exists()]
    if missing:
        missing_names = ", ".join(missing)
        raise SystemExit(
            f"Indice incompleto em papers/rag_index: faltando {missing_names}. Rode o comando build primeiro."
        )
    chunks = cast(list[JsonDict], load_jsonl(CHUNKS_PATH))
    vectorizer = joblib.load(VECTORIZER_PATH)
    matrix = cast(IndexMatrix, joblib.load(MATRIX_PATH))
    manifest = cast(JsonDict, json.loads(MANIFEST_PATH.read_text(encoding="utf-8")))
    return chunks, vectorizer, matrix, manifest


def get_runtime_index(
    live: bool,
    chunk_size: int,
    overlap: int,
) -> tuple[list[JsonDict], TfidfVectorizer, IndexMatrix, JsonDict]:
    if live:
        return get_cached_live_index(chunk_size=chunk_size, overlap=overlap)

    try:
        return load_index()
    except SystemExit:
        return build_runtime_index(chunk_size=chunk_size, overlap=overlap)


def retrieve(
    question: str,
    top_k: int,
    live: bool,
    chunk_size: int,
    overlap: int,
) -> tuple[list[dict], TfidfVectorizer, dict]:
    chunks, vectorizer, matrix, manifest = get_runtime_index(
        live=live,
        chunk_size=chunk_size,
        overlap=overlap,
    )
    clean_question = expand_query(question)
    if not clean_question:
        raise SystemExit("Pergunta vazia.")

    question_vector = vectorizer.transform([clean_question])
    scores = linear_kernel(question_vector, matrix).ravel()
    ranked_indexes = scores.argsort()[::-1]

    results: list[dict] = []
    for idx in ranked_indexes:
        score = float(scores[idx])
        if score <= 0:
            continue
        result = dict(chunks[idx])
        result["score"] = score
        results.append(result)
        if len(results) >= top_k:
            break
    return results, vectorizer, manifest


def split_sentences(text: str) -> list[str]:
    raw_parts = re.split(r"(?<=[\.!?;:])\s+|(?<=[。！？])|\n+", text)
    sentences: list[str] = []
    for part in raw_parts:
        cleaned = normalize_text(part)
        if len(cleaned) >= 40:
            sentences.append(cleaned)
    return sentences


def synthesize_answer(
    question: str,
    results: list[dict],
    vectorizer: TfidfVectorizer,
    max_sentences: int,
) -> list[dict]:
    if not results:
        return []

    candidates: list[dict] = []
    for result in results:
        sentences = split_sentences(result["text"])
        if not sentences:
            sentences = [result["text"][:350]]
        for sentence in sentences:
            candidates.append(
                {
                    "text": sentence,
                    "file_name": result["file_name"],
                    "page": result["page"],
                }
            )

    sentence_texts = [candidate["text"] for candidate in candidates]
    sentence_matrix = vectorizer.transform(sentence_texts)
    question_vector = vectorizer.transform([expand_query(question)])
    sentence_scores = linear_kernel(question_vector, sentence_matrix).ravel()
    ranked_indexes = sentence_scores.argsort()[::-1]

    selected: list[dict] = []
    seen_sentences: set[str] = set()
    for idx in ranked_indexes:
        sentence = candidates[idx]
        key = sentence["text"]
        if key in seen_sentences:
            continue
        seen_sentences.add(key)
        selected.append(
            {
                "text": sentence["text"],
                "file_name": sentence["file_name"],
                "page": sentence["page"],
                "score": float(sentence_scores[idx]),
            }
        )
        if len(selected) >= max_sentences:
            break
    return selected


def build_answer_payload(
    question: str,
    results: list[dict],
    vectorizer: TfidfVectorizer,
    manifest: JsonDict,
    max_sentences: int,
    live: bool,
) -> JsonDict:
    answer_sentences = synthesize_answer(
        question,
        results=results,
        vectorizer=vectorizer,
        max_sentences=max_sentences,
    )
    return {
        "question": question,
        "mode": "live" if live else "persisted-or-live-fallback",
        "manifest": manifest,
        "pdf_locations": count_pdf_locations(),
        "answer": " ".join(item["text"] for item in answer_sentences),
        "answer_sentences": answer_sentences,
        "results": results,
    }


def handle_build(args: argparse.Namespace) -> int:
    manifest = build_index(
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        force=args.force,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


def handle_ask(args: argparse.Namespace) -> int:
    results, vectorizer, manifest = retrieve(
        args.question,
        top_k=args.top_k,
        live=args.live,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
    )
    payload = build_answer_payload(
        args.question,
        results=results,
        vectorizer=vectorizer,
        manifest=manifest,
        max_sentences=args.max_sentences,
        live=args.live,
    )

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(f"Pergunta: {args.question}\n")
    if payload["answer"]:
        print("Resposta sintetizada:\n")
        print(payload["answer"])
        print()
    else:
        print("Nenhuma resposta sintetizada foi gerada.\n")

    print("Fontes principais:\n")
    for idx, result in enumerate(results, start=1):
        score = f"{result['score']:.4f}"
        print(f"{idx}. {result['file_name']} | pagina {result['page']} | score {score}")

    if args.show_chunks:
        print("\nTrechos recuperados:\n")
        for idx, result in enumerate(results, start=1):
            snippet = result["text"][: args.preview_chars].replace("\n", " ")
            print(f"[{idx}] {snippet}\n")

    return 0


def handle_stats(_args: argparse.Namespace) -> int:
    _chunks, _vectorizer, _matrix, manifest = load_index()
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


def send_json_response(
    handler: BaseHTTPRequestHandler,
    payload: JsonDict,
    status: HTTPStatus = HTTPStatus.OK,
) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def send_html_response(handler: BaseHTTPRequestHandler, body: bytes) -> None:
    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def serve_ui(
    host: str,
    port: int,
    default_live: bool,
    default_top_k: int,
    default_max_sentences: int,
    chunk_size: int,
    overlap: int,
    open_browser: bool,
) -> int:
    if not UI_INDEX_PATH.exists():
        raise SystemExit("Interface nao encontrada em papers/ui/index.html.")

    class RagRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            route = self.path.split("?", 1)[0]
            if route in {"/", "/index.html"}:
                send_html_response(self, UI_INDEX_PATH.read_bytes())
                return

            if route == "/api/config":
                send_json_response(
                    self,
                    {
                        "default_live": default_live,
                        "defaults": {
                            "top_k": default_top_k,
                            "max_sentences": default_max_sentences,
                            "chunk_size": chunk_size,
                            "overlap": overlap,
                        },
                        "pdf_locations": count_pdf_locations(),
                    },
                )
                return

            send_json_response(
                self,
                {"error": "Rota nao encontrada."},
                status=HTTPStatus.NOT_FOUND,
            )

        def do_POST(self) -> None:  # noqa: N802
            route = self.path.split("?", 1)[0]
            if route != "/api/ask":
                send_json_response(
                    self,
                    {"error": "Rota nao encontrada."},
                    status=HTTPStatus.NOT_FOUND,
                )
                return

            content_length = coerce_positive_int(
                self.headers.get("Content-Length"),
                default=0,
                minimum=0,
            )
            raw_body = self.rfile.read(content_length) if content_length else b"{}"

            try:
                body = cast(JsonDict, json.loads(raw_body.decode("utf-8")))
            except json.JSONDecodeError:
                send_json_response(
                    self,
                    {"error": "JSON invalido."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return

            question = normalize_text(str(body.get("question", "")))
            if not question:
                send_json_response(
                    self,
                    {"error": "Pergunta vazia."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return

            request_live = coerce_bool(body.get("live"), default_live)
            request_top_k = coerce_positive_int(
                body.get("top_k"),
                default=default_top_k,
                minimum=1,
                maximum=10,
            )
            request_max_sentences = coerce_positive_int(
                body.get("max_sentences"),
                default=default_max_sentences,
                minimum=1,
                maximum=10,
            )

            try:
                results, vectorizer, manifest = retrieve(
                    question,
                    top_k=request_top_k,
                    live=request_live,
                    chunk_size=chunk_size,
                    overlap=overlap,
                )
                payload = build_answer_payload(
                    question,
                    results=results,
                    vectorizer=vectorizer,
                    manifest=manifest,
                    max_sentences=request_max_sentences,
                    live=request_live,
                )
            except SystemExit as exc:
                send_json_response(
                    self,
                    {"error": str(exc)},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            except Exception as exc:  # pragma: no cover - network runtime path
                send_json_response(
                    self,
                    {"error": f"Falha ao consultar o RAG: {exc}"},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
                return

            send_json_response(self, payload)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer((host, port), RagRequestHandler)
    url = f"http://{host}:{port}"
    print(f"Interface do RAG disponivel em {url}")
    print("PDFs em papers/pdfs sao priorizados; PDFs ainda presos na raiz continuam sendo lidos.")
    print("Pressione Ctrl+C para encerrar o servidor.")

    if open_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover - interactive shutdown
        print("\nServidor encerrado.")
    finally:
        server.server_close()

    return 0


def handle_serve(args: argparse.Namespace) -> int:
    return serve_ui(
        host=args.host,
        port=args.port,
        default_live=args.live,
        default_top_k=args.top_k,
        default_max_sentences=args.max_sentences,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        open_browser=args.open_browser,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="RAG local para os PDFs da pasta papers.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Extrai PDFs e gera o indice local.")
    build_parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    build_parser.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP)
    build_parser.add_argument("--force", action="store_true")
    build_parser.set_defaults(handler=handle_build)

    ask_parser = subparsers.add_parser("ask", help="Consulta o indice local.")
    ask_parser.add_argument("question")
    ask_parser.add_argument("--top-k", type=int, default=5)
    ask_parser.add_argument("--max-sentences", type=int, default=5)
    ask_parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    ask_parser.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP)
    ask_parser.add_argument("--live", action="store_true")
    ask_parser.add_argument("--show-chunks", action="store_true")
    ask_parser.add_argument("--preview-chars", type=int, default=300)
    ask_parser.add_argument("--json", action="store_true")
    ask_parser.set_defaults(handler=handle_ask)

    stats_parser = subparsers.add_parser("stats", help="Mostra estatisticas do indice.")
    stats_parser.set_defaults(handler=handle_stats)

    serve_parser = subparsers.add_parser("serve", help="Abre a interface web local do RAG.")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
    serve_parser.add_argument("--top-k", type=int, default=5)
    serve_parser.add_argument("--max-sentences", type=int, default=5)
    serve_parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    serve_parser.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP)
    serve_parser.add_argument("--live", dest="live", action="store_true")
    serve_parser.add_argument("--persisted", dest="live", action="store_false")
    serve_parser.add_argument("--open-browser", action="store_true")
    serve_parser.set_defaults(handler=handle_serve, live=True)
    return parser


def main() -> int:
    ensure_stdout_utf8()
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())