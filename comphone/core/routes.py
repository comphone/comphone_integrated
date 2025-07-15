# comphone/core/routes.py - Fixed Version (แก้ปัญหา endpoint conflicts)

from flask import render_template, jsonify, current_app
from flask_login import login_required, current_user
from comphone.core import bp
from comphone.models import Task, Customer, Product, Sale, User
from comphone import db
import sqlalchemy as sa
from datetime import datetime, timezone, timedelta

@bp.route('/')
@bp.route('/index')
@login_required
def index():
    """Main dashboard page"""
    try:
        # Get dashboard statistics
        stats = get_dashboard_stats()
        
        # Get recent tasks (last 5)
        recent_tasks = get_recent_tasks(limit=5)
        
        # Get recent activities
        recent_activities = get_recent_activities(limit=10)
        
        return render_template(
            'core/dashboard.html', 
            stats=stats, 
            recent_tasks=recent_tasks,
            recent_activities=recent_activities
        )
        
    except Exception as e:
        # Handle any database errors gracefully
        current_app.logger.error(f"Dashboard error: {e}")
        
        # Return minimal dashboard with default values
        stats = {
            'total_tasks': 0, 
            'pending_tasks': 0, 
            'total_customers': 0, 
            'total_products': 0,
            'completed_today': 0,
            'overdue_tasks': 0
        }
        recent_tasks = []
        recent_activities = []
        
        return render_template(
            'core/dashboard.html', 
            stats=stats, 
            recent_tasks=recent_tasks,
            recent_activities=recent_activities
        )

def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        # Basic counts
        total_tasks = db.session.scalar(sa.select(sa.func.count(Task.id))) or 0
        pending_tasks = db.session.scalar(
            sa.select(sa.func.count(Task.id)).where(Task.status == 'needsAction')
        ) or 0
        total_customers = db.session.scalar(sa.select(sa.func.count(Customer.id))) or 0
        total_products = db.session.scalar(sa.select(sa.func.count(Product.id))) or 0
        
        # Today's completed tasks
        today = datetime.now(timezone.utc).date()
        completed_today = db.session.scalar(
            sa.select(sa.func.count(Task.id)).where(
                (Task.status == 'completed') & 
                (sa.func.date(Task.completed_at) == today)
            )
        ) or 0
        
        # Overdue tasks
        now = datetime.now(timezone.utc)
        overdue_tasks = db.session.scalar(
            sa.select(sa.func.count(Task.id)).where(
                (Task.status == 'needsAction') & 
                (Task.due_date < now)
            )
        ) or 0
        
        return {
            'total_tasks': total_tasks,
            'pending_tasks': pending_tasks,
            'total_customers': total_customers,
            'total_products': total_products,
            'completed_today': completed_today,
            'overdue_tasks': overdue_tasks
        }
        
    except Exception as e:
        current_app.logger.error(f"Error getting dashboard stats: {e}")
        return {
            'total_tasks': 0, 'pending_tasks': 0, 'total_customers': 0, 
            'total_products': 0, 'completed_today': 0, 'overdue_tasks': 0
        }

def get_recent_tasks(limit=5):
    """Get recent tasks"""
    try:
        return db.session.scalars(
            sa.select(Task)
            .order_by(Task.created_at.desc())
            .limit(limit)
        ).all()
    except Exception as e:
        current_app.logger.error(f"Error getting recent tasks: {e}")
        return []

def get_recent_activities(limit=10):
    """Get recent activities (tasks created, completed, etc.)"""
    try:
        activities = []
        
        # Recent completed tasks
        completed_tasks = db.session.scalars(
            sa.select(Task)
            .where(Task.status == 'completed')
            .order_by(Task.completed_at.desc())
            .limit(limit // 2)
        ).all()
        
        for task in completed_tasks:
            activities.append({
                'type': 'task_completed',
                'title': f'งาน "{task.title}" เสร็จสิ้น',
                'timestamp': task.completed_at,
                'icon': 'check-circle',
                'color': 'success'
            })
        
        # Recent created tasks
        new_tasks = db.session.scalars(
            sa.select(Task)
            .order_by(Task.created_at.desc())
            .limit(limit // 2)
        ).all()
        
        for task in new_tasks:
            activities.append({
                'type': 'task_created',
                'title': f'สร้างงานใหม่ "{task.title}"',
                'timestamp': task.created_at,
                'icon': 'plus-circle',
                'color': 'primary'
            })
        
        # Sort by timestamp
        activities.sort(key=lambda x: x['timestamp'] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        
        return activities[:limit]
        
    except Exception as e:
        current_app.logger.error(f"Error getting recent activities: {e}")
        return []

@bp.route('/health')
def health_check():
    """System health check endpoint"""
    try:
        # Test database connection
        db.session.scalar(sa.select(sa.func.count(User.id)))
        
        return jsonify({
            'status': 'healthy',
            'message': 'Comphone system is running',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'database': 'connected'
        })
        
    except Exception as e:
        current_app.logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'message': 'Database connection failed',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': str(e)
        }), 503

@bp.route('/api/stats')
@login_required
def api_stats():
    """API endpoint for dashboard statistics"""
    try:
        stats = get_dashboard_stats()
        return jsonify({
            'status': 'success',
            'data': stats
        })
    except Exception as e:
        current_app.logger.error(f"API stats error: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to get statistics'
        }), 500

@bp.route('/about')
def about():
    """About page"""
    return render_template('core/about.html')

@bp.route('/contact')
def contact():
    """Contact page"""
    return render_template('core/contact.html')

@bp.route('/help')
@login_required
def help_page():
    """Help page"""
    return render_template('core/help.html')

# Error handlers สำหรับ blueprint นี้
@bp.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors for this blueprint"""
    return render_template('core/404.html'), 404

@bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors for this blueprint"""
    db.session.rollback()
    return render_template('core/500.html'), 500