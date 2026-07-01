"""Source adapter: SkipTheDrive (skipthedrive.com).

SkipTheDrive aggregates remote job listings. We attempt to fetch their public
RSS feed for technology/development jobs.

Compliance: public pages only, no login, polite rate limiting.
"""
from __future__ import annotations

from typing import List

import httpx

from app.config import settings
from app.scraper.sources.base import BaseSource, RawJob

_FEED_URL = "https://www.skipthedrive.com/feed/"


class SkipTheDriveSource(BaseSource):
    name = "SkipTheDrive"
    type = "api"
    base_url = "https://www.skipthedrive.com"
    uses_api = False
    robots_checked = True
    tos_checked = True
    failure_status = "blocked"

    def __init__(self) -> None:
        super().__init__()
        self.status = "active" if settings.enable_skipthedrive else "skipped"
        if self.status == "skipped":
            self.reason_if_skipped = "Disabled via ENABLE_SKIPTHEDRIVE=false."

    def fetch(self, keyword: str) -> List[RawJob]:
        try:
            items = self._get_rss(_FEED_URL)
        except (httpx.HTTPError, ValueError) as exc:
            self.logger.warning("SkipTheDrive feed failed: %s", exc)
            raise

        results: List[RawJob] = []
        for item in items:
            title = item.get("title", "")
            desc = item.get("description", "") or item.get("encoded", "")
            link = item.get("link", "") or item.get("guid", "")
            pub_date = item.get("pubDate", "")

            # Try to extract company from title "Title at Company"
            company = ""
            if " at " in title:
                parts = title.rsplit(" at ", 1)
                if len(parts) == 2:
                    company = parts[1].strip()

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
        self.logger.info("SkipTheDrive returned %d jobs for '%s'", len(results), keyword)
        return results
