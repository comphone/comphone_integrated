"""
Comphone Integrated System - Enhanced Configuration
Complete configuration management with environment support
"""

import os
from datetime import timedelta
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.absolute()

class Config:
    """Base configuration class"""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'comphone-integrated-system-secret-key-change-in-production'
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{BASE_DIR}/comphone_integrated.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'connect_args': {'timeout': 20}
    }
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.environ.get('SESSION_TIMEOUT_HOURS', 24)))
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    UPLOAD_FOLDER = BASE_DIR / 'static' / 'uploads'
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}
    
    # Business Configuration
    BUSINESS_NAME = os.environ.get('BUSINESS_NAME', 'Comphone Service Center')
    BUSINESS_PHONE = os.environ.get('BUSINESS_PHONE', '02-123-4567')
    BUSINESS_EMAIL = os.environ.get('BUSINESS_EMAIL', 'info@comphone.com')
    BUSINESS_ADDRESS = os.environ.get('BUSINESS_ADDRESS', 'Bangkok, Thailand')
    BUSINESS_WEBSITE = os.environ.get('BUSINESS_WEBSITE', 'https://comphone.com')
    BUSINESS_TAX_ID = os.environ.get('BUSINESS_TAX_ID', '0105544000000')
    
    # Tax Configuration
    DEFAULT_TAX_RATE = float(os.environ.get('DEFAULT_TAX_RATE', 7.0))
    TAX_ENABLED = os.environ.get('TAX_ENABLED', 'True').lower() == 'true'
    
    # Currency Configuration
    CURRENCY_CODE = os.environ.get('CURRENCY_CODE', 'THB')
    CURRENCY_SYMBOL = os.environ.get('CURRENCY_SYMBOL', '฿')
    
    # Localization
    DEFAULT_LANGUAGE = os.environ.get('DEFAULT_LANGUAGE', 'th')
    DEFAULT_TIMEZONE = os.environ.get('DEFAULT_TIMEZONE', 'Asia/Bangkok')
    SUPPORTED_LANGUAGES = ['th', 'en']
    
    # LINE Bot Configuration
    LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
    LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
    LINE_BOT_ENABLED = bool(LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET)
    
    # LINE Notify Configuration
    LINE_NOTIFY_TOKEN = os.environ.get('LINE_NOTIFY_TOKEN')
    LINE_NOTIFY_ENABLED = bool(LINE_NOTIFY_TOKEN)
    
    # Google API Configuration
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
    GOOGLE_CREDENTIALS_FILE = BASE_DIR / 'credentials' / 'google_credentials.json'
    GOOGLE_TOKEN_FILE = BASE_DIR / 'credentials' / 'google_token.json'
    GOOGLE_SCOPES = [
        'https://www.googleapis.com/auth/tasks',
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/drive.file'
    ]
    
    # Email Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', BUSINESS_EMAIL)
    
    # Security Configuration
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    BCRYPT_LOG_ROUNDS = 12
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    RATELIMIT_DEFAULT = "100 per hour"
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT', 'False').lower() == 'true'
    LOG_FILE = BASE_DIR / 'logs' / 'comphone.log'
    
    # Task Configuration
    DEFAULT_TASK_PRIORITY = os.environ.get('DEFAULT_TASK_PRIORITY', 'medium')
    AUTO_ASSIGN_TASKS = os.environ.get('AUTO_ASSIGN_TASKS', 'False').lower() == 'true'
    TASK_REMINDER_ENABLED = os.environ.get('TASK_REMINDER_ENABLED', 'True').lower() == 'true'
    OVERDUE_REMINDER_HOURS = int(os.environ.get('OVERDUE_REMINDER_HOURS', 24))
    
    # POS Configuration
    ALLOW_NEGATIVE_STOCK = os.environ.get('ALLOW_NEGATIVE_STOCK', 'False').lower() == 'true'
    AUTO_REDUCE_STOCK = os.environ.get('AUTO_REDUCE_STOCK', 'True').lower() == 'true'
    RECEIPT_FOOTER_TEXT = os.environ.get('RECEIPT_FOOTER_TEXT', 'ขอบคุณที่ใช้บริการ')
    
    # Notification Configuration
    NOTIFICATION_CHANNELS = ['web', 'line', 'email']
    DEFAULT_NOTIFICATION_CHANNELS = ['web']
    
    # Backup Configuration
    BACKUP_ENABLED = os.environ.get('BACKUP_ENABLED', 'True').lower() == 'true'
    BACKUP_INTERVAL_HOURS = int(os.environ.get('BACKUP_INTERVAL_HOURS', 24))
    BACKUP_RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', 30))
    BACKUP_LOCATION = BASE_DIR / 'backups'
    
    # API Configuration
    API_RATE_LIMIT = os.environ.get('API_RATE_LIMIT', '100 per hour')
    API_KEY_REQUIRED = os.environ.get('API_KEY_REQUIRED', 'False').lower() == 'true'
    
    # Pagination Configuration
    ITEMS_PER_PAGE = int(os.environ.get('ITEMS_PER_PAGE', 20))
    MAX_ITEMS_PER_PAGE = int(os.environ.get('MAX_ITEMS_PER_PAGE', 100))
    
    @staticmethod
    def init_app(app):
        """Initialize app configuration"""
        # Create necessary directories
        directories = [
            Config.UPLOAD_FOLDER,
            BASE_DIR / 'logs',
            BASE_DIR / 'static',
            BASE_DIR / 'static' / 'css',
            BASE_DIR / 'static' / 'js',
            BASE_DIR / 'static' / 'images',
            BASE_DIR / 'instance',
            BASE_DIR / 'credentials',
            Config.BACKUP_LOCATION
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            
        # Setup logging
        if not app.debug and not app.testing:
            Config.setup_logging(app)
    
    @staticmethod
    def setup_logging(app):
        """Setup application logging"""
        import logging
        from logging.handlers import RotatingFileHandler, SMTPHandler
        
        # Set log level
        log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
        
        # Create logs directory
        Config.LOG_FILE.parent.mkdir(exist_ok=True)
        
        # File handler
        file_handler = RotatingFileHandler(
            Config.LOG_FILE,
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(log_level)
        app.logger.addHandler(file_handler)
        
        # Console handler
        if Config.LOG_TO_STDOUT:
            import sys
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setLevel(log_level)
            app.logger.addHandler(stream_handler)
        
        # Email handler for errors
        if Config.MAIL_SERVER and Config.MAIL_USERNAME:
            mail_handler = SMTPHandler(
                mailhost=(Config.MAIL_SERVER, Config.MAIL_PORT),
                fromaddr=Config.MAIL_DEFAULT_SENDER,
                toaddrs=[Config.BUSINESS_EMAIL],
                subject='Comphone System Error',
                credentials=(Config.MAIL_USERNAME, Config.MAIL_PASSWORD),
                secure=() if Config.MAIL_USE_TLS else None
            )
            mail_handler.setLevel(logging.ERROR)
            app.logger.addHandler(mail_handler)
        
        app.logger.setLevel(log_level)
        app.logger.info('Comphone System startup')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or f'sqlite:///{BASE_DIR}/comphone_dev.db'
    
    # Security (relaxed for development)
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False
    
    # Logging
    LOG_LEVEL = 'DEBUG'
    LOG_TO_STDOUT = True
    
    # Development features
    TEMPLATES_AUTO_RELOAD = True
    SEND_FILE_MAX_AGE_DEFAULT = 0
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Additional development setup
        import logging
        logging.basicConfig(level=logging.DEBUG)
        app.logger.info('Development mode enabled')

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Database with connection pooling
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'max_overflow': 30
    }
    
    # Security
    SESSION_COOKIE_SECURE = True
    WTF_CSRF_ENABLED = True
    
    # Performance
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Production-specific logging
        import logging
        from logging.handlers import SysLogHandler
        
        syslog_handler = SysLogHandler()
        syslog_handler.setLevel(logging.WARNING)
        app.logger.addHandler(syslog_handler)
        
        app.logger.info('Production mode enabled')

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    
    # In-memory database for testing
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False
    
    # Speed up password hashing for tests
    BCRYPT_LOG_ROUNDS = 4
    
    # Disable rate limiting for tests
    RATELIMIT_ENABLED = False
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        app.logger.info('Testing mode enabled')

class StagingConfig(Config):
    """Staging configuration - similar to production but with debug info"""
    DEBUG = False
    TESTING = False
    
    # Use production-like database
    SQLALCHEMY_DATABASE_URI = os.environ.get('STAGING_DATABASE_URL') or f'sqlite:///{BASE_DIR}/comphone_staging.db'
    
    # Relaxed security for staging
    SESSION_COOKIE_SECURE = False
    
    # Enhanced logging for staging
    LOG_LEVEL = 'DEBUG'
    LOG_TO_STDOUT = True
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        app.logger.info('Staging mode enabled')

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'staging': StagingConfig,
    'default': DevelopmentConfig
}

# Helper functions for configuration
def get_config_class(config_name=None):
    """Get configuration class by name"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    return config.get(config_name, config['default'])

def validate_config():
    """Validate configuration settings"""
    errors = []
    
    # Check required environment variables for production
    if os.environ.get('FLASK_ENV') == 'production':
        required_vars = [
            'SECRET_KEY',
            'DATABASE_URL',
            'BUSINESS_NAME',
            'BUSINESS_EMAIL'
        ]
        
        for var in required_vars:
            if not os.environ.get(var):
                errors.append(f"Missing required environment variable: {var}")
    
    # Check LINE Bot configuration
    line_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
    line_secret = os.environ.get('LINE_CHANNEL_SECRET')
    if (line_token and not line_secret) or (line_secret and not line_token):
        errors.append("Both LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET are required for LINE Bot")
    
    # Check Google API configuration
    google_client_id = os.environ.get('GOOGLE_CLIENT_ID')
    google_client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
    if (google_client_id and not google_client_secret) or (google_client_secret and not google_client_id):
        errors.append("Both GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are required for Google integration")
    
    # Check email configuration
    mail_username = os.environ.get('MAIL_USERNAME')
    mail_password = os.environ.get('MAIL_PASSWORD')
    if (mail_username and not mail_password) or (mail_password and not mail_username):
        errors.append("Both MAIL_USERNAME and MAIL_PASSWORD are required for email functionality")
    
    return errors

def create_sample_env_file():
    """Create sample .env file with all configuration options"""
    env_content = """# Comphone Integrated System Configuration
# Copy this file to .env and modify the values as needed

# Flask Environment
FLASK_ENV=development
DEBUG=True

# Security
SECRET_KEY=your-super-secret-key-change-in-production

# Database
DATABASE_URL=sqlite:///comphone_integrated.db
# For PostgreSQL: postgresql://username:password@localhost/comphone_db
# For MySQL: mysql://username:password@localhost/comphone_db

# Business Information
BUSINESS_NAME=Comphone Service Center
BUSINESS_PHONE=02-123-4567
BUSINESS_EMAIL=info@comphone.com
BUSINESS_ADDRESS=Bangkok, Thailand
BUSINESS_WEBSITE=https://comphone.com
BUSINESS_TAX_ID=0105544000000

# Tax Configuration
DEFAULT_TAX_RATE=7.0
TAX_ENABLED=True

# Currency
CURRENCY_CODE=THB
CURRENCY_SYMBOL=฿

# Localization
DEFAULT_LANGUAGE=th
DEFAULT_TIMEZONE=Asia/Bangkok

# Session Configuration
SESSION_TIMEOUT_HOURS=24
SESSION_COOKIE_SECURE=False

# LINE Bot Configuration (Optional)
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret
LINE_NOTIFY_TOKEN=your_line_notify_token

# Google API Configuration (Optional)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_API_KEY=your_google_api_key

# Email Configuration (Optional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USE_SSL=False
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password

# Task Management
DEFAULT_TASK_PRIORITY=medium
AUTO_ASSIGN_TASKS=False
TASK_REMINDER_ENABLED=True
OVERDUE_REMINDER_HOURS=24

# POS Configuration
ALLOW_NEGATIVE_STOCK=False
AUTO_REDUCE_STOCK=True
RECEIPT_FOOTER_TEXT=ขอบคุณที่ใช้บริการ

# Logging
LOG_LEVEL=INFO
LOG_TO_STDOUT=False

# Backup Configuration
BACKUP_ENABLED=True
BACKUP_INTERVAL_HOURS=24
BACKUP_RETENTION_DAYS=30

# API Configuration
API_RATE_LIMIT=100 per hour
API_KEY_REQUIRED=False

# Pagination
ITEMS_PER_PAGE=20
MAX_ITEMS_PER_PAGE=100

# Rate Limiting (Redis URL for production)
REDIS_URL=redis://localhost:6379/0
"""
    
    env_file = BASE_DIR / '.env.example'
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print(f"✅ Sample environment file created: {env_file}")
    print("📝 Copy .env.example to .env and modify the values as needed")

# Integration helpers
class IntegrationStatus:
    """Check integration status"""
    
    @staticmethod
    def line_bot_ready():
        """Check if LINE Bot is configured"""
        return bool(
            os.environ.get('LINE_CHANNEL_ACCESS_TOKEN') and 
            os.environ.get('LINE_CHANNEL_SECRET')
        )
    
    @staticmethod
    def line_notify_ready():
        """Check if LINE Notify is configured"""
        return bool(os.environ.get('LINE_NOTIFY_TOKEN'))
    
    @staticmethod
    def google_api_ready():
        """Check if Google API is configured"""
        return bool(
            os.environ.get('GOOGLE_CLIENT_ID') and
            os.environ.get('GOOGLE_CLIENT_SECRET')
        )
    
    @staticmethod
    def email_ready():
        """Check if email is configured"""
        return bool(
            os.environ.get('MAIL_USERNAME') and
            os.environ.get('MAIL_PASSWORD')
        )
    
    @staticmethod
    def get_status():
        """Get all integration statuses"""
        return {
            'line_bot': IntegrationStatus.line_bot_ready(),
            'line_notify': IntegrationStatus.line_notify_ready(),
            'google_api': IntegrationStatus.google_api_ready(),
            'email': IntegrationStatus.email_ready()
        }

# Export everything
__all__ = [
    'Config', 'DevelopmentConfig', 'ProductionConfig', 'TestingConfig', 'StagingConfig',
    'config', 'get_config_class', 'validate_config', 'create_sample_env_file',
    'IntegrationStatus', 'BASE_DIR'
]

# Auto-create .env.example if it doesn't exist
if __name__ == '__main__':
    create_sample_env_file()
    
    # Validate current configuration
    errors = validate_config()
    if errors:
        print("⚠️  Configuration validation errors:")
        for error in errors:
            print(f"   - {error}")
    else:
        print("✅ Configuration validation passed!")