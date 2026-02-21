import os
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, JSON, Text, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, default="")
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    completed_tutorial = Column(Boolean, default=False)
    active_campaign_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    reset_token = Column(String, nullable=True)
    reset_token_expiry = Column(DateTime, nullable=True)
    
    campaigns = relationship("Campaign", back_populates="user", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("UserAPIKeys", back_populates="user", uselist=False, cascade="all, delete-orphan")
    email_settings = relationship("EmailSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    credits = relationship("UserCredits", back_populates="user", uselist=False, cascade="all, delete-orphan")
    credit_transactions = relationship("CreditTransaction", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("UserSubscription", back_populates="user", cascade="all, delete-orphan")
    email_signature = relationship("EmailSignature", back_populates="user", uselist=False, cascade="all, delete-orphan")
    credit_state = relationship("CreditState", back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserAPIKeys(Base):
    __tablename__ = "user_api_keys"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    twilio_account_sid = Column(String, nullable=True)
    twilio_auth_token = Column(String, nullable=True)
    twilio_phone_number = Column(String, nullable=True)
    
    hunter_api_key = Column(String, nullable=True)
    
    sendgrid_api_key = Column(String, nullable=True)
    from_email = Column(String, nullable=True)
    
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    user = relationship("User", back_populates="api_keys")


class EmailSignature(Base):
    """User email signature and email preferences."""
    __tablename__ = "email_signatures"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    full_name = Column(String, nullable=True)
    position = Column(String, nullable=True)
    company_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    website = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    disclaimer = Column(Text, nullable=True)
    custom_signature = Column(Text, nullable=True)  # Full custom HTML/text signature
    use_custom = Column(Boolean, default=False)  # Whether to use custom signature instead of built
    base_pitch = Column(Text, nullable=True)  # Saved base pitch for AI email generation
    
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    user = relationship("User", back_populates="email_signature")


class EmailTemplate(Base):
    """User-saved email templates for reuse."""
    __tablename__ = "email_templates"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    name = Column(String, nullable=False)
    subject = Column(String, nullable=True)
    body = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    user = relationship("User", backref="email_templates")
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "subject": self.subject,
            "body": self.body,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class EmailSettings(Base):
    __tablename__ = "email_settings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    provider = Column(String, default="none", nullable=False)
    
    gmail_access_token = Column(Text, nullable=True)
    gmail_refresh_token = Column(Text, nullable=True)
    gmail_token_expiry = Column(DateTime, nullable=True)
    gmail_email_address = Column(String, nullable=True)
    
    outlook_access_token = Column(Text, nullable=True)
    outlook_refresh_token = Column(Text, nullable=True)
    outlook_token_expiry = Column(DateTime, nullable=True)
    outlook_email_address = Column(String, nullable=True)
    
    smtp_host = Column(String, nullable=True)
    smtp_port = Column(Integer, nullable=True)
    smtp_username = Column(String, nullable=True)
    smtp_password_encrypted = Column(Text, nullable=True)
    smtp_from_email = Column(String, nullable=True)
    smtp_use_tls = Column(Boolean, default=True)
    
    sendgrid_api_key_encrypted = Column(Text, nullable=True)
    sendgrid_from_email = Column(String, nullable=True)
    
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    user = relationship("User", back_populates="email_settings")


class GlobalOAuthSettings(Base):
    __tablename__ = "global_oauth_settings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    gmail_client_id = Column(String, nullable=True)
    gmail_client_secret_encrypted = Column(Text, nullable=True)
    gmail_redirect_uri = Column(String, nullable=True)
    gmail_configured = Column(Boolean, default=False)
    
    outlook_client_id = Column(String, nullable=True)
    outlook_client_secret_encrypted = Column(Text, nullable=True)
    outlook_redirect_uri = Column(String, nullable=True)
    outlook_configured = Column(Boolean, default=False)
    
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    business_type = Column(String, nullable=False)
    location = Column(String, nullable=False)
    lead_ids = Column(JSON, default=list)
    next_page_token = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    user = relationship("User", back_populates="campaigns")


class Lead(Base):
    __tablename__ = "leads"
    
    id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    contact_name = Column(String, default="")  # Name of person to contact
    address = Column(String, default="")
    phone = Column(String, default="")
    website = Column(String, default="")
    email = Column(String, default="")
    score = Column(Integer, default=0)
    score_reasoning = Column(JSON, nullable=True)
    stage = Column(String, default="New")
    notes = Column(Text, default="")
    rating = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    email_source = Column(String, nullable=True)
    email_confidence = Column(Float, nullable=True)
    email_candidates = Column(JSON, default=list)
    
    heuristic_score = Column(Integer, nullable=True)
    ai_score = Column(Integer, nullable=True)
    score_breakdown = Column(JSON, nullable=True)
    score_confidence = Column(Float, nullable=True)
    last_scored_at = Column(DateTime, nullable=True)
    
    render_pathway = Column(String, nullable=True)
    js_detected = Column(Boolean, default=False)
    js_confidence = Column(Float, nullable=True)
    framework_hints = Column(JSON, nullable=True)
    technographics = Column(JSON, nullable=True)
    
    source = Column(String, default="search")
    import_id = Column(String, ForeignKey("csv_imports.id"), nullable=True)
    import_status = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    user = relationship("User", back_populates="leads")
    csv_import = relationship("CsvImport", back_populates="leads")


class CsvImport(Base):
    __tablename__ = "csv_imports"
    
    id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String, nullable=True)
    total_rows = Column(Integer, default=0)
    to_score = Column(Integer, default=0)
    scored_count = Column(Integer, default=0)
    unreachable_count = Column(Integer, default=0)
    pending_count = Column(Integer, default=0)
    pending_credits_count = Column(Integer, default=0)
    skipped_duplicate = Column(Integer, default=0)
    skipped_no_url = Column(Integer, default=0)
    skipped_invalid = Column(Integer, default=0)
    status = Column(String, default="in_progress")
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    
    user = relationship("User", backref="csv_imports")
    leads = relationship("Lead", back_populates="csv_import")


class ScoreCache(Base):
    __tablename__ = "score_cache"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    url_hash = Column(String, unique=True, nullable=False, index=True)
    normalized_url = Column(String, nullable=False)
    
    heuristic_result = Column(JSON, nullable=True)
    ai_result = Column(JSON, nullable=True)
    final_score = Column(Integer, nullable=False)
    confidence = Column(Float, nullable=False)
    
    render_pathway = Column(String, nullable=True)
    js_detected = Column(Boolean, default=False)
    js_confidence = Column(Float, nullable=True)
    detection_signals = Column(JSON, nullable=True)
    framework_hints = Column(JSON, nullable=True)
    
    has_errors = Column(Boolean, default=False)
    error_messages = Column(JSON, nullable=True)
    
    fetched_at = Column(DateTime, default=datetime.now, nullable=False)
    created_at = Column(DateTime, default=datetime.now)


class GlobalState(Base):
    __tablename__ = "global_state"
    
    id = Column(Integer, primary_key=True)
    emails_sent_count = Column(Integer, default=0)
    sms_sent_count = Column(Integer, default=0)
    active_campaign_id = Column(String, nullable=True)


class UserCredits(Base):
    """User credit balance tracking."""
    __tablename__ = "user_credits"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    balance = Column(Integer, default=0, nullable=False)
    total_purchased = Column(Integer, default=0, nullable=False)
    total_used = Column(Integer, default=0, nullable=False)
    stripe_customer_id = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    user = relationship("User", back_populates="credits")


class UserSubscription(Base):
    """User subscription tracking with credit drip support."""
    __tablename__ = "user_subscriptions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stripe_subscription_id = Column(String, unique=True, nullable=False)
    package_id = Column(String, nullable=False)
    credits_per_period = Column(Integer, nullable=False)
    status = Column(String, default="active", nullable=False)
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    canceled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    user = relationship("User", back_populates="subscriptions")


class CreditTransaction(Base):
    """Credit transaction history with idempotency support."""
    __tablename__ = "credit_transactions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    transaction_type = Column(String, nullable=False)
    description = Column(String, nullable=True)
    stripe_payment_intent_id = Column(String, nullable=True)
    stripe_checkout_session_id = Column(String, nullable=True)
    stripe_event_id = Column(String, nullable=True, unique=True, index=True)
    balance_after = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    user = relationship("User", back_populates="credit_transactions")


class CreditState(Base):
    """Credit drip state tracking for progressive credit issuance."""
    __tablename__ = "credit_states"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    last_issued_at = Column(DateTime, nullable=True)
    issuance_cursor = Column(Float, default=0.0, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    user = relationship("User", back_populates="credit_state")


class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    stripe_session_id = Column(String, unique=True, nullable=True)
    stripe_payment_intent = Column(String, nullable=True)
    amount_cents = Column(Integer, nullable=False)
    credits_purchased = Column(Integer, nullable=False)
    plan_name = Column(String, nullable=False)
    status = Column(String, default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    user = relationship("User", backref="payments")


class FoundingMemberCounter(Base):
    __tablename__ = "founding_member_counter"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    count = Column(Integer, default=0, nullable=False)
    max_slots = Column(Integer, default=100, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Waitlist(Base):
    __tablename__ = "waitlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    referral_source = Column(String, nullable=True)
    signup_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    confirmed = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    tier = Column(String, default="free")
    plan = Column(String, nullable=True)
    stripe_session_id = Column(String, nullable=True)
    paid = Column(Boolean, default=False)
    unsubscribed = Column(Boolean, default=False)
    invited = Column(Boolean, default=False)
    invited_at = Column(DateTime, nullable=True)


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,
    max_overflow=20,
    connect_args={"connect_timeout": 10}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)
    
def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
