#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quickstart Script - Quick setup for Comphone Integrated System
"""

import os
import sys
import shutil
from pathlib import Path

def create_directories():
    """Create necessary directories"""
    directories = [
        'static', 'static/css', 'static/js', 'static/images',
        'templates', 'templates/auth', 'templates/main', 'templates/pos',
        'templates/service', 'templates/tasks', 'templates/customers',
        'templates/admin', 'templates/shared', 'templates/errors',
        'uploads', 'instance', 'logs', 'credentials', 'backups',
        'blueprints'
    ]
    
    print("📁 Creating directories...")
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"   ✅ {directory}")

def create_missing_files():
    """Create missing blueprint files"""
    print("📄 Creating missing blueprint files...")
    
    # Create __init__.py files
    init_files = [
        'blueprints/__init__.py',
        'utils/__init__.py',
        'templates/__init__.py'
    ]
    
    for init_file in init_files:
        Path(init_file).parent.mkdir(parents=True, exist_ok=True)
        if not Path(init_file).exists():
            Path(init_file).write_text('# Package initialization\n')
            print(f"   ✅ {init_file}")

def fix_imports():
    """Fix import issues in existing files"""
    print("🔧 Fixing import issues...")
    
    # Fix tasks.py import
    tasks_file = Path('blueprints/tasks.py')
    if tasks_file.exists():
        content = tasks_file.read_text(encoding='utf-8')
        
        # Make sure it exports tasks_bp
        if 'tasks_bp =' not in content:
            # Add the proper blueprint export
            content = content.replace(
                "tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')",
                "tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')"
            )
            
            if 'tasks_bp = Blueprint' not in content:
                # Add blueprint definition if missing
                content = content.replace(
                    "from flask import (",
                    "from flask import Blueprint, " + "(" if "(" in content else ""
                )
                
                # Add blueprint definition after imports
                if 'tasks_bp = Blueprint' not in content:
                    import_section = content.split('\n\n')[0]  # First section should be imports
                    rest = '\n\n'.join(content.split('\n\n')[1:])
                    content = import_section + '\n\ntasks_bp = Blueprint(\'tasks\', __name__)\n\n' + rest
        
        tasks_file.write_text(content, encoding='utf-8')
        print(f"   ✅ Fixed {tasks_file}")

def create_basic_templates():
    """Create basic template files"""
    print("📄 Creating basic template files...")
    
    # Create basic error templates
    error_templates = {
        'templates/errors/404.html': '''{% extends "base.html" %}
{% block title %}ไม่พบหน้าที่ต้องการ{% endblock %}
{% block content %}
<div class="container mt-5">
    <div class="text-center">
        <h1 class="display-1">404</h1>
        <p class="lead">ไม่พบหน้าที่ต้องการ</p>
        <a href="{{ url_for('main.dashboard') }}" class="btn btn-primary">กลับหน้าหลัก</a>
    </div>
</div>
{% endblock %}''',
        
        'templates/errors/500.html': '''{% extends "base.html" %}
{% block title %}เกิดข้อผิดพลาด{% endblock %}
{% block content %}
<div class="container mt-5">
    <div class="text-center">
        <h1 class="display-1">500</h1>
        <p class="lead">เกิดข้อผิดพลาดในระบบ</p>
        <a href="{{ url_for('main.dashboard') }}" class="btn btn-primary">กลับหน้าหลัก</a>
    </div>
</div>
{% endblock %}''',
        
        'templates/main/index.html': '''{% extends "base.html" %}
{% block title %}หน้าหลัก{% endblock %}
{% block content %}
<div class="container mt-5">
    <div class="jumbotron">
        <h1 class="display-4">ยินดีต้อนรับสู่ Comphone System</h1>
        <p class="lead">ระบบจัดการงานซ่อมและขายโทรศัพท์</p>
        <a href="{{ url_for('main.dashboard') }}" class="btn btn-primary btn-lg">เข้าสู่ระบบ</a>
    </div>
</div>
{% endblock %}''',
        
        'templates/auth/login.html': '''{% extends "base.html" %}
{% block title %}เข้าสู่ระบบ{% endblock %}
{% block content %}
<div class="container mt-5">
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h4>เข้าสู่ระบบ</h4>
                </div>
                <div class="card-body">
                    <form method="POST">
                        <div class="mb-3">
                            <label for="username" class="form-label">ชื่อผู้ใช้</label>
                            <input type="text" class="form-control" id="username" name="username" required>
                        </div>
                        <div class="mb-3">
                            <label for="password" class="form-label">รหัสผ่าน</label>
                            <input type="password" class="form-control" id="password" name="password" required>
                        </div>
                        <div class="mb-3 form-check">
                            <input type="checkbox" class="form-check-input" id="remember" name="remember">
                            <label class="form-check-label" for="remember">จดจำการเข้าสู่ระบบ</label>
                        </div>
                        <button type="submit" class="btn btn-primary">เข้าสู่ระบบ</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}''',
        
        'templates/main/dashboard.html': '''{% extends "base.html" %}
{% block title %}แดชบอร์ด{% endblock %}
{% block content %}
<div class="container-fluid mt-4">
    <h1>แดชบอร์ด</h1>
    
    <div class="row">
        <div class="col-md-3">
            <div class="card bg-primary text-white">
                <div class="card-body">
                    <h5>ลูกค้าทั้งหมด</h5>
                    <h2>{{ stats.get('total_customers', 0) }}</h2>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card bg-success text-white">
                <div class="card-body">
                    <h5>งานทั้งหมด</h5>
                    <h2>{{ stats.get('total_tasks', 0) }}</h2>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card bg-info text-white">
                <div class="card-body">
                    <h5>งานซ่อม</h5>
                    <h2>{{ stats.get('total_service_jobs', 0) }}</h2>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card bg-warning text-white">
                <div class="card-body">
                    <h5>สินค้า</h5>
                    <h2>{{ stats.get('total_products', 0) }}</h2>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}'''
    }
    
    for template_path, content in error_templates.items():
        template_file = Path(template_path)
        template_file.parent.mkdir(parents=True, exist_ok=True)
        if not template_file.exists():
            template_file.write_text(content, encoding='utf-8')
            print(f"   ✅ {template_path}")

def main():
    """Main setup function"""
    print("🚀 Starting Comphone Integrated System Setup...")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not Path('models.py').exists():
        print("❌ Error: models.py not found. Please run this script from the project root directory.")
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Create missing files
    create_missing_files()
    
    # Fix imports
    fix_imports()
    
    # Create basic templates
    create_basic_templates()
    
    print("\n" + "=" * 60)
    print("🎉 Setup completed successfully!")
    print("=" * 60)
    print("📝 Next steps:")
    print("1. Run: python app.py")
    print("2. Or run: flask init-db")
    print("3. Create admin: flask create-admin")
    print("4. Access: http://localhost:5000")
    print("=" * 60)

if __name__ == '__main__':
    main()