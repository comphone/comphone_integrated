# comphone/api_routes.py

import os
import json
import datetime
import pytz
from flask import Blueprint, request, jsonify, current_app, session, url_for
from dateutil.parser import parse as date_parse
from werkzeug.utils import secure_filename

# Local imports
from .google_services import (
    get_customer_database, get_single_task, update_google_task,
    delete_google_task, get_google_tasks_for_report,
    add_tech_report_to_notes, upload_file_to_drive_for_task,
    create_or_update_calendar_event, upload_data_from_memory_to_drive,
    find_or_create_drive_folder # Ensure this is imported for avatar/attachment folders
)
from .utils import (
    parse_customer_info_from_notes, THAILAND_TZ,
    ALLOWED_EXTENSIONS
)
from .line_handler import send_completion_notification, send_update_notification, send_new_task_notification
from .main_routes import login_required
from .extensions import cache

# Import settings_manager for backup import functionality
from .settings_manager import save_app_settings # Assuming settings_manager has save_app_settings

bp = Blueprint('api', __name__, url_prefix='/api')

# กำหนดชื่อไฟล์สำหรับเก็บข้อมูล Subscriptions
SUBSCRIPTIONS_FILE = 'push_subscriptions.json'

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/customers')
@login_required
def get_customers():
    current_app.logger.info("Accessed /api/customers endpoint.")
    user_creds_dict = session.get('credentials')
    customer_list = get_customer_database(credentials=user_creds_dict)
    current_app.logger.debug(f"Returning {len(customer_list)} customers.")
    return jsonify(customer_list)

@bp.route('/calendar_tasks')
@login_required
def api_calendar_tasks():
    current_app.logger.info("Accessed /api/calendar_tasks endpoint.")
    user_creds_dict = session.get('credentials')
    try:
        tasks_raw = get_google_tasks_for_report(show_completed=True, credentials=user_creds_dict) or []
        events = []
        today_thai = datetime.datetime.now(pytz.timezone('Asia/Bangkok')).date()

        for task in tasks_raw:
            if not task.get('due'):
                continue

            customer_info = parse_customer_info_from_notes(task.get('notes', ''))
            is_completed = task.get('status') == 'completed'
            is_overdue = False
            is_today = False

            try:
                due_dt_local = date_parse(task['due']).astimezone(pytz.timezone('Asia/Bangkok'))
                if not is_completed and due_dt_local.date() < today_thai:
                    is_overdue = True
                elif not is_completed and due_dt_local.date() == today_thai:
                    is_today = True
            except (ValueError, TypeError):
                current_app.logger.warning(f"Invalid due date format for task {task.get('id')}: {task.get('due')}")
                pass

            event = {
                'id': task.get('id'),
                'title': f"{customer_info.get('name', 'N/A')} - {task.get('title')}",
                'start': task.get('due'),
                'url': url_for('main.task_details', task_id=task.get('id')),
                'extendedProps': {
                    'is_completed': is_completed,
                    'is_overdue': is_overdue,
                    'is_today': is_today
                }
            }
            events.append(event)
            
        current_app.logger.debug(f"Generated {len(events)} calendar events.")
        return jsonify(events)
    except Exception as e:
        current_app.logger.error(f"Error fetching tasks for calendar API: {e}", exc_info=True)
        return jsonify({"error": "Could not fetch tasks from server"}), 500

@bp.route('/task/<task_id>/report', methods=['POST'])
@login_required
def add_task_report(task_id):
    current_app.logger.info(f"Accessed /api/task/{task_id}/report (POST) endpoint.")
    user_creds_dict = session.get('credentials')
    task = get_single_task(task_id, credentials=user_creds_dict)
    if not task:
        current_app.logger.warning(f"Task {task_id} not found for report submission.")
        return jsonify({'status': 'error', 'message': 'ไม่พบงาน'}), 404

    action = request.form.get('action')
    work_summary = request.form.get('work_summary', '').strip()
    technicians_json = request.form.get('technicians_report') or request.form.get('technicians_reschedule')
    uploaded_attachments_json = request.form.get('uploaded_attachments_json') # Get uploaded attachments from JS
    
    current_app.logger.debug(f"Report action: {action}, Work Summary: {work_summary[:50]}...")
    
    try:
        technicians = json.loads(technicians_json) if technicians_json else []
        current_app.logger.debug(f"Technicians parsed: {technicians}")
    except json.JSONDecodeError:
        current_app.logger.error(f"Invalid JSON for technicians in task report for task {task_id}: {technicians_json}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'รูปแบบข้อมูลช่างไม่ถูกต้อง'}), 400
    
    # Process attachments from JS
    uploaded_attachments = []
    if uploaded_attachments_json:
        try:
            uploaded_attachments = json.loads(uploaded_attachments_json)
        except json.JSONDecodeError as e:
            current_app.logger.error(f"Error parsing uploaded_attachments_json: {e}", exc_info=True)


    report_data = {
        'summary_date': datetime.datetime.now(THAILAND_TZ).isoformat(),
        'work_summary': work_summary,
        'technicians': technicians,
        'attachments': uploaded_attachments,
        'type': action
    }

    if action == 'save_report':
        if not work_summary and not uploaded_attachments:
            current_app.logger.warning(f"Attempted to save report for task {task_id} without summary or attachments.")
            return jsonify({'status': 'error', 'message': 'กรุณาใส่สรุปความคืบหน้าหรือแนบไฟล์'}), 400
        add_tech_report_to_notes(task_id, report_data, credentials=user_creds_dict)
        send_update_notification(task, "ไม่มีการเปลี่ยนแปลง", work_summary, technicians, True)
        current_app.logger.info(f"Report saved and update notification sent for task {task_id}.")

    elif action == 'complete_task':
        if not work_summary:
            current_app.logger.warning(f"Attempted to complete task {task_id} without work summary.")
            return jsonify({'status': 'error', 'message': 'กรุณากรอกสรุปงานที่ทำเพื่อปิดงาน'}), 400
        report_data['type'] = 'completion'
        add_tech_report_to_notes(task_id, report_data, credentials=user_creds_dict)
        completed_task = update_google_task(task_id, status='completed', credentials=user_creds_dict)
        if completed_task:
            send_completion_notification(completed_task, technicians)
            current_app.logger.info(f"Task {task_id} completed and completion notification sent.")
        else:
            current_app.logger.error(f"Failed to mark task {task_id} as completed in Google Tasks.")


    elif action == 'reschedule_task':
        new_due_str = request.form.get('reschedule_due')
        if not new_due_str:
            current_app.logger.warning(f"Attempted to reschedule task {task_id} without new due date.")
            return jsonify({'status': 'error', 'message': 'กรุณาระบุวันนัดหมายใหม่'}), 400
        
        dt_local = date_parse(new_due_str)
        due_date_gmt = dt_local.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')
        report_data['work_summary'] = f"เลื่อนนัดไปเป็น {dt_local.strftime('%d/%m/%Y %H:%M')}"
        if request.form.get('reschedule_reason', '').strip():
            report_data['work_summary'] += f" - เหตุผล: {request.form.get('reschedule_reason').strip()}"
        
        add_tech_report_to_notes(task_id, report_data, credentials=user_creds_dict)
        rescheduled_task = update_google_task(task_id, due=due_date_gmt, status='needsAction', credentials=user_creds_dict)
        if rescheduled_task:
            create_or_update_calendar_event(rescheduled_task, credentials=user_creds_dict)
            send_update_notification(rescheduled_task, dt_local.strftime('%d/%m/%Y %H:%M'), request.form.get('reschedule_reason'), technicians, False)
            current_app.logger.info(f"Task {task_id} rescheduled to {new_due_str} and notification sent.")
        else:
            current_app.logger.error(f"Failed to reschedule task {task_id} in Google Tasks.")

    cache.clear()
    return jsonify({'status': 'success', 'message': 'บันทึกข้อมูลเรียบร้อยแล้ว'})

# --- Route for Uploading Technician Avatars ---
@bp.route('/upload_avatar', methods=['POST'])
@login_required
def api_upload_avatar():
    current_app.logger.info("Accessed /api/upload_avatar endpoint.")
    user_creds_dict = session.get('credentials')
    
    if 'file' not in request.files:
        current_app.logger.warning("No file part in the upload_avatar request.")
        return jsonify({'status': 'error', 'message': 'ไม่พบไฟล์ที่อัปโหลด'}), 400
    
    file = request.files['file']
    if file.filename == '':
        current_app.logger.warning("No selected file for upload_avatar.")
        return jsonify({'status': 'error', 'message': 'ไม่ได้เลือกไฟล์'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        if not os.environ.get('GOOGLE_DRIVE_FOLDER_ID'):
            current_app.logger.error("GOOGLE_DRIVE_FOLDER_ID is not set for avatar upload.")
            return jsonify({'status': 'error', 'message': 'ไม่ได้ตั้งค่า Drive Folder ID'}), 500

        tech_avatars_folder_id = None
        try:
            tech_avatars_folder_id = find_or_create_drive_folder(
                "Technician Avatars", 
                os.environ.get('GOOGLE_DRIVE_FOLDER_ID'), 
                credentials=user_creds_dict
            )
        except Exception as e:
            current_app.logger.error(f"Error finding/creating Technician Avatars folder: {e}", exc_info=True)
            return jsonify({'status': 'error', 'message': 'ไม่สามารถสร้างโฟลเดอร์รูปภาพได้'}), 500


        if tech_avatars_folder_id:
            file.seek(0) 
            
            uploaded_file_info = upload_data_from_memory_to_drive(
                file, 
                filename, 
                file.mimetype, 
                tech_avatars_folder_id, 
                credentials=user_creds_dict
            )

            if uploaded_file_info:
                current_app.logger.info(f"Avatar file '{filename}' uploaded successfully. ID: {uploaded_file_info.get('id')}")
                return jsonify({
                    'status': 'success', 
                    'message': 'อัปโหลดรูปภาพสำเร็จ', 
                    'file_id': uploaded_file_info.get('id'),
                    'file_url': uploaded_file_info.get('webViewLink')
                }), 200
            else:
                current_app.logger.error(f"Failed to upload avatar file '{filename}'.")
                return jsonify({'status': 'error', 'message': 'ไม่สามารถอัปโหลดไฟล์รูปภาพได้'}), 500
        else:
            current_app.logger.error("Could not get Technician Avatars folder ID.")
            return jsonify({'status': 'error', 'message': 'ไม่สามารถจัดเก็บรูปภาพได้'}), 500
    else:
        current_app.logger.warning(f"Invalid file type for avatar upload: {file.filename}")
        return jsonify({'status': 'error', 'message': 'รูปแบบไฟล์ไม่ถูกต้อง'}), 400

# --- NEW ROUTE: For general file attachments in 'form.html' and other places ---
@bp.route('/upload_attachment', methods=['POST'])
@login_required
def upload_attachment():
    current_app.logger.info("Accessed /api/upload_attachment endpoint (general attachment).")
    user_creds_dict = session.get('credentials')
    
    if 'file' not in request.files:
        current_app.logger.warning("No file part in the upload_attachment request.")
        return jsonify({'status': 'error', 'message': 'ไม่พบไฟล์ที่อัปโหลด'}), 400
    
    file = request.files['file']
    if file.filename == '':
        current_app.logger.warning("No selected file for upload_attachment.")
        return jsonify({'status': 'error', 'message': 'ไม่ได้เลือกไฟล์'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        if not os.environ.get('GOOGLE_DRIVE_FOLDER_ID'):
            current_app.logger.error("GOOGLE_DRIVE_FOLDER_ID is not set for general attachment upload.")
            return jsonify({'status': 'error', 'message': 'ไม่ได้ตั้งค่า Drive Folder ID'}), 500

        general_attachments_folder_id = None
        try:
            general_attachments_folder_id = find_or_create_drive_folder(
                "Temporary Attachments", # This name should be consistent or configurable
                os.environ.get('GOOGLE_DRIVE_FOLDER_ID'), 
                credentials=user_creds_dict
            )
        except Exception as e:
            current_app.logger.error(f"Error finding/creating Temporary Attachments folder: {e}", exc_info=True)
            return jsonify({'status': 'error', 'message': 'ไม่สามารถสร้างโฟลเดอร์สำหรับไฟล์แนบได้'}), 500

        if general_attachments_folder_id:
            file.seek(0)
            uploaded_file_info = upload_data_from_memory_to_drive(
                file, 
                filename, 
                file.mimetype, 
                general_attachments_folder_id, 
                credentials=user_creds_dict
            )

            if uploaded_file_info:
                current_app.logger.info(f"General attachment '{filename}' uploaded successfully. ID: {uploaded_file_info.get('id')}")
                return jsonify({
                    'status': 'success', 
                    'message': 'อัปโหลดไฟล์แนบสำเร็จ', 
                    'file_info': uploaded_file_info # Change from 'file_url' to 'file_info' for consistency
                }), 200
            else:
                current_app.logger.error(f"Failed to upload general attachment '{filename}'.")
                return jsonify({'status': 'error', 'message': 'ไม่สามารถอัปโหลดไฟล์แนบได้'}), 500
        else:
            current_app.logger.error("Could not get Temporary Attachments folder ID.")
            return jsonify({'status': 'error', 'message': 'ไม่สามารถจัดเก็บไฟล์แนบได้'}), 500
    else:
        current_app.logger.warning(f"Invalid file type for general attachment upload: {file.filename}")
        return jsonify({'status': 'error', 'message': 'รูปแบบไฟล์ไม่ถูกต้อง'}), 400


@bp.route('/task/<task_id>', methods=['DELETE'])
@login_required
def api_delete_task(task_id):
    current_app.logger.info(f"Accessed /api/task/{task_id} (DELETE) endpoint.")
    user_creds_dict = session.get('credentials')
    if delete_google_task(task_id, credentials=user_creds_dict):
        cache.clear()
        current_app.logger.info(f"Task {task_id} deleted successfully.")
        return jsonify({'status': 'success', 'message': 'ลบงานเรียบร้อยแล้ว'})
    else:
        current_app.logger.error(f"Failed to delete task {task_id}.")
        return jsonify({'status': 'error', 'message': 'ไม่สามารถลบงานได้'}), 500

@bp.route('/task/schedule_from_calendar', methods=['POST'])
@login_required
def schedule_task_from_calendar():
    current_app.logger.info("Accessed /api/task/schedule_from_calendar (POST) endpoint.")
    user_creds_dict = session.get('credentials')
    data = request.json
    task_id = data.get('task_id')
    new_due_str = data.get('new_due_date')
    
    if not task_id or not new_due_str:
        current_app.logger.warning("Missing task_id or new_due_date for calendar scheduling.")
        return jsonify({'status': 'error', 'message': 'ข้อมูลไม่ครบถ้วน'}), 400
        
    try:
        task = get_single_task(task_id, credentials=user_creds_dict)
        if not task:
            current_app.logger.warning(f"Task {task_id} not found for calendar scheduling.")
            return jsonify({'status': 'error', 'message': 'ไม่พบงาน'}), 404
        if task.get('status') == 'completed':
            current_app.logger.warning(f"Attempted to reschedule completed task {task_id}.")
            return jsonify({'status': 'error', 'message': 'ไม่สามารถย้ายงานที่เสร็จแล้วได้'}), 403

        dt_utc = date_parse(new_due_str)
        due_date_gmt = dt_utc.isoformat().replace('+00:00', 'Z')

        updated_task = update_google_task(task_id, credentials=user_creds_dict, due=due_date_gmt, status='needsAction')
        
        if updated_task:
            cache.clear()
            current_app.logger.info(f"Task {task_id} rescheduled from calendar successfully to {new_due_str}.")
            return jsonify({'status': 'success', 'message': 'อัปเดตวันนัดหมายเรียบร้อยแล้ว'})
        else:
            current_app.logger.error(f"Failed to update task {task_id} in Google Tasks during calendar scheduling.")
            return jsonify({'status': 'error', 'message': 'ไม่สามารถอัปเดตงานใน Google Tasks ได้'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error scheduling task from calendar for task {task_id}: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f'เกิดข้อผิดพลาด: {e}'}), 500

# --- Route สำหรับ Push Notification ---
@bp.route('/save-subscription', methods=['POST'])
@login_required
def save_subscription():
    """รับและบันทึกข้อมูล subscription จากผู้ใช้"""
    current_app.logger.info("Accessed /api/save-subscription endpoint.")
    subscription_data = request.json
    if not subscription_data:
        current_app.logger.warning("No subscription data received for push notification.")
        return jsonify({'status': 'error', 'message': 'No subscription data received'}), 400
    
    user_email = session.get('profile', {}).get('email')
    if not user_email:
        current_app.logger.warning("User not logged in when attempting to save subscription.")
        return jsonify({'status': 'error', 'message': 'User not logged in'}), 401

    subscriptions = {}
    if os.path.exists(SUBSCRIPTIONS_FILE):
        with open(SUBSCRIPTIONS_FILE, 'r') as f:
            try:
                subscriptions = json.load(f)
                current_app.logger.debug(f"Loaded existing subscriptions from {SUBSCRIPTIONS_FILE}.")
            except json.JSONDecodeError:
                current_app.logger.error(f"Error decoding JSON from {SUBSCRIPTIONS_FILE}. Starting with empty subscriptions.", exc_info=True)
                pass
    
    subscriptions[user_email] = subscription_data
    
    try:
        with open(SUBSCRIPTIONS_FILE, 'w') as f:
            json.dump(subscriptions, f, indent=2)
        current_app.logger.info(f"Subscription for {user_email} saved to {SUBSCRIPTIONS_FILE}.")
        return jsonify({'status': 'success'}), 201
    except IOError as e:
        current_app.logger.error(f"Error writing subscription to file {SUBSCRIPTIONS_FILE}: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Could not save subscription'}), 500

# --- NEW ROUTE: For importing backup data (JSON) ---
@bp.route('/import_backup', methods=['POST'])
@login_required
def import_backup():
    current_app.logger.info("Accessed /api/import_backup endpoint.")
    user_creds_dict = session.get('credentials')

    if 'backup_file' not in request.files:
        return jsonify({'status': 'error', 'message': 'ไม่พบไฟล์สำรอง'}), 400

    backup_file = request.files['backup_file']
    file_type = request.form.get('file_type')

    if backup_file.filename == '':
        return jsonify({'status': 'error', 'message': 'ไม่ได้เลือกไฟล์'}), 400

    if not backup_file.filename.lower().endswith('.json'):
        return jsonify({'status': 'error', 'message': 'รองรับเฉพาะไฟล์ .json'}), 400

    try:
        file_content = backup_file.read().decode('utf-8')
        data = json.loads(file_content)
        
        if file_type == 'tasks_json':
            current_app.logger.info(f"Importing {len(data)} tasks from backup.")
            # This is a simplified import. For production, you'd need:
            # - More robust error handling for each task creation.
            # - Option to update existing tasks vs. creating new ones.
            # - Batching for large number of tasks.
            imported_count = 0
            for task_data in data:
                # Ensure fields match create_google_task expected format
                title = task_data.get('title', 'Imported Task')
                notes = task_data.get('notes')
                due = task_data.get('due')
                
                # You might need to refine 'notes' parsing for actual import
                if create_google_task(title, notes=notes, due=due, credentials=user_creds_dict):
                    imported_count += 1
            cache.clear()
            return jsonify({'status': 'success', 'message': f'นำเข้างานสำเร็จ {imported_count} รายการ'}), 200

        elif file_type == 'settings_json':
            current_app.logger.info("Importing settings from backup.")
            if save_app_settings(data): # Assuming save_app_settings handles the format
                cache.clear()
                return jsonify({'status': 'success', 'message': 'นำเข้าการตั้งค่าสำเร็จ'}), 200
            else:
                return jsonify({'status': 'error', 'message': 'ไม่สามารถนำเข้าการตั้งค่าได้'}), 500
        else:
            return jsonify({'status': 'error', 'message': 'ประเภทไฟล์ไม่ถูกต้อง'}), 400

    except json.JSONDecodeError:
        current_app.logger.error("Invalid JSON format for backup file.", exc_info=True)
        return jsonify({'status': 'error', 'message': 'ไฟล์ JSON ไม่ถูกต้อง'}), 400
    except Exception as e:
        current_app.logger.error(f"Error during backup import: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f'เกิดข้อผิดพลาดในการนำเข้า: {e}'}), 500