import os
import smtplib
import base64
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from helpers.models import EmailSettings as EmailSettingsModel
from helpers.encryption import encrypt, decrypt


class EmailProviderError(Exception):
    """Raised when email sending fails."""
    pass


def get_email_settings(db: Session, user_id: int) -> Optional[EmailSettingsModel]:
    """Get email settings for a user."""
    return db.query(EmailSettingsModel).filter(EmailSettingsModel.user_id == user_id).first()


def refresh_gmail_token(settings: EmailSettingsModel, db: Session) -> str:
    """Refresh Gmail access token using refresh token."""
    if not settings.gmail_refresh_token:
        raise EmailProviderError("No Gmail refresh token available")
    
    refresh_token = decrypt(settings.gmail_refresh_token)
    
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise EmailProviderError("Gmail OAuth credentials not configured")
    
    response = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    })
    
    if response.status_code != 200:
        raise EmailProviderError(f"Failed to refresh Gmail token: {response.text}")
    
    data = response.json()
    settings.gmail_access_token = encrypt(data["access_token"])
    settings.gmail_token_expiry = datetime.now() + timedelta(seconds=data.get("expires_in", 3600))
    db.commit()
    
    return decrypt(settings.gmail_access_token)


def send_via_gmail(settings: EmailSettingsModel, to_email: str, subject: str, html_body: str, db: Session) -> dict:
    """Send email via Gmail API (legacy manual OAuth method)."""
    if not settings.gmail_access_token or not settings.gmail_email_address:
        raise EmailProviderError("Gmail not properly configured")
    
    if settings.gmail_token_expiry and datetime.now() >= settings.gmail_token_expiry:
        access_token = refresh_gmail_token(settings, db)
    else:
        access_token = decrypt(settings.gmail_access_token)
    
    message = MIMEMultipart('alternative')
    message['From'] = settings.gmail_email_address
    message['To'] = to_email
    message['Subject'] = subject
    message.attach(MIMEText(html_body, 'html'))
    
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    
    response = requests.post(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"raw": raw_message}
    )
    
    if response.status_code != 200:
        raise EmailProviderError(f"Gmail API error: {response.text}")
    
    return {"success": True, "provider": "gmail", "message_id": response.json().get("id")}


def refresh_outlook_token(settings: EmailSettingsModel, db: Session) -> str:
    """Refresh Outlook access token using refresh token."""
    if not settings.outlook_refresh_token:
        raise EmailProviderError("No Outlook refresh token available")
    
    refresh_token = decrypt(settings.outlook_refresh_token)
    
    client_id = os.getenv("MS_CLIENT_ID")
    client_secret = os.getenv("MS_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise EmailProviderError("Outlook OAuth credentials not configured")
    
    response = requests.post("https://login.microsoftonline.com/common/oauth2/v2.0/token", data={
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "scope": "offline_access Mail.Send User.Read"
    })
    
    if response.status_code != 200:
        raise EmailProviderError(f"Failed to refresh Outlook token: {response.text}")
    
    data = response.json()
    settings.outlook_access_token = encrypt(data["access_token"])
    settings.outlook_token_expiry = datetime.now() + timedelta(seconds=data.get("expires_in", 3600))
    db.commit()
    
    return decrypt(settings.outlook_access_token)


def send_via_outlook(settings: EmailSettingsModel, to_email: str, subject: str, html_body: str, db: Session) -> dict:
    """Send email via Microsoft Graph API."""
    if not settings.outlook_access_token or not settings.outlook_email_address:
        raise EmailProviderError("Outlook not properly configured")
    
    if settings.outlook_token_expiry and datetime.now() >= settings.outlook_token_expiry:
        access_token = refresh_outlook_token(settings, db)
    else:
        access_token = decrypt(settings.outlook_access_token)
    
    message_data = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "HTML",
                "content": html_body
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": to_email
                    }
                }
            ]
        }
    }
    
    response = requests.post(
        "https://graph.microsoft.com/v1.0/me/sendMail",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        },
        json=message_data
    )
    
    if response.status_code != 202:
        raise EmailProviderError(f"Outlook Graph API error: {response.text}")
    
    return {"success": True, "provider": "outlook"}


def send_via_smtp(settings: EmailSettingsModel, to_email: str, subject: str, html_body: str) -> dict:
    """Send email via SMTP."""
    if not all([settings.smtp_host, settings.smtp_port, settings.smtp_username, 
                settings.smtp_password_encrypted, settings.smtp_from_email]):
        raise EmailProviderError("SMTP not properly configured")
    
    smtp_password = decrypt(settings.smtp_password_encrypted)
    
    message = MIMEMultipart('alternative')
    message['From'] = settings.smtp_from_email
    message['To'] = to_email
    message['Subject'] = subject
    message.attach(MIMEText(html_body, 'html'))
    
    import socket as _socket
    old_timeout = _socket.getdefaulttimeout()
    _socket.setdefaulttimeout(5)
    try:
        if settings.smtp_use_tls:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=5)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=5)
        
        server.login(settings.smtp_username, smtp_password)
        server.send_message(message)
        server.quit()
        
        return {"success": True, "provider": "smtp"}
    except (TimeoutError, _socket.timeout, OSError) as e:
        raise EmailProviderError(f"SMTP connection timed out: {str(e)}")
    except Exception as e:
        raise EmailProviderError(f"SMTP error: {str(e)}")
    finally:
        _socket.setdefaulttimeout(old_timeout)


def send_via_sendgrid(settings: EmailSettingsModel, to_email: str, subject: str, html_body: str) -> dict:
    """Send email via SendGrid API."""
    if not settings.sendgrid_api_key_encrypted or not settings.sendgrid_from_email:
        raise EmailProviderError("SendGrid not properly configured")
    
    api_key = decrypt(settings.sendgrid_api_key_encrypted)
    
    response = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": settings.sendgrid_from_email},
            "subject": subject,
            "content": [{"type": "text/html", "value": html_body}]
        }
    )
    
    if response.status_code not in [200, 202]:
        raise EmailProviderError(f"SendGrid API error: {response.text}")
    
    return {"success": True, "provider": "sendgrid"}


def send_email_for_user(db: Session, user_id: int, to_email: str, subject: str, html_body: str) -> dict:
    """Send email using the user's configured provider."""
    settings = get_email_settings(db, user_id)
    
    if not settings or settings.provider == "none":
        raise EmailProviderError("No email provider configured. Please set up an email provider in Settings.")
    
    if settings.provider == "gmail":
        return send_via_gmail(settings, to_email, subject, html_body, db)
    elif settings.provider == "outlook":
        return send_via_outlook(settings, to_email, subject, html_body, db)
    elif settings.provider == "smtp":
        return send_via_smtp(settings, to_email, subject, html_body)
    elif settings.provider == "sendgrid":
        return send_via_sendgrid(settings, to_email, subject, html_body)
    else:
        raise EmailProviderError(f"Unsupported email provider: {settings.provider}")


def _build_mime_with_attachment(
    from_email: str, to_email: str, subject: str, html_body: str,
    attachment_bytes: bytes, attachment_filename: str, attachment_mime: str = "application/pdf"
) -> MIMEMultipart:
    message = MIMEMultipart('mixed')
    message['From'] = from_email
    message['To'] = to_email
    message['Subject'] = subject

    html_part = MIMEText(html_body, 'html')
    message.attach(html_part)

    maintype, subtype = attachment_mime.split("/", 1)
    attachment = MIMEApplication(attachment_bytes, _subtype=subtype)
    attachment.add_header('Content-Disposition', 'attachment', filename=attachment_filename)
    message.attach(attachment)

    return message


def send_via_gmail_with_attachment(
    settings: EmailSettingsModel, to_email: str, subject: str, html_body: str,
    db: Session, attachment_bytes: bytes, attachment_filename: str, attachment_mime: str = "application/pdf"
) -> dict:
    if not settings.gmail_access_token or not settings.gmail_email_address:
        raise EmailProviderError("Gmail not properly configured")

    if settings.gmail_token_expiry and datetime.now() >= settings.gmail_token_expiry:
        access_token = refresh_gmail_token(settings, db)
    else:
        access_token = decrypt(settings.gmail_access_token)

    message = _build_mime_with_attachment(
        settings.gmail_email_address, to_email, subject, html_body,
        attachment_bytes, attachment_filename, attachment_mime
    )
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    response = requests.post(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"raw": raw_message}
    )

    if response.status_code != 200:
        raise EmailProviderError(f"Gmail API error: {response.text}")

    return {"success": True, "provider": "gmail", "message_id": response.json().get("id")}


def send_via_outlook_with_attachment(
    settings: EmailSettingsModel, to_email: str, subject: str, html_body: str,
    db: Session, attachment_bytes: bytes, attachment_filename: str, attachment_mime: str = "application/pdf"
) -> dict:
    if not settings.outlook_access_token or not settings.outlook_email_address:
        raise EmailProviderError("Outlook not properly configured")

    if settings.outlook_token_expiry and datetime.now() >= settings.outlook_token_expiry:
        access_token = refresh_outlook_token(settings, db)
    else:
        access_token = decrypt(settings.outlook_access_token)

    message_data = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": html_body},
            "toRecipients": [{"emailAddress": {"address": to_email}}],
            "attachments": [{
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": attachment_filename,
                "contentType": attachment_mime,
                "contentBytes": base64.b64encode(attachment_bytes).decode()
            }]
        }
    }

    response = requests.post(
        "https://graph.microsoft.com/v1.0/me/sendMail",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json=message_data
    )

    if response.status_code != 202:
        raise EmailProviderError(f"Outlook Graph API error: {response.text}")

    return {"success": True, "provider": "outlook"}


def send_via_smtp_with_attachment(
    settings: EmailSettingsModel, to_email: str, subject: str, html_body: str,
    attachment_bytes: bytes, attachment_filename: str, attachment_mime: str = "application/pdf"
) -> dict:
    if not all([settings.smtp_host, settings.smtp_port, settings.smtp_username,
                settings.smtp_password_encrypted, settings.smtp_from_email]):
        raise EmailProviderError("SMTP not properly configured")

    smtp_password = decrypt(settings.smtp_password_encrypted)

    message = _build_mime_with_attachment(
        settings.smtp_from_email, to_email, subject, html_body,
        attachment_bytes, attachment_filename, attachment_mime
    )

    import socket as _socket
    old_timeout = _socket.getdefaulttimeout()
    _socket.setdefaulttimeout(5)
    try:
        if settings.smtp_use_tls:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=5)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=5)

        server.login(settings.smtp_username, smtp_password)
        server.send_message(message)
        server.quit()

        return {"success": True, "provider": "smtp"}
    except (TimeoutError, _socket.timeout, OSError) as e:
        raise EmailProviderError(f"SMTP connection timed out: {str(e)}")
    except Exception as e:
        raise EmailProviderError(f"SMTP error: {str(e)}")
    finally:
        _socket.setdefaulttimeout(old_timeout)


def send_via_sendgrid_with_attachment(
    settings: EmailSettingsModel, to_email: str, subject: str, html_body: str,
    attachment_bytes: bytes, attachment_filename: str, attachment_mime: str = "application/pdf"
) -> dict:
    if not settings.sendgrid_api_key_encrypted or not settings.sendgrid_from_email:
        raise EmailProviderError("SendGrid not properly configured")

    api_key = decrypt(settings.sendgrid_api_key_encrypted)

    response = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": settings.sendgrid_from_email},
            "subject": subject,
            "content": [{"type": "text/html", "value": html_body}],
            "attachments": [{
                "content": base64.b64encode(attachment_bytes).decode(),
                "type": attachment_mime,
                "filename": attachment_filename,
                "disposition": "attachment"
            }]
        }
    )

    if response.status_code not in [200, 202]:
        raise EmailProviderError(f"SendGrid API error: {response.text}")

    return {"success": True, "provider": "sendgrid"}


def send_email_with_attachment_for_user(
    db: Session, user_id: int, to_email: str, subject: str, html_body: str,
    attachment_bytes: bytes, attachment_filename: str, attachment_mime: str = "application/pdf"
) -> dict:
    settings = get_email_settings(db, user_id)

    if not settings or settings.provider == "none":
        raise EmailProviderError("No email provider configured. Please set up an email provider in Settings.")

    if settings.provider == "gmail":
        return send_via_gmail_with_attachment(settings, to_email, subject, html_body, db, attachment_bytes, attachment_filename, attachment_mime)
    elif settings.provider == "outlook":
        return send_via_outlook_with_attachment(settings, to_email, subject, html_body, db, attachment_bytes, attachment_filename, attachment_mime)
    elif settings.provider == "smtp":
        return send_via_smtp_with_attachment(settings, to_email, subject, html_body, attachment_bytes, attachment_filename, attachment_mime)
    elif settings.provider == "sendgrid":
        return send_via_sendgrid_with_attachment(settings, to_email, subject, html_body, attachment_bytes, attachment_filename, attachment_mime)
    else:
        raise EmailProviderError(f"Unsupported email provider: {settings.provider}")
