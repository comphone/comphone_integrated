"""
Comphone Integrated System - Complete Flask Application
Main application factory and configuration
"""

import os
from flask import Flask, render_template, request, jsonify
from flask_login import LoginManager, current_user
from datetime import datetime, timezone
from config import config, get_config_class, validate_config, BASE_DIR
from models import db, User, create_tables, init_default_settings, create_sample_data

def create_app(config_name=None):
    """Create Flask application with configuration"""
    
    # Get configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    config_class = get_config_class(config_name)
    
    # Create Flask app
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize configuration
    config_class.init_app(app)
    
    # Validate configuration
    config_errors = validate_config()
    if config_errors and config_name == 'production':
        for error in config_errors:
            app.logger.error(f"Configuration error: {error}")
    
    # Initialize extensions
    init_extensions(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register template filters and functions
    register_template_helpers(app)
    
    # Initialize database
    with app.app_context():
        init_database()
    
    # Setup logging
    setup_logging(app)
    
    app.logger.info(f'Comphone System started in {config_name} mode')
    
    return app

def init_extensions(app):
    """Initialize Flask extensions"""
    
    # Initialize SQLAlchemy
    db.init_app(app)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'กรุณาเข้าสู่ระบบเพื่อใช้งาน'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    @login_manager.unauthorized_handler
    def unauthorized():
        if request.is_json:
            return jsonify({'error': 'Authentication required'}), 401
        return render_template('auth/login.html'), 401

def register_blueprints(app):
    """Register application blueprints"""
    
    # Import blueprints
    from blueprints.main import main_bp
    from blueprints.auth import auth_bp
    from blueprints.tasks import tasks_bp
    from blueprints.customers import customers_bp
    from blueprints.pos import pos_bp
    from blueprints.service_jobs import service_jobs_bp
    from blueprints.line_bot import line_bp
    from blueprints.google_api import google_bp
    from blueprints.api import api_bp
    
    # Register blueprints
    app.register_blueprint(main_bp, url_prefix='/')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(tasks_bp, url_prefix='/tasks')
    app.register_blueprint(customers_bp, url_prefix='/customers')
    app.register_blueprint(pos_bp, url_prefix='/pos')
    app.register_blueprint(service_jobs_bp, url_prefix='/service')
    app.register_blueprint(line_bp, url_prefix='/line')
    app.register_blueprint(google_bp, url_prefix='/google')
    app.register_blueprint(api_bp, url_prefix='/api')

def register_error_handlers(app):
    """Register error handlers"""
    
    @app.errorhandler(400)
    def bad_request_error(error):
        if request.is_json:
            return jsonify({'error': 'Bad request'}), 400
        return render_template('errors/400.html'), 400
    
    @app.errorhandler(401)
    def unauthorized_error(error):
        if request.is_json:
            return jsonify({'error': 'Unauthorized'}), 401
        return render_template('errors/401.html'), 401
    
    @app.errorhandler(403)
    def forbidden_error(error):
        if request.is_json:
            return jsonify({'error': 'Forbidden'}), 403
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found_error(error):
        if request.is_json:
            return jsonify({'error': 'Not found'}), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(429)
    def ratelimit_handler(error):
        if request.is_json:
            return jsonify({'error': 'Rate limit exceeded'}), 429
        return render_template('errors/429.html'), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        if request.is_json:
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('errors/500.html'), 500

def register_template_helpers(app):
    """Register template filters and global functions"""
    
    from models import get_setting
    
    @app.template_filter('datetime')
    def datetime_filter(datetime_obj, format='%d/%m/%Y %H:%M'):
        """Format datetime for templates"""
        if datetime_obj:
            if hasattr(datetime_obj, 'strftime'):
                return datetime_obj.strftime(format)
        return ''
    
    @app.template_filter('date')
    def date_filter(date_obj, format='%d/%m/%Y'):
        """Format date for templates"""
        if date_obj:
            if hasattr(date_obj, 'strftime'):
                return date_obj.strftime(format)
        return ''
    
    @app.template_filter('currency')
    def currency_filter(amount):
        """Format currency for templates"""
        if amount is None:
            return '฿0.00'
        return f"฿{float(amount):,.2f}"
    
    @app.template_filter('percentage')
    def percentage_filter(value, decimals=1):
        """Format percentage for templates"""
        if value is None:
            return '0%'
        return f"{float(value):.{decimals}f}%"
    
    @app.template_filter('status_badge')
    def status_badge_filter(status):
        """Get Bootstrap badge class for status"""
        badge_classes = {
            'pending': 'bg-warning text-dark',
            'in_progress': 'bg-info text-white',
            'completed': 'bg-success text-white',
            'cancelled': 'bg-danger text-white',
            'on_hold': 'bg-secondary text-white',
            'received': 'bg-primary text-white',
            'diagnosed': 'bg-info text-white',
            'waiting_parts': 'bg-warning text-dark',
            'in_repair': 'bg-info text-white',
            'testing': 'bg-warning text-dark',
            'delivered': 'bg-success text-white',
            'paid': 'bg-success text-white',
            'partial': 'bg-warning text-dark',
            'refunded': 'bg-secondary text-white',
            'active': 'bg-success text-white',
            'inactive': 'bg-secondary text-white'
        }
        return badge_classes.get(str(status).lower(), 'bg-secondary text-white')
    
    @app.template_filter('priority_badge')
    def priority_badge_filter(priority):
        """Get Bootstrap badge class for priority"""
        badge_classes = {
            'low': 'bg-success text-white',
            'medium': 'bg-info text-white',
            'high': 'bg-warning text-dark',
            'urgent': 'bg-danger text-white'
        }
        return badge_classes.get(str(priority).lower(), 'bg-secondary text-white')
    
    @app.template_filter('truncate_words')
    def truncate_words_filter(text, length=50):
        """Truncate text to specified length"""
        if not text:
            return ''
        if len(text) <= length:
            return text
        return text[:length] + '...'
    
    @app.template_filter('filesize')
    def filesize_filter(bytes_size):
        """Format file size for display"""
        if not bytes_size:
            return '0 B'
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} TB"
    
    @app.context_processor
    def inject_global_vars():
        """Inject global variables into all templates"""
        return {
            'business_name': get_setting('business_name', 'Comphone Service Center'),
            'business_phone': get_setting('business_phone', '02-123-4567'),
            'business_email': get_setting('business_email', 'info@comphone.com'),
            'current_year': datetime.now().year,
            'app_version': '1.0.0',
            'now': datetime.now(timezone.utc)
        }
    
    @app.context_processor
    def inject_user_vars():
        """Inject user-specific variables"""
        if current_user.is_authenticated:
            return {
                'user_full_name': current_user.full_name,
                'user_role': current_user.role.value,
                'user_is_admin': current_user.is_admin,
                'user_is_technician': current_user.is_technician
            }
        return {}

def init_database():
    """Initialize database tables and default data"""
    try:
        # Create all tables
        print("🔧 Creating database tables...")
        if create_tables():
            print("✅ Database tables created successfully!")
        
        # Initialize default settings
        print("⚙️  Initializing default settings...")
        init_default_settings()
        print("✅ Default settings initialized!")
        
        # Create sample data if no users exist
        if User.query.count() == 0:
            print("👥 Creating sample data...")
            create_sample_data()
            print("✅ Sample data created successfully!")
        else:
            print("ℹ️  Sample data already exists, skipping...")
        
        print("🎉 Database initialization completed!")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise e

def setup_logging(app):
    """Setup application logging"""
    if not app.debug and not app.testing:
        import logging
        from logging.handlers import RotatingFileHandler
        
        # Ensure logs directory exists
        logs_dir = BASE_DIR / 'logs'
        logs_dir.mkdir(exist_ok=True)
        
        # Setup file handler
        file_handler = RotatingFileHandler(
            logs_dir / 'comphone.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)

def create_default_directories():
    """Create necessary directories"""
    directories = [
        BASE_DIR / 'static',
        BASE_DIR / 'static' / 'uploads',
        BASE_DIR / 'static' / 'css',
        BASE_DIR / 'static' / 'js',
        BASE_DIR / 'static' / 'images',
        BASE_DIR / 'templates',
        BASE_DIR / 'instance',
        BASE_DIR / 'logs',
        BASE_DIR / 'credentials',
        BASE_DIR / 'backups'
    ]
    
    print("📁 Creating necessary directories...")
    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"   ✅ {directory.name}")
        except Exception as e:
            print(f"   ⚠️  Could not create {directory}: {e}")

# Create application instance
app = create_app()

if __name__ == '__main__':
    # Create directories first
    create_default_directories()
    
    # Print startup information
    print("=" * 60)
    print("🚀 Starting Comphone Integrated System")
    print("=" * 60)
    print(f"📊 Dashboard: http://localhost:5000")
    print(f"👤 Admin Login: admin/admin123")
    print(f"🔧 Technician Login: technician/tech123")
    print(f"💰 Sales Login: sales/sales123")
    print("=" * 60)
    print("🎯 Available Features:")
    print("   • Dashboard with real-time statistics")
    print("   • Task Management with assignment")
    print("   • Customer Management with devices")
    print("   • POS System with inventory")
    print("   • Service Job Tracking")
    print("   • User Management (Admin)")
    print("   • System Settings")
    print("   • Activity Logging")
    print("=" * 60)
    
    # Get configuration info
    config_name = os.environ.get('FLASK_ENV', 'development')
    debug_mode = app.config.get('DEBUG', False)
    
    print(f"🔧 Environment: {config_name}")
    print(f"🐛 Debug Mode: {'Enabled' if debug_mode else 'Disabled'}")
    print(f"💾 Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    # Check integrations
    from config import IntegrationStatus
    integrations = IntegrationStatus.get_status()
    print(f"🤖 LINE Bot: {'✅ Ready' if integrations['line_bot'] else '❌ Not configured'}")
    print(f"📧 Email: {'✅ Ready' if integrations['email'] else '❌ Not configured'}")
    print(f"🔗 Google API: {'✅ Ready' if integrations['google_api'] else '❌ Not configured'}")
    
    print("=" * 60)
    print("🎉 Ready to serve requests!")
    print("=" * 60)
    
    # Run the application
    try:
        app.run(
            debug=debug_mode,
            host='0.0.0.0',
            port=int(os.environ.get('PORT', 5000)),
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down Comphone System...")
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        raise