"""Source adapter: Hiring Cafe (hiring.cafe) -- best-effort, reports blocked.

We make a real best-effort attempt against Hiring Cafe's public surface. Findings
recorded at runtime in /api/scraper/diagnostics:

  * robots.txt disallows the search mechanism (``Disallow: /*?searchState=*`` and
    ``/jobs/*?page=*``) -- exactly how the UI queries jobs.
  * The internal search endpoint is undocumented and does not respond to plain
    public requests (observed HTTP 405/404), i.e. there is no usable public JSON
    API for keyword search.

The adapter probes the endpoint and, when it does not return usable JSON jobs,
raises a descriptive error so the source is reported as ``blocked`` with the
exact reason -- never silently failing, never bypassing controls.

To enable later: confirm an officially supported public/partner API (or written
permission), then implement parsing here.
"""
from __future__ import annotations

import time
from typing import List

import httpx

from app.config import settings
from app.scraper.sources.base import BaseSource, RawJob

_PROBE_URL = "https://hiring.cafe/api/search-jobs"


class HiringCafeSource(BaseSource):
    name = "Hiring Cafe"
    type = "career_page"
    base_url = "https://hiring.cafe"
    uses_api = False
    robots_checked = True
    tos_checked = True
    failure_status = "blocked"

    def __init__(self) -> None:
        super().__init__()
        self.status = "active" if settings.enable_hiring_cafe else "skipped"
        if self.status == "skipped":
            self.reason_if_skipped = "Disabled via ENABLE_HIRING_CAFE=false."

    def fetch(self, keyword: str) -> List[RawJob]:
        time.sleep(settings.request_delay_seconds)
        headers = {
            "User-Agent": "JobAggregatorBot/1.0 (+respects robots.txt)",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {"searchQuery": keyword, "size": 20}
        try:
            with httpx.Client(timeout=settings.request_timeout_seconds) as c:
                resp = c.post(_PROBE_URL, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise RuntimeError(f"request error reaching Hiring Cafe: {exc}") from exc

        if resp.status_code != 200:
            raise RuntimeError(
                f"HTTP {resp.status_code} - no usable public Hiring Cafe API "
                "(undocumented internal endpoint; robots disallows the search path)."
            )
        try:
            data = resp.json()
        except ValueError as exc:
            raise RuntimeError("Hiring Cafe response was not JSON.") from exc

        jobs = data.get("jobs") if isinstance(data, dict) else None
        if not jobs:
            raise RuntimeError(
                "Hiring Cafe endpoint returned no usable job array; no documented "
                "public API. Needs confirmed access before activation."
            )
        # If a future public API returns jobs, map them here.
        return []
