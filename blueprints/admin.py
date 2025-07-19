#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Admin Blueprint - System Administration Panel
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timezone, timedelta
from models import (
    db, User, Customer, Task, ServiceJob, Product, Sale, SystemSettings,
    ActivityLog, UserRole, log_activity, get_setting, set_setting
)
from sqlalchemy import func, or_, and_

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    """Decorator to require admin role"""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'error')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    """Admin dashboard"""
    # System statistics
    stats = {
        'users': {
            'total': User.query.count(),
            'active': User.query.filter_by(is_active=True).count(),
            'admins': User.query.filter_by(role=UserRole.ADMIN).count(),
            'technicians': User.query.filter_by(role=UserRole.TECHNICIAN).count(),
            'sales': User.query.filter_by(role=UserRole.SALES).count()
        },
        'customers': {
            'total': Customer.query.count(),
            'active': Customer.query.filter_by(status='active').count(),
            'new_this_month': Customer.query.filter(
                Customer.created_at >= datetime.now().replace(day=1)
            ).count()
        },
        'tasks': {
            'total': Task.query.count(),
            'pending': Task.query.filter_by(status='pending').count(),
            'completed': Task.query.filter_by(status='completed').count()
        },
        'service_jobs': {
            'total': ServiceJob.query.count(),
            'active': ServiceJob.query.filter(
                ServiceJob.status.in_(['received', 'in_repair'])
            ).count(),
            'completed': ServiceJob.query.filter_by(status='completed').count()
        },
        'products': {
            'total': Product.query.count(),
            'active': Product.query.filter_by(is_active=True).count(),
            'low_stock': Product.query.filter(
                Product.stock_quantity <= Product.min_stock_level
            ).count()
        },
        'sales': {
            'total': Sale.query.count(),
            'today': Sale.query.filter(
                func.date(Sale.created_at) == datetime.now().date()
            ).count(),
            'total_revenue': db.session.query(func.sum(Sale.total_amount)).scalar() or 0
        }
    }
    
    # Recent activities
    recent_activities = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(10).all()
    
    # System health
    system_health = {
        'database_connected': True,
        'line_bot_configured': bool(current_app.config.get('LINE_CHANNEL_ACCESS_TOKEN')),
        'email_configured': bool(current_app.config.get('MAIL_USERNAME')),
        'google_api_configured': bool(current_app.config.get('GOOGLE_CLIENT_ID'))
    }
    
    return render_template('admin/dashboard.html',
                         stats=stats,
                         recent_activities=recent_activities,
                         system_health=system_health)

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """User management"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    role_filter = request.args.get('role', '')
    status_filter = request.args.get('status', '')
    
    # Build query
    query = User.query
    
    if search:
        query = query.filter(
            or_(
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
    
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/users.html',
                         users=users,
                         search=search,
                         role_filter=role_filter,
                         status_filter=status_filter,
                         user_roles=UserRole)

@admin_bp.route('/settings')
@login_required
@admin_required
def settings():
    """System settings"""
    settings = SystemSettings.query.order_by(SystemSettings.category, SystemSettings.key).all()
    
    # Group by category
    settings_by_category = {}
    for setting in settings:
        category = setting.category or 'general'
        if category not in settings_by_category:
            settings_by_category[category] = []
        settings_by_category[category].append(setting)
    
    return render_template('admin/settings.html',
                         settings_by_category=settings_by_category)

@admin_bp.route('/settings/update', methods=['POST'])
@login_required
@admin_required
def update_settings():
    """Update system settings"""
    try:
        updated_count = 0
        
        for key, value in request.form.items():
            if key.startswith('setting_'):
                setting_key = key[8:]  # Remove 'setting_' prefix
                
                # Get or create setting
                setting = SystemSettings.query.filter_by(key=setting_key).first()
                if setting:
                    old_value = setting.value
                    setting.value = value
                    setting.updated_by = current_user.id
                    setting.updated_at = datetime.now(timezone.utc)
                    
                    if old_value != value:
                        updated_count += 1
                        
                        # Log the change
                        log_activity(
                            action='setting_updated',
                            entity_type='system_settings',
                            entity_id=setting.id,
                            user_id=current_user.id,
                            description=f"Setting {setting_key} changed from '{old_value}' to '{value}'"
                        )
        
        db.session.commit()
        flash(f'อัพเดตการตั้งค่า {updated_count} รายการเรียบร้อยแล้ว', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update settings error: {e}")
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
    
    return redirect(url_for('admin.settings'))

@admin_bp.route('/activity_log')
@login_required
@admin_required
def activity_log():
    """Activity log viewer"""
    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', '')
    user_filter = request.args.get('user', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Build query
    query = ActivityLog.query
    
    if action_filter:
        query = query.filter(ActivityLog.action.contains(action_filter))
    
    if user_filter:
        query = query.filter(ActivityLog.user_id == user_filter)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(ActivityLog.created_at >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(ActivityLog.created_at < date_to_obj)
        except ValueError:
            pass
    
    activities = query.order_by(ActivityLog.created_at.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    
    # Get users for filter
    users = User.query.filter_by(is_active=True).order_by(User.username).all()
    
    return render_template('admin/activity_log.html',
                         activities=activities,
                         users=users,
                         action_filter=action_filter,
                         user_filter=user_filter,
                         date_from=date_from,
                         date_to=date_to)

@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    """System reports"""
    # Date range
    date_from = request.args.get('date_from', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.args.get('date_to', datetime.now().strftime('%Y-%m-%d'))
    
    # Users by role
    users_by_role = db.session.query(
        User.role,
        func.count(User.id).label('count')
    ).group_by(User.role).all()
    
    # Tasks by status
    tasks_by_status = db.session.query(
        Task.status,
        func.count(Task.id).label('count')
    ).group_by(Task.status).all()
    
    # Sales by day
    sales_by_day = db.session.query(
        func.date(Sale.created_at).label('date'),
        func.count(Sale.id).label('count'),
        func.sum(Sale.total_amount).label('total')
    ).filter(
        Sale.created_at >= date_from,
        Sale.created_at <= date_to
    ).group_by(func.date(Sale.created_at)).all()
    
    # Top products
    top_products = db.session.query(
        Product.name,
        func.sum(SaleItem.quantity).label('total_quantity'),
        func.sum(SaleItem.total_price).label('total_revenue')
    ).join(
        SaleItem, Product.id == SaleItem.product_id
    ).join(
        Sale, SaleItem.sale_id == Sale.id
    ).filter(
        Sale.created_at >= date_from,
        Sale.created_at <= date_to
    ).group_by(
        Product.id, Product.name
    ).order_by(
        func.sum(SaleItem.quantity).desc()
    ).limit(10).all()
    
    return render_template('admin/reports.html',
                         users_by_role=users_by_role,
                         tasks_by_status=tasks_by_status,
                         sales_by_day=sales_by_day,
                         top_products=top_products,
                         date_from=date_from,
                         date_to=date_to)

@admin_bp.route('/system_info')
@login_required
@admin_required
def system_info():
    """System information"""
    import sys
    import platform
    
    system_info = {
        'python_version': sys.version,
        'platform': platform.platform(),
        'flask_env': current_app.config.get('FLASK_ENV', 'development'),
        'debug_mode': current_app.debug,
        'database_uri': current_app.config.get('SQLALCHEMY_DATABASE_URI', '').split('://')[0] + '://***',
        'secret_key_set': bool(current_app.config.get('SECRET_KEY')),
        'line_bot_configured': bool(current_app.config.get('LINE_CHANNEL_ACCESS_TOKEN')),
        'email_configured': bool(current_app.config.get('MAIL_USERNAME')),
        'google_api_configured': bool(current_app.config.get('GOOGLE_CLIENT_ID'))
    }
    
    # Database statistics
    db_stats = {
        'users': User.query.count(),
        'customers': Customer.query.count(),
        'tasks': Task.query.count(),
        'service_jobs': ServiceJob.query.count(),
        'products': Product.query.count(),
        'sales': Sale.query.count(),
        'activity_logs': ActivityLog.query.count()
    }
    
    return render_template('admin/system_info.html',
                         system_info=system_info,
                         db_stats=db_stats)

@admin_bp.route('/backup')
@login_required
@admin_required
def backup():
    """Database backup"""
    return render_template('admin/backup.html')

@admin_bp.route('/api/backup/create', methods=['POST'])
@login_required
@admin_required
def create_backup():
    """Create database backup"""
    try:
        import shutil
        import os
        from datetime import datetime
        
        # Create backup filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"comphone_backup_{timestamp}.db"
        backup_path = os.path.join(current_app.config.get('BACKUP_LOCATION', 'backups'), backup_filename)
        
        # Ensure backup directory exists
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        # Copy database file
        db_path = current_app.config.get('SQLALCHEMY_DATABASE_URI').replace('sqlite:///', '')
        shutil.copy2(db_path, backup_path)
        
        # Log activity
        log_activity(
            action='backup_created',
            user_id=current_user.id,
            description=f"Database backup created: {backup_filename}"
        )
        
        return jsonify({
            'success': True,
            'message': f'สำรองข้อมูลสำเร็จ: {backup_filename}',
            'backup_file': backup_filename
        })
        
    except Exception as e:
        current_app.logger.error(f"Backup error: {e}")
        return jsonify({
            'success': False,
            'message': f'เกิดข้อผิดพลาด: {str(e)}'
        }), 500

@admin_bp.route('/api/system/stats')
@login_required
@admin_required
def api_system_stats():
    """API for system statistics"""
    stats = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'total_customers': Customer.query.count(),
        'active_customers': Customer.query.filter_by(status='active').count(),
        'total_tasks': Task.query.count(),
        'pending_tasks': Task.query.filter_by(status='pending').count(),
        'total_service_jobs': ServiceJob.query.count(),
        'active_service_jobs': ServiceJob.query.filter(
            ServiceJob.status.in_(['received', 'in_repair'])
        ).count(),
        'total_products': Product.query.count(),
        'low_stock_products': Product.query.filter(
            Product.stock_quantity <= Product.min_stock_level
        ).count(),
        'total_sales': Sale.query.count(),
        'today_sales': Sale.query.filter(
            func.date(Sale.created_at) == datetime.now().date()
        ).count(),
        'total_revenue': db.session.query(func.sum(Sale.total_amount)).scalar() or 0
    }
    
    return jsonify(stats)

# Context processor
@admin_bp.app_context_processor
def inject_admin_vars():
    """Inject admin-related variables into templates"""
    return {
        'UserRole': UserRole,
        'admin_menu_items': [
            {'name': 'Dashboard', 'url': 'admin.dashboard', 'icon': 'fas fa-tachometer-alt'},
            {'name': 'Users', 'url': 'admin.users', 'icon': 'fas fa-users'},
            {'name': 'Settings', 'url': 'admin.settings', 'icon': 'fas fa-cog'},
            {'name': 'Activity Log', 'url': 'admin.activity_log', 'icon': 'fas fa-history'},
            {'name': 'Reports', 'url': 'admin.reports', 'icon': 'fas fa-chart-bar'},
            {'name': 'System Info', 'url': 'admin.system_info', 'icon': 'fas fa-info-circle'},
            {'name': 'Backup', 'url': 'admin.backup', 'icon': 'fas fa-database'}
        ]
    }