# comphone/extensions.py

from apscheduler.schedulers.background import BackgroundScheduler
from cachetools import TTLCache
from flask_wtf.csrf import CSRFProtect
import pytz

# สร้าง instances ของ Extensions ทั้งหมดที่จะใช้ร่วมกันในแอปพลิเคชัน
# ไฟล์ __init__.py และไฟล์อื่นๆ จะมา import จากที่นี่

csrf = CSRFProtect()
cache = TTLCache(maxsize=100, ttl=300) # สร้าง Cache object ที่มีอายุ 5 นาที
scheduler = BackgroundScheduler(daemon=True, timezone=pytz.timezone('Asia/Bangkok'))