"""
Technographics detection module.
Extracts technology stack information from existing HTML content.
No additional HTTP requests - uses the same page fetch already done for AI scoring.
"""

import re
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse


def detect_technographics(html: str, final_url: str = "", response_headers: Optional[Dict] = None) -> Dict[str, Any]:
    if not html or len(html.strip()) < 50:
        return _empty_technographics()

    soup = BeautifulSoup(html, 'html.parser')
    html_lower = html.lower()

    result = {
        "cms": detect_cms(html_lower, soup),
        "cms_version": detect_cms_version(soup),
        "ssl": detect_ssl(final_url),
        "mobile_responsive": detect_mobile_responsive(soup),
        "analytics": detect_analytics(html_lower, soup),
        "jquery": detect_jquery(html_lower, soup),
        "cookie_consent": detect_cookie_consent(html_lower, soup),
        "social_links": detect_social_links(soup),
        "page_bloat": detect_page_bloat(soup),
        "og_tags": detect_og_tags(soup),
        "favicon": detect_favicon(soup, html_lower),
        "detected": True,
    }

    return result


def _empty_technographics() -> Dict[str, Any]:
    return {
        "cms": {"name": "Unknown", "confidence": "low"},
        "cms_version": None,
        "ssl": False,
        "mobile_responsive": False,
        "analytics": {"google_analytics": False, "meta_pixel": False, "other": []},
        "jquery": {"present": False, "version": None},
        "cookie_consent": False,
        "social_links": {},
        "page_bloat": {"external_scripts": 0, "external_stylesheets": 0, "total_external": 0},
        "og_tags": {"has_og_title": False, "has_og_image": False},
        "favicon": False,
        "detected": False,
    }


def detect_cms(html_lower: str, soup: BeautifulSoup) -> Dict[str, Any]:
    if "wp-content" in html_lower or "wp-includes" in html_lower:
        return {"name": "WordPress", "confidence": "high"}
    if "wix.com" in html_lower or "wixsite.com" in html_lower or "_wix_browser_sess" in html_lower:
        return {"name": "Wix", "confidence": "high"}
    if "squarespace.com" in html_lower or "squarespace-cdn.com" in html_lower:
        return {"name": "Squarespace", "confidence": "high"}
    if "cdn.shopify.com" in html_lower or "shopify" in html_lower:
        return {"name": "Shopify", "confidence": "high"}
    if "webflow.com" in html_lower or "wf-" in html_lower:
        return {"name": "Webflow", "confidence": "medium"}
    if "/media/jui/" in html_lower or "joomla" in html_lower:
        return {"name": "Joomla", "confidence": "medium"}
    if "drupal" in html_lower or "/sites/default/files" in html_lower or "/misc/drupal.js" in html_lower:
        return {"name": "Drupal", "confidence": "medium"}
    if "ghost.io" in html_lower or "ghost-" in html_lower:
        return {"name": "Ghost", "confidence": "medium"}
    if "weebly.com" in html_lower:
        return {"name": "Weebly", "confidence": "high"}
    if "godaddy" in html_lower:
        return {"name": "GoDaddy", "confidence": "medium"}

    generator = soup.find("meta", attrs={"name": "generator"})
    if generator:
        gen_content = (generator.get("content", "") or "").lower()
        if "wordpress" in gen_content:
            return {"name": "WordPress", "confidence": "high"}
        if "joomla" in gen_content:
            return {"name": "Joomla", "confidence": "high"}
        if "drupal" in gen_content:
            return {"name": "Drupal", "confidence": "high"}
        if "wix" in gen_content:
            return {"name": "Wix", "confidence": "high"}
        if "squarespace" in gen_content:
            return {"name": "Squarespace", "confidence": "high"}
        if gen_content.strip():
            return {"name": gen_content.strip().title(), "confidence": "medium"}

    return {"name": "Custom/Unknown", "confidence": "low"}


def detect_cms_version(soup: BeautifulSoup) -> Optional[str]:
    generator = soup.find("meta", attrs={"name": "generator"})
    if generator:
        content = generator.get("content", "") or ""
        version_match = re.search(r'[\d]+\.[\d]+(?:\.[\d]+)?', content)
        if version_match:
            return version_match.group(0)
    return None


def detect_ssl(final_url: str) -> bool:
    return final_url.lower().startswith("https://")


def detect_mobile_responsive(soup: BeautifulSoup) -> bool:
    viewport = soup.find("meta", attrs={"name": "viewport"})
    return viewport is not None


def detect_analytics(html_lower: str, soup: BeautifulSoup) -> Dict[str, Any]:
    result = {
        "google_analytics": False,
        "meta_pixel": False,
        "other": []
    }

    if "gtag(" in html_lower or "googletagmanager.com" in html_lower or "google-analytics.com" in html_lower or "ga(" in html_lower:
        result["google_analytics"] = True

    if "connect.facebook.net" in html_lower or "fbq(" in html_lower or "facebook.com/tr" in html_lower:
        result["meta_pixel"] = True

    if "hotjar.com" in html_lower:
        result["other"].append("Hotjar")
    if "clarity.ms" in html_lower:
        result["other"].append("Microsoft Clarity")
    if "plausible.io" in html_lower:
        result["other"].append("Plausible")
    if "matomo" in html_lower or "piwik" in html_lower:
        result["other"].append("Matomo")
    if "mixpanel.com" in html_lower:
        result["other"].append("Mixpanel")
    if "segment.com" in html_lower or "segment.io" in html_lower:
        result["other"].append("Segment")

    return result


def detect_jquery(html_lower: str, soup: BeautifulSoup) -> Dict[str, Any]:
    result = {"present": False, "version": None}

    if "jquery" in html_lower:
        result["present"] = True

        version_patterns = [
            r'jquery[.-](\d+\.\d+(?:\.\d+)?)',
            r'jquery\.min\.js\?ver=(\d+\.\d+(?:\.\d+)?)',
            r'jQuery\s+v?(\d+\.\d+(?:\.\d+)?)',
        ]
        for pattern in version_patterns:
            match = re.search(pattern, html_lower)
            if match:
                result["version"] = match.group(1)
                break

    return result


def detect_cookie_consent(html_lower: str, soup: BeautifulSoup) -> bool:
    cookie_indicators = [
        "cookie-consent", "cookieconsent", "cookie-notice", "cookie-banner",
        "cookie-popup", "gdpr-consent", "cc-banner", "cc-window",
        "cookiebot", "osano", "onetrust", "termly", "iubenda",
        "cookie_consent", "accept-cookies", "cookie-law"
    ]
    return any(indicator in html_lower for indicator in cookie_indicators)


def detect_social_links(soup: BeautifulSoup) -> Dict[str, bool]:
    social = {
        "facebook": False,
        "instagram": False,
        "linkedin": False,
        "twitter": False,
        "youtube": False,
        "tiktok": False,
    }

    all_links = soup.find_all("a", href=True)
    for link in all_links:
        href = (link.get("href", "") or "").lower()
        if "facebook.com" in href and "/tr" not in href and "sharer" not in href:
            social["facebook"] = True
        if "instagram.com" in href:
            social["instagram"] = True
        if "linkedin.com" in href and "share" not in href:
            social["linkedin"] = True
        if "twitter.com" in href or "x.com/" in href:
            social["twitter"] = True
        if "youtube.com" in href:
            social["youtube"] = True
        if "tiktok.com" in href:
            social["tiktok"] = True

    return social


def detect_page_bloat(soup: BeautifulSoup) -> Dict[str, int]:
    external_scripts = 0
    external_stylesheets = 0

    for script in soup.find_all("script", src=True):
        src = script.get("src", "")
        if src.startswith("http") or src.startswith("//"):
            external_scripts += 1

    for link in soup.find_all("link", rel="stylesheet"):
        href = link.get("href", "")
        if href.startswith("http") or href.startswith("//"):
            external_stylesheets += 1

    return {
        "external_scripts": external_scripts,
        "external_stylesheets": external_stylesheets,
        "total_external": external_scripts + external_stylesheets,
    }


def detect_og_tags(soup: BeautifulSoup) -> Dict[str, bool]:
    og_title = soup.find("meta", attrs={"property": "og:title"})
    og_image = soup.find("meta", attrs={"property": "og:image"})
    return {
        "has_og_title": og_title is not None,
        "has_og_image": og_image is not None,
    }


def detect_favicon(soup: BeautifulSoup, html_lower: str) -> bool:
    favicon_link = soup.find("link", rel=re.compile(r"icon|shortcut", re.I))
    if favicon_link:
        return True
    if "favicon" in html_lower:
        return True
    return False


def classify_tech_health(technographics: Dict[str, Any]) -> Dict[str, List[Dict[str, str]]]:
    green = []
    amber = []
    red = []

    if technographics.get("ssl"):
        green.append({"label": "HTTPS", "detail": "SSL secured"})
    else:
        red.append({"label": "No SSL", "detail": "Not using HTTPS"})

    if technographics.get("mobile_responsive"):
        green.append({"label": "Responsive", "detail": "Mobile-friendly viewport"})
    else:
        red.append({"label": "Not Responsive", "detail": "No viewport meta tag"})

    cms = technographics.get("cms", {})
    cms_name = cms.get("name", "Unknown")
    cms_version = technographics.get("cms_version")

    if cms_name not in ("Custom/Unknown", "Unknown"):
        if cms_version:
            try:
                major = int(cms_version.split(".")[0])
                if cms_name == "WordPress" and major < 6:
                    amber.append({"label": f"{cms_name} {cms_version}", "detail": "Older version detected"})
                else:
                    green.append({"label": f"{cms_name} {cms_version}", "detail": "CMS detected"})
            except (ValueError, IndexError):
                green.append({"label": cms_name, "detail": "CMS detected"})
        else:
            green.append({"label": cms_name, "detail": "CMS detected"})

    analytics = technographics.get("analytics", {})
    has_any_analytics = analytics.get("google_analytics") or analytics.get("meta_pixel") or len(analytics.get("other", [])) > 0
    if has_any_analytics:
        parts = []
        if analytics.get("google_analytics"):
            parts.append("GA")
        if analytics.get("meta_pixel"):
            parts.append("Meta Pixel")
        parts.extend(analytics.get("other", []))
        green.append({"label": "Analytics", "detail": ", ".join(parts[:3])})
    else:
        red.append({"label": "No Analytics", "detail": "No tracking detected"})

    jquery = technographics.get("jquery", {})
    if jquery.get("present"):
        version = jquery.get("version")
        if version:
            try:
                major = int(version.split(".")[0])
                if major < 3:
                    amber.append({"label": f"jQuery {version}", "detail": "Older version"})
                else:
                    green.append({"label": f"jQuery {version}", "detail": "Current version"})
            except (ValueError, IndexError):
                amber.append({"label": "jQuery", "detail": "Version unknown"})
        else:
            amber.append({"label": "jQuery", "detail": "Version unknown"})

    og_tags = technographics.get("og_tags", {})
    if og_tags.get("has_og_title") and og_tags.get("has_og_image"):
        green.append({"label": "OG Tags", "detail": "Social sharing optimised"})
    elif og_tags.get("has_og_title") or og_tags.get("has_og_image"):
        amber.append({"label": "Partial OG", "detail": "Incomplete social tags"})
    else:
        amber.append({"label": "No OG Tags", "detail": "Poor social sharing"})

    if technographics.get("favicon"):
        green.append({"label": "Favicon", "detail": "Browser icon present"})
    else:
        red.append({"label": "No Favicon", "detail": "Missing browser icon"})

    if technographics.get("cookie_consent"):
        green.append({"label": "Cookie Consent", "detail": "GDPR compliance"})

    social = technographics.get("social_links", {})
    active_socials = [k for k, v in social.items() if v]
    if len(active_socials) >= 3:
        green.append({"label": "Social Links", "detail": f"{len(active_socials)} platforms"})
    elif len(active_socials) >= 1:
        amber.append({"label": "Limited Social", "detail": f"Only {len(active_socials)} platform(s)"})

    bloat = technographics.get("page_bloat", {})
    total_ext = bloat.get("total_external", 0)
    if total_ext > 30:
        amber.append({"label": "Page Bloat", "detail": f"{total_ext} external resources"})

    return {"green": green, "amber": amber, "red": red}
