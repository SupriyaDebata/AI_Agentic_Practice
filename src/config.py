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
EMBEDDING_BATCH  = 64

# ── ChromaDB ──────────────────────────────────────────────────────────────────
CHROMA_PATH     = str(Path(__file__).parent.parent / "chroma_db")
CHROMA_METRIC   = "cosine"
COLLECTION_NAME = "chat_documents"

# ── Chunking ──────────────────────────────────────────────────────────────────
CHUNK_SIZE    = 800
CHUNK_OVERLAP = 100

# ── Retrieval ─────────────────────────────────────────────────────────────────
TOP_K                = 5
SIMILARITY_THRESHOLD = 0.0   # always pass top-K to LLM; grounded refusal handles irrelevance
MAX_CONTEXT          = 4000  # max chars assembled into the LLM prompt

# ── PDF processing ────────────────────────────────────────────────────────────
PDF_MIN_TEXT       = 30
PDF_EXTRACT_TABLES = True
PDF_EXTRACT_IMAGES = True

# ── Excel processing ──────────────────────────────────────────────────────────
EXCEL_ROWS_PER_CHUNK = 20

# ── Prompts ───────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "You are a document assistant. Answer questions using ONLY the retrieved context below.\n"
    "Rules:\n"
    "1. Base every answer strictly on facts stated in the context. Never invent numbers, names, or values.\n"
    "2. The question may use different words than the document. Reason about MEANING, not exact wording.\n"
    "   If the context contains the answer under different wording, extract and state it clearly.\n"
    "3. If after checking all excerpts the answer is genuinely not present, respond with exactly:\n"
    "   I could not find this in the provided documents.\n"
    "   Do NOT add any citation after this sentence.\n"
    "4. When you can answer, end your response with a citation:\n"
    "   [Source: filename, Page/Sheet: value, Section: type]"
)

PROMPT_TEMPLATE = "{system}\n\nCONTEXT:\n{context}\n\nQUESTION: {question}\nANSWER:"

NO_ANSWER = "I could not find this in the provided documents."
