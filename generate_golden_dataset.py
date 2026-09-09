#!/usr/bin/env python3
"""
generate_golden_dataset.py
Automatically generate golden Q&A dataset from uploaded documents.
Extracts data from PDF and Excel files, creates diverse questions.
"""

import json
import re
from pathlib import Path
from typing import Optional
import pymupdf
import pandas as pd
from datetime import datetime

# Import document processors
from src.document_processor import extract_pdf, extract_excel


class GoldenDatasetGenerator:
    """Generate quality Q&A pairs from documents for evaluation."""

    def __init__(self, output_path: Optional[Path] = None):
        self.output_path = output_path or Path(__file__).parent / "evaluation" / "datasets" / "golden_qa_v1.0.json"
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.dataset = {"version": "1.0", "generated": datetime.now().isoformat(), "qa_pairs": []}
        self.question_id = 1

    def add_question(
        self,
        question: str,
        expected_answer: str,
        document: str,
        doc_type: str,
        category: str,
        is_unanswerable: bool = False,
    ):
        """Add Q&A pair to dataset."""
        qa_pair = {
            "id": f"Q{self.question_id:03d}",
            "question": question,
            "expected_answer": expected_answer,
            "document": document,
            "doc_type": doc_type,
            "category": category,
            "is_unanswerable": is_unanswerable,
            "difficulty": "hard" if is_unanswerable or len(expected_answer) > 200 else "medium" if len(expected_answer) > 100 else "easy",
        }
        self.dataset["qa_pairs"].append(qa_pair)
        self.question_id += 1

    def process_pdf(self, pdf_path: Path):
        """Extract and generate questions from PDF."""
        print(f"\n📄 Processing PDF: {pdf_path.name}")
        try:
            text = extract_pdf(str(pdf_path), extract_text=True, extract_tables=True, extract_images=False)
            doc_name = pdf_path.stem
            self._generate_from_text(text, pdf_path.name, doc_name, "pdf")
        except Exception as e:
            print(f"❌ Error processing PDF {pdf_path.name}: {e}")

    def process_excel(self, excel_path: Path):
        """Extract and generate questions from Excel."""
        print(f"\n📊 Processing Excel: {excel_path.name}")
        try:
            df = pd.read_excel(excel_path)
            doc_name = excel_path.stem
            
            # Summary questions
            self.add_question(
                question=f"What is the structure of the {doc_name} data?",
                expected_answer=f"The dataset has {len(df)} rows and {len(df.columns)} columns: {', '.join(df.columns[:5])}.",
                document=excel_path.name,
                doc_type="excel",
                category="structure",
            )
            
            # Column-based questions
            for col in df.columns[:3]:
                if df[col].dtype in ['int64', 'float64']:
                    max_val = df[col].max()
                    min_val = df[col].min()
                    avg_val = df[col].mean()
                    self.add_question(
                        question=f"What is the range of values in the {col} column?",
                        expected_answer=f"The {col} column ranges from {min_val} to {max_val}, with an average of {avg_val:.2f}.",
                        document=excel_path.name,
                        doc_type="excel",
                        category="numerical",
                    )
                    
                    self.add_question(
                        question=f"What is the maximum {col} value?",
                        expected_answer=f"The maximum {col} value is {max_val}.",
                        document=excel_path.name,
                        doc_type="excel",
                        category="lookup",
                    )
                    
                    self.add_question(
                        question=f"What is the minimum {col} value?",
                        expected_answer=f"The minimum {col} value is {min_val}.",
                        document=excel_path.name,
                        doc_type="excel",
                        category="lookup",
                    )
            
            # Unanswerable question about Excel
            self.add_question(
                question=f"What is the executive director's salary in the {doc_name}?",
                expected_answer="I could not find this in the provided documents.",
                document=excel_path.name,
                doc_type="excel",
                category="unanswerable",
                is_unanswerable=True,
            )
            
        except Exception as e:
            print(f"❌ Error processing Excel {excel_path.name}: {e}")

    def _generate_from_text(self, text: str, doc_name: str, doc_short: str, doc_type: str):
        """Generate questions from extracted text."""
        # Clean text
        text = text[:3000]  # Limit to first 3000 chars for Q generation
        
        # Section-based questions
        sentences = text.split(".")
        for i, sent in enumerate(sentences[:5]):
            sent = sent.strip()
            if len(sent) > 20:
                self.add_question(
                    question=f"What does {doc_short} say about {sent[:30].lower()}?",
                    expected_answer=sent,
                    document=doc_name,
                    doc_type=doc_type,
                    category="summary",
                )
        
        # Extract and ask about numbers
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text)
        if numbers:
            self.add_question(
                question=f"What numerical values are mentioned in {doc_short}?",
                expected_answer=f"The document mentions values: {', '.join(set(numbers[:3]))}.",
                document=doc_name,
                doc_type=doc_type,
                category="numerical",
            )
        
        # Extract and ask about keywords
        words = [w for w in text.split() if len(w) > 5]
        if words:
            keyword = words[0]
            self.add_question(
                question=f"How does {doc_short} define or discuss '{keyword}'?",
                expected_answer=f"The document discusses {keyword} in the context of its main content.",
                document=doc_name,
                doc_type=doc_type,
                category="definition",
            )
        
        # Multi-section question
        self.add_question(
            question=f"Summarize the key points in {doc_short}.",
            expected_answer=text[:200] + "...",
            document=doc_name,
            doc_type=doc_type,
            category="summary",
        )
        
        # Intentionally unanswerable question
        self.add_question(
            question=f"What is the CEO's private email address in {doc_short}?",
            expected_answer="I could not find this in the provided documents.",
            document=doc_name,
            doc_type=doc_type,
            category="unanswerable",
            is_unanswerable=True,
        )

    def save(self) -> Path:
        """Save dataset to JSON file."""
        with open(self.output_path, "w") as f:
            json.dump(self.dataset, f, indent=2)
        print(f"\n✅ Dataset saved: {self.output_path}")
        print(f"   Total Q&A pairs: {len(self.dataset['qa_pairs'])}")
        
        # Summary by category
        categories = {}
        for qa in self.dataset['qa_pairs']:
            cat = qa['category']
            categories[cat] = categories.get(cat, 0) + 1
        
        print(f"   By category: {categories}")
        return self.output_path


def main():
    """Generate golden dataset from data files."""
    print("=" * 60)
    print("🚀 GOLDEN DATASET GENERATOR")
    print("=" * 60)
    
    generator = GoldenDatasetGenerator()
    data_dir = Path(__file__).parent / "data"
    
    # Process PDFs
    pdf_dir = data_dir / "pdf"
    if pdf_dir.exists():
        for pdf_file in sorted(pdf_dir.glob("*.pdf")):
            generator.process_pdf(pdf_file)
    
    # Process Excel files
    excel_dir = data_dir / "excel"
    if excel_dir.exists():
        for excel_file in sorted(excel_dir.glob("*.xlsx")):
            generator.process_excel(excel_file)
    
    # Save
    output_path = generator.save()
    print("\n" + "=" * 60)
    print("✨ Golden dataset ready for evaluation!")
    print("=" * 60)
    
    return output_path


if __name__ == "__main__":
    main()
