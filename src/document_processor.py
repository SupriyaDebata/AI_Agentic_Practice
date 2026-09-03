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

    # Only open pdfplumber (a second full PDF parse) when table extraction is on.
    # Without this guard, every PDF is parsed twice even when no tables are needed.
    plumb_ctx = pdfplumber.open(str(path)) if config.PDF_EXTRACT_TABLES else None
    plumb_pages = plumb_ctx.pages if plumb_ctx else [None] * fitz_doc.page_count

    try:
        for page_num, (fp, pp) in enumerate(zip(fitz_doc, plumb_pages), 1):
            base = {"source": filename, "page": str(page_num), "file_id": fid}

            text = fp.get_text("text").strip()
            if len(text) >= config.PDF_MIN_TEXT:
                out.append({**base, "type": "text", "idx": 0, "text": text})

            if config.PDF_EXTRACT_TABLES and pp is not None:
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
                    "text": f"[Image/chart on page {page_num} of {filename} — not extractable as text.]",
                })
    finally:
        fitz_doc.close()
        if plumb_ctx:
            plumb_ctx.close()

    return out


def _aggregate_chunk(df: pd.DataFrame, id_col: str, sheet: str, base: dict) -> dict | None:
    """Return a pre-computed aggregate chunk (highest/lowest/total per numeric column).

    Pre-computing these facts at ingest time means the LLM never has to scan raw
    rows to answer 'which X had the highest Y' — the answer is stated explicitly.
    """
    lines = [f"Aggregate statistics for sheet '{sheet}' (source: {base['source']}):"]
    for col_name in df.columns:
        if col_name == id_col:
            continue
        col_data = df[[id_col, col_name]].copy()
        # Parse numeric values; handle comma-formatted numbers like "1,200"
        numeric = pd.to_numeric(
            col_data[col_name].astype(str).str.replace(",", "", regex=False).str.strip(),
            errors="coerce",
        )
        valid_idx = numeric.dropna().index
        if len(valid_idx) < 2:
            continue
        col_data = col_data.loc[valid_idx]
        numeric = numeric.loc[valid_idx]
        max_i = numeric.idxmax()
        min_i = numeric.idxmin()
        lines.append(
            f"  {col_name}: "
            f"highest={col_data.loc[max_i, id_col]} ({numeric[max_i]:.4g}), "
            f"lowest={col_data.loc[min_i, id_col]} ({numeric[min_i]:.4g}), "
            f"total={numeric.sum():.4g}, "
            f"average={numeric.mean():.4g}, "
            f"count={len(numeric)}"
        )
    if len(lines) == 1:
        return None
    return {**base, "strategy": "agg", "idx": 0, "text": "\n".join(lines)}


def extract_excel(path: Path, filename: str) -> list[dict]:
    """Extract rows from every sheet using all three serialisation strategies.

    Storing row_as_text, markdown_table, column_wise, and aggregate chunks lets
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
        id_col = df.columns[0]  # first column treated as the row identifier (Region, Product, etc.)

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

        # column_wise — one chunk per column paired with row identifier, best for targeted lookups
        # Previously stored only raw values; now includes the identifier so the LLM knows
        # which row each value belongs to (e.g. "West: 4500 | East: 3600 | North: 1200").
        for i, col_name in enumerate(df.columns):
            if col_name == id_col:
                vals = df[col_name].dropna().astype(str).tolist()
                text = f"Column: {col_name}\nValues: {', '.join(vals)}"
            else:
                paired = df[[id_col, col_name]].dropna(subset=[col_name])
                pairs = [
                    f"{str(r[id_col]).strip()}: {str(r[col_name]).strip()}"
                    for _, r in paired.iterrows()
                ]
                text = f"Column: {col_name} (by {id_col})\n" + " | ".join(pairs)
            if text.strip():
                out.append({**base, "strategy": "col", "idx": i, "text": text})

        # aggregate — pre-computed highest/lowest/total per numeric column
        agg = _aggregate_chunk(df, id_col, sheet, base)
        if agg:
            out.append(agg)

    wb.close()
    return out
