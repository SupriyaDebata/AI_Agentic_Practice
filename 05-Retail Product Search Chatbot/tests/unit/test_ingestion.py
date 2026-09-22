"""Unit tests for data ingestion and validation."""
import pandas as pd
import pytest

from app.ingestion.validators import validate_dataframe
from app.ingestion.excel_loader import load_products
from app.config.settings import settings


def _base_row(**overrides) -> dict:
    row = dict(
        id=1, category="Dress", product_name="Test Dress",
        description="A nice dress", price=499.0, size="5-6Y",
        colour="White", kids_age="5-6", gender="Girl",
        brand="Babyhug", stock=True,
    )
    row.update(overrides)
    return row


# ── validate_dataframe ────────────────────────────────────────────────────────

def test_valid_row_passes():
    df = pd.DataFrame([_base_row()])
    valid, errors = validate_dataframe(df)
    assert len(valid) == 1
    assert errors == []


def test_invalid_gender_is_rejected():
    df = pd.DataFrame([_base_row(gender="Robot")])
    valid, errors = validate_dataframe(df)
    assert len(valid) == 0
    assert len(errors) == 1


def test_negative_price_is_rejected():
    df = pd.DataFrame([_base_row(price=-100)])
    valid, errors = validate_dataframe(df)
    assert len(errors) == 1


def test_stock_int_coerced_to_bool():
    df = pd.DataFrame([_base_row(stock=1)])
    valid, errors = validate_dataframe(df)
    assert len(valid) == 1
    assert valid[0].stock is True


def test_stock_zero_coerced_to_false():
    df = pd.DataFrame([_base_row(stock=0)])
    valid, errors = validate_dataframe(df)
    assert len(valid) == 1
    assert valid[0].stock is False


def test_mixed_valid_and_invalid():
    df = pd.DataFrame([_base_row(), _base_row(price=-1), _base_row(id=3)])
    valid, errors = validate_dataframe(df)
    assert len(valid) == 2
    assert len(errors) == 1


# ── excel_loader ──────────────────────────────────────────────────────────────

def test_load_products_xlsx():
    """The generated products.xlsx must load cleanly with no errors."""
    products = load_products(settings.products_xlsx)
    assert len(products) >= 50, "Need at least 50 products"
    assert all(p.price > 0 for p in products)
    assert all(p.gender in ("Boy", "Girl", "Unisex") for p in products)


def test_products_have_variety():
    products = load_products(settings.products_xlsx)
    genders = {p.gender for p in products}
    assert "Boy" in genders
    assert "Girl" in genders
    assert "Unisex" in genders


def test_products_cover_multiple_categories():
    products = load_products(settings.products_xlsx)
    categories = {p.category for p in products}
    assert len(categories) >= 5


def test_products_have_price_range():
    products = load_products(settings.products_xlsx)
    prices = [p.price for p in products]
    assert min(prices) < 500
    assert max(prices) > 1000
