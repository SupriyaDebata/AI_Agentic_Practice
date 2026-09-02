# ChatOnDocument Sample Data — Comprehensive Guide

## ✅ Setup Complete

Your **ChatOnDocument** RAG pipeline now has fully-prepared sample data that demonstrates all key engineering challenges in document retrieval and citation.

---

## 📊 What Was Created

### 1. **sample_report.pdf** (3 pages)
A realistic annual report with multiple content types:

- **Page 1: Executive Summary**
  - Company name: ACME Corporation
  - Annual report year: 2024
  - Total revenue: $282,000
  - CFO: Grace Kim
  - 2025 revenue target: $360,000

- **Page 2: Tables & Data**
  - **Sales Performance Table**: Quarterly breakdown of 3 products
    - Widget Alpha, Gadget Pro, Tech Suite
    - Q1-Q4 data with annual totals
  - **Inventory Status Table**: Product status (OK / LOW)
    - Product ID, units in stock, reorder points

- **Page 3: Performance Analysis**
  - Text-based chart representation (visualization data)
  - Key business insights and trends

### 2. **sample_data.xlsx** (3 sheets)
Multi-sheet Excel workbook with tabular data:

| Sheet | Rows | Purpose | Key Data |
|-------|------|---------|----------|
| **quarterly** | 3 products | Sales by quarter | Widget Alpha Q3: $18,000; Gadget Pro total: $119,000 |
| **employee** | 4 employees | Staff directory | Alice Johnson: Engineering, $95,000 |
| **inventory** | 3 items | Stock status | Gadget Pro (gp-010): LOW status |

---

## 🎯 Test Coverage Map

These samples are designed to pass all **15 test questions** in `test_questions.json`:

### Text Questions (T1-T5) ✓
```
T1: Company name → "ACME Corporation" (Page 1)
T2: Report year → "2024" (Page 1)
T3: Total revenue → "$282,000" (Page 1, Page 2 table total)
T4: CFO name → "Grace Kim" (Page 1)
T5: 2025 target → "$360,000" (Page 1)
```

### Table Questions (TB1-TB4) ✓
```
TB1: Highest sales → "Gadget Pro $119,000" (Page 2 table)
TB2: Widget Alpha Q3 → "$18,000" (Page 2 table, monthly breakdown)
TB3: LOW inventory → "Gadget Pro (gp-010)" (Page 2 inventory table)
TB4: Total all products → "$282,000" (Page 2 table footer)
```

### Image/Chart Questions (I1-I3) ✓
```
I1: Contains charts? → YES (Page 3 Performance Chart)
I2: Chart page number? → "Page 3"
I3: Chart description → Requires vision/OCR (intentional failure case)
```

### Excel Questions (E1-E3) ✓
```
E1: Sheet names → ["quarterly", "employee", "inventory"]
E2: Alice details → "Engineering, $95,000"
E3: Inventory products → "Widget Alpha, Gadget Pro, Tech Suite with units"
```

---

## 🏗️ The Three Engineering Challenges

### Challenge 1: PDF Table Extraction
**Question**: Can the RAG system extract and cite table cells accurately?

**Test Case**: "What were the Q3 sales for Widget Alpha?"
- **Expected Answer**: $18,000 with citation to [sample_report.pdf, Page 2, Sales Table]
- **Why It Matters**: Tables are complex structures; naive text splitting loses cell relationships
- **Chunking Strategy**: `section_aware` chunker should preserve table structure as semantic units
- **Success Metric**: Retrieved chunk contains complete row/column context, not fragmented cells

**Data in PDF**:
```
Sales Performance by Product (2024)
Product          | Q1      | Q2      | Q3      | Q4      | Annual Total
Widget Alpha     | $15,000 | $16,500 | $18,000 | $19,500 | $69,000
Gadget Pro       | $28,000 | $30,000 | $31,000 | $30,000 | $119,000
Tech Suite       | $12,000 | $13,500 | $14,500 | $15,500 | $55,500
TOTAL            | $55,000 | $60,000 | $63,500 | $65,000 | $282,000
```

---

### Challenge 2: Excel Serialization Format Comparison
**Question**: Which serialization method (row_as_text, markdown_table, or column_wise) retrieves best?

**Test Case**: "What is Alice's salary and department?"
- **Expected Answer**: "Engineering, $95,000" with citation to [sample_data.xlsx, employee sheet]
- **Why It Matters**: Excel serialization dramatically affects retrieval quality
  
**Three Formats Tested**:

1. **row_as_text** (simple):
   ```
   Name: Alice Johnson, Department: Engineering, Salary: 95000, Start Year: 2020
   ```
   ✓ Pro: Minimal tokens
   ✗ Con: Column headers lose context; hard to filter

2. **markdown_table** (structured):
   ```
   | Name | Department | Salary | Start Year |
   |------|------------|--------|------------|
   | Alice Johnson | Engineering | 95000 | 2020 |
   ```
   ✓ Pro: Visual clarity, header preserved
   ✗ Con: More tokens; may not embed well for sparse queries

3. **column_wise** (normalized):
   ```
   Column: Name = [Alice Johnson, Bob Smith, Charlie Davis, Diana Wong]
   Column: Department = [Engineering, Sales, Marketing, Engineering]
   Column: Salary = [95000, 75000, 68000, 92000]
   ```
   ✓ Pro: Groups similar values; reduces duplication
   ✗ Con: Requires join for row context

**Success Metric**: Run `evaluator.py` against all 3 formats; report accuracy by question type

---

### Challenge 3: Chart Image Placeholder (Vision/OCR Readiness)
**Question**: What does the performance chart show?

**Test Case**: Question I3 - "Can you describe the performance chart?"
- **Current Answer**: "GROUNDED_REFUSAL" (chart is text-based, not OCR-able)
- **Why It Matters**: Charts contain critical data that text extraction misses
  - Bar chart → Product revenue breakdown ($69K, $119K, $55.5K)
  - Trend lines → Historical growth patterns
  - Visual encoding → Market dominance perception
  
**Current Approach**: Text representation in PDF
```
2024 Revenue by Product
Widget Alpha:  ████████░░░░░░░░░░░░░░░░░░ $69,000  (24%)
Gadget Pro:    ██████████████████░░░░░░░░ $119,000 (42%)
Tech Suite:    ███████░░░░░░░░░░░░░░░░░░░░ $55,500  (20%)
```

**Future Enhancement**: Embed actual chart images → triggers Ollama vision model or external OCR

---

## 📋 How to Use

### 1. Start the Streamlit App
```bash
streamlit run app.py
```

### 2. Tab 1: Upload & Ingest
- **Upload**: Select `data/sample_report.pdf` and `data/sample_data.xlsx`
- **Chunk Strategy**: Choose one:
  - `fixed` — splits on exact token count (baseline)
  - `recursive` — preserves logical boundaries (sentences)
  - `section_aware` — keeps tables & sections intact (best for mixed content)
- **Excel Format**: Choose one:
  - `row_as_text` — CSV-like
  - `markdown_table` — structured grid
  - `column_wise` — normalized columns
- **Click**: Ingest Files

### 3. Tab 2: Chat
Ask any of the 15 test questions:
```
Q: What is the total annual revenue for the year?
A: $282,000. [Citation: sample_report.pdf, Page 1, Executive Summary]

Q: Which product had the highest annual total sales?
A: Gadget Pro with $119,000. [Citation: sample_report.pdf, Page 2, Sales Table]

Q: What is Alice's salary and department?
A: Alice Johnson works in Engineering with a salary of $95,000. 
   [Citation: sample_data.xlsx, employee sheet]
```

### 4. Run Evaluation
```bash
python evaluator.py
```

Produces `reports/eval_report_TIMESTAMP.json`:
- Accuracy per source type (text, table, image, excel)
- Latency per question
- Refusal rate
- Recommended best Excel serialization format

---

## 🔍 Data Metadata (Rule 3 Compliance)

Every chunk stored in ChromaDB carries **four mandatory fields**:

```python
{
    "source": "sample_report.pdf",           # Filename
    "page": 2,                               # Page number or sheet name
    "chunk_type": "table",                   # text | table | excel | image_placeholder
    "chunk_index": 0                         # Sequence within source
}
```

Example for Sales Table:
```python
{
    "text": "Product,Q1,Q2,Q3,Q4,Annual Total\nWidget Alpha,$15000...",
    "source": "sample_report.pdf",
    "page": 2,
    "chunk_type": "table",
    "chunk_index": 1
}
```

Example for Excel Row:
```python
{
    "text": "Name: Alice Johnson, Department: Engineering, Salary: 95000",
    "source": "sample_data.xlsx",
    "page": "employee",
    "chunk_type": "excel",
    "chunk_index": 0
}
```

---

## 📈 Expected Accuracy Targets

Based on this sample data structure:

| Question Type | Expected Accuracy | Confidence |
|---------------|-------------------|------------|
| **Text** (T1-T5) | 95%+ | Very High |
| **Table** (TB1-TB4) | 85-90% | High |
| **Image** (I1-I3) | 70% | Medium* |
| **Excel** (E1-E3) | 90%+ | Very High |
| **Overall** | ~85% | High |

*Image accuracy depends on chunker strategy; chart images require OCR/vision model.

---

## 🚀 Next Steps

1. **Run ingest** with different chunk strategies
2. **Run evaluation** with different Excel formats
3. **Measure accuracy** by source type
4. **Identify winner**: Which Excel format retrieves best?
5. **Document learnings** in `sharing-learnings/findings.md`

---

## 📂 File Structure Reference

```
ChatOnDocument/
├── data/
│   ├── sample_report.pdf          ← 3-page annual report (PDF)
│   ├── sample_data.xlsx           ← Multi-sheet workbook (Excel)
│   └── create_sample_data.py      ← (Original generator, kept for reference)
├── chroma_db/                     ← Embedded vector DB (auto-created)
│   └── chroma.sqlite3
├── reports/                       ← Evaluation results (auto-created)
│   └── eval_report_*.json
└── [other project files...]
```

---

## ✅ Checklist

- [x] PDF created with text + tables + chart representation
- [x] Excel created with 3 sheets (quarterly, employee, inventory)
- [x] All 15 test questions covered by sample data
- [x] Metadata fields (source, page, chunk_type, chunk_index) defined
- [x] Engineering challenges clearly mapped to test cases
- [x] Ready for ingest → evaluation workflow

**You're ready to start the RAG pipeline! 🎉**
