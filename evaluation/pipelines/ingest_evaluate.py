"""Integration pipeline: ingest document -> index -> evaluate.

Allows optional automatic evaluation after document upload.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

from src import config

logger = logging.getLogger(__name__)


def ingest_and_evaluate(
    file_path: str,
    collection_name: str = "chat_documents",
    auto_evaluate: bool = False,
) -> Tuple[int, Optional[dict]]:
    """
    Ingest document and optionally run evaluation.
    
    Args:
        file_path: Path to document (PDF or Excel)
        collection_name: ChromaDB collection name
        auto_evaluate: If True, run evaluation after ingest
    
    Returns:
        (chunk_count, evaluation_result)
        - chunk_count: Number of chunks stored
        - evaluation_result: Dict with eval results, or None if auto_evaluate=False
    """
    from app import _ingest  # Import from app.py
    
    logger.info(f"Ingesting: {file_path}")
    chunk_count = _ingest(Path(file_path), collection_name)
    logger.info(f"Stored {chunk_count} chunks")
    
    evaluation_result = None
    if auto_evaluate and config.EVALUATION_ENABLED:
        logger.info("Running automatic evaluation...")
        try:
            from evaluation.ragas.evaluation import evaluate_dataset
            from evaluation.metrics.quality_gate import apply_quality_gate
            
            # Run evaluation on test split
            eval_report = evaluate_dataset(
                collection_name=collection_name,
                split="test",
            )
            gate_result = apply_quality_gate(eval_report)
            
            evaluation_result = {
                "status": gate_result.get("gate_status"),
                "passed_metrics": gate_result.get("passed_metrics"),
                "failed_metrics": gate_result.get("failed_metrics"),
            }
            
            logger.info(f"Evaluation: {evaluation_result['status']}")
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            evaluation_result = {"status": "ERROR", "error": str(e)}
    
    return chunk_count, evaluation_result


def get_evaluation_status(collection_name: str) -> Optional[dict]:
    """
    Get latest evaluation status for a collection (if available).
    
    Returns None if no evaluation has been run.
    """
    # Future: implement by querying evaluation results database
    # For now, just a placeholder
    return None
