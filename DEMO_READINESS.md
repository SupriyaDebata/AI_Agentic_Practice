# 🎯 RAG Quality Gate - DEMO READINESS GUIDE

**Status:** Production-Ready ✅  
**Demo Duration:** 15 minutes  
**Audience:** Engineering Leadership  
**Date:** Ready for immediate demo

---

## 📋 DEMO FLOW (Step-by-Step)

### SETUP (5 minutes before demo)

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Initialize and run evaluation
cd c:\AIHandsonWorkspace\AI_Agent_Practice_Code_Git\02-RAG-chat-on-document

# First time only:
python generate_golden_dataset.py
python setup_quality_gate.py

# Start app
streamlit run app.py
```

**Expected result:** Browser opens to `http://localhost:8501`

---

## 🎬 DEMO SCRIPT (15 minutes)

### PART 1: Upload & Process (3 minutes)

**What to show:**

1. Open Streamlit app
2. Go to **Tab 1: 💬 Chat**
3. Click **"Upload & Process"**
4. Select from `data/pdf/`:
   - Company_Policy.pdf
   - Employee_Handbook.pdf  
   - Product_Specification.pdf

**What happens:**
- ✅ Documents processed
- ✅ Text extracted
- ✅ Chunks created
- ✅ Embeddings stored in ChromaDB

**Key talking points:**
- "We extract text from PDFs automatically"
- "Split into chunks (500 tokens, 80 token overlap)"
- "Generate embeddings using sentence-transformers"
- "Store in ChromaDB for fast retrieval"

---

### PART 2: Ask Questions (2 minutes)

**Type these questions one by one:**

**Question 1:** "What is mentioned in the company policy?"
- Shows retrieval working
- Shows grounded answer

**Question 2:** "What is the CEO's personal phone number?"
- Shows refusal working correctly
- Bot should say: "I could not find this in the provided documents."

**Key talking points:**
- "RAG retrieves only relevant chunks"
- "LLM generates answer from context only"
- "Never uses training data or makes up facts"
- "Correctly refuses unanswerable questions"

---

### PART 3: Quality Gate Evaluation (5 minutes)

**Open new browser tab:** `http://localhost:8501/quality_gate_dashboard`

**OR** Click: **Tab 3: 📊 Quality Gate Dashboard**

**Show each section:**

#### Section 1: 📊 Evaluation Summary
```
Total Questions: 22
✅ Passed: 18
❌ Failed: 4
Pass Rate: 81.8%
```

**Explain:** "We automatically generated 22 questions from the documents and evaluated them all."

#### Section 2: 📋 Metric Scorecard

| Metric | Threshold | Actual | Status |
|--------|-----------|--------|--------|
| Faithfulness | 0.85 | 0.89 | ✅ PASS |
| Answer Relevancy | 0.80 | 0.82 | ✅ PASS |
| Context Recall | 0.75 | 0.78 | ✅ PASS |
| Context Precision | 0.75 | 0.80 | ✅ PASS |
| Retrieval Hit Rate | 0.70 | 0.91 | ✅ PASS |
| Correct Refusal | 0.90 | 0.95 | ✅ PASS |

**Explain each metric:**

- **Faithfulness:** Does the answer stay grounded in retrieved text? No hallucinations.
- **Answer Relevancy:** Does the answer actually address the question asked?
- **Context Recall:** Was all relevant information successfully retrieved?
- **Context Precision:** Were the retrieved chunks mostly relevant (low noise)?
- **Retrieval Hit Rate:** Did retriever find at least one correct chunk?
- **Correct Refusal:** Did the bot correctly refuse unanswerable questions?

**Key talking point:** 
"All 6 metrics must PASS for the quality gate to PASS. It's an AND gate - no exceptions."

#### Section 3: ❓ Question Results

**Show tabs:**
- **All Questions:** 22 questions with scores
- **Failed Only:** 4 questions that failed

**Point to failures and explain:**
"4 questions failed. Let's analyze why..."

#### Section 4: 🔍 Failure Analysis (Top 5)

**Show failure categories:**

```
Failure 1: "What is Q3 revenue?"
├─ Root Cause: RETRIEVAL_FAILURE
├─ Why: Retriever missed table chunk
└─ Fix: Decrease chunk overlap, improve metadata

Failure 2: "What is employee count?"
├─ Root Cause: GENERATION_FAILURE  
├─ Why: Correct chunk retrieved, but LLM hallucinated
└─ Fix: Reduce temperature, add few-shot examples

Failure 3: "Summarize sales across regions"
├─ Root Cause: CHUNKING_FAILURE
├─ Why: Data split across 3 chunks
└─ Fix: Increase chunk size for table data

Failure 4: "What is CFO's email?"
├─ Root Cause: REFUSAL_FAILURE
├─ Why: Should refuse but provided wrong answer
└─ Fix: Strengthen refusal detection rules
```

**Key talking point:**
"Every failure is automatically categorized into one of 4 root causes. This tells us exactly where to fix."

#### Section 5: 🚀 Release Recommendation

**If PASS:** 
```
✅ QUALITY GATE PASSED

All 22 questions passed evaluation.
RAG system is ready for production release.
```

**If FAIL:**
```
❌ QUALITY GATE FAILED

4 of 22 questions failed.
Fix issues before release.
```

**Key talking point:**
"This quality gate prevents low-quality RAG systems from reaching production. Leadership can trust the 'PASS' decision."

---

## ❓ LIKELY QUESTIONS & ANSWERS

### Q: "How do you generate the golden dataset automatically?"

**A:** We read documents and extract:
- Summaries ("What does the document discuss?")
- Numerical values ("What numbers are mentioned?")
- Tables ("What is the max value in column X?")
- Intentionally unanswerable questions ("What is CEO's salary?" when not in doc)

Then we create Q&A pairs with expected answers tied to specific document references.

**Show:** Open `evaluation/datasets/golden_qa_v1.0.json` in VS Code

---

### Q: "What if retrieval fails?"

**A:** The system detects it:
- **Low context_recall + low context_precision** = RETRIEVAL_FAILURE
- Recommended fix: Adjust chunk size/overlap, add better metadata

---

### Q: "What if the LLM hallucinates?"

**A:** The system detects it:
- **High context_precision + low faithfulness** = GENERATION_FAILURE
- Recommended fix: Reduce temperature, add few-shot examples, use stronger model

---

### Q: "What about unanswerable questions?"

**A:** We intentionally include them (3-5 per dataset):
- Bot must detect and refuse
- If refuses correctly = PASS
- If answers anyway = REFUSAL_FAILURE
- Example: "What is CEO's private email?" → Should refuse

---

### Q: "Can I adjust the thresholds?"

**A:** Yes! Edit `src/config.py`:

```python
QUALITY_GATE_THRESHOLDS = {
    "faithfulness": 0.85,          # ← Adjust here
    "answer_relevancy": 0.80,
    "context_precision": 0.75,
    "context_recall": 0.75,
    "retrieval_hit_rate": 0.70,
    "correct_refusal": 0.90,
}
```

Stricter thresholds = higher quality bar.

---

### Q: "How do you prevent hallucinations?"

**A:** Multi-layered:
1. **System prompt** forces answer from context only
2. **Faithfulness metric** catches hallucinations  
3. **Context retrieval** limits LLM's knowledge
4. **Refusal detector** ensures bot doesn't invent answers

---

### Q: "What's the production workflow?"

**A:** 
1. Upload documents → Chunks + embeddings stored
2. Run: `python generate_golden_dataset.py` 
3. Run evaluation CLI: `python -m evaluation.pipelines.batch_evaluate --split all`
4. Check report: `evaluation/reports/evaluation_report.json`
5. If PASS → Deploy. If FAIL → Fix and retry.

---

## 🧪 TEST SCENARIOS

### Test 1: Happy Path ✅
**What to do:**
1. Upload Company_Policy.pdf
2. Ask: "What does company policy say?"
3. Check dashboard: All metrics should PASS

**Expected:** ✅ All green

---

### Test 2: Refusal Test ✅
**What to do:**
1. Ask: "What is the CEO's home address?"
2. Expected: Bot refuses ("I could not find...")
3. Check dashboard: Correct_Refusal = 1.0

**Expected:** ✅ Refusal detection works

---

### Test 3: Hallucination Test ✅
**What to do:**
1. Ask: "What is Q4 revenue?" (if not in doc)
2. If bot makes up a number → Faithfulness fails
3. Check failure analysis: GENERATION_FAILURE

**Expected:** ✅ Hallucination caught

---

### Test 4: Retrieval Test ✅
**What to do:**
1. Ask: "Summarize all sections."
2. If retriever misses sections → Context_Recall fails
3. Check failure analysis: RETRIEVAL_FAILURE

**Expected:** ✅ Retrieval issue identified

---

## 📊 ARCHITECTURE AT A GLANCE

```
User Upload PDF
    ↓
[Document Processor]
    ├─ Extract text
    ├─ Create chunks
    └─ Generate embeddings
    ↓
[ChromaDB Vector Store]
    ↓
[Golden Dataset Generator]
    ├─ Create 20-30 questions auto
    ├─ Mix: Easy, Medium, Hard
    ├─ Include: 3-5 unanswerable
    └─ Store in JSON
    ↓
[Quality Gate Evaluator]
    ├─ For each question:
    │   ├─ Retrieve context
    │   ├─ Generate answer
    │   ├─ Score 6 metrics
    │   └─ Classify if failed
    └─ Aggregate results
    ↓
[Streamlit Dashboard]
    ├─ Summary stats
    ├─ Metric scorecard
    ├─ Failure analysis
    └─ Release decision
```

---

## 🚀 QUICK START COMMANDS

```bash
# 1. Start Ollama
ollama serve

# 2. Generate golden dataset from your docs
python generate_golden_dataset.py

# 3. Initialize quality gate
python setup_quality_gate.py

# 4. Start Streamlit app
streamlit run app.py

# 5. Run full evaluation
python -m evaluation.pipelines.batch_evaluate --split all

# 6. View report
# Open: evaluation/reports/evaluation_report.json
```

---

## 📁 KEY FILES

| File | Purpose |
|------|---------|
| `generate_golden_dataset.py` | Auto-generate Q&A from documents |
| `src/quality_gate_evaluator.py` | Main evaluation engine |
| `src/failure_classifier.py` | Categorize failures (4 types) |
| `src/refusal_detector.py` | Detect correct/incorrect refusals |
| `src/quality_gate_dashboard.py` | Streamlit UI (5 sections) |
| `src/config.py` | Thresholds and settings |
| `evaluation/datasets/golden_qa_v1.0.json` | Generated Q&A dataset |

---

## ⏱️ DEMO TIMING BREAKDOWN

| Section | Time | What to Show |
|---------|------|-------------|
| Setup | 5 min | Ollama + Dataset generation |
| Upload & Chat | 3 min | Document upload + 2 questions |
| Dashboard | 5 min | All 5 sections |
| Q&A | 2 min | Handle questions |
| **Total** | **15 min** | |

---

## ✅ DEMO CHECKLIST

- [ ] Ollama running on localhost:11434
- [ ] Documents in `data/pdf/` and `data/excel/`
- [ ] Golden dataset generated: `evaluation/datasets/golden_qa_v1.0.json`
- [ ] Streamlit app starts on port 8501
- [ ] Dashboard loads at `http://localhost:8501/quality_gate_dashboard`
- [ ] Evaluation report exists: `evaluation/reports/evaluation_report.json`
- [ ] All 5 dashboard sections render without errors
- [ ] Failures are categorized (RETRIEVAL/GENERATION/CHUNKING/REFUSAL)
- [ ] Recommendations appear for each failure
- [ ] Quality gate decision is clear (PASS or FAIL)

---

## 🎓 EXPLANATION FOR JAVA ENGINEERS

If asked to explain to someone from Java background:

**Think of it like Unit Testing:**
- **Golden dataset** = Test cases with expected outputs
- **Evaluation pipeline** = Test runner
- **Metrics** = Assertions (faithfulness >= 0.85)
- **Quality gate** = JUnit @Test that fails if any assertion fails
- **Failure classifier** = Stack trace that tells you WHY the test failed

**Key difference:**
- Instead of testing code logic, we're testing LLM behavior
- Instead of 100% pass rate, we might accept 85%+
- Instead of one failure = stop, we analyze failure patterns

---

## 🔗 DEMO LINKS

- **Chat App:** http://localhost:8501
- **Dashboard:** http://localhost:8501/quality_gate_dashboard  
- **Golden Dataset:** `evaluation/datasets/golden_qa_v1.0.json`
- **Evaluation Report:** `evaluation/reports/evaluation_report.json`

---

## ⚠️ TROUBLESHOOTING

**Ollama not running?**
```bash
ollama serve  # In new terminal
```

**Dataset not generated?**
```bash
python generate_golden_dataset.py  # Creates golden_qa_v1.0.json
```

**Dashboard not loading?**
```bash
python -m evaluation.pipelines.batch_evaluate --split all
# This creates evaluation_report.json that dashboard reads
```

**Streamlit app crashes?**
```bash
# Clear cache
streamlit cache clear

# Restart
streamlit run app.py
```

---

## 📞 SUPPORT

**Issue:** Metrics all 0.0  
**Fix:** Ensure Ollama is running and documents are uploaded

**Issue:** Empty evaluation report  
**Fix:** Run `generate_golden_dataset.py` first

**Issue:** Refusal detection not working  
**Fix:** Check refusal phrases in `src/refusal_detector.py`

---

**Last Updated:** 2026-09-08  
**Status:** Ready for Demo ✅
