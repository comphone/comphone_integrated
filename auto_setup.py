#!/usr/bin/env python3
"""
Comphone Integrated System - Automated Setup Script
This script creates all necessary files and directories for the system
Run: python auto_setup.py
"""

import os
import sys
from pathlib import Path

def create_directories():
    """Create all necessary directories"""
    directories = [
        'blueprints',
        'templates/auth',
        'templates/main',
        'templates/tasks',
        'templates/pos',
        'templates/customers',
        'templates/service_jobs',
        'templates/errors',
        'static/css',
        'static/js',
        'static/uploads',
        'instance',
        'logs',
        'credentials'
    ]
    
    print("📁 Creating directories...")
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"   ✅ {directory}")

def create_requirements_txt():
    """Create requirements.txt file"""
    content = """# Flask Framework
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-Login==0.6.3
Flask-Migrate==4.0.5
Flask-WTF==1.1.1

# Database
SQLAlchemy==2.0.21
alembic==1.12.0

# Security
Werkzeug==2.3.7
cryptography==41.0.4

# External APIs
google-api-python-client==2.100.0
google-auth-httplib2==0.1.1
google-auth-oauthlib==1.1.0
line-bot-sdk==3.5.0
requests==2.31.0

# Utilities
python-dotenv==1.0.0
python-dateutil==2.8.2
click==8.1.7
itsdangerous==2.1.2
MarkupSafe==2.1.3
Jinja2==3.1.2

# Development Tools (Optional)
pytest==7.4.2
pytest-flask==1.2.0
coverage==7.3.0
black==23.7.0
flake8==6.0.0

# Production Server (Optional)
gunicorn==21.2.0
"""
    
    with open('requirements.txt', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ requirements.txt created")

def create_env_file():
    """Create .env file"""
    content = """# Comphone Integrated System - Environment Configuration

# Flask Settings
FLASK_ENV=development
SECRET_KEY=comphone-integrated-system-secret-key-change-in-production
DEBUG=True

# Database Configuration
DATABASE_URL=sqlite:///instance/comphone_integrated.db
SQLALCHEMY_TRACK_MODIFICATIONS=False

# LINE Bot Configuration
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token_here
LINE_CHANNEL_SECRET=your_line_channel_secret_here
LINE_WEBHOOK_URL=https://your-domain.com/line/webhook

# Google API Configuration
GOOGLE_CREDENTIALS_PATH=credentials/google_credentials.json
GOOGLE_DRIVE_FOLDER_ID=your_google_drive_folder_id_here
GOOGLE_TASKS_LIST_ID=your_google_tasks_list_id_here

# Business Configuration
BUSINESS_NAME=Comphone Service Center
BUSINESS_PHONE=02-123-4567
BUSINESS_EMAIL=info@comphone.com
BUSINESS_ADDRESS=Bangkok, Thailand

# System Configuration
DEFAULT_TAX_RATE=7.0
TASK_SYNC_INTERVAL=300
NOTIFICATION_ENABLED=True
NOTIFICATION_TIMES=09:00,17:00
ENABLE_AUTO_SYNC=True

# File Upload Configuration
MAX_CONTENT_LENGTH=16777216
UPLOAD_FOLDER=static/uploads
ALLOWED_EXTENSIONS=txt,pdf,png,jpg,jpeg,gif,doc,docx,xls,xlsx

# Security Configuration
BCRYPT_LOG_ROUNDS=12
SESSION_COOKIE_SECURE=False
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# API Configuration
API_RATE_LIMIT=100/hour

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
"""
    
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ .env created")

def create_gitignore():
    """Create .gitignore file"""
    content = """# Comphone Integrated System - Git Ignore

# Environment files
.env
.env.local
.env.development.local
.env.test.local
.env.production.local

# Database
*.db
*.sqlite
*.sqlite3
instance/

# Logs
logs/
*.log

# Credentials
credentials/google_credentials.json
credentials/google_token.json
*.pem
*.key

# Uploads
static/uploads/*
!static/uploads/.gitkeep

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
pip-wheel-metadata/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual Environment
venv/
env/
ENV/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Flask
instance/
.webassets-cache

# Coverage
htmlcov/
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/
.pytest_cache/

# Migrations (if using Flask-Migrate)
migrations/versions/

# Configuration backups
*.bak
*.backup
*.old
"""
    
    with open('.gitignore', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ .gitignore created")

def create_init_files():
    """Create __init__.py files"""
    init_files = [
        'blueprints/__init__.py'
    ]
    
    for file_path in init_files:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('# Package initialization\n')
        print(f"✅ {file_path} created")

def create_placeholder_files():
    """Create placeholder files"""
    placeholders = [
        'static/uploads/.gitkeep',
        'logs/.gitkeep',
        'credentials/.gitkeep'
    ]
    
    for placeholder in placeholders:
        with open(placeholder, 'w', encoding='utf-8') as f:
            f.write('# Placeholder file to keep directory in git\n')
        print(f"✅ {placeholder} created")

def create_readme():
    """Create README.md file"""
    content = """# 🎯 Comphone Integrated System

Complete POS + LINE Tasks Auto Integration System

## 🚀 Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   python run.py
   ```

3. **Access the system:**
   - URL: http://localhost:5000
   - Admin: admin/admin123
   - Technician: technician/tech123

## 📱 Features

- ✅ **POS System**: Sales, inventory, customer management
- ✅ **Task Management**: Google Tasks integration
- ✅ **LINE Bot**: Customer communication
- ✅ **Service Jobs**: Repair tracking
- ✅ **User Management**: Role-based access
- ✅ **Reporting**: Sales and performance analytics

## 🔧 Configuration

Edit `.env` file to customize:
- Business information
- API credentials
- System settings

## 📚 Documentation

- Complete setup guide in `docs/installation.md`
- API documentation in `docs/api.md`
- User manual in `docs/user_guide.md`

## 🆘 Support

If you encounter issues:
1. Check `logs/app.log` for errors
2. Verify virtual environment is activated
3. Ensure all dependencies are installed

---

Built with ❤️ using Flask, SQLAlchemy, and modern web technologies.
"""
    
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ README.md created")

def print_manual_steps():
    """Print manual steps for user"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     📋 MANUAL STEPS REQUIRED                                ║
╚══════════════════════════════════════════════════════════════════════════════╝

🔥 IMPORTANT: You need to manually create these files by copying content from
the artifacts provided in the conversation:

📄 Core Files (REQUIRED):
   1. models.py         - Copy from "models.py - Complete Database Models"
   2. config.py         - Copy from "config.py - System Configuration"
   3. app.py           - Copy from "app.py - Main Flask Application"
   4. run.py           - Copy from "run.py - Simple Application Runner"

📁 Blueprint Files (REQUIRED):
   Copy each blueprint from "Complete Blueprint Files" artifact:
   1. blueprints/auth.py
   2. blueprints/main.py
   3. blueprints/tasks.py
   4. blueprints/pos.py
   5. blueprints/customers.py
   6. blueprints/service_jobs.py
   7. blueprints/line_bot.py
   8. blueprints/google_api.py
   9. blueprints/api.py

🎨 Template Files (REQUIRED):
   Copy each template from the template artifacts:
   1. templates/base.html
   2. templates/auth/login.html
   3. templates/auth/profile.html
   4. templates/main/dashboard.html
   5. templates/tasks/list.html
   6. templates/tasks/create.html
   7. templates/pos/sales.html
   8. templates/pos/products.html
   9. templates/customers/list.html
   10. templates/customers/create.html
   11. templates/service_jobs/list.html
   12. templates/service_jobs/create.html
   13. templates/errors/404.html
   14. templates/errors/500.html

⚡ After copying all files:

1. Install dependencies:
   pip install -r requirements.txt

2. Run the application:
   python run.py

3. Access: http://localhost:5000
   Login: admin/admin123 or technician/tech123

🎯 The system will automatically:
   - Create database tables
   - Add sample data
   - Set up default users
   - Initialize settings

💡 Pro Tip: Copy files in this order:
   1. models.py (first)
   2. config.py
   3. Blueprint files
   4. Template files
   5. app.py and run.py (last)

""")

def main():
    """Main setup function"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  🎯 Comphone System Auto Setup                              ║
║                  Creating project structure...                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        # Create project structure
        create_directories()
        create_requirements_txt()
        create_env_file()
        create_gitignore()
        create_init_files()
        create_placeholder_files()
        create_readme()
        
        print("\n✅ Project structure created successfully!")
        print_manual_steps()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        return False

if __name__ == '__main__':
    success = main()
    if success:
        print("\n🎉 Setup completed! Follow the manual steps above to finish.")
    else:
        print("\n💥 Setup failed! Please check the error messages.")
    
    sys.exit(0 if success else 1)