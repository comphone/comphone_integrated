# comphone/line_notifications.py

import os
import json
from flask import url_for, current_app
from linebot import LineBotApi
from linebot.models import TextSendMessage
from pywebpush import webpush, WebPushException

from . import utils
from .settings_manager import get_app_settings

SUBSCRIPTIONS_FILE = 'push_subscriptions.json'

def trigger_push_notification(title, body, url, icon='/static/logo.png'):
    """
    ส่ง Push Notification ไปยังผู้ใช้ทุกคนที่สมัครรับการแจ้งเตือน
    """
    if not os.path.exists(SUBSCRIPTIONS_FILE):
        current_app.logger.info("push_subscriptions.json not found, skipping push notification.")
        return

    VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY")
    VAPID_CLAIM_EMAIL = os.environ.get("VAPID_CLAIM_EMAIL")

    if not all([VAPID_PRIVATE_KEY, VAPID_CLAIM_EMAIL]):
        current_app.logger.error("VAPID keys are not configured in environment variables. Cannot send push notifications.")
        return

    with open(SUBSCRIPTIONS_FILE, 'r') as f:
        try:
            subscriptions = json.load(f)
        except json.JSONDecodeError:
            current_app.logger.warning("Could not decode push_subscriptions.json.")
            return
            
    payload = json.dumps({
        "title": title,
        "body": body,
        "icon": icon,
        "url": url
    })
    
    # subscriptions is a dict with email as key, we iterate through its values
    for email, sub_info in list(subscriptions.items()):
        try:
            webpush(
                subscription_info=sub_info,
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{VAPID_CLAIM_EMAIL}"}
            )
            current_app.logger.info(f"Sent push notification to {email}")
        except WebPushException as ex:
            current_app.logger.error(f"Failed to send push notification to {email}: {ex}")
            # ถ้า subscription ไม่ถูกต้องแล้ว (เช่น ผู้ใช้ล้างแคช) ให้ลบออกจากลิสต์
            if ex.response and ex.response.status_code in [404, 410]:
                current_app.logger.info(f"Removing expired subscription for {email}")
                subscriptions.pop(email, None)

    # บันทึกไฟล์ subscription ที่อัปเดตแล้ว (กรณีมีการลบ subscription ที่หมดอายุ)
    with open(SUBSCRIPTIONS_FILE, 'w') as f:
        json.dump(subscriptions, f, indent=2)

def send_new_task_notification(task):
    """
    ส่งการแจ้งเตือนเมื่อมีงานใหม่ (ทั้ง LINE และ Push Notification)
    """
    line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))
    admin_group_id = get_app_settings().get('line_recipients', {}).get('admin_group_id')
    
    # ต้องสร้าง app context เพื่อให้ url_for ทำงานได้นอก request
    with current_app.app_context():
        task_url = url_for('main.task_details', task_id=task.get('id'), _external=True)

    # --- 1. ส่ง LINE Notification ---
    if admin_group_id:
        customer_info = utils.parse_customer_info_from_notes(task.get('notes', ''))
        parsed_dates = utils.parse_google_task_dates(task)
        due_info = f"นัดหมาย: {parsed_dates.get('due_formatted', '-')}"
        location_info = f"พิกัด: {customer_info.get('map_url', '-')}"
        message_text = (
            f"✨ มีงานใหม่เข้า!\n\n"
            f"ชื่องาน: {task.get('title', '-')}\n"
            f"ลูกค้า: {customer_info.get('name', '-')}\n"
            f"📞 โทร: {customer_info.get('phone', '-')}\n"
            f"🗓️ {due_info}\n"
            f"📍 {location_info}\n\n"
            f"ดูรายละเอียดในเว็บ:\n{task_url}"
        )
        try:
            line_bot_api.push_message(admin_group_id, TextSendMessage(text=message_text))
        except Exception as e:
            current_app.logger.error(f"Error sending LINE notification: {e}")

    # --- 2. ส่ง Push Notification ---
    customer_info = utils.parse_customer_info_from_notes(task.get('notes', ''))
    push_title = f"มีงานใหม่: {task.get('title')}"
    push_body = f"ลูกค้า: {customer_info.get('name', 'N/A')}"
    trigger_push_notification(title=push_title, body=push_body, url=task_url)

# คุณสามารถเพิ่มการเรียก trigger_push_notification ในฟังก์ชันอื่นๆ ได้ตามต้องการ
# def send_completion_notification(task, technicians):
#     ...
#     trigger_push_notification(...)

# def send_update_notification(task, ...):
#     ...
#     trigger_push_notification(...)
