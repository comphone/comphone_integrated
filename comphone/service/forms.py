# comphone/service/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange

# ไม่ต้อง import db หรือ models ที่นี่โดยตรง
# choices จะถูกกำหนดใน route แทน เพื่อหลีกเลี่ยง circular import

class ServiceJobForm(FlaskForm):
    """
    ฟอร์มสำหรับสร้างงานซ่อมใหม่
    """
    customer_id = SelectField('ลูกค้า', coerce=int, validators=[Optional()]) # เพิ่มฟิลด์เลือกลูกค้า
    description = TextAreaField('รายละเอียดงานซ่อม', validators=[DataRequired()])
    submit = SubmitField('สร้างงานซ่อม')

class AddPartToJobForm(FlaskForm):
    """
    ฟอร์มสำหรับเพิ่มอะไหล่ที่ใช้ในงานซ่อม
    """
    product_id = SelectField('เลือกอะไหล่', coerce=int, validators=[DataRequired()])
    quantity_used = IntegerField('จำนวนที่เบิก', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('เบิกอะไหล่')

class UpdateStatusForm(FlaskForm):
    """
    ฟอร์มสำหรับอัปเดตสถานะงานซ่อม
    """
    status = SelectField('สถานะ', choices=[
        ('รอดำเนินการ', 'รอดำเนินการ'),
        ('กำลังซ่อม', 'กำลังซ่อม'),
        ('เสร็จสิ้น', 'เสร็จสิ้น'),
        ('ยกเลิก', 'ยกเลิก')
    ], validators=[DataRequired()])
    submit = SubmitField('อัปเดตสถานะ')

