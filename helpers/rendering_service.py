"""
Playwright-based rendering service for JavaScript-heavy websites.
Provides selective rendering with caching and error handling.
"""

from typing import Dict, Any, Optional
import hashlib
import time
from datetime import datetime, timedelta

_playwright_imported = False
sync_playwright = None
PlaywrightTimeout = None

def _ensure_playwright():
    global _playwright_imported, sync_playwright, PlaywrightTimeout
    if not _playwright_imported:
        from playwright.sync_api import sync_playwright as _sp, TimeoutError as _pt
        sync_playwright = _sp
        PlaywrightTimeout = _pt
        _playwright_imported = True


# In-memory cache for rendered content (24h TTL)
_render_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_HOURS = 24


def _get_cache_key(url: str) -> str:
    """Generate cache key from URL."""
    return hashlib.md5(url.encode()).hexdigest()


def _is_cache_valid(cache_entry: Dict[str, Any]) -> bool:
    """Check if cache entry is still valid."""
    if not cache_entry or "timestamp" not in cache_entry:
        return False
    
    cache_time = datetime.fromtimestamp(cache_entry["timestamp"])
    expiry_time = cache_time + timedelta(hours=CACHE_TTL_HOURS)
    
    return datetime.now() < expiry_time


def render_with_playwright(
    url: str,
    timeout: int = 8000,
    wait_for_selector: Optional[str] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Render a JavaScript-heavy website using headless Chromium.
    
    Args:
        url: URL to render
        timeout: Page load timeout in milliseconds (default 8000ms)
        wait_for_selector: Optional CSS selector to wait for before capturing
        use_cache: Whether to use cached results (default True)
        
    Returns:
        Dict with rendered HTML, status, errors, and metadata
    """
    _ensure_playwright()
    cache_key = _get_cache_key(url)
    
    # Check cache first
    if use_cache and cache_key in _render_cache:
        cached = _render_cache[cache_key]
        if _is_cache_valid(cached):
            cached["from_cache"] = True
            return cached
    
    result = {
        "success": False,
        "html": "",
        "text_content": "",
        "final_url": url,
        "status_code": None,
        "errors": [],
        "metadata": {},
        "timestamp": time.time(),
        "from_cache": False
    }
    
    try:
        with sync_playwright() as p:
            # Launch browser with stealth settings
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                ]
            )
            
            # Create context with realistic settings
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                ignore_https_errors=True,
                java_script_enabled=True
            )
            
            # Create page
            page = context.new_page()
            
            # Navigate with timeout
            try:
                response = page.goto(url, timeout=timeout, wait_until='networkidle')
                
                if response:
                    result["status_code"] = response.status
                    result["final_url"] = page.url
                
                # Wait for specific selector if provided
                if wait_for_selector:
                    try:
                        page.wait_for_selector(wait_for_selector, timeout=2000)
                    except PlaywrightTimeout:
                        result["errors"].append(f"Selector '{wait_for_selector}' not found")
                
                # Additional wait for dynamic content
                page.wait_for_timeout(1000)
                
                # Capture rendered HTML
                result["html"] = page.content()
                
                # Extract text content
                result["text_content"] = page.evaluate("document.body.innerText")
                
                # Capture metadata
                result["metadata"] = {
                    "title": page.title(),
                    "url": page.url,
                    "viewport": page.viewport_size,
                }
                
                result["success"] = True
                
            except PlaywrightTimeout:
                result["errors"].append("Page load timeout")
            except Exception as e:
                result["errors"].append(f"Navigation error: {str(e)[:200]}")
            
            finally:
                browser.close()
    
    except Exception as e:
        result["errors"].append(f"Rendering error: {str(e)[:200]}")
    
    # Cache successful renders
    if result["success"] and use_cache:
        _render_cache[cache_key] = result
    
    return result


def render_if_needed(
    url: str,
    static_html: str,
    detection_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Conditionally render a website based on framework detection.
    
    Args:
        url: Website URL
        static_html: Already-fetched static HTML
        detection_result: Output from framework_detector.detect_js_framework()
        
    Returns:
        Dict with rendering results and pathway information
    """
    result = {
        "rendered": False,
        "html": static_html,
        "text_content": "",
        "pathway": "static",
        "detection": detection_result,
        "errors": []
    }
    
    # Decide whether to render
    needs_rendering = detection_result.get("is_js_heavy", False)
    confidence = detection_result.get("confidence", 0)
    
    if not needs_rendering:
        result["pathway"] = "static"
        return result
    
    # Attempt rendering
    render_result = render_with_playwright(url)
    
    if render_result["success"]:
        result["rendered"] = True
        result["html"] = render_result["html"]
        result["text_content"] = render_result["text_content"]
        result["pathway"] = "rendered"
        result["metadata"] = render_result.get("metadata", {})
        result["from_cache"] = render_result.get("from_cache", False)
    else:
        # Rendering failed - fall back to static
        result["pathway"] = "render_failed"
        result["errors"] = render_result.get("errors", [])
    
    return result


def clear_render_cache():
    """Clear all cached rendered content."""
    global _render_cache
    _render_cache = {}


def get_cache_stats() -> Dict[str, Any]:
    """Get statistics about the render cache."""
    valid_entries = sum(1 for entry in _render_cache.values() if _is_cache_valid(entry))
    
    return {
        "total_entries": len(_render_cache),
        "valid_entries": valid_entries,
        "expired_entries": len(_render_cache) - valid_entries,
        "cache_ttl_hours": CACHE_TTL_HOURS
    }
