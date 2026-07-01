"""Source adapter: Workday public career pages.

Workday career pages use a JSON API at
https://{company}.wd5.myworkdayjobs.com/wday/cxs/{company}/External/jobs
The exact subdomain structure varies (wd1, wd3, wd5, etc.).

We attempt the most common pattern. If the company uses a different Workday
tenant URL structure, the adapter logs the failure gracefully.

Compliance: public career pages, no login, polite rate limiting.
"""
from __future__ import annotations

from typing import List

import httpx

from app.config import settings
from app.scraper.sources.base import BaseSource, RawJob

# Common Workday subdomain variants to try.
_WD_VARIANTS = ["wd1", "wd3", "wd5"]


class WorkdaySource(BaseSource):
    name = "Workday"
    type = "api"
    base_url = "https://myworkdayjobs.com"
    uses_api = True
    robots_checked = True
    tos_checked = True
    failure_status = "blocked"

    def __init__(self) -> None:
        super().__init__()
        has_companies = bool(settings.workday_company_list)
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
        for company in settings.workday_company_list:
            jobs = self._try_fetch_company(company)
            results.extend(jobs)
        self.logger.info("Workday returned %d jobs for '%s'", len(results), keyword)
        return results

    def _try_fetch_company(self, company: str) -> List[RawJob]:
        """Try each Workday subdomain variant for the company."""
        for wd in _WD_VARIANTS:
            url = f"https://{company}.{wd}.myworkdayjobs.com/wday/cxs/{company}/External/jobs"
            try:
                data = self._cached_get_json(url, params={"limit": 20, "offset": 0})
                if isinstance(data, dict) and "jobPostings" in data:
                    return self._parse_jobs(data, company, wd)
            except (httpx.HTTPError, ValueError):
                continue
        self.logger.info("Workday: no accessible tenant found for %s", company)
        return []

    def _parse_jobs(self, data: dict, company: str, wd: str) -> List[RawJob]:
        results: List[RawJob] = []
        for item in data.get("jobPostings", []):
            title = item.get("title", "")
            location = item.get("locationsText", "") or ""
            external_path = item.get("externalPath", "")
            apply_url = f"https://{company}.{wd}.myworkdayjobs.com{external_path}" if external_path else ""

            results.append(
                RawJob(
                    title=title,
                    company_name=company.replace("-", " ").title(),
                    location=location,
                    date_posted_raw=item.get("postedOn"),
                    full_description=item.get("bulletFields", [None])[0] if item.get("bulletFields") else None,
                    original_apply_url=apply_url,
                    source_name=self.name,
                    source_job_id=str(item.get("bulletFields", [""])[0] if item.get("bulletFields") else ""),
                    remote_flag=None,
                    candidate_required_location=location,
                )
            )
        return results
