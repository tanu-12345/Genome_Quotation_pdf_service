"""
Genome Corporation Quotation PDF Generator Microservice
"""

import os
from flask import Flask, request, jsonify, send_file
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from io import BytesIO
from datetime import datetime
import base64
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COMPANY_NAME = "Genome Corporation"
COMPANY_ADDRESS = "B-6/370, CHITRAKOOT MARG, HOTEL ABHAY HAVELI, JAIPUR"
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
    if amount is None:
        amount = 0
    return f"Rs. {amount:,.2f}"


def number_to_words(num):
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
    quote_id = data.get('quote_id', 'QT-2026-0001')
    quote_date = data.get('quote_date', datetime.now().strftime('%Y-%m-%d'))
    valid_until = data.get('valid_until', datetime.now().strftime('%Y-%m-%d'))
    customer_name = data.get('customer_name', 'Customer Name')
    customer_address = data.get('customer_address', 'Address')
    customer_gstin = data.get('customer_gstin', 'GSTIN')
    customer_state = data.get('customer_state', '08')
    line_items = data.get('line_items', [])
    subtotal = float(data.get('subtotal', 0))
    cgst = subtotal * 0.09
    sgst = subtotal * 0.09
    total = subtotal + cgst + sgst

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    elements = []
    styles = getSampleStyleSheet()
    normal = styles['Normal']
    heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=11, fontName='Helvetica-Bold', spaceAfter=8)

    # HEADER
    header_table = Table([['', COMPANY_NAME], ['', 'Tax Quotation']], colWidths=[3*inch, 4*inch])
    header_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 0), (1, 0), 24),
        ('FONTSIZE', (1, 1), (1, 1), 11),
        ('TEXTCOLOR', (1, 1), (1, 1), colors.HexColor('#666666')),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.2*inch))

    # COMPANY + INVOICE DETAILS
    company_text = f"{COMPANY_ADDRESS}\nPhone: {COMPANY_PHONE}\nEmail: {COMPANY_EMAIL}\nGSTIN: {COMPANY_GSTIN}\nState: {COMPANY_STATE}"
    invoice_data = [['Invoice No.', quote_id], ['Date', quote_date], ['Valid Until', valid_until], ['Place of supply', COMPANY_STATE]]
    inv_table = Table(invoice_data, colWidths=[1.5*inch, 2*inch])
    inv_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ]))
    top_table = Table([[Paragraph(company_text, normal), inv_table]], colWidths=[3.5*inch, 3.5*inch])
    top_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    elements.append(top_table)
    elements.append(Spacer(1, 0.2*inch))

    # BILL TO
    elements.append(Paragraph('Bill To', heading_style))
    elements.append(Paragraph(f"<b>{customer_name}</b><br/>{customer_address}<br/>GSTIN: {customer_gstin}<br/>State: {customer_state}-Rajasthan", normal))
    elements.append(Spacer(1, 0.2*inch))

    # LINE ITEMS
    items_data = [['#', 'Item name', 'HSN/SAC', 'Qty', 'Unit', 'Price/unit', 'Amount']]
    total_qty = 0
    for idx, item in enumerate(line_items, 1):
        qty = int(item.get('qty', 1))
        rate = float(item.get('rate', 0))
        total_qty += qty
        items_data.append([str(idx), item.get('description', 'Item'), item.get('hsn', ''), str(qty), item.get('unit', 'Pcs'), format_currency(rate), format_currency(qty * rate)])
    items_data.append(['', '', '', '', 'Total', str(total_qty), format_currency(subtotal)])
    items_table = Table(items_data, colWidths=[0.4*inch, 2.4*inch, 0.8*inch, 0.5*inch, 0.6*inch, 1.2*inch, 1.3*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5f5f5')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f5f5f5')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 0.2*inch))

    # AMOUNTS
    amount_words = number_to_words(int(round(total)))
    amounts_data = [['Sub Total', format_currency(subtotal)], ['Tax (18%)', format_currency(cgst + sgst)], ['Total', format_currency(total)]]
    amt_table = Table(amounts_data, colWidths=[1.5*inch, 1.5*inch])
    amt_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f5f5f5')),
    ]))
    amounts_section = Table([[Paragraph(f"<b>Invoice Amount in Words</b><br/>{amount_words}", normal), amt_table]], colWidths=[3.5*inch, 3.5*inch])
    amounts_section.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    elements.append(amounts_section)
    elements.append(Spacer(1, 0.2*inch))

    # TAX BREAKDOWN
    tax_data = [
        ['HSN/SAC', 'Taxable amount', 'CGST Rate', 'CGST Amt', 'SGST Rate', 'SGST Amt'],
        ['', format_currency(subtotal), '9%', format_currency(cgst), '9%', format_currency(sgst)],
        ['Total', format_currency(subtotal), '', format_currency(cgst), '', format_currency(sgst)]
    ]
    tax_table = Table(tax_data, colWidths=[1.1*inch, 1.2*inch, 0.9*inch, 1.1*inch, 0.9*inch, 1.1*inch])
    tax_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5f5f5')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f5f5f5')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(tax_table)
    elements.append(Spacer(1, 0.3*inch))

    # FOOTER
    bank_text = f"<b>Bank Details</b><br/>Name: {BANK_NAME}<br/>Account No.: {BANK_ACCOUNT}<br/>IFSC: {BANK_IFSC}<br/>Holder: {BANK_HOLDER}"
    sign_text = f"<b>For: {COMPANY_NAME}</b><br/><br/><br/><br/><b>{SIGNATORY_NAME}</b><br/>{SIGNATORY_TITLE}"
    footer_table = Table([[Paragraph(bank_text, normal), Paragraph(sign_text, normal)]], colWidths=[3.5*inch, 3.5*inch])
    footer_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('FONTSIZE', (0, 0), (-1, -1), 8), ('ALIGN', (1, 0), (1, 0), 'CENTER')]))
    elements.append(footer_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'Genome Quotation PDF Generator'}), 200


@app.route('/generate', methods=['POST'])
def generate_pdf():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        pdf_buffer = generate_quotation_pdf(data)
        pdf_base64 = base64.b64encode(pdf_buffer.getvalue()).decode('utf-8')
        return jsonify({'status': 'success', 'quote_id': data.get('quote_id'), 'pdf_base64': pdf_base64, 'file_size_bytes': len(pdf_buffer.getvalue()), 'generated_at': datetime.now().isoformat()}), 200
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/generate-file', methods=['POST'])
def generate_pdf_file():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        pdf_buffer = generate_quotation_pdf(data)
        quote_id = data.get('quote_id', 'quotation').replace('/', '-')
        return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name=f"Genome-Quotation-{quote_id}.pdf")
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
