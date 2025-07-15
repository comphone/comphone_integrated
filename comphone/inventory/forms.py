# comphone/inventory/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, IntegerField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional

class ProductForm(FlaskForm):
    """
    ฟอร์มสำหรับเพิ่ม/แก้ไขสินค้า
    """
    name = StringField('ชื่อสินค้า', validators=[DataRequired()])
    description = TextAreaField('รายละเอียด', validators=[Optional()])
    cost_price = FloatField('ราคาทุน', validators=[DataRequired(), NumberRange(min=0)])
    selling_price = FloatField('ราคาขาย', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('บันทึก')

class StockInForm(FlaskForm):
    """
    ฟอร์มสำหรับรับสินค้าเข้าสต็อก
    """
    quantity = IntegerField('จำนวนที่รับเข้า', validators=[DataRequired(), NumberRange(min=1, message="จำนวนต้องมากกว่า 0")])
    submit = SubmitField('เพิ่มสต็อก')

