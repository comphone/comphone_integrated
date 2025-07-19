#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Custom Decorators - Role-based access control and utility decorators
"""

from functools import wraps
from flask import jsonify, redirect, url_for, flash, request, current_app, abort
from flask_login import current_user
from models import UserRole

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        if not current_user.is_admin:
            flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'error')
            return redirect(url_for('main.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

def manager_required(f):
    """Decorator to require manager role or higher"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        if not current_user.is_manager:
            flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'error')
            return redirect(url_for('main.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

def technician_required(f):
    """Decorator to require technician role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        if not current_user.is_technician and not current_user.is_admin:
            flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'error')
            return redirect(url_for('main.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

def sales_required(f):
    """Decorator to require sales role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        if (current_user.role != UserRole.SALES and 
            not current_user.is_admin and 
            not current_user.is_manager):
            flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'error')
            return redirect(url_for('main.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    """Decorator to require specific roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            if current_user.role not in roles and not current_user.is_admin:
                flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้', 'error')
                return redirect(url_for('main.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def api_key_required(f):
    """Decorator to require API key for API endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_app.config.get('API_KEY_REQUIRED', False):
            return f(*args, **kwargs)
        
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'API key required'}), 401
        
        # In a real application, you would validate the API key against a database
        valid_api_key = current_app.config.get('API_KEY')
        if api_key != valid_api_key:
            return jsonify({'error': 'Invalid API key'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def json_required(f):
    """Decorator to require JSON content type"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        return f(*args, **kwargs)
    return decorated_function

def ajax_required(f):
    """Decorator to require AJAX requests"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_xhr:
            return jsonify({'error': 'This endpoint requires AJAX'}), 400
        return f(*args, **kwargs)
    return decorated_function

def rate_limited(max_per_minute=60):
    """Decorator for rate limiting"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Simple rate limiting implementation
            # In production, you would use Redis or similar
            from flask_limiter import Limiter
            from flask_limiter.util import get_remote_address
            
            limiter = Limiter(
                key_func=get_remote_address,
                default_limits=[f"{max_per_minute} per minute"]
            )
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_activity(action, entity_type=None):
    """Decorator to automatically log user activity"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from models import log_activity as log_to_db
            
            result = f(*args, **kwargs)
            
            # Log the activity after successful execution
            if current_user.is_authenticated:
                entity_id = None
                
                # Try to extract entity_id from kwargs or args
                if 'id' in kwargs:
                    entity_id = kwargs['id']
                elif len(args) > 0:
                    entity_id = args[0]
                
                log_to_db(
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    user_id=current_user.id,
                    description=f"User {current_user.username} performed {action}",
                    user_ip=request.environ.get('REMOTE_ADDR'),
                    user_agent=request.headers.get('User-Agent')
                )
            
            return result
        return decorated_function
    return decorator

def validate_form(form_class):
    """Decorator to validate form data"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            form = form_class()
            
            if request.method == 'POST' and not form.validate():
                # Handle validation errors
                if request.is_json:
                    return jsonify({
                        'success': False,
                        'errors': form.errors
                    }), 400
                else:
                    for field, errors in form.errors.items():
                        for error in errors:
                            flash(f'{field}: {error}', 'error')
                    return redirect(request.url)
            
            return f(form, *args, **kwargs)
        return decorated_function
    return decorator

def cache_response(timeout=300):
    """Decorator to cache response for specified time"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Simple caching implementation
            # In production, you would use Redis or similar
            cache_key = f"{request.endpoint}:{request.args}"
            
            # Check cache (pseudo-code)
            # cached_response = cache.get(cache_key)
            # if cached_response:
            #     return cached_response
            
            result = f(*args, **kwargs)
            
            # Store in cache (pseudo-code)
            # cache.set(cache_key, result, timeout=timeout)
            
            return result
        return decorated_function
    return decorator

def require_fresh_login(f):
    """Decorator to require fresh login for sensitive operations"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        # Check if login is fresh (within last 30 minutes)
        from datetime import datetime, timedelta
        
        if (current_user.last_login and 
            current_user.last_login < datetime.now() - timedelta(minutes=30)):
            flash('กรุณาเข้าสู่ระบบใหม่เพื่อดำเนินการต่อ', 'warning')
            return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    return decorated_function

def maintenance_mode(f):
    """Decorator to show maintenance mode"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_app.config.get('MAINTENANCE_MODE', False):
            if not current_user.is_authenticated or not current_user.is_admin:
                return render_template('maintenance.html'), 503
        
        return f(*args, **kwargs)
    return decorated_function

def feature_flag(flag_name):
    """Decorator to check feature flags"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_app.config.get(f'FEATURE_{flag_name.upper()}', False):
                abort(404)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def permission_required(permission):
    """Decorator to check specific permissions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            if not current_user.can_access(permission):
                flash('คุณไม่มีสิทธิ์เข้าถึงฟังก์ชันนี้', 'error')
                return redirect(url_for('main.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_ownership(model_class, id_field='id', owner_field='user_id'):
    """Decorator to validate resource ownership"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            # Get the resource ID from kwargs
            resource_id = kwargs.get(id_field)
            if not resource_id:
                abort(400)
            
            # Check ownership
            resource = model_class.query.get_or_404(resource_id)
            owner_id = getattr(resource, owner_field)
            
            if owner_id != current_user.id and not current_user.is_admin:
                flash('คุณไม่มีสิทธิ์เข้าถึงข้อมูลนี้', 'error')
                return redirect(url_for('main.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def async_task(f):
    """Decorator for async task processing"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # In production, you would use Celery or similar
        # For now, just execute normally
        try:
            result = f(*args, **kwargs)
            return result
        except Exception as e:
            current_app.logger.error(f"Async task error: {e}")
            raise
    return decorated_function

def handle_exceptions(f):
    """Decorator to handle exceptions gracefully"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            current_app.logger.error(f"Exception in {f.__name__}: {e}")
            
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': 'เกิดข้อผิดพลาดในระบบ'
                }), 500
            else:
                flash('เกิดข้อผิดพลาดในระบบ กรุณาลองใหม่อีกครั้ง', 'error')
                return redirect(request.referrer or url_for('main.dashboard'))
    return decorated_function

def timing_decorator(f):
    """Decorator to measure execution time"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        import time
        start_time = time.time()
        
        result = f(*args, **kwargs)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        current_app.logger.info(f"Function {f.__name__} executed in {execution_time:.4f} seconds")
        
        return result
    return decorated_function

def validate_json_keys(required_keys):
    """Decorator to validate required JSON keys"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({'error': 'Content-Type must be application/json'}), 400
            
            data = request.get_json()
            missing_keys = [key for key in required_keys if key not in data]
            
            if missing_keys:
                return jsonify({
                    'error': f'Missing required keys: {", ".join(missing_keys)}'
                }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def cors_enabled(f):
    """Decorator to enable CORS"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = f(*args, **kwargs)
        
        if hasattr(response, 'headers'):
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        return response
    return decorated_function

def require_https(f):
    """Decorator to require HTTPS"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_secure and not current_app.debug:
            return redirect(request.url.replace('http://', 'https://'))
        return f(*args, **kwargs)
    return decorated_function

def gzip_response(f):
    """Decorator to compress response with gzip"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = f(*args, **kwargs)
        
        if (hasattr(response, 'headers') and 
            'gzip' in request.headers.get('Accept-Encoding', '')):
            import gzip
            import io
            
            if hasattr(response, 'data'):
                compressed_data = gzip.compress(response.data)
                response.data = compressed_data
                response.headers['Content-Encoding'] = 'gzip'
                response.headers['Content-Length'] = len(compressed_data)
        
        return response
    return decorated_function

def audit_log(action_type):
    """Decorator to create audit log entries"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from models import log_activity
            
            start_time = datetime.now()
            
            try:
                result = f(*args, **kwargs)
                
                # Log successful action
                if current_user.is_authenticated:
                    log_activity(
                        action=action_type,
                        user_id=current_user.id,
                        description=f"Successfully executed {action_type}",
                        user_ip=request.environ.get('REMOTE_ADDR'),
                        user_agent=request.headers.get('User-Agent')
                    )
                
                return result
                
            except Exception as e:
                # Log failed action
                if current_user.is_authenticated:
                    log_activity(
                        action=f"{action_type}_failed",
                        user_id=current_user.id,
                        description=f"Failed to execute {action_type}: {str(e)}",
                        user_ip=request.environ.get('REMOTE_ADDR'),
                        user_agent=request.headers.get('User-Agent')
                    )
                
                raise
        return decorated_function
    return decorator

def security_headers(f):
    """Decorator to add security headers"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = f(*args, **kwargs)
        
        if hasattr(response, 'headers'):
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response
    return decorated_function

def require_2fa(f):
    """Decorator to require two-factor authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        # Check if 2FA is enabled for this user
        if hasattr(current_user, 'two_factor_enabled') and current_user.two_factor_enabled:
            if not session.get('2fa_verified'):
                flash('กรุณายืนยันตัวตนด้วย 2FA', 'warning')
                return redirect(url_for('auth.verify_2fa'))
        
        return f(*args, **kwargs)
    return decorated_function

# Export all decorators
__all__ = [
    'admin_required', 'manager_required', 'technician_required', 'sales_required',
    'role_required', 'api_key_required', 'json_required', 'ajax_required',
    'rate_limited', 'log_activity', 'validate_form', 'cache_response',
    'require_fresh_login', 'maintenance_mode', 'feature_flag', 'permission_required',
    'validate_ownership', 'async_task', 'handle_exceptions', 'timing_decorator',
    'validate_json_keys', 'cors_enabled', 'require_https', 'gzip_response',
    'audit_log', 'security_headers', 'require_2fa'
]