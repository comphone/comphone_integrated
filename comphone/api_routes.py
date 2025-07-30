# comphone/api_routes.py

import os
import json
from flask import Blueprint, request, jsonify, current_app, session
from .main_routes import login_required
from .google_services import get_single_task, update_google_task, get_google_tasks_for_report
from .extensions import cache

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/save-subscription', methods=['POST'])
@login_required
def save_subscription():
    if not request.json or 'endpoint' not in request.json:
        return jsonify({'status': 'error', 'message': 'Invalid subscription data'}), 400
    current_app.logger.info(f"Received subscription: {request.json}")
    return jsonify({'status': 'success'}), 201

@bp.route('/task/schedule_from_calendar', methods=['POST'])
@login_required
def schedule_task_from_calendar():
    data = request.json
    task_id = data.get('task_id')
    new_due_str = data.get('new_due_date')

    if not task_id or not new_due_str:
        return jsonify({'status': 'error', 'message': 'ข้อมูลไม่ครบถ้วน'}), 400

    task = get_single_task(task_id)
    if not task:
        return jsonify({'status': 'error', 'message': 'ไม่พบงาน'}), 404

    if task.get('status') == 'completed':
        return jsonify({'status': 'error', 'message': 'ไม่สามารถย้ายงานที่เสร็จแล้วได้'}), 403

    updated_task = update_google_task(task_id, due=new_due_str, status='needsAction')
    
    if updated_task:
        cache.clear()
        return jsonify({'status': 'success', 'message': 'อัปเดตวันนัดหมายเรียบร้อยแล้ว'})
    else:
        return jsonify({'status': 'error', 'message': 'ไม่สามารถอัปเดตงานใน Google Tasks ได้'}), 500
        
@bp.route('/customers')
@login_required
def get_customers():
    tasks = get_google_tasks_for_report(show_completed=True)
    if not tasks:
        return jsonify([])
    # Logic to extract unique customers from tasks
    # ...
    return jsonify([]) # Placeholder

@bp.route('/upload_avatar', methods=['POST'])
@login_required
def api_upload_avatar():
    # Placeholder for avatar upload logic
    return jsonify({'status': 'success', 'message': 'Avatar uploaded successfully.'})
    
@bp.route('/calendar_tasks')
@login_required
def api_calendar_tasks():
    # This needs a proper implementation using google_services
    return jsonify([])

@bp.route('/upload_attachment', methods=['POST'])
@login_required
def upload_attachment():
    # Placeholder for attachment upload logic
    return jsonify({'status': 'success', 'message': 'Attachment uploaded successfully.'})

@bp.route('/task/<task_id>', methods=['DELETE'])
@login_required
def api_delete_task(task_id):
    # Placeholder for delete task logic
    return jsonify({'status': 'success', 'message': f'Task {task_id} deleted successfully.'})