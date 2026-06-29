"""Deliberately blocked sources.

These job boards prohibit unauthorized scraping in their Terms of Service and/or
actively block crawlers. We keep them as visible, no-op stubs so they appear in
the sources report with an explicit reason, instead of being silently omitted.
None of them are ever queried (the engine only runs ``status == 'active'``).

To integrate any of these compliantly you would need an official partner / data
API and credentials -- then set ``status='active'`` and implement ``fetch``.
"""
from __future__ import annotations

from typing import List

from app.scraper.sources.base import BaseSource, RawJob


class _BlockedSource(BaseSource):
    type = "career_page"
    status = "blocked"
    uses_api = False
    robots_checked = True
    tos_checked = True

    def fetch(self, keyword: str) -> List[RawJob]:  # pragma: no cover - never called
        raise RuntimeError(f"{self.name} is blocked for compliance reasons.")


class LinkedInSource(_BlockedSource):
    name = "LinkedIn"
    base_url = "https://www.linkedin.com/jobs"
    reason_if_skipped = (
        "Terms of Service prohibit unauthorized scraping; no free public jobs API. "
        "Requires an official LinkedIn Talent Solutions / partner API agreement."
    )


class IndeedSource(_BlockedSource):
    name = "Indeed"
    base_url = "https://www.indeed.com"
    reason_if_skipped = (
        "Direct scraping skipped for compliance and blocking risk. The open "
        "Publisher API was retired for most new users and now needs approval. "
        "TODO (PM): evaluate Indeed Publisher/Employer API access."
    )


class SimplyHiredSource(_BlockedSource):
    name = "SimplyHired"
    base_url = "https://www.simplyhired.com"
    reason_if_skipped = (
        "Part of the Indeed network; direct scraping skipped for compliance and "
        "blocking risk. No approved public API for this use case."
    )


class GlassdoorSource(_BlockedSource):
    name = "Glassdoor"
    base_url = "https://www.glassdoor.com"
    reason_if_skipped = (
        "Jobs/content are restricted and scraping is prohibited by Terms of "
        "Service. API access is partner-gated. TODO (PM): evaluate partner program."
    )


class ZipRecruiterSource(_BlockedSource):
    name = "ZipRecruiter"
    base_url = "https://www.ziprecruiter.com"
    reason_if_skipped = (
        "Terms of Service restrict scraping/crawling. Partner/publisher API access "
        "required before any integration."
    )


ALL_BLOCKED = [
    LinkedInSource(),
    IndeedSource(),
    SimplyHiredSource(),
    GlassdoorSource(),
    ZipRecruiterSource(),
]
