"""
Result models returned from retrieval and the final search response.
"""
from __future__ import annotations

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from app.models.product import Product
from app.models.search import RetrievalRoute


class RetrievalResult(BaseModel):
    """Score + metadata from a single retriever for one product."""
    product_id: int
    
    score: float
    source: Literal["sql", "bm25", "vector", "hybrid"]
    rank: Optional[int] = None


class SearchResult(BaseModel):
    """A ranked product ready to show the user."""
    product: Product
    final_score: float
    sources: List[str] = Field(default_factory=list)  # e.g. ["bm25", "vector"]


class SearchResponse(BaseModel):
    """Top-level response returned by the search service."""
    query: str
    results: List[SearchResult]
    route_used: RetrievalRoute
    total_candidates: int
    latency_ms: Dict[str, float] = Field(default_factory=dict)
    error: Optional[str] = None
