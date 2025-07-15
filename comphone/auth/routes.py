"""
Authentication Blueprint
Handles user login, logout, registration, and profile management
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from datetime import datetime, timezone
import re

from models import db, User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        
        # Validate input
        if not username or not password:
            flash('กรุณากรอกชื่อผู้ใช้และรหัสผ่าน', 'error')
            return render_template('auth/login.html')
        
        # Find user by username or email
        user = User.query.filter(
            db.or_(User.username == username, User.email == username)
        ).first()
        
        if user and user.is_active and user.check_password(password):
            # Successful login
            login_user(user, remember=remember)
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()
            
            # Get next URL
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            else:
                return redirect(url_for('main.dashboard'))
        else:
            flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('ออกจากระบบเรียบร้อยแล้ว', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    
    # Get user statistics
    user_stats = get_user_statistics(current_user)
    
    return render_template('auth/profile.html', 
                         user=current_user, 
                         user_stats=user_stats)

@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile"""
    
    if request.method == 'POST':
        try:
            # Update basic information
            current_user.first_name = request.form.get('first_name', '').strip()
            current_user.last_name = request.form.get('last_name', '').strip()
            current_user.email = request.form.get('email', '').strip()
            current_user.phone = request.form.get('phone', '').strip()
            
            # Validate email format
            if current_user.email and not is_valid_email(current_user.email):
                flash('รูปแบบอีเมลไม่ถูกต้อง', 'error')
                return render_template('auth/edit_profile.html')
            
            # Check if email is already used by another user
            if current_user.email:
                existing_user = User.query.filter(
                    User.email == current_user.email,
                    User.id != current_user.id
                ).first()
                if existing_user:
                    flash('อีเมลนี้ถูกใช้แล้ว', 'error')
                    return render_template('auth/edit_profile.html')
            
            # Update technician skills if user is technician
            if current_user.is_technician:
                skills = request.form.getlist('skills')
                current_user.set_skills(skills)
            
            db.session.commit()
            flash('อัปเดตโปรไฟล์เรียบร้อย', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
    
    return render_template('auth/edit_profile.html')

@auth_bp.route('/profile/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password"""
    
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate current password
        if not current_user.check_password(current_password):
            flash('รหัสผ่านปัจจุบันไม่ถูกต้อง', 'error')
            return render_template('auth/change_password.html')
        
        # Validate new password
        if len(new_password) < 6:
            flash('รหัสผ่านใหม่ต้องมีอย่างน้อย 6 ตัวอักษร', 'error')
            return render_template('auth/change_password.html')
        
        # Check password confirmation
        if new_password != confirm_password:
            flash('รหัสผ่านใหม่ไม่ตรงกัน', 'error')
            return render_template('auth/change_password.html')
        
        try:
            # Update password
            current_user.set_password(new_password)
            db.session.commit()
            
            flash('เปลี่ยนรหัสผ่านเรียบร้อย', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
    
    return render_template('auth/change_password.html')

@auth_bp.route('/users')
@login_required
def list_users():
    """List all users (admin only)"""
    
    if current_user.role != 'admin':
        flash('ไม่มีสิทธิ์เข้าถึงหน้านี้', 'error')
        return redirect(url_for('main.dashboard'))
    
    users = User.query.order_by(User.created_at.desc()).all()
    
    return render_template('auth/list_users.html', users=users)

@auth_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
def create_user():
    """Create new user (admin only)"""
    
    if current_user.role != 'admin':
        flash('ไม่มีสิทธิ์เข้าถึงหน้านี้', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        try:
            # Get form data
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            role = request.form.get('role', 'user')
            is_technician = bool(request.form.get('is_technician'))
            
            # Validate required fields
            if not username or not password or not first_name:
                flash('กรุณากรอกข้อมูลที่จำเป็น', 'error')
                return render_template('auth/create_user.html')
            
            # Validate username format
            if not re.match(r'^[a-zA-Z0-9_]+$', username):
                flash('ชื่อผู้ใช้ต้องประกอบด้วยตัวอักษร ตัวเลข และ _ เท่านั้น', 'error')
                return render_template('auth/create_user.html')
            
            # Check if username already exists
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash('ชื่อผู้ใช้นี้มีอยู่แล้ว', 'error')
                return render_template('auth/create_user.html')
            
            # Check if email already exists
            if email:
                if not is_valid_email(email):
                    flash('รูปแบบอีเมลไม่ถูกต้อง', 'error')
                    return render_template('auth/create_user.html')
                
                existing_email = User.query.filter_by(email=email).first()
                if existing_email:
                    flash('อีเมลนี้มีอยู่แล้ว', 'error')
                    return render_template('auth/create_user.html')
            
            # Validate password
            if len(password) < 6:
                flash('รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร', 'error')
                return render_template('auth/create_user.html')
            
            # Create new user
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=role,
                is_technician=is_technician
            )
            user.set_password(password)
            
            # Set technician skills if applicable
            if is_technician:
                skills = request.form.getlist('skills')
                if skills:
                    user.set_skills(skills)
            
            db.session.add(user)
            db.session.commit()
            
            flash(f'สร้างผู้ใช้ {username} เรียบร้อย', 'success')
            return redirect(url_for('auth.list_users'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
    
    return render_template('auth/create_user.html')

@auth_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """Edit user (admin only)"""
    
    if current_user.role != 'admin':
        flash('ไม่มีสิทธิ์เข้าถึงหน้านี้', 'error')
        return redirect(url_for('main.dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        try:
            # Update user information
            user.first_name = request.form.get('first_name', '').strip()
            user.last_name = request.form.get('last_name', '').strip()
            user.email = request.form.get('email', '').strip()
            user.phone = request.form.get('phone', '').strip()
            user.role = request.form.get('role', 'user')
            user.is_technician = bool(request.form.get('is_technician'))
            user.is_active = bool(request.form.get('is_active'))
            
            # Validate email
            if user.email and not is_valid_email(user.email):
                flash('รูปแบบอีเมลไม่ถูกต้อง', 'error')
                return render_template('auth/edit_user.html', user=user)
            
            # Check if email is already used by another user
            if user.email:
                existing_user = User.query.filter(
                    User.email == user.email,
                    User.id != user.id
                ).first()
                if existing_user:
                    flash('อีเมลนี้ถูกใช้แล้ว', 'error')
                    return render_template('auth/edit_user.html', user=user)
            
            # Update technician skills
            if user.is_technician:
                skills = request.form.getlist('skills')
                user.set_skills(skills)
            
            # Update password if provided
            new_password = request.form.get('new_password', '')
            if new_password:
                if len(new_password) < 6:
                    flash('รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร', 'error')
                    return render_template('auth/edit_user.html', user=user)
                user.set_password(new_password)
            
            db.session.commit()
            flash(f'อัปเดตผู้ใช้ {user.username} เรียบร้อย', 'success')
            return redirect(url_for('auth.list_users'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
    
    return render_template('auth/edit_user.html', user=user)

@auth_bp.route('/users/<int:user_id>/toggle_active', methods=['POST'])
@login_required
def toggle_user_active(user_id):
    """Toggle user active status (admin only)"""
    
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'ไม่มีสิทธิ์เข้าถึง'}), 403
    
    user = User.query.get_or_404(user_id)
    
    # Cannot deactivate own account
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': 'ไม่สามารถปิดใช้งานบัญชีตนเองได้'}), 400
    
    try:
        user.is_active = not user.is_active
        db.session.commit()
        
        status = 'เปิดใช้งาน' if user.is_active else 'ปิดใช้งาน'
        return jsonify({
            'success': True,
            'message': f'{status}ผู้ใช้ {user.username} เรียบร้อย',
            'is_active': user.is_active
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'เกิดข้อผิดพลาด: {str(e)}'}), 500

@auth_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    """Delete user (admin only)"""
    
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'ไม่มีสิทธิ์เข้าถึง'}), 403
    
    user = User.query.get_or_404(user_id)
    
    # Cannot delete own account
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': 'ไม่สามารถลบบัญชีตนเองได้'}), 400
    
    try:
        # Check if user has related data
        from models import Task, ServiceJob, Sale
        
        has_tasks = Task.query.filter(
            db.or_(Task.assigned_to_id == user_id, Task.created_by_id == user_id)
        ).first() is not None
        
        has_service_jobs = ServiceJob.query.filter_by(assigned_to_id=user_id).first() is not None
        has_sales = Sale.query.filter_by(sold_by_id=user_id).first() is not None
        
        if has_tasks or has_service_jobs or has_sales:
            return jsonify({
                'success': False,
                'message': 'ไม่สามารถลบผู้ใช้ที่มีข้อมูลการทำงานได้'
            }), 400
        
        username = user.username
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'ลบผู้ใช้ {username} เรียบร้อย'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'เกิดข้อผิดพลาด: {str(e)}'}), 500

def get_user_statistics(user):
    """Get user statistics for profile page"""
    from models import Task, ServiceJob, Sale
    
    stats = {}
    
    # Task statistics
    stats['total_tasks_assigned'] = Task.query.filter_by(assigned_to=user).count()
    stats['completed_tasks'] = Task.query.filter_by(assigned_to=user, status='completed').count()
    stats['pending_tasks'] = Task.query.filter_by(assigned_to=user, status='needsAction').count()
    
    # Calculate task completion rate
    if stats['total_tasks_assigned'] > 0:
        stats['task_completion_rate'] = (stats['completed_tasks'] / stats['total_tasks_assigned']) * 100
    else:
        stats['task_completion_rate'] = 0
    
    # Service job statistics (for technicians)
    if user.is_technician:
        stats['total_service_jobs'] = ServiceJob.query.filter_by(assigned_to=user).count()
        stats['completed_service_jobs'] = ServiceJob.query.filter_by(
            assigned_to=user, 
            status='completed'
        ).count()
    
    # Sales statistics (for sales users)
    if user.role in ['admin', 'manager', 'sales']:
        stats['total_sales'] = Sale.query.filter_by(sold_by=user).count()
        total_sales_amount = db.session.query(
            func.sum(Sale.total_amount)
        ).filter_by(sold_by=user).scalar() or 0
        stats['total_sales_amount'] = total_sales_amount
    
    return stats

def is_valid_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# Available technician skills
TECHNICIAN_SKILLS = [
    'phone_repair',
    'computer_repair',
    'network_setup',
    'software_installation',
    'hardware_installation',
    'data_recovery',
    'virus_removal',
    'system_optimization',
    'printer_repair',
    'tablet_repair'
]

@auth_bp.context_processor
def inject_technician_skills():
    """Inject technician skills into templates"""
    return {'technician_skills': TECHNICIAN_SKILLS}