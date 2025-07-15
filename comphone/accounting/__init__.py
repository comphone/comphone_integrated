# comphone/accounting/__init__.py
from flask import Blueprint

bp = Blueprint('accounting', __name__)

from comphone.accounting import routes
