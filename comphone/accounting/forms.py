# comphone/accounting/forms.py
from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, SubmitField
from wtforms.validators import Optional
from comphone.models import Customer
import sqlalchemy as sa
from comphone import db

class ReportFilterForm(FlaskForm):
    """
    ฟอร์มสำหรับกรองรายงาน
    """
    start_date = DateField('ตั้งแต่วันที่', format='%Y-%m-%d', validators=[Optional()])
    end_date = DateField('ถึงวันที่', format='%Y-%m-%d', validators=[Optional()])
    customer_id = SelectField('ลูกค้า', coerce=int, validators=[Optional()])
    submit = SubmitField('ค้นหา')

    def __init__(self, *args, **kwargs):
        super(ReportFilterForm, self).__init__(*args, **kwargs)
        # โหลดตัวเลือกลูกค้าเมื่อฟอร์มถูกสร้าง
        # เพิ่มตัวเลือก "ทั้งหมด" (All) ที่มีค่าเป็น 0 หรือ None
        self.customer_id.choices = [(0, 'ลูกค้าทั้งหมด')] + \
                                   [(c.id, c.name) for c in db.session.scalars(sa.select(Customer).order_by(Customer.name)).all()]

