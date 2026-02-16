import os
from typing import Dict, List, Optional
from twilio.rest import Client

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")

def validate_sms_config(account_sid: Optional[str] = None, auth_token: Optional[str] = None, phone_number: Optional[str] = None) -> bool:
    sid = account_sid or TWILIO_ACCOUNT_SID
    token = auth_token or TWILIO_AUTH_TOKEN
    phone = phone_number or TWILIO_PHONE_NUMBER
    return all([sid, token, phone])

def prepare_sms_variables(lead: Dict) -> Dict[str, str]:
    address = lead.get("address", "")
    parts = address.split(",") if address else []
    city = parts[-2].strip() if len(parts) >= 2 else "your area"
    
    return {
        "business_name": lead.get("name", ""),
        "name": lead.get("name", ""),
        "city": city,
        "score": str(lead.get("score", 0)),
        "phone": lead.get("phone", ""),
        "website": lead.get("website", "")
    }

def render_sms_template(template: str, variables: Dict[str, str]) -> str:
    message = template
    for key, value in variables.items():
        placeholder = f"{{{{{key}}}}}"
        message = message.replace(placeholder, value)
    return message

def send_sms(to_phone: str, message: str, account_sid: Optional[str] = None, auth_token: Optional[str] = None, phone_number: Optional[str] = None) -> Dict:
    sid = account_sid or TWILIO_ACCOUNT_SID
    token = auth_token or TWILIO_AUTH_TOKEN
    from_phone = phone_number or TWILIO_PHONE_NUMBER
    
    if not validate_sms_config(sid, token, from_phone):
        raise ValueError("Twilio configuration incomplete. Please set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER")
    
    if not to_phone:
        raise ValueError("Recipient phone number is required")
    
    try:
        client = Client(sid, token)
        
        sms_message = client.messages.create(
            body=message,
            from_=from_phone,
            to=to_phone
        )
        
        return {
            "success": True,
            "message_sid": sms_message.sid,
            "status": sms_message.status
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
