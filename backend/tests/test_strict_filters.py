"""Strict filter tests: US, Remote, Date.

Verifies every acceptance/rejection case listed in the production-readiness spec.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from app.scraper.relevance import is_remote_job, is_us_job, is_recent_job


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _job(location: str = "", **kw) -> dict:
    """Build a minimal job dict for filter testing."""
    return {"location": location, **kw}


def _today():
    return datetime.now(tz=timezone.utc)


# ===========================================================================
# 1. US FILTER — Rejections
# ===========================================================================

class TestUSFilterRejections:
    """Jobs from these countries MUST be rejected."""

    @pytest.mark.parametrize("location", [
        "Bangalore, India",
        "Toronto, Canada",
        "Berlin, Germany",
        "Remote - India",
        "Karachi, Pakistan",
        "Dhaka, Bangladesh",
        "Manila, Philippines",
        "Ho Chi Minh City, Vietnam",
        "Shanghai, China",
        "Tokyo, Japan",
        "Singapore",
        "Sydney, Australia",
        "London, United Kingdom",
        "London, UK",
        "Paris, France",
        "Madrid, Spain",
        "Milan, Italy",
        "Amsterdam, Netherlands",
        "São Paulo, Brazil",
        "Mexico City, Mexico",
        "EMEA Region",
        "LATAM",
        "APAC",
        "Remote - Europe",
    ])
    def test_non_us_locations_rejected(self, location):
        job = _job(location=location)
        assert is_us_job(job) is False, f"Should reject: {location}"


# ===========================================================================
# 2. US FILTER — Acceptances
# ===========================================================================

class TestUSFilterAcceptances:
    """Jobs with US signals MUST be accepted."""

    @pytest.mark.parametrize("location", [
        "Remote US",
        "Remote - United States",
        "United States",
        "USA",
        "New York, NY",
        "San Francisco, California",
        "Austin, Texas",
        "Seattle, Washington",
        "Miami, Florida",
        "Arlington, Virginia",
        "Remote, US",
        "U.S.",
    ])
    def test_us_locations_accepted(self, location):
        job = _job(location=location)
        assert is_us_job(job) is True, f"Should accept: {location}"

    def test_us_state_names_accepted(self):
        """Every US state name should be recognized."""
        for state in [
            "California", "Texas", "New York", "Washington",
            "Florida", "Virginia", "Illinois", "Ohio",
            "Pennsylvania", "Georgia", "Colorado", "Oregon",
        ]:
            job = _job(location=f"Remote, {state}")
            assert is_us_job(job) is True, f"Should accept state: {state}"


# ===========================================================================
# 3. US FILTER — Override (explicit US + blocked country)
# ===========================================================================

class TestUSFilterOverride:
    """Jobs with BOTH a blocked country and an explicit US signal should be ACCEPTED."""

    @pytest.mark.parametrize("location", [
        "Remote US, India Office",
        "US Citizens, Germany Optional",
        "United States (India Support Team)",
    ])
    def test_us_override_with_blocked_country(self, location):
        job = _job(location=location)
        assert is_us_job(job) is True, (
            f"Should accept because of explicit US signal: {location}"
        )


# ===========================================================================
# 4. REMOTE FILTER
# ===========================================================================

class TestRemoteFilter:
    """Remote jobs MUST be accepted; onsite/hybrid MUST be rejected."""

    @pytest.mark.parametrize("location,expected", [
        ("Remote", True),
        ("Fully Remote", True),
        ("Remote US", True),
        ("Remote - United States", True),
        ("Work From Home", True),
        ("Hybrid - New York", False),
        ("Onsite - San Francisco", False),
        ("In-Office Only", False),
    ])
    def test_remote_filter(self, location, expected):
        job = _job(location=location, remote_type=location)
        result = is_remote_job(job)
        label = "accept" if expected else "reject"
        assert result is expected, f"Should {label}: {location}"

    def test_explicit_remote_flag(self):
        job = _job(location="San Francisco, CA", remote=True)
        assert is_remote_job(job) is True

    def test_no_remote_signal_rejected(self):
        job = _job(location="New York, NY")
        assert is_remote_job(job) is False


# ===========================================================================
# 5. DATE FILTER (is_recent_job)
# ===========================================================================

class TestDateFilter:
    """Only jobs within the lookback window should pass."""

    def test_yesterday_accepted(self):
        yesterday = _today() - timedelta(days=1)
        assert is_recent_job(yesterday, lookback_days=10) is True

    def test_today_accepted(self):
        assert is_recent_job(_today(), lookback_days=10) is True

    def test_5_days_ago_accepted(self):
        dt = _today() - timedelta(days=5)
        assert is_recent_job(dt, lookback_days=10) is True

    def test_10_days_ago_accepted(self):
        dt = _today() - timedelta(days=10)
        assert is_recent_job(dt, lookback_days=10) is True

    def test_11_days_ago_rejected(self):
        dt = _today() - timedelta(days=11)
        assert is_recent_job(dt, lookback_days=10) is False

    def test_30_days_ago_rejected(self):
        dt = _today() - timedelta(days=30)
        assert is_recent_job(dt, lookback_days=10) is False

    def test_none_date_rejected(self):
        assert is_recent_job(None, lookback_days=10) is False

    def test_custom_lookback(self):
        dt = _today() - timedelta(days=4)
        assert is_recent_job(dt, lookback_days=3) is False
        assert is_recent_job(dt, lookback_days=5) is True
