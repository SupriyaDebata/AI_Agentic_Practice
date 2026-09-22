"""RRF fusion of BM25 + vector results."""
from app.models.results import RetrievalResult


def reciprocal_rank_fusion(
    bm25_results: list[RetrievalResult],
    vector_results: list[RetrievalResult],
    k: int = 60,
) -> list[RetrievalResult]:
    """
    RRF score = sum(1/(k + rank)) for each product across all retriever lists.
    Returns merged list sorted by RRF score descending, source="hybrid".
    """
    scores: dict[int, float] = {}

    for rank, result in enumerate(bm25_results):
        scores[result.product_id] = scores.get(result.product_id, 0.0) + 1.0 / (k + rank + 1)

    for rank, result in enumerate(vector_results):
        scores[result.product_id] = scores.get(result.product_id, 0.0) + 1.0 / (k + rank + 1)

    sorted_ids = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    return [
        RetrievalResult(
            product_id=pid,
            score=score,
            source="hybrid",
            rank=i + 1,
        )
        for i, (pid, score) in enumerate(sorted_ids)
    ]
