# create_data.py
# สคริปต์สำหรับสร้างข้อมูลตัวอย่างโดยเฉพาะ

from app import create_app
from models import create_sample_data

print("⚙️  Initializing application to create sample data...")

# สร้าง app instance และ app context
app = create_app()
with app.app_context():
    print("⏳ Creating sample data... (admin, technician, sales)")
    
    # เรียกใช้ฟังก์ชันสร้างข้อมูลตัวอย่าง
    create_sample_data()
    
    print("✅ Sample data created successfully!")
