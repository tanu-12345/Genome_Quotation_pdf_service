"""
Genome Corporation — Tax Quotation PDF Microservice
Matches exact Genome Corporation invoice template layout
Deploy: Railway / Render
Endpoint: POST /generate        -> returns PDF binary (file download)
          POST /generate-base64 -> returns base64 JSON
          GET  /health
"""

from flask import Flask, request, send_file, jsonify
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, Image)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
import io, os, base64
from datetime import datetime

app = Flask(__name__)

# ── Company Constants ─────────────────────────────────────────
COMPANY_NAME    = "Genome Corporation"
COMPANY_ADDRESS = "B-6/370, CHITRAKOOT MARG HOTEL ABHAY HAVELI JAIPUR"
COMPANY_PHONE   = "9929866773"
COMPANY_EMAIL   = "rahul@genomecorp.in"
COMPANY_GSTIN   = "08AAJFG3518N1Z1"
COMPANY_STATE   = "08-Rajasthan"

BANK_NAME       = "PUNJAB NATIONAL BANK, JAIPUR-CHITRAKOOT"
BANK_ACCOUNT    = "09974015006716"
BANK_IFSC       = "PUNB0099710"
BANK_HOLDER     = "GENOME CORPORATION"

LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'genome_logo_clean.png')

# ── Colors ────────────────────────────────────────────────────
BLACK   = HexColor('#000000')
GREY_BG = HexColor('#F5F5F5')
BORDER  = HexColor('#BBBBBB')
WHITE   = colors.white
PAGE_W, PAGE_H = A4


# ── Helpers ───────────────────────────────────────────────────
def fmt(amount):
    try:
        return f"\u20b9 {float(amount):,.2f}"
    except:
        return "\u20b9 0.00"


def number_to_words(n):
    if n == 0:
        return "Zero Rupees only"
    ones  = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven',
             'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen',
             'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
    tens  = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty',
             'Sixty', 'Seventy', 'Eighty', 'Ninety']

    def two_digit(num):
        if num < 20: return ones[num]
        return tens[num // 10] + (' ' + ones[num % 10] if num % 10 else '')

    def three_digit(num):
        if num >= 100:
            return ones[num // 100] + ' Hundred' + (' ' + two_digit(num % 100) if num % 100 else '')
        return two_digit(num)

    parts = []
    if n >= 10000000:
        parts.append(three_digit(n // 10000000) + ' Crore'); n %= 10000000
    if n >= 100000:
        parts.append(three_digit(n // 100000) + ' Lakh'); n %= 100000
    if n >= 1000:
        parts.append(three_digit(n // 1000) + ' Thousand'); n %= 1000
    if n > 0:
        parts.append(three_digit(n))
    return ' '.join(parts) + ' Rupees only'


# ── PDF Builder ───────────────────────────────────────────────
def build_quotation_pdf(d):
    """
    Build quotation PDF matching Genome Corporation template.

    Expected keys:
      quote_no        : str   e.g. "GC/QT/2026-27/00001"
      quote_date      : str   e.g. "19-05-2026"
      valid_until     : str   e.g. "18-06-2026"
      customer_name   : str
      customer_address: str
      customer_gstin  : str
      customer_state  : str   e.g. "08"
      line_items      : list of {description, hsn, qty, unit, rate}
      subtotal        : float
    """
    quote_no     = d.get('quote_no', 'GC/QT/2026-27/00001')
    quote_date   = d.get('quote_date', datetime.now().strftime('%d-%m-%Y'))
    valid_until  = d.get('valid_until', '')
    cust_name    = d.get('customer_name', 'Customer Name')
    cust_addr    = d.get('customer_address', '')
    cust_gstin   = d.get('customer_gstin', '')
    cust_state   = d.get('customer_state', '08')
    line_items   = d.get('line_items', [])
    subtotal     = float(d.get('subtotal', 0))

    cgst  = round(subtotal * 0.09, 2)
    sgst  = round(subtotal * 0.09, 2)
    total = round(subtotal + cgst + sgst, 2)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        topMargin=10*mm, bottomMargin=10*mm,
        leftMargin=10*mm, rightMargin=10*mm)

    def S(name, **kw):
        return ParagraphStyle(name, **kw)

    s_title  = S('T',  fontName='Helvetica-Bold', fontSize=13, textColor=BLACK, leading=16)
    s_co     = S('C',  fontName='Helvetica-Bold', fontSize=16, textColor=BLACK, leading=20)
    s_addr   = S('A',  fontName='Helvetica',      fontSize=8,  textColor=BLACK, leading=11)
    s_label  = S('LB', fontName='Helvetica-Bold', fontSize=8,  textColor=BLACK, leading=11)
    s_value  = S('V',  fontName='Helvetica',      fontSize=8,  textColor=BLACK, leading=11)
    s_hdr    = S('H',  fontName='Helvetica-Bold', fontSize=8,  textColor=BLACK, leading=11)
    s_cell   = S('CE', fontName='Helvetica',      fontSize=8,  textColor=BLACK, leading=11)
    s_bold8  = S('B8', fontName='Helvetica-Bold', fontSize=8,  textColor=BLACK, leading=11)
    s_words  = S('W',  fontName='Helvetica-Bold', fontSize=8,  textColor=BLACK, leading=12)
    s_small  = S('SM', fontName='Helvetica',      fontSize=7,  textColor=BLACK, leading=10)

    story = []
    CW = PAGE_W - 20*mm

    # ── Title ─────────────────────────────────────────────────
    title_tbl = Table([[Paragraph('Tax Quotation', s_title)]], colWidths=[CW])
    title_tbl.setStyle(TableStyle([
        ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING',    (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(title_tbl)
    story.append(Spacer(1, 2*mm))

    # ── Header: Logo + Company | Quotation meta ───────────────
    logo_cell = ''
    if os.path.exists(LOGO_PATH):
        logo_cell = Image(LOGO_PATH, width=20*mm, height=18*mm)

    co_block = [
        [logo_cell, Paragraph(COMPANY_NAME, s_co)],
        ['', Paragraph(COMPANY_ADDRESS, s_addr)],
        ['', Paragraph(f'Phone no.: {COMPANY_PHONE}', s_addr)],
        ['', Paragraph(f'Email: {COMPANY_EMAIL}', s_addr)],
        ['', Paragraph(f'GSTIN: {COMPANY_GSTIN}', s_addr)],
        ['', Paragraph(f'State: {COMPANY_STATE}', s_addr)],
    ]
    co_tbl = Table(co_block, colWidths=[22*mm, 68*mm])
    co_tbl.setStyle(TableStyle([
        ('SPAN',          (0,0), (0,-1)),
        ('VALIGN',        (0,0), (0,-1),  'MIDDLE'),
        ('VALIGN',        (1,0), (1,-1),  'TOP'),
        ('TOPPADDING',    (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('LEFTPADDING',   (0,0), (-1,-1), 0),
    ]))

    meta_data = [
        [Paragraph('Quotation No.', s_label),  Paragraph('Date', s_label)],
        [Paragraph(quote_no, s_bold8),          Paragraph(quote_date, s_bold8)],
        [Paragraph('Valid Until:', s_label),    Paragraph('Place of supply', s_label)],
        [Paragraph(valid_until, s_value),        Paragraph(COMPANY_STATE, s_value)],
    ]
    meta_tbl = Table(meta_data, colWidths=[45*mm, 40*mm])
    meta_tbl.setStyle(TableStyle([
        ('BOX',           (0,0), (-1,-1), 0.5, BORDER),
        ('INNERGRID',     (0,0), (-1,-1), 0.3, BORDER),
        ('TOPPADDING',    (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING',   (0,0), (-1,-1), 4),
    ]))

    header_tbl = Table([[co_tbl, meta_tbl]], colWidths=[95*mm, 90*mm])
    header_tbl.setStyle(TableStyle([
        ('BOX',           (0,0), (-1,-1), 0.5, BORDER),
        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING',    (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING',   (0,0), (-1,-1), 3),
        ('RIGHTPADDING',  (0,0), (-1,-1), 3),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 1*mm))

    # ── Bill To ───────────────────────────────────────────────
    bill_rows = [
        [Paragraph('Bill To', s_label)],
        [Paragraph(f'<b>{cust_name}</b>', s_bold8)],
        [Paragraph(cust_addr, s_addr)],
        [Paragraph(f'GSTIN : {cust_gstin}', s_addr)],
        [Paragraph(f'State: {cust_state}-Rajasthan', s_addr)],
    ]
    bill_tbl = Table(bill_rows, colWidths=[CW])
    bill_tbl.setStyle(TableStyle([
        ('BOX',           (0,0), (-1,-1), 0.5, BORDER),
        ('TOPPADDING',    (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING',   (0,0), (-1,-1), 4),
    ]))
    story.append(bill_tbl)
    story.append(Spacer(1, 1*mm))

    # ── Line Items ────────────────────────────────────────────
    li_header = [
        Paragraph('#', s_hdr),
        Paragraph('Item name', s_hdr),
        Paragraph('HSN/\nSAC', s_hdr),
        Paragraph('Quantity', s_hdr),
        Paragraph('Unit', s_hdr),
        Paragraph('Price/unit', s_hdr),
        Paragraph('Amount', s_hdr),
    ]
    li_rows = [li_header]
    total_qty = 0

    for idx, item in enumerate(line_items, 1):
        desc = item.get('description', '')
        hsn  = item.get('hsn', '')
        qty  = int(item.get('qty', 0))
        unit = item.get('unit', 'Pcs')
        rate = float(item.get('rate', 0))
        amt  = qty * rate
        total_qty += qty
        li_rows.append([
            Paragraph(str(idx), s_cell),
            Paragraph(desc, s_cell),
            Paragraph(str(hsn), s_cell),
            Paragraph(str(qty), s_cell),
            Paragraph(unit, s_cell),
            Paragraph(fmt(rate), s_cell),
            Paragraph(fmt(amt), s_cell),
        ])

    # Pad to minimum 10 rows for clean look
    while len(li_rows) < 10:
        li_rows.append(['', '', '', '', '', '', ''])

    # Total row
    li_rows.append([
        '', Paragraph('Total', s_bold8), '',
        Paragraph(str(total_qty), s_bold8),
        '', '', Paragraph(fmt(subtotal), s_bold8)
    ])

    col_widths = [8*mm, 72*mm, 16*mm, 16*mm, 12*mm, 24*mm, 24*mm]
    li_tbl = Table(li_rows, colWidths=col_widths, repeatRows=1)
    li_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),  (-1,0),  GREY_BG),
        ('BOX',           (0,0),  (-1,-1), 0.5, BORDER),
        ('INNERGRID',     (0,0),  (-1,-1), 0.3, BORDER),
        ('TOPPADDING',    (0,0),  (-1,-1), 3),
        ('BOTTOMPADDING', (0,0),  (-1,-1), 3),
        ('LEFTPADDING',   (0,0),  (-1,-1), 3),
        ('ALIGN',         (2,0),  (-1,-1), 'RIGHT'),
        ('ALIGN',         (0,0),  (0,-1),  'CENTER'),
        ('BACKGROUND',    (0,-1), (-1,-1), GREY_BG),
        ('FONTNAME',      (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('LINEABOVE',     (0,-1), (-1,-1), 0.5, BORDER),
    ]))
    story.append(li_tbl)
    story.append(Spacer(1, 1*mm))

    # ── Amounts ───────────────────────────────────────────────
    words_text = number_to_words(int(round(total)))

    amounts_right = [
        [Paragraph('Sub Total', s_label),         Paragraph(fmt(subtotal), s_cell)],
        [Paragraph('Tax (18%)', s_label),           Paragraph(fmt(cgst + sgst), s_cell)],
        [Paragraph('<b>Total</b>', s_bold8), Paragraph(f'<b>{fmt(total)}</b>', s_bold8)],
    ]
    amt_right_tbl = Table(amounts_right, colWidths=[30*mm, 30*mm])
    amt_right_tbl.setStyle(TableStyle([
        ('BOX',           (0,0), (-1,-1), 0.5, BORDER),
        ('INNERGRID',     (0,0), (-1,-1), 0.3, BORDER),
        ('TOPPADDING',    (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING',   (0,0), (-1,-1), 4),
        ('ALIGN',         (1,0), (1,-1),  'RIGHT'),
        ('BACKGROUND',    (0,-1),(-1,-1), GREY_BG),
    ]))

    words_left = Table([
        [Paragraph('Quotation Amount in Words', s_label)],
        [Paragraph(words_text, s_words)],
    ], colWidths=[120*mm])
    words_left.setStyle(TableStyle([
        ('BOX',           (0,0), (-1,-1), 0.5, BORDER),
        ('TOPPADDING',    (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING',   (0,0), (-1,-1), 4),
        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
    ]))

    amounts_row = Table([[words_left, amt_right_tbl]], colWidths=[122*mm, 63*mm])
    amounts_row.setStyle(TableStyle([
        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING',   (0,0), (-1,-1), 0),
        ('RIGHTPADDING',  (0,0), (-1,-1), 0),
        ('TOPPADDING',    (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(amounts_row)
    story.append(Spacer(1, 1*mm))

    # ── Tax Breakdown ─────────────────────────────────────────
    hsn_val = line_items[0].get('hsn', '') if line_items else ''
    tax_rows = [
        [Paragraph('HSN/SAC', s_hdr),
         Paragraph('Taxable amount', s_hdr),
         Paragraph('CGST\nRate', s_hdr),
         Paragraph('CGST\nAmount', s_hdr),
         Paragraph('SGST\nRate', s_hdr),
         Paragraph('SGST\nAmount', s_hdr),
         Paragraph('Total Tax\nAmount', s_hdr)],
        [Paragraph(str(hsn_val), s_cell), Paragraph(fmt(subtotal), s_cell),
         Paragraph('9%', s_cell),         Paragraph(fmt(cgst), s_cell),
         Paragraph('9%', s_cell),         Paragraph(fmt(sgst), s_cell),
         Paragraph(fmt(cgst+sgst), s_cell)],
        [Paragraph('Total', s_bold8),     Paragraph(fmt(subtotal), s_bold8),
         '',                               Paragraph(fmt(cgst), s_bold8),
         '',                               Paragraph(fmt(sgst), s_bold8),
         Paragraph(fmt(cgst+sgst), s_bold8)],
    ]
    tax_tbl = Table(tax_rows, colWidths=[18*mm, 28*mm, 16*mm, 24*mm, 16*mm, 24*mm, 24*mm])
    tax_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),  (-1,0),  GREY_BG),
        ('BACKGROUND',    (0,-1), (-1,-1), GREY_BG),
        ('BOX',           (0,0),  (-1,-1), 0.5, BORDER),
        ('INNERGRID',     (0,0),  (-1,-1), 0.3, BORDER),
        ('TOPPADDING',    (0,0),  (-1,-1), 3),
        ('BOTTOMPADDING', (0,0),  (-1,-1), 3),
        ('LEFTPADDING',   (0,0),  (-1,-1), 3),
        ('ALIGN',         (1,0),  (-1,-1), 'RIGHT'),
        ('FONTNAME',      (0,-1), (-1,-1), 'Helvetica-Bold'),
    ]))
    story.append(tax_tbl)
    story.append(Spacer(1, 1*mm))

    # ── Footer: Bank | Terms | Signatory ──────────────────────
    bank_text = (
        f'<b>Bank Details</b><br/>'
        f'Name : {BANK_NAME}<br/>'
        f'Account No. : {BANK_ACCOUNT}<br/>'
        f'IFSC code : {BANK_IFSC}<br/>'
        f"Account holder's name : {BANK_HOLDER}"
    )
    terms_text = (
        '<b>Terms and conditions</b><br/>'
        'This is a quotation only, not a tax invoice.<br/>'
        'Prices valid until the date mentioned above.<br/>'
        'GST applicable as per government norms.'
    )
    signatory_text = (
        f'For : {COMPANY_NAME}<br/>'
        '<br/><br/><br/>'
        '<b>Authorized Signatory</b>'
    )

    footer_tbl = Table([
        [Paragraph(bank_text, s_small),
         Paragraph(terms_text, s_small),
         Paragraph(signatory_text, s_small)]
    ], colWidths=[65*mm, 65*mm, 55*mm])
    footer_tbl.setStyle(TableStyle([
        ('BOX',           (0,0), (-1,-1), 0.5, BORDER),
        ('INNERGRID',     (0,0), (-1,-1), 0.3, BORDER),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING',   (0,0), (-1,-1), 4),
        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
        ('ALIGN',         (2,0), (2,0),   'CENTER'),
    ]))
    story.append(footer_tbl)

    doc.build(story)
    buf.seek(0)
    return buf


# ── Routes ────────────────────────────────────────────────────
@app.route('/generate', methods=['POST'])
def generate():
    try:
        d = request.get_json(force=True)
        if not d:
            return jsonify({'error': 'No JSON body'}), 400
        buf = build_quotation_pdf(d)
        qno = d.get('quote_no', 'quotation').replace('/', '-')
        filename = f"Genome-Quotation-{qno}.pdf"
        return send_file(buf, mimetype='application/pdf',
                         as_attachment=True, download_name=filename)
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@app.route('/generate-base64', methods=['POST'])
def generate_base64():
    try:
        d = request.get_json(force=True)
        if not d:
            return jsonify({'error': 'No JSON body'}), 400
        buf = build_quotation_pdf(d)
        pdf_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        return jsonify({
            'status': 'success',
            'quote_no': d.get('quote_no'),
            'pdf_base64': pdf_b64,
            'file_size_bytes': len(buf.getvalue()),
            'generated_at': datetime.now().isoformat()
        }), 200
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'service': 'Genome Quotation PDF Service',
        'logo_found': os.path.exists(LOGO_PATH)
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
