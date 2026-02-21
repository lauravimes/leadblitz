import os
import re
from typing import Dict, Optional
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "")

def render_template(template: str, variables: Dict) -> str:
    result = template
    for key, value in variables.items():
        placeholder = "{{" + key + "}}"
        result = result.replace(placeholder, str(value))
    return result


def extract_city_from_address(address: str) -> str:
    parts = [p.strip() for p in address.split(',')]
    if len(parts) >= 2:
        return parts[-2]
    return parts[0] if parts else "Unknown"


def prepare_email_variables(lead_data: Dict) -> Dict:
    return {
        "business_name": lead_data.get("name", ""),
        "name": lead_data.get("name", ""),
        "address": lead_data.get("address", ""),
        "phone": lead_data.get("phone", ""),
        "website": lead_data.get("website", ""),
        "email": lead_data.get("email", ""),
        "score": lead_data.get("score", 0),
        "stage": lead_data.get("stage", "New"),
        "city": extract_city_from_address(lead_data.get("address", ""))
    }


def send_email(to_email: str, subject: str, body: str, sendgrid_api_key: Optional[str] = None, from_email: Optional[str] = None) -> tuple[bool, Optional[str]]:
    api_key = sendgrid_api_key or SENDGRID_API_KEY
    sender_email = from_email or FROM_EMAIL
    
    if not api_key or not sender_email:
        return False, "SendGrid not configured (missing SENDGRID_API_KEY or FROM_EMAIL)"
    
    if not to_email or '@' not in to_email:
        return False, "Invalid email address"
    
    footer = "\n\n---\nIf you'd prefer not to be contacted, reply 'STOP' and you'll be removed."
    full_body = body + footer
    
    message = Mail(
        from_email=sender_email,
        to_emails=to_email,
        subject=subject,
        html_content=full_body.replace('\n', '<br>')
    )
    
    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        return response.status_code in [200, 201, 202], None
    
    except Exception as e:
        error_msg = str(e)[:200]
        return False, error_msg


def validate_email_config(sendgrid_api_key: Optional[str] = None, from_email: Optional[str] = None) -> tuple[bool, Optional[str]]:
    api_key = sendgrid_api_key or SENDGRID_API_KEY
    sender_email = from_email or FROM_EMAIL
    
    if not api_key:
        return False, "SENDGRID_API_KEY not set"
    if not sender_email:
        return False, "FROM_EMAIL not set"
    return True, None
