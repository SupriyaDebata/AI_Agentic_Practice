"""src/evaluation_metrics.py -- RAG evaluation metrics: heuristic RAGAS-style scoring."""

import re


class MetricsCalculator:
    """Calculate heuristic RAGAS-style metrics for RAG evaluation."""

    def calculate_answer_relevancy(
        self,
        question: str,
        answer: str,
    ) -> float:
        """Calculate how relevant the answer is to the question (0-1)."""
        try:
            return self._fallback_relevancy(question, answer)
        except Exception as e:
            print(f"Error calculating answer relevancy: {e}")
            return 0.5

    # Interrogative and auxiliary words that appear in questions but NEVER in answers.
    # Including them in q_words makes relevancy artificially low (they never intersect).
    _QUESTION_STOP = frozenset({
        "what", "which", "when", "where", "who", "whom", "whose", "how", "why",
        "does", "this", "that", "your", "from", "with", "have", "been", "into",
        "many", "much", "some", "there", "their", "they", "were", "will", "would",
        "could", "should", "each", "give", "most", "more", "very", "also",
    })

    def _fallback_relevancy(self, question: str, answer: str) -> float:
        """Heuristic answer relevancy: fraction of question CONTENT words present in the answer.

        Excludes interrogative words (what, how, which…) that appear in questions
        but never in answers, preventing them from unfairly lowering the score.
        Also grants partial credit when the answer is very short (≤5 words) but
        contains at least one question content word — short precise answers should
        not score zero simply because they are terse.
        """
        if not answer:
            return 0.0

        strip = lambda s: s.lower().strip("?,.'\"():")  # noqa: E731
        q_words = set(
            strip(w)
            for w in question.split()
            if len(strip(w)) > 2 and strip(w) not in self._QUESTION_STOP
        )
        # Include all answer words regardless of length — short numbers ("24", "5")
        # and short names ("INR") are valid content words.
        a_words = set(strip(w) for w in answer.split() if strip(w))

        if not q_words:
            return 1.0

        overlap = len(q_words & a_words)
        base = overlap / len(q_words)

        # Partial credit floor for short precise answers:
        # A 1-5 word answer that contains ANY question content word is at least 0.50.
        if base == 0.0 and len(answer.split()) <= 5 and a_words:
            # Check if any answer word is a substring of any question content word
            # (handles abbreviations / stemming mismatches like "North" ↔ "northern")
            for aw in a_words:
                for qw in q_words:
                    if aw in qw or qw in aw:
                        return 0.50
        return min(1.0, max(0.0, base))

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

    _PREAMBLE_RE = re.compile(
        r"^(according to|based on|from|per|as per|as stated in|as mentioned in|"
        r"as described in|as indicated in|referring to|see|in)\s+(excerpt|source|"
        r"document|context|passage|section|the document|the context|the excerpt)"
        r"[\s\d,.:;-]*",
        re.IGNORECASE,
    )

    @classmethod
    def _strip_answer_preamble(cls, answer: str) -> str:
        """Remove LLM citation preambles before scoring (e.g. 'According to Excerpt 1,')."""
        cleaned = cls._PREAMBLE_RE.sub("", answer.strip()).strip().lstrip(",. ")
        return cleaned if cleaned else answer

    def _calculate_faithfulness_heuristic(self, answer: str, contexts: list[str]) -> float:
        """Heuristic faithfulness: fraction of answer key-words that appear in context.

        No artificial floor — 0 overlap = 0 faithfulness (fully hallucinated answer).
        Strips LLM citation preambles before scoring so 'According to Excerpt 1' doesn't
        penalise an otherwise grounded answer.
        """
        if not answer or not contexts:
            return 0.0

        clean_answer = self._strip_answer_preamble(answer).lower()
        context_text = " ".join(c.lower() for c in contexts if c)

        context_words = set(w for w in context_text.split() if len(w) > 3)
        answer_words  = set(w for w in clean_answer.split() if len(w) > 3)

        if not answer_words:
            return 1.0  # trivially faithful empty answer

        overlap = len(answer_words & context_words) / len(answer_words)
        return min(1.0, max(0.0, overlap))

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

            # Use BOTH question and answer terms (> 3 chars) to judge context relevance.
            # Using only answer terms penalises short answers; question terms anchor intent.
            q_terms = set(w.lower().strip("?,.'\"") for w in question.split() if len(w) > 3)
            a_terms = set(w.lower().strip("?,.'\"") for w in self._strip_answer_preamble(answer).split() if len(w) > 3)
            key_terms = q_terms | a_terms
            if not key_terms:
                return 1.0
            relevant_count = sum(
                1 for ctx in contexts
                if any(term in ctx.lower() for term in key_terms)
            )
            precision = relevant_count / len(contexts) if contexts else 0.0
            return min(1.0, max(0.0, precision))
        except Exception as e:
            print(f"Error calculating context precision: {e}")
            return 0.5

    def calculate_context_recall(
        self,
        question: str,
        contexts: list[str],
        answer: str,
    ) -> float:
        """Context recall: fraction of question+answer key-words present in retrieved context."""
        try:
            if not contexts:
                return 0.0
            # Target = terms needed to answer the question (question + answer vocabulary)
            q_words = set(w.lower() for w in question.split() if len(w) > 3)
            a_words = set(w.lower() for w in self._strip_answer_preamble(answer).split() if len(w) > 3)
            target = q_words | a_words
            if not target:
                return 1.0
            context_text = " ".join(c.lower() for c in contexts if c)
            context_words = set(w for w in context_text.split() if len(w) > 3)
            return min(1.0, max(0.0, len(target & context_words) / len(target)))
        except Exception as e:
            print(f"Error calculating context recall: {e}")
            return 0.5

    def calculate_citation_accuracy(
        self,
        answer: str,
        contexts: list[str],
        citation_scores: list[float] | None = None,
    ) -> float:
        """Citation accuracy: quality of the best-matching retrieved source.

        Uses the MAX cosine similarity score from the vector store. Rationale:
        citation accuracy asks 'did we cite a relevant source?' — we only need
        ONE highly relevant source. Averaging in weak secondary chunks (e.g.
        an Excel file retrieved because it contains a product name) unfairly
        penalises a system that correctly found the primary source at 92%.
        Falls back to faithfulness heuristic when no scores are available.
        """
        if citation_scores:
            return min(1.0, max(0.0, max(citation_scores)))
        return self._calculate_faithfulness_heuristic(answer, contexts)

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

