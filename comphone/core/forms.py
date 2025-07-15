from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

class CustomerForm(FlaskForm):
    name = StringField('ชื่อลูกค้า', validators=[DataRequired()])
    phone = StringField('เบอร์โทร')
    address = StringField('ที่อยู่')
    submit = SubmitField('บันทึก')