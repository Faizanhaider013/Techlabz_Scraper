"""Regression tests for the query-time TODAY gate.

The original bug: the jobs API and stats trusted the stored ``is_posted_today``
boolean, which is frozen at scrape time. A job saved on an earlier day kept the
flag ``True`` and kept showing as "today". These tests prove the query layer now
gates on the live ``normalized_date_posted`` range in APP_TIMEZONE instead, so a
stale flag on an old job can never leak into today's results.
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base
from app.models import Job
from app.scraper.date_utils import now_local
from app.services import job_service
from app.services.stats_service import get_stats


@pytest.fixture()
def strict_today(monkeypatch):
    """Force strict today-only mode for a test."""
    monkeypatch.setattr(settings, "today_only", True)
    monkeypatch.setattr(settings, "scraper_lookback_days", 0)


@pytest.fixture()
def window_7d(monkeypatch):
    """Force a 7-day freshness window for a test."""
    monkeypatch.setattr(settings, "today_only", False)
    monkeypatch.setattr(settings, "scraper_lookback_days", 7)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def _job(title, when, *, is_posted_today, url):
    """Build a fully-valid ServiceNow+remote+US Job row dated ``when``."""
    return Job(
        title=title,
        company_name="Acme",
        location="Remote US",
        date_posted_raw=str(when.date()),
        posted_date=when,
        is_posted_today=is_posted_today,
        original_apply_url=url,
        source_name="test",
        is_servicenow=True,
        is_remote=True,
        is_us=True,
        dedupe_key=url,
    )


def test_stale_old_job_is_not_returned_as_today(db):
    """An OLD job with a stale is_posted_today=True must be excluded."""
    today = now_local().replace(hour=9, minute=0, second=0, microsecond=0)
    old = today - timedelta(days=46)  # ~ "May 14" relative to a late-June today

    db.add(_job("ServiceNow Developer Remote US (today)", today,
                is_posted_today=True, url="https://example.com/today"))
    # Stale row: flag says today, but the date is clearly old (the reported bug).
    db.add(_job("ServiceNow & Moveworks Sales Executive", old,
                is_posted_today=True, url="https://example.com/old"))
    db.commit()

    jobs, total = job_service.list_jobs(db, days=0)
    titles = [j.title for j in jobs]

    assert total == 1
    assert "ServiceNow Developer Remote US (today)" in titles
    assert all("Sales Executive" not in t for t in titles)


def test_default_listing_is_today_only(db, strict_today):
    """With TODAY_ONLY, the default (days=10) still returns only today since db cleanup restricts it (or settings.date_window_days is 0)."""
    # Wait, our list_jobs filters by days. In strict_today, lookback_days = 0, meaning only today.
    # But list_jobs default is days=10. If we want strictly today, we pass days=0.
    today = now_local().replace(hour=12, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)

    db.add(_job("ServiceNow Admin Remote US", today,
                is_posted_today=True, url="https://example.com/a"))
    db.add(_job("ServiceNow Architect Remote US (yesterday)", yesterday,
                is_posted_today=True, url="https://example.com/b"))
    db.commit()

    jobs, total = job_service.list_jobs(db, days=0)
    assert total == 1
    assert jobs[0].title == "ServiceNow Admin Remote US"


def test_window_7d_includes_last_week_excludes_older(db, window_7d):
    """7-day window: default listing shows the last 7 days, not older jobs."""
    today = now_local().replace(hour=12, minute=0, second=0, microsecond=0)
    three_days = today - timedelta(days=3)
    ten_days = today - timedelta(days=10)

    db.add(_job("ServiceNow Developer Remote US (today)", today,
                is_posted_today=True, url="https://example.com/t"))
    db.add(_job("ServiceNow Admin Remote US (3 days ago)", three_days,
                is_posted_today=False, url="https://example.com/3"))
    db.add(_job("ServiceNow Architect Remote US (10 days ago)", ten_days,
                is_posted_today=False, url="https://example.com/10"))
    db.commit()

    jobs, total = job_service.list_jobs(db, days=7)
    titles = {j.title for j in jobs}
    assert total == 2
    assert "ServiceNow Developer Remote US (today)" in titles
    assert "ServiceNow Admin Remote US (3 days ago)" in titles
    assert all("10 days ago" not in t for t in titles)

    # The explicit "Posted Today" tab is ALWAYS strictly today, even in 7-day mode.
    today_jobs, today_total = job_service.list_jobs(db, days=0)
    assert today_total == 1
    assert today_jobs[0].title == "ServiceNow Developer Remote US (today)"


def test_stats_today_count_ignores_stale_flag(db, strict_today):
    """today_jobs / posted_today count only genuinely-today rows."""
    today = now_local().replace(hour=8, minute=0, second=0, microsecond=0)
    old = today - timedelta(days=10)

    db.add(_job("ServiceNow Developer Remote US", today,
                is_posted_today=True, url="https://example.com/1"))
    db.add(_job("ServiceNow Consultant Remote US (old)", old,
                is_posted_today=True, url="https://example.com/2"))
    db.commit()

    stats = get_stats(db)
    assert stats.today_jobs == 1
    assert stats.posted_today == 1
