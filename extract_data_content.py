#!/usr/bin/env python3
"""Extract content from PDFs and Excel to create golden dataset."""

import pymupdf
import pandas as pd
from pathlib import Path
import json

def extract_pdf_content():
    """Extract text from all PDFs."""
    pdf_files = list(Path("data/pdf").glob("*.pdf"))
    pdf_content = {}
    
    print("=" * 80)
    print("📄 PDF CONTENT EXTRACTION")
    print("=" * 80)
    
    for pdf_file in pdf_files:
        print(f"\n📄 FILE: {pdf_file.name}")
        print("-" * 80)
        try:
            doc = pymupdf.open(pdf_file)
            print(f"Pages: {len(doc)}")
            
            full_text = ""
            for page_num, page in enumerate(doc):
                text = page.get_text()
                full_text += text
            
            pdf_content[pdf_file.name] = {
                "path": str(pdf_file),
                "pages": len(doc),
                "length": len(full_text),
                "preview": full_text[:1000]
            }
            
            print(f"Total content: {len(full_text)} characters")
            print(f"Preview (first 500 chars):\n{full_text[:500]}\n")
            
        except Exception as e:
            print(f"❌ Error: {e}\n")
    
    return pdf_content

def extract_excel_content():
    """Extract data from all Excel files."""
    excel_files = list(Path("data/excel").glob("*.xlsx"))
    excel_content = {}
    
    print("\n" + "=" * 80)
    print("📊 EXCEL CONTENT EXTRACTION")
    print("=" * 80)
    
    for excel_file in excel_files:
        print(f"\n📊 FILE: {excel_file.name}")
        print("-" * 80)
        try:
            xl_file = pd.ExcelFile(excel_file)
            print(f"Sheets: {xl_file.sheet_names}")
            
            sheet_data = {}
            for sheet_name in xl_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                print(f"\nSheet '{sheet_name}':")
                print(f"  Shape: {df.shape}")
                print(f"  Columns: {list(df.columns)}")
                print(f"  Preview:\n{df.head(10)}\n")
                
                sheet_data[sheet_name] = {
                    "shape": df.shape,
                    "columns": list(df.columns),
                    "data": df.to_dict(orient="records")
                }
            
            excel_content[excel_file.name] = {
                "path": str(excel_file),
                "sheets": sheet_data
            }
            
        except Exception as e:
            print(f"❌ Error: {e}\n")
    
    return excel_content

if __name__ == "__main__":
    pdf_data = extract_pdf_content()
    excel_data = extract_excel_content()
    
    # Save for reference
    with open("data_analysis.json", "w") as f:
        json.dump({
            "pdfs": pdf_data,
            "excel": excel_data
        }, f, indent=2, default=str)
    
    print("\n✅ Data extraction complete! Saved to data_analysis.json")
