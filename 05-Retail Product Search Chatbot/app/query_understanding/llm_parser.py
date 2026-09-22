"""Parse natural language queries into SearchIntent using Ollama llama3.1."""
import json
import re

import ollama

from app.models.search import SearchIntent, RetrievalRoute
from app.models.filters import ProductFilter
from app.config import settings, get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a query parser for a kids clothing catalog search system.
Extract structured search intent from the user's natural language query.

The catalog has these fields:
- category: Dress, T-Shirt, Jeans, Jacket, Shorts, Shoes, Accessories
- price: in Indian Rupees (INR). "under 800", "below 500", "less than 1000", "800 rs", "800 rupees" → price_max
- colour: Red, Blue, Green, White, Yellow, Pink, Purple, Black, Orange, Grey, Multicolour
- kids_age: normalize to nearest range string: "3-4", "5-6", "7-8", "9-10"
- gender: Boy, Girl, Unisex
- brand: Babyhug, FirstCry, HRX, Hopscotch, etc.

Return ONLY valid JSON in this exact format (no markdown, no explanation):
{
  "hard_filters": {
    "category": null or string,
    "price_min": null or number,
    "price_max": null or number,
    "colour": null or string,
    "kids_age": null or string,
    "gender": null or "Boy"/"Girl"/"Unisex",
    "brand": null or string,
    "stock": null or true/false
  },
  "lexical_query": "keywords for BM25 search",
  "semantic_query": "rephrased semantic/occasion/style intent"
}

Examples:
- "red dress under 800 rs" → price_max: 800, colour: "Red", category: "Dress"
- "white birthday frock for girls 7-8 years" → colour: "White", category: "Dress", gender: "Girl", kids_age: "7-8"
- "lion print t-shirt boy" → category: "T-Shirt", gender: "Boy", lexical_query: "lion print t-shirt"
- "same but under 500" (with context of previous red query) → price_max: 500, carry over other filters from context
"""


# ── Regex fallback — runs when LLM fails or returns bad JSON ──────────────────

# (?!\s*[-–]\s*\d) — negative lookahead stops "under 5-6 yrs" matching as price 5
_PRICE_MAX_RE = re.compile(
    r"(?:under|below|less\s+than|within|upto?|max(?:imum)?)\s*₹?\s*(\d{2,})(?!\s*[-–]\s*\d)",
    re.IGNORECASE,
)
_PRICE_MAX_RS_RE = re.compile(
    r"₹\s*(\d{2,})\b|(\d{3,})\s*(?:rs\.?|rupees?|/-)",
    re.IGNORECASE,
)
_PRICE_MIN_RE = re.compile(
    r"(?:above|over|more\s+than|at\s+least|minimum)\s*₹?\s*(\d{2,})(?!\s*[-–]\s*\d)",
    re.IGNORECASE,
)
_COLOUR_RE = re.compile(
    r"\b(red|blue|green|white|yellow|pink|purple|black|orange|grey|gray|multicolou?r)\b",
    re.IGNORECASE,
)
_GENDER_RE = re.compile(r"\b(boy|girl|unisex)\b", re.IGNORECASE)
_AGE_RE = re.compile(r"\b(\d+)\s*[-–to]+\s*(\d+)\s*(?:year|yr|y)?\b", re.IGNORECASE)
_AGE_SINGLE_RE = re.compile(r"\b(\d+)\s*(?:year|yr|y(?:ears?)?)\b", re.IGNORECASE)
_CATEGORY_RE = re.compile(
    r"\b(dress|frock|t-?shirt|tshirt|tee|jeans|shorts|jacket|skirt|dungaree|shirt)\b",
    re.IGNORECASE,
)
_BRAND_RE = re.compile(
    r"\b(babyhug|firstcry|hrx|hopscotch)\b",
    re.IGNORECASE,
)

_COLOUR_MAP = {"gray": "Grey", "multicolor": "Multicolour", "multicolour": "Multicolour"}
_CATEGORY_MAP = {
    "frock": "Dress", "tshirt": "T-Shirt", "tee": "T-Shirt",
    "t-shirt": "T-Shirt", "shirt": "T-Shirt",
}
_BRAND_MAP = {
    "babyhug": "Babyhug", "firstcry": "FirstCry",
    "hrx": "HRX", "hopscotch": "Hopscotch",
}
_AGE_RANGES = [(3, 4, "3-4"), (5, 6, "5-6"), (7, 8, "7-8"), (9, 10, "9-10")]


def _nearest_age_range(age: int) -> str:
    best = min(_AGE_RANGES, key=lambda r: abs((r[0] + r[1]) / 2 - age))
    return best[2]


def _regex_filters(query: str) -> ProductFilter:
    """Extract filters from the query using regex — used as fallback."""
    kw = {}

    m = _PRICE_MAX_RE.search(query)
    if m:
        kw["price_max"] = float(m.group(1))
    else:
        m = _PRICE_MAX_RS_RE.search(query)
        if m:
            # two capture groups: ₹NNN or NNN rs
            kw["price_max"] = float(m.group(1) or m.group(2))

    m = _PRICE_MIN_RE.search(query)
    if m:
        kw["price_min"] = float(m.group(1))

    m = _COLOUR_RE.search(query)
    if m:
        raw = m.group(1).lower()
        kw["colour"] = _COLOUR_MAP.get(raw, raw.capitalize())

    m = _GENDER_RE.search(query)
    if m:
        kw["gender"] = m.group(1).capitalize()

    # Age range "7-8 years" takes priority over single age
    m = _AGE_RE.search(query)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        kw["kids_age"] = _nearest_age_range((lo + hi) // 2)
    else:
        m = _AGE_SINGLE_RE.search(query)
        if m:
            kw["kids_age"] = _nearest_age_range(int(m.group(1)))

    m = _CATEGORY_RE.search(query)
    if m:
        raw = m.group(1).lower()
        kw["category"] = _CATEGORY_MAP.get(raw, raw.capitalize())

    m = _BRAND_RE.search(query)
    if m:
        raw = m.group(1).lower()
        kw["brand"] = _BRAND_MAP.get(raw, raw.capitalize())

    return ProductFilter(**kw)


def _merge_filters(llm: ProductFilter, regex: ProductFilter) -> ProductFilter:
    """Fill any null LLM fields with regex-extracted values."""
    data = llm.model_dump()
    for field, value in regex.model_dump().items():
        if data.get(field) is None and value is not None:
            data[field] = value
    return ProductFilter(**data)


class LLMQueryParser:
    def __init__(self):
        self._client = ollama.Client(host=f"http://{settings.ollama_host}:{settings.ollama_port}")

    def parse(self, query: str, conversation_context: str = "") -> SearchIntent:
        """Parse query into SearchIntent. Always applies regex as safety net."""
        regex_filters = _regex_filters(query)
        logger.debug("regex_fallback_extracted", filters=regex_filters.model_dump())

        try:
            prompt = f"Query: {query}"
            if conversation_context:
                prompt = f"Previous context:\n{conversation_context}\n\nCurrent query: {query}"

            response = self._client.chat(
                model=settings.ollama_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                options={"temperature": settings.llm_temperature},
            )

            content = response.message.content.strip()
            m = re.search(r"```(?:json)?\s*(.*?)```", content, re.DOTALL)
            if m:
                content = m.group(1).strip()

            data = json.loads(content)
            llm_filters = ProductFilter(
                **{k: v for k, v in data.get("hard_filters", {}).items() if v is not None}
            )
            logger.debug("llm_parsed_successfully", filters=llm_filters.model_dump())
            
            # Merge: regex fills any gap the LLM missed
            filters = _merge_filters(llm_filters, regex_filters)
            logger.debug("filters_merged", final_filters=filters.model_dump())

            intent = SearchIntent(
                hard_filters=filters,
                lexical_query=data.get("lexical_query", query),
                semantic_query=data.get("semantic_query", query),
            )
            logger.info(
                "query_parsed_with_llm",
                user_query=query,
                hard_filters=filters.model_dump(),
                lexical_query=intent.lexical_query,
                semantic_query=intent.semantic_query,
            )

        except Exception as e:
            # LLM failed — use regex filters + raw query for BM25/vector
            logger.warning(
                "llm_parsing_failed_using_regex",
                error=str(e),
                regex_filters=regex_filters.model_dump(),
            )
            intent = SearchIntent(
                hard_filters=regex_filters,
                lexical_query=query,
                semantic_query=query,
            )

        intent.route = _decide_route(intent)
        logger.info(
            "retrieval_route_decided",
            route=intent.route.value,
        )
        return intent


def _decide_route(intent: SearchIntent) -> RetrievalRoute:
    has_filters = intent.hard_filters.has_any_filter()
    has_lexical = bool(intent.lexical_query)
    has_semantic = bool(intent.semantic_query)

    if has_filters and has_lexical and has_semantic:
        return RetrievalRoute.SQL_BM25_VECTOR
    elif has_filters and has_semantic:
        return RetrievalRoute.SQL_VECTOR
    elif has_filters and has_lexical:
        return RetrievalRoute.SQL_BM25
    elif has_filters:
        return RetrievalRoute.SQL_ONLY
    elif has_lexical and has_semantic:
        return RetrievalRoute.BM25_VECTOR
    elif has_semantic:
        return RetrievalRoute.VECTOR_ONLY
    else:
        return RetrievalRoute.BM25_VECTOR
