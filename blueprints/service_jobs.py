# ============================================================================
# blueprints/service_jobs.py - Simple Service Jobs Blueprint
# ============================================================================

from flask import Blueprint, render_template
from flask_login import login_required

service_jobs_bp = Blueprint('service_jobs', __name__)

@service_jobs_bp.route('/')
@login_required
def list_jobs():
    """List all service jobs"""
    return render_template('service_jobs/list.html', jobs=[])