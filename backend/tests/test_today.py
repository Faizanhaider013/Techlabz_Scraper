"""Tests for the strict TODAY gate and the full today+ServiceNow+Remote+US funnel."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.scraper.date_utils import (
    get_today_range,
    is_posted_today,
    normalize_relative_date,
    now_local,
    parse_source_date,
)
from app.config import settings
from app.scraper.relevance import classify_job


@pytest.fixture(autouse=True)
def _strict_today(monkeypatch):
    """Pin STRICT today-only mode so these assertions don't depend on .env.

    (The portal's date window is configurable; the freshness-window behaviour is
    covered separately in test_window.py.)
    """
    monkeypatch.setattr(settings, "today_only", True)
    monkeypatch.setattr(settings, "scraper_lookback_days", 0)


TODAY = now_local().date()
TODAY_ISO = TODAY.isoformat()
YESTERDAY_ISO = (TODAY - timedelta(days=1)).isoformat()
OLD_ISO = "2026-05-14"  # fixed old date used in the brief


# ---------------------------------------------------------------------------
# is_posted_today — date gate
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "raw",
    ["Today", "today", "Posted today", "Just posted", "0 days ago", TODAY_ISO],
)
def test_today_values_pass(raw):
    assert is_posted_today(raw_date=raw) is True


@pytest.mark.parametrize(
    "raw",
    [
        "1 day ago",
        "Yesterday",
        "3 days ago",
        "14 May 2026",
        "May 14, 2026",
        OLD_ISO,
        YESTERDAY_ISO,
        "recent",
        None,
        "",
    ],
)
def test_non_today_values_fail(raw):
    assert is_posted_today(raw_date=raw) is False


def test_current_iso_timestamp_passes():
    assert is_posted_today(raw_date=now_local().isoformat()) is True


def test_get_today_range_covers_now():
    start, end = get_today_range()
    now = now_local()
    assert start <= now <= end
    assert start.hour == 0 and end.hour == 23


def test_normalize_relative_date():
    assert normalize_relative_date("today") == TODAY
    assert normalize_relative_date("yesterday") == TODAY - timedelta(days=1)
    assert normalize_relative_date("3 days ago") == TODAY - timedelta(days=3)
    assert normalize_relative_date("recent") is None


def test_parse_source_date():
    assert parse_source_date(OLD_ISO) == datetime(2026, 5, 14).date()
    assert parse_source_date(None) is None


# ---------------------------------------------------------------------------
# Full funnel via classify_job (today + ServiceNow + Remote + US)
# ---------------------------------------------------------------------------
def make(title, location, raw_date, description=""):
    return {
        "title": title,
        "location": location,
        "full_description": description or title,
        "short_description": description or title,
        "candidate_required_location": location,
        "date_posted_raw": raw_date,
        "remote": "remote" in (title + " " + location).lower() or None,
    }


def classify(title, location, raw_date, description=""):
    job = make(title, location, raw_date, description)
    return classify_job(job, normalized_date=parse_source_date(raw_date))


def test_pass_cases():
    assert classify("ServiceNow Developer Remote US", "Remote US", "Today")["allowed"]
    assert classify("ServiceNow Admin Remote United States", "Remote United States", TODAY_ISO)["allowed"]
    assert classify("Service Now Architect Remote US", "Remote US", now_local().isoformat())["allowed"]


def test_fail_old_date():
    r = classify("ServiceNow Consultant Remote US", "Remote US", "2026-05-14")
    assert not r["allowed"] and r["reason"] == "old_date"


def test_fail_old_date_textual():
    r = classify("ServiceNow Sales Executive", "Atlanta, Georgia", "14 May 2026")
    assert not r["allowed"] and r["reason"] == "old_date"


def test_fail_yesterday():
    r = classify("ServiceNow Developer Remote US", "Remote US", "Yesterday")
    assert not r["allowed"] and r["reason"] == "old_date"


def test_fail_3_days_ago():
    r = classify("ServiceNow Developer Remote US", "Remote US", "3 days ago")
    assert not r["allowed"] and r["reason"] == "old_date"


def test_fail_unknown_date():
    r = classify("ServiceNow Developer Remote US", "Remote US", None)
    assert not r["allowed"] and r["reason"] == "unknown_date"


def test_fail_non_relevant_even_if_today():
    # A non-tech role is rejected as not relevant even when posted today.
    r = classify("Marketing Manager Remote US", "Remote US", "Today")
    assert not r["allowed"] and r["reason"] == "not_relevant"


def test_fail_non_us_even_if_today():
    r = classify("ServiceNow Developer Remote", "India", "Today", "ServiceNow remote role in India")
    assert not r["allowed"] and r["reason"] == "not_us"
