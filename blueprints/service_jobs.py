# C:/.../comphone_integrated/blueprints/service_jobs.py

from flask import (
    Blueprint, render_template, request, jsonify, redirect, url_for, flash
)
from flask_login import login_required, current_user
from models import db, ServiceJob, Customer, Product, ServiceJobPart, User, Task
from sqlalchemy import or_
from datetime import datetime
from utils.decorators import admin_required

service_jobs_bp = Blueprint('service_jobs', __name__, url_prefix='/service-jobs')

# ===== Service Jobs List & Dashboard =====
@service_jobs_bp.route('/')
@login_required
def list_jobs(): # <-- แก้ไขชื่อฟังก์ชันตรงนี้
    """หน้าหลักของระบบจัดการงานซ่อม"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    search = request.args.get('search', '')

    jobs_query = ServiceJob.query.order_by(ServiceJob.created_at.desc())

    if status:
        jobs_query = jobs_query.filter(ServiceJob.status == status)

    if search:
        jobs_query = jobs_query.join(Customer).filter(
            or_(
                ServiceJob.title.contains(search),
                ServiceJob.device_model.contains(search),
                Customer.name.contains(search),
                Customer.phone.contains(search)
            )
        )

    jobs = jobs_query.paginate(page=page, per_page=15, error_out=False)
    
    stats = {
        'pending': ServiceJob.query.filter_by(status='pending').count(),
        'in_progress': ServiceJob.query.filter_by(status='in_progress').count(),
        'waiting_for_parts': ServiceJob.query.filter_by(status='waiting_for_parts').count(),
        'completed': ServiceJob.query.filter_by(status='completed').count(),
    }

    return render_template('service_jobs/index.html', jobs=jobs, stats=stats, status=status, search=search)

# ===== Create & Edit Service Job =====
@service_jobs_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_job():
    """สร้างงานซ่อมใหม่"""
    if request.method == 'POST':
        try:
            new_job = ServiceJob(
                title=request.form['title'],
                customer_id=request.form['customer_id'],
                assigned_to=request.form.get('assigned_to'),
                status='pending',
                priority=request.form.get('priority', 'medium'),
                device_type=request.form.get('device_type'),
                device_brand=request.form.get('device_brand'),
                device_model=request.form.get('device_model'),
                serial_number=request.form.get('serial_number'),
                problem_description=request.form['problem_description'],
                estimated_cost=float(request.form.get('estimated_cost', 0.0)),
                created_by=current_user.id
            )
            db.session.add(new_job)
            db.session.commit()
            flash('สร้างงานซ่อมสำเร็จ', 'success')
            return redirect(url_for('service_jobs.view_job', job_id=new_job.id))
        except Exception as e:
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')

    customers = Customer.query.order_by(Customer.name).all()
    technicians = User.query.filter_by(role='technician').all()
    return render_template('service_jobs/job_form.html', job=None, customers=customers, technicians=technicians)

@service_jobs_bp.route('/<int:job_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_job(job_id):
    """แก้ไขข้อมูลงานซ่อม"""
    job = ServiceJob.query.get_or_404(job_id)
    if request.method == 'POST':
        try:
            job.title = request.form['title']
            job.customer_id = request.form['customer_id']
            job.assigned_to = request.form.get('assigned_to')
            job.status = request.form['status']
            job.priority = request.form.get('priority', 'medium')
            job.device_type = request.form.get('device_type')
            job.device_brand = request.form.get('device_brand')
            job.device_model = request.form.get('device_model')
            job.serial_number = request.form.get('serial_number')
            job.problem_description = request.form['problem_description']
            job.solution_description = request.form.get('solution_description')
            job.estimated_cost = float(request.form.get('estimated_cost', 0.0))
            job.final_cost = float(request.form.get('final_cost', 0.0))
            
            if job.status == 'completed' and not job.completed_at:
                job.completed_at = datetime.utcnow()

            db.session.commit()
            flash('อัปเดตงานซ่อมสำเร็จ', 'success')
            return redirect(url_for('service_jobs.view_job', job_id=job.id))
        except Exception as e:
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')

    customers = Customer.query.order_by(Customer.name).all()
    technicians = User.query.filter_by(role='technician').all()
    return render_template('service_jobs/job_form.html', job=job, customers=customers, technicians=technicians)


@service_jobs_bp.route('/<int:job_id>')
@login_required
def view_job(job_id):
    """ดูรายละเอียดงานซ่อม"""
    job = ServiceJob.query.get_or_404(job_id)
    parts_used = ServiceJobPart.query.filter_by(service_job_id=job.id).all()
    available_parts = Product.query.filter(Product.stock > 0, Product.is_service_part == True).all()
    
    parts_cost = sum(part.unit_price * part.quantity for part in parts_used)

    return render_template('service_jobs/job_detail.html', 
                         job=job, 
                         parts_used=parts_used, 
                         available_parts=available_parts,
                         parts_cost=parts_cost)

@service_jobs_bp.route('/api/<int:job_id>/update-status', methods=['POST'])
@login_required
def update_status(job_id):
    """API อัปเดตสถานะงานซ่อม"""
    job = ServiceJob.query.get_or_404(job_id)
    data = request.get_json()
    new_status = data.get('status')

    if not new_status:
        return jsonify({'success': False, 'message': 'ไม่พบข้อมูลสถานะ'}), 400

    job.status = new_status
    if new_status == 'completed' and not job.completed_at:
        job.completed_at = datetime.utcnow()
    
    db.session.commit()
    return jsonify({'success': True, 'message': f'อัปเดตสถานะเป็น {new_status} สำเร็จ'})

@service_jobs_bp.route('/api/<int:job_id>/add-part', methods=['POST'])
@login_required
def add_part_to_job(job_id):
    """API เพิ่มอะไหล่ในงานซ่อม"""
    job = ServiceJob.query.get_or_404(job_id)
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = int(data.get('quantity', 1))

    product = Product.query.get(product_id)
    if not product or not product.is_service_part:
        return jsonify({'success': False, 'message': 'ไม่พบอะไหล่ที่ต้องการ'}), 404

    if product.stock < quantity:
        return jsonify({'success': False, 'message': f'อะไหล่ไม่เพียงพอ (คงเหลือ: {product.stock})'}), 400

    try:
        existing_part = ServiceJobPart.query.filter_by(service_job_id=job.id, product_id=product.id).first()
        if existing_part:
            existing_part.quantity += quantity
        else:
            new_part = ServiceJobPart(
                service_job_id=job.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=product.price
            )
            db.session.add(new_part)
        
        product.stock -= quantity
        db.session.commit()

        return jsonify({'success': True, 'message': 'เพิ่มอะไหล่สำเร็จ'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
        
@service_jobs_bp.route('/api/<int:job_id>/remove-part/<int:part_id>', methods=['POST'])
@login_required
def remove_part_from_job(job_id, part_id):
    """API ลบอะไหล่ออกจากงานซ่อม"""
    part = ServiceJobPart.query.get_or_404(part_id)
    if part.service_job_id != job_id:
        return jsonify({'success': False, 'message': 'ข้อมูลไม่ถูกต้อง'}), 403

    product = Product.query.get(part.product_id)
    
    try:
        if product:
            product.stock += part.quantity
            
        db.session.delete(part)
        db.session.commit()
        return jsonify({'success': True, 'message': 'ลบอะไหล่และคืนสต็อกสำเร็จ'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500