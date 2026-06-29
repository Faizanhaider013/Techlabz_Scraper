"""Source adapter: Jobright (jobright.ai) -- best-effort, reports skipped/blocked.

Jobright is an AI job-matching product whose listings are behind an account /
single-page app; there is no confirmed public, unauthenticated jobs API or
crawlable listing for keyword search. Disabled by default (ENABLE_JOBRIGHT=false).

When disabled it is reported as ``skipped``. When explicitly enabled it makes a
best-effort public request and, if the data is not publicly accessible without
login, raises a descriptive error -> reported as ``blocked``. It never logs in
and never bypasses protections.
"""
from __future__ import annotations

import time
from typing import List

import httpx

from app.config import settings
from app.scraper.sources.base import BaseSource, RawJob

_PROBE_URL = "https://jobright.ai/jobs"


class JobrightSource(BaseSource):
    name = "Jobright"
    type = "career_page"
    base_url = "https://jobright.ai"
    uses_api = False
    robots_checked = True
    tos_checked = True
    failure_status = "blocked"

    def __init__(self) -> None:
        super().__init__()
        self.status = "active" if settings.enable_jobright else "skipped"
        if self.status == "skipped":
            self.reason_if_skipped = (
                "Disabled via ENABLE_JOBRIGHT=false. Listings require an account / "
                "are SPA-rendered; no confirmed public API. TODO (PM): confirm access."
            )

    def fetch(self, keyword: str) -> List[RawJob]:
        time.sleep(settings.request_delay_seconds)
        headers = {"User-Agent": "JobAggregatorBot/1.0 (+respects robots.txt)"}
        try:
            with httpx.Client(timeout=settings.request_timeout_seconds, follow_redirects=True) as c:
                resp = c.get(_PROBE_URL, headers=headers)
        except httpx.HTTPError as exc:
            raise RuntimeError(f"request error reaching Jobright: {exc}") from exc

        if resp.status_code != 200:
            raise RuntimeError(
                f"HTTP {resp.status_code} - Jobright public listing not accessible "
                "without an account. Not bypassed per policy."
            )
        # SPA shell with no server-rendered jobs -> nothing to parse publicly.
        raise RuntimeError(
            "Jobright serves a single-page app with no public job data in HTML "
            "and no confirmed public API. Login/bypass is out of scope."
        )
