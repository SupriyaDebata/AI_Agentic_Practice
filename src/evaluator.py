"""src/evaluator.py -- Orchestrate RAG evaluation: run tests, collect metrics, generate reports."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

from src import config
from src.dataset_manager import DatasetManager
from src.evaluation_metrics import evaluate_qa_pair
from src.quality_gate import QualityGateEvaluator


class RAGEvaluator:
    """Orchestrate end-to-end RAG evaluation."""

    def __init__(
        self,
        dataset_path: Optional[str] = None,
        reports_path: Optional[str] = None,
    ):
        self.dataset_manager = DatasetManager(dataset_path)
        self.quality_gate = QualityGateEvaluator()
        self.reports_path = Path(reports_path or config.EVALUATION_REPORTS_PATH)
        self.reports_path.mkdir(parents=True, exist_ok=True)

    def evaluate_dataset(
        self,
        rag_query_fn: Callable,
        progress_callback: Optional[Callable] = None,
    ) -> dict:
        """Evaluate entire dataset using provided RAG query function.

        Args:
            rag_query_fn: Function(question) -> (answer, contexts) tuple
            progress_callback: Optional function(current, total) for progress updates

        Returns:
            dict with evaluation results and quality gate status
        """
        dataset = self.dataset_manager.load_dataset()
        if not dataset:
            return {
                "status": "ERROR",
                "message": "No dataset loaded",
                "timestamp": datetime.now().isoformat(),
            }

        evaluation_results = []
        errors = []

        for idx, qa_item in enumerate(dataset):
            try:
                if progress_callback:
                    progress_callback(idx + 1, len(dataset))

                question = qa_item.get("question", "")
                expected_answer = qa_item.get("expected_answer", "")

                if not question:
                    errors.append(f"Question {idx + 1}: empty question")
                    continue

                # Get answer from RAG system
                answer, contexts = rag_query_fn(question)

                if not answer:
                    errors.append(f"Question {idx + 1}: no answer from RAG")
                    continue

                # Evaluate this QA pair
                result = evaluate_qa_pair(
                    question=question,
                    answer=answer,
                    contexts=contexts or [],
                )
                result["qa_id"] = qa_item.get("id", idx + 1)
                result["expected_answer"] = expected_answer
                evaluation_results.append(result)

            except Exception as e:
                errors.append(f"Question {idx + 1}: {str(e)}")

        # Evaluate quality gate
        if evaluation_results:
            aggregate_scores = {}
            for metric_name in config.QUALITY_GATE_THRESHOLDS.keys():
                scores = [r["scores"].get(metric_name, 0.5) for r in evaluation_results]
                aggregate_scores[metric_name] = sum(scores) / len(scores)

            quality_gate_result = self.quality_gate.evaluate_metrics(aggregate_scores)
        else:
            quality_gate_result = None

        report = {
            "timestamp": datetime.now().isoformat(),
            "dataset_stats": self.dataset_manager.get_dataset_stats(),
            "evaluation_count": len(evaluation_results),
            "error_count": len(errors),
            "errors": errors,
            "results": evaluation_results,
            "quality_gate": {
                "status": quality_gate_result.overall_status if quality_gate_result else "N/A",
                "passed": quality_gate_result.passed if quality_gate_result else False,
                "summary": quality_gate_result.summary if quality_gate_result else "",
                "metrics": [
                    {
                        "name": m.name,
                        "score": round(m.score, 4),
                        "threshold": m.threshold,
                        "passed": m.passed,
                    }
                    for m in (quality_gate_result.metric_results if quality_gate_result else [])
                ],
            },
        }

        return report

    def evaluate_single_qa(
        self,
        question: str,
        rag_query_fn: Callable,
    ) -> dict:
        """Evaluate a single QA pair."""
        try:
            answer, contexts = rag_query_fn(question)

            if not answer:
                return {"status": "ERROR", "message": "No answer from RAG"}

            result = evaluate_qa_pair(
                question=question,
                answer=answer,
                contexts=contexts or [],
            )

            return {
                "status": "SUCCESS",
                "result": result,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    def save_report(self, report: dict, filename: Optional[str] = None) -> Path:
        """Save evaluation report to file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"evaluation_{timestamp}.json"

        filepath = self.reports_path / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)

        return filepath

    def load_report(self, filename: str) -> Optional[dict]:
        """Load evaluation report from file."""
        filepath = self.reports_path / filename
        if not filepath.exists():
            return None

        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def list_reports(self) -> list[dict]:
        """List all saved evaluation reports."""
        reports = []
        for filepath in sorted(self.reports_path.glob("evaluation_*.json"), reverse=True):
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                    reports.append({
                        "filename": filepath.name,
                        "timestamp": data.get("timestamp", ""),
                        "evaluation_count": data.get("evaluation_count", 0),
                        "passed": data.get("quality_gate", {}).get("passed", False),
                    })
            except (json.JSONDecodeError, IOError):
                pass

        return reports

    def get_latest_report(self) -> Optional[dict]:
        """Get the most recent evaluation report."""
        reports = self.list_reports()
        if not reports:
            return None

        latest = reports[0]
        return self.load_report(latest["filename"])

    def generate_html_report(self, report: dict) -> str:
        """Generate HTML report from evaluation results."""
        quality_gate = report.get("quality_gate", {})
        results = report.get("results", [])

        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            '<meta charset="utf-8">',
            "<title>RAG Quality Gate Report</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; }",
            "h1, h2 { color: #333; }",
            ".status-pass { color: green; font-weight: bold; }",
            ".status-fail { color: red; font-weight: bold; }",
            "table { border-collapse: collapse; width: 100%; margin: 20px 0; }",
            "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "th { background-color: #f2f2f2; }",
            ".metric-pass { background-color: #e8f5e9; }",
            ".metric-fail { background-color: #ffebee; }",
            "</style>",
            "</head>",
            "<body>",
            "<h1>RAG Quality Gate Evaluation Report</h1>",
            f"<p>Generated: {report.get('timestamp', 'N/A')}</p>",
            "<hr>",
            "<h2>Overall Status</h2>",
            f"<p class='status-{'pass' if quality_gate.get('passed') else 'fail'}'>",
            f"{quality_gate.get('status', 'N/A')}</p>",
            f"<p>{quality_gate.get('summary', '')}</p>",
        ]

        # Metrics table
        html_parts.extend([
            "<h2>Quality Metrics</h2>",
            "<table>",
            "<tr><th>Metric</th><th>Score</th><th>Threshold</th><th>Status</th></tr>",
        ])

        for metric in quality_gate.get("metrics", []):
            status_class = "metric-pass" if metric.get("passed") else "metric-fail"
            html_parts.append(
                f"<tr class='{status_class}'>"
                f"<td>{metric.get('name', 'N/A')}</td>"
                f"<td>{metric.get('score', 0):.4f}</td>"
                f"<td>{metric.get('threshold', 0):.4f}</td>"
                f"<td>{'✅ PASS' if metric.get('passed') else '❌ FAIL'}</td>"
                f"</tr>"
            )

        html_parts.append("</table>")

        # Results summary
        html_parts.extend([
            "<h2>Evaluation Summary</h2>",
            f"<p>Total Evaluated: {report.get('evaluation_count', 0)}</p>",
            f"<p>Errors: {report.get('error_count', 0)}</p>",
        ])

        if results:
            html_parts.extend([
                "<h2>Top Results</h2>",
                "<table>",
                "<tr><th>Question</th><th>Faithfulness</th><th>Relevancy</th><th>Precision</th></tr>",
            ])

            for result in results[:10]:
                scores = result.get("scores", {})
                html_parts.append(
                    f"<tr>"
                    f"<td>{result.get('question', '')[:50]}...</td>"
                    f"<td>{scores.get('faithfulness', 0):.4f}</td>"
                    f"<td>{scores.get('answer_relevancy', 0):.4f}</td>"
                    f"<td>{scores.get('context_precision', 0):.4f}</td>"
                    f"</tr>"
                )

            html_parts.append("</table>")

        html_parts.extend([
            "</body>",
            "</html>",
        ])

        return "\n".join(html_parts)
