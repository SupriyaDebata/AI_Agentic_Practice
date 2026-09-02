"""ingest.py — Orchestration pipeline for PDF and Excel ingestion."""

from pathlib import Path

import fitz          # PyMuPDF
import pdfplumber
import openpyxl
import pandas as pd

from chunkers import chunk_text
from excel_serializer import serialize_dataframe
from retriever import add_chunks


# ── PDF helpers ───────────────────────────────────────────────────────────────

def _table_to_markdown(table: list[list]) -> str:
    """Convert a pdfplumber table (list-of-lists) to a markdown string."""
    if not table or not table[0]:
        return ""
    header = " | ".join(str(h or "") for h in table[0])
    sep    = " | ".join("---" for _ in table[0])
    rows   = [" | ".join(str(c or "") for c in row) for row in table[1:]]
    return "\n".join([header, sep] + rows)


def _extract_pdf_chunks(file_path: str, chunk_strategy: str, original_filename: str = None) -> list[dict]:
    """
    Extract three chunk types from a PDF:
      - text   : plain text (PyMuPDF), split by chunking strategy
      - table  : markdown-formatted tables (pdfplumber)
      - image_placeholder : note that a visual element exists on this page
    """
    path = Path(file_path)
    filename = original_filename or path.name
    all_chunks: list[dict] = []

    fitz_doc = fitz.open(str(path))

    with pdfplumber.open(str(path)) as plumber_doc:
        for page_num, (fitz_page, plumber_page) in enumerate(
            zip(fitz_doc, plumber_doc.pages), start=1
        ):
            base_meta = {"source": filename, "page": str(page_num)}

            # Detect images / charts (stored as image_placeholder)
            if fitz_page.get_images(full=True):
                all_chunks.append({
                    **base_meta,
                    "chunk_type":  "image_placeholder",
                    "chunk_index": 0,
                    "text": (
                        f"[IMAGE or CHART detected on page {page_num} of {filename}. "
                        "This page contains a visual element such as a graph, diagram, "
                        "or photograph. Visual content cannot be read by text extraction — "
                        "ask specifically about the visual content shown on this page.]"
                    ),
                })

            # Table extraction → markdown
            tables = plumber_page.extract_tables() or []
            for t_idx, table in enumerate(tables):
                md = _table_to_markdown(table)
                if md:
                    all_chunks.append({
                        **base_meta,
                        "chunk_type":  "table",
                        "chunk_index": t_idx,
                        "text":        md,
                    })

            # Plain text → chunked
            raw_text = fitz_page.get_text("text").strip()
            if len(raw_text) >= 30:
                text_chunks = chunk_text(
                    raw_text,
                    {**base_meta, "chunk_type": "text"},
                    strategy=chunk_strategy,
                )
                all_chunks.extend(text_chunks)

    fitz_doc.close()
    return all_chunks


# ── Excel helpers ─────────────────────────────────────────────────────────────

def _extract_excel_chunks(file_path: str, serialization_format: str, original_filename: str = None) -> list[dict]:
    """Read every sheet and serialize each DataFrame to text chunks."""
    path = Path(file_path)
    filename = original_filename or path.name
    all_chunks: list[dict] = []

    wb = openpyxl.load_workbook(str(path), data_only=True)

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = list(ws.values)
        if len(rows) < 2:
            continue

        headers = [
            str(h).strip() if h is not None else f"col_{i}"
            for i, h in enumerate(rows[0])
        ]
        data = [
            [str(c).strip() if c is not None else "" for c in row]
            for row in rows[1:]
        ]
        df = pd.DataFrame(data, columns=headers)
        df.replace("", pd.NA, inplace=True)
        df.dropna(how="all", inplace=True)

        if df.empty:
            continue

        base_meta = {
            "source":     filename,
            "page":       sheet_name,
            "chunk_type": "excel",
        }
        chunks = serialize_dataframe(df, base_meta, format=serialization_format)
        all_chunks.extend(chunks)

    wb.close()
    return all_chunks


# ── Public API ────────────────────────────────────────────────────────────────

def ingest_pdf(
    file_path: str,
    chunk_strategy: str = "recursive",
    collection_name: str = "documents",
    original_filename: str = None,
) -> int:
    """Ingest a PDF. Returns number of chunks stored."""
    chunks = _extract_pdf_chunks(file_path, chunk_strategy, original_filename)
    return add_chunks(chunks, collection_name)


def ingest_excel(
    file_path: str,
    serialization_format: str = "row_as_text",
    collection_name: str = "documents",
    original_filename: str = None,
) -> int:
    """Ingest an Excel file. Returns number of chunks stored."""
    chunks = _extract_excel_chunks(file_path, serialization_format, original_filename)
    return add_chunks(chunks, collection_name)


def ingest_file(
    file_path: str,
    chunk_strategy: str = "recursive",
    serialization_format: str = "row_as_text",
    collection_name: str = "documents",
    original_filename: str = None,
) -> int:
    """
    Dispatch to ingest_pdf or ingest_excel based on file extension.
    Returns number of chunks stored.
    original_filename: Used for citations when file_path is a temp file.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()
    
    if suffix == ".pdf":
        return ingest_pdf(file_path, chunk_strategy, collection_name, original_filename)
    elif suffix in [".xlsx", ".xls"]:
        return ingest_excel(file_path, serialization_format, collection_name, original_filename)
    else:
        raise ValueError(f"Unsupported file type: {suffix}. Use .pdf, .xlsx, or .xls")
