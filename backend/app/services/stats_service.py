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


from typing import Optional
from datetime import datetime, timezone


def _relevant():
    """Hard filter shared by every stat: remote + US (relevance enforced at save)."""
    return (Job.is_remote.is_(True), Job.is_us.is_(True))


def _range_filter(days: int):
    """SQL conditions restricting to jobs within the last ``days`` days.

    Authoritative: derived from the live clock in APP_TIMEZONE applied to
    posted_date, never the frozen is_posted_today flag.
    """
    start, end = get_window_range(days)
    return (
        Job.posted_date.isnot(None),
        Job.posted_date >= start,
        Job.posted_date <= end,
    )


def _range_filter_dynamic(days: Optional[int], start_date: Optional[str], end_date: Optional[str]):
    from dateutil.parser import parse as parse_iso

    conds = [Job.posted_date.isnot(None)]

    if start_date or end_date:
        if start_date:
            try:
                start_dt = parse_iso(start_date).replace(tzinfo=timezone.utc)
                conds.append(Job.posted_date >= start_dt)
            except Exception:
                pass
        if end_date:
            try:
                end_dt = parse_iso(end_date).replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
                conds.append(Job.posted_date <= end_dt)
            except Exception:
                pass
    elif days is not None:
        if days == 0:
            start_dt = now_local().replace(hour=0, minute=0, second=0, microsecond=0)
            conds.append(Job.posted_date >= start_dt)
        else:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            conds.append(Job.posted_date >= cutoff)

    return conds


def _count_since(db: Session, days: int) -> int:
    cutoff = now_local() - timedelta(days=days)
    return db.execute(
        select(func.count())
        .select_from(Job)
        .where(*_relevant())
        .where(Job.posted_date >= cutoff)
    ).scalar_one()


def _top(db: Session, column, active_conds: list, limit: int = 8) -> list[CountItem]:
    rows = db.execute(
        select(column, func.count().label("c"))
        .where(*_relevant(), *active_conds)
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


def get_stats(
    db: Session,
    days: Optional[int] = 10,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> StatsResponse:
    # "Posted today" is always strictly today (window 0) -- drives the badge/tab.
    today_count = db.execute(
        select(func.count())
        .select_from(Job)
        .where(*_relevant())
        .where(*_range_filter(0))
    ).scalar_one()

    active_conds = _range_filter_dynamic(days, start_date, end_date)

    # Headline total = jobs within active window.
    total = db.execute(
        select(func.count())
        .select_from(Job)
        .where(*_relevant())
        .where(*active_conds)
    ).scalar_one()

    diags = _latest_run_diagnostics(db)
    attempted = [d for d in diags if d.enabled]
    with_results = [d for d in attempted if d.saved_count > 0]

    # Module coverage across stored jobs in the active window.
    module_rows = db.execute(
        select(Job.matched_modules)
        .where(*_relevant(), *active_conds)
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
        .where(*_relevant(), *active_conds)
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
        last_10_days=_count_since(db, 10),
        sources_attempted=len(attempted),
        sources_with_results=len(with_results),
        rejected_old_jobs=sum(d.rejected_old_date for d in diags),
        rejected_unknown_date=sum(d.rejected_unknown_date for d in diags),
        rejected_non_servicenow=sum(d.rejected_non_servicenow for d in diags),
        rejected_non_remote=sum(d.rejected_non_remote for d in diags),
        rejected_non_us=sum(d.rejected_non_us for d in diags),
        today_only=settings.today_only,
        window_days=days if days is not None else 10,
        modules_covered=len(module_counter),
        sources_checked=len(attempted),
        total_categories=len(category_breakdown),
        module_breakdown=module_breakdown,
        category_breakdown=category_breakdown,
        top_companies=_top(db, Job.company_name, active_conds),
        top_locations=_top(db, Job.location, active_conds),
        source_breakdown=_top(db, Job.source_name, active_conds),
        keyword_breakdown=_top(db, Job.keyword_matched, active_conds),
    )
