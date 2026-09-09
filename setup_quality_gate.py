#!/usr/bin/env python3
"""setup_quality_gate.py -- Initialize evaluation framework and dataset."""

import sys
from pathlib import Path

from src.dataset_manager import DatasetManager
from src import config


def setup_quality_gate():
    """Initialize quality gate directories and sample dataset."""

    print("Setting up RAG Quality Gate...")

    # Create evaluation directories
    eval_path = Path(config.EVALUATION_REPORTS_PATH)
    eval_path.mkdir(parents=True, exist_ok=True)
    print(f" Created evaluation reports directory: {eval_path}")

    dataset_path = Path(config.EVALUATION_DATASET_PATH)
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    print(f" Created dataset directory: {dataset_path.parent}")

    # Initialize dataset manager
    dm = DatasetManager(config.EVALUATION_DATASET_PATH)

    # Check if dataset already exists
    existing = dm.load_dataset()
    if existing:
        print(f" Dataset already exists with {len(existing)} questions")
        return

    # Import sample dataset
    print(" Importing sample dataset...")
    if dm.import_sample_dataset():
        print(" Sample dataset imported successfully!")
        stats = dm.get_dataset_stats()
        print(f"   - Total questions: {stats['total_questions']}")
        print(f"   - With answers: {stats['questions_with_answers']}")
    else:
        print(" Failed to import sample dataset")
        return False

    print("\n Quality Gate setup complete!")
    print(f"   Dataset: {config.EVALUATION_DATASET_PATH}")
    print(f"   Reports: {config.EVALUATION_REPORTS_PATH}")
    print(f"   Next: Run 'streamlit run app.py' to start the app")

    return True


if __name__ == "__main__":
    try:
        success = setup_quality_gate()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f" Setup failed: {e}")
        sys.exit(1)
