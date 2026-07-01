"""Scraper engine: orchestrates sources, strict filtering, dedupe, persistence
and per-source diagnostics.

Workflow per run:
  1. Load configured keywords.
  2. For each ACTIVE source adapter, fetch jobs for each keyword (best effort).
  3. Classify every raw job through the full funnel
     (ServiceNow -> remote -> US), recording counts and rejection reasons.
  4. Deduplicate + save only jobs that pass all three filters.
  5. Record a SourceDiag per source (active and non-active) and persist them to
     the source_diagnostics table, plus a ScraperRun summary row.

The engine never fails silently: every source ends with an explicit status and,
if it failed, a captured error -- visible via /api/scraper/diagnostics.
"""
from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Job, ScraperRun, SourceDiagnostic
from app.scraper.date_utils import is_posted_today
from app.scraper.diagnostics import (
    STATUS_BLOCKED,
    STATUS_SKIPPED,
    SourceDiag,
)
from app.scraper.date_utils import now_local
from app.scraper.normalizer import normalize
from app.scraper.relevance import classify_job
from app.scraper.sources import ALL_SOURCES, active_sources
from app.scraper.sources.base import RawJob
from app.utils.logger import get_logger

logger = get_logger("engine")


def _days_old(normalized_date) -> Optional[int]:
    """Whole days between the job's posting date and today (None if unknown)."""
    if normalized_date is None:
        return None
    posted = normalized_date.date() if hasattr(normalized_date, "date") else normalized_date
    delta = (now_local().date() - posted).days
    return max(0, delta)


def _load_keywords(db: Session) -> List[str]:
    """Queries that drive the scrape.

    When query expansion is enabled (default) the smart query builder generates
    the full role/module/technical/US query set from the taxonomy. Otherwise we
    fall back to DB-seeded keywords (or the configured defaults).
    """
    from app.models import Keyword
    from app.scraper.query_builder import build_search_queries

    if settings.enable_query_expansion:
        return build_search_queries()

    rows = db.execute(select(Keyword).where(Keyword.active.is_(True))).scalars().all()
    db_keywords = [r.term for r in rows]
    return db_keywords or settings.keywords


def build_relevance_input(record: dict, raw: RawJob) -> dict:
    """Assemble the text dict the relevance filter inspects (keyword excluded)."""
    return {
        "title": record.get("title"),
        "company_name": record.get("company_name"),
        "location": record.get("location"),
        "short_description": record.get("short_description"),
        "full_description": record.get("full_description"),
        "job_type": record.get("job_type"),
        "remote_type": record.get("remote_type"),
        "workplace_type": raw.remote_type,
        "tags": raw.tags,
        "category": raw.category,
        "candidate_required_location": raw.candidate_required_location,
        "remote": raw.remote_flag,
        "date_posted_raw": record.get("date_posted_raw"),
    }


def run_scraper(
    db: Session,
    trigger: str = "manual",
    dry_run: bool = False,
    run_id: Optional[int] = None,
) -> ScraperRun:
    """Execute one scrape (or diagnostic dry run) and return the ScraperRun.

    When ``dry_run`` is True, sources are fetched and classified but nothing is
    persisted to the jobs table -- used by ``diagnose-sources``.
    """
    if run_id is not None:
        run = db.get(ScraperRun, run_id)
        if run is None:
            raise ValueError(f"Pre-allocated ScraperRun #{run_id} not found.")
        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        db.commit()
    else:
        run = ScraperRun(
            status="running",
            trigger="diagnostic" if dry_run else trigger,
            started_at=datetime.now(timezone.utc),
        )
        db.add(run)
        db.commit()
        db.refresh(run)

    keywords = _load_keywords(db)
    active = active_sources()
    active_names = {s.name for s in active}
    logger.info(
        "Scraper run #%d started (trigger=%s, dry_run=%s) | %d keyword(s), %d active source(s)",
        run.id, run.trigger, dry_run, len(keywords), len(active),
    )

    diags: dict[str, SourceDiag] = {}
    seen_keys: set[str] = set()  # intra-run dedupe across all sources

    # ---- Non-active sources: surface them with their compliance status ----
    for source in ALL_SOURCES:
        if source.name in active_names:
            continue
        status = STATUS_BLOCKED if source.status == "blocked" else STATUS_SKIPPED
        diag = SourceDiag(source_name=source.name, enabled=False, status=status)
        diag.last_error = source.reason_if_skipped
        diags[source.name] = diag

    # ---- Active sources: run the full funnel ------------------------------
    for source in active:
        diag = SourceDiag(source_name=source.name, enabled=True)
        diags[source.name] = diag
        source_seen: set[str] = set()
        source.pages_fetched = 0  # adapters increment this per page fetched
        source._run_cache = {}    # fresh feed/board cache for this run

        for keyword in keywords:
            diag.queries_tried += 1
            logger.info("  [%s] fetching keyword=%r", source.name, keyword)
            try:
                raw_jobs = source.fetch(keyword)
            except Exception as exc:  # noqa: BLE001 - one source must not kill the run
                msg = f"{type(exc).__name__}: {exc}"
                logger.error("  [%s] fetch failed: %s", source.name, msg)
                logger.debug(traceback.format_exc())
                diag.status = source.failure_status
                diag.last_error = msg
                # A blocked source fails identically for every keyword -> stop early.
                if source.failure_status == "blocked":
                    break
                continue

            for raw in raw_jobs:
                if not raw.original_apply_url or not raw.title:
                    continue

                record = normalize(raw, keyword_matched=keyword)
                key = record["dedupe_key"]

                # Count each distinct job once per source (keyword loops would
                # otherwise re-examine the same job and inflate the funnel).
                if key in source_seen:
                    continue
                source_seen.add(key)

                diag.raw_count += 1
                diag.add_raw(raw.title, record.get("date_posted_raw"), query=keyword)

                rel_input = build_relevance_input(record, raw)
                classification = classify_job(
                    rel_input, normalized_date=record["normalized_date_posted"]
                )
                diag.record(raw.title, classification)

                if not classification["allowed"]:
                    diag.note_rejected(keyword, classification["reason"])
                    continue

                # Cross-source dedupe: a job another source already saved.
                if key in seen_keys:
                    diag.duplicate_count += 1
                    continue
                seen_keys.add(key)

                # Enrich with multi-stack relevance metadata for storage / UI.
                modules = classification.get("matched_modules") or []
                categories = classification.get("matched_categories") or []
                keywords_matched = classification.get("matched_keywords") or []
                primary_category = classification.get("primary_category")
                record["is_servicenow"] = classification.get("has_servicenow", False)
                record["is_remote"] = True
                record["is_us"] = True
                record["relevance_score"] = classification.get("relevance_score", 0)
                record["primary_category"] = primary_category
                record["matched_categories"] = json.dumps(categories)
                record["matched_keywords"] = json.dumps(keywords_matched)
                record["matched_terms"] = json.dumps(keywords_matched)
                record["matched_modules"] = json.dumps(modules)
                record["query_used"] = keyword
                record["days_old"] = _days_old(record["normalized_date_posted"])

                diag.note_saved(
                    keyword, raw.title, modules,
                    categories=categories, keywords=keywords_matched,
                    primary_category=primary_category,
                )

                if dry_run:
                    diag.saved_count += 1  # would-save count
                    continue

                created = _upsert_job(db, record)
                if created:
                    diag.saved_count += 1
                else:
                    diag.duplicate_count += 1

        if not dry_run:
            db.commit()
        diag.pages_fetched = getattr(source, "pages_fetched", 0)
        diag.finalize()
        logger.info(
            "  [%s] status=%s raw=%d today=%d sn=%d remote=%d us=%d saved=%d "
            "| rejected old=%d unknown=%d | pages=%d%s",
            source.name, diag.status, diag.raw_count, diag.today_matches,
            diag.servicenow_count, diag.remote_count, diag.us_count, diag.saved_count,
            diag.rejected_old_date, diag.rejected_unknown_date, diag.pages_fetched,
            f" error={diag.last_error}" if diag.last_error else "",
        )

    if not dry_run:
        _refresh_posted_today(db)

    # ---- Aggregate run totals + persist diagnostics -----------------------
    total_raw = sum(d.raw_count for d in diags.values())
    total_saved = sum(d.saved_count for d in diags.values())
    total_dupes = sum(d.duplicate_count for d in diags.values())
    total_sn_rej = sum(d.rejected_non_servicenow for d in diags.values())
    total_rm_rej = sum(d.rejected_non_remote for d in diags.values())
    total_us_rej = sum(d.rejected_non_us for d in diags.values())
    total_old_rej = sum(d.rejected_old_date for d in diags.values())
    total_unknown_rej = sum(d.rejected_unknown_date for d in diags.values())
    errors = [f"{d.source_name}: {d.last_error}" for d in diags.values()
              if d.status == "error" and d.last_error]

    _persist_diagnostics(db, run.id, diags.values())

    if errors and total_saved == 0 and total_raw == 0:
        status = "failed"
    elif errors:
        status = "partial"
    else:
        status = "success"

    run.finished_at = datetime.now(timezone.utc)
    run.status = status
    run.total_found = total_raw
    run.total_raw_fetched = total_raw
    run.total_relevant = total_saved
    run.total_skipped_irrelevant = total_sn_rej
    run.total_skipped_non_remote = total_rm_rej
    run.total_skipped_non_us = total_us_rej
    run.total_new = total_saved
    run.total_duplicates = total_dupes
    run.errors = json.dumps(errors) if errors else None
    run.source_summary = json.dumps(
        {d.source_name: {"status": d.status, "raw": d.raw_count, "saved": d.saved_count}
         for d in diags.values()}
    )
    db.commit()
    db.refresh(run)

    logger.info(
        "Scraper run #%d %s | raw=%d saved(today)=%d dup=%d | rejected: "
        "old=%d unknown=%d non-SN=%d non-remote=%d non-US=%d",
        run.id, status, total_raw, total_saved, total_dupes,
        total_old_rej, total_unknown_rej, total_sn_rej, total_rm_rej, total_us_rej,
    )
    return run


def _persist_diagnostics(db: Session, run_id: int, diags) -> None:
    for d in diags:
        db.add(
            SourceDiagnostic(
                source_name=d.source_name,
                run_id=run_id,
                enabled=d.enabled,
                status=d.status,
                raw_count=d.raw_count,
                parsed_jobs=d.parsed_jobs,
                today_matches=d.today_matches,
                servicenow_count=d.servicenow_count,
                remote_count=d.remote_count,
                us_count=d.us_count,
                saved_count=d.saved_count,
                rejected_old_date=d.rejected_old_date,
                rejected_unknown_date=d.rejected_unknown_date,
                rejected_non_servicenow=d.rejected_non_servicenow,
                rejected_low_relevance=d.rejected_low_relevance,
                rejected_non_remote=d.rejected_non_remote,
                rejected_non_us=d.rejected_non_us,
                duplicate_count=d.duplicate_count,
                pages_fetched=d.pages_fetched,
                queries_tried=d.queries_tried,
                sample_titles=json.dumps(d.sample_raw_titles) if d.sample_raw_titles else None,
                sample_raw_dates=json.dumps(d.sample_raw_dates) if d.sample_raw_dates else None,
                sample_rejections=json.dumps(d.sample_rejections) if d.sample_rejections else None,
                near_matches=json.dumps(d.near_matches)
                if (settings.debug_show_near_matches and d.near_matches) else None,
                sample_saved_titles=json.dumps(d.sample_saved_titles) if d.sample_saved_titles else None,
                top_successful_queries=json.dumps(d.top_successful_queries()) or None,
                top_matched_modules=json.dumps(d.top_matched_modules()) or None,
                top_categories_found=json.dumps(d.top_categories_found()) or None,
                top_keywords_found=json.dumps(d.top_keywords_found()) or None,
                query_stats=json.dumps(d.query_stats()) or None,
                reason=d.last_error if not d.enabled else None,
                error_message=d.last_error if d.enabled else None,
            )
        )
    db.commit()


def _upsert_job(db: Session, record: dict) -> bool:
    existing: Optional[Job] = db.execute(
        select(Job).where(Job.dedupe_key == record["dedupe_key"])
    ).scalar_one_or_none()

    if existing is None:
        db.add(Job(**record))
        return True

    existing.normalized_date_posted = record["normalized_date_posted"] or existing.normalized_date_posted
    existing.is_posted_today = record["is_posted_today"]
    existing.short_description = record["short_description"] or existing.short_description
    existing.full_description = record["full_description"] or existing.full_description
    existing.salary = record["salary"] or existing.salary
    existing.job_type = record["job_type"] or existing.job_type
    existing.remote_type = record["remote_type"] or existing.remote_type
    existing.relevance_score = record.get("relevance_score", existing.relevance_score)
    existing.primary_category = record.get("primary_category") or existing.primary_category
    existing.matched_categories = record.get("matched_categories") or existing.matched_categories
    existing.matched_keywords = record.get("matched_keywords") or existing.matched_keywords
    existing.matched_terms = record.get("matched_terms") or existing.matched_terms
    existing.matched_modules = record.get("matched_modules") or existing.matched_modules
    existing.query_used = record.get("query_used") or existing.query_used
    existing.days_old = record.get("days_old") if record.get("days_old") is not None else existing.days_old
    existing.is_servicenow = record.get("is_servicenow", existing.is_servicenow)
    existing.is_remote = True
    existing.is_us = True
    return False


def _refresh_posted_today(db: Session) -> None:
    jobs = db.execute(select(Job)).scalars().all()
    changed = 0
    for job in jobs:
        flag = is_posted_today(job.normalized_date_posted)
        if job.is_posted_today != flag:
            job.is_posted_today = flag
            changed += 1
    if changed:
        db.commit()
        logger.info("Refreshed is_posted_today on %d job(s)", changed)
