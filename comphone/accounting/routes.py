# comphone/accounting/routes.py
from flask import render_template, request, current_app, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
import sqlalchemy as sa
from sqlalchemy.orm import joinedload
from comphone import db
from comphone.accounting import bp
from comphone.models import Sale, SaleItem, Product, Customer
from comphone.decorators import admin_required # Import decorator
from comphone.accounting.forms import ReportFilterForm
from datetime import datetime, time, date, timedelta

# สำหรับ PDF Export
from weasyprint import HTML, CSS
import io # เพิ่ม import io

@bp.route('/reports')
@login_required
@admin_required # กำหนดให้เฉพาะ Admin เข้าถึงหน้ารายงานได้ (ตามแผน)
def reports():
    """
    หน้ารายงานสรุปยอดขายและกำไร พร้อมตัวกรอง
    Endpoint: accounting.reports
    """
    form = ReportFilterForm(request.args)

    # กำหนดค่าเริ่มต้นของวันที่
    start_date_filter = None
    end_date_filter = None
    customer_id_filter = None

    if form.validate():
        if form.start_date.data:
            start_date_filter = datetime.combine(form.start_date.data, time.min)
        if form.end_date.data:
            end_date_filter = datetime.combine(form.end_date.data, time.max)
        if form.customer_id.data and form.customer_id.data != 0: # 0 คือ "ลูกค้าทั้งหมด"
            customer_id_filter = form.customer_id.data

    # สร้าง query สำหรับ Sale
    query = sa.select(Sale).options(
        joinedload(Sale.customer),
        joinedload(Sale.items).joinedload(SaleItem.product)
    ).order_by(Sale.timestamp.desc())

    # ใช้ตัวกรอง
    if start_date_filter:
        query = query.where(Sale.timestamp >= start_date_filter)
    if end_date_filter:
        query = query.where(Sale.timestamp <= end_date_filter)
    if customer_id_filter:
        query = query.where(Sale.customer_id == customer_id_filter)

    sales = db.session.scalars(query).unique().all()


    # คำนวณยอดขายรวมและกำไรเบื้องต้น
    total_sales = sum(sale.total_amount for sale in sales)
    total_profit = 0.0
    for sale in sales:
        for item in sale.items:
            # คำนวณกำไรสำหรับแต่ละรายการขาย: (ราคาขายต่อชิ้น - ราคาทุนต่อชิ้น) * จำนวน
            profit_per_item = item.price_per_item - item.product.cost_price
            total_profit += profit_per_item * item.quantity

    return render_template('accounting/reports.html',
                           title='รายงานสรุป',
                           form=form,
                           sales=sales,
                           total_sales=total_sales,
                           total_profit=total_profit,
                           # ส่งค่าที่เลือกในฟอร์มกลับไปเพื่อให้แสดงผลใน input
                           start_date=form.start_date.data.strftime('%Y-%m-%d') if form.start_date.data else '',
                           end_date=form.end_date.data.strftime('%Y-%m-%d') if form.end_date.data else '')


@bp.route('/receipt_pdf/<int:sale_id>')
@login_required
def receipt_pdf(sale_id):
    """
    สร้างใบเสร็จรับเงินในรูปแบบ PDF
    Endpoint: accounting.receipt_pdf
    """
    sale = db.session.scalar(
        sa.select(Sale).options(
            joinedload(Sale.customer),
            joinedload(Sale.items).joinedload(SaleItem.product)
        ).where(Sale.id == sale_id)
    )
    if not sale:
        flash('ไม่พบรายการขายที่ต้องการสร้างใบเสร็จ', 'danger')
        return redirect(url_for('accounting.reports'))

    # เรนเดอร์ HTML template สำหรับใบเสร็จ
    rendered_html = render_template('accounting/receipt_pdf_template.html', sale=sale)

    # สร้าง PDF จาก HTML
    pdf_bytes = HTML(string=rendered_html, base_url=request.url_root).write_pdf(
        stylesheets=[CSS(string='''
            @page { size: A4; margin: 1cm; }
            body { font-family: 'TH Sarabun New', sans-serif; font-size: 10pt; }
            table { width: 100%; border-collapse: collapse; margin-bottom: 10px; }
            th, td { border: 1px solid #000; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            .text-right { text-align: right; }
            .text-center { text-align: center; }
            .header, .footer { text-align: center; margin-bottom: 20px; }
            .total { font-size: 12pt; font-weight: bold; }
        ''')]
    )
    # แก้ไข: ห่อ bytes object ด้วย io.BytesIO
    return send_file(io.BytesIO(pdf_bytes), mimetype='application/pdf', download_name=f'receipt_{sale.id}.pdf')


@bp.route('/quote_pdf/<int:sale_id>') # ใช้ sale_id เป็นตัวอย่าง, อาจเปลี่ยนเป็น quote_id ในอนาคต
@login_required
def quote_pdf(sale_id):
    """
    สร้างใบเสนอราคาในรูปแบบ PDF (ใช้ข้อมูล Sale เป็นตัวอย่าง)
    Endpoint: accounting.quote_pdf
    """
    sale = db.session.scalar(
        sa.select(Sale).options(
            joinedload(Sale.customer),
            joinedload(Sale.items).joinedload(SaleItem.product)
        ).where(Sale.id == sale_id)
    )
    if not sale:
        flash('ไม่พบข้อมูลที่ต้องการสร้างใบเสนอราคา', 'danger')
        return redirect(url_for('accounting.reports'))

    # เรนเดอร์ HTML template สำหรับใบเสนอราคา
    rendered_html = render_template('accounting/quote_pdf_template.html', sale=sale, timedelta=timedelta) # ส่ง timedelta ไปยัง template

    # สร้าง PDF จาก HTML
    pdf_bytes = HTML(string=rendered_html, base_url=request.url_root).write_pdf(
        stylesheets=[CSS(string='''
            @page { size: A4; margin: 1cm; }
            body { font-family: 'TH Sarabun New', sans-serif; font-size: 10pt; }
            table { width: 100%; border-collapse: collapse; margin-bottom: 10px; }
            th, td { border: 1px solid #000; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            .text-right { text-align: right; }
            .text-center { text-align: center; }
            .header, .footer { text-align: center; margin-bottom: 20px; }
            .total { font-size: 12pt; font-weight: bold; }
        ''')]
    )
    # แก้ไข: ห่อ bytes object ด้วย io.BytesIO
    return send_file(io.BytesIO(pdf_bytes), mimetype='application/pdf', download_name=f'quote_{sale.id}.pdf')
