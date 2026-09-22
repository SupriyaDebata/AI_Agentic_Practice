"""CatalogSearchService — orchestrates SQL, BM25, and ChromaDB vector search."""
import time

from app.config import settings, get_logger
from app.models.search import SearchIntent, RetrievalRoute
from app.models.results import SearchResult, RetrievalResult, SearchResponse
from app.repositories.sql_repository import SQLProductRepository
from app.retrieval.bm25_retriever import BM25Retriever
from app.retrieval.vector_retriever import VectorRetriever
from app.retrieval.hybrid_retriever import reciprocal_rank_fusion
from app.query_understanding.llm_parser import LLMQueryParser

logger = get_logger(__name__)

_DIVIDER = "─" * 60


def _top_named(results: list[RetrievalResult], product_map: dict, n: int = 3) -> list[str]:
    """Return 'ProductName (score)' strings for the top-n results."""
    out = []
    for r in results[:n]:
        p = product_map.get(r.product_id)
        name = p.product_name if p else f"id={r.product_id}"
        out.append(f"{name} ({round(r.score, 3)})")
    return out


class CatalogSearchService:
    def __init__(self):
        self._sql_repo = SQLProductRepository()
        self._bm25 = BM25Retriever()
        self._vector = VectorRetriever(settings.embedding_model)
        self._parser = LLMQueryParser()
        self._all_products = []
        self._ready = False

    def initialize(self) -> None:
        self._all_products = self._sql_repo.get_all(top_k=500)
        self._bm25.build_index(self._all_products)
        self._vector.build_index(self._all_products)
        self._ready = True
        logger.info("catalog_service_ready", products=len(self._all_products))

    def parse_query(self, query: str, context: str = "") -> SearchIntent:
        return self._parser.parse(query, context)

    def search(self, intent: SearchIntent) -> SearchResponse:
        start = time.time()
        latency: dict = {}
        route = intent.route or RetrievalRoute.BM25_VECTOR

        active_filters = {k: v for k, v in intent.hard_filters.model_dump().items() if v is not None}

        # ── Query banner ──────────────────────────────────────────────────────
        logger.info(_DIVIDER)
        logger.info(
            "QUERY",
            lexical=intent.lexical_query,
            semantic=intent.semantic_query,
            route=route.value,
        )
        if active_filters:
            logger.info("HARD_FILTERS", **active_filters)
        else:
            logger.info("HARD_FILTERS", note="none — full catalog search")

        # ── Step 1: SQL hard-filter ───────────────────────────────────────────
        sql_products = []
        if route in (
            RetrievalRoute.SQL_ONLY,
            RetrievalRoute.SQL_BM25,
            RetrievalRoute.SQL_VECTOR,
            RetrievalRoute.SQL_BM25_VECTOR,
        ):
            t0 = time.time()
            sql_products = self._sql_repo.filter(intent.hard_filters, top_k=settings.sql_candidate_k)
            latency["sql_ms"] = round((time.time() - t0) * 1000, 1)
            sql_names = [p.product_name for p in sql_products[:5]]
            logger.info(
                "[1] SQL",
                matched=len(sql_products),
                top_products=sql_names,
                latency_ms=latency["sql_ms"],
            )

        sql_was_applied = route in (
            RetrievalRoute.SQL_ONLY,
            RetrievalRoute.SQL_BM25,
            RetrievalRoute.SQL_VECTOR,
            RetrievalRoute.SQL_BM25_VECTOR,
        )

        # Hard filters were active but matched nothing — honest no-result response
        if sql_was_applied and not sql_products:
            logger.info("[RESULT] SQL filters matched 0 products — returning empty")
            logger.info(_DIVIDER)
            latency["total_ms"] = round((time.time() - start) * 1000, 1)
            return SearchResponse(
                query=intent.lexical_query or intent.semantic_query,
                results=[],
                route_used=route,
                total_candidates=0,
                latency_ms=latency,
            )

        candidate_pool = sql_products if sql_products else self._all_products
        product_map = {p.id: p for p in candidate_pool}

        # SQL-only: skip retrieval
        if route == RetrievalRoute.SQL_ONLY:
            results = [
                SearchResult(product=p, final_score=1.0 - i * 0.01, sources=["sql"])
                for i, p in enumerate(candidate_pool[: intent.top_k])
            ]
            latency["total_ms"] = round((time.time() - start) * 1000, 1)
            logger.info("[RESULT]", count=len(results), total_ms=latency["total_ms"])
            logger.info(_DIVIDER)
            return SearchResponse(
                query=intent.lexical_query or intent.semantic_query,
                results=results,
                route_used=route,
                total_candidates=len(candidate_pool),
                latency_ms=latency,
            )

        # ── Step 2: BM25 keyword search ───────────────────────────────────────
        bm25_results = []
        if route in (
            RetrievalRoute.BM25_ONLY,
            RetrievalRoute.SQL_BM25,
            RetrievalRoute.BM25_VECTOR,
            RetrievalRoute.SQL_BM25_VECTOR,
        ):
            t0 = time.time()
            if sql_products:
                tmp = BM25Retriever()
                tmp.build_index(candidate_pool)
                bm25_results = tmp.search(intent.lexical_query, top_k=settings.bm25_candidate_k)
            else:
                bm25_results = self._bm25.search(intent.lexical_query, top_k=settings.bm25_candidate_k)
            latency["bm25_ms"] = round((time.time() - t0) * 1000, 1)
            logger.info(
                "[2] BM25",
                query=intent.lexical_query,
                pool_size=len(candidate_pool),
                results=len(bm25_results),
                top=_top_named(bm25_results, product_map),
                latency_ms=latency["bm25_ms"],
            )

        # ── Step 3: ChromaDB vector search ────────────────────────────────────
        vector_results = []
        if route in (
            RetrievalRoute.VECTOR_ONLY,
            RetrievalRoute.SQL_VECTOR,
            RetrievalRoute.BM25_VECTOR,
            RetrievalRoute.SQL_BM25_VECTOR,
        ):
            t0 = time.time()
            candidate_ids = [p.id for p in sql_products] if sql_products else None
            vector_results = self._vector.search(
                intent.semantic_query,
                top_k=settings.vector_candidate_k,
                candidate_ids=candidate_ids,
            )
            latency["vector_ms"] = round((time.time() - t0) * 1000, 1)
            logger.info(
                "[3] Vector (ChromaDB)",
                query=intent.semantic_query,
                pool=f"{len(candidate_ids)} SQL ids" if candidate_ids else "full catalog",
                results=len(vector_results),
                top=_top_named(vector_results, product_map),
                latency_ms=latency["vector_ms"],
            )

        # ── Step 4: RRF fusion ────────────────────────────────────────────────
        if bm25_results and vector_results:
            fused = reciprocal_rank_fusion(bm25_results, vector_results, k=settings.rrf_k)
            fused_top = _top_named(fused, product_map, n=5)
            logger.info(
                "[4] RRF Fusion",
                bm25_in=len(bm25_results),
                vector_in=len(vector_results),
                fused_out=len(fused),
                top_5=fused_top,
            )
        elif bm25_results:
            fused = bm25_results
        else:
            fused = vector_results

        # ── Final result ──────────────────────────────────────────────────────
        results = []
        for r in fused[: intent.top_k]:
            p = product_map.get(r.product_id)
            if p:
                sources = [r.source] if r.source != "hybrid" else ["bm25", "vector"]
                results.append(SearchResult(product=p, final_score=r.score, sources=sources))

        latency["total_ms"] = round((time.time() - start) * 1000, 1)

        final_names = [f"{r.product.product_name} (₹{r.product.price})" for r in results]
        logger.info(
            "[RESULT]",
            count=len(results),
            products=final_names,
            total_ms=latency["total_ms"],
        )
        logger.info(_DIVIDER)

        return SearchResponse(
            query=intent.lexical_query or intent.semantic_query,
            results=results,
            route_used=route,
            total_candidates=len(candidate_pool),
            latency_ms=latency,
        )
