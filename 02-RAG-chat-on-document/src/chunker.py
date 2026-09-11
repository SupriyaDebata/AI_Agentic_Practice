"""src/chunker.py -- Section-aware text chunking for PDF narrative text."""

import re
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src import config

# Matches the start of a new section: blank line, numbered heading, or bullet
_SECTION_BREAK = re.compile(
    r"(?:\n\s*\n)"                                    # blank line
    r"|(?=\n\s*(?:\d+[\.\)]\s|\#{1,3}\s|\|\-\s))",  # numbered / heading / bullet
    re.MULTILINE,
)

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=config.CHUNK_SIZE,
    chunk_overlap=config.CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def chunk_text(text: str) -> list[str]:
    """Split text respecting section boundaries, merging adjacent small sections.

    Each policy section (e.g. 'Work From Home', 'Annual Leave') stays in its
    own chunk so its embedding vector remains focused on one topic. Sections
    larger than CHUNK_SIZE are sub-split with RecursiveCharacterTextSplitter.

    Adjacent sections that are individually short (e.g. a product title followed
    by a spec table) are merged into one chunk so the product name context is
    not lost. Two sections are merged only when their combined length stays
    within CHUNK_SIZE.
    """
    sections = [s.strip() for s in _SECTION_BREAK.split(text) if s.strip()]
    chunks: list[str] = []
    pending = ""

    for section in sections:
        if len(section) <= config.CHUNK_SIZE:
            # Merge into the pending buffer if it still fits; otherwise flush first
            if pending and len(pending) + 1 + len(section) <= config.CHUNK_SIZE:
                pending = pending + "\n" + section
            else:
                if pending:
                    chunks.append(pending)
                pending = section
        else:
            # Large section: flush pending then sub-split
            if pending:
                chunks.append(pending)
                pending = ""
            chunks.extend(_splitter.split_text(section))

    if pending:
        chunks.append(pending)

    return [c for c in chunks if c.strip()]
