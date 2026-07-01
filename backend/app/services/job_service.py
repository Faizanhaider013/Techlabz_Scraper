"""Query layer for jobs: search, filter, sort and pagination."""
from __future__ import annotations

from datetime import timedelta
from typing import Optional, Tuple

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.models import Job
from app.scraper.date_utils import get_window_range, now_local

# date_filter -> number of days lookback (None means no lower bound).
_DATE_WINDOWS = {"today": 0, "last_3_days": 3, "last_7_days": 7, "all": None}


def list_jobs(
    db: Session,
    *,
    q: Optional[str] = None,
    keyword: Optional[str] = None,
    location: Optional[str] = None,
    days: Optional[int] = 10,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    source: Optional[str] = None,
    remote_type: Optional[str] = None,
    module: Optional[str] = None,
    category: Optional[str] = None,
    sort: str = "newest",
    page: int = 1,
    limit: int = 20,
) -> Tuple[list[Job], int]:
    """Return (jobs, total_count) for the given filters.

    Global hard filter: regardless of the query parameters, only remote + US
    jobs are ever returned. This is defense-in-depth -- the scraper already
    refuses to save anything that isn't relevant + remote + US.
    """
    stmt = select(Job).where(
        Job.is_remote.is_(True),
        Job.is_us.is_(True),
    )

    from app.config import settings as _settings
    from datetime import datetime, timezone, timedelta

    if q:
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Job.title).like(like),
                func.lower(Job.company_name).like(like),
                func.lower(Job.keyword_matched).like(like),
                func.lower(Job.short_description).like(like),
            )
        )
    if keyword:
        # Substring match across title / matched query / matched keywords so quick
        # keyword filters ("Laravel", "Node.js", ...) work regardless of the exact
        # generated query a job was found under.
        kw = f"%{keyword.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Job.title).like(kw),
                func.lower(Job.keyword_matched).like(kw),
                func.lower(Job.matched_keywords).like(kw),
            )
        )
    if location:
        stmt = stmt.where(func.lower(Job.location).like(f"%{location.strip().lower()}%"))
    if source:
        stmt = stmt.where(func.lower(Job.source_name) == source.strip().lower())
    if remote_type:
        stmt = stmt.where(func.lower(Job.remote_type) == remote_type.strip().lower())
    if module:
        # matched_modules is a JSON array of module codes, e.g. ["ITSM","CMDB"].
        stmt = stmt.where(Job.matched_modules.like(f'%"{module.strip()}"%'))
    if category:
        # Match the primary category or any entry in the matched_categories JSON.
        cat = category.strip()
        stmt = stmt.where(
            or_(
                func.lower(Job.primary_category) == cat.lower(),
                Job.matched_categories.like(f'%"{cat}"%'),
            )
        )

    # Date range filters: start_date/end_date override days lookback
    if start_date or end_date:
        if start_date:
            try:
                from dateutil.parser import parse as parse_iso
                start_dt = parse_iso(start_date).replace(tzinfo=timezone.utc)
                stmt = stmt.where(Job.posted_date >= start_dt)
            except Exception:
                pass
        if end_date:
            try:
                from dateutil.parser import parse as parse_iso
                end_dt = parse_iso(end_date).replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
                stmt = stmt.where(Job.posted_date <= end_dt)
            except Exception:
                pass
    elif days is not None:
        if days == 0:
            # Special case for "today"
            start_dt = now_local().replace(hour=0, minute=0, second=0, microsecond=0)
            stmt = stmt.where(Job.posted_date >= start_dt)
        else:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            stmt = stmt.where(Job.posted_date >= cutoff)

    # Count total before pagination.
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar_one()

    # Sorting: NULL dates sort last. Posted-today always floats to the top.
    order_col = Job.posted_date
    direction = asc if sort == "oldest" else desc
    stmt = stmt.order_by(desc(Job.is_posted_today), direction(order_col), desc(Job.id))

    page = max(1, page)
    limit = max(1, min(limit, 100))
    stmt = stmt.offset((page - 1) * limit).limit(limit)

    jobs = db.execute(stmt).scalars().all()
    return list(jobs), total


def get_job(db: Session, job_id: int) -> Optional[Job]:
    return db.get(Job, job_id)
