# comphone/utils.py

import re
import os
import json
import datetime
import pytz
import base64
import zipfile
from io import BytesIO
from dateutil.parser import parse as date_parse
import qrcode
from flask import url_for, session, current_app, Response # เพิ่ม Response เพื่อใช้กับ _create_backup_zip ในบางกรณี

from linebot.models import (
    BubbleContainer, BoxComponent, TextComponent, ButtonComponent,
    SeparatorComponent, URIAction
)

# --- ค่าคงที่ (Constants) ---
THAILAND_TZ = pytz.timezone('Asia/Bangkok')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'kmz', 'kml'}
TEXT_SNIPPETS = {
    'task_details': [
        {'key': 'ล้างแอร์', 'value': 'ล้างทำความสะอาดเครื่องปรับอากาศ, ตรวจเช็คน้ำยา, วัดแรงดันไฟฟ้า และทำความสะอาดคอยล์ร้อน-เย็น'},
        {'key': 'ติดตั้งแอร์', 'value': 'ติดตั้งเครื่องปรับอากาศใหม่ ขนาด [ขนาด BTU] พร้อมเดินท่อน้ำยาและสายไฟ, ติดตั้งเบรกเกอร์'},
        {'key': 'ซ่อมตู้เย็น', 'value': 'ซ่อมตู้เย็น [ยี่ห้อ/รุ่น] อาการไม่เย็น, ตรวจสอบคอมเพรสเซอร์และน้ำยา'},
        {'key': 'ตรวจเช็ค', 'value': 'เข้าตรวจเช็คอาการเสียเบื้องต้นตามที่ลูกค้าแจ้ง'}
    ],
    'progress_reports': [
        {'key': 'ลูกค้าเลื่อนนัด', 'value': 'ลูกค้าขอเลื่อนนัดเป็นวันที่ [dd/mm/yyyy] เนื่องจากไม่สะดวก'},
        {'key': 'รออะไหล่', 'value': 'ตรวจสอบแล้วพบว่าต้องรออะไหล่ [ชื่ออะไหล่] จะแจ้งลูกค้าให้ทราบกำหนดการอีกครั้ง'},
        {'key': 'เข้าพื้นที่ไม่ได้', 'value': 'ไม่สามารถเข้าพื้นที่ได้เนื่องจาก [เหตุผล] ได้โทรแจ้งลูกค้าแล้ว'},
        {'key': 'เสร็จบางส่วน', 'value': 'ดำเนินการเสร็จสิ้นบางส่วน เหลือ [สิ่งที่ต้องทำต่อ] จะเข้ามาดำเนินการต่อในวันถัดไป'}
    ]
}

# --- ฟังก์ชันช่วยเหลือ (Helper Functions) ---

def sanitize_filename(name):
    """Removes invalid characters from a string to make it a valid filename."""
    if not name:
        return "Unnamed"
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def parse_customer_info_from_notes(notes):
    """Parses customer information from the notes string of a Google Task."""
    info = {'name': '', 'phone': '', 'address': '', 'map_url': None, 'organization': ''}
    if not notes:
        return info

    org_match = re.search(r"หน่วยงาน:\s*(.*)", notes, re.IGNORECASE)
    name_match = re.search(r"ลูกค้า:\s*(.*)", notes, re.IGNORECASE)
    phone_match = re.search(r"เบอร์โทรศัพท์:\s*(.*)", notes, re.IGNORECASE)
    address_match = re.search(r"ที่อยู่:\s*(.*)", notes, re.IGNORECASE)
    map_url_match = re.search(r"(https?:\/\/[^\s]+|(?:\-?\d+\.\d+,\s*\-?\d+\.\d+))", notes)

    if org_match: info['organization'] = org_match.group(1).strip().split(':')[-1].strip()
    if name_match: info['name'] = name_match.group(1).strip().split(':')[-1].strip()
    if phone_match: info['phone'] = phone_match.group(1).strip().split(':')[-1].strip()
    if address_match: info['address'] = address_match.group(1).strip().split(':')[-1].strip()

    if map_url_match:
        coords_or_url = map_url_match.group(1).strip()
        if re.match(r"^\-?\d+\.\d+,\s*\-?\d+\.\d+$", coords_or_url):
            info['map_url'] = f"https://maps.google.com/maps?q={coords_or_url}"
        else:
            info['map_url'] = coords_or_url

    return info

def parse_tech_report_from_notes(notes):
    """Parses technician reports embedded in the notes string."""
    if not notes:
        return [], ""
    report_blocks = re.findall(r"--- TECH_REPORT_START ---\s*\n(.*?)\n--- TECH_REPORT_END ---", notes, re.DOTALL)
    history = []
    for json_str in report_blocks:
        try:
            report_data = json.loads(json_str)
            history.append(report_data)
        except json.JSONDecodeError:
            current_app.logger.warning(f"Could not parse tech report JSON: {json_str}")
            pass

    temp_notes = re.sub(r"--- TECH_REPORT_START ---.*?--- TECH_REPORT_END ---", "", notes, flags=re.DOTALL)
    temp_notes = re.sub(r"--- CUSTOMER_FEEDBACK_START ---.*?--- CUSTOMER_FEEDBACK_END ---", "", temp_notes, flags=re.DOTALL)
    original_notes_text = temp_notes.strip()

    history.sort(key=lambda x: x.get('summary_date', '0000-00-00'), reverse=True)
    return history, original_notes_text

def parse_customer_feedback_from_notes(notes):
    """Parses customer feedback data embedded in the notes string."""
    feedback_data = {}
    if not notes:
        return feedback_data

    feedback_match = re.search(r"--- CUSTOMER_FEEDBACK_START ---\s*\n(.*?)\n--- CUSTOMER_FEEDBACK_END ---", notes, re.DOTALL)
    if feedback_match:
        try:
            feedback_data = json.loads(feedback_match.group(1))
        except json.JSONDecodeError:
            pass
    return feedback_data

def parse_google_task_dates(task_item):
    """Parses and formats date fields from a Google Task item."""
    parsed = task_item.copy()
    for key in ['created', 'due', 'completed']:
        if parsed.get(key):
            try:
                dt_utc = date_parse(parsed[key])
                parsed[f'{key}_formatted'] = dt_utc.astimezone(THAILAND_TZ).strftime("%d/%m/%y %H:%M")
                if key == 'due':
                    parsed['due_for_input'] = dt_utc.astimezone(THAILAND_TZ).strftime("%Y-%m-%dT%H:%M")
            except (ValueError, TypeError):
                current_app.logger.warning(f"Invalid date format for '{key}': {parsed[key]}")
                parsed[f'{key}_formatted'] = ''
                if key == 'due': parsed['due_for_input'] = ''
        else:
            parsed[f'{key}_formatted'] = ''
            if key == 'due': parsed['due_for_input'] = ''
    return parsed

def generate_qr_code_base64(data, box_size=10, border=4, fill_color='#28a745', back_color='#FFFFFF'):
    """Generates a base64-encoded QR code image string."""
    try:
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=box_size, border=border)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color=fill_color, back_color=back_color)
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        current_app.logger.error(f"Error generating QR code: {e}", exc_info=True)
        return ""

def _create_backup_zip():
    """Creates a zip file in memory containing system data and code."""
    from .google_services import get_google_tasks_for_report
    from .settings_manager import get_app_settings, SETTINGS_FILE

    current_app.logger.info("Starting _create_backup_zip function.")
    try:
        user_creds = session.get('credentials')
        if not user_creds:
            current_app.logger.error("Cannot create backup zip: User not logged in.")
            return None, None
            
        current_app.logger.debug("Fetching all Google Tasks for backup.")
        all_tasks = get_google_tasks_for_report(show_completed=True, credentials=user_creds)
        current_app.logger.debug("Fetching application settings for backup.")
        settings = get_app_settings()

        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            current_app.logger.debug("Writing tasks_backup.json to zip.")
            zf.writestr('data/tasks_backup.json', json.dumps(all_tasks or [], indent=4, ensure_ascii=False))
            current_app.logger.debug("Writing settings_backup.json to zip.")
            zf.writestr('data/settings_backup.json', json.dumps(settings, indent=4, ensure_ascii=False))

            project_root = os.path.dirname(os.path.abspath(__file__))
            parent_root = os.path.join(project_root, '..')
            current_app.logger.debug(f"Scanning project root for files to zip: {parent_root}")
            
            for folder, _, files in os.walk(parent_root):
                # Exclude virtual environments and cache folders
                if '__pycache__' in folder or 'venv' in folder or '.venv' in folder or '/instance' in folder: # เพิ่ม /instance
                    continue
                for file in files:
                    # Exclude sensitive files or large database files
                    if not file.endswith(('.token.json', '.env', '.sqlite3', '.db', '.pyc')):
                        file_path = os.path.join(folder, file)
                        try:
                            archive_name = os.path.relpath(file_path, parent_root)
                            zf.write(file_path, arcname=archive_name)
                            current_app.logger.debug(f"Added {archive_name} to zip.")
                        except Exception as e:
                            current_app.logger.warning(f"Could not add file {file_path} to zip: {e}")

        memory_file.seek(0)
        backup_filename = f"comphone_backup_{datetime.datetime.now(THAILAND_TZ).strftime('%Y%m%d_%H%M%S')}.zip"
        current_app.logger.info(f"Backup zip '{backup_filename}' created successfully.")
        return memory_file, backup_filename
    except Exception as e:
        current_app.logger.error(f"Error creating backup zip: {e}", exc_info=True)
        return None, None

def create_task_flex_message(task):
    """Creates a Flex Message bubble for a single task to be sent via LINE."""
    customer = parse_customer_info_from_notes(task.get('notes', ''))
    dates = parse_google_task_dates(task)
    return BubbleContainer(
        body=BoxComponent(layout='vertical', spacing='md', contents=[
            TextComponent(text=task.get('title', '...'), weight='bold', size='lg', wrap=True),
            SeparatorComponent(margin='md'),
            BoxComponent(layout='vertical', margin='lg', spacing='sm', contents=[
                BoxComponent(layout='baseline', spacing='sm', contents=[
                    TextComponent(text='ลูกค้า:', color='#AAAAAA', size='sm', flex=2),
                    TextComponent(text=customer.get('name', '-'), wrap=True, color='#666666', size='sm', flex=5)
                ]),
                BoxComponent(layout='baseline', spacing='sm', contents=[
                    TextComponent(text='นัดหมาย:', color='#AAAAAA', size='sm', flex=2),
                    TextComponent(text=dates.get('due_formatted', '-'), wrap=True, color='#666666', size='sm', flex=5)
                ])
            ]),
        ]),
        footer=BoxComponent(layout='vertical', spacing='sm', contents=[
            ButtonComponent(
                style='primary',
                height='sm',
                action=URIAction(label='📝 เปิดในเว็บ', uri=url_for('main.task_details', task_id=task['id'], _external=True))
            )
        ])
    )