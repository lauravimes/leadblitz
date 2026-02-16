from datetime import datetime
from typing import Optional, Dict, List, Tuple
from sqlalchemy.orm import Session

from helpers.models import (
    UserCredits,
    CreditTransaction,
    User as UserModel,
    SessionLocal
)
from helpers.stripe_client import CREDIT_COSTS, CREDIT_PACKAGES


class CreditManager:
    
    def _get_session(self) -> Session:
        return SessionLocal()
    
    def get_user_credits(self, user_id: int) -> Dict:
        session = self._get_session()
        try:
            credits = session.query(UserCredits).filter_by(user_id=user_id).first()
            if not credits:
                credits = UserCredits(user_id=user_id, balance=0)
                session.add(credits)
                session.commit()
                session.refresh(credits)
            
            return {
                "balance": credits.balance,
                "total_purchased": credits.total_purchased,
                "total_used": credits.total_used,
                "stripe_customer_id": credits.stripe_customer_id
            }
        finally:
            session.close()
    
    def get_balance(self, user_id: int) -> int:
        return int(self.get_user_credits(user_id)["balance"] or 0)
    
    def has_sufficient_credits(self, user_id: int, action: str, count: int = 1) -> Tuple[bool, int, int]:
        cost = CREDIT_COSTS.get(action, 0) * count
        balance = self.get_balance(user_id)
        return balance >= cost, balance, cost
    
    def deduct_credits(
        self,
        user_id: int,
        action: str,
        count: int = 1,
        description: Optional[str] = None
    ) -> Tuple[bool, int]:
        cost = CREDIT_COSTS.get(action, 0) * count
        if cost == 0:
            return True, self.get_balance(user_id)
        
        session = self._get_session()
        try:
            credits = session.query(UserCredits).filter_by(user_id=user_id).with_for_update().first()
            if not credits:
                credits = UserCredits(user_id=user_id, balance=0)
                session.add(credits)
                session.flush()
            
            balance = int(credits.balance or 0)
            if balance < cost:
                return False, balance
            
            credits.balance = balance - cost
            credits.total_used = int(credits.total_used or 0) + cost
            new_balance = credits.balance
            
            transaction = CreditTransaction(
                user_id=user_id,
                amount=-cost,
                transaction_type="usage",
                description=description or f"{action} x{count}",
                balance_after=new_balance
            )
            session.add(transaction)
            session.commit()
            
            return True, new_balance
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def add_credits(
        self,
        user_id: int,
        amount: int,
        description: str,
        stripe_payment_intent_id: Optional[str] = None,
        stripe_checkout_session_id: Optional[str] = None
    ) -> int:
        session = self._get_session()
        try:
            credits = session.query(UserCredits).filter_by(user_id=user_id).with_for_update().first()
            if not credits:
                credits = UserCredits(user_id=user_id, balance=0)
                session.add(credits)
                session.flush()
            
            credits.balance = int(credits.balance or 0) + amount
            credits.total_purchased = int(credits.total_purchased or 0) + amount
            new_balance = credits.balance
            
            transaction = CreditTransaction(
                user_id=user_id,
                amount=amount,
                transaction_type="purchase",
                description=description,
                stripe_payment_intent_id=stripe_payment_intent_id,
                stripe_checkout_session_id=stripe_checkout_session_id,
                balance_after=new_balance
            )
            session.add(transaction)
            session.commit()
            
            return new_balance
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def set_stripe_customer_id(self, user_id: int, stripe_customer_id: str):
        session = self._get_session()
        try:
            credits = session.query(UserCredits).filter_by(user_id=user_id).first()
            if not credits:
                credits = UserCredits(user_id=user_id, balance=0, stripe_customer_id=stripe_customer_id)
                session.add(credits)
            else:
                credits.stripe_customer_id = stripe_customer_id
            session.commit()
        finally:
            session.close()
    
    def get_transaction_history(self, user_id: int, limit: int = 50) -> List[Dict]:
        session = self._get_session()
        try:
            transactions = session.query(CreditTransaction).filter_by(
                user_id=user_id
            ).order_by(
                CreditTransaction.created_at.desc()
            ).limit(limit).all()
            
            return [
                {
                    "id": t.id,
                    "amount": t.amount,
                    "type": t.transaction_type,
                    "description": t.description,
                    "balance_after": t.balance_after,
                    "created_at": t.created_at.isoformat()
                }
                for t in transactions
            ]
        finally:
            session.close()
    
    def check_duplicate_session(self, checkout_session_id: str) -> bool:
        session = self._get_session()
        try:
            existing = session.query(CreditTransaction).filter_by(
                stripe_checkout_session_id=checkout_session_id
            ).first()
            return existing is not None
        finally:
            session.close()


credit_manager = CreditManager()
