import os
import asyncio
import time
import warnings
import logging
warnings.filterwarnings("ignore", category=DeprecationWarning)
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Depends, Body, UploadFile, File, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Any
import csv
import io
import requests
import uuid
from urllib.parse import urlencode
from datetime import datetime, timedelta
from dotenv import load_dotenv

from helpers.database import db, Lead, Campaign
from helpers.google_places import search_places
from helpers.enrichment import analyze_website, score_lead_with_ai
from helpers.email_service import render_template, prepare_email_variables, send_email, validate_email_config
from helpers.ai_email import generate_personalized_email
from helpers.sms_service import render_sms_template, prepare_sms_variables, send_sms, validate_sms_config
from helpers.email_enrichment import (
    extract_emails_from_website, extract_domain, choose_best_email,
    enrich_from_hunter, HUNTER_API_KEY, extract_phone_from_website
)
from helpers.auth import create_user, authenticate_user, create_session_token, get_user_api_keys, update_user_api_keys, hash_password, verify_password
from helpers.middleware import get_current_user, get_current_user_optional
from helpers.models import SessionLocal, User, EmailSettings
from helpers.email_senders import send_email_for_user, EmailProviderError
from helpers.encryption import encrypt, decrypt
from helpers.credits import credit_manager
from helpers.stripe_client import (
    CREDIT_PACKAGES, CREDIT_COSTS,
    create_checkout_session, get_stripe_credentials
)

load_dotenv()

_app_start = time.time()

logger = logging.getLogger("leadblitz")

ADMIN_EMAILS = ["shaca147@gmail.com"]

@asynccontextmanager
async def lifespan(app):
    try:
        db_session = SessionLocal()
        for email in ADMIN_EMAILS:
            user = db_session.query(User).filter(User.email == email).first()
            if user and not user.is_admin:
                user.is_admin = True
                db_session.commit()
                print(f"[STARTUP] Set admin flag for {email}", flush=True)
        db_session.close()
    except Exception as e:
        print(f"[STARTUP] Admin check skipped: {e}", flush=True)
    logger.warning("[STARTUP] LeadBlitz server ready and accepting requests on port 5000")
    print("[STARTUP] LeadBlitz server ready and accepting requests on port 5000", flush=True)
    yield
    print("[SHUTDOWN] LeadBlitz server shutting down", flush=True)

app = FastAPI(title="AI Lead Generation Tool", lifespan=lifespan)

@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/api/internal/ensure-admins")
async def ensure_admins():
    db_session = SessionLocal()
    try:
        updated = []
        for email in ADMIN_EMAILS:
            user = db_session.query(User).filter(User.email == email).first()
            if user and not user.is_admin:
                user.is_admin = True
                db_session.commit()
                updated.append(email)
            elif user and user.is_admin:
                updated.append(f"{email} (already admin)")
            else:
                updated.append(f"{email} (not found)")
        return {"updated": updated}
    finally:
        db_session.close()

app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PUBLIC_CACHE_PATHS = {'/', '/blog', '/privacy', '/terms'}
PUBLIC_CACHE_PREFIXES = ('/blog/',)

@app.middleware("http")
async def add_cache_control_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    content_type = response.headers.get("content-type", "")
    if path in PUBLIC_CACHE_PATHS or any(path.startswith(p) for p in PUBLIC_CACHE_PREFIXES):
        response.headers["Cache-Control"] = "public, max-age=3600"
    elif path.startswith("/static/"):
        response.headers["Cache-Control"] = "public, max-age=86400"
    elif "text/html" in content_type or path.startswith("/api/") or path.startswith("/admin/") or path in ('/login', '/register', '/dashboard'):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

app.mount("/static", StaticFiles(directory="static"), name="static")


def safe_int(value, default: int, min_val: int = None, max_val: int = None) -> int:
    try:
        result = int(value) if value is not None else default
    except (ValueError, TypeError):
        result = default
    if min_val is not None and result < min_val:
        result = min_val
    if max_val is not None and result > max_val:
        result = max_val
    return result


class SearchRequest(BaseModel):
    business_type: str
    location: str
    limit: Optional[Any] = 20
    auto_score: Optional[bool] = True

    @validator('limit', pre=True, always=True)
    def coerce_limit(cls, v):
        return safe_int(v, default=20, min_val=1, max_val=100)


class UpdateLeadRequest(BaseModel):
    email: Optional[str] = None
    email_source: Optional[str] = None
    stage: Optional[str] = None
    notes: Optional[str] = None
    contact_name: Optional[str] = None
    phone: Optional[str] = None


class PreviewEmailsRequest(BaseModel):
    subject_template: str
    body_template: str


class PersonalizedEmailRequest(BaseModel):
    lead_id: str
    base_pitch: str


class SendEmailsRequest(BaseModel):
    subject_template: str
    body_template: str
    only_scored_above: Optional[Any] = None
    stage_filter: Optional[str] = None
    include_score_report: Optional[bool] = False
    attach_pdf_report: Optional[bool] = False
    lead_ids: Optional[List[str]] = None

    @validator('only_scored_above', pre=True, always=True)
    def coerce_score(cls, v):
        if v is None:
            return None
        return safe_int(v, default=0, min_val=0, max_val=100)


class SendSingleEmailRequest(BaseModel):
    lead_id: str
    subject_template: str
    body_template: str
    include_score_report: Optional[bool] = False
    attach_pdf_report: Optional[bool] = False


class PreviewSMSRequest(BaseModel):
    message_template: str


class SendSMSRequest(BaseModel):
    message_template: str
    only_scored_above: Optional[Any] = None
    stage_filter: Optional[str] = None
    lead_ids: Optional[List[str]] = None

    @validator('only_scored_above', pre=True, always=True)
    def coerce_score(cls, v):
        if v is None:
            return None
        return safe_int(v, default=0, min_val=0, max_val=100)


class EnrichFromWebsiteRequest(BaseModel):
    lead_ids: Optional[List[str]] = None


class EnrichFromHunterRequest(BaseModel):
    lead_ids: Optional[List[str]] = None
    max_per_domain: Optional[Any] = 3

    @validator('max_per_domain', pre=True, always=True)
    def coerce_max(cls, v):
        return safe_int(v, default=3, min_val=1, max_val=20)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class UpdateAPIKeysRequest(BaseModel):
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    hunter_api_key: Optional[str] = None
    sendgrid_api_key: Optional[str] = None
    from_email: Optional[str] = None


class SMTPConfigRequest(BaseModel):
    smtp_host: str
    smtp_port: Any = 587
    smtp_username: str
    smtp_password: str
    smtp_from_email: str
    smtp_use_tls: Optional[bool] = True

    @validator('smtp_port', pre=True, always=True)
    def coerce_port(cls, v):
        return safe_int(v, default=587, min_val=1, max_val=65535)


class SendGridConfigRequest(BaseModel):
    api_key: str
    from_email: str


class TestEmailRequest(BaseModel):
    to_email: str
    subject: Optional[str] = "Test Email"
    body: Optional[str] = "This is a test email from your AI Lead Generation Tool."


FREE_TRIAL_CREDITS = 200


def format_score_report_for_email(lead) -> str:
    """Format the score breakdown as plain text for email inclusion."""
    reasoning = lead.score_reasoning
    if not reasoning:
        return ""
    
    lines = []
    lines.append("=" * 50)
    lines.append(f"WEBSITE ANALYSIS REPORT: {lead.name}")
    lines.append("=" * 50)
    lines.append(f"Overall Score: {lead.score}/100")
    lines.append("")
    
    # Website Quality
    if reasoning.get("website_quality"):
        wq = reasoning["website_quality"]
        lines.append(f"WEBSITE QUALITY: {wq.get('score', 0)}/30")
        if wq.get("notes"):
            for note in wq["notes"][:3]:
                lines.append(f"  - {note}")
        lines.append("")
    
    # Digital Presence
    if reasoning.get("digital_presence"):
        dp = reasoning["digital_presence"]
        lines.append(f"DIGITAL PRESENCE: {dp.get('score', 0)}/30")
        if dp.get("notes"):
            for note in dp["notes"][:3]:
                lines.append(f"  - {note}")
        lines.append("")
    
    # Automation Opportunity
    if reasoning.get("automation_opportunity"):
        ao = reasoning["automation_opportunity"]
        lines.append(f"AUTOMATION OPPORTUNITY: {ao.get('score', 0)}/40")
        if ao.get("notes"):
            for note in ao["notes"][:3]:
                lines.append(f"  - {note}")
        lines.append("")
    
    # Sales Report
    if reasoning.get("sales_report"):
        sr = reasoning["sales_report"]
        lines.append("-" * 50)
        lines.append("SALES INSIGHTS")
        lines.append("-" * 50)
        
        if sr.get("strengths"):
            lines.append("Strengths:")
            for s in sr["strengths"][:3]:
                lines.append(f"  + {s}")
            lines.append("")
        
        if sr.get("weaknesses"):
            lines.append("Areas for Improvement:")
            for w in sr["weaknesses"][:3]:
                lines.append(f"  - {w}")
            lines.append("")
        
        if sr.get("sales_opportunities"):
            lines.append("Opportunities:")
            for o in sr["sales_opportunities"][:3]:
                lines.append(f"  * {o}")
            lines.append("")
    
    lines.append("=" * 50)
    
    return "\n".join(lines)


@app.post("/api/auth/register")
async def register(request: RegisterRequest):
    db_session = SessionLocal()
    try:
        existing_user = db_session.query(User).filter(User.email == request.email.lower()).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        user = create_user(db_session, request.email, request.password, request.full_name)
        session_token = create_session_token(user.id)
        
        credit_manager.add_credits(
            user_id=user.id,
            amount=FREE_TRIAL_CREDITS,
            description="Free trial - Welcome bonus!"
        )
        
        response = JSONResponse(content={
            "success": True,
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "completed_tutorial": user.completed_tutorial
            }
        })
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            max_age=86400 * 30,
            samesite="lax",
            path="/"
        )
        return response
    finally:
        db_session.close()


@app.post("/api/auth/login")
async def login(request: LoginRequest):
    db_session = SessionLocal()
    try:
        user = authenticate_user(db_session, request.email, request.password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        session_token = create_session_token(user.id)
        
        response = JSONResponse(content={
            "success": True,
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "completed_tutorial": user.completed_tutorial
            }
        })
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            max_age=86400 * 30,
            samesite="lax",
            path="/"
        )
        return response
    finally:
        db_session.close()


@app.post("/api/auth/logout")
async def logout():
    response = JSONResponse(content={"success": True})
    response.delete_cookie(
        key="session_token",
        path="/",
        samesite="lax"
    )
    return response


@app.post("/api/auth/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    import secrets as secrets_mod
    from helpers.system_email import send_system_email, build_branded_email, get_app_base_url
    
    db_session = SessionLocal()
    try:
        user = db_session.query(User).filter(User.email == request.email.lower()).first()
        
        if user:
            reset_token = secrets_mod.token_urlsafe(32)
            user.reset_token = reset_token
            user.reset_token_expiry = datetime.now() + timedelta(hours=1)
            db_session.commit()
            
            base_url = get_app_base_url()
            reset_link = f"{base_url}/reset-password?token={reset_token}"
            
            greeting = f"Hi{(' ' + user.full_name) if user.full_name else ''},"
            html_body = build_branded_email(
                heading="Password Reset Request",
                body_content=f"""
                    <p>{greeting}</p>
                    <p>We received a request to reset the password for your LeadBlitz account.</p>
                    <p>Click the button below to set a new password. This link is valid for <strong>1 hour</strong>.</p>
                """,
                button_text="Reset Password",
                button_url=reset_link,
                footer_note="If you didn't request this password reset, you can safely ignore this email. Your password will remain unchanged."
            )
            
            email_sent = send_system_email(
                to_email=user.email,
                subject="Reset Your Password - LeadBlitz",
                html_body=html_body
            )
            
            if not email_sent:
                print(f"[PASSWORD RESET] Reset link for {user.email}: {reset_link}")
        
        return {"success": True, "message": "If an account exists with that email, a password reset link has been sent."}
    finally:
        db_session.close()


@app.post("/api/auth/reset-password")
async def reset_password(request: ResetPasswordRequest):
    db_session = SessionLocal()
    try:
        valid_user = db_session.query(User).filter(
            User.reset_token == request.token,
            User.reset_token.isnot(None),
            User.reset_token_expiry > datetime.now()
        ).first()
        
        if not valid_user:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token. Please request a new one.")
        
        if len(request.new_password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        
        new_hash = hash_password(request.new_password)
        valid_user.password_hash = new_hash
        valid_user.reset_token = None
        valid_user.reset_token_expiry = None
        db_session.flush()
        db_session.commit()
        
        print(f"[RESET-PASSWORD] User: {valid_user.email}, new hash (first 20): {new_hash[:20]}")
        
        db_session.expire(valid_user)
        verification_user = db_session.query(User).filter(User.id == valid_user.id).first()
        if verification_user and verify_password(request.new_password, verification_user.password_hash):
            print(f"[RESET-PASSWORD] Verification PASSED for {verification_user.email}")
        else:
            print(f"[RESET-PASSWORD] Verification FAILED for user id {valid_user.id}")
        
        return {"success": True, "message": "Password has been reset successfully. You can now log in."}
    except HTTPException:
        raise
    except Exception as e:
        db_session.rollback()
        print(f"[RESET-PASSWORD] ERROR: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset password. Please try again.")
    finally:
        db_session.close()


@app.get("/api/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    db_session = SessionLocal()
    try:
        api_keys = get_user_api_keys(db_session, current_user.id)
        
        return {
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "full_name": current_user.full_name,
                "completed_tutorial": current_user.completed_tutorial,
                "is_admin": current_user.is_admin or False
            },
            "api_keys_status": {
                "twilio": bool(api_keys.twilio_account_sid and api_keys.twilio_auth_token),
                "hunter": bool(api_keys.hunter_api_key or HUNTER_API_KEY)
            }
        }
    finally:
        db_session.close()


@app.get("/api/user/api-keys")
async def get_api_keys(current_user: User = Depends(get_current_user)):
    db_session = SessionLocal()
    try:
        api_keys = get_user_api_keys(db_session, current_user.id)
        
        return {
            "twilio_account_sid": api_keys.twilio_account_sid or "",
            "twilio_auth_token": api_keys.twilio_auth_token or "",
            "twilio_phone_number": api_keys.twilio_phone_number or "",
            "hunter_api_key": api_keys.hunter_api_key or ""
        }
    finally:
        db_session.close()


@app.put("/api/user/api-keys")
async def update_api_keys(request: UpdateAPIKeysRequest, current_user: User = Depends(get_current_user)):
    db_session = SessionLocal()
    try:
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        api_keys = update_user_api_keys(db_session, current_user.id, **update_data)
        
        return {
            "success": True,
            "message": "API keys updated successfully"
        }
    finally:
        db_session.close()


class EmailSignatureRequest(BaseModel):
    full_name: Optional[str] = None
    position: Optional[str] = None
    company_name: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    disclaimer: Optional[str] = None
    custom_signature: Optional[str] = None
    use_custom: Optional[bool] = False
    base_pitch: Optional[str] = None


@app.get("/api/email-signature")
async def get_email_signature(current_user: User = Depends(get_current_user)):
    """Get user's email signature settings."""
    from helpers.models import EmailSignature
    db_session = SessionLocal()
    try:
        sig = db_session.query(EmailSignature).filter(EmailSignature.user_id == current_user.id).first()
        if not sig:
            return {
                "full_name": current_user.full_name or "",
                "position": "",
                "company_name": "",
                "phone": "",
                "website": "",
                "logo_url": "",
                "disclaimer": "",
                "custom_signature": "",
                "use_custom": False,
                "base_pitch": ""
            }
        return {
            "full_name": sig.full_name or "",
            "position": sig.position or "",
            "company_name": sig.company_name or "",
            "phone": sig.phone or "",
            "website": sig.website or "",
            "logo_url": sig.logo_url or "",
            "disclaimer": sig.disclaimer or "",
            "custom_signature": sig.custom_signature or "",
            "use_custom": sig.use_custom or False,
            "base_pitch": sig.base_pitch or ""
        }
    finally:
        db_session.close()


@app.post("/api/email-signature")
async def save_email_signature(request: EmailSignatureRequest, current_user: User = Depends(get_current_user)):
    """Save user's email signature settings."""
    from helpers.models import EmailSignature
    db_session = SessionLocal()
    try:
        sig = db_session.query(EmailSignature).filter(EmailSignature.user_id == current_user.id).first()
        if not sig:
            sig = EmailSignature(user_id=current_user.id)
            db_session.add(sig)
        
        # Only update fields that are explicitly provided (not None)
        if request.full_name is not None:
            sig.full_name = request.full_name
        if request.position is not None:
            sig.position = request.position
        if request.company_name is not None:
            sig.company_name = request.company_name
        if request.phone is not None:
            sig.phone = request.phone
        if request.website is not None:
            sig.website = request.website
        if request.logo_url is not None:
            sig.logo_url = request.logo_url
        if request.disclaimer is not None:
            sig.disclaimer = request.disclaimer
        if request.custom_signature is not None:
            sig.custom_signature = request.custom_signature
        if request.use_custom is not None:
            sig.use_custom = request.use_custom
        if request.base_pitch is not None:
            sig.base_pitch = request.base_pitch
        
        db_session.commit()
        return {"success": True, "message": "Email signature saved successfully"}
    finally:
        db_session.close()


class EmailTemplateRequest(BaseModel):
    name: str
    subject: Optional[str] = None
    body: Optional[str] = None


@app.get("/api/email-templates")
async def get_email_templates(current_user: User = Depends(get_current_user)):
    """Get all email templates for the current user."""
    from helpers.models import EmailTemplate
    db_session = SessionLocal()
    try:
        templates = db_session.query(EmailTemplate).filter(
            EmailTemplate.user_id == current_user.id
        ).order_by(EmailTemplate.updated_at.desc()).all()
        return {"templates": [t.to_dict() for t in templates]}
    finally:
        db_session.close()


@app.post("/api/email-templates")
async def save_email_template(request: EmailTemplateRequest, current_user: User = Depends(get_current_user)):
    """Save a new email template."""
    from helpers.models import EmailTemplate
    db_session = SessionLocal()
    try:
        template = EmailTemplate(
            user_id=current_user.id,
            name=request.name,
            subject=request.subject,
            body=request.body
        )
        db_session.add(template)
        db_session.commit()
        db_session.refresh(template)
        return {"success": True, "template": template.to_dict()}
    finally:
        db_session.close()


@app.delete("/api/email-templates/{template_id}")
async def delete_email_template(template_id: int, current_user: User = Depends(get_current_user)):
    """Delete an email template."""
    from helpers.models import EmailTemplate
    db_session = SessionLocal()
    try:
        template = db_session.query(EmailTemplate).filter(
            EmailTemplate.id == template_id,
            EmailTemplate.user_id == current_user.id
        ).first()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        db_session.delete(template)
        db_session.commit()
        return {"success": True, "message": "Template deleted"}
    finally:
        db_session.close()


ALLOWED_IMAGE_TYPES = {'image/png', 'image/jpeg', 'image/gif', 'image/webp'}
MAX_LOGO_SIZE = 2 * 1024 * 1024  # 2MB

@app.post("/api/upload-logo")
async def upload_logo(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """Upload a company logo for email signature."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload PNG, JPG, GIF, or WebP.")
    
    contents = await file.read()
    if len(contents) > MAX_LOGO_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 2MB.")
    
    # Create uploads directory if not exists
    upload_dir = os.path.join("static", "uploads", "logos")
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename with user ID prefix
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'png'
    filename = f"user_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(upload_dir, filename)
    
    # Delete old logo files for this user
    for old_file in os.listdir(upload_dir):
        if old_file.startswith(f"user_{current_user.id}_"):
            try:
                os.remove(os.path.join(upload_dir, old_file))
            except:
                pass
    
    # Save the new file
    with open(filepath, 'wb') as f:
        f.write(contents)
    
    # Return the URL path
    logo_url = f"/static/uploads/logos/{filename}"
    return {"success": True, "url": logo_url}


@app.put("/api/user/tutorial-completed")
async def mark_tutorial_completed(current_user: User = Depends(get_current_user)):
    db_session = SessionLocal()
    try:
        user = db_session.query(User).filter(User.id == current_user.id).first()
        if user:
            user.completed_tutorial = True
            db_session.commit()
        
        return {"success": True}
    finally:
        db_session.close()


@app.get("/api/oauth/status")
async def get_oauth_status(current_user: User = Depends(get_current_user)):
    """Get OAuth configuration status for Gmail and Outlook."""
    gmail_client_id, gmail_client_secret, gmail_redirect_uri = db.get_gmail_oauth_credentials()
    outlook_client_id, outlook_client_secret, outlook_redirect_uri = db.get_outlook_oauth_credentials()
    
    return {
        "gmail_configured": all([gmail_client_id, gmail_client_secret, gmail_redirect_uri]),
        "outlook_configured": all([outlook_client_id, outlook_client_secret, outlook_redirect_uri]),
        "gmail_redirect_uri": gmail_redirect_uri or "",
        "outlook_redirect_uri": outlook_redirect_uri or ""
    }


@app.post("/api/oauth/gmail/configure")
async def configure_gmail_oauth(
    client_id: str = Body(...),
    client_secret: str = Body(...),
    redirect_uri: str = Body(...),
    current_user: User = Depends(get_current_user)
):
    """Save Gmail OAuth configuration (shared across all users)."""
    if not client_id or not client_secret or not redirect_uri:
        raise HTTPException(status_code=400, detail="All fields are required")
    
    client_secret_encrypted = encrypt(client_secret)
    db.save_gmail_oauth_config(client_id, client_secret_encrypted, redirect_uri)
    
    return {
        "success": True,
        "message": "Gmail OAuth configured successfully"
    }


@app.post("/api/oauth/outlook/configure")
async def configure_outlook_oauth(
    client_id: str = Body(...),
    client_secret: str = Body(...),
    redirect_uri: str = Body(...),
    current_user: User = Depends(get_current_user)
):
    """Save Outlook OAuth configuration (shared across all users)."""
    if not client_id or not client_secret or not redirect_uri:
        raise HTTPException(status_code=400, detail="All fields are required")
    
    client_secret_encrypted = encrypt(client_secret)
    db.save_outlook_oauth_config(client_id, client_secret_encrypted, redirect_uri)
    
    return {
        "success": True,
        "message": "Outlook OAuth configured successfully"
    }


GA_MEASUREMENT_ID = os.getenv("GA_MEASUREMENT_ID", "")

def get_ga_head_snippet():
    if not GA_MEASUREMENT_ID:
        return ""
    return f'''<!-- Google Analytics 4 -->
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{GA_MEASUREMENT_ID}');
</script>'''

def inject_ga_into_html(html_content):
    snippet = get_ga_head_snippet()
    if not snippet:
        return html_content
    return html_content.replace("<head>", f"<head>\n{snippet}", 1)

@app.get("/api/config/ga")
async def get_ga_config():
    return {"ga_measurement_id": GA_MEASUREMENT_ID or None}

@app.get("/robots.txt", response_class=Response)
async def robots_txt():
    content = """User-agent: *
Allow: /
Disallow: /api/
Disallow: /admin/
Disallow: /login
Disallow: /dashboard
Sitemap: https://leadblitz.co/sitemap.xml
"""
    return Response(content=content, media_type="text/plain")


@app.get("/sitemap.xml", response_class=Response)
async def sitemap_xml():
    urls = [
        {"loc": "https://leadblitz.co/", "priority": "1.0", "changefreq": "weekly"},
        {"loc": "https://leadblitz.co/blog", "priority": "0.8", "changefreq": "weekly"},
        {"loc": "https://leadblitz.co/blog/cold-email-that-gets-replies", "priority": "0.7", "changefreq": "monthly"},
        {"loc": "https://leadblitz.co/blog/sms-fastest-route", "priority": "0.7", "changefreq": "monthly"},
        {"loc": "https://leadblitz.co/blog/free-audit-strategy", "priority": "0.7", "changefreq": "monthly"},
        {"loc": "https://leadblitz.co/blog/follow-up-sequence", "priority": "0.7", "changefreq": "monthly"},
        {"loc": "https://leadblitz.co/privacy", "priority": "0.3", "changefreq": "yearly"},
        {"loc": "https://leadblitz.co/terms", "priority": "0.3", "changefreq": "yearly"},
    ]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url in urls:
        xml += f'  <url>\n    <loc>{url["loc"]}</loc>\n    <changefreq>{url["changefreq"]}</changefreq>\n    <priority>{url["priority"]}</priority>\n  </url>\n'
    xml += '</urlset>'
    return Response(content=xml, media_type="application/xml")


@app.get("/llms.txt", response_class=Response)
async def llms_txt():
    content = """# LeadBlitz

## Name
LeadBlitz

## Description
LeadBlitz is an AI-powered lead generation and website audit platform built for freelance web designers and small agencies. It helps users find local businesses with outdated websites, score them using AI, and close deals with professional audit reports.

## Features
- Google Places API business search to discover local leads
- AI-powered website scoring (0-100) analyzing performance, mobile-friendliness, SEO, SSL, and design quality
- One-click professional PDF audit reports branded for client delivery
- Email campaign composer with templates, AI personalization, and bulk sending
- SMS outreach via Twilio integration
- CRM pipeline with 6 stages and inline editing
- CSV import for bulk lead uploads with background AI scoring
- Multi-user system with session-based authentication
- Credit-based usage model

## Target Users
- Freelance web designers
- Small web design agencies
- Digital marketing consultants doing outbound prospecting

## Pricing
- 200 free credits on signup (no credit card required)
- Starter: $15 for 100 credits
- Professional: $59 for 500 credits
- Pro Team: $199 for 2,000 credits

## Links
- Website: https://leadblitz.co
- Blog: https://leadblitz.co/blog
- Privacy Policy: https://leadblitz.co/privacy
- Terms of Service: https://leadblitz.co/terms
"""
    return Response(content=content, media_type="text/plain")


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_page():
    with open("templates/privacy.html", "r") as f:
        return inject_ga_into_html(f.read())


@app.get("/terms", response_class=HTMLResponse)
async def terms_page():
    with open("templates/terms.html", "r") as f:
        return inject_ga_into_html(f.read())


@app.get("/blog", response_class=HTMLResponse)
async def blog_page():
    with open("templates/blog.html", "r") as f:
        return inject_ga_into_html(f.read())


@app.get("/blog/cold-email-that-gets-replies", response_class=HTMLResponse)
async def blog_cold_email():
    with open("templates/blog_cold_email.html", "r") as f:
        return inject_ga_into_html(f.read())

@app.get("/blog/sms-fastest-route", response_class=HTMLResponse)
async def blog_sms():
    with open("templates/blog_sms.html", "r") as f:
        return inject_ga_into_html(f.read())

@app.get("/blog/follow-up-sequence", response_class=HTMLResponse)
async def blog_follow_up():
    with open("templates/blog_follow_up.html", "r") as f:
        return inject_ga_into_html(f.read())

@app.get("/blog/free-audit-strategy", response_class=HTMLResponse)
async def blog_free_audit():
    with open("templates/blog_free_audit.html", "r") as f:
        return inject_ga_into_html(f.read())


@app.get("/", response_class=HTMLResponse)
async def read_root(current_user: User = Depends(get_current_user_optional)):
    if not current_user:
        with open("templates/landing.html", "r") as f:
            return inject_ga_into_html(f.read())
    
    with open("static/index.html", "r") as f:
        return inject_ga_into_html(f.read())


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    with open("static/index.html", "r") as f:
        return inject_ga_into_html(f.read())


@app.get("/register", response_class=HTMLResponse)
async def register_page():
    with open("static/index.html", "r") as f:
        return inject_ga_into_html(f.read())


@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page():
    with open("static/index.html", "r") as f:
        return inject_ga_into_html(f.read())


@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page():
    with open("static/index.html", "r") as f:
        return inject_ga_into_html(f.read())


@app.get("/home")
async def home_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/", status_code=301)


@app.get("/favicon.ico")
async def favicon():
    from fastapi.responses import FileResponse
    favicon_path = os.path.join("static", "favicon.png")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/png")
    raise HTTPException(status_code=404, detail="Favicon not found")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(current_user: User = Depends(get_current_user_optional)):
    if not current_user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login", status_code=302)
    with open("static/index.html", "r") as f:
        return inject_ga_into_html(f.read())


def auto_score_leads_background(lead_dicts: list, user_id: int):
    """Background task to automatically score leads after search"""
    from helpers.hybrid_scorer import score_website_hybrid, create_backward_compatible_reasoning
    from datetime import datetime
    import concurrent.futures
    import time as time_module

    PER_LEAD_TIMEOUT = 30
    BATCH_TOTAL_TIMEOUT = 300
    batch_start = time_module.time()

    for lead_dict in lead_dicts:
        if time_module.time() - batch_start >= BATCH_TOTAL_TIMEOUT:
            print(f"Auto-scoring batch timeout reached after {BATCH_TOTAL_TIMEOUT}s")
            break

        website = lead_dict.get("website")
        lead_id = lead_dict.get("id")
        if not website or not lead_id:
            continue

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(score_website_hybrid, website, True)
                hybrid_result = future.result(timeout=PER_LEAD_TIMEOUT)

            score_reasoning = create_backward_compatible_reasoning(hybrid_result)

            render_pathway = hybrid_result.get("render_pathway", "")
            has_errors = hybrid_result.get("has_errors", False)
            breakdown = hybrid_result.get("breakdown", {})
            final_score = hybrid_result.get("final_score", 0)

            scoring_failed = (
                render_pathway in ["fetch_failed", "bot_blocked"] or
                (has_errors and final_score == 0) or
                (not breakdown and final_score == 0)
            )

            if scoring_failed:
                db.update_lead(
                    lead_id, user_id=user_id,
                    score=0, score_reasoning=score_reasoning,
                    heuristic_score=0, ai_score=0,
                    score_breakdown=None, score_confidence=0.3
                )
            else:
                has_credits, _, _ = credit_manager.has_sufficient_credits(user_id, "ai_scoring", 1)
                if has_credits:
                    credit_manager.deduct_credits(user_id, "ai_scoring", 1, f"Auto-scoring for {lead_dict.get('name', 'Unknown')}")
                db.update_lead(
                    lead_id, user_id=user_id,
                    score=score_reasoning.get("total_score", 0),
                    score_reasoning=score_reasoning,
                    heuristic_score=hybrid_result.get("heuristic_score"),
                    ai_score=hybrid_result.get("ai_score"),
                    score_breakdown=hybrid_result.get("breakdown"),
                    score_confidence=hybrid_result.get("confidence"),
                    last_scored_at=datetime.now(),
                    technographics=hybrid_result.get("technographics")
                )
            print(f"Auto-scored lead {lead_dict.get('name', 'Unknown')}: score={score_reasoning.get('total_score', 0)}")
        except concurrent.futures.TimeoutError:
            print(f"Auto-scoring timed out for {website} (>{PER_LEAD_TIMEOUT}s)")
            db.update_lead(lead_id, user_id=user_id, score=0)
        except Exception as e:
            print(f"Auto-scoring failed for {website}: {e}")
            db.update_lead(lead_id, user_id=user_id, score=0)


@app.post("/api/search")
async def api_search(request: SearchRequest, background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user)):
    try:
        limit = safe_int(request.limit, default=20, min_val=1, max_val=50)
        
        existing_campaign = db.find_campaign_by_search(
            business_type=request.business_type,
            location=request.location,
            user_id=current_user.id
        )
        
        if existing_campaign:
            db.set_active_campaign(existing_campaign.id, user_id=current_user.id)
            leads = db.get_campaign_leads(existing_campaign.id, user_id=current_user.id)
            return {
                "count": len(leads),
                "leads": [lead.to_dict() for lead in leads],
                "campaign": existing_campaign.to_dict(),
                "cached": True
            }
        
        # Check if user has enough credits for the requested limit (1 credit per lead)
        has_credits, balance, cost = credit_manager.has_sufficient_credits(
            current_user.id, "search", count=limit
        )
        if not has_credits:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. Searching for up to {limit} leads costs {limit} credits, but you only have {balance}. Please reduce the limit or purchase more credits."
            )
        
        campaign = db.create_campaign(
            business_type=request.business_type,
            location=request.location,
            user_id=current_user.id
        )
        
        print(f"[SEARCH] Calling Google Places API for '{request.business_type}' in '{request.location}' (limit={limit})")
        t0 = time.time()
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(search_places, request.business_type, request.location, limit),
                timeout=45.0
            )
        except asyncio.TimeoutError:
            elapsed = time.time() - t0
            print(f"[SEARCH] Google Places API timed out after {elapsed:.1f}s")
            db.delete_campaign(campaign.id, user_id=current_user.id)
            raise HTTPException(status_code=504, detail="Search timed out. Google Places API did not respond in time. Please try again.")
        elapsed = time.time() - t0
        print(f"[SEARCH] Google Places API returned in {elapsed:.1f}s")
        
        places = result.get("places", [])
        next_page_token = result.get("next_page_token")
        print(f"[SEARCH] Got {len(places)} places")
        
        if not places:
            db.delete_campaign(campaign.id, user_id=current_user.id)
            raise HTTPException(
                status_code=404, 
                detail="No businesses found for this search. Please check the location spelling or try a different search."
            )
        
        if next_page_token:
            db.update_campaign(campaign.id, user_id=current_user.id, next_page_token=next_page_token)
        
        leads = []
        for place in places:
            lead = Lead(
                name=place.get("name", "Unknown"),
                address=place.get("address", ""),
                phone=place.get("phone", ""),
                email=place.get("email", ""),
                website=place.get("website", ""),
                rating=place.get("rating", 0),
                review_count=place.get("review_count", 0)
            )
            db.add_lead(lead, user_id=current_user.id, campaign_id=campaign.id)
            leads.append(lead.to_dict())
        
        # Deduct credits for leads found (1 credit per lead)
        leads_found = len(leads)
        if leads_found > 0:
            credit_manager.deduct_credits(
                current_user.id,
                "lead_search",
                leads_found,
                f"Lead search: {leads_found} leads for '{request.business_type}' in '{request.location}'"
            )
        
        updated_campaign = db.get_campaign(campaign.id, user_id=current_user.id)
        
        if request.auto_score:
            leads_with_websites = [l for l in leads if l.get("website")]
            if leads_with_websites:
                background_tasks.add_task(auto_score_leads_background, leads_with_websites, current_user.id)
        
        return {
            "count": len(leads),
            "leads": leads,
            "campaign": updated_campaign.to_dict() if updated_campaign else campaign.to_dict(),
            "cached": False
        }
    
    except ValueError as e:
        error_msg = str(e)
        print(f"[SEARCH] ValueError: {error_msg}")
        if "timed out" in error_msg.lower():
            raise HTTPException(status_code=504, detail=error_msg)
        elif "quota" in error_msg.lower() or "OVER_QUERY_LIMIT" in error_msg:
            raise HTTPException(status_code=429, detail=error_msg)
        elif "REQUEST_DENIED" in error_msg or "API key" in error_msg.lower():
            raise HTTPException(status_code=502, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Search temporarily unavailable. Please try again in a moment.")


@app.post("/api/load-more-leads")
async def api_load_more_leads(current_user: User = Depends(get_current_user)):
    try:
        active_campaign_id = db.get_active_campaign_id(user_id=current_user.id)
        if not active_campaign_id:
            raise HTTPException(status_code=400, detail="No active campaign")
        
        campaign = db.get_campaign(active_campaign_id, user_id=current_user.id)
        if not campaign or not campaign.next_page_token:
            raise HTTPException(status_code=400, detail="No more leads available")
        
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(search_places, campaign.business_type, campaign.location, 20, campaign.next_page_token),
                timeout=45.0
            )
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="Search timed out. Please try again.")
        
        places = result.get("places", [])
        next_page_token = result.get("next_page_token")
        
        db.update_campaign(campaign.id, user_id=current_user.id, next_page_token=next_page_token)
        
        leads = []
        for place in places:
            lead = Lead(
                name=place.get("name", "Unknown"),
                address=place.get("address", ""),
                phone=place.get("phone", ""),
                email=place.get("email", ""),
                website=place.get("website", ""),
                rating=place.get("rating", 0),
                review_count=place.get("review_count", 0)
            )
            db.add_lead(lead, user_id=current_user.id, campaign_id=campaign.id)
            leads.append(lead.to_dict())
        
        updated_campaign = db.get_campaign(campaign.id, user_id=current_user.id)
        
        return {
            "count": len(leads),
            "leads": leads,
            "campaign": updated_campaign.to_dict() if updated_campaign else campaign.to_dict()
        }
    
    except ValueError as e:
        error_msg = str(e)
        print(f"[LOAD-MORE] ValueError: {error_msg}")
        if "timed out" in error_msg.lower():
            raise HTTPException(status_code=504, detail=error_msg)
        elif "quota" in error_msg.lower() or "OVER_QUERY_LIMIT" in error_msg:
            raise HTTPException(status_code=429, detail=error_msg)
        elif "REQUEST_DENIED" in error_msg or "API key" in error_msg.lower():
            raise HTTPException(status_code=502, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Unable to load more leads. Please try again.")


@app.post("/api/score-leads")
async def api_score_leads(current_user: User = Depends(get_current_user)):
    from helpers.hybrid_scorer import score_website_hybrid, create_backward_compatible_reasoning
    from helpers.enrichment import analyze_website, score_lead_with_ai
    from datetime import datetime
    import time as time_module
    
    PER_LEAD_TIMEOUT = 30
    BATCH_TOTAL_TIMEOUT = 300
    
    try:
        leads = db.get_active_leads(user_id=current_user.id)
        
        leads_with_website = [l for l in leads if l.website]
        leads_needing_first_score = [l for l in leads_with_website if l.last_scored_at is None]
        
        if leads_needing_first_score:
            has_credits, balance, cost = credit_manager.has_sufficient_credits(
                current_user.id, "ai_scoring", len(leads_needing_first_score)
            )
            if not has_credits:
                raise HTTPException(
                    status_code=402,
                    detail=f"Insufficient credits. Need {cost} credits to score {len(leads_needing_first_score)} new leads, but only have {balance}. Please purchase more credits."
                )
        
        def _run_batch_scoring():
            import concurrent.futures
            scored_leads = []
            scored_lead_ids = set()
            credits_used = 0
            failed_leads = []
            timed_out_leads = []
            batch_start_time = time_module.time()
            
            for lead in leads:
                elapsed_total = time_module.time() - batch_start_time
                if elapsed_total >= BATCH_TOTAL_TIMEOUT:
                    remaining = [l for l in leads if l.id not in scored_lead_ids and l.website]
                    for r in remaining:
                        timed_out_leads.append({"name": r.name, "website": r.website, "reason": "Batch timeout exceeded (5 minutes)"})
                        db.update_lead(r.id, user_id=current_user.id, score=0)
                    break
                
                if lead.website:
                    is_first_score = lead.last_scored_at is None
                    
                    try:
                        use_cache = lead.last_scored_at is None
                        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                            future = executor.submit(score_website_hybrid, lead.website, use_cache)
                            hybrid_result = future.result(timeout=PER_LEAD_TIMEOUT)
                    
                        render_pathway = hybrid_result.get("render_pathway", "")
                        has_errors = hybrid_result.get("has_errors", False)
                        breakdown = hybrid_result.get("breakdown", {})
                        final_score = hybrid_result.get("final_score", 0)
                        
                        scoring_failed = (
                            render_pathway in ["fetch_failed", "bot_blocked"] or
                            (has_errors and final_score == 0) or
                            (not breakdown and final_score == 0)
                        )
                        
                        if is_first_score and not scoring_failed:
                            success, _ = credit_manager.deduct_credits(
                                current_user.id, "ai_scoring", 1,
                                f"AI scoring for {lead.name}"
                            )
                            if not success:
                                break
                            credits_used += 1
                        
                        if scoring_failed:
                            if render_pathway == "bot_blocked":
                                reason = "Website has advanced security that blocks automated access"
                            elif render_pathway == "fetch_failed":
                                reason = "Could not connect to website (may be down or inaccessible)"
                            elif has_errors:
                                reason = "Website returned errors during analysis"
                            else:
                                reason = "Unable to analyze website content"
                            
                            failed_leads.append({
                                "name": lead.name,
                                "website": lead.website,
                                "reason": reason
                            })
                            
                            score_reasoning = create_backward_compatible_reasoning(hybrid_result)
                            lead_updated = db.update_lead(
                                lead.id,
                                user_id=current_user.id,
                                score=0,
                                score_reasoning=score_reasoning,
                                heuristic_score=0,
                                ai_score=0,
                                score_breakdown=None,
                                score_confidence=0.3
                            )
                            scored_leads.append(lead_updated.to_dict() if hasattr(lead_updated, 'to_dict') else lead_updated)
                            continue
                        
                        score_reasoning = create_backward_compatible_reasoning(hybrid_result)
                        lead_updated = db.update_lead(
                            lead.id,
                            user_id=current_user.id,
                            score=score_reasoning.get("total_score", 0),
                            score_reasoning=score_reasoning,
                            heuristic_score=hybrid_result.get("heuristic_score"),
                            ai_score=hybrid_result.get("ai_score"),
                            score_breakdown=hybrid_result.get("breakdown"),
                            score_confidence=hybrid_result.get("confidence"),
                            last_scored_at=datetime.now(),
                            technographics=hybrid_result.get("technographics")
                        )
                    except concurrent.futures.TimeoutError:
                        print(f"Scoring timed out for {lead.website} (>{PER_LEAD_TIMEOUT}s)")
                        timed_out_leads.append({"name": lead.name, "website": lead.website, "reason": f"Scoring timed out after {PER_LEAD_TIMEOUT} seconds"})
                        lead_updated = db.update_lead(lead.id, user_id=current_user.id, score=0)
                        if lead_updated:
                            scored_leads.append(lead_updated.to_dict() if hasattr(lead_updated, 'to_dict') else lead_updated)
                        scored_lead_ids.add(lead.id)
                        continue
                    except Exception as hybrid_error:
                        print(f"Hybrid scoring failed for {lead.website}: {hybrid_error}, falling back to legacy")
                        try:
                            website_analysis = analyze_website(lead.website)
                            score_result = score_lead_with_ai(lead.to_dict(), website_analysis)
                            lead_updated = db.update_lead(
                                lead.id,
                                user_id=current_user.id,
                                score=score_result["score"],
                                score_reasoning=score_result["reasoning"],
                                last_scored_at=datetime.now()
                            )
                            if is_first_score:
                                credits_used += 1
                        except Exception as legacy_error:
                            print(f"Legacy scoring also failed for {lead.website}: {legacy_error}")
                            lead_updated = db.update_lead(lead.id, user_id=current_user.id, score=0)
                else:
                    lead_updated = db.update_lead(lead.id, user_id=current_user.id, score=0)
                
                if lead_updated:
                    scored_leads.append(lead_updated.to_dict() if hasattr(lead_updated, 'to_dict') else lead_updated)
                    scored_lead_ids.add(lead.id)
            
            failure_summary = {}
            for fl in failed_leads:
                reason = fl["reason"]
                if reason not in failure_summary:
                    failure_summary[reason] = []
                failure_summary[reason].append(fl["name"])
            
            return {
                "count": len(scored_leads),
                "leads": scored_leads,
                "credits_used": credits_used,
                "failed_count": len(failed_leads),
                "failed_leads": failed_leads,
                "failure_summary": failure_summary,
                "timed_out_count": len(timed_out_leads),
                "timed_out_leads": timed_out_leads
            }
        
        result = await asyncio.to_thread(_run_batch_scoring)
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Unable to score leads right now. Please try again.")


@app.post("/api/score-lead/{lead_id}")
async def api_score_single_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    """Score a single lead - used for progressive scoring with real-time updates"""
    from helpers.hybrid_scorer import score_website_hybrid, create_backward_compatible_reasoning
    from helpers.enrichment import analyze_website, score_lead_with_ai
    from datetime import datetime
    
    try:
        lead = db.get_lead(lead_id, user_id=current_user.id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        if not lead.website:
            return {"lead": lead.to_dict(), "scored": False, "reason": "No website"}
        
        is_first_score = lead.last_scored_at is None
        
        if is_first_score:
            has_credits, balance, cost = credit_manager.has_sufficient_credits(
                current_user.id, "ai_scoring", 1
            )
            if not has_credits:
                raise HTTPException(
                    status_code=402,
                    detail=f"Insufficient credits. Need 1 credit but only have {balance}."
                )
        
        def _do_single_score(website, use_cache):
            return score_website_hybrid(website, use_cache=use_cache)
        
        def _do_legacy_score(website, lead_dict):
            wa = analyze_website(website)
            return score_lead_with_ai(lead_dict, wa)
        
        try:
            use_cache = lead.last_scored_at is None
            hybrid_result = await asyncio.wait_for(
                asyncio.to_thread(_do_single_score, lead.website, use_cache),
                timeout=45.0
            )
            
            render_pathway = hybrid_result.get("render_pathway", "")
            has_errors = hybrid_result.get("has_errors", False)
            breakdown = hybrid_result.get("breakdown", {})
            final_score = hybrid_result.get("final_score", 0)
            
            scoring_failed = (
                render_pathway in ["fetch_failed", "bot_blocked"] or
                (has_errors and final_score == 0) or
                (not breakdown and final_score == 0)
            )
            
            credits_used = 0
            if is_first_score and not scoring_failed:
                success, _ = credit_manager.deduct_credits(
                    current_user.id, "ai_scoring", 1,
                    f"AI scoring for {lead.name}"
                )
                if success:
                    credits_used = 1
            
            score_reasoning = create_backward_compatible_reasoning(hybrid_result)
            
            if scoring_failed:
                lead_updated = db.update_lead(
                    lead.id,
                    user_id=current_user.id,
                    score=0,
                    score_reasoning=score_reasoning,
                    heuristic_score=0,
                    ai_score=0,
                    score_breakdown=None,
                    score_confidence=0.3
                )
            else:
                lead_updated = db.update_lead(
                    lead.id,
                    user_id=current_user.id,
                    score=score_reasoning.get("total_score", 0),
                    score_reasoning=score_reasoning,
                    heuristic_score=hybrid_result.get("heuristic_score"),
                    ai_score=hybrid_result.get("ai_score"),
                    score_breakdown=hybrid_result.get("breakdown"),
                    score_confidence=hybrid_result.get("confidence"),
                    last_scored_at=datetime.now(),
                    technographics=hybrid_result.get("technographics")
                )
            
            return {
                "lead": lead_updated.to_dict() if hasattr(lead_updated, 'to_dict') else lead_updated,
                "scored": True,
                "credits_used": credits_used,
                "failed": scoring_failed
            }
            
        except asyncio.TimeoutError:
            print(f"Scoring timed out for {lead.website} (>45s)")
            return {"lead": lead.to_dict(), "scored": False, "reason": "Scoring timed out", "failed": True}
        except Exception as hybrid_error:
            print(f"Hybrid scoring failed for {lead.website}: {hybrid_error}, falling back to legacy")
            try:
                score_result = await asyncio.wait_for(
                    asyncio.to_thread(_do_legacy_score, lead.website, lead.to_dict()),
                    timeout=30.0
                )
            except (asyncio.TimeoutError, Exception) as e:
                print(f"Legacy scoring also failed for {lead.website}: {e}")
                return {"lead": lead.to_dict(), "scored": False, "reason": "Scoring failed", "failed": True}
            lead_updated = db.update_lead(
                lead.id,
                user_id=current_user.id,
                score=score_result["score"],
                score_reasoning=score_result["reasoning"],
                last_scored_at=datetime.now()
            )
            
            credits_used = 1 if is_first_score else 0
            if is_first_score:
                credit_manager.deduct_credits(
                    current_user.id, "ai_scoring", 1,
                    f"AI scoring for {lead.name}"
                )
            
            return {
                "lead": lead_updated.to_dict() if hasattr(lead_updated, 'to_dict') else lead_updated,
                "scored": True,
                "credits_used": credits_used,
                "failed": False
            }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Unable to score this lead. Please try again.")


@app.get("/api/leads")
async def api_get_leads(
    current_user: User = Depends(get_current_user),
    view: Optional[str] = None,
    campaign_id: Optional[str] = None
):
    print(f"GET /api/leads called with campaign_id={campaign_id}, view={view}, user_id={current_user.id}")
    if campaign_id:
        leads = db.get_campaign_leads(campaign_id, user_id=current_user.id)
        active_campaign_id = campaign_id
    elif view == "all":
        leads = db.get_all_leads(user_id=current_user.id)
        active_campaign_id = None
    elif view == "strong":
        all_leads = db.get_all_leads(user_id=current_user.id)
        leads = [l for l in all_leads if l.score is not None and l.score > 0 and l.score < 30]
        active_campaign_id = None
    else:
        leads = db.get_active_leads(user_id=current_user.id)
        active_campaign_id = db.get_active_campaign_id(user_id=current_user.id)
    
    print(f"GET /api/leads returning {len(leads)} leads, active_campaign_id={active_campaign_id}")
    return {
        "count": len(leads),
        "leads": [lead.to_dict() for lead in leads],
        "active_campaign_id": active_campaign_id,
        "view": view
    }


@app.patch("/api/leads/{lead_id}")
async def api_update_lead(lead_id: str, request: UpdateLeadRequest, current_user: User = Depends(get_current_user)):
    update_data = {}
    if request.email is not None:
        update_data["email"] = request.email
        if request.email_source is None:
            update_data["email_source"] = "manual"
    if request.email_source is not None:
        update_data["email_source"] = request.email_source
    if request.stage is not None:
        update_data["stage"] = request.stage
    if request.notes is not None:
        update_data["notes"] = request.notes
    if request.contact_name is not None:
        update_data["contact_name"] = request.contact_name
    if request.phone is not None:
        update_data["phone"] = request.phone
    
    lead = db.update_lead(lead_id, user_id=current_user.id, **update_data)
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return lead.to_dict()


@app.delete("/api/leads/{lead_id}")
async def api_delete_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    success = db.delete_lead(lead_id, user_id=current_user.id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return {"success": True, "message": "Lead deleted successfully"}


@app.get("/api/leads/csv-template")
async def api_csv_template(current_user: User = Depends(get_current_user)):
    from helpers.csv_import import get_csv_template
    csv_content = get_csv_template()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="leadblitz-import-template.csv"'}
    )


@app.post("/api/leads/import-csv")
async def api_import_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    from helpers.csv_import import (
        parse_csv_file, process_csv_rows, generate_import_id,
        score_import_leads_background
    )

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail={
            "error": "invalid_format",
            "message": "This file doesn't appear to be a valid CSV. Please upload a .csv file."
        })

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail={
            "error": "empty_file",
            "message": "No data found in CSV"
        })

    rows, error = parse_csv_file(content, file.filename)
    if error:
        raise HTTPException(status_code=400, detail=error)

    import_id = generate_import_id()
    result = process_csv_rows(rows, current_user.id, import_id, file.filename)

    lead_ids_to_score = result.pop("_lead_ids_to_score", [])
    if lead_ids_to_score:
        score_import_leads_background(lead_ids_to_score, import_id, current_user.id)

    return result


@app.get("/api/leads/import-status/{import_id}")
async def api_import_status(import_id: str, current_user: User = Depends(get_current_user)):
    from helpers.csv_import import get_import_status
    status = get_import_status(import_id, current_user.id)
    if not status:
        raise HTTPException(status_code=404, detail="Import not found")
    return status


@app.get("/api/leads/{lead_id}/score-breakdown")
async def api_get_score_breakdown(lead_id: str, current_user: User = Depends(get_current_user)):
    lead = db.get_lead(lead_id, user_id=current_user.id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if not lead.score_reasoning:
        raise HTTPException(status_code=404, detail="No score breakdown available for this lead")
    
    return {
        "lead_id": lead.id,
        "lead_name": lead.name,
        "score": lead.score,
        "reasoning": lead.score_reasoning
    }


@app.post("/api/leads/{lead_id}/client-report")
async def api_generate_client_report(lead_id: str, request: Request, current_user: User = Depends(get_current_user)):
    from helpers.client_report import generate_client_report, render_client_report_html
    
    lead = db.get_lead(lead_id, user_id=current_user.id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if not lead.score_reasoning:
        raise HTTPException(status_code=400, detail="Lead must be scored before generating a report")
    
    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    agency_name = body.get("agency_name", "")
    agency_website = body.get("agency_website", "")
    agency_tagline = body.get("agency_tagline", "")
    
    lead_dict = lead.to_dict()
    report = generate_client_report(
        lead_dict,
        agency_name=agency_name,
        agency_website=agency_website,
        agency_tagline=agency_tagline
    )
    
    return report


@app.post("/api/leads/{lead_id}/client-report-html")
async def api_generate_client_report_html(lead_id: str, request: Request, current_user: User = Depends(get_current_user)):
    from helpers.client_report import generate_client_report, render_client_report_html
    from fastapi.responses import HTMLResponse
    
    lead = db.get_lead(lead_id, user_id=current_user.id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if not lead.score_reasoning:
        raise HTTPException(status_code=400, detail="Lead must be scored before generating a report")
    
    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    agency_name = body.get("agency_name", "")
    agency_website = body.get("agency_website", "")
    agency_tagline = body.get("agency_tagline", "")
    
    lead_dict = lead.to_dict()
    
    try:
        report = generate_client_report(
            lead_dict,
            agency_name=agency_name,
            agency_website=agency_website,
            agency_tagline=agency_tagline
        )
    except Exception as e:
        print(f"[client-report-html] Exception generating report for lead {lead_id}: {type(e).__name__}: {e}")
        error_msg = str(e).lower()
        if "timeout" in error_msg or "timed out" in error_msg or "APITimeoutError" in type(e).__name__:
            return JSONResponse(status_code=504, content={"error": "Report generation timed out"})
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")
    
    if report.get("timeout"):
        return JSONResponse(status_code=504, content={"error": "Report generation timed out"})
    
    if report.get("error") and not report.get("executive_summary"):
        return JSONResponse(status_code=500, content={"error": report["error"]})
    
    html = render_client_report_html(report)
    return HTMLResponse(content=html)


@app.post("/api/leads/{lead_id}/internal-report")
async def api_generate_internal_report(lead_id: str, current_user: User = Depends(get_current_user)):
    from helpers.client_report import generate_internal_report
    
    lead = db.get_lead(lead_id, user_id=current_user.id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if not lead.score_reasoning:
        raise HTTPException(status_code=400, detail="Lead must be scored before generating a report")
    
    lead_dict = lead.to_dict()
    report = generate_internal_report(lead_dict)
    
    return report


@app.post("/api/leads/{lead_id}/report")
async def api_generate_pdf_report(lead_id: str, request: Request, type: Optional[str] = None, current_user: User = Depends(get_current_user)):
    from helpers.client_report import generate_client_report, generate_internal_report
    from helpers.pdf_report import generate_client_pdf, generate_internal_pdf

    lead = db.get_lead(lead_id, user_id=current_user.id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if not lead.score_reasoning:
        raise HTTPException(status_code=400, detail="Lead must be scored before generating a report")

    try:
        body = await request.json()
    except Exception:
        body = {}
    report_type = type or body.get("type", "client")
    lead_dict = lead.to_dict()

    if report_type == "internal":
        report_data = generate_internal_report(lead_dict)
        pdf_bytes = generate_internal_pdf(report_data)
        filename = f"Internal_Report_{lead.name.replace(' ', '_')}.pdf"
    else:
        agency_name = body.get("agency_name", "")
        agency_website = body.get("agency_website", "")
        agency_tagline = body.get("agency_tagline", "")
        report_data = generate_client_report(
            lead_dict,
            agency_name=agency_name,
            agency_website=agency_website,
            agency_tagline=agency_tagline
        )
        if report_data.get("error") and not report_data.get("executive_summary"):
            raise HTTPException(status_code=500, detail=report_data["error"])
        pdf_bytes = generate_client_pdf(report_data)
        filename = f"Website_Audit_{lead.name.replace(' ', '_')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.post("/api/leads/{lead_id}/report/email")
async def api_email_pdf_report(lead_id: str, request: Request, type: Optional[str] = None, current_user: User = Depends(get_current_user)):
    from helpers.client_report import generate_client_report, generate_internal_report
    from helpers.pdf_report import generate_client_pdf, generate_internal_pdf
    from helpers.email_senders import send_email_with_attachment_for_user

    lead = db.get_lead(lead_id, user_id=current_user.id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if not lead.score_reasoning:
        raise HTTPException(status_code=400, detail="Lead must be scored before generating a report")

    if not lead.email or '@' not in lead.email:
        raise HTTPException(status_code=400, detail="Lead has no valid email address")

    try:
        body = await request.json()
    except Exception:
        body = {}
    report_type = type or body.get("type", "client")
    subject = body.get("subject", "")
    email_body = body.get("body", "")
    lead_dict = lead.to_dict()

    if report_type == "internal":
        report_data = generate_internal_report(lead_dict)
        pdf_bytes = generate_internal_pdf(report_data)
        filename = f"Internal_Report_{lead.name.replace(' ', '_')}.pdf"
        if not subject:
            subject = f"Internal Report - {lead.name}"
    else:
        agency_name = body.get("agency_name", "")
        agency_website = body.get("agency_website", "")
        agency_tagline = body.get("agency_tagline", "")
        report_data = generate_client_report(
            lead_dict,
            agency_name=agency_name,
            agency_website=agency_website,
            agency_tagline=agency_tagline
        )
        if report_data.get("error") and not report_data.get("executive_summary"):
            raise HTTPException(status_code=500, detail=report_data["error"])
        pdf_bytes = generate_client_pdf(report_data)
        filename = f"Website_Audit_{lead.name.replace(' ', '_')}.pdf"
        if not subject:
            subject = f"Website Audit Report - {lead.name}"

    if not email_body:
        if report_type == "client":
            email_body = f"""<html><body>
<p>Hi {lead.contact_name or 'there'},</p>
<p>Please find attached a complimentary website audit report for <b>{lead.name}</b>.</p>
<p>The report includes a detailed analysis of your website's performance, security, mobile experience, and more, along with actionable recommendations.</p>
<p>I'd love to discuss the findings with you. Feel free to reply to this email or give me a call.</p>
<p>Best regards</p>
</body></html>"""
        else:
            email_body = f"<html><body><p>Internal lead report for {lead.name} is attached.</p></body></html>"

    db_session = SessionLocal()
    try:
        result = send_email_with_attachment_for_user(
            db=db_session,
            user_id=current_user.id,
            to_email=lead.email,
            subject=subject,
            html_body=email_body,
            attachment_bytes=pdf_bytes,
            attachment_filename=filename,
            attachment_mime="application/pdf"
        )
        db.update_lead(lead.id, user_id=current_user.id, stage="Contacted")
        return {"success": True, "message": f"Report emailed to {lead.email}", "provider": result.get("provider")}
    except EmailProviderError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")
    finally:
        db_session.close()


@app.get("/api/campaigns")
async def api_get_campaigns(current_user: User = Depends(get_current_user)):
    campaigns = db.get_all_campaigns(user_id=current_user.id)
    active_campaign_id = db.get_active_campaign_id(user_id=current_user.id)
    return {
        "campaigns": [campaign.to_dict() for campaign in campaigns],
        "active_campaign_id": active_campaign_id
    }


@app.get("/api/campaigns/{campaign_id}")
async def api_get_campaign(campaign_id: str, current_user: User = Depends(get_current_user)):
    campaign = db.get_campaign(campaign_id, user_id=current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    lead_count = len(db.get_campaign_leads(campaign_id, user_id=current_user.id))
    campaign_dict = campaign.to_dict()
    campaign_dict['lead_count'] = lead_count
    
    return {"campaign": campaign_dict}


@app.post("/api/campaigns/{campaign_id}/activate")
async def api_activate_campaign(campaign_id: str, current_user: User = Depends(get_current_user)):
    campaign = db.get_campaign(campaign_id, user_id=current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    print(f"Activating campaign: {campaign_id}, name: {campaign.name}, lead_ids count: {len(campaign.lead_ids) if campaign.lead_ids else 0}")
    
    db.set_active_campaign(campaign_id, user_id=current_user.id)
    leads = db.get_campaign_leads(campaign_id, user_id=current_user.id)
    
    print(f"Retrieved {len(leads)} leads for campaign {campaign_id}")
    
    return {
        "campaign": campaign.to_dict(),
        "leads": [lead.to_dict() for lead in leads]
    }


@app.delete("/api/campaigns/{campaign_id}")
async def api_delete_campaign(campaign_id: str, current_user: User = Depends(get_current_user)):
    campaign = db.get_campaign(campaign_id, user_id=current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    success = db.delete_campaign(campaign_id, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete campaign")
    
    return {"success": True, "message": "Campaign deleted"}


@app.post("/api/campaigns/view-all")
async def api_view_all_campaigns(current_user: User = Depends(get_current_user)):
    db.set_active_campaign(None, user_id=current_user.id)
    leads = db.get_all_leads(user_id=current_user.id)
    
    return {
        "active_campaign_id": None,
        "leads": [lead.to_dict() for lead in leads]
    }


@app.get("/api/stats")
async def api_get_stats(current_user: User = Depends(get_current_user)):
    leads = db.get_all_leads(user_id=current_user.id)
    
    stages = {}
    total_score = 0
    scored_count = 0
    
    for lead in leads:
        stage = lead.stage
        stages[stage] = stages.get(stage, 0) + 1
        
        is_successfully_scored = (
            lead.score is not None and lead.score > 0 and
            (lead.last_scored_at is not None or lead.score_reasoning is not None)
        )
        if is_successfully_scored:
            total_score += lead.score
            scored_count += 1
    
    avg_score = round(total_score / scored_count, 1) if scored_count > 0 else 0
    
    return {
        "total_leads": len(leads),
        "by_stage": stages,
        "avg_score": avg_score,
        "emails_sent": db.emails_sent_count,
        "sms_sent": db.sms_sent_count
    }


@app.get("/api/analytics")
async def api_get_analytics(current_user: User = Depends(get_current_user)):
    leads = db.get_all_leads(user_id=current_user.id)
    campaigns = db.get_all_campaigns(user_id=current_user.id)
    
    stages = {}
    total_score = 0
    scored_count = 0
    high_opportunity_count = 0
    
    for lead in leads:
        stage = lead.stage
        stages[stage] = stages.get(stage, 0) + 1
        
        is_successfully_scored = (
            lead.score is not None and lead.score > 0 and
            (lead.last_scored_at is not None or lead.score_reasoning is not None)
        )
        
        if is_successfully_scored:
            total_score += lead.score
            scored_count += 1
        
        if is_successfully_scored and lead.score < 30:
            high_opportunity_count += 1
    
    avg_score = round(total_score / scored_count, 1) if scored_count > 0 else 0
    
    deals_in_progress = stages.get("Meeting", 0) + stages.get("Replied", 0)
    
    return {
        "total_leads": len(leads),
        "total_campaigns": len(campaigns),
        "avg_score": avg_score,
        "by_stage": stages,
        "emails_sent": db.emails_sent_count,
        "sms_sent": db.sms_sent_count,
        "last_7_days_sent": db.emails_sent_count,
        "high_opportunity_leads": high_opportunity_count,
        "deals_in_progress": deals_in_progress
    }


@app.get("/api/export")
async def api_export_csv(current_user: User = Depends(get_current_user)):
    leads = db.get_all_leads(user_id=current_user.id)
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "id", "name", "address", "phone", "website", "email", "score", 
        "website_quality", "digital_presence", "automation_score",
        "stage", "notes", "email_source"
    ])
    
    writer.writeheader()
    for lead in leads:
        # Extract component scores from score_reasoning
        website_quality = ""
        digital_presence = ""
        automation_score = ""
        
        if lead.score_reasoning:
            try:
                reasoning = lead.score_reasoning if isinstance(lead.score_reasoning, dict) else json.loads(lead.score_reasoning)
                website_quality = reasoning.get("website_quality", {}).get("score", "")
                digital_presence = reasoning.get("digital_presence", {}).get("score", "")
                automation_score = reasoning.get("automation_opportunity", {}).get("score", "")
            except:
                pass
        
        writer.writerow({
            "id": lead.id,
            "name": lead.name,
            "address": lead.address,
            "phone": lead.phone,
            "website": lead.website,
            "email": lead.email,
            "score": lead.score,
            "website_quality": f"'{website_quality}/30" if website_quality else "",
            "digital_presence": f"'{digital_presence}/30" if digital_presence else "",
            "automation_score": f"'{automation_score}/40" if automation_score else "",
            "stage": lead.stage,
            "notes": lead.notes,
            "email_source": lead.email_source or ""
        })
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"}
    )


@app.post("/api/preview-emails")
async def api_preview_emails(request: PreviewEmailsRequest, current_user: User = Depends(get_current_user)):
    leads = db.get_all_leads(user_id=current_user.id)[:5]
    
    previews = []
    for lead in leads:
        variables = prepare_email_variables(lead.to_dict())
        
        subject = render_template(request.subject_template, variables)
        body = render_template(request.body_template, variables)
        
        previews.append({
            "lead_id": lead.id,
            "lead_name": lead.name,
            "subject": subject,
            "body": body
        })
    
    return {
        "count": len(previews),
        "previews": previews
    }


@app.post("/api/generate-personalized")
async def api_generate_personalized(request: PersonalizedEmailRequest, current_user: User = Depends(get_current_user)):
    lead = db.get_lead(request.lead_id, user_id=current_user.id)
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    has_credits, balance, cost = credit_manager.has_sufficient_credits(
        current_user.id, "email_personalization", 1
    )
    if not has_credits:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Need {cost} credit for AI personalization, but only have {balance}. Please purchase more credits."
        )
    
    success, _ = credit_manager.deduct_credits(
        current_user.id, "email_personalization", 1,
        f"AI email personalization for {lead.name}"
    )
    if not success:
        raise HTTPException(status_code=402, detail="Failed to deduct credits. Please try again.")
    
    try:
        email_content = generate_personalized_email(
            lead.to_dict(),
            request.base_pitch
        )
        
        return {
            "lead_id": lead.id,
            "lead_name": lead.name,
            "subject": email_content["subject"],
            "body": email_content["body"],
            "credits_used": 1
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Unable to generate email: {str(e)}")


@app.post("/api/send-emails")
async def api_send_emails(request: SendEmailsRequest, current_user: User = Depends(get_current_user)):
    db_session = SessionLocal()
    try:
        leads = db.get_all_leads(user_id=current_user.id)
        
        eligible_leads = []
        for lead in leads:
            if not lead.email or '@' not in lead.email:
                continue
            if request.lead_ids:
                if lead.id not in request.lead_ids:
                    continue
            else:
                if request.only_scored_above is not None and lead.score < request.only_scored_above:
                    continue
                if request.stage_filter and lead.stage != request.stage_filter:
                    continue
            eligible_leads.append(lead)
        
        has_credits, balance, cost = credit_manager.has_sufficient_credits(
            current_user.id, "email_send", len(eligible_leads)
        )
        if not has_credits:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. Need {cost} credits to send {len(eligible_leads)} emails, but only have {balance}. Please purchase more credits."
            )
        
        sent = 0
        if request.lead_ids:
            skipped = len(request.lead_ids) - len(eligible_leads)
        else:
            skipped = len(leads) - len(eligible_leads)
        errors = []
        credits_used = 0
        
        for lead in eligible_leads:
            success, _ = credit_manager.deduct_credits(
                current_user.id, "email_send", 1,
                f"Email to {lead.email}"
            )
            if not success:
                errors.append({
                    "lead_id": lead.id,
                    "lead_name": lead.name,
                    "reason": "Insufficient credits"
                })
                break
            credits_used += 1
            
            variables = prepare_email_variables(lead.to_dict())
            subject = render_template(request.subject_template, variables)
            body = render_template(request.body_template, variables)
            
            if request.include_score_report and lead.score_reasoning:
                score_report = format_score_report_for_email(lead)
                body = body + "\n\n" + score_report
            
            try:
                if request.attach_pdf_report and lead.score_reasoning:
                    from helpers.client_report import generate_client_report
                    from helpers.pdf_report import generate_client_pdf
                    from helpers.email_senders import send_email_with_attachment_for_user
                    report_data = generate_client_report(lead.to_dict())
                    if not report_data.get("error") or report_data.get("executive_summary"):
                        pdf_bytes = generate_client_pdf(report_data)
                        filename = f"Website_Audit_{lead.name.replace(' ', '_')}.pdf"
                        result = send_email_with_attachment_for_user(
                            db_session, current_user.id, lead.email,
                            subject, body, pdf_bytes, filename
                        )
                    else:
                        result = send_email_for_user(db_session, current_user.id, lead.email, subject, body)
                else:
                    result = send_email_for_user(db_session, current_user.id, lead.email, subject, body)
                
                if result.get("success"):
                    db.update_lead(lead.id, user_id=current_user.id, stage="Contacted")
                    sent += 1
                    db.increment_emails_sent()
                else:
                    errors.append({
                        "lead_id": lead.id,
                        "lead_name": lead.name,
                        "reason": "Email sending failed"
                    })
            except EmailProviderError as e:
                errors.append({
                    "lead_id": lead.id,
                    "lead_name": lead.name,
                    "reason": str(e)
                })
            except Exception as e:
                errors.append({
                    "lead_id": lead.id,
                    "lead_name": lead.name,
                    "reason": f"Unexpected error: {str(e)}"
                })
        
        return {
            "sent": sent,
            "skipped": skipped,
            "errors": errors,
            "credits_used": credits_used
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Unable to send emails right now. Please check your email settings and try again.")
    finally:
        db_session.close()


@app.post("/api/send-single-email")
async def api_send_single_email(request: SendSingleEmailRequest, current_user: User = Depends(get_current_user)):
    """Send a single email to a specific lead."""
    db_session = SessionLocal()
    try:
        # Get the lead
        lead = db.get_lead(request.lead_id, user_id=current_user.id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        if not lead.email or '@' not in lead.email:
            raise HTTPException(status_code=400, detail="Lead does not have a valid email address")
        
        # Check credits
        has_credits, balance, cost = credit_manager.has_sufficient_credits(
            current_user.id, "email_send", 1
        )
        if not has_credits:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. Need 1 credit to send email, but only have {balance}. Please purchase more credits."
            )
        
        # Deduct credit
        success, _ = credit_manager.deduct_credits(
            current_user.id, "email_send", 1,
            f"Email to {lead.email}"
        )
        if not success:
            raise HTTPException(status_code=402, detail="Failed to deduct credit")
        
        # Prepare email
        variables = prepare_email_variables(lead.to_dict())
        subject = render_template(request.subject_template, variables)
        body = render_template(request.body_template, variables)
        
        # Append score report if requested
        if request.include_score_report and lead.score_reasoning:
            score_report = format_score_report_for_email(lead)
            body = body + "\n\n" + score_report
        
        if request.attach_pdf_report and lead.score_reasoning:
            from helpers.client_report import generate_client_report
            from helpers.pdf_report import generate_client_pdf
            from helpers.email_senders import send_email_with_attachment_for_user
            report_data = generate_client_report(lead.to_dict())
            if not report_data.get("error") or report_data.get("executive_summary"):
                pdf_bytes = generate_client_pdf(report_data)
                filename = f"Website_Audit_{lead.name.replace(' ', '_')}.pdf"
                result = send_email_with_attachment_for_user(
                    db_session, current_user.id, lead.email,
                    subject, body, pdf_bytes, filename
                )
            else:
                result = send_email_for_user(db_session, current_user.id, lead.email, subject, body)
        else:
            result = send_email_for_user(db_session, current_user.id, lead.email, subject, body)
        
        if result.get("success"):
            db.update_lead(lead.id, user_id=current_user.id, stage="Contacted")
            db.increment_emails_sent()
            return {
                "success": True,
                "message": f"Email sent successfully to {lead.email}",
                "credits_used": 1
            }
        else:
            raise HTTPException(status_code=500, detail="Email sending failed")
            
    except HTTPException:
        raise
    except EmailProviderError as e:
        print(f"Email provider error: {e}")
        raise HTTPException(status_code=500, detail="Email sending failed. Please check your email provider settings and try again.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Unable to send email right now. Please try again.")
    finally:
        db_session.close()


@app.post("/api/preview-sms")
async def api_preview_sms(request: PreviewSMSRequest, current_user: User = Depends(get_current_user)):
    from helpers.models import Lead as LeadModel
    db_session = SessionLocal()
    try:
        lead_models = db_session.query(LeadModel).filter(
            LeadModel.user_id == current_user.id,
            LeadModel.phone.isnot(None),
            LeadModel.phone != ''
        ).limit(5).all()
        
        previews = []
        for lead in lead_models:
            lead_dict = {
                'name': lead.name,
                'phone': lead.phone,
                'email': lead.email,
                'address': lead.address,
                'website': lead.website
            }
            variables = prepare_sms_variables(lead_dict)
            message = render_sms_template(request.message_template, variables)
            
            previews.append({
                "lead_id": lead.id,
                "lead_name": lead.name,
                "phone": lead.phone,
                "message": message
            })
        
        return {
            "previews": previews,
            "count": len(previews)
        }
    finally:
        db_session.close()


@app.post("/api/send-sms")
async def api_send_sms(request: SendSMSRequest, current_user: User = Depends(get_current_user)):
    db_session = SessionLocal()
    try:
        api_keys = get_user_api_keys(db_session, current_user.id)
        
        if not validate_sms_config(
            account_sid=api_keys.twilio_account_sid,
            auth_token=api_keys.twilio_auth_token,
            phone_number=api_keys.twilio_phone_number
        ):
            raise HTTPException(status_code=400, detail="SMS is not configured yet. Please set up your Twilio credentials in Settings to enable SMS campaigns.")
        
        leads = db.get_all_leads(user_id=current_user.id)
        
        eligible_leads = []
        for lead in leads:
            if not lead.phone:
                continue
            if request.lead_ids:
                if lead.id not in request.lead_ids:
                    continue
            else:
                if request.only_scored_above is not None and lead.score < request.only_scored_above:
                    continue
                if request.stage_filter and lead.stage != request.stage_filter:
                    continue
            eligible_leads.append(lead)
        
        has_credits, balance, cost = credit_manager.has_sufficient_credits(
            current_user.id, "sms_send", len(eligible_leads)
        )
        if not has_credits:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. Need {cost} credits to send {len(eligible_leads)} SMS messages, but only have {balance}. Please purchase more credits."
            )
        
        sent = 0
        if request.lead_ids:
            skipped = len(request.lead_ids) - len(eligible_leads)
        else:
            skipped = len(leads) - len(eligible_leads)
        errors = []
        credits_used = 0
        
        for lead in eligible_leads:
            success, _ = credit_manager.deduct_credits(
                current_user.id, "sms_send", 1,
                f"SMS to {lead.phone}"
            )
            if not success:
                errors.append({
                    "lead_id": lead.id,
                    "lead_name": lead.name,
                    "reason": "Insufficient credits"
                })
                break
            credits_used += 2
            
            variables = prepare_sms_variables(lead.to_dict())
            message = render_sms_template(request.message_template, variables)
            
            result = send_sms(
                lead.phone, 
                message,
                account_sid=api_keys.twilio_account_sid,
                auth_token=api_keys.twilio_auth_token,
                phone_number=api_keys.twilio_phone_number
            )
            
            if result.get("success"):
                db.update_lead(lead.id, user_id=current_user.id, stage="Contacted")
                sent += 1
                db.increment_sms_sent()
            else:
                errors.append({
                    "lead_id": lead.id,
                    "lead_name": lead.name,
                    "reason": result.get("error", "Unknown error")
                })
        
        return {
            "sent": sent,
            "skipped": skipped,
            "errors": errors,
            "credits_used": credits_used
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Unable to send SMS messages. Please check your Twilio settings and try again.")
    finally:
        db_session.close()


@app.post("/api/enrich-from-website")
async def api_enrich_from_website(request: EnrichFromWebsiteRequest, current_user: User = Depends(get_current_user)):
    try:
        if request.lead_ids:
            print(f"[enrich-website] Enriching {len(request.lead_ids)} specific leads for user {current_user.id}")
            leads_to_enrich = [db.get_lead(lid, user_id=current_user.id) for lid in request.lead_ids]
            leads_to_enrich = [l for l in leads_to_enrich if l is not None]
        else:
            all_leads = db.get_all_leads(user_id=current_user.id)
            leads_to_enrich = [l for l in all_leads if l.website and not l.email]
            print(f"[enrich-website] Enriching all {len(leads_to_enrich)} leads without email for user {current_user.id}")
        
        leads_needing_work = []
        for lead in leads_to_enrich:
            if not lead.website:
                continue
            needs_email = not lead.email
            needs_phone = not lead.phone
            if needs_email or needs_phone:
                leads_needing_work.append((lead, needs_email, needs_phone))
        
        def _run_enrichment():
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            def enrich_single_lead(lead_info):
                lead, needs_email, needs_phone = lead_info
                update_data = {}
                try:
                    if needs_email:
                        candidates = extract_emails_from_website(lead.website)
                        if candidates:
                            email_candidates_merged = list(set(lead.email_candidates + candidates))
                            best_email = choose_best_email(candidates)
                            if best_email:
                                update_data['email'] = best_email
                                update_data['email_source'] = "website"
                                update_data['email_confidence'] = 0.7
                                update_data['email_candidates'] = email_candidates_merged
                    if needs_phone:
                        phone = extract_phone_from_website(lead.website)
                        if phone:
                            update_data['phone'] = phone
                except Exception as e:
                    print(f"[enrich-website] Error enriching {lead.website}: {e}")
                return (lead, update_data)
            
            updated = 0
            updated_leads = []
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(enrich_single_lead, info): info for info in leads_needing_work}
                for future in as_completed(futures, timeout=60):
                    try:
                        lead, update_data = future.result(timeout=15)
                        if update_data:
                            lead_updated = db.update_lead(
                                lead.id,
                                user_id=current_user.id,
                                **update_data
                            )
                            if lead_updated:
                                updated += 1
                                updated_leads.append(lead_updated.to_dict())
                    except Exception as e:
                        print(f"[enrich-website] Future error: {e}")
            
            return {"updated": updated, "leads": updated_leads}
        
        result = await asyncio.to_thread(_run_enrichment)
        return result
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Unable to enrich leads from websites. Please try again.")


@app.post("/api/enrich-from-hunter")
async def api_enrich_from_hunter(request: EnrichFromHunterRequest, current_user: User = Depends(get_current_user)):
    db_session = SessionLocal()
    HUNTER_CREDIT_COST = 2
    try:
        api_keys = get_user_api_keys(db_session, current_user.id)
        
        hunter_key = api_keys.hunter_api_key or HUNTER_API_KEY
        if not hunter_key:
            raise HTTPException(
                status_code=400,
                detail="Hunter.io API key not configured. Please add your Hunter.io API key in Settings."
            )
        
        if request.lead_ids:
            leads_to_enrich = [db.get_lead(lid, user_id=current_user.id) for lid in request.lead_ids]
            leads_to_enrich = [l for l in leads_to_enrich if l is not None]
        else:
            all_leads = db.get_all_leads(user_id=current_user.id)
            leads_to_enrich = [l for l in all_leads if l.website and not l.email]
        
        eligible_leads = [l for l in leads_to_enrich if l.website and not l.email and extract_domain(l.website)]
        total_cost = len(eligible_leads) * HUNTER_CREDIT_COST
        
        if total_cost > 0:
            current_balance = credit_manager.get_balance(current_user.id)
            if current_balance < total_cost:
                raise HTTPException(
                    status_code=402,
                    detail=f"Insufficient credits. Hunter enrichment costs {HUNTER_CREDIT_COST} credits per lead. You need {total_cost} credits but only have {current_balance}."
                )
        
        updated = 0
        updated_leads = []
        credits_used = 0
        
        for lead in eligible_leads:
            domain = extract_domain(lead.website)
            
            success, _ = credit_manager.deduct_credits(
                current_user.id, "hunter_enrichment", HUNTER_CREDIT_COST,
                f"Hunter.io email lookup for {lead.name}"
            )
            if not success:
                break
            
            credits_used += HUNTER_CREDIT_COST
            
            hunter_result = enrich_from_hunter(
                domain, 
                max_results=request.max_per_domain,
                hunter_api_key=hunter_key
            )
            
            if not hunter_result.get("success"):
                continue
            
            hunter_emails = hunter_result.get("emails", [])
            
            if hunter_emails:
                email_candidates_merged = list(lead.email_candidates)
                for email_obj in hunter_emails:
                    email_addr = email_obj.get("email")
                    if email_addr and email_addr not in email_candidates_merged:
                        email_candidates_merged.append(email_addr)
                
                best_hunter = hunter_emails[0]
                lead_updated = db.update_lead(
                    lead.id,
                    user_id=current_user.id,
                    email=best_hunter.get("email"),
                    email_source="hunter",
                    email_confidence=best_hunter.get("confidence", 0.5),
                    email_candidates=email_candidates_merged
                )
                if lead_updated:
                    updated += 1
                    updated_leads.append(lead_updated.to_dict())
        
        return {
            "updated": updated,
            "leads": updated_leads,
            "credits_used": credits_used
        }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Unable to enrich leads via Hunter. Please try again.")
    finally:
        db_session.close()


@app.get("/api/email/auth/gmail/url")
async def get_gmail_auth_url(current_user: User = Depends(get_current_user)):
    """Get Gmail OAuth URL for user authentication."""
    client_id, _, redirect_uri = db.get_gmail_oauth_credentials()
    
    if not client_id or not redirect_uri:
        raise HTTPException(
            status_code=500,
            detail="Gmail OAuth not configured. Please configure OAuth settings in Settings → OAuth Setup tab."
        )
    
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/userinfo.email",
        "access_type": "offline",
        "prompt": "consent",
        "state": str(current_user.id)
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    
    return {
        "auth_url": auth_url,
        "provider": "gmail"
    }


@app.get("/api/email/auth/gmail/callback")
def gmail_auth_callback(code: str, state: str):
    db_session = SessionLocal()
    try:
        user_id = int(state)
        
        client_id, client_secret, redirect_uri = db.get_gmail_oauth_credentials()
        
        if not all([client_id, client_secret, redirect_uri]):
            raise HTTPException(
                status_code=500,
                detail="Gmail OAuth credentials not configured. Please configure OAuth settings in Settings → OAuth Setup tab."
            )
        
        token_response = requests.post("https://oauth2.googleapis.com/token", data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }, timeout=15)
        
        if token_response.status_code != 200:
            print(f"Gmail token exchange failed: {token_response.status_code} - {token_response.text}")
            raise HTTPException(
                status_code=400,
                detail="Gmail authorization failed. Please try connecting again."
            )
        
        tokens = token_response.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in", 3600)
        
        user_info_response = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo", timeout=15,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if user_info_response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail="Failed to get user info from Gmail"
            )
        
        user_info = user_info_response.json()
        gmail_email = user_info.get("email")
        
        settings = db_session.query(EmailSettings).filter(EmailSettings.user_id == user_id).first()
        
        if not settings:
            settings = EmailSettings(user_id=user_id)
            db_session.add(settings)
        
        settings.provider = "gmail"
        settings.gmail_access_token = encrypt(access_token)
        settings.gmail_refresh_token = encrypt(refresh_token) if refresh_token else None
        settings.gmail_token_expiry = datetime.now() + timedelta(seconds=expires_in)
        settings.gmail_email_address = gmail_email
        
        db_session.commit()
        
        return {
            "success": True,
            "provider": "gmail",
            "email": gmail_email,
            "message": "Gmail successfully connected"
        }
    
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    except HTTPException:
        raise
    except Exception as e:
        db_session.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Gmail connection failed. Please try again.")
    finally:
        db_session.close()


@app.get("/api/email/auth/outlook/url")
async def get_outlook_auth_url(current_user: User = Depends(get_current_user)):
    client_id, _, redirect_uri = db.get_outlook_oauth_credentials()
    
    if not client_id or not redirect_uri:
        raise HTTPException(
            status_code=500,
            detail="Outlook OAuth not configured. Please configure OAuth settings in Settings → OAuth Setup tab."
        )
    
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "offline_access Mail.Send User.Read",
        "response_mode": "query",
        "state": str(current_user.id)
    }
    
    auth_url = f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{urlencode(params)}"
    
    return {
        "auth_url": auth_url,
        "provider": "outlook"
    }


@app.get("/api/email/auth/outlook/callback")
def outlook_auth_callback(code: str, state: str):
    db_session = SessionLocal()
    try:
        user_id = int(state)
        
        client_id, client_secret, redirect_uri = db.get_outlook_oauth_credentials()
        
        if not all([client_id, client_secret, redirect_uri]):
            raise HTTPException(
                status_code=500,
                detail="Outlook OAuth credentials not configured. Please configure OAuth settings in Settings → OAuth Setup tab."
            )
        
        token_response = requests.post(
            "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
                "scope": "offline_access Mail.Send User.Read"
            },
            timeout=15
        )
        
        if token_response.status_code != 200:
            print(f"Outlook token exchange failed: {token_response.status_code} - {token_response.text}")
            raise HTTPException(
                status_code=400,
                detail="Outlook authorization failed. Please try connecting again."
            )
        
        tokens = token_response.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in", 3600)
        
        user_info_response = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15
        )
        
        if user_info_response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail="Failed to get user info from Outlook"
            )
        
        user_info = user_info_response.json()
        outlook_email = user_info.get("mail") or user_info.get("userPrincipalName")
        
        settings = db_session.query(EmailSettings).filter(EmailSettings.user_id == user_id).first()
        
        if not settings:
            settings = EmailSettings(user_id=user_id)
            db_session.add(settings)
        
        settings.provider = "outlook"
        settings.outlook_access_token = encrypt(access_token)
        settings.outlook_refresh_token = encrypt(refresh_token) if refresh_token else None
        settings.outlook_token_expiry = datetime.now() + timedelta(seconds=expires_in)
        settings.outlook_email_address = outlook_email
        
        db_session.commit()
        
        return {
            "success": True,
            "provider": "outlook",
            "email": outlook_email,
            "message": "Outlook successfully connected"
        }
    
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    except HTTPException:
        raise
    except Exception as e:
        db_session.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Outlook connection failed. Please try again.")
    finally:
        db_session.close()


@app.post("/api/email/settings/smtp")
async def configure_smtp(request: SMTPConfigRequest, current_user: User = Depends(get_current_user)):
    db_session = SessionLocal()
    try:
        settings = db_session.query(EmailSettings).filter(EmailSettings.user_id == current_user.id).first()
        
        if not settings:
            settings = EmailSettings(user_id=current_user.id)
            db_session.add(settings)
        
        settings.provider = "smtp"
        settings.smtp_host = request.smtp_host
        settings.smtp_port = request.smtp_port
        settings.smtp_username = request.smtp_username
        settings.smtp_password_encrypted = encrypt(request.smtp_password)
        settings.smtp_from_email = request.smtp_from_email
        settings.smtp_use_tls = request.smtp_use_tls
        
        db_session.commit()
        
        verify_warning = None
        try:
            import smtplib as _smtplib
            import socket as _socket
            _socket.setdefaulttimeout(5)
            try:
                if request.smtp_use_tls:
                    srv = _smtplib.SMTP(request.smtp_host, int(request.smtp_port), timeout=5)
                    srv.starttls()
                else:
                    srv = _smtplib.SMTP_SSL(request.smtp_host, int(request.smtp_port), timeout=5)
                srv.login(request.smtp_username, request.smtp_password)
                srv.quit()
            finally:
                _socket.setdefaulttimeout(None)
        except (TimeoutError, _socket.timeout, OSError) as ve:
            verify_warning = "Settings saved but connection verification timed out. Your settings may still be correct."
            print(f"SMTP verify timeout: {ve}")
        except Exception as ve:
            verify_warning = f"Settings saved but verification failed: {str(ve)}. You can still try sending a test email."
            print(f"SMTP verify error: {ve}")
        
        result = {
            "success": True,
            "provider": "smtp",
            "message": "SMTP settings configured successfully" if not verify_warning else verify_warning
        }
        if verify_warning:
            result["warning"] = verify_warning
        return result
    
    except Exception as e:
        db_session.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="SMTP configuration failed. Please check your settings and try again.")
    finally:
        db_session.close()


@app.post("/api/email/settings/sendgrid")
async def configure_sendgrid(request: SendGridConfigRequest, current_user: User = Depends(get_current_user)):
    db_session = SessionLocal()
    try:
        settings = db_session.query(EmailSettings).filter(EmailSettings.user_id == current_user.id).first()
        
        if not settings:
            settings = EmailSettings(user_id=current_user.id)
            db_session.add(settings)
        
        settings.provider = "sendgrid"
        settings.sendgrid_api_key_encrypted = encrypt(request.api_key)
        settings.sendgrid_from_email = request.from_email
        
        db_session.commit()
        
        return {
            "success": True,
            "provider": "sendgrid",
            "message": "SendGrid settings configured successfully"
        }
    
    except Exception as e:
        db_session.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="SendGrid configuration failed. Please check your API key and try again.")
    finally:
        db_session.close()


@app.get("/api/email/settings/status")
async def get_email_settings_status(current_user: User = Depends(get_current_user)):
    db_session = SessionLocal()
    try:
        settings = db_session.query(EmailSettings).filter(EmailSettings.user_id == current_user.id).first()
        
        if not settings or settings.provider == "none":
            return {
                "configured": False,
                "provider": "none",
                "email": None
            }
        
        response_data = {
            "configured": True,
            "provider": settings.provider,
            "email": None
        }
        
        if settings.provider == "gmail":
            response_data["email"] = settings.gmail_email_address
            response_data["token_valid"] = settings.gmail_token_expiry and datetime.now() < settings.gmail_token_expiry
        elif settings.provider == "outlook":
            response_data["email"] = settings.outlook_email_address
            response_data["token_valid"] = settings.outlook_token_expiry and datetime.now() < settings.outlook_token_expiry
        elif settings.provider == "smtp":
            response_data["email"] = settings.smtp_from_email
            response_data["smtp_host"] = settings.smtp_host
            response_data["smtp_port"] = settings.smtp_port
        elif settings.provider == "sendgrid":
            response_data["email"] = settings.sendgrid_from_email
        
        return response_data
    
    finally:
        db_session.close()


@app.delete("/api/email/settings/disconnect")
async def disconnect_email_provider(current_user: User = Depends(get_current_user)):
    db_session = SessionLocal()
    try:
        settings = db_session.query(EmailSettings).filter(EmailSettings.user_id == current_user.id).first()
        
        if not settings:
            return {
                "success": True,
                "message": "No email provider was connected"
            }
        
        old_provider = settings.provider
        
        settings.provider = "none"
        settings.gmail_access_token = None
        settings.gmail_refresh_token = None
        settings.gmail_token_expiry = None
        settings.gmail_email_address = None
        settings.outlook_access_token = None
        settings.outlook_refresh_token = None
        settings.outlook_token_expiry = None
        settings.outlook_email_address = None
        settings.smtp_host = None
        settings.smtp_port = None
        settings.smtp_username = None
        settings.smtp_password_encrypted = None
        settings.smtp_from_email = None
        settings.smtp_use_tls = True
        settings.sendgrid_api_key_encrypted = None
        settings.sendgrid_from_email = None
        
        db_session.commit()
        
        return {
            "success": True,
            "message": f"{old_provider.capitalize()} disconnected successfully"
        }
    
    except Exception as e:
        db_session.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to disconnect email provider. Please try again.")
    finally:
        db_session.close()


@app.post("/api/email/test")
async def send_test_email(request: TestEmailRequest, current_user: User = Depends(get_current_user)):
    db_session = SessionLocal()
    try:
        settings = db_session.query(EmailSettings).filter(EmailSettings.user_id == current_user.id).first()
        
        if not settings or settings.provider == "none":
            raise HTTPException(
                status_code=400,
                detail="No email provider configured. Please set up an email provider first."
            )
        
        html_body = f"<html><body><p>{request.body}</p></body></html>"
        
        try:
            result = send_email_for_user(
                db=db_session,
                user_id=current_user.id,
                to_email=request.to_email,
                subject=request.subject,
                html_body=html_body
            )
            
            return {
                "success": True,
                "message": f"Test email sent successfully via {result.get('provider')}",
                "provider": result.get("provider"),
                "to_email": request.to_email
            }
        
        except EmailProviderError as e:
            error_msg = str(e)
            print(f"Test email provider error: {e}")
            if "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
                raise HTTPException(status_code=408, detail=f"Test email timed out: {error_msg}. The server may be slow to respond — try again or check your SMTP host/port.")
            raise HTTPException(status_code=400, detail=f"Test email failed: {error_msg}")
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to send test email. Please check your email settings.")
    finally:
        db_session.close()


@app.get("/api/credits")
async def get_credits(current_user: User = Depends(get_current_user)):
    credits = credit_manager.get_user_credits(current_user.id)
    return {
        "balance": credits["balance"],
        "total_purchased": credits["total_purchased"],
        "total_used": credits["total_used"],
        "packages": CREDIT_PACKAGES,
        "costs": CREDIT_COSTS
    }


class CreateCheckoutRequest(BaseModel):
    plan_name: str


@app.post("/api/create-checkout-session")
async def api_create_checkout_session(
    request: Request,
    checkout_request: CreateCheckoutRequest,
    current_user: User = Depends(get_current_user)
):
    from helpers.models import Payment, FoundingMemberCounter, SessionLocal as DBSession
    
    package_id = checkout_request.plan_name
    if package_id not in CREDIT_PACKAGES:
        raise HTTPException(status_code=400, detail="Invalid plan")
    
    if package_id == "founding_member":
        db_session = DBSession()
        try:
            counter = db_session.query(FoundingMemberCounter).first()
            if not counter:
                counter = FoundingMemberCounter(count=0, max_slots=100)
                db_session.add(counter)
                db_session.commit()
                db_session.refresh(counter)
            if counter.count >= counter.max_slots:
                raise HTTPException(status_code=400, detail="Founding Member slots are sold out!")
        finally:
            db_session.close()
    
    host = request.headers.get("host", "localhost:5000")
    protocol = "https" if "replit" in host else "http"
    base_url = f"{protocol}://{host}"
    
    credits_info = credit_manager.get_user_credits(current_user.id)
    
    try:
        result = await create_checkout_session(
            user_id=current_user.id,
            user_email=current_user.email,
            package_id=package_id,
            success_url=f"{base_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base_url}/payment/cancel",
            stripe_customer_id=credits_info.get("stripe_customer_id")
        )
        
        db_session = DBSession()
        try:
            package = CREDIT_PACKAGES[package_id]
            payment = Payment(
                user_id=current_user.id,
                stripe_session_id=result["session_id"],
                amount_cents=package["price_cents"],
                credits_purchased=package["credits"],
                plan_name=package["name"],
                status="pending"
            )
            db_session.add(payment)
            db_session.commit()
        finally:
            db_session.close()
        
        return {"url": result["url"], "session_id": result["session_id"]}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Unable to start checkout. Please try again.")


@app.get("/api/subscriptions")
async def get_subscriptions(current_user: User = Depends(get_current_user)):
    from helpers.models import UserSubscription, SessionLocal
    
    db = SessionLocal()
    try:
        subscriptions = db.query(UserSubscription).filter(
            UserSubscription.user_id == current_user.id,
            UserSubscription.status.in_(["active", "canceling"])
        ).all()
        
        has_active = any(sub.status == "active" for sub in subscriptions)
        
        return {
            "has_active_subscription": has_active,
            "subscriptions": [
                {
                    "id": sub.id,
                    "package_id": sub.package_id,
                    "package_name": CREDIT_PACKAGES.get(sub.package_id, {}).get("name", sub.package_id),
                    "credits_per_period": sub.credits_per_period,
                    "status": sub.status,
                    "cancel_at_period_end": sub.cancel_at_period_end,
                    "stripe_subscription_id": sub.stripe_subscription_id,
                    "current_period_start": sub.current_period_start.isoformat() if sub.current_period_start else None,
                    "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
                    "created_at": sub.created_at.isoformat() if sub.created_at else None
                }
                for sub in subscriptions
            ]
        }
    finally:
        db.close()


@app.post("/api/subscriptions/{subscription_id}/cancel")
async def cancel_subscription(subscription_id: int, current_user: User = Depends(get_current_user)):
    import stripe
    from helpers.models import UserSubscription, SessionLocal
    
    db_session = SessionLocal()
    try:
        sub = db_session.query(UserSubscription).filter_by(
            id=subscription_id,
            user_id=current_user.id,
            status="active"
        ).first()
        
        if not sub:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        _, secret_key = await get_stripe_credentials()
        stripe.api_key = secret_key
        
        stripe_sub_id = sub.stripe_subscription_id
        await asyncio.to_thread(stripe.Subscription.modify, stripe_sub_id, cancel_at_period_end=True)
        
        sub.status = "canceling"
        db_session.commit()
        
        return {"message": "Subscription will cancel at end of billing period"}
    except stripe.error.StripeError as e:
        print(f"Stripe cancellation error: {e}")
        raise HTTPException(status_code=400, detail="Unable to cancel subscription. Please try again or contact support.")
    finally:
        db_session.close()


@app.get("/api/credits/history")
async def get_credit_history(current_user: User = Depends(get_current_user)):
    transactions = credit_manager.get_transaction_history(current_user.id)
    return {"transactions": transactions}


@app.get("/api/credits/transactions")
async def get_credit_transactions(current_user: User = Depends(get_current_user)):
    transactions = credit_manager.get_transaction_history(current_user.id)
    return {"transactions": transactions}


class CheckoutRequest(BaseModel):
    package_id: str


@app.post("/api/credits/checkout")
async def create_checkout(
    request: Request,
    checkout_request: CheckoutRequest,
    current_user: User = Depends(get_current_user)
):
    from helpers.models import Payment, FoundingMemberCounter, SessionLocal as DBSession
    
    package_id = checkout_request.package_id
    if package_id not in CREDIT_PACKAGES:
        raise HTTPException(status_code=400, detail="Invalid package")
    
    if package_id == "founding_member":
        db_session = DBSession()
        try:
            counter = db_session.query(FoundingMemberCounter).first()
            if not counter:
                counter = FoundingMemberCounter(count=0, max_slots=100)
                db_session.add(counter)
                db_session.commit()
                db_session.refresh(counter)
            if counter.count >= counter.max_slots:
                raise HTTPException(status_code=400, detail="Founding Member slots are sold out!")
        finally:
            db_session.close()
    
    host = request.headers.get("host", "localhost:5000")
    protocol = "https" if "replit" in host else "http"
    base_url = f"{protocol}://{host}"
    
    credits_info = credit_manager.get_user_credits(current_user.id)
    
    try:
        result = await create_checkout_session(
            user_id=current_user.id,
            user_email=current_user.email,
            package_id=package_id,
            success_url=f"{base_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base_url}/payment/cancel",
            stripe_customer_id=credits_info.get("stripe_customer_id")
        )
        
        db_session = DBSession()
        try:
            package = CREDIT_PACKAGES[package_id]
            payment = Payment(
                user_id=current_user.id,
                stripe_session_id=result["session_id"],
                amount_cents=package["price_cents"],
                credits_purchased=package["credits"],
                plan_name=package["name"],
                status="pending"
            )
            db_session.add(payment)
            db_session.commit()
        finally:
            db_session.close()
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Unable to start checkout. Please try again.")


class TwilioPostCallRequest(BaseModel):
    caller_phone: str
    caller_name: str
    caller_email: Optional[str] = ""
    call_type: str
    call_summary: str


@app.post("/api/twilio/post-call")
async def twilio_post_call(request: Request, payload: TwilioPostCallRequest):
    from helpers.system_email import send_post_call_emails

    logger_name = "twilio-post-call"
    import logging
    log = logging.getLogger(logger_name)

    webhook_secret = os.environ.get("TWILIO_WEBHOOK_SECRET", "")
    if webhook_secret:
        provided = request.headers.get("x-webhook-secret", "")
        if provided != webhook_secret:
            log.warning("[POST-CALL] Rejected: invalid or missing x-webhook-secret header")
            raise HTTPException(status_code=403, detail="Forbidden")

    log.info(
        f"[POST-CALL] Received: type={payload.call_type}, "
        f"name={payload.caller_name}, phone={payload.caller_phone}, "
        f"email={payload.caller_email or '(none)'}"
    )

    if payload.call_type not in ("demo", "support", "other"):
        log.warning(f"[POST-CALL] Unknown call_type '{payload.call_type}', treating as 'other'")

    try:
        emails_sent, errors = send_post_call_emails(
            call_type=payload.call_type,
            caller_name=payload.caller_name,
            caller_email=payload.caller_email or "",
            caller_phone=payload.caller_phone,
            call_summary=payload.call_summary,
        )
        if errors:
            log.warning(f"[POST-CALL] Partial errors: {errors}")
    except Exception as e:
        log.error(f"[POST-CALL] Unexpected error: {e}")
        emails_sent = 0

    log.info(f"[POST-CALL] Done. Emails sent: {emails_sent}")
    return {"status": "ok", "emails_sent": emails_sent}


@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    import stripe
    import json as json_module
    from helpers.models import Payment, FoundingMemberCounter, SessionLocal
    
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    
    try:
        _, secret_key = await get_stripe_credentials()
        stripe.api_key = secret_key
        
        webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
        
        if webhook_secret:
            event = await asyncio.to_thread(stripe.Webhook.construct_event, payload, signature, webhook_secret)
        else:
            event_data = json_module.loads(payload)
            event = stripe.Event.construct_from(event_data, stripe.api_key)
        
        if event.type == "checkout.session.completed":
            session = event.data.object
            metadata = session.get("metadata", {})
            
            if metadata.get("waitlist") == "true":
                from helpers.waitlist import update_waitlist_payment, send_waitlist_email
                waitlist_email = metadata.get("email", "")
                waitlist_plan = metadata.get("plan")
                checkout_id = session.get("id", "")
                wl_result = update_waitlist_payment(checkout_id, waitlist_email)
                if wl_result:
                    try:
                        send_waitlist_email(waitlist_email, wl_result["signup_number"], "founding", waitlist_plan)
                    except Exception:
                        pass
                return {"received": True, "status": "waitlist_processed"}
            
            user_id = metadata.get("user_id")
            package_id = metadata.get("package_id")
            credits_amount = int(metadata.get("credits", 0))
            plan_name = metadata.get("plan_name", "Credit Package")
            amount_cents = int(metadata.get("amount_cents", 0))
            checkout_session_id = session.get("id")
            payment_intent_id = session.get("payment_intent")
            customer_id = session.get("customer")
            
            if user_id:
                if credit_manager.check_duplicate_session(checkout_session_id):
                    return {"received": True, "status": "duplicate"}
                
                user_id_int = int(user_id)
                
                verified_package = CREDIT_PACKAGES.get(package_id)
                if verified_package:
                    credits_amount = verified_package["credits"]
                    plan_name = verified_package["name"]
                
                if customer_id:
                    credit_manager.set_stripe_customer_id(user_id_int, customer_id)
                
                db = SessionLocal()
                try:
                    if package_id == "founding_member":
                        counter = db.query(FoundingMemberCounter).with_for_update().first()
                        if not counter:
                            counter = FoundingMemberCounter(count=0, max_slots=100)
                            db.add(counter)
                            db.flush()
                        if counter.count >= counter.max_slots:
                            print(f"Founding member slots exhausted, rejecting webhook for user {user_id}")
                            db.rollback()
                            return {"received": True, "status": "founding_member_sold_out"}
                        counter.count += 1
                    
                    credit_manager.add_credits(
                        user_id=user_id_int,
                        amount=credits_amount,
                        description=f"Purchase: {plan_name}",
                        stripe_payment_intent_id=payment_intent_id,
                        stripe_checkout_session_id=checkout_session_id
                    )
                    
                    payment = db.query(Payment).filter_by(
                        stripe_session_id=checkout_session_id
                    ).first()
                    if payment:
                        payment.status = "completed"
                        payment.stripe_payment_intent = payment_intent_id
                    else:
                        payment = Payment(
                            user_id=user_id_int,
                            stripe_session_id=checkout_session_id,
                            stripe_payment_intent=payment_intent_id,
                            amount_cents=amount_cents,
                            credits_purchased=credits_amount,
                            plan_name=plan_name,
                            status="completed"
                        )
                        db.add(payment)
                    
                    db.commit()
                finally:
                    db.close()
        
        elif event.type == "checkout.session.expired":
            session = event.data.object
            checkout_session_id = session.get("id")
            if checkout_session_id:
                db = SessionLocal()
                try:
                    payment = db.query(Payment).filter_by(
                        stripe_session_id=checkout_session_id
                    ).first()
                    if payment:
                        payment.status = "failed"
                        db.commit()
                finally:
                    db.close()
        
        return {"received": True}
    
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=400, detail="Webhook processing error")


@app.get("/api/founding-member-slots")
async def get_founding_member_slots():
    from helpers.models import FoundingMemberCounter, SessionLocal as DBSession
    db = DBSession()
    try:
        counter = db.query(FoundingMemberCounter).first()
        if not counter:
            counter = FoundingMemberCounter(count=0, max_slots=100)
            db.add(counter)
            db.commit()
            db.refresh(counter)
        return {
            "sold": counter.count,
            "max_slots": counter.max_slots,
            "remaining": counter.max_slots - counter.count
        }
    finally:
        db.close()


@app.get("/api/payments/history")
async def get_payment_history(current_user: User = Depends(get_current_user)):
    from helpers.models import Payment, SessionLocal as DBSession
    db = DBSession()
    try:
        payments = db.query(Payment).filter_by(
            user_id=current_user.id
        ).order_by(Payment.created_at.desc()).limit(50).all()
        return {
            "payments": [
                {
                    "id": p.id,
                    "plan_name": p.plan_name,
                    "amount_cents": p.amount_cents,
                    "credits_purchased": p.credits_purchased,
                    "status": p.status,
                    "stripe_session_id": p.stripe_session_id,
                    "created_at": p.created_at.isoformat() if p.created_at else None
                }
                for p in payments
            ]
        }
    finally:
        db.close()


@app.get("/api/payment-details")
async def get_payment_details(session_id: str):
    from helpers.models import Payment, SessionLocal as DBSession
    db = DBSession()
    try:
        payment = db.query(Payment).filter_by(stripe_session_id=session_id).first()
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        return {
            "plan_name": payment.plan_name,
            "amount_cents": payment.amount_cents,
            "credits_purchased": payment.credits_purchased,
            "status": payment.status,
            "created_at": payment.created_at.isoformat() if payment.created_at else None
        }
    finally:
        db.close()


@app.get("/payment/success", response_class=HTMLResponse)
async def payment_success_page():
    with open("templates/payment_success.html", "r") as f:
        return inject_ga_into_html(f.read())


@app.get("/payment/cancel", response_class=HTMLResponse)
async def payment_cancel_page():
    with open("templates/payment_cancel.html", "r") as f:
        return inject_ga_into_html(f.read())


@app.get("/api/stripe/publishable-key")
async def get_publishable_key():
    try:
        publishable_key, _ = await get_stripe_credentials()
        return {"publishable_key": publishable_key}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Payment system temporarily unavailable. Please try again.")


@app.post("/api/credits/issue")
async def issue_credits_cron(request: Request):
    """
    Scheduled credit issuance endpoint - should be called daily by a cron job.
    Issues accrued credits to all users with active subscriptions.
    Protected by a simple secret key.
    """
    from datetime import datetime, timezone
    from helpers.models import UserSubscription, CreditState, UserCredits, SessionLocal
    from helpers.credit_drip import (
        issue_credits_for_user, 
        get_or_create_credit_state,
        get_plan_config
    )
    
    cron_secret = os.environ.get("CREDIT_CRON_SECRET", "")
    auth_header = request.headers.get("Authorization", "")
    
    if cron_secret and auth_header != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    db = SessionLocal()
    try:
        active_subs = db.query(UserSubscription).filter(
            UserSubscription.status.in_(["active", "canceling"])
        ).all()
        
        results = []
        total_issued = 0
        
        for sub in active_subs:
            if not sub.current_period_start or not sub.current_period_end:
                continue
            
            credit_state = get_or_create_credit_state(db, sub.user_id)
            
            user_credits = db.query(UserCredits).filter_by(user_id=sub.user_id).first()
            if not user_credits:
                user_credits = UserCredits(user_id=sub.user_id, balance=0, total_purchased=0, total_used=0)
                db.add(user_credits)
                db.commit()
            
            credits_issued = issue_credits_for_user(
                db=db,
                user_id=sub.user_id,
                subscription=sub,
                credit_state=credit_state,
                user_credits=user_credits
            )
            
            if credits_issued > 0:
                total_issued += credits_issued
                results.append({
                    "user_id": sub.user_id,
                    "credits_issued": credits_issued,
                    "new_balance": user_credits.balance
                })
        
        return {
            "success": True,
            "total_users_processed": len(active_subs),
            "total_credits_issued": total_issued,
            "details": results
        }
    
    finally:
        db.close()


@app.get("/api/credits/drip-status")
async def get_drip_status(current_user: User = Depends(get_current_user)):
    """Get the current credit drip status for the user."""
    from datetime import datetime, timezone
    from helpers.models import UserSubscription, CreditState, SessionLocal
    from helpers.credit_drip import get_plan_config, calculate_accrued_credits
    
    db = SessionLocal()
    try:
        sub = db.query(UserSubscription).filter_by(
            user_id=current_user.id,
            status="active"
        ).first()
        
        if not sub:
            return {
                "has_subscription": False,
                "message": "No active subscription"
            }
        
        credit_state = db.query(CreditState).filter_by(user_id=current_user.id).first()
        plan_config = get_plan_config(sub.package_id)
        
        if not plan_config or not sub.current_period_start or not sub.current_period_end:
            return {
                "has_subscription": True,
                "package_id": sub.package_id,
                "status": sub.status,
                "message": "Subscription active but period not set"
            }
        
        now = datetime.now(timezone.utc)
        period_start = sub.current_period_start
        period_end = sub.current_period_end
        if period_start.tzinfo is None:
            period_start = period_start.replace(tzinfo=timezone.utc)
        if period_end.tzinfo is None:
            period_end = period_end.replace(tzinfo=timezone.utc)
        
        period_total_seconds = (period_end - period_start).total_seconds()
        elapsed_seconds = (now - period_start).total_seconds()
        progress_percent = min(100, max(0, (elapsed_seconds / period_total_seconds) * 100)) if period_total_seconds > 0 else 0
        
        pending_credits, _, _ = calculate_accrued_credits(
            monthly_credits=plan_config["monthly_credits"],
            period_start=period_start,
            period_end=period_end,
            last_issued_at=credit_state.last_issued_at if credit_state else None,
            issuance_cursor=credit_state.issuance_cursor if credit_state else 0.0,
            current_time=now
        )
        
        return {
            "has_subscription": True,
            "package_id": sub.package_id,
            "package_name": CREDIT_PACKAGES.get(sub.package_id, {}).get("name", sub.package_id),
            "credits_per_period": plan_config["monthly_credits"],
            "status": sub.status,
            "cancel_at_period_end": sub.cancel_at_period_end,
            "current_period_start": period_start.isoformat(),
            "current_period_end": period_end.isoformat(),
            "period_progress_percent": round(progress_percent, 1),
            "pending_credits": pending_credits,
            "last_issued_at": credit_state.last_issued_at.isoformat() if credit_state and credit_state.last_issued_at else None
        }
    
    finally:
        db.close()


# ============== ADMIN ENDPOINTS ==============

from helpers.models import UserCredits

def require_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@app.get("/api/admin/users")
async def admin_list_users(current_user: User = Depends(require_admin)):
    db_session = SessionLocal()
    try:
        users = db_session.query(User).order_by(User.created_at.desc()).all()
        result = []
        for user in users:
            credits = db_session.query(UserCredits).filter_by(user_id=user.id).first()
            result.append({
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name or "",
                "is_admin": user.is_admin or False,
                "is_active": user.is_active,
                "credits": credits.balance if credits else 0,
                "created_at": user.created_at.isoformat() if user.created_at else None
            })
        return {"users": result}
    finally:
        db_session.close()


class AdminAddCreditsRequest(BaseModel):
    user_id: Any
    amount: Any
    reason: Optional[str] = "Admin credit adjustment"

    @validator('user_id', pre=True, always=True)
    def coerce_user_id(cls, v):
        return safe_int(v, default=0, min_val=1)

    @validator('amount', pre=True, always=True)
    def coerce_amount(cls, v):
        return safe_int(v, default=0, min_val=1, max_val=100000)


@app.post("/api/admin/credits/add")
async def admin_add_credits(request: AdminAddCreditsRequest, current_user: User = Depends(require_admin)):
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    db_session = SessionLocal()
    try:
        user = db_session.query(User).filter_by(id=request.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        credit_manager.add_credits(
            user_id=request.user_id,
            amount=request.amount,
            description=request.reason
        )
        
        credits = db_session.query(UserCredits).filter_by(user_id=request.user_id).first()
        new_balance = credits.balance if credits else 0
        
        return {
            "success": True,
            "message": f"Added {request.amount} credits to {user.email}",
            "new_balance": new_balance
        }
    finally:
        db_session.close()


class AdminToggleAdminRequest(BaseModel):
    user_id: int
    is_admin: bool


@app.post("/api/admin/toggle-admin")
async def admin_toggle_admin(request: AdminToggleAdminRequest, current_user: User = Depends(require_admin)):
    if request.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot modify your own admin status")
    
    db_session = SessionLocal()
    try:
        user = db_session.query(User).filter_by(id=request.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.is_admin = request.is_admin
        db_session.commit()
        
        return {
            "success": True,
            "message": f"{'Granted' if request.is_admin else 'Revoked'} admin for {user.email}"
        }
    finally:
        db_session.close()


import re

def validate_email_format(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

VALID_REFERRAL_SOURCES = ["reddit", "linkedin", "twitter", "friend", "google", "other"]

class WaitlistSignupRequest(BaseModel):
    email: str
    name: Optional[str] = None
    referral_source: Optional[str] = None

class WaitlistFoundingRequest(BaseModel):
    email: str
    name: Optional[str] = None
    referral_source: Optional[str] = None
    plan: str


@app.get("/api/waitlist/count")
async def waitlist_count():
    from helpers.waitlist import get_waitlist_count, get_free_spots_remaining, get_founding_count
    return {
        "total": get_waitlist_count(),
        "free_spots_remaining": get_free_spots_remaining(),
        "founding_count": get_founding_count()
    }


@app.post("/api/waitlist/signup")
async def waitlist_signup(request_data: WaitlistSignupRequest, request: Request, background_tasks: BackgroundTasks):
    from helpers.waitlist import add_to_waitlist, check_rate_limit, send_waitlist_email

    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Too many signups. Please try again later.")

    if not validate_email_format(request_data.email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    if request_data.referral_source and request_data.referral_source not in VALID_REFERRAL_SOURCES:
        request_data.referral_source = "other"

    result = add_to_waitlist(
        email=request_data.email,
        name=request_data.name,
        referral_source=request_data.referral_source,
        tier="free"
    )

    if "error" in result and result["error"] == "duplicate":
        return {
            "success": True,
            "message": "You're already on the waitlist!",
            "signup_number": result["signup_number"],
            "duplicate": True
        }

    background_tasks.add_task(
        send_waitlist_email,
        request_data.email,
        result["signup_number"],
        "free"
    )

    return {
        "success": True,
        "message": "You're on the waitlist!",
        "signup_number": result["signup_number"],
        "email": result["email"]
    }


@app.post("/api/waitlist/founding")
async def waitlist_founding(request_data: WaitlistFoundingRequest, request: Request, background_tasks: BackgroundTasks):
    from helpers.waitlist import add_to_waitlist, check_rate_limit, FOUNDING_PLANS, get_waitlist_entry_by_email
    from helpers.stripe_client import get_stripe_client

    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Too many signups. Please try again later.")

    if not validate_email_format(request_data.email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    if request_data.plan not in FOUNDING_PLANS:
        raise HTTPException(status_code=400, detail="Please select a valid plan.")

    existing = get_waitlist_entry_by_email(request_data.email)
    if existing and existing.get("paid"):
        return {
            "success": True,
            "message": "You're already a founding member!",
            "signup_number": existing["signup_number"],
            "duplicate": True
        }

    if not existing:
        result = add_to_waitlist(
            email=request_data.email,
            name=request_data.name,
            referral_source=request_data.referral_source,
            tier="founding",
            plan=request_data.plan
        )
        if "error" in result and result["error"] == "duplicate":
            pass

    plan_info = FOUNDING_PLANS[request_data.plan]
    client = await get_stripe_client()

    domain = os.environ.get("REPLIT_DOMAINS", "").split(",")[0]
    base_url = f"https://{domain}" if domain else "http://localhost:5000"

    try:
        session = client.checkout.sessions.create(params={
            "payment_method_types": ["card"],
            "line_items": [{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"LeadBlitz Founding Member - {plan_info['name']}",
                        "description": plan_info["description"],
                    },
                    "unit_amount": plan_info["price_cents"],
                },
                "quantity": 1,
            }],
            "mode": "payment",
            "success_url": f"{base_url}/waitlist/thankyou?email={request_data.email}&session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{base_url}/",
            "customer_email": request_data.email,
            "metadata": {
                "waitlist": "true",
                "tier": "founding",
                "plan": request_data.plan,
                "email": request_data.email,
                "name": request_data.name or ""
            }
        })

        return {
            "success": True,
            "checkout_url": session.url,
            "session_id": session.id
        }
    except Exception as e:
        logger_msg = f"Stripe checkout error: {e}"
        print(logger_msg)
        raise HTTPException(status_code=500, detail="Unable to start checkout. Please try again.")


@app.get("/waitlist/thankyou", response_class=HTMLResponse)
async def waitlist_thankyou(request: Request):
    with open("static/waitlist_thankyou.html", "r") as f:
        return inject_ga_into_html(f.read())


@app.get("/api/waitlist/entry")
async def waitlist_entry(email: str):
    from helpers.waitlist import get_waitlist_entry_by_email, generate_referral_code, get_free_spots_remaining, MAX_FREE_SPOTS
    entry = get_waitlist_entry_by_email(email)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    entry["referral_code"] = generate_referral_code(email)
    entry["first_100"] = entry["signup_number"] <= MAX_FREE_SPOTS
    entry["free_spots_remaining"] = get_free_spots_remaining()
    return entry


@app.post("/api/waitlist/confirm-payment")
async def confirm_waitlist_payment(request: Request, background_tasks: BackgroundTasks):
    from helpers.waitlist import update_waitlist_payment, send_waitlist_email
    body = await request.json()
    session_id = body.get("session_id")
    email = body.get("email")

    if not session_id or not email:
        raise HTTPException(status_code=400, detail="Missing session_id or email")

    result = update_waitlist_payment(session_id, email)
    if result:
        background_tasks.add_task(
            send_waitlist_email,
            email,
            result["signup_number"],
            "founding",
            result.get("plan")
        )
        return {"success": True, "signup_number": result["signup_number"]}

    raise HTTPException(status_code=404, detail="Waitlist entry not found")


class AdminWaitlistLogin(BaseModel):
    password: str

waitlist_admin_sessions = {}

@app.post("/api/admin/waitlist/login")
async def admin_waitlist_login(request_data: AdminWaitlistLogin, request: Request):
    admin_pw = os.environ.get("ADMIN_PASSWORD", "")
    if not admin_pw:
        raise HTTPException(status_code=500, detail="Admin access not configured")

    if request_data.password != admin_pw:
        raise HTTPException(status_code=401, detail="Invalid password")

    import secrets
    token = secrets.token_hex(32)
    waitlist_admin_sessions[token] = datetime.now()
    return {"success": True, "token": token}


def verify_waitlist_admin(request: Request):
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        if token in waitlist_admin_sessions:
            created = waitlist_admin_sessions[token]
            if datetime.now() - created < timedelta(hours=24):
                return True
    raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/admin/waitlist", response_class=HTMLResponse)
async def admin_waitlist_page():
    with open("static/admin_waitlist.html", "r") as f:
        return inject_ga_into_html(f.read())


@app.get("/api/admin/waitlist/stats")
async def admin_waitlist_stats(request: Request):
    verify_waitlist_admin(request)
    from helpers.waitlist import get_admin_stats
    return get_admin_stats()


@app.get("/api/admin/waitlist/list")
async def admin_waitlist_list(request: Request, search: Optional[str] = None,
                               sort_by: str = "created_at", sort_order: str = "desc"):
    verify_waitlist_admin(request)
    from helpers.waitlist import get_waitlist_entries
    return {"entries": get_waitlist_entries(search, sort_by, sort_order)}


class WaitlistNotesRequest(BaseModel):
    entry_id: int
    notes: str

@app.post("/api/admin/waitlist/notes")
async def admin_waitlist_notes(request_data: WaitlistNotesRequest, request: Request):
    verify_waitlist_admin(request)
    from helpers.waitlist import update_waitlist_notes
    success = update_waitlist_notes(request_data.entry_id, request_data.notes)
    if not success:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"success": True}


class WaitlistInviteRequest(BaseModel):
    entry_ids: List[int]

@app.post("/api/admin/waitlist/invite")
async def admin_waitlist_invite(request_data: WaitlistInviteRequest, request: Request):
    verify_waitlist_admin(request)
    from helpers.waitlist import mark_invited
    count = mark_invited(request_data.entry_ids)
    return {"success": True, "invited_count": count}


@app.get("/api/admin/waitlist/export")
async def admin_waitlist_export(request: Request):
    verify_waitlist_admin(request)
    from helpers.waitlist import get_waitlist_entries

    entries = get_waitlist_entries()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["#", "Email", "Name", "Source", "Tier", "Plan", "Paid", "Invited", "Date", "Notes"])
    for e in entries:
        writer.writerow([
            e["signup_number"], e["email"], e["name"] or "", e["referral_source"] or "",
            e["tier"], e["plan"] or "", e["paid"], e["invited"],
            e["created_at"] or "", e["notes"] or ""
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=waitlist_export.csv"}
    )


import resource
_startup_elapsed = time.time() - _app_start
_mem_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
print(f"[startup] App loaded in {_startup_elapsed:.2f}s, peak memory: {_mem_mb:.0f} MB")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
