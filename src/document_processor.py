"""src/document_processor.py — Extract text, tables, and structured data from PDF and Excel files."""

import hashlib
from pathlib import Path

import fitz
import openpyxl
import pandas as pd
import pdfplumber

from src import config


def _file_id(path: Path) -> str:
    # Hash file content so the same document uploaded multiple times
    # always produces the same ID (temp-file mtime changes on every upload).
    return hashlib.sha256(path.read_bytes()).hexdigest()[:20]


def extract_pdf(path: Path, filename: str) -> list[dict]:
    """Extract text chunks, tables, and image placeholders from a PDF.

    Returns a list of dicts with keys: text, source, page, type, file_id.
    """
    fid = _file_id(path)
    out: list[dict] = []
    fitz_doc = fitz.open(str(path))

    with pdfplumber.open(str(path)) as plumb:
        for page_num, (fp, pp) in enumerate(zip(fitz_doc, plumb.pages), 1):
            base = {"source": filename, "page": str(page_num), "file_id": fid}

            text = fp.get_text("text").strip()
            if len(text) >= config.PDF_MIN_TEXT:
                out.append({**base, "type": "text", "idx": 0, "text": text})

            if config.PDF_EXTRACT_TABLES:
                for t_i, table in enumerate(pp.extract_tables() or []):
                    if not table or not table[0]:
                        continue
                    header = " | ".join(str(h or "") for h in table[0])
                    sep    = " | ".join("---" for _ in table[0])
                    rows   = [" | ".join(str(c or "") for c in row) for row in table[1:]]
                    md = "\n".join([header, sep] + rows)
                    if md.strip():
                        out.append({**base, "type": "table", "idx": t_i, "text": md})

            if config.PDF_EXTRACT_IMAGES and fp.get_images(full=True):
                out.append({
                    **base, "type": "image", "idx": 0,
                    "text": (
                        f"[Visual content on page {page_num} of {filename}. "
                        "Image/chart present. OCR not enabled.]"
                    ),
                })

    fitz_doc.close()
    return out


def extract_excel(path: Path, filename: str) -> list[dict]:
    """Extract rows from every sheet using all three serialisation strategies.

    Storing row_as_text, markdown_table, and column_wise together lets
    semantic search surface whichever format best matches each question.
    Returns a list of dicts with keys: text, source, page, type, file_id, strategy.
    """
    fid = _file_id(path)
    out: list[dict] = []
    wb  = openpyxl.load_workbook(str(path), data_only=True)

    for sheet in wb.sheetnames:
        rows = list(wb[sheet].values)
        if len(rows) < 2:
            continue

        headers = [
            str(h).strip() if h is not None else f"col_{i}"
            for i, h in enumerate(rows[0])
        ]
        data = [
            [None if (c is None or str(c).strip() == "") else str(c).strip() for c in row]
            for row in rows[1:]
        ]
        df = pd.DataFrame(data, columns=headers).dropna(how="all")
        if df.empty:
            continue

        base = {"source": filename, "page": sheet, "file_id": fid, "type": "excel"}

        # row_as_text — one chunk per row, best for record lookups
        for i, (_, row) in enumerate(df.iterrows()):
            parts = [
                f"{col}: {row[col]}"
                for col in df.columns
                if pd.notna(row[col]) and str(row[col]).strip()
            ]
            if parts:
                out.append({**base, "strategy": "row", "idx": i, "text": " | ".join(parts)})

        # markdown_table — full table in one chunk, best for comparisons
        rpc = config.EXCEL_ROWS_PER_CHUNK
        for i, start in enumerate(range(0, len(df), rpc)):
            md = df.iloc[start:start + rpc].to_markdown(index=False)
            if md and md.strip():
                out.append({**base, "strategy": "table", "idx": i, "text": md})

        # column_wise — one chunk per column, best for aggregates
        for i, col_name in enumerate(df.columns):
            vals = df[col_name].dropna().astype(str).tolist()
            if vals:
                out.append({
                    **base, "strategy": "col", "idx": i,
                    "text": f"Column: {col_name}\nValues: {', '.join(vals)}",
                })

    wb.close()
    return out
