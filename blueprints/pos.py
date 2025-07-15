# blueprints/pos.py - Complete POS System Blueprint
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import login_required, current_user
from models import db, Product, Sale, SaleItem, Customer, ServiceJob, User
from datetime import datetime, timedelta
import json
import qrcode
import io
import base64
from sqlalchemy import func, and_, or_
from utils.decorators import admin_required
from utils.helpers import format_currency, generate_receipt_number

pos_bp = Blueprint('pos', __name__, url_prefix='/pos')

# ===== POS Main Interface =====
@pos_bp.route('/')
@login_required
def index():
    """หน้าหลัก POS - ระบบขาย"""
    # ดึงสินค้าที่มีสต็อก
    products = Product.query.filter(Product.stock > 0).all()
    categories = db.session.query(Product.category).distinct().all()
    
    # สถิติการขายวันนี้
    today = datetime.now().date()
    today_sales = Sale.query.filter(
        func.date(Sale.created_at) == today
    ).all()
    
    stats = {
        'today_sales': len(today_sales),
        'today_revenue': sum(sale.total_amount for sale in today_sales),
        'products_count': Product.query.count(),
        'low_stock_count': Product.query.filter(Product.stock <= Product.min_stock).count()
    }
    
    return render_template('pos/index.html', 
                         products=products, 
                         categories=categories,
                         stats=stats)

# ===== Sales Processing =====
@pos_bp.route('/api/create_sale', methods=['POST'])
@login_required
def create_sale():
    """สร้างการขายใหม่"""
    try:
        data = request.get_json()
        
        # ตรวจสอบข้อมูล
        if not data.get('items') or not data.get('customer_id'):
            return jsonify({'error': 'ข้อมูลไม่ครบถ้วน'}), 400
        
        # สร้างการขาย
        sale = Sale(
            customer_id=data['customer_id'],
            user_id=current_user.id,
            payment_method=data.get('payment_method', 'cash'),
            discount=data.get('discount', 0),
            tax=data.get('tax', 0),
            notes=data.get('notes', ''),
            receipt_number=generate_receipt_number()
        )
        
        total_amount = 0
        sale_items = []
        
        # ประมวลผลรายการสินค้า
        for item_data in data['items']:
            product = Product.query.get(item_data['product_id'])
            if not product:
                return jsonify({'error': f'ไม่พบสินค้า ID: {item_data["product_id"]}'}), 400
            
            quantity = int(item_data['quantity'])
            
            # ตรวจสอบสต็อก
            if product.stock < quantity:
                return jsonify({'error': f'สต็อกไม่เพียงพอ: {product.name}'}), 400
            
            # สร้างรายการขาย
            sale_item = SaleItem(
                product_id=product.id,
                quantity=quantity,
                unit_price=product.price,
                total_price=quantity * product.price
            )
            sale_items.append(sale_item)
            total_amount += sale_item.total_price
            
            # อัปเดตสต็อก
            product.stock -= quantity
        
        # คำนวณยอดรวม
        sale.subtotal = total_amount
        sale.total_amount = total_amount - sale.discount + sale.tax
        
        # บันทึกลงฐานข้อมูล
        db.session.add(sale)
        db.session.flush()  # เพื่อให้ได้ sale.id
        
        # เพิ่มรายการสินค้า
        for sale_item in sale_items:
            sale_item.sale_id = sale.id
            db.session.add(sale_item)
        
        db.session.commit()
        
        # ส่งกลับข้อมูลการขาย
        return jsonify({
            'success': True,
            'sale_id': sale.id,
            'receipt_number': sale.receipt_number,
            'total_amount': sale.total_amount,
            'message': 'บันทึกการขายสำเร็จ'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@pos_bp.route('/api/search_products')
@login_required
def search_products():
    """ค้นหาสินค้า"""
    query = request.args.get('q', '')
    category = request.args.get('category', '')
    
    products_query = Product.query
    
    if query:
        products_query = products_query.filter(
            or_(
                Product.name.contains(query),
                Product.barcode.contains(query),
                Product.sku.contains(query)
            )
        )
    
    if category:
        products_query = products_query.filter(Product.category == category)
    
    products = products_query.filter(Product.stock > 0).limit(50).all()
    
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'price': float(p.price),
        'stock': p.stock,
        'barcode': p.barcode,
        'category': p.category,
        'image_url': p.image_url
    } for p in products])

@pos_bp.route('/api/scan_barcode')
@login_required
def scan_barcode():
    """สแกนบาร์โค้ดเพื่อหาสินค้า"""
    barcode = request.args.get('barcode')
    if not barcode:
        return jsonify({'error': 'ไม่พบบาร์โค้ด'}), 400
    
    product = Product.query.filter_by(barcode=barcode).first()
    if not product:
        return jsonify({'error': 'ไม่พบสินค้า'}), 404
    
    if product.stock <= 0:
        return jsonify({'error': 'สินค้าหมด'}), 400
    
    return jsonify({
        'id': product.id,
        'name': product.name,
        'price': float(product.price),
        'stock': product.stock,
        'barcode': product.barcode,
        'category': product.category
    })

# ===== Product Management =====
@pos_bp.route('/products')
@login_required
def products():
    """หน้าจัดการสินค้า"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    
    products_query = Product.query
    
    if search:
        products_query = products_query.filter(
            or_(
                Product.name.contains(search),
                Product.sku.contains(search),
                Product.barcode.contains(search)
            )
        )
    
    if category:
        products_query = products_query.filter(Product.category == category)
    
    products = products_query.paginate(
        page=page, per_page=20, error_out=False
    )
    
    categories = db.session.query(Product.category).distinct().all()
    
    return render_template('pos/products.html', 
                         products=products, 
                         categories=categories,
                         search=search,
                         category=category)

@pos_bp.route('/products/create', methods=['GET', 'POST'])
@login_required
def create_product():
    """สร้างสินค้าใหม่"""
    if request.method == 'POST':
        try:
            product = Product(
                name=request.form['name'],
                sku=request.form['sku'],
                barcode=request.form.get('barcode', ''),
                category=request.form['category'],
                price=float(request.form['price']),
                cost=float(request.form.get('cost', 0)),
                stock=int(request.form['stock']),
                min_stock=int(request.form.get('min_stock', 5)),
                unit=request.form.get('unit', 'ชิ้น'),
                description=request.form.get('description', ''),
                image_url=request.form.get('image_url', ''),
                is_active=True
            )
            
            db.session.add(product)
            db.session.commit()
            
            flash('เพิ่มสินค้าสำเร็จ', 'success')
            return redirect(url_for('pos.products'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
    
    categories = db.session.query(Product.category).distinct().all()
    return render_template('pos/product_form.html', 
                         product=None, 
                         categories=categories)

@pos_bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    """แก้ไขสินค้า"""
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        try:
            product.name = request.form['name']
            product.sku = request.form['sku']
            product.barcode = request.form.get('barcode', '')
            product.category = request.form['category']
            product.price = float(request.form['price'])
            product.cost = float(request.form.get('cost', 0))
            product.stock = int(request.form['stock'])
            product.min_stock = int(request.form.get('min_stock', 5))
            product.unit = request.form.get('unit', 'ชิ้น')
            product.description = request.form.get('description', '')
            product.image_url = request.form.get('image_url', '')
            product.is_active = request.form.get('is_active') == 'on'
            
            db.session.commit()
            flash('อัปเดตสินค้าสำเร็จ', 'success')
            return redirect(url_for('pos.products'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'error')
    
    categories = db.session.query(Product.category).distinct().all()
    return render_template('pos/product_form.html', 
                         product=product, 
                         categories=categories)

# ===== Sales History & Reports =====
@pos_bp.route('/sales')
@login_required
def sales_history():
    """ประวัติการขาย"""
    page = request.args.get('page', 1, type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    sales_query = Sale.query
    
    if date_from:
        sales_query = sales_query.filter(Sale.created_at >= date_from)
    if date_to:
        sales_query = sales_query.filter(Sale.created_at <= date_to)
    
    sales = sales_query.order_by(Sale.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('pos/sales.html', 
                         sales=sales,
                         date_from=date_from,
                         date_to=date_to)

@pos_bp.route('/sales/<int:sale_id>')
@login_required
def sale_detail(sale_id):
    """รายละเอียดการขาย"""
    sale = Sale.query.get_or_404(sale_id)
    return render_template('pos/sale_detail.html', sale=sale)

@pos_bp.route('/sales/<int:sale_id>/receipt')
@login_required
def receipt(sale_id):
    """ใบเสร็จ"""
    sale = Sale.query.get_or_404(sale_id)
    return render_template('pos/receipt.html', sale=sale)

@pos_bp.route('/reports')
@login_required
def reports():
    """รายงานการขาย"""
    # รายงานรายวัน
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    
    daily_sales = db.session.query(
        func.date(Sale.created_at).label('date'),
        func.sum(Sale.total_amount).label('total'),
        func.count(Sale.id).label('count')
    ).filter(
        Sale.created_at >= week_ago
    ).group_by(func.date(Sale.created_at)).all()
    
    # สินค้าขายดี
    top_products = db.session.query(
        Product.name,
        func.sum(SaleItem.quantity).label('total_quantity'),
        func.sum(SaleItem.total_price).label('total_revenue')
    ).join(
        SaleItem, Product.id == SaleItem.product_id
    ).join(
        Sale, SaleItem.sale_id == Sale.id
    ).filter(
        Sale.created_at >= week_ago
    ).group_by(
        Product.id, Product.name
    ).order_by(
        func.sum(SaleItem.quantity).desc()
    ).limit(10).all()
    
    # สินค้าใกล้หมด
    low_stock = Product.query.filter(
        Product.stock <= Product.min_stock
    ).all()
    
    return render_template('pos/reports.html',
                         daily_sales=daily_sales,
                         top_products=top_products,
                         low_stock=low_stock)

# ===== Customer Integration =====
@pos_bp.route('/api/customers')
@login_required
def get_customers():
    """ดึงข้อมูลลูกค้าสำหรับ POS"""
    search = request.args.get('search', '')
    
    customers_query = Customer.query
    
    if search:
        customers_query = customers_query.filter(
            or_(
                Customer.name.contains(search),
                Customer.phone.contains(search),
                Customer.email.contains(search)
            )
        )
    
    customers = customers_query.limit(20).all()
    
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'phone': c.phone,
        'email': c.email,
        'address': c.address
    } for c in customers])

@pos_bp.route('/api/customers/create', methods=['POST'])
@login_required
def create_customer_quick():
    """สร้างลูกค้าใหม่แบบเร็ว"""
    try:
        data = request.get_json()
        
        customer = Customer(
            name=data['name'],
            phone=data.get('phone', ''),
            email=data.get('email', ''),
            address=data.get('address', '')
        )
        
        db.session.add(customer)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'customer': {
                'id': customer.id,
                'name': customer.name,
                'phone': customer.phone,
                'email': customer.email
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ===== Service Job Integration =====
@pos_bp.route('/api/service_jobs/create_from_sale', methods=['POST'])
@login_required
def create_service_job_from_sale():
    """สร้างงานซ่อมจากการขาย"""
    try:
        data = request.get_json()
        sale_id = data.get('sale_id')
        
        sale = Sale.query.get_or_404(sale_id)
        
        # สร้างงานซ่อม
        service_job = ServiceJob(
            title=f'งานซ่อม - ใบเสร็จ {sale.receipt_number}',
            description=f'งานซ่อมจากการขาย {sale.receipt_number}',
            customer_id=sale.customer_id,
            assigned_to=current_user.id,
            status='pending',
            priority='medium',
            sale_id=sale.id,
            device_type=data.get('device_type', ''),
            device_brand=data.get('device_brand', ''),
            device_model=data.get('device_model', ''),
            problem_description=data.get('problem_description', ''),
            estimated_cost=data.get('estimated_cost', 0)
        )
        
        db.session.add(service_job)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'service_job_id': service_job.id,
            'message': 'สร้างงานซ่อมสำเร็จ'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ===== Inventory Management =====
@pos_bp.route('/inventory')
@login_required
def inventory():
    """จัดการสต็อกสินค้า"""
    products = Product.query.all()
    
    # สต็อกต่ำ
    low_stock = Product.query.filter(
        Product.stock <= Product.min_stock
    ).all()
    
    # สต็อกหมด
    out_of_stock = Product.query.filter(Product.stock == 0).all()
    
    return render_template('pos/inventory.html',
                         products=products,
                         low_stock=low_stock,
                         out_of_stock=out_of_stock)

@pos_bp.route('/api/inventory/adjust', methods=['POST'])
@login_required
def adjust_inventory():
    """ปรับสต็อกสินค้า"""
    try:
        data = request.get_json()
        product_id = data['product_id']
        adjustment = int(data['adjustment'])
        reason = data.get('reason', 'ปรับปรุงสต็อก')
        
        product = Product.query.get_or_404(product_id)
        old_stock = product.stock
        product.stock += adjustment
        
        # ป้องกันสต็อกติดลบ
        if product.stock < 0:
            product.stock = 0
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'old_stock': old_stock,
            'new_stock': product.stock,
            'message': f'ปรับสต็อก {product.name} สำเร็จ'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ===== Utility Functions =====
@pos_bp.route('/api/generate_barcode')
@login_required
def generate_barcode():
    """สร้างบาร์โค้ด"""
    text = request.args.get('text', '')
    if not text:
        return jsonify({'error': 'ไม่พบข้อความ'}), 400
    
    try:
        # สร้าง QR Code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(text)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # แปลงเป็น base64
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_str = base64.b64encode(img_buffer.getvalue()).decode()
        
        return jsonify({
            'barcode': f'data:image/png;base64,{img_str}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@pos_bp.route('/api/dashboard_stats')
@login_required
def dashboard_stats():
    """สถิติสำหรับแดชบอร์ด"""
    today = datetime.now().date()
    
    # ยอดขายวันนี้
    today_sales = Sale.query.filter(
        func.date(Sale.created_at) == today
    ).all()
    
    # ยอดขายเดือนนี้
    month_start = today.replace(day=1)
    month_sales = Sale.query.filter(
        Sale.created_at >= month_start
    ).all()
    
    stats = {
        'today_sales_count': len(today_sales),
        'today_revenue': sum(s.total_amount for s in today_sales),
        'month_sales_count': len(month_sales),
        'month_revenue': sum(s.total_amount for s in month_sales),
        'total_products': Product.query.count(),
        'low_stock_products': Product.query.filter(
            Product.stock <= Product.min_stock
        ).count(),
        'out_of_stock_products': Product.query.filter(
            Product.stock == 0
        ).count()
    }
    
    return jsonify(stats)

# ===== Error Handlers =====
@pos_bp.errorhandler(404)
def not_found(error):
    return render_template('pos/404.html'), 404

@pos_bp.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('pos/500.html'), 500