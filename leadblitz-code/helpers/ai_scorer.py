"""
AI-based website review with strict evidence requirements.
Returns structured scores (0-50 points) with mandatory evidence citations.
"""

import json
from typing import Dict, Any
from openai import OpenAI


SYSTEM_PROMPT = """You are a website audit expert helping entrepreneurs identify sales opportunities for web development and AI integration services.

Your role: Provide clear, actionable insights in plain English that help the user understand:
1. What this business does well online
2. Where they're falling short
3. Specific opportunities to add value (AI tools, chatbots, modern features, design improvements)

CRITICAL RULES:
1. ONLY use text fragments and elements provided by the caller
2. Do not guess about hidden JS content or features you cannot see
3. If evidence is insufficient, mark "insufficient_evidence": true and reduce confidence
4. Write for a non-technical audience - avoid jargon, use plain English
5. Focus on business impact and sales opportunities"""


def score_with_ai(
    site_content: Dict[str, Any],
    heuristic_evidence: Dict[str, Any],
    final_url: str,
    rendering_limitations: bool,
    technographics: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Call OpenAI to score website based on extracted content and heuristics.
    
    Args:
        site_content: Extracted HTML elements (title, h1s, CTAs, etc.)
        heuristic_evidence: Evidence from deterministic checks
        final_url: Final URL after redirects
        rendering_limitations: Whether HTML appears incomplete
        technographics: Detected technology stack data
        
    Returns:
        Dict with category scores, justifications, confidence
    """
    
    tech_section = ""
    if technographics and technographics.get("detected"):
        cms = technographics.get("cms", {})
        cms_name = cms.get("name", "Unknown")
        cms_version = technographics.get("cms_version")
        analytics = technographics.get("analytics", {})
        jquery = technographics.get("jquery", {})
        social = technographics.get("social_links", {})
        active_socials = [k for k, v in social.items() if v]
        bloat = technographics.get("page_bloat", {})
        
        tech_section = f"""
TECHNOLOGY STACK DETECTED:
- CMS: {cms_name}{f' version {cms_version}' if cms_version else ''}
- SSL/HTTPS: {'Yes' if technographics.get('ssl') else 'No'}
- Mobile Responsive: {'Yes' if technographics.get('mobile_responsive') else 'No'}
- Google Analytics: {'Yes' if analytics.get('google_analytics') else 'No'}
- Meta/Facebook Pixel: {'Yes' if analytics.get('meta_pixel') else 'No'}
- Other Analytics: {', '.join(analytics.get('other', [])) or 'None'}
- jQuery: {'Yes, version ' + jquery.get('version', 'unknown') if jquery.get('present') else 'No'}
- Cookie Consent: {'Yes' if technographics.get('cookie_consent') else 'No'}
- Open Graph Tags: Title={'Yes' if technographics.get('og_tags', {}).get('has_og_title') else 'No'}, Image={'Yes' if technographics.get('og_tags', {}).get('has_og_image') else 'No'}
- Favicon: {'Yes' if technographics.get('favicon') else 'No'}
- Social Links: {', '.join(active_socials) if active_socials else 'None found'}
- External Resources: {bloat.get('external_scripts', 0)} scripts, {bloat.get('external_stylesheets', 0)} stylesheets
"""
    
    user_content = f"""Please review this website and provide scores with evidence.

URL: {final_url}
Rendering limitations: {"Yes - content may be incomplete due to JavaScript" if rendering_limitations else "No"}

EXTRACTED CONTENT:
---
Title: {site_content.get('title', 'N/A')}

H1 Headlines: {', '.join(site_content.get('h1_tags', [])) or 'None found'}

H2 Headings: {', '.join(site_content.get('h2_tags', [])[:5]) or 'None found'}

CTA Buttons: {', '.join(site_content.get('cta_buttons', [])) or 'None found'}

Navigation Links: {', '.join(site_content.get('nav_links', [])[:15]) or 'None found'}

Image Alt Texts: {', '.join(site_content.get('image_alts', [])[:5]) or 'None found'}

Link Texts (sample): {', '.join(site_content.get('link_texts', [])[:20]) or 'None found'}

Text Excerpt (first 2000 chars):
{site_content.get('text_excerpt', '')[:2000]}

HEURISTIC FINDINGS:
{json.dumps(heuristic_evidence, indent=2)}
{tech_section}---

SCORING RUBRIC (max 50 points):

1. Brand Clarity (0-12): Is the offer obvious above the fold? Who it's for? Quote H1/headline.
2. Visual Design (0-10): Consistency, whitespace, typography. Cite visible elements or explain N/A.
3. Conversion UX (0-12): Clear CTAs, contact routes, booking/quote flows. Quote CTA texts.
4. Trust & Proof (0-10): Testimonials, case studies, awards, real photos, social proof. Quote snippets.
5. Accessibility (0-6): Alt texts present, contrast keywords, aria attributes visible.

IMPORTANT: Reference the technology stack in your report. For example:
- If using WordPress with an old version, mention specific security implications
- If no Google Analytics, mention they have no traffic visibility
- If no SSL, explain how this affects customer trust and Google rankings
- Reference specific CMS, jQuery versions, missing features by name

Return JSON with:
{{
  "category_scores": {{
    "brand": 0-12,
    "visual": 0-10,
    "conversion": 0-12,
    "trust": 0-10,
    "a11y": 0-6
  }},
  "justifications": {{
    "brand": "Quote H1 and explain who it's for...",
    "visual": "Describe visible design elements...",
    "conversion": "Quote CTA texts and describe flow...",
    "trust": "Quote testimonials/proof or explain absence...",
    "a11y": "List alt texts found or note missing..."
  }},
  "plain_english_report": {{
    "strengths": ["List 2-3 specific things this website does well - be concrete, reference specific technologies found"],
    "weaknesses": ["List 2-4 specific areas that need improvement - reference specific technology gaps like missing analytics, old CMS versions, no SSL"],
    "technology_observations": "Detailed paragraph about the tech stack. Reference specific CMS name and version, jQuery version, whether they have analytics, SSL status, social presence. Be specific - e.g. 'This site runs WordPress 5.2 which has known security vulnerabilities' or 'No Google Analytics means they have zero visibility into their traffic'",
    "sales_opportunities": ["List 3-5 specific services you could sell them based on their tech gaps: e.g., 'Upgrade from WordPress 5.2 to fix security vulnerabilities', 'Install Google Analytics for traffic insights', 'Add SSL certificate to improve trust and SEO'"]
  }},
  "insufficient_evidence": false,
  "confidence": 0.0
}}

IMPORTANT: Write the plain_english_report in simple, clear language that helps identify sales opportunities. Be specific and actionable. Reference actual technology findings.
If content is sparse but quality indicators exist (good title, clear H1, HTTPS, contact info), don't penalize heavily - just lower confidence.
If you cannot find evidence for a category, score it low and explain in justifications."""

    try:
        client = OpenAI()
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        
        # Validate and clamp scores
        category_scores = result.get("category_scores", {})
        clamped_scores = {
            "brand": max(0, min(12, category_scores.get("brand", 0))),
            "visual": max(0, min(10, category_scores.get("visual", 0))),
            "conversion": max(0, min(12, category_scores.get("conversion", 0))),
            "trust": max(0, min(10, category_scores.get("trust", 0))),
            "a11y": max(0, min(6, category_scores.get("a11y", 0)))
        }
        
        # Handle insufficient evidence with grace
        insufficient = result.get("insufficient_evidence", False)
        confidence = result.get("confidence", 0.7)
        
        # If insufficient evidence but heuristic scores are decent, maintain minimum AI score
        total_ai = sum(clamped_scores.values())
        if insufficient and total_ai < 20 and heuristic_evidence.get("text_word_count", 0) > 150:
            # Bump to minimum viable score
            adjustment = (20 - total_ai) / 5
            for key in clamped_scores:
                clamped_scores[key] = int(clamped_scores[key] + adjustment)
        
        return {
            "category_scores": clamped_scores,
            "justifications": result.get("justifications", {}),
            "plain_english_report": result.get("plain_english_report", {}),
            "insufficient_evidence": insufficient,
            "confidence": max(0.0, min(1.0, confidence))
        }
        
    except json.JSONDecodeError as e:
        # AI didn't return valid JSON
        return {
            "category_scores": {
                "brand": 0,
                "visual": 0,
                "conversion": 0,
                "trust": 0,
                "a11y": 0
            },
            "justifications": {
                "error": f"AI response was not valid JSON: {str(e)}"
            },
            "insufficient_evidence": True,
            "confidence": 0.0
        }
    except Exception as e:
        # OpenAI error
        return {
            "category_scores": {
                "brand": 0,
                "visual": 0,
                "conversion": 0,
                "trust": 0,
                "a11y": 0
            },
            "justifications": {
                "error": f"AI scoring failed: {str(e)}"
            },
            "insufficient_evidence": True,
            "confidence": 0.0
        }


def combine_scores(heuristic: Dict[str, Any], ai_review: Dict[str, Any]) -> Dict[str, Any]:
    """
    Combine heuristic and AI scores into final result.
    
    Args:
        heuristic: Result from site_heuristics.score_site_heuristics()
        ai_review: Result from score_with_ai()
        
    Returns:
        Combined scores with confidence and breakdown
    """
    heuristic_total = heuristic.get("total_heuristic", 0)
    ai_total = sum(ai_review.get("category_scores", {}).values())
    
    # Clamp AI total to 50
    ai_total_clamped = max(0, min(50, ai_total))
    
    # Final score: heuristic (0-50) + AI (0-50)
    final_score = round(heuristic_total + ai_total_clamped)
    
    # Calculate confidence
    word_count = heuristic.get("evidence", {}).get("text_word_count", 0)
    heuristic_confidence = 0.9 if word_count > 150 else 0.6
    ai_confidence = ai_review.get("confidence", 0.6)
    
    combined_confidence = (heuristic_confidence + ai_confidence) / 2
    
    return {
        "final_score": final_score,
        "confidence": round(combined_confidence, 2),
        "heuristic_score": heuristic_total,
        "ai_score": int(ai_total_clamped),
        "breakdown": {
            "heuristic": heuristic.get("scores", {}),
            "ai": ai_review.get("category_scores", {})
        },
        "evidence": heuristic.get("evidence", {}),
        "ai_justifications": ai_review.get("justifications", {}),
        "plain_english_report": ai_review.get("plain_english_report", {}),
        "rendering_limitations": heuristic.get("rendering_limitations", False),
        "insufficient_evidence": ai_review.get("insufficient_evidence", False)
    }
