# Invoice Field Extractor
**Author:** Supriya Debata | Prompt Engineering Week 1

---

## Quick Start (3 steps)

### Step 1 — Start Ollama
Open a terminal and run:
```bash
ollama serve
```
In a second terminal (first time only):
```bash
ollama pull llama3.1
```

### Step 2 — Install dependencies
In your project folder, with your venv active:
```bash
pip install -r requirements.txt
```

### Step 3 — Launch the UI
```bash
streamlit run app.py
```
Browser opens at **http://localhost:8501**

---

## Project Structure

```
invoice-extractor/
├── app.py              ← Streamlit UI (run this)
├── extractor.py        ← Ollama API calls + JSON parsing
├── pipeline.py         ← CLI: run one invoice / all versions
├── evaluate.py         ← Precision/recall scoring
├── requirements.txt
├── CLAUDE.md           ← Project rules
├── SDD.md              ← Software Design Document
├── invoices/
│   ├── inv-01 ... inv-15   ← 15 test invoices
│   └── ground_truth.json   ← Expected outputs for scoring
├── prompts/
│   ├── v1-zero-shot.md
│   ├── v2-role-context.md
│   ├── v3-few-shot.md
│   ├── v4-cot-xml.md
│   └── v5-self-verify.md
├── outputs/            ← JSON results (auto-created)
└── scorecard/          ← Accuracy tables (auto-created)
```

---

## CLI Usage

```bash
# Extract one invoice with one version
python pipeline.py --invoice invoices/inv-01-clean-usd.txt --version v3

# Run all 5 versions on one invoice
python pipeline.py --invoice invoices/inv-01-clean-usd.txt --all

# Run full evaluation (all 15 invoices × all 5 versions)
python evaluate.py

# Run evaluation for a single version
python evaluate.py --version v4
```

---

## Week 1 Day Plan

| Day | Task |
|-----|------|
| 1 | ✅ Folder structure + 15 invoices created |
| 2 | Run v1 on all 15, check tax hallucination on inv-04/05 |
| 3 | Run v2 and v3, compare with v1 results |
| 4 | Run v4 (CoT + XML), update scorecard |
| 5 | Run v5 (self-verify), generate final scorecard report |

---

## Critical Tests to Watch

| Invoice | Field | Must return |
|---------|-------|-------------|
| inv-04, inv-05, inv-15 | `tax` | `null` — never compute |
| inv-08 | `invoice_date` | `"2024-03-22"` (from `22/03/2024`) |
| inv-11, inv-12 | `tax` | numeric (VAT / GST recognized) |
| inv-15 | `invoice_number` | `null` — never invent |
