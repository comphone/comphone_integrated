#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tasks Blueprint - Complete Task Management System
Fixed and Enhanced Version
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models import db, Task, User, Customer, TaskStatus, TaskPriority, UserRole, log_activity
from sqlalchemy import or_, and_
from datetime import datetime, timezone
import os
from werkzeug.utils import secure_filename

# Create Blueprint
tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route('/')
@login_required
def list_tasks():
    """หน้าหลักสำหรับแสดงรายการ Task ทั้งหมด"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    search = request.args.get('search', '')
    assignee = request.args.get('assignee', '')
    
    # Build query
    query = Task.query
    
    # Filter by status
    if status:
        try:
            status_enum = TaskStatus(status)
            query = query.filter(Task.status == status_enum)
        except ValueError:
            pass
    
    # Filter by priority
    if priority:
        try:
            priority_enum = TaskPriority(priority)
            query = query.filter(Task.priority == priority_enum)
        except ValueError:
            pass
    
    # Filter by assignee
    if assignee:
        query = query.filter(Task.assignees.any(User.id == assignee))
    
    # Search functionality
    if search:
        query = query.filter(
            or_(
                Task.title.contains(search),
                Task.task_number.contains(search),
                Task.description.contains(search)
            )
        )
    
    # Apply role-based filtering
    if current_user.role == UserRole.TECHNICIAN:
        query = query.filter(Task.assignees.any(User.id == current_user.id))
    
    # Order by due date and creation date
    query = query.order_by(Task.due_date.asc().nullslast(), Task.created_at.desc())
    
    # Paginate results
    tasks = query.paginate(page=page, per_page=20, error_out=False)
    
    # Get filter options
    users = User.query.filter_by(is_active=True).all()
    customers = Customer.query.filter_by(status='active').all()
    
    # Statistics
    stats = {
        'total': Task.query.count(),
        'pending': Task.query.filter_by(status=TaskStatus.PENDING).count(),
        'in_progress': Task.query.filter_by(status=TaskStatus.IN_PROGRESS).count(),
        'completed': Task.query.filter_by(status=TaskStatus.COMPLETED).count(),
        'overdue': Task.query.filter(
            Task.due_date < datetime.now(timezone.utc),
            Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS])
        ).count()
    }
    
    return render_template('tasks/index.html',
                         tasks=tasks,
                         stats=stats,
                         users=users,
                         customers=customers,
                         status=status,
                         priority=priority,
                         search=search,
                         assignee=assignee,
                         TaskStatus=TaskStatus,
                         TaskPriority=TaskPriority)

@tasks_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_task():
    """สร้าง Task ใหม่"""
    if request.method == 'POST':
        try:
            # Get form data
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            priority = request.form.get('priority', 'medium')
            customer_id = request.form.get('customer_id')
            service_job_id = request.form.get('service_job_id')
            due_date = request.form.get('due_date')
            estimated_hours = request.form.get('estimated_hours')
            assignees = request.form.getlist('assignees')
            
            # Validation
            if not title:
                flash('กรุณากรอกหัวข้องาน', 'error')
                return render_template('tasks/task_form.html', 
                                     task=None, 
                                     users=User.query.filter_by(is_active=True).all(),
                                     customers=Customer.query.filter_by(status='active').all())
            
            # Create task
            task = Task(
                title=title,
                description=description,
                priority=TaskPriority(priority),
                customer_id=customer_id if customer_id else None,
                service_job_id=service_job_id if service_job_id else None,
                created_by=current_user.id,
                estimated_hours=float(estimated_hours) if estimated_hours else None
            )
            
            # Set due date
            if due_date:
                task.due_date = datetime.fromisoformat(due_date)
            
            # Generate task number
            task.generate_task_number()
            
            db.session.add(task)
            db.session.flush()  # Get the task ID
            
            # Assign users
            if assignees:
                for assignee_id in assignees:
                    user = User.query.get(assignee_id)
                    if user:
                        task.assignees.append(user)
            
            db.session.commit()
            
            # Log activity
            log_activity(
                action='task_created',
                entity_type='task',
                entity_id=task.id,
                user_id=current_user.id,
                description=f"Task {task.task_number} created"
            )
            
            flash(f'สร้างงาน {task.task_number} สำเร็จ', 'success')
            return redirect(url_for('tasks.view_task', task_id=task.id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Create task error: {e}")
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
    
    # GET request - show form
    users = User.query.filter_by(is_active=True).order_by(User.full_name).all()
    customers = Customer.query.filter_by(status='active').order_by(Customer.name).all()
    
    return render_template('tasks/task_form.html', 
                         task=None, 
                         users=users, 
                         customers=customers,
                         TaskPriority=TaskPriority)

@tasks_bp.route('/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    """แก้ไข Task"""
    task = Task.query.get_or_404(task_id)
    
    # Check permission
    if (not current_user.is_admin and 
        task.created_by != current_user.id and 
        not task.assignees.filter_by(id=current_user.id).first()):
        flash('คุณไม่มีสิทธิ์แก้ไข Task นี้', 'error')
        return redirect(url_for('tasks.list_tasks'))
    
    if request.method == 'POST':
        try:
            # Store old values for logging
            old_values = {
                'title': task.title,
                'status': task.status.value,
                'priority': task.priority.value
            }
            
            # Update task
            task.title = request.form.get('title', '').strip()
            task.description = request.form.get('description', '').strip()
            task.priority = TaskPriority(request.form.get('priority', 'medium'))
            task.customer_id = request.form.get('customer_id') or None
            task.service_job_id = request.form.get('service_job_id') or None
            task.estimated_hours = float(request.form.get('estimated_hours')) if request.form.get('estimated_hours') else None
            
            # Update status
            new_status = request.form.get('status')
            if new_status:
                task.status = TaskStatus(new_status)
                
                # Update completion date
                if task.status == TaskStatus.COMPLETED and not task.completed_at:
                    task.completed_at = datetime.now(timezone.utc)
                elif task.status != TaskStatus.COMPLETED and task.completed_at:
                    task.completed_at = None
            
            # Update due date
            due_date = request.form.get('due_date')
            if due_date:
                task.due_date = datetime.fromisoformat(due_date)
            else:
                task.due_date = None
            
            # Update assignees
            assignees = request.form.getlist('assignees')
            task.assignees.clear()
            if assignees:
                for assignee_id in assignees:
                    user = User.query.get(assignee_id)
                    if user:
                        task.assignees.append(user)
            
            task.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            
            # Log activity
            new_values = {
                'title': task.title,
                'status': task.status.value,
                'priority': task.priority.value
            }
            
            log_activity(
                action='task_updated',
                entity_type='task',
                entity_id=task.id,
                user_id=current_user.id,
                description=f"Task {task.task_number} updated",
                old_values=old_values,
                new_values=new_values
            )
            
            flash('อัปเดต Task สำเร็จ', 'success')
            return redirect(url_for('tasks.view_task', task_id=task.id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Edit task error: {e}")
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
    
    # GET request - show form
    users = User.query.filter_by(is_active=True).order_by(User.full_name).all()
    customers = Customer.query.filter_by(status='active').order_by(Customer.name).all()
    
    return render_template('tasks/task_form.html', 
                         task=task, 
                         users=users, 
                         customers=customers,
                         TaskStatus=TaskStatus,
                         TaskPriority=TaskPriority)

@tasks_bp.route('/<int:task_id>')
@login_required
def view_task(task_id):
    """ดูรายละเอียด Task"""
    task = Task.query.get_or_404(task_id)
    
    # Check permission
    if (not current_user.is_admin and 
        task.created_by != current_user.id and 
        not task.assignees.filter_by(id=current_user.id).first()):
        flash('คุณไม่มีสิทธิ์ดู Task นี้', 'error')
        return redirect(url_for('tasks.list_tasks'))
    
    # Get related data
    attachments = task.attachments.all()
    comments = task.comments.order_by(TaskComment.created_at.desc()).all()
    
    return render_template('tasks/task_detail.html', 
                         task=task,
                         attachments=attachments,
                         comments=comments)

@tasks_bp.route('/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    """ลบ Task"""
    task = Task.query.get_or_404(task_id)
    
    # Check permission
    if not current_user.is_admin and task.created_by != current_user.id:
        flash('คุณไม่มีสิทธิ์ลบ Task นี้', 'error')
        return redirect(url_for('tasks.view_task', task_id=task_id))
    
    try:
        task_number = task.task_number
        
        # Delete related records
        task.attachments.delete()
        task.comments.delete()
        task.assignees.clear()
        
        db.session.delete(task)
        db.session.commit()
        
        # Log activity
        log_activity(
            action='task_deleted',
            entity_type='task',
            entity_id=task_id,
            user_id=current_user.id,
            description=f"Task {task_number} deleted"
        )
        
        flash(f'ลบงาน {task_number} สำเร็จ', 'success')
        return redirect(url_for('tasks.list_tasks'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Delete task error: {e}")
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
        return redirect(url_for('tasks.view_task', task_id=task_id))

@tasks_bp.route('/api/<int:task_id>/toggle-status', methods=['POST'])
@login_required
def toggle_task_status(task_id):
    """API สำหรับเปลี่ยนสถานะ Task (เช่น ติ๊ก ✔)"""
    task = Task.query.get_or_404(task_id)
    
    # Check permission
    if (not current_user.is_admin and 
        task.created_by != current_user.id and 
        not task.assignees.filter_by(id=current_user.id).first()):
        return jsonify({'success': False, 'message': 'ไม่มีสิทธิ์'}), 403
    
    try:
        old_status = task.status
        
        if task.status == TaskStatus.COMPLETED:
            task.status = TaskStatus.PENDING
            task.completed_at = None
        else:
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc)
        
        task.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        # Log activity
        log_activity(
            action='task_status_toggled',
            entity_type='task',
            entity_id=task.id,
            user_id=current_user.id,
            description=f"Task {task.task_number} status changed from {old_status.value} to {task.status.value}"
        )
        
        return jsonify({
            'success': True,
            'new_status': task.status.value,
            'old_status': old_status.value,
            'message': 'อัปเดตสถานะสำเร็จ'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Toggle task status error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@tasks_bp.route('/api/<int:task_id>/assign', methods=['POST'])
@login_required
def assign_task(task_id):
    """API สำหรับมอบหมายงาน"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'ไม่มีสิทธิ์'}), 403
    
    task = Task.query.get_or_404(task_id)
    
    try:
        data = request.get_json()
        assignee_ids = data.get('assignee_ids', [])
        
        # Clear existing assignments
        task.assignees.clear()
        
        # Add new assignments
        for assignee_id in assignee_ids:
            user = User.query.get(assignee_id)
            if user:
                task.assignees.append(user)
        
        task.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        # Log activity
        assignee_names = [user.full_name for user in task.assignees]
        log_activity(
            action='task_assigned',
            entity_type='task',
            entity_id=task.id,
            user_id=current_user.id,
            description=f"Task {task.task_number} assigned to {', '.join(assignee_names)}"
        )
        
        return jsonify({
            'success': True,
            'message': 'มอบหมายงานสำเร็จ',
            'assignees': [{'id': user.id, 'name': user.full_name} for user in task.assignees]
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Assign task error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@tasks_bp.route('/api/<int:task_id>/comment', methods=['POST'])
@login_required
def add_comment(task_id):
    """API สำหรับเพิ่มความคิดเห็น"""
    task = Task.query.get_or_404(task_id)
    
    try:
        data = request.get_json()
        content = data.get('content', '').strip()
        
        if not content:
            return jsonify({'success': False, 'message': 'กรุณากรอกความคิดเห็น'}), 400
        
        comment = TaskComment(
            task_id=task.id,
            author_id=current_user.id,
            content=content,
            is_internal=data.get('is_internal', False)
        )
        
        db.session.add(comment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'เพิ่มความคิดเห็นสำเร็จ',
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'author_name': comment.author.full_name,
                'created_at': comment.created_at.isoformat(),
                'is_internal': comment.is_internal
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Add comment error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@tasks_bp.route('/api/<int:task_id>/upload', methods=['POST'])
@login_required
def upload_attachment(task_id):
    """API สำหรับอัปโหลดไฟล์แนบ"""
    task = Task.query.get_or_404(task_id)
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'ไม่พบไฟล์'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'ไม่ได้เลือกไฟล์'}), 400
        
        # Check file size
        if len(file.read()) > current_app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024):
            return jsonify({'success': False, 'message': 'ไฟล์ใหญ่เกินไป'}), 400
        
        file.seek(0)  # Reset file pointer
        
        # Secure filename
        filename = secure_filename(file.filename)
        
        # Create upload directory
        upload_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'tasks')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # Create attachment record
        attachment = TaskAttachment(
            task_id=task.id,
            filename=filename,
            original_filename=file.filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            mime_type=file.content_type,
            uploaded_by=current_user.id
        )
        
        db.session.add(attachment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'อัปโหลดไฟล์สำเร็จ',
            'attachment': {
                'id': attachment.id,
                'filename': attachment.filename,
                'original_filename': attachment.original_filename,
                'file_size': attachment.file_size,
                'uploaded_by': attachment.uploader.full_name,
                'uploaded_at': attachment.uploaded_at.isoformat()
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Upload attachment error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@tasks_bp.route('/my_tasks')
@login_required
def my_tasks():
    """งานของฉัน"""
    # Get tasks assigned to current user
    tasks = Task.query.filter(
        Task.assignees.any(User.id == current_user.id)
    ).order_by(Task.due_date.asc().nullslast(), Task.created_at.desc()).all()
    
    # Statistics
    stats = {
        'total': len(tasks),
        'pending': len([t for t in tasks if t.status == TaskStatus.PENDING]),
        'in_progress': len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS]),
        'completed': len([t for t in tasks if t.status == TaskStatus.COMPLETED]),
        'overdue': len([t for t in tasks if t.due_date and t.due_date < datetime.now(timezone.utc) and t.status != TaskStatus.COMPLETED])
    }
    
    return render_template('tasks/my_tasks.html', 
                         tasks=tasks, 
                         stats=stats,
                         TaskStatus=TaskStatus,
                         TaskPriority=TaskPriority)

@tasks_bp.route('/dashboard')
@login_required
def dashboard():
    """แดชบอร์ดงาน"""
    # Task statistics
    stats = {
        'total': Task.query.count(),
        'pending': Task.query.filter_by(status=TaskStatus.PENDING).count(),
        'in_progress': Task.query.filter_by(status=TaskStatus.IN_PROGRESS).count(),
        'completed': Task.query.filter_by(status=TaskStatus.COMPLETED).count(),
        'overdue': Task.query.filter(
            Task.due_date < datetime.now(timezone.utc),
            Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS])
        ).count()
    }
    
    # Recent tasks
    recent_tasks = Task.query.order_by(Task.created_at.desc()).limit(10).all()
    
    # My tasks (if user is assigned)
    my_tasks = []
    if current_user.role == UserRole.TECHNICIAN:
        my_tasks = Task.query.filter(
            Task.assignees.any(User.id == current_user.id)
        ).order_by(Task.due_date.asc().nullslast()).limit(5).all()
    
    # Overdue tasks
    overdue_tasks = Task.query.filter(
        Task.due_date < datetime.now(timezone.utc),
        Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS])
    ).order_by(Task.due_date.asc()).limit(5).all()
    
    return render_template('tasks/dashboard.html',
                         stats=stats,
                         recent_tasks=recent_tasks,
                         my_tasks=my_tasks,
                         overdue_tasks=overdue_tasks)

# Context processor
@tasks_bp.app_context_processor
def inject_task_vars():
    """Inject task-related variables into templates"""
    return {
        'TaskStatus': TaskStatus,
        'TaskPriority': TaskPriority
    }