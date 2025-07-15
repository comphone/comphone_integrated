# C:/.../comphone_integrated/utils/decorators.py

from functools import wraps
from flask import abort
from flask_login import current_user

def admin_required(f):
    """
    Decorator to ensure the user is an admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

def technician_required(f):
    """
    Decorator to ensure the user is a technician or an admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not (current_user.is_technician or current_user.is_admin):
            abort(403) # Forbidden
        return f(*args, **kwargs)
    return decorated_function