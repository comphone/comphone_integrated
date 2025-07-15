# comphone/models.py - Complete Fixed Version

from datetime import datetime, timezone
from typing import Optional, List
import sqlalchemy as sa
import sqlalchemy.orm as so
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import json
from comphone import db, login

# ===== USER MANAGEMENT =====
class User(UserMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True, unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    is_admin: so.Mapped[bool] = so.mapped_column(default=False)
    
    # เพิ่มข้อมูลสำหรับ technician
    full_name: so.Mapped[Optional[str]] = so.mapped_column(sa.String(150))
    phone: so.Mapped[Optional[str]] = so.mapped_column(sa.String(50))
    avatar_drive_id: so.Mapped[Optional[str]] = so.mapped_column(sa.String(200))
    is_technician: so.Mapped[bool] = so.mapped_column(default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if self.password_hash is None: 
            return False
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

# ===== CUSTOMER MANAGEMENT (Enhanced) =====
class Customer(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(150), index=True)
    phone: so.Mapped[Optional[str]] = so.mapped_column(sa.String(50))
    address: so.Mapped[Optional[str]] = so.mapped_column(sa.String(500))
    
    # เพิ่มจาก LINE Tasks Auto
    organization: so.Mapped[Optional[str]] = so.mapped_column(sa.String(200))
    line_user_id: so.Mapped[Optional[str]] = so.mapped_column(sa.String(100), unique=True)
    map_url: so.Mapped[Optional[str]] = so.mapped_column(sa.String(500))
    created_at: so.Mapped[datetime] = so.mapped_column(default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    service_jobs: so.WriteOnlyMapped['ServiceJob'] = so.relationship(back_populates='customer')
    sales: so.WriteOnlyMapped['Sale'] = so.relationship(back_populates='customer')
    tasks: so.WriteOnlyMapped['Task'] = so.relationship(back_populates='customer')

    def __repr__(self):
        return f'<Customer {self.name}>'

# ===== TASK MANAGEMENT (ใหม่ - จาก LINE Tasks Auto) =====
class Task(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    google_task_id: so.Mapped[Optional[str]] = so.mapped_column(sa.String(200), unique=True, index=True)
    title: so.Mapped[str] = so.mapped_column(sa.String(500))
    description: so.Mapped[Optional[str]] = so.mapped_column(sa.Text)
    status: so.Mapped[str] = so.mapped_column(sa.String(50), default='needsAction', index=True)
    
    # Dates
    due_date: so.Mapped[Optional[datetime]]
    created_at: so.Mapped[datetime] = so.mapped_column(default=lambda: datetime.now(timezone.utc), index=True)
    completed_at: so.Mapped[Optional[datetime]]
    
    # Foreign Keys
    customer_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('customer.id'), index=True)
    
    # Relationships
    customer: so.Mapped[Optional['Customer']] = so.relationship(back_populates='tasks')
    reports: so.Mapped[List['TaskReport']] = so.relationship(back_populates='task', cascade="all, delete-orphan")
    attachments: so.Mapped[List['TaskAttachment']] = so.relationship(back_populates='task', cascade="all, delete-orphan")
    feedback: so.Mapped[Optional['CustomerFeedback']] = so.relationship(back_populates='task', uselist=False)

    @property
    def is_overdue(self):
        if self.status != 'needsAction' or not self.due_date:
            return False
        return datetime.now(timezone.utc) > self.due_date

    @property
    def latest_report(self):
        if not self.reports:
            return None
        return max(self.reports, key=lambda r: r.report_date)

    def __repr__(self):
        return f'<Task {self.title}>'

class TaskReport(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    task_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('task.id'), index=True)
    report_date: so.Mapped[datetime] = so.mapped_column(default=lambda: datetime.now(timezone.utc), index=True)
    report_type: so.Mapped[str] = so.mapped_column(sa.String(50), default='report')  # report, reschedule
    
    # Content
    work_summary: so.Mapped[str] = so.mapped_column(sa.Text)
    technicians_json: so.Mapped[Optional[str]] = so.mapped_column(sa.Text)  # JSON array of technician names
    equipment_used_json: so.Mapped[Optional[str]] = so.mapped_column(sa.Text)  # JSON array of equipment
    
    # For reschedule reports
    reschedule_reason: so.Mapped[Optional[str]] = so.mapped_column(sa.Text)
    new_due_date: so.Mapped[Optional[datetime]]
    
    # Relationships
    task: so.Mapped[Task] = so.relationship(back_populates='reports')
    
    @property
    def technicians(self):
        if self.technicians_json:
            try:
                return json.loads(self.technicians_json)
            except json.JSONDecodeError:
                return []
        return []
    
    @technicians.setter
    def technicians(self, value):
        self.technicians_json = json.dumps(value) if value else None
    
    @property
    def equipment_used(self):
        if self.equipment_used_json:
            try:
                return json.loads(self.equipment_used_json)
            except json.JSONDecodeError:
                return []
        return []
    
    @equipment_used.setter
    def equipment_used(self, value):
        self.equipment_used_json = json.dumps(value) if value else None

class TaskAttachment(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    task_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('task.id'), index=True)
    google_drive_id: so.Mapped[str] = so.mapped_column(sa.String(200))
    filename: so.Mapped[str] = so.mapped_column(sa.String(500))
    file_url: so.Mapped[Optional[str]] = so.mapped_column(sa.String(1000))
    upload_date: so.Mapped[datetime] = so.mapped_column(default=lambda: datetime.now(timezone.utc))
    
    # เชื่อมกับ report ไหน (อาจจะไม่มีถ้าเป็นไฟล์จากการสร้าง task)
    report_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('task_report.id'))
    
    # Relationships
    task: so.Mapped[Task] = so.relationship(back_populates='attachments')

class CustomerFeedback(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    task_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('task.id'), unique=True, index=True)
    feedback_date: so.Mapped[Optional[datetime]]
    feedback_type: so.Mapped[Optional[str]] = so.mapped_column(sa.String(50))  # ok, problem_reported
    problem_description: so.Mapped[Optional[str]] = so.mapped_column(sa.Text)
    follow_up_sent_date: so.Mapped[Optional[datetime]]
    
    # Relationships  
    task: so.Mapped[Task] = so.relationship(back_populates='feedback')

# ===== PRODUCT & INVENTORY (เดิม) =====
class Product(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(150), index=True, unique=True)
    description: so.Mapped[Optional[str]] = so.mapped_column(sa.String(255))
    cost_price: so.Mapped[float] = so.mapped_column(sa.Float, default=0.0)
    selling_price: so.Mapped[float] = so.mapped_column(sa.Float, default=0.0)
    quantity: so.Mapped[int] = so.mapped_column(default=0)
    
    # เพิ่มข้อมูลสำหรับ equipment catalog (จาก LINE Tasks Auto)
    unit: so.Mapped[Optional[str]] = so.mapped_column(sa.String(50))
    is_equipment: so.Mapped[bool] = so.mapped_column(default=False)  # แยกสินค้าขายกับอุปกรณ์ซ่อม

    def __repr__(self):
        return f'<Product {self.name}>'

class StockMovement(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    product_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('product.id'), index=True)
    change: so.Mapped[int]  # +/- amount
    reason: so.Mapped[str] = so.mapped_column(sa.String(50))  # sale, purchase, adjustment, service_use
    timestamp: so.Mapped[datetime] = so.mapped_column(default=lambda: datetime.now(timezone.utc))
    related_id: so.Mapped[Optional[int]] = so.mapped_column()  # sale_id, service_job_id, etc.
    notes: so.Mapped[Optional[str]] = so.mapped_column(sa.String(255))

# ===== SALES (เดิม) =====
class Sale(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    timestamp: so.Mapped[datetime] = so.mapped_column(default=lambda: datetime.now(timezone.utc))
    total_amount: so.Mapped[float] = so.mapped_column(sa.Float)
    customer_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('customer.id'))
    
    # Relationships
    items: so.Mapped[List['SaleItem']] = so.relationship(back_populates='sale', cascade="all, delete-orphan", lazy='selectin')
    customer: so.Mapped[Optional['Customer']] = so.relationship(back_populates='sales')

class SaleItem(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    sale_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('sale.id'), index=True)
    product_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('product.id'), index=True)
    quantity: so.Mapped[int]
    price_per_item: so.Mapped[float] = so.mapped_column(sa.Float)
    
    # Relationships
    sale: so.Mapped[Sale] = so.relationship(back_populates='items')
    product: so.Mapped[Product] = so.relationship()

# ===== SERVICE JOBS (ปรับปรุง) =====
class ServiceJob(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    customer_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('customer.id'), index=True)
    description: so.Mapped[str] = so.mapped_column(sa.String(500))
    status: so.Mapped[str] = so.mapped_column(sa.String(50), default='รอดำเนินการ')
    created_at: so.Mapped[datetime] = so.mapped_column(default=lambda: datetime.now(timezone.utc))
    
    # เชื่อมกับ Task (จาก LINE Tasks Auto)
    task_id: so.Mapped[Optional[int]] = so.mapped_column(sa.ForeignKey('task.id'))
    
    # Relationships
    customer: so.Mapped[Customer] = so.relationship(back_populates='service_jobs')
    parts_used: so.Mapped[List['ServicePartUsage']] = so.relationship(back_populates='service_job', cascade="all, delete-orphan")

class ServicePartUsage(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    service_job_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('service_job.id'), index=True)
    product_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('product.id'), index=True)
    quantity_used: so.Mapped[int]
    
    # Relationships
    service_job: so.Mapped[ServiceJob] = so.relationship(back_populates='parts_used')
    product: so.Mapped[Product] = so.relationship()

# ===== SYSTEM SETTINGS (ใหม่) =====
class Setting(db.Model):
    """ตารางสำหรับเก็บ app settings (แทนการใช้ JSON file)"""
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    key: so.Mapped[str] = so.mapped_column(sa.String(100), unique=True, index=True)
    value_json: so.Mapped[Optional[str]] = so.mapped_column(sa.Text)
    updated_at: so.Mapped[datetime] = so.mapped_column(default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    @property
    def value(self):
        if self.value_json:
            try:
                return json.loads(self.value_json)
            except json.JSONDecodeError:
                return None
        return None
    
    @value.setter
    def value(self, data):
        self.value_json = json.dumps(data) if data is not None else None

    @classmethod
    def get_setting(cls, key, default=None):
        setting = db.session.scalar(sa.select(cls).where(cls.key == key))
        return setting.value if setting else default
    
    @classmethod
    def set_setting(cls, key, value):
        setting = db.session.scalar(sa.select(cls).where(cls.key == key))
        if setting:
            setting.value = value
        else:
            setting = cls(key=key, value=value)
            db.session.add(setting)
        db.session.commit()
        return setting

# ===== FLASK-LOGIN USER LOADER =====
@login.user_loader
def load_user(id):
    """Load user for Flask-Login"""
    return db.session.get(User, int(id))