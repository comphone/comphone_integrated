# ============================================================================
# blueprints/customers.py - Simple Customers Blueprint
# ============================================================================

from flask import Blueprint, render_template
from flask_login import login_required

customers_bp = Blueprint('customers', __name__)

@customers_bp.route('/')
@login_required
def list_customers():
    """List all customers"""
    return render_template('customers/list.html', customers=[])

@customers_bp.route('/add')
@login_required
def add_customer():
    """Add new customer"""
    return render_template('customers/add.html')