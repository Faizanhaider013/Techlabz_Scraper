"""Source adapter: Hubstaff Talent (talent.hubstaff.com).

Hubstaff Talent provides a public API for browsing remote job/talent listings.
We fetch technology job listings and filter client-side.

Compliance: public API, no login, polite rate limiting.
"""
from __future__ import annotations

from typing import List

import httpx

from app.config import settings
from app.scraper.sources.base import BaseSource, RawJob

_API_URL = "https://talent.hubstaff.com/api/v1/jobs"


class HubstaffTalentSource(BaseSource):
    name = "HubstaffTalent"
    type = "api"
    base_url = "https://talent.hubstaff.com"
    uses_api = True
    robots_checked = True
    tos_checked = True
    failure_status = "blocked"

    def __init__(self) -> None:
        super().__init__()
        self.status = "active" if settings.enable_hubstaff_talent else "skipped"
        if self.status == "skipped":
            self.reason_if_skipped = "Disabled via ENABLE_HUBSTAFF_TALENT=false."

    def fetch(self, keyword: str) -> List[RawJob]:
        results: List[RawJob] = []
        max_pages = max(1, min(settings.max_pages_per_source, 5))

        for page in range(1, max_pages + 1):
            try:
                data = self._cached_get_json(
                    _API_URL,
                    params={"page": page, "search": keyword},
                )
            except (httpx.HTTPError, ValueError) as exc:
                self.logger.warning("HubstaffTalent page %d failed: %s", page, exc)
                if page == 1:
                    raise
                break

            items = data if isinstance(data, list) else data.get("jobs", []) if isinstance(data, dict) else []
            if not items:
                break

            for item in items:
                if not isinstance(item, dict):
                    continue

                title = item.get("title", "")
                company = item.get("company_name", "") or item.get("company", "")
                location = item.get("location", "Remote")
                skills = item.get("skills") or []
                skill_list = [s.get("name", "") for s in skills] if isinstance(skills, list) else []

                results.append(
                    RawJob(
                        title=title,
                        company_name=company if isinstance(company, str) else "",
                        location=location or "Remote",
                        date_posted_raw=item.get("created_at") or item.get("published_at"),
                        job_type=item.get("type") or item.get("job_type"),
                        salary=self._format_budget(item),
                        full_description=item.get("description"),
                        original_apply_url=item.get("url", "") or item.get("apply_url", ""),
                        source_name=self.name,
                        source_job_id=str(item.get("id", "")),
                        remote_type="remote",
                        remote_flag=True,
                        tags=skill_list if skill_list else None,
                        candidate_required_location=location or "Remote",
                    )
                )
        self.logger.info("HubstaffTalent returned %d jobs for '%s'", len(results), keyword)
        return results

    @staticmethod
    def _format_budget(item: dict) -> str | None:
        budget = item.get("budget") or item.get("hourly_rate")
        if budget:
            return str(budget)
        return None
