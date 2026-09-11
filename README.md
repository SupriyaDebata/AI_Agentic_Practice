# RAG Chat — Document Q&A with Quality Gate Evaluation

Upload PDF/Excel files, ask questions, and evaluate your RAG pipeline against a golden dataset with binary 1.0 / 0.0 scoring and a leadership-ready scorecard.

---

## What This Project Does

| Layer | What Happens |
|-------|-------------|
| **Upload** | PDF/Excel → parsed → chunked → embedded → stored in ChromaDB |
| **Chat** | Question → dual-pass semantic search → Ollama LLM → grounded answer |
| **Quality Gate** | 6 RAGAS-style metrics per answer — binary **1.0 PASS** or **0.0 FAIL** |
| **Evaluation** | Run all 28 golden Q&A pairs live — scorecard + failure root-cause analysis |

---

## Quick Start

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) installed and `llama3.1` model pulled
- 8 GB RAM minimum

### 1. Install

```bash
cd 02-RAG-chat-on-document
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Start Ollama (separate terminal, keep running)

```bash
ollama serve
# Shows: Listening on 127.0.0.1:11434
```

### 3. Launch the App

```bash
streamlit run app.py
```

Opens at **http://localhost:8501**

---

## Demo Flow 1 — Chat with Documents

### Step 1: Upload Documents

In the left sidebar → **📁 Document Management**:

1. Click **"Select PDF or Excel files"**
2. Pick one or more files from `data/pdf/` or `data/excel/`
3. Click **📤 Upload & Process**
4. Wait for the green `✅ filename: N chunks` confirmation

**Available sample documents:**

| File | Contents |
|------|---------|
| `Employee_Handbook.pdf` | Annual leave, sick leave, benefits |
| `Company_Policy.pdf` | Security, expenses, travel policy |
| `Product_Specification.pdf` | Smart thermostat specs, warranty |
| `Sales_Data.xlsx` | Regional sales figures |
| `Customer_Data.xlsx` | Customer records |

### Step 2: Ask a Question

In the main panel → **💬 Ask Your Question**:

```
How many days of annual leave do full-time employees receive?
What is the warranty period for the thermostat?
Which region has the highest sales?
What is the CEO's salary?          ← should refuse (not in docs)
```

Click **🔍 Get Answer**.

### Step 3: Read the Results

**Answer panel:**
- ✅ The answer text (grounded in documents)

**Quality Metrics panel — raw score with PASS / FAIL verdict:**

| Metric | Score shown | Delta shows |
|--------|------------|-------------|
| Faithfulness | `0.91` | `PASS (≥0.85)` ← green |
| Answer Relevancy | `0.84` | `PASS (≥0.80)` ← green |
| Context Precision | `0.75` | `PASS (≥0.75)` ← green |
| Context Recall | `0.60` | `FAIL — threshold 0.75` ← red |
| Citation Accuracy | `0.93` | `PASS (≥0.90)` ← green |
| Retrieval F1 | `0.65` | `FAIL — threshold 0.70` ← red |

The **verdict** (PASS / FAIL) is binary — a score either clears the threshold or it does not.
The **value** shown is always the raw metric (0.00 – 1.00) so you can see how close or far it is.

**Grounded Refusal (unanswerable questions):**  
When the bot answers "I could not find this in the provided documents", all 6 metrics score **1.0** automatically — refusing an unanswerable question is the correct, trustworthy behavior.

**Sources panel:**
Each source shows the actual file name, page/sheet, and retrieval relevance score:
```
Source 1: Employee_Handbook.pdf  •  Page/Sheet: 2  •  Relevance: 0.91
```
For refusal answers: "No sources cited — bot refused..."

### Step 4: Chat History

Scroll down to **📜 Chat History**:

- **Metrics Summary tab** — binary pass rate table across all questions asked this session
- **Q&A Details tab** — each question with per-metric binary scores (`1.0 ✅ (raw 0.91)` or `0.0 ❌ (raw 0.60)`)

---

## Demo Flow 2 — Live Dataset Evaluation

### What the Evaluation Does

Runs all **28 golden Q&A pairs** through your RAG pipeline one by one and builds a leadership-ready scorecard.

### Step 1: Upload Documents First (Flow 1, Step 1)

Evaluation requires documents to be indexed. Upload all 5 sample files.

### Step 2: Run Evaluation

Scroll to **🎯 Run Dataset Evaluation** → click **▶️ Run All Dataset**.

You will see:
1. **Progress bar** — question-by-question progress
2. **Status line** — current question being evaluated
3. **6 live metric tiles** — binary pass rate (%) updating after each question
4. **Live scorecard table** — row added for every question as it completes

### Step 3: Read the Scorecard

Each row in the table — raw scores exactly as the deliverable format:

```
Q: warranty period   faithfulness 0.95  relevance 0.92  ctx_recall 1.0    PASS
Q: CEO's salary      (unanswerable)     bot refused → correct              PASS
Q: Q3 West sales     faithfulness 0.60  relevance 0.72  ctx_recall 0.55   FAIL  → retrieval-miss (Excel chunk)
```

| Column | Answered Question | Unanswerable Question |
|--------|-------------------|----------------------|
| Faithfulness | `0.91` | `—` |
| Relevance | `0.84` | `—` |
| Ctx Recall | `0.55` | `—` |
| Ctx Precision | `0.60` | `—` |
| Citation Acc | `0.62` | `—` |
| Retrieval F1 | `0.57` | `—` |
| Result | `FAIL` | `PASS` |
| Note / Reason | `Retrieval-miss — wrong chunks retrieved (Excel chunk)` | `bot refused → correct` |

### Step 4: Leadership Scorecard (appears after run completes)

**5 KPI tiles:**
- Total Questions, Overall Pass Rate, Answerable PASS, Refusal Accuracy, Unanswerable Tests

**Binary pass rate per metric:**

| Metric | Threshold | Pass Rate | Status |
|--------|-----------|-----------|--------|
| Faithfulness | 0.85 | 88% | ✅ Good |
| Answer Relevancy | 0.80 | 76% | ⚠️ Review |
| … | … | … | … |

**Pass rate by difficulty:** Easy / Medium / Hard

**Pass rate by question type:** Direct / Structured Data / Semantic Search / No Answer

**Failure Classification:**

| Category | # Failures | % of Failures | Recommended Fix |
|----------|-----------|--------------|----------------|
| Retrieval | 4 | 57% | Lower SIMILARITY_THRESHOLD or increase TOP_K |
| Generation | 2 | 29% | Strengthen system prompt grounding rules |
| Chunking | 1 | 14% | Raise SIMILARITY_THRESHOLD to filter weak matches |

**Top-5 Failures** — expandable cards each showing:
- Root cause (e.g., "Retrieval-miss — wrong chunks retrieved (Excel chunk)")
- Recommended fix (e.g., "Lower SIMILARITY_THRESHOLD or increase TOP_K in config.py")
- Which metrics failed and their raw scores
- Bot answer preview

---

## The 6 Quality Metrics Explained

### Retrieval Metrics (did we find the right chunks?)

| Metric | Threshold | Measures |
|--------|-----------|---------|
| **Context Precision** | ≥ 0.75 | Fraction of retrieved chunks that are relevant to the question |
| **Context Recall** | ≥ 0.75 | Fraction of required knowledge covered by retrieved chunks |
| **Retrieval F1** | ≥ 0.70 | Harmonic mean of context precision and recall |

### Generation Metrics (did the LLM answer well?)

| Metric | Threshold | Measures |
|--------|-----------|---------|
| **Faithfulness** | ≥ 0.85 | Fraction of answer words that appear in retrieved context (no hallucination) |
| **Answer Relevancy** | ≥ 0.80 | Fraction of question content words addressed in the answer |
| **Citation Accuracy** | ≥ 0.90 | Highest cosine similarity score from the vector store (best source quality) |

### Scoring Rule

```
Metric value shown  =  raw score (0.00 – 1.00)
Verdict             =  PASS  if score ≥ threshold
                       FAIL  if score < threshold
Correct refusal     =  PASS  (all metrics, auto-rewarded)
```

The raw score tells you *how* the answer performed. The verdict tells you whether it cleared the bar.

### Failure Classification

| Category | Triggered By | Fix |
|----------|-------------|-----|
| **Retrieval** | context_recall FAIL, retrieval_f1 FAIL | Lower `SIMILARITY_THRESHOLD`, raise `TOP_K` |
| **Generation** | faithfulness FAIL, answer_relevancy FAIL | Tune system prompt, check chunk content |
| **Chunking** | context_precision FAIL (noisy chunks) | Raise `SIMILARITY_THRESHOLD`, adjust `CHUNK_SIZE` |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Streamlit UI  (app.py)                              │
│  • Chat panel   • Quality metrics   • Eval runner   │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│  RAG Pipeline                                        │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────┐ │
│  │ Doc Processor│  │  Chunker      │  │Embeddings│ │
│  │ PDF / Excel  │→ │ 600 chars     │→ │MiniLM-L6 │ │
│  └──────────────┘  │ 120 overlap   │  └────┬─────┘ │
│                    └───────────────┘       │        │
│                                    ┌───────▼──────┐ │
│                                    │  ChromaDB    │ │
│                                    │  Vector Store│ │
│                                    └───────┬──────┘ │
│  ┌──────────────────────────────┐          │        │
│  │  Dual-Pass Retriever         │◄─────────┘        │
│  │  full question + noun-phrase │  TOP_K=5          │
│  └──────────────┬───────────────┘                   │
│                 │                                    │
│  ┌──────────────▼───────────────┐                   │
│  │  Ollama LLM  (llama3.1)      │                   │
│  │  Streaming   MAX_TOKENS=1500 │                   │
│  └──────────────┬───────────────┘                   │
└─────────────────┼───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│  Quality Gate   (src/evaluation_metrics.py)          │
│  6 heuristic RAGAS-style metrics → binary 1.0 / 0.0 │
│  Grounded refusal detection → auto 1.0              │
│  Failure classification: retrieval / gen / chunking  │
└─────────────────────────────────────────────────────┘
```

---

## Configuration (`src/config.py`)

```python
# ── Retrieval ──────────────────────────────────────
TOP_K                = 5      # chunks retrieved per question
SIMILARITY_THRESHOLD = 0.30    # lower → more results, higher → stricter
CHUNK_SIZE           = 600     # characters per chunk
CHUNK_OVERLAP        = 120     # overlap between consecutive chunks
MAX_CONTEXT          = 12000   # max total context passed to LLM

# ── LLM ───────────────────────────────────────────
OLLAMA_MODEL       = "llama3.1"
OLLAMA_TEMPERATURE = 0.1       # lower = more deterministic
OLLAMA_MAX_TOKENS  = 1500      # longer answers improve faithfulness score

# ── Embedding ──────────────────────────────────────
EMBEDDING_MODEL  = "all-MiniLM-L6-v2"
EMBEDDING_DEVICE = "cpu"       # "cuda" if GPU available

# ── Quality Gate Thresholds ────────────────────────
QUALITY_GATE_THRESHOLDS = {
    "faithfulness":      0.85,
    "answer_relevancy":  0.80,
    "context_precision": 0.75,
    "context_recall":    0.75,
    "citation_accuracy": 0.90,
    "retrieval_f1":      0.70,
}
```

**Tuning tips:**

| Goal | Change |
|------|--------|
| More answers found | Lower `SIMILARITY_THRESHOLD` (try 0.15) |
| Less noise in retrieval | Raise `SIMILARITY_THRESHOLD` (try 0.30) |
| Longer, more complete answers | Raise `OLLAMA_MAX_TOKENS` |
| Faster responses | Lower `TOP_K` (try 5) |
| More context for complex docs | Raise `MAX_CONTEXT` |

---

## Project Structure

```
02-RAG-chat-on-document/
│
├── app.py                          ← Single entry point: chat + evaluation UI
├── requirements.txt
├── README.md
│
├── src/
│   ├── config.py                   ← All tuning parameters and thresholds
│   ├── chat.py                     ← Ollama streaming, grounded prompt
│   ├── retriever.py                ← Dual-pass semantic search
│   ├── vector_store.py             ← ChromaDB read/write ops
│   ├── embeddings.py               ← Sentence-Transformers
│   ├── chunker.py                  ← Text splitting with overlap
│   ├── document_processor.py       ← PDF + multi-strategy Excel ingestion
│   ├── evaluation_metrics.py       ← 6 RAGAS-style heuristic metrics
│   └── quality_gate.py             ← Threshold check → PASS / FAIL
│
├── evaluation/
│   └── datasets/
│       └── golden_qa_v1.0.json     ← 28 golden Q&A pairs
│
├── data/
│   ├── pdf/
│   │   ├── Employee_Handbook.pdf
│   │   ├── Company_Policy.pdf
│   │   └── Product_Specification.pdf
│   └── excel/
│       ├── Sales_Data.xlsx
│       └── Customer_Data.xlsx
│
└── chroma_db/                      ← Vector store (auto-created on first upload)
```

---

## Golden Dataset (`evaluation/datasets/golden_qa_v1.0.json`)

**28 Q&A pairs** covering:

| Source | Questions | Types |
|--------|-----------|-------|
| Employee_Handbook.pdf | 7 | annual leave, sick leave, benefits |
| Company_Policy.pdf | 6 | security, expenses, travel |
| Product_Specification.pdf | 5 | warranty, specs, connectivity |
| Sales_Data.xlsx | 5 | regional sales, top products |
| Customer_Data.xlsx | 2 | customer records |
| Cross-doc / no-answer | 3 | **refusal tests** (`should_refuse: true`) |

**Difficulty split:** 10 easy · 12 medium · 6 hard  
**Refusal questions** (3): CEO salary, external competitor pricing, employee criminal records — bot must refuse all three.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Upload fails | Check Ollama is running: `ollama serve` |
| "0 chunks indexed" | File already indexed — click 🗑️ Clear All Data and re-upload |
| All metrics 0.00 | Bot refused but refusal not detected — answer may start with unexpected phrasing |
| Faithfulness low | LLM added words not in context — the aggregate chunk may not include enough vocabulary |
| Context Recall low | Retrieved chunks don't cover the answer — lower `SIMILARITY_THRESHOLD` or raise `TOP_K` |
| Answer too short | Raise `OLLAMA_MAX_TOKENS` in config (currently 1500) |
| Evaluation stuck | Ollama timeout — check `ollama serve` terminal for errors |
| Module not found | `pip install --upgrade -r requirements.txt` |

---

## Performance

| Operation | Typical Time |
|-----------|-------------|
| App startup (model warm-up) | 3–5 sec |
| Document upload (5 files) | 15–30 sec |
| Single Q&A + 6 metrics | 3–8 sec |
| Full 28-question evaluation | 5–10 min |

---

## Security

- **Local-only** — no data sent to any cloud service
- **No API keys** — uses Ollama running on your machine
- **Privacy-first** — all documents stay on your disk
