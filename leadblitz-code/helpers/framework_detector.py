"""
Framework detector to identify JavaScript-heavy websites.
Determines which sites need full rendering vs. static HTML analysis.
"""

from typing import Dict, List, Any
from bs4 import BeautifulSoup
import re


def detect_js_framework(html: str) -> Dict[str, Any]:
    """
    Detect if a website uses modern JavaScript frameworks that require rendering.
    
    Args:
        html: Raw HTML content from initial fetch
        
    Returns:
        Dict with detection results, confidence, and signals
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Initialize detection signals
    signals = []
    confidence_score = 0.0
    framework_hints = []
    
    # 1. Check for framework-specific signatures
    framework_signatures = {
        'React': [
            'data-reactroot',
            'data-reactid',
            'id="root"',
            'id="__next"',  # Next.js
            '_next/static',
            'react-dom',
            'React.createElement'
        ],
        'Vue': [
            'data-v-',
            'id="app"',
            'vue.js',
            'vuejs',
            '__NUXT__',
            'window.__NUXT__'
        ],
        'Angular': [
            'ng-app',
            'ng-version',
            '[ng-',
            'angular.min.js',
            'data-ng-'
        ],
        'Svelte': [
            'svelte',
            '_svelte',
            'svelte.js'
        ],
        'Gatsby': [
            'gatsby',
            '___gatsby',
            'gatsby-react-router'
        ]
    }
    
    html_lower = html.lower()
    for framework, signatures in framework_signatures.items():
        for sig in signatures:
            if sig.lower() in html_lower:
                framework_hints.append(framework)
                signals.append(f"Framework signature: {framework} ({sig})")
                confidence_score += 0.15
                break
    
    # 2. Check for build tool artifacts (Webpack, Vite, etc.)
    build_tool_patterns = [
        r'webpack',
        r'vite',
        r'\.chunk\.js',
        r'bundle\.js',
        r'app\.[a-z0-9]+\.js',  # Hashed filenames
        r'main\.[a-z0-9]+\.js',
        r'vendor\.[a-z0-9]+\.js'
    ]
    
    for pattern in build_tool_patterns:
        if re.search(pattern, html_lower):
            signals.append(f"Build artifact detected: {pattern}")
            confidence_score += 0.1
            break
    
    # 3. Analyze DOM structure
    # Remove scripts and styles for text analysis
    for tag in soup(['script', 'style', 'noscript']):
        tag.decompose()
    
    visible_text = soup.get_text(separator=' ', strip=True)
    text_word_count = len(visible_text.split())
    
    # Restore soup for script analysis
    soup = BeautifulSoup(html, 'html.parser')
    scripts = soup.find_all('script')
    script_count = len(scripts)
    
    # Calculate total script size
    script_size = sum(len(script.get_text()) for script in scripts)
    html_size = len(html)
    script_ratio = script_size / html_size if html_size > 0 else 0
    
    # 4. Check for hydration markers
    hydration_markers = [
        'data-reactroot',
        'data-server-rendered',
        'dehydrated',
        'hydrate',
        '__INITIAL_STATE__',
        '__PRELOADED_STATE__'
    ]
    
    for marker in hydration_markers:
        if marker.lower() in html_lower:
            signals.append(f"Hydration marker: {marker}")
            confidence_score += 0.1
    
    # 5. Check for minimal content (classic SPA pattern)
    if text_word_count < 120:
        signals.append(f"Low text content: {text_word_count} words")
        confidence_score += 0.2
    
    if text_word_count < 50:
        signals.append("Very sparse HTML - likely SPA shell")
        confidence_score += 0.3
    
    # 6. High script-to-HTML ratio
    if script_ratio > 0.4:
        signals.append(f"High script ratio: {script_ratio:.1%}")
        confidence_score += 0.15
    
    if script_ratio > 0.6:
        signals.append("Extremely high script ratio")
        confidence_score += 0.15
    
    # 7. Check for typical SPA DOM patterns
    root_containers = soup.find_all(id=re.compile(r'^(root|app|__next|___gatsby)$'))
    if root_containers:
        for container in root_containers:
            if len(container.get_text(strip=True)) < 50:
                signals.append(f"Empty root container: {container.get('id')}")
                confidence_score += 0.2
    
    # 8. Check for noscript warnings
    noscript_tags = soup.find_all('noscript')
    for noscript in noscript_tags:
        text = noscript.get_text(strip=True).lower()
        if any(word in text for word in ['javascript', 'enable', 'required', 'need']):
            signals.append("Noscript warning detected")
            confidence_score += 0.15
            break
    
    # Cap confidence at 1.0
    confidence_score = min(confidence_score, 1.0)
    
    # Determine if JS rendering is needed
    needs_rendering = confidence_score >= 0.5 or (text_word_count < 100 and script_ratio > 0.3)
    
    return {
        "is_js_heavy": needs_rendering,
        "confidence": round(confidence_score, 2),
        "signals": signals,
        "framework_hints": list(set(framework_hints)),  # Remove duplicates
        "metrics": {
            "text_word_count": text_word_count,
            "script_count": script_count,
            "script_ratio": round(script_ratio, 3),
            "html_size": html_size
        },
        "recommendation": "render" if needs_rendering else "static"
    }


def should_use_rendering(detection_result: Dict[str, Any]) -> bool:
    """
    Determine if a site should use headless rendering based on detection.
    
    Args:
        detection_result: Output from detect_js_framework()
        
    Returns:
        Boolean indicating if rendering is recommended
    """
    return detection_result.get("is_js_heavy", False)


def get_detection_summary(detection_result: Dict[str, Any]) -> str:
    """
    Generate human-readable summary of detection results.
    
    Args:
        detection_result: Output from detect_js_framework()
        
    Returns:
        Summary string for logging/UI
    """
    if not detection_result.get("is_js_heavy"):
        return "Static HTML site - no rendering needed"
    
    frameworks = detection_result.get("framework_hints", [])
    confidence = detection_result.get("confidence", 0)
    metrics = detection_result.get("metrics", {})
    
    framework_str = ", ".join(frameworks) if frameworks else "Unknown framework"
    
    return (
        f"JavaScript-heavy site detected ({framework_str}) - "
        f"Confidence: {confidence:.0%} - "
        f"{metrics.get('text_word_count', 0)} words visible"
    )
