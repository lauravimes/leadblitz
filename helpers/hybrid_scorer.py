"""
Hybrid website scoring orchestration.
Combines deterministic heuristics with AI review and manages caching.
"""

import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from urllib.parse import urlparse, urlunparse

from helpers.models import ScoreCache, SessionLocal


def normalize_url(url: str) -> str:
    """
    Normalize URL for consistent caching.
    
    Args:
        url: Raw URL (may include or exclude protocol)
        
    Returns:
        Normalized URL string
    """
    if not url:
        return ""
    
    # Add https if no protocol
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    
    # Parse and normalize
    parsed = urlparse(url)
    
    # Remove www. prefix for consistency
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    
    # Rebuild without query/fragment for cache key
    normalized = urlunparse((
        parsed.scheme,
        netloc,
        parsed.path.rstrip('/') or '/',
        '',  # params
        '',  # query
        ''   # fragment
    ))
    
    return normalized


def url_to_hash(url: str) -> str:
    """
    Convert URL to consistent hash for cache lookup.
    
    Args:
        url: Normalized URL
        
    Returns:
        SHA256 hash string
    """
    return hashlib.sha256(url.encode('utf-8')).hexdigest()


def get_cached_score(url: str, max_age_hours: int = 24) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached score if fresh enough.
    
    Args:
        url: Website URL
        max_age_hours: Maximum age of cache in hours (default 24)
        
    Returns:
        Cached score data or None if not found/expired
    """
    normalized = normalize_url(url)
    url_hash = url_to_hash(normalized)
    
    db = SessionLocal()
    try:
        cache_entry = db.query(ScoreCache).filter(
            ScoreCache.url_hash == url_hash
        ).first()
        
        if not cache_entry:
            return None
        
        # Check freshness
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        if cache_entry.fetched_at < cutoff:
            return None
        
        # Reconstruct format to match fresh scoring results
        heuristic_data = cache_entry.heuristic_result or {}
        ai_data = cache_entry.ai_result or {}
        
        # Calculate scores from cached data
        heuristic_score = heuristic_data.get("total_heuristic", 0)
        ai_category_scores = ai_data.get("category_scores", {})
        ai_score = min(50, sum(ai_category_scores.values()))
        
        return {
            "final_score": cache_entry.final_score,
            "confidence": cache_entry.confidence,
            "heuristic_score": heuristic_score,  # ← Add top-level score!
            "ai_score": int(ai_score),  # ← Add top-level score!
            "breakdown": {  # ← Reconstruct breakdown!
                "heuristic": heuristic_data.get("scores", {}),
                "ai": ai_category_scores
            },
            "evidence": heuristic_data.get("evidence", {}),
            "ai_justifications": ai_data.get("justifications", {}),
            "plain_english_report": ai_data.get("plain_english_report", {}),
            "rendering_limitations": heuristic_data.get("rendering_limitations", False),
            "has_errors": cache_entry.has_errors,
            "errors": cache_entry.error_messages or [],
            "render_pathway": cache_entry.render_pathway,
            "js_detected": cache_entry.js_detected,
            "js_confidence": cache_entry.js_confidence,
            "detection_signals": cache_entry.detection_signals or [],
            "framework_hints": cache_entry.framework_hints or [],
            "cached": True,
            "cached_at": cache_entry.fetched_at.isoformat() if cache_entry.fetched_at else None
        }
    finally:
        db.close()


def save_score_to_cache(url: str, score_data: Dict[str, Any]) -> None:
    """
    Save or update score in cache.
    
    Args:
        url: Website URL
        score_data: Combined score data to cache
    """
    normalized = normalize_url(url)
    url_hash = url_to_hash(normalized)
    
    db = SessionLocal()
    try:
        cache_entry = db.query(ScoreCache).filter(
            ScoreCache.url_hash == url_hash
        ).first()
        
        if cache_entry:
            # Update existing
            cache_entry.heuristic_result = score_data.get("heuristic")
            cache_entry.ai_result = score_data.get("ai_review")
            cache_entry.final_score = score_data.get("final_score", 0)
            cache_entry.confidence = score_data.get("confidence", 0.5)
            cache_entry.has_errors = score_data.get("has_errors", False)
            cache_entry.error_messages = score_data.get("errors", [])
            cache_entry.render_pathway = score_data.get("render_pathway")
            cache_entry.js_detected = score_data.get("js_detected", False)
            cache_entry.js_confidence = score_data.get("js_confidence")
            cache_entry.detection_signals = score_data.get("detection_signals")
            cache_entry.framework_hints = score_data.get("framework_hints")
            cache_entry.fetched_at = datetime.now()
        else:
            # Create new
            cache_entry = ScoreCache(
                url_hash=url_hash,
                normalized_url=normalized,
                heuristic_result=score_data.get("heuristic"),
                ai_result=score_data.get("ai_review"),
                final_score=score_data.get("final_score", 0),
                confidence=score_data.get("confidence", 0.5),
                has_errors=score_data.get("has_errors", False),
                error_messages=score_data.get("errors", []),
                render_pathway=score_data.get("render_pathway"),
                js_detected=score_data.get("js_detected", False),
                js_confidence=score_data.get("js_confidence"),
                detection_signals=score_data.get("detection_signals"),
                framework_hints=score_data.get("framework_hints"),
                fetched_at=datetime.now()
            )
            db.add(cache_entry)
        
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to cache score: {str(e)}")
    finally:
        db.close()


def score_website_hybrid(url: str, use_cache: bool = True) -> Dict[str, Any]:
    """
    Score a website using hybrid approach with selective rendering.
    
    Flow:
    1. Check cache
    2. Fetch static HTML
    3. Detect JavaScript frameworks
    4. Selectively render if JS-heavy
    5. Score using best available content
    6. Save results with detection metadata
    
    Args:
        url: Website URL to score
        use_cache: Whether to use/update cache (default True)
        
    Returns:
        Dict with final_score, confidence, breakdown, detection metadata
    """
    from helpers.site_fetcher import fetch_multiple_pages, extract_site_content_for_ai
    from helpers.site_heuristics import score_site_heuristics
    from helpers.ai_scorer import score_with_ai, combine_scores
    from helpers.framework_detector import detect_js_framework, get_detection_summary
    from helpers.rendering_service import render_if_needed
    from helpers.technographics import detect_technographics, classify_tech_health
    
    # Check cache first
    if use_cache:
        cached = get_cached_score(url)
        if cached:
            return cached
    
    # Step 1: Fetch website pages (static HTML)
    fetch_result = fetch_multiple_pages(url, max_pages=3)
    
    final_url = fetch_result.get("final_url", url)
    static_html = fetch_result.get("combined_html", "")
    fetch_status = fetch_result.get("status")
    
    # Check if website is blocking us with bot protection (403, 401, etc)
    is_blocked = fetch_status in [403, 401, 429]
    needs_browser_render = fetch_status == 202  # HTTP 202 often needs JS rendering
    used_fallback_render = False
    
    # If blocked, failed to fetch, or needs browser rendering, try Playwright
    if not static_html or is_blocked or needs_browser_render:
        print(f"Static fetch failed/blocked for {url} (status: {fetch_status}). Attempting Playwright render...")
        from helpers.rendering_service import render_with_playwright
        
        fallback_render = render_with_playwright(final_url or url)
        
        if fallback_render.get("html"):
            rendered_html = fallback_render["html"]
            
            # Check if the rendered content is actually a block page
            block_indicators = ['403 - forbidden', '403 forbidden', 'access denied', 'access to this page is forbidden',
                               'blocked', 'captcha', 'cloudflare', 'challenge-platform', 'ray id']
            html_lower = rendered_html.lower()
            is_block_page = any(indicator in html_lower for indicator in block_indicators)
            
            if is_block_page and len(rendered_html) < 20000:
                print(f"Playwright rendered a block page for {url} - treating as bot-blocked")
                is_blocked = True
                # Fall through to bot-blocked handling below
            else:
                # Successfully rendered with Playwright - use this content
                static_html = rendered_html
                used_fallback_render = True
                print(f"✓ Playwright fallback successful for {url}")
        
        # Handle bot-blocked or failed fetch scenarios
        if not static_html or is_blocked:
            sophistication_message = (
                "🛡️ **ADVANCED SECURITY DETECTED** - This website uses enterprise-grade bot protection "
                "(likely Cloudflare, Akamai, or similar). This indicates a sophisticated, well-funded organization "
                "with strong cybersecurity practices. While we cannot automatically score this site, the presence of "
                "advanced security measures suggests: (1) Professional IT infrastructure, (2) Investment in digital security, "
                "(3) Likely already has modern web architecture, (4) May not be an ideal target for basic web services. "
                "**Recommendation:** Manually review this website - companies with this level of security often have strong "
                "existing web presences and development teams."
            ) if is_blocked else ""
            
            return {
                "final_score": 0,
                "confidence": 0.3,
                "heuristic_score": 0,
                "ai_score": 0,
                "breakdown": {},
                "has_errors": True,
                "errors": fetch_result.get("errors", []) + (fallback_render.get("errors", []) if 'fallback_render' in dir() else []),
                "rendering_limitations": True,
                "render_pathway": "bot_blocked" if is_blocked else "fetch_failed",
                "js_detected": False,
                "bot_blocked": is_blocked,
                "sophistication_message": sophistication_message,
                "plain_english_report": {
                    "strengths": ["Website has enterprise-grade security measures"],
                    "weaknesses": [],
                    "technology_observations": sophistication_message if is_blocked else "Unable to access website",
                    "sales_opportunities": ["May not be an ideal prospect - sophisticated IT already in place"]
                } if is_blocked else {},
                "cached": False
            }
    
    # Step 2: Detect JavaScript frameworks
    detection = detect_js_framework(static_html)
    detection_summary = get_detection_summary(detection)
    print(f"Framework detection for {url}: {detection_summary}")
    
    # Step 3: Conditionally render if JS-heavy (skip if we already rendered via fallback)
    if used_fallback_render:
        # Already rendered with Playwright - skip additional rendering
        html_to_score = static_html
        render_pathway = "rendered"
        render_result = {"html": static_html, "pathway": "rendered", "errors": []}
    else:
        # Normal flow - conditionally render based on JS detection
        render_result = render_if_needed(final_url, static_html, detection)
        html_to_score = render_result.get("html", static_html)
        render_pathway = render_result.get("pathway", "static")
    
    # Step 4: Run heuristic scoring on best available HTML
    heuristic = score_site_heuristics(html_to_score, final_url)
    
    # Step 4.5: ESCALATION CHECK - If contact info is weak but content is rich, try Playwright
    if not used_fallback_render and render_pathway != "rendered":
        contact_score = heuristic.get("scores", {}).get("contact", 0)
        word_count = heuristic.get("evidence", {}).get("text_word_count", 0)
        contact_summary = heuristic.get("evidence", {}).get("contact_detection_summary", {})
        
        should_escalate = False
        escalation_reason = ""
        
        if contact_score < 3 and word_count > 200:
            should_escalate = True
            escalation_reason = f"Contact score low ({contact_score}) but rich content ({word_count} words)"
        
        emails_found = contact_summary.get("emails", 0)
        forms_found = len(contact_summary.get("forms", []))
        ctas_found = contact_summary.get("ctas", 0)
        
        if emails_found == 0 and forms_found == 0 and word_count > 100:
            should_escalate = True
            escalation_reason = "No emails/forms found but page has content - may be JavaScript-loaded"
        
        if should_escalate:
            print(f"Escalating to Playwright for {url}: {escalation_reason}")
            from helpers.rendering_service import render_with_playwright
            
            priority_links = heuristic.get("evidence", {}).get("priority_links", [])
            priority_links_from_fetch = fetch_result.get("priority_links_discovered", [])
            all_priority_links = list(set(priority_links + priority_links_from_fetch))
            
            pages_to_render = [final_url or url]
            for link in all_priority_links[:2]:
                if 'contact' in link.lower() or 'quote' in link.lower() or 'enquir' in link.lower():
                    pages_to_render.append(link)
            
            escalated_html = ""
            for render_url in pages_to_render[:3]:
                escalation_render = render_with_playwright(render_url)
                if escalation_render.get("html"):
                    escalated_html += f"\n\n<!-- Rendered: {render_url} -->\n{escalation_render['html']}"
            
            if escalated_html and len(escalated_html) > len(html_to_score):
                html_to_score = escalated_html
                render_pathway = "escalated_render"
                heuristic = score_site_heuristics(html_to_score, final_url)
                print(f"✓ Escalation render successful for {url} ({len(pages_to_render)} pages) - new contact score: {heuristic.get('scores', {}).get('contact', 0)}")
    
    # Step 5: Extract content for AI
    site_content = extract_site_content_for_ai(html_to_score, max_chars=6000)
    
    # Step 5.5: Detect technographics from existing HTML (no new requests)
    technographics_data = detect_technographics(html_to_score, final_url)
    
    # Determine rendering limitations
    rendering_limitations = (
        heuristic.get("rendering_limitations", False) or 
        (detection.get("is_js_heavy", False) and render_pathway != "rendered")
    )
    
    # Step 6: Run AI scoring
    ai_review = score_with_ai(
        site_content=site_content,
        heuristic_evidence=heuristic.get("evidence", {}),
        final_url=final_url,
        rendering_limitations=rendering_limitations,
        technographics=technographics_data
    )
    
    # Step 7: Combine scores
    result = combine_scores(heuristic, ai_review)
    
    # Add detection and rendering metadata
    result["cached"] = False
    result["has_errors"] = False
    result["errors"] = render_result.get("errors", [])
    result["render_pathway"] = render_pathway
    result["js_detected"] = detection.get("is_js_heavy", False)
    result["js_confidence"] = detection.get("confidence", 0.0)
    result["framework_hints"] = detection.get("framework_hints", [])
    result["detection_signals"] = detection.get("signals", [])
    result["rendering_limitations"] = rendering_limitations
    result["technographics"] = technographics_data
    
    # Step 8: Save to cache
    if use_cache:
        cache_data = {
            "heuristic": heuristic,
            "ai_review": ai_review,
            "final_score": result["final_score"],
            "confidence": result["confidence"],
            "has_errors": False,
            "errors": render_result.get("errors", []),
            "render_pathway": render_pathway,
            "js_detected": detection.get("is_js_heavy", False),
            "js_confidence": detection.get("confidence", 0.0),
            "detection_signals": detection.get("signals", []),
            "framework_hints": detection.get("framework_hints", []),
            "technographics": technographics_data
        }
        save_score_to_cache(url, cache_data)
    
    return result


def create_backward_compatible_reasoning(hybrid_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create score_reasoning JSON that maintains backward compatibility.
    
    Args:
        hybrid_result: Result from score_website_hybrid()
        
    Returns:
        JSON structure compatible with existing frontend
    """
    breakdown = hybrid_result.get("breakdown", {})
    heuristic_scores = breakdown.get("heuristic", {})
    ai_scores = breakdown.get("ai", {})
    
    # Calculate component scores first
    website_quality_score = heuristic_scores.get("mobile", 0) + heuristic_scores.get("seo", 0) + ai_scores.get("visual", 0)
    digital_presence_score = heuristic_scores.get("security", 0) + heuristic_scores.get("content", 0) + ai_scores.get("brand", 0)
    automation_opportunity_score = heuristic_scores.get("contact", 0) + heuristic_scores.get("tech", 0) + ai_scores.get("conversion", 0) + ai_scores.get("trust", 0)
    
    # Total score is driven by sum of component scores (ensures they always add up)
    calculated_total = website_quality_score + digital_presence_score + automation_opportunity_score
    
    # Map to old structure while adding new data
    return {
        "total_score": calculated_total,
        "confidence": hybrid_result.get("confidence", 0.5),
        
        # Legacy fields (scores must sum to total_score)
        "website_quality": {
            "score": website_quality_score,
            "rationale": hybrid_result.get("ai_justifications", {}).get("visual", "")
        },
        "digital_presence": {
            "score": digital_presence_score,
            "rationale": hybrid_result.get("ai_justifications", {}).get("brand", "")
        },
        "automation_opportunity": {
            "score": automation_opportunity_score,
            "rationale": hybrid_result.get("ai_justifications", {}).get("conversion", "")
        },
        
        # New hybrid data
        "hybrid_breakdown": {
            "heuristic_score": hybrid_result.get("heuristic_score", 0),
            "ai_score": hybrid_result.get("ai_score", 0),
            "heuristic_categories": heuristic_scores,
            "ai_categories": ai_scores
        },
        
        "evidence": hybrid_result.get("evidence", {}),
        "ai_justifications": hybrid_result.get("ai_justifications", {}),
        
        # CRITICAL: Include plain English sales report
        "plain_english_report": hybrid_result.get("plain_english_report", {}),
        
        "summary": f"Hybrid score: {hybrid_result.get('heuristic_score', 0)}/50 technical + {hybrid_result.get('ai_score', 0)}/50 UX/brand = {calculated_total}/100",
        "top_recommendation": hybrid_result.get("ai_justifications", {}).get("conversion", "Improve website conversion elements"),
        
        "rendering_limitations": hybrid_result.get("rendering_limitations", False),
        "render_pathway": hybrid_result.get("render_pathway", "static"),
        "js_detected": hybrid_result.get("js_detected", False),
        "js_confidence": hybrid_result.get("js_confidence", 0.0),
        "framework_hints": hybrid_result.get("framework_hints", []),
        "detection_signals": hybrid_result.get("detection_signals", []),
        "cached": hybrid_result.get("cached", False),
        
        # Bot blocking detection
        "bot_blocked": hybrid_result.get("bot_blocked", False),
        "sophistication_message": hybrid_result.get("sophistication_message", ""),
        
        # Technographics
        "technographics": hybrid_result.get("technographics", None)
    }
