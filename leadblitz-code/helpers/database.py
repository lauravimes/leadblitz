import uuid
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from helpers.models import (
    Campaign as CampaignModel,
    Lead as LeadModel,
    User as UserModel,
    GlobalState as GlobalStateModel,
    GlobalOAuthSettings as GlobalOAuthSettingsModel,
    SessionLocal,
    init_db
)

# Initialize database tables
init_db()


class Campaign:
    """Campaign object that wraps SQLAlchemy model."""
    
    def __init__(
        self,
        business_type: str,
        location: str,
        lead_ids: Optional[List[str]] = None,
        next_page_token: Optional[str] = None,
        id: Optional[str] = None,
        created_at: Optional[datetime] = None
    ):
        self.id = id or str(uuid.uuid4())
        self.business_type = business_type
        self.location = location
        self.lead_ids = lead_ids or []
        self.next_page_token = next_page_token
        self.created_at = created_at or datetime.now()
        self.name = f"{business_type} in {location}"
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "business_type": self.business_type,
            "location": self.location,
            "lead_count": len(self.lead_ids),
            "lead_ids": self.lead_ids,
            "next_page_token": self.next_page_token,
            "has_more": self.next_page_token is not None,
            "created_at": self.created_at.isoformat()
        }
    
    def add_lead(self, lead_id: str):
        if lead_id not in self.lead_ids:
            self.lead_ids.append(lead_id)
    
    @classmethod
    def from_model(cls, model: CampaignModel) -> 'Campaign':
        """Create Campaign from SQLAlchemy model."""
        return cls(
            id=model.id,
            business_type=model.business_type,
            location=model.location,
            lead_ids=model.lead_ids or [],
            next_page_token=model.next_page_token,
            created_at=model.created_at
        )
    
    def to_model(self, user_id: int) -> CampaignModel:
        """Convert to SQLAlchemy model."""
        return CampaignModel(
            id=self.id,
            user_id=user_id,
            name=self.name,
            business_type=self.business_type,
            location=self.location,
            lead_ids=self.lead_ids,
            next_page_token=self.next_page_token,
            created_at=self.created_at
        )


class Lead:
    """Lead object that wraps SQLAlchemy model."""
    
    def __init__(
        self,
        name: str,
        contact_name: str = "",
        address: str = "",
        phone: str = "",
        website: str = "",
        email: str = "",
        score: int = 0,
        score_reasoning: Optional[Dict] = None,
        stage: str = "New",
        notes: str = "",
        rating: float = 0.0,
        review_count: int = 0,
        email_source: Optional[str] = None,
        email_confidence: Optional[float] = None,
        email_candidates: Optional[List[str]] = None,
        id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        last_scored_at: Optional[datetime] = None,
        heuristic_score: Optional[int] = None,
        ai_score: Optional[int] = None,
        score_breakdown: Optional[Dict] = None,
        score_confidence: Optional[float] = None,
        technographics: Optional[Dict] = None,
        source: str = "search",
        import_id: Optional[str] = None,
        import_status: Optional[str] = None
    ):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.contact_name = contact_name
        self.address = address
        self.phone = phone
        self.website = website
        self.email = email
        self.score = score
        self.score_reasoning = score_reasoning
        self.stage = stage
        self.notes = notes
        self.rating = rating
        self.review_count = review_count
        self.email_source = email_source
        self.email_confidence = email_confidence
        self.email_candidates = email_candidates if email_candidates is not None else []
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.last_scored_at = last_scored_at
        self.heuristic_score = heuristic_score
        self.ai_score = ai_score
        self.score_breakdown = score_breakdown
        self.score_confidence = score_confidence
        self.technographics = technographics
        self.source = source
        self.import_id = import_id
        self.import_status = import_status

    def to_dict(self) -> Dict:
        score_status = "not_scored"
        score_fail_reason = None
        
        reasoning = self.score_reasoning
        if isinstance(reasoning, str):
            try:
                import json
                reasoning = json.loads(reasoning)
            except (ValueError, TypeError):
                reasoning = None
        
        if hasattr(self, 'last_scored_at') and self.last_scored_at is not None:
            score_status = "scored"
        elif self.score is not None and self.score > 0 and reasoning is not None:
            score_status = "scored"
        elif reasoning is not None:
            is_bot = isinstance(reasoning, dict) and reasoning.get("bot_blocked")
            if is_bot:
                score_status = "bot_protected"
                score_fail_reason = "Website has advanced security that blocks automated access"
            else:
                score_status = "failed"
                if isinstance(reasoning, dict):
                    score_fail_reason = reasoning.get("fetch_error") or reasoning.get("error") or "Scoring could not complete successfully"
                else:
                    score_fail_reason = "Scoring could not complete successfully"

        result = {
            "id": self.id,
            "name": self.name,
            "contact_name": self.contact_name,
            "address": self.address,
            "phone": self.phone,
            "website": self.website,
            "email": self.email,
            "score": self.score,
            "score_reasoning": self.score_reasoning,
            "score_status": score_status,
            "score_fail_reason": score_fail_reason,
            "stage": self.stage,
            "notes": self.notes,
            "rating": self.rating,
            "review_count": self.review_count,
            "email_source": self.email_source,
            "email_confidence": self.email_confidence,
            "email_candidates": self.email_candidates,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
        
        if hasattr(self, 'heuristic_score') and self.heuristic_score is not None:
            result["heuristic_score"] = self.heuristic_score
        if hasattr(self, 'ai_score') and self.ai_score is not None:
            result["ai_score"] = self.ai_score
        if hasattr(self, 'score_breakdown') and self.score_breakdown is not None:
            result["score_breakdown"] = self.score_breakdown
        if hasattr(self, 'score_confidence') and self.score_confidence is not None:
            result["score_confidence"] = self.score_confidence
        if hasattr(self, 'last_scored_at') and self.last_scored_at is not None:
            result["last_scored_at"] = self.last_scored_at.isoformat() if isinstance(self.last_scored_at, datetime) else self.last_scored_at
        if hasattr(self, 'technographics') and self.technographics is not None:
            result["technographics"] = self.technographics
        if hasattr(self, 'source') and self.source:
            result["source"] = self.source
        if hasattr(self, 'import_id') and self.import_id:
            result["import_id"] = self.import_id
        if hasattr(self, 'import_status') and self.import_status:
            result["import_status"] = self.import_status
        
        return result

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)
        self.updated_at = datetime.now()
    
    @classmethod
    def from_model(cls, model: LeadModel) -> 'Lead':
        """Create Lead from SQLAlchemy model."""
        return cls(
            id=model.id,
            name=model.name,
            contact_name=model.contact_name or "",
            address=model.address,
            phone=model.phone,
            website=model.website,
            email=model.email,
            score=model.score,
            score_reasoning=model.score_reasoning,
            stage=model.stage,
            notes=model.notes,
            rating=model.rating,
            review_count=model.review_count,
            email_source=model.email_source,
            email_confidence=model.email_confidence,
            email_candidates=model.email_candidates or [],
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_scored_at=model.last_scored_at,
            heuristic_score=model.heuristic_score,
            ai_score=model.ai_score,
            score_breakdown=model.score_breakdown,
            score_confidence=model.score_confidence,
            technographics=model.technographics,
            source=model.source or "search",
            import_id=model.import_id,
            import_status=model.import_status
        )
    
    def to_model(self, user_id: int) -> LeadModel:
        """Convert to SQLAlchemy model."""
        return LeadModel(
            id=self.id,
            user_id=user_id,
            name=self.name,
            contact_name=self.contact_name,
            address=self.address,
            phone=self.phone,
            website=self.website,
            email=self.email,
            score=self.score,
            score_reasoning=self.score_reasoning,
            stage=self.stage,
            notes=self.notes,
            rating=self.rating,
            review_count=self.review_count,
            email_source=self.email_source,
            email_confidence=self.email_confidence,
            email_candidates=self.email_candidates,
            created_at=self.created_at,
            updated_at=self.updated_at,
            technographics=self.technographics,
            source=self.source,
            import_id=self.import_id,
            import_status=self.import_status
        )


class LeadDatabase:
    """Database interface using PostgreSQL with user-scoped data."""
    
    def __init__(self):
        self._ensure_global_state()
    
    def _get_session(self) -> Session:
        """Get database session."""
        return SessionLocal()
    
    def _ensure_global_state(self):
        """Ensure global state exists in database."""
        session = self._get_session()
        try:
            state = session.query(GlobalStateModel).filter_by(id=1).first()
            if not state:
                state = GlobalStateModel(
                    id=1,
                    emails_sent_count=0,
                    sms_sent_count=0,
                    active_campaign_id=None
                )
                session.add(state)
                session.commit()
        finally:
            session.close()
    
    @property
    def emails_sent_count(self) -> int:
        session = self._get_session()
        try:
            state = session.query(GlobalStateModel).filter_by(id=1).first()
            return state.emails_sent_count if state else 0
        finally:
            session.close()
    
    @property
    def sms_sent_count(self) -> int:
        session = self._get_session()
        try:
            state = session.query(GlobalStateModel).filter_by(id=1).first()
            return state.sms_sent_count if state else 0
        finally:
            session.close()
    
    def get_active_campaign_id(self, user_id: int) -> Optional[str]:
        """Get active campaign ID for a specific user."""
        session = self._get_session()
        try:
            user = session.query(UserModel).filter_by(id=user_id).first()
            return user.active_campaign_id if user else None
        finally:
            session.close()

    def add_lead(self, lead: Lead, user_id: int, campaign_id: Optional[str] = None) -> Lead:
        """Add or update a lead for a specific user."""
        session = self._get_session()
        try:
            lead_model = lead.to_model(user_id)
            existing = session.query(LeadModel).filter_by(id=lead.id, user_id=user_id).first()
            
            if existing:
                for key, value in lead.to_dict().items():
                    if key not in ['created_at', 'updated_at']:
                        setattr(existing, key, value)
                session.commit()
            else:
                session.add(lead_model)
                session.commit()
            
            if campaign_id:
                campaign_model = session.query(CampaignModel).filter_by(
                    id=campaign_id, 
                    user_id=user_id
                ).first()
                if campaign_model:
                    if lead.id not in (campaign_model.lead_ids or []):
                        campaign_model.lead_ids = (campaign_model.lead_ids or []) + [lead.id]
                        session.commit()
            
            return lead
        finally:
            session.close()

    def get_lead(self, lead_id: str, user_id: int) -> Optional[Lead]:
        """Get a specific lead for a user."""
        session = self._get_session()
        try:
            lead_model = session.query(LeadModel).filter_by(
                id=lead_id, 
                user_id=user_id
            ).first()
            return Lead.from_model(lead_model) if lead_model else None
        finally:
            session.close()

    def get_all_leads(self, user_id: int) -> List[Lead]:
        """Get all leads for a specific user."""
        session = self._get_session()
        try:
            lead_models = session.query(LeadModel).filter(
                LeadModel.user_id == user_id
            ).all()
            return [Lead.from_model(model) for model in lead_models]
        finally:
            session.close()
    
    def get_campaign_leads(self, campaign_id: str, user_id: int) -> List[Lead]:
        """Get all leads for a specific campaign and user."""
        session = self._get_session()
        try:
            campaign_model = session.query(CampaignModel).filter_by(
                id=campaign_id, 
                user_id=user_id
            ).first()
            if not campaign_model:
                print(f"[get_campaign_leads] Campaign {campaign_id} not found for user {user_id}")
                return []
            
            lead_ids = campaign_model.lead_ids
            print(f"[get_campaign_leads] Campaign {campaign_id} has {len(lead_ids) if lead_ids else 0} lead_ids, type={type(lead_ids)}")
            
            if not lead_ids:
                print(f"[get_campaign_leads] No lead_ids for campaign {campaign_id}")
                return []
            
            if isinstance(lead_ids, str):
                import json
                try:
                    lead_ids = json.loads(lead_ids)
                    print(f"[get_campaign_leads] Parsed lead_ids from string, got {len(lead_ids)} ids")
                except (ValueError, TypeError):
                    print(f"[get_campaign_leads] Failed to parse lead_ids string: {lead_ids[:100]}")
                    return []
            
            print(f"[get_campaign_leads] Querying leads with {len(lead_ids)} ids, first 3: {lead_ids[:3]}")
            
            lead_models = session.query(LeadModel).filter(
                LeadModel.id.in_(lead_ids),
                LeadModel.user_id == user_id
            ).all()
            print(f"[get_campaign_leads] Found {len(lead_models)} leads in DB for campaign {campaign_id}")
            return [Lead.from_model(model) for model in lead_models]
        finally:
            session.close()
    
    def get_active_leads(self, user_id: int) -> List[Lead]:
        """Get leads from the active campaign for a specific user."""
        campaign_id = self.get_active_campaign_id(user_id)
        if campaign_id:
            return self.get_campaign_leads(campaign_id, user_id)
        return self.get_all_leads(user_id)

    def update_lead(self, lead_id: str, user_id: int, **kwargs) -> Optional[Lead]:
        """Update a lead for a specific user."""
        session = self._get_session()
        try:
            lead_model = session.query(LeadModel).filter_by(
                id=lead_id, 
                user_id=user_id
            ).first()
            if not lead_model:
                return None
            
            for key, value in kwargs.items():
                if hasattr(lead_model, key) and value is not None:
                    setattr(lead_model, key, value)
            
            lead_model.updated_at = datetime.now()
            session.commit()
            session.refresh(lead_model)
            
            return Lead.from_model(lead_model)
        finally:
            session.close()

    def delete_lead(self, lead_id: str, user_id: int) -> bool:
        """Delete a lead for a specific user."""
        session = self._get_session()
        try:
            lead_model = session.query(LeadModel).filter_by(
                id=lead_id, 
                user_id=user_id
            ).first()
            if lead_model:
                session.delete(lead_model)
                session.commit()
                return True
            return False
        finally:
            session.close()

    def clear_all(self):
        session = self._get_session()
        try:
            session.query(LeadModel).delete()
            session.query(CampaignModel).delete()
            state = session.query(GlobalStateModel).filter_by(id=1).first()
            if state:
                state.emails_sent_count = 0
                state.sms_sent_count = 0
                state.active_campaign_id = None
            session.commit()
        finally:
            session.close()

    def increment_emails_sent(self, count: int = 1):
        """Increment global email sent counter."""
        session = self._get_session()
        try:
            state = session.query(GlobalStateModel).filter_by(id=1).first()
            if state:
                state.emails_sent_count += count
                session.commit()
        finally:
            session.close()
    
    def increment_sms_sent(self, count: int = 1):
        """Increment global SMS sent counter."""
        session = self._get_session()
        try:
            state = session.query(GlobalStateModel).filter_by(id=1).first()
            if state:
                state.sms_sent_count += count
                session.commit()
        finally:
            session.close()
    
    def create_campaign(self, business_type: str, location: str, user_id: int) -> Campaign:
        """Create a new campaign for a specific user."""
        campaign = Campaign(business_type=business_type, location=location)
        
        session = self._get_session()
        try:
            campaign_model = campaign.to_model(user_id)
            session.add(campaign_model)
            
            user = session.query(UserModel).filter_by(id=user_id).first()
            if user:
                user.active_campaign_id = campaign.id
            
            session.commit()
            return campaign
        finally:
            session.close()
    
    def update_campaign(self, campaign_id: str, user_id: int, next_page_token: Optional[str] = None) -> Optional[Campaign]:
        """Update a campaign for a specific user."""
        session = self._get_session()
        try:
            campaign_model = session.query(CampaignModel).filter_by(
                id=campaign_id, 
                user_id=user_id
            ).first()
            if not campaign_model:
                return None
            
            if next_page_token is not None:
                campaign_model.next_page_token = next_page_token
            
            session.commit()
            return Campaign.from_model(campaign_model)
        finally:
            session.close()
    
    def delete_campaign(self, campaign_id: str, user_id: int) -> bool:
        """Delete a campaign and its associated leads for a specific user."""
        session = self._get_session()
        try:
            campaign_model = session.query(CampaignModel).filter_by(
                id=campaign_id, 
                user_id=user_id
            ).first()
            if not campaign_model:
                return False
            
            lead_ids = campaign_model.lead_ids or []
            if lead_ids:
                session.query(LeadModel).filter(
                    LeadModel.id.in_(lead_ids),
                    LeadModel.user_id == user_id
                ).delete(synchronize_session=False)
            
            session.delete(campaign_model)
            session.commit()
            return True
        finally:
            session.close()
    
    def get_campaign(self, campaign_id: str, user_id: int) -> Optional[Campaign]:
        """Get a specific campaign for a user."""
        session = self._get_session()
        try:
            campaign_model = session.query(CampaignModel).filter_by(
                id=campaign_id, 
                user_id=user_id
            ).first()
            return Campaign.from_model(campaign_model) if campaign_model else None
        finally:
            session.close()
    
    def get_all_campaigns(self, user_id: int) -> List[Campaign]:
        """Get all campaigns for a specific user."""
        session = self._get_session()
        try:
            campaign_models = session.query(CampaignModel).filter(
                CampaignModel.user_id == user_id
            ).order_by(
                CampaignModel.created_at.desc()
            ).all()
            return [Campaign.from_model(model) for model in campaign_models]
        finally:
            session.close()
    
    def find_campaign_by_search(self, business_type: str, location: str, user_id: int) -> Optional[Campaign]:
        """Find a campaign by business type and location for a specific user."""
        business_type_normalized = business_type.lower().strip()
        location_normalized = location.lower().strip()
        
        session = self._get_session()
        try:
            campaign_models = session.query(CampaignModel).filter(
                CampaignModel.user_id == user_id
            ).all()
            for model in campaign_models:
                if (model.business_type.lower().strip() == business_type_normalized and
                    model.location.lower().strip() == location_normalized):
                    return Campaign.from_model(model)
            return None
        finally:
            session.close()
    
    def set_active_campaign(self, campaign_id: Optional[str], user_id: int):
        """Set the active campaign for a specific user."""
        session = self._get_session()
        try:
            if campaign_id is not None:
                campaign_exists = session.query(CampaignModel).filter_by(
                    id=campaign_id, 
                    user_id=user_id
                ).first() is not None
                if not campaign_exists:
                    return
            
            user = session.query(UserModel).filter_by(id=user_id).first()
            if user:
                user.active_campaign_id = campaign_id
                session.commit()
        finally:
            session.close()
    
    def get_global_oauth_settings(self) -> Optional[GlobalOAuthSettingsModel]:
        """Get global OAuth settings (shared across all users)."""
        session = self._get_session()
        try:
            settings = session.query(GlobalOAuthSettingsModel).first()
            return settings
        finally:
            session.close()
    
    def save_gmail_oauth_config(self, client_id: str, client_secret_encrypted: str, redirect_uri: str):
        """Save Gmail OAuth configuration (shared across all users). Singleton pattern enforced with id=1."""
        session = self._get_session()
        try:
            settings = session.query(GlobalOAuthSettingsModel).filter_by(id=1).first()
            if not settings:
                settings = GlobalOAuthSettingsModel(id=1)
                session.add(settings)
            
            settings.gmail_client_id = client_id
            settings.gmail_client_secret_encrypted = client_secret_encrypted
            settings.gmail_redirect_uri = redirect_uri
            settings.gmail_configured = True
            session.commit()
        finally:
            session.close()
    
    def save_outlook_oauth_config(self, client_id: str, client_secret_encrypted: str, redirect_uri: str):
        """Save Outlook OAuth configuration (shared across all users). Singleton pattern enforced with id=1."""
        session = self._get_session()
        try:
            settings = session.query(GlobalOAuthSettingsModel).filter_by(id=1).first()
            if not settings:
                settings = GlobalOAuthSettingsModel(id=1)
                session.add(settings)
            
            settings.outlook_client_id = client_id
            settings.outlook_client_secret_encrypted = client_secret_encrypted
            settings.outlook_redirect_uri = redirect_uri
            settings.outlook_configured = True
            session.commit()
        finally:
            session.close()
    
    def get_gmail_oauth_credentials(self):
        """Get Gmail OAuth credentials (database first, then env fallback). Returns (client_id, client_secret, redirect_uri)."""
        from helpers.encryption import decrypt
        
        oauth_settings = self.get_global_oauth_settings()
        
        if oauth_settings and oauth_settings.gmail_configured:
            client_id = oauth_settings.gmail_client_id
            client_secret = decrypt(oauth_settings.gmail_client_secret_encrypted) if oauth_settings.gmail_client_secret_encrypted else None
            redirect_uri = oauth_settings.gmail_redirect_uri
            if client_id and client_secret and redirect_uri:
                return (client_id, client_secret, redirect_uri)
        
        import os
        client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
        redirect_uri = os.getenv("GOOGLE_OAUTH_REDIRECT_URI")
        
        if client_id and client_secret and redirect_uri:
            return (client_id, client_secret, redirect_uri)
        
        return (None, None, None)
    
    def get_outlook_oauth_credentials(self):
        """Get Outlook OAuth credentials (database first, then env fallback). Returns (client_id, client_secret, redirect_uri)."""
        from helpers.encryption import decrypt
        
        oauth_settings = self.get_global_oauth_settings()
        
        if oauth_settings and oauth_settings.outlook_configured:
            client_id = oauth_settings.outlook_client_id
            client_secret = decrypt(oauth_settings.outlook_client_secret_encrypted) if oauth_settings.outlook_client_secret_encrypted else None
            redirect_uri = oauth_settings.outlook_redirect_uri
            if client_id and client_secret and redirect_uri:
                return (client_id, client_secret, redirect_uri)
        
        import os
        client_id = os.getenv("MS_CLIENT_ID")
        client_secret = os.getenv("MS_CLIENT_SECRET")
        redirect_uri = os.getenv("MS_REDIRECT_URI")
        
        if client_id and client_secret and redirect_uri:
            return (client_id, client_secret, redirect_uri)
        
        return (None, None, None)


db = LeadDatabase()
