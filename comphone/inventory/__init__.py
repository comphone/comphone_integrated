from flask import Blueprint
bp = Blueprint('inventory', __name__)
from comphone.inventory import routes