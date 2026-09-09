# ChatOnDocument with RAG Quality Gate

Upload PDF or Excel files, ask questions in plain English, get grounded answers with source citations and built-in quality monitoring.

**Status:** ✅ Production-Ready | **Demo Ready:** Yes

---

## 📋 What This Project Does

1. **Document Upload** - Ingest PDF or Excel files with automatic text extraction
2. **Semantic Retrieval** - Find relevant document sections using embeddings + dual-search
3. **Grounded Answering** - Stream answers from retrieved context only (no hallucinations)
4. **Source Citations** - Link every answer back to source with page numbers
5. **Quality Evaluation** - Measure RAG quality against 8+ metrics in real-time
6. **Production Dashboards** - View metrics, datasets, and evaluation history

---

## 🚀 End-to-End Setup & Running (5 Minutes)

### Prerequisites

- Python 3.11+ 
- Ollama installed (for local LLM + embeddings)
- 8GB RAM minimum

### Step 1: Install Dependencies

```bash
# Clone or navigate to project directory
cd AI_Agent_Practice_Code_Git/02-RAG-chat-on-document

# Create virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
```

### Step 2: Start Ollama (Required)

Open a **new terminal** and run:

```bash
ollama serve
```

This starts the local LLM and embedding service. You should see:
```
Listening on 127.0.0.1:11434
```

**Note:** Keep this running in the background.

### Step 3: Initialize Quality Gate (First Time Only)

```bash
# Create evaluation directories and sample dataset
python setup_quality_gate.py
```

You should see:
```
✅ Created evaluation reports directory
✅ Created dataset directory
✅ Sample dataset imported successfully!
```

### Step 4: Launch the App

In your original terminal:

```bash
streamlit run app.py
```

The browser opens to `http://localhost:8501`

---

## 🎯 Using the App

### Tab 1: 💬 Chat

1. **Upload Documents**
   - Click "Upload a PDF or Excel file"
   - Select 1+ files
   - Click "Upload & Process"
   - Wait for success messages

2. **Ask Questions**
   - Type your question in the text box
   - Click "Ask" button
   - Stream answer with citations

3. **View Sources**
   - Expand "Sources (N)" below answer
   - See page numbers, relevance scores
   - Verify grounding in documents

### Tab 2: 🎯 Quality Gate

#### **Metrics Tab**
- View latest evaluation results
- See individual metric scores vs thresholds
- Check results by question
- Download reports (HTML, JSON, CSV)

#### **Dataset Tab**
- Import sample QA dataset
- View current questions
- Validate dataset completeness

#### **Evaluation Tab**
- Run evaluation on full dataset or single question
- Monitor progress

#### **History Tab**
- View past evaluation reports
- Compare results over time

#### **Settings Tab**
- View current metric thresholds
- Understand metric definitions
- Configure via `src/config.py`

---

## 📊 Quality Metrics Explained

| Metric | Threshold | Meaning |
|--------|-----------|---------|
| **Faithfulness** | ≥ 0.85 | Answer grounded in context, no hallucinations |
| **Answer Relevancy** | ≥ 0.80 | Answer directly addresses question |
| **Context Precision** | ≥ 0.75 | Retrieved chunks are relevant |
| **Context Recall** | ≥ 0.75 | No important info was missed |
| **Citation Accuracy** | ≥ 0.90 | Cited facts appear in sources |
| **Hallucination Score** | ≥ 0.85 | Inverse of faithfulness |
| **Retrieval F1** | ≥ 0.70 | Balance of precision + recall |

**Quality Gate Status:**
- ✅ **PASS** - All metrics meet thresholds
- ❌ **FAIL** - One or more metrics below threshold

---

## ⚙️ Configuration

### Key Settings (`src/config.py`)

```python
# LLM Configuration
OLLAMA_MODEL = "llama3.1"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_TEMPERATURE = 0.1
OLLAMA_MAX_TOKENS = 800

# Embedding Configuration
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DEVICE = "cpu"

# Retrieval Configuration
TOP_K = 3                      # Retrieved chunks
SIMILARITY_THRESHOLD = 0.50    # Minimum relevance score
CHUNK_SIZE = 500              # Characters per chunk
CHUNK_OVERLAP = 80            # Overlap between chunks

# Quality Gate Thresholds
QUALITY_GATE_THRESHOLDS = {
    "faithfulness": 0.85,
    "answer_relevancy": 0.80,
    "context_precision": 0.75,
    "context_recall": 0.75,
    "citation_accuracy": 0.90,
    "grounded_refusal": 1.0,
    "retrieval_f1": 0.70,
}

# Evaluation Settings
EVALUATION_ENABLED = False     # Auto-evaluate on upload
EVALUATION_MODEL = "llama3.1"
EVALUATION_TEMPERATURE = 0.0   # Deterministic
```

### Modify Thresholds

Edit `QUALITY_GATE_THRESHOLDS` in `src/config.py`, then restart:

```bash
streamlit run app.py
```

---

## 🧪 Validation & Testing

### Quick Validation

```bash
python test_quality_gate.py
```

Expected output:
```
[TEST] RAG Quality Gate - Framework Validation
============================================================
PASS - Imports
PASS - Configuration
PASS - Dataset Manager
PASS - Metrics Calculator
PASS - Quality Gate
```

---

## 📁 Project Structure

```
.
├── app.py                          # Main Streamlit app (Chat + Quality Gate)
├── requirements.txt                # Python dependencies
├── setup_quality_gate.py           # Initialize evaluation framework
├── test_quality_gate.py            # Validation tests
│
├── src/
│   ├── config.py                   # All configurable parameters
│   ├── chat.py                     # LLM interaction
│   ├── retriever.py                # Semantic search
│   ├── vector_store.py             # ChromaDB management
│   ├── embeddings.py               # Embedding generation
│   ├── chunker.py                  # Text chunking
│   ├── document_processor.py        # PDF/Excel extraction
│   │
│   ├── quality_gate.py             # Quality gate logic
│   ├── evaluation_metrics.py        # Metric calculations
│   ├── dataset_manager.py          # Golden QA dataset
│   ├── evaluator.py                # Evaluation orchestration
│   └── streamlit_quality_dashboard.py  # Dashboard UI
│
├── chroma_db/                      # ChromaDB vector store
├── evaluation/
│   ├── datasets/
│   │   └── golden_qa_v1.0.json     # QA dataset for evaluation
│   └── reports/                    # Evaluation reports (JSON/HTML)
└── .env                            # Environment variables (optional)
```

---

## 🔧 Troubleshooting

### "Ollama is not running"
- In a new terminal, run: `ollama serve`
- Keep it running in background during app usage

### "No chunks indexed"
- Upload documents first in Chat tab
- Wait for success messages
- Reload page

### "No evaluation results"
- Import sample dataset (Dataset tab → Import Sample Dataset)
- This takes ~5-30 seconds depending on document size

### "Metrics are low"
- Check documents are relevant to questions
- Verify chunk size isn't too large (`CHUNK_SIZE` in config)
- Review retrieved contexts in Chat tab
- Adjust thresholds if needed

### Import Errors
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Clear cache
rm -rf chroma_db/ __pycache__ .streamlit/
```

---

## 📊 Performance Benchmarks

| Operation | Time |
|-----------|------|
| App startup | 2-3 seconds |
| Document ingestion | ~1-2 sec/page |
| Single question | 2-5 seconds |
| Full evaluation (5 Q's) | 30-60 seconds |
| Dashboard load | ~2 seconds |

---

## 🎯 Quality Gate Workflow

```
1. Upload Documents
   ↓
2. Ask Questions
   ↓
3. Get Answers with Citations
   ↓
4. Import Dataset (Quality Gate Tab)
   ↓
5. Run Evaluation
   ↓
6. Review Metrics
   ↓
7. Pass/Fail Decision
   ↓
8. Download Report
```

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────┐
│    Streamlit UI (Chat + Dashboard)  │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│     RAG Pipeline (Existing)         │
│  - Retrieval (ChromaDB)             │
│  - LLM (Ollama)                     │
│  - Citations                        │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│   Quality Gate Framework (New)      │
│  - Metrics (RAGAS)                  │
│  - Dataset Manager                  │
│  - Quality Gate Logic               │
│  - Reporting & Dashboards           │
└─────────────────────────────────────┘
```

---

## 🔐 Security Notes

- **No credentials stored** - Local-only Ollama usage
- **No data sent to cloud** - Everything runs locally
- **Privacy-first** - All documents stay on your machine
- **Optional authentication** - Can be added to Streamlit via `.streamlit/secrets.toml`

---

## 📈 Next Steps

1. ✅ Complete setup above
2. ✅ Upload test documents (PDF/Excel)
3. ✅ Ask 3-5 test questions
4. ✅ View metrics in Quality Gate tab
5. ✅ Download HTML report for stakeholders
6. ✅ Adjust thresholds if needed
7. ✅ Deploy to production

---

## 🤝 Support

### Common Questions

**Q: Can I use different LLMs?**  
A: Yes, change `OLLAMA_MODEL` in `src/config.py`. Supports any Ollama-compatible model.

**Q: How do I increase quality scores?**  
A: Improve documents (clarity, completeness) or adjust config (`CHUNK_SIZE`, `SIMILARITY_THRESHOLD`, `TOP_K`).

**Q: Can this run without Ollama?**  
A: Yes, with API keys for OpenAI/Claude/Gemini (requires code changes). See `src/config.py` for integration points.

**Q: How is evaluation data stored?**  
A: JSON files in `evaluation/datasets/` and `evaluation/reports/`. Editable with any text editor.

---

## 📝 Version Info

- **Python:** 3.11+
- **Streamlit:** 1.41+
- **ChromaDB:** 0.5+
- **RAGAS:** 0.1+
- **Status:** Production-Ready ✅
- **Last Updated:** 2024-09-08

---

## 🎓 Learning Resources

- [RAGAS Framework](https://ragas.io) - RAG evaluation metrics
- [LangChain Docs](https://python.langchain.com) - LLM orchestration
- [Streamlit Docs](https://docs.streamlit.io) - Dashboard framework
- [ChromaDB Docs](https://docs.trychroma.com) - Vector database

---

## 🚀 Ready to Start?

```bash
# 1. Install
pip install -r requirements.txt

# 2. Start Ollama (new terminal)
ollama serve

# 3. Initialize (original terminal)
python setup_quality_gate.py

# 4. Run
streamlit run app.py
```

Then open http://localhost:8501 and start chatting! 💬

---

**Made with ❤️ for document-based Q&A with quality assurance**
