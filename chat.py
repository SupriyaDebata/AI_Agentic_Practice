"""chat.py — Context assembly, Ollama call, citation formatting, grounded refusal."""

import json
import requests
from typing import Iterator

from retriever import search

OLLAMA_URL     = "http://localhost:11434/api/generate"
OLLAMA_MODEL   = "llama3.1"
OLLAMA_TIMEOUT = 300

_SYSTEM_PROMPT = """\
You are an Enterprise Document Intelligence Assistant.

Your job is to answer questions ONLY from the retrieved document context provided to you.

Rules:
1. Use only information present in the retrieved context.
2. Never invent facts, numbers, dates, values, or interpretations.
3. If the answer cannot be found in the retrieved context, respond with exactly:
   I could not find sufficient evidence in the provided documents to answer this question.
4. Every answer must include at least one citation in this format:
   [Source: <file_name>, Page <page_no>, Section: <section_type>]
5. When answering from a table:
   - Preserve exact row and column values.
   - Mention table name if available.
   - Specify row identifier when possible.
6. When answering from Excel:
   - Mention sheet name from the source header.
   - Mention row identifier if available.
   Example: West recorded the highest Q3 sales with 4,200 units.
   [Source: sales.xlsx, Page: Q3_Sales, Section: Excel]
7. If multiple excerpts contain relevant information, combine them and provide separate citations.
8. If an excerpt says it contains a chart or image that was not processed:
   The answer appears to be contained in a chart image that is not available as text. Vision/OCR processing is required.
9. Be concise and fact-based."""

_PROMPT_TEMPLATE = """\
{system}

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""


def _call_ollama(prompt: str) -> str:
    """Blocking Ollama call — used by the evaluator."""
    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model":   OLLAMA_MODEL,
                "prompt":  prompt,
                "stream":  False,
                "options": {"temperature": 0.1, "num_predict": 800},
            },
            timeout=OLLAMA_TIMEOUT,
        )
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        raise ConnectionError("Ollama is not running. Open a terminal and run: ollama serve")
    except requests.exceptions.ReadTimeout:
        raise TimeoutError(
            f"Ollama did not respond within {OLLAMA_TIMEOUT}s. "
            "The model may still be loading — wait a moment and retry."
        )


def _stream_ollama(prompt: str) -> Iterator[str]:
    """Yield response tokens from Ollama as they arrive (stream=True)."""
    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model":   OLLAMA_MODEL,
                "prompt":  prompt,
                "stream":  True,
                "options": {"temperature": 0.1, "num_predict": 800},
            },
            stream=True,
            timeout=OLLAMA_TIMEOUT,
        )
        r.raise_for_status()
        for raw_line in r.iter_lines():
            if raw_line:
                chunk = json.loads(raw_line)
                token = chunk.get("response", "")
                if token:
                    yield token
                if chunk.get("done", False):
                    break
    except requests.exceptions.ConnectionError:
        yield "\n\n[Ollama offline — run: ollama serve]"
    except Exception as exc:
        yield f"\n\n[Stream error: {exc}]"


def prepare_stream(
    question: str,
    collection_name: str = "documents",
    n_results: int = 5,
) -> tuple[Iterator[str], list[dict]]:
    """
    Retrieve context, then return (token_stream, citations).
    Iterate token_stream in the UI to show the answer as it types out.
    Citations are available immediately — display them after streaming ends.
    """
    hits = search(question, collection_name=collection_name, n_results=n_results)

    if not hits:
        def _empty() -> Iterator[str]:
            yield "I could not find sufficient evidence in the provided documents to answer this question."
        return _empty(), []

    context = _build_context(hits)
    prompt  = _PROMPT_TEMPLATE.format(
        system=_SYSTEM_PROMPT, context=context, question=question
    )
    return _stream_ollama(prompt), _deduplicated_citations(hits)


_SECTION_LABEL = {
    "text":              "Text Section",
    "table":             "Table",
    "excel":             "Excel",
    "image_placeholder": "Chart/Image",
}


def _build_context(hits: list[dict]) -> str:
    """Assemble retrieved chunks with source metadata so the LLM can cite correctly."""
    parts: list[str] = []
    for i, h in enumerate(hits, 1):
        section = _SECTION_LABEL.get(h["chunk_type"], h["chunk_type"])
        header = (
            f"[Excerpt {i} | Source: {h['source']}, "
            f"Page: {h['page']}, Section: {section}]"
        )
        parts.append(f"{header}\n{h['text']}")
    return "\n\n---\n\n".join(parts)


def _deduplicated_citations(hits: list[dict]) -> list[dict]:
    """Return one citation per unique (source, page, chunk_type) combination."""
    seen: set[tuple] = set()
    citations: list[dict] = []
    for h in hits:
        key = (h["source"], h["page"], h["chunk_type"])
        if key not in seen:
            seen.add(key)
            citations.append({
                "source": h["source"],
                "page":   h["page"],
                "type":   h["chunk_type"],
                "score":  h["score"],
            })
    return citations


def answer_question(
    question: str,
    collection_name: str = "documents",
    n_results: int = 5,
) -> dict:
    """
    Full RAG pipeline: retrieve → build context → prompt → generate → cite.

    Returns dict with:
      answer     : str   — LLM response or grounded refusal
      citations  : list  — deduplicated source list
      hits       : list  — raw retrieval hits
      is_refusal : bool  — True when answer could not be grounded
    """
    hits = search(question, collection_name=collection_name, n_results=n_results)

    if not hits:
        return {
            "answer": (
                "GROUNDED_REFUSAL: No documents have been ingested yet. "
                "Please upload and ingest documents first."
            ),
            "citations":  [],
            "hits":       [],
            "is_refusal": True,
        }

    context = _build_context(hits)
    prompt  = _PROMPT_TEMPLATE.format(
        system=_SYSTEM_PROMPT, context=context, question=question
    )
    raw        = _call_ollama(prompt)
    is_refusal = "could not find sufficient evidence" in raw.lower()

    return {
        "answer":     raw,
        "citations":  _deduplicated_citations(hits),
        "hits":       hits,
        "is_refusal": is_refusal,
    }


def check_ollama() -> bool:
    """Ping Ollama health endpoint. Returns True if running."""
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False
