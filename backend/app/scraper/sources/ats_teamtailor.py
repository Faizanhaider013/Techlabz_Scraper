"""Source adapter: Teamtailor public career pages.

Teamtailor career pages expose a JSON API at
https://{company}.teamtailor.com/api/v1/jobs (or via the public careers page).
Requires the company's Teamtailor subdomain.

Compliance: public career pages, no login, polite rate limiting.
"""
from __future__ import annotations

from typing import List

import httpx

from app.config import settings
from app.scraper.sources.base import BaseSource, RawJob


class TeamtailorSource(BaseSource):
    name = "Teamtailor"
    type = "api"
    base_url = "https://teamtailor.com"
    uses_api = True
    robots_checked = True
    tos_checked = True

    def __init__(self) -> None:
        super().__init__()
        has_companies = bool(settings.teamtailor_company_list)
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
        for company in settings.teamtailor_company_list:
            # Teamtailor uses a feed endpoint
            url = f"https://{company}.teamtailor.com/jobs.json"
            try:
                data = self._cached_get_json(url)
            except (httpx.HTTPError, ValueError) as exc:
                self.logger.warning("Teamtailor company '%s' failed: %s", company, exc)
                continue

            jobs = data.get("data", []) if isinstance(data, dict) else data if isinstance(data, list) else []
            for item in jobs:
                attrs = item.get("attributes", {}) if isinstance(item, dict) else {}
                if not attrs and isinstance(item, dict):
                    attrs = item

                title = attrs.get("title", "")
                location = attrs.get("location", "") or ""
                remote_flag = bool(attrs.get("remote"))
                body = attrs.get("body", "") or attrs.get("description", "")

                links = item.get("links", {}) if isinstance(item, dict) else {}
                apply_url = links.get("careersite-job-url", "") or links.get("self", "") or ""

                results.append(
                    RawJob(
                        title=title,
                        company_name=company.replace("-", " ").title(),
                        location=location or ("Remote" if remote_flag else ""),
                        date_posted_raw=attrs.get("created-at") or attrs.get("published_at"),
                        full_description=body,
                        original_apply_url=apply_url,
                        source_name=self.name,
                        source_job_id=str(item.get("id", "")) if isinstance(item, dict) else "",
                        remote_type="remote" if remote_flag else None,
                        remote_flag=remote_flag,
                        candidate_required_location=location,
                    )
                )
        self.logger.info("Teamtailor returned %d jobs for '%s'", len(results), keyword)
        return results
