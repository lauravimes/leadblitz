import csv
import io
import re
import uuid
import asyncio
import threading
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse

from helpers.models import SessionLocal, Lead as LeadModel, CsvImport as CsvImportModel
from helpers.credits import credit_manager


REQUIRED_HEADERS = {"website_url"}
TEMPLATE_HEADERS = ["business_name", "website_url", "email", "phone", "notes"]
MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_ROWS = 1000


def generate_import_id() -> str:
    return f"imp_{uuid.uuid4().hex[:12]}"


def normalize_domain(url: str) -> str:
    url = url.strip().lower()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split("/")[0]
        domain = domain.lstrip("www.")
        domain = domain.rstrip("/")
        return domain
    except Exception:
        return url.strip().lower()


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def validate_url_format(url: str) -> bool:
    url = url.strip()
    if not url:
        return False
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        parsed = urlparse(url)
        return bool(parsed.netloc) and "." in parsed.netloc
    except Exception:
        return False


def get_csv_template() -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(TEMPLATE_HEADERS)
    writer.writerow(["Joe's Plumbing", "https://joesplumbing.com", "joe@joesplumbing.com", "555-1234", "Referred by Mike"])
    return output.getvalue()


def parse_csv_file(file_content: bytes, filename: str) -> Tuple[Optional[List[Dict]], Optional[Dict]]:
    if len(file_content) > MAX_FILE_SIZE:
        return None, {"error": "too_large", "message": "Maximum 1000 leads per import. Please split your file into smaller batches."}

    try:
        text = file_content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = file_content.decode("latin-1")
        except Exception:
            return None, {"error": "invalid_format", "message": "This file doesn't appear to be a valid CSV. Please upload a .csv file."}

    text = text.strip()
    if not text:
        return None, {"error": "empty_file", "message": "No data found in CSV"}

    try:
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            return None, {"error": "empty_file", "message": "No data found in CSV"}

        headers_lower = [h.strip().lower() for h in reader.fieldnames]
        has_url = "website_url" in headers_lower
        if not has_url:
            return None, {"error": "no_url_column", "message": "We couldn't find a website/URL column. Please make sure your CSV includes website URLs."}

        header_map = {}
        for i, h in enumerate(reader.fieldnames):
            header_map[h.strip().lower()] = h

        rows = []
        for row in reader:
            rows.append(row)
            if len(rows) > MAX_ROWS:
                return None, {"error": "too_large", "message": "Maximum 1000 leads per import. Please split your file into smaller batches."}

        if not rows:
            return None, {"error": "empty_file", "message": "No data found in CSV"}

        parsed = []
        for row in rows:
            normalized = {}
            for key, value in row.items():
                if key:
                    normalized[key.strip().lower()] = (value or "").strip()
            parsed.append(normalized)

        return parsed, None

    except csv.Error:
        return None, {"error": "invalid_format", "message": "This file doesn't appear to be a valid CSV. Please upload a .csv file."}


def process_csv_rows(rows: List[Dict], user_id: int, import_id: str, filename: str) -> Dict:
    session = SessionLocal()
    try:
        existing_leads = session.query(LeadModel).filter(LeadModel.user_id == user_id).all()
        existing_domains = set()
        for lead in existing_leads:
            if lead.website:
                existing_domains.add(normalize_domain(lead.website))

        seen_domains = set()
        skipped_no_url = 0
        skipped_duplicate = 0
        skipped_invalid = 0
        valid_leads = []

        for row in rows:
            url = row.get("website_url", "").strip()

            if not url:
                skipped_no_url += 1
                continue

            if not validate_url_format(url):
                skipped_invalid += 1
                continue

            domain = normalize_domain(url)

            if domain in seen_domains:
                skipped_duplicate += 1
                continue

            if domain in existing_domains:
                skipped_duplicate += 1
                continue

            seen_domains.add(domain)
            valid_leads.append(row)

        credits_info = credit_manager.get_user_credits(user_id)
        credits_available = credits_info["balance"]
        to_score = len(valid_leads)
        credits_to_use = min(credits_available, to_score)
        pending_credits = max(0, to_score - credits_to_use)

        csv_import = CsvImportModel(
            id=import_id,
            user_id=user_id,
            filename=filename,
            total_rows=len(rows),
            to_score=to_score,
            scored_count=0,
            unreachable_count=0,
            pending_count=to_score,
            pending_credits_count=pending_credits,
            skipped_duplicate=skipped_duplicate,
            skipped_no_url=skipped_no_url,
            skipped_invalid=skipped_invalid,
            status="in_progress"
        )
        session.add(csv_import)
        session.flush()

        lead_ids_to_score = []
        lead_ids_pending_credits = []

        for i, row in enumerate(valid_leads):
            lead_id = str(uuid.uuid4())
            url = normalize_url(row.get("website_url", ""))
            name = row.get("business_name", "").strip() or normalize_domain(url)
            email = row.get("email", "").strip()
            phone = row.get("phone", "").strip()
            notes = row.get("notes", "").strip()

            if i < credits_to_use:
                status = "queued"
                lead_ids_to_score.append(lead_id)
            else:
                status = "pending_credits"
                lead_ids_pending_credits.append(lead_id)

            lead = LeadModel(
                id=lead_id,
                user_id=user_id,
                name=name,
                website=url,
                email=email,
                phone=phone,
                notes=notes,
                source="import",
                import_id=import_id,
                import_status=status,
                stage="New",
                score=0
            )
            session.add(lead)

        session.commit()

        total_skipped = skipped_duplicate + skipped_no_url + skipped_invalid
        parts = []
        if skipped_duplicate > 0:
            parts.append(f"{skipped_duplicate} duplicate{'s' if skipped_duplicate != 1 else ''}")
        if skipped_no_url > 0:
            parts.append(f"{skipped_no_url} missing URL")
        if skipped_invalid > 0:
            parts.append(f"{skipped_invalid} invalid")
        skipped_text = f" {total_skipped} skipped ({', '.join(parts)})." if total_skipped > 0 else ""

        msg = f"{to_score} leads imported."
        if credits_to_use > 0:
            msg += f" Scoring {credits_to_use} websites"
        if pending_credits > 0:
            msg += f" ({pending_credits} paused — upgrade to score remaining)."
        else:
            msg += "."
        msg += skipped_text

        return {
            "success": True,
            "import_id": import_id,
            "summary": {
                "total_rows": len(rows),
                "to_score": to_score,
                "skipped_duplicate": skipped_duplicate,
                "skipped_no_url": skipped_no_url,
                "skipped_invalid": skipped_invalid,
                "credits_available": credits_available,
                "credits_to_use": credits_to_use,
                "pending_credits": pending_credits
            },
            "message": msg,
            "_lead_ids_to_score": lead_ids_to_score
        }
    finally:
        session.close()


def get_import_status(import_id: str, user_id: int) -> Optional[Dict]:
    session = SessionLocal()
    try:
        csv_import = session.query(CsvImportModel).filter_by(id=import_id, user_id=user_id).first()
        if not csv_import:
            return None

        leads = session.query(LeadModel).filter_by(import_id=import_id, user_id=user_id).all()
        scored = sum(1 for l in leads if l.import_status == "scored")
        unreachable = sum(1 for l in leads if l.import_status == "unreachable")
        pending = sum(1 for l in leads if l.import_status in ("queued", "scoring"))
        pending_credits = sum(1 for l in leads if l.import_status == "pending_credits")
        total = csv_import.to_score

        if pending == 0 and csv_import.status == "in_progress":
            csv_import.status = "completed" if pending_credits == 0 else "partial"
            csv_import.completed_at = datetime.now()
            csv_import.scored_count = scored
            csv_import.unreachable_count = unreachable
            csv_import.pending_credits_count = pending_credits
            csv_import.pending_count = 0
            session.commit()

        return {
            "import_id": import_id,
            "status": csv_import.status,
            "total": total,
            "scored": scored,
            "unreachable": unreachable,
            "pending": pending,
            "pending_credits": pending_credits
        }
    finally:
        session.close()


def score_import_leads_background(lead_ids: List[str], import_id: str, user_id: int):
    thread = threading.Thread(
        target=_run_scoring_thread,
        args=(lead_ids, import_id, user_id),
        daemon=True
    )
    thread.start()


def _run_scoring_thread(lead_ids: List[str], import_id: str, user_id: int):
    from helpers.hybrid_scorer import score_website_hybrid, create_backward_compatible_reasoning
    import concurrent.futures
    import time as time_module

    semaphore = threading.Semaphore(10)
    PER_LEAD_TIMEOUT = 45

    def score_single_lead(lead_id: str):
        with semaphore:
            session = SessionLocal()
            try:
                lead = session.query(LeadModel).filter_by(id=lead_id, user_id=user_id).first()
                if not lead or not lead.website:
                    return

                lead.import_status = "scoring"
                session.commit()

                try:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(score_website_hybrid, lead.website, True)
                        hybrid_result = future.result(timeout=PER_LEAD_TIMEOUT)

                    score_reasoning = create_backward_compatible_reasoning(hybrid_result)
                    render_pathway = hybrid_result.get("render_pathway", "")
                    has_errors = hybrid_result.get("has_errors", False)
                    breakdown = hybrid_result.get("breakdown", {})
                    final_score = hybrid_result.get("final_score", 0)

                    scoring_failed = (
                        render_pathway in ["fetch_failed", "bot_blocked"] or
                        (has_errors and final_score == 0) or
                        (not breakdown and final_score == 0)
                    )

                    if scoring_failed:
                        lead.score = 0
                        lead.score_reasoning = score_reasoning
                        lead.heuristic_score = 0
                        lead.ai_score = 0
                        lead.import_status = "unreachable"
                        session.commit()
                        return

                    has_credits, _, _ = credit_manager.has_sufficient_credits(user_id, "ai_scoring", 1)
                    if not has_credits:
                        lead.import_status = "pending_credits"
                        session.commit()
                        return

                    credit_manager.deduct_credits(user_id, "ai_scoring", 1, f"CSV import scoring: {lead.name}")

                    lead.score = score_reasoning.get("total_score", 0)
                    lead.score_reasoning = score_reasoning
                    lead.heuristic_score = hybrid_result.get("heuristic_score")
                    lead.ai_score = hybrid_result.get("ai_score")
                    lead.score_breakdown = hybrid_result.get("breakdown")
                    lead.score_confidence = hybrid_result.get("confidence")
                    lead.last_scored_at = datetime.now()
                    lead.technographics = hybrid_result.get("technographics")
                    lead.import_status = "scored"
                    session.commit()

                except concurrent.futures.TimeoutError:
                    lead.import_status = "unreachable"
                    lead.score = 0
                    session.commit()
                except Exception as e:
                    print(f"CSV import scoring error for {lead.website}: {e}")
                    lead.import_status = "unreachable"
                    lead.score = 0
                    session.commit()
            except Exception as e:
                print(f"CSV import lead processing error: {e}")
            finally:
                session.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(score_single_lead, lid) for lid in lead_ids]
        concurrent.futures.wait(futures)

    session = SessionLocal()
    try:
        csv_import = session.query(CsvImportModel).filter_by(id=import_id).first()
        if csv_import:
            leads = session.query(LeadModel).filter_by(import_id=import_id).all()
            scored = sum(1 for l in leads if l.import_status == "scored")
            unreachable = sum(1 for l in leads if l.import_status == "unreachable")
            pending_credits = sum(1 for l in leads if l.import_status == "pending_credits")

            csv_import.scored_count = scored
            csv_import.unreachable_count = unreachable
            csv_import.pending_credits_count = pending_credits
            csv_import.pending_count = 0
            csv_import.status = "completed" if pending_credits == 0 else "partial"
            csv_import.completed_at = datetime.now()
            session.commit()
    finally:
        session.close()

    print(f"CSV import {import_id} scoring complete")
