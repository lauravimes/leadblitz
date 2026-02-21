#!/usr/bin/env python3
"""
Production startup script for LeadBlitz on Render
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_environment():
    """Check that all required environment variables are set"""
    required_vars = [
        'DATABASE_URL',
        'OPENAI_API_KEY', 
        'ENCRYPTION_KEY',
        'SESSION_SECRET'
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)
    
    logger.info("✅ All required environment variables are set")

def main():
    """Main startup function"""
    logger.info("🚀 Starting LeadBlitz deployment...")
    
    # Check environment
    check_environment()
    
    # Import and start the app
    try:
        logger.info("Loading main application...")
        from main import app
        logger.info("✅ Main application loaded successfully")
        
        # Start uvicorn
        import uvicorn
        port = int(os.getenv("PORT", 5000))
        logger.info(f"Starting server on port {port}")
        
        uvicorn.run(
            app,
            host="0.0.0.0", 
            port=port,
            log_level="info"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()