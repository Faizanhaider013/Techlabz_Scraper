"""Source adapter: Himalayas public Remote Jobs API.

Himalayas publishes a free, public JSON feed of remote jobs at
``https://himalayas.app/jobs/api``. robots.txt allows everything except
``/apply`` (which we never touch), and the feed is intended for programmatic
use. All Himalayas jobs are remote; each job carries ``locationRestrictions``
(e.g. ["United States"]) which we use for the US filter.

The feed is keyword-independent, so we fetch it once per run, cache it briefly,
and filter locally for each keyword. The strict ServiceNow + Remote + US filter
is applied centrally by the engine before anything is saved.

Compliance: see SOURCES_REPORT.md.
"""
from __future__ import annotations

from typing import List

import httpx

from app.config import settings
from app.scraper.relevance import mentions_target_term
from app.scraper.sources.base import BaseSource, RawJob

# Politeness: page size; page count comes from MAX_PAGES_PER_SOURCE.
_PAGE_SIZE = 100


class HimalayasSource(BaseSource):
    name = "Himalayas"
    type = "api"
    base_url = "https://himalayas.app/jobs/api"
    uses_api = True
    robots_checked = True
    tos_checked = True

    def __init__(self) -> None:
        super().__init__()
        self.status = "active" if settings.enable_himalayas else "skipped"
        if self.status == "skipped":
            self.reason_if_skipped = "Disabled via ENABLE_HIMALAYAS=false."

    def _load_feed(self) -> list[dict]:
        jobs: list[dict] = []
        max_pages = max(1, min(settings.max_pages_per_source, 10))
        for page in range(max_pages):
            offset = page * _PAGE_SIZE
            try:
                # Cached per (limit, offset) so the keyword loop fetches once.
                data = self._cached_get_json(
                    self.base_url, params={"limit": _PAGE_SIZE, "offset": offset}
                )
            except (httpx.HTTPError, ValueError) as exc:
                self.logger.warning("Himalayas page offset=%d failed: %s", offset, exc)
                if page == 0:
                    raise
                break
            batch = data.get("jobs", []) if isinstance(data, dict) else []
            if not batch:
                break
            jobs.extend(batch)
        return jobs

    def fetch(self, keyword: str) -> List[RawJob]:
        feed = self._load_feed()
        results: List[RawJob] = []
        for item in feed:
            if not isinstance(item, dict):
                continue
            # Pre-filter on the required term (e.g. "servicenow"), not the exact
            # keyword phrase, so all ServiceNow roles surface to the funnel.
            if not mentions_target_term(
                item.get("title"), item.get("excerpt"), item.get("description"),
                item.get("categories"),
            ):
                continue

            loc_list = item.get("locationRestrictions") or []
            location = ", ".join(loc_list) if loc_list else "Remote"
            results.append(
                RawJob(
                    title=item.get("title", ""),
                    company_name=item.get("companyName", ""),
                    location=location,
                    date_posted_raw=item.get("pubDate"),
                    job_type=item.get("employmentType"),
                    salary=self._format_salary(item),
                    full_description=item.get("description") or item.get("excerpt"),
                    original_apply_url=item.get("applicationLink")
                    or item.get("guid", ""),
                    source_name=self.name,
                    source_job_id=str(item.get("guid", "")),
                    remote_type="remote",
                    remote_flag=True,  # Himalayas is a remote-only board.
                    tags=item.get("categories") if isinstance(item.get("categories"), list) else None,
                    candidate_required_location=location,
                )
            )
        self.logger.info("Himalayas returned %d jobs for '%s'", len(results), keyword)
        return results

    @staticmethod
    def _format_salary(item: dict) -> str | None:
        lo, hi = item.get("minSalary"), item.get("maxSalary")
        cur = item.get("currency") or "$"
        if lo and hi:
            return f"{cur}{int(lo):,} - {cur}{int(hi):,}"
        return None
