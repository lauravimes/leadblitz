from fastapi import Request, HTTPException
from helpers.models import SessionLocal, User
from helpers.auth import verify_session_token

def get_current_user(request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session_data = verify_session_token(session_token)
    if not session_data:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == session_data["user_id"]).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        return user
    finally:
        db.close()

def get_current_user_optional(request: Request):
    try:
        return get_current_user(request)
    except HTTPException:
        return None
