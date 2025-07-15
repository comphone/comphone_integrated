# C:/.../comphone_integrated/blueprints/google_api.py

import os
from flask import (
    Blueprint, request, url_for, session, jsonify, redirect, current_app, flash
)
from flask_login import login_required
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import google.auth.transport.requests

from models import db, Task, ServiceJob, Sale

google_bp = Blueprint('google', __name__, url_prefix='/google')

# --- Google API Setup ---
SCOPES = [
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive.file'
]

def get_google_credentials():
    """Gets valid Google credentials from session or initiates OAuth2 flow."""
    creds = None
    token_file = current_app.config.get('GOOGLE_TOKEN_FILE')
    
    # ลองโหลด credentials จากไฟล์ token ที่บันทึกไว้
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    # ถ้า credentials ไม่มีหรือหมดอายุ, ทำการ refresh หรือเริ่ม flow ใหม่
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(google.auth.transport.requests.Request())
                # บันทึก credentials ที่ refresh แล้ว
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                current_app.logger.error(f"Error refreshing Google token: {e}")
                # ถ้า refresh ไม่ได้ ให้เริ่ม flow ใหม่โดยการลบไฟล์ token เก่า
                os.remove(token_file)
                return None
        else:
            return None # ไม่มี credentials ให้เริ่ม flow ใหม่
    return creds

# --- OAuth2 Authentication Routes ---
@google_bp.route('/authorize')
@login_required
def authorize():
    """Starts the OAuth 2.0 authorization flow."""
    creds_file = current_app.config.get('GOOGLE_CREDENTIALS_FILE')
    if not os.path.exists(creds_file):
        flash('ไม่พบไฟล์ Google Credentials (google_credentials.json)', 'error')
        return redirect(url_for('main.index'))

    flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
    # บอกให้ flow รู้ว่า redirect ไปที่ไหนหลัง authorize เสร็จ
    flow.redirect_uri = url_for('google.oauth2callback', _external=True)
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    # เก็บ state ไว้ใน session เพื่อตรวจสอบความปลอดภัย
    session['google_oauth_state'] = state
    return redirect(authorization_url)

@google_bp.route('/oauth2callback')
@login_required
def oauth2callback():
    """Callback route for Google's OAuth 2.0."""
    # ตรวจสอบ state เพื่อป้องกัน CSRF
    state = session.pop('google_oauth_state', None)
    if state is None or state != request.args.get('state'):
        abort(401)

    creds_file = current_app.config.get('GOOGLE_CREDENTIALS_FILE')
    flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
    flow.redirect_uri = url_for('google.oauth2callback', _external=True)

    try:
        # แลก authorization code ที่ได้มาเป็น access token
        flow.fetch_token(authorization_response=request.url)
        creds = flow.credentials
        
        # บันทึก credentials ลงไฟล์ token สำหรับการใช้งานครั้งต่อไป
        token_file = current_app.config.get('GOOGLE_TOKEN_FILE')
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
            
        flash('เชื่อมต่อบัญชี Google สำเร็จ!', 'success')
    except Exception as e:
        flash(f'เกิดข้อผิดพลาดในการเชื่อมต่อ Google: {e}', 'error')
    
    return redirect(url_for('main.index'))


# --- Google API Service Functions ---

@google_bp.route('/sync-task/<int:task_id>', methods=['POST'])
@login_required
def sync_google_task(task_id):
    """Syncs a single task to Google Tasks."""
    creds = get_google_credentials()
    if not creds:
        return jsonify({'success': False, 'message': 'Google account not authorized.', 'redirect': url_for('google.authorize')})

    task = Task.query.get_or_404(task_id)
    try:
        service = build('tasks', 'v1', credentials=creds)
        
        task_body = {
            'title': task.title,
            'notes': task.description or '',
            'status': 'needsAction' if task.status != 'completed' else 'completed'
        }
        if task.due_date:
            # Format: '2024-12-31T00:00:00.000Z'
            task_body['due'] = task.due_date.isoformat() + "Z"
            
        # ถ้าเคย sync แล้ว ให้ update, ถ้ายัง ให้ insert
        if task.google_task_id:
            result = service.tasks().update(tasklist='@default', task=task.google_task_id, body=task_body).execute()
        else:
            result = service.tasks().insert(tasklist='@default', body=task_body).execute()
            task.google_task_id = result.get('id')
            db.session.commit()
            
        return jsonify({'success': True, 'message': 'Sync Task กับ Google สำเร็จ!'})
        
    except HttpError as e:
        return jsonify({'success': False, 'message': f'Google API Error: {e}'}), 500

@google_bp.route('/upload-receipt/<int:sale_id>', methods=['POST'])
@login_required
def upload_receipt_to_drive(sale_id):
    """Generates a receipt and uploads it to Google Drive."""
    creds = get_google_credentials()
    if not creds:
        return jsonify({'success': False, 'message': 'Google account not authorized.', 'redirect': url_for('google.authorize')})
        
    sale = Sale.query.get_or_404(sale_id)
    folder_id = current_app.config.get('GOOGLE_DRIVE_FOLDER_ID')
    if not folder_id:
        return jsonify({'success': False, 'message': 'ไม่ได้ตั้งค่า Google Drive Folder ID'})

    try:
        # --- สร้างไฟล์ใบเสร็จ (ตัวอย่างนี้จะสร้างไฟล์ text ง่ายๆ) ---
        receipt_content = f"ใบเสร็จเลขที่: {sale.receipt_number}\n"
        receipt_content += f"วันที่: {sale.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        receipt_content += f"ลูกค้า: {sale.customer.name}\n\n"
        for item in sale.items:
            receipt_content += f"- {item.product.name} x{item.quantity} = {item.total_price} บาท\n"
        receipt_content += f"\nยอดรวม: {sale.total_amount} บาท"
        
        file_path = f"/tmp/receipt_{sale.receipt_number}.txt"
        with open(file_path, "w") as f:
            f.write(receipt_content)
        # --------------------------------------------------------

        service = build('drive', 'v3', credentials=creds)
        file_metadata = {
            'name': f'receipt_{sale.receipt_number}.txt',
            'parents': [folder_id]
        }
        media = MediaFileUpload(file_path, mimetype='text/plain')
        
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        
        # ลบไฟล์ชั่วคราว
        os.remove(file_path)

        # บันทึก Link ไปยัง Google Drive ไว้ใน Sale
        sale.gdrive_receipt_url = file.get('webViewLink')
        db.session.commit()

        return jsonify({'success': True, 'message': 'อัปโหลดใบเสร็จไปยัง Google Drive สำเร็จ!', 'link': file.get('webViewLink')})

    except HttpError as e:
        return jsonify({'success': False, 'message': f'Google API Error: {e}'}), 500