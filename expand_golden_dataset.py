#!/usr/bin/env python3
"""expand_golden_dataset.py -- Expand golden QA dataset with domain-specific questions."""

import json
from pathlib import Path
from datetime import datetime

from src.dataset_manager import DatasetManager
from src import config


def add_sample_questions():
    """Add 80 comprehensive domain questions to golden dataset."""

    dm = DatasetManager(config.EVALUATION_DATASET_PATH)

    # Comprehensive 80-question set covering all domains
    extended_questions = [
        # Financial Questions (10)
        {"question": "What is the total revenue?", "expected_answer": "Total revenue information"},
        {"question": "What is the net profit?", "expected_answer": "Net profit or net income"},
        {"question": "What are the operating expenses?", "expected_answer": "Operating expense details"},
        {"question": "What is the gross margin?", "expected_answer": "Gross margin percentage"},
        {"question": "What are the year-over-year growth rates?", "expected_answer": "Growth rate information"},
        {"question": "What is the cash flow position?", "expected_answer": "Cash flow details"},
        {"question": "What is the debt-to-equity ratio?", "expected_answer": "Financial ratio information"},
        {"question": "What is the EBITDA?", "expected_answer": "EBITDA or earnings information"},
        {"question": "What is the cost of goods sold?", "expected_answer": "COGS information"},
        {"question": "What are the total assets?", "expected_answer": "Asset valuation"},

        # Sales & Revenue (10)
        {"question": "Which region has the highest sales?", "expected_answer": "Top performing region"},
        {"question": "What is the sales breakdown by product?", "expected_answer": "Product sales information"},
        {"question": "What are the Q1 sales figures?", "expected_answer": "Q1 quarterly results"},
        {"question": "What is the average selling price?", "expected_answer": "ASP or pricing information"},
        {"question": "How many units were sold?", "expected_answer": "Unit sales volume"},
        {"question": "What is the monthly sales trend?", "expected_answer": "Month-over-month sales data"},
        {"question": "What are the top-performing product categories?", "expected_answer": "Category performance"},
        {"question": "What is the sales forecast?", "expected_answer": "Sales projections"},
        {"question": "What are the customer acquisition costs?", "expected_answer": "CAC or acquisition data"},
        {"question": "What is the customer lifetime value?", "expected_answer": "CLV or customer value metrics"},

        # Product Questions (10)
        {"question": "What products are available?", "expected_answer": "Product list or catalog"},
        {"question": "What is the product warranty period?", "expected_answer": "Warranty terms"},
        {"question": "What are the product specifications?", "expected_answer": "Technical specs"},
        {"question": "What features does Product A have?", "expected_answer": "Feature list"},
        {"question": "What is the pricing for each product?", "expected_answer": "Product pricing"},
        {"question": "What product has the best margin?", "expected_answer": "High-margin product"},
        {"question": "What are the product categories?", "expected_answer": "Product classification"},
        {"question": "What is the product roadmap?", "expected_answer": "Future product plans"},
        {"question": "What are the product dimensions?", "expected_answer": "Physical specifications"},
        {"question": "What colors are available?", "expected_answer": "Product variants"},

        # Customer Questions (10)
        {"question": "Who are our major customers?", "expected_answer": "Customer list"},
        {"question": "What is the customer retention rate?", "expected_answer": "Retention metrics"},
        {"question": "How many active customers do we have?", "expected_answer": "Customer count"},
        {"question": "What is the customer satisfaction score?", "expected_answer": "NPS or satisfaction data"},
        {"question": "What are the customer segments?", "expected_answer": "Segmentation information"},
        {"question": "What is the churn rate?", "expected_answer": "Customer churn metrics"},
        {"question": "What are the top customer complaints?", "expected_answer": "Customer feedback"},
        {"question": "What is the customer support response time?", "expected_answer": "Support metrics"},
        {"question": "What is the repeat purchase rate?", "expected_answer": "Repeat customer data"},
        {"question": "What are customer demographics?", "expected_answer": "Demographic information"},

        # Operations Questions (10)
        {"question": "What is the production capacity?", "expected_answer": "Capacity information"},
        {"question": "What is the inventory level?", "expected_answer": "Stock information"},
        {"question": "What is the order fulfillment time?", "expected_answer": "Lead time metrics"},
        {"question": "What are the warehouse locations?", "expected_answer": "Facility locations"},
        {"question": "What is the supply chain efficiency?", "expected_answer": "Supply chain metrics"},
        {"question": "What is the defect rate?", "expected_answer": "Quality metrics"},
        {"question": "What is the supplier list?", "expected_answer": "Supplier information"},
        {"question": "What are the production costs?", "expected_answer": "Manufacturing cost data"},
        {"question": "What is the delivery success rate?", "expected_answer": "Delivery metrics"},
        {"question": "What are the operational bottlenecks?", "expected_answer": "Process constraints"},

        # Legal & Compliance (10)
        {"question": "What is the invoice number?", "expected_answer": "Invoice ID"},
        {"question": "What are the payment terms?", "expected_answer": "Payment conditions"},
        {"question": "What is the invoice date?", "expected_answer": "Invoice timestamp"},
        {"question": "What is the billing address?", "expected_answer": "Address information"},
        {"question": "What tax was applied?", "expected_answer": "Tax information"},
        {"question": "What is the invoice total?", "expected_answer": "Amount due"},
        {"question": "What are the terms and conditions?", "expected_answer": "Legal terms"},
        {"question": "What is the contract duration?", "expected_answer": "Contract period"},
        {"question": "What are the penalties for late payment?", "expected_answer": "Late payment terms"},
        {"question": "What is the refund policy?", "expected_answer": "Refund terms"},

        # Data Validation Questions (10)
        {"question": "Is there information about company size?", "expected_answer": "Company size data"},
        {"question": "What is the employee count?", "expected_answer": "Headcount information"},
        {"question": "What are the company values?", "expected_answer": "Company mission/values"},
        {"question": "What is the founding year?", "expected_answer": "Company founding date"},
        {"question": "What is the headquarters location?", "expected_answer": "Office location"},
        {"question": "What certifications does the company have?", "expected_answer": "Certification list"},
        {"question": "What awards have been won?", "expected_answer": "Award information"},
        {"question": "What is the company vision?", "expected_answer": "Future vision statement"},
        {"question": "What market segments do we serve?", "expected_answer": "Market information"},
        {"question": "What is our competitive advantage?", "expected_answer": "Differentiation factors"},
    ]

    # Save to dataset
    if dm.save_dataset(extended_questions):
        print(f"[OK] Golden dataset expanded to {len(extended_questions)} questions")
        stats = dm.get_dataset_stats()
        print(f"[OK] Dataset stats: {stats['total_questions']} questions total")
        validation = dm.validate_dataset()
        print(f"[OK] Validation: {validation['completeness_pct']:.1f}% complete")
        return True
    else:
        print("[ERROR] Failed to save extended dataset")
        return False


def manual_import_guide():
    """Print guide for manually adding questions from documents."""

    guide = """
╔════════════════════════════════════════════════════════════════════╗
║                 MANUAL QUESTION IMPORT GUIDE                       ║
╚════════════════════════════════════════════════════════════════════╝

To add questions from your test PDFs and Excel files:

1. IDENTIFY KEY QUESTIONS
   - Review your test documents
   - List 80+ domain-specific questions
   - Examples: "What is total revenue?", "Which region has highest sales?"

2. ADD PROGRAMMATICALLY

   from src.dataset_manager import DatasetManager
   dm = DatasetManager()

   dm.add_question(
       question="What is the total revenue?",
       expected_answer="Revenue figures with currency",
       contexts=[]
   )

3. BATCH IMPORT (Recommended)

   questions = [
       {"question": "Q1", "expected_answer": "A1"},
       {"question": "Q2", "expected_answer": "A2"},
       ...
   ]
   dm.save_dataset(questions)

4. VERIFY IMPORT

   python -c "from src.dataset_manager import DatasetManager;
              dm = DatasetManager();
              stats = dm.get_dataset_stats();
              print(f'Questions: {stats[\"total_questions\"]}')"

5. RUN EVALUATION

   streamlit run app.py
   → Quality Gate Tab → Dataset Tab → View imported questions
   → Evaluation Tab → Run Full Dataset Evaluation

EXPECTED RESULTS:
- 80 questions total
- ~30-60 seconds per evaluation
- ~45-90 minutes for full evaluation run
- Comprehensive coverage of all metrics

TIPS:
✓ Questions should be domain-specific
✓ Mix simple and complex questions
✓ Include edge cases and failure scenarios
✓ Expected answers provide grounding truth
✓ Larger dataset = more reliable metrics
"""

    print(guide)


if __name__ == "__main__":
    import sys

    print("=" * 70)
    print("EXPAND GOLDEN DATASET - 80 Questions")
    print("=" * 70)

    success = add_sample_questions()

    print("\n" + "=" * 70)

    if success:
        print("[SUCCESS] Dataset expanded!")
        print("\nNext steps:")
        print("1. streamlit run app.py")
        print("2. Go to Quality Gate > Dataset tab")
        print("3. View the 70 questions")
        print("4. Go to Evaluation tab")
        print("5. Click 'Run Full Dataset Evaluation'")
        print("\nExpected time: 45-90 minutes for full evaluation")
    else:
        print("[FAILED] Could not expand dataset")
        sys.exit(1)
