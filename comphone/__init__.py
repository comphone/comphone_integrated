# comphone/__init__.py
import os
import atexit
import datetime
import logging # เพิ่ม import logging
from flask import Flask, render_template, session, request # เพิ่ม request

# เพิ่ม import สำหรับ Jinja2 filter
from dateutil.parser import parse as date_parse 

from dotenv import load_dotenv
load_dotenv()

from .extensions import csrf, scheduler

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # --- ตั้งค่า Logger สำหรับแอปพลิเคชัน ---
    app.logger.setLevel(logging.DEBUG) 
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.info("Flask app creation started.")

    # --- ตั้งค่าพื้นฐานสำหรับแอปพลิเคชัน ---
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('FLASK_SECRET_KEY', 'a_very_secret_key_for_development'),
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,
    )
    app.logger.debug(f"FLASK_SECRET_KEY is set: {bool(os.environ.get('FLASK_SECRET_KEY'))}") # เพิ่ม Log

    # --- ลงทะเบียน Jinja2 Filters ---
    app.jinja_env.filters['date_parse'] = date_parse # <--- เพิ่มบรรทัดนี้
    app.logger.info("Jinja2 custom filters registered.")


    # --- เริ่มต้นการทำงานของส่วนเสริม (Extensions) ---
    csrf.init_app(app)
    app.logger.info("CSRF extension initialized.")

    # IMPORT app_scheduler HERE TO AVOID CIRCULAR IMPORT WITH set_flask_app
    from .app_scheduler import run_scheduler, cleanup_scheduler, initialize_scheduler, set_flask_app

    # Set the Flask app instance in app_scheduler BEFORE initializing scheduler jobs
    set_flask_app(app) 

    with app.app_context():
        from .settings_manager import load_settings_from_drive_on_startup

        app.logger.info("Entering app context for initial setup (settings & scheduler).")

        try:
            load_settings_from_drive_on_startup()
            app.logger.info("Settings loaded from Google Drive successfully.")
        except Exception as e:
            app.logger.error(f"Error loading settings from Google Drive: {e}", exc_info=True)

        try:
            initialize_scheduler()
            run_scheduler() 
            app.logger.info("Scheduler initialized and started successfully.")
        except Exception as e:
            app.logger.error(f"Error initializing or starting scheduler: {e}", exc_info=True)

        atexit.register(cleanup_scheduler)
        app.logger.info("Scheduler cleanup registered for application exit.")

    from . import main_routes, tool_routes, api_routes, line_handler
    app.register_blueprint(main_routes.bp)
    app.register_blueprint(tool_routes.bp)
    app.register_blueprint(api_routes.bp)
    app.register_blueprint(line_handler.bp)
    app.logger.info("All Blueprints registered.")

    from .utils import THAILAND_TZ
    from .google_services import check_google_api_status

    @app.context_processor
    def inject_global_vars():
        is_logged_in = 'credentials' in session
        google_connected = False
        if is_logged_in:
            google_connected = check_google_api_status(session.get('credentials'))
        app.logger.debug(f"Context Processor: User logged in: {is_logged_in}, Google API Connected: {google_connected}")
        return {
            'now': datetime.datetime.now(THAILAND_TZ),
            'thaizone': THAILAND_TZ,
            'google_api_connected': google_connected
        }

    @app.errorhandler(404)
    def page_not_found(e):
        app.logger.warning(f"404 Not Found: {request.path}") 
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        app.logger.error(f"Server Error (500): {e}", exc_info=True) 
        return render_template('500.html'), 500

    app.logger.info("Flask app creation finished.") 
    return app