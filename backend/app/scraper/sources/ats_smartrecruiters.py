"""Source adapter: SmartRecruiters public API.

SmartRecruiters exposes public job board APIs per company at
https://api.smartrecruiters.com/v1/companies/{companyId}/postings
No API key required for public postings.

Compliance: public API, no login.
"""
from __future__ import annotations

from typing import List

import httpx

from app.config import settings
from app.scraper.sources.base import BaseSource, RawJob

_NON_REMOTE_WT = ("hybrid", "on-site", "onsite")


class SmartRecruitersSource(BaseSource):
    name = "SmartRecruiters"
    type = "api"
    base_url = "https://api.smartrecruiters.com/v1/companies"
    uses_api = True
    robots_checked = True
    tos_checked = True

    def __init__(self) -> None:
        super().__init__()
        has_companies = bool(settings.smartrecruiters_company_list)
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
        for company in settings.smartrecruiters_company_list:
            url = f"{self.base_url}/{company}/postings"
            try:
                data = self._cached_get_json(url, params={"limit": 100})
            except (httpx.HTTPError, ValueError) as exc:
                self.logger.warning("SmartRecruiters company '%s' failed: %s", company, exc)
                continue
            content = data.get("content", []) if isinstance(data, dict) else []
            for item in content:
                loc = item.get("location") or {}
                location = loc.get("city", "") or loc.get("region", "") or ""
                country = loc.get("country", "")
                if country:
                    location = f"{location}, {country}".strip(", ")
                remote_flag = bool(loc.get("remote"))

                results.append(
                    RawJob(
                        title=item.get("name", ""),
                        company_name=item.get("company", {}).get("name", "") or company,
                        location=location or "Remote" if remote_flag else location,
                        date_posted_raw=item.get("releasedDate"),
                        job_type=item.get("typeOfEmployment", {}).get("label") if isinstance(item.get("typeOfEmployment"), dict) else None,
                        full_description=item.get("jobAd", {}).get("sections", {}).get("jobDescription", {}).get("text", "") if isinstance(item.get("jobAd"), dict) else "",
                        original_apply_url=item.get("applyUrl", "") or f"https://jobs.smartrecruiters.com/{company}/{item.get('id', '')}",
                        source_name=self.name,
                        source_job_id=str(item.get("id", "")),
                        remote_type="remote" if remote_flag else None,
                        remote_flag=remote_flag,
                        candidate_required_location=f"{location} {country}".strip(),
                    )
                )
        self.logger.info("SmartRecruiters returned %d jobs for '%s'", len(results), keyword)
        return results
