from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, ServiceJob, Customer, Device, User, Notification
from datetime import datetime, timedelta
from sqlalchemy import func, desc, or_, and_
import json

service_jobs_bp = Blueprint('service_jobs', __name__, url_prefix='/service_jobs')

@service_jobs_bp.route('/')
@login_required
def index():
    """หน้าหลักจัดการงานบริการ"""
    try:
        # รับพารามิเตอร์การค้นหาและกรอง
        search = request.args.get('search', '', type=str).strip()
        status = request.args.get('status', '', type=str)
        priority = request.args.get('priority', '', type=str)
        sort = request.args.get('sort', 'created_desc', type=str)
        page = request.args.get('page', 1, type=int)
        per_page = 12
        
        # สร้าง query หลัก
        query = ServiceJob.query
        
        # Join กับ Customer สำหรับการค้นหา
        query = query.join(Customer, ServiceJob.customer_id == Customer.id)
        
        # ค้นหา
        if search:
            search_filter = or_(
                ServiceJob.job_number.ilike(f'%{search}%'),
                ServiceJob.problem_description.ilike(f'%{search}%'),
                Customer.first_name.ilike(f'%{search}%'),
                Customer.last_name.ilike(f'%{search}%'),
                Customer.phone.ilike(f'%{search}%')
            )
            query = query.filter(search_filter)
        
        # กรองตามสถานะ
        if status:
            from models import ServiceStatus
            try:
                status_enum = ServiceStatus(status)
                query = query.filter(ServiceJob.status == status_enum)
            except ValueError:
                pass
        
        # กรองตามความสำคัญ
        if priority:
            from models import Priority
            try:
                priority_enum = Priority(priority)
                query = query.filter(ServiceJob.priority == priority_enum)
            except ValueError:
                pass
        
        # เรียงลำดับ
        if sort == 'created_asc':
            query = query.order_by(ServiceJob.created_at.asc())
        elif sort == 'priority':
            # เรียงตามความสำคัญ: high -> medium -> low
            query = query.order_by(
                ServiceJob.priority.desc(),
                ServiceJob.created_at.desc()
            )
        elif sort == 'due_date':
            query = query.order_by(
                ServiceJob.estimated_completion.asc().nullslast(),
                ServiceJob.created_at.desc()
            )
        else:  # created_desc (default)
            query = query.order_by(ServiceJob.created_at.desc())
        
        # แบ่งหน้า
        service_jobs = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # สถิติงานบริการ
        today = datetime.utcnow().date()
        stats = {
            'total': ServiceJob.query.count(),
            'pending': ServiceJob.query.filter_by(status='pending').count(),
            'in_progress': ServiceJob.query.filter_by(status='in_progress').count(),
            'completed_today': ServiceJob.query.filter(
                and_(
                    ServiceJob.completed_at >= today,
                    ServiceJob.completed_at < today + timedelta(days=1)
                )
            ).count()
        }
        
        return render_template(
            'service_jobs/index.html',
            service_jobs=service_jobs,
            stats=stats,
            search=search,
            status=status,
            priority=priority,
            sort=sort
        )
        
    except Exception as e:
        flash(f'เกิดข้อผิดพลาดในการโหลดข้อมูล: {str(e)}', 'error')
        return render_template('service_jobs/index.html', service_jobs=None, stats={})

@service_jobs_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """สร้างงานบริการใหม่"""
    if request.method == 'POST':
        try:
            # รับข้อมูลจากฟอร์ม
            customer_id = request.form.get('customer_id', type=int)
            device_id = request.form.get('device_id', type=int)
            problem_description = request.form.get('problem_description', '').strip()
            priority = request.form.get('priority', 'medium')
            estimated_completion = request.form.get('estimated_completion')
            technician_id = request.form.get('technician_id', type=int)
            notes = request.form.get('notes', '').strip()
            
            # ตรวจสอบข้อมูลที่จำเป็น
            if not customer_id:
                flash('กรุณาเลือกลูกค้า', 'error')
                return redirect(url_for('service_jobs.create'))
                
            if not problem_description:
                flash('กรุณาระบุรายละเอียดปัญหา', 'error')
                return redirect(url_for('service_jobs.create'))
            
            # ตรวจสอบลูกค้า
            customer = db.session.get(Customer, customer_id)
            if not customer:
                flash('ไม่พบข้อมูลลูกค้า', 'error')
                return redirect(url_for('service_jobs.create'))
            
            # ตรวจสอบอุปกรณ์ (ถ้ามี)
            if device_id:
                device = db.session.get(Device, device_id)
                if not device or device.customer_id != customer_id:
                    flash('ไม่พบข้อมูลอุปกรณ์ หรืออุปกรณ์ไม่ได้เป็นของลูกค้านี้', 'error')
                    return redirect(url_for('service_jobs.create'))
            
            # แปลงวันที่
            estimated_completion_date = None
            if estimated_completion:
                try:
                    estimated_completion_date = datetime.strptime(estimated_completion, '%Y-%m-%d').date()
                except ValueError:
                    flash('รูปแบบวันที่ไม่ถูกต้อง', 'error')
                    return redirect(url_for('service_jobs.create'))
            
            # สร้างงานบริการใหม่
            from models import Priority
            service_job = ServiceJob(
                customer_id=customer_id,
                device_id=device_id if device_id else None,
                problem_description=problem_description,
                priority=Priority(priority),
                estimated_completion=estimated_completion_date,
                technician_id=technician_id if technician_id else None,
                notes=notes or None
            )
            
            db.session.add(service_job)
            db.session.flush()  # เพื่อให้ได้ ID
            
            # สร้างการแจ้งเตือนถ้ามีการมอบหมายช่าง
            if technician_id:
                notification = Notification(
                    user_id=technician_id,
                    title='งานใหม่ได้รับมอบหมาย',
                    message=f'คุณได้รับมอบหมายงานซ่อม {service_job.job_number} จากลูกค้า {customer.first_name} {customer.last_name}',
                    notification_type='task_assigned',
                    entity_type='service_job',
                    entity_id=service_job.id,
                    read=False
                )
                db.session.add(notification)
            
            db.session.commit()
            
            flash(f'สร้างงานบริการ {service_job.job_number} เรียบร้อยแล้ว', 'success')
            return redirect(url_for('service_jobs.view', id=service_job.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
            return redirect(url_for('service_jobs.create'))
    
    # GET: แสดงฟอร์มสร้างงานใหม่
    customers = Customer.query.order_by(Customer.first_name).all()
    technicians = User.query.filter_by(role='technician', is_active=True).order_by(User.first_name).all()
    
    return render_template('service_jobs/create.html', customers=customers, technicians=technicians)

@service_jobs_bp.route('/<int:id>')
@login_required
def view(id):
    """ดูรายละเอียดงานบริการ"""
    try:
        service_job = db.session.get(ServiceJob, id)
        if not service_job:
            flash('ไม่พบข้อมูลงานบริการ', 'error')
            return redirect(url_for('service_jobs.index'))
        
        return render_template('service_jobs/view.html', service_job=service_job)
        
    except Exception as e:
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
        return redirect(url_for('service_jobs.index'))

@service_jobs_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    """แก้ไขงานบริการ"""
    try:
        service_job = db.session.get(ServiceJob, id)
        if not service_job:
            flash('ไม่พบข้อมูลงานบริการ', 'error')
            return redirect(url_for('service_jobs.index'))
        
        if request.method == 'POST':
            # รับข้อมูลจากฟอร์ม
            problem_description = request.form.get('problem_description', '').strip()
            diagnosis = request.form.get('diagnosis', '').strip()
            solution = request.form.get('solution', '').strip()
            priority = request.form.get('priority', 'medium')
            status = request.form.get('status', 'pending')
            estimated_completion = request.form.get('estimated_completion')
            technician_id = request.form.get('technician_id', type=int)
            labor_cost = request.form.get('labor_cost', type=float) or 0
            parts_cost = request.form.get('parts_cost', type=float) or 0
            notes = request.form.get('notes', '').strip()
            
            # ตรวจสอบข้อมูลที่จำเป็น
            if not problem_description:
                flash('กรุณาระบุรายละเอียดปัญหา', 'error')
                return render_template('service_jobs/edit.html', service_job=service_job)
            
            # แปลงวันที่
            estimated_completion_date = None
            if estimated_completion:
                try:
                    estimated_completion_date = datetime.strptime(estimated_completion, '%Y-%m-%d').date()
                except ValueError:
                    flash('รูปแบบวันที่ไม่ถูกต้อง', 'error')
                    return render_template('service_jobs/edit.html', service_job=service_job)
            
            # อัปเดตข้อมูล
            from models import Priority, ServiceStatus
            old_technician = service_job.technician_id
            old_status = service_job.status
            
            service_job.problem_description = problem_description
            service_job.diagnosis = diagnosis or None
            service_job.solution = solution or None
            service_job.priority = Priority(priority)
            service_job.status = ServiceStatus(status)
            service_job.estimated_completion = estimated_completion_date
            service_job.technician_id = technician_id if technician_id else None
            service_job.labor_cost = labor_cost
            service_job.parts_cost = parts_cost
            service_job.notes = notes or None
            service_job.updated_at = datetime.utcnow()
            
            # คำนวณราคารวม
            service_job.calculate_total_cost()
            
            # ถ้าเปลี่ยนสถานะเป็นเสร็จสิ้น
            if status == 'completed' and old_status != ServiceStatus.COMPLETED:
                service_job.completed_at = datetime.utcnow()
            
            # สร้างการแจ้งเตือนถ้ามีการมอบหมายช่างใหม่
            if technician_id and technician_id != old_technician:
                notification = Notification(
                    user_id=technician_id,
                    title='งานได้รับการมอบหมายใหม่',
                    message=f'คุณได้รับมอบหมายงานซ่อม {service_job.job_number}',
                    notification_type='task_reassigned',
                    entity_type='service_job',
                    entity_id=service_job.id,
                    read=False
                )
                db.session.add(notification)
            
            db.session.commit()
            
            flash(f'อัปเดตงานบริการ {service_job.job_number} เรียบร้อยแล้ว', 'success')
            return redirect(url_for('service_jobs.view', id=service_job.id))
        
        # GET: แสดงฟอร์มแก้ไข
        technicians = User.query.filter_by(role='technician', is_active=True).order_by(User.first_name).all()
        
        return render_template('service_jobs/edit.html', service_job=service_job, technicians=technicians)
        
    except Exception as e:
        db.session.rollback()
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
        return redirect(url_for('service_jobs.index'))

@service_jobs_bp.route('/<int:id>/status', methods=['POST'])
@login_required
def update_status(id):
    """อัปเดตสถานะงานบริการ (API)"""
    try:
        service_job = db.session.get(ServiceJob, id)
        if not service_job:
            return jsonify({'success': False, 'message': 'ไม่พบข้อมูลงานบริการ'})
        
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'success': False, 'message': 'ไม่ได้ระบุสถานะใหม่'})
        
        from models import ServiceStatus
        try:
            status_enum = ServiceJobStatus(new_status)
        except ValueError:
            return jsonify({'success': False, 'message': 'สถานะไม่ถูกต้อง'})
        
        old_status = service_job.status
        service_job.status = status_enum
        service_job.updated_at = datetime.utcnow()
        
        # ถ้าเปลี่ยนสถานะเป็นเสร็จสิ้น
        if new_status == 'completed' and old_status != ServiceJobStatus.COMPLETED:
            service_job.completed_date = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'อัปเดตสถานะเป็น {status_enum.value} เรียบร้อยแล้ว'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'เกิดข้อผิดพลาด: {str(e)}'})

@service_jobs_bp.route('/<int:id>/notes', methods=['POST'])
@login_required
def update_notes(id):
    """อัปเดตหมายเหตุงานบริการ (API)"""
    try:
        service_job = db.session.get(ServiceJob, id)
        if not service_job:
            return jsonify({'success': False, 'message': 'ไม่พบข้อมูลงานบริการ'})
        
        data = request.get_json()
        notes = data.get('notes', '').strip()
        
        service_job.internal_notes = notes or None
        service_job.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'บันทึกหมายเหตุเรียบร้อยแล้ว'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'เกิดข้อผิดพลาด: {str(e)}'})

@service_jobs_bp.route('/stats')
@login_required
def get_stats():
    """API สำหรับดึงสถิติงานบริการ"""
    try:
        from models import ServiceJobStatus
        today = datetime.utcnow().date()
        
        stats = {
            'total': ServiceJob.query.count(),
            'pending': ServiceJob.query.filter_by(status=ServiceJobStatus.RECEIVED).count(),
            'in_progress': ServiceJob.query.filter_by(status=ServiceJobStatus.IN_REPAIR).count(),
            'completed_today': ServiceJob.query.filter(
                and_(
                    ServiceJob.completed_date >= today,
                    ServiceJob.completed_date < today + timedelta(days=1)
                )
            ).count()
        }
        
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'เกิดข้อผิดพลาด: {str(e)}'})

@service_jobs_bp.route('/customer/<int:customer_id>/devices')
@login_required
def get_customer_devices(customer_id):
    """API สำหรับดึงอุปกรณ์ของลูกค้า"""
    try:
        from models import CustomerDevice
        devices = CustomerDevice.query.filter_by(customer_id=customer_id).all()
        
        devices_data = []
        for device in devices:
            devices_data.append({
                'id': device.id,
                'device_type': device.device_type,
                'brand': device.brand,
                'model': device.model,
                'serial_number': device.serial_number,
                'display_name': f"{device.brand} {device.model}" + (f" ({device.serial_number})" if device.serial_number else "")
            })
        
        return jsonify({'success': True, 'devices': devices_data})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'เกิดข้อผิดพลาด: {str(e)}'})

@service_jobs_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_service_job(id):
    """ลบงานบริการ"""
    try:
        service_job = db.session.get(ServiceJob, id)
        if not service_job:
            return jsonify({'success': False, 'message': 'ไม่พบข้อมูลงานบริการ'})
        
        # ตรวจสอบสิทธิ์ (เฉพาะ admin หรือผู้สร้างงาน)
        if not current_user.is_admin and service_job.created_by != current_user.id:
            return jsonify({'success': False, 'message': 'คุณไม่มีสิทธิ์ลบงานนี้'})
        
        # ตรวจสอบว่างานยังไม่เสร็จสิ้น
        if service_job.status in [ServiceJobStatus.COMPLETED, ServiceJobStatus.DELIVERED]:
            return jsonify({'success': False, 'message': 'ไม่สามารถลบงานที่เสร็จสิ้นแล้ว'})
        
        job_number = service_job.job_number
        db.session.delete(service_job)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'ลบงานบริการ {job_number} เรียบร้อยแล้ว'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'เกิดข้อผิดพลาด: {str(e)}'})

# Helper functions
def get_service_job_filters():
    """ดึงตัวเลือกสำหรับกรองข้อมูล"""
    from models import ServiceJobStatus, TaskPriority
    
    status_choices = [
        ('', 'ทั้งหมด'),
        (ServiceJobStatus.RECEIVED.value, 'รับงาน'),
        (ServiceJobStatus.DIAGNOSED.value, 'วินิจฉัยแล้ว'),
        (ServiceJobStatus.WAITING_PARTS.value, 'รออะไหล่'),
        (ServiceJobStatus.IN_REPAIR.value, 'กำลังซ่อม'),
        (ServiceJobStatus.TESTING.value, 'ทดสอบ'),
        (ServiceJobStatus.COMPLETED.value, 'เสร็จสิ้น'),
        (ServiceJobStatus.DELIVERED.value, 'ส่งมอบแล้ว'),
        (ServiceJobStatus.CANCELLED.value, 'ยกเลิก')
    ]
    
    priority_choices = [
        ('', 'ทั้งหมด'),
        (TaskPriority.LOW.value, 'ต่ำ'),
        (TaskPriority.MEDIUM.value, 'ปานกลาง'),
        (TaskPriority.HIGH.value, 'สูง'),
        (TaskPriority.URGENT.value, 'ด่วนมาก')
    ]
    
    return status_choices, priority_choices