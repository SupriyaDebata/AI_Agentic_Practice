"""Unit tests for domain models (no DB, no LLM, no external services)."""
import pytest
from pydantic import ValidationError

from app.models.product import Product
from app.models.filters import ProductFilter
from app.models.search import SearchIntent, ConversationState, RetrievalRoute
from app.models.results import RetrievalResult, SearchResult, SearchResponse


# ── Product ───────────────────────────────────────────────────────────────────

def make_product(**overrides) -> Product:
    base = dict(
        id=1,
        category="Dress",
        product_name="Floral Party Frock",
        description="Girls white frilly frock, great for parties",
        price=899.0,
        size="7-8Y",
        colour="White",
        kids_age="7-8",
        gender="Girl",
        brand="Babyhug",
        stock=True,
    )
    base.update(overrides)
    return Product(**base)


def test_product_valid():
    p = make_product()
    assert p.id == 1
    assert p.price == 899.0
    assert p.gender == "Girl"


def test_product_price_must_be_positive():
    with pytest.raises(ValidationError):
        make_product(price=-10)


def test_product_price_zero_rejected():
    with pytest.raises(ValidationError):
        make_product(price=0)


def test_product_searchable_text_contains_name_and_description():
    p = make_product()
    text = p.searchable_text()
    assert "Floral Party Frock" in text
    assert "frilly" in text


def test_product_embedding_text():
    p = make_product()
    text = p.to_embedding_text()
    assert "Floral Party Frock" in text


def test_product_invalid_gender():
    with pytest.raises(ValidationError):
        make_product(gender="Unknown")


# ── ProductFilter ─────────────────────────────────────────────────────────────

def test_filter_empty_has_no_filter():
    f = ProductFilter()
    assert not f.has_any_filter()


def test_filter_with_category():
    f = ProductFilter(category="Dress")
    assert f.has_any_filter()


def test_gender_boy_expands_to_include_unisex():
    f = ProductFilter(gender="Boy")
    assert set(f.gender_values()) == {"Boy", "Unisex"}


def test_gender_girl_expands_to_include_unisex():
    f = ProductFilter(gender="Girl")
    assert set(f.gender_values()) == {"Girl", "Unisex"}


def test_gender_unisex_only():
    f = ProductFilter(gender="Unisex")
    assert f.gender_values() == ["Unisex"]


def test_gender_none_returns_none():
    f = ProductFilter()
    assert f.gender_values() is None


def test_filter_negative_price_rejected():
    with pytest.raises(ValidationError):
        ProductFilter(price_max=-1)


# ── SearchIntent ──────────────────────────────────────────────────────────────

def test_search_intent_defaults():
    intent = SearchIntent()
    assert intent.lexical_query == ""
    assert intent.semantic_query == ""
    assert intent.top_k == 5
    assert not intent.hard_filters.has_any_filter()


def test_search_intent_full():
    intent = SearchIntent(
        hard_filters=ProductFilter(colour="White", category="Dress", price_max=1000),
        lexical_query="white birthday dress party",
        semantic_query="birthday party festive frock",
        route=RetrievalRoute.SQL_BM25_VECTOR,
        top_k=5,
    )
    assert intent.hard_filters.colour == "White"
    assert intent.route == RetrievalRoute.SQL_BM25_VECTOR


# ── ConversationState ─────────────────────────────────────────────────────────

def test_conversation_state_starts_empty():
    state = ConversationState(session_id="sess-001")
    assert state.history == []
    assert state.last_intent is None


def test_conversation_state_add_turn():
    state = ConversationState(session_id="sess-001")
    state.add_turn("user", "white dress for 7-8 year old")
    state.add_turn("assistant", "Here are some options…")
    assert len(state.history) == 2
    assert state.history[0].role == "user"


def test_conversation_state_stores_last_intent():
    state = ConversationState(session_id="sess-001")
    intent = SearchIntent(hard_filters=ProductFilter(gender="Boy"))
    state.last_intent = intent
    assert state.last_intent.hard_filters.gender == "Boy"


# ── RetrievalResult ───────────────────────────────────────────────────────────

def test_retrieval_result():
    r = RetrievalResult(product_id=42, score=0.91, source="vector", rank=1)
    assert r.product_id == 42
    assert r.source == "vector"


def test_retrieval_result_invalid_source():
    with pytest.raises(ValidationError):
        RetrievalResult(product_id=1, score=0.5, source="unknown")


# ── SearchResponse ────────────────────────────────────────────────────────────

def test_search_response_no_error():
    resp = SearchResponse(
        query="white dress",
        results=[],
        route_used=RetrievalRoute.SQL_ONLY,
        total_candidates=0,
    )
    assert resp.error is None
    assert resp.results == []
