# ============================================================================
# blueprints/google_api.py - Simple Google API Blueprint
# ============================================================================

from flask import Blueprint, render_template
from flask_login import login_required

google_bp = Blueprint('google_api', __name__)

@google_bp.route('/auth')
@login_required
def auth():
    """Google API authentication"""
    return render_template('google/auth.html')