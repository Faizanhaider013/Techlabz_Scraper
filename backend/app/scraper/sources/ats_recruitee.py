"""Source adapter: Recruitee public career pages.

Recruitee career pages expose a JSON API at
https://{company}.recruitee.com/api/offers/
No API key required.

Compliance: public API, no login, polite rate limiting.
"""
from __future__ import annotations

from typing import List

import httpx

from app.config import settings
from app.scraper.sources.base import BaseSource, RawJob


class RecruiteeSource(BaseSource):
    name = "Recruitee"
    type = "api"
    base_url = "https://recruitee.com"
    uses_api = True
    robots_checked = True
    tos_checked = True

    def __init__(self) -> None:
        super().__init__()
        has_companies = bool(settings.recruitee_company_list)
        if not settings.enable_company_ats:
            self.status = "skipped"
            self.reason_if_skipped = "Disabled via ENABLE_COMPANY_ATS=false."
        elif not has_companies:
            self.status = "active"
            self.reason_if_skipped = None
        else:
            self.status = "active"

    def fetch(self, keyword: str) -> List[RawJob]:
        results: List[RawJob] = []
        for company in settings.recruitee_company_list:
            url = f"https://{company}.recruitee.com/api/offers/"
            try:
                data = self._cached_get_json(url)
            except (httpx.HTTPError, ValueError) as exc:
                self.logger.warning("Recruitee company '%s' failed: %s", company, exc)
                continue
            offers = data.get("offers", []) if isinstance(data, dict) else []
            for item in offers:
                location = item.get("location", "") or ""
                remote_flag = bool(item.get("remote"))

                results.append(
                    RawJob(
                        title=item.get("title", ""),
                        company_name=item.get("company_name", "") or company.replace("-", " ").title(),
                        location=location or ("Remote" if remote_flag else ""),
                        date_posted_raw=item.get("published_at") or item.get("created_at"),
                        job_type=item.get("employment_type_code"),
                        full_description=item.get("description"),
                        original_apply_url=item.get("careers_url", "") or item.get("url", ""),
                        source_name=self.name,
                        source_job_id=str(item.get("id", "")),
                        remote_type="remote" if remote_flag else None,
                        remote_flag=remote_flag,
                        candidate_required_location=location,
                    )
                )
        self.logger.info("Recruitee returned %d jobs for '%s'", len(results), keyword)
        return results
