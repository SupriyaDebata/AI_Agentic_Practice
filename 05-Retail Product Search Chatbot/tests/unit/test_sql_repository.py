"""
Unit tests for SQLProductRepository.

Uses an in-memory SQLite database so tests are fast and isolated.
"""
import pytest
from app.repositories.sql_repository import (
    SQLProductRepository, create_tables, _make_engine
)
from app.models.product import Product
from app.models.filters import ProductFilter


IN_MEMORY = "sqlite:///:memory:"


def make_repo() -> SQLProductRepository:
    repo = SQLProductRepository(db_url=IN_MEMORY)
    create_tables(repo._engine)
    return repo


def sample_products() -> list[Product]:
    return [
        Product(id=1, category="Dress", product_name="White Party Frock",
                description="White frilly frock for parties", price=899,
                size="7-8Y", colour="White", kids_age="7-8",
                gender="Girl", brand="Babyhug", stock=True),
        Product(id=2, category="T-Shirt", product_name="Lion Print Tee",
                description="Boys tee with lion face print", price=399,
                size="5-6Y", colour="Yellow", kids_age="5-6",
                gender="Boy", brand="Babyhug", stock=True),
        Product(id=3, category="Dungaree", product_name="Denim Dungaree",
                description="Unisex blue denim dungaree", price=749,
                size="7-8Y", colour="Blue", kids_age="7-8",
                gender="Unisex", brand="Babyhug", stock=True),
        Product(id=4, category="T-Shirt", product_name="Expensive Animal Tee",
                description="Tee with lion and safari animals", price=799,
                size="5-6Y", colour="White", kids_age="5-6",
                gender="Unisex", brand="HRX", stock=True),
        Product(id=5, category="Dress", product_name="Luxury Lace Gown",
                description="White lace gown, premium occasion wear", price=2499,
                size="7-8Y", colour="White", kids_age="7-8",
                gender="Girl", brand="Hopscotch", stock=True),
        Product(id=6, category="T-Shirt", product_name="Out of Stock Tee",
                description="Cool tee that is out of stock", price=299,
                size="5-6Y", colour="Red", kids_age="5-6",
                gender="Boy", brand="FirstCry", stock=False),
    ]


@pytest.fixture
def repo_with_data() -> SQLProductRepository:
    repo = make_repo()
    repo.bulk_insert(sample_products())
    return repo


# ── Schema & insert ───────────────────────────────────────────────────────────

def test_insert_and_get_all(repo_with_data):
    products = repo_with_data.get_all()
    assert len(products) == 6


def test_get_by_ids(repo_with_data):
    products = repo_with_data.get_by_ids([1, 3])
    assert len(products) == 2
    ids = {p.id for p in products}
    assert ids == {1, 3}


# ── Hard constraint: price ────────────────────────────────────────────────────

def test_price_max_filters_correctly(repo_with_data):
    """CRITICAL: price_max=500 must never return a product priced above 500."""
    results = repo_with_data.filter(ProductFilter(price_max=500))
    assert all(p.price <= 500 for p in results), \
        "A product above price_max was returned"


def test_price_min_filters_correctly(repo_with_data):
    results = repo_with_data.filter(ProductFilter(price_min=700))
    assert all(p.price >= 700 for p in results)


def test_price_range(repo_with_data):
    results = repo_with_data.filter(ProductFilter(price_min=400, price_max=800))
    assert all(400 <= p.price <= 800 for p in results)
    assert len(results) > 0


# ── Hard constraint: colour ───────────────────────────────────────────────────

def test_white_filter_returns_only_white(repo_with_data):
    """CRITICAL: colour=White must never return a Blue product."""
    results = repo_with_data.filter(ProductFilter(colour="White"))
    assert all(p.colour == "White" for p in results)
    assert len(results) > 0


# ── Hard constraint: gender + Unisex expansion ────────────────────────────────

def test_boy_filter_includes_unisex(repo_with_data):
    """Boy query should return Boy + Unisex products."""
    results = repo_with_data.filter(ProductFilter(gender="Boy"))
    genders = {p.gender for p in results}
    assert "Boy" in genders
    assert "Unisex" in genders
    assert "Girl" not in genders


def test_girl_filter_includes_unisex(repo_with_data):
    results = repo_with_data.filter(ProductFilter(gender="Girl"))
    genders = {p.gender for p in results}
    assert "Girl" in genders
    assert "Unisex" in genders
    assert "Boy" not in genders


def test_girl_filter_never_returns_boy(repo_with_data):
    results = repo_with_data.filter(ProductFilter(gender="Girl"))
    assert all(p.gender != "Boy" for p in results)


# ── Hard constraint: category ─────────────────────────────────────────────────

def test_category_filter(repo_with_data):
    results = repo_with_data.filter(ProductFilter(category="Dress"))
    assert all(p.category == "Dress" for p in results)
    assert len(results) == 2  # 2 dresses in sample (id=1,5)


# ── Hard constraint: stock ────────────────────────────────────────────────────

def test_in_stock_filter(repo_with_data):
    results = repo_with_data.filter(ProductFilter(stock=True))
    assert all(p.stock for p in results)
    assert len(results) == 5


# ── Combined constraints ──────────────────────────────────────────────────────

def test_white_dress_under_1000(repo_with_data):
    """
    CRITICAL test: white dress for 7-8 year old under 1000.
    Must return White Party Frock (₹899) but NOT Luxury Lace Gown (₹2499).
    """
    results = repo_with_data.filter(ProductFilter(
        colour="White", category="Dress", kids_age="7-8", price_max=1000
    ))
    names = {p.product_name for p in results}
    assert "White Party Frock" in names
    assert "Luxury Lace Gown" not in names


def test_lion_tee_under_500_excludes_expensive(repo_with_data):
    """
    CRITICAL test: lion tee under 500 must not return the ₹799 animal tee.
    """
    results = repo_with_data.filter(ProductFilter(price_max=500))
    ids = {p.id for p in results}
    assert 4 not in ids  # Expensive Animal Tee (₹799) must be excluded


def test_empty_filter_returns_all(repo_with_data):
    results = repo_with_data.filter(ProductFilter())
    assert len(results) == 6


def test_no_results_for_impossible_filter(repo_with_data):
    results = repo_with_data.filter(ProductFilter(colour="Purple", category="Dress"))
    assert results == []
