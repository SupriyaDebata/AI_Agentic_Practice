"""excel_serializer.py — Three ways to turn a DataFrame into retrievable text chunks."""

import pandas as pd


def row_as_text(df: pd.DataFrame, metadata: dict) -> list[dict]:
    """
    Each row → one chunk: "Col1: val1 | Col2: val2 | ..."
    Best for key-value lookups: "What is Alice's salary?"
    """
    chunks: list[dict] = []
    cols = list(df.columns)

    for row_idx, (_, row) in enumerate(df.iterrows()):
        parts = [
            f"{col}: {row[col]}"
            for col in cols
            if pd.notna(row[col]) and str(row[col]).strip()
        ]
        text = " | ".join(parts)
        if text.strip():
            chunks.append({**metadata, "text": text, "chunk_index": row_idx})

    return chunks


def markdown_table(df: pd.DataFrame, metadata: dict, rows_per_chunk: int = 20) -> list[dict]:
    """
    DataFrame → markdown table split every rows_per_chunk rows.
    Best for comparison questions: "Which row has the highest value?"
    """
    chunks: list[dict] = []
    chunk_idx = 0

    for start in range(0, len(df), rows_per_chunk):
        sub = df.iloc[start: start + rows_per_chunk]
        md = sub.to_markdown(index=False)
        if md and md.strip():
            chunks.append({**metadata, "text": md, "chunk_index": chunk_idx})
            chunk_idx += 1

    return chunks


def column_wise(df: pd.DataFrame, metadata: dict) -> list[dict]:
    """
    Each column → one chunk: "Column: <name>\nValues: a, b, c, ..."
    Best for statistical questions about a single column.
    """
    chunks: list[dict] = []

    for col_idx, col in enumerate(df.columns):
        vals = df[col].dropna().astype(str).tolist()
        if not vals:
            continue
        text = f"Column: {col}\nValues: {', '.join(vals)}"
        chunks.append({**metadata, "text": text, "chunk_index": col_idx})

    return chunks


SERIALIZERS: dict[str, object] = {
    "row_as_text":    row_as_text,
    "markdown_table": markdown_table,
    "column_wise":    column_wise,
}


def serialize_dataframe(df: pd.DataFrame, metadata: dict, format: str = "row_as_text") -> list[dict]:
    """Dispatch a DataFrame to the selected serialization format."""
    fn = SERIALIZERS.get(format, row_as_text)
    return fn(df, metadata)
