# comphone/app_scheduler.py

import datetime
from flask import Flask, current_app # Keep current_app here for other uses
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import logging

# Local imports
from .google_services import get_google_tasks_for_report, check_google_api_status
from .settings_manager import get_app_settings, load_settings_from_drive_on_startup, backup_settings_to_drive
from .line_handler import line_bot_api # Only import what's needed for sending messages
from .utils import THAILAND_TZ, create_task_flex_message

# Initialize APScheduler
scheduler = BackgroundScheduler(timezone=THAILAND_TZ)
cache = {} # A simple in-memory cache for demo purposes, can be replaced with Flask-Caching

# Setup logging for scheduler
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

# Reference to the Flask app instance (to be set after app creation)
flask_app_instance = None

def set_flask_app(app):
    """Sets the Flask app instance for scheduler jobs and initial logging."""
    global flask_app_instance
    flask_app_instance = app
    # Now that app is set, we can ensure initial scheduler logs use it
    if app:
        with app.app_context():
            app.logger.debug("Flask app instance set for app_scheduler.")

def initialize_scheduler():
    """Initializes the scheduler with default jobs if not already running."""
    # Ensure logging happens within app_context if app_instance is available
    if not scheduler.running:
        if flask_app_instance:
            with flask_app_instance.app_context():
                flask_app_instance.logger.info("Scheduler is not running, initializing it.")
        else:
            print("Scheduler is not running, initializing it (no app instance for logging).") # Fallback print
        scheduler.start()
    else:
        if flask_app_instance:
            with flask_app_instance.app_context():
                flask_app_instance.logger.info("Scheduler is already running.")
        else:
            print("Scheduler is already running (no app instance for logging).") # Fallback print
    
def run_scheduler():
    """Removes existing jobs and re-adds them based on current settings."""
    # Ensure run_scheduler always called within an app_context (as it is in __init__.py)
    # So current_app should be available here.
    app_settings = get_app_settings()
    report_times = app_settings.get('report_times', {})
    admin_group_id = app_settings.get('line_recipients', {}).get('admin_group_id')
    manager_user_id = app_settings.get('line_recipients', {}).get('manager_user_id')

    for job in scheduler.get_jobs():
        job.remove()
    current_app.logger.info("Cleared all existing scheduler jobs.")

    if admin_group_id:
        current_app.logger.info(f"Adding scheduler jobs for LINE Admin Group ID: {admin_group_id}")
        
        if 'appointment_reminder_hour_thai' in report_times:
            hour = report_times['appointment_reminder_hour_thai']
            scheduler.add_job(
                send_appointment_reminders_job,
                trigger=CronTrigger(hour=hour, minute=0, timezone=THAILAND_TZ),
                id='appointment_reminder',
                name='Appointment Reminder',
                args=[admin_group_id, manager_user_id, flask_app_instance], # Pass app instance
                replace_existing=True
            )
            current_app.logger.info(f"Scheduled 'Appointment Reminder' for {hour}:00 THA.")

        if 'outstanding_report_hour_thai' in report_times:
            hour = report_times['outstanding_report_hour_thai']
            scheduler.add_job(
                send_outstanding_tasks_report_job,
                trigger=CronTrigger(hour=hour, minute=0, timezone=THAILAND_TZ),
                id='outstanding_tasks_report',
                name='Outstanding Tasks Report',
                args=[admin_group_id, manager_user_id, flask_app_instance], # Pass app instance
                replace_existing=True
            )
            current_app.logger.info(f"Scheduled 'Outstanding Tasks Report' for {hour}:00 THA.")

        if 'customer_followup_hour_thai' in report_times:
            hour = report_times['customer_followup_hour_thai']
            scheduler.add_job(
                send_customer_followup_report_job,
                trigger=CronTrigger(hour=hour, minute=0, timezone=THAILAND_TZ),
                id='customer_followup_report',
                name='Customer Follow-up Report',
                args=[admin_group_id, manager_user_id, flask_app_instance], # Pass app instance
                replace_existing=True
            )
            current_app.logger.info(f"Scheduled 'Customer Follow-up Report' for {hour}:00 THA.")
    else:
        current_app.logger.warning("LINE Admin Group ID is not configured. Skipping scheduled LINE reports.")

    scheduler.add_job(
        scheduled_backup_job,
        trigger=CronTrigger(hour=3, minute=0, timezone=THAILAND_TZ),
        id='auto_backup_settings_to_drive',
        name='Auto Backup Settings to Drive',
        args=[flask_app_instance], # Pass app instance
        replace_existing=True
    )
    current_app.logger.info("Scheduled 'Auto Backup Settings to Drive' for 03:00 THA daily.")

    current_app.logger.info(f"Current scheduled jobs: {scheduler.get_jobs()}")

def cleanup_scheduler():
    """Shuts down the scheduler cleanly."""
    if scheduler.running:
        scheduler.shutdown()
        if flask_app_instance:
            with flask_app_instance.app_context():
                flask_app_instance.logger.info("Scheduler shut down.")
        else:
            print("Scheduler shut down (no app instance for logging).")
    else:
        if flask_app_instance:
            with flask_app_instance.app_context():
                flask_app_instance.logger.info("Scheduler was not running, no need to shut down.")
        else:
            print("Scheduler was not running, no need to shut down (no app instance for logging).")


# --- Scheduled Jobs Functions (now accept app_instance) ---
def send_appointment_reminders_job(admin_group_id, manager_user_id, app_instance):
    with app_instance.app_context(): # Use the passed app_instance
        app_instance.logger.info("Running send_appointment_reminders_job.")
        user_creds = get_app_settings().get('admin_credentials') 
        if not user_creds:
            app_instance.logger.error("No admin credentials found for appointment reminders.")
            return

        all_tasks = get_google_tasks_for_report(show_completed=False, credentials=user_creds)
        if not all_tasks:
            app_instance.logger.info("No tasks found for appointment reminders today.")
            return

        today_thai = datetime.datetime.now(THAILAND_TZ).date()
        today_tasks = [
            task for task in all_tasks
            if task.get('due') and datetime.datetime.fromisoformat(task['due'].replace('Z', '+00:00')).astimezone(THAILAND_TZ).date() == today_thai
        ]

        if today_tasks:
            messages = [TextSendMessage(text="⏰ แจ้งเตือนงานนัดหมายวันนี้:")]
            for task in today_tasks:
                messages.append(create_task_flex_message(task))
            
            if admin_group_id:
                line_bot_api.push_message(admin_group_id, messages)
            if manager_user_id:
                line_bot_api.push_message(manager_user_id, messages)
            app_instance.logger.info(f"Sent {len(today_tasks)} appointment reminders.")
        else:
            app_instance.logger.info("No appointments today to send reminders for.")

def send_outstanding_tasks_report_job(admin_group_id, manager_user_id, app_instance):
    with app_instance.app_context(): # Use the passed app_instance
        app_instance.logger.info("Running send_outstanding_tasks_report_job.")
        user_creds = get_app_settings().get('admin_credentials')
        if not user_creds:
            app_instance.logger.error("No admin credentials found for outstanding tasks report.")
            return

        all_tasks = get_google_tasks_for_report(show_completed=False, credentials=user_creds)
        if not all_tasks:
            app_instance.logger.info("No outstanding tasks found.")
            return

        today_thai = datetime.datetime.now(THAILAND_TZ).date()
        outstanding_tasks = [
            task for task in all_tasks
            if task.get('status') == 'needsAction' and task.get('due') and 
               datetime.datetime.fromisoformat(task['due'].replace('Z', '+00:00')).astimezone(THAILAND_TZ).date() <= today_thai
        ]

        if outstanding_tasks:
            messages = [TextSendMessage(text="⚠️ รายงานงานค้าง (ที่ถึงกำหนดแล้วแต่ยังไม่เสร็จ):")]
            for task in outstanding_tasks:
                messages.append(create_task_flex_message(task))

            if admin_group_id:
                line_bot_api.push_message(admin_group_id, messages)
            if manager_user_id:
                line_bot_api.push_message(manager_user_id, messages)
            app_instance.logger.info(f"Sent {len(outstanding_tasks)} outstanding tasks report.")
        else:
            app_instance.logger.info("No outstanding tasks to report.")

def send_customer_followup_report_job(admin_group_id, manager_user_id, app_instance):
    with app_instance.app_context(): # Use the passed app_instance
        app_instance.logger.info("Running send_customer_followup_report_job.")
        user_creds = get_app_settings().get('admin_credentials')
        if not user_creds:
            app_instance.logger.error("No admin credentials found for customer follow-up report.")
            return

        all_tasks = get_google_tasks_for_report(show_completed=True, credentials=user_creds)
        if not all_tasks:
            app_instance.logger.info("No tasks found for customer follow-up report.")
            return

        followup_tasks = []
        today_thai = datetime.datetime.now(THAILAND_TZ).date()
        
        for task in all_tasks:
            if task.get('status') == 'completed' and task.get('completed'):
                completed_dt = datetime.datetime.fromisoformat(task['completed'].replace('Z', '+00:00')).astimezone(THAILAND_TZ)
                if (today_thai - completed_dt.date()).days in [1, 2, 3]:
                    followup_tasks.append(task)
        
        if followup_tasks:
            messages = [TextSendMessage(text="📞 รายงานงานที่อาจต้องติดตามผลลูกค้า:")]
            for task in followup_tasks:
                messages.append(create_task_flex_message(task))

            if admin_group_id:
                line_bot_api.push_message(admin_group_id, messages)
            if manager_user_id:
                line_bot_api.push_message(manager_user_id, messages)
            app_instance.logger.info(f"Sent {len(followup_tasks)} customer follow-up tasks report.")
        else:
            app_instance.logger.info("No customer follow-up tasks to report.")

def scheduled_backup_job(app_instance):
    with app_instance.app_context(): # Use the passed app_instance
        app_instance.logger.info("Running scheduled_backup_job.")
        return backup_settings_to_drive()