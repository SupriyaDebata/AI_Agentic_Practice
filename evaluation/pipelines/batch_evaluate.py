"""Batch evaluation CLI.

Run evaluation on golden dataset and generate reports.

Usage:
    python -m evaluation.pipelines.batch_evaluate --collection chat_documents --split test
    python -m evaluation.pipelines.batch_evaluate --collection chat_documents --output reports/eval.json
"""

import argparse
import json
import logging
import sys
from pathlib import Path
import os
os.environ["PYTHONUTF8"] = "1"

from src import config
from evaluation.ragas.evaluation import evaluate_dataset
from evaluation.metrics.quality_gate import apply_quality_gate
from evaluation.metrics.report_generator import (
    save_json_report,
    generate_html_report,
    print_report_summary,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Run RAG quality gate evaluation on golden dataset"
    )
    parser.add_argument(
        "--collection",
        default="chat_documents",
        help="ChromaDB collection to evaluate (default: chat_documents)",
    )
    parser.add_argument(
        "--split",
        default="test",
        choices=["train", "test", "all"],
        help="Dataset split to evaluate (default: test)",
    )
    parser.add_argument(
        "--dataset",
        default=None,
        help="Path to golden dataset JSON (default: from config)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON file path (default: reports/evaluation_report.json)",
    )
    parser.add_argument(
        "--html",
        default=None,
        help="Output HTML file path (default: reports/evaluation_report.html)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress console output",
    )
    
    args = parser.parse_args()
    
    # Set defaults
    output_json = args.output or str(
        Path(config.EVALUATION_REPORTS_PATH) / "evaluation_report.json"
    )
    output_html = args.html or str(
        Path(config.EVALUATION_REPORTS_PATH) / "evaluation_report.html"
    )
    
    try:
        # Run evaluation
        logger.info(f"Starting evaluation on collection '{args.collection}' ({args.split} split)")
        evaluation_report = evaluate_dataset(
            dataset_path=args.dataset,
            collection_name=args.collection,
            split=args.split,
        )
        
        # Apply quality gate
        logger.info("Applying quality gate...")
        gate_result = apply_quality_gate(evaluation_report)
        
        # Save reports
        logger.info(f"Saving JSON report to {output_json}")
        save_json_report(evaluation_report, gate_result, output_json)
        
        logger.info(f"Saving HTML report to {output_html}")
        generate_html_report(evaluation_report, gate_result, output_html)
        
        # Print summary
        if not args.quiet:
            print_report_summary(evaluation_report, gate_result)
            print(f"\n Reports saved:")
            print(f"   JSON: {output_json}")
            print(f"   HTML: {output_html}")
        
        # Exit with code 0 (PASS) or 1 (FAIL)
        exit_code = 0 if gate_result["gate_status"] == "PASS" else 1
        sys.exit(exit_code)
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
