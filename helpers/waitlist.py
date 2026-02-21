import os
import hashlib
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from threading import Lock
from typing import Optional, Dict, Any

from helpers.models import SessionLocal, Waitlist
from helpers.system_email import send_system_email, build_branded_email, get_app_base_url
from sqlalchemy import func

logger = logging.getLogger(__name__)

FOUNDING_PLANS = {
    "starter": {
        "name": "Starter",
        "price_cents": 750,
        "display_price": "$7.50/mo",
        "description": "LeadBlitz Founding Member - Starter (50% off first 3 months)"
    },
    "pro": {
        "name": "Pro",
        "price_cents": 2950,
        "display_price": "$29.50/mo",
        "description": "LeadBlitz Founding Member - Pro (50% off first 3 months)"
    },
    "agency": {
        "name": "Agency",
        "price_cents": 9950,
        "display_price": "$99.50/mo",
        "description": "LeadBlitz Founding Member - Agency (50% off first 3 months)"
    }
}

MAX_FREE_SPOTS = 100

rate_limit_store: Dict[str, list] = defaultdict(list)
rate_limit_lock = Lock()


def check_rate_limit(ip: str, max_requests: int = 5, window_seconds: int = 3600) -> bool:
    now = datetime.now()
    cutoff = now - timedelta(seconds=window_seconds)

    with rate_limit_lock:
        rate_limit_store[ip] = [t for t in rate_limit_store[ip] if t > cutoff]
        if len(rate_limit_store[ip]) >= max_requests:
            return False
        rate_limit_store[ip].append(now)
        return True


def get_waitlist_count() -> int:
    session = SessionLocal()
    try:
        return session.query(func.count(Waitlist.id)).scalar() or 0
    finally:
        session.close()


def get_free_spots_remaining() -> int:
    session = SessionLocal()
    try:
        free_count = session.query(func.count(Waitlist.id)).filter(
            Waitlist.tier == "free"
        ).scalar() or 0
        return max(0, MAX_FREE_SPOTS - free_count)
    finally:
        session.close()


def get_founding_count() -> int:
    session = SessionLocal()
    try:
        return session.query(func.count(Waitlist.id)).filter(
            Waitlist.tier == "founding",
            Waitlist.paid == True
        ).scalar() or 0
    finally:
        session.close()


def add_to_waitlist(email: str, name: Optional[str], referral_source: Optional[str],
                    tier: str = "free", plan: Optional[str] = None) -> Dict[str, Any]:
    session = SessionLocal()
    try:
        existing = session.query(Waitlist).filter(
            func.lower(Waitlist.email) == email.lower().strip()
        ).first()
        if existing:
            return {"error": "duplicate", "signup_number": existing.signup_number}

        max_num = session.query(func.max(Waitlist.signup_number)).scalar() or 0
        signup_number = max_num + 1

        entry = Waitlist(
            email=email.strip().lower(),
            name=name.strip() if name else None,
            referral_source=referral_source,
            signup_number=signup_number,
            tier=tier,
            plan=plan,
            confirmed=True if tier == "free" else False
        )
        session.add(entry)
        session.commit()

        return {
            "success": True,
            "signup_number": signup_number,
            "id": entry.id,
            "tier": tier,
            "email": entry.email
        }
    except Exception as e:
        session.rollback()
        logger.error(f"Error adding to waitlist: {e}")
        raise
    finally:
        session.close()


def update_waitlist_payment(stripe_session_id: str, email: str) -> Optional[Dict]:
    session = SessionLocal()
    try:
        entry = session.query(Waitlist).filter(
            func.lower(Waitlist.email) == email.lower()
        ).first()
        if entry:
            entry.stripe_session_id = stripe_session_id
            entry.paid = True
            entry.confirmed = True
            session.commit()
            return {
                "signup_number": entry.signup_number,
                "tier": entry.tier,
                "plan": entry.plan,
                "email": entry.email
            }
        return None
    finally:
        session.close()


def get_waitlist_entry_by_email(email: str) -> Optional[Dict]:
    session = SessionLocal()
    try:
        entry = session.query(Waitlist).filter(
            func.lower(Waitlist.email) == email.lower()
        ).first()
        if entry:
            return {
                "id": entry.id,
                "email": entry.email,
                "name": entry.name,
                "signup_number": entry.signup_number,
                "tier": entry.tier,
                "plan": entry.plan,
                "paid": entry.paid,
                "created_at": entry.created_at.isoformat() if entry.created_at else None
            }
        return None
    finally:
        session.close()


def generate_referral_code(email: str) -> str:
    return hashlib.md5(email.lower().encode()).hexdigest()[:10]


def get_admin_stats() -> Dict:
    session = SessionLocal()
    try:
        total = session.query(func.count(Waitlist.id)).scalar() or 0
        founding = session.query(func.count(Waitlist.id)).filter(
            Waitlist.tier == "founding", Waitlist.paid == True
        ).scalar() or 0
        free_count = session.query(func.count(Waitlist.id)).filter(
            Waitlist.tier == "free"
        ).scalar() or 0

        revenue_result = session.query(Waitlist).filter(
            Waitlist.tier == "founding", Waitlist.paid == True
        ).all()
        revenue = 0
        for entry in revenue_result:
            if entry.plan and entry.plan in FOUNDING_PLANS:
                revenue += FOUNDING_PLANS[entry.plan]["price_cents"]

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        signups_today = session.query(func.count(Waitlist.id)).filter(
            Waitlist.created_at >= today
        ).scalar() or 0
        signups_week = session.query(func.count(Waitlist.id)).filter(
            Waitlist.created_at >= week_ago
        ).scalar() or 0

        sources = session.query(
            Waitlist.referral_source,
            func.count(Waitlist.id)
        ).filter(
            Waitlist.referral_source.isnot(None)
        ).group_by(Waitlist.referral_source).order_by(
            func.count(Waitlist.id).desc()
        ).limit(10).all()

        return {
            "total_signups": total,
            "founding_members": founding,
            "free_signups": free_count,
            "revenue_cents": revenue,
            "revenue_display": f"${revenue / 100:.2f}",
            "free_spots_remaining": max(0, MAX_FREE_SPOTS - free_count),
            "signups_today": signups_today,
            "signups_week": signups_week,
            "top_sources": [{"source": s or "Unknown", "count": c} for s, c in sources]
        }
    finally:
        session.close()


def get_waitlist_entries(search: Optional[str] = None, sort_by: str = "created_at",
                        sort_order: str = "desc") -> list:
    session = SessionLocal()
    try:
        query = session.query(Waitlist)
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Waitlist.email.ilike(search_term)) |
                (Waitlist.name.ilike(search_term))
            )

        sort_col = getattr(Waitlist, sort_by, Waitlist.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())

        entries = query.all()
        return [{
            "id": e.id,
            "signup_number": e.signup_number,
            "email": e.email,
            "name": e.name,
            "referral_source": e.referral_source,
            "tier": e.tier,
            "plan": e.plan,
            "paid": e.paid,
            "confirmed": e.confirmed,
            "invited": e.invited,
            "invited_at": e.invited_at.isoformat() if e.invited_at else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "notes": e.notes,
            "unsubscribed": e.unsubscribed
        } for e in entries]
    finally:
        session.close()


def update_waitlist_notes(entry_id: int, notes: str) -> bool:
    session = SessionLocal()
    try:
        entry = session.query(Waitlist).filter_by(id=entry_id).first()
        if entry:
            entry.notes = notes
            session.commit()
            return True
        return False
    finally:
        session.close()


def mark_invited(entry_ids: list) -> int:
    session = SessionLocal()
    try:
        count = 0
        for eid in entry_ids:
            entry = session.query(Waitlist).filter_by(id=eid).first()
            if entry and not entry.invited:
                entry.invited = True
                entry.invited_at = datetime.now()
                count += 1
        session.commit()
        return count
    finally:
        session.close()


def send_waitlist_email(email: str, signup_number: int, tier: str,
                        plan: Optional[str] = None, credits: int = 500):
    try:
        subject = "You're on the LeadBlitz Waitlist!"
        referral_code = generate_referral_code(email)
        base_url = get_app_base_url()
        referral_url = f"{base_url}/?ref={referral_code}"

        if tier == "founding":
            subject = "Welcome, Founding Member! You're In!"
            plan_name = FOUNDING_PLANS.get(plan, {}).get("name", "Founding Member")
            body_content = f"""
                <p>You're <strong>#{signup_number}</strong> on the LeadBlitz waitlist.</p>
                <p>As a <strong>{plan_name} Founding Member</strong>, here's what you're getting:</p>
                <ul style="line-height: 2;">
                    <li><strong>1,000 free bonus credits</strong> at launch</li>
                    <li><strong>50% off</strong> your first 3 months</li>
                    <li><strong>Founding Member</strong> badge permanently on your account</li>
                    <li><strong>Priority access</strong> before free waitlist members</li>
                </ul>
                <p>We'll email you as soon as early access opens. You'll be among the first to know.</p>
            """
        else:
            first_100_perk = "<p>You're in the <strong>first 100</strong>! You'll receive <strong>500 free credits</strong> when we launch.</p>" if signup_number <= MAX_FREE_SPOTS else ""
            body_content = f"""
                <p>You're <strong>#{signup_number}</strong> on the LeadBlitz waitlist.</p>
                {first_100_perk}
                <p>We'll email you as soon as early access opens.</p>
            """

        html_body = build_branded_email(
            heading="Welcome to the Waitlist!" if tier == "free" else "Welcome, Founding Member!",
            body_content=body_content,
            button_text="Share & Move Up the List",
            button_url=referral_url,
            footer_note="Share your referral link with friends to move up the waitlist."
        )

        sent = send_system_email(to_email=email, subject=subject, html_body=html_body)
        if sent:
            logger.info(f"Waitlist email sent to {email}")
        else:
            logger.info(f"SMTP not configured, skipping waitlist email to {email}")
    except Exception as e:
        logger.error(f"Failed to send waitlist email to {email}: {e}")
