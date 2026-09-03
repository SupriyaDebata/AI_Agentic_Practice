"""src/config.py — All configurable values. Change here, applies everywhere."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env", override=False)
except ImportError:
    pass

# ── Ollama ────────────────────────────────────────────────────────────────────
OLLAMA_MODEL       = os.environ.get("OLLAMA_MODEL", "llama3.1")
OLLAMA_URL         = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_TEMPERATURE = 0.1
OLLAMA_MAX_TOKENS  = 800
OLLAMA_TIMEOUT     = 120

# ── Embedding ─────────────────────────────────────────────────────────────────
EMBEDDING_MODEL  = "all-MiniLM-L6-v2"
EMBEDDING_DEVICE = "cpu"
EMBEDDING_BATCH  = 128

# ── ChromaDB ──────────────────────────────────────────────────────────────────
CHROMA_PATH     = str(Path(__file__).parent.parent / "chroma_db")
CHROMA_METRIC   = "cosine"
COLLECTION_NAME = "chat_documents"

# ── Chunking ──────────────────────────────────────────────────────────────────
CHUNK_SIZE    = 800
CHUNK_OVERLAP = 100

# ── Retrieval ─────────────────────────────────────────────────────────────────
TOP_K                = 5
SIMILARITY_THRESHOLD = 0.25  # chunks below this score are not sent to the LLM
MAX_CONTEXT          = 4000  # max chars assembled into the LLM prompt

# ── PDF processing ────────────────────────────────────────────────────────────
PDF_MIN_TEXT       = 30
PDF_EXTRACT_TABLES = True
PDF_EXTRACT_IMAGES = True

# ── Excel processing ──────────────────────────────────────────────────────────
EXCEL_ROWS_PER_CHUNK = 20

# ── Prompts ───────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "You are a document assistant. Answer questions using ONLY the retrieved context below.\n\n"
    "Rules:\n"
    "1. Answer strictly from the context excerpts provided. Never invent or infer numbers, names, "
    "dates, or values not explicitly present in the text.\n"
    "2. Do NOT use your training data or general knowledge under any circumstances. "
    "If the answer is not explicitly stated in the context excerpts, treat it as absent and apply Rule 3.\n"
    "3. If after checking ALL excerpts the answer is genuinely not present, respond with exactly:\n"
    "   I could not find this in the provided documents.\n"
    "   Do NOT add any citation, explanation, or extra text after this sentence.\n"
    "4. If a context excerpt contains text like '[Image/chart' or 'not extractable as text', "
    "the image could not be read. Treat that image's content as absent and apply Rule 3. "
    "Do NOT attempt to guess or describe what the image might contain.\n"
    "5. When reading a Table or Excel excerpt: match every value to its exact column header and "
    "row label. Never transpose or misalign values. "
    "For 'highest/lowest' questions, identify the row where the specified column has the max/min value.\n"
    "6. The question may use different words than the document. Reason about MEANING — "
    "if the context contains the answer under different terminology, extract it clearly.\n"
    "7. If multiple source excerpts are provided, use only those that directly answer the question. "
    "Do not blend or guess from unrelated excerpts."
)

PROMPT_TEMPLATE = "{system}\n\nCONTEXT:\n{context}\n\nQUESTION: {question}\nANSWER:"

NO_ANSWER = "I could not find this in the provided documents."
