"""src/document_processor.py -- Extract text, tables, and structured data from PDF and Excel files."""

import hashlib
import re
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

    # doc_title: first meaningful line of page 1, used as context on later pages
    # so spec chunks like "Power supply: 24 VAC." embed with the product name.
    doc_title = ""

    try:
        for page_num, (fp, pp) in enumerate(zip(fitz_doc, plumb_pages), 1):
            base = {"source": filename, "page": str(page_num), "file_id": fid}

            text = fp.get_text("text").strip()

            # Capture the document title from page 1 (first non-empty line)
            if page_num == 1 and text:
                first_line = next((ln.strip() for ln in text.split("\n") if ln.strip()), "")
                doc_title = first_line[:100]

            # For pages after page 1, prepend the document title so spec/data chunks
            # carry the product or document name into their embedding.
            # Example: "Smart Thermostat X100\nPower supply: 24 VAC."
            if page_num > 1 and doc_title and text:
                text = f"{doc_title}\n{text}"

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
                    "text": f"[Image/chart on page {page_num} of {filename} -- not extractable as text.]",
                })
    finally:
        fitz_doc.close()
        if plumb_ctx:
            plumb_ctx.close()

    return out


def _aggregate_chunk(df: pd.DataFrame, id_col: str, sheet: str, base: dict) -> dict | None:
    """Return a pre-computed aggregate chunk (highest/lowest/total per numeric column).

    Uses natural-language sentences that include the id_col descriptor (e.g. "region",
    "product", "customer") so answers like "The North region has the lowest revenue"
    share vocabulary with both the question and the context, improving faithfulness scoring.
    """
    def _fmt(v: float) -> str:
        return str(int(v)) if v == int(v) else f"{v:,.2f}"

    # Use the id_col name as a natural noun (e.g. "Region" → "region", "Product Name" → "product name")
    id_label = id_col.lower()

    lines = [f"Summary of {sheet} data (source: {base['source']}):"]
    for col_name in df.columns:
        if col_name == id_col:
            continue
        col_data = df[[id_col, col_name]].copy()
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
        max_val = col_data.loc[max_i, id_col]
        min_val = col_data.loc[min_i, id_col]
        lines.append(
            f"For {col_name}: "
            f"The {max_val} {id_label} has the highest {col_name} ({_fmt(numeric[max_i])}). "
            f"The {min_val} {id_label} has the lowest {col_name} ({_fmt(numeric[min_i])}). "
            f"Total {col_name}: {_fmt(numeric.sum())}. "
            f"Average {col_name}: {_fmt(numeric.mean())} across {len(numeric)} {id_label}s."
        )
    if len(lines) == 1:
        return None
    return {**base, "strategy": "agg", "idx": 0, "text": "\n".join(lines)}


_ID_PATTERN = re.compile(r'^[A-Za-z]{1,4}\d{2,}$')  # matches C001, O1001, P01, etc.


def _build_id_lookup(sheets_dfs: dict[str, pd.DataFrame]) -> dict[str, str]:
    """Scan all sheets in a workbook and build an ID → display-name map.

    Detects "reference" sheets whose first column is all ID-like codes (C001, O1001…)
    and maps each ID to the value in the second column (the human-readable name).

    This lets order rows like "Customer ID: C001" be enriched with "Apex Retail"
    so semantic search can match "How many units did Apex Retail order?"
    """
    lookup: dict[str, str] = {}
    for df in sheets_dfs.values():
        if df.empty or len(df.columns) < 2:
            continue
        id_col, name_col = df.columns[0], df.columns[1]
        sample = df[id_col].dropna().astype(str).str.strip().head(6).tolist()
        # Only treat as a reference sheet if ≥ half the sample values look like IDs
        if sum(1 for v in sample if _ID_PATTERN.match(v)) >= len(sample) // 2 + 1:
            for _, row in df.iterrows():
                k = str(row.get(id_col) or "").strip()
                v = str(row.get(name_col) or "").strip()
                if k and v and k != v and _ID_PATTERN.match(k):
                    lookup[k] = v
    return lookup


def extract_excel(path: Path, filename: str) -> list[dict]:
    """Extract rows from every sheet using all four serialisation strategies.

    Storing row_as_text, markdown_table, column_wise, and aggregate chunks lets
    semantic search surface whichever format best matches each question.

    Also builds a cross-sheet ID→Name lookup so order rows like
    'Customer ID: C001' are enriched with 'Apex Retail', enabling
    semantic retrieval for questions that use customer names rather than IDs.

    Returns a list of dicts with keys: text, source, page, type, file_id, strategy.
    """
    fid = _file_id(path)
    out: list[dict] = []
    wb  = openpyxl.load_workbook(str(path), data_only=True)

    # ── Pass 1: load all sheet DataFrames so we can build the ID lookup ────────
    all_dfs: dict[str, pd.DataFrame] = {}
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
        if not df.empty:
            all_dfs[sheet] = df

    # ID→Name map built once across all sheets (e.g. C001 → "Apex Retail")
    id_lookup = _build_id_lookup(all_dfs)

    # ── Pass 2: generate chunks per sheet ──────────────────────────────────────
    for sheet, df in all_dfs.items():
        base = {"source": filename, "page": sheet, "file_id": fid, "type": "excel"}
        id_col = df.columns[0]  # first column treated as the row identifier

        # row_as_text -- one chunk per row, best for record lookups.
        # Inline-resolves ID codes to human names using the cross-sheet lookup
        # so "Customer ID: C001" becomes "Customer ID: C001 (Apex Retail)".
        for i, (_, row) in enumerate(df.iterrows()):
            parts = []
            for col in df.columns:
                val = row[col]
                if pd.notna(val) and str(val).strip():
                    val_str = str(val).strip()
                    resolved = id_lookup.get(val_str)
                    if resolved:
                        parts.append(f"{col}: {val_str} ({resolved})")
                    else:
                        parts.append(f"{col}: {val_str}")
            if parts:
                out.append({**base, "strategy": "row", "idx": i, "text": " | ".join(parts)})

        # markdown_table -- full table in one chunk, best for comparisons
        rpc = config.EXCEL_ROWS_PER_CHUNK
        for i, start in enumerate(range(0, len(df), rpc)):
            md = df.iloc[start:start + rpc].to_markdown(index=False)
            if md and md.strip():
                out.append({**base, "strategy": "table", "idx": i, "text": md})

        # column_wise -- one chunk per column paired with row identifier, best for targeted lookups
        # Previously stored only raw values; now includes the identifier so the LLM knows
        # which row each value belongs to (e.g. "West: 4500 | East: 3600 | North: 1200").
        for i, col_name in enumerate(df.columns):
            if col_name == id_col:
                # Resolve ID codes to names in the identifier column list
                vals = [
                    f"{v} ({id_lookup[v]})" if id_lookup.get(v) else v
                    for v in df[col_name].dropna().astype(str).str.strip().tolist()
                ]
                text = f"Column: {col_name}\nValues: {', '.join(vals)}"
            else:
                paired = df[[id_col, col_name]].dropna(subset=[col_name])
                pairs = []
                for _, r in paired.iterrows():
                    id_val = str(r[id_col]).strip()
                    label = f"{id_val} ({id_lookup[id_val]})" if id_lookup.get(id_val) else id_val
                    pairs.append(f"{label}: {str(r[col_name]).strip()}")
                text = f"Column: {col_name} (by {id_col})\n" + " | ".join(pairs)
            if text.strip():
                out.append({**base, "strategy": "col", "idx": i, "text": text})

        # aggregate -- pre-computed highest/lowest/total per numeric column
        agg = _aggregate_chunk(df, id_col, sheet, base)
        if agg:
            out.append(agg)

    wb.close()
    return out
