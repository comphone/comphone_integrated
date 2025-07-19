"""
Comphone Integrated System - Complete Auth Blueprint
User authentication with all required routes
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timezone
from models import db, User, UserRole, log_activity
import re

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('กรุณากรอกชื่อผู้ใช้และรหัสผ่าน', 'error')
            return render_template('auth/login.html')
        
        # Find user
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('บัญชีผู้ใช้ถูกระงับการใช้งาน', 'error')
                return render_template('auth/login.html')
            
            # Successful login
            login_user(user, remember=bool(request.form.get('remember_me')))
            
            # Update last login
            user.last_login = datetime.now(timezone.utc)
            user.last_activity = datetime.now(timezone.utc)
            db.session.commit()
            
            flash(f'ยินดีต้อนรับ {user.full_name}', 'success')
            
            # Redirect to intended page or dashboard
            next_page = request.args.get('next')
            if not next_page:
                next_page = url_for('main.dashboard')
            
            return redirect(next_page)
        else:
            flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    flash('ออกจากระบบเรียบร้อยแล้ว', 'info')
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('auth/profile.html', user=current_user)

@auth_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Update user profile"""
    try:
        # Update basic information
        current_user.first_name = request.form.get('first_name', '').strip()
        current_user.last_name = request.form.get('last_name', '').strip()
        current_user.phone = request.form.get('phone', '').strip()
        current_user.email = request.form.get('email', '').strip()
        
        # Update preferences
        current_user.timezone = request.form.get('timezone', 'Asia/Bangkok')
        current_user.language = request.form.get('language', 'th')
        current_user.theme_preference = request.form.get('theme', 'light')
        
        # Update technician-specific information
        if current_user.is_technician:
            skills = []
            for skill in ['phone_repair', 'computer_repair', 'data_recovery', 'network_setup', 'software_install']:
                if request.form.get(f'skill_{skill}'):
                    skills.append(skill)
            current_user.set_skills(skills)
        
        current_user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        flash('อัปเดตข้อมูลส่วนตัวเรียบร้อยแล้ว', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Profile update error: {e}")
        flash('เกิดข้อผิดพลาดในการอัปเดตข้อมูล', 'error')
    
    return redirect(url_for('auth.profile'))

@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password"""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate input
        if not current_password:
            flash('กรุณาระบุรหัสผ่านปัจจุบัน', 'error')
            return render_template('auth/change_password.html')
        
        if not current_user.check_password(current_password):
            flash('รหัสผ่านปัจจุบันไม่ถูกต้อง', 'error')
            return render_template('auth/change_password.html')
        
        if not new_password or len(new_password) < 6:
            flash('รหัสผ่านใหม่ต้องมีอย่างน้อย 6 ตัวอักษร', 'error')
            return render_template('auth/change_password.html')
        
        if new_password != confirm_password:
            flash('รหัสผ่านใหม่ไม่ตรงกัน', 'error')
            return render_template('auth/change_password.html')
        
        if current_password == new_password:
            flash('รหัสผ่านใหม่ต้องแตกต่างจากรหัสผ่านเดิม', 'error')
            return render_template('auth/change_password.html')
        
        try:
            # Update password
            current_user.set_password(new_password)
            current_user.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            
            flash('เปลี่ยนรหัสผ่านเรียบร้อยแล้ว', 'success')
            return redirect(url_for('auth.profile'))
        
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Password change error: {e}")
            flash('เกิดข้อผิดพลาดในการเปลี่ยนรหัสผ่าน', 'error')
    
    return render_template('auth/change_password.html')

@auth_bp.route('/users')
@login_required
def manage_users():
    """User management (admin only)"""
    if not current_user.is_admin:
        flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'error')
        return redirect(url_for('main.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    role_filter = request.args.get('role', '')
    status_filter = request.args.get('status', '')
    
    # Build query
    query = User.query
    
    if search:
        query = query.filter(
            db.or_(
                User.username.contains(search),
                User.email.contains(search),
                User.first_name.contains(search),
                User.last_name.contains(search)
            )
        )
    
    if role_filter:
        try:
            role_enum = UserRole(role_filter)
            query = query.filter(User.role == role_enum)
        except ValueError:
            pass
    
    if status_filter == 'active':
        query = query.filter(User.is_active == True)
    elif status_filter == 'inactive':
        query = query.filter(User.is_active == False)
    
    # Get all users for now (pagination can be added later)
    users = query.order_by(User.created_at.desc()).all()
    
    return render_template('auth/manage_users.html',
                         users=users,
                         search=search,
                         role_filter=role_filter,
                         status_filter=status_filter,
                         user_roles=UserRole)

@auth_bp.route('/users/<int:user_id>/toggle_status', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    """Toggle user active status (admin only)"""
    if not current_user.is_admin:
        flash('คุณไม่มีสิทธิ์ดำเนินการนี้', 'error')
        return redirect(url_for('main.dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('ไม่สามารถเปลี่ยนสถานะตัวเองได้', 'error')
        return redirect(url_for('auth.manage_users'))
    
    try:
        old_status = user.is_active
        user.is_active = not user.is_active
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        status_text = 'เปิดใช้งาน' if user.is_active else 'ปิดใช้งาน'
        flash(f'{status_text}บัญชีผู้ใช้ {user.username} เรียบร้อยแล้ว', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Toggle user status error: {e}")
        flash('เกิดข้อผิดพลาดในการเปลี่ยนสถานะผู้ใช้', 'error')
    
    return redirect(url_for('auth.manage_users'))

@auth_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """Edit user (admin only)"""
    if not current_user.is_admin:
        flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'error')
        return redirect(url_for('main.dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        try:
            # Update user information
            username = request.form.get('username', '').strip().lower()
            email = request.form.get('email', '').strip().lower()
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            phone = request.form.get('phone', '').strip()
            role = request.form.get('role', 'support')
            department = request.form.get('department', '').strip()
            
            # Validate input
            errors = []
            
            if not username or len(username) < 3:
                errors.append('ชื่อผู้ใช้ต้องมีอย่างน้อย 3 ตัวอักษร')
            
            if username != user.username and User.query.filter_by(username=username).first():
                errors.append('ชื่อผู้ใช้นี้ถูกใช้งานแล้ว')
            
            if not email or not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
                errors.append('อีเมลไม่ถูกต้อง')
            
            if email != user.email and User.query.filter_by(email=email).first():
                errors.append('อีเมลนี้ถูกใช้งานแล้ว')
            
            if not first_name:
                errors.append('กรุณาระบุชื่อ')
            
            if not last_name:
                errors.append('กรุณาระบุนามสกุล')
            
            try:
                user_role = UserRole(role)
            except ValueError:
                errors.append('บทบาทผู้ใช้ไม่ถูกต้อง')
                user_role = user.role
            
            if errors:
                for error in errors:
                    flash(error, 'error')
                return render_template('auth/edit_user.html', user=user, user_roles=UserRole)
            
            # Update user fields
            user.username = username
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.phone = phone
            user.role = user_role
            user.is_technician = (user_role == UserRole.TECHNICIAN)
            user.updated_at = datetime.now(timezone.utc)
            
            # Update password if provided
            new_password = request.form.get('new_password', '').strip()
            if new_password:
                if len(new_password) < 6:
                    flash('รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร', 'error')
                    return render_template('auth/edit_user.html', user=user, user_roles=UserRole)
                user.set_password(new_password)
            
            db.session.commit()
            
            flash(f'อัปเดตข้อมูลผู้ใช้ {user.username} เรียบร้อยแล้ว', 'success')
            return redirect(url_for('auth.manage_users'))
        
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Edit user error: {e}")
            flash('เกิดข้อผิดพลาดในการอัปเดตข้อมูลผู้ใช้', 'error')
    
    return render_template('auth/edit_user.html', user=user, user_roles=UserRole)

@auth_bp.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    """User registration (admin only)"""
    if not current_user.is_admin:
        flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username', '').strip().lower()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone = request.form.get('phone', '').strip()
        role = request.form.get('role', 'support')
        department = request.form.get('department', '').strip()
        
        # Validate input
        errors = []
        
        if not username or len(username) < 3:
            errors.append('ชื่อผู้ใช้ต้องมีอย่างน้อย 3 ตัวอักษร')
        
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            errors.append('ชื่อผู้ใช้ใช้ได้เฉพาะตัวอักษร ตัวเลข และ _')
        
        if User.query.filter_by(username=username).first():
            errors.append('ชื่อผู้ใช้นี้ถูกใช้งานแล้ว')
        
        if not email or not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            errors.append('อีเมลไม่ถูกต้อง')
        
        if User.query.filter_by(email=email).first():
            errors.append('อีเมลนี้ถูกใช้งานแล้ว')
        
        if not password or len(password) < 6:
            errors.append('รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร')
        
        if password != confirm_password:
            errors.append('รหัสผ่านไม่ตรงกัน')
        
        if not first_name:
            errors.append('กรุณาระบุชื่อ')
        
        if not last_name:
            errors.append('กรุณาระบุนามสกุล')
        
        try:
            user_role = UserRole(role)
        except ValueError:
            errors.append('บทบาทผู้ใช้ไม่ถูกต้อง')
            user_role = UserRole.SUPPORT
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register.html', user_roles=UserRole)
        
        try:
            # Create new user
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                role=user_role,
                is_technician=(user_role == UserRole.TECHNICIAN)
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            flash(f'สร้างบัญชีผู้ใช้ {username} เรียบร้อยแล้ว', 'success')
            return redirect(url_for('auth.manage_users'))
        
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"User registration error: {e}")
            flash('เกิดข้อผิดพลาดในการสร้างบัญชีผู้ใช้', 'error')
    
    return render_template('auth/register.html', user_roles=UserRole)

@auth_bp.route('/sessions')
@login_required
def active_sessions():
    """View active sessions"""
    session_info = {
        'current_session': {
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent'),
            'login_time': current_user.last_login,
            'last_activity': current_user.last_activity
        }
    }
    
    return render_template('auth/sessions.html', session_info=session_info)

# Helper functions
def get_user_stats(user):
    """Get user statistics"""
    if not user:
        return {}
    
    stats = {
        'total_tasks_created': 0,
        'total_tasks_assigned': 0,
        'completed_tasks': 0,
        'pending_tasks': 0
    }
    
    return stats

# Template context processor
@auth_bp.app_context_processor
def inject_auth_vars():
    """Inject authentication-related variables into templates"""
    return {
        'UserRole': UserRole,
        'get_user_stats': get_user_stats
    }
