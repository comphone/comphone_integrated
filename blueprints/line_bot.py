# C:/.../comphone_integrated/blueprints/line_bot.py

from flask import Blueprint, request, abort, current_app
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    PostbackEvent,
    FollowEvent
)
import json

from models import db, Customer, Task, User

line_bp = Blueprint('line_bot', __name__, url_prefix='/line')

# --- LINE Bot Setup ---
handler = None
configuration = None
messaging_api = None

# --- Event Handler Functions (ย้ายมาไว้ตรงนี้โดยไม่มี Decorator) ---

def handle_text_message(event):
    """Handler for text messages from users."""
    text = event.message.text.lower().strip()
    line_user_id = event.source.user_id
    customer = Customer.query.filter_by(line_user_id=line_user_id).first()
    if not customer:
        reply_text = "สวัสดีครับ! ดูเหมือนคุณจะยังไม่ได้ลงทะเบียนกับเรา กรุณาลงทะเบียนผ่านเมนู 'สมัคร/เชื่อมต่อบัญชี' ก่อนนะครับ"
        reply_message(event.reply_token, reply_text)
        return

    if 'แจ้งปัญหา' in text or 'แจ้งซ่อม' in text:
        reply_text = f"สวัสดีคุณ {customer.name} ครับ กรุณากดที่เมนู 'แจ้งปัญหา/งานซ่อม' เพื่อกรอกรายละเอียดได้เลยครับ"
    elif 'สถานะ' in text or 'ตามงาน' in text:
        last_job = Task.query.filter_by(customer_id=customer.id).order_by(Task.created_at.desc()).first()
        if last_job:
            reply_text = f"สถานะงานล่าสุดของคุณ '{last_job.title}' คือ: {last_job.status}"
        else:
            reply_text = "ไม่พบข้อมูลงานในระบบของท่านครับ"
    else:
        reply_text = "ขออภัยครับ ฉันไม่เข้าใจคำสั่ง กรุณาเลือกจากเมนูได้เลยครับ"
    reply_message(event.reply_token, reply_text)


def handle_postback(event):
    """Handler for postback events (button clicks)."""
    data = event.postback.data
    line_user_id = event.source.user_id
    
    if data == 'action=create_task':
        reply_text = "กรุณาพิมพ์รายละเอียดปัญหาที่ต้องการแจ้งได้เลยครับ โดยขึ้นต้นว่า 'แจ้งปัญหา' ตามด้วยรายละเอียด"
    elif data == 'action=check_status':
        customer = Customer.query.filter_by(line_user_id=line_user_id).first()
        if customer:
            last_job = Task.query.filter_by(customer_id=customer.id).order_by(Task.created_at.desc()).first()
            if last_job:
                reply_text = f"สถานะงานล่าสุด: {last_job.title}\nสถานะ: {last_job.status}"
            else:
                reply_text = "ไม่พบข้อมูลงานในระบบของท่านครับ"
        else:
            reply_text = "กรุณาลงทะเบียนก่อนใช้งานครับ"
    else:
        reply_text = "ดำเนินการตามคำขอของท่านแล้ว"
    reply_message(event.reply_token, reply_text)


def handle_follow(event):
    """Handler for when a user adds the bot as a friend."""
    line_user_id = event.source.user_id
    try:
        profile = messaging_api.get_profile(line_user_id)
        display_name = profile.display_name
    except Exception:
        display_name = "ผู้ใช้ใหม่"
    reply_text = (
        f"สวัสดีคุณ {display_name} ยินดีต้อนรับสู่ Comphone Service ครับ!\n\n"
        "กรุณากดที่เมนู 'สมัคร/เชื่อมต่อบัญชี' ด้านล่างเพื่อเริ่มใช้งานระบบแจ้งซ่อมและติดตามสถานะได้เลยครับ"
    )
    reply_message(event.reply_token, reply_text)


def init_line_bot(app):
    """Initialize LINE Bot handlers from app config and register handlers."""
    global handler, configuration, messaging_api
    
    channel_secret = app.config.get('LINE_CHANNEL_SECRET')
    channel_access_token = app.config.get('LINE_CHANNEL_ACCESS_TOKEN')
    
    if not all([channel_secret, channel_access_token]):
        app.logger.warning("LINE Bot credentials are not set. The LINE webhook will not work.")
        return

    handler = WebhookHandler(channel_secret)
    configuration = Configuration(access_token=channel_access_token)
    api_client = ApiClient(configuration)
    messaging_api = MessagingApi(api_client)
    
    # --- START: จุดที่แก้ไข ---
    # Register event handlers manually after handler is created
    handler.add(MessageEvent, message=TextMessageContent)(handle_text_message)
    handler.add(PostbackEvent)(handle_postback)
    handler.add(FollowEvent)(handle_follow)
    # --- END: จุดที่แก้ไข ---
    
    app.logger.info("LINE Bot initialized and handlers registered successfully.")

# --- Webhook Endpoint ---
@line_bp.route("/callback", methods=['POST'])
def callback():
    """LINE Bot Webhook endpoint."""
    if handler is None:
        current_app.logger.error("LINE Bot handler is not initialized.")
        abort(500)

    signature = request.headers.get('X-Line-Signature')
    if not signature:
        abort(400)

    body = request.get_data(as_text=True)
    current_app.logger.info(f"Request body: {body}")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        current_app.logger.error("Invalid signature. Please check your channel secret.")
        abort(400)
    except Exception as e:
        current_app.logger.error(f"Error handling webhook: {e}")
        abort(500)

    return 'OK'


# --- Utility Functions ---
def reply_message(reply_token, text):
    """A simple helper to reply with a text message."""
    if messaging_api:
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=text)]
            )
        )

def push_message(to, text):
    """A simple helper to push a text message to a user."""
    if messaging_api:
        messaging_api.push_message(
            to=to,
            messages=[TextMessage(text=text)]
        )