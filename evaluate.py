#!/usr/bin/env python3
"""
Simple RAGAS Evaluation Script
Evaluate RAG system on golden Q&A dataset with clear metrics and results.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from src import config
from src.chat import get_answer
from src.evaluation_metrics import MetricsCalculator
from src.quality_gate import QualityGateEvaluator


class SimpleEvaluator:
    """Simple RAG evaluator: run golden dataset and show metrics."""

    def __init__(self, dataset_path: Optional[str] = None):
        self.dataset_path = Path(dataset_path or "evaluation/datasets/golden_qa_v1.0.json")
        self.quality_gate = QualityGateEvaluator()
        self.metrics_calc = MetricsCalculator()

    def load_dataset(self) -> dict:
        """Load golden Q&A dataset."""
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Dataset not found: {self.dataset_path}")
        with open(self.dataset_path) as f:
            return json.load(f)

    def evaluate(self, show_progress: bool = True) -> dict:
        """Evaluate all questions in the dataset.

        Args:
            show_progress: Print progress updates

        Returns:
            dict with results and metrics
        """
        dataset = self.load_dataset()
        qa_pairs = dataset.get("qa_pairs", [])
        metadata = dataset.get("metadata", {})

        results = {
            "timestamp": datetime.now().isoformat(),
            "dataset_id": dataset.get("dataset_id", "unknown"),
            "total_questions": len(qa_pairs),
            "evaluations": [],
            "summary": {},
        }

        print(f"\n📊 Evaluating {len(qa_pairs)} questions from golden dataset...")
        print("=" * 80)

        for idx, qa_item in enumerate(qa_pairs, 1):
            question = qa_item.get("question", "")
            expected_answer = qa_item.get("expected_answer", "")
            should_refuse = qa_item.get("should_refuse", False)
            q_id = qa_item.get("q_id", f"Q{idx:03d}")

            if show_progress:
                print(f"\n[{idx}/{len(qa_pairs)}] {q_id}: {question[:70]}...")

            try:
                # Get RAG answer (streaming + citations)
                answer_stream, citations, context_texts = get_answer(question, config.COLLECTION_NAME)
                
                # Consume streaming answer to get full text
                answer = "".join(answer_stream)

                # Calculate metrics using MetricsCalculator
                metrics_scores = {
                    "faithfulness": self.metrics_calc.calculate_faithfulness(answer, context_texts),
                    "answer_relevancy": self.metrics_calc.calculate_answer_relevancy(question, answer),
                    "context_precision": self.metrics_calc.calculate_context_precision(question, context_texts, answer),
                    "context_recall": self.metrics_calc.calculate_context_recall(question, context_texts, answer),
                    "citation_accuracy": self.metrics_calc.calculate_citation_accuracy(answer, context_texts),
                    "retrieval_f1": self.metrics_calc.calculate_retrieval_f1(expected_answer.split() if expected_answer else [], context_texts),
                    "response_completeness": 1.0 if len(answer) > 20 else 0.5,
                    "grounded_refusal": 1.0 if should_refuse == (config.NO_ANSWER in answer) else 0.0,
                }

                # Check quality gate
                gate_result = self.quality_gate.evaluate_metrics(metrics_scores)

                evaluation = {
                    "q_id": q_id,
                    "question": question,
                    "rag_answer": answer,
                    "expected_answer": expected_answer,
                    "should_refuse": should_refuse,
                    "metrics": metrics_scores,
                    "pass": gate_result.passed,
                }

                results["evaluations"].append(evaluation)

                # Print inline result
                status = "✅ PASS" if gate_result.passed else "❌ FAIL"
                faith = metrics_scores.get("faithfulness", 0.0)
                print(f"  {status} | Faithfulness: {faith:.2f}")

            except Exception as e:
                print(f"  ⚠️  ERROR: {str(e)}")
                results["evaluations"].append({
                    "q_id": q_id,
                    "question": question,
                    "error": str(e),
                })

        # Calculate summary metrics
        summary = self._calculate_summary(results["evaluations"])
        results["summary"] = summary

        # Print summary
        self._print_summary(summary, metadata)

        return results

    def _calculate_summary(self, evaluations: list[dict]) -> dict:
        """Calculate aggregate metrics across all questions."""
        if not evaluations:
            return {}

        # Filter out errors
        valid_evals = [e for e in evaluations if "metrics" in e]
        if not valid_evals:
            return {}

        # Collect all metric names
        all_metrics = set()
        for ev in valid_evals:
            all_metrics.update(ev.get("metrics", {}).keys())

        # Calculate averages
        summary = {}
        for metric in sorted(all_metrics):
            values = [
                ev["metrics"][metric]
                for ev in valid_evals
                if metric in ev.get("metrics", {}) and ev["metrics"][metric] is not None
            ]
            if values:
                summary[metric] = {
                    "mean": round(sum(values) / len(values), 4),
                    "min": round(min(values), 4),
                    "max": round(max(values), 4),
                    "count": len(values),
                }

        # Overall pass rate
        passed = sum(1 for e in valid_evals if e.get("pass", False))
        summary["pass_rate"] = round(passed / len(valid_evals), 4) if valid_evals else 0.0

        return summary

    def _print_summary(self, summary: dict, metadata: dict) -> None:
        """Print evaluation summary to console."""
        print("\n" + "=" * 80)
        print("📈 EVALUATION SUMMARY")
        print("=" * 80)

        if not summary:
            print("No metrics calculated.")
            return

        # Overall pass rate
        pass_rate = summary.get("pass_rate", 0.0)
        print(f"\n✅ Overall Pass Rate: {pass_rate * 100:.1f}%")

        # Metric averages
        print("\n📊 Metric Averages (Mean):")
        print("-" * 80)
        for metric in sorted(summary.keys()):
            if metric == "pass_rate":
                continue
            stats = summary[metric]
            mean = stats.get("mean", 0)
            min_val = stats.get("min", 0)
            max_val = stats.get("max", 0)
            count = stats.get("count", 0)
            print(
                f"  {metric:30s} | Mean: {mean:.3f}  Min: {min_val:.3f}  "
                f"Max: {max_val:.3f}  (N={count})"
            )

        print("\n" + "=" * 80)

    def save_report(self, results: dict, output_path: Optional[str] = None) -> str:
        """Save results to JSON report.

        Args:
            results: Evaluation results dict
            output_path: Where to save (default: evaluation/reports/eval_TIMESTAMP.json)

        Returns:
            Path to saved report
        """
        if output_path is None:
            reports_dir = Path("evaluation/reports")
            reports_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = reports_dir / f"evaluation_{timestamp}.json"
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

        print(f"\n💾 Report saved: {output_path}")
        return str(output_path)


def main():
    """Run simple evaluation."""
    import argparse

    parser = argparse.ArgumentParser(description="Simple RAGAS evaluation on golden dataset")
    parser.add_argument(
        "--dataset",
        type=str,
        default="evaluation/datasets/golden_qa_v1.0.json",
        help="Path to golden QA dataset",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to save JSON report (default: auto-timestamped in evaluation/reports/)",
    )
    args = parser.parse_args()

    try:
        evaluator = SimpleEvaluator(dataset_path=args.dataset)
        results = evaluator.evaluate(show_progress=True)
        report_path = evaluator.save_report(results, output_path=args.output)
        print(f"\n✅ Evaluation complete! Report: {report_path}")
        return 0
    except Exception as e:
        print(f"\n❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
