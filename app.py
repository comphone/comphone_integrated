from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from enum import Enum
import os
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'comphone-service-center-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///service_center.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Enums
class UserRole(Enum):
    ADMIN = 'admin'
    TECHNICIAN = 'technician'
    SALES = 'sales'

class ServiceJobStatus(Enum):
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    WAITING_PARTS = 'waiting_parts'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.SALES)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    id_card = db.Column(db.String(20))
    birthday = db.Column(db.Date)
    gender = db.Column(db.String(10))
    occupation = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    devices = db.relationship('Device', backref='customer', lazy=True)
    service_jobs = db.relationship('ServiceJob', backref='customer', lazy=True)
    sales = db.relationship('Sale', backref='customer', lazy=True)

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    device_type = db.Column(db.String(50), nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    serial_number = db.Column(db.String(100))
    imei = db.Column(db.String(20))
    color = db.Column(db.String(30))
    storage_capacity = db.Column(db.String(20))
    purchase_date = db.Column(db.Date)
    warranty_expiry = db.Column(db.Date)
    condition_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    service_jobs = db.relationship('ServiceJob', backref='device', lazy=True)

class ServiceJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)
    problem_description = db.Column(db.Text, nullable=False)
    diagnosis = db.Column(db.Text)
    solution = db.Column(db.Text)
    status = db.Column(db.Enum(ServiceJobStatus), default=ServiceJobStatus.PENDING)
    priority = db.Column(db.String(10), default='medium')
    assigned_technician_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    estimated_cost = db.Column(db.Float)
    actual_cost = db.Column(db.Float)
    estimated_completion_date = db.Column(db.Date)
    expected_completion_date = db.Column(db.Date)
    actual_completion_date = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = db.Column(db.Text)
    
    assigned_technician = db.relationship('User', backref='assigned_jobs')

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sku = db.Column(db.String(50), unique=True)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    brand = db.Column(db.String(50))
    price = db.Column(db.Float, nullable=False)
    cost = db.Column(db.Float)
    cost_price = db.Column(db.Float)
    stock_quantity = db.Column(db.Integer, default=0)
    low_stock_alert = db.Column(db.Integer, default=5)
    min_stock_level = db.Column(db.Integer, default=5)
    location = db.Column(db.String(50))
    weight = db.Column(db.Float)
    is_active = db.Column(db.Boolean, default=True)
    image = db.Column(db.String(200))
    barcode = db.Column(db.String(50))
    supplier = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    salesperson_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    total_amount = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float)
    subtotal = db.Column(db.Float, default=0)
    discount = db.Column(db.Float, default=0)
    tax = db.Column(db.Float, default=0)
    payment_method = db.Column(db.String(50))
    payment_status = db.Column(db.String(20), default='paid')
    sale_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    
    salesperson = db.relationship('User', foreign_keys=[salesperson_id], backref='sales')
    user = db.relationship('User', foreign_keys=[user_id], backref='user_sales')
    items = db.relationship('SaleItem', backref='sale', lazy=True)

class SaleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, default=0)
    
    product = db.relationship('Product', backref='sale_items')

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    service_job_id = db.Column(db.Integer, db.ForeignKey('service_job.id'))
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'))
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float)
    subtotal = db.Column(db.Float, default=0)
    tax_amount = db.Column(db.Float, default=0)
    tax = db.Column(db.Float, default=0)
    discount_amount = db.Column(db.Float, default=0)
    discount = db.Column(db.Float, default=0)
    payment_status = db.Column(db.String(20), default='pending')
    status = db.Column(db.String(20), default='pending')
    payment_method = db.Column(db.String(20))
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    invoice_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime)
    paid_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    
    customer = db.relationship('Customer', backref='invoices')
    service_job = db.relationship('ServiceJob', backref='invoices')
    sale = db.relationship('Sale', backref='invoices')
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True)

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    
    product = db.relationship('Product', lazy=True)

class SystemSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Template Functions
@app.template_filter('user_role')
def user_role_filter(role):
    if hasattr(role, 'value'):
        role_value = role.value
    else:
        role_value = str(role)
    
    role_translations = {
        'admin': 'ผู้ดูแลระบบ',
        'technician': 'ช่างเทคนิค', 
        'sales': 'พนักงานขาย'
    }
    return role_translations.get(role_value, role_value)

@app.template_filter('status_badge')
def status_badge_filter(status):
    if hasattr(status, 'value'):
        status_value = status.value
    else:
        status_value = str(status)
    
    status_classes = {
        'pending': 'bg-warning text-dark',
        'in_progress': 'bg-info text-white',
        'waiting_parts': 'bg-purple text-white',
        'completed': 'bg-success text-white',
        'cancelled': 'bg-danger text-white'
    }
    
    status_texts = {
        'pending': 'รอดำเนินการ',
        'in_progress': 'กำลังดำเนินการ',
        'waiting_parts': 'รออะไหล่',
        'completed': 'เสร็จสิ้น',
        'cancelled': 'ยกเลิก'
    }
    
    css_class = status_classes.get(status_value, 'bg-secondary text-white')
    text = status_texts.get(status_value, status_value)
    
    return f'<span class="badge {css_class}">{text}</span>'

@app.template_global()
def moment():
    return datetime

@app.template_global()
def now():
    return datetime.now()

def render_template_placeholder(title, icon):
    """ฟังก์ชันสำหรับแสดงหน้าเมื่อเกิดข้อผิดพลาด"""
    return render_template('main/placeholder.html', title=title, icon=icon, user=current_user)

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            print(f"✅ User {username} logged in successfully")
            return redirect(url_for('dashboard'))
        else:
            flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'error')
    
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Main Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        print(f"🚀 Loading dashboard for user: {current_user.username}")
        
        # Dashboard statistics with safe queries
        total_customers = db.session.query(Customer).count()
        total_jobs = db.session.query(ServiceJob).count()
        completed_jobs = db.session.query(ServiceJob).filter(ServiceJob.status == ServiceJobStatus.COMPLETED).count()
        pending_jobs = db.session.query(ServiceJob).filter(ServiceJob.status == ServiceJobStatus.PENDING).count()
        in_progress_jobs = db.session.query(ServiceJob).filter(ServiceJob.status == ServiceJobStatus.IN_PROGRESS).count()
        
        # Calculate monthly revenue from sales
        current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_revenue = db.session.query(db.func.sum(Sale.total_amount)).filter(
            Sale.created_at >= current_month
        ).scalar() or 0

        # Recent jobs (last 5)
        recent_jobs = db.session.query(ServiceJob).order_by(ServiceJob.created_at.desc()).limit(5).all()
        
        # Products stats
        total_products = db.session.query(Product).count()
        low_stock_products = db.session.query(Product).filter(
            Product.stock_quantity <= Product.low_stock_alert
        ).count()
        
        # Sales stats
        total_sales = db.session.query(Sale).count()
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_sales = db.session.query(Sale).filter(Sale.created_at >= today_start).count()
        
        # Prepare data for template
        template_data = {
            'user': current_user,
            'total_customers': total_customers,
            'total_service_jobs': total_jobs,
            'active_jobs': pending_jobs + in_progress_jobs,
            'completed_jobs': completed_jobs,
            'pending_jobs': pending_jobs,
            'in_progress_jobs': in_progress_jobs,
            'products_count': total_products,
            'monthly_revenue': float(monthly_revenue),
            'recent_jobs': recent_jobs,
            'total_products': total_products,
            'low_stock_products': low_stock_products,
            'total_sales': total_sales,
            'today_sales': today_sales,
            'moment': datetime
        }
        
        print(f"📊 Dashboard data prepared: customers={total_customers}, jobs={total_jobs}, revenue={monthly_revenue}")
        
        return render_template('main/dashboard.html', **template_data)
        
    except Exception as e:
        print(f"⚠️ Dashboard error: {e}")
        import traceback
        traceback.print_exc()
        
        # Return basic template if error
        return render_template('main/dashboard.html', 
                             total_customers=0,
                             total_service_jobs=0,
                             active_jobs=0,
                             completed_jobs=0,
                             pending_jobs=0,
                             in_progress_jobs=0,
                             products_count=0,
                             monthly_revenue=0.0,
                             recent_jobs=[],
                             total_products=0,
                             low_stock_products=0,
                             total_sales=0,
                             today_sales=0,
                             moment=datetime,
                             user=current_user)

# Customer Routes
@app.route('/customers')
@login_required
def customers():
    try:
        search = request.args.get('search', '')
        page = request.args.get('page', 1, type=int)
        
        query = Customer.query
        if search:
            query = query.filter(
                db.or_(
                    Customer.name.contains(search),
                    Customer.phone.contains(search),
                    Customer.email.contains(search)
                )
            )
        
        customers_list = query.order_by(Customer.created_at.desc()).all()
        
        # Calculate statistics
        active_customers = len([c for c in customers_list if len(c.devices) > 0])
        total_devices = Device.query.count()
        this_month_customers = Customer.query.filter(
            Customer.created_at >= datetime.now().replace(day=1)
        ).count()
        
        return render_template('customers/index.html', 
                             customers=customers_list,
                             active_customers=active_customers,
                             total_devices=total_devices,
                             this_month_customers=this_month_customers,
                             user=current_user)
    except Exception as e:
        print(f"⚠️ Customers error: {e}")
        return render_template_placeholder('ลูกค้า', 'fas fa-users')

@app.route('/customers', methods=['POST'])
@login_required
def create_customer():
    try:
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        address = request.form.get('address')
        id_card = request.form.get('id_card')
        birthday = request.form.get('birthday')
        gender = request.form.get('gender')
        occupation = request.form.get('occupation')
        notes = request.form.get('notes')
        
        customer = Customer(
            name=name,
            phone=phone,
            email=email,
            address=address,
            id_card=id_card,
            gender=gender,
            occupation=occupation,
            notes=notes
        )
        
        if birthday:
            customer.birthday = datetime.strptime(birthday, '%Y-%m-%d').date()
        
        db.session.add(customer)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'เพิ่มลูกค้าเรียบร้อยแล้ว', 'id': customer.id})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/customers/<int:customer_id>')
@login_required
def view_customer(customer_id):
    try:
        customer = Customer.query.get_or_404(customer_id)
        return render_template('customers/view.html', customer=customer, user=current_user)
    except Exception as e:
        print(f"⚠️ View customer error: {e}")
        return redirect(url_for('customers'))

@app.route('/customers/<int:customer_id>/edit')
@login_required
def edit_customer(customer_id):
    try:
        customer = Customer.query.get_or_404(customer_id)
        return render_template('customers/edit.html', customer=customer, user=current_user)
    except Exception as e:
        print(f"⚠️ Edit customer error: {e}")
        return redirect(url_for('customers'))

@app.route('/customers/<int:customer_id>', methods=['DELETE'])
@login_required
def delete_customer(customer_id):
    try:
        customer = Customer.query.get_or_404(customer_id)
        
        # Check if customer has associated records
        if customer.service_jobs or customer.sales:
            return jsonify({'success': False, 'message': 'ไม่สามารถลบลูกค้าที่มีประวัติการใช้บริการ'}), 400
        
        db.session.delete(customer)
        db.session.commit()
        return jsonify({'success': True, 'message': 'ลบลูกค้าเรียบร้อยแล้ว'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/customers/add')
@login_required
def add_customer():
    try:
        return render_template('customers/add.html', user=current_user)
    except Exception as e:
        print(f"⚠️ Add customer error: {e}")
        return redirect(url_for('customers'))

# Service Jobs Routes
@app.route('/service-jobs')
@login_required
def service_jobs():
    try:
        # Get filter parameters
        search = request.args.get('search', '')
        status_filter = request.args.get('status', '')
        technician_filter = request.args.get('technician', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        page = request.args.get('page', 1, type=int)
        
        # Build query with proper joins
        query = ServiceJob.query.join(Customer).join(Device)
        
        # Apply filters
        if search:
            query = query.filter(
                db.or_(
                    ServiceJob.id.like(f'%{search}%'),
                    Customer.name.contains(search),
                    Customer.phone.contains(search),
                    Device.brand.contains(search),
                    Device.model.contains(search),
                    ServiceJob.problem_description.contains(search)
                )
            )
        
        if status_filter:
            query = query.filter(ServiceJob.status == ServiceJobStatus(status_filter))
        
        if technician_filter:
            query = query.filter(ServiceJob.assigned_technician_id == technician_filter)
        
        if date_from:
            query = query.filter(ServiceJob.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
        
        if date_to:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(ServiceJob.created_at < date_to_obj)
        
        service_jobs_list = query.order_by(ServiceJob.created_at.desc()).all()
        
        # Get statistics for status cards
        pending_jobs = ServiceJob.query.filter_by(status=ServiceJobStatus.PENDING).count()
        in_progress_jobs = ServiceJob.query.filter_by(status=ServiceJobStatus.IN_PROGRESS).count()
        waiting_parts_jobs = ServiceJob.query.filter_by(status=ServiceJobStatus.WAITING_PARTS).count()
        completed_jobs = ServiceJob.query.filter_by(status=ServiceJobStatus.COMPLETED).count()
        cancelled_jobs = ServiceJob.query.filter_by(status=ServiceJobStatus.CANCELLED).count()
        
        # Get technicians for filter dropdown
        technicians = User.query.filter_by(role=UserRole.TECHNICIAN).all()
        
        # Get customers for new job form
        customers = Customer.query.order_by(Customer.name).all()
        
        return render_template('service_jobs/index.html', 
                             service_jobs=service_jobs_list,
                             pending_jobs=pending_jobs,
                             in_progress_jobs=in_progress_jobs,
                             waiting_parts_jobs=waiting_parts_jobs,
                             completed_jobs=completed_jobs,
                             cancelled_jobs=cancelled_jobs,
                             technicians=technicians,
                             customers=customers,
                             user=current_user)
    except Exception as e:
        print(f"⚠️ Service jobs error: {e}")
        return render_template_placeholder('งานบริการ', 'fas fa-tools')

@app.route('/service-jobs', methods=['POST'])
@login_required
def create_service_job():
    try:
        # Get form data
        customer_id = request.form.get('customer_id')
        device_id = request.form.get('device_id')
        problem_description = request.form.get('problem_description')
        diagnosis = request.form.get('diagnosis')
        priority = request.form.get('priority', 'medium')
        assigned_technician_id = request.form.get('technician_id') or None
        expected_completion_date = request.form.get('expected_completion_date')
        estimated_cost = request.form.get('estimated_cost')
        status = request.form.get('status', 'pending')
        notes = request.form.get('notes')
        
        # Create new service job
        job = ServiceJob(
            customer_id=customer_id,
            device_id=device_id,
            problem_description=problem_description,
            diagnosis=diagnosis,
            priority=priority,
            assigned_technician_id=assigned_technician_id,
            estimated_cost=float(estimated_cost) if estimated_cost else None,
            status=ServiceJobStatus(status),
            notes=notes
        )
        
        if expected_completion_date:
            job.expected_completion_date = datetime.strptime(expected_completion_date, '%Y-%m-%d').date()
            job.estimated_completion_date = job.expected_completion_date
        
        db.session.add(job)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'เพิ่มงานบริการใหม่เรียบร้อยแล้ว'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/service-jobs/<int:job_id>')
@login_required
def view_service_job(job_id):
    try:
        job = ServiceJob.query.get_or_404(job_id)
        return render_template('service_jobs/view.html', job=job, user=current_user)
    except Exception as e:
        print(f"⚠️ View service job error: {e}")
        return redirect(url_for('service_jobs'))

@app.route('/service-jobs/<int:job_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_service_job(job_id):
    try:
        job = ServiceJob.query.get_or_404(job_id)
        
        if request.method == 'POST':
            # Update job data
            job.problem_description = request.form.get('problem_description')
            job.diagnosis = request.form.get('diagnosis')
            job.solution = request.form.get('solution')
            job.priority = request.form.get('priority', 'medium')
            job.assigned_technician_id = request.form.get('assigned_technician_id') or None
            job.estimated_cost = float(request.form.get('estimated_cost')) if request.form.get('estimated_cost') else None
            job.actual_cost = float(request.form.get('actual_cost')) if request.form.get('actual_cost') else None
            job.status = ServiceJobStatus(request.form.get('status'))
            job.notes = request.form.get('notes')
            
            expected_completion_date = request.form.get('expected_completion_date')
            if expected_completion_date:
                job.expected_completion_date = datetime.strptime(expected_completion_date, '%Y-%m-%d').date()
                job.estimated_completion_date = job.expected_completion_date
            
            # Set completion date if status is completed
            if job.status == ServiceJobStatus.COMPLETED and not job.completed_at:
                job.completed_at = datetime.utcnow()
                job.actual_completion_date = datetime.utcnow()
            
            job.updated_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'อัปเดตงานบริการเรียบร้อยแล้ว'})
        
        # GET request - show edit form
        customers = Customer.query.order_by(Customer.name).all()
        technicians = User.query.filter_by(role=UserRole.TECHNICIAN).all()
        
        return render_template('service_jobs/edit.html', 
                             job=job, 
                             customers=customers,
                             technicians=technicians,
                             user=current_user)
        
    except Exception as e:
        db.session.rollback()
        print(f"⚠️ Edit service job error: {e}")
        if request.method == 'POST':
            return jsonify({'success': False, 'message': str(e)}), 500
        return redirect(url_for('service_jobs'))

@app.route('/service-jobs/<int:job_id>/delete', methods=['POST'])
@login_required
def delete_service_job(job_id):
    try:
        job = ServiceJob.query.get_or_404(job_id)
        
        # Check if job has associated invoices
        if job.invoices:
            return jsonify({'success': False, 'message': 'ไม่สามารถลบงานบริการที่มีใบเสร็จแล้ว'}), 400
        
        db.session.delete(job)
        db.session.commit()
        return jsonify({'success': True, 'message': 'ลบงานบริการเรียบร้อยแล้ว'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# Product Routes
@app.route('/products')
@login_required
def products():
    try:
        search = request.args.get('search', '')
        category_filter = request.args.get('category', '')
        page = request.args.get('page', 1, type=int)
        
        query = Product.query.filter_by(is_active=True)
        
        if search:
            query = query.filter(
                db.or_(
                    Product.name.contains(search),
                    Product.sku.contains(search),
                    Product.brand.contains(search),
                    Product.category.contains(search)
                )
            )
        
        if category_filter:
            query = query.filter(Product.category == category_filter)
        
        products_list = query.order_by(Product.name).all()
        
        # Calculate statistics
        total_products = Product.query.filter_by(is_active=True).count()
        low_stock_products = Product.query.filter(
            Product.stock_quantity <= Product.low_stock_alert,
            Product.is_active == True
        ).count()
        out_of_stock = Product.query.filter(
            Product.stock_quantity == 0,
            Product.is_active == True
        ).count()
        total_value = db.session.query(db.func.sum(Product.price * Product.stock_quantity)).scalar() or 0
        
        # Get categories for filter
        categories = db.session.query(Product.category).filter(
            Product.category.isnot(None),
            Product.is_active == True
        ).distinct().all()
        categories = [cat[0] for cat in categories if cat[0]]
        
        return render_template('products/index.html',
                             products=products_list,
                             total_products=total_products,
                             low_stock_products=low_stock_products,
                             out_of_stock=out_of_stock,
                             total_value=float(total_value),
                             categories=categories,
                             user=current_user)
    except Exception as e:
        print(f"⚠️ Products error: {e}")
        return render_template_placeholder('สินค้า', 'fas fa-box')

@app.route('/products', methods=['POST'])
@login_required
def create_product():
    try:
        name = request.form.get('name')
        sku = request.form.get('sku')
        description = request.form.get('description')
        category = request.form.get('category')
        brand = request.form.get('brand')
        price = float(request.form.get('price'))
        cost = float(request.form.get('cost')) if request.form.get('cost') else None
        stock_quantity = int(request.form.get('stock_quantity', 0))
        low_stock_alert = int(request.form.get('low_stock_alert', 5))
        location = request.form.get('location')
        weight = float(request.form.get('weight')) if request.form.get('weight') else None
        barcode = request.form.get('barcode')
        supplier = request.form.get('supplier')
        
        product = Product(
            name=name,
            sku=sku,
            description=description,
            category=category,
            brand=brand,
            price=price,
            cost=cost,
            cost_price=cost,
            stock_quantity=stock_quantity,
            low_stock_alert=low_stock_alert,
            min_stock_level=low_stock_alert,
            location=location,
            weight=weight,
            barcode=barcode,
            supplier=supplier
        )
        
        db.session.add(product)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'เพิ่มสินค้าเรียบร้อยแล้ว', 'id': product.id})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/products/<int:product_id>')
@login_required
def view_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        return render_template('products/view.html', product=product, user=current_user)
    except Exception as e:
        print(f"⚠️ View product error: {e}")
        return redirect(url_for('products'))

@app.route('/products/<int:product_id>/edit')
@login_required
def edit_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        return render_template('products/edit.html', product=product, user=current_user)
    except Exception as e:
        print(f"⚠️ Edit product error: {e}")
        return redirect(url_for('products'))

@app.route('/products/<int:product_id>', methods=['DELETE'])
@login_required
def delete_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        
        # Check if product has associated sales
        if product.sale_items:
            return jsonify({'success': False, 'message': 'ไม่สามารถลบสินค้าที่มีประวัติการขาย'}), 400
        
        # Soft delete
        product.is_active = False
        db.session.commit()
        return jsonify({'success': True, 'message': 'ลบสินค้าเรียบร้อยแล้ว'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/products/<int:product_id>/adjust-stock', methods=['POST'])
@login_required
def adjust_product_stock(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        adjustment = int(request.form.get('adjustment', 0))
        reason = request.form.get('reason', '')
        
        old_quantity = product.stock_quantity
        product.stock_quantity += adjustment
        
        if product.stock_quantity < 0:
            product.stock_quantity = 0
        
        product.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'ปรับสต็อกเรียบร้อยแล้ว: {old_quantity} → {product.stock_quantity}',
            'new_quantity': product.stock_quantity
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/products/add')
@login_required
def add_product():
    try:
        return render_template('products/add.html', user=current_user)
    except Exception as e:
        print(f"⚠️ Add product error: {e}")
        return redirect(url_for('products'))

@app.route('/products/bulk-delete', methods=['POST'])
@login_required
def bulk_delete_products():
    try:
        product_ids = request.json.get('product_ids', [])
        
        if not product_ids:
            return jsonify({'success': False, 'message': 'ไม่มีสินค้าที่เลือก'}), 400
        
        products = Product.query.filter(Product.id.in_(product_ids)).all()
        
        for product in products:
            if product.sale_items:
                return jsonify({'success': False, 'message': f'ไม่สามารถลบสินค้า "{product.name}" ที่มีประวัติการขาย'}), 400
        
        # Soft delete all selected products
        for product in products:
            product.is_active = False
        
        db.session.commit()
        return jsonify({'success': True, 'message': f'ลบสินค้า {len(products)} รายการเรียบร้อยแล้ว'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/products/export')
@login_required
def export_products():
    try:
        products = Product.query.filter_by(is_active=True).all()
        
        # Simple CSV export
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['SKU', 'ชื่อสินค้า', 'หมวดหมู่', 'แบรนด์', 'ราคา', 'ต้นทุน', 'สต็อก', 'ที่เก็บ'])
        
        # Write data
        for product in products:
            writer.writerow([
                product.sku or '',
                product.name,
                product.category or '',
                product.brand or '',
                product.price,
                product.cost or 0,
                product.stock_quantity,
                product.location or ''
            ])
        
        output.seek(0)
        
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=products_{datetime.now().strftime("%Y%m%d")}.csv'
            }
        )
        
    except Exception as e:
        print(f"⚠️ Export products error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# Sales Routes
@app.route('/sales')
@login_required
def sales():
    try:
        search = request.args.get('search', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        query = Sale.query.join(User, Sale.salesperson_id == User.id, isouter=True)
        
        if search:
            query = query.filter(
                db.or_(
                    Sale.id.like(f'%{search}%'),
                    User.username.contains(search)
                )
            )
        
        if date_from:
            query = query.filter(Sale.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
        
        if date_to:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Sale.created_at < date_to_obj)
        
        sales_list = query.order_by(Sale.created_at.desc()).all()
        
        # Calculate statistics
        total_sales = Sale.query.count()
        today_sales = Sale.query.filter(
            Sale.created_at >= datetime.now().replace(hour=0, minute=0, second=0)
        ).count()
        total_revenue = db.session.query(db.func.sum(Sale.total_amount)).scalar() or 0
        avg_sale = total_revenue / total_sales if total_sales > 0 else 0
        
        return render_template('sales/index.html',
                             sales=sales_list,
                             total_sales=total_sales,
                             today_sales=today_sales,
                             total_revenue=float(total_revenue),
                             avg_sale=float(avg_sale),
                             user=current_user)
    except Exception as e:
        print(f"⚠️ Sales error: {e}")
        return render_template_placeholder('ขาย', 'fas fa-cash-register')

@app.route('/sales', methods=['POST'])
@login_required
def create_sale():
    try:
        customer_id = request.form.get('customer_id') or None
        items_data = request.form.get('items')
        payment_method = request.form.get('payment_method', 'cash')
        discount = float(request.form.get('discount', 0))
        notes = request.form.get('notes', '')
        
        if not items_data:
            return jsonify({'success': False, 'message': 'ไม่มีสินค้าในการขาย'}), 400
        
        items = json.loads(items_data)
        
        if not items:
            return jsonify({'success': False, 'message': 'ไม่มีสินค้าในการขาย'}), 400
        
        # Calculate totals
        subtotal = 0
        sale_items = []
        
        for item in items:
            product = Product.query.get(item['product_id'])
            if not product:
                return jsonify({'success': False, 'message': f'ไม่พบสินค้า ID: {item["product_id"]}'}), 400
            
            quantity = int(item['quantity'])
            if product.stock_quantity < quantity:
                return jsonify({'success': False, 'message': f'สินค้า "{product.name}" มีสต็อกไม่เพียงพอ'}), 400
            
            unit_price = float(item.get('unit_price', product.price))
            total_price = unit_price * quantity
            subtotal += total_price
            
            sale_items.append({
                'product': product,
                'quantity': quantity,
                'unit_price': unit_price,
                'total_price': total_price
            })
        
        tax = subtotal * 0.07  # 7% VAT
        total_amount = subtotal + tax - discount
        
        # Create sale
        sale = Sale(
            customer_id=customer_id,
            salesperson_id=current_user.id,
            user_id=current_user.id,
            total_amount=total_amount,
            total=total_amount,
            subtotal=subtotal,
            discount=discount,
            tax=tax,
            payment_method=payment_method,
            payment_status='paid',
            notes=notes
        )
        
        db.session.add(sale)
        db.session.flush()  # Get sale ID
        
        # Create sale items and update stock
        for item_data in sale_items:
            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=item_data['product'].id,
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price'],
                total_price=item_data['total_price']
            )
            db.session.add(sale_item)
            
            # Update product stock
            item_data['product'].stock_quantity -= item_data['quantity']
            item_data['product'].updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'บันทึกการขายเรียบร้อยแล้ว',
            'sale_id': sale.id,
            'total_amount': total_amount
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/sales/<int:sale_id>/receipt')
@login_required
def sale_receipt(sale_id):
    try:
        sale = Sale.query.get_or_404(sale_id)
        return render_template('sales/receipt.html', sale=sale, user=current_user)
    except Exception as e:
        print(f"⚠️ Sale receipt error: {e}")
        return redirect(url_for('sales'))

@app.route('/sales/history')
@login_required
def sales_history():
    try:
        # Get recent sales for quick access
        recent_sales = Sale.query.order_by(Sale.created_at.desc()).limit(10).all()
        return render_template('sales/history.html', recent_sales=recent_sales, user=current_user)
    except Exception as e:
        print(f"⚠️ Sales history error: {e}")
        return render_template_placeholder('ประวัติการขาย', 'fas fa-history')

# Invoice Routes
@app.route('/invoices')
@login_required
def invoices():
    try:
        search = request.args.get('search', '')
        status_filter = request.args.get('status', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        query = Invoice.query.join(Customer, isouter=True)
        
        if search:
            query = query.filter(
                db.or_(
                    Invoice.invoice_number.contains(search),
                    Customer.name.contains(search),
                    Customer.phone.contains(search)
                )
            )
        
        if status_filter:
            query = query.filter(Invoice.payment_status == status_filter)
        
        if date_from:
            query = query.filter(Invoice.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
        
        if date_to:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Invoice.created_at < date_to_obj)
        
        invoices_list = query.order_by(Invoice.created_at.desc()).all()
        
        # Calculate statistics
        total_invoices = Invoice.query.count()
        pending_invoices = Invoice.query.filter_by(payment_status='pending').count()
        paid_invoices = Invoice.query.filter_by(payment_status='paid').count()
        overdue_invoices = Invoice.query.filter(
            Invoice.due_date < datetime.now(),
            Invoice.payment_status == 'pending'
        ).count()
        
        total_amount = db.session.query(db.func.sum(Invoice.total_amount)).scalar() or 0
        pending_amount = db.session.query(db.func.sum(Invoice.total_amount)).filter(
            Invoice.payment_status == 'pending'
        ).scalar() or 0
        
        return render_template('invoices/index.html',
                             invoices=invoices_list,
                             total_invoices=total_invoices,
                             pending_invoices=pending_invoices,
                             paid_invoices=paid_invoices,
                             overdue_invoices=overdue_invoices,
                             total_amount=float(total_amount),
                             pending_amount=float(pending_amount),
                             user=current_user)
    except Exception as e:
        print(f"⚠️ Invoices error: {e}")
        return render_template_placeholder('ใบเสร็จ', 'fas fa-file-invoice')

@app.route('/invoices', methods=['POST'])
@login_required
def create_invoice():
    try:
        customer_id = request.form.get('customer_id')
        service_job_id = request.form.get('service_job_id') or None
        sale_id = request.form.get('sale_id') or None
        items_data = request.form.get('items')
        due_days = int(request.form.get('due_days', 30))
        notes = request.form.get('notes', '')
        
        if not items_data:
            return jsonify({'success': False, 'message': 'ไม่มีรายการในใบเสร็จ'}), 400
        
        items = json.loads(items_data)
        
        # Generate invoice number
        last_invoice = Invoice.query.order_by(Invoice.id.desc()).first()
        invoice_number = f"INV-{datetime.now().strftime('%Y%m')}-{(last_invoice.id + 1) if last_invoice else 1:04d}"
        
        # Calculate totals
        subtotal = sum(float(item['total_price']) for item in items)
        tax = subtotal * 0.07  # 7% VAT
        total_amount = subtotal + tax
        
        # Create invoice
        invoice = Invoice(
            customer_id=customer_id,
            service_job_id=service_job_id,
            sale_id=sale_id,
            invoice_number=invoice_number,
            total_amount=total_amount,
            total=total_amount,
            subtotal=subtotal,
            tax_amount=tax,
            tax=tax,
            due_date=datetime.now() + timedelta(days=due_days),
            notes=notes
        )
        
        db.session.add(invoice)
        db.session.flush()  # Get invoice ID
        
        # Create invoice items
        for item in items:
            invoice_item = InvoiceItem(
                invoice_id=invoice.id,
                product_id=item.get('product_id'),
                description=item['description'],
                quantity=int(item['quantity']),
                unit_price=float(item['unit_price']),
                total_price=float(item['total_price'])
            )
            db.session.add(invoice_item)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'สร้างใบเสร็จเรียบร้อยแล้ว',
            'invoice_id': invoice.id,
            'invoice_number': invoice_number
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/invoices/<int:invoice_id>')
@login_required
def view_invoice(invoice_id):
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        return render_template('invoices/view.html', invoice=invoice, user=current_user)
    except Exception as e:
        print(f"⚠️ View invoice error: {e}")
        return redirect(url_for('invoices'))

@app.route('/invoices/<int:invoice_id>/print')
@login_required
def print_invoice(invoice_id):
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        return render_template('invoices/print.html', invoice=invoice, user=current_user)
    except Exception as e:
        print(f"⚠️ Print invoice error: {e}")
        return redirect(url_for('invoices'))

@app.route('/invoices/<int:invoice_id>/send', methods=['POST'])
@login_required
def send_invoice(invoice_id):
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        email = request.form.get('email')
        
        # TODO: Implement email sending logic here
        # For now, just return success
        
        return jsonify({'success': True, 'message': f'ส่งใบเสร็จไปที่ {email} เรียบร้อยแล้ว'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/invoices/<int:invoice_id>', methods=['DELETE'])
@login_required
def delete_invoice(invoice_id):
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        
        if invoice.payment_status == 'paid':
            return jsonify({'success': False, 'message': 'ไม่สามารถลบใบเสร็จที่ชำระแล้ว'}), 400
        
        db.session.delete(invoice)
        db.session.commit()
        return jsonify({'success': True, 'message': 'ลบใบเสร็จเรียบร้อยแล้ว'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/invoices/bulk-send', methods=['POST'])
@login_required
def bulk_send_invoices():
    try:
        invoice_ids = request.json.get('invoice_ids', [])
        
        if not invoice_ids:
            return jsonify({'success': False, 'message': 'ไม่มีใบเสร็จที่เลือก'}), 400
        
        # TODO: Implement bulk email sending logic here
        
        return jsonify({'success': True, 'message': f'ส่งใบเสร็จ {len(invoice_ids)} ฉบับเรียบร้อยแล้ว'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/invoices/bulk-delete', methods=['POST'])
@login_required
def bulk_delete_invoices():
    try:
        invoice_ids = request.json.get('invoice_ids', [])
        
        if not invoice_ids:
            return jsonify({'success': False, 'message': 'ไม่มีใบเสร็จที่เลือก'}), 400
        
        invoices = Invoice.query.filter(Invoice.id.in_(invoice_ids)).all()
        
        for invoice in invoices:
            if invoice.payment_status == 'paid':
                return jsonify({'success': False, 'message': f'ไม่สามารถลบใบเสร็จ "{invoice.invoice_number}" ที่ชำระแล้ว'}), 400
        
        for invoice in invoices:
            db.session.delete(invoice)
        
        db.session.commit()
        return jsonify({'success': True, 'message': f'ลบใบเสร็จ {len(invoices)} ฉบับเรียบร้อยแล้ว'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/invoices/export')
@login_required
def export_invoices():
    try:
        invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
        
        # Simple CSV export
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['เลขที่ใบเสร็จ', 'ลูกค้า', 'จำนวนเงิน', 'สถานะ', 'วันที่สร้าง', 'วันครบกำหนด'])
        
        # Write data
        for invoice in invoices:
            writer.writerow([
                invoice.invoice_number,
                invoice.customer.name if invoice.customer else '',
                invoice.total_amount,
                invoice.payment_status,
                invoice.created_at.strftime('%Y-%m-%d'),
                invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else ''
            ])
        
        output.seek(0)
        
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=invoices_{datetime.now().strftime("%Y%m%d")}.csv'
            }
        )
        
    except Exception as e:
        print(f"⚠️ Export invoices error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# Report Routes
@app.route('/reports')
@login_required
def reports():
    try:
        # Date range for reports
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Sales reports
        sales_data = db.session.query(
            db.func.date(Sale.created_at).label('date'),
            db.func.sum(Sale.total_amount).label('total'),
            db.func.count(Sale.id).label('count')
        ).filter(
            Sale.created_at >= start_date
        ).group_by(
            db.func.date(Sale.created_at)
        ).all()
        
        # Service jobs reports
        service_jobs_data = db.session.query(
            ServiceJob.status,
            db.func.count(ServiceJob.id).label('count')
        ).group_by(ServiceJob.status).all()
        
        # Top products
        top_products = db.session.query(
            Product.name,
            db.func.sum(SaleItem.quantity).label('total_sold'),
            db.func.sum(SaleItem.total_price).label('total_revenue')
        ).join(SaleItem).join(Sale).filter(
            Sale.created_at >= start_date
        ).group_by(Product.id, Product.name).order_by(
            db.func.sum(SaleItem.total_price).desc()
        ).limit(10).all()
        
        # Monthly revenue
        monthly_revenue = db.session.query(
            db.func.sum(Sale.total_amount)
        ).filter(
            Sale.created_at >= datetime.now().replace(day=1)
        ).scalar() or 0
        
        # Calculate trends
        previous_month = (datetime.now().replace(day=1) - timedelta(days=1)).replace(day=1)
        previous_monthly_revenue = db.session.query(
            db.func.sum(Sale.total_amount)
        ).filter(
            Sale.created_at >= previous_month,
            Sale.created_at < datetime.now().replace(day=1)
        ).scalar() or 0
        
        revenue_trend = ((monthly_revenue - previous_monthly_revenue) / previous_monthly_revenue * 100) if previous_monthly_revenue > 0 else 0
        
        return render_template('reports/index.html',
                             sales_data=sales_data,
                             service_jobs_data=service_jobs_data,
                             top_products=top_products,
                             monthly_revenue=float(monthly_revenue),
                             revenue_trend=round(revenue_trend, 1),
                             user=current_user)
    except Exception as e:
        print(f"⚠️ Reports error: {e}")
        return render_template_placeholder('รายงาน', 'fas fa-chart-bar')

@app.route('/reports/export')
@login_required
def export_reports():
    try:
        report_type = request.args.get('type', 'sales')
        
        if report_type == 'sales':
            # Export sales report
            sales = Sale.query.order_by(Sale.created_at.desc()).all()
            
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['วันที่', 'ลูกค้า', 'พนักงานขาย', 'จำนวนเงิน', 'วิธีชำระ', 'สถานะ'])
            
            # Write data
            for sale in sales:
                writer.writerow([
                    sale.created_at.strftime('%Y-%m-%d %H:%M'),
                    sale.customer.name if sale.customer else 'ลูกค้าทั่วไป',
                    sale.salesperson.username if sale.salesperson else '',
                    sale.total_amount,
                    sale.payment_method or '',
                    sale.payment_status
                ])
            
            output.seek(0)
            
            from flask import Response
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename=sales_report_{datetime.now().strftime("%Y%m%d")}.csv'
                }
            )
        
        # Add other report types as needed
        return jsonify({'success': False, 'message': 'ประเภทรายงานไม่ถูกต้อง'}), 400
        
    except Exception as e:
        print(f"⚠️ Export reports error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# Additional Routes
@app.route('/users')
@login_required
def users():
    try:
        if current_user.role != UserRole.ADMIN:
            return render_template('errors/403.html'), 403
        
        users_list = User.query.order_by(User.created_at.desc()).all()
        return render_template('users/index.html', users=users_list, user=current_user)
    except Exception as e:
        print(f"⚠️ Users error: {e}")
        return render_template_placeholder('ผู้ใช้', 'fas fa-users-cog')

@app.route('/settings')
@login_required
def settings():
    try:
        if current_user.role != UserRole.ADMIN:
            return render_template('errors/403.html'), 403
        
        settings_list = SystemSettings.query.all()
        return render_template('settings/index.html', settings=settings_list, user=current_user)
    except Exception as e:
        print(f"⚠️ Settings error: {e}")
        return render_template_placeholder('ตั้งค่า', 'fas fa-cog')

@app.route('/profile')
@login_required
def profile():
    try:
        return render_template('users/profile.html', user=current_user)
    except Exception as e:
        print(f"⚠️ Profile error: {e}")
        return render_template_placeholder('โปรไฟล์', 'fas fa-user')

@app.route('/inventory')
@login_required
def inventory():
    try:
        # Get low stock products
        low_stock_products = Product.query.filter(
            Product.stock_quantity <= Product.low_stock_alert,
            Product.is_active == True
        ).all()
        
        # Get out of stock products
        out_of_stock_products = Product.query.filter(
            Product.stock_quantity == 0,
            Product.is_active == True
        ).all()
        
        # Calculate inventory value
        total_value = db.session.query(
            db.func.sum(Product.price * Product.stock_quantity)
        ).filter(Product.is_active == True).scalar() or 0
        
        return render_template('inventory/index.html',
                             low_stock_products=low_stock_products,
                             out_of_stock_products=out_of_stock_products,
                             total_value=float(total_value),
                             user=current_user)
    except Exception as e:
        print(f"⚠️ Inventory error: {e}")
        return render_template_placeholder('คลังสินค้า', 'fas fa-warehouse')

# API Routes
@app.route('/api/customers/<int:customer_id>/devices')
@login_required
def api_customer_devices(customer_id):
    try:
        customer = Customer.query.get_or_404(customer_id)
        devices = [{'id': d.id, 'name': f'{d.brand} {d.model} ({d.device_type})'} for d in customer.devices]
        return jsonify({'success': True, 'devices': devices})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/products/<int:product_id>')
@login_required
def api_product_details(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        return jsonify({
            'success': True,
            'product': {
                'id': product.id,
                'name': product.name,
                'price': product.price,
                'stock_quantity': product.stock_quantity,
                'sku': product.sku or ''
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/sales/last')
@login_required
def api_last_sale():
    try:
        last_sale = Sale.query.order_by(Sale.id.desc()).first()
        if last_sale:
            return jsonify({
                'success': True,
                'sale': {
                    'id': last_sale.id,
                    'total_amount': last_sale.total_amount,
                    'created_at': last_sale.created_at.isoformat()
                }
            })
        return jsonify({'success': True, 'sale': None})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/sales/unpaid')
@login_required
def api_unpaid_sales():
    try:
        unpaid_sales = Sale.query.filter_by(payment_status='pending').count()
        return jsonify({'success': True, 'count': unpaid_sales})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/service-jobs/completed')
@login_required
def api_completed_jobs():
    try:
        completed_jobs = ServiceJob.query.filter_by(status=ServiceJobStatus.COMPLETED).count()
        return jsonify({'success': True, 'count': completed_jobs})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Error Handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

# Sample Data Creation
def create_sample_data():
    """สร้างข้อมูลตัวอย่างสำหรับทดสอบระบบ"""
    print("🔧 Creating sample data...")
    
    # Create admin user
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_user = User(
            username='admin',
            email='admin@comphone.com',
            role=UserRole.ADMIN
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
    
    # Create technician user
    tech_user = User.query.filter_by(username='technician').first()
    if not tech_user:
        tech_user = User(
            username='technician',
            email='tech@comphone.com',
            role=UserRole.TECHNICIAN
        )
        tech_user.set_password('tech123')
        db.session.add(tech_user)
    
    # Create sales user
    sales_user = User.query.filter_by(username='sales').first()
    if not sales_user:
        sales_user = User(
            username='sales',
            email='sales@comphone.com',
            role=UserRole.SALES
        )
        sales_user.set_password('sales123')
        db.session.add(sales_user)
    
    db.session.commit()
    
    # Create sample customers
    if Customer.query.count() == 0:
        customers_data = [
            {'name': 'สมชาย ใจดี', 'phone': '081-234-5678', 'email': 'somchai@email.com'},
            {'name': 'สมหญิง สวยงาม', 'phone': '082-345-6789', 'email': 'somying@email.com'},
            {'name': 'นายแสง ดีใจ', 'phone': '083-456-7890', 'email': 'saeng@email.com'}
        ]
        
        for data in customers_data:
            customer = Customer(**data)
            db.session.add(customer)
    
    # Create sample products
    if Product.query.count() == 0:
        products_data = [
            {
                'name': 'iPhone 15 Pro Max',
                'sku': 'IPH15PM-256',
                'category': 'Smartphone',
                'brand': 'Apple',
                'price': 44900.0,
                'cost': 38000.0,
                'stock_quantity': 10,
                'description': 'iPhone 15 Pro Max 256GB'
            },
            {
                'name': 'Samsung Galaxy S24 Ultra',
                'sku': 'SGS24U-512',
                'category': 'Smartphone',
                'brand': 'Samsung',
                'price': 42900.0,
                'cost': 35000.0,
                'stock_quantity': 8,
                'description': 'Galaxy S24 Ultra 512GB'
            },
            {
                'name': 'หน้าจอ iPhone 15',
                'sku': 'SCR-IPH15',
                'category': 'Parts',
                'brand': 'Apple',
                'price': 4500.0,
                'cost': 3200.0,
                'stock_quantity': 15,
                'description': 'หน้าจอทดแทน iPhone 15'
            },
            {
                'name': 'แบตเตอรี่ Samsung S24',
                'sku': 'BAT-SGS24',
                'category': 'Parts',
                'brand': 'Samsung',
                'price': 1200.0,
                'cost': 800.0,
                'stock_quantity': 20,
                'description': 'แบตเตอรี่ทดแทน Galaxy S24'
            },
            {
                'name': 'เคสใส iPhone 15',
                'sku': 'CASE-IPH15-CL',
                'category': 'Accessories',
                'brand': 'Generic',
                'price': 199.0,
                'cost': 50.0,
                'stock_quantity': 50,
                'description': 'เคสใสกันกระแทก'
            }
        ]
        
        for data in products_data:
            product = Product(**data)
            product.cost_price = product.cost
            product.min_stock_level = product.low_stock_alert
            db.session.add(product)
    
    db.session.commit()
    print("✅ Sample data created successfully!")

# Initialize Database
def init_db():
    """สร้างตารางฐานข้อมูลและข้อมูลเริ่มต้น"""
    print("🗃️ Initializing database...")
    
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("✅ Database tables created successfully!")
            
            # Create sample data
            create_sample_data()
            
        except Exception as e:
            print(f"⚠️ Database initialization error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    print("🚀 Starting Comphone Service Center Application...")
    print("=" * 50)
    
    # Initialize database
    init_db()
    
    print("\n📋 Login Credentials:")
    print("👤 Admin: admin / admin123")
    print("🔧 Technician: technician / tech123") 
    print("💰 Sales: sales / sales123")
    print("=" * 50)
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)