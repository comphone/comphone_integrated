# comphone/auth/forms.py (ตัวอย่าง - คุณต้องมีไฟล์นี้อยู่แล้ว)
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo
import sqlalchemy as sa
from comphone import db
from comphone.models import User

class LoginForm(FlaskForm):
    """
    ฟอร์มสำหรับ Login
    """
    username = StringField('ชื่อผู้ใช้', validators=[DataRequired()])
    password = PasswordField('รหัสผ่าน', validators=[DataRequired()])
    remember_me = BooleanField('จดจำฉัน')
    submit = SubmitField('เข้าสู่ระบบ')

class RegistrationForm(FlaskForm):
    """
    ฟอร์มสำหรับลงทะเบียนผู้ใช้งานใหม่
    """
    username = StringField('ชื่อผู้ใช้', validators=[DataRequired()])
    email = StringField('อีเมล', validators=[DataRequired(), Email()])
    password = PasswordField('รหัสผ่าน', validators=[DataRequired()])
    password2 = PasswordField(
        'ยืนยันรหัสผ่าน', validators=[DataRequired(), EqualTo('password')])
    is_admin = BooleanField('เป็นผู้ดูแลระบบ') # เพิ่มฟิลด์นี้สำหรับกำหนดสิทธิ์
    submit = SubmitField('ลงทะเบียน')

    def validate_username(self, username):
        user = db.session.scalar(sa.select(User).where(User.username == username.data))
        if user is not None:
            raise ValidationError('ชื่อผู้ใช้นี้ถูกใช้งานแล้ว กรุณาเลือกชื่ออื่น.')

    def validate_email(self, email):
        user = db.session.scalar(sa.select(User).where(User.email == email.data))
        if user is not None:
            raise ValidationError('อีเมลนี้ถูกใช้งานแล้ว กรุณาเลือกอีเมลอื่น.')

