"""Tests for the strict relevance filter (ServiceNow + Remote + US)."""
from __future__ import annotations

import pytest

from app.scraper.relevance import (
    is_allowed_job,
    is_remote_job,
    is_servicenow_job,
    is_us_job,
    normalize_text,
)


def job(title="", location="", description="", tags=None, candidate=None, remote=None):
    return {
        "title": title,
        "location": location,
        "full_description": description,
        "short_description": description,
        "tags": tags or [],
        "candidate_required_location": candidate if candidate is not None else location,
        "remote": remote,
    }


# ---------------------------------------------------------------------------
# Jobs that MUST pass
# ---------------------------------------------------------------------------
PASS_CASES = [
    job(title="ServiceNow Developer - Remote US", location="Remote US"),
    job(title="Service Now Administrator", location="United States Remote"),
    job(title="Senior ServiceNow Architect", location="Remote, USA"),
    job(title="ServiceNow ITSM Consultant", location="Remote United States"),
]


@pytest.mark.parametrize("data", PASS_CASES, ids=lambda d: d["title"])
def test_allowed_jobs_pass(data):
    allowed, reasons, _cls = is_allowed_job(data)
    assert allowed is True, f"Expected pass but got reasons={reasons}"
    assert "allowed" in reasons


# ---------------------------------------------------------------------------
# Jobs that MUST fail (multi-stack: relevant role but wrong location, or not a
# tech role at all).
# ---------------------------------------------------------------------------
def test_staff_product_engineer_brazil_fails():
    # Relevant role (software engineer) but Brazil -> not US.
    allowed, reasons, _ = is_allowed_job(job(title="Staff Product Engineer", location="Brazil"))
    assert allowed is False
    assert "not_us" in reasons


def test_quality_engineer_sao_paulo_fails():
    allowed, _, _ = is_allowed_job(job(title="Senior Quality Engineer", location="São Paulo"))
    assert allowed is False


def test_python_developer_remote_worldwide_fails():
    allowed, reasons, _ = is_allowed_job(
        job(title="Python Developer", location="Remote Worldwide")
    )
    assert allowed is False
    # Relevant + remote, but worldwide is not US-eligible by default.
    assert "not_us" in reasons


def test_frontend_engineer_remote_europe_fails():
    allowed, reasons, _ = is_allowed_job(
        job(title="Frontend Engineer", location="Remote Europe")
    )
    assert allowed is False
    assert "not_us" in reasons


def test_servicenow_developer_india_onsite_fails():
    # ServiceNow yes, but India + onsite (not US, not remote).
    allowed, reasons, _ = is_allowed_job(
        job(title="ServiceNow Developer", location="India", description="onsite role in Bangalore")
    )
    assert allowed is False
    assert "not_us" in reasons


def test_marketing_manager_remote_us_fails_not_relevant():
    # Non-tech role: rejected as not relevant even though Remote + US.
    allowed, reasons, _ = is_allowed_job(
        job(title="Marketing Manager", location="Remote US")
    )
    assert allowed is False
    assert "not_relevant" in reasons


def test_quality_engineer_remote_us_fails():
    # Multi-stack: QA is not a supported category and is explicitly rejected.
    allowed, reasons, _ = is_allowed_job(
        job(title="QA Engineer", location="Remote US", remote=True)
    )
    assert allowed is False
    assert "not_relevant" in reasons


# ---------------------------------------------------------------------------
# Unit-level checks
# ---------------------------------------------------------------------------
def test_normalize_unifies_service_now():
    assert "servicenow" in normalize_text("Service Now Developer")
    assert "servicenow" in normalize_text("service-now admin")


def test_is_servicenow_excludes_generic():
    assert is_servicenow_job(job(title="ServiceNow Developer")) is True
    assert is_servicenow_job(job(title="Senior Backend Developer")) is False


def test_is_remote_rejects_onsite():
    assert is_remote_job(job(location="Remote US")) is True
    assert is_remote_job(job(location="New York", description="onsite only")) is False


def test_is_us_rejects_other_countries():
    assert is_us_job(job(location="United States")) is True
    assert is_us_job(job(location="Germany")) is False
    assert is_us_job(job(location="Remote Worldwide")) is False


def test_is_us_recognizes_states_and_codes():
    # ATS-style concrete US locations should be recognized.
    assert is_us_job(job(location="Austin, TX")) is True
    assert is_us_job(job(location="Remote - California")) is True
    assert is_us_job(job(location="New York, NY (HQ)")) is True
    # Non-US should still fail.
    assert is_us_job(job(location="Remote, Italy")) is False
    assert is_us_job(job(location="Berlin, Germany")) is False


def test_ats_servicenow_remote_us_job_passes():
    # Mirrors a real Greenhouse/Lever/Ashby ServiceNow listing.
    allowed, reasons, _ = is_allowed_job(
        job(
            title="ServiceNow Developer",
            location="Remote - US",
            description="Build ServiceNow ITSM workflows. Remote within the US.",
            remote=True,
        )
    )
    assert allowed is True, reasons


def test_explicitly_rejected_roles():
    # Python role (no allowed stack signal) -> rejected
    allowed, reasons, _ = is_allowed_job(job(title="Python Developer", location="Remote US"))
    assert allowed is False
    assert "not_relevant" in reasons

    # DevOps role (no allowed stack signal) -> rejected
    allowed, reasons, _ = is_allowed_job(job(title="DevOps Engineer", location="Remote US"))
    assert allowed is False
    assert "not_relevant" in reasons

    # Python role WITH allowed stack signal (ServiceNow) -> allowed
    allowed, reasons, _ = is_allowed_job(job(title="ServiceNow Developer (Python a plus)", location="Remote US"))
    assert allowed is True, reasons
    assert "allowed" in reasons

    # Java role WITH allowed stack signal (React) -> allowed
    allowed, reasons, _ = is_allowed_job(job(title="React Frontend Developer (Java experience)", location="Remote US"))
    assert allowed is True, reasons
    assert "allowed" in reasons
