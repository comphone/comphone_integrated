from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Customer, Device, ServiceJob, Sale
from datetime import datetime, timedelta
from sqlalchemy import func, desc, or_
import re

customers_bp = Blueprint('customers', __name__, url_prefix='/customers')

def validate_phone_number(phone):
    """ตรวจสอบรูปแบบเบอร์โทรศัพท์"""
    phone = re.sub(r'[^\d]', '', phone)  # เอาเฉพาะตัวเลข
    if len(phone) == 10 and phone.startswith('0'):
        return phone
    elif len(phone) == 9:
        return '0' + phone
    return None

def format_phone_display(phone):
    """จัดรูปแบบเบอร์โทรศัพท์สำหรับแสดงผล"""
    if not phone:
        return ''
    phone = re.sub(r'[^\d]', '', phone)
    if len(phone) == 10:
        return f"{phone[:3]}-{phone[3:6]}-{phone[6:]}"
    return phone

@customers_bp.route('/')
@login_required
def list_customers():
    """หน้ารายชื่อลูกค้า"""
    try:
        # รับพารามิเตอร์การค้นหาและกรอง
        search = request.args.get('search', '', type=str).strip()
        sort_by = request.args.get('sort', 'name', type=str)
        order = request.args.get('order', 'asc', type=str)
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # สร้าง query หลัก
        query = Customer.query
        
        # ค้นหา
        if search:
            search_filter = or_(
                Customer.first_name.ilike(f'%{search}%'),
                Customer.last_name.ilike(f'%{search}%'),
                Customer.phone.ilike(f'%{search}%'),
                Customer.email.ilike(f'%{search}%'),
                Customer.address.ilike(f'%{search}%')
            )
            query = query.filter(search_filter)
        
        # เรียงลำดับ
        if sort_by == 'name':
            order_column = Customer.first_name if order == 'asc' else desc(Customer.first_name)
        elif sort_by == 'created':
            order_column = Customer.created_at if order == 'asc' else desc(Customer.created_at)
        elif sort_by == 'last_service':
            # เรียงตามวันที่บริการล่าสุด
            query = query.outerjoin(ServiceJob).group_by(Customer.id)
            if order == 'asc':
                order_column = func.max(ServiceJob.created_at).asc()
            else:
                order_column = func.max(ServiceJob.created_at).desc()
        else:
            order_column = Customer.first_name
            
        query = query.order_by(order_column)
        
        # แบ่งหน้า
        customers = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        # สถิติลูกค้า
        total_customers = Customer.query.count()
        new_this_month = Customer.query.filter(
            Customer.created_at >= datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        # ลูกค้าที่มีงานบริการล่าสุด (30 วันที่ผ่านมา)
        recent_service_customers = db.session.query(Customer).join(ServiceJob).filter(
            ServiceJob.created_at >= datetime.now() - timedelta(days=30)
        ).distinct().count()
        
        stats = {
            'total': total_customers,
            'new_this_month': new_this_month,
            'recent_service': recent_service_customers,
            'active_percentage': round((recent_service_customers / total_customers * 100) if total_customers > 0 else 0, 1)
        }
        
        return render_template(
            'customers/list_customers.html',
            customers=customers,
            stats=stats,
            search=search,
            sort_by=sort_by,
            order=order,
            format_phone_display=format_phone_display
        )
        
    except Exception as e:
        flash(f'เกิดข้อผิดพลาดในการโหลดข้อมูลลูกค้า: {str(e)}', 'error')
        return render_template('customers/list_customers.html', customers=None, stats={})

@customers_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_customer():
    """เพิ่มลูกค้าใหม่"""
    if request.method == 'POST':
        try:
            # รับข้อมูลจากฟอร์ม
            first_name = request.form.get('first_name', '').strip().title()
            last_name = request.form.get('last_name', '').strip().title()
            phone = request.form.get('phone', '').strip()
            email = request.form.get('email', '').strip().lower()
            address = request.form.get('address', '').strip()
            notes = request.form.get('notes', '').strip()
            
            # ตรวจสอบข้อมูลที่จำเป็น
            if not first_name:
                flash('กรุณากรอกชื่อ', 'error')
                return render_template('customers/add_customer.html')
                
            if not last_name:
                flash('กรุณากรอกนามสกุล', 'error')
                return render_template('customers/add_customer.html')
            
            # ตรวจสอบและจัดรูปแบบเบอร์โทรศัพท์
            if phone:
                phone = validate_phone_number(phone)
                if not phone:
                    flash('รูปแบบเบอร์โทรศัพท์ไม่ถูกต้อง', 'error')
                    return render_template('customers/add_customer.html')
                
                # ตรวจสอบเบอร์โทรซ้ำ
                existing_phone = Customer.query.filter_by(phone=phone).first()
                if existing_phone:
                    flash('เบอร์โทรศัพท์นี้มีอยู่ในระบบแล้ว', 'error')
                    return render_template('customers/add_customer.html')
            
            # ตรวจสอบอีเมลซ้ำ
            if email:
                existing_email = Customer.query.filter_by(email=email).first()
                if existing_email:
                    flash('อีเมลนี้มีอยู่ในระบบแล้ว', 'error')
                    return render_template('customers/add_customer.html')
            
            # สร้างลูกค้าใหม่
            customer = Customer(
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                email=email or None,
                address=address or None,
                notes=notes or None,
                created_by=current_user.id
            )
            
            db.session.add(customer)
            db.session.commit()
            
            flash(f'เพิ่มลูกค้า {first_name} {last_name} เรียบร้อยแล้ว', 'success')
            return redirect(url_for('customers.view_customer', id=customer.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
            return render_template('customers/add_customer.html')
    
    return render_template('customers/add_customer.html')

@customers_bp.route('/<int:id>')
@login_required
def view_customer(id):
    """ดูรายละเอียดลูกค้า"""
    try:
        customer = db.session.get(Customer, id)
        if not customer:
            flash('ไม่พบข้อมูลลูกค้า', 'error')
            return redirect(url_for('customers.list_customers'))
        
        # ข้อมูลอุปกรณ์
        devices = Device.query.filter_by(customer_id=id).order_by(desc(Device.created_at)).all()
        
        # ประวัติการบริการ (10 รายการล่าสุด)
        service_jobs = ServiceJob.query.filter_by(customer_id=id).order_by(desc(ServiceJob.created_at)).limit(10).all()
        
        # ประวัติการซื้อ (10 รายการล่าสุด)
        sales = Sale.query.filter_by(customer_id=id).order_by(desc(Sale.created_at)).limit(10).all()
        
        # สถิติลูกค้า
        stats = {
            'total_devices': len(devices),
            'total_services': ServiceJob.query.filter_by(customer_id=id).count(),
            'total_sales': Sale.query.filter_by(customer_id=id).count(),
            'total_spent': db.session.query(func.sum(Sale.total_amount)).filter_by(customer_id=id).scalar() or 0,
            'last_service': ServiceJob.query.filter_by(customer_id=id).order_by(desc(ServiceJob.created_at)).first(),
            'last_purchase': Sale.query.filter_by(customer_id=id).order_by(desc(Sale.created_at)).first()
        }
        
        return render_template(
            'customers/view_customer.html',
            customer=customer,
            devices=devices,
            service_jobs=service_jobs,
            sales=sales,
            stats=stats,
            format_phone_display=format_phone_display
        )
        
    except Exception as e:
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
        return redirect(url_for('customers.list_customers'))

@customers_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_customer(id):
    """แก้ไขข้อมูลลูกค้า"""
    try:
        customer = db.session.get(Customer, id)
        if not customer:
            flash('ไม่พบข้อมูลลูกค้า', 'error')
            return redirect(url_for('customers.list_customers'))
        
        if request.method == 'POST':
            # รับข้อมูลจากฟอร์ม
            first_name = request.form.get('first_name', '').strip().title()
            last_name = request.form.get('last_name', '').strip().title()
            phone = request.form.get('phone', '').strip()
            email = request.form.get('email', '').strip().lower()
            address = request.form.get('address', '').strip()
            notes = request.form.get('notes', '').strip()
            
            # ตรวจสอบข้อมูลที่จำเป็น
            if not first_name:
                flash('กรุณากรอกชื่อ', 'error')
                return render_template('customers/edit_customer.html', customer=customer)
                
            if not last_name:
                flash('กรุณากรอกนามสกุล', 'error')
                return render_template('customers/edit_customer.html', customer=customer)
            
            # ตรวจสอบและจัดรูปแบบเบอร์โทรศัพท์
            if phone:
                phone = validate_phone_number(phone)
                if not phone:
                    flash('รูปแบบเบอร์โทรศัพท์ไม่ถูกต้อง', 'error')
                    return render_template('customers/edit_customer.html', customer=customer)
                
                # ตรวจสอบเบอร์โทรซ้ำ (ยกเว้นลูกค้าคนนี้)
                existing_phone = Customer.query.filter(
                    Customer.phone == phone,
                    Customer.id != id
                ).first()
                if existing_phone:
                    flash('เบอร์โทรศัพท์นี้มีอยู่ในระบบแล้ว', 'error')
                    return render_template('customers/edit_customer.html', customer=customer)
            
            # ตรวจสอบอีเมลซ้ำ (ยกเว้นลูกค้าคนนี้)
            if email:
                existing_email = Customer.query.filter(
                    Customer.email == email,
                    Customer.id != id
                ).first()
                if existing_email:
                    flash('อีเมลนี้มีอยู่ในระบบแล้ว', 'error')
                    return render_template('customers/edit_customer.html', customer=customer)
            
            # อัปเดตข้อมูลลูกค้า
            customer.first_name = first_name
            customer.last_name = last_name
            customer.phone = phone
            customer.email = email or None
            customer.address = address or None
            customer.notes = notes or None
            customer.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash(f'อัปเดตข้อมูลลูกค้า {first_name} {last_name} เรียบร้อยแล้ว', 'success')
            return redirect(url_for('customers.view_customer', id=customer.id))
        
        # สถิติลูกค้าสำหรับแสดงในหน้าแก้ไข
        stats = {
            'total_devices': Device.query.filter_by(customer_id=id).count(),
            'total_services': ServiceJob.query.filter_by(customer_id=id).count(),
            'total_sales': Sale.query.filter_by(customer_id=id).count(),
            'member_since': customer.created_at
        }
        
        return render_template(
            'customers/edit_customer.html', 
            customer=customer, 
            stats=stats,
            format_phone_display=format_phone_display
        )
        
    except Exception as e:
        db.session.rollback()
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
        return redirect(url_for('customers.list_customers'))

@customers_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_customer(id):
    """ลบลูกค้า"""
    try:
        customer = db.session.get(Customer, id)
        if not customer:
            return jsonify({'success': False, 'message': 'ไม่พบข้อมูลลูกค้า'})
        
        # ตรวจสอบว่ามีข้อมูลที่เกี่ยวข้องหรือไม่
        has_devices = Device.query.filter_by(customer_id=id).count() > 0
        has_services = ServiceJob.query.filter_by(customer_id=id).count() > 0
        has_sales = Sale.query.filter_by(customer_id=id).count() > 0
        
        if has_devices or has_services or has_sales:
            return jsonify({
                'success': False, 
                'message': 'ไม่สามารถลบลูกค้าได้ เนื่องจากมีข้อมูลที่เกี่ยวข้องในระบบ'
            })
        
        customer_name = f"{customer.first_name} {customer.last_name}"
        db.session.delete(customer)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'ลบลูกค้า {customer_name} เรียบร้อยแล้ว'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'เกิดข้อผิดพลาด: {str(e)}'})

@customers_bp.route('/search_api')
@login_required
def search_customers_api():
    """API สำหรับค้นหาลูกค้า (สำหรับ autocomplete)"""
    try:
        query = request.args.get('q', '').strip()
        if not query or len(query) < 2:
            return jsonify([])
        
        customers = Customer.query.filter(
            or_(
                Customer.first_name.ilike(f'%{query}%'),
                Customer.last_name.ilike(f'%{query}%'),
                Customer.phone.ilike(f'%{query}%')
            )
        ).limit(10).all()
        
        results = []
        for customer in customers:
            results.append({
                'id': customer.id,
                'name': f"{customer.first_name} {customer.last_name}",
                'phone': format_phone_display(customer.phone),
                'email': customer.email
            })
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@customers_bp.route('/<int:id>/add_device', methods=['POST'])
@login_required
def add_device(id):
    """เพิ่มอุปกรณ์ให้ลูกค้า"""
    try:
        customer = db.session.get(Customer, id)
        if not customer:
            return jsonify({'success': False, 'message': 'ไม่พบข้อมูลลูกค้า'})
        
        device_type = request.form.get('device_type', '').strip()
        brand = request.form.get('brand', '').strip()
        model = request.form.get('model', '').strip()
        serial_number = request.form.get('serial_number', '').strip()
        
        if not device_type or not brand or not model:
            return jsonify({'success': False, 'message': 'กรุณากรอกข้อมูลที่จำเป็น'})
        
        # ตรวจสอบ serial number ซ้ำ
        if serial_number:
            existing_device = Device.query.filter_by(serial_number=serial_number).first()
            if existing_device:
                return jsonify({'success': False, 'message': 'หมายเลขเครื่องนี้มีอยู่ในระบบแล้ว'})
        
        device = Device(
            customer_id=id,
            device_type=device_type,
            brand=brand,
            model=model,
            serial_number=serial_number or None,
            created_by=current_user.id
        )
        
        db.session.add(device)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'เพิ่มอุปกรณ์ {device_type} {brand} {model} เรียบร้อยแล้ว',
            'device': {
                'id': device.id,
                'device_type': device.device_type,
                'brand': device.brand,
                'model': device.model,
                'serial_number': device.serial_number
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'เกิดข้อผิดพลาด: {str(e)}'})