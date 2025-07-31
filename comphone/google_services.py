# comphone/google_services.py

import os
import io
from flask import current_app, session
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from cachetools import cached # <<< เพิ่ม import นี้

from .extensions import cache

SCOPES = ['https://www.googleapis.com/auth/tasks', 'https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/drive']

def get_credentials():
    """
    สร้างและคืนค่า Credentials object จาก session
    พร้อมจัดการการ refresh token โดยอัตโนมัติ
    """
    creds_dict = session.get('credentials')
    if not creds_dict:
        return None

    # สร้าง Credentials object จาก dictionary ใน session
    credentials = Credentials.from_authorized_user_info(creds_dict, SCOPES)

    # ตรวจสอบและ refresh token ถ้าหมดอายุ
    if credentials and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
            # อัปเดต credentials ใน session หลังจากการ refresh
            session['credentials'] = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            session.modified = True
            current_app.logger.info("Credentials refreshed successfully.")
        except Exception as e:
            current_app.logger.error(f"Error refreshing credentials: {e}", exc_info=True)
            session.pop('credentials', None)
            session.pop('profile', None)
            return None
            
    return credentials

@cached(cache) # <<< แก้ไข Cache decorator
def get_google_tasks_for_report(show_completed=False, credentials=None):
    creds = get_credentials() if credentials is None else Credentials.from_authorized_user_info(credentials, SCOPES)
    if not creds:
        return None
    try:
        service = build('tasks', 'v1', credentials=creds)
        results = service.tasks().list(tasklist='@default', maxResults=100, showCompleted=show_completed).execute()
        return results.get('items', [])
    except HttpError as e:
        current_app.logger.error(f"An error occurred: {e}")
        return None

def get_single_task(task_id, credentials=None):
    creds = get_credentials() if credentials is None else Credentials.from_authorized_user_info(credentials, SCOPES)
    if not creds:
        return None
    try:
        service = build('tasks', 'v1', credentials=creds)
        task = service.tasks().get(tasklist='@default', task=task_id).execute()
        return task
    except HttpError as e:
        current_app.logger.error(f"An error occurred fetching single task: {e}")
        return None

def create_google_task(title, notes=None, due=None, credentials=None):
    creds = get_credentials() if credentials is None else Credentials.from_authorized_user_info(credentials, SCOPES)
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
        current_app.logger.error(f"An error occurred creating a task: {e}")
        return None

def update_google_task(task_id, credentials=None, **kwargs):
    creds = get_credentials() if credentials is None else Credentials.from_authorized_user_info(credentials, SCOPES)
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
        current_app.logger.error(f"An error occurred updating task: {e}")
        return None
        
def delete_google_task(task_id, credentials=None):
    creds = get_credentials() if credentials is None else Credentials.from_authorized_user_info(credentials, SCOPES)
    if not creds:
        return False
    try:
        service = build('tasks', 'v1', credentials=creds)
        service.tasks().delete(tasklist='@default', task=task_id).execute()
        cache.clear()
        return True
    except HttpError as e:
        current_app.logger.error(f"An error occurred deleting task: {e}")
        return False

def check_google_api_status(credentials=None):
    creds = get_credentials() if credentials is None else Credentials.from_authorized_user_info(credentials, SCOPES)
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