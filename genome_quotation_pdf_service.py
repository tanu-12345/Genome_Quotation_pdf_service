"""
Genome Corporation Quotation PDF Generator Microservice
Generates branded quotation PDFs matching company template
Deploy to: Render.com (free tier)
"""
import os
from flask import Flask, request, jsonify, send_file
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from io import BytesIO
import json
from datetime import datetime
import base64
import logging

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Company constants
COMPANY_NAME = "Genome Corporation"
COMPANY_ADDRESS = "B-6/370, CHITRAKOOT MARG\nHOTEL ABHAY HAVELI, JAIPUR"
COMPANY_PHONE = "9929866773"
COMPANY_EMAIL = "rahul@genomecorp.in"
COMPANY_GSTIN = "08AAJFG3518N1Z1"
COMPANY_STATE = "08-Rajasthan"

BANK_NAME = "PUNJAB NATIONAL BANK, JAIPUR-CHITRAKOOT"
BANK_ACCOUNT = "09974015006716"
BANK_IFSC = "PUNB0099710"
BANK_HOLDER = "GENOME CORPORATION"

SIGNATORY_NAME = "Dinesh Kumar Vaishnav"
SIGNATORY_TITLE = "Authorized Signatory"


def format_currency(amount):
    """Format number as Indian currency"""
    if amount is None:
        amount = 0
    return f"₹ {amount:,.2f}"


def number_to_words(num):
    """Convert number to Indian words"""
    ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine']
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
    scales = ['', 'Thousand', 'Lakh', 'Crore']

    if num == 0:
        return 'Zero'

    words = []
    scale_idx = 0

    while num > 0:
        chunk = num % 100
        if chunk != 0:
            chunk_words = ''
            if chunk >= 10:
                chunk_words = tens[chunk // 10]
                if chunk % 10:
                    chunk_words += ' ' + ones[chunk % 10]
            else:
                chunk_words = ones[chunk]

            if scales[scale_idx]:
                chunk_words += ' ' + scales[scale_idx]
            words.insert(0, chunk_words)

        num = num // 100
        scale_idx += 1

    return ' '.join(words) + ' Rupees only'


def generate_quotation_pdf(data):
    """
    Generate quotation PDF from data dict
    
    Expected keys:
    - quote_id: str
    - quote_date: str (YYYY-MM-DD)
    - valid_until: str (YYYY-MM-DD)
    - customer_name: str
    - customer_address: str
    - customer_gstin: str
    - customer_state: str (2-digit code, e.g., "08")
    - line_items: list of dicts with keys: description, hsn, qty, unit, rate
    - subtotal: float
    """

    # Extract data with defaults
    quote_id = data.get('quote_id', 'QT-2026-0001')
    quote_date = data.get('quote_date', datetime.now().strftime('%Y-%m-%d'))
    valid_until = data.get('valid_until', datetime.now().strftime('%Y-%m-%d'))
    customer_name = data.get('customer_name', 'Customer Name')
    customer_address = data.get('customer_address', 'Address')
    customer_gstin = data.get('customer_gstin', 'GSTIN')
    customer_state = data.get('customer_state', '08')
    line_items = data.get('line_items', [])
    subtotal = float(data.get('subtotal', 0))

    # Calculate tax (GST)
    cgst = subtotal * 0.09
    sgst = subtotal * 0.09
    total = subtotal + cgst + sgst

    # Create PDF buffer
    buffer = BytesIO()

    # Create PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    # Container for PDF elements
    elements = []

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=colors.HexColor('#000000'),
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#666666'),
        spaceAfter=20
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=colors.HexColor('#000000'),
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )

    # ===== HEADER =====
    header_data = [
        ['', COMPANY_NAME, ''],
        ['', 'Tax Quotation', '']
    ]
    header_table = Table(header_data, colWidths=[2*inch, 3*inch, 2*inch])
    header_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 0), (1, 0), 28),
        ('FONTSIZE', (1, 1), (1, 1), 12),
        ('TEXTCOLOR', (1, 1), (1, 1), colors.HexColor('#666666')),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.3*inch))

    # ===== COMPANY & INVOICE DETAILS =====
    company_details = f"""<b>{COMPANY_ADDRESS}</b><br/>
Phone: {COMPANY_PHONE}<br/>
Email: {COMPANY_EMAIL}<br/>
GSTIN: {COMPANY_GSTIN}<br/>
State: {COMPANY_STATE}"""

    invoice_details = [
        ['Invoice No.', quote_id],
        ['Date', quote_date],
        ['Valid Until', valid_until],
        ['Place of supply', COMPANY_STATE]
    ]

    top_info_table = Table([
        [Paragraph(company_details, styles['Normal']), Table(invoice_details, colWidths=[1.5*inch, 2*inch])]
    ], colWidths=[3.5*inch, 3.5*inch])

    top_info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (1, 0), (1, -1), 9),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('GRID', (1, 0), (1, -1), 1, colors.HexColor('#e0e0e0')),
    ]))

    elements.append(top_info_table)
    elements.append(Spacer(1, 0.2*inch))

    # ===== BILL TO =====
    elements.append(Paragraph('Bill To', heading_style))
    bill_to_text = f"<b>{customer_name}</b><br/>{customer_address}<br/>GSTIN: {customer_gstin}<br/>State: {customer_state}-Rajasthan"
    elements.append(Paragraph(bill_to_text, styles['Normal']))
    elements.append(Spacer(1, 0.2*inch))

    # ===== LINE ITEMS TABLE =====
    line_items_table_data = [
        ['#', 'Item name', 'HSN/SAC', 'Qty', 'Unit', 'Price/unit', 'Amount']
    ]

    total_qty = 0
    for idx, item in enumerate(line_items, 1):
        description = item.get('description', 'Item')
        hsn = item.get('hsn', '')
        qty = int(item.get('qty', 1))
        unit = item.get('unit', 'Pcs')
        rate = float(item.get('rate', 0))
        amount = qty * rate

        total_qty += qty

        line_items_table_data.append([
            str(idx),
            description,
            hsn,
            str(qty),
            unit,
            format_currency(rate),
            format_currency(amount)
        ])

    # Add total row
    line_items_table_data.append([
        '', '', '', '', 'Total', str(total_qty), format_currency(subtotal)
    ])

    line_items_table = Table(line_items_table_data, colWidths=[0.5*inch, 2.5*inch, 0.8*inch, 0.6*inch, 0.7*inch, 1.2*inch, 1.2*inch])
    line_items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5f5f5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -2), 1, colors.HexColor('#ddd')),
        ('ALIGN', (3, 1), (6, -2), 'RIGHT'),
        ('FONTSIZE', (0, 1), (-1, -2), 8),
        ('BACKGROUND', (-2, -1), (-1, -1), colors.HexColor('#f5f5f5')),
        ('FONTNAME', (-2, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, -1), (-1, -1), 1, colors.HexColor('#ddd')),
    ]))

    elements.append(line_items_table)
    elements.append(Spacer(1, 0.2*inch))

    # ===== AMOUNTS SECTION =====
    amount_words = number_to_words(int(round(total)))

    amounts_left = f"<b>Invoice Amount in Words</b><br/>{amount_words}"

    amounts_right_data = [
        ['Sub Total', format_currency(subtotal)],
        ['Tax (18%)', format_currency(cgst + sgst)],
        ['Total', format_currency(total)]
    ]

    amounts_table = Table([
        [Paragraph(amounts_left, styles['Normal']), Table(amounts_right_data, colWidths=[1.5*inch, 1.5*inch])]
    ], colWidths=[3.5*inch, 3.5*inch])

    amounts_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (1, 0), (1, -1), 9),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('GRID', (1, 0), (1, -3), 1, colors.HexColor('#e0e0e0')),
        ('BACKGROUND', (1, -1), (1, -1), colors.HexColor('#f5f5f5')),
        ('FONTNAME', (1, -1), (1, -1), 'Helvetica-Bold'),
    ]))

    elements.append(amounts_table)
    elements.append(Spacer(1, 0.2*inch))

    # ===== TAX BREAKDOWN TABLE =====
    tax_breakdown_data = [
        ['HSN/SAC', 'Taxable amount', 'CGST Rate', 'CGST Amount', 'SGST Rate', 'SGST Amount'],
        ['', format_currency(subtotal), '9%', format_currency(cgst), '9%', format_currency(sgst)],
        ['Total', format_currency(subtotal), '', format_currency(cgst), '', format_currency(sgst)]
    ]

    tax_table = Table(tax_breakdown_data, colWidths=[1.2*inch, 1.2*inch, 0.9*inch, 1.2*inch, 0.9*inch, 1.2*inch])
    tax_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5f5f5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#ddd')),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f5f5f5')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))

    elements.append(tax_table)
    elements.append(Spacer(1, 0.3*inch))

    # ===== FOOTER (Bank & Signatory) =====
    bank_details = f"""<b>Bank Details</b><br/>
Name: {BANK_NAME}<br/>
Account No.: {BANK_ACCOUNT}<br/>
IFSC Code: {BANK_IFSC}<br/>
Account Holder: {BANK_HOLDER}"""

    signatory_block = f"""<b>For: {COMPANY_NAME}</b><br/>
<br/>
<br/>
<br/>
<b>{SIGNATORY_NAME}</b><br/>
{SIGNATORY_TITLE}"""

    footer_table = Table([
        [Paragraph(bank_details, styles['Normal']), Paragraph(signatory_block, styles['Normal'])]
    ], colWidths=[3.5*inch, 3.5*inch])

    footer_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))

    elements.append(footer_table)

    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'service': 'Genome Quotation PDF Generator'}), 200


@app.route('/generate', methods=['POST'])
def generate_pdf():
    """
    Generate quotation PDF
    
    Request body: JSON with quotation data
    Returns: JSON with base64-encoded PDF
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        logger.info(f"Generating PDF for quote: {data.get('quote_id', 'unknown')}")

        # Generate PDF
        pdf_buffer = generate_quotation_pdf(data)

        # Encode to base64
        pdf_base64 = base64.b64encode(pdf_buffer.getvalue()).decode('utf-8')

        return jsonify({
            'status': 'success',
            'quote_id': data.get('quote_id'),
            'pdf_base64': pdf_base64,
            'file_size_bytes': len(pdf_buffer.getvalue()),
            'generated_at': datetime.now().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        return jsonify({'error': str(e), 'status': 'failed'}), 500


@app.route('/generate-file', methods=['POST'])
def generate_pdf_file():
    """
    Generate quotation PDF and return as file download
    
    Request body: JSON with quotation data
    Returns: PDF file
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        logger.info(f"Generating PDF file for quote: {data.get('quote_id', 'unknown')}")

        # Generate PDF
        pdf_buffer = generate_quotation_pdf(data)

        # Filename
        quote_id = data.get('quote_id', 'quotation').replace('/', '-')
        filename = f"Genome-Quotation-{quote_id}.pdf"

        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"Error generating PDF file: {str(e)}")
        return jsonify({'error': str(e), 'status': 'failed'}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
