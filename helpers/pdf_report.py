import io
import json
from datetime import datetime
from typing import Dict, Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.graphics.shapes import Drawing, Rect, String, Circle
from reportlab.graphics import renderPDF


PURPLE = colors.HexColor("#7c3aed")
PURPLE_LIGHT = colors.HexColor("#a78bfa")
PURPLE_BG = colors.HexColor("#f5f3ff")
GREEN = colors.HexColor("#16a34a")
GREEN_BG = colors.HexColor("#f0fdf4")
AMBER = colors.HexColor("#d97706")
AMBER_BG = colors.HexColor("#fffbeb")
RED = colors.HexColor("#dc2626")
RED_BG = colors.HexColor("#fef2f2")
DARK = colors.HexColor("#1f2937")
GRAY = colors.HexColor("#6b7280")
LIGHT_GRAY = colors.HexColor("#e5e7eb")
WHITE = colors.white
BG_CARD = colors.HexColor("#f9fafb")


def _get_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        'ReportTitle',
        parent=styles['Title'],
        fontSize=22,
        textColor=DARK,
        spaceAfter=4,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        'ReportSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=GRAY,
        spaceAfter=20,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=PURPLE,
        spaceBefore=16,
        spaceAfter=8,
        fontName='Helvetica-Bold',
    ))
    styles.add(ParagraphStyle(
        'BodyText2',
        parent=styles['Normal'],
        fontSize=10,
        textColor=DARK,
        leading=15,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        'SmallGray',
        parent=styles['Normal'],
        fontSize=9,
        textColor=GRAY,
        leading=13,
    ))
    styles.add(ParagraphStyle(
        'BulletItem',
        parent=styles['Normal'],
        fontSize=10,
        textColor=DARK,
        leading=15,
        leftIndent=16,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        'FindingTitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=DARK,
        fontName='Helvetica-Bold',
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        'StatusBadge',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica-Bold',
        alignment=TA_RIGHT,
    ))
    styles.add(ParagraphStyle(
        'FooterText',
        parent=styles['Normal'],
        fontSize=8,
        textColor=GRAY,
        alignment=TA_CENTER,
    ))
    return styles


def _score_color(score: int):
    if score >= 80:
        return GREEN
    elif score >= 60:
        return colors.HexColor("#22c55e")
    elif score >= 40:
        return AMBER
    elif score >= 20:
        return colors.HexColor("#f97316")
    return RED


def _grade_from_score(score: int) -> str:
    if score >= 80: return "A"
    if score >= 60: return "B"
    if score >= 40: return "C"
    if score >= 20: return "D"
    return "F"


def _status_color(status: str):
    return {"good": GREEN, "needs_attention": AMBER, "critical": RED}.get(status, GRAY)


def _status_label(status: str) -> str:
    return {"good": "Good", "needs_attention": "Needs Attention", "critical": "Critical"}.get(status, "Unknown")


def _safe(text: str) -> str:
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _header_footer(canvas, doc, title_text="Website Audit Report", agency_name=""):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GRAY)
    left_text = agency_name or "LeadBlitz"
    canvas.drawString(doc.leftMargin, doc.height + doc.topMargin + 12, left_text)
    canvas.drawRightString(
        doc.width + doc.leftMargin,
        doc.height + doc.topMargin + 12,
        title_text
    )
    canvas.setStrokeColor(LIGHT_GRAY)
    canvas.line(
        doc.leftMargin,
        doc.height + doc.topMargin + 8,
        doc.width + doc.leftMargin,
        doc.height + doc.topMargin + 8,
    )
    canvas.drawString(doc.leftMargin, 25, f"Generated {datetime.now().strftime('%B %d, %Y')}")
    canvas.drawRightString(
        doc.width + doc.leftMargin, 25,
        f"Page {doc.page}"
    )
    canvas.restoreState()


def _build_score_table(score: int, grade: str, styles):
    sc = _score_color(score)
    score_para = Paragraph(
        f'<font size="28" color="{sc.hexval()}">{score}</font>'
        f'<font size="14" color="{GRAY.hexval()}">/100</font>',
        styles['BodyText2']
    )
    score_label = Paragraph(
        '<font size="9" color="#6b7280">Overall Score</font>',
        styles['SmallGray']
    )
    grade_para = Paragraph(
        f'<font size="28" color="{sc.hexval()}">{grade}</font>',
        styles['BodyText2']
    )
    grade_label = Paragraph(
        '<font size="9" color="#6b7280">Grade</font>',
        styles['SmallGray']
    )

    data = [[score_para, grade_para], [score_label, grade_label]]
    t = Table(data, colWidths=[2.5 * inch, 2.5 * inch])
    t.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, -1), BG_CARD),
        ('BOX', (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    return t


def _build_finding_block(section: Dict, styles) -> list:
    status = section.get("status", "needs_attention")
    sc = _status_color(status)
    label = _status_label(status)

    elements = []

    title_text = _safe(section.get("title", ""))
    badge = f'<font color="{sc.hexval()}">[{label}]</font>'

    title_row = Table(
        [[
            Paragraph(f'<b>{title_text}</b>', styles['FindingTitle']),
            Paragraph(badge, styles['StatusBadge']),
        ]],
        colWidths=[4 * inch, 1.8 * inch],
    )
    title_row.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (-1, -1), (-1, -1), 0),
    ]))
    elements.append(title_row)

    finding = section.get("finding", "")
    if finding:
        elements.append(Paragraph(
            f'<b>Finding:</b> {_safe(finding)}',
            styles['BodyText2']
        ))

    impact = section.get("impact", "")
    if impact:
        elements.append(Paragraph(
            f'<font color="#6b7280"><b>Why it matters:</b> {_safe(impact)}</font>',
            styles['SmallGray']
        ))

    rec = section.get("recommendation", "")
    if rec:
        elements.append(Paragraph(
            f'<font color="{PURPLE.hexval()}"><b>Recommendation:</b> {_safe(rec)}</font>',
            styles['BodyText2']
        ))

    elements.append(Spacer(1, 4))

    wrapper = Table(
        [[elements]],
        colWidths=[5.8 * inch],
    )
    wrapper.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), WHITE),
        ('BOX', (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ('LINEWIDTH', (0, 0), (0, -1), 3),
        ('LINECOLOR', (0, 0), (0, -1), sc),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 14),
        ('RIGHTPADDING', (0, 0), (-1, -1), 14),
    ]))

    return [wrapper, Spacer(1, 8)]


def generate_client_pdf(report_data: Dict[str, Any]) -> bytes:
    buffer = io.BytesIO()
    styles = _get_styles()

    business_name = report_data.get("business_name", "Business")
    website = report_data.get("website", "")
    score = report_data.get("score", 0)
    grade = report_data.get("overall_grade", _grade_from_score(score))
    executive_summary = report_data.get("executive_summary", "")
    sections = report_data.get("sections", [])
    top_priorities = report_data.get("top_priorities", [])
    positive_highlights = report_data.get("positive_highlights", [])
    agency_name = report_data.get("agency_name", "")
    agency_website = report_data.get("agency_website", "")
    agency_tagline = report_data.get("agency_tagline", "")

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=0.8 * inch, bottomMargin=0.6 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    )

    story = []

    story.append(Paragraph("Website Audit Report", styles['ReportTitle']))
    story.append(Paragraph(
        f'Prepared for <b>{_safe(business_name)}</b><br/>'
        f'<font size="9" color="#9ca3af">{_safe(website)}</font>',
        styles['ReportSubtitle']
    ))
    story.append(Spacer(1, 8))

    story.append(_build_score_table(score, grade, styles))
    story.append(Spacer(1, 16))

    if executive_summary:
        story.append(Paragraph("Executive Summary", styles['SectionHeader']))
        summary_table = Table(
            [[Paragraph(_safe(executive_summary), styles['BodyText2'])]],
            colWidths=[5.8 * inch],
        )
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), BG_CARD),
            ('BOX', (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('LEFTPADDING', (0, 0), (-1, -1), 14),
            ('RIGHTPADDING', (0, 0), (-1, -1), 14),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 12))

    if positive_highlights:
        story.append(Paragraph("What You're Doing Well", styles['SectionHeader']))
        for h in positive_highlights:
            story.append(Paragraph(
                f'<font color="{GREEN.hexval()}">&#10004;</font> {_safe(h)}',
                styles['BulletItem']
            ))
        story.append(Spacer(1, 8))

    if sections:
        story.append(Paragraph("Detailed Findings", styles['SectionHeader']))
        for section in sections:
            story.extend(_build_finding_block(section, styles))

    if top_priorities:
        story.append(Spacer(1, 8))
        story.append(Paragraph("Top Priorities", styles['SectionHeader']))
        prio_elements = []
        for i, p in enumerate(top_priorities, 1):
            prio_elements.append(Paragraph(
                f'<font color="{PURPLE.hexval()}"><b>{i}.</b></font> {_safe(p)}',
                styles['BulletItem']
            ))
        prio_table = Table(
            [[prio_elements]],
            colWidths=[5.8 * inch],
        )
        prio_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#fffbeb")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#fbbf24")),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('LEFTPADDING', (0, 0), (-1, -1), 14),
            ('RIGHTPADDING', (0, 0), (-1, -1), 14),
        ]))
        story.append(prio_table)

    if agency_name:
        story.append(Spacer(1, 24))
        cta_content = []
        cta_content.append(Paragraph(
            '<font size="13" color="#7c3aed"><b>Ready to improve your website?</b></font>',
            ParagraphStyle('CTA', alignment=TA_CENTER, spaceAfter=6)
        ))
        tagline = agency_tagline or "We can help you address these findings and grow your online presence."
        cta_content.append(Paragraph(
            f'<font size="10" color="#6b7280">{_safe(tagline)}</font>',
            ParagraphStyle('CTASub', alignment=TA_CENTER, spaceAfter=8)
        ))
        cta_content.append(Paragraph(
            f'<font size="11" color="#1f2937"><b>{_safe(agency_name)}</b></font>',
            ParagraphStyle('CTAName', alignment=TA_CENTER, spaceAfter=2)
        ))
        if agency_website:
            cta_content.append(Paragraph(
                f'<font size="10" color="#7c3aed">{_safe(agency_website)}</font>',
                ParagraphStyle('CTAWeb', alignment=TA_CENTER)
            ))
        cta_table = Table([[cta_content]], colWidths=[5.8 * inch])
        cta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), PURPLE_BG),
            ('BOX', (0, 0), (-1, -1), 0.5, PURPLE_LIGHT),
            ('TOPPADDING', (0, 0), (-1, -1), 16),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
            ('LEFTPADDING', (0, 0), (-1, -1), 20),
            ('RIGHTPADDING', (0, 0), (-1, -1), 20),
        ]))
        story.append(cta_table)

    story.append(Spacer(1, 20))
    story.append(Paragraph(
        "This report was generated automatically based on publicly available website data.",
        styles['FooterText']
    ))

    def on_page(canvas, doc_ref):
        _header_footer(canvas, doc_ref, "Website Audit Report", agency_name)

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buffer.getvalue()


def generate_internal_pdf(report_data: Dict[str, Any]) -> bytes:
    buffer = io.BytesIO()
    styles = _get_styles()

    business_name = report_data.get("business_name", "Business")
    website = report_data.get("website", "")
    score = report_data.get("score", 0)
    grade = _grade_from_score(score)
    contact_name = report_data.get("contact_name", "")
    email = report_data.get("email", "")
    phone = report_data.get("phone", "")
    address = report_data.get("address", "")
    scoring = report_data.get("scoring", {})
    report = report_data.get("report", {})
    tech_health = report_data.get("tech_health", {})
    technographics = report_data.get("technographics", {})
    social_links = report_data.get("social_links", {})

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=0.8 * inch, bottomMargin=0.6 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    )

    story = []

    story.append(Paragraph("Internal Lead Report", styles['ReportTitle']))
    story.append(Paragraph(
        f'<b>{_safe(business_name)}</b><br/>'
        f'<font size="9" color="#9ca3af">{_safe(website)}</font>',
        styles['ReportSubtitle']
    ))
    story.append(Spacer(1, 8))

    story.append(_build_score_table(score, grade, styles))
    story.append(Spacer(1, 12))

    contact_rows = []
    if contact_name:
        contact_rows.append(["Contact", contact_name])
    if email:
        contact_rows.append(["Email", email])
    if phone:
        contact_rows.append(["Phone", phone])
    if address:
        contact_rows.append(["Address", address])

    if contact_rows:
        story.append(Paragraph("Contact Information", styles['SectionHeader']))
        ct = Table(contact_rows, colWidths=[1.2 * inch, 4.6 * inch])
        ct.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), GRAY),
            ('TEXTCOLOR', (1, 0), (1, -1), DARK),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, LIGHT_GRAY),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(ct)
        story.append(Spacer(1, 8))

    if scoring:
        story.append(Paragraph("Score Breakdown", styles['SectionHeader']))
        score_rows = [
            ["Component", "Score"],
            ["Total Score", str(scoring.get("total", score))],
            ["Heuristic Score", str(scoring.get("heuristic", 0))],
            ["AI Score", str(scoring.get("ai", 0))],
            ["Confidence", f"{scoring.get('confidence', 0)}%"],
        ]
        st = Table(score_rows, colWidths=[3 * inch, 2.8 * inch])
        st.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), PURPLE),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('TEXTCOLOR', (0, 1), (-1, -1), DARK),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, BG_CARD]),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('BOX', (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ]))
        story.append(st)

        heuristic_cats = scoring.get("heuristic_categories", {})
        ai_cats = scoring.get("ai_categories", {})
        if heuristic_cats or ai_cats:
            story.append(Spacer(1, 8))
            story.append(Paragraph("Category Scores", styles['SectionHeader']))
            cat_rows = [["Category", "Heuristic", "AI"]]
            all_cats = set(list(heuristic_cats.keys()) + list(ai_cats.keys()))
            for cat in sorted(all_cats):
                h_val = heuristic_cats.get(cat, "-")
                a_val = ai_cats.get(cat, "-")
                cat_rows.append([cat.replace("_", " ").title(), str(h_val), str(a_val)])

            if len(cat_rows) > 1:
                cat_table = Table(cat_rows, colWidths=[2.4 * inch, 1.7 * inch, 1.7 * inch])
                cat_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BACKGROUND', (0, 0), (-1, 0), PURPLE),
                    ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
                    ('TEXTCOLOR', (0, 1), (-1, -1), DARK),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, BG_CARD]),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('BOX', (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
                    ('LINEBELOW', (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
                    ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ]))
                story.append(cat_table)

        story.append(Spacer(1, 8))

    if report:
        if report.get("strengths"):
            story.append(Paragraph("Strengths", styles['SectionHeader']))
            for s in report["strengths"]:
                story.append(Paragraph(
                    f'<font color="{GREEN.hexval()}">&#10004;</font> {_safe(s)}',
                    styles['BulletItem']
                ))
            story.append(Spacer(1, 6))

        if report.get("weaknesses"):
            story.append(Paragraph("Weaknesses", styles['SectionHeader']))
            for w in report["weaknesses"]:
                if isinstance(w, dict):
                    label = w.get("label", "")
                    detail = w.get("detail", "")
                    story.append(Paragraph(
                        f'<font color="{RED.hexval()}">&#10060;</font> <b>{_safe(label)}</b>: {_safe(detail)}',
                        styles['BulletItem']
                    ))
                else:
                    story.append(Paragraph(
                        f'<font color="{RED.hexval()}">&#10060;</font> {_safe(str(w))}',
                        styles['BulletItem']
                    ))
            story.append(Spacer(1, 6))

        if report.get("technology_observations"):
            story.append(Paragraph("Technology Observations", styles['SectionHeader']))
            story.append(Paragraph(_safe(report["technology_observations"]), styles['BodyText2']))
            story.append(Spacer(1, 6))

        if report.get("sales_opportunities"):
            story.append(Paragraph("Sales Opportunities", styles['SectionHeader']))
            for opp in report["sales_opportunities"]:
                story.append(Paragraph(
                    f'<font color="{PURPLE.hexval()}">&#9654;</font> {_safe(opp)}',
                    styles['BulletItem']
                ))
            story.append(Spacer(1, 6))

    if tech_health:
        has_items = any(tech_health.get(k) for k in ["green", "amber", "red"])
        if has_items:
            story.append(Paragraph("Technology Health", styles['SectionHeader']))
            for item in tech_health.get("green", []):
                lbl = item.get("label", "") if isinstance(item, dict) else str(item)
                detail = item.get("detail", "") if isinstance(item, dict) else ""
                story.append(Paragraph(
                    f'<font color="{GREEN.hexval()}">&#9679;</font> <b>{_safe(lbl)}</b> {_safe(detail)}',
                    styles['BulletItem']
                ))
            for item in tech_health.get("amber", []):
                lbl = item.get("label", "") if isinstance(item, dict) else str(item)
                detail = item.get("detail", "") if isinstance(item, dict) else ""
                story.append(Paragraph(
                    f'<font color="{AMBER.hexval()}">&#9679;</font> <b>{_safe(lbl)}</b> {_safe(detail)}',
                    styles['BulletItem']
                ))
            for item in tech_health.get("red", []):
                lbl = item.get("label", "") if isinstance(item, dict) else str(item)
                detail = item.get("detail", "") if isinstance(item, dict) else ""
                story.append(Paragraph(
                    f'<font color="{RED.hexval()}">&#9679;</font> <b>{_safe(lbl)}</b> {_safe(detail)}',
                    styles['BulletItem']
                ))
            story.append(Spacer(1, 6))

    if social_links:
        active = {k: v for k, v in social_links.items() if v}
        if active:
            story.append(Paragraph("Social Media Presence", styles['SectionHeader']))
            for platform, url in active.items():
                story.append(Paragraph(
                    f'<b>{_safe(platform.title())}:</b> {_safe(str(url))}',
                    styles['BulletItem']
                ))
            story.append(Spacer(1, 6))

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=LIGHT_GRAY))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"Internal report generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}. For internal use only.",
        styles['FooterText']
    ))

    def on_page(canvas, doc_ref):
        _header_footer(canvas, doc_ref, "Internal Lead Report", "")

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buffer.getvalue()
