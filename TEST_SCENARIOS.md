# ChatOnDocument — Demo Guide & Test Scenarios

Upload any PDF or Excel file → ask questions in plain English → get grounded answers with source citations.

---

## Before You Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Pull and start the local LLM
ollama pull llama3.1
ollama serve          # keep this terminal open

# 3. Verify everything is ready
python verify_setup.py

# 4. Run the app
streamlit run app.py
```

Upload files from `data/pdf/` and `data/excel/`, then use the questions below.

---

## Quick Demo Sequence (5 questions)

Run these in order to show all capabilities in ~3 minutes:

| # | Question | What it demonstrates |
|---|----------|---------------------|
| 1 | How many days of annual leave do employees receive per year? | Direct retrieval from PDF + citation |
| 2 | After how many wrong login attempts will my account be locked out? | Semantic match (doc says "failed authentication attempts") |
| 3 | Which customers are classified as Enterprise segment? | Excel structured data retrieval |
| 4 | What is the operating temperature range of the Smart Thermostat X100? | PDF table extraction |
| 5 | What was the service performance score for Q2 shown in the product chart? | Grounded refusal — chart is image, no OCR, no hallucination |

---

## TC-1 — Direct Question

> Answer is clearly stated in the document. Expect: correct answer + citation.

| Question | Source | Expected answer |
|----------|--------|-----------------|
| What is the operating temperature range of the Smart Thermostat X100? | Product_Specification.pdf, spec table | -10°C to 55°C |
| How many days of annual leave do employees receive per year? | Employee_Handbook.pdf, p.1 | 24 days per calendar year |
| How many characters must a password contain? | Company_Policy.pdf, p.1 | Minimum 12 characters |

---

## TC-2 — Answer Not Present

> Information does not exist in any document. Expect: `"I could not find this in the provided documents."` — no hallucination, no citations.

| Question | Why it is absent |
|----------|-----------------|
| What is the CEO salary? | No salary information in any document |
| What is the retail price of the Smart Thermostat X100? | No pricing information anywhere |
| Who is the head of the security operations team? | Policy names the team, no individual named |

---

## TC-3 — Semantic Search (Different Wording)

> Question uses different words from the document. Expect: correct answer retrieved via semantic similarity.

| Question (rephrased) | Document wording | Expected answer |
|----------------------|-----------------|-----------------|
| What temperatures can this device work in? | "Operating Temperature: -10°C to 55°C" | -10°C to 55°C |
| Can I work remotely for the entire week? | "Work From Home: up to 3 days per week" | No — maximum 3 days per week |
| After how many wrong login attempts is my account locked? | "5 consecutive failed authentication attempts" | 5 attempts |
| What spending limit needs only my manager's sign-off? | "expenses up to INR 10,000 — manager approval only" | Up to INR 10,000 |

---

## TC-4 — Multiple Files / Sheets

> Answer exists in exactly one specific file and sheet. Expect: correct answer + citation naming the right file and sheet.

| Question | Only correct source | Expected answer |
|----------|-------------------|-----------------|
| Which customers are classified as Enterprise segment? | Customer_Data.xlsx → sheet "Customers" | Apex Retail, NorthStar Stores |
| What was the total revenue for the West region? | Sales_Data.xlsx → sheet "Regional Sales" | 840,000 |
| Which product had the highest units sold in Q3? | Sales_Data.xlsx → sheet "Product Sales" | Thermostat X100 — 1,200 units |

---

## TC-5 — Table / Structured Data

> Answer is inside a table or structured data. Support depends on content type.

| Question | Source | Supported? | Expected |
|----------|--------|-----------|----------|
| Which region had the highest Q3 units? | Sales_Data.xlsx → Regional Sales | YES | West — 4,200 units |
| What is the display size of the Smart Thermostat X100? | Product_Specification.pdf, spec table | YES | 4.3 inch LCD |
| What was the service performance score for Q2 in the chart? | Product_Specification.pdf, bar chart (image) | NO — image only, no OCR | Should refuse, not invent a number |

---

## How Excel Is Stored (3 Strategies)

Every row is stored three ways simultaneously — semantic search picks the best representation per question:

| Strategy | Best for | Example |
|----------|----------|---------|
| `row_as_text` | Record lookups | `Region: West \| Q1 Units: 3500 \| Revenue: 840000` |
| `markdown_table` | Comparisons, rankings | Full Markdown table with headers |
| `column_wise` | Aggregates, column-level questions | `Column: Region / Values: East, West, North, South` |

---

## App Capability Summary

| Capability | Status |
|------------|--------|
| PDF body text | Supported — PyMuPDF per page |
| PDF tables | Supported — pdfplumber → Markdown |
| PDF images / charts | Not supported — placeholder stored, LLM refuses |
| Excel rows (all sheets, all strategies) | Supported — row_as_text + markdown_table + column_wise |
| Semantic / synonym matching | Supported — sentence-transformers + dual-search |
| Grounded refusal (answer absent) | Supported — system prompt enforces, citations stripped |
| Cross-sheet relational joins | Not supported — sheets retrieved independently |

---

## RAG Pipeline

```
Upload
  └─ src/document_processor.py   Extract text / tables / Excel rows (3 strategies)
  └─ src/chunker.py              Section-aware chunks (each topic isolated)
  └─ src/embeddings.py           Generate vectors  (all-MiniLM-L6-v2, 384 dims)
  └─ src/vector_store.py         Store in ChromaDB  (cosine similarity)

Ask
  └─ src/retriever.py            Dual-search (full question + noun phrase) → merge → context
  └─ src/chat.py                 Grounded prompt → stream Ollama answer + citations
```
