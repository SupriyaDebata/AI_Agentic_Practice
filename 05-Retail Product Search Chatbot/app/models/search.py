"""
Search-related models: SearchIntent, SearchRequest, ConversationState.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.filters import ProductFilter


class RetrievalRoute(str, Enum):
    """Which retrievers the agent should invoke."""
    SQL_ONLY = "SQL_ONLY"
    BM25_ONLY = "BM25_ONLY"
    VECTOR_ONLY = "VECTOR_ONLY"
    SQL_BM25 = "SQL_BM25"
    SQL_VECTOR = "SQL_VECTOR"
    BM25_VECTOR = "BM25_VECTOR"
    SQL_BM25_VECTOR = "SQL_BM25_VECTOR"


class SearchIntent(BaseModel):
    """
    Structured output produced by LLM query understanding.

    This is the contract between query understanding and retrieval.
    Hard filters go to SQL. Queries go to BM25 and vector retrievers.
    """
    hard_filters: ProductFilter = Field(default_factory=ProductFilter)
    lexical_query: str = Field(
        default="",
        description="Keywords for BM25 exact matching",
    )
    semantic_query: str = Field(
        default="",
        description="Concepts for vector semantic search",
    )
    route: Optional[RetrievalRoute] = None
    top_k: int = 5


class ConversationTurn(BaseModel):
    role: str          # "user" or "assistant"
    content: str


class ConversationState(BaseModel):
    """
    State persisted across turns in a conversation session.

    Follow-up queries merge new constraints with this state rather than
    starting from scratch.
    """
    session_id: str
    history: List[ConversationTurn] = Field(default_factory=list)
    last_intent: Optional[SearchIntent] = None
    last_results: List[Dict[str, Any]] = Field(default_factory=list)

    def add_turn(self, role: str, content: str) -> None:
        self.history.append(ConversationTurn(role=role, content=content))
