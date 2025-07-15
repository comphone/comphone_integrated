from pathlib import Path

# รายการโฟลเดอร์ที่ต้องสร้าง
folders = [
    "blueprints", "templates", "static", "instance", "logs", "credentials", "backups",
    "templates/auth", "templates/main", "templates/tasks", "templates/customers",
    "templates/pos", "templates/service_jobs", "templates/errors",
    "static/css", "static/js", "static/images", "static/uploads"
]

# สร้างโฟลเดอร์ถ้ายังไม่มี
for folder in folders:
    path = Path(folder)
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created folder: {folder}")
    else:
        print(f"ℹ️ Folder already exists: {folder}")

# สร้างไฟล์ __init__.py ใน blueprints
init_file = Path("blueprints/__init__.py")
if not init_file.exists():
    init_file.write_text("# Package init\n")
    print(f"✅ Created file: {init_file}")
else:
    print(f"ℹ️ File already exists: {init_file}")
