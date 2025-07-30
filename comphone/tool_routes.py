# comphone/tool_routes.py

import datetime
import json
from collections import defaultdict
from flask import (
    Blueprint, request, render_template, redirect, url_for, flash,
    session, Response, current_app, send_file, jsonify 
)
from dateutil.parser import parse as date_parse
import pytz
import io 
import os # เพิ่ม import os สำหรับ _debug_env_vars

# Local imports
from .google_services import get_google_tasks_for_report, delete_google_task, find_or_create_drive_folder # เพิ่ม find_or_create_drive_folder
from .utils import (
    parse_customer_info_from_notes, parse_google_task_dates,
    parse_tech_report_from_notes, sanitize_filename, _create_backup_zip
)
from .settings_manager import get_app_settings, save_app_settings, backup_settings_to_drive
from .app_scheduler import cache, run_scheduler, scheduled_backup_job
from .main_routes import login_required  
from .line_handler import send_test_notification 

# สร้าง Blueprint ชื่อ 'tools'
bp = Blueprint('tools', __name__, url_prefix='/tools')

# --- Debugging Endpoints (สำหรับตรวจสอบปัญหา) ---
@bp.route('/_debug_url_map')
@login_required 
def debug_url_map():
    """Returns a plain text representation of the current URL map."""
    current_app.logger.info("Accessed /tools/_debug_url_map endpoint.")
    output = io.StringIO()
    output.write("Flask URL Map:\n")
    output.write("----------------\n")
    for rule in current_app.url_map.iter_rules():
        methods = ','.join(rule.methods) if rule.methods else 'ANY'
        output.write(f"  Endpoint: {rule.endpoint}\n")
        output.write(f"  Rule: {rule.rule}\n")
        output.write(f"  Methods: {methods}\n")
        output.write(f"  Blueprint: {rule.endpoint.split('.')[0] if '.' in rule.endpoint else 'None'}\n")
        output.write("----------------\n")
    current_app.logger.debug("URL Map generated.")
    return Response(output.getvalue(), mimetype='text/plain')

@bp.route('/_debug_env_vars')
@login_required 
def debug_env_vars():
    """Returns selected environment variables for debugging. BE CAREFUL WITH SENSITIVE INFO!"""
    current_app.logger.info("Accessed /tools/_debug_env_vars endpoint.")
    sensitive_keys = [
        'FLASK_SECRET_KEY', 'GOOGLE_CLIENT_SECRET', 'LINE_CHANNEL_ACCESS_TOKEN', 
        'LINE_CHANNEL_SECRET', 'REFRESH_TOKEN' 
    ]
    env_data = {}
    for key, value in os.environ.items(): 
        if key in sensitive_keys:
            env_data[key] = '[REDACTED]'
        else:
            env_data[key] = value
    
    current_app.logger.debug("Environment variables data prepared.")
    return jsonify(env_data)

# --- End Debugging Endpoints ---


@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings_page():
    current_app.logger.info("Accessed /tools/settings page.")
    if request.method == 'POST':
        try:
            technician_list = json.loads(request.form.get('technician_list_json', '[]'))
            current_app.logger.debug(f"Received technician_list_json: {request.form.get('technician_list_json', '[]')}")
        except json.JSONDecodeError:
            flash('ข้อมูลช่างไม่ถูกต้อง (Invalid JSON)', 'danger')
            current_app.logger.error("Invalid JSON for technician_list_json received.")
            return redirect(url_for('tools.settings_page'))

        settings_data = {
            'report_times': {
                'appointment_reminder_hour_thai': int(request.form.get('appointment_reminder_hour', 7)),
                'outstanding_report_hour_thai': int(request.form.get('outstanding_report_hour', 20)),
                'customer_followup_hour_thai': int(request.form.get('customer_followup_hour', 9))
            },
            'line_recipients': {
                'admin_group_id': request.form.get('admin_group_id', '').strip(),
                'technician_group_id': request.form.get('technician_group_id', '').strip(),
                'manager_user_id': request.form.get('manager_user_id', '').strip()
            },
            'shop_info': {
                'contact_phone': request.form.get('shop_contact_phone', '').strip(),
                'line_id': request.form.get('shop_line_id', '').strip()
            },
            'technician_list': technician_list
        }

        if save_app_settings(settings_data):
            current_app.logger.info("Application settings saved. Attempting to run scheduler and backup settings.")
            run_scheduler()
            cache.clear()
            if backup_settings_to_drive():
                flash('บันทึกและสำรองการตั้งค่าไปที่ Google Drive เรียบร้อยแล้ว!', 'success')
                current_app.logger.info("Settings backed up to Google Drive.")
            else:
                flash('บันทึกการตั้งค่าสำเร็จ แต่สำรองไปที่ Google Drive ไม่สำเร็จ!', 'warning')
                current_app.logger.warning("Settings saved, but backup to Google Drive failed.")
        else:
            flash('เกิดข้อผิดพลาดในการบันทึกการตั้งค่า!', 'danger')
            current_app.logger.error("Error saving application settings.")
        return redirect(url_for('tools.settings_page'))

    current_settings = get_app_settings()
    current_app.logger.info("Rendering settings_page.html.")
    return render_template('settings_page.html', settings=current_settings)

@bp.route('/test_notification', methods=['POST'])
@login_required
def test_notification():
    """Sends a test message to the admin LINE group."""
    current_app.logger.info("test_notification route called.")
    if send_test_notification():
        flash('ส่งข้อความทดสอบไปยัง LINE Admin Group สำเร็จ!', 'success')
        current_app.logger.info("Test LINE notification sent successfully.")
    else:
        flash('ไม่สามารถส่งข้อความทดสอบได้ โปรดตรวจสอบ LINE Admin Group ID และลองอีกครั้ง', 'danger')
        current_app.logger.error("Failed to send test LINE notification.")
    return redirect(url_for('tools.settings_page'))

@bp.route('/backup_data')
@login_required
def backup_data():
    """Creates and downloads a full system backup zip file."""
    current_app.logger.info("backup_data route called (download full backup).")
    memory_file, filename = _create_backup_zip()
    if memory_file and filename:
        current_app.logger.info(f"Full backup zip '{filename}' created successfully. Sending file.")
        return send_file(
            memory_file,
            as_attachment=True,
            download_name=filename,
            mimetype='application/zip'
        )
    else:
        flash("ไม่สามารถสร้างไฟล์ Backup ได้", "danger")
        current_app.logger.error("Failed to create full backup zip file.")
        return redirect(url_for('tools.settings_page'))

@bp.route('/trigger_auto_backup_now', methods=['POST'])
@login_required
def trigger_auto_backup_now():
    """Manually triggers the scheduled backup job."""
    current_app.logger.info("trigger_auto_backup_now route called (manual backup to Drive).")
    success = scheduled_backup_job()
    if success:
        flash("การสำรองข้อมูลไปยัง Google Drive เสร็จสมบูรณ์!", "success")
        current_app.logger.info("Manual backup to Google Drive completed successfully.")
    else:
        flash("เกิดข้อผิดพลาดระหว่างการสำรองข้อมูลไปยัง Google Drive!", "danger")
        current_app.logger.error("Manual backup to Google Drive failed.")
    return redirect(url_for('tools.settings_page'))


@bp.route('/technician_report')
@login_required
def technician_report():
    current_app.logger.info("Accessed /tools/technician_report page.")
    user_creds_dict = session.get('credentials')
    now = datetime.datetime.now(pytz.timezone('Asia/Bangkok'))
    try:
        year = int(request.args.get('year', now.year))
        month = int(request.args.get('month', now.month))
    except (ValueError, TypeError):
        year, month = now.year, now.month
    
    months = [{'value': i, 'name': datetime.date(2000, i, 1).strftime('%B')} for i in range(1, 13)]
    
    app_settings = get_app_settings()
    technician_list = app_settings.get('technician_list', []) # List of all technicians from settings

    tasks = get_google_tasks_for_report(show_completed=True, credentials=user_creds_dict) or []
    
    technician_summary = defaultdict(lambda: {
        'tasks_completed': [],
        'total_completed_count': 0,
        'equipment_used': defaultdict(int) # Counts equipment used by this tech
    })

    # Process all tasks to build the technician summary
    for task_raw in tasks:
        # Check if task is completed and in the selected month/year
        if task_raw.get('status') == 'completed' and task_raw.get('completed'):
            try:
                completed_dt = date_parse(task_raw['completed']).astimezone(pytz.timezone('Asia/Bangkok'))
                if completed_dt.year == year and completed_dt.month == month:
                    
                    task = parse_google_task_dates(task_raw) # Parse dates for display in template
                    customer_info = parse_customer_info_from_notes(task.get('notes', ''))
                    tech_history, _ = parse_tech_report_from_notes(task.get('notes', ''))

                    task_techs = set()
                    
                    for report_entry in tech_history:
                        for t_name in report_entry.get('technicians', []):
                            if isinstance(t_name, str):
                                task_techs.add(t_name.strip())
                        
                        # --- Logic to parse equipment from report_entry (conceptual) ---
                        # This part needs custom parsing based on how 'equipment_used_display' or other equipment info is stored
                        # For example, if it's a string like "Item1: 2, Item2: 1", you'd parse it here
                        # if 'equipment_used_display' in report_entry and isinstance(report_entry['equipment_used_display'], str):
                        #     # Example parsing: "Item1: 2, Item2: 1" -> {'Item1': 2, 'Item2': 1}
                        #     # This part is highly dependent on your actual data format in notes
                        #     pass 
                        # --- End of equipment parsing logic ---

                    task_display_data = {
                        'id': task.get('id'),
                        'title': task.get('title'),
                        'customer_name': customer_info.get('name', 'N/A'),
                        'completed_formatted': completed_dt.strftime("%d/%m/%Y %H:%M"),
                        'latest_report_summary': task.get('latest_report_summary', 'ไม่มีสรุป') 
                        # 'equipment_used': parsed_equipment_for_this_task # if you parse it
                    }
                    
                    for tech_name in task_techs:
                        technician_summary[tech_name]['tasks_completed'].append(task_display_data)
                        technician_summary[tech_name]['total_completed_count'] += 1
                        # If you parsed equipment for this task, add it to the tech's summary
                        # for item, count in task_equipment_used.items():
                        #    technician_summary[tech_name]['equipment_used'][item] += count
                        
            except Exception as e:
                current_app.logger.error(f"Error processing task {task_raw.get('id')} for technician report: {e}", exc_info=True)
                continue
    
    # Sort technicians alphabetically
    sorted_technician_summary = dict(sorted(technician_summary.items()))

    # Render the card-based template for technician report
    return render_template(
        'technician_report_cards.html', # <--- เปลี่ยนชื่อเทมเพลตเป็นชื่อที่คุณใช้สำหรับ Card Layout
        technician_summary=sorted_technician_summary,
        selected_year=year,
        selected_month=month,
        months=months,
        years=list(range(now.year - 5, now.year + 2)),
        technician_list=technician_list # Full list of all technicians from settings
    )

@bp.route('/manage_duplicates')
@login_required
def manage_duplicates():
    current_app.logger.info("Accessed /tools/manage_duplicates page.")
    user_creds_dict = session.get('credentials')
    tasks = get_google_tasks_for_report(show_completed=True, credentials=user_creds_dict) or []
    duplicates = defaultdict(list)
    for task in tasks:
        if task.get('title'):
            customer_name = parse_customer_info_from_notes(task.get('notes', '')).get('name', '').strip().lower()
            key = (task['title'].strip(), customer_name)
            duplicates[key].append(task)
    
    potential_duplicate_sets = {k: sorted(v, key=lambda t: t.get('created', ''), reverse=True) for k, v in duplicates.items() if len(v) > 1}
    return render_template('manage_duplicates.html', duplicates=potential_duplicate_sets)

@bp.route('/delete_task_duplicates', methods=['POST'])
@login_required
def delete_task_duplicates():
    current_app.logger.info("delete_task_duplicates route called.")
    user_creds_dict = session.get('credentials')
    task_ids_to_delete = request.form.getlist('task_ids')
    deleted_count = 0
    for task_id in task_ids_to_delete:
        if delete_google_task(task_id, credentials=user_creds_dict):
            deleted_count += 1
    flash(f"ลบงานที่ซ้ำซ้อนออกไป {deleted_count} รายการเรียบร้อยแล้ว", "success")
    cache.clear()
    current_app.logger.info(f"Deleted {deleted_count} duplicate tasks.")
    return redirect(url_for('tools.manage_duplicates'))


@bp.route('/manage_equipment_duplicates')
@login_required
def manage_equipment_duplicates():
    current_app.logger.info("Accessed /tools/manage_equipment_duplicates page.")
    catalog = get_app_settings().get('equipment_catalog', [])
    duplicates = defaultdict(list)
    # Enumerate the original catalog to get indices
    for i, item in enumerate(catalog):
        name = item.get('item_name', '').strip().lower()
        if name:
            # Store the original index along with the item data
            duplicates[name].append({'original_index': i, 'data': item})
    
    # Filter for items that have more than one entry
    duplicate_sets = {k: sorted(v, key=lambda x: x['original_index']) for k, v in duplicates.items() if len(v) > 1}
    return render_template('equipment_duplicates.html', duplicates=duplicate_sets)

@bp.route('/delete_equipment_duplicates_batch', methods=['POST'])
@login_required
def delete_equipment_duplicates_batch():
    current_app.logger.info("delete_equipment_duplicates_batch route called.")
    indices_to_delete = request.form.getlist('item_indices')
    if not indices_to_delete:
        flash("กรุณาเลือกรายการที่ต้องการลบ", "warning")
        current_app.logger.warning("No item indices selected for deletion.")
        return redirect(url_for('tools.manage_equipment_duplicates'))

    # Convert indices from string to int and sort them in descending order
    # to avoid index shifting issues during deletion.
    indices_to_delete = sorted([int(i) for i in indices_to_delete], reverse=True)
    
    current_settings = get_app_settings()
    equipment_catalog = current_settings.get('equipment_catalog', [])
    
    deleted_count = 0
    for index in indices_to_delete:
        if 0 <= index < len(equipment_catalog):
            equipment_catalog.pop(index)
            deleted_count += 1
            
    current_settings['equipment_catalog'] = equipment_catalog
    if save_app_settings(current_settings):
        flash(f"ลบรายการอุปกรณ์ที่ซ้ำซ้อนออกไป {deleted_count} รายการเรียบร้อยแล้ว", "success")
        current_app.logger.info(f"Deleted {deleted_count} duplicate equipment items.")
    else:
        flash("เกิดข้อผิดพลาดในการบันทึกข้อมูลอุปกรณ์", "danger")
        current_app.logger.error("Error saving equipment catalog after deleting duplicates.")

    return redirect(url_for('tools.manage_equipment_duplicates'))


@bp.route("/organize_files", methods=['GET', 'POST'])
@login_required
def organize_files():
    current_app.logger.info("Accessed /tools/organize_files page.")
    user_creds_dict = session.get('credentials')
    if request.method == 'POST':
        flash('เริ่มการจัดระเบียบไฟล์... กระบวนการนี้อาจใช้เวลาสักครู่', 'info')
        # This part should be implemented, possibly as a background task
        # from .google_services import run_file_organization_logic
        # success, message = run_file_organization_logic(credentials=user_creds_dict)
        # flash(message, 'success' if success else 'danger')
        flash('ฟังก์ชันจัดระเบียบไฟล์ยังไม่ถูกพัฒนา', 'warning')
        current_app.logger.warning("File organization function is not yet implemented.")
        return redirect(url_for('tools.settings_page'))

    return render_template('organize_files.html')