"""src/dataset_manager.py -- Manage golden QA datasets for evaluation."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from src import config


class DatasetManager:
    """Manage golden QA datasets for RAG evaluation."""

    def __init__(self, dataset_path: Optional[str] = None):
        self.dataset_path = Path(dataset_path or config.EVALUATION_DATASET_PATH)
        self.dataset_path.parent.mkdir(parents=True, exist_ok=True)

    def load_dataset(self) -> list[dict]:
        """Load golden QA dataset from file."""
        if not self.dataset_path.exists():
            return []

        try:
            with open(self.dataset_path, "r") as f:
                data = json.load(f)
                return data if isinstance(data, list) else data.get("questions", [])
        except (json.JSONDecodeError, IOError):
            return []

    def save_dataset(self, questions: list[dict]) -> bool:
        """Save golden QA dataset to file."""
        try:
            self.dataset_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.dataset_path, "w") as f:
                json.dump(questions, f, indent=2)
            return True
        except IOError:
            return False

    def add_question(
        self,
        question: str,
        expected_answer: Optional[str] = None,
        contexts: Optional[list[str]] = None,
    ) -> bool:
        """Add a single QA pair to the dataset."""
        dataset = self.load_dataset()

        new_qa = {
            "id": len(dataset) + 1,
            "question": question,
            "expected_answer": expected_answer or "",
            "contexts": contexts or [],
            "added_at": datetime.now().isoformat(),
        }

        dataset.append(new_qa)
        return self.save_dataset(dataset)

    def remove_question(self, question_id: int) -> bool:
        """Remove a question from the dataset."""
        dataset = self.load_dataset()
        dataset = [q for q in dataset if q.get("id") != question_id]
        return self.save_dataset(dataset)

    def update_question(self, question_id: int, updates: dict) -> bool:
        """Update a question in the dataset."""
        dataset = self.load_dataset()
        for q in dataset:
            if q.get("id") == question_id:
                q.update(updates)
                return self.save_dataset(dataset)
        return False

    def get_question(self, question_id: int) -> Optional[dict]:
        """Get a specific question by ID."""
        dataset = self.load_dataset()
        for q in dataset:
            if q.get("id") == question_id:
                return q
        return None

    def import_sample_dataset(self) -> bool:
        """Import a sample dataset for demo purposes."""
        sample_questions = [
            {
                "id": 1,
                "question": "What is the total revenue?",
                "expected_answer": "Total revenue figures should be presented with currency.",
                "contexts": [],
                "added_at": datetime.now().isoformat(),
            },
            {
                "id": 2,
                "question": "Which region has the highest sales?",
                "expected_answer": "Region comparison data should be extracted from documents.",
                "contexts": [],
                "added_at": datetime.now().isoformat(),
            },
            {
                "id": 3,
                "question": "What are the payment terms?",
                "expected_answer": "Payment terms like net-30, net-60, etc.",
                "contexts": [],
                "added_at": datetime.now().isoformat(),
            },
            {
                "id": 4,
                "question": "What products are mentioned?",
                "expected_answer": "List of products mentioned in the documents.",
                "contexts": [],
                "added_at": datetime.now().isoformat(),
            },
            {
                "id": 5,
                "question": "What is the invoice number?",
                "expected_answer": "Specific invoice number from the document.",
                "contexts": [],
                "added_at": datetime.now().isoformat(),
            },
        ]

        return self.save_dataset(sample_questions)

    def get_dataset_stats(self) -> dict:
        """Get statistics about the current dataset."""
        dataset = self.load_dataset()
        return {
            "total_questions": len(dataset),
            "questions_with_answers": sum(1 for q in dataset if q.get("expected_answer")),
            "questions_with_contexts": sum(1 for q in dataset if q.get("contexts")),
            "dataset_path": str(self.dataset_path),
            "last_modified": datetime.fromtimestamp(
                self.dataset_path.stat().st_mtime
            ).isoformat() if self.dataset_path.exists() else None,
        }

    def validate_dataset(self) -> dict:
        """Validate dataset completeness.

        Only question text and expected_answer are required.
        Missing contexts is a soft warning — evaluation still runs without them.
        """
        dataset = self.load_dataset()
        issues = []        # blocking: cannot evaluate
        warnings = []      # soft: evaluation degrades but still works

        for q in dataset:
            qa_id = q.get("id", "?")
            if not q.get("question"):
                issues.append(f"Q{qa_id}: missing question text")
            if not q.get("expected_answer"):
                issues.append(f"Q{qa_id}: missing expected answer")
            if not q.get("contexts"):
                warnings.append(f"Q{qa_id}: no ground-truth contexts (context recall will be skipped)")

        all_messages = issues + warnings
        return {
            "is_valid": len(issues) == 0,   # valid as long as no blocking issues
            "total_questions": len(dataset),
            "issues": all_messages,
            "completeness_pct": max(0, (1 - len(issues) / max(len(dataset), 1)) * 100),
        }

    def export_csv(self, output_path: str) -> bool:
        """Export dataset to CSV format."""
        try:
            import csv

            dataset = self.load_dataset()
            if not dataset:
                return False

            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f, fieldnames=["id", "question", "expected_answer", "added_at"]
                )
                writer.writeheader()
                for q in dataset:
                    writer.writerow({
                        "id": q.get("id", ""),
                        "question": q.get("question", ""),
                        "expected_answer": q.get("expected_answer", ""),
                        "added_at": q.get("added_at", ""),
                    })
            return True
        except Exception:
            return False
