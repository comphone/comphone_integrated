# comphone/main_routes.py

import datetime
import json
import functools
from collections import defaultdict
from flask import Blueprint, request, render_template, redirect, url_for, flash, session, current_app, Response
from dateutil.parser import parse as date_parse
import pytz
import os 
from google_auth_oauthlib.flow import Flow 
from google.oauth2.credentials import Credentials 
from google.auth.transport.requests import Request 
from googleapiclient.discovery import build

# Local imports
from .google_services import (
    get_google_tasks_for_report, get_single_task, create_google_task,
    update_google_task, check_google_api_status, create_or_update_calendar_event
)
from .utils import (
    parse_customer_info_from_notes, parse_tech_report_from_notes,
    parse_google_task_dates, THAILAND_TZ, TEXT_SNIPPETS,
    generate_qr_code_base64, parse_customer_feedback_from_notes
)
from .settings_manager import get_app_settings
from .line_handler import send_new_task_notification

# สร้าง Blueprint ชื่อ 'main'
bp = Blueprint('main', __name__)

# --- Login Required Decorator ---
def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'credentials' not in session:
            current_app.logger.warning(f"Access denied: User not logged in for {request.path}")
            flash('กรุณาเข้าสู่ระบบด้วยบัญชี Google ของคุณ', 'info')
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes หลัก ---
@bp.route('/login')
def login():
    # ตรวจสอบว่ามี credentials ใน session แล้วหรือไม่
    if 'credentials' in session:
        current_app.logger.info("User already has credentials, redirecting to summary.")
        return redirect(url_for('main.summary'))

    # หากยังไม่มี ให้เริ่มกระบวนการ OAuth
    client_config = {
        "web": {
            "client_id": os.environ.get('GOOGLE_CLIENT_ID'),
            "project_id": "comphone-integrated-system", # หรือชื่อ Project ID จริงของคุณ
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": os.environ.get('GOOGLE_CLIENT_SECRET'),
            "redirect_uris": [url_for('main.callback', _external=True)],
            "javascript_origins": ["https://comphone-integrated.onrender.com"] # เพิ่ม URL ของคุณ
        }
    }

    # กำหนด SCOPES ที่ต้องการ
    SCOPES = [
        'https://www.googleapis.com/auth/tasks',
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/drive',
        'openid', 
        'email',
        'profile'
    ]

    # สร้าง Flow instance
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=url_for('main.callback', _external=True)
    )

    # สร้าง Authorization URL และ Redirect ผู้ใช้ไปที่ Google
    authorization_url, state = flow.authorization_url(
        access_type='offline', # เพื่อให้ได้ refresh_token
        include_granted_scopes='true'
    )
    session['state'] = state # เก็บ state ไว้ตรวจสอบความปลอดภัย
    session['google_client_config'] = client_config # เก็บ config ไว้ใช้ใน callback

    current_app.logger.info(f"Redirecting to Google for OAuth. Authorization URL: {authorization_url}")
    return redirect(authorization_url)


@bp.route('/callback')
def callback():
    current_app.logger.info("Accessed /callback endpoint (Google OAuth callback).")
    state = session.get('state')
    google_client_config = session.get('google_client_config')

    if not state or not google_client_config:
        flash('เกิดข้อผิดพลาดในการตรวจสอบสถานะการล็อกอิน', 'danger')
        current_app.logger.error("State or client config missing from session during OAuth callback.")
        return redirect(url_for('main.login'))

    # สร้าง Flow instance ใหม่จาก session
    flow = Flow.from_client_config(
        google_client_config,
        scopes=None, # ไม่ต้องระบุ scopes ซ้ำ
        state=state,
        redirect_uri=url_for('main.callback', _external=True)
    )

    try:
        # แลกเปลี่ยน Authorization Code เป็น Access Token
        flow.fetch_token(authorization_response=request.url)

        credentials = flow.credentials
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }

        oauth2_service = build('oauth2', 'v2', credentials=credentials)
        user_info = oauth2_service.userinfo().get().execute()

        session['profile'] = {
            'id': user_info['id'],
            'email': user_info['email'],
            'name': user_info.get('name', user_info['email']),
            'picture': user_info.get('picture', '')
        }

        current_app.logger.info(f"User {user_info.get('email')} logged in successfully.")
        flash('เข้าสู่ระบบสำเร็จ!', 'success')
        return redirect(url_for('main.summary'))

    except Exception as e:
        flash(f'การล็อกอินล้มเหลว: {e}', 'danger')
        current_app.logger.error(f"Error during OAuth token exchange or user info fetch: {e}", exc_info=True)
        return redirect(url_for('main.login'))


@bp.route('/logout')
def logout():
    session.pop('credentials', None)
    session.pop('profile', None)
    flash('คุณได้ออกจากระบบแล้ว', 'success')
    current_app.logger.info("User logged out.")
    return redirect(url_for('main.login'))

@bp.route('/')
def root_redirect():
    return redirect(url_for('main.summary'))

@bp.route('/summary')
@login_required
def summary():
    current_app.logger.info("Accessed /summary page.")
    user_creds_dict = session.get('credentials')

    status_filter = request.args.get('status_filter', 'today')
    search_query = request.args.get('search_query', '').strip() 
    current_app.logger.debug(f"Summary page with status_filter: {status_filter}, search_query: '{search_query}'")

    all_tasks = get_google_tasks_for_report(show_completed=True, credentials=user_creds_dict)

    if not all_tasks:
        current_app.logger.warning("No tasks fetched from Google Tasks. Displaying empty dashboard.")
        return render_template(
            'dashboard.html',
            tasks=[],
            status_filter=status_filter,
            total_tasks=0,
            completed_tasks=0,
            needs_action_tasks=0,
            today_tasks_count=0,
            chart_data={'labels': [], 'values': []},
            search_query=search_query
        )


    # --- คำนวณสถิติสำหรับ Dashboard (จาก all_tasks) ---
    # โค้ดส่วนนี้ถูกต้องแล้ว ไม่ต้องแก้
    # total_tasks, completed_tasks, needs_action_tasks, today_tasks_count

    processed_tasks = []
    now_thai = datetime.datetime.now(THAILAND_TZ)

    # ประมวลผล tasks ทั้งหมดเพื่อเพิ่มข้อมูลที่จำเป็นสำหรับเทมเพลตและ filter
    for task_raw in all_tasks:
        task = parse_google_task_dates(task_raw)

        task['due_date_obj'] = None
        if task.get('due'):
            try:
                task['due_date_obj'] = date_parse(task['due'].replace('Z', '+00:00')).astimezone(THAILAND_TZ)
            except (ValueError, TypeError) as e:
                current_app.logger.warning(f"Error parsing due date for task {task.get('id')}: {task.get('due')}. Error: {e}", exc_info=True)
                task['due_date_obj'] = None

        customer_info = parse_customer_info_from_notes(task.get('notes', ''))
        task['customer_name'] = customer_info.get('name', 'N/A')
        task['customer_phone'] = customer_info.get('phone', 'N/A')
        task['customer_address'] = customer_info.get('address', 'N/A')
        task['customer_organization'] = customer_info.get('organization', 'N/A')
        task['customer_map_url'] = customer_info.get('map_url')

        tech_history, original_notes = parse_tech_report_from_notes(task.get('notes', ''))
        task['tech_reports'] = tech_history
        task['original_notes'] = original_notes
        if tech_history:
            task['latest_report_summary'] = tech_history[0].get('work_summary', 'ไม่มีสรุป')
            task['latest_report_date'] = tech_history[0].get('summary_date')
            task['latest_report_type'] = tech_history[0].get('type')
        else:
            task['latest_report_summary'] = 'ยังไม่มีรายงาน'
            task['latest_report_date'] = None
            task['latest_report_type'] = None

        # Add is_overdue and is_today flags for template use
        task['is_overdue'] = False
        task['is_today'] = False
        if task.get('status') == 'needsAction' and task['due_date_obj']:
            if task['due_date_obj'].date() < now_thai.date():
                task['is_overdue'] = True
            elif task['due_date_obj'].date() == now_thai.date():
                task['is_today'] = True

        processed_tasks.append(task)

    # Recalculate summary counts from processed_tasks
    total_tasks = len(processed_tasks)
    completed_tasks = sum(1 for task in processed_tasks if task.get('status') == 'completed')
    needs_action_tasks = sum(1 for task in processed_tasks if task.get('status') == 'needsAction')
    today_tasks_count = sum(1 for task in processed_tasks if task['is_today'])

    # --- Filter tasks based on status_filter AND search_query ---
    filtered_tasks_for_display = [] 
    for task in processed_tasks:
        status_match = False
        if status_filter == 'needsAction': # Filter for all needsAction tasks
            if task.get('status') == 'needsAction':
                status_match = True
        elif status_filter == 'today':
            if task['is_today']:
                status_match = True
        elif status_filter == 'outstanding':
            if task['is_overdue']:
                status_match = True
        elif status_filter == 'upcoming':
            if task.get('status') == 'needsAction' and task['due_date_obj'] and task['due_date_obj'].date() > now_thai.date():
                status_match = True
        elif status_filter == 'completed':
            if task.get('status') == 'completed':
                status_match = True
        elif status_filter == 'all': # This 'all' status filter case must handle all tasks regardless of status
            status_match = True
        else: # Default to today if filter is invalid
            if task['is_today']:
                status_match = True

        if status_match:
            if search_query:
                search_text = f"{task.get('title', '')} {task.get('customer_name', '')} {task.get('customer_organization', '')} {task.get('customer_phone', '')} {task.get('customer_address', '')}".lower()
                if search_query.lower() in search_text:
                    filtered_tasks_for_display.append(task)
            else:
                filtered_tasks_for_display.append(task) 

    # Sort tasks for display in the table
    filtered_tasks_for_display.sort(key=lambda t: (
        0 if t['is_overdue'] else 
        1 if t['is_today'] else 
        2 if t.get('status') == 'needsAction' else 
        3 if t.get('status') == 'completed' else 4, 
        t['due_date_obj'] if t.get('due_date_obj') else datetime.datetime.max.replace(tzinfo=pytz.utc), 
        date_parse(t.get('completed', '0001-01-01T00:00:00Z')) if t.get('completed') else datetime.datetime.min.replace(tzinfo=pytz.utc), 
        date_parse(t.get('created', '0001-01-01T00:00:00Z')) 
    ))

    # --- คำนวณข้อมูลสำหรับ Chart (กราฟสรุปรายเดือน) ---
    monthly_completed_counts = defaultdict(int)
    for task in processed_tasks: 
        if task.get('status') == 'completed' and task.get('completed'):
            try:
                completed_month = date_parse(task['completed']).astimezone(THAILAND_TZ).strftime('%Y-%m')
                monthly_completed_counts[completed_month] += 1
            except (ValueError, TypeError) as e:
                current_app.logger.warning(f"Error parsing completed date for chart: {task.get('completed')}. Error: {e}", exc_info=True)

    sorted_months = sorted(monthly_completed_counts.keys())
    chart_labels = [datetime.datetime.strptime(m, '%Y-%m').strftime('%b %Y') for m in sorted_months]
    chart_values = [monthly_completed_counts[m] for m in sorted_months]

    chart_data = {
        'labels': chart_labels,
        'values': chart_values
    }

    current_app.logger.info(f"Displaying {len(filtered_tasks_for_display)} tasks for filter: {status_filter} after search.")

    return render_template(
        'dashboard.html', 
        tasks=filtered_tasks_for_display, # ส่ง tasks ที่ถูก filter แล้ว
        status_filter=status_filter,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        needs_action_tasks=needs_action_tasks,
        today_tasks_count=today_tasks_count,
        chart_data=chart_data,
        search_query=search_query 
    )

@bp.route('/summary/print')
@login_required
def summary_print():
    current_app.logger.info("Accessed /summary/print page.")
    user_creds_dict = session.get('credentials')

    all_tasks = get_google_tasks_for_report(show_completed=True, credentials=user_creds_dict)
    printable_tasks = []

    for task_raw in all_tasks:
        task = parse_google_task_dates(task_raw)

        task['due_date_obj'] = None
        if task.get('due'):
            try:
                task['due_date_obj'] = date_parse(task['due'].replace('Z', '+00:00')).astimezone(THAILAND_TZ)
            except (ValueError, TypeError) as e:
                current_app.logger.warning(f"Error parsing due date for task {task.get('id')} in summary_print: {task.get('due')}. Error: {e}", exc_info=True)
                task['due_date_obj'] = None

        customer_info = parse_customer_info_from_notes(task.get('notes', ''))
        task['customer_name'] = customer_info.get('name', 'N/A')
        task['customer_phone'] = customer_info.get('phone', 'N/A')
        task['customer_address'] = customer_info.get('address', 'N/A')
        task['customer_organization'] = customer_info.get('organization', 'N/A')
        task['customer_map_url'] = customer_info.get('map_url')

        tech_history, original_notes = parse_tech_report_from_notes(task.get('notes', ''))
        task['tech_reports'] = tech_history
        task['original_notes'] = original_notes

        printable_tasks.append(task)

    printable_tasks.sort(key=lambda t: date_parse(t.get('created', '0')))

    current_app.logger.info(f"Displaying {len(printable_tasks)} tasks for printing.")
    return render_template('summary_print.html', tasks=printable_tasks)


@bp.route('/form', methods=['GET', 'POST'])
@login_required
def form_page():
    current_app.logger.info("Accessed /form page.")
    if request.method == 'POST':
        user_creds_dict = session.get('credentials')
        title = request.form['title']
        customer_name = request.form.get('customer_name', '').strip()
        customer_phone = request.form.get('customer_phone', '').strip()
        customer_address = request.form.get('customer_address', '').strip()
        customer_org = request.form.get('customer_org', '').strip()
        map_url = request.form.get('map_url', '').strip()
        description = request.form.get('description', '').strip()
        technicians_json = request.form.get('technicians_create')

        due_date_str = request.form.get('due_date')
        due_date_gmt = None
        if due_date_str:
            try:
                dt_local = THAILAND_TZ.localize(date_parse(due_date_str))
                due_date_gmt = dt_local.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')
            except ValueError:
                flash('รูปแบบวันและเวลาไม่ถูกต้อง', 'danger')
                current_app.logger.warning(f"Invalid due date format received: {due_date_str}")
                return redirect(url_for('main.form_page'))

        notes = f"ลูกค้า: {customer_name}\n"
        if customer_org:
            notes += f"หน่วยงาน: {customer_org}\n"
        if customer_phone:
            notes += f"เบอร์โทรศัพท์: {customer_phone}\n"
        if customer_address:
            notes += f"ที่อยู่: {customer_address}\n"
        if map_url:
            notes += f"แผนที่: {map_url}\n"
        if description:
            notes += f"รายละเอียด: {description}\n"

        technicians = []
        if technicians_json:
            try:
                technicians = json.loads(technicians_json)
                tech_names = ", ".join([t.get('name', 'N/A') for t in technicians])
                if tech_names:
                    notes += f"ช่างผู้รับผิดชอบ: {tech_names}\n"
            except json.JSONDecodeError:
                current_app.logger.error(f"Invalid JSON for technicians_create: {technicians_json}")
                flash('ข้อมูลช่างไม่ถูกต้อง (Invalid JSON)', 'danger')
                return redirect(url_for('main.form_page'))

        try:
            current_app.logger.info(f"Attempting to create Google Task: {title}")
            new_task = create_google_task(title, notes=notes, due=due_date_gmt, credentials=user_creds_dict)
            if new_task:
                create_or_update_calendar_event(new_task, credentials=user_creds_dict)
                send_new_task_notification(new_task, technicians)

                flash('สร้างงานใหม่สำเร็จ!', 'success')
                current_app.logger.info(f"New task created successfully: {new_task.get('id')}")
                return redirect(url_for('main.summary'))
            else:
                flash('ไม่สามารถสร้างงานใหม่ได้ โปรดลองอีกครั้ง', 'danger')
                current_app.logger.error("Failed to create new Google Task.")
        except Exception as e:
            flash(f'เกิดข้อผิดพลาดในการสร้างงาน: {e}', 'danger')
            current_app.logger.error(f"Exception during new task creation: {e}", exc_info=True)

    return render_template('form.html', task_detail_snippets=TEXT_SNIPPETS.get('task_details', []))

@bp.route('/task/<task_id>')
@login_required
def task_details(task_id):
    current_app.logger.info(f"Accessed /task/{task_id} details page.")
    user_creds_dict = session.get('credentials')
    task_raw = get_single_task(task_id, credentials=user_creds_dict)

    if not task_raw:
        flash('ไม่พบงานนี้', 'danger')
        current_app.logger.warning(f"Task {task_id} not found.")
        return redirect(url_for('main.summary'))

    task = parse_google_task_dates(task_raw)

    # --- แก้ไขตรงนี้: เก็บ customer_info ลงใน task['customer_info'] object เพื่อให้ template เข้าถึงได้ ---
    customer_info = parse_customer_info_from_notes(task.get('notes', ''))
    task['customer_info'] = customer_info # <--- เพิ่มบรรทัดนี้
    task['customer_name'] = customer_info.get('name', 'N/A')
    task['customer_phone'] = customer_info.get('phone', 'N/A')
    task['customer_address'] = customer_info.get('address', 'N/A')
    task['customer_organization'] = customer_info.get('organization', 'N/A')
    task['customer_map_url'] = customer_info.get('map_url')

    tech_history, original_notes_text = parse_tech_report_from_notes(task.get('notes', ''))
    task['tech_reports'] = tech_history
    task['original_notes_clean'] = original_notes_text

    all_attachments = []
    for report in tech_history:
        if report.get('attachments'):
            all_attachments.extend(report['attachments'])

    app_settings = get_app_settings()

    return render_template('update_task_details.html', task=task, technician_list=app_settings.get('technician_list', []), all_attachments=all_attachments, progress_report_snippets=TEXT_SNIPPETS.get('progress_reports', []))

@bp.route('/edit_task/<task_id>', methods=['GET', 'POST']) # <--- เพิ่ม GET ที่นี่
@login_required
def edit_task(task_id):
    if request.method == 'GET':
        current_app.logger.info(f"Accessed /edit_task/{task_id} page (GET).")
        user_creds_dict = session.get('credentials')
        task_raw = get_single_task(task_id, credentials=user_creds_dict)
        if not task_raw:
            flash('ไม่พบงานนี้', 'danger')
            return redirect(url_for('main.summary'))
        task = parse_google_task_dates(task_raw) # Parse dates for display in form
        customer_info = parse_customer_info_from_notes(task.get('notes', ''))
        # Pass existing customer data to pre-fill the form
        return render_template('edit_task.html', task=task, customer_info=customer_info) # You'll need an edit_task.html template

    if request.method == 'POST': # This is the existing POST logic
        current_app.logger.info(f"Accessed /edit_task/{task_id} (POST) endpoint.")
        user_creds_dict = session.get('credentials')
        title = request.form['title']
        notes = request.form.get('notes', '')

        due_date_str = request.form.get('due_date_edit')
        due_date_gmt = None
        if due_date_str:
            try:
                dt_local = THAILAND_TZ.localize(date_parse(due_date_str))
                due_date_gmt = dt_local.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')
            except ValueError:
                flash('รูปแบบวันและเวลาไม่ถูกต้อง', 'danger')
                current_app.logger.warning(f"Invalid due date format for task {task_id}: {due_date_str}")
                return redirect(url_for('main.task_details', task_id=task_id))

        try:
            current_app.logger.info(f"Attempting to update task {task_id}.")
            updated_task = update_google_task(task_id, title=title, notes=notes, due=due_date_gmt, credentials=user_creds_dict)
            if updated_task:
                create_or_update_calendar_event(updated_task, credentials=user_creds_dict)
                flash('อัปเดตงานเรียบร้อยแล้ว!', 'success')
                current_app.logger.info(f"Task {task_id} updated successfully.")
            else:
                flash('ไม่สามารถอัปเดตงานได้ โปรดลองอีกครั้ง', 'danger')
                current_app.logger.error(f"Failed to update task {task_id}.")
        except Exception as e:
            flash(f'เกิดข้อผิดพลาดในการอัปเดตงาน: {e}', 'danger')
            current_app.logger.error(f"Exception during task update for {task_id}: {e}", exc_info=True)

        return redirect(url_for('main.task_details', task_id=task_id))


@bp.route('/calendar')
@login_required
def calendar_view():
    current_app.logger.info("Accessed /calendar page.")
    return render_template('calendar.html')

@bp.route('/customer_onboarding/<task_id>')
def customer_onboarding_page(task_id):
    current_app.logger.info(f"Accessed /customer_onboarding/{task_id} page.")
    task_raw = get_single_task(task_id, credentials=session.get('credentials'))

    if not task_raw:
        current_app.logger.warning(f"Task {task_id} not found for customer onboarding page.")
        return "งานไม่พบหรือไม่สามารถเข้าถึงได้", 404

    task = parse_google_task_dates(task_raw)
    customer_info = parse_customer_info_from_notes(task.get('notes', ''))
    task['customer_name'] = customer_info.get('name', 'N/A')
    task['customer_phone'] = customer_info.get('phone', 'N/A')
    task['customer_address'] = customer_info.get('address', 'N/A')
    task['customer_organization'] = customer_info.get('organization', 'N/A')
    task['customer_map_url'] = customer_info.get('map_url')

    tech_history, original_notes_text = parse_tech_report_from_notes(task.get('notes', ''))
    task['tech_reports'] = tech_history
    task['original_notes_clean'] = original_notes_text

    all_attachments = []
    for report in tech_history:
        if report.get('attachments'):
            all_attachments.extend(report['attachments'])

    return render_template('customer_onboarding.html', 
                           task=task, 
                           customer_info=customer_info, 
                           tech_reports=tech_history,
                           all_attachments=all_attachments,
                           customer_feedback=customer_feedback)

@bp.route('/generate_customer_onboarding_qr/<task_id>')
@login_required
def generate_customer_onboarding_qr(task_id):
    current_app.logger.info(f"Accessed /generate_customer_onboarding_qr/{task_id} endpoint.")
    onboarding_url = url_for('main.customer_onboarding_page', task_id=task_id, _external=True)
    current_app.logger.debug(f"QR Code URL: {onboarding_url}")

    qr_code_data = generate_qr_code_base64(onboarding_url)
    if qr_code_data:
        current_app.logger.info(f"QR Code for task {task_id} generated successfully.")
        return Response(qr_code_data, mimetype="text/plain")
    else:
        current_app.logger.error(f"Failed to generate QR Code for task {task_id}.")
        return "ไม่สามารถสร้าง QR Code ได้", 500

@bp.route('/generate_public_report_qr/<task_id>')
@login_required
def generate_public_report_qr(task_id):
    current_app.logger.info(f"Accessed /generate_public_report_qr/{task_id} endpoint.")
    public_report_url = url_for('main.customer_onboarding_page', task_id=task_id, _external=True)
    current_app.logger.debug(f"Public Report QR Code URL: {public_report_url}")

    qr_code_data = generate_qr_code_base64(public_report_url)
    if qr_code_data:
        current_app.logger.info(f"QR Code for task {task_id} generated successfully.")
        return Response(qr_code_data, mimetype="text/plain")
    else:
        current_app.logger.error(f"Failed to generate QR Code for task {task_id}.")
        return "ไม่สามารถสร้าง QR Code ได้", 500