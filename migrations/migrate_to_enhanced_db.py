# migrations/migrate_to_enhanced_db.py
"""
Database Migration Script for LINE Tasks Auto + POS Integration
Run this after updating models.py to create new tables and migrate data
"""

import sys
import os
import json
from datetime import datetime, timezone
from dateutil.parser import parse as date_parse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from comphone import create_app, db
from comphone.models import (
    User, Customer, Task, TaskReport, TaskAttachment, 
    CustomerFeedback, Product, Setting
)

def init_database():
    """Initialize the database with new tables"""
    print("🔄 Creating database tables...")
    db.create_all()
    print("✅ Database tables created successfully!")

def create_default_admin_user():
    """Create default admin user if none exists"""
    admin = db.session.scalar(db.select(User).where(User.is_admin == True))
    if not admin:
        admin = User(
            username='admin',
            email='admin@comphone.local',
            is_admin=True,
            full_name='System Administrator'
        )
        admin.set_password('admin123')  # Change this!
        db.session.add(admin)
        db.session.commit()
        print("✅ Created default admin user (username: admin, password: admin123)")
        print("⚠️  PLEASE CHANGE THE DEFAULT PASSWORD!")
    else:
        print("ℹ️  Admin user already exists")

def migrate_settings_from_json():
    """Migrate settings from JSON file to database"""
    settings_file = 'settings.json'
    if os.path.exists(settings_file):
        print("🔄 Migrating settings from JSON file to database...")
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings_data = json.load(f)
            
            for key, value in settings_data.items():
                Setting.set_setting(key, value)
            
            print("✅ Settings migrated successfully!")
            
            # Backup old file
            backup_name = f'settings_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            os.rename(settings_file, backup_name)
            print(f"📦 Original settings.json backed up as {backup_name}")
            
        except Exception as e:
            print(f"❌ Error migrating settings: {e}")
    else:
        print("ℹ️  No settings.json file found, creating default settings...")
        create_default_settings()

def create_default_settings():
    """Create default application settings"""
    default_settings = {
        'report_times': {
            'appointment_reminder_hour_thai': 7,
            'outstanding_report_hour_thai': 20,
            'customer_followup_hour_thai': 9
        },
        'line_recipients': {
            'admin_group_id': '',
            'technician_group_id': '',
            'manager_user_id': ''
        },
        'auto_backup': {
            'enabled': False,
            'hour_thai': 2,
            'minute_thai': 0
        },
        'shop_info': {
            'contact_phone': '081-XXX-XXXX',
            'line_id': '@ComphoneService'
        },
        'technician_list': [],
        'equipment_catalog': []
    }
    
    for key, value in default_settings.items():
        Setting.set_setting(key, value)
    
    print("✅ Default settings created")

def migrate_google_tasks_data():
    """Placeholder for Google Tasks data migration"""
    print("\n📋 Google Tasks Data Migration")
    print("=" * 50)
    print("ℹ️  This step requires Google Tasks API access.")
    print("ℹ️  After setting up the integration, run the data migration separately.")
    print("ℹ️  Migration script will be provided in Session 3.")

def create_sample_equipment_data():
    """Create sample equipment/products for testing"""
    print("🔄 Creating sample equipment data...")
    
    sample_equipment = [
        {'name': 'น้ำยาแอร์ R32', 'unit': 'ขวด', 'price': 150.0, 'is_equipment': True},
        {'name': 'คอมเพรสเซอร์ 1/2 HP', 'unit': 'ตัว', 'price': 2500.0, 'is_equipment': True},
        {'name': 'พัดลมคอยล์เย็น', 'unit': 'ตัว', 'price': 800.0, 'is_equipment': True},
        {'name': 'สายไฟ VCT 2x1.5', 'unit': 'เมตร', 'price': 25.0, 'is_equipment': True},
        {'name': 'เบรกเกอร์ 20A', 'unit': 'ตัว', 'price': 180.0, 'is_equipment': True},
    ]
    
    for item_data in sample_equipment:
        existing = db.session.scalar(db.select(Product).where(Product.name == item_data['name']))
        if not existing:
            product = Product(
                name=item_data['name'],
                unit=item_data['unit'],
                selling_price=item_data['price'],
                cost_price=item_data['price'] * 0.7,  # Assume 30% markup
                is_equipment=item_data['is_equipment'],
                quantity=10  # Initial stock
            )
            db.session.add(product)
    
    db.session.commit()
    print("✅ Sample equipment data created")

def run_full_migration():
    """Run complete migration process"""
    print("🚀 Starting Enhanced Database Migration")
    print("=" * 50)
    
    app = create_app()
    with app.app_context():
        try:
            # Step 1: Initialize database
            init_database()
            
            # Step 2: Create admin user
            create_default_admin_user()
            
            # Step 3: Migrate settings
            migrate_settings_from_json()
            
            # Step 4: Create sample data
            create_sample_equipment_data()
            
            # Step 5: Google Tasks migration (placeholder)
            migrate_google_tasks_data()
            
            print("\n🎉 Migration completed successfully!")
            print("\n📝 Next Steps:")
            print("1. Update environment variables for Google APIs")
            print("2. Test the enhanced POS system")
            print("3. Run Google Tasks data migration (Session 3)")
            print("4. Configure LINE Bot integration (Session 4)")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            print("💡 Make sure you have backed up your data before running migration!")
            raise

if __name__ == '__main__':
    run_full_migration()