# ============================================================================
# blueprints/tasks.py - Simple Tasks Blueprint
# ============================================================================

from flask import Blueprint, render_template
from flask_login import login_required

tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route('/')
@login_required
def list_tasks():
    """List all tasks"""
    return render_template('tasks/list.html', tasks=[])

@tasks_bp.route('/create')
@login_required
def create_task():
    """Create new task"""
    return render_template('tasks/create.html')