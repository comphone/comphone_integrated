# ===== comphone/auth/__init__.py =====
from flask import Blueprint

# สร้าง blueprint สำหรับ authentication
bp = Blueprint('auth', __name__)

# Import routes หลังจากสร้าง blueprint แล้ว (เพื่อหลีกเลี่ยง circular import)
from comphone.auth import routes

# ===== comphone/core/__init__.py =====
from flask import Blueprint

# สร้าง blueprint สำหรับ core functionality
bp = Blueprint('core', __name__)

# Import routes หลังจากสร้าง blueprint แล้ว (เพื่อหลีกเลี่ยง circular import)
from comphone.core import routes