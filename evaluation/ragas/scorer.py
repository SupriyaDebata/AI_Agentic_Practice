"""RAGAS metrics instantiation and configuration.

Provides factory functions to create RAGAS metric objects with proper
LLM and embedding configuration.
"""

from typing import Optional

from src import config

try:
    from ragas.metrics.collections import (
        Faithfulness,
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
        SemanticSimilarity,
    )
    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False


def _get_eval_llm():
    """Get InstructorLLM for RAGAS 0.4+ metric computation.

    Ollama exposes an OpenAI-compatible API at /v1, so we point the OpenAI
    client at Ollama's base URL -- no cloud key required.
    """
    if not RAGAS_AVAILABLE:
        raise RuntimeError("RAGAS not installed. Run: pip install ragas")

    from openai import OpenAI
    from ragas.llms import llm_factory

    ollama_client = OpenAI(
        base_url=f"{config.EVALUATION_BASE_URL}/v1",
        api_key="ollama",  # Ollama ignores the key but the client requires one
    )
    return llm_factory(
        model=config.EVALUATION_MODEL,
        client=ollama_client,
        temperature=config.EVALUATION_TEMPERATURE,
    )


def _get_eval_embeddings():
    """Get embeddings for RAGAS metric computation.

    Uses ragas-native HuggingFaceEmbeddings (same model as retrieval).
    """
    if not RAGAS_AVAILABLE:
        raise RuntimeError("RAGAS not installed. Run: pip install ragas")

    from ragas.embeddings import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model=config.EMBEDDING_MODEL,
        device=config.EMBEDDING_DEVICE,
    )


def instantiate_ragas_metrics() -> dict:
    """Create all RAGAS metric objects.

    Returns:
        {
            "faithfulness": Faithfulness(...),
            "answer_relevancy": AnswerRelevancy(...),
            ...
        }

    Raises:
        RuntimeError: If RAGAS or dependencies not installed
    """
    if not RAGAS_AVAILABLE:
        raise RuntimeError(
            "RAGAS not installed. Run: pip install ragas"
        )

    llm = _get_eval_llm()
    embeddings = _get_eval_embeddings()

    return {
        "faithfulness": Faithfulness(llm=llm),
        "answer_relevancy": AnswerRelevancy(llm=llm, embeddings=embeddings),
        "context_precision": ContextPrecision(llm=llm),
        "context_recall": ContextRecall(llm=llm),
        "answer_semantic_similarity": SemanticSimilarity(embeddings=embeddings),
    }


def is_ragas_available() -> bool:
    """Check if RAGAS and dependencies are installed."""
    return RAGAS_AVAILABLE


def check_ragas_health() -> tuple[bool, Optional[str]]:
    """Test RAGAS and LLM connectivity.

    Returns:
        (healthy: bool, error_message: Optional[str])
    """
    if not RAGAS_AVAILABLE:
        return False, "RAGAS not installed"

    try:
        llm = _get_eval_llm()
        embeddings = _get_eval_embeddings()
        return True, None
    except Exception as e:
        return False, str(e)


def score_metric(metric_obj, metric_data: dict):
    """Score a single metric with RAGAS 0.4+ compatibility.
    
    Handles both sync and async metric APIs by using asyncio to run
    async scoring methods synchronously when needed.
    
    Args:
        metric_obj: RAGAS metric instance (Faithfulness, etc.)
        metric_data: Dict with keys: question, contexts, answer, ground_truth
    
    Returns:
        float: Metric score (0.0-1.0)
    
    Raises:
        Exception: If scoring fails
    """
    import asyncio
    
    # Try to detect if we need async scoring (RAGAS 0.4+)
    # In RAGAS 0.4+, score() is a method that expects specific kwargs or Row objects
    try:
        # RAGAS 0.4+ uses async methods
        # Try calling score_async first, which is the proper async method
        if hasattr(metric_obj, 'score_async'):
            # For RAGAS 0.4+: use async API
            loop = asyncio.get_event_loop()
            score = loop.run_until_complete(
                metric_obj.score_async(
                    row=metric_data,
                    callbacks=None
                )
            )
            return float(score)
        elif hasattr(metric_obj, 'score') and callable(metric_obj.score):
            # Try the synchronous score method
            # In newer versions, this might work with Row objects
            try:
                # First try with direct call (older RAGAS versions)
                score = metric_obj.score(metric_data)
                return float(score)
            except TypeError:
                # If that fails, try with **kwargs (RAGAS 0.4+)
                score = metric_obj.score(**metric_data)
                return float(score)
        else:
            raise AttributeError(f"Metric object {type(metric_obj)} has no score method")
    except RuntimeError:
        # No event loop in current thread, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            if hasattr(metric_obj, 'score_async'):
                score = loop.run_until_complete(
                    metric_obj.score_async(
                        row=metric_data,
                        callbacks=None
                    )
                )
                return float(score)
            else:
                raise RuntimeError("score_async method not available")
        finally:
            loop.close()
