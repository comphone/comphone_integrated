#!/usr/bin/env python3
"""
สคริปต์ทดสอบ models และแก้ไขปัญหา
"""

import os
import sys
from datetime import datetime, timezone, timedelta

def test_imports():
    """ทดสอบการ import models"""
    try:
        print("🔍 ทดสอบการ import models...")
        from models import (
            db, User, Customer, CustomerDevice, Product, ServiceJob, 
            Task, Sale, SaleItem, Notification, SystemSettings,
            UserRole, TaskStatus, TaskPriority, ServiceJobStatus, PaymentStatus,
            create_tables, init_default_settings, create_sample_data
        )
        print("✅ Import models สำเร็จ!")
        return True
    except Exception as e:
        print(f"❌ Import models ล้มเหลว: {e}")
        return False

def test_flask_app():
    """ทดสอบการสร้าง Flask app"""
    try:
        print("🔍 ทดสอบการสร้าง Flask app...")
        
        from flask import Flask
        from models import db
        
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'test-key'
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        db.init_app(app)
        
        with app.app_context():
            # ลองสร้างตาราง
            db.create_all()
            print("✅ สร้าง Flask app และตารางสำเร็จ!")
            
            # ลองสร้างข้อมูลทดสอบ
            from models import User, UserRole
            
            # ตรวจสอบว่ามีข้อมูลอยู่แล้วหรือไม่
            if User.query.count() == 0:
                admin = User(
                    username='test_admin',
                    email='test@test.com',
                    first_name='Test',
                    last_name='Admin',
                    role=UserRole.ADMIN
                )
                admin.set_password('test123')
                db.session.add(admin)
                db.session.commit()
                print("✅ สร้างข้อมูลทดสอบสำเร็จ!")
            else:
                print("ℹ️ มีข้อมูลอยู่แล้ว")
        
        # ลบไฟล์ทดสอบ
        if os.path.exists('test.db'):
            os.remove('test.db')
            
        return True
        
    except Exception as e:
        print(f"❌ ทดสอบ Flask app ล้มเหลว: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_main_app():
    """ตรวจสอบ app.py หลัก"""
    try:
        print("🔍 ตรวจสอบ app.py...")
        
        # ลอง import app
        sys.path.insert(0, '.')
        
        if os.path.exists('app.py'):
            print("✅ พบไฟล์ app.py")
            
            # อ่านเนื้อหาไฟล์
            with open('app.py', 'r', encoding='utf-8') as f:
                content = f.read()
                
            # ตรวจสอบส่วนสำคัญ
            checks = [
                ('create_app', 'def create_app()' in content),
                ('Flask-Limiter', 'Limiter(' in content),
                ('models import', 'from models import' in content),
                ('template filters', '@app.template_filter' in content),
                ('login route', '@app.route(\'/login\'' in content)
            ]
            
            for check_name, result in checks:
                status = "✅" if result else "❌"
                print(f"  {status} {check_name}")
                
            return all(result for _, result in checks)
        else:
            print("❌ ไม่พบไฟล์ app.py")
            return False
            
    except Exception as e:
        print(f"❌ ตรวจสอบ app.py ล้มเหลว: {e}")
        return False

def create_blueprints_folder():
    """สร้างโฟลเดอร์ blueprints และไฟล์พื้นฐาน"""
    try:
        print("🔍 ตรวจสอบโฟลเดอร์ blueprints...")
        
        if not os.path.exists('blueprints'):
            os.makedirs('blueprints')
            print("✅ สร้างโฟลเดอร์ blueprints")
        
        # สร้างไฟล์ __init__.py
        init_file = 'blueprints/__init__.py'
        if not os.path.exists(init_file):
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write('# Blueprints package\n')
            print("✅ สร้างไฟล์ blueprints/__init__.py")
        
        # สร้างไฟล์ main.py อย่างง่าย
        main_file = 'blueprints/main.py'
        if not os.path.exists(main_file):
            main_content = '''from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from models import db, User, Customer, ServiceJob, Task

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def dashboard():
    """หน้า Dashboard หลัก"""
    try:
        # สถิติพื้นฐาน
        stats = {
            'total_customers': Customer.query.count(),
            'total_service_jobs': ServiceJob.query.count(),
            'pending_tasks': Task.query.filter_by(status='pending').count(),
            'active_users': User.query.filter_by(is_active=True).count()
        }
        
        # งานล่าสุด
        recent_jobs = ServiceJob.query.order_by(ServiceJob.created_at.desc()).limit(5).all()
        
        return render_template('main/dashboard.html', stats=stats, recent_jobs=recent_jobs)
    except Exception as e:
        print(f"Dashboard error: {e}")
        return render_template('main/dashboard.html', stats={}, recent_jobs=[])
'''
            with open(main_file, 'w', encoding='utf-8') as f:
                f.write(main_content)
            print("✅ สร้างไฟล์ blueprints/main.py")
        
        return True
        
    except Exception as e:
        print(f"❌ สร้างโฟลเดอร์ blueprints ล้มเหลว: {e}")
        return False

def create_templates_folder():
    """สร้างโฟลเดอร์ templates และไฟล์พื้นฐาน"""
    try:
        print("🔍 ตรวจสอบโฟลเดอร์ templates...")
        
        # สร้างโฟลเดอร์หลัก
        folders = ['templates', 'templates/auth', 'templates/main', 'templates/errors']
        for folder in folders:
            if not os.path.exists(folder):
                os.makedirs(folder)
                print(f"✅ สร้างโฟลเดอร์ {folder}")
        
        # สร้างไฟล์ layout.html พื้นฐาน
        layout_file = 'templates/layout.html'
        if not os.path.exists(layout_file):
            layout_content = '''<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Comphone Service Center{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('main.dashboard') }}">
                <i class="fas fa-mobile-alt me-2"></i>Comphone Service
            </a>
            {% if current_user.is_authenticated %}
            <div class="navbar-nav ms-auto">
                <span class="navbar-text me-3">สวัสดี, {{ current_user.first_name }}</span>
                <a class="nav-link" href="{{ url_for('logout') }}">ออกจากระบบ</a>
            </div>
            {% endif %}
        </div>
    </nav>

    <main class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'danger' if category == 'error' else category }} alert-dismissible fade show">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </main>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>'''
            with open(layout_file, 'w', encoding='utf-8') as f:
                f.write(layout_content)
            print("✅ สร้างไฟล์ templates/layout.html")
        
        # สร้างไฟล์ dashboard.html พื้นฐาน
        dashboard_file = 'templates/main/dashboard.html'
        if not os.path.exists(dashboard_file):
            dashboard_content = '''{% extends "layout.html" %}

{% block title %}Dashboard - Comphone Service Center{% endblock %}

{% block content %}
<div class="row">
    <div class="col-12">
        <h1>Dashboard</h1>
        <p>ยินดีต้อนรับสู่ระบบ Comphone Service Center</p>
    </div>
</div>

<div class="row">
    <div class="col-md-3">
        <div class="card text-white bg-primary mb-3">
            <div class="card-body">
                <h5 class="card-title">ลูกค้า</h5>
                <h2>{{ stats.total_customers or 0 }}</h2>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card text-white bg-success mb-3">
            <div class="card-body">
                <h5 class="card-title">งานบริการ</h5>
                <h2>{{ stats.total_service_jobs or 0 }}</h2>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card text-white bg-warning mb-3">
            <div class="card-body">
                <h5 class="card-title">งานรอดำเนินการ</h5>
                <h2>{{ stats.pending_tasks or 0 }}</h2>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="card text-white bg-info mb-3">
            <div class="card-body">
                <h5 class="card-title">ผู้ใช้งาน</h5>
                <h2>{{ stats.active_users or 0 }}</h2>
            </div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-12">
        <h3>งานล่าสุด</h3>
        <div class="table-responsive">
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>หมายเลขงาน</th>
                        <th>ลูกค้า</th>
                        <th>สถานะ</th>
                        <th>วันที่สร้าง</th>
                    </tr>
                </thead>
                <tbody>
                    {% for job in recent_jobs %}
                    <tr>
                        <td>{{ job.job_number }}</td>
                        <td>{{ job.customer.name if job.customer else 'ไม่ระบุ' }}</td>
                        <td>{{ job.status.value|status_badge|safe if job.status else 'ไม่ระบุ' }}</td>
                        <td>{{ job.created_at.strftime('%d/%m/%Y %H:%M') if job.created_at else 'ไม่ระบุ' }}</td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="4" class="text-center">ไม่มีข้อมูล</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}'''
            with open(dashboard_file, 'w', encoding='utf-8') as f:
                f.write(dashboard_content)
            print("✅ สร้างไฟล์ templates/main/dashboard.html")
        
        return True
        
    except Exception as e:
        print(f"❌ สร้างโฟลเดอร์ templates ล้มเหลว: {e}")
        return False

def run_tests():
    """รันการทดสอบทั้งหมด"""
    print("🚀 เริ่มทดสอบระบบ Comphone Service Center")
    print("=" * 50)
    
    tests = [
        ("Import Models", test_imports),
        ("Flask App", test_flask_app),
        ("Check app.py", check_main_app),
        ("Create Blueprints", create_blueprints_folder),
        ("Create Templates", create_templates_folder)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} ล้มเหลว: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 สรุปผลการทดสอบ:")
    
    for test_name, result in results:
        status = "✅ ผ่าน" if result else "❌ ไม่ผ่าน"
        print(f"  {status} {test_name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n🎯 ผลรวม: {passed}/{total} การทดสอบผ่าน")
    
    if passed == total:
        print("\n🎉 ระบบพร้อมใช้งาน! ลองรันคำสั่ง: python app.py")
    else:
        print("\n⚠️ มีการทดสอบที่ไม่ผ่าน กรุณาตรวจสอบและแก้ไข")
    
    return passed == total

if __name__ == '__main__':
    run_tests()