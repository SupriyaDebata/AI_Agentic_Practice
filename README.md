# ChatOnDocument — RAG Pipeline

Upload any PDF or Excel file, ask questions in plain English, get grounded answers with source citations. The LLM only answers from what is in the document — it refuses to guess.

---

## File Structure

```
app.py                       Streamlit UI — upload + chat
verify_setup.py              Pre-demo health check (data files + ChromaDB + Ollama)
requirements.txt             Python dependencies
.env.example                 Environment template

src/
    config.py                All settings (model, chunk size, prompts)
    document_processor.py    PDF and Excel extraction
    chunker.py               Section-aware text chunking
    embeddings.py            Sentence-transformer model (cached)
    vector_store.py          ChromaDB operations (cached)
    retriever.py             Dual-search + context assembly
    chat.py                  Ollama LLM streaming

data/
    pdf/     Company_Policy.pdf, Employee_Handbook.pdf, Product_Specification.pdf
    excel/   Customer_Data.xlsx, Sales_Data.xlsx
```

---

## RAG Pipeline

```
STEP 1 — INGEST  (once per document)
──────────────────────────────────────────────────────────────
Upload PDF / Excel
    → detect file type
    → PDF:   extract text per page   (PyMuPDF)
             extract tables           (pdfplumber)  → single chunk per table
             detect images            → placeholder chunk (no OCR)
    → Excel: serialize rows in 3 ways (row_as_text + markdown_table + column_wise)
    → split narrative text into sections then chunks  (section-aware, 800 chars)
    → embed all chunks   (sentence-transformers  all-MiniLM-L6-v2, 384 dims)
    → store in ChromaDB  (cosine distance)
    → skip if already ingested  (SHA-256 hash of name + size + mtime)

STEP 2 — RETRIEVE  (every question)
──────────────────────────────────────────────────────────────
Question
    → dual search: full question vector  +  noun-phrase vector
    → merge results, keep best score per unique chunk
    → assemble context  (top-5 chunks, max 4 000 chars, with source metadata headers)
    → format citations  (source · page/sheet · type)

STEP 3 — GENERATE  (every question)
──────────────────────────────────────────────────────────────
    → build grounded prompt from context + system rules
    → stream answer from Ollama  (llama3.1 at localhost:11434)
    → if answer not found → strip citations, return refusal message
```

---

## Setup

```bash
pip install -r requirements.txt

# Pull and start Ollama
ollama pull llama3.1
ollama serve           # keep this terminal open

# Verify everything is ready
python verify_setup.py

# Run the app
streamlit run app.py
```

Override model or URL without editing code:
```bash
OLLAMA_MODEL=mistral streamlit run app.py
```

---

## Key Settings (`src/config.py`)

| Setting | Default | What it controls |
|---------|---------|-----------------|
| `OLLAMA_MODEL` | `llama3.1` | Local LLM (env override: `OLLAMA_MODEL`) |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformer for 384-dim vectors |
| `CHUNK_SIZE` | `800` | Characters per text chunk |
| `CHUNK_OVERLAP` | `100` | Overlap between adjacent chunks |
| `TOP_K` | `5` | Candidate chunks returned per query |
| `SIMILARITY_THRESHOLD` | `0.0` | No score filter — grounded refusal handles irrelevance |
| `MAX_CONTEXT` | `4000` | Max characters fed to the LLM |

---

## What the App Can and Cannot Do

| Capability | Status |
|------------|--------|
| PDF body text extraction | Supported |
| PDF table extraction | Supported |
| PDF images / charts | Not supported — placeholder stored, LLM refuses |
| Excel rows (all sheets, all strategies) | Supported |
| Semantic / synonym matching | Supported — dual-search with noun-phrase pass |
| Grounded refusal (answer absent) | Supported — system prompt + post-stream guard |
| Cross-sheet relational joins | Not supported — sheets retrieved independently |

---

See [TEST_SCENARIOS.md](TEST_SCENARIOS.md) for the full demo guide and 15-question evaluation set.
