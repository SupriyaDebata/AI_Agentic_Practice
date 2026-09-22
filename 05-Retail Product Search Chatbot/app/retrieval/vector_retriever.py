"""Vector semantic retriever using sentence-transformers + ChromaDB."""
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from app.models.product import Product
from app.models.results import RetrievalResult
from app.config import settings


class VectorRetriever:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model_name = model_name
        self._embed_fn = SentenceTransformerEmbeddingFunction(model_name=model_name)
        self._client = chromadb.PersistentClient(path=str(settings.chroma_persist_dir))
        self._collection = self._client.get_or_create_collection(
            name="products",
            embedding_function=self._embed_fn,
            metadata={"hnsw:space": "cosine"},
        )

    def build_index(self, products: list[Product]) -> None:
        """Embed product text and upsert all products into ChromaDB collection."""
        existing = self._collection.get(include=[])
        if existing["ids"]:
            self._collection.delete(ids=existing["ids"])

        ids = [str(p.id) for p in products]
        documents = [p.to_embedding_text() for p in products]
        metadatas = [{"product_id": p.id} for p in products]
        self._collection.add(ids=ids, documents=documents, metadatas=metadatas)

    def search(
        self,
        query: str,
        top_k: int = 20,
        candidate_ids: list[int] | None = None,
    ) -> list[RetrievalResult]:
        """
        Query ChromaDB for semantic similarity.

        candidate_ids: when provided, restricts search to those product IDs
        (used after SQL pre-filtering to keep hard constraints intact).
        """
        count = self._collection.count()
        if count == 0:
            return []

        kwargs: dict = {"query_texts": [query]}

        if candidate_ids:
            # ChromaDB $in filter on metadata field
            kwargs["where"] = {"product_id": {"$in": candidate_ids}}
            kwargs["n_results"] = min(top_k, len(candidate_ids))
        else:
            kwargs["n_results"] = min(top_k, count)

        results = self._collection.query(**kwargs)

        retrieval_results = []
        if results["ids"] and results["ids"][0]:
            for rank, (dist, meta) in enumerate(
                zip(results["distances"][0], results["metadatas"][0])
            ):
                retrieval_results.append(
                    RetrievalResult(
                        product_id=meta["product_id"],
                        score=1.0 - dist,  # cosine distance → similarity
                        source="vector",
                        rank=rank + 1,
                    )
                )
        return retrieval_results
