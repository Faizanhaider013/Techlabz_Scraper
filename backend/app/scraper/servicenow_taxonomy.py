"""ServiceNow taxonomy: the single source of truth for every term the scraper
searches for and scores against.

The portal is a ServiceNow *ecosystem* scraper, not just a "ServiceNow Developer"
search. This module enumerates:

  * CORE_TERMS        - the brand / platform names (ServiceNow, Now Platform, ...)
  * STRONG_TERMS      - ServiceNow-specific technical artifacts that are decisive
                        on their own (GlideRecord, Script Include, Flow Designer...)
  * WEAK_TERMS        - platform concepts that are real signals but also appear in
                        non-ServiceNow ITSM/CMDB/GRC jobs (CMDB, Discovery, ACL...)
  * MODULES           - every major product/module group + its keywords, keyed by a
                        stable code shared with the frontend module filter
  * ROLE_TITLES       - common ServiceNow role titles
  * INDUSTRY_TERMS    - industry workflow products
  * GENERIC_TERMS     - terms that, ALONE, must NOT make a job ServiceNow-relevant

Detection helpers are self-contained (their own light normalization) so this
module has no dependency on the relevance filter and cannot create import cycles.
"""
from __future__ import annotations

import re
from collections import OrderedDict
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Normalization (self-contained; mirrors relevance.normalize_text intentionally)
# ---------------------------------------------------------------------------
_WS_RE = re.compile(r"\s+")
_SERVICE_NOW_RE = re.compile(r"service[\s\-_]*now", re.IGNORECASE)


def normalize(text) -> str:
    """Lowercase, unify ServiceNow spellings, collapse whitespace.

    "Service Now", "service-now", "service_now" all become "servicenow".
    """
    if text is None:
        return ""
    if isinstance(text, (list, tuple, set)):
        text = " ".join(str(x) for x in text)
    t = str(text).lower()
    t = _SERVICE_NOW_RE.sub("servicenow", t)
    t = _WS_RE.sub(" ", t)
    return t.strip()


# ---------------------------------------------------------------------------
# 1. Core ServiceNow keywords
# ---------------------------------------------------------------------------
CORE_TERMS: List[str] = [
    "ServiceNow",
    "Service Now",
    "Service-Now",
    "Now Platform",
    "Now Assist",
    "ServiceNow Platform",
]

# ---------------------------------------------------------------------------
# 2. ServiceNow technical terms
#    Split into STRONG (decisive alone -> can accept a job without the literal
#    word "ServiceNow") and WEAK (real but also seen in generic ITSM jobs).
# ---------------------------------------------------------------------------
STRONG_TERMS: List[str] = [
    "GlideRecord",
    "GlideAjax",
    "Script Include",
    "Business Rule",
    "Client Script",
    "UI Policy",
    "UI Action",
    "Flow Designer",
    "Workflow Editor",
    "IntegrationHub",
    "Integration Hub",
    "MID Server",
    "REST Message",
    "SOAP Message",
    "Transform Map",
    "Import Set",
    "Update Set",
    "Scoped App",
    "Scoped Application",
    "Application Repository",
    "ATF",
    "Automated Test Framework",
    "Service Portal",
    "Employee Center",
    "UI Builder",
    "Agent Workspace",
    "Service Operations Workspace",
    "App Engine",
    "App Engine Studio",
    "Creator Workflows",
    "Now Assist",
    "Record Producer",
    "Catalog Item",
]

WEAK_TERMS: List[str] = [
    "ACL",
    "Workspace",
    "Service Catalog",
    "CMDB",
    "Discovery",
    "Service Mapping",
    "ITSM",
    "ITOM",
]

# All technical terms (for list-modules / matched_terms display).
TECHNICAL_TERMS: List[str] = STRONG_TERMS + WEAK_TERMS

# ---------------------------------------------------------------------------
# 3-13. Modules. Code -> (display label, [keywords]). The code is the stable
# identifier shared with the frontend module filter and stored on saved jobs.
# ---------------------------------------------------------------------------
MODULES: "OrderedDict[str, Tuple[str, List[str]]]" = OrderedDict([
    ("ITSM", ("ITSM", [
        "ITSM", "Incident Management", "Problem Management", "Change Management",
        "Request Management", "Knowledge Management", "Service Catalog",
        "Catalog Item", "Catalog Items", "Record Producer", "SLA",
        "Major Incident Management", "Continual Improvement Management",
        "Walk-up Experience", "Universal Request",
    ])),
    ("ITOM", ("ITOM", [
        "ITOM", "Discovery", "Service Mapping", "Event Management",
        "Cloud Management", "Operational Intelligence", "AIOps",
        "Health Log Analytics", "Metric Intelligence", "Agent Client Collector",
        "ACC", "MID Server",
    ])),
    ("CMDB", ("CMDB", [
        "CMDB", "CSDM", "Common Service Data Model", "Configuration Item",
        "CI Class", "CI Relationship", "CMDB Health", "CMDB Data Manager",
        "Service Graph Connector", "Data Foundations",
        "Configuration Management Database",
    ])),
    ("ITAM", ("ITAM/SAM/HAM", [
        "ITAM", "IT Asset Management", "HAM", "Hardware Asset Management",
        "SAM", "Software Asset Management", "Software Asset Workspace",
        "Asset Lifecycle", "Contract Management", "Procurement",
        "License Management", "Entitlement Management",
    ])),
    ("HRSD", ("HRSD", [
        "HRSD", "Human Resources Service Delivery", "Employee Center",
        "Employee Center Pro", "HR Case Management", "Lifecycle Events",
        "Employee Journey", "HR Portal", "HR Knowledge", "HR Service Delivery",
    ])),
    ("CSM", ("CSM", [
        "CSM", "Customer Service Management", "Customer Service Portal",
        "Case Management", "Customer Communities", "Service Bridge",
    ])),
    ("FSM", ("FSM", [
        "FSM", "Field Service Management", "Dispatch", "Work Order Management",
    ])),
    ("SecOps", ("SecOps", [
        "SecOps", "Security Operations", "Security Incident Response", "SIR",
        "Vulnerability Response", "Threat Intelligence", "Security Incident",
        "Vulnerability Management", "Configuration Compliance",
    ])),
    ("IRM/GRC", ("IRM/GRC", [
        "IRM", "Integrated Risk Management", "GRC",
        "Governance Risk Compliance", "Policy and Compliance", "Risk Management",
        "Audit Management", "Vendor Risk Management", "Third Party Risk Management",
        "TPRM", "Business Continuity Management", "BCM", "Operational Risk",
    ])),
    ("SPM/ITBM", ("SPM/ITBM", [
        "SPM", "Strategic Portfolio Management", "ITBM", "IT Business Management",
        "Project Portfolio Management", "PPM", "Demand Management",
        "Resource Management", "Agile Development", "Agile 2.0",
        "Investment Funding", "Portfolio Planning",
    ])),
    ("App Engine", ("App Engine", [
        "App Engine", "App Engine Studio", "Creator Workflows",
        "Scoped Application", "Scoped App", "Application Repository",
    ])),
    ("Service Portal", ("Service Portal", [
        "Service Portal", "Employee Center", "Employee Center Pro",
    ])),
    ("Integration Hub", ("Integration Hub", [
        "Integration Hub", "IntegrationHub", "REST Message", "SOAP Message",
        "Spoke", "Flow Designer",
    ])),
    ("Discovery", ("Discovery", [
        "Discovery", "Service Mapping", "MID Server", "Agent Client Collector",
    ])),
    ("Flow Designer", ("Flow Designer", [
        "Flow Designer", "Process Automation Designer", "Workflow Editor",
        "Automation Engine",
    ])),
    ("Virtual Agent", ("Virtual Agent", [
        "Virtual Agent", "Now Assist", "Document Intelligence",
        "Predictive Intelligence",
    ])),
    ("Performance Analytics", ("Performance Analytics", [
        "Performance Analytics", "Reporting", "Dashboards",
    ])),
    ("DevOps", ("DevOps", [
        "ServiceNow DevOps", "DevOps Change Automation", "DevOps Config",
        "RPA Hub",
    ])),
])

# ---------------------------------------------------------------------------
# 13. Industry workflows
# ---------------------------------------------------------------------------
INDUSTRY_TERMS: List[str] = [
    "Financial Services Operations", "FSO",
    "Telecommunications Service Management", "TSM",
    "Public Sector Digital Services",
    "Healthcare and Life Sciences Service Management",
    "Manufacturing Connected Workforce", "ESG Management",
    "Legal Service Delivery", "Procurement Service Management",
    "Source-to-Pay Operations",
]

# ---------------------------------------------------------------------------
# 14. Common ServiceNow role titles
# ---------------------------------------------------------------------------
ROLE_TITLES: List[str] = [
    "ServiceNow Developer", "ServiceNow Administrator", "ServiceNow Admin",
    "ServiceNow Consultant", "ServiceNow Technical Consultant",
    "ServiceNow Functional Consultant", "ServiceNow Architect",
    "ServiceNow Solution Architect", "ServiceNow Platform Architect",
    "ServiceNow Engineer", "ServiceNow Platform Engineer",
    "ServiceNow Business Analyst", "ServiceNow Product Owner",
    "ServiceNow Platform Owner", "ServiceNow Implementation Specialist",
    "ServiceNow Integration Specialist", "ServiceNow Service Portal Developer",
    "ServiceNow HRSD Developer", "ServiceNow CSM Developer",
    "ServiceNow ITSM Developer", "ServiceNow ITOM Developer",
    "ServiceNow CMDB Analyst", "ServiceNow Discovery Engineer",
    "ServiceNow SecOps Consultant", "ServiceNow GRC Consultant",
    "ServiceNow IRM Consultant", "ServiceNow SPM Consultant",
    "ServiceNow SAM Consultant", "ServiceNow HAM Consultant",
    "ServiceNow App Engine Developer", "ServiceNow Workflow Developer",
    "ServiceNow QA Engineer", "ServiceNow Tester", "ServiceNow Support Engineer",
]

# ---------------------------------------------------------------------------
# Generic terms that, on their own (no ServiceNow evidence), must NOT accept.
# ---------------------------------------------------------------------------
GENERIC_TERMS: List[str] = [
    "ITSM", "CMDB", "GRC", "IRM", "HR", "HRSD", "ITOM", "ITAM", "CSM",
    "Security Operations", "Project Portfolio Management", "Incident Management",
    "Change Management", "Problem Management", "Service Management",
]


# ---------------------------------------------------------------------------
# Matching helpers
# ---------------------------------------------------------------------------
def _term_present(term: str, normalized_text: str) -> bool:
    """Word-boundary match of a (normalized) term inside already-normalized text."""
    if not term or not normalized_text:
        return False
    return re.search(r"\b" + re.escape(term) + r"\b", normalized_text) is not None


def _present_any(terms: List[str], normalized_text: str) -> List[str]:
    """Return the original-cased terms whose normalized form appears in the text."""
    found: List[str] = []
    seen = set()
    for term in terms:
        nterm = normalize(term)
        if nterm in seen:
            continue
        seen.add(nterm)
        if _term_present(nterm, normalized_text):
            found.append(term)
    return found


def detect_core_terms(text: str) -> List[str]:
    return _present_any(CORE_TERMS, normalize(text))


def detect_strong_terms(text: str) -> List[str]:
    """ServiceNow-specific technical terms that are decisive on their own."""
    return _present_any(STRONG_TERMS, normalize(text))


def detect_technical_terms(text: str) -> List[str]:
    return _present_any(TECHNICAL_TERMS, normalize(text))


def detect_roles(text: str) -> List[str]:
    return _present_any(ROLE_TITLES, normalize(text))


def detect_modules(text: str) -> List[str]:
    """Return the module codes whose keywords appear in the text."""
    ntext = normalize(text)
    codes: List[str] = []
    for code, (_label, keywords) in MODULES.items():
        if any(_term_present(normalize(kw), ntext) for kw in keywords):
            codes.append(code)
    return codes


def all_module_codes() -> List[str]:
    return list(MODULES.keys())


def module_label(code: str) -> str:
    entry = MODULES.get(code)
    return entry[0] if entry else code


def iter_all_terms() -> "OrderedDict[str, List[str]]":
    """Ordered groups for the ``list-modules`` CLI command."""
    groups: "OrderedDict[str, List[str]]" = OrderedDict()
    groups["Core ServiceNow"] = list(CORE_TERMS)
    groups["Strong technical terms"] = list(STRONG_TERMS)
    groups["Weaker / generic platform terms"] = list(WEAK_TERMS)
    for code, (label, keywords) in MODULES.items():
        groups[f"Module: {label} [{code}]"] = list(keywords)
    groups["Industry workflows"] = list(INDUSTRY_TERMS)
    groups["Role titles"] = list(ROLE_TITLES)
    return groups
