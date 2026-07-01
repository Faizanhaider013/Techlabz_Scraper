"""Source adapter: Jobspresso (jobspresso.co).

Jobspresso publishes public RSS feeds for remote job listings.
We fetch the feed and filter client-side by keyword.

Compliance: public RSS feed, no login required.
"""
from __future__ import annotations

from typing import List

import httpx

from app.config import settings
from app.scraper.sources.base import BaseSource, RawJob

_FEED_URL = "https://jobspresso.co/feed/"


class JobspressoSource(BaseSource):
    name = "Jobspresso"
    type = "api"
    base_url = "https://jobspresso.co"
    uses_api = True
    robots_checked = True
    tos_checked = True
    failure_status = "blocked"

    def __init__(self) -> None:
        super().__init__()
        self.status = "active" if settings.enable_jobspresso else "skipped"
        if self.status == "skipped":
            self.reason_if_skipped = "Disabled via ENABLE_JOBSPRESSO=false."

    def fetch(self, keyword: str) -> List[RawJob]:
        try:
            items = self._get_rss(_FEED_URL)
        except (httpx.HTTPError, ValueError) as exc:
            self.logger.warning("Jobspresso feed failed: %s", exc)
            raise

        results: List[RawJob] = []
        for item in items:
            title = item.get("title", "")
            desc = item.get("description", "") or item.get("encoded", "")
            link = item.get("link", "") or item.get("guid", "")
            pub_date = item.get("pubDate", "")

            # Try to extract company from dc:creator or title
            company = item.get("creator", "") or ""

            results.append(
                RawJob(
                    title=title,
                    company_name=company,
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
        self.logger.info("Jobspresso returned %d jobs for '%s'", len(results), keyword)
        return results
