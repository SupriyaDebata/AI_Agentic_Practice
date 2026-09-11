"""src/config.py -- All configurable values. Change here, applies everywhere."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env", override=False)
except ImportError:
    pass

# -- Ollama --------------------------------------------------------------------
OLLAMA_MODEL       = os.environ.get("OLLAMA_MODEL", "llama3.1")
OLLAMA_URL         = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_TEMPERATURE = 0.1
OLLAMA_MAX_TOKENS  = 1500   # raised: short answers hurt faithfulness word-overlap scoring
OLLAMA_TIMEOUT     = 180

# -- Embedding -----------------------------------------------------------------
EMBEDDING_MODEL  = "all-MiniLM-L6-v2"
EMBEDDING_DEVICE = "cpu"
EMBEDDING_BATCH  = 128

# -- ChromaDB ------------------------------------------------------------------
CHROMA_PATH     = str(Path(__file__).parent.parent / "chroma_db")
CHROMA_METRIC   = "cosine"
COLLECTION_NAME = "chat_documents"

# -- Chunking ------------------------------------------------------------------
CHUNK_SIZE    = 600    # larger chunks preserve more sentence context
CHUNK_OVERLAP = 120    # more overlap prevents losing info at chunk boundaries

# -- Retrieval -----------------------------------------------------------------
TOP_K                = 5     # more candidates → more context passed to LLM
SIMILARITY_THRESHOLD = 0.20   # slightly lower to catch relevant chunks with less overlap
MAX_CONTEXT          = 12000  # room for 5 chunks at ~600 chars each

# -- PDF processing ------------------------------------------------------------
PDF_MIN_TEXT       = 30
PDF_EXTRACT_TABLES = True
PDF_EXTRACT_IMAGES = True

# -- Excel processing ----------------------------------------------------------
EXCEL_ROWS_PER_CHUNK = 20

# -- Prompts -------------------------------------------------------------------
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
    "4. ANSWER FORMAT — CRITICAL:\n"
    "   a) Start DIRECTLY with the answer — no preamble such as 'According to the source', "
    "'Based on the document', 'The context states', or 'From the source'.\n"
    "   b) NEVER answer with a single word or bare name. ALWAYS write a complete sentence "
    "that restates the key part of the question and includes all relevant values. "
    "BAD: 'North'  GOOD: 'The North region has the lowest revenue of 620,000.' "
    "BAD: '24 days'  GOOD: 'Full-time employees receive 24 days of annual leave per calendar year.' "
    "BAD: 'Wi-Fi'  GOOD: 'The Smart Thermostat X100 supports Wi-Fi 2.4 GHz connectivity.' "
    "The answer MUST contain the content words from the question (region, revenue, employees, etc.) "
    "so that a reader can understand the answer without reading the question.\n"
    "   c) Use the EXACT words and phrases from the context — do NOT paraphrase, abbreviate, or "
    "substitute synonyms. Copy numbers, units, model names, and technical terms verbatim. "
    "Include EVERY specific value: measurements, frequencies, temperatures, voltages, periods, codes.\n"
    "   d) Do NOT reference source file names, page numbers, or excerpt labels in your answer.\n"
    "5. If a context excerpt contains text like '[Image/chart' or 'not extractable as text', "
    "the image could not be read. Treat that image's content as absent and apply Rule 3. "
    "Do NOT attempt to guess or describe what the image might contain.\n"
    "6. When reading a Table or Excel excerpt: match every value to its exact column header and "
    "row label. Never transpose or misalign values. "
    "For 'highest/lowest' questions, identify the row where the specified column has the max/min value.\n"
    "7. The question may use different words than the document. Reason about MEANING — "
    "if the context contains the answer under different terminology, extract it clearly "
    "using the document's own wording.\n"
    "8. If multiple source excerpts are provided, use only those that directly answer the question. "
    "Do not blend or guess from unrelated excerpts.\n"
    "9. COMPLETENESS CHECK: Before finishing, re-read your answer and verify that every key fact "
    "from the relevant context excerpt appears in your answer. If you omitted any value, add it."
)

PROMPT_TEMPLATE = (
    "{system}\n\n"
    "CONTEXT:\n{context}\n\n"
    "QUESTION: {question}\n"
    "REMINDER: Write a COMPLETE sentence that includes both the subject from the question "
    "AND the specific values from the context. Never reply with a single word or name only.\n"
    "ANSWER:"
)

NO_ANSWER = "I could not find this in the provided documents."

# -- Evaluation (RAGAS) --------------------------------------------------------
EVALUATION_ENABLED    = False  # Set to True to auto-evaluate after document upload
EVALUATION_MODEL      = os.environ.get("EVALUATION_MODEL", "llama3.1")  # LLM for RAGAS metric scoring
EVALUATION_BASE_URL   = os.environ.get("EVALUATION_BASE_URL", "http://localhost:11434")  # Ollama endpoint
EVALUATION_TEMPERATURE = 0.0   # Deterministic evaluation (vs 0.1 for inference)
RAGAS_BATCH_SIZE      = 10     # Process N questions in parallel for evaluation
EVALUATION_TIMEOUT    = 180    # Timeout for evaluation LLM (seconds)

# -- Quality Gate Thresholds ---------------------------------------------------
QUALITY_GATE_THRESHOLDS = {
    "faithfulness": 0.85,
    "answer_relevancy": 0.80,
    "context_precision": 0.75,
    "context_recall": 0.75,
    "citation_accuracy": 0.90,
    "grounded_refusal": 1.0,
    "retrieval_f1": 0.70,
    "response_completeness": 0.75,
}

# -- Evaluation Dataset Path ---------------------------------------------------
EVALUATION_DATASET_PATH = str(Path(__file__).parent.parent / "evaluation" / "datasets" / "golden_qa_v1.0.json")
EVALUATION_REPORTS_PATH = str(Path(__file__).parent.parent / "evaluation" / "reports")
