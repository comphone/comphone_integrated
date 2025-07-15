from flask import Blueprint
bp = Blueprint('service', __name__)
from comphone.service import routes