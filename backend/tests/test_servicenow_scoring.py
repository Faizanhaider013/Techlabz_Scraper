"""Tests for score_servicenow_relevance: the ServiceNow ecosystem acceptance rule.

Covers every PASS / FAIL case from the product spec. PASS cases must be accepted
(is_servicenow True); FAIL cases (generic ITSM/CMDB/GRC, other platforms) must be
rejected so no irrelevant jobs are shown.
"""
from __future__ import annotations

import pytest

from app.scraper.relevance import score_servicenow_relevance


def _job(title="", description=""):
    return {"title": title, "full_description": description, "short_description": description}


# ---------------------------------------------------------------------------
# MUST be accepted
# ---------------------------------------------------------------------------
PASS_CASES = [
    _job("ServiceNow Developer", "Remote US ServiceNow role"),
    _job("ServiceNow ITSM Consultant", "Remote United States"),
    _job("ServiceNow CMDB Analyst", "Remote US, CMDB health"),
    _job("ServiceNow HRSD Developer", "Employee Center, Remote US"),
    _job("ServiceNow CSM Architect", "Customer Service Management, Remote US"),
    _job("ServiceNow SecOps Consultant", "Security Incident Response, Remote US"),
    _job("ServiceNow GRC / IRM Consultant", "Policy and Compliance, Remote US"),
    _job("ServiceNow App Engine Developer", "App Engine Studio, Remote US"),
    _job("ServiceNow Service Portal Developer", "Service Portal widgets, Remote US"),
    _job("Now Platform Engineer", "Build on the Now Platform, Remote US"),
    _job("Senior Developer", "Daily GlideRecord and Script Includes on the ServiceNow platform"),
]


@pytest.mark.parametrize("data", PASS_CASES, ids=lambda d: d["title"])
def test_servicenow_jobs_pass(data):
    result = score_servicenow_relevance(data)
    assert result["is_servicenow"] is True, f"Expected accept, got {result}"


# ---------------------------------------------------------------------------
# MUST be rejected (no ServiceNow evidence)
# ---------------------------------------------------------------------------
FAIL_CASES = [
    _job("ITSM Analyst", "Generic incident and change management, no platform named"),
    _job("CMDB Analyst", "Maintain the configuration management database"),
    _job("GRC Consultant", "Governance risk and compliance program management"),
    _job("Product Engineer", "Remote US product engineering, Python and Go"),
    _job("Salesforce Developer", "Apex, Visualforce, Lightning, Remote US"),
    _job("Workday HRSD Consultant", "HR service delivery implemented on Workday"),
    _job("Jira Service Management Admin", "Administer Jira Service Management, Remote US"),
]


@pytest.mark.parametrize("data", FAIL_CASES, ids=lambda d: d["title"])
def test_generic_jobs_fail(data):
    result = score_servicenow_relevance(data)
    assert result["is_servicenow"] is False, f"Expected reject, got {result}"


def test_score_shape_and_modules():
    result = score_servicenow_relevance(_job("ServiceNow ITSM Consultant", "incident management"))
    assert set(result) == {
        "score", "matched_terms", "matched_modules", "matched_roles",
        "is_servicenow", "reason",
    }
    assert "ITSM" in result["matched_modules"]
    assert result["score"] >= 100


def test_title_servicenow_scores_100():
    assert score_servicenow_relevance(_job("ServiceNow Developer"))["score"] >= 100


def test_generic_only_reason():
    result = score_servicenow_relevance(_job("CMDB Analyst", "configuration management database"))
    assert result["reason"] == "generic_only_no_servicenow"
