import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Tuple

logger = logging.getLogger(__name__)

ADMIN_EMAIL = "laura.vimes@icloud.com"

SMTP_HOST = lambda: os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = lambda: int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = lambda: os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = lambda: os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = lambda: os.environ.get("SMTP_FROM_EMAIL", "noreply@leadblitz.co")


def is_smtp_configured() -> bool:
    return bool(SMTP_USERNAME() and SMTP_PASSWORD() and SMTP_HOST())


def get_app_base_url() -> str:
    for var in ("BASE_URL", "APP_BASE_URL"):
        value = os.environ.get(var, "")
        if value:
            return value.rstrip("/")
    return "https://leadblitz.co"


def send_system_email(to_email: str, subject: str, html_body: str) -> bool:
    if not is_smtp_configured():
        logger.warning(
            "[SYSTEM EMAIL] SMTP not configured. "
            "Set SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_EMAIL "
            "environment variables to enable transactional emails."
        )
        return False

    from_email = SMTP_FROM_EMAIL() or f"noreply@{SMTP_HOST()}"

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST(), SMTP_PORT(), timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USERNAME(), SMTP_PASSWORD())
            server.sendmail(from_email, to_email, msg.as_string())

        logger.info(f"[SYSTEM EMAIL] Sent '{subject}' to {to_email}")
        return True
    except Exception as e:
        logger.error(f"[SYSTEM EMAIL] Failed to send to {to_email}: {e}")
        return False


def build_branded_email(heading: str, body_content: str, button_text: str = None,
                        button_url: str = None, footer_note: str = None) -> str:
    button_html = ""
    if button_text and button_url:
        button_html = f"""
            <div style="text-align: center; margin: 32px 0;">
                <a href="{button_url}"
                   style="display: inline-block; background: linear-gradient(135deg, #8b5cf6, #a855f7);
                          color: #ffffff; text-decoration: none; padding: 14px 40px;
                          border-radius: 8px; font-weight: 600; font-size: 16px;
                          box-shadow: 0 4px 14px rgba(139, 92, 246, 0.4);">
                    {button_text}
                </a>
            </div>
            <p style="text-align: center; font-size: 12px; color: #9ca3af; margin-top: 8px;">
                Or copy this link: <a href="{button_url}" style="color: #8b5cf6; word-break: break-all;">{button_url}</a>
            </p>
        """

    footer_html = ""
    if footer_note:
        footer_html = f'<p style="color: #6b7280; font-size: 14px; margin-top: 24px;">{footer_note}</p>'

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="margin: 0; padding: 0; background-color: #f3f4f6; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
            <div style="background: linear-gradient(135deg, #8b5cf6, #7c3aed); padding: 32px; border-radius: 12px 12px 0 0; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">
                    &#9889; LeadBlitz
                </h1>
            </div>
            <div style="background: #ffffff; padding: 40px 32px; border-radius: 0 0 12px 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
                <h2 style="color: #1f2937; margin: 0 0 20px 0; font-size: 22px; font-weight: 600;">
                    {heading}
                </h2>
                <div style="color: #374151; font-size: 15px; line-height: 1.7;">
                    {body_content}
                </div>
                {button_html}
                {footer_html}
            </div>
            <div style="text-align: center; padding: 24px 0; color: #9ca3af; font-size: 12px;">
                <p style="margin: 0;">&copy; LeadBlitz. All rights reserved.</p>
                <p style="margin: 4px 0 0 0;">AI-powered lead generation for web professionals.</p>
            </div>
        </div>
    </body>
    </html>
    """


def send_post_call_emails(
    call_type: str,
    caller_name: str,
    caller_email: str,
    caller_phone: str,
    call_summary: str,
) -> Tuple[int, list]:
    emails_sent = 0
    errors = []
    calendly_link = os.environ.get("CALENDLY_LINK", "https://cal.com/leadblitz/demo")

    if call_type == "demo":
        caller_subject = "Your LeadBlitz Demo Booking Link \U0001f680"
        caller_body = build_branded_email(
            heading="Thanks for Calling LeadBlitz!",
            body_content=f"""
                <p>Hi {caller_name},</p>
                <p>Great chatting with you! We'd love to show you how LeadBlitz can
                supercharge your lead generation.</p>
                <p>Click the button below to book a time for your personalised demo:</p>
            """,
            button_text="Book Your Demo",
            button_url=calendly_link,
            footer_note='Visit <a href="https://leadblitz.co" style="color: #8b5cf6;">leadblitz.co</a> to learn more about what we can do for your business.',
        )
        admin_subject = f"NEW DEMO REQUEST from {caller_name}"
        admin_body = build_branded_email(
            heading="New Demo Request",
            body_content=f"""
                <p><strong>Name:</strong> {caller_name}</p>
                <p><strong>Phone:</strong> {caller_phone}</p>
                <p><strong>Email:</strong> {caller_email or 'Not provided'}</p>
                <p><strong>Summary:</strong> {call_summary}</p>
            """,
        )

    elif call_type == "support":
        caller_subject = "LeadBlitz Support \u2014 We\u2019re On It"
        caller_body = build_branded_email(
            heading="We've Got Your Support Request",
            body_content=f"""
                <p>Hi {caller_name},</p>
                <p>Thanks for reaching out to LeadBlitz support. We've logged your issue
                and our team will get back to you within <strong>24 hours</strong>.</p>
                <p><strong>Here's a summary of what you told us:</strong></p>
                <div style="background: #f9fafb; border-left: 4px solid #8b5cf6; padding: 16px; margin: 16px 0; border-radius: 4px;">
                    {call_summary}
                </div>
                <p>If you need to add anything, just reply to this email.</p>
            """,
            footer_note='Visit <a href="https://leadblitz.co" style="color: #8b5cf6;">leadblitz.co</a> for our help resources.',
        )
        admin_subject = f"SUPPORT CALL from {caller_name}"
        admin_body = build_branded_email(
            heading="Support Call Received",
            body_content=f"""
                <p><strong>Name:</strong> {caller_name}</p>
                <p><strong>Phone:</strong> {caller_phone}</p>
                <p><strong>Email:</strong> {caller_email or 'Not provided'}</p>
                <p><strong>Issue:</strong> {call_summary}</p>
            """,
        )

    else:
        caller_subject = "Thanks for Calling LeadBlitz"
        caller_body = build_branded_email(
            heading="Thanks for Getting in Touch!",
            body_content=f"""
                <p>Hi {caller_name},</p>
                <p>Thanks for calling LeadBlitz. Here's a summary of your call:</p>
                <div style="background: #f9fafb; border-left: 4px solid #8b5cf6; padding: 16px; margin: 16px 0; border-radius: 4px;">
                    {call_summary}
                </div>
                <p>We'll follow up if there's anything else we can help with.</p>
            """,
            footer_note='Visit <a href="https://leadblitz.co" style="color: #8b5cf6;">leadblitz.co</a> to learn more.',
        )
        admin_subject = f"CALL from {caller_name}"
        admin_body = build_branded_email(
            heading="General Call Received",
            body_content=f"""
                <p><strong>Name:</strong> {caller_name}</p>
                <p><strong>Phone:</strong> {caller_phone}</p>
                <p><strong>Email:</strong> {caller_email or 'Not provided'}</p>
                <p><strong>Type:</strong> {call_type}</p>
                <p><strong>Summary:</strong> {call_summary}</p>
            """,
        )

    if caller_email:
        try:
            if send_system_email(caller_email, caller_subject, caller_body):
                emails_sent += 1
            else:
                errors.append(f"Failed to send caller email to {caller_email}")
        except Exception as e:
            logger.error(f"[POST-CALL] Error sending caller email: {e}")
            errors.append(str(e))

    try:
        if send_system_email(ADMIN_EMAIL, admin_subject, admin_body):
            emails_sent += 1
        else:
            errors.append(f"Failed to send admin notification to {ADMIN_EMAIL}")
    except Exception as e:
        logger.error(f"[POST-CALL] Error sending admin email: {e}")
        errors.append(str(e))

    return emails_sent, errors
