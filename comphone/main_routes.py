# comphone/main_routes.py

import datetime
import json
import functools
from collections import defaultdict
from flask import Blueprint, request, render_template, redirect, url_for, flash, session, current_app
from dateutil.parser import parse as date_parse
import pytz
import os 
from google_auth_oauthlib.flow import Flow 
from google.oauth2.credentials import Credentials 
from google.auth.transport.requests import Request 
from googleapiclient.discovery import build

# Local imports
from .google_services import get_google_tasks_for_report, get_single_task, create_google_task, update_google_task, create_or_update_calendar_event
from .utils import parse_customer_info_from_notes, parse_tech_report_from_notes, parse_google_task_dates, THAILAND_TZ
from .settings_manager import get_app_settings

bp = Blueprint('main', __name__)

def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'credentials' not in session:
            flash('กรุณาเข้าสู่ระบบด้วยบัญชี Google ของคุณ', 'info')
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/login')
def login():
    if 'credentials' in session:
        return redirect(url_for('main.summary'))

    client_config = {
        "web": {
            "client_id": os.environ.get('GOOGLE_CLIENT_ID'),
            "project_id": "comphone-integrated-system",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": os.environ.get('GOOGLE_CLIENT_SECRET'),
            "redirect_uris": [url_for('main.callback', _external=True)],
        }
    }
    
    SCOPES = [
        'https://www.googleapis.com/auth/tasks', 'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/drive', 'openid', 'email', 'profile'
    ]

    flow = Flow.from_client_config(
        client_config, scopes=SCOPES, redirect_uri=url_for('main.callback', _external=True)
    )

    authorization_url, state = flow.authorization_url(
        access_type='offline', include_granted_scopes='true', prompt='consent'
    )
    session['state'] = state
    session['google_client_config'] = client_config
    return redirect(authorization_url)

@bp.route('/callback')
def callback():
    state = session.get('state')
    google_client_config = session.get('google_client_config')

    if not state or not google_client_config:
        flash('เกิดข้อผิดพลาดในการตรวจสอบสถานะการล็อกอิน', 'danger')
        return redirect(url_for('main.login'))

    flow = Flow.from_client_config(
        google_client_config, scopes=None, state=state, redirect_uri=url_for('main.callback', _external=True)
    )

    try:
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        session['credentials'] = {
            'token': credentials.token, 'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': google_client_config['web']['client_id'],
            'client_secret': google_client_config['web']['client_secret'],
            'scopes': credentials.scopes
        }

        oauth2_service = build('oauth2', 'v2', credentials=credentials)
        user_info = oauth2_service.userinfo().get().execute()
        session['profile'] = {
            'email': user_info.get('email'), 'name': user_info.get('name'),
            'picture': user_info.get('picture', '')
        }
        flash('เข้าสู่ระบบสำเร็จ!', 'success')
        return redirect(url_for('main.summary'))
    except Exception as e:
        flash(f'การล็อกอินล้มเหลว: {e}', 'danger')
        current_app.logger.error(f"Error during OAuth token exchange: {e}", exc_info=True)
        return redirect(url_for('main.login'))

@bp.route('/logout')
def logout():
    session.clear()
    flash('คุณได้ออกจากระบบแล้ว', 'success')
    return redirect(url_for('main.login'))

@bp.route('/')
def root_redirect():
    return redirect(url_for('main.summary'))

def _process_tasks(all_tasks):
    """Helper function to process raw task data."""
    processed_tasks = []
    now_thai = datetime.datetime.now(THAILAND_TZ)
    for task_raw in all_tasks:
        task = parse_google_task_dates(task_raw)
        task['due_date_obj'] = None
        if task.get('due'):
            try:
                task['due_date_obj'] = date_parse(task['due']).astimezone(THAILAND_TZ)
            except (ValueError, TypeError): pass

        customer_info = parse_customer_info_from_notes(task.get('notes', ''))
        task['customer_name'] = customer_info.get('name')
        task['customer_organization'] = customer_info.get('organization')

        task['is_overdue'] = False
        task['is_today'] = False
        if task.get('status') == 'needsAction' and task['due_date_obj']:
            if task['due_date_obj'].date() < now_thai.date():
                task['is_overdue'] = True
            elif task['due_date_obj'].date() == now_thai.date():
                task['is_today'] = True
        processed_tasks.append(task)
    return processed_tasks

@bp.route('/summary')
@login_required
def summary():
    status_filter = request.args.get('status_filter', 'today')
    search_query = request.args.get('search_query', '').strip()

    all_tasks = get_google_tasks_for_report(show_completed=True)
    if all_tasks is None:
        flash('เกิดข้อผิดพลาดในการเชื่อมต่อกับ Google API, กรุณาลองเข้าสู่ระบบใหม่', 'danger')
        return redirect(url_for('main.logout'))
    
    processed_tasks = _process_tasks(all_tasks)
    
    # Filtering logic can be added here based on status_filter and search_query
    
    monthly_completed_counts = defaultdict(int)
    for task in processed_tasks:
        if task.get('status') == 'completed' and task.get('completed'):
            completed_month = date_parse(task['completed']).astimezone(THAILAND_TZ).strftime('%Y-%m')
            monthly_completed_counts[completed_month] += 1
            
    sorted_months = sorted(monthly_completed_counts.keys())
    chart_labels = [datetime.datetime.strptime(m, '%Y-%m').strftime('%b %y') for m in sorted_months]
    chart_values = [monthly_completed_counts[m] for m in sorted_months]
    chart_data = {'labels': chart_labels, 'values': chart_values}

    return render_template(
        'dashboard.html',
        tasks=processed_tasks,
        status_filter=status_filter,
        search_query=search_query,
        chart_data=chart_data,
        total_tasks=len(processed_tasks),
        completed_tasks=sum(1 for t in processed_tasks if t.get('status') == 'completed'),
        needs_action_tasks=sum(1 for t in processed_tasks if t.get('status') == 'needsAction'),
        today_tasks_count=sum(1 for t in processed_tasks if t['is_today'])
    )

@bp.route('/summary/print')
@login_required
def summary_print():
    # This route needs to be implemented
    return "This is the print page. Not implemented yet."

@bp.route('/task/<task_id>')
@login_required
def task_details(task_id):
    # This route needs to be implemented
    return f"Details for task {task_id}. Not implemented yet."

@bp.route('/form', methods=['GET', 'POST'])
@login_required
def form_page():
    if request.method == 'POST':
        # Logic to create a task
        flash("Task creation not implemented yet.", "info")
        return redirect(url_for('main.summary'))
    return render_template('form.html')

@bp.route('/calendar')
@login_required
def calendar_view():
    return render_template('calendar.html')

@bp.route('/edit_task/<task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    return f"Edit page for task {task_id} not yet implemented."