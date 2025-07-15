from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required
import sqlalchemy as sa
from comphone import db
from comphone.pos import bp
from comphone.models import Product, Sale, SaleItem, StockMovement, Customer
from comphone.utils.line_api import send_line_message
from flask import current_app

@bp.route('/')
@login_required
def index():
    """แสดงหน้า POS หลัก"""
    customers = db.session.scalars(sa.select(Customer).order_by(Customer.name)).all()
    return render_template('pos/pos.html', title='หน้าขาย (POS)', customers=customers)

@bp.route('/api/search_products')
@login_required
def search_products():
    """API สำหรับค้นหาสินค้าแบบ Real-time"""
    query = request.args.get('q', '', type=str).strip() # เพิ่ม .strip()
    
    stmt = sa.select(Product).where(Product.quantity > 0) 
    if query:
        # ใช้ .ilike() สำหรับการค้นหาที่ไม่สนใจตัวพิมพ์เล็กใหญ่
        # และใช้ .strip() กับ Product.name ก่อนเปรียบเทียบ (หากชื่อใน DB มีช่องว่าง)
        stmt = stmt.where(sa.func.lower(Product.name).like(f'%{query.lower()}%')) # ใช้ .lower() ทั้งคู่เพื่อความชัวร์
    
    products = db.session.scalars(stmt.order_by(Product.name)).all()
    
    products_data = []
    for p in products:
        products_data.append({
            'id': p.id,
            'name': p.name,
            'price': p.selling_price,
            'quantity': p.quantity
        })
    return jsonify(products_data)

@bp.route('/checkout', methods=['POST'])
@login_required
def checkout():
    """
    รับข้อมูลตะกร้าสินค้า, บันทึกการขาย, ตัดสต็อก, และส่ง LINE Message
    """
    data = request.get_json()
    cart_items = data.get('cart')
    customer_id = data.get('customerId') or None

    if not cart_items:
        return jsonify({'status': 'error', 'message': 'ไม่มีสินค้าในตะกร้า'}), 400

    try:
        total_amount = 0
        
        new_sale = Sale(customer_id=customer_id, total_amount=0)
        db.session.add(new_sale)
        
        for item in cart_items:
            product = db.session.get(Product, item['id'])
            if not product:
                raise ValueError(f"ไม่พบสินค้า ID: {item['id']}")

            quantity = int(item['quantity'])
            
            if product.quantity < quantity:
                raise ValueError(f'สินค้า "{product.name}" มีไม่พอในสต็อก')

            product.quantity -= quantity
            
            price = float(item['price'])
            total_amount += price * quantity
            
            sale_item = SaleItem(sale=new_sale, product_id=product.id, quantity=quantity, price_per_item=price)
            db.session.add(sale_item)
            
            movement = StockMovement(product_id=product.id, change=-quantity, reason='sale')
            db.session.add(movement)
            
        new_sale.total_amount = total_amount
        db.session.flush() 
        
        db.session.commit()
        
        # ส่ง LINE Message (ใช้ send_line_message แทน send_line_notification)
        try:
            customer_name = db.session.get(Customer, customer_id).name if customer_id else "ลูกค้าทั่วไป"
            message = f"📢 มีรายการขายใหม่!\nลูกค้า: {customer_name}\nยอดรวม: {total_amount:,.2f} บาท\nจำนวน: {len(cart_items)} รายการ"
            send_line_message(message) 
        except Exception as e:
            print(f"Could not send LINE message: {e}")

        flash('ทำรายการขายสำเร็จ!', 'success')
        return jsonify({'status': 'success', 'redirect_url': url_for('core.index')})

    except ValueError as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'เกิดข้อผิดพลาดร้ายแรง: {str(e)}'}), 500
