"""Source adapter: NoDesk (nodesk.co).

NoDesk is a remote job board. We attempt to fetch public job listing pages.
If the site blocks automated access, it reports as blocked in diagnostics.

Compliance: public pages only, no login, polite rate limiting.
"""
from __future__ import annotations

from typing import List

import httpx

from app.config import settings
from app.scraper.sources.base import BaseSource, RawJob

_FEED_URL = "https://nodesk.co/remote-jobs/feed/"


class NoDeskSource(BaseSource):
    name = "NoDesk"
    type = "api"
    base_url = "https://nodesk.co"
    uses_api = False
    robots_checked = True
    tos_checked = True
    failure_status = "blocked"

    def __init__(self) -> None:
        super().__init__()
        self.status = "active" if settings.enable_nodesk else "skipped"
        if self.status == "skipped":
            self.reason_if_skipped = "Disabled via ENABLE_NODESK=false."

    def fetch(self, keyword: str) -> List[RawJob]:
        try:
            items = self._get_rss(_FEED_URL)
        except (httpx.HTTPError, ValueError) as exc:
            self.logger.warning("NoDesk feed failed: %s", exc)
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
        self.logger.info("NoDesk returned %d jobs for '%s'", len(results), keyword)
        return results
