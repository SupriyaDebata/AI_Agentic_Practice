"""chunkers.py — Three text chunking strategies: fixed, recursive, section_aware."""

import re
# langchain_text_splitters is imported lazily inside recursive_chunker
# to avoid loading the full LangChain/PyTorch stack at app startup.

# ---------------------------------------------------------------------------
# nltk setup — checks local data only (no network calls at startup).
# Falls back to regex sentence splitting if punkt data is not installed.
# To enable: python -m nltk.downloader punkt_tab
# ---------------------------------------------------------------------------
_NLTK_AVAILABLE = False
try:
    import nltk
    from nltk.tokenize import sent_tokenize as _st

    # Only check local disk — never download at startup
    for _model in ("tokenizers/punkt_tab", "tokenizers/punkt"):
        try:
            nltk.data.find(_model)
            _NLTK_AVAILABLE = True
            break
        except LookupError:
            pass
except Exception:
    pass


def sent_tokenize(text: str) -> list[str]:
    if _NLTK_AVAILABLE:
        return _st(text)                      # type: ignore[name-defined]
    return re.split(r"(?<=[.!?])\s+", text.strip())


def _split_sentences(text: str) -> list[str]:
    """Return a list of sentences — uses nltk if available, regex otherwise."""
    return sent_tokenize(text)


def fixed_chunker(
    text: str,
    metadata: dict,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[dict]:
    """Slide a fixed-size window over text with overlap."""
    chunks: list[dict] = []
    start, idx, length = 0, 0, len(text)

    while start < length:
        end = min(start + chunk_size, length)
        fragment = text[start:end].strip()
        if fragment:
            chunks.append({**metadata, "text": fragment, "chunk_index": idx})
            idx += 1
        if end == length:
            break
        start += chunk_size - chunk_overlap

    return chunks


def recursive_chunker(
    text: str,
    metadata: dict,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[dict]:
    """Use LangChain RecursiveCharacterTextSplitter — respects paragraph/sentence boundaries."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter  # lazy
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    pieces = splitter.split_text(text)
    return [
        {**metadata, "text": p.strip(), "chunk_index": i}
        for i, p in enumerate(pieces)
        if p.strip()
    ]


def section_aware_chunker(
    text: str,
    metadata: dict,
    min_chunk_size: int = 100,
    max_chunk_size: int = 1500,
) -> list[dict]:
    """
    Split on structural headings, then use nltk sentence tokenization to
    subdivide any section that still exceeds max_chunk_size.

    Heading patterns detected:
      - Markdown: ## Heading
      - Numbered: 1. / 1.1 / 1.1.1 style
      - ALL CAPS lines
      - Lines ending with ':'
    Falls back to regex sentence splitting if nltk is not installed.
    """
    heading_re = re.compile(
        r"(?m)^("
        r"#{1,4}\s.+"                        # ## Markdown headings
        r"|(?:\d+\.)+\d*\s+\S.{0,60}"        # 1. / 1.1 / 1.1.1 numbered
        r"|[A-Z][A-Z\s\-]{3,}:?$"            # ALL CAPS lines
        r"|[A-Z].{3,50}:\s*$"                # Title ending in colon
        r")"
    )

    # ── Pass 1: split on blank lines, group by heading boundaries ─────────────
    raw_paragraphs = re.split(r"\n{2,}", text)
    sections: list[str] = []
    buffer = ""

    for para in raw_paragraphs:
        stripped = para.strip()
        if not stripped:
            continue
        is_heading = bool(heading_re.match(stripped))
        would_overflow = len(buffer) + len(stripped) > max_chunk_size

        if is_heading or would_overflow:
            if buffer:
                sections.append(buffer)
            buffer = stripped
        else:
            buffer = f"{buffer}\n\n{stripped}".strip() if buffer else stripped

    if buffer:
        sections.append(buffer)

    # ── Pass 2: subdivide sections still too large using sentence boundaries ──
    split_sections: list[str] = []
    for sec in sections:
        if len(sec) <= max_chunk_size:
            split_sections.append(sec)
            continue
        # Break at sentence boundaries
        sentences = _split_sentences(sec)
        bucket = ""
        for sent in sentences:
            if len(bucket) + len(sent) > max_chunk_size and bucket:
                split_sections.append(bucket.strip())
                bucket = sent
            else:
                bucket = f"{bucket} {sent}".strip() if bucket else sent
        if bucket:
            split_sections.append(bucket.strip())

    # ── Pass 3: merge sections below minimum size ──────────────────────────────
    merged: list[str] = []
    acc = ""
    for sec in split_sections:
        if len(acc) + len(sec) < min_chunk_size:
            acc = f"{acc}\n\n{sec}".strip() if acc else sec
        else:
            if acc:
                merged.append(acc)
            acc = sec
    if acc:
        merged.append(acc)

    return [
        {**metadata, "text": t, "chunk_index": i}
        for i, t in enumerate(merged)
        if len(t.strip()) >= 20
    ]


CHUNKERS: dict[str, object] = {
    "fixed":         fixed_chunker,
    "recursive":     recursive_chunker,
    "section_aware": section_aware_chunker,
}


def chunk_text(text: str, metadata: dict, strategy: str = "recursive") -> list[dict]:
    """Dispatch text to the selected chunking strategy."""
    fn = CHUNKERS.get(strategy, recursive_chunker)
    return fn(text, metadata)
