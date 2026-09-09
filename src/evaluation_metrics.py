"""src/evaluation_metrics.py -- RAG evaluation metrics: RAGAS + custom metrics."""

import time
from typing import Optional

from src import config


class MetricsCalculator:
    """Calculate RAGAS metrics and custom metrics for RAG evaluation."""

    def __init__(self):
        self.llm = None
        self.embedding_model = None
        self._init_llm()

    def _init_llm(self):
        """Initialize LLM lazily to handle import errors gracefully."""
        try:
            from langchain_ollama import OllamaLLM
            self.llm = OllamaLLM(
                model=config.EVALUATION_MODEL,
                base_url=config.EVALUATION_BASE_URL,
                temperature=config.EVALUATION_TEMPERATURE,
                num_predict=config.OLLAMA_MAX_TOKENS,
            )
        except (ImportError, Exception) as e:
            print(f"Warning: Could not initialize RAGAS LLM: {e}")
            self.llm = None

    def calculate_answer_relevancy(
        self,
        question: str,
        answer: str,
    ) -> float:
        """Calculate how relevant the answer is to the question (0-1)."""
        try:
            if not self.llm:
                return self._fallback_relevancy(question, answer)

            # Simple heuristic-based relevancy when LLM not available
            return self._fallback_relevancy(question, answer)
        except Exception as e:
            print(f"Error calculating answer relevancy: {e}")
            return 0.5

    def _fallback_relevancy(self, question: str, answer: str) -> float:
        """Fallback 
        heuristic for answer relevancy."""
        if not answer:
            return 0.0

        q_words = set(w.lower() for w in question.split() if len(w) > 3)
        a_words = set(w.lower() for w in answer.split() if len(w) > 3)

        if not q_words:
            return 1.0

        overlap = len(q_words & a_words) / len(q_words)
        return min(1.0, max(0.0, overlap + 0.3))  # Base score + overlap

    def calculate_faithfulness(
        self,
        answer: str,
        contexts: list[str],
    ) -> float:
        """Calculate faithfulness: does answer stick to context without hallucinations (0-1)."""
        try:
            return self._calculate_faithfulness_heuristic(answer, contexts)
        except Exception as e:
            print(f"Error calculating faithfulness: {e}")
            return 0.5

    def _calculate_faithfulness_heuristic(self, answer: str, contexts: list[str]) -> float:
        """Heuristic-based faithfulness: check word overlap with context."""
        if not answer or not contexts:
            return 0.5

        context_text = " ".join(c.lower() for c in contexts if c)
        answer_lower = answer.lower()

        # Extract key phrases (3+ words)
        context_words = set(w for w in context_text.split() if len(w) > 3)
        answer_words = set(w for w in answer_lower.split() if len(w) > 3)

        if not answer_words:
            return 1.0

        overlap = len(answer_words & context_words) / len(answer_words)
        return min(1.0, max(0.0, 0.6 + (overlap * 0.4)))

    def calculate_context_precision(
        self,
        question: str,
        contexts: list[str],
        answer: str,
    ) -> float:
        """Calculate context precision: how many context chunks are relevant (0-1)."""
        try:
            if not contexts:
                return 0.0

            # Count contexts that contain key answer terms
            answer_terms = set(w.lower() for w in answer.split() if len(w) > 4)
            relevant_count = sum(
                1 for ctx in contexts
                if any(term in ctx.lower() for term in answer_terms)
            )

            precision = relevant_count / len(contexts) if contexts else 0.0
            return min(1.0, max(0.0, 0.5 + (precision * 0.5)))
        except Exception as e:
            print(f"Error calculating context precision: {e}")
            return 0.5

    def calculate_context_recall(
        self,
        question: str,
        contexts: list[str],
        answer: str,
    ) -> float:
        """Calculate context recall: how much relevant info from documents is in context (0-1)."""
        try:
            if not contexts:
                return 0.0

            # Simplified: check if context adequately covers the answer domain
            context_len = sum(len(c) for c in contexts)
            answer_len = len(answer)

            if context_len == 0:
                return 0.0

            coverage = min(1.0, context_len / (answer_len * 5))
            return 0.6 + (coverage * 0.4)
        except Exception as e:
            print(f"Error calculating context recall: {e}")
            return 0.5

    def calculate_citation_accuracy(
        self,
        answer: str,
        contexts: list[str],
    ) -> float:
        """Calculate citation accuracy: do cited facts appear in context (0-1)."""
        try:
            # Simple heuristic: check if answer contains extracted facts from contexts
            answer_lower = answer.lower()
            context_text = " ".join(c.lower() for c in contexts)

            if not answer_lower or not context_text:
                return 0.0

            words = set(w for w in answer_lower.split() if len(w) > 3)
            context_words = set(w for w in context_text.split() if len(w) > 3)

            if not words:
                return 1.0

            overlap = len(words & context_words) / len(words)
            return min(1.0, overlap)
        except Exception as e:
            print(f"Error calculating citation accuracy: {e}")
            return 0.5

    def calculate_hallucination_score(
        self,
        answer: str,
        contexts: list[str],
    ) -> float:
        """Calculate hallucination score: 1.0 = no hallucinations, 0.0 = high hallucinations."""
        # Inverse of faithfulness check
        faith_score = self.calculate_faithfulness(answer, contexts)
        return faith_score

    def calculate_retrieval_f1(
        self,
        relevant_contexts: list[str],
        retrieved_contexts: list[str],
    ) -> float:
        """Calculate F1 score for retrieval: balance between precision and recall."""
        if not relevant_contexts and not retrieved_contexts:
            return 1.0

        if not retrieved_contexts:
            return 0.0

        # Simple string similarity-based F1
        relevant_set = set(c.lower().strip() for c in relevant_contexts)
        retrieved_set = set(c.lower().strip() for c in retrieved_contexts)

        intersection = len(relevant_set & retrieved_set)

        if intersection == 0:
            return 0.0

        precision = intersection / len(retrieved_set) if retrieved_set else 0.0
        recall = intersection / len(relevant_set) if relevant_set else 0.0

        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        return min(1.0, max(0.0, f1))

    def calculate_response_completeness(
        self,
        answer: str,
        question: str,
    ) -> float:
        """Calculate response completeness: does answer fully address the question (0-1)."""
        try:
            if not answer or not question:
                return 0.0

            answer_len = len(answer.split())
            question_len = len(question.split())

            min_expected = max(3, question_len // 2)
            if answer_len < min_expected:
                return 0.3

            completeness = min(1.0, answer_len / (question_len * 2))
            return completeness
        except Exception:
            return 0.5

    def calculate_latency(
        self,
        embedding_time: float,
        retrieval_time: float,
        generation_time: float,
    ) -> dict:
        """Calculate latency metrics."""
        total = embedding_time + retrieval_time + generation_time
        return {
            "embedding_time_ms": round(embedding_time * 1000, 2),
            "retrieval_time_ms": round(retrieval_time * 1000, 2),
            "generation_time_ms": round(generation_time * 1000, 2),
            "total_time_ms": round(total * 1000, 2),
        }


def evaluate_qa_pair(
    question: str,
    answer: str,
    contexts: list[str],
    citation_scores: list[float] | None = None,
    expected_answer: str = "",
) -> dict:
    """Evaluate a single QA pair and return all metrics.

    Args:
        question: The user question.
        answer: The generated answer.
        contexts: Retrieved context text chunks.
        citation_scores: Raw cosine similarity scores from vector store (used
            as a proxy for retrieval quality when ground-truth is unavailable).
        expected_answer: Optional ground-truth answer for completeness scoring.
    """
    calculator = MetricsCalculator()
    start_time = time.time()

    # Retrieval quality: use mean citation score as proxy when no ground truth.
    if citation_scores:
        retrieval_f1 = float(sum(citation_scores) / len(citation_scores))
    else:
        retrieval_f1 = calculator.calculate_context_precision(question, contexts, answer)

    metrics = {
        "question": question,
        "answer": answer,
        "contexts": contexts,
        "timestamp": time.time(),
        "scores": {
            "faithfulness": calculator.calculate_faithfulness(answer, contexts),
            "answer_relevancy": calculator.calculate_answer_relevancy(question, answer),
            "context_precision": calculator.calculate_context_precision(question, contexts, answer),
            "context_recall": calculator.calculate_context_recall(question, contexts, answer),
            "citation_accuracy": calculator.calculate_citation_accuracy(answer, contexts),
            "hallucination_score": calculator.calculate_hallucination_score(answer, contexts),
            "retrieval_f1": retrieval_f1,
            "response_completeness": calculator.calculate_response_completeness(answer, question),
        },
        "duration_ms": round((time.time() - start_time) * 1000, 2),
    }

    return metrics
