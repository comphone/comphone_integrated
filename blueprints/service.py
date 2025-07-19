#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Service Jobs Blueprint - Complete Service Management System
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timezone, timedelta
from models import (
    db, ServiceJob, Customer, CustomerDevice, User, Task, Product, 
    ServiceJobStatus, TaskPriority, UserRole, log_activity
)
from sqlalchemy import func, or_, and_

service_bp = Blueprint('service_jobs', __name__)

@service_bp.route('/')
@login_required
def list_jobs():
    """รายการงานซ่อม"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    search = request.args.get('search', '')
    technician = request.args.get('technician', '')
    
    # Build query
    query = ServiceJob.query
    
    if status:
        try:
            status_enum = ServiceJobStatus(status)
            query = query.filter(ServiceJob.status == status_enum)
        except ValueError:
            pass
    
    if priority:
        try:
            priority_enum = TaskPriority(priority)
            query = query.filter(ServiceJob.priority == priority_enum)
        except ValueError:
            pass
    
    if technician:
        query = query.filter(ServiceJob.assigned_technician == technician)
    
    if search:
        query = query.join(Customer).filter(
            or_(
                ServiceJob.title.contains(search),
                ServiceJob.job_number.contains(search),
                Customer.name.contains(search),
                Customer.phone.contains(search)
            )
        )
    
    # Apply role-based filtering
    if current_user.role == UserRole.TECHNICIAN:
        query = query.filter(ServiceJob.assigned_technician == current_user.id)
    
    jobs = query.order_by(ServiceJob.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Get filter options
    technicians = User.query.filter_by(is_technician=True).all()
    
    # Statistics
    stats = {
        'total': ServiceJob.query.count(),
        'received': ServiceJob.query.filter_by(status=ServiceJobStatus.RECEIVED).count(),
        'in_repair': ServiceJob.query.filter_by(status=ServiceJobStatus.IN_REPAIR).count(),
        'completed': ServiceJob.query.filter_by(status=ServiceJobStatus.COMPLETED).count(),
        'overdue': ServiceJob.query.filter(
            ServiceJob.promised_date < datetime.now(timezone.utc),
            ServiceJob.status.in_([ServiceJobStatus.RECEIVED, ServiceJobStatus.IN_REPAIR])
        ).count()
    }
    
    return render_template('service/list_jobs.html',
                         jobs=jobs,
                         stats=stats,
                         technicians=technicians,
                         status=status,
                         priority=priority,
                         search=search,
                         technician=technician,
                         ServiceJobStatus=ServiceJobStatus,
                         TaskPriority=TaskPriority)

@service_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_job():
    """สร้างงานซ่อมใหม่"""
    if request.method == 'POST':
        try:
            # Get form data
            customer_id = request.form.get('customer_id')
            device_id = request.form.get('device_id')
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            service_type = request.form.get('service_type', 'repair')
            priority = request.form.get('priority', 'medium')
            assigned_technician = request.form.get('assigned_technician')
            estimated_cost = request.form.get('estimated_cost', 0)
            promised_date = request.form.get('promised_date')
            reported_problem = request.form.get('reported_problem', '').strip()
            
            # Validation
            if not customer_id or not title:
                flash('กรุณากรอกข้อมูลที่จำเป็น', 'error')
                return redirect(url_for('service_jobs.create_job'))
            
            # Create service job
            job = ServiceJob(
                title=title,
                description=description,
                customer_id=customer_id,
                device_id=device_id if device_id else None,
                service_type=service_type,
                priority=TaskPriority(priority),
                assigned_technician=assigned_technician if assigned_technician else None,
                created_by=current_user.id,
                estimated_cost=float(estimated_cost) if estimated_cost else 0,
                reported_problem=reported_problem,
                promised_date=datetime.fromisoformat(promised_date) if promised_date else None
            )
            
            # Generate job number
            job.generate_job_number()
            
            db.session.add(job)
            db.session.commit()
            
            # Log activity
            log_activity(
                action='service_job_created',
                entity_type='service_job',
                entity_id=job.id,
                user_id=current_user.id,
                description=f"Service job {job.job_number} created"
            )
            
            flash(f'สร้างงานซ่อม {job.job_number} เรียบร้อยแล้ว', 'success')
            return redirect(url_for('service_jobs.view_job', job_id=job.id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Create service job error: {e}")
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
    
    # Get data for form
    customers = Customer.query.filter_by(status='active').all()
    technicians = User.query.filter_by(is_technician=True, is_active=True).all()
    
    return render_template('service/create_job.html',
                         customers=customers,
                         technicians=technicians,
                         TaskPriority=TaskPriority)

@service_bp.route('/<int:job_id>')
@login_required
def view_job(job_id):
    """ดูรายละเอียดงานซ่อม"""
    job = ServiceJob.query.get_or_404(job_id)
    
    # Check permission
    if (current_user.role == UserRole.TECHNICIAN and 
        job.assigned_technician != current_user.id):
        flash('คุณไม่มีสิทธิ์เข้าถึงงานนี้', 'error')
        return redirect(url_for('service_jobs.list_jobs'))
    
    # Get related tasks
    tasks = Task.query.filter_by(service_job_id=job.id).order_by(Task.created_at.desc()).all()
    
    return render_template('service/view_job.html', job=job, tasks=tasks)

@service_bp.route('/<int:job_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_job(job_id):
    """แก้ไขงานซ่อม"""
    job = ServiceJob.query.get_or_404(job_id)
    
    # Check permission
    if (current_user.role == UserRole.TECHNICIAN and 
        job.assigned_technician != current_user.id and
        not current_user.is_admin):
        flash('คุณไม่มีสิทธิ์แก้ไขงานนี้', 'error')
        return redirect(url_for('service_jobs.view_job', job_id=job_id))
    
    if request.method == 'POST':
        try:
            # Store old values for logging
            old_values = {
                'title': job.title,
                'status': job.status.value,
                'priority': job.priority.value,
                'assigned_technician': job.assigned_technician
            }
            
            # Update fields
            job.title = request.form.get('title', '').strip()
            job.description = request.form.get('description', '').strip()
            job.service_type = request.form.get('service_type', job.service_type)
            job.priority = TaskPriority(request.form.get('priority', 'medium'))
            job.reported_problem = request.form.get('reported_problem', '').strip()
            job.diagnosis = request.form.get('diagnosis', '').strip()
            job.solution = request.form.get('solution', '').strip()
            job.work_performed = request.form.get('work_performed', '').strip()
            job.estimated_cost = float(request.form.get('estimated_cost', 0) or 0)
            job.quoted_price = float(request.form.get('quoted_price', 0) or 0)
            job.final_price = float(request.form.get('final_price', 0) or 0)
            job.internal_notes = request.form.get('internal_notes', '').strip()
            
            # Handle status change
            new_status = request.form.get('status')
            if new_status and new_status != job.status.value:
                job.status = ServiceJobStatus(new_status)
                
                # Update dates based on status
                if job.status == ServiceJobStatus.COMPLETED:
                    job.completed_date = datetime.now(timezone.utc)
                elif job.status == ServiceJobStatus.DELIVERED:
                    job.delivered_date = datetime.now(timezone.utc)
            
            # Handle technician assignment
            new_technician = request.form.get('assigned_technician')
            if new_technician and new_technician != str(job.assigned_technician):
                job.assigned_technician = int(new_technician) if new_technician else None
            
            # Handle promised date
            promised_date = request.form.get('promised_date')
            if promised_date:
                job.promised_date = datetime.fromisoformat(promised_date)
            
            # Handle customer approval
            job.customer_approved = request.form.get('customer_approved') == 'on'
            if job.customer_approved and not job.approval_date:
                job.approval_date = datetime.now(timezone.utc)
            
            # Quality control
            job.tested = request.form.get('tested') == 'on'
            job.quality_check_passed = request.form.get('quality_check_passed') == 'on'
            job.quality_notes = request.form.get('quality_notes', '').strip()
            
            job.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            
            # Log activity
            new_values = {
                'title': job.title,
                'status': job.status.value,
                'priority': job.priority.value,
                'assigned_technician': job.assigned_technician
            }
            
            log_activity(
                action='service_job_updated',
                entity_type='service_job',
                entity_id=job.id,
                user_id=current_user.id,
                description=f"Service job {job.job_number} updated",
                old_values=old_values,
                new_values=new_values
            )
            
            flash('อัพเดตงานซ่อมเรียบร้อยแล้ว', 'success')
            return redirect(url_for('service_jobs.view_job', job_id=job.id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Edit service job error: {e}")
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
    
    # Get data for form
    customers = Customer.query.filter_by(status='active').all()
    technicians = User.query.filter_by(is_technician=True, is_active=True).all()
    devices = CustomerDevice.query.filter_by(customer_id=job.customer_id).all()
    
    return render_template('service/edit_job.html',
                         job=job,
                         customers=customers,
                         technicians=technicians,
                         devices=devices,
                         ServiceJobStatus=ServiceJobStatus,
                         TaskPriority=TaskPriority)

@service_bp.route('/<int:job_id>/update_status', methods=['POST'])
@login_required
def update_status(job_id):
    """อัพเดตสถานะงานซ่อม"""
    job = ServiceJob.query.get_or_404(job_id)
    
    # Check permission
    if (current_user.role == UserRole.TECHNICIAN and 
        job.assigned_technician != current_user.id):
        flash('คุณไม่มีสิทธิ์อัพเดตงานนี้', 'error')
        return redirect(url_for('service_jobs.view_job', job_id=job_id))
    
    try:
        new_status = request.form.get('status')
        old_status = job.status.value
        
        if new_status and new_status != old_status:
            job.status = ServiceJobStatus(new_status)
            
            # Update relevant dates
            if job.status == ServiceJobStatus.COMPLETED:
                job.completed_date = datetime.now(timezone.utc)
            elif job.status == ServiceJobStatus.DELIVERED:
                job.delivered_date = datetime.now(timezone.utc)
            
            job.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            
            # Log activity
            log_activity(
                action='service_job_status_updated',
                entity_type='service_job',
                entity_id=job.id,
                user_id=current_user.id,
                description=f"Service job {job.job_number} status changed from {old_status} to {new_status}"
            )
            
            flash(f'อัพเดตสถานะเป็น {job.status.value} เรียบร้อยแล้ว', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update status error: {e}")
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
    
    return redirect(url_for('service_jobs.view_job', job_id=job_id))

@service_bp.route('/<int:job_id>/assign', methods=['POST'])
@login_required
def assign_technician(job_id):
    """มอบหมายงานให้ช่าง"""
    if not current_user.is_manager:
        flash('คุณไม่มีสิทธิ์มอบหมายงาน', 'error')
        return redirect(url_for('service_jobs.view_job', job_id=job_id))
    
    job = ServiceJob.query.get_or_404(job_id)
    
    try:
        technician_id = request.form.get('technician_id')
        old_technician = job.assigned_technician
        
        if technician_id:
            technician = User.query.get(technician_id)
            if technician and technician.is_technician:
                job.assigned_technician = technician.id
                job.updated_at = datetime.now(timezone.utc)
                db.session.commit()
                
                # Log activity
                log_activity(
                    action='service_job_assigned',
                    entity_type='service_job',
                    entity_id=job.id,
                    user_id=current_user.id,
                    description=f"Service job {job.job_number} assigned to {technician.full_name}"
                )
                
                flash(f'มอบหมายงานให้ {technician.full_name} เรียบร้อยแล้ว', 'success')
            else:
                flash('ไม่พบช่างที่เลือก', 'error')
        else:
            flash('กรุณาเลือกช่าง', 'error')
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Assign technician error: {e}")
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
    
    return redirect(url_for('service_jobs.view_job', job_id=job_id))

@service_bp.route('/<int:job_id>/delete', methods=['POST'])
@login_required
def delete_job(job_id):
    """ลบงานซ่อม"""
    if not current_user.is_admin:
        flash('คุณไม่มีสิทธิ์ลบงานซ่อม', 'error')
        return redirect(url_for('service_jobs.view_job', job_id=job_id))
    
    job = ServiceJob.query.get_or_404(job_id)
    
    try:
        job_number = job.job_number
        
        # Delete related tasks first
        Task.query.filter_by(service_job_id=job.id).delete()
        
        db.session.delete(job)
        db.session.commit()
        
        # Log activity
        log_activity(
            action='service_job_deleted',
            entity_type='service_job',
            entity_id=job_id,
            user_id=current_user.id,
            description=f"Service job {job_number} deleted"
        )
        
        flash(f'ลบงานซ่อม {job_number} เรียบร้อยแล้ว', 'success')
        return redirect(url_for('service_jobs.list_jobs'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete service job error: {e}")
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
        return redirect(url_for('service_jobs.view_job', job_id=job_id))

@service_bp.route('/dashboard')
@login_required
def dashboard():
    """แดชบอร์ดงานซ่อม"""
    # Statistics
    stats = {
        'total': ServiceJob.query.count(),
        'received': ServiceJob.query.filter_by(status=ServiceJobStatus.RECEIVED).count(),
        'in_repair': ServiceJob.query.filter_by(status=ServiceJobStatus.IN_REPAIR).count(),
        'completed': ServiceJob.query.filter_by(status=ServiceJobStatus.COMPLETED).count(),
        'delivered': ServiceJob.query.filter_by(status=ServiceJobStatus.DELIVERED).count(),
        'overdue': ServiceJob.query.filter(
            ServiceJob.promised_date < datetime.now(timezone.utc),
            ServiceJob.status.in_([ServiceJobStatus.RECEIVED, ServiceJobStatus.IN_REPAIR])
        ).count()
    }
    
    # Recent jobs
    recent_jobs = ServiceJob.query.order_by(ServiceJob.created_at.desc()).limit(10).all()
    
    # My jobs (for technicians)
    my_jobs = []
    if current_user.is_technician:
        my_jobs = ServiceJob.query.filter_by(assigned_technician=current_user.id).order_by(ServiceJob.created_at.desc()).limit(5).all()
    
    # Overdue jobs
    overdue_jobs = ServiceJob.query.filter(
        ServiceJob.promised_date < datetime.now(timezone.utc),
        ServiceJob.status.in_([ServiceJobStatus.RECEIVED, ServiceJobStatus.IN_REPAIR])
    ).order_by(ServiceJob.promised_date.asc()).limit(5).all()
    
    return render_template('service/dashboard.html',
                         stats=stats,
                         recent_jobs=recent_jobs,
                         my_jobs=my_jobs,
                         overdue_jobs=overdue_jobs)

@service_bp.route('/reports')
@login_required
def reports():
    """รายงานงานซ่อม"""
    if not current_user.can_access('reports'):
        flash('คุณไม่มีสิทธิ์เข้าถึงรายงาน', 'error')
        return redirect(url_for('service_jobs.list_jobs'))
    
    # Date range
    date_from = request.args.get('date_from', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.args.get('date_to', datetime.now().strftime('%Y-%m-%d'))
    
    # Jobs by status
    jobs_by_status = db.session.query(
        ServiceJob.status,
        func.count(ServiceJob.id).label('count')
    ).filter(
        ServiceJob.created_at >= date_from,
        ServiceJob.created_at <= date_to
    ).group_by(ServiceJob.status).all()
    
    # Jobs by technician
    jobs_by_technician = db.session.query(
        User.full_name,
        func.count(ServiceJob.id).label('count')
    ).join(
        ServiceJob, User.id == ServiceJob.assigned_technician
    ).filter(
        ServiceJob.created_at >= date_from,
        ServiceJob.created_at <= date_to
    ).group_by(User.id).all()
    
    # Revenue
    revenue_data = db.session.query(
        func.sum(ServiceJob.final_price).label('total_revenue')
    ).filter(
        ServiceJob.created_at >= date_from,
        ServiceJob.created_at <= date_to,
        ServiceJob.status == ServiceJobStatus.COMPLETED
    ).scalar() or 0
    
    return render_template('service/reports.html',
                         jobs_by_status=jobs_by_status,
                         jobs_by_technician=jobs_by_technician,
                         revenue_data=revenue_data,
                         date_from=date_from,
                         date_to=date_to)

# API Endpoints
@service_bp.route('/api/jobs')
@login_required
def api_jobs():
    """API สำหรับดึงรายการงานซ่อม"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    jobs = ServiceJob.query.order_by(ServiceJob.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'jobs': [{
            'id': job.id,
            'job_number': job.job_number,
            'title': job.title,
            'status': job.status.value,
            'priority': job.priority.value,
            'customer_name': job.customer.name,
            'created_at': job.created_at.isoformat(),
            'promised_date': job.promised_date.isoformat() if job.promised_date else None,
            'technician_name': job.technician.full_name if job.technician else None
        } for job in jobs.items],
        'pagination': {
            'page': jobs.page,
            'pages': jobs.pages,
            'per_page': jobs.per_page,
            'total': jobs.total
        }
    })

@service_bp.route('/api/jobs/<int:job_id>')
@login_required
def api_job_detail(job_id):
    """API สำหรับดึงรายละเอียดงานซ่อม"""
    job = ServiceJob.query.get_or_404(job_id)
    
    return jsonify({
        'id': job.id,
        'job_number': job.job_number,
        'title': job.title,
        'description': job.description,
        'status': job.status.value,
        'priority': job.priority.value,
        'customer': {
            'id': job.customer.id,
            'name': job.customer.name,
            'phone': job.customer.phone,
            'email': job.customer.email
        },
        'technician': {
            'id': job.technician.id,
            'name': job.technician.full_name
        } if job.technician else None,
        'created_at': job.created_at.isoformat(),
        'promised_date': job.promised_date.isoformat() if job.promised_date else None,
        'completed_date': job.completed_date.isoformat() if job.completed_date else None,
        'estimated_cost': job.estimated_cost,
        'final_price': job.final_price,
        'reported_problem': job.reported_problem,
        'diagnosis': job.diagnosis,
        'solution': job.solution
    })

# Context processor
@service_bp.app_context_processor
def inject_service_vars():
    """Inject service-related variables into templates"""
    return {
        'ServiceJobStatus': ServiceJobStatus,
        'TaskPriority': TaskPriority
    }