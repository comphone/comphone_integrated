from flask import Blueprint

bp = Blueprint('core', __name__)

from comphone.core import routes  # import routes หลังจากสร้าง bp
