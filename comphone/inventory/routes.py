# comphone/inventory/routes.py
from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required
import sqlalchemy as sa
from comphone import db
from comphone.inventory import bp
from comphone.inventory.forms import ProductForm, StockInForm
from comphone.models import Product, StockMovement

@bp.route('/products')
@login_required
def products():
    """แสดงหน้ารายการสินค้า"""
    products_query = db.session.scalars(sa.select(Product).order_by(Product.name)).all()

    # แปลง Product objects ให้เป็น dictionary เพื่อให้ JSON serializable
    # นี่คือการแก้ไขสำหรับ TypeError: Object of type Product is not JSON serializable
    products_data = []
    for p in products_query:
        products_data.append({
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'cost_price': p.cost_price,
            'selling_price': p.selling_price,
            'quantity': p.quantity
        })

    return render_template('inventory/products.html', title='รายการสินค้า', products=products_data)

@bp.route('/product/new', methods=['GET', 'POST'])
@login_required
def create_product():
    """หน้าฟอร์มสำหรับเพิ่มสินค้าใหม่"""
    form = ProductForm()
    if form.validate_on_submit():
        # ตรวจสอบชื่อสินค้าซ้ำก่อนบันทึก
        existing_product = db.session.scalar(sa.select(Product).where(Product.name == form.name.data))
        if existing_product:
            flash(f'ชื่อสินค้า "{form.name.data}" มีอยู่ในระบบแล้ว กรุณาใช้ชื่ออื่น หรือไปที่เมนู "รับเข้า" เพื่อเพิ่มสต็อก.', 'danger')
            return render_template('inventory/product_form.html', form=form, title='เพิ่มสินค้าใหม่')

        product = Product(name=form.name.data, description=form.description.data,
                          cost_price=form.cost_price.data, selling_price=form.selling_price.data,
                          quantity=0) # สินค้าใหม่เริ่มที่ 0, เพิ่มสต็อกผ่าน Stock-In
        db.session.add(product)
        db.session.commit()
        flash('เพิ่มสินค้าใหม่เรียบร้อยแล้ว!', 'success')
        return redirect(url_for('inventory.products'))
    return render_template('inventory/product_form.html', form=form, title='เพิ่มสินค้าใหม่')

@bp.route('/product/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    """หน้าฟอร์มสำหรับแก้ไขข้อมูลสินค้า"""
    product = db.get_or_404(Product, id)
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        # ตรวจสอบชื่อสินค้าซ้ำเมื่อแก้ไข (ยกเว้นชื่อเดิมของสินค้านี้เอง)
        existing_product = db.session.scalar(sa.select(Product).where(
            sa.and_(Product.name == form.name.data, Product.id != id)
        ))
        if existing_product:
            flash(f'ชื่อสินค้า "{form.name.data}" มีอยู่ในระบบแล้ว กรุณาใช้ชื่ออื่น.', 'danger')
            return render_template('inventory/product_form.html', form=form, title='แก้ไขสินค้า')

        product.name = form.name.data
        product.description = form.description.data
        product.cost_price = form.cost_price.data
        product.selling_price = form.selling_price.data
        # quantity ไม่ได้แก้ไขจากหน้านี้
        db.session.commit()
        flash('แก้ไขข้อมูลสินค้าเรียบร้อยแล้ว', 'success')
        return redirect(url_for('inventory.products'))
    return render_template('inventory/product_form.html', form=form, title='แก้ไขสินค้า')

@bp.route('/product/<int:id>/delete', methods=['POST'])
@login_required
def delete_product(id):
    """ฟังก์ชันสำหรับลบข้อมูลสินค้า"""
    product = db.get_or_404(Product, id)
    db.session.delete(product)
    db.session.commit()
    flash('ลบสินค้าเรียบร้อยแล้ว', 'info')
    return redirect(url_for('inventory.products'))

@bp.route('/product/<int:id>/stock_in', methods=['GET', 'POST'])
@login_required
def stock_in(id):
    """หน้าสำหรับรับสินค้าเข้าสต็อก"""
    product = db.get_or_404(Product, id)
    form = StockInForm()
    
    if form.validate_on_submit():
        quantity_in = form.quantity.data
        
        # เพิ่มจำนวนสินค้า
        product.quantity += quantity_in
        
        # บันทึกการเคลื่อนไหวสต็อก
        movement = StockMovement(product_id=product.id, change=quantity_in, reason='stock_in')
        db.session.add(movement)
        
        db.session.commit()
        flash(f'รับสินค้า "{product.name}" เข้าสต็อก {quantity_in} ชิ้นเรียบร้อยแล้ว!', 'success')
        return redirect(url_for('inventory.products'))
        
    return render_template('inventory/stock_in.html', title=f'รับสินค้าเข้า: {product.name}', product=product, form=form)

