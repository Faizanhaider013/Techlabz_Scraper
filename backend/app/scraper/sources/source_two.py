"""Source adapter: Remotive public API.

Remotive offers a documented public REST API at
https://remotive.com/api/remote-jobs that supports a ``search`` parameter.
This is an officially provided API, so we use it directly (no HTML scraping).

Compliance: see SOURCES_REPORT.md.
"""
from __future__ import annotations

from typing import List

import httpx

from app.scraper.sources.base import BaseSource, RawJob


class RemotiveSource(BaseSource):
    name = "Remotive"
    type = "api"
    base_url = "https://remotive.com/api/remote-jobs"
    uses_api = True
    robots_checked = True
    tos_checked = True

    def __init__(self) -> None:
        super().__init__()
        from app.config import settings
        self.status = "active" if settings.enable_remotive else "skipped"
        if self.status == "skipped":
            self.reason_if_skipped = "Disabled via ENABLE_REMOTIVE=false."

    def fetch(self, keyword: str) -> List[RawJob]:
        # Server-side keyword search -> cached per (keyword) so repeats are free.
        try:
            data = self._cached_get_json(
                self.base_url, params={"search": keyword, "limit": 100}
            )
        except (httpx.HTTPError, ValueError) as exc:
            self.logger.warning("Remotive fetch failed: %s", exc)
            raise

        jobs = data.get("jobs", []) if isinstance(data, dict) else []
        results: List[RawJob] = []
        for item in jobs:
            results.append(
                RawJob(
                    title=item.get("title", ""),
                    company_name=item.get("company_name", ""),
                    location=item.get("candidate_required_location") or "Remote",
                    date_posted_raw=item.get("publication_date"),
                    job_type=item.get("job_type"),
                    salary=item.get("salary") or None,
                    full_description=item.get("description"),
                    original_apply_url=item.get("url", ""),
                    source_name=self.name,
                    source_job_id=str(item.get("id", "")),
                    remote_type="remote",
                    # Remotive is a remote-only board -> explicit remote flag.
                    remote_flag=True,
                    tags=item.get("tags") if isinstance(item.get("tags"), list) else None,
                    category=item.get("category"),
                    candidate_required_location=item.get("candidate_required_location"),
                )
            )
        self.logger.info("Remotive returned %d jobs for '%s'", len(results), keyword)
        return results
