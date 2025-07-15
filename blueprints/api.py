# ============================================================================
# blueprints/api.py - Simple API Blueprint
# ============================================================================

from flask import Blueprint, jsonify
from flask_login import login_required

api_bp = Blueprint('api', __name__)

@api_bp.route('/status')
def status():
    """API status endpoint"""
    return jsonify({'status': 'ok', 'message': 'API is running'})

@api_bp.route('/tasks')
@login_required
def api_tasks():
    """Get tasks via API"""
    return jsonify({'tasks': []})