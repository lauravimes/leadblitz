#!/usr/bin/env python3
"""
Minimal diagnostic script for Render deployment debugging
"""
import os
import sys

print("🔍 LEADBLITZ DEPLOYMENT DIAGNOSTICS")
print("=" * 50)

# Check Python version
print(f"Python version: {sys.version}")
print(f"Platform: {sys.platform}")

# Check critical environment variables
env_vars = [
    'DATABASE_URL',
    'OPENAI_API_KEY', 
    'ENCRYPTION_KEY',
    'SESSION_SECRET',
    'PORT'
]

print("\n📋 ENVIRONMENT VARIABLES:")
for var in env_vars:
    value = os.getenv(var)
    if value:
        # Show first 10 chars for security
        preview = value[:10] + "..." if len(value) > 10 else value
        print(f"✅ {var}: {preview}")
    else:
        print(f"❌ {var}: NOT SET")

# Test critical imports
print("\n📦 TESTING IMPORTS:")
test_imports = [
    ('os', 'os'),
    ('FastAPI', 'fastapi'),
    ('SQLAlchemy', 'sqlalchemy'), 
    ('OpenAI', 'openai'),
    ('Requests', 'requests'),
    ('BeautifulSoup', 'bs4'),
    ('Uvicorn', 'uvicorn'),
    ('Dotenv', 'dotenv'),
    ('Cryptography', 'cryptography.fernet'),
]

for name, module in test_imports:
    try:
        __import__(module)
        print(f"✅ {name}: OK")
    except ImportError as e:
        print(f"❌ {name}: FAILED - {e}")
    except Exception as e:
        print(f"⚠️ {name}: ERROR - {e}")

# Test database connection if URL exists
db_url = os.getenv('DATABASE_URL')
if db_url:
    print("\n🗄️ TESTING DATABASE CONNECTION:")
    try:
        import sqlalchemy
        engine = sqlalchemy.create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text("SELECT 1"))
            print("✅ Database connection: OK")
    except Exception as e:
        print(f"❌ Database connection: FAILED - {e}")
else:
    print("\n🗄️ DATABASE: URL not set, skipping test")

# Test file system
print("\n📁 TESTING FILE SYSTEM:")
required_files = [
    'main.py',
    'requirements.txt',
    'helpers/database.py',
    'static/index.html'
]

for file in required_files:
    if os.path.exists(file):
        print(f"✅ {file}: EXISTS")
    else:
        print(f"❌ {file}: MISSING")

print("\n🚀 ATTEMPTING MINIMAL FASTAPI START:")
try:
    from fastapi import FastAPI
    app = FastAPI()
    
    @app.get("/")
    def root():
        return {"status": "ok", "message": "LeadBlitz diagnostic successful"}
    
    print("✅ FastAPI app created successfully")
    
    # Try to start uvicorn
    import uvicorn
    port = int(os.getenv("PORT", 5000))
    print(f"🔥 Starting uvicorn on port {port}")
    
    uvicorn.run(app, host="0.0.0.0", port=port)
    
except Exception as e:
    print(f"❌ FastAPI startup failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)