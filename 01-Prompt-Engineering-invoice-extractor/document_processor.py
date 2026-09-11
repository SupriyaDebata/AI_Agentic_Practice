"""
document_processor.py — Extract text from multiple document formats
Supports: PDF, JPEG, PNG, BMP, TIFF, and plain text
"""

import io
from pathlib import Path
from PIL import Image
import pytesseract
import pdfplumber
from pdf2image import convert_from_bytes

# Try to find Tesseract binary
try:
    import pytesseract
    # Uncomment and set if Tesseract is in non-standard location:
    # pytesseract.pytesseract.pytesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
except ImportError:
    pytesseract = None


def extract_from_pdf(file_bytes: bytes, file_name: str = "") -> str:
    """Extract text from PDF using pdfplumber (preferred) or OCR fallback."""
    text_parts = []
    
    try:
        # Try pdfplumber first (faster, better for text-based PDFs)
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text and text.strip():
                    text_parts.append(f"--- Page {page_num} ---\n{text}")
        
        if text_parts:
            return "\n\n".join(text_parts)
    except Exception as e:
        print(f"⚠️ pdfplumber failed: {e}. Falling back to OCR...")
    
    # Fallback: Convert PDF to images and use OCR
    try:
        images = convert_from_bytes(file_bytes)
        for page_num, image in enumerate(images, 1):
            text = pytesseract.image_to_string(image)
            if text.strip():
                text_parts.append(f"--- Page {page_num} ---\n{text}")
        return "\n\n".join(text_parts) if text_parts else "[No text detected in PDF]"
    except Exception as e:
        return f"[Error extracting from PDF: {str(e)}]"


def extract_from_image(file_bytes: bytes, file_name: str = "") -> str:
    """Extract text from image (JPEG, PNG, BMP, TIFF) using OCR."""
    try:
        image = Image.open(io.BytesIO(file_bytes))
        text = pytesseract.image_to_string(image)
        return text if text.strip() else "[No text detected in image]"
    except Exception as e:
        return f"[Error extracting from image: {str(e)}]"


def extract_from_text(file_bytes: bytes, file_name: str = "") -> str:
    """Extract text from plain text file."""
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return file_bytes.decode("latin-1")
        except Exception as e:
            return f"[Error decoding text file: {str(e)}]"


def extract_text(file_bytes: bytes, file_name: str) -> str:
    """
    Smart extractor: detects file type and extracts text.
    Supports: .pdf, .jpg, .jpeg, .png, .bmp, .tiff, .gif, .txt, .doc
    
    Args:
        file_bytes: Raw file content
        file_name: Original file name (used to detect format)
    
    Returns:
        Extracted text string
    """
    ext = Path(file_name).suffix.lower()
    
    # PDF
    if ext == ".pdf":
        return extract_from_pdf(file_bytes, file_name)
    
    # Images
    elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".gif"]:
        return extract_from_image(file_bytes, file_name)
    
    # Text
    elif ext in [".txt", ".csv", ".log"]:
        return extract_from_text(file_bytes, file_name)
    
    else:
        # Try image first, then text as fallback
        try:
            return extract_from_image(file_bytes, file_name)
        except:
            return extract_from_text(file_bytes, file_name)
