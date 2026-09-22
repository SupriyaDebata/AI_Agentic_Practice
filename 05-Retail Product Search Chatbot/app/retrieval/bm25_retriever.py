"""BM25 keyword retriever using rank-bm25 library."""
import heapq

from rank_bm25 import BM25Okapi

from app.models.product import Product
from app.models.results import RetrievalResult


class BM25Retriever:
    def __init__(self):
        self._bm25 = None
        self._products: list[Product] = []

    def build_index(self, products: list[Product]) -> None:
        """Build BM25 index from product searchable_text()."""
        self._products = products
        tokenized_corpus = [
            p.searchable_text().lower().split() for p in products
        ]
        self._bm25 = BM25Okapi(tokenized_corpus)

    def search(self, query: str, top_k: int = 20) -> list[RetrievalResult]:
        """Return top_k products by BM25 score."""
        if self._bm25 is None or not self._products:
            return []
        tokens = query.lower().split()
        scores = self._bm25.get_scores(tokens)
        ranked = heapq.nlargest(top_k, enumerate(scores), key=lambda x: x[1])
        results = []
        for rank, (idx, score) in enumerate(ranked):
            results.append(
                RetrievalResult(
                    product_id=self._products[idx].id,
                    score=float(score),
                    source="bm25",
                    rank=rank + 1,
                )
            )
        return results
