import os
import re
import requests
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")

EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

# Phone regex patterns for UK, US, and international formats
PHONE_REGEX = re.compile(r'''
    (?:
        # UK formats: 07mobile, 01xxx, 02xxx, 0800/0845 etc
        (?:0\d{2,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4})|
        # UK with country code +44
        (?:\+44[\s\-]?\(?\d{1,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{3,4})|
        # US formats: (xxx) xxx-xxxx, xxx-xxx-xxxx
        (?:\+?1?[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4})|
        # International format
        (?:\+\d{1,3}[\s\-]?\(?\d{1,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{3,4})
    )
''', re.VERBOSE)

# Emails to exclude (automated/system emails)
NOREPLY_PATTERNS = ['noreply@', 'no-reply@', 'donotreply@', 'do-not-reply@', 'mailer-daemon@']

# Exact placeholder/dummy emails to block
PLACEHOLDER_EMAILS = {
    'example@yourmail.com', 'test@example.com', 'email@example.com',
    'your@email.com', 'info@example.com', 'name@yourmail.com',
    'user@example.com', 'admin@example.com', 'contact@example.com',
    'hello@example.com', 'support@example.com', 'sales@example.com',
    'name@example.com', 'your@yourmail.com', 'mail@example.com',
    'yourname@email.com', 'name@domain.com', 'email@domain.com',
    'user@domain.com', 'your@domain.com', 'test@test.com',
    'example@example.com', 'info@yoursite.com', 'contact@yoursite.com',
}

# Invalid email domains to filter out
INVALID_DOMAINS = ['example.com', 'domain.com', 'email.com', 'yoursite.com', 'test.com', 'wixpress.com', 'sentry.io', 'sentry-next.wixpress.com', 'yourmail.com', 'sample.com', 'placeholder.com', 'tempmail.com', 'mailinator.com']

PLACEHOLDER_DOMAIN_KEYWORDS = ['example', 'test', 'placeholder', 'yourmail', 'sample', 'yoursite', 'yourdomain', 'mysite', 'fakeemail', 'tempmail']

GENERIC_PREFIXES = [
    "info", "contact", "hello", "support", "sales", "admin",
    "enquiries", "enquiry", "mail", "general", "office"
]

CONTACT_PAGE_PATHS = ['/contact', '/contact-us', '/about', '/about-us']

# Standard headers for requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}

def extract_domain(website: str) -> Optional[str]:
    """Extract domain from website URL."""
    try:
        if not website:
            return None
        if not website.startswith(('http://', 'https://')):
            website = f'https://{website}'
        parsed = urlparse(website)
        domain = parsed.netloc or parsed.path
        domain = domain.replace('www.', '')
        return domain
    except Exception:
        return None


def _fetch_page(url: str, timeout: int = 10) -> Tuple[str, str]:
    """Fetch a single page and return (url, html_content)."""
    try:
        response = requests.get(url, timeout=timeout, headers=HEADERS, verify=True, allow_redirects=True)
        if response.status_code == 200:
            return (url, response.text)
    except Exception:
        pass
    return (url, "")


def _extract_emails_from_html(html: str) -> set:
    """Extract emails from raw HTML using regex - fast, no parsing."""
    emails = set()
    if not html:
        return emails
    
    # Direct regex on raw HTML (fastest approach)
    found = EMAIL_REGEX.findall(html)
    for email in found:
        emails.add(email.lower().strip())
    
    # Check for obfuscated emails
    obfuscated_patterns = [
        r'([a-zA-Z0-9._%+-]+)\s*\[\s*at\s*\]\s*([a-zA-Z0-9.-]+)\s*\[\s*dot\s*\]\s*([a-zA-Z]{2,})',
        r'([a-zA-Z0-9._%+-]+)\s*\(\s*at\s*\)\s*([a-zA-Z0-9.-]+)\s*\(\s*dot\s*\)\s*([a-zA-Z]{2,})',
    ]
    for pattern in obfuscated_patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple) and len(match) == 3:
                emails.add(f"{match[0]}@{match[1]}.{match[2]}".lower().strip())
    
    return emails


def _extract_phones_from_html(html: str) -> set:
    """Extract phone numbers from raw HTML using regex."""
    phones = set()
    if not html:
        return phones
    
    found = PHONE_REGEX.findall(html)
    for phone in found:
        # Clean and normalize
        cleaned = re.sub(r'[\s\-\(\)]', '', phone)
        if len(cleaned) >= 10:
            phones.add(phone.strip())
    
    return phones


def _filter_emails(emails: set) -> List[str]:
    """Filter out invalid/noreply/placeholder emails."""
    filtered = []
    for email in emails:
        if not email or '@' not in email or '.' not in email:
            continue
        
        email_lower = email.lower().strip()
        
        if email_lower in PLACEHOLDER_EMAILS:
            continue
        
        # Filter out noreply patterns
        if any(pattern in email_lower for pattern in NOREPLY_PATTERNS):
            continue
        
        # Filter out invalid domains
        if any(domain in email_lower for domain in INVALID_DOMAINS):
            continue
        
        email_domain = email.lower().split('@')[-1] if '@' in email else ''
        if any(keyword in email_domain for keyword in PLACEHOLDER_DOMAIN_KEYWORDS):
            continue
        
        # Filter out file extensions
        if email.endswith(('.png', '.jpg', '.gif', '.svg', '.webp', '.js', '.css')):
            continue
        
        filtered.append(email)
    
    return list(set(filtered))


def extract_emails_from_website(website: str, timeout: int = 10) -> List[str]:
    """
    Extract email addresses from a business website using PARALLEL fetching.
    Checks homepage + contact pages simultaneously for speed.
    Returns a list of unique email addresses found.
    """
    if not website:
        return []
    
    try:
        if not website.startswith(('http://', 'https://')):
            website = f'https://{website}'
        
        pages_to_check = [website]
        for path in CONTACT_PAGE_PATHS:
            pages_to_check.append(urljoin(website, path))
        
        all_html = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(_fetch_page, url, timeout): url for url in pages_to_check}
            for future in as_completed(futures, timeout=timeout * 2):
                try:
                    url, html = future.result(timeout=timeout + 5)
                    if html:
                        all_html.append(html)
                except Exception:
                    continue
        
        all_emails = set()
        for html in all_html:
            all_emails.update(_extract_emails_from_html(html))
        
        return _filter_emails(all_emails)
    
    except Exception as e:
        print(f"Error extracting emails from {website}: {e}")
        return []


def is_generic_email(email: str) -> bool:
    """Check if an email is generic (info@, contact@, etc.)."""
    if not email:
        return False
    prefix = email.split('@')[0].lower()
    return prefix in GENERIC_PREFIXES


def choose_best_email(candidates: List[str]) -> Optional[str]:
    """
    Choose the best email from a list of candidates.
    Prefer generic emails like info@, contact@, hello@.
    """
    if not candidates:
        return None
    
    generic_emails = [e for e in candidates if is_generic_email(e)]
    if generic_emails:
        return generic_emails[0]
    
    return candidates[0]


def extract_phone_from_website(website: str, timeout: int = 10) -> Optional[str]:
    """
    Extract phone number from a business website using PARALLEL fetching.
    Checks homepage + contact pages simultaneously for speed.
    Returns the first valid phone number found.
    """
    if not website:
        return None
    
    try:
        if not website.startswith(('http://', 'https://')):
            website = f'https://{website}'
        
        pages_to_check = [website]
        for path in CONTACT_PAGE_PATHS:
            pages_to_check.append(urljoin(website, path))
        
        all_html = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(_fetch_page, url, timeout): url for url in pages_to_check}
            for future in as_completed(futures, timeout=timeout * 2):
                try:
                    url, html = future.result(timeout=timeout + 5)
                    if html:
                        all_html.append(html)
                except Exception:
                    continue
        
        # Extract phones from all HTML content using regex
        all_phones = set()
        for html in all_html:
            all_phones.update(_extract_phones_from_html(html))
            # Also check for tel: links
            tel_matches = re.findall(r'href=["\']tel:([^"\']+)["\']', html, re.IGNORECASE)
            for tel in tel_matches:
                cleaned = re.sub(r'[^\d+]', '', tel)
                if len(cleaned) >= 10:
                    all_phones.add(tel.strip())
        
        # Return the first valid phone
        if all_phones:
            return list(all_phones)[0]
        
        return None
    
    except Exception as e:
        print(f"Error extracting phone from {website}: {e}")
        return None


def enrich_from_hunter(domain: str, max_results: int = 3, hunter_api_key: Optional[str] = None) -> Dict:
    """
    Use Hunter.io API to find emails for a domain.
    Returns dict with 'emails' (list) and 'success' (bool).
    """
    api_key = hunter_api_key or HUNTER_API_KEY
    
    if not api_key:
        return {"success": False, "error": "HUNTER_API_KEY not configured", "emails": []}
    
    try:
        url = "https://api.hunter.io/v2/domain-search"
        params = {
            "domain": domain,
            "api_key": api_key,
            "limit": max_results
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 401:
            return {"success": False, "error": "Invalid Hunter API key", "emails": []}
        
        if response.status_code == 429:
            return {"success": False, "error": "Hunter API rate limit reached", "emails": []}
        
        if response.status_code != 200:
            return {"success": False, "error": f"Hunter API error: {response.status_code}", "emails": []}
        
        data = response.json()
        
        if "data" not in data or "emails" not in data["data"]:
            return {"success": True, "emails": []}
        
        email_list = []
        for email_obj in data["data"]["emails"]:
            email_address = email_obj.get("value")
            confidence = email_obj.get("confidence", 0)
            email_type = email_obj.get("type", "")
            
            if not email_address:
                continue
            
            is_generic = is_generic_email(email_address) or email_type == "generic"
            
            if is_generic or confidence >= 50:
                email_list.append({
                    "email": email_address,
                    "confidence": confidence / 100.0,
                    "type": email_type
                })
        
        return {"success": True, "emails": email_list}
    
    except Exception as e:
        print(f"Hunter API error for {domain}: {e}")
        return {"success": False, "error": str(e), "emails": []}
