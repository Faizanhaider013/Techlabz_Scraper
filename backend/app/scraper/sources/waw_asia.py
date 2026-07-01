"""Source adapter: Waw Asia (waw.asia/jobs).

Asia-focused remote jobs. We attempt to fetch public job listing pages.
Since this is Asia-focused, most jobs may be rejected by the US location filter
unless they are tagged as worldwide remote.

Compliance: public pages only, no login, polite rate limiting.
"""
from __future__ import annotations

from typing import List

import httpx

from app.config import settings
from app.scraper.sources.base import BaseSource, RawJob

_FEED_URL = "https://waw.asia/feed"


class WawAsiaSource(BaseSource):
    name = "WawAsia"
    type = "api"
    base_url = "https://waw.asia"
    uses_api = False
    robots_checked = True
    tos_checked = True
    failure_status = "blocked"

    def __init__(self) -> None:
        super().__init__()
        self.status = "active" if settings.enable_waw_asia else "skipped"
        if self.status == "skipped":
            self.reason_if_skipped = "Disabled via ENABLE_WAW_ASIA=false."

    def fetch(self, keyword: str) -> List[RawJob]:
        try:
            items = self._get_rss(_FEED_URL)
        except (httpx.HTTPError, ValueError) as exc:
            self.logger.warning("WawAsia feed failed: %s", exc)
            raise

        results: List[RawJob] = []
        for item in items:
            title = item.get("title", "")
            desc = item.get("description", "") or item.get("encoded", "")
            link = item.get("link", "") or item.get("guid", "")
            pub_date = item.get("pubDate", "")

            results.append(
                RawJob(
                    title=title,
                    company_name="",
                    location="Asia Remote",
                    date_posted_raw=pub_date or None,
                    full_description=desc,
                    original_apply_url=link,
                    source_name=self.name,
                    source_job_id=link,
                    remote_type="remote",
                    remote_flag=True,
                    candidate_required_location="Asia",
                )
            )
        self.logger.info("WawAsia returned %d jobs for '%s'", len(results), keyword)
        return results
