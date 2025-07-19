#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Blueprint - Complete REST API Endpoints
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timezone, timedelta
from models import (
    db, User, Customer, Task, ServiceJob, Product, Sale, SaleItem,
    TaskStatus, TaskPriority, ServiceJobStatus, PaymentStatus, UserRole,
    log_activity, get_setting
)
from sqlalchemy import func, or_, and_
from werkzeug.security import generate_password_hash

api_bp = Blueprint('api', __name__)

# ===== Dashboard API =====
@api_bp.route('/dashboard/stats')
@login_required
def api_dashboard_stats():
    """Get dashboard statistics"""
    try:
        # Basic stats
        stats = {
            'users': {
                'total': User.query.count(),
                'active': User.query.filter_by(is_active=True).count(),
                'technicians': User.query.filter_by(is_technician=True).count()
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
                'pending': Task.query.filter_by(status=TaskStatus.PENDING).count(),
                'in_progress': Task.query.filter_by(status=TaskStatus.IN_PROGRESS).count(),
                'completed': Task.query.filter_by(status=TaskStatus.COMPLETED).count(),
                'overdue': Task.query.filter(
                    Task.due_date < datetime.now(timezone.utc),
                    Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS])
                ).count()
            },
            'service_jobs': {
                'total': ServiceJob.query.count(),
                'received': ServiceJob.query.filter_by(status=ServiceJobStatus.RECEIVED).count(),
                'in_repair': ServiceJob.query.filter_by(status=ServiceJobStatus.IN_REPAIR).count(),
                'completed': ServiceJob.query.filter_by(status=ServiceJobStatus.COMPLETED).count(),
                'overdue': ServiceJob.query.filter(
                    ServiceJob.promised_date < datetime.now(timezone.utc),
                    ServiceJob.status.in_([ServiceJobStatus.RECEIVED, ServiceJobStatus.IN_REPAIR])
                ).count()
            },
            'sales': {
                'total': Sale.query.count(),
                'today': Sale.query.filter(
                    func.date(Sale.created_at) == datetime.now().date()
                ).count(),
                'this_month': Sale.query.filter(
                    Sale.created_at >= datetime.now().replace(day=1)
                ).count(),
                'total_revenue': db.session.query(func.sum(Sale.total_amount)).scalar() or 0
            },
            'products': {
                'total': Product.query.count(),
                'active': Product.query.filter_by(is_active=True).count(),
                'low_stock': Product.query.filter(
                    Product.stock_quantity <= Product.min_stock_level
                ).count(),
                'out_of_stock': Product.query.filter_by(stock_quantity=0).count()
            }
        }
        
        # Role-based filtering
        if current_user.role == UserRole.TECHNICIAN:
            stats['my_tasks'] = Task.query.filter(
                Task.assignees.any(User.id == current_user.id)
            ).count()
            stats['my_service_jobs'] = ServiceJob.query.filter_by(
                assigned_technician=current_user.id
            ).count()
        
        return jsonify(stats)
    except Exception as e:
        current_app.logger.error(f"Dashboard stats error: {e}")
        return jsonify({'error': 'Unable to fetch statistics'}), 500

@api_bp.route('/dashboard/charts')
@login_required
def api_dashboard_charts():
    """Get chart data for dashboard"""
    try:
        # Last 7 days data
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=6)
        
        # Tasks by day
        tasks_by_day = db.session.query(
            func.date(Task.created_at).label('date'),
            func.count(Task.id).label('count')
        ).filter(
            Task.created_at >= start_date
        ).group_by(func.date(Task.created_at)).all()
        
        # Service jobs by day
        jobs_by_day = db.session.query(
            func.date(ServiceJob.created_at).label('date'),
            func.count(ServiceJob.id).label('count')
        ).filter(
            ServiceJob.created_at >= start_date
        ).group_by(func.date(ServiceJob.created_at)).all()
        
        # Sales by day
        sales_by_day = db.session.query(
            func.date(Sale.created_at).label('date'),
            func.sum(Sale.total_amount).label('total')
        ).filter(
            Sale.created_at >= start_date
        ).group_by(func.date(Sale.created_at)).all()
        
        # Tasks by status
        tasks_by_status = db.session.query(
            Task.status,
            func.count(Task.id).label('count')
        ).group_by(Task.status).all()
        
        # Service jobs by status
        jobs_by_status = db.session.query(
            ServiceJob.status,
            func.count(ServiceJob.id).label('count')
        ).group_by(ServiceJob.status).all()
        
        return jsonify({
            'tasks_by_day': [{'date': str(item.date), 'count': item.count} for item in tasks_by_day],
            'jobs_by_day': [{'date': str(item.date), 'count': item.count} for item in jobs_by_day],
            'sales_by_day': [{'date': str(item.date), 'total': float(item.total or 0)} for item in sales_by_day],
            'tasks_by_status': [{'status': item.status.value, 'count': item.count} for item in tasks_by_status],
            'jobs_by_status': [{'status': item.status.value, 'count': item.count} for item in jobs_by_status]
        })
    except Exception as e:
        current_app.logger.error(f"Dashboard charts error: {e}")
        return jsonify({'error': 'Unable to fetch chart data'}), 500

# ===== Task API =====
@api_bp.route('/tasks/quick_add', methods=['POST'])
@login_required
def api_quick_add_task():
    """Quick add task API endpoint"""
    try:
        data = request.get_json()
        if not data or not data.get('title'):
            return jsonify({'error': 'Title is required'}), 400
        
        # Create task
        task = Task(
            title=data['title'],
            description=data.get('description', ''),
            priority=TaskPriority(data.get('priority', 'medium')),
            created_by=current_user.id,
            customer_id=data.get('customer_id'),
            service_job_id=data.get('service_job_id')
        )
        
        # Handle due date
        if data.get('due_date'):
            task.due_date = datetime.fromisoformat(data['due_date'])
        
        # Generate task number
        task.generate_task_number()
        
        db.session.add(task)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'task_id': task.id,
            'task_number': task.task_number,
            'message': 'Task created successfully'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Quick add task error: {e}")
        return jsonify({'error': 'Failed to create task'}), 500

@api_bp.route('/tasks/<int:task_id>/toggle_status', methods=['POST'])
@login_required
def api_toggle_task_status(task_id):
    """Toggle task status"""
    task = Task.query.get_or_404(task_id)
    
    # Check permission
    if (not current_user.is_admin and 
        task.created_by != current_user.id and
        not task.assignees.filter_by(id=current_user.id).first()):
        return jsonify({'error': 'Permission denied'}), 403
    
    try:
        old_status = task.status
        
        if task.status == TaskStatus.COMPLETED:
            task.status = TaskStatus.PENDING
            task.completed_at = None
        else:
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'old_status': old_status.value,
            'new_status': task.status.value,
            'message': 'Task status updated'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Toggle task status error: {e}")
        return jsonify({'error': 'Failed to update task status'}), 500

# ===== Service Job API =====
@api_bp.route('/service_jobs/<int:job_id>/update_status', methods=['POST'])
@login_required
def api_update_service_job_status(job_id):
    """Update service job status"""
    job = ServiceJob.query.get_or_404(job_id)
    
    # Check permission
    if (current_user.role == UserRole.TECHNICIAN and 
        job.assigned_technician != current_user.id):
        return jsonify({'error': 'Permission denied'}), 403
    
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'error': 'Status is required'}), 400
        
        old_status = job.status
        job.status = ServiceJobStatus(new_status)
        
        # Update relevant dates
        if job.status == ServiceJobStatus.COMPLETED:
            job.completed_date = datetime.now(timezone.utc)
        elif job.status == ServiceJobStatus.DELIVERED:
            job.delivered_date = datetime.now(timezone.utc)
        
        job.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'old_status': old_status.value,
            'new_status': job.status.value,
            'message': 'Service job status updated'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Update service job status error: {e}")
        return jsonify({'error': 'Failed to update status'}), 500

# ===== Customer API =====
@api_bp.route('/customers/search')
@login_required
def api_search_customers():
    """Search customers API"""
    query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 20, type=int)
    
    if not query:
        return jsonify([])
    
    customers = Customer.query.filter(
        Customer.status == 'active',
        or_(
            Customer.name.contains(query),
            Customer.phone.contains(query),
            Customer.email.contains(query),
            Customer.customer_code.contains(query)
        )
    ).limit(limit).all()
    
    return jsonify([{
        'id': customer.id,
        'name': customer.name,
        'phone': customer.phone,
        'email': customer.email,
        'customer_code': customer.customer_code,
        'customer_type': customer.customer_type,
        'address': customer.address
    } for customer in customers])

@api_bp.route('/customers/quick_add', methods=['POST'])
@login_required
def api_quick_add_customer():
    """Quick add customer API"""
    try:
        data = request.get_json()
        
        if not data or not data.get('name') or not data.get('phone'):
            return jsonify({'error': 'Name and phone are required'}), 400
        
        # Check if customer already exists
        existing = Customer.query.filter_by(phone=data['phone']).first()
        if existing:
            return jsonify({'error': 'Phone number already exists'}), 400
        
        customer = Customer(
            name=data['name'],
            phone=data['phone'],
            email=data.get('email', ''),
            address=data.get('address', ''),
            customer_type=data.get('customer_type', 'individual'),
            created_by=current_user.id
        )
        
        customer.generate_customer_code()
        
        db.session.add(customer)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'customer': {
                'id': customer.id,
                'name': customer.name,
                'phone': customer.phone,
                'email': customer.email,
                'customer_code': customer.customer_code
            },
            'message': 'Customer created successfully'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Quick add customer error: {e}")
        return jsonify({'error': 'Failed to create customer'}), 500

# ===== Product API =====
@api_bp.route('/products/search')
@login_required
def api_search_products():
    """Search products API"""
    query = request.args.get('q', '').strip()
    category = request.args.get('category', '')
    limit = request.args.get('limit', 50, type=int)
    
    products_query = Product.query.filter(Product.is_active == True)
    
    if query:
        products_query = products_query.filter(
            or_(
                Product.name.contains(query),
                Product.sku.contains(query),
                Product.barcode.contains(query)
            )
        )
    
    if category:
        products_query = products_query.filter(Product.category == category)
    
    products = products_query.limit(limit).all()
    
    return jsonify([{
        'id': product.id,
        'name': product.name,
        'sku': product.sku,
        'barcode': product.barcode,
        'price': float(product.price),
        'cost': float(product.cost or 0),
        'stock_quantity': product.stock_quantity,
        'category': product.category,
        'is_service': product.is_service,
        'image_url': product.image_url
    } for product in products])

@api_bp.route('/products/<int:product_id>/adjust_stock', methods=['POST'])
@login_required
def api_adjust_product_stock(product_id):
    pass
