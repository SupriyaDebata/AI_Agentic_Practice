"""src/retriever.py — Semantic retrieval: embed → dual-search → filter → context."""

from src import config
from src.embeddings import embed_query
from src.vector_store import search_chunks

_TYPE_LABEL = {"text": "Text", "table": "Table", "image": "Chart/Image", "excel": "Excel"}

_STOP_WORDS = {
    "can", "i", "is", "are", "was", "were", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "have", "has", "had", "be", "been",
    "what", "how", "who", "where", "when", "why", "which",
    "the", "a", "an", "my", "me", "us", "our", "for", "in", "on", "at", "to",
    "of", "by", "with", "from", "about", "this", "that", "it", "its",
}


def _to_noun_phrase(question: str) -> str:
    """Strip stop words to produce a noun-phrase that matches document headings better.

    'Can I work remotely for the entire week?' → 'work remotely entire week'
    """
    tokens = [t.strip("?.,!") for t in question.lower().split()]
    return " ".join(t for t in tokens if t and t not in _STOP_WORDS)


def _search_and_merge(question: str, collection: str, top_k: int) -> list[dict]:
    """Run two search passes and merge by best score per unique chunk."""
    # Pass 1 — full question (captures intent and sentence context)
    vec_full = embed_query(question)
    hits_full = search_chunks(vec_full, collection, top_k)

    # Pass 2 — noun-phrase (matches section headings and key terms more directly)
    noun_phrase = _to_noun_phrase(question)
    hits_kw: list[dict] = []
    if noun_phrase and noun_phrase != question.lower().strip():
        vec_kw = embed_query(noun_phrase)
        hits_kw = search_chunks(vec_kw, collection, top_k)

    # Merge: keep highest score per unique text
    best: dict[str, dict] = {}
    for h in hits_full + hits_kw:
        key = h["text"].strip().lower()
        if key not in best or h["score"] > best[key]["score"]:
            best[key] = h

    return sorted(best.values(), key=lambda h: h["score"], reverse=True)[:top_k]


def get_context(question: str, collection: str) -> tuple[str, list[dict]]:
    """Return (context_string, citations) for the given question.

    context_string: labelled excerpts ready to paste into the LLM prompt.
    citations:      deduplicated list of {source, page, type, score}.
    """
    hits = _search_and_merge(question, collection, config.TOP_K)

    # Apply similarity threshold — filter after merging both passes
    hits = [h for h in hits if h["score"] >= config.SIMILARITY_THRESHOLD]

    if not hits:
        return "", []

    # Build context string capped at MAX_CONTEXT chars
    parts: list[str] = []
    total = 0
    for i, h in enumerate(hits, 1):
        label = _TYPE_LABEL.get(h["type"], h["type"])
        block = f"[Excerpt {i} | {h['source']}, Page/Sheet: {h['page']}, {label}]\n{h['text']}"
        if total + len(block) > config.MAX_CONTEXT:
            break
        parts.append(block)
        total += len(block)
    context = "\n\n---\n\n".join(parts)

    # Deduplicate citations by (source, page, type)
    seen: set[tuple] = set()
    citations: list[dict] = []
    for h in hits:
        key = (h["source"], h["page"], h["type"])
        if key not in seen:
            seen.add(key)
            citations.append({
                "source": h["source"],
                "page":   h["page"],
                "type":   h["type"],
                "score":  h["score"],
            })

    return context, citations
