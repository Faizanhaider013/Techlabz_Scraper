"""Tests for the ServiceNow taxonomy and the smart query builder."""
from __future__ import annotations

from app.scraper import servicenow_taxonomy as tax
from app.scraper.query_builder import build_search_queries, query_categories


def test_module_detection_finds_codes():
    assert "ITSM" in tax.detect_modules("ServiceNow ITSM incident management")
    assert "CMDB" in tax.detect_modules("CMDB and CSDM configuration item work")
    assert "HRSD" in tax.detect_modules("Human Resources Service Delivery and Employee Center")
    assert tax.detect_modules("Salesforce Apex developer") == []


def test_strong_terms_are_servicenow_specific():
    assert "GlideRecord" in tax.detect_strong_terms("writes GlideRecord queries")
    assert "Script Include" in tax.detect_strong_terms("builds a Script Include")
    # A generic ITSM phrase is not a strong, decisive term.
    assert tax.detect_strong_terms("incident management process") == []


def test_core_terms_normalize_spellings():
    assert "ServiceNow" in tax.detect_core_terms("Service-Now developer")
    assert "Now Platform" in tax.detect_core_terms("expert on the Now Platform")


def test_role_detection():
    assert "ServiceNow Developer" in tax.detect_roles("Senior ServiceNow Developer wanted")


def test_module_codes_and_labels():
    codes = tax.all_module_codes()
    assert "ITSM" in codes and "SecOps" in codes
    assert tax.module_label("IRM/GRC") == "IRM/GRC"
    assert tax.module_label("ITAM") == "ITAM/SAM/HAM"


def test_iter_all_terms_groups():
    groups = tax.iter_all_terms()
    assert "Core ServiceNow" in groups
    assert any(k.startswith("Module:") for k in groups)


def test_query_builder_generates_capped_unique_queries():
    queries = build_search_queries()
    assert any("PHP Developer" in q for q in queries)
    assert any("React Developer" in q for q in queries)
    assert any("ServiceNow" in q for q in queries)
    assert any("Remote US" in q for q in queries)
    # No duplicates (case-insensitive) and capped at MAX_QUERIES_PER_SOURCE.
    lowered = [q.lower() for q in queries]
    assert len(lowered) == len(set(lowered))
    assert len(queries) <= 100


def test_query_categories_grouped_by_category_name():
    cats = query_categories()
    # Keys are human category names; each maps to a list of generated queries.
    assert "ServiceNow" in cats
    assert any("PHP" in name for name in cats)
    assert all(isinstance(v, list) and v for v in cats.values())
