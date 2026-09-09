#!/usr/bin/env python3
"""test_quality_gate.py -- Quick validation of quality gate framework."""

import sys
from src.dataset_manager import DatasetManager
from src.quality_gate import QualityGateEvaluator
from src.evaluation_metrics import MetricsCalculator
from src import config


def test_imports():
    """Test that all modules import correctly."""
    print(" Testing imports...")
    try:
        from src.evaluation_metrics import evaluate_qa_pair, MetricsCalculator
        from src.quality_gate import QualityGateEvaluator, MetricResult, QualityGateResult
        from src.dataset_manager import DatasetManager
        from src.evaluator import RAGEvaluator
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_dataset_manager():
    """Test dataset manager functionality."""
    print("\n Testing dataset manager...")
    try:
        dm = DatasetManager()

        # Test import sample
        if dm.import_sample_dataset():
            print("✅ Sample dataset imported")
        else:
            print("❌ Failed to import sample dataset")
            return False

        # Test load
        dataset = dm.load_dataset()
        if dataset and len(dataset) > 0:
            print(f"✅ Dataset loaded with {len(dataset)} questions")
        else:
            print("❌ Failed to load dataset")
            return False

        # Test stats
        stats = dm.get_dataset_stats()
        print(f"✅ Dataset stats: {stats['total_questions']} questions")

        # Test validation
        validation = dm.validate_dataset()
        print(f"✅ Dataset validation: {'Valid' if validation['is_valid'] else 'Has issues'}")

        return True
    except Exception as e:
        print(f"❌ Dataset manager error: {e}")
        return False


def test_quality_gate():
    """Test quality gate evaluation logic."""
    print("\n Testing quality gate...")
    try:
        evaluator = QualityGateEvaluator()

        # Test with mock scores
        test_scores = {
            "faithfulness": 0.88,
            "answer_relevancy": 0.85,
            "context_precision": 0.80,
            "context_recall": 0.78,
            "citation_accuracy": 0.92,
            "hallucination_score": 0.88,
            "retrieval_f1": 0.75,
            "answer_semantic_similarity": 0.82,
            "grounded_refusal": 1.0,
        }

        result = evaluator.evaluate_metrics(test_scores)

        print(f"✅ Evaluation result: {result.overall_status}")
        print(f"   Summary: {result.summary}")
        print(f"   Metrics evaluated: {len(result.metric_results)}")

        # Check metric details
        details = evaluator.get_metric_details("faithfulness")
        if details:
            print(f"✅ Metric details available: {details['name']}")
        else:
            print("❌ Failed to get metric details")
            return False

        return True
    except Exception as e:
        print(f"❌ Quality gate error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_metrics_calculator():
    """Test metrics calculator."""
    print("\n Testing metrics calculator...")
    try:
        calc = MetricsCalculator()

        # Test citation accuracy (doesn't require LLM)
        answer = "The total revenue is $100,000 for Q1 2024."
        contexts = ["Q1 2024 revenue reached $100,000 mark."]

        score = calc.calculate_citation_accuracy(answer, contexts)
        if 0 <= score <= 1:
            print(f"✅ Citation accuracy calculated: {score:.2%}")
        else:
            print(f"❌ Citation accuracy out of range: {score}")
            return False

        # Test response completeness
        question = "What is the total revenue?"
        answer = "The total revenue for Q1 2024 is $100,000, which represents a 15% increase from Q4 2023."

        completeness = calc.calculate_response_completeness(answer, question)
        if 0 <= completeness <= 1:
            print(f"✅ Response completeness calculated: {completeness:.2%}")
        else:
            print(f"❌ Response completeness out of range: {completeness}")
            return False

        # Test retrieval F1
        relevant = ["context 1", "context 2"]
        retrieved = ["context 1", "context 3"]

        f1 = calc.calculate_retrieval_f1(relevant, retrieved)
        if 0 <= f1 <= 1:
            print(f"✅ Retrieval F1 calculated: {f1:.2%}")
        else:
            print(f"❌ Retrieval F1 out of range: {f1}")
            return False

        return True
    except Exception as e:
        print(f"❌ Metrics calculator error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_configuration():
    """Test that configuration is valid."""
    print("\n Testing configuration...")
    try:
        # Check required config values
        assert config.EVALUATION_DATASET_PATH, "Missing EVALUATION_DATASET_PATH"
        assert config.EVALUATION_REPORTS_PATH, "Missing EVALUATION_REPORTS_PATH"
        assert config.QUALITY_GATE_THRESHOLDS, "Missing QUALITY_GATE_THRESHOLDS"

        # Check thresholds
        required_metrics = [
            "faithfulness",
            "answer_relevancy",
            "context_precision",
            "context_recall",
            "citation_accuracy",
        ]

        for metric in required_metrics:
            assert metric in config.QUALITY_GATE_THRESHOLDS, f"Missing threshold for {metric}"

        print(f"✅ Configuration valid")
        print(f"   Thresholds: {len(config.QUALITY_GATE_THRESHOLDS)} metrics")
        print(f"   Dataset path: {config.EVALUATION_DATASET_PATH}")
        print(f"   Reports path: {config.EVALUATION_REPORTS_PATH}")

        return True
    except AssertionError as e:
        print(f"❌ Configuration error: {e}")
        return False
    except Exception as e:
        print(f"❌ Configuration test error: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print(" RAG Quality Gate - Framework Validation")
    print("=" * 60)

    tests = [
        ("Imports", test_imports),
        ("Configuration", test_configuration),
        ("Dataset Manager", test_dataset_manager),
        ("Metrics Calculator", test_metrics_calculator),
        ("Quality Gate", test_quality_gate),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f" {test_name} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    print("\n" + "=" * 60)
    print("📋 Test Results Summary")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = " PASS" if passed else " FAIL"
        print(f"{status} - {test_name}")
        all_passed = all_passed and passed

    print("=" * 60)

    if all_passed:
        print(" All tests passed! Quality Gate framework is ready.")
        return 0
    else:
        print(" Some tests failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
