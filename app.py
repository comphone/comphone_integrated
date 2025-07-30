# app.py
import os
from comphone import create_app

# สร้าง app instance โดยใช้ Application Factory
app = create_app()

if __name__ == '__main__':
    # รันแอปพลิเคชันในโหมด Debug
    # Render.com จะใช้คำสั่ง gunicorn ใน render.yaml แทน
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 8080)),
        debug=True
    )