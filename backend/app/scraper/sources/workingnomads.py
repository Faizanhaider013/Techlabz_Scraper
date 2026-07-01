"""Source adapter: Working Nomads (workingnomads.com).

Working Nomads exposes a public API at
https://www.workingnomads.com/api/exposed_jobs/ that returns JSON job listings.
No API key required. All jobs are remote.

Compliance: public API, no login, polite rate limiting.
"""
from __future__ import annotations

from typing import List

import httpx

from app.config import settings
from app.scraper.sources.base import BaseSource, RawJob

_API_URL = "https://www.workingnomads.com/api/exposed_jobs/"


class WorkingNomadsSource(BaseSource):
    name = "WorkingNomads"
    type = "api"
    base_url = "https://www.workingnomads.com"
    uses_api = True
    robots_checked = True
    tos_checked = True

    def __init__(self) -> None:
        super().__init__()
        self.status = "active" if settings.enable_working_nomads else "skipped"
        if self.status == "skipped":
            self.reason_if_skipped = "Disabled via ENABLE_WORKING_NOMADS=false."

    def fetch(self, keyword: str) -> List[RawJob]:
        try:
            data = self._cached_get_json(_API_URL)
        except (httpx.HTTPError, ValueError) as exc:
            self.logger.warning("WorkingNomads fetch failed: %s", exc)
            raise

        if not isinstance(data, list):
            return []

        results: List[RawJob] = []
        for item in data:
            if not isinstance(item, dict):
                continue

            title = item.get("title", "")
            company = item.get("company_name", "")
            location = item.get("location", "Remote")
            tags = item.get("tags") or []
            tag_list = [t.get("name", "") for t in tags] if isinstance(tags, list) else []

            results.append(
                RawJob(
                    title=title,
                    company_name=company,
                    location=location or "Remote",
                    date_posted_raw=item.get("pub_date"),
                    job_type=item.get("category_name"),
                    full_description=item.get("description"),
                    original_apply_url=item.get("url", ""),
                    source_name=self.name,
                    source_job_id=str(item.get("id", "") or item.get("slug", "")),
                    remote_type="remote",
                    remote_flag=True,
                    tags=tag_list if tag_list else None,
                    category=item.get("category_name"),
                    candidate_required_location=location or "Remote",
                )
            )
        self.logger.info("WorkingNomads returned %d jobs for '%s'", len(results), keyword)
        return results
