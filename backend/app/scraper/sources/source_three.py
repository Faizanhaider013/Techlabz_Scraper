"""Source adapter: Arbeitnow public Job Board API.

Arbeitnow publishes a free, public job-board API at
https://www.arbeitnow.com/api/job-board-api (no key required). We page through
results and filter by keyword client-side.

Compliance: see SOURCES_REPORT.md.
"""
from __future__ import annotations

from typing import List

import httpx

from app.config import settings
from app.scraper.relevance import mentions_target_term
from app.scraper.sources.base import BaseSource, RawJob


class ArbeitnowSource(BaseSource):
    name = "Arbeitnow"
    type = "api"
    base_url = "https://www.arbeitnow.com/api/job-board-api"
    uses_api = True
    robots_checked = True
    tos_checked = True

    def __init__(self) -> None:
        super().__init__()
        self.status = "active" if settings.enable_arbeitnow else "skipped"
        if self.status == "skipped":
            self.reason_if_skipped = "Disabled via ENABLE_ARBEITNOW=false."

    def fetch(self, keyword: str) -> List[RawJob]:
        results: List[RawJob] = []
        max_pages = max(1, min(settings.max_pages_per_source, 10))
        for page in range(1, max_pages + 1):
            try:
                # Keyword-independent feed pages -> cached for the whole run.
                data = self._cached_get_json(self.base_url, params={"page": page})
            except (httpx.HTTPError, ValueError) as exc:
                self.logger.warning("Arbeitnow page %d failed: %s", page, exc)
                if page == 1:
                    raise
                break

            items = data.get("data", []) if isinstance(data, dict) else []
            if not items:
                break

            for item in items:
                if not mentions_target_term(
                    item.get("title"), item.get("description"), item.get("tags"),
                ):
                    continue

                tags = item.get("tags") or []
                job_types = item.get("job_types") or []
                is_remote = bool(item.get("remote"))
                location = item.get("location", "")
                results.append(
                    RawJob(
                        title=item.get("title", ""),
                        company_name=item.get("company_name", ""),
                        location=location,
                        date_posted_raw=item.get("created_at"),
                        job_type=", ".join(job_types) if job_types else None,
                        full_description=item.get("description"),
                        original_apply_url=item.get("url", ""),
                        source_name=self.name,
                        source_job_id=str(item.get("slug", "")),
                        remote_type="remote" if is_remote else None,
                        # Arbeitnow exposes a real remote flag (may be False).
                        remote_flag=is_remote,
                        tags=tags if isinstance(tags, list) else None,
                        candidate_required_location=location,
                    )
                )
        self.logger.info("Arbeitnow returned %d jobs for '%s'", len(results), keyword)
        return results
