#!/usr/bin/env python3
"""
Ultra-minimal LeadBlitz test - NO database required
"""
import os
from fastapi import FastAPI

print("🚀 MINIMAL LEADBLITZ TEST")
print("=" * 40)

# Check basic environment
print(f"Python working: ✅")
print(f"FastAPI available: ✅") 

app = FastAPI()

@app.get("/")
def root():
    return {"status": "success", "message": "LeadBlitz minimal test working!"}

@app.get("/health")
def health():
    return {"status": "healthy", "database": "not required for this test"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5000))
    print(f"🔥 Starting on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)