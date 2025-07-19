#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helper Functions - Utility functions for the application
"""

import os
import uuid
import hashlib
from datetime import datetime, timezone
from functools import wraps
from flask import current_app, request, jsonify
from flask_login import current_user
from decimal import Decimal
import re

def generate_receipt_number():
    """Generate unique receipt number"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_part = str(uuid.uuid4().hex[:6]).upper()
    return f"RCP{timestamp}{random_part}"

def generate_job_number():
    """Generate unique job number"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_part = str(uuid.uuid4().hex[:4]).upper()
    return f"JOB{timestamp}{random_part}"

def generate_task_number():
    """Generate unique task number"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_part = str(uuid.uuid4().hex[:4]).upper()
    return f"TSK{timestamp}{random_part}"

def generate_customer_code():
    """Generate unique customer code"""
    timestamp = datetime.now().strftime('%Y%m%d')
    random_part = str(uuid.uuid4().hex[:6]).upper()
    return f"CUS{timestamp}{random_part}"

def format_currency(amount, currency_symbol='฿'):
    """Format currency display"""
    if amount is None:
        return f"{currency_symbol}0.00"
    
    if isinstance(amount, str):
        try:
            amount = float(amount)
        except ValueError:
            return f"{currency_symbol}0.00"
    
    return f"{currency_symbol}{amount:,.2f}"

def format_percentage(value, decimal_places=2):
    """Format percentage display"""
    if value is None:
        return "0.00%"
    
    try:
        value = float(value)
        return f"{value:.{decimal_places}f}%"
    except (ValueError, TypeError):
        return "0.00%"

def calculate_tax(amount, tax_rate=7.0):
    """Calculate tax amount"""
    if amount is None or tax_rate is None:
        return 0.0
    
    try:
        amount = float(amount)
        tax_rate = float(tax_rate)
        return amount * (tax_rate / 100)
    except (ValueError, TypeError):
        return 0.0

def calculate_discount(amount, discount_rate=0.0, discount_amount=0.0):
    """Calculate discount amount"""
    if amount is None:
        return 0.0
    
    try:
        amount = float(amount)
        discount_rate = float(discount_rate or 0)
        discount_amount = float(discount_amount or 0)
        
        # If discount_amount is specified, use it
        if discount_amount > 0:
            return min(discount_amount, amount)
        
        # Otherwise use percentage discount
        return amount * (discount_rate / 100)
    except (ValueError, TypeError):
        return 0.0

def validate_email(email):
    """Validate email address"""
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    """Validate Thai phone number"""
    if not phone:
        return False
    
    # Remove common separators
    phone = re.sub(r'[-\s\(\)]', '', phone)
    
    # Thai phone number patterns
    patterns = [
        r'^(\+66|66|0)[2-9]\d{8}$',  # Mobile and landline
        r'^(\+66|66|0)[8-9]\d{8}$',  # Mobile only
    ]
    
    for pattern in patterns:
        if re.match(pattern, phone):
            return True
    
    return False

def sanitize_filename(filename):
    """Sanitize filename for safe storage"""
    # Remove path components
    filename = os.path.basename(filename)
    
    # Replace dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    return filename

def get_file_hash(file_path):
    """Get MD5 hash of file"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except IOError:
        return None

def allowed_file(filename, allowed_extensions=None):
    """Check if file extension is allowed"""
    if allowed_extensions is None:
        allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', set())
    
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def get_file_size_mb(file_path):
    """Get file size in MB"""
    try:
        size_bytes = os.path.getsize(file_path)
        return round(size_bytes / (1024 * 1024), 2)
    except OSError:
        return 0

def truncate_text(text, max_length=100, suffix='...'):
    """Truncate text to specified length"""
    if not text:
        return ''
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def get_time_ago(date):
    """Get human-readable time ago"""
    if not date:
        return 'ไม่ระบุ'
    
    now = datetime.now(timezone.utc)
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    
    diff = now - date
    
    if diff.days > 365:
        years = diff.days // 365
        return f'{years} ปีที่แล้ว'
    elif diff.days > 30:
        months = diff.days // 30
        return f'{months} เดือนที่แล้ว'
    elif diff.days > 0:
        return f'{diff.days} วันที่แล้ว'
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f'{hours} ชั่วโมงที่แล้ว'
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f'{minutes} นาทีที่แล้ว'
    else:
        return 'เมื่อสักครู่'

def paginate_query(query, page=1, per_page=20, error_out=False):
    """Paginate SQLAlchemy query"""
    return query.paginate(
        page=page,
        per_page=per_page,
        error_out=error_out
    )

def get_or_404(model, id_value, error_message=None):
    """Get model instance or return 404"""
    instance = model.query.get(id_value)
    if instance is None:
        from flask import abort
        abort(404, error_message or f'{model.__name__} not found')
    return instance

def flash_form_errors(form):
    """Flash form validation errors"""
    from flask import flash
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'{field}: {error}', 'error')

def get_enum_choices(enum_class):
    """Get choices for enum in forms"""
    return [(item.value, item.value.replace('_', ' ').title()) for item in enum_class]

def calculate_business_days(start_date, end_date):
    """Calculate business days between two dates"""
    from datetime import timedelta
    
    if start_date > end_date:
        return 0
    
    days = 0
    current_date = start_date
    
    while current_date <= end_date:
        # Monday = 0, Sunday = 6
        if current_date.weekday() < 5:  # Monday to Friday
            days += 1
        current_date += timedelta(days=1)
    
    return days

def is_business_day(date):
    """Check if date is a business day"""
    return date.weekday() < 5  # Monday to Friday

def next_business_day(date):
    """Get next business day"""
    from datetime import timedelta
    
    next_day = date + timedelta(days=1)
    while not is_business_day(next_day):
        next_day += timedelta(days=1)
    
    return next_day

def generate_barcode_data(text):
    """Generate barcode data for display"""
    import base64
    import io
    
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(text)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_str = base64.b64encode(img_buffer.getvalue()).decode()
        
        return f'data:image/png;base64,{img_str}'
    except ImportError:
        return None

def clean_phone_number(phone):
    """Clean and format phone number"""
    if not phone:
        return ''
    
    # Remove all non-digit characters
    phone = re.sub(r'\D', '', phone)
    
    # Handle different formats
    if phone.startswith('66'):
        phone = '0' + phone[2:]
    elif phone.startswith('+66'):
        phone = '0' + phone[3:]
    elif len(phone) == 9:
        phone = '0' + phone
    
    # Format as 0X-XXXX-XXXX
    if len(phone) == 10:
        return f"{phone[:2]}-{phone[2:6]}-{phone[6:]}"
    
    return phone

def generate_secure_token(length=32):
    """Generate secure random token"""
    return os.urandom(length).hex()

def get_client_ip():
    """Get client IP address"""
    return request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)

def log_user_activity(action, description=None, entity_type=None, entity_id=None):
    """Log user activity"""
    from models import log_activity
    
    if current_user.is_authenticated:
        log_activity(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=current_user.id,
            description=description,
            user_ip=get_client_ip(),
            user_agent=request.headers.get('User-Agent')
        )

def require_ajax(f):
    """Decorator to require AJAX requests"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_xhr:
            return jsonify({'error': 'This endpoint requires AJAX'}), 400
        return f(*args, **kwargs)
    return decorated_function

def json_response(data=None, message=None, success=True, status_code=200):
    """Standardized JSON response"""
    response_data = {
        'success': success,
        'message': message,
        'data': data
    }
    
    return jsonify(response_data), status_code

def parse_date_range(date_string):
    """Parse date range string"""
    if not date_string:
        return None, None
    
    try:
        if ' - ' in date_string:
            start_str, end_str = date_string.split(' - ')
            start_date = datetime.strptime(start_str.strip(), '%Y-%m-%d')
            end_date = datetime.strptime(end_str.strip(), '%Y-%m-%d')
            return start_date, end_date
        else:
            date = datetime.strptime(date_string.strip(), '%Y-%m-%d')
            return date, date
    except ValueError:
        return None, None

def format_thai_date(date, include_time=False):
    """Format date in Thai format"""
    if not date:
        return ''
    
    thai_months = [
        'มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน',
        'พฤษภาคม', 'มิถุนายน', 'กรกฎาคม', 'สิงหาคม',
        'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม'
    ]
    
    day = date.day
    month = thai_months[date.month - 1]
    year = date.year + 543  # Convert to Buddhist Era
    
    if include_time:
        return f"{day} {month} {year} {date.strftime('%H:%M')}"
    else:
        return f"{day} {month} {year}"

def get_business_settings():
    """Get business settings as dict"""
    from models import get_setting
    
    return {
        'name': get_setting('business_name', 'Comphone Service Center'),
        'phone': get_setting('business_phone', '02-123-4567'),
        'email': get_setting('business_email', 'info@comphone.com'),
        'address': get_setting('business_address', 'Bangkok, Thailand'),
        'tax_rate': get_setting('default_tax_rate', 7.0),
        'currency': get_setting('currency_code', 'THB'),
        'currency_symbol': get_setting('currency_symbol', '฿')
    }

def backup_database():
    """Create database backup"""
    import shutil
    from pathlib import Path
    
    try:
        # Get database path
        db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI')
        if not db_uri.startswith('sqlite:'):
            raise ValueError("Only SQLite databases are supported for backup")
        
        db_path = db_uri.replace('sqlite:///', '')
        
        # Create backup filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"backup_{timestamp}.db"
        
        # Create backup directory
        backup_dir = Path(current_app.config.get('BACKUP_LOCATION', 'backups'))
        backup_dir.mkdir(exist_ok=True)
        
        backup_path = backup_dir / backup_filename
        
        # Copy database file
        shutil.copy2(db_path, backup_path)
        
        return str(backup_path)
    except Exception as e:
        current_app.logger.error(f"Backup error: {e}")
        return None

# Template functions
def register_template_functions(app):
    """Register template functions"""
    app.jinja_env.globals.update({
        'format_currency': format_currency,
        'format_percentage': format_percentage,
        'truncate_text': truncate_text,
        'get_time_ago': get_time_ago,
        'format_thai_date': format_thai_date,
        'clean_phone_number': clean_phone_number,
        'get_business_settings': get_business_settings
    })

# Export all functions
__all__ = [
    'generate_receipt_number', 'generate_job_number', 'generate_task_number',
    'generate_customer_code', 'format_currency', 'format_percentage',
    'calculate_tax', 'calculate_discount', 'validate_email', 'validate_phone',
    'sanitize_filename', 'get_file_hash', 'allowed_file', 'get_file_size_mb',
    'truncate_text', 'get_time_ago', 'paginate_query', 'get_or_404',
    'flash_form_errors', 'get_enum_choices', 'calculate_business_days',
    'is_business_day', 'next_business_day', 'generate_barcode_data',
    'clean_phone_number', 'generate_secure_token', 'get_client_ip',
    'log_user_activity', 'require_ajax', 'json_response', 'parse_date_range',
    'format_thai_date', 'get_business_settings', 'backup_database',
    'register_template_functions'
]