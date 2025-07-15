# comphone/__init__.py - Fixed Version (แก้ปัญหา Blueprint conflicts)

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import config
from sqlalchemy import MetaData
import os

# SQLAlchemy naming convention สำหรับ constraints
convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

# Initialize extensions (แต่ยังไม่ผูกกับ app)
db = SQLAlchemy(metadata=MetaData(naming_convention=convention))
migrate = Migrate()
login = LoginManager()

def create_app(config_name='default'):
    """Application factory pattern - Clean version"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    login.init_app(app)
    
    # Configure login manager
    login.login_view = 'auth.login'
    login.login_message = 'กรุณาเข้าสู่ระบบเพื่อใช้งาน'
    login.login_message_category = 'info'

    # Create upload folder
    upload_folder = app.config.get('UPLOAD_FOLDER')
    if upload_folder and not os.path.exists(upload_folder):
        try:
            os.makedirs(upload_folder)
        except OSError:
            pass

    # Register blueprints (import ภายใน function เพื่อหลีกเลี่ยง circular import)
    with app.app_context():
        register_blueprints(app)
    
    return app

def register_blueprints(app):
    """Register blueprints safely"""
    
    # Import blueprints ภายใน function
    from comphone.core.routes import core_bp
    from comphone.auth.routes import auth_bp
    
    # Register blueprints
    app.register_blueprint(core_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    print("✅ Blueprints registered successfully")