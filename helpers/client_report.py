"""
Client-facing report generation.
Creates professional audit reports that users can send to business owners.
"""

import json
from typing import Dict, Any, Optional
from openai import OpenAI
from helpers.technographics import classify_tech_health


def generate_client_report(
    lead_data: Dict[str, Any],
    agency_name: str = "",
    agency_website: str = "",
    agency_tagline: str = ""
) -> Dict[str, Any]:
    technographics = lead_data.get("technographics") or {}
    score_reasoning = lead_data.get("score_reasoning") or {}
    score = lead_data.get("score", 0)
    business_name = lead_data.get("name", "Business")
    website = lead_data.get("website", "")
    
    if isinstance(score_reasoning, str):
        try:
            score_reasoning = json.loads(score_reasoning)
        except (ValueError, TypeError):
            score_reasoning = {}
    
    plain_report = score_reasoning.get("plain_english_report", {})
    tech_health = classify_tech_health(technographics) if technographics.get("detected") else {"green": [], "amber": [], "red": []}
    
    tech_summary = _build_tech_summary(technographics)
    
    client = OpenAI(timeout=60.0)
    
    prompt = f"""Generate a professional website audit report for a business owner. This report will be sent directly to the business by a web services agency.

BUSINESS: {business_name}
WEBSITE: {website}
OVERALL SCORE: {score}/100

TECHNOLOGY FINDINGS:
{tech_summary}

STRENGTHS FOUND:
{json.dumps(plain_report.get('strengths', []), indent=2)}

WEAKNESSES FOUND:
{json.dumps(plain_report.get('weaknesses', []), indent=2)}

TECHNOLOGY OBSERVATIONS:
{plain_report.get('technology_observations', 'Not available')}

GREEN (Good): {json.dumps([item['label'] + ' - ' + item['detail'] for item in tech_health['green']])}
AMBER (Needs attention): {json.dumps([item['label'] + ' - ' + item['detail'] for item in tech_health['amber']])}
RED (Critical): {json.dumps([item['label'] + ' - ' + item['detail'] for item in tech_health['red']])}

Write the report in this JSON format:
{{
    "executive_summary": "2-3 sentence overview of the website's health aimed at a non-technical business owner. Be professional, not alarmist.",
    "overall_grade": "A/B/C/D/F based on score (A=80-100, B=60-79, C=40-59, D=20-39, F=0-19)",
    "sections": [
        {{
            "title": "Section name (e.g., Security & Trust, Mobile Experience, Search Visibility, Analytics & Tracking, Social Media Presence, Technical Health)",
            "status": "good/needs_attention/critical",
            "finding": "What we found - plain English, no jargon, 1-2 sentences",
            "impact": "Why this matters for the business - focus on customer impact, lost revenue, competitor advantage. 1-2 sentences.",
            "recommendation": "What they should do about it - actionable, specific. 1 sentence."
        }}
    ],
    "top_priorities": ["Top 3 things this business should address first - specific and actionable"],
    "positive_highlights": ["2-3 genuine positive things about their website to start on a good note"]
}}

RULES:
- Write for a non-technical business owner - NO jargon
- Be professional and helpful, not salesy or alarmist
- Reference specific technology findings (e.g., "Your site uses WordPress 5.2" not "Your CMS is outdated")
- Focus on business impact: lost customers, missed opportunities, competitor advantage
- Each section should have clear red/amber/green status
- Generate 5-8 sections covering the most relevant findings
- Be honest but constructive - frame issues as opportunities"""

    try:
        import time as _time
        print(f"[client_report] Starting OpenAI call for {business_name} ({website})")
        _start = _time.time()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional web consultant creating audit reports for business owners. Write clearly, professionally, and focus on business impact rather than technical jargon."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            response_format={"type": "json_object"}
        )
        _elapsed = _time.time() - _start
        print(f"[client_report] OpenAI call completed in {_elapsed:.1f}s for {business_name}")
        
        report = json.loads(response.choices[0].message.content)
        
        report["business_name"] = business_name
        report["website"] = website
        report["score"] = score
        report["agency_name"] = agency_name
        report["agency_website"] = agency_website
        report["agency_tagline"] = agency_tagline
        report["tech_health"] = tech_health
        report["technographics"] = technographics
        
        return report
    
    except Exception as e:
        import time as _time
        print(f"[client_report] OpenAI call FAILED for {business_name}: {type(e).__name__}: {e}")
        error_msg = str(e).lower()
        if "timed out" in error_msg or "timeout" in error_msg or "APITimeoutError" in type(e).__name__:
            return {
                "error": "Report generation timed out",
                "timeout": True,
                "business_name": business_name,
                "website": website,
                "score": score
            }
        return {
            "error": str(e),
            "business_name": business_name,
            "website": website,
            "score": score
        }


def generate_internal_report(lead_data: Dict[str, Any]) -> Dict[str, Any]:
    technographics = lead_data.get("technographics") or {}
    score_reasoning = lead_data.get("score_reasoning") or {}
    score = lead_data.get("score", 0)
    business_name = lead_data.get("name", "Business")
    website = lead_data.get("website", "")
    
    if isinstance(score_reasoning, str):
        try:
            score_reasoning = json.loads(score_reasoning)
        except (ValueError, TypeError):
            score_reasoning = {}
    
    plain_report = score_reasoning.get("plain_english_report", {})
    tech_health = classify_tech_health(technographics) if technographics.get("detected") else {"green": [], "amber": [], "red": []}
    hybrid = score_reasoning.get("hybrid_breakdown", {})
    
    return {
        "business_name": business_name,
        "website": website,
        "score": score,
        "contact_name": lead_data.get("contact_name", ""),
        "email": lead_data.get("email", ""),
        "phone": lead_data.get("phone", ""),
        "address": lead_data.get("address", ""),
        "scoring": {
            "total": score,
            "heuristic": hybrid.get("heuristic_score", 0),
            "ai": hybrid.get("ai_score", 0),
            "confidence": score_reasoning.get("confidence", 0),
            "heuristic_categories": hybrid.get("heuristic_categories", {}),
            "ai_categories": hybrid.get("ai_categories", {}),
        },
        "report": plain_report,
        "technographics": technographics,
        "tech_health": tech_health,
        "ai_justifications": score_reasoning.get("ai_justifications", {}),
        "evidence": score_reasoning.get("evidence", {}),
        "social_links": technographics.get("social_links", {}) if technographics else {},
        "render_pathway": score_reasoning.get("render_pathway", ""),
    }


def _build_tech_summary(technographics: Dict[str, Any]) -> str:
    if not technographics or not technographics.get("detected"):
        return "No technology data available"
    
    lines = []
    cms = technographics.get("cms", {})
    cms_name = cms.get("name", "Unknown")
    cms_version = technographics.get("cms_version")
    if cms_name != "Custom/Unknown":
        lines.append(f"CMS: {cms_name}{f' version {cms_version}' if cms_version else ''}")
    else:
        lines.append("CMS: Custom-built or unidentified platform")
    
    lines.append(f"SSL/HTTPS: {'Active' if technographics.get('ssl') else 'NOT ACTIVE'}")
    lines.append(f"Mobile Responsive: {'Yes' if technographics.get('mobile_responsive') else 'No'}")
    
    analytics = technographics.get("analytics", {})
    analytics_items = []
    if analytics.get("google_analytics"):
        analytics_items.append("Google Analytics")
    if analytics.get("meta_pixel"):
        analytics_items.append("Meta/Facebook Pixel")
    analytics_items.extend(analytics.get("other", []))
    lines.append(f"Analytics: {', '.join(analytics_items) if analytics_items else 'None detected'}")
    
    jquery = technographics.get("jquery", {})
    if jquery.get("present"):
        lines.append(f"jQuery: Version {jquery.get('version', 'unknown')}")
    
    lines.append(f"Cookie Consent: {'Present' if technographics.get('cookie_consent') else 'Not detected'}")
    lines.append(f"Favicon: {'Present' if technographics.get('favicon') else 'Missing'}")
    
    og = technographics.get("og_tags", {})
    lines.append(f"Open Graph: Title={'Yes' if og.get('has_og_title') else 'No'}, Image={'Yes' if og.get('has_og_image') else 'No'}")
    
    social = technographics.get("social_links", {})
    active = [k.title() for k, v in social.items() if v]
    lines.append(f"Social Links: {', '.join(active) if active else 'None found'}")
    
    bloat = technographics.get("page_bloat", {})
    lines.append(f"External Resources: {bloat.get('external_scripts', 0)} scripts, {bloat.get('external_stylesheets', 0)} stylesheets")
    
    return "\n".join(lines)


def render_client_report_html(report: Dict[str, Any]) -> str:
    if "error" in report:
        return f"<html><body><h1>Report generation failed</h1><p>{report['error']}</p></body></html>"
    
    business_name = report.get("business_name", "Business")
    website = report.get("website", "")
    score = report.get("score", 0)
    grade = report.get("overall_grade", "N/A")
    executive_summary = report.get("executive_summary", "")
    sections = report.get("sections", [])
    top_priorities = report.get("top_priorities", [])
    positive_highlights = report.get("positive_highlights", [])
    agency_name = report.get("agency_name", "")
    agency_website = report.get("agency_website", "")
    agency_tagline = report.get("agency_tagline", "")
    
    grade_color = {"A": "#16a34a", "B": "#22c55e", "C": "#eab308", "D": "#f97316", "F": "#ef4444"}.get(grade, "#6b7280")
    
    sections_html = ""
    for section in sections:
        status = section.get("status", "needs_attention")
        status_color = {"good": "#16a34a", "needs_attention": "#eab308", "critical": "#ef4444"}.get(status, "#6b7280")
        status_icon = {"good": "&#10004;", "needs_attention": "&#9888;", "critical": "&#10060;"}.get(status, "&#8226;")
        status_label = {"good": "Good", "needs_attention": "Needs Attention", "critical": "Critical"}.get(status, "Unknown")
        
        sections_html += f"""
        <div style="border: 1px solid #e5e7eb; border-radius: 12px; padding: 20px; margin-bottom: 16px; border-left: 4px solid {status_color};">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <h3 style="margin: 0; font-size: 16px; color: #1f2937;">{section.get('title', '')}</h3>
                <span style="background: {status_color}15; color: {status_color}; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600;">{status_icon} {status_label}</span>
            </div>
            <p style="margin: 8px 0 4px; color: #374151; font-size: 14px;"><strong>Finding:</strong> {section.get('finding', '')}</p>
            <p style="margin: 4px 0; color: #6b7280; font-size: 13px;"><strong>Why it matters:</strong> {section.get('impact', '')}</p>
            <p style="margin: 4px 0 0; color: #7c3aed; font-size: 13px; font-weight: 500;"><strong>Recommendation:</strong> {section.get('recommendation', '')}</p>
        </div>"""
    
    priorities_html = ""
    for i, priority in enumerate(top_priorities, 1):
        priorities_html += f'<div style="display: flex; gap: 12px; align-items: flex-start; margin-bottom: 12px;"><span style="background: #7c3aed; color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px; flex-shrink: 0;">{i}</span><span style="color: #374151; font-size: 14px; line-height: 1.6; padding-top: 3px;">{priority}</span></div>'
    
    positives_html = ""
    for highlight in positive_highlights:
        positives_html += f'<div style="display: flex; gap: 8px; align-items: flex-start; margin-bottom: 8px;"><span style="color: #16a34a; font-size: 16px;">&#10004;</span><span style="color: #374151; font-size: 14px;">{highlight}</span></div>'
    
    footer_html = ""
    if agency_name:
        footer_html = f"""
        <div style="margin-top: 40px; padding: 24px; background: linear-gradient(135deg, #f5f3ff 0%, #fdf4ff 100%); border-radius: 12px; text-align: center; border: 1px solid rgba(139, 92, 246, 0.2);">
            <p style="margin: 0 0 8px; font-size: 16px; font-weight: 700; color: #7c3aed;">Ready to improve your website?</p>
            <p style="margin: 0 0 12px; color: #6b7280; font-size: 14px;">{agency_tagline or 'We can help you address these findings and grow your online presence.'}</p>
            <p style="margin: 0; font-weight: 600; color: #1f2937; font-size: 15px;">{agency_name}</p>
            {f'<p style="margin: 4px 0 0; color: #7c3aed; font-size: 13px;">{agency_website}</p>' if agency_website else ''}
        </div>"""
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Website Audit Report - {business_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #ffffff; color: #1f2937; line-height: 1.6; }}
        @media print {{
            body {{ padding: 0; }}
            .no-print {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div style="max-width: 700px; margin: 0 auto; padding: 40px 24px;">
        <div style="text-align: center; margin-bottom: 32px; padding-bottom: 24px; border-bottom: 2px solid #f3f4f6;">
            <h1 style="font-size: 24px; font-weight: 700; color: #1f2937; margin-bottom: 4px;">Website Audit Report</h1>
            <p style="color: #6b7280; font-size: 14px;">Prepared for {business_name}</p>
            <p style="color: #9ca3af; font-size: 12px; margin-top: 4px;">{website}</p>
        </div>
        
        <div style="display: flex; justify-content: center; gap: 24px; margin-bottom: 32px;">
            <div style="text-align: center; padding: 20px 32px; background: #f9fafb; border-radius: 12px; border: 1px solid #e5e7eb;">
                <div style="font-size: 36px; font-weight: 800; color: {grade_color};">{score}/100</div>
                <div style="font-size: 13px; color: #6b7280; margin-top: 4px;">Overall Score</div>
            </div>
            <div style="text-align: center; padding: 20px 32px; background: #f9fafb; border-radius: 12px; border: 1px solid #e5e7eb;">
                <div style="font-size: 36px; font-weight: 800; color: {grade_color};">{grade}</div>
                <div style="font-size: 13px; color: #6b7280; margin-top: 4px;">Grade</div>
            </div>
        </div>
        
        <div style="background: #f9fafb; border-radius: 12px; padding: 20px; margin-bottom: 28px; border: 1px solid #e5e7eb;">
            <h2 style="font-size: 16px; font-weight: 600; color: #1f2937; margin-bottom: 8px;">Executive Summary</h2>
            <p style="color: #374151; font-size: 14px; line-height: 1.7;">{executive_summary}</p>
        </div>
        
        {f'<div style="margin-bottom: 28px;"><h2 style="font-size: 16px; font-weight: 600; color: #16a34a; margin-bottom: 12px;">What You Are Doing Well</h2>{positives_html}</div>' if positives_html else ''}
        
        <div style="margin-bottom: 28px;">
            <h2 style="font-size: 18px; font-weight: 600; color: #1f2937; margin-bottom: 16px;">Detailed Findings</h2>
            {sections_html}
        </div>
        
        {f'<div style="background: linear-gradient(135deg, #fef3c7 0%, #fef9c3 100%); border-radius: 12px; padding: 20px; margin-bottom: 28px; border: 1px solid #fbbf24;"><h2 style="font-size: 16px; font-weight: 600; color: #92400e; margin-bottom: 12px;">Top Priorities</h2>{priorities_html}</div>' if priorities_html else ''}
        
        {footer_html}
        
        <div style="margin-top: 32px; text-align: center; color: #9ca3af; font-size: 11px;">
            <p>This report was generated automatically based on publicly available website data.</p>
        </div>
    </div>
</body>
</html>"""
