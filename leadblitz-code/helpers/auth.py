import os
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime, timedelta
from helpers.models import User, UserAPIKeys
from sqlalchemy.orm import Session

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SESSION_SECRET = os.getenv("SESSION_SECRET")
if not SESSION_SECRET:
    raise ValueError("SESSION_SECRET environment variable is not set")

serializer = URLSafeTimedSerializer(SESSION_SECRET)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_session_token(user_id: int) -> str:
    return serializer.dumps({"user_id": user_id, "created_at": datetime.now().isoformat()})

def verify_session_token(token: str, max_age: int = 86400 * 30) -> dict:
    try:
        data = serializer.loads(token, max_age=max_age)
        return data
    except:
        return None

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email.lower()).first()

def create_user(db: Session, email: str, password: str, full_name: str = ""):
    hashed_pw = hash_password(password)
    user = User(
        email=email.lower(),
        password_hash=hashed_pw,
        full_name=full_name,
        is_active=True,
        completed_tutorial=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    api_keys = UserAPIKeys(user_id=user.id)
    db.add(api_keys)
    db.commit()
    
    return user

def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user

def get_user_api_keys(db: Session, user_id: int):
    keys = db.query(UserAPIKeys).filter(UserAPIKeys.user_id == user_id).first()
    if not keys:
        keys = UserAPIKeys(user_id=user_id)
        db.add(keys)
        db.commit()
        db.refresh(keys)
    return keys

def update_user_api_keys(db: Session, user_id: int, **kwargs):
    keys = get_user_api_keys(db, user_id)
    for key, value in kwargs.items():
        if hasattr(keys, key):
            setattr(keys, key, value)
    db.commit()
    db.refresh(keys)
    return keys
