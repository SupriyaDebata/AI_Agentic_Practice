"""src/chunker.py — Section-aware text chunking for PDF narrative text."""

import re
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src import config

# Matches the start of a new section: blank line, numbered heading, or bullet
_SECTION_BREAK = re.compile(
    r"(?:\n\s*\n)"                                    # blank line
    r"|(?=\n\s*(?:\d+[\.\)]\s|\#{1,3}\s|\•|\-\s))",  # numbered / heading / bullet
    re.MULTILINE,
)

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=config.CHUNK_SIZE,
    chunk_overlap=config.CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def chunk_text(text: str) -> list[str]:
    """Split text respecting section boundaries.

    Each policy section (e.g. 'Work From Home', 'Annual Leave') stays in its
    own chunk so its embedding vector remains focused on one topic. Sections
    larger than CHUNK_SIZE are sub-split with RecursiveCharacterTextSplitter.
    """
    sections = [s.strip() for s in _SECTION_BREAK.split(text) if s.strip()]
    chunks: list[str] = []
    for section in sections:
        if len(section) <= config.CHUNK_SIZE:
            chunks.append(section)
        else:
            chunks.extend(_splitter.split_text(section))
    return [c for c in chunks if c.strip()]
