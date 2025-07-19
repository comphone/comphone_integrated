from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from models import db, Task, Customer, ServiceJob, Product, Sale, Notification, User
from sqlalchemy import func, desc
import logging

main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

@main_bp.route('/')
def index():
    """Redirect to dashboard if logged in, otherwise to login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard with statistics and recent activities"""
    try:
        # Get basic statistics
        stats = {}
        
        # Task statistics
        stats['total_tasks'] = Task.query.count()
        stats['pending_tasks'] = Task.query.filter_by(status='pending').count()
        
        # Service job statistics
        stats['total_service_jobs'] = ServiceJob.query.count()
        stats['active_jobs'] = ServiceJob.query.filter_by(status='in_progress').count()
        
        # Customer statistics
        stats['total_customers'] = Customer.query.count()
        today = datetime.utcnow().date()
        first_day_of_month = today.replace(day=1)
        stats['new_customers'] = Customer.query.filter(
            func.date(Customer.created_at) >= first_day_of_month
        ).count()
        
        # Sales statistics
        today_sales = db.session.query(func.sum(Sale.total_amount)).filter(
            func.date(Sale.created_at) == today
        ).scalar()
        stats['today_sales'] = today_sales or 0
        
        stats['today_transactions'] = Sale.query.filter(
            func.date(Sale.created_at) == today
        ).count()
        
        # Low stock items
        stats['low_stock_items'] = Product.query.filter(
            Product.stock_quantity <= Product.min_stock_level
        ).count()
        
        # Get recent activities (using service jobs as activities for now)
        recent_activities = ServiceJob.query.order_by(desc(ServiceJob.created_at)).limit(5).all()
        
        # Get user's assigned tasks
        my_tasks = Task.query.filter_by(assigned_to=current_user.id).filter(
            Task.status.in_(['pending', 'in_progress'])
        ).order_by(desc(Task.created_at)).limit(5).all()
        
        # Get recent jobs
        recent_jobs = ServiceJob.query.order_by(desc(ServiceJob.created_at)).limit(5).all()
        
        # Get notifications
        try:
            notifications = Notification.query.filter_by(
                user_id=current_user.id, 
                read=False
            ).order_by(desc(Notification.created_at)).limit(5).all()
        except Exception as e:
            logger.error(f"Error getting notifications: {e}")
            notifications = []
        
        return render_template('main/dashboard.html',
                             stats=stats,
                             recent_activities=recent_activities,
                             my_tasks=my_tasks,
                             recent_jobs=recent_jobs,
                             notifications=notifications)
                             
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        flash('เกิดข้อผิดพลาดในการโหลดข้อมูล Dashboard', 'error')
        return render_template('main/dashboard.html',
                             stats={},
                             recent_activities=[],
                             my_tasks=[],
                             recent_jobs=[],
                             notifications=[])

@main_bp.route('/search')
@login_required
def search():
    """Global search functionality"""
    query = request.args.get('q', '').strip()
    results = {'customers': [], 'jobs': [], 'tasks': [], 'products': []}
    
    if query and len(query) >= 2:
        # Search customers
        customers = Customer.query.filter(
            db.or_(
                Customer.first_name.ilike(f'%{query}%'),
                Customer.last_name.ilike(f'%{query}%'),
                Customer.email.ilike(f'%{query}%'),
                Customer.phone.ilike(f'%{query}%')
            )
        ).limit(10).all()
        results['customers'] = customers
        
        # Search service jobs
        jobs = ServiceJob.query.filter(
            db.or_(
                ServiceJob.title.ilike(f'%{query}%'),
                ServiceJob.description.ilike(f'%{query}%')
            )
        ).limit(10).all()
        results['jobs'] = jobs
        
        # Search tasks
        tasks = Task.query.filter(
            db.or_(
                Task.title.ilike(f'%{query}%'),
                Task.description.ilike(f'%{query}%')
            )
        ).limit(10).all()
        results['tasks'] = tasks
        
        # Search products
        products = Product.query.filter(
            db.or_(
                Product.name.ilike(f'%{query}%'),
                Product.description.ilike(f'%{query}%'),
                Product.sku.ilike(f'%{query}%')
            )
        ).limit(10).all()
        results['products'] = products
    
    return render_template('main/search_results.html', 
                         query=query, 
                         results=results)

@main_bp.route('/notifications')
@login_required
def notifications():
    """Show all notifications for current user"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        notifications = Notification.query.filter_by(user_id=current_user.id).order_by(
            desc(Notification.created_at)
        ).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        # Mark notifications as read when viewed
        unread_notifications = Notification.query.filter_by(
            user_id=current_user.id, 
            read=False
        ).all()
        
        for notification in unread_notifications:
            notification.read = True
        
        db.session.commit()
        
        return render_template('main/notifications.html', notifications=notifications)
        
    except Exception as e:
        logger.error(f"Error loading notifications: {e}")
        flash('เกิดข้อผิดพลาดในการโหลดการแจ้งเตือน', 'error')
        return render_template('main/notifications.html', notifications=None)

@main_bp.route('/settings')
@login_required
def settings():
    """System settings page"""
    return render_template('main/settings.html')

@main_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('main/profile.html', user=current_user)

@main_bp.route('/reports')
@login_required
def reports():
    """Reports and analytics page"""
    # Get date range from query parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Default to current month if no dates provided
    if not start_date or not end_date:
        today = datetime.utcnow().date()
        start_date = today.replace(day=1)
        end_date = today
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Generate reports data
    report_data = {
        'date_range': {'start': start_date, 'end': end_date},
        'sales': generate_sales_report(start_date, end_date),
        'service_jobs': generate_service_jobs_report(start_date, end_date),
        'customers': generate_customers_report(start_date, end_date),
        'inventory': generate_inventory_report()
    }
    
    return render_template('main/reports.html', data=report_data)

@main_bp.route('/activity_log')
@login_required
def activity_log():
    """Show system activity log"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # For now, use service jobs as activity log
    # In a real system, you'd have a dedicated ActivityLog model
    activities = ServiceJob.query.order_by(desc(ServiceJob.created_at)).paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    return render_template('main/activity_log.html', activities=activities)

# API Routes
@main_bp.route('/api/dashboard_stats')
@login_required
def api_dashboard_stats():
    """API endpoint for dashboard statistics"""
    try:
        stats = {}
        
        # Task statistics
        stats['total_tasks'] = Task.query.count()
        stats['pending_tasks'] = Task.query.filter_by(status='pending').count()
        stats['completed_tasks'] = Task.query.filter_by(status='completed').count()
        
        # Service job statistics
        stats['total_service_jobs'] = ServiceJob.query.count()
        stats['active_jobs'] = ServiceJob.query.filter_by(status='in_progress').count()
        stats['completed_jobs'] = ServiceJob.query.filter_by(status='completed').count()
        
        # Customer statistics
        stats['total_customers'] = Customer.query.count()
        
        # Sales statistics
        today = datetime.utcnow().date()
        today_sales = db.session.query(func.sum(Sale.total_amount)).filter(
            func.date(Sale.created_at) == today
        ).scalar()
        stats['today_sales'] = float(today_sales or 0)
        
        stats['today_transactions'] = Sale.query.filter(
            func.date(Sale.created_at) == today
        ).count()
        
        # Inventory statistics
        stats['total_products'] = Product.query.count()
        stats['low_stock_items'] = Product.query.filter(
            Product.stock_quantity <= Product.min_stock_level
        ).count()
        
        return jsonify({
            'status': 'success',
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"API dashboard stats error: {e}")
        return jsonify({
            'status': 'error',
            'message': 'เกิดข้อผิดพลาดในการดึงข้อมูลสถิติ'
        }), 500

@main_bp.route('/api/quick_add_task', methods=['POST'])
@login_required
def api_quick_add_task():
    """API endpoint for quick task creation"""
    try:
        data = request.get_json()
        
        if not data or not data.get('title'):
            return jsonify({
                'status': 'error',
                'message': 'กรุณาระบุชื่องาน'
            }), 400
        
        # Create new task
        task = Task(
            title=data['title'],
            description=data.get('description', ''),
            priority=data.get('priority', 'medium'),
            assigned_to=current_user.id,
            created_by=current_user.id
        )
        
        # Set due date if provided
        if data.get('due_date'):
            try:
                task.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d')
            except ValueError:
                pass
        
        db.session.add(task)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'สร้างงานเรียบร้อยแล้ว',
            'task_id': task.id
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"API quick add task error: {e}")
        return jsonify({
            'status': 'error',
            'message': 'เกิดข้อผิดพลาดในการสร้างงาน'
        }), 500

@main_bp.route('/api/notifications')
@login_required
def api_notifications():
    """API endpoint for notifications"""
    try:
        notifications = Notification.query.filter_by(
            user_id=current_user.id, 
            read=False
        ).order_by(desc(Notification.created_at)).limit(10).all()
        
        notifications_data = []
        for notification in notifications:
            notifications_data.append({
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'type': notification.type,
                'created_at': notification.created_at.isoformat()
            })
        
        return jsonify({
            'status': 'success',
            'data': notifications_data,
            'count': len(notifications_data)
        })
        
    except Exception as e:
        logger.error(f"API notifications error: {e}")
        return jsonify({
            'status': 'error',
            'message': 'เกิดข้อผิดพลาดในการดึงข้อมูลการแจ้งเตือน'
        }), 500

# Helper functions for reports
def generate_sales_report(start_date, end_date):
    """Generate sales report for date range"""
    sales = Sale.query.filter(
        func.date(Sale.created_at) >= start_date,
        func.date(Sale.created_at) <= end_date
    ).all()
    
    total_sales = sum(sale.total_amount for sale in sales)
    total_transactions = len(sales)
    
    return {
        'total_sales': total_sales,
        'total_transactions': total_transactions,
        'average_transaction': total_sales / total_transactions if total_transactions > 0 else 0,
        'sales': sales
    }

def generate_service_jobs_report(start_date, end_date):
    """Generate service jobs report for date range"""
    jobs = ServiceJob.query.filter(
        func.date(ServiceJob.created_at) >= start_date,
        func.date(ServiceJob.created_at) <= end_date
    ).all()
    
    completed_jobs = [job for job in jobs if job.status == 'completed']
    pending_jobs = [job for job in jobs if job.status == 'pending']
    in_progress_jobs = [job for job in jobs if job.status == 'in_progress']
    
    return {
        'total_jobs': len(jobs),
        'completed_jobs': len(completed_jobs),
        'pending_jobs': len(pending_jobs),
        'in_progress_jobs': len(in_progress_jobs),
        'jobs': jobs
    }

def generate_customers_report(start_date, end_date):
    """Generate customers report for date range"""
    new_customers = Customer.query.filter(
        func.date(Customer.created_at) >= start_date,
        func.date(Customer.created_at) <= end_date
    ).all()
    
    total_customers = Customer.query.count()
    
    return {
        'new_customers': len(new_customers),
        'total_customers': total_customers,
        'customers': new_customers
    }

def generate_inventory_report():
    """Generate inventory report"""
    products = Product.query.all()
    low_stock_products = Product.query.filter(
        Product.stock_quantity <= Product.min_stock_level
    ).all()
    
    total_value = sum(product.stock_quantity * product.cost for product in products if product.cost)
    
    return {
        'total_products': len(products),
        'low_stock_count': len(low_stock_products),
        'total_inventory_value': total_value,
        'low_stock_products': low_stock_products
    }