# comphone_integrated/migrate_database.py

import os
import sys
import traceback
from flask import Flask
from comphone import create_app, db
from comphone.models import User, Customer, Product, Sale, ServiceJob, ServicePartUsage

class DatabaseMigrator:
    """Migration script for old system → new Comphone Integrated DB."""

    def __init__(self, app, dry_run=False):
        self.app = app
        self.dry_run = dry_run

    def migrate(self):
        with self.app.app_context():
            try:
                print("🔄 Starting migration...")
                db.create_all()

                self.migrate_users()
                self.migrate_customers()
                self.migrate_products()
                self.migrate_sales()
                self.migrate_service_jobs()

                db.session.commit()
                print("✅ Migration completed successfully!")
            except Exception as e:
                db.session.rollback()
                print("❌ Migration failed:", e)
                print(traceback.format_exc())

    def migrate_users(self):
        print("  - Migrating users...")
        # *** ตัวอย่าง: เพิ่ม admin user (จริงควรอ่านจาก source เก่า) ***
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@comphone.com', is_admin=True)
            admin.set_password('adminpass')
            db.session.add(admin)

    def migrate_customers(self):
        print("  - Migrating customers...")
        # *** ตัวอย่าง: เพิ่ม dummy customer (จริงควรอ่านจาก source เก่า) ***
        if not Customer.query.first():
            customer = Customer(name='ชื่อลูกค้าตัวอย่าง', phone='0812345678', address='ที่อยู่ตัวอย่าง')
            db.session.add(customer)

    def migrate_products(self):
        print("  - Migrating products...")
        # *** ตัวอย่าง: เพิ่ม dummy product (จริงควรอ่านจาก source เก่า) ***
        if not Product.query.first():
            product = Product(name='สินค้าตัวอย่าง', cost_price=100, selling_price=150, quantity=10)
            db.session.add(product)

    def migrate_sales(self):
        print("  - Migrating sales...")
        # *** ตัวอย่าง: ข้าม migration จริงสำหรับ Sale ไปก่อน ***

    def migrate_service_jobs(self):
        print("  - Migrating service jobs...")
        # *** ตัวอย่าง: ข้าม migration จริงสำหรับ ServiceJob ไปก่อน ***

if __name__ == "__main__":
    # ควรตั้ง env ก่อนรัน เช่น export FLASK_ENV=development
    app = create_app()
    migrator = DatabaseMigrator(app)
    migrator.migrate()
