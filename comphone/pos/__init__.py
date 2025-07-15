from flask import Blueprint

bp = Blueprint('pos', __name__)

# Import routes ไว้ท้ายสุดเสมอ
from comphone.pos import routes