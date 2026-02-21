import os
import asyncio
import requests
import stripe
from typing import Optional, Dict, Any, Tuple

CREDIT_PACKAGES = {
    "starter": {
        "name": "Starter",
        "credits": 100,
        "price_cents": 1500,
        "description": "100 credits for AI lead scoring, outreach, and more"
    },
    "professional": {
        "name": "Professional",
        "credits": 500,
        "price_cents": 5900,
        "description": "500 credits for growing agencies"
    },
    "pro_team": {
        "name": "Pro Team",
        "credits": 2000,
        "price_cents": 19900,
        "description": "2000 credits for high-volume teams"
    },
    "founding_member": {
        "name": "Founding Member",
        "credits": 2000,
        "price_cents": 9900,
        "description": "2000 credits - 50% off Pro Team (limited to first 100 buyers)"
    }
}

CREDIT_COSTS = {
    "ai_scoring": 1,
    "email_send": 0,
    "sms_send": 2,
    "lead_search": 0,
    "email_personalization": 1
}


def _fetch_stripe_credentials() -> Tuple[str, str]:
    hostname = os.environ.get("REPLIT_CONNECTORS_HOSTNAME")
    repl_identity = os.environ.get("REPL_IDENTITY")
    web_repl_renewal = os.environ.get("WEB_REPL_RENEWAL")
    
    if repl_identity:
        x_replit_token = f"repl {repl_identity}"
    elif web_repl_renewal:
        x_replit_token = f"depl {web_repl_renewal}"
    else:
        raise ValueError("No Replit authentication token found")
    
    is_production = os.environ.get("REPLIT_DEPLOYMENT") == "1"
    target_environment = "production" if is_production else "development"
    
    url = f"https://{hostname}/api/v2/connection"
    params = {
        "include_secrets": "true",
        "connector_names": "stripe",
        "environment": target_environment
    }
    
    response = requests.get(url, params=params, headers={
        "Accept": "application/json",
        "X_REPLIT_TOKEN": x_replit_token
    }, timeout=15)
    
    data = response.json()
    connection_settings = data.get("items", [{}])[0]
    
    settings = connection_settings.get("settings", {})
    publishable_key = settings.get("publishable")
    secret_key = settings.get("secret")
    
    if not publishable_key or not secret_key:
        raise ValueError(f"Stripe {target_environment} connection not configured")
    
    return publishable_key, secret_key


async def get_stripe_credentials() -> Tuple[str, str]:
    return await asyncio.to_thread(_fetch_stripe_credentials)


async def get_stripe_client() -> stripe.StripeClient:
    _, secret_key = await get_stripe_credentials()
    return stripe.StripeClient(secret_key)


async def create_checkout_session(
    user_id: int,
    user_email: str,
    package_id: str,
    success_url: str,
    cancel_url: str,
    stripe_customer_id: Optional[str] = None
) -> Dict[str, Any]:
    if package_id not in CREDIT_PACKAGES:
        raise ValueError(f"Invalid package: {package_id}")
    
    package = CREDIT_PACKAGES[package_id]
    client = await get_stripe_client()
    
    price_data = {
        "currency": "usd",
        "product_data": {
            "name": package["name"],
            "description": package["description"],
        },
        "unit_amount": package["price_cents"],
    }
    
    session_params = {
        "payment_method_types": ["card"],
        "line_items": [{
            "price_data": price_data,
            "quantity": 1,
        }],
        "mode": "payment",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": {
            "user_id": str(user_id),
            "package_id": package_id,
            "credits": str(package["credits"]),
            "plan_name": package["name"],
            "amount_cents": str(package["price_cents"])
        }
    }
    
    if stripe_customer_id:
        session_params["customer"] = stripe_customer_id
    else:
        session_params["customer_email"] = user_email
    
    session = await asyncio.to_thread(client.checkout.sessions.create, params=session_params)
    
    return {
        "session_id": session.id,
        "url": session.url
    }


async def verify_webhook_signature(payload: bytes, signature: str) -> Dict[str, Any]:
    _, secret_key = await get_stripe_credentials()
    stripe.api_key = secret_key
    
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        import json
        event_data = json.loads(payload.decode('utf-8'))
        event = stripe.Event.construct_from(event_data, stripe.api_key)
        return {"type": event.type, "data": event.data.object}
    
    event = await asyncio.to_thread(stripe.Webhook.construct_event, payload, signature, webhook_secret)
    
    return {
        "type": event.type,
        "data": event.data.object
    }


async def get_customer_by_email(email: str) -> Optional[str]:
    client = await get_stripe_client()
    customers = await asyncio.to_thread(client.customers.list, params={"email": email, "limit": 1})
    if customers.data:
        return customers.data[0].id
    return None


async def create_customer(email: str, user_id: int) -> str:
    client = await get_stripe_client()
    customer = await asyncio.to_thread(client.customers.create, params={
        "email": email,
        "metadata": {"user_id": str(user_id)}
    })
    return customer.id
