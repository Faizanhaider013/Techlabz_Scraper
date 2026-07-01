"""Source adapter: Pangian (pangian.com).

Pangian is a remote work community with job listings. We attempt to fetch
public job pages. If login is required, it reports as blocked.

Compliance: public pages only, no login, no anti-bot bypass.
"""
from __future__ import annotations

from typing import List

import httpx

from app.config import settings
from app.scraper.sources.base import BaseSource, RawJob

_FEED_URL = "https://pangian.com/feed/"


class PangianSource(BaseSource):
    name = "Pangian"
    type = "api"
    base_url = "https://pangian.com"
    uses_api = False
    robots_checked = True
    tos_checked = True
    failure_status = "blocked"

    def __init__(self) -> None:
        super().__init__()
        self.status = "active" if settings.enable_pangian else "skipped"
        if self.status == "skipped":
            self.reason_if_skipped = "Disabled via ENABLE_PANGIAN=false."

    def fetch(self, keyword: str) -> List[RawJob]:
        try:
            items = self._get_rss(_FEED_URL)
        except (httpx.HTTPError, ValueError) as exc:
            self.logger.warning("Pangian feed failed: %s", exc)
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
                    location="Remote",
                    date_posted_raw=pub_date or None,
                    full_description=desc,
                    original_apply_url=link,
                    source_name=self.name,
                    source_job_id=link,
                    remote_type="remote",
                    remote_flag=True,
                    candidate_required_location="Remote",
                )
            )
        self.logger.info("Pangian returned %d jobs for '%s'", len(results), keyword)
        return results
