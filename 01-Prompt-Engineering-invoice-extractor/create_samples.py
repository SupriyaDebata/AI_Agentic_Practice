"""
create_samples.py - Generate sample invoice files for testing
Creates: sample_invoice.jpg and sample_invoice.pdf
"""

from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
import io

def create_jpeg_invoice():
    """Create a sample invoice as JPEG image"""
    # Create a white background image
    width, height = 800, 1000
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    
    # Try to use a nice font, fallback to default
    try:
        title_font = ImageFont.truetype("arial.ttf", 24)
        heading_font = ImageFont.truetype("arial.ttf", 16)
        normal_font = ImageFont.truetype("arial.ttf", 12)
        small_font = ImageFont.truetype("arial.ttf", 10)
    except:
        title_font = ImageFont.load_default()
        heading_font = ImageFont.load_default()
        normal_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    y_pos = 30
    line_height = 30
    
    # Header
    draw.text((50, y_pos), "INVOICE", font=title_font, fill='black')
    y_pos += line_height + 20
    
    # Company info
    draw.text((50, y_pos), "TechVendor Inc.", font=heading_font, fill='black')
    y_pos += line_height
    draw.text((50, y_pos), "123 Business Street", font=normal_font, fill='black')
    y_pos += line_height
    draw.text((50, y_pos), "New York, NY 10001", font=normal_font, fill='black')
    y_pos += line_height
    draw.text((50, y_pos), "Email: invoice@techvendor.com", font=normal_font, fill='black')
    y_pos += line_height + 20
    
    # Invoice details
    draw.line([(50, y_pos), (750, y_pos)], fill='black', width=2)
    y_pos += 15
    
    invoice_date = datetime.now()
    due_date = invoice_date + timedelta(days=30)
    
    draw.text((50, y_pos), f"Invoice Number: INV-2026-001234", font=normal_font, fill='black')
    y_pos += line_height
    draw.text((50, y_pos), f"Invoice Date: {invoice_date.strftime('%Y-%m-%d')}", font=normal_font, fill='black')
    y_pos += line_height
    draw.text((50, y_pos), f"Due Date: {due_date.strftime('%Y-%m-%d')}", font=normal_font, fill='black')
    y_pos += line_height + 20
    
    # Bill To
    draw.text((50, y_pos), "BILL TO:", font=heading_font, fill='black')
    y_pos += line_height
    draw.text((50, y_pos), "Acme Corporation", font=normal_font, fill='black')
    y_pos += line_height
    draw.text((50, y_pos), "456 Client Avenue", font=normal_font, fill='black')
    y_pos += line_height
    draw.text((50, y_pos), "Los Angeles, CA 90001", font=normal_font, fill='black')
    y_pos += line_height + 30
    
    # Table headers
    draw.text((50, y_pos), "Description", font=heading_font, fill='black')
    draw.text((400, y_pos), "Qty", font=heading_font, fill='black')
    draw.text((480, y_pos), "Unit Price", font=heading_font, fill='black')
    draw.text((630, y_pos), "Amount", font=heading_font, fill='black')
    y_pos += line_height
    draw.line([(50, y_pos), (750, y_pos)], fill='black', width=1)
    y_pos += 15
    
    # Line items
    items = [
        ("Software License (Annual)", 2, 5000),
        ("Implementation Services", 40, 150),
        ("Training Sessions", 8, 200),
    ]
    
    for desc, qty, unit_price in items:
        total = qty * unit_price
        draw.text((50, y_pos), desc, font=normal_font, fill='black')
        draw.text((400, y_pos), str(qty), font=normal_font, fill='black')
        draw.text((480, y_pos), f"${unit_price:,.2f}", font=normal_font, fill='black')
        draw.text((630, y_pos), f"${total:,.2f}", font=normal_font, fill='black')
        y_pos += line_height
    
    y_pos += 15
    draw.line([(50, y_pos), (750, y_pos)], fill='black', width=1)
    y_pos += 15
    
    # Totals
    subtotal = sum(qty * unit_price for _, qty, unit_price in items)
    tax_rate = 0.10
    tax = subtotal * tax_rate
    total = subtotal + tax
    
    draw.text((500, y_pos), "Subtotal:", font=normal_font, fill='black')
    draw.text((630, y_pos), f"${subtotal:,.2f}", font=normal_font, fill='black')
    y_pos += line_height
    
    draw.text((500, y_pos), "Tax (10%):", font=normal_font, fill='black')
    draw.text((630, y_pos), f"${tax:,.2f}", font=normal_font, fill='black')
    y_pos += line_height
    
    draw.line([(500, y_pos), (750, y_pos)], fill='black', width=2)
    y_pos += 15
    
    draw.text((500, y_pos), "Total:", font=heading_font, fill='black')
    draw.text((630, y_pos), f"${total:,.2f}", font=heading_font, fill='black')
    y_pos += line_height + 30
    
    # Currency
    draw.text((50, y_pos), "Currency: USD", font=normal_font, fill='black')
    y_pos += line_height
    
    # Payment terms
    draw.text((50, y_pos), "Payment Terms: Net 30", font=normal_font, fill='black')
    y_pos += line_height + 20
    
    # Footer
    draw.line([(50, y_pos), (750, y_pos)], fill='black', width=1)
    y_pos += 15
    draw.text((50, y_pos), "Thank you for your business!", font=small_font, fill='gray')
    
    # Save as JPEG
    image.save('invoices/sample_invoice.jpg', 'JPEG', quality=95)
    print("✅ Created: invoices/sample_invoice.jpg")


def create_pdf_invoice():
    """Create a sample invoice as PDF"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
    except ImportError:
        print("❌ reportlab not installed. Run: pip install reportlab")
        return
    
    from datetime import datetime, timedelta
    
    filename = 'invoices/sample_invoice.pdf'
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    y = height - 0.5 * inch
    
    # Header
    c.setFont("Helvetica-Bold", 24)
    c.drawString(0.5 * inch, y, "INVOICE")
    y -= 0.3 * inch
    
    # Company info
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.5 * inch, y, "TechVendor Inc.")
    y -= 0.2 * inch
    c.setFont("Helvetica", 10)
    c.drawString(0.5 * inch, y, "123 Business Street")
    y -= 0.15 * inch
    c.drawString(0.5 * inch, y, "New York, NY 10001")
    y -= 0.15 * inch
    c.drawString(0.5 * inch, y, "Email: invoice@techvendor.com")
    y -= 0.3 * inch
    
    # Horizontal line
    c.line(0.5 * inch, y, 7.5 * inch, y)
    y -= 0.2 * inch
    
    # Invoice details
    c.setFont("Helvetica", 10)
    invoice_date = datetime.now()
    due_date = invoice_date + timedelta(days=30)
    
    c.drawString(0.5 * inch, y, f"Invoice Number: INV-2026-001234")
    y -= 0.15 * inch
    c.drawString(0.5 * inch, y, f"Invoice Date: {invoice_date.strftime('%Y-%m-%d')}")
    y -= 0.15 * inch
    c.drawString(0.5 * inch, y, f"Due Date: {due_date.strftime('%Y-%m-%d')}")
    y -= 0.25 * inch
    
    # Bill To
    c.setFont("Helvetica-Bold", 11)
    c.drawString(0.5 * inch, y, "BILL TO:")
    y -= 0.15 * inch
    c.setFont("Helvetica", 10)
    c.drawString(0.5 * inch, y, "Acme Corporation")
    y -= 0.15 * inch
    c.drawString(0.5 * inch, y, "456 Client Avenue")
    y -= 0.15 * inch
    c.drawString(0.5 * inch, y, "Los Angeles, CA 90001")
    y -= 0.35 * inch
    
    # Table headers
    c.setFont("Helvetica-Bold", 10)
    c.drawString(0.5 * inch, y, "Description")
    c.drawString(4 * inch, y, "Qty")
    c.drawString(4.8 * inch, y, "Unit Price")
    c.drawString(6.2 * inch, y, "Amount")
    y -= 0.15 * inch
    c.line(0.5 * inch, y, 7.5 * inch, y)
    y -= 0.2 * inch
    
    # Line items
    c.setFont("Helvetica", 10)
    items = [
        ("Software License (Annual)", 2, 5000),
        ("Implementation Services", 40, 150),
        ("Training Sessions", 8, 200),
    ]
    
    for desc, qty, unit_price in items:
        total = qty * unit_price
        c.drawString(0.5 * inch, y, desc)
        c.drawString(4 * inch, y, str(qty))
        c.drawString(4.8 * inch, y, f"${unit_price:,.2f}")
        c.drawString(6.2 * inch, y, f"${total:,.2f}")
        y -= 0.2 * inch
    
    y -= 0.1 * inch
    c.line(0.5 * inch, y, 7.5 * inch, y)
    y -= 0.2 * inch
    
    # Totals
    subtotal = sum(qty * unit_price for _, qty, unit_price in items)
    tax_rate = 0.10
    tax = subtotal * tax_rate
    total = subtotal + tax
    
    c.drawString(5 * inch, y, "Subtotal:")
    c.drawString(6.2 * inch, y, f"${subtotal:,.2f}")
    y -= 0.2 * inch
    
    c.drawString(5 * inch, y, "Tax (10%):")
    c.drawString(6.2 * inch, y, f"${tax:,.2f}")
    y -= 0.2 * inch
    
    c.line(5 * inch, y, 7.5 * inch, y)
    y -= 0.15 * inch
    
    c.setFont("Helvetica-Bold", 11)
    c.drawString(5 * inch, y, "Total:")
    c.drawString(6.2 * inch, y, f"${total:,.2f}")
    y -= 0.3 * inch
    
    # Currency & Payment terms
    c.setFont("Helvetica", 10)
    c.drawString(0.5 * inch, y, "Currency: USD")
    y -= 0.2 * inch
    c.drawString(0.5 * inch, y, "Payment Terms: Net 30")
    y -= 0.3 * inch
    
    # Footer
    c.line(0.5 * inch, y, 7.5 * inch, y)
    y -= 0.2 * inch
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(0.5 * inch, y, "Thank you for your business!")
    
    # Save PDF
    c.save()
    print(f"✅ Created: {filename}")


if __name__ == "__main__":
    print("📄 Generating sample invoices...")
    try:
        create_jpeg_invoice()
    except Exception as e:
        print(f"❌ Error creating JPEG: {e}")
    
    try:
        create_pdf_invoice()
    except Exception as e:
        print(f"❌ Error creating PDF: {e}")
        print("\n💡 Tip: Install reportlab for PDF generation:")
        print("   pip install reportlab")
    
    print("\n✅ Done! Check the 'invoices/' folder for sample files.")
