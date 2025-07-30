# comphone/google_services.py

import os
import json
import time
import re
import datetime
import pytz
from flask import current_app, url_for, session, Flask # เพิ่ม Flask เพื่อเข้าถึง logger ได้
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload, MediaIoBaseDownload
from dateutil.parser import parse as date_parse

# --- Import cache จาก extensions.py ---
from .extensions import cache

# --- Local imports ---
from .utils import parse_customer_info_from_notes, sanitize_filename

# --- Constants ---
SCOPES = ['https://www.googleapis.com/auth/tasks', 'https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/drive']
GOOGLE_TASKS_LIST_ID = os.environ.get('GOOGLE_TASKS_LIST_ID', '@default')
GOOGLE_DRIVE_FOLDER_ID = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
GOOGLE_CALENDAR_ID = os.environ.get('GOOGLE_CALENDAR_ID', 'primary')

# --- Helper Functions for API Calls ---
def _execute_google_api_call_with_retry(api_call, *args, **kwargs):
    """
    Executes a Google API call with an exponential backoff retry mechanism
    for transient errors.
    """
    max_retries = 3
    base_delay = 1
    for i in range(max_retries):
        try:
            current_app.logger.debug(f"Attempt {i+1} to execute Google API call: {api_call.__self__.__class__.__name__}.{api_call.__name__}")
            return api_call(*args, **kwargs).execute()
        except HttpError as e:
            if e.resp.status in [500, 502, 503, 504, 429] and i < max_retries - 1:
                delay = base_delay * (2 ** i)
                current_app.logger.warning(f"Google API transient error (Status: {e.resp.status}). Retrying in {delay} seconds. Error: {e.content.decode()}")
                time.sleep(delay)
            else:
                current_app.logger.error(f"Google API HttpError (Status: {e.resp.status}) after {i+1} attempts: {e.content.decode()}", exc_info=True)
                raise
        except Exception as e:
            current_app.logger.error(f"Unexpected error during Google API call: {e}", exc_info=True)
            raise
    return None

# --- Service Initialization ---
def get_google_service(api_name, api_version, credentials=None):
    """
    Builds and returns a Google API service object with valid credentials.
    Uses user-specific credentials from the session if provided.
    """
    current_app.logger.debug(f"Attempting to get Google service: {api_name} v{api_version}")
    if not credentials:
        current_app.logger.warning(f"No credentials provided to get_google_service for {api_name}.")
        return None
    
    creds = Credentials(**credentials)

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            current_app.logger.info(f"Credentials for {api_name} expired, attempting to refresh.")
            try:
                creds.refresh(Request())
                # Update the session with the refreshed credentials
                session['credentials'] = {
                    'token': creds.token, 'refresh_token': creds.refresh_token,
                    'token_uri': creds.token_uri, 'client_id': creds.client_id,
                    'client_secret': creds.client_secret, 'scopes': creds.scopes
                }
                current_app.logger.info(f"Credentials for {api_name} refreshed successfully.")
            except Exception as e:
                current_app.logger.error(f"Error refreshing user token for {api_name}: {e}", exc_info=True)
                return None
        else:
            current_app.logger.warning(f"Credentials for {api_name} are invalid and cannot be refreshed (no refresh token or other issue).")
            return None
    
    current_app.logger.debug(f"Building Google service {api_name} v{api_version} with valid credentials.")
    return build(api_name, api_version, credentials=creds)

def get_google_tasks_service(credentials=None):
    return get_google_service('tasks', 'v1', credentials=credentials)

def get_google_drive_service(credentials=None):
    return get_google_service('drive', 'v3', credentials=credentials)

def get_google_calendar_service(credentials=None):
    return get_google_service('calendar', 'v3', credentials=credentials)

# --- Google Tasks Functions ---
def get_google_tasks_for_report(show_completed=True, credentials=None):
    service = get_google_tasks_service(credentials=credentials)
    if not service: return None
    try:
        current_app.logger.info("Fetching Google Tasks for report.")
        results = _execute_google_api_call_with_retry(service.tasks().list, tasklist=GOOGLE_TASKS_LIST_ID, showCompleted=show_completed, maxResults=2500)
        current_app.logger.debug(f"Fetched {len(results.get('items', []))} tasks.")
        return results.get('items', [])
    except HttpError as err:
        current_app.logger.error(f"API Error getting tasks for report: {err}", exc_info=True)
        return None

def get_single_task(task_id, credentials=None):
    if not task_id: return None
    service = get_google_tasks_service(credentials=credentials)
    if not service: return None
    try:
        cache.clear() # Cache clear happens here, so ensure cache is imported and configured
        current_app.logger.info(f"Fetching single task: {task_id}")
        return _execute_google_api_call_with_retry(service.tasks().get, tasklist=GOOGLE_TASKS_LIST_ID, task=task_id)
    except HttpError as err:
        current_app.logger.error(f"Error getting single task {task_id}: {err}", exc_info=True)
        return None

def create_google_task(title, notes=None, due=None, credentials=None):
    service = get_google_tasks_service(credentials=credentials)
    if not service: return None
    try:
        task_body = {'title': title, 'notes': notes, 'status': 'needsAction'}
        if due: task_body['due'] = due
        current_app.logger.info(f"Creating Google Task: {title}")
        return _execute_google_api_call_with_retry(service.tasks().insert, tasklist=GOOGLE_TASKS_LIST_ID, body=task_body)
    except HttpError as e:
        current_app.logger.error(f"Error creating Google Task: {e}", exc_info=True)
        return None

def update_google_task(task_id, credentials=None, **kwargs):
    service = get_google_tasks_service(credentials=credentials)
    if not service: return None
    try:
        current_app.logger.info(f"Updating Google Task: {task_id} with {kwargs}")
        task = _execute_google_api_call_with_retry(service.tasks().get, tasklist=GOOGLE_TASKS_LIST_ID, task=task_id)
        task.update(kwargs)
        if kwargs.get('status') == 'completed':
            task['completed'] = datetime.datetime.now(pytz.utc).isoformat().replace('+00:00', 'Z')
        else:
            task.pop('completed', None)
        return _execute_google_api_call_with_retry(service.tasks().update, tasklist=GOOGLE_TASKS_LIST_ID, task=task_id, body=task)
    except HttpError as e:
        current_app.logger.error(f"Failed to update task {task_id}: {e}", exc_info=True)
        return None

def delete_google_task(task_id, credentials=None):
    service = get_google_tasks_service(credentials=credentials)
    if not service: return False
    try:
        current_app.logger.info(f"Deleting Google Task: {task_id}")
        _execute_google_api_call_with_retry(service.tasks().delete, tasklist=GOOGLE_TASKS_LIST_ID, task=task_id)
        return True
    except HttpError as err:
        current_app.logger.error(f"API Error deleting task {task_id}: {err}", exc_info=True)
        return False
        
def add_tech_report_to_notes(task_id, report_data, credentials=None):
    """Appends a new technician report to an existing task's notes."""
    current_app.logger.info(f"Adding tech report to notes for task: {task_id}")
    task = get_single_task(task_id, credentials=credentials)
    if not task:
        current_app.logger.warning(f"Task {task_id} not found when trying to add tech report.")
        return None
    
    current_notes = task.get('notes', '')
    report_json = json.dumps(report_data, ensure_ascii=False, indent=2)
    new_report_block = f"\n\n--- TECH_REPORT_START ---\n{report_json}\n--- TECH_REPORT_END ---"
    
    updated_notes = current_notes + new_report_block
    
    return update_google_task(task_id, notes=updated_notes, credentials=credentials)


# --- Google Drive & Calendar Functions ---
def find_or_create_drive_folder(name, parent_id, credentials=None):
    service = get_google_drive_service(credentials=credentials)
    if not service: return None
    current_app.logger.info(f"Searching for or creating Drive folder: '{name}' in parent '{parent_id}'")
    query = f"name = '{name}' and '{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    try:
        response = _execute_google_api_call_with_retry(service.files().list, q=query, spaces='drive', fields='files(id, name)', pageSize=1)
        if response and response.get('files'):
            current_app.logger.info(f"Found existing folder: '{name}' (ID: {response['files'][0]['id']})")
            return response['files'][0]['id']
        else:
            file_metadata = {'name': name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id]}
            current_app.logger.info(f"Creating new folder: '{name}' in parent '{parent_id}'")
            folder = _execute_google_api_call_with_retry(service.files().create, body=file_metadata, fields='id')
            current_app.logger.info(f"Created new folder: '{name}' (ID: {folder.get('id')})")
            return folder.get('id')
    except HttpError as e:
        current_app.logger.error(f"Error finding or creating folder '{name}': {e}", exc_info=True)
        return None

def _perform_drive_upload(media_body, file_name, folder_id, credentials=None):
    service = get_google_drive_service(credentials=credentials)
    if not service or not folder_id: 
        current_app.logger.error(f"Cannot perform Drive upload: Service or folder_id is missing (Service: {bool(service)}, Folder ID: {bool(folder_id)}).")
        return None
    
    current_app.logger.info(f"Uploading file '{file_name}' to Drive folder '{folder_id}'")
    file_metadata = {'name': file_name, 'parents': [folder_id]}
    try:
        file_obj = _execute_google_api_call_with_retry(
            service.files().create,
            body=file_metadata, media_body=media_body, fields='id, name, webViewLink, thumbnailLink'
        )
        if file_obj and 'id' in file_obj:
            current_app.logger.info(f"File '{file_name}' uploaded. Setting public permissions.")
            _execute_google_api_call_with_retry(
                service.permissions().create,
                fileId=file_obj['id'], body={'role': 'reader', 'type': 'anyone'}
            )
            current_app.logger.info(f"File '{file_name}' permissions set to public. ID: {file_obj.get('id')}")
            return file_obj
        current_app.logger.error(f"File '{file_name}' upload failed or returned no ID.")
        return None
    except HttpError as e:
        current_app.logger.error(f"HttpError during Drive upload for '{file_name}': {e}", exc_info=True)
        return None
    except Exception as e:
        current_app.logger.error(f"Unexpected error during Drive upload for '{file_name}': {e}", exc_info=True)
        return None


def upload_file_to_drive_for_task(task, file_storage, filename, credentials=None):
    """Uploads a file to a specific folder for a given task."""
    current_app.logger.info(f"Initiating file upload for task {task.get('id')}: {filename}")
    if not GOOGLE_DRIVE_FOLDER_ID:
        current_app.logger.error("GOOGLE_DRIVE_FOLDER_ID is not set in environment variables.")
        return None
        
    customer_info = parse_customer_info_from_notes(task.get('notes', ''))
    task_date = date_parse(task.get('created')).astimezone(pytz.timezone('Asia/Bangkok')).strftime('%Y-%m-%d')
    
    folder_name = sanitize_filename(f"{task_date} - {customer_info.get('name', 'Unknown')} - {task.get('title', 'Untitled Task')}")
    task_folder_id = find_or_create_drive_folder(folder_name, GOOGLE_DRIVE_FOLDER_ID, credentials=credentials)
    
    if not task_folder_id:
        current_app.logger.error(f"Failed to find or create task folder for {task.get('id')}.")
        return None

    attachments_folder_id = find_or_create_drive_folder("Attachments", task_folder_id, credentials=credentials)
    if not attachments_folder_id:
        current_app.logger.error(f"Failed to find or create 'Attachments' subfolder for task {task.get('id')}.")
        return None

    media = MediaIoBaseUpload(file_storage, mimetype=file_storage.mimetype, resumable=True)
    uploaded_file_info = _perform_drive_upload(media, filename, attachments_folder_id, credentials=credentials)

    if uploaded_file_info:
        current_app.logger.info(f"File '{filename}' uploaded successfully to Drive.")
        return {
            "id": uploaded_file_info.get('id'),
            "name": uploaded_file_info.get('name'),
            "url": uploaded_file_info.get('webViewLink'),
            "thumbnail": uploaded_file_info.get('thumbnailLink')
        }
    current_app.logger.error(f"Failed to upload file '{filename}' for task {task.get('id')}.")
    return None

def upload_data_from_memory_to_drive(memory_file, filename, mimetype, folder_id, credentials=None):
    """Uploads a file-like object from memory to Google Drive."""
    current_app.logger.info(f"Uploading data from memory: '{filename}' to folder '{folder_id}'")
    media = MediaIoBaseUpload(memory_file, mimetype=mimetype, resumable=True)
    file_info = _perform_drive_upload(media, filename, folder_id, credentials)
    if file_info:
        current_app.logger.info(f"Data '{filename}' uploaded successfully from memory to Drive.")
        return True
    current_app.logger.error(f"Failed to upload data '{filename}' from memory to Drive.")
    return False

def create_or_update_calendar_event(task, credentials=None):
    service = get_google_calendar_service(credentials=credentials)
    if not service or not task.get('due'):
        current_app.logger.warning(f"Cannot create/update calendar event for task {task.get('id')}: Service or due date missing.")
        return None

    customer_info = parse_customer_info_from_notes(task.get('notes', ''))
    notes = task.get('notes', '')
    event_id_match = re.search(r"calendarEventId:\s*(\S+)", notes)
    event_id = event_id_match.group(1) if event_id_match else None

    start_time = date_parse(task['due'])
    end_time = start_time + datetime.timedelta(hours=1)

    event_body = {
        'summary': f"{task.get('title')} - {customer_info.get('name', 'N/A')}",
        'location': customer_info.get('map_url', customer_info.get('address', '')),
        'description': f"ดูรายละเอียดงานในระบบ: {url_for('main.task_details', task_id=task.get('id'), _external=True)}",
        'start': {'dateTime': start_time.isoformat(), 'timeZone': 'Asia/Bangkok'},
        'end': {'dateTime': end_time.isoformat(), 'timeZone': 'Asia/Bangkok'},
    }

    try:
        if event_id:
            current_app.logger.info(f"Updating calendar event {event_id} for task {task.get('id')}.")
            return _execute_google_api_call_with_retry(service.events().update, calendarId=GOOGLE_CALENDAR_ID, eventId=event_id, body=event_body)
        else:
            current_app.logger.info(f"Creating new calendar event for task {task.get('id')}.")
            new_event = _execute_google_api_call_with_retry(service.events().insert, calendarId=GOOGLE_CALENDAR_ID, body=event_body)
            if new_event:
                new_notes = f"{notes}\n\ncalendarEventId: {new_event['id']}"
                update_google_task(task['id'], notes=new_notes, credentials=credentials)
                current_app.logger.info(f"New calendar event created (ID: {new_event['id']}) and linked to task notes.")
            return new_event
    except HttpError as e:
        current_app.logger.error(f"HttpError with Google Calendar for task {task['id']}: {e}", exc_info=True)
        return None
    except Exception as e:
        current_app.logger.error(f"Unexpected error with Google Calendar for task {task['id']}: {e}", exc_info=True)
        return None

# --- High-Level Functions ---
def get_customer_database(credentials=None):
    current_app.logger.info("Fetching customer database (all tasks).")
    all_tasks = get_google_tasks_for_report(show_completed=True, credentials=credentials)
    if not all_tasks:
        current_app.logger.warning("No tasks found for customer database generation.")
        return []
    customers_dict = {}
    all_tasks.sort(key=lambda x: x.get('created', '0'), reverse=True)
    for task in all_tasks:
        notes = task.get('notes', '')
        customer_info = parse_customer_info_from_notes(notes)
        name = customer_info.get('name', '').strip()
        if not name:
            continue
        customer_key = name.lower()
        if customer_key not in customers_dict:
            customers_dict[customer_key] = customer_info
    current_app.logger.info(f"Generated customer database with {len(customers_dict)} unique customers.")
    return list(customers_dict.values())

def check_google_api_status(credentials=None):
    current_app.logger.debug("Checking Google API status.")
    if not credentials:
        current_app.logger.debug("No credentials provided for Google API status check.")
        return False
    service = get_google_drive_service(credentials=credentials)
    if not service:
        current_app.logger.debug("Could not get Drive service for Google API status check.")
        return False
    try:
        # Try a simple API call to check connectivity
        _execute_google_api_call_with_retry(service.about().get, fields='user')
        current_app.logger.info("Google API connection successful.")
        return True
    except HttpError as e:
        current_app.logger.error(f"Google API HttpError during status check: {e.resp.status} - {e.content.decode()}", exc_info=True)
        return False
    except Exception as e:
        current_app.logger.error(f"Unexpected error during Google API status check: {e}", exc_info=True)
        return False