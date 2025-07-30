# comphone/line_handler.py

import os
import json
import requests
from flask import Blueprint, request, abort, current_app, session, url_for
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, FlexSendMessage,
    SourceUser, SourceGroup, SourceRoom, QuickReply, QuickReplyButton, MessageAction
)
from .google_services import get_single_task, get_google_tasks_for_report
from .utils import create_task_flex_message
from .settings_manager import get_app_settings

# Initialize LINE Bot API
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')

if not LINE_CHANNEL_ACCESS_TOKEN:
    current_app.logger.error("LINE_CHANNEL_ACCESS_TOKEN is not set.")
if not LINE_CHANNEL_SECRET:
    current_app.logger.error("LINE_CHANNEL_SECRET is not set.")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

bp = Blueprint('line_handler', __name__, url_prefix='/line')

# --- Helper function for sending LINE messages ---
def _send_line_message(target_id, messages):
    try:
        if isinstance(messages, str):
            messages = TextSendMessage(text=messages)
        elif not isinstance(messages, list):
            messages = [messages]
        
        line_bot_api.push_message(target_id, messages)
        current_app.logger.info(f"LINE message sent successfully to {target_id}.")
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send LINE message to {target_id}: {e}", exc_info=True)
        return False

# --- New function to send test notification (REQUIRED FIX) ---
def send_test_notification():
    """Sends a simple test message to the configured LINE Admin Group."""
    app_settings = get_app_settings()
    admin_group_id = app_settings.get('line_recipients', {}).get('admin_group_id')
    
    if not admin_group_id:
        current_app.logger.error("LINE Admin Group ID is not configured in settings for test notification.")
        return False
        
    message = "✅ การส่งข้อความทดสอบจากระบบ Comphone Integrated System สำเร็จแล้ว!"
    current_app.logger.info(f"Attempting to send test notification to LINE Admin Group: {admin_group_id}")
    return _send_line_message(admin_group_id, message)

# --- NEW FUNCTION: Send new task notification ---
def send_new_task_notification(task, technicians):
    """Sends a notification when a new task is created."""
    app_settings = get_app_settings()
    admin_group_id = app_settings.get('line_recipients', {}).get('admin_group_id')
    technician_group_id = app_settings.get('line_recipients', {}).get('technician_group_id')

    tech_names = ", ".join([t.get('name', 'N/A') for t in technicians]) if technicians else "ไม่ระบุช่าง"
    message_title = f"✨ งานใหม่เข้ามา: {task.get('title')}"
    message_body = (
        f"ลูกค้า: {task.get('customer_name', 'ไม่ระบุ')}\n"
        f"นัดหมาย: {task.get('due_formatted', 'N/A')}\n"
        f"ช่างผู้รับผิดชอบ: {tech_names}\n"
        f"รายละเอียด: {task.get('notes', 'ไม่มีรายละเอียด')}"
    )
    
    flex_message = FlexSendMessage(
        alt_text=message_title,
        contents=create_task_flex_message(task)
    )
    
    messages = [TextSendMessage(text=f"{message_title}\n{message_body}"), flex_message]
    
    if admin_group_id:
        _send_line_message(admin_group_id, messages)
    if technician_group_id: # ส่งให้กลุ่มช่างด้วย
        _send_line_message(technician_group_id, messages)
    current_app.logger.info(f"New task notification sent for task {task.get('id')}.")


# --- LINE Notification Functions (called from other modules) ---
def send_completion_notification(task, technicians):
    """Sends a notification when a task is completed."""
    app_settings = get_app_settings()
    admin_group_id = app_settings.get('line_recipients', {}).get('admin_group_id')
    manager_user_id = app_settings.get('line_recipients', {}).get('manager_user_id')
    
    tech_names = ", ".join([t.get('name', 'N/A') for t in technicians]) if technicians else "ไม่ระบุช่าง"
    message_title = f"✅ งานเสร็จสิ้น: {task.get('title')}"
    message_body = (
        f"ลูกค้า: {task.get('customer_name', 'ไม่ระบุ')}\n"
        f"เวลาปิดงาน: {task.get('completed_formatted', 'N/A')}\n"
        f"ช่างผู้รับผิดชอบ: {tech_names}\n\n"
        f"สรุปงาน: {task.get('latest_report_summary', 'ไม่มีสรุป')}"
    )
    
    flex_message = FlexSendMessage(
        alt_text=message_title,
        contents=create_task_flex_message(task)
    )
    
    messages = [TextSendMessage(text=f"{message_title}\n{message_body}"), flex_message]
    
    if admin_group_id:
        _send_line_message(admin_group_id, messages)
    if manager_user_id:
        _send_line_message(manager_user_id, messages) # Send to manager as well
    current_app.logger.info(f"Completion notification sent for task {task.get('id')}.")


def send_update_notification(task, reschedule_date, reschedule_reason, technicians, is_progress_update):
    """Sends a notification when a task is updated or rescheduled."""
    app_settings = get_app_settings()
    admin_group_id = app_settings.get('line_recipients', {}).get('admin_group_id')
    technician_group_id = app_settings.get('line_recipients', {}).get('technician_group_id')
    
    tech_names = ", ".join([t.get('name', 'N/A') for t in technicians]) if technicians else "ไม่ระบุช่าง"
    
    if is_progress_update:
        message_title = f"🔄 อัปเดตความคืบหน้างาน: {task.get('title')}"
        message_body = (
            f"ลูกค้า: {task.get('customer_name', 'ไม่ระบุ')}\n"
            f"ช่าง: {tech_names}\n"
            f"สถานะ: {task.get('latest_report_summary', 'ไม่มีสรุป')}"
        )
    else: # Reschedule
        message_title = f"🗓️ เลื่อนนัดหมายงาน: {task.get('title')}"
        message_body = (
            f"ลูกค้า: {task.get('customer_name', 'ไม่ระบุ')}\n"
            f"จาก: {task.get('due_formatted', 'N/A')}\n"
            f"เป็น: {reschedule_date}\n"
            f"เหตุผล: {reschedule_reason if reschedule_reason else 'ไม่มี'}\n"
            f"ช่าง: {tech_names}"
        )
        
    flex_message = FlexSendMessage(
        alt_text=message_title,
        contents=create_task_flex_message(task)
    )
    
    messages = [TextSendMessage(text=f"{message_title}\n{message_body}"), flex_message]
    
    if admin_group_id:
        _send_line_message(admin_group_id, messages)
    # ถ้ามี Technician Group ID และไม่ใช่กลุ่มเดียวกับ Admin
    if technician_group_id and technician_group_id != admin_group_id:
        _send_line_message(technician_group_id, messages)
    current_app.logger.info(f"Update/Reschedule notification sent for task {task.get('id')}.")


# --- LINE Webhook Handler (for incoming messages) ---
@bp.route("/webhook", methods=['POST'])
def webhook():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    current_app.logger.debug(f"Request body: {body}")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        current_app.logger.error("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    except Exception as e:
        current_app.logger.error(f"Unhandled exception in LINE webhook: {e}", exc_info=True)
        abort(500)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text
    user_id = event.source.user_id
    current_app.logger.info(f"Received message: '{text}' from User ID: {user_id}")

    if text == 'สถานะ':
        _send_line_message(event.reply_token, TextSendMessage(text="ระบบทำงานปกติค่ะ"))
    elif text == 'สวัสดี':
        _send_line_message(event.reply_token, TextSendMessage(text=f"สวัสดีค่ะ คุณ {user_id}"))
    elif text == 'ดูงาน':
        with current_app.app_context():
            user_creds_dict = session.get('credentials') # ต้องแน่ใจว่ามี credentials ใน session
            if not user_creds_dict:
                current_app.logger.warning("No user credentials in session for 'ดูงาน' command.")
                _send_line_message(event.reply_token, TextSendMessage(text="ไม่สามารถเข้าถึงข้อมูลงานได้ กรุณาล็อกอินผ่านระบบเว็บก่อนค่ะ"))
                return

            tasks = get_google_tasks_for_report(show_completed=False, credentials=user_creds_dict)
            if tasks:
                messages = []
                for task in tasks[:3]: # แสดงแค่ 3 งานแรก
                    messages.append(create_task_flex_message(task))
                _send_line_message(event.reply_token, messages)
            else:
                _send_line_message(event.reply_token, TextSendMessage(text="วันนี้ไม่มีงานที่ต้องทำค่ะ"))
    else:
        _send_line_message(event.reply_token, TextSendMessage(text=f"คุณพูดว่า: {text}"))

    # ตัวอย่างการตอบกลับด้วย Quick Reply
    if text == "ถามอะไรก็ได้":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text='เลือกคำถาม:',
                quick_reply=QuickReply(items=[
                    QuickReplyButton(action=MessageAction(label="สถานะ", text="สถานะ")),
                    QuickReplyButton(action=MessageAction(label="ดูงาน", text="ดูงาน"))
                ])
            )
        )