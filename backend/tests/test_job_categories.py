"""Tests for multi-stack category classification and the job taxonomy."""
from __future__ import annotations

import pytest

from app.scraper import job_taxonomy as jtax
from app.scraper.query_builder import build_search_queries
from app.scraper.relevance import classify_job_category, is_allowed_job, score_job_relevance


def _job(title, description="", location="Remote US"):
    return {
        "title": title,
        "full_description": description,
        "short_description": description,
        "location": location,
        "candidate_required_location": location,
        "remote": True,
    }


# ---------------------------------------------------------------------------
# Relevance: tech roles MUST be classified as relevant
# ---------------------------------------------------------------------------
PASS = [
    ("PHP Developer", "php"),
    ("Laravel Backend Developer", "laravel"),
    ("Node.js Developer", "node_backend"),
    ("React Developer", "react_frontend"),
    ("MERN Stack Developer", "mern"),
    ("MEAN Stack Developer", "mean"),
    ("ServiceNow Developer", "servicenow"),
]


@pytest.mark.parametrize("title,expected", PASS, ids=[p[0] for p in PASS])
def test_relevant_categories(title, expected):
    cls = classify_job_category(_job(title))
    assert cls["is_relevant"] is True, cls
    assert cls["primary_category"] == expected, cls


# ---------------------------------------------------------------------------
# Non-tech roles MUST be rejected as not relevant
# ---------------------------------------------------------------------------
FAIL = [
    "Sales Executive", "Marketing Manager", "Customer Support",
    "Content Strategist", "Product Manager", "Accountant", "Nurse", "Teacher",
    "Software Engineer", "Python Developer", "DevOps Engineer",
]


@pytest.mark.parametrize("title", FAIL)
def test_non_tech_rejected(title):
    cls = classify_job_category(_job(title))
    assert cls["is_relevant"] is False, cls


# ---------------------------------------------------------------------------
# Full funnel (relevance + remote + US) via is_allowed_job
# ---------------------------------------------------------------------------
def test_is_allowed_job_returns_triple_and_passes():
    allowed, reasons, cls = is_allowed_job(_job("React Developer Remote US"))
    assert allowed is True and "allowed" in reasons
    assert cls["primary_category"] == "react_frontend"


def test_is_allowed_job_rejects_non_tech():
    allowed, reasons, cls = is_allowed_job(_job("Sales Executive"))
    assert allowed is False and "not_relevant" in reasons


def test_servicenow_strict_rejects_generic_cmdb():
    cls = classify_job_category(_job("CMDB Analyst", "configuration management database"))
    assert cls["is_relevant"] is False


# ---------------------------------------------------------------------------
# Taxonomy / query builder
# ---------------------------------------------------------------------------
def test_all_categories_present():
    ids = jtax.all_category_ids()
    for cid in ["servicenow", "php", "laravel", "node_backend", "react_frontend",
                "mern", "mean"]:
        assert cid in ids


def test_score_job_relevance_for_single_category():
    r = score_job_relevance(_job("Laravel Developer"), "laravel")
    assert r["relevance_score"] >= 100
    assert any("laravel" in k.lower() for k in r["matched_keywords"])


from app.config import settings


def test_query_builder_covers_multiple_stacks(monkeypatch):
    monkeypatch.setattr(settings, "max_queries_per_source", 150)
    qs = build_search_queries()
    assert any("Laravel" in q for q in qs)
    assert any("Node.js" in q for q in qs)
    assert any("React" in q for q in qs)
    assert len(qs) <= 200
