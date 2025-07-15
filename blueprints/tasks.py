# C:/.../comphone_integrated/blueprints/tasks.py

from flask import (
    Blueprint, render_template, request, jsonify, redirect, url_for, flash
)
from flask_login import login_required, current_user
from models import db, Task, User, Customer
from sqlalchemy import or_
from datetime import datetime

tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')

# ===== Task List Page =====
@tasks_bp.route('/') # <-- URL ยังคงเป็น /tasks/ เหมือนเดิม
@login_required
def list_tasks(): # <-- แก้ไขชื่อฟังก์ชันตรงนี้
    """หน้าหลักสำหรับแสดงรายการ Task ทั้งหมด"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    search = request.args.get('search', '')

    tasks_query = Task.query.order_by(Task.due_date.asc().nullslast(), Task.created_at.desc())

    if status:
        tasks_query = tasks_query.filter(Task.status == status)
    if priority:
        tasks_query = tasks_query.filter(Task.priority == priority)
    if search:
        tasks_query = tasks_query.join(User, Task.assigned_to == User.id, isouter=True).filter(
            or_(
                Task.title.contains(search),
                Task.description.contains(search),
                User.full_name.contains(search)
            )
        )

    if not current_user.is_admin:
        tasks_query = tasks_query.filter(Task.assigned_to == current_user.id)

    tasks = tasks_query.paginate(page=page, per_page=20, error_out=False)

    return render_template('tasks/index.html',
                         tasks=tasks,
                         status=status,
                         priority=priority,
                         search=search)

# ... (โค้ดส่วนที่เหลือของไฟล์เหมือนเดิมทุกประการ) ...

# ===== Create & Edit Task =====
@tasks_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_task():
    """สร้าง Task ใหม่"""
    if request.method == 'POST':
        try:
            due_date = request.form.get('due_date')
            new_task = Task(
                title=request.form['title'],
                description=request.form.get('description'),
                status=request.form.get('status', 'pending'),
                priority=request.form.get('priority', 'medium'),
                assigned_to=request.form.get('assigned_to'),
                customer_id=request.form.get('customer_id'),
                created_by=current_user.id,
                due_date=datetime.fromisoformat(due_date) if due_date else None
            )
            db.session.add(new_task)
            db.session.commit()
            flash('สร้าง Task สำเร็จ', 'success')
            return redirect(url_for('tasks.list_tasks')) # <-- แก้ไขตรงนี้ให้เรียกใช้ชื่อใหม่
        except Exception as e:
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')

    users = User.query.order_by(User.full_name).all()
    customers = Customer.query.order_by(Customer.name).all()
    return render_template('tasks/task_form.html', task=None, users=users, customers=customers)


@tasks_bp.route('/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    """แก้ไข Task"""
    task = Task.query.get_or_404(task_id)
    if not current_user.is_admin and task.assigned_to != current_user.id and task.created_by != current_user.id:
        flash('คุณไม่มีสิทธิ์แก้ไข Task นี้', 'error')
        return redirect(url_for('tasks.list_tasks')) # <-- แก้ไขตรงนี้ให้เรียกใช้ชื่อใหม่

    if request.method == 'POST':
        try:
            due_date = request.form.get('due_date')
            task.title = request.form['title']
            task.description = request.form.get('description')
            task.status = request.form.get('status')
            task.priority = request.form.get('priority')
            task.assigned_to = request.form.get('assigned_to')
            task.customer_id = request.form.get('customer_id')
            task.due_date = datetime.fromisoformat(due_date) if due_date else None
            
            if task.status == 'completed' and not task.completed_at:
                task.completed_at = datetime.utcnow()

            db.session.commit()
            flash('อัปเดต Task สำเร็จ', 'success')
            return redirect(url_for('tasks.view_task', task_id=task.id))
        except Exception as e:
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')

    users = User.query.order_by(User.full_name).all()
    customers = Customer.query.order_by(Customer.name).all()
    return render_template('tasks/task_form.html', task=task, users=users, customers=customers)


@tasks_bp.route('/<int:task_id>')
@login_required
def view_task(task_id):
    """ดูรายละเอียด Task"""
    task = Task.query.get_or_404(task_id)
    return render_template('tasks/task_detail.html', task=task)


@tasks_bp.route('/api/<int:task_id>/toggle-status', methods=['POST'])
@login_required
def toggle_task_status(task_id):
    """API สำหรับเปลี่ยนสถานะ Task (เช่น ติ๊ก ✔)"""
    task = Task.query.get_or_404(task_id)
    
    if not current_user.is_admin and task.assigned_to != current_user.id:
        return jsonify({'success': False, 'message': 'ไม่มีสิทธิ์'}), 403

    try:
        if task.status == 'completed':
            task.status = 'pending'
            task.completed_at = None
        else:
            task.status = 'completed'
            task.completed_at = datetime.utcnow()
        
        db.session.commit()
        return jsonify({
            'success': True,
            'new_status': task.status,
            'message': 'อัปเดตสถานะสำเร็จ'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500