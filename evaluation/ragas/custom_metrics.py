"""Custom evaluation metrics specific to RAG system.

Implements:
- Citation Accuracy: % of facts with valid citations
- Grounded Refusal: System refuses when answer absent
- Retrieval F1: Standard IR metric on chunk-level retrieval
"""

import re
from typing import Optional


class CitationAccuracyScorer:
    """Score: % of answer facts with citations in context.
    
    Threshold: >= 0.90 (strict: citations are binding for compliance)
    """
    
    def score(
        self,
        answer: str,
        citations: list[dict],
        context_chunks: list[dict],
    ) -> float:
        """
        Score citation accuracy.
        
        Args:
            answer: Generated answer text
            citations: List of {source, page, type, score} dicts provided by system
            context_chunks: List of retrieved context chunks with metadata
        
        Returns:
            Score 0.0-1.0: (accurate_citations / total_facts)
        
        Logic:
            - Assume answer facts = sentence count (simple heuristic)
            - Check if each citation matches a retrieved chunk
            - Score = citations_found / expected_facts
        """
        if not answer or not answer.strip():
            return 0.0
        
        # Heuristic: split answer by sentences to get fact count
        sentences = re.split(r'[.!?]+', answer.strip())
        fact_count = len([s for s in sentences if s.strip()])
        
        if fact_count == 0:
            return 1.0  # Empty answer, no facts to cite
        
        # Verify each citation matches a chunk
        valid_citations = 0
        for citation in citations:
            # Check if citation references a real chunk
            chunk_key = (citation.get("source"), citation.get("page"), citation.get("type"))
            for chunk in context_chunks:
                chunk_source = chunk.get("source")
                chunk_page = chunk.get("page")
                chunk_type = chunk.get("type")
                if (chunk_source, chunk_page, chunk_type) == chunk_key:
                    valid_citations += 1
                    break
        
        # Score: valid citations vs. expected facts
        # If more citations than facts, cap at 1.0
        accuracy = min(valid_citations / fact_count, 1.0) if fact_count > 0 else 1.0
        return accuracy


class GroundedRefusalScorer:
    """Score: System correctly refuses unanswerable questions.
    
    Threshold: = 1.0 (binary: all negative cases must refuse)
    """
    
    def score(
        self,
        answer: str,
        should_refuse: bool,
        no_answer_phrase: str = "I could not find this in the provided documents.",
    ) -> float:
        """
        Score grounded refusal behavior.
        
        Args:
            answer: Generated answer
            should_refuse: True if question should get no-answer response
            no_answer_phrase: Expected refusal phrase
        
        Returns:
            1.0 if correct (refused when should, answered when shouldn't)
            0.0 if wrong (answered when shouldn't, or didn't refuse when should)
        """
        answer_text = answer.strip() if answer else ""
        no_answer_text = no_answer_phrase.strip()
        
        # Check if answer matches refusal phrase (or contains it)
        is_refusal = (
            answer_text == no_answer_text or 
            answer_text.startswith(no_answer_text)
        )
        
        # Correct if: (should_refuse and is_refusal) or (not should_refuse and not is_refusal)
        if should_refuse:
            return 1.0 if is_refusal else 0.0
        else:
            return 0.0 if is_refusal else 1.0


class RetrievalF1Scorer:
    """Score: Retrieval precision x recall F1.
    
    Threshold: >= 0.70 (standard IR metric)
    """
    
    def score(
        self,
        retrieved_chunk_ids: list[str],
        expected_chunk_ids: list[str],
    ) -> float:
        """
        Compute retrieval F1 score.
        
        Args:
            retrieved_chunk_ids: IDs of chunks returned by retriever
            expected_chunk_ids: IDs of chunks expected to be retrieved
        
        Returns:
            F1 score 0.0-1.0 = 2 * (precision * recall) / (precision + recall)
        
        Logic:
            - Precision = (overlap / len(retrieved)) if retrieved else 0
            - Recall = (overlap / len(expected)) if expected else 0
            - F1 = harmonic mean
        """
        if not retrieved_chunk_ids and not expected_chunk_ids:
            return 1.0  # Both empty: perfect
        
        if not expected_chunk_ids:
            # No chunks expected but system retrieved some
            return 0.0
        
        if not retrieved_chunk_ids:
            # Chunks expected but none retrieved
            return 0.0
        
        # Compute overlap
        retrieved_set = set(retrieved_chunk_ids)
        expected_set = set(expected_chunk_ids)
        overlap = len(retrieved_set & expected_set)
        
        # Precision: relevant chunks that were retrieved
        precision = overlap / len(retrieved_set) if retrieved_set else 0.0
        
        # Recall: expected chunks that were retrieved
        recall = overlap / len(expected_set) if expected_set else 0.0
        
        # F1: harmonic mean
        if precision + recall == 0:
            return 0.0
        
        f1 = 2 * (precision * recall) / (precision + recall)
        return f1


def score_custom_metrics(
    answer: str,
    citations: list[dict],
    context_chunks: list[dict],
    should_refuse: bool,
    retrieved_chunk_ids: list[str],
    expected_chunk_ids: list[str],
    no_answer_phrase: str = "I could not find this in the provided documents.",
) -> dict:
    """
    Compute all custom metrics at once.
    
    Args:
        answer: Generated answer
        citations: Citations provided by system
        context_chunks: Retrieved context chunks
        should_refuse: Whether question should get refusal
        retrieved_chunk_ids: IDs of retrieved chunks
        expected_chunk_ids: IDs of expected chunks
        no_answer_phrase: Expected refusal phrase
    
    Returns:
        {
            "citation_accuracy": 0.94,
            "grounded_refusal": 1.0,
            "retrieval_f1": 0.72,
        }
    """
    citation_scorer = CitationAccuracyScorer()
    refusal_scorer = GroundedRefusalScorer()
    f1_scorer = RetrievalF1Scorer()
    
    return {
        "citation_accuracy": citation_scorer.score(answer, citations, context_chunks),
        "grounded_refusal": refusal_scorer.score(answer, should_refuse, no_answer_phrase),
        "retrieval_f1": f1_scorer.score(retrieved_chunk_ids, expected_chunk_ids),
    }
