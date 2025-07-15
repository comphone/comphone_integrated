from flask import render_template, redirect, url_for, flash
from flask_login import login_required
import sqlalchemy as sa
from sqlalchemy.orm import joinedload
from comphone import db
from comphone.service import bp
from comphone.service.forms import ServiceJobForm, AddPartToJobForm, UpdateStatusForm
from comphone.models import ServiceJob, Customer, Product, ServicePartUsage, StockMovement

@bp.route('/jobs')
@login_required
def jobs():
    """
    แสดงรายการงานซ่อมทั้งหมด
    Endpoint: service.jobs
    """
    service_jobs = db.session.scalars(
        sa.select(ServiceJob).options(joinedload(ServiceJob.customer)).order_by(ServiceJob.created_at.desc())
    ).all()
    return render_template('service/service_jobs.html', title="รายการงานซ่อม", jobs=service_jobs)

@bp.route('/job/new', methods=['GET', 'POST'])
@login_required
def create_job():
    """
    สร้างงานซ่อมใหม่
    Endpoint: service.create_job
    """
    form = ServiceJobForm()
    # โหลดตัวเลือกสำหรับฟิลด์ customer_id
    # เพิ่มตัวเลือกเริ่มต้น "-- เลือกลูกค้า --" ที่มีค่าเป็น None หรือ 0 (ถ้าใช้ coerce=int)
    form.customer_id.choices = [(0, '-- เลือกลูกค้า --')] + \
                               [(c.id, c.name) for c in db.session.scalars(sa.select(Customer).order_by(Customer.name))]
    
    if form.validate_on_submit():
        # ตรวจสอบว่าเลือกลูกค้าหรือไม่
        customer_id = form.customer_id.data if form.customer_id.data != 0 else None
        job = ServiceJob(customer_id=customer_id, description=form.description.data)
        db.session.add(job)
        db.session.commit()
        flash('สร้างงานซ่อมใหม่สำเร็จ!', 'success')
        return redirect(url_for('service.jobs'))
        
    return render_template('service/service_job_form.html', form=form, title='สร้างงานซ่อมใหม่')

@bp.route('/job/<int:job_id>', methods=['GET', 'POST'])
@login_required
def job_detail(job_id):
    """
    แสดงรายละเอียดงานซ่อม และฟอร์มสำหรับเบิกอะไหล่/อัปเดตสถานะ
    Endpoint: service.job_detail
    """
    job = db.get_or_404(ServiceJob, job_id)
    
    # ฟอร์มสำหรับเบิกอะไหล่
    part_form = AddPartToJobForm()
    # กรองสินค้าที่มีสต็อกมากกว่า 0 สำหรับตัวเลือก
    part_form.product_id.choices = [(p.id, f"{p.name} (คงเหลือ: {p.quantity})") for p in db.session.scalars(sa.select(Product).where(Product.quantity > 0).order_by(Product.name))]
    
    # ฟอร์มสำหรับอัปเดตสถานะ
    status_form = UpdateStatusForm(obj=job)

    return render_template('service/service_job_detail.html', title=f"รายละเอียดงานซ่อม #{job.id}", 
                           job=job, part_form=part_form, status_form=status_form)

@bp.route('/job/<int:job_id>/add_part', methods=['POST'])
@login_required
def add_part_to_job(job_id):
    """
    เพิ่มอะไหล่ที่ใช้ในงานซ่อมและตัดสต็อก
    Endpoint: service.add_part_to_job
    """
    job = db.get_or_404(ServiceJob, job_id)
    form = AddPartToJobForm()
    # ต้องสร้าง choices อีกครั้งเมื่อฟอร์มถูกสร้างใหม่ใน POST request
    form.product_id.choices = [(p.id, p.name) for p in db.session.scalars(sa.select(Product).order_by(Product.name))]

    if form.validate_on_submit():
        product = db.get_or_404(Product, form.product_id.data)
        quantity = form.quantity_used.data

        if product.quantity < quantity:
            flash(f'ไม่สามารถเบิก "{product.name}" ได้เนื่องจากสต็อกมีไม่พอ (คงเหลือ: {product.quantity})', 'danger')
            return redirect(url_for('service.job_detail', job_id=job_id))

        # ลดสต็อก
        product.quantity -= quantity
        
        # บันทึกการเบิกอะไหล่
        part_usage = ServicePartUsage(service_job_id=job.id, product_id=product.id, quantity_used=quantity)
        db.session.add(part_usage)
        
        # บันทึกการเคลื่อนไหวสต็อก
        movement = StockMovement(product_id=product.id, change=-quantity, reason='service_use', related_id=job.id)
        db.session.add(movement)

        db.session.commit()
        flash(f'เบิกอะไหล่ "{product.name}" จำนวน {quantity} ชิ้นสำเร็จ!', 'success')
    
    return redirect(url_for('service.job_detail', job_id=job_id))

@bp.route('/job/<int:job_id>/update_status', methods=['POST'])
@login_required
def update_status(job_id):
    """
    อัปเดตสถานะของงานซ่อม
    Endpoint: service.update_status
    """
    job = db.get_or_404(ServiceJob, job_id)
    form = UpdateStatusForm()
    if form.validate_on_submit():
        job.status = form.status.data
        db.session.commit()
        flash(f'อัปเดตสถานะงานซ่อม #{job.id} เป็น "{job.status}" เรียบร้อยแล้ว', 'info')
    
    return redirect(url_for('service.job_detail', job_id=job_id))
