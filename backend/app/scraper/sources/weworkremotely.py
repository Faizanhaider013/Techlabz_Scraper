"""Source adapter: We Work Remotely (weworkremotely.com).

We Work Remotely publishes public RSS feeds per category. We fetch the
programming category feed and filter client-side by keyword. All WWR jobs
are remote by definition.

Compliance: public RSS feed, no login, polite rate limiting.
"""
from __future__ import annotations

from typing import List

import httpx

from app.config import settings
from app.scraper.sources.base import BaseSource, RawJob

# Public RSS feeds by category.
_FEED_URLS = [
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
    "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-front-end-programming-jobs.rss",
]


class WeWorkRemotelySource(BaseSource):
    name = "WeWorkRemotely"
    type = "api"
    base_url = "https://weworkremotely.com"
    uses_api = True
    robots_checked = True
    tos_checked = True

    def __init__(self) -> None:
        super().__init__()
        self.status = "active" if settings.enable_weworkremotely else "skipped"
        if self.status == "skipped":
            self.reason_if_skipped = "Disabled via ENABLE_WEWORKREMOTELY=false."

    def fetch(self, keyword: str) -> List[RawJob]:
        results: List[RawJob] = []
        for feed_url in _FEED_URLS:
            try:
                items = self._get_rss(feed_url)
            except (httpx.HTTPError, ValueError) as exc:
                self.logger.warning("WWR feed %s failed: %s", feed_url, exc)
                continue

            for item in items:
                title = item.get("title", "")
                desc = item.get("description", "")
                link = item.get("link", "") or item.get("guid", "")
                pub_date = item.get("pubDate", "")

                # Extract company from title pattern "Company: Title"
                company = ""
                if ":" in title:
                    parts = title.split(":", 1)
                    company = parts[0].strip()
                    title = parts[1].strip()

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
        self.logger.info("WeWorkRemotely returned %d jobs for '%s'", len(results), keyword)
        return results
