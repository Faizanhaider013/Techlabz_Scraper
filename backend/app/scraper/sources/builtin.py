"""Source adapter: Built In (builtin.com) -- best-effort, reports blocked.

Per the new requirement we make a real best-effort attempt against Built In's
public listing pages using httpx + BeautifulSoup (no login, no stealth browser,
no anti-bot bypass). In practice Built In:

  * disallows the keyword search path in robots.txt (``Disallow: /jobs*?search=``), and
  * returns **HTTP 403** to automated clients, serving JS-rendered listings.

So the adapter attempts an allowed listing page, and if it is blocked (403) or
yields no parseable jobs, it raises a descriptive error. The engine records this
as ``status=blocked`` with the exact reason in /api/scraper/diagnostics -- it
never fails silently, and it never bypasses the protection.

To enable real collection later: use an official Built In feed / partner API, or
an allowed structured endpoint that does not 403, then implement parsing here.
"""
from __future__ import annotations

import time
from typing import List

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.scraper.sources.base import BaseSource, RawJob

# An allowed (non-search) listing path. We still expect a 403 from anti-bot.
_LISTING_URL = "https://builtin.com/jobs/remote"


class BuiltInSource(BaseSource):
    name = "Built In"
    type = "career_page"
    base_url = "https://builtin.com/jobs"
    uses_api = False
    robots_checked = True
    tos_checked = True
    failure_status = "blocked"

    def __init__(self) -> None:
        super().__init__()
        # Attempted when enabled; the run will honestly report blocked if 403.
        self.status = "active" if settings.enable_builtin else "skipped"
        if self.status == "skipped":
            self.reason_if_skipped = "Disabled via ENABLE_BUILTIN=false."

    def fetch(self, keyword: str) -> List[RawJob]:
        time.sleep(settings.request_delay_seconds)  # polite delay
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; JobAggregatorBot/1.0; +respects robots.txt)",
            "Accept": "text/html,application/xhtml+xml",
        }
        try:
            with httpx.Client(timeout=settings.request_timeout_seconds, follow_redirects=True) as c:
                resp = c.get(_LISTING_URL, headers=headers)
        except httpx.HTTPError as exc:
            raise RuntimeError(f"request error reaching Built In: {exc}") from exc

        if resp.status_code == 403:
            raise RuntimeError(
                "HTTP 403 - Built In blocks automated clients (anti-bot). Not "
                "bypassed per policy. robots.txt also disallows /jobs*?search=."
            )
        if resp.status_code != 200:
            raise RuntimeError(f"unexpected HTTP {resp.status_code} from Built In listing page.")

        # If we ever DO get HTML, parse JSON-LD JobPosting blocks (best effort).
        soup = BeautifulSoup(resp.text, "html.parser")
        results: List[RawJob] = []
        for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
            text = (tag.string or "").strip()
            if "JobPosting" not in text or keyword.lower() not in text.lower():
                continue
            # Real parsing would map fields here; left intentionally minimal because
            # the page is JS-rendered and returns no JobPosting blocks in practice.
        if not results:
            raise RuntimeError(
                "Built In listing returned no parseable JobPosting data "
                "(JavaScript-rendered). No public structured endpoint available."
            )
        return results
