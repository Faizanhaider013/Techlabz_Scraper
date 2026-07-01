"""Source adapter: Europe Remotely (europeremotely.com).

Europe-focused remote jobs. We attempt to fetch their public RSS/listing pages.
Since this is Europe-focused, most jobs may be rejected by the US location filter
unless they are tagged as worldwide remote.

Compliance: public pages only, no login, polite rate limiting.
"""
from __future__ import annotations

from typing import List

import httpx

from app.config import settings
from app.scraper.sources.base import BaseSource, RawJob

_FEED_URL = "https://europeremotely.com/feed/"


class EuropeRemotelySource(BaseSource):
    name = "EuropeRemotely"
    type = "api"
    base_url = "https://europeremotely.com"
    uses_api = False
    robots_checked = True
    tos_checked = True
    failure_status = "blocked"

    def __init__(self) -> None:
        super().__init__()
        self.status = "active" if settings.enable_europe_remotely else "skipped"
        if self.status == "skipped":
            self.reason_if_skipped = "Disabled via ENABLE_EUROPE_REMOTELY=false."

    def fetch(self, keyword: str) -> List[RawJob]:
        try:
            items = self._get_rss(_FEED_URL)
        except (httpx.HTTPError, ValueError) as exc:
            self.logger.warning("EuropeRemotely feed failed: %s", exc)
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
                    location="Europe Remote",
                    date_posted_raw=pub_date or None,
                    full_description=desc,
                    original_apply_url=link,
                    source_name=self.name,
                    source_job_id=link,
                    remote_type="remote",
                    remote_flag=True,
                    candidate_required_location="Europe",
                )
            )
        self.logger.info("EuropeRemotely returned %d jobs for '%s'", len(results), keyword)
        return results
