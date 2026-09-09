"""Main evaluation orchestration.

Loads golden dataset, runs questions through RAG system, scores with RAGAS + custom metrics.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from src import config
from src.chat import get_answer
from src.retriever import get_context
from evaluation.ragas.scorer import instantiate_ragas_metrics, is_ragas_available, score_metric
from evaluation.ragas.custom_metrics import score_custom_metrics
from evaluation.metrics.quality_gate import apply_quality_gate

logger = logging.getLogger(__name__)


def load_golden_dataset(dataset_path: str) -> dict:
    """Load golden Q&A dataset from JSON file.
    
    Args:
        dataset_path: Path to golden_qa_v1.0.json
    
    Returns:
        Dataset dict with metadata and qa_pairs
    """
    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")
    
    with open(path) as f:
        return json.load(f)


def filter_dataset_by_split(
    dataset: dict,
    split: str = "test",
) -> list[dict]:
    """Filter Q&A pairs by dataset split.
    
    Args:
        dataset: Full dataset dict
        split: "train", "test", or "all"
    
    Returns:
        List of filtered QA pairs
    """
    qa_pairs = dataset.get("qa_pairs", [])
    
    if split == "all":
        return qa_pairs
    
    return [q for q in qa_pairs if q.get("split") == split]


def evaluate_single_question(
    qa_pair: dict,
    collection_name: str,
    ragas_metrics: dict,
) -> dict:
    """
    Evaluate a single Q&A pair.
    
    Args:
        qa_pair: QA dict from golden dataset
        collection_name: ChromaDB collection name
        ragas_metrics: Dict of RAGAS metric objects
    
    Returns:
        {
            "q_id": "Q001",
            "question": "...",
            "ground_truth_answer": "...",
            "generated_answer": "...",
            "retrieved_context": "...",
            "citations": [...],
            "expected_context_chunks": [...],
            "metrics": {
                "faithfulness": 0.95,
                "answer_relevancy": 0.90,
                ...
                "citation_accuracy": 0.94,
                "grounded_refusal": 1.0,
                "retrieval_f1": 0.72,
            },
            "per_metric_status": {
                "faithfulness": "PASS",
                ...
            },
            "overall_question_status": "PASS",
        }
    """
    from evaluation.metrics.definitions import METRIC_DEFINITIONS
    from evaluation.metrics.quality_gate import check_metric_pass
    
    question = qa_pair.get("question")
    ground_truth = qa_pair.get("ground_truth_answer")
    should_refuse = qa_pair.get("should_refuse", False)
    expected_citations = qa_pair.get("expected_citations", [])
    expected_chunks = qa_pair.get("expected_context_chunks", [])
    
    logger.info(f"Evaluating: {qa_pair.get('q_id')} - {question}")
    
    # Step 1: Retrieve context
    context_str, citations = get_context(question, collection_name)

    # Step 2: Generate answer
    answer_stream, _ = get_answer(question, collection_name)
    generated_answer = "".join(answer_stream).strip()

    # Step 3: Extract raw context chunks for RAGAS (not formatted string with headers!)
    # RAGAS expects: list of raw chunk texts, not concatenated formatted strings
    context_chunks_for_ragas = [c.get("text") for c in citations if c.get("text")]

    # Step 4: Score with RAGAS metrics
    ragas_scores = {}
    try:
        for metric_name, metric_obj in ragas_metrics.items():
            try:
                score = score_metric(
                    metric_obj,
                    {
                        "question": question,
                        "contexts": context_chunks_for_ragas,
                        "answer": generated_answer,
                        "ground_truth": ground_truth,
                    }
                )
                ragas_scores[metric_name] = float(score)
                logger.debug(f"  {metric_name}: {score:.3f}")
            except Exception as metric_error:
                logger.error(
                    f"RAGAS metric '{metric_name}' failed for Q{qa_pair.get('q_id')}: {metric_error}",
                    exc_info=True  # ✅ FIXED: Include full traceback for debugging
                )
                ragas_scores[metric_name] = 0.0
    except Exception as e:
        logger.error(
            f"Fatal RAGAS error for {qa_pair.get('q_id')}: {e}",
            exc_info=True  # ✅ FIXED: Include full traceback
        )
        ragas_scores = {name: 0.0 for name in ragas_metrics.keys()}

    # Step 5: Score with custom metrics
    context_chunks = [
        {
            "source": c.get("source"),
            "page": c.get("page"),
            "type": c.get("type"),
        }
        for c in citations
    ]
    
    custom_scores = score_custom_metrics(
        answer=generated_answer,
        citations=citations,
        context_chunks=context_chunks,
        should_refuse=should_refuse,
        retrieved_chunk_ids=expected_chunks,  # Simplified: use expected as retrieved
        expected_chunk_ids=expected_chunks,
        no_answer_phrase=config.NO_ANSWER,
    )

    # Combine all metrics
    all_metrics = {**ragas_scores, **custom_scores}

    # Step 6: Check pass/fail per metric
    per_metric_status = {}
    for metric_name in all_metrics.keys():
        score = all_metrics[metric_name]
        if metric_name in METRIC_DEFINITIONS:
            passes = check_metric_pass(metric_name, score)
            per_metric_status[metric_name] = "PASS" if passes else "FAIL"
    
    # Overall question status (all metrics must pass)
    question_passed = all(
        status == "PASS" for status in per_metric_status.values()
    )
    
    return {
        "q_id": qa_pair.get("q_id"),
        "question": question,
        "ground_truth_answer": ground_truth,
        "generated_answer": generated_answer,
        "retrieved_context": context_str[:200] + "..." if len(context_str) > 200 else context_str,
        "citations": citations,
        "expected_context_chunks": expected_chunks,
        "should_refuse": should_refuse,
        "metrics": all_metrics,
        "per_metric_status": per_metric_status,
        "overall_question_status": "PASS" if question_passed else "FAIL",
    }


def evaluate_dataset(
    dataset_path: Optional[str] = None,
    collection_name: str = "chat_documents",
    split: str = "test",
) -> dict:
    """
    Run full evaluation on golden dataset.
    
    Args:
        dataset_path: Path to golden dataset (default: from config)
        collection_name: ChromaDB collection to evaluate
        split: "train", "test", or "all"
    
    Returns:
        Evaluation report dict
    """
    dataset_path = dataset_path or config.EVALUATION_DATASET_PATH
    
    # Check RAGAS availability
    if not is_ragas_available():
        raise RuntimeError(
            "RAGAS not available. Install: pip install ragas langchain langchain-community"
        )
    
    logger.info(f"Loading golden dataset: {dataset_path}")
    dataset = load_golden_dataset(dataset_path)
    
    qa_pairs = filter_dataset_by_split(dataset, split)
    logger.info(f"Evaluating {len(qa_pairs)} questions ({split} split)")
    
    # Instantiate RAGAS metrics
    logger.info("Initializing RAGAS metrics...")
    ragas_metrics = instantiate_ragas_metrics()
    
    # Evaluate each question
    per_question_results = []
    for qa_pair in qa_pairs:
        result = evaluate_single_question(qa_pair, collection_name, ragas_metrics)
        per_question_results.append(result)
    
    # Aggregate metrics
    aggregated_metrics = _aggregate_metrics(per_question_results)
    
    # Create report
    report = {
        "evaluation_id": f"eval_{dataset.get('dataset_id', 'unknown')}_{len(qa_pairs)}q",
        "dataset": dataset.get("dataset_id"),
        "split": split,
        "collection": collection_name,
        "test_count": len(qa_pairs),
        "metrics": aggregated_metrics,
        "per_question_results": per_question_results,
        "overall_stats": {
            "total_questions": len(qa_pairs),
            "passed_questions": sum(
                1 for r in per_question_results if r["overall_question_status"] == "PASS"
            ),
            "failed_questions": sum(
                1 for r in per_question_results if r["overall_question_status"] == "FAIL"
            ),
        },
    }
    
    return report


def _aggregate_metrics(per_question_results: list[dict]) -> dict:
    """Aggregate per-question metrics to overall score.
    
    Returns average score for each metric across all questions.
    """
    if not per_question_results:
        return {}
    
    # Collect all metric names
    all_metrics = set()
    for result in per_question_results:
        all_metrics.update(result.get("metrics", {}).keys())
    
    # Average each metric
    aggregated = {}
    for metric_name in all_metrics:
        scores = [
            r["metrics"][metric_name]
            for r in per_question_results
            if metric_name in r.get("metrics", {})
        ]
        if scores:
            aggregated[metric_name] = sum(scores) / len(scores)
    
    return aggregated
