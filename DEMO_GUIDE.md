# ChatOnDocument RAG + Quality Gate Demo Guide

## Quick Start

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Launch Streamlit
streamlit run app.py
```

Then open **http://localhost:8501** in your browser.

---

## Demo Flow (3 Steps)

### 📤 Step 1: Upload Documents

Click **🚀 Upload & Process** to index the sample PDFs and Excel files:
- `data/pdf/Product_Specification.pdf` — Smart Thermostat specs
- `data/pdf/Employee_Handbook.pdf` — Leave, WFH, benefits
- `data/pdf/Company_Policy.pdf` — Security, expense, data classification
- `data/excel/Sales_Data.xlsx` — Regional & product sales
- `data/excel/Customer_Data.xlsx` — Customers & orders

**Result:** 18 chunks indexed into ChromaDB.

---

### 💬 Step 2: Ask Questions

Type a question and click **🔍 Ask Question**. Examples:

✅ **Answerable** (will retrieve + generate):
- "What are the employee benefits?"
- "How many days of annual leave do employees get?"
- "Which region has the highest sales?"
- "What warranty period does the Smart Thermostat X100 have?"

❌ **Unanswerable** (will correctly refuse):
- "What is the CEO's name?" (not in docs)
- "When was the company founded?" (not in docs, despite being in the dataset questions)

**Key:** Each answer is **automatically evaluated silently** using 8 metrics:
- Faithfulness (answer sticks to context)
- Answer Relevancy (addresses the question)
- Context Precision (retrieved chunks are relevant)
- Context Recall (enough context was retrieved)
- Citation Accuracy (facts from context)
- Hallucination Score (no made-up info)
- Retrieval F1 (quality of retrieval)
- Response Completeness (answer is detailed enough)

---

### 📊 Step 3: View Live Quality Metrics

**Immediately after the first question**, scroll down to **📊 RAG Quality Gate**:

#### 📊 Live Metrics Tab
Shows **Session Metrics** based on all your Q&A in this session:
- **✅ QUALITY GATE PASS/FAIL** — overall status
- **KPI Cards** — 4 main metrics with % score vs. threshold
- **Radar Chart** — visual 8-metric comparison vs. thresholds
- **Bar Chart** — sorted by pass/fail per metric
- **Question-Level Table** — breakdown of each Q&A evaluation
- **Download buttons** — export JSON/HTML/CSV

**No need to run a separate evaluation** — it's live as you chat!

---

## Batch Evaluation (Full Dataset)

### 🚀 Run Evaluation Tab
1. Click **🚀 Run Full Evaluation**
2. System tests all 25 golden QA pairs against your RAG pipeline
3. Progress bar updates in real-time
4. Report saves automatically
5. View results in **Live Metrics** tab

**Takes ~2–5 min** depending on document complexity and Ollama speed.

---

## Understanding Your Error

### Why "What are the benefits?" returned "I could not find this in the provided documents"?

**Root cause:** `SIMILARITY_THRESHOLD` was set to **0.50** — too strict.

**Fix applied:**
- Changed to **0.35** in `config.py`
- Now semantically related questions like "benefits" properly retrieve the context chunk with "medical insurance, accidental coverage, employee assistance program"

**Test it:** Re-upload documents and ask again — should now work ✅

---

## Golden Dataset Structure

Located at: `evaluation/datasets/golden_qa_v1.0.json`

```json
[
  {
    "id": 1,
    "question": "How many days of annual leave do full-time employees receive per year?",
    "expected_answer": "Full-time employees receive 24 days of annual leave per calendar year.",
    "contexts": ["Full-time employees receive 24 days of annual leave..."],
    "source_doc": "Employee_Handbook.pdf"
  },
  ...
]
```

**25 questions** across all 5 documents, with:
- ✅ Question text
- ✅ Expected answer (ground truth)
- ✅ Context chunks (for precision/recall scoring)
- ✅ Source document reference

All are **answerable** from the provided documents.

---

## Quality Gate Thresholds

Edit `src/config.py → QUALITY_GATE_THRESHOLDS`:

```python
QUALITY_GATE_THRESHOLDS = {
    "faithfulness": 0.85,           # 85%: no hallucinations
    "answer_relevancy": 0.80,       # 80%: directly addresses question
    "context_precision": 0.75,      # 75%: retrieved chunks are on-topic
    "context_recall": 0.75,         # 75%: retrieved enough context
    "citation_accuracy": 0.90,      # 90%: facts from docs
    "hallucination_score": 1.0,     # 100%: no made-up info
    "retrieval_f1": 0.70,           # 70%: good precision/recall balance
    "response_completeness": 0.75,  # 75%: answer detail level
}
```

**✅ PASS** = all metrics above their threshold  
**❌ FAIL** = any metric below threshold

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Ollama is NOT running" | Open terminal → `ollama serve` |
| No chunks indexed | Click **Upload & Process** after adding files |
| Question returns "I could not find..." | Documents don't contain an answer OR similarity score is too low (try rephrasing) |
| Dashboard shows empty metrics | Ask a question first — metrics are collected live |
| CSV/JSON download is empty | Ensure at least 1 question was asked |

---

## Files Modified for This Fix

| File | Change |
|---|---|
| `src/config.py` | `SIMILARITY_THRESHOLD: 0.50 → 0.35` |
| `src/retriever.py` | Returns 3-tuple: `(context, citations, context_texts)` |
| `src/chat.py` | Returns 3-tuple: `(stream, citations, context_texts)` |
| `src/evaluation_metrics.py` | Fixed retrieval_f1 bug; added citation_scores param |
| `app.py` | Inline evaluation; always-visible dashboard; new unpack |
| `src/streamlit_quality_dashboard.py` | Rewritten with Plotly charts; working batch eval button |
| `src/dataset_manager.py` | Soft validation (contexts optional for evaluation) |
| **Deleted** | 5 orphan files (quality_gate_evaluator, etc.) |
| `evaluation/datasets/golden_qa_v1.0.json` | 25 real Q&A pairs extracted from actual docs |

---

## Next Steps for Your Demo

1. **Clear all** → refresh page
2. **Upload sample docs** → 18 chunks indexed
3. **Ask 2–3 good questions** → answers retrieve + evaluate inline
4. **Show Live Metrics** → radar & bar charts, KPI cards
5. **Click "Run Full Evaluation"** → tests all 25 golden questions
6. **Show report** → pass/fail status, metric scores, downloadable HTML/JSON

**Total demo time:** ~10 minutes + Q&A.

---

## API Examples (for integration)

### Evaluate a Single Q&A Programmatically

```python
from src.chat import get_answer
from src.evaluation_metrics import evaluate_qa_pair

question = "How many days of annual leave do employees get?"
stream, citations, context_texts = get_answer(question, "chat_documents")
answer = "".join(stream)

result = evaluate_qa_pair(
    question=question,
    answer=answer,
    contexts=context_texts,
    citation_scores=[c["score"] for c in citations]
)

print(result["scores"])  # 8 metric scores
print(f"Faithfulness: {result['scores']['faithfulness']:.0%}")
```

### Run Full Dataset Evaluation

```python
from src.evaluator import RAGEvaluator
from src.chat import get_answer

evaluator = RAGEvaluator()

def rag_fn(q):
    stream, citations, ctx = get_answer(q, "chat_documents")
    return "".join(stream), ctx

report = evaluator.evaluate_dataset(rag_fn)
evaluator.save_report(report)
print(f"Quality Gate: {'PASS' if report['quality_gate']['passed'] else 'FAIL'}")
```

---

## Architecture Summary

```
┌─ app.py (Streamlit UI)
│  ├─ Upload docs → chunk → embed → store in ChromaDB
│  ├─ Chat loop → get_answer() → stream to user
│  ├─ Inline eval → evaluate_qa_pair() → store in session state
│  └─ Render dashboard → show live metrics + batch controls
│
├─ src/chat.py → LLM streaming via Ollama
├─ src/retriever.py → Semantic search + dual-pass retrieval
├─ src/embeddings.py → Sentence-Transformers encoding
├─ src/vector_store.py → ChromaDB CRUD
│
├─ src/evaluation_metrics.py → 8-metric evaluation
├─ src/quality_gate.py → Threshold enforcement
├─ src/evaluator.py → Batch evaluation orchestration
├─ src/dataset_manager.py → Golden QA CRUD + validation
│
└─ src/streamlit_quality_dashboard.py → Plotly UI
```

---

**Questions?** Check the dashboard **⚙️ Settings** tab for threshold details and active config.
