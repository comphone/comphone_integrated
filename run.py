#!/usr/bin/env python3
"""
Comphone Integrated System - Application Launcher
Run: python run.py
"""

try:
    from app import app
    
    if __name__ == '__main__':
        print("🚀 Starting Comphone Integrated System...")
        print("📊 Dashboard: http://localhost:5000")
        print("👤 Admin Login: admin/admin123")
        print("🔧 Technician Login: technician/tech123")
        print("=" * 50)
        
        app.run(debug=True, host='0.0.0.0', port=5000)
        
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("🔧 Please create the required files first!")
    print("📋 Missing files:")
    print("   - app.py")
    print("   - models.py") 
    print("   - config.py")
    print("   - requirements.txt")
    print("\n💡 Follow the step-by-step guide to create all files.")