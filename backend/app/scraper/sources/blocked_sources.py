"""Deliberately blocked / skipped sources.

These job boards are blocked for compliance reasons (TOS, login/paywall,
anti-bot, discontinued) or are not viable job boards. We keep them as visible,
no-op stubs so they appear in the sources report with an explicit reason,
instead of being silently omitted.
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


class _SkippedSource(BaseSource):
    type = "career_page"
    status = "skipped"
    uses_api = False
    robots_checked = True
    tos_checked = True

    def fetch(self, keyword: str) -> List[RawJob]:  # pragma: no cover - never called
        raise RuntimeError(f"{self.name} is skipped: {self.reason_if_skipped}")


# --- Existing blocked sources ---

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


# --- New blocked / skipped sources ---

class FlexJobsSource(_BlockedSource):
    name = "FlexJobs"
    base_url = "https://www.flexjobs.com"
    reason_if_skipped = (
        "Paywalled: requires paid membership for full job listings. "
        "No public API or free access. Not bypassing paywall per policy."
    )


class ToptalSource(_SkippedSource):
    name = "Toptal"
    base_url = "https://www.toptal.com"
    reason_if_skipped = (
        "Talent marketplace, not a normal public job board. "
        "No public job/project listing pages available for scraping."
    )


class VirtualVocationsSource(_SkippedSource):
    name = "VirtualVocations"
    base_url = "https://www.virtualvocations.com"
    reason_if_skipped = (
        "Requires paid membership for full job access. "
        "Public snippets only; insufficient data for useful listings."
    )


class StackOverflowJobsSource(_SkippedSource):
    name = "StackOverflowJobs"
    base_url = "https://stackoverflow.com/jobs"
    reason_if_skipped = (
        "Stack Overflow Jobs was discontinued in 2022. "
        "No active public job board exists. Legacy source."
    )


class RemoteHabitsSource(_SkippedSource):
    name = "RemoteHabits"
    base_url = "https://remotehabits.com"
    reason_if_skipped = (
        "Content/interview site about remote work; does not host an actual "
        "job board with job postings."
    )


class WellfoundSource(_BlockedSource):
    name = "Wellfound"
    base_url = "https://wellfound.com"
    reason_if_skipped = (
        "Formerly AngelList Talent. Requires login for full job access. "
        "Anti-bot protections active. Not bypassing login per policy."
    )


class UpworkSource(_BlockedSource):
    name = "Upwork"
    base_url = "https://www.upwork.com"
    reason_if_skipped = (
        "Gated marketplace platform. Project/job pages require authentication. "
        "Terms of Service prohibit scraping. Not bypassing per policy."
    )


class FreelancerSource(_BlockedSource):
    name = "Freelancer"
    base_url = "https://www.freelancer.com"
    reason_if_skipped = (
        "Gated marketplace. Login required for project details. "
        "Anti-bot protections active. Not bypassing per policy."
    )


class RemoteRocketshipSource(_SkippedSource):
    name = "RemoteRocketship"
    base_url = "https://remoterocketship.com"
    reason_if_skipped = (
        "No clear public job source page or API verified. "
        "May only aggregate or link to other boards."
    )


class RemoteOfAsiaSource(_SkippedSource):
    name = "RemoteOfAsia"
    base_url = "https://remoteofasia.com"
    reason_if_skipped = (
        "No verified public source / API. Asia-focused; most jobs would be "
        "rejected by US location filter anyway."
    )


class RemoteOKEuropeSource(_SkippedSource):
    name = "RemoteOKEurope"
    base_url = "https://remoteok.com"
    reason_if_skipped = (
        "Not a separate source; RemoteOK Europe is just a category/filter on "
        "RemoteOK. Jobs already fetched by the existing RemoteOK adapter. "
        "No duplication needed."
    )


ALL_BLOCKED = [
    # --- Original blocked ---
    LinkedInSource(),
    IndeedSource(),
    SimplyHiredSource(),
    GlassdoorSource(),
    ZipRecruiterSource(),
    # --- New blocked / skipped ---
    FlexJobsSource(),
    ToptalSource(),
    VirtualVocationsSource(),
    StackOverflowJobsSource(),
    RemoteHabitsSource(),
    WellfoundSource(),
    UpworkSource(),
    FreelancerSource(),
    RemoteRocketshipSource(),
    RemoteOfAsiaSource(),
    RemoteOKEuropeSource(),
]
