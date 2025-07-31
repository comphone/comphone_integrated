# comphone/google_services.py

import os
import io
import json
from flask import current_app, session
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload
from cachetools import cached # <<< เพิ่ม import นี้

from .extensions import cache

SCOPES = ['https://www.googleapis.com/auth/tasks', 'https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/drive']
GOOGLE_DRIVE_FOLDER_ID = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')

def get_credentials():
    creds_dict = session.get('credentials')
    if not creds_dict:
        return None
    credentials = Credentials.from_authorized_user_info(creds_dict, SCOPES)
    if credentials and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
            session['credentials'] = {
                'token': credentials.token, 'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri, 'client_id': credentials.client_id,
                'client_secret': credentials.client_secret, 'scopes': credentials.scopes
            }
            session.modified = True
        except Exception as e:
            current_app.logger.error(f"Error refreshing credentials: {e}", exc_info=True)
            session.clear()
            return None
    return credentials

def get_google_drive_service():
    creds = get_credentials()
    if not creds:
        return None
    try:
        return build('drive', 'v3', credentials=creds)
    except HttpError as e:
        current_app.logger.error(f"Failed to build Google Drive service: {e}", exc_info=True)
        return None

@cached(cache)
def find_or_create_drive_folder(name, parent_id):
    service = get_google_drive_service()
    if not service:
        return None
    try:
        q = f"name='{name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        response = service.files().list(q=q, spaces='drive', fields='files(id, name)').execute()
        if response.get('files'):
            return response.get('files')[0].get('id')
        else:
            file_metadata = {'name': name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id]}
            folder = service.files().create(body=file_metadata, fields='id').execute()
            return folder.get('id')
    except HttpError as error:
        current_app.logger.error(f'An error occurred: {error}')
        return None

def upload_data_from_memory_to_drive(file_stream, filename, mimetype, folder_id):
    service = get_google_drive_service()
    if not service:
        return None
    try:
        file_metadata = {'name': filename, 'parents': [folder_id]}
        media = MediaIoBaseUpload(file_stream, mimetype=mimetype, resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        return file
    except HttpError as error:
        current_app.logger.error(f'An error occurred during file upload: {error}')
        return None

@cached(cache)
def get_google_tasks_for_report(show_completed=False):
    creds = get_credentials()
    if not creds:
        return None
    try:
        service = build('tasks', 'v1', credentials=creds)
        results = service.tasks().list(tasklist='@default', maxResults=100, showCompleted=show_completed).execute()
        return results.get('items', [])
    except HttpError as e:
        current_app.logger.error(f"An error occurred fetching tasks: {e}")
        return None

def get_single_task(task_id):
    creds = get_credentials()
    if not creds:
        return None
    try:
        service = build('tasks', 'v1', credentials=creds)
        return service.tasks().get(tasklist='@default', task=task_id).execute()
    except HttpError as e:
        current_app.logger.error(f"An error occurred fetching task {task_id}: {e}")
        return None

def create_google_task(title, notes=None, due=None):
    creds = get_credentials()
    if not creds:
        return None
    try:
        service = build('tasks', 'v1', credentials=creds)
        task_body = {'title': title}
        if notes:
            task_body['notes'] = notes
        if due:
            task_body['due'] = due
        task = service.tasks().insert(tasklist='@default', body=task_body).execute()
        cache.clear()
        return task
    except HttpError as e:
        current_app.logger.error(f"An error occurred creating task: {e}")
        return None

def update_google_task(task_id, **kwargs):
    creds = get_credentials()
    if not creds:
        return None
    try:
        service = build('tasks', 'v1', credentials=creds)
        task = service.tasks().get(tasklist='@default', task=task_id).execute()
        task.update(kwargs)
        updated_task = service.tasks().update(tasklist='@default', task=task_id, body=task).execute()
        cache.clear()
        return updated_task
    except HttpError as e:
        current_app.logger.error(f"An error occurred updating task {task_id}: {e}")
        return None

def delete_google_task(task_id):
    creds = get_credentials()
    if not creds:
        return False
    try:
        service = build('tasks', 'v1', credentials=creds)
        service.tasks().delete(tasklist='@default', task=task_id).execute()
        cache.clear()
        return True
    except HttpError as e:
        current_app.logger.error(f"An error occurred deleting task {task_id}: {e}")
        return False

def check_google_api_status(credentials=None):
    creds = get_credentials()
    if not creds or not creds.valid:
        return False
    try:
        service = build('oauth2', 'v2', credentials=creds)
        service.userinfo().get().execute()
        return True
    except:
        return False
        
def create_or_update_calendar_event(task, credentials=None):
    # Placeholder for this function as it is complex
    return True

def _execute_google_api_call_with_retry(api_call, *args, **kwargs):
    # Placeholder for this function
    return api_call(*args, **kwargs).execute()