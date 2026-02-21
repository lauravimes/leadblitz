"""
Credit Drip System - Weekly batch credit issuance for subscription plans.

Credits are issued in 4 weekly batches (25% each):
- Week 0 (immediately): 25%
- Week 1 (day 7): 25%
- Week 2 (day 14): 25%
- Week 3 (day 21): 25%

This prevents abuse where users subscribe, receive all credits, then cancel.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

PLAN_CONFIG = {
    "starter_monthly": {
        "monthly_credits": 250,
        "price_cents": 999,
    },
    "professional_monthly": {
        "monthly_credits": 1000,
        "price_cents": 3999,
    },
    "enterprise_monthly": {
        "monthly_credits": 5000,
        "price_cents": 12999,
    },
}

TOPUP_PACKS = {
    "credits_100": {"credits": 100, "price_cents": 719},
    "credits_500": {"credits": 500, "price_cents": 2879},
    "credits_2000": {"credits": 2000, "price_cents": 9359},
}

WEEK_DAYS = [0, 7, 14, 21]


def get_plan_config(package_id: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a plan."""
    return PLAN_CONFIG.get(package_id)


def calculate_weekly_credits(monthly_credits: int) -> list:
    """
    Calculate credits for each weekly batch (25% each).
    Returns list of 4 credit amounts that sum to monthly_credits.
    """
    base_amount = monthly_credits // 4
    remainder = monthly_credits % 4
    
    batches = [base_amount] * 4
    for i in range(remainder):
        batches[i] += 1
    
    return batches


def get_current_week(period_start: datetime, current_time: datetime) -> int:
    """
    Determine which week we're in (0-3) based on days since period start.
    Week 0: days 0-6 (but credits issued immediately)
    Week 1: days 7-13
    Week 2: days 14-20
    Week 3: days 21+
    """
    if period_start.tzinfo is None:
        period_start = period_start.replace(tzinfo=timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    
    days_elapsed = (current_time - period_start).days
    
    if days_elapsed >= 21:
        return 3
    elif days_elapsed >= 14:
        return 2
    elif days_elapsed >= 7:
        return 1
    else:
        return 0


def calculate_credits_due(
    monthly_credits: int,
    period_start: datetime,
    current_time: datetime,
    weeks_issued: int
) -> Tuple[int, int]:
    """
    Calculate credits due based on current week vs weeks already issued.
    
    Args:
        monthly_credits: Total credits for the billing period
        period_start: Start of billing period
        current_time: Current time
        weeks_issued: Number of weekly batches already issued (0-4)
    
    Returns:
        Tuple of (credits_to_issue, new_weeks_issued)
    """
    if weeks_issued >= 4:
        return 0, 4
    
    current_week = get_current_week(period_start, current_time)
    weeks_to_issue_through = current_week + 1
    
    if weeks_to_issue_through <= weeks_issued:
        return 0, weeks_issued
    
    weekly_batches = calculate_weekly_credits(monthly_credits)
    
    credits_to_issue = sum(weekly_batches[weeks_issued:weeks_to_issue_through])
    
    return credits_to_issue, weeks_to_issue_through


def issue_credits_for_user(
    db: Session,
    user_id: int,
    subscription: Any,
    credit_state: Any,
    user_credits: Any,
    current_time: Optional[datetime] = None
) -> int:
    """
    Issue weekly batch credits for a user with an active subscription.
    
    Returns the number of credits issued.
    """
    from helpers.models import CreditTransaction
    
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    
    if subscription.status not in ("active", "canceling"):
        return 0
    
    if not subscription.current_period_start or not subscription.current_period_end:
        return 0
    
    period_start = subscription.current_period_start
    period_end = subscription.current_period_end
    if period_start.tzinfo is None:
        period_start = period_start.replace(tzinfo=timezone.utc)
    if period_end.tzinfo is None:
        period_end = period_end.replace(tzinfo=timezone.utc)
    
    if current_time > period_end:
        return 0
    
    plan_config = get_plan_config(subscription.package_id)
    if not plan_config:
        return 0
    
    monthly_credits = plan_config["monthly_credits"]
    weeks_issued = int(credit_state.issuance_cursor or 0)
    
    credits_to_issue, new_weeks_issued = calculate_credits_due(
        monthly_credits=monthly_credits,
        period_start=period_start,
        current_time=current_time,
        weeks_issued=weeks_issued
    )
    
    if credits_to_issue > 0:
        user_credits.balance += credits_to_issue
        new_balance = user_credits.balance
        
        week_label = f"week {new_weeks_issued}" if new_weeks_issued <= 3 else "final batch"
        transaction = CreditTransaction(
            user_id=user_id,
            amount=credits_to_issue,
            transaction_type="subscription_accrual",
            description=f"Weekly credit batch: {credits_to_issue} credits ({week_label})",
            balance_after=new_balance
        )
        db.add(transaction)
    
    credit_state.last_issued_at = current_time
    credit_state.issuance_cursor = float(new_weeks_issued)
    credit_state.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    
    return credits_to_issue


def issue_initial_credits(
    db: Session,
    user_id: int,
    package_id: str
) -> int:
    """
    Issue the initial 25% of credits immediately when a subscription starts.
    This should be called from the webhook when a new subscription is created.
    
    Returns the number of credits issued.
    """
    from helpers.models import UserCredits, CreditTransaction, CreditState
    
    plan_config = get_plan_config(package_id)
    if not plan_config:
        return 0
    
    monthly_credits = plan_config["monthly_credits"]
    weekly_batches = calculate_weekly_credits(monthly_credits)
    initial_credits = weekly_batches[0]
    
    user_credits = db.query(UserCredits).filter_by(user_id=user_id).first()
    if not user_credits:
        user_credits = UserCredits(user_id=user_id, balance=0)
        db.add(user_credits)
        db.flush()
    
    user_credits.balance += initial_credits
    new_balance = user_credits.balance
    
    transaction = CreditTransaction(
        user_id=user_id,
        amount=initial_credits,
        transaction_type="subscription_accrual",
        description=f"Initial subscription credits: {initial_credits} credits (25%)",
        balance_after=new_balance
    )
    db.add(transaction)
    
    credit_state = db.query(CreditState).filter_by(user_id=user_id).first()
    if credit_state:
        credit_state.last_issued_at = datetime.now(timezone.utc)
        credit_state.issuance_cursor = 1.0
        credit_state.updated_at = datetime.now(timezone.utc)
    else:
        credit_state = CreditState(
            user_id=user_id,
            last_issued_at=datetime.now(timezone.utc),
            issuance_cursor=1.0
        )
        db.add(credit_state)
    
    db.commit()
    
    return initial_credits


def has_active_subscription(db: Session, user_id: int) -> bool:
    """Check if user has an active subscription."""
    from helpers.models import UserSubscription
    
    sub = db.query(UserSubscription).filter_by(
        user_id=user_id,
        status="active"
    ).first()
    
    return sub is not None


def reset_credit_state_for_new_period(
    db: Session,
    user_id: int,
    new_period_start: datetime
) -> None:
    """Reset credit state when a new billing period starts."""
    from helpers.models import CreditState
    
    credit_state = db.query(CreditState).filter_by(user_id=user_id).first()
    if credit_state:
        credit_state.last_issued_at = new_period_start
        credit_state.issuance_cursor = 0.0
        credit_state.updated_at = datetime.now(timezone.utc)
    else:
        credit_state = CreditState(
            user_id=user_id,
            last_issued_at=new_period_start,
            issuance_cursor=0.0
        )
        db.add(credit_state)
    
    db.commit()


def get_or_create_credit_state(db: Session, user_id: int) -> Any:
    """Get or create credit state for a user."""
    from helpers.models import CreditState
    
    credit_state = db.query(CreditState).filter_by(user_id=user_id).first()
    if not credit_state:
        credit_state = CreditState(
            user_id=user_id,
            last_issued_at=None,
            issuance_cursor=0.0
        )
        db.add(credit_state)
        db.commit()
    
    return credit_state
