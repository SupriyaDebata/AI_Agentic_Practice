# 🚀 Quick Flow Guide (10 Minutes)

## Step 1: Setup (2 min)

```bash
# Terminal 1 - Start Ollama
ollama serve
# Wait for: "Listening on 127.0.0.1:11434"

# Terminal 2 - Start Chat App
cd 02-RAG-chat-on-document
streamlit run app_simple.py
# Opens: http://localhost:8501
```

---

## Step 2: Upload Documents (2 min)

**In Streamlit UI:**

1. Left sidebar → **📁 Document Management**
2. Click **"Select PDF or Excel files"**
3. Choose from `data/pdf/` and `data/excel/`:
   - `Employee_Handbook.pdf` ✓
   - `Company_Policy.pdf` ✓
   - `Product_Specification.pdf` ✓
   - `Sales_Data.xlsx` ✓
   - `Customer_Data.xlsx` ✓
4. Click **📤 Upload & Process**
5. Wait for success: `Total: XX chunks indexed`

**What happens:** PDFs/Excel → chunks (500 chars) → embeddings → ChromaDB

---

## Step 3: Ask Questions (3 min)

**In Streamlit UI:**

1. Main area → **Enter your question:**
   ```
   "How many days of annual leave?"
   ```
2. Click **🔍 Get Answer**
3. See result:
   - ✅ **Answer** (grounded in docs)
   - � **Quality Metrics** (6 RAGAS scores with pass/fail)
   - 📚 **Sources** (which chunks were used)
4. Try more questions:
   - "What employee benefits?"
   - "Which region has highest sales?"
   - "Warranty on thermostat?"
**Scroll down to see:**
- 📜 **Chat History** with tabs for Metrics Summary & Q&A Details
- 🎯 **Golden Q&A Dataset** with 28 test questions and refusal tests
**Live Metrics Displayed:**
- Faithfulness (no hallucinations)
- Answer Relevancy (answers the question)
- Context Precision (chunks relevant)
- Context Recall (enough chunks)
- Citation Accuracy (facts in sources)
- Retrieval F1 (precision & recall balance)

**What happens:** Question → retrieve chunks → LLM generates answer → calculate metrics → display all in UI

---

## Step 4: Evaluate Quality (3 min)

**In Terminal (New window):**

```bash
python evaluate.py
```

**Console output:**

```
📊 Evaluating 28 questions from golden dataset...
================================================================================

[1/28] Q001: How many days of annual leave?...
  ✅ PASS | Faithfulness: 0.92
[2/28] Q002: How many days of sick leave?...
  ✅ PASS | Faithfulness: 0.88
...

================================================================================
📈 EVALUATION SUMMARY
================================================================================

✅ Overall Pass Rate: 92.1%

📊 Metric Averages (Mean):
  answer_relevancy     | Mean: 0.88  Min: 0.65  Max: 0.99  (N=25)
  context_precision    | Mean: 0.87  Min: 0.50  Max: 1.00  (N=25)
  context_recall       | Mean: 0.84  Min: 0.40  Max: 1.00  (N=25)
  faithfulness         | Mean: 0.89  Min: 0.70  Max: 0.98  (N=25)

💾 Report saved: evaluation/reports/evaluation_20260910_130800.json
```

**What happens:** 
- Tests all 28 golden Q&A pairs
- Calculates 8 RAGAS metrics per question
- Shows pass/fail status
- Saves JSON report

---

## 🎨 What the UI Shows

### After Each Question:

```
✅ Answer
How many days of annual leave do full-time employees receive per year?
Full-time employees receive 24 days of annual leave per calendar year.

📊 Quality Metrics
✅ Quality Gate: PASS (Score: Excellent)

[Faithfulness: 0.92]  [Answer Relevancy: 0.88]  [Context Precision: 0.87]
[Context Recall: 0.84]  [Citation Accuracy: 0.91]  [Retrieval F1: 0.85]

📚 Sources
> Source 1: Full-time employees receive 24 days of annual leave...
```

### Chat History:

```
📜 Chat History
1. How many days of annual leave?... ✅ PASS
   Question: How many days of annual leave do full-time employees receive per year?
   Answer: Full-time employees receive 24 days...
   Sources: 1 | Faithfulness: 0.92
   Faithfulness: 0.920 | Relevancy: 0.880
   Ctx Precision: 0.870 | Ctx Recall: 0.840
   Citation Acc: 0.910 | Retrieval F1: 0.850
```

---

| Metric | What It Means | ✅ Target |
|--------|---------------|-----------|
| **Faithfulness** | No hallucinations (answer from docs only) | ≥ 0.85 |
| **Answer Relevancy** | Answers the question asked | ≥ 0.80 |
| **Context Precision** | Retrieved chunks are relevant | ≥ 0.75 |
| **Context Recall** | Found enough relevant chunks | ≥ 0.75 |
| **Citation Accuracy** | Cited facts exist in sources | ≥ 0.90 |
| **Grounded Refusal** | Refuses when no answer exists | = 1.0 |
| **Retrieval F1** | Balance of precision & recall | ≥ 0.70 |
| **Completeness** | Answer is detailed enough | ≥ 0.75 |

---

## 🎯 Full Timeline

| Time | Action | Result |
|------|--------|--------|
| 0:00 | `ollama serve` | LLM ready ✓ |
| 0:30 | `streamlit run app_simple.py` | Chat UI open ✓ |
| 1:00 | Upload 5 docs | 18 chunks indexed ✓ |
| 2:00 | Ask question 1 | Answer + 6 metrics displayed ✓ |
| 2:30 | Ask question 2 | Answer + 6 metrics displayed ✓ |
| 3:00 | Ask question 3 | Answer + metrics + history ✓ |
| 4:00 | Scroll chat history | See all Q&A with metrics ✓ |
| 5:00 | `python evaluate.py` | Tests golden dataset ✓ |
| 8:00 | View results | See summary + pass rate ✓ |
| 10:00 | ✅ DONE | Complete RAG demo ✓ |

---

## 🔧 Troubleshooting

| Issue | Fix |
|-------|-----|
| "ModuleNotFoundError" | Run `pip install -r requirements.txt` |
| Ollama offline | Run `ollama serve` in separate terminal |
| No chunks indexed | Check file format (PDF/Excel only) |
| Empty answer | Check document has relevant content |
| Slow evaluation | First run downloads models (~2GB) |

---

## 📁 File Structure

```
app_simple.py              ← Chat interface
evaluate.py               ← Quality evaluation
data/
  ├─ pdf/                 ← Upload PDFs here
  └─ excel/               ← Upload Excel here
evaluation/
  ├─ datasets/
  │  └─ golden_qa_v1.0.json    ← 28 test Q&A pairs
  └─ reports/             ← Evaluation results
src/
  ├─ chat.py              ← LLM answering
  ├─ embeddings.py        ← Vector embeddings
  ├─ retriever.py         ← Document search
  ├─ evaluation_metrics.py ← RAGAS metrics
  └─ quality_gate.py      ← Pass/fail logic
```

---

## ⚡ Quick Commands

```bash
# Start everything
ollama serve &
streamlit run app_simple.py

# Evaluate
python evaluate.py

# View report
cat evaluation/reports/evaluation_*.json | jq

# Reset everything
rm -rf chroma_db/*
```

---

**Ready? Start at Step 1 → You'll have a working RAG + evaluation in 10 minutes! 🎉**
