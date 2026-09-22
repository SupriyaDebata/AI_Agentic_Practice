# Retail Product Search Chatbot
### Hybrid Agentic RAG — Kids' Clothing Catalog (FirstCry / Babyhug style)

A conversational product-search chatbot combining **SQL**, **BM25**, and **ChromaDB vector search**,
driven by a local LLM (Ollama + llama3.2) that understands natural language queries.
The entire catalog search is also exposed as an **MCP server** so any agent can call it as a tool.

---

## The Problem

A query like **"white birthday dress for a 7–8 year old girl under ₹1000"** has three parts:

| Part | Needs | Why |
|---|---|---|
| `colour=White`, `age=7-8`, `price≤1000` | SQL exact filter | Never approximate a price constraint |
| `birthday`, `festive`, `party` | ChromaDB vector search | Semantic meaning, not just keywords |
| `white dress` | BM25 keyword match | Exact word boost |

No single mode handles all three — this app combines all three.

---

## End-to-End Flow

```
User query
    │
    ▼
LLM Query Parser (llama3.2 via Ollama)
    Extracts: hard_filters | lexical_query | semantic_query | route
    │
    ▼
─── ROUTING ──────────────────────────────────
    │            │                │
    ▼            ▼                ▼
  SQL          BM25          ChromaDB
(SQLite)    (rank-bm25)    (vector store)
exact        keyword        semantic
filters      scoring        similarity
    │            └──────┬───────┘
    │                   ▼
    │            RRF Fusion  (1 / (60 + rank))
    │                   │
    └───────────────────┘
                        │
                        ▼
                  Top-5 Products → Chat UI
```

---

## MCP Server

The catalog search is wrapped as an **MCP server** (`app/mcp/server.py`) with two tools:

| Tool | What it does |
|---|---|
| `search_sql_bm25(lexical_query, filters…)` | SQL hard-filter → BM25 keyword rank on the filtered pool |
| `search_vector(semantic_query, restrict_to_product_ids?)` | ChromaDB cosine similarity, optionally restricted to SQL-filtered IDs |

An LLM agent can call both tools and merge the results — the same routing logic the internal service uses.

Start the MCP server:
```bash
python -m app.mcp.server
# or
mcp run app/mcp/server.py
```

---

## Project Structure

```
05-Retail Product Search Chatbot/
├── app.py                          ← Streamlit entry point
├── app/
│   ├── config/settings.py          ← All config (Ollama host, model, paths)
│   ├── models/                     ← Product, ProductFilter, SearchIntent, results
│   ├── ingestion/                  ← Load & validate products.xlsx
│   ├── repositories/
│   │   └── sql_repository.py       ← SQLite via SQLAlchemy (hard filters)
│   ├── retrieval/
│   │   ├── bm25_retriever.py       ← BM25 keyword search (rank-bm25)
│   │   ├── vector_retriever.py     ← Semantic search (ChromaDB + sentence-transformers)
│   │   └── hybrid_retriever.py     ← RRF fusion
│   ├── query_understanding/
│   │   └── llm_parser.py           ← llama3.2 parses query → SearchIntent
│   ├── services/
│   │   └── catalog_service.py      ← Orchestrates all retrieval steps
│   └── mcp/
│       └── server.py               ← MCP server (2 tools: sql_bm25, vector)
├── scripts/
│   ├── create_dataset.py           ← Generates data/products.xlsx (~75 products)
│   └── ingest.py                   ← Loads xlsx → SQLite catalog.db
├── data/
│   ├── products.xlsx               ← Kids clothing catalog
│   ├── catalog.db                  ← SQLite database
│   └── chroma_store/               ← ChromaDB persisted vector store
└── requirements.txt
```

---

## Quick Start

```bash
# 1. Pull the model
ollama pull llama3.2

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate the product catalog
python scripts/create_dataset.py

# 4. Ingest into SQLite
python scripts/ingest.py

# 5. Run the Streamlit app
streamlit run app.py

# Optional: run the MCP server separately
python -m app.mcp.server
```

---

## Sample Queries

| Query | Route | How it works |
|---|---|---|
| `white dress for 7-8 year girl for birthday` | SQL_BM25_VECTOR | SQL: colour=White, age=7-8, gender=Girl → vector: "festive party dress" |
| `boy t-shirt with lion print` | SQL_BM25_VECTOR | SQL: gender=Boy → BM25: "lion print" + vector: "animal print" |
| `same but under 500 rupees` | SQL_BM25_VECTOR | Adds price_max=500 from conversation context |
| `something cozy for cold weather` | BM25_VECTOR | No hard filters → pure semantic |
| `Babyhug jackets for 5-6 year boys` | SQL_BM25_VECTOR | SQL: brand=Babyhug, age=5-6, gender=Boy + BM25: "jacket" |

---

## Key Design Rules

1. **LLM never writes SQL** — LLM outputs a `ProductFilter` object → SQLAlchemy builds safe parameterised queries
2. **Hard constraints stay hard** — price < 500 means no product over ₹500 ever appears
3. **Gender expands to Unisex** — "boy" query returns Boy AND Unisex products
4. **ChromaDB restricts by SQL IDs** — vector search on the filtered pool keeps hard constraints intact
5. **RRF fusion** — `score = 1/(60 + rank)`, avoids scale mixing between BM25 and cosine scores
6. **Regex safety net** — if Ollama is slow/down, regex extracts filters from the raw query

---

## Technology Stack

| Component | Library |
|---|---|
| LLM | Ollama + llama3.2 (local, no API key) |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` |
| Vector store | **ChromaDB** (persistent, cosine space) |
| Keyword search | rank-bm25 `BM25Okapi` |
| SQL | SQLAlchemy + SQLite |
| MCP | `mcp` (FastMCP) — 2 tools exposed |
| UI | Streamlit |
| Fusion | Reciprocal Rank Fusion (RRF) |

---

## Retrieval Routes

| Route | When | Components |
|---|---|---|
| `SQL_ONLY` | Pure structured query | SQL filter |
| `BM25_VECTOR` | Pure semantic / keyword query | BM25 + ChromaDB → RRF |
| `SQL_BM25` | Filters + keywords | SQL → BM25 on pool |
| `SQL_VECTOR` | Filters + semantic | SQL → ChromaDB on pool |
| `SQL_BM25_VECTOR` | All three (most queries) | SQL → BM25 + ChromaDB → RRF |
