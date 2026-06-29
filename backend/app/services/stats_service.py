"""Aggregate dashboard statistics (TODAY-focused when TODAY_ONLY)."""
from __future__ import annotations

import json
from collections import Counter
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Job, SourceDiagnostic
from app.scraper.date_utils import get_window_range, now_local
from app.scraper.job_taxonomy import category_name
from app.scraper.servicenow_taxonomy import module_label
from app.schemas import CountItem, StatsResponse


def _relevant():
    """Hard filter shared by every stat: remote + US (relevance enforced at save)."""
    return (Job.is_remote.is_(True), Job.is_us.is_(True))


def _range_filter(days: int):
    """SQL conditions restricting to jobs within the last ``days`` days.

    Authoritative: derived from the live clock in APP_TIMEZONE applied to
    normalized_date_posted, never the frozen is_posted_today flag.
    """
    start, end = get_window_range(days)
    return (
        Job.normalized_date_posted.isnot(None),
        Job.normalized_date_posted >= start,
        Job.normalized_date_posted <= end,
    )


def _window_filter():
    """Scope breakdowns to the active freshness window (today-only or last N days)."""
    return _range_filter(settings.date_window_days) if settings.date_filter_active else ()


def _count_since(db: Session, days: int) -> int:
    cutoff = now_local() - timedelta(days=days)
    return db.execute(
        select(func.count())
        .select_from(Job)
        .where(*_relevant())
        .where(Job.normalized_date_posted >= cutoff)
    ).scalar_one()


def _top(db: Session, column, limit: int = 8) -> list[CountItem]:
    rows = db.execute(
        select(column, func.count().label("c"))
        .where(*_relevant(), *_window_filter())
        .where(column.isnot(None))
        .where(column != "")
        .group_by(column)
        .order_by(func.count().desc())
        .limit(limit)
    ).all()
    return [CountItem(label=str(label), count=count) for label, count in rows]


def _latest_run_diagnostics(db: Session) -> list[SourceDiagnostic]:
    latest = db.execute(
        select(SourceDiagnostic.run_id).order_by(SourceDiagnostic.id.desc()).limit(1)
    ).first()
    if latest is None:
        return []
    return db.execute(
        select(SourceDiagnostic).where(SourceDiagnostic.run_id == latest[0])
    ).scalars().all()


def get_stats(db: Session) -> StatsResponse:
    # "Posted today" is always strictly today (window 0) -- drives the badge/tab.
    today_count = db.execute(
        select(func.count())
        .select_from(Job)
        .where(*_relevant())
        .where(*_range_filter(0))
    ).scalar_one()

    # Headline total = jobs within the active freshness window (today-only or
    # last N days); all-time only when no date gate is active.
    if settings.date_filter_active:
        total = db.execute(
            select(func.count())
            .select_from(Job)
            .where(*_relevant())
            .where(*_window_filter())
        ).scalar_one()
    else:
        total = db.execute(
            select(func.count()).select_from(Job).where(*_relevant())
        ).scalar_one()

    diags = _latest_run_diagnostics(db)
    attempted = [d for d in diags if d.enabled]
    with_results = [d for d in attempted if d.saved_count > 0]

    # Module coverage across stored jobs in the active window.
    module_rows = db.execute(
        select(Job.matched_modules)
        .where(*_relevant(), *_window_filter())
        .where(Job.matched_modules.isnot(None))
    ).scalars().all()
    module_counter: Counter = Counter()
    for raw in module_rows:
        try:
            codes = json.loads(raw) if raw else []
        except (ValueError, TypeError):
            codes = []
        for code in codes if isinstance(codes, list) else []:
            module_counter[str(code)] += 1
    module_breakdown = [
        CountItem(label=module_label(code), count=count)
        for code, count in module_counter.most_common(20)
    ]

    # Category coverage across stored jobs in the active window.
    cat_rows = db.execute(
        select(Job.primary_category, func.count().label("c"))
        .where(*_relevant(), *_window_filter())
        .where(Job.primary_category.isnot(None))
        .where(Job.primary_category != "")
        .group_by(Job.primary_category)
        .order_by(func.count().desc())
    ).all()
    category_breakdown = [
        CountItem(label=category_name(str(code)), count=count) for code, count in cat_rows
    ]

    return StatsResponse(
        total_jobs=total,
        today_jobs=today_count,
        posted_today=today_count,
        last_3_days=_count_since(db, 3),
        last_7_days=_count_since(db, 7),
        sources_attempted=len(attempted),
        sources_with_results=len(with_results),
        rejected_old_jobs=sum(d.rejected_old_date for d in diags),
        rejected_unknown_date=sum(d.rejected_unknown_date for d in diags),
        rejected_non_servicenow=sum(d.rejected_non_servicenow for d in diags),
        rejected_non_remote=sum(d.rejected_non_remote for d in diags),
        rejected_non_us=sum(d.rejected_non_us for d in diags),
        today_only=settings.today_only,
        window_days=settings.date_window_days,
        modules_covered=len(module_counter),
        sources_checked=len(attempted),
        total_categories=len(category_breakdown),
        module_breakdown=module_breakdown,
        category_breakdown=category_breakdown,
        top_companies=_top(db, Job.company_name),
        top_locations=_top(db, Job.location),
        source_breakdown=_top(db, Job.source_name),
        keyword_breakdown=_top(db, Job.keyword_matched),
    )
