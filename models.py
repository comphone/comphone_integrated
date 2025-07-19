"""
Comphone Integrated System - Fixed Database Models
แก้ไขปัญหา foreign key และ relationship ทั้งหมด
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone, timedelta
import json
import enum

# Initialize SQLAlchemy
db = SQLAlchemy()

# Enums for consistent choices
class TaskStatus(enum.Enum):
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    ON_HOLD = 'on_hold'

class TaskPriority(enum.Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    URGENT = 'urgent'

class ServiceJobStatus(enum.Enum):
    RECEIVED = 'received'
    DIAGNOSED = 'diagnosed'
    WAITING_PARTS = 'waiting_for_parts'
    IN_REPAIR = 'in_repair'
    TESTING = 'testing'
    COMPLETED = 'completed'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'

class PaymentStatus(enum.Enum):
    PENDING = 'pending'
    PARTIAL = 'partial'
    PAID = 'paid'
    REFUNDED = 'refunded'
    CANCELLED = 'cancelled'

class UserRole(enum.Enum):
    ADMIN = 'admin'
    MANAGER = 'manager'
    TECHNICIAN = 'technician'
    SALES = 'sales'
    SUPPORT = 'support'

# แก้ไข Association table ให้ระบุ foreign_keys ชัดเจน
task_assignees = db.Table('task_assignees',
    db.Column('task_id', db.Integer, db.ForeignKey('task.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('assigned_at', db.DateTime, default=lambda: datetime.now(timezone.utc))
)

class User(UserMixin, db.Model):
    """Enhanced User model with role-based access and preferences"""
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Personal Information
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))
    avatar_url = db.Column(db.String(255))
    
    # Role and Permissions
    role = db.Column(db.Enum(UserRole), default=UserRole.SUPPORT, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_technician = db.Column(db.Boolean, default=False)
    department = db.Column(db.String(50))
    
    # Technician-specific fields
    skill_set = db.Column(db.Text)  # JSON stored as text
    hourly_rate = db.Column(db.Float)
    certification_level = db.Column(db.String(20))
    
    # LINE Integration
    line_user_id = db.Column(db.String(100), unique=True)
    line_display_name = db.Column(db.String(100))
    line_notify_enabled = db.Column(db.Boolean, default=True)
    
    # Google Integration
    google_email = db.Column(db.String(120))
    google_calendar_id = db.Column(db.String(255))
    google_sync_enabled = db.Column(db.Boolean, default=False)
    
    # User Preferences
    timezone = db.Column(db.String(50), default='Asia/Bangkok')
    language = db.Column(db.String(10), default='th')
    theme_preference = db.Column(db.String(20), default='light')
    notification_preferences = db.Column(db.Text)  # JSON
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)
    last_activity = db.Column(db.DateTime)
    
    def set_password(self, password):
        """Set user's password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches user's password"""
        return check_password_hash(self.password_hash, password)

    def get_full_name(self):
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.username

    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.now(timezone.utc)
        db.session.commit()

    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone': self.phone,
            'role': self.role.value if self.role else None,
            'active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

    @property
    def full_name(self):
        """Property to easily access the full name."""
        return self.get_full_name()

    def set_skills(self, skills_list):
        """Set technician skills as JSON"""
        self.skill_set = json.dumps(skills_list) if skills_list else None
    
    def get_skills(self):
        """Get technician skills from JSON"""
        return json.loads(self.skill_set) if self.skill_set else []
    
    def set_notification_preferences(self, preferences):
        """Set notification preferences as JSON"""
        self.notification_preferences = json.dumps(preferences)
    
    def get_notification_preferences(self):
        """Get notification preferences from JSON"""
        return json.loads(self.notification_preferences) if self.notification_preferences else {}
    
    @property
    def is_admin(self):
        """Check if user is admin"""
        return self.role == UserRole.ADMIN
    
    @property
    def is_manager(self):
        """Check if user is manager or admin"""
        return self.role in [UserRole.ADMIN, UserRole.MANAGER]
    
    def can_access(self, resource):
        """Check if user can access resource"""
        permissions = {
            UserRole.ADMIN: ['all'],
            UserRole.MANAGER: ['tasks', 'customers', 'sales', 'service_jobs', 'reports'],
            UserRole.TECHNICIAN: ['tasks', 'service_jobs', 'customers'],
            UserRole.SALES: ['customers', 'sales', 'products'],
            UserRole.SUPPORT: ['tasks', 'customers']
        }
        user_permissions = permissions.get(self.role, [])
        return 'all' in user_permissions or resource in user_permissions
    
    def __repr__(self):
        return f'<User {self.username}>'

class Customer(db.Model):
    """Enhanced Customer model with detailed information"""
    __tablename__ = 'customer'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic Information
    name = db.Column(db.String(100), nullable=False, index=True)
    customer_code = db.Column(db.String(20), unique=True, index=True)
    customer_type = db.Column(db.String(20), default='individual')  # individual, corporate
    
    # Contact Information
    phone = db.Column(db.String(20), index=True)
    email = db.Column(db.String(120), index=True)
    line_id = db.Column(db.String(100))
    
    # Address Information
    address = db.Column(db.Text)
    district = db.Column(db.String(50))
    province = db.Column(db.String(50))
    postal_code = db.Column(db.String(10))
    country = db.Column(db.String(50), default='Thailand')
    
    # Corporate Information
    company_name = db.Column(db.String(100))
    tax_id = db.Column(db.String(20))
    contact_person = db.Column(db.String(100))
    
    # Customer Status
    status = db.Column(db.String(20), default='active')
    credit_limit = db.Column(db.Float, default=0.0)
    payment_terms = db.Column(db.String(50), default='cash')
    
    # Notes and Tags
    notes = db.Column(db.Text)
    tags = db.Column(db.Text)  # JSON stored as text
    internal_notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_contact = db.Column(db.DateTime)
    
    # Foreign Keys
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # เพิ่ม property สำหรับ backward compatibility กับระบบเดิม
    @property
    def first_name(self):
        """Backward compatibility - แยกชื่อจาก name"""
        if ' ' in self.name:
            return self.name.split(' ')[0]
        return self.name
    
    @property 
    def last_name(self):
        """Backward compatibility - แยกนามสกุลจาก name"""
        if ' ' in self.name:
            parts = self.name.split(' ')
            return ' '.join(parts[1:]) if len(parts) > 1 else ''
        return ''
    
    def set_tags(self, tags_list):
        """Set customer tags as JSON"""
        self.tags = json.dumps(tags_list) if tags_list else None
    
    def get_tags(self):
        """Get customer tags from JSON"""
        return json.loads(self.tags) if self.tags else []
    
    def generate_customer_code(self):
        """Generate unique customer code"""
        if not self.customer_code:
            import random
            import string
            prefix = 'CUS'
            suffix = ''.join(random.choices(string.digits, k=6))
            self.customer_code = f"{prefix}{suffix}"
    
    def __repr__(self):
        return f'<Customer {self.name}>'

class CustomerDevice(db.Model):
    """Customer devices for tracking repair history"""
    __tablename__ = 'customer_device'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    
    # Device Information
    device_type = db.Column(db.String(50))
    brand = db.Column(db.String(50))
    model = db.Column(db.String(100))
    serial_number = db.Column(db.String(100))
    imei = db.Column(db.String(20))
    
    # Device Details
    color = db.Column(db.String(30))
    storage_capacity = db.Column(db.String(20))
    purchase_date = db.Column(db.Date)
    warranty_expiry = db.Column(db.Date)
    
    # Status
    status = db.Column(db.String(20), default='active')
    notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # เพิ่ม created_by สำหรับ compatibility
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    customer = db.relationship('Customer', backref='devices')
    creator = db.relationship('User', backref='created_devices')
    
    def __repr__(self):
        return f'<Device {self.brand} {self.model}>'

class Product(db.Model):
    """Enhanced Product model for inventory and services"""
    __tablename__ = 'product'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic Information
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text)
    sku = db.Column(db.String(50), unique=True, index=True)
    barcode = db.Column(db.String(100), unique=True, index=True)
    
    # Product Classification
    category = db.Column(db.String(50), index=True)
    subcategory = db.Column(db.String(50))
    brand = db.Column(db.String(50))
    model = db.Column(db.String(100))
    product_type = db.Column(db.String(20), default='product')
    
    # Pricing
    cost = db.Column(db.Float, default=0.0)
    price = db.Column(db.Float, nullable=False)
    wholesale_price = db.Column(db.Float)
    minimum_price = db.Column(db.Float)
    
    # Inventory
    stock_quantity = db.Column(db.Integer, default=0)
    min_stock_level = db.Column(db.Integer, default=0)
    max_stock_level = db.Column(db.Integer)
    reorder_point = db.Column(db.Integer)
    
    # Service-specific fields
    is_service = db.Column(db.Boolean, default=False)
    service_duration = db.Column(db.Integer)
    requires_technician = db.Column(db.Boolean, default=False)
    skill_requirements = db.Column(db.Text)
    
    # Product Status
    is_active = db.Column(db.Boolean, default=True)
    is_taxable = db.Column(db.Boolean, default=True)
    tax_rate = db.Column(db.Float, default=7.0)
    
    # Media
    image_url = db.Column(db.String(255))
    images = db.Column(db.Text)
    
    # Specifications
    specifications = db.Column(db.Text)
    warranty_period = db.Column(db.Integer)
    weight = db.Column(db.Float)
    dimensions = db.Column(db.String(100))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    is_service_part = db.Column(db.Boolean, default=False, nullable=False)
    
    def set_skill_requirements(self, skills_list):
        """Set required skills as JSON"""
        self.skill_requirements = json.dumps(skills_list) if skills_list else None
    
    def get_skill_requirements(self):
        """Get required skills from JSON"""
        return json.loads(self.skill_requirements) if self.skill_requirements else []
    
    def set_specifications(self, specs_dict):
        """Set specifications as JSON"""
        self.specifications = json.dumps(specs_dict) if specs_dict else None
    
    def get_specifications(self):
        """Get specifications from JSON"""
        return json.loads(self.specifications) if self.specifications else {}
    
    @property
    def is_low_stock(self):
        """Check if product is low on stock"""
        if self.min_stock_level is not None:
             return self.stock_quantity <= self.min_stock_level
        return False
    
    @property
    def profit_margin(self):
        """Calculate profit margin percentage"""
        if self.cost and self.cost > 0:
            return ((self.price - self.cost) / self.cost) * 100
        return 0
    
    def __repr__(self):
        return f'<Product {self.name}>'

class ServiceJob(db.Model):
    """Enhanced Service Job model for repair tracking"""
    __tablename__ = 'service_job'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic Information
    job_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Customer and Device
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('customer_device.id'))
    
    # Job Classification
    service_type = db.Column(db.String(50))
    category = db.Column(db.String(50))
    priority = db.Column(db.Enum(TaskPriority), default=TaskPriority.MEDIUM)
    status = db.Column(db.Enum(ServiceJobStatus), default=ServiceJobStatus.RECEIVED, index=True)
    
    # Technician Assignment
    assigned_technician = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Problem and Solution
    reported_problem = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    solution = db.Column(db.Text)
    work_performed = db.Column(db.Text)
    
    # เพิ่ม field สำหรับ backward compatibility
    problem_description = db.Column(db.Text)  # alias สำหรับ reported_problem
    
    # Parts and Labor
    parts_needed = db.Column(db.Text)
    labor_hours = db.Column(db.Float, default=0.0)
    parts_cost = db.Column(db.Float, default=0.0)
    labor_cost = db.Column(db.Float, default=0.0)
    additional_costs = db.Column(db.Float, default=0.0)
    
    # เพิ่ม field สำหรับ compatibility กับระบบเดิม
    total_cost = db.Column(db.Float, default=0.0)
    
    # Estimates and Pricing
    estimated_cost = db.Column(db.Float)
    quoted_price = db.Column(db.Float)
    final_price = db.Column(db.Float)
    customer_approved = db.Column(db.Boolean, default=False)
    approval_date = db.Column(db.DateTime)
    
    # Scheduling
    received_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    promised_date = db.Column(db.DateTime)
    completed_date = db.Column(db.DateTime)
    delivered_date = db.Column(db.DateTime)
    
    # เพิ่ม field สำหรับ compatibility
    estimated_completion = db.Column(db.Date)
    completed_at = db.Column(db.DateTime)
    
    # Quality Control
    tested = db.Column(db.Boolean, default=False)
    test_results = db.Column(db.Text)
    quality_check_passed = db.Column(db.Boolean)
    quality_notes = db.Column(db.Text)
    
    # Warranty
    warranty_period = db.Column(db.Integer, default=30)
    warranty_terms = db.Column(db.Text)
    warranty_void_date = db.Column(db.Date)
    
    # Customer Communication
    customer_notified = db.Column(db.Boolean, default=False)
    customer_satisfaction = db.Column(db.Integer)
    customer_feedback = db.Column(db.Text)
    
    # Internal Notes
    internal_notes = db.Column(db.Text)
    special_instructions = db.Column(db.Text)
    notes = db.Column(db.Text)  # alias สำหรับ internal_notes
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    customer = db.relationship('Customer', backref='service_jobs')
    device = db.relationship('CustomerDevice', backref='service_jobs')
    technician = db.relationship('User', foreign_keys=[assigned_technician], backref='assigned_service_jobs')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_service_jobs')
    
    def __init__(self, **kwargs):
        super(ServiceJob, self).__init__(**kwargs)
        if not self.job_number:
            self.job_number = self.generate_job_number()
        # Sync fields for backward compatibility
        if self.reported_problem and not self.problem_description:
            self.problem_description = self.reported_problem
        elif self.problem_description and not self.reported_problem:
            self.reported_problem = self.problem_description
    
    def generate_job_number(self):
        """Generate unique job number"""
        if not self.job_number:
            import random
            import string
            prefix = 'SRV'
            suffix = ''.join(random.choices(string.digits, k=6))
            self.job_number = f"{prefix}{suffix}"
        return self.job_number
    
    def calculate_total_cost(self):
        """Calculate total cost"""
        self.total_cost = (self.parts_cost or 0) + (self.labor_cost or 0) + (self.additional_costs or 0)
        return self.total_cost
    
    @property
    def profit_margin(self):
        """Calculate profit margin"""
        if self.final_price and self.total_cost:
            return self.final_price - self.total_cost
        return 0
    
    @property
    def is_overdue(self):
        """Check if job is overdue"""
        if self.promised_date and self.status not in [ServiceJobStatus.COMPLETED, ServiceJobStatus.DELIVERED]:
            return datetime.now(timezone.utc) > self.promised_date
        return False
    
    # เพิ่ม property สำหรับ backward compatibility กับระบบเดิม
    @property
    def technician_id(self):
        """Backward compatibility alias"""
        return self.assigned_technician
    
    @technician_id.setter
    def technician_id(self, value):
        """Backward compatibility alias"""
        self.assigned_technician = value
    
    def __repr__(self):
        return f'<ServiceJob {self.job_number}>'

class Task(db.Model):
    """Enhanced Task model with advanced tracking"""
    __tablename__ = 'task'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic Information
    title = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text)
    task_number = db.Column(db.String(20), unique=True, index=True)
    
    # Task Classification
    category = db.Column(db.String(50), index=True)
    task_type = db.Column(db.String(50))
    priority = db.Column(db.Enum(TaskPriority), default=TaskPriority.MEDIUM)
    status = db.Column(db.Enum(TaskStatus), default=TaskStatus.PENDING, index=True)
    
    # Scheduling
    due_date = db.Column(db.DateTime, index=True)
    scheduled_start = db.Column(db.DateTime)
    scheduled_end = db.Column(db.DateTime)
    actual_start = db.Column(db.DateTime)
    actual_end = db.Column(db.DateTime)
    estimated_hours = db.Column(db.Float)
    actual_hours = db.Column(db.Float)
    
    # Relationships
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), index=True)
    service_job_id = db.Column(db.Integer, db.ForeignKey('service_job.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Task Details
    location = db.Column(db.String(200))
    requirements = db.Column(db.Text)
    notes = db.Column(db.Text)
    internal_notes = db.Column(db.Text)
    
    # Progress Tracking
    completion_percentage = db.Column(db.Integer, default=0)
    checklist = db.Column(db.Text)
    
    # Google Tasks Integration
    google_task_id = db.Column(db.String(100), unique=True)
    google_tasklist_id = db.Column(db.String(100))
    last_synced = db.Column(db.DateTime)
    
    # LINE Integration
    line_notification_sent = db.Column(db.Boolean, default=False)
    reminder_sent = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime)
    
    # Self-referential relationship for subtasks
    parent_id = db.Column(db.Integer, db.ForeignKey('task.id'))
    
    # แก้ไข Relationships โดยระบุ foreign_keys ชัดเจน
    customer = db.relationship('Customer', backref='tasks')
    service_job = db.relationship('ServiceJob', backref='tasks')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_tasks')
    subtasks = db.relationship('Task', backref=db.backref('parent_task', remote_side=[id]), lazy='dynamic')
    
    # แก้ไข many-to-many relationship โดยระบุ foreign_keys
    assignees = db.relationship('User', 
                               secondary=task_assignees,
                               primaryjoin=id == task_assignees.c.task_id,
                               secondaryjoin=User.id == task_assignees.c.user_id,
                               backref=db.backref('assigned_tasks', lazy='dynamic'),
                               lazy='dynamic')
    
    def generate_task_number(self):
        """Generate unique task number"""
        if not self.task_number:
            import random
            import string
            prefix = 'TSK'
            suffix = ''.join(random.choices(string.digits, k=6))
            self.task_number = f"{prefix}{suffix}"
    
    def set_checklist(self, checklist_items):
        """Set checklist as JSON"""
        self.checklist = json.dumps(checklist_items) if checklist_items else None
    
    def get_checklist(self):
        """Get checklist from JSON"""
        return json.loads(self.checklist) if self.checklist else []
    
    @property
    def is_overdue(self):
        """Check if task is overdue"""
        if self.due_date and self.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
            return datetime.now(timezone.utc) > self.due_date
        return False
    
    @property
    def time_remaining(self):
        """Get time remaining until due date"""
        if self.due_date:
            return self.due_date - datetime.now(timezone.utc)
        return None
    
    def __repr__(self):
        return f'<Task {self.title}>'

class Sale(db.Model):
    """Enhanced Sales model with detailed tracking"""
    __tablename__ = 'sale'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Sale Information
    sale_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    sale_type = db.Column(db.String(20), default='cash')
    
    # Customer and Salesperson
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    salesperson_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Financial Information
    subtotal = db.Column(db.Float, nullable=False)
    tax_amount = db.Column(db.Float, default=0.0)
    discount_amount = db.Column(db.Float, default=0.0)
    discount_percentage = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    
    # Payment Information
    payment_method = db.Column(db.String(50))
    payment_status = db.Column(db.Enum(PaymentStatus), default=PaymentStatus.PENDING)
    paid_amount = db.Column(db.Float, default=0.0)
    payment_reference = db.Column(db.String(100))
    
    # Sale Status
    status = db.Column(db.String(20), default='completed') # completed, cancelled, refunded
    
    # Notes
    notes = db.Column(db.Text)
    internal_notes = db.Column(db.Text)
    
    # Timestamps
    sale_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    customer = db.relationship('Customer', backref='sales')
    salesperson = db.relationship('User', backref='sales')
    items = db.relationship('SaleItem', backref='sale', lazy='dynamic', cascade='all, delete-orphan')

    def __init__(self, **kwargs):
        super(Sale, self).__init__(**kwargs)
        if not self.sale_number:
            self.sale_number = self.generate_sale_number()

    def generate_sale_number(self):
        """Generate unique sale number"""
        if not self.sale_number:
            import random
            import string
            prefix = 'SAL'
            suffix = ''.join(random.choices(string.digits, k=6))
            self.sale_number = f"{prefix}{suffix}"
        return self.sale_number
    
    @property
    def outstanding_amount(self):
        """Calculate outstanding amount"""
        return self.total_amount - self.paid_amount
    
    def __repr__(self):
        return f'<Sale {self.sale_number}>'

class SaleItem(db.Model):
    """Model for items within a sale (associates Product with Sale)"""
    __tablename__ = 'sale_item'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False, index=True)
    
    # Sale details for this item
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price_per_unit = db.Column(db.Float, nullable=False)
    cost_per_unit = db.Column(db.Float)
    discount_amount = db.Column(db.Float, default=0.0)
    total_price = db.Column(db.Float, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    product = db.relationship('Product', backref='sale_items')

    def __repr__(self):
        return f'<SaleItem for Sale {self.sale_id} - Product {self.product_id}>'

class SystemSettings(db.Model):
    """System settings and configuration"""
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    data_type = db.Column(db.String(20), default='string')
    category = db.Column(db.String(50), default='general')
    description = db.Column(db.Text)
    is_public = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    def get_value(self):
        """Get typed value"""
        if self.data_type == 'integer':
            return int(self.value) if self.value else 0
        elif self.data_type == 'float':
            return float(self.value) if self.value else 0.0
        elif self.data_type == 'boolean':
            return self.value.lower() == 'true' if self.value else False
        elif self.data_type == 'json':
            return json.loads(self.value) if self.value else {}
        return self.value or ''
    
    def set_value(self, value):
        """Set typed value"""
        if self.data_type == 'json':
            self.value = json.dumps(value)
        else:
            self.value = str(value)
    
    def __repr__(self):
        return f'<Setting {self.key}>'

class ActivityLog(db.Model):
    """Activity logging for audit trail"""
    __tablename__ = 'activity_log'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Activity Information
    action = db.Column(db.String(50), nullable=False, index=True)
    entity_type = db.Column(db.String(50), index=True)
    entity_id = db.Column(db.Integer, index=True)
    
    # User Information
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user_ip = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    
    # Details
    description = db.Column(db.Text)
    old_values = db.Column(db.Text)  # JSON
    new_values = db.Column(db.Text)  # JSON
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    
    # Relationships
    user = db.relationship('User', backref='activity_logs')
    
    def __repr__(self):
        return f'<ActivityLog {self.action} on {self.entity_type}>'

class Notification(db.Model):
    """Notification system"""
    __tablename__ = 'notification'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Notification Content
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), default='info')
    category = db.Column(db.String(50), default='general')
    
    # Recipients
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    role_filter = db.Column(db.String(50))
    
    # Related Entity
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.Integer)
    
    # Delivery Channels
    web_notification = db.Column(db.Boolean, default=True)
    line_notification = db.Column(db.Boolean, default=False)
    email_notification = db.Column(db.Boolean, default=False)
    
    # Status - เพิ่ม read property ที่หายไปเพื่อแก้ไขปัญหา
    is_read = db.Column(db.Boolean, default=False)
    read = db.Column(db.Boolean, default=False)  # alias สำหรับ is_read
    read_at = db.Column(db.DateTime)
    delivered = db.Column(db.Boolean, default=False)
    delivery_attempts = db.Column(db.Integer, default=0)
    
    # Scheduling
    scheduled_for = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    recipient = db.relationship('User', backref='notifications')
    
    def __init__(self, **kwargs):
        super(Notification, self).__init__(**kwargs)
        # Sync read fields for backward compatibility
        if self.is_read and not self.read:
            self.read = self.is_read
        elif self.read and not self.is_read:
            self.is_read = self.read
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.read = True
        self.read_at = datetime.now(timezone.utc)
    
    def __repr__(self):
        return f'<Notification {self.title}>'

# Database initialization functions
def create_tables():
    """Create all database tables"""
    try:
        db.create_all()
        print("✅ Database tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

def init_default_settings():
    """Initialize default system settings"""
    try:
        if SystemSettings.query.count() == 0:
            default_settings = [
                ('business_name', 'Comphone Service Center', 'string', 'business', 'Company name'),
                ('business_phone', '02-123-4567', 'string', 'business', 'Business phone number'),
                ('business_email', 'info@comphone.com', 'string', 'business', 'Business email'),
                ('business_address', 'Bangkok, Thailand', 'string', 'business', 'Business address'),
                ('default_tax_rate', '7.0', 'float', 'finance', 'Default VAT rate (%)'),
                ('tax_enabled', 'true', 'boolean', 'finance', 'Enable tax calculations'),
                ('default_language', 'th', 'string', 'system', 'Default system language'),
                ('default_timezone', 'Asia/Bangkok', 'string', 'system', 'Default timezone'),
                ('session_timeout', '24', 'integer', 'system', 'Session timeout (hours)'),
                ('line_notifications_enabled', 'false', 'boolean', 'notifications', 'Enable LINE notifications'),
                ('email_notifications_enabled', 'false', 'boolean', 'notifications', 'Enable email notifications'),
                ('overdue_reminder_hours', '24', 'integer', 'notifications', 'Hours before due date to send reminder'),
                ('google_sync_enabled', 'false', 'boolean', 'integrations', 'Enable Google Tasks sync'),
                ('line_bot_enabled', 'false', 'boolean', 'integrations', 'Enable LINE Bot'),
                ('allow_negative_stock', 'false', 'boolean', 'pos', 'Allow selling when stock is negative'),
                ('auto_reduce_stock', 'true', 'boolean', 'pos', 'Automatically reduce stock on sale'),
                ('receipt_footer_text', 'ขอบคุณที่ใช้บริการ', 'string', 'pos', 'Text to show on receipt footer'),
                ('default_task_priority', 'medium', 'string', 'tasks', 'Default priority for new tasks'),
                ('auto_assign_tasks', 'false', 'boolean', 'tasks', 'Auto-assign tasks to available technicians'),
                ('task_reminder_enabled', 'true', 'boolean', 'tasks', 'Enable task reminders'),
            ]
            
            for key, value, data_type, category, description in default_settings:
                setting = SystemSettings(
                    key=key,
                    value=value,
                    data_type=data_type,
                    category=category,
                    description=description,
                    is_public=True
                )
                db.session.add(setting)
            
            db.session.commit()
            print("✅ Default settings created successfully!")
            
    except Exception as e:
        print(f"⚠️  Error creating default settings: {e}")
        db.session.rollback()

def create_sample_data():
    """Create sample data for testing"""
    try:
        if User.query.count() > 0:
            print("ℹ️  Sample data already exists, skipping...")
            return
        
        admin = User(
            username='admin',
            email='admin@comphone.com',
            first_name='ผู้ดูแล',
            last_name='ระบบ',
            role=UserRole.ADMIN,
            phone='02-123-4567',
            is_active=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        
        tech = User(
            username='technician',
            email='tech@comphone.com',
            first_name='ช่าง',
            last_name='เทคนิค',
            role=UserRole.TECHNICIAN,
            phone='08-1111-1111',
            is_technician=True,
            hourly_rate=200.0,
            certification_level='senior'
        )
        tech.set_password('tech123')
        tech.set_skills(['phone_repair', 'computer_repair', 'data_recovery'])
        db.session.add(tech)
        
        sales_user = User(
            username='sales',
            email='sales@comphone.com',
            first_name='พนักงาน',
            last_name='ขาย',
            role=UserRole.SALES,
            phone='08-2222-2222'
        )
        sales_user.set_password('sales123')
        db.session.add(sales_user)
        
        db.session.flush()
        
        customers_data = [
            {
                'name': 'คุณสมชาย ใจดี',
                'phone': '08-1234-5678',
                'email': 'somchai@email.com',
                'customer_type': 'individual',
                'address': '123 ถนนสุขุมวิท กรุงเทพฯ 10110',
                'created_by': admin.id
            },
            {
                'name': 'บริษัท เทคโนโลยี จำกัด',
                'phone': '02-555-6666',
                'email': 'contact@technology.co.th',
                'customer_type': 'corporate',
                'company_name': 'บริษัท เทคโนโลยี จำกัด',
                'tax_id': '0105544000123',
                'contact_person': 'คุณวิทยา',
                'address': '456 ถนนพระราม 4 กรุงเทพฯ 10500',
                'created_by': admin.id
            }
        ]
        
        customers = []
        for customer_data in customers_data:
            customer = Customer(**customer_data)
            customer.generate_customer_code()
            customers.append(customer)
            db.session.add(customer)
        
        db.session.flush()
        
        device1 = CustomerDevice(
            customer_id=customers[0].id,
            device_type='smartphone',
            brand='iPhone',
            model='iPhone 13 Pro',
            serial_number='ABC123456789',
            color='Pacific Blue',
            storage_capacity='256GB',
            created_by=admin.id
        )
        db.session.add(device1)
        
        products_data = [
            {
                'name': 'ซ่อมหน้าจอ iPhone',
                'description': 'เปลี่ยนหน้าจอ iPhone ทุกรุ่น รวมค่าแรง',
                'sku': 'SRV-IP-SCREEN',
                'price': 3500.00,
                'cost': 2000.00,
                'category': 'Phone Repair',
                'product_type': 'service',
                'is_service': True,
                'service_duration': 60,
                'requires_technician': True
            },
            {
                'name': 'แบตเตอรี่ Samsung Galaxy',
                'description': 'แบตเตอรี่ Samsung Galaxy S21/S22/S23',
                'sku': 'PRT-SAM-BAT',
                'price': 1200.00,
                'cost': 800.00,
                'category': 'Parts',
                'stock_quantity': 25,
                'min_stock_level': 5,
                'barcode': '1234567890123'
            },
            {
                'name': 'เคสป้องกัน iPhone',
                'description': 'เคสซิลิโคนป้องกัน iPhone',
                'sku': 'ACC-IP-CASE',
                'price': 590.00,
                'cost': 200.00,
                'category': 'Accessories',
                'stock_quantity': 50,
                'min_stock_level': 10,
                'barcode': '1234567890124'
            }
        ]
        
        products = []
        for product_data in products_data:
            product = Product(**product_data)
            products.append(product)
            db.session.add(product)
        
        db.session.flush()
        
        service_job = ServiceJob(
            title='ซ่อมหน้าจอ iPhone 13 Pro',
            description='หน้าจอแตก ต้องการเปลี่ยนใหม่',
            customer_id=customers[0].id,
            device_id=device1.id,
            service_type='repair',
            category='screen_repair',
            priority=TaskPriority.HIGH,
            assigned_technician=tech.id,
            created_by=admin.id,
            reported_problem='หน้าจอแตกจากการตก',
            problem_description='หน้าจอแตกจากการตก',
            estimated_cost=3500.00,
            promised_date=datetime.now(timezone.utc).replace(hour=17, minute=0, second=0),
            estimated_completion=(datetime.now(timezone.utc) + timedelta(days=1)).date()
        )
        service_job.calculate_total_cost()
        db.session.add(service_job)
        
        db.session.flush()
        
        task = Task(
            title='เปลี่ยนหน้าจอ iPhone 13 Pro',
            description='ถอดหน้าจอเก่าและติดตั้งหน้าจอใหม่',
            customer_id=customers[0].id,
            service_job_id=service_job.id,
            created_by=admin.id,
            priority=TaskPriority.HIGH,
            category='repair',
            task_type='screen_replacement',
            estimated_hours=1.5,
            due_date=datetime.now(timezone.utc).replace(hour=17, minute=0, second=0)
        )
        task.generate_task_number()
        task.assignees.append(tech)
        db.session.add(task)
        
        sale = Sale(
            customer_id=customers[0].id,
            salesperson_id=sales_user.id,
            subtotal=590.00,
            tax_amount=41.30,
            total_amount=631.30,
            payment_method='cash',
            payment_status=PaymentStatus.PAID,
            paid_amount=631.30,
            status='completed'
        )
        
        sale_item = SaleItem(
            sale=sale,
            product_id=products[2].id,
            quantity=1,
            price_per_unit=products[2].price,
            cost_per_unit=products[2].cost,
            total_price=products[2].price
        )
        
        db.session.add(sale)
        db.session.add(sale_item)
        
        # เพิ่ม Notification ตัวอย่าง
        notification = Notification(
            user_id=tech.id,
            title='งานใหม่ได้รับมอบหมาย',
            message=f'คุณได้รับมอบหมายงานซ่อม {service_job.job_number}',
            notification_type='task_assigned',
            entity_type='service_job',
            entity_id=service_job.id,
            is_read=False,
            read=False
        )
        db.session.add(notification)
        
        db.session.commit()
        print("✅ Sample data created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        db.session.rollback()
        import traceback
        traceback.print_exc()

# Helper functions
def get_setting(key, default=None):
    """Get system setting value"""
    try:
        setting = SystemSettings.query.filter_by(key=key).first()
        if setting:
            return setting.get_value()
        return default
    except:
        return default

def set_setting(key, value, user_id=None):
    """Set system setting value"""
    try:
        setting = SystemSettings.query.filter_by(key=key).first()
        if setting:
            setting.set_value(value)
            setting.updated_by = user_id
            setting.updated_at = datetime.now(timezone.utc)
        else:
            setting = SystemSettings(key=key, value=str(value), updated_by=user_id)
            db.session.add(setting)
        
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error setting {key}: {e}")
        return False

def log_activity(action, entity_type=None, entity_id=None, user_id=None, 
                description=None, old_values=None, new_values=None,
                user_ip=None, user_agent=None):
    """Log user activity"""
    try:
        log = ActivityLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            description=description,
            old_values=json.dumps(old_values) if old_values else None,
            new_values=json.dumps(new_values) if new_values else None,
            user_ip=user_ip,
            user_agent=user_agent
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Error logging activity: {e}")
        db.session.rollback()

# Helper function สำหรับ template
def moment():
    """Helper function สำหรับ moment.js และ template"""
    return datetime

# Export all models and functions
__all__ = [
    'db', 'User', 'Customer', 'CustomerDevice', 'Product', 'Task', 
    'ServiceJob', 'Sale', 'SaleItem', 
    'SystemSettings', 'ActivityLog', 'Notification', 'TaskStatus', 
    'TaskPriority', 'ServiceJobStatus', 'PaymentStatus', 'UserRole',
    'create_tables', 'init_default_settings', 'create_sample_data',
    'get_setting', 'set_setting', 'log_activity', 'moment'
]