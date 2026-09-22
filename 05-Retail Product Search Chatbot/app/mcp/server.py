"""
MCP server for the Retail Product Search Chatbot.

Exposes two tools an LLM agent can call:
  - search_sql_bm25 : SQL hard-filter + BM25 keyword search
  - search_vector   : ChromaDB semantic (vector) search

Compatible with mcp >= 2.x  (MCPServer replaces FastMCP).

Run:
    python -m app.mcp.server
    # or
    mcp run app/mcp/server.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from mcp.server.mcpserver import MCPServer

from app.config import configure_logging, settings, get_logger
from app.models.filters import ProductFilter

configure_logging()  # readable console output + suppress torchvision noise
from app.repositories.sql_repository import SQLProductRepository
from app.retrieval.bm25_retriever import BM25Retriever
from app.retrieval.vector_retriever import VectorRetriever

logger = get_logger(__name__)

# ── Load catalog once at server startup ───────────────────────────────────────

_sql_repo = SQLProductRepository()
_all_products = _sql_repo.get_all(top_k=500)

_bm25 = BM25Retriever()
_bm25.build_index(_all_products)

_vector = VectorRetriever(settings.embedding_model)
_vector.build_index(_all_products)

logger.info("mcp_server_ready", products_loaded=len(_all_products))

# ── MCP server ────────────────────────────────────────────────────────────────

mcp = MCPServer(
    name="retail-product-search",
    description="Hybrid search over kids-clothing catalog: SQL hard-filters + BM25 + ChromaDB vector.",
)


# ── Tool 1: SQL hard-filter → BM25 keyword rank ──────────────────────────────

@mcp.tool()
def search_sql_bm25(
    lexical_query: str,
    category: Optional[str] = None,
    colour: Optional[str] = None,
    gender: Optional[str] = None,
    kids_age: Optional[str] = None,
    brand: Optional[str] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    top_k: int = 10,
) -> str:
    """
    Apply SQL hard-filters then rank the filtered pool with BM25.

    Use for queries with explicit constraints (price, age, gender, brand)
    plus keyword terms like "lion print" or "jacket".

    Returns JSON list of products with bm25_score and rank.
    """
    filters = ProductFilter(
        category=category,
        colour=colour,
        gender=gender,
        kids_age=kids_age,
        brand=brand,
        price_min=price_min,
        price_max=price_max,
    )

    sql_products = _sql_repo.filter(filters, top_k=settings.sql_candidate_k)
    logger.info("tool_sql_filter", matched=len(sql_products), filters=filters.model_dump(exclude_none=True))

    pool = sql_products if sql_products else _all_products

    if sql_products:
        tmp = BM25Retriever()
        tmp.build_index(pool)
        bm25_results = tmp.search(lexical_query, top_k=top_k)
    else:
        bm25_results = _bm25.search(lexical_query, top_k=top_k)

    logger.info("tool_bm25_done", results=len(bm25_results))

    product_map = {p.id: p for p in pool}
    output = []
    for r in bm25_results[:top_k]:
        p = product_map.get(r.product_id)
        if p:
            output.append({**p.model_dump(), "bm25_score": round(r.score, 4), "rank": r.rank})

    return json.dumps(output, ensure_ascii=False)


# ── Tool 2: ChromaDB vector (semantic) search ────────────────────────────────

@mcp.tool()
def search_vector(
    semantic_query: str,
    restrict_to_product_ids: Optional[list[int]] = None,
    top_k: int = 10,
) -> str:
    """
    Semantic search over product descriptions using ChromaDB embeddings.

    Use for occasion/style queries like "birthday party dress" or "cozy winter wear"
    where exact keywords won't match.

    restrict_to_product_ids: optional list of IDs from a prior SQL filter call —
    restricts vector search to that subset so hard constraints stay enforced.

    Returns JSON list of products with similarity_score and rank.
    """
    logger.info(
        "tool_vector_search",
        query=semantic_query,
        restricted_to=len(restrict_to_product_ids) if restrict_to_product_ids else "all",
    )

    vector_results = _vector.search(
        semantic_query,
        top_k=top_k,
        candidate_ids=restrict_to_product_ids,
    )

    logger.info("tool_vector_done", results=len(vector_results))

    if restrict_to_product_ids:
        id_set = set(restrict_to_product_ids)
        product_map = {p.id: p for p in _all_products if p.id in id_set}
    else:
        product_map = {p.id: p for p in _all_products}

    output = []
    for r in vector_results[:top_k]:
        p = product_map.get(r.product_id)
        if p:
            output.append({**p.model_dump(), "similarity_score": round(r.score, 4), "rank": r.rank})

    return json.dumps(output, ensure_ascii=False)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
