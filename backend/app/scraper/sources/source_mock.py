"""DEVELOPMENT-ONLY mock source: sample ServiceNow remote US jobs.

This adapter is **disabled by default**. It only becomes active when
``ENABLE_MOCK_DATA=true`` in the environment. It exists so developers can see the
end-to-end pipeline and UI working even when the live compliant APIs currently
have zero genuine ServiceNow remote-US listings.

It is clearly labelled as mock data (source_name = "MockDev") and must NEVER be
enabled in production. Every record still passes the same strict relevance filter
as real data.
"""
from __future__ import annotations

from typing import List

from app.config import settings
from app.scraper.sources.base import BaseSource, RawJob

# Realistic sample listings. All are genuine ServiceNow + remote + US shaped.
_SAMPLES = [
    {
        "title": "ServiceNow Developer (Remote, US)",
        "company": "Northwind Consulting",
        "location": "Remote - United States",
        "tags": ["servicenow", "itsm", "javascript", "glide"],
        "salary": "$120,000 - $150,000",
        "job_type": "Full-time",
        "desc": "We are hiring a ServiceNow Developer to build ITSM and CMDB "
                "workflows. Fully remote within the United States. Experience with "
                "Glide, Flow Designer and scoped apps required.",
        "id": "mock-sn-dev-1",
    },
    {
        "title": "Senior ServiceNow Architect",
        "company": "BluePeak Technologies",
        "location": "Remote, USA",
        "tags": ["servicenow", "architecture", "hrsd", "csm"],
        "salary": "$160,000 - $185,000",
        "job_type": "Full-time",
        "desc": "Lead ServiceNow platform architecture across ITSM, HRSD and CSM. "
                "Remote role open to candidates anywhere in the United States.",
        "id": "mock-sn-arch-2",
    },
    {
        "title": "ServiceNow ITSM Administrator",
        "company": "Cascade Health Systems",
        "location": "Remote United States",
        "tags": ["servicenow", "itsm", "cmdb", "discovery"],
        "salary": None,
        "job_type": "Contract",
        "desc": "Administer our ServiceNow instance: ITSM, CMDB and Discovery. "
                "100% remote, US-based candidates only.",
        "id": "mock-sn-admin-3",
    },
]


class MockDevSource(BaseSource):
    name = "MockDev"
    type = "mock"
    base_url = None
    uses_api = False
    robots_checked = True
    tos_checked = True

    def __init__(self) -> None:
        super().__init__()
        # Active only when explicitly enabled for development.
        self.status = "active" if settings.enable_mock_data else "skipped"
        if not settings.enable_mock_data:
            self.reason_if_skipped = (
                "Development-only mock data. Enabled with ENABLE_MOCK_DATA=true; "
                "never used in production."
            )

    def fetch(self, keyword: str) -> List[RawJob]:
        results: List[RawJob] = []
        for s in _SAMPLES:
            results.append(
                RawJob(
                    title=s["title"],
                    company_name=s["company"],
                    location=s["location"],
                    date_posted_raw="today",
                    job_type=s["job_type"],
                    salary=s["salary"],
                    full_description=s["desc"],
                    original_apply_url=f"https://example.com/jobs/{s['id']}",
                    source_name=self.name,
                    source_job_id=s["id"],
                    remote_type="remote",
                    remote_flag=True,
                    tags=s["tags"],
                    candidate_required_location=s["location"],
                )
            )
        self.logger.info("MockDev returned %d sample jobs", len(results))
        return results
