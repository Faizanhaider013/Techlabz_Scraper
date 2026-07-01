


"""Command-line interface for running the scraper outside the API process.

Usage:
    python -m app.cli scrape            # run one scrape now (cron-friendly)
    python -m app.cli scrape-recent     # scrape jobs from the last LOOKBACK_DAYS days
    python -m app.cli scrape-today      # scrape, keeping only TODAY jobs
    python -m app.cli diagnose-sources  # dry run: fetch + classify, print funnel table
    python -m app.cli diagnose-queries  # dry run: per-query raw/saved/rejected table
    python -m app.cli list-categories   # print all job categories + enabled state
    python -m app.cli list-keywords     # print all category keywords
    python -m app.cli list-modules      # print every ServiceNow module group + queries
    python -m app.cli list-sources      # print all sources with status/method
    python -m app.cli test-source NAME  # run one source only and print diagnostics
    python -m app.cli test-company-careers  # run company career sources only
    python -m app.cli init-db           # create tables and seed sources/keywords
    python -m app.cli reset-db          # DROP all tables, recreate, reseed (DEV)
    python -m app.cli clean-non-today   # delete jobs whose date is not today
    python -m app.cli clean-old-jobs    # delete jobs older than today
    python -m app.cli clean-irrelevant  # delete stored jobs that fail the strict filter
    python -m app.cli sources           # print the sources compliance report
"""
from __future__ import annotations

import json
import sys

from sqlalchemy import select

from app.database import Base, SessionLocal, engine, init_db
from app.scraper.engine import run_scraper
from app.scraper.relevance import is_allowed_job
from app.services.source_service import seed_keywords, sync_sources
from app.utils.logger import get_logger

logger = get_logger("cli")


def cmd_init_db() -> None:
    init_db()
    db = SessionLocal()
    try:
        sync_sources(db)
        seed_keywords(db)
    finally:
        db.close()
    logger.info("Database initialized.")


def cmd_reset_db() -> None:
    """Drop every table and recreate a clean schema, then reseed metadata.

    Use this for local development to wipe old/irrelevant data and pick up the
    new strict-filter schema. Destructive: all stored jobs are removed.
    """
    import app.models  # noqa: F401 - ensure models are registered

    logger.warning("reset-db: dropping ALL tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        sync_sources(db)
        seed_keywords(db)
    finally:
        db.close()
    logger.info("Database reset complete. Run 'python -m app.cli scrape' to collect jobs.")


def cmd_clean_irrelevant() -> None:
    """Remove already-stored jobs that do not pass the strict relevance filter."""
    from app.models import Job

    init_db()
    db = SessionLocal()
    removed = 0
    try:
        jobs = db.execute(select(Job)).scalars().all()
        for job in jobs:
            candidate = {
                "title": job.title,
                "company_name": job.company_name,
                "location": job.location,
                "short_description": job.short_description,
                "full_description": job.full_description,
                "job_type": job.job_type,
                "remote_type": job.remote_type,
                "candidate_required_location": job.location,
                "remote": job.is_remote,
            }
            allowed, _, _ = is_allowed_job(candidate)
            if not allowed:
                db.delete(job)
                removed += 1
        db.commit()
    finally:
        db.close()
    logger.info("clean-irrelevant: removed %d irrelevant job(s).", removed)


def cmd_scrape() -> None:
    init_db()
    db = SessionLocal()
    try:
        sync_sources(db)
        seed_keywords(db)
        run = run_scraper(db, trigger="manual")
        logger.info(
            "Done. status=%s raw=%d saved_today=%d duplicates=%d",
            run.status, run.total_found, run.total_new, run.total_duplicates,
        )
    finally:
        db.close()


def cmd_scrape_recent() -> None:
    """Scrape jobs from the last LOOKBACK_DAYS days (the engine enforces the window)."""
    from app.config import settings

    logger.info(
        "scrape-recent: collecting ServiceNow remote US/Canada jobs from the last %d day(s).",
        settings.date_window_days,
    )
    cmd_scrape()


def cmd_scrape_today() -> None:
    """Scrape and keep only TODAY jobs (the engine enforces the today gate)."""
    cmd_scrape()
    # Belt-and-suspenders: prune anything not dated today.
    cmd_clean_non_today()


def _delete_out_of_window(db) -> int:
    """Delete jobs whose date falls outside the active freshness window.

    With TODAY_ONLY this is "not today"; with a lookback (e.g. 7 days) it keeps
    jobs from the last N days and removes anything older / unknown.
    """
    from app.config import settings
    from app.models import Job
    from app.scraper.date_utils import is_within_window

    removed = 0
    for job in db.execute(select(Job)).scalars().all():
        if not is_within_window(
            raw_date=job.date_posted_raw,
            normalized_date=job.posted_date,
            days=settings.date_window_days,
        ):
            db.delete(job)
            removed += 1
    db.commit()
    return removed


def cmd_clean_non_today() -> None:
    """Delete every job whose date is outside the active freshness window."""
    init_db()
    db = SessionLocal()
    try:
        removed = _delete_out_of_window(db)
    finally:
        db.close()
    logger.info("clean-non-today: removed %d out-of-window job(s).", removed)


def cmd_clean_old_jobs() -> None:
    """Delete jobs older than the active freshness window."""
    init_db()
    db = SessionLocal()
    try:
        removed = _delete_out_of_window(db)
    finally:
        db.close()
    logger.info("clean-old-jobs: removed %d old job(s).", removed)


def cmd_diagnose_sources() -> None:
    """Dry run: fetch + classify every source and print the funnel table."""
    from app.models import SourceDiagnostic
    from app.scraper.engine import run_scraper

    init_db()
    db = SessionLocal()
    try:
        sync_sources(db)
        seed_keywords(db)
        run = run_scraper(db, trigger="diagnostic", dry_run=True)
        rows = (
            db.query(SourceDiagnostic)
            .filter(SourceDiagnostic.run_id == run.id)
            .order_by(SourceDiagnostic.saved_count.desc(), SourceDiagnostic.source_name)
            .all()
        )
        header = (
            f"{'source':<14}{'raw':>5}{'today':>6}{'SvcNow':>7}{'remote':>7}"
            f"{'US':>4}{'saved':>6}{'oldRej':>7}{'unkRej':>7}{'pg':>4}  status"
        )
        print("\n=== Source Diagnostics (dry run, nothing saved) ===")
        print(header)
        print("-" * len(header))
        for r in rows:
            print(
                f"{r.source_name:<14}{r.raw_count:>5}{r.today_matches:>6}"
                f"{r.servicenow_count:>7}{r.remote_count:>7}{r.us_count:>4}"
                f"{r.saved_count:>6}{r.rejected_old_date:>7}{r.rejected_unknown_date:>7}"
                f"{r.pages_fetched:>4}  {r.status}"
            )
            note = (r.error_message or r.reason or "")
            if note:
                print(f"{'':>14}↳ {note[:90]}")
        total_saved = sum(r.saved_count for r in rows)
        # Aggregate module coverage across all sources for this run.
        module_totals: dict[str, int] = {}
        for r in rows:
            for item in json.loads(r.top_matched_modules or "[]"):
                module_totals[item["module"]] = module_totals.get(item["module"], 0) + item["count"]
        print("-" * len(header))
        print(f"Would-save total (window + ServiceNow + Remote + US/Canada): {total_saved}")
        if module_totals:
            top = sorted(module_totals.items(), key=lambda kv: kv[1], reverse=True)
            print("Top modules found: " + ", ".join(f"{m} ({c})" for m, c in top[:12]))
    finally:
        db.close()


def cmd_diagnose_queries() -> None:
    """Dry run: print the per-query raw/saved/rejected funnel."""
    from app.models import SourceDiagnostic

    init_db()
    db = SessionLocal()
    try:
        sync_sources(db)
        seed_keywords(db)
        run = run_scraper(db, trigger="diagnostic", dry_run=True)
        rows = (
            db.query(SourceDiagnostic)
            .filter(SourceDiagnostic.run_id == run.id)
            .all()
        )
        queries: list[dict] = []
        for r in rows:
            for item in json.loads(r.query_stats or "[]"):
                item = dict(item)
                item["source"] = r.source_name
                queries.append(item)
        queries.sort(key=lambda q: (q.get("saved_count", 0), q.get("raw_count", 0)), reverse=True)

        header = f"{'query':<40}{'source':<12}{'raw':>5}{'saved':>6}{'rej':>5}  topReason"
        print("\n=== Query Diagnostics (dry run, nothing saved) ===")
        print(header)
        print("-" * len(header))
        for q in queries[:60]:
            print(
                f"{q['query'][:39]:<40}{q['source'][:11]:<12}{q.get('raw_count', 0):>5}"
                f"{q.get('saved_count', 0):>6}{q.get('rejected_count', 0):>5}  "
                f"{q.get('top_rejection_reason') or ''}"
            )
        if not queries:
            print("(no per-query stats recorded -- sources may have returned nothing)")
    finally:
        db.close()


def cmd_list_modules() -> None:
    """Print every ServiceNow taxonomy group and the generated query set."""
    from app.config import settings
    from app.scraper.query_builder import build_search_queries, query_categories
    from app.scraper.servicenow_taxonomy import iter_all_terms

    print("\n=== ServiceNow Module Coverage (taxonomy) ===")
    for group, terms in iter_all_terms().items():
        print(f"\n{group} ({len(terms)} terms)")
        print("  " + ", ".join(terms))

    print("\n=== Generated Search Queries ===")
    for category, queries in query_categories().items():
        print(f"\n[{category}] ({len(queries)})")
        for q in queries:
            print(f"  - {q}")
    total = build_search_queries()
    print(f"\nTotal queries used per source this run: {len(total)} "
          f"(cap MAX_QUERIES_PER_SOURCE={settings.max_queries_per_source})")


def cmd_list_categories() -> None:
    """Print all job categories, their enabled state, and keyword counts."""
    from app.config import settings
    from app.scraper import job_taxonomy as jtax

    enabled = set(settings.enabled_category_list)
    print("\n=== Job Categories ===")
    print(f"JOB_MODE={settings.job_mode}  MIN_RELEVANCE_SCORE={settings.min_relevance_score}")
    print(f"{'id':<20}{'name':<22}{'enabled':>8}{'keywords':>10}{'strong':>8}")
    print("-" * 68)
    for cat in jtax.CATEGORIES.values():
        print(
            f"{cat.category_id:<20}{cat.category_name:<22}"
            f"{('yes' if cat.category_id in enabled else 'no'):>8}"
            f"{len(cat.keywords):>10}{len(cat.strong_terms):>8}"
        )


def cmd_list_keywords() -> None:
    """Print every category and its keywords."""
    from app.scraper import job_taxonomy as jtax

    print("\n=== Category Keywords ===")
    for name, keywords in jtax.iter_keywords().items():
        print(f"\n{name} ({len(keywords)})")
        print("  " + ", ".join(keywords))


def cmd_list_sources() -> None:
    """Print all registered sources with enabled/implemented/status/method."""
    from app.scraper.sources import ALL_SOURCES

    print("\n=== Registered Sources ===")
    header = f"{'source_name':<22}{'enabled':<10}{'implemented':<14}{'status':<16}{'method':<12}"
    print(header)
    print("-" * len(header))
    for s in ALL_SOURCES:
        enabled = "yes" if s.status == "active" else "no"
        implemented = "yes" if s.status not in ("blocked", "skipped") or s.__class__.__name__ != "_BlockedSource" else "stub"
        # Determine method
        if s.uses_api:
            method = "api"
        elif s.type == "mock":
            method = "mock"
        else:
            method = "html/rss"

        # Override implemented for blocked sources
        if s.status in ("blocked", "skipped"):
            implemented = "stub"

        print(f"{s.name:<22}{enabled:<10}{implemented:<14}{s.status:<16}{method:<12}")
        if s.reason_if_skipped:
            print(f"{'':>22}-> {s.reason_if_skipped[:80]}")


def cmd_test_source() -> None:
    """Run one source only and print diagnostics."""
    if len(sys.argv) < 3:
        print("Usage: python -m app.cli test-source SOURCE_NAME")
        print("Example: python -m app.cli test-source remotive")
        sys.exit(1)

    source_name = sys.argv[2]
    from app.scraper.sources import ALL_SOURCES

    # Find the source (case-insensitive match)
    source = None
    for s in ALL_SOURCES:
        if s.name.lower() == source_name.lower():
            source = s
            break

    if source is None:
        print(f"Source '{source_name}' not found. Available sources:")
        for s in ALL_SOURCES:
            print(f"  - {s.name} [{s.status}]")
        sys.exit(1)

    print(f"\n=== Testing source: {source.name} ===")
    print(f"Status: {source.status}")
    print(f"Type: {source.type}")
    print(f"Base URL: {source.base_url}")
    print(f"Uses API: {source.uses_api}")

    if source.status in ("blocked", "skipped"):
        print(f"\nSource is {source.status}: {source.reason_if_skipped}")
        print("Not fetching (would be skipped by the engine).")
        return

    from app.scraper.query_builder import build_search_queries

    init_db()
    keywords = build_search_queries()[:5]  # Use first 5 queries only for test
    print(f"\nTesting with {len(keywords)} keyword(s): {', '.join(keywords[:3])}...")

    source.pages_fetched = 0
    source._run_cache = {}
    total_raw = 0

    for kw in keywords:
        try:
            jobs = source.fetch(kw)
            total_raw += len(jobs)
            if jobs:
                print(f"  [{kw}] -> {len(jobs)} raw job(s)")
                for j in jobs[:2]:
                    print(f"    - {j.title[:60]} @ {j.company_name[:30]}")
        except Exception as exc:
            print(f"  [{kw}] -> ERROR: {exc}")
            break

    print(f"\nTotal raw jobs: {total_raw}")
    print(f"Pages fetched: {source.pages_fetched}")
    print("Done.")


def cmd_test_company_careers() -> None:
    """Test the company careers source specifically."""
    from app.config import settings
    from app.scraper.sources.company_careers import CompanyCareersSource

    print("\n=== Testing Company Careers ===")
    print(f"Enabled: {settings.enable_company_careers}")
    print(f"Targets: {settings.company_career_target_list[:5]}... ({len(settings.company_career_target_list)} total)")

    if not settings.enable_company_careers:
        print("Company careers disabled. Set ENABLE_COMPANY_CAREERS=true.")
        return

    source = CompanyCareersSource()
    source.pages_fetched = 0
    source._run_cache = {}

    try:
        jobs = source.fetch("software engineer")
        print(f"\nTotal raw jobs found: {len(jobs)}")
        # Group by company
        by_company: dict[str, int] = {}
        for j in jobs:
            by_company[j.company_name] = by_company.get(j.company_name, 0) + 1
        print(f"Companies with jobs: {len(by_company)}")
        for company, count in sorted(by_company.items(), key=lambda x: x[1], reverse=True):
            print(f"  {company}: {count} job(s)")
        print(f"Pages fetched: {source.pages_fetched}")
    except Exception as exc:
        print(f"ERROR: {exc}")


def cmd_sources() -> None:
    from app.scraper.sources import ALL_SOURCES

    print("\n=== Source Compliance Report ===")
    for s in ALL_SOURCES:
        print(f"\n- {s.name} [{s.status}] ({s.type})")
        print(f"    base_url:      {s.base_url}")
        print(f"    uses_api:      {s.uses_api}")
        print(f"    robots_checked:{s.robots_checked}  tos_checked:{s.tos_checked}")
        if s.reason_if_skipped:
            print(f"    reason:        {s.reason_if_skipped}")


def main() -> None:
    commands = {
        "scrape": cmd_scrape,
        "scrape-recent": cmd_scrape_recent,
        "scrape-today": cmd_scrape_today,
        "diagnose-sources": cmd_diagnose_sources,
        "diagnose-queries": cmd_diagnose_queries,
        "list-categories": cmd_list_categories,
        "list-keywords": cmd_list_keywords,
        "list-modules": cmd_list_modules,
        "list-sources": cmd_list_sources,
        "test-source": cmd_test_source,
        "test-company-careers": cmd_test_company_careers,
        "init-db": cmd_init_db,
        "reset-db": cmd_reset_db,
        "clean-non-today": cmd_clean_non_today,
        "clean-old-jobs": cmd_clean_old_jobs,
        "clean-irrelevant": cmd_clean_irrelevant,
        "sources": cmd_sources,
    }
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print(__doc__)
        sys.exit(1)
    commands[sys.argv[1]]()


if __name__ == "__main__":
    main()
