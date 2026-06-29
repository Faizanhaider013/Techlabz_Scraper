"""Key-gated API sources: Adzuna, USAJOBS, The Muse, Jooble.

All are OFF by default. Each activates only when its ENABLE_* flag is true AND
the required key/credential is present; otherwise it is reported as
``needs_api_key`` (enabled but unconfigured) or ``skipped`` (disabled). They
paginate up to MAX_PAGES_PER_SOURCE and map a real posted date so the TODAY gate
can apply. We cannot exercise these without credentials, but the plumbing is
ready: add keys to .env and they participate in the run + diagnostics.
"""
from __future__ import annotations

import time
from typing import List

import httpx

from app.config import settings
from app.scraper.sources.base import BaseSource, RawJob


class _KeyedSource(BaseSource):
    type = "api"
    uses_api = True
    robots_checked = True
    tos_checked = True
    enable_flag = ""        # settings attribute name
    required_keys: tuple = ()  # settings attribute names that must be non-empty

    def __init__(self) -> None:
        super().__init__()
        enabled = bool(getattr(settings, self.enable_flag, False))
        has_keys = all(getattr(settings, k, "") for k in self.required_keys)
        if not enabled:
            self.status = "skipped"
            self.reason_if_skipped = f"Disabled via {self.enable_flag.upper()}=false."
        elif not has_keys:
            self.status = "needs_api_key"
            self.reason_if_skipped = (
                f"Enabled but missing credentials ({', '.join(self.required_keys)})."
            )
        else:
            self.status = "active"

    @property
    def _max_pages(self) -> int:
        return max(1, min(settings.max_pages_per_source, 10))


class AdzunaSource(_KeyedSource):
    name = "Adzuna"
    base_url = "https://api.adzuna.com/v1/api/jobs/us/search"
    enable_flag = "enable_adzuna"
    required_keys = ("adzuna_app_id", "adzuna_app_key")

    def fetch(self, keyword: str) -> List[RawJob]:
        results: List[RawJob] = []
        for page in range(1, self._max_pages + 1):
            params = {
                "app_id": settings.adzuna_app_id,
                "app_key": settings.adzuna_app_key,
                "what": keyword,
                "results_per_page": 50,
                "content-type": "application/json",
            }
            data = self._get_json(f"{self.base_url}/{page}", params=params)
            items = data.get("results", []) if isinstance(data, dict) else []
            if not items:
                break
            for it in items:
                loc = (it.get("location") or {}).get("display_name", "")
                results.append(
                    RawJob(
                        title=it.get("title", ""),
                        company_name=(it.get("company") or {}).get("display_name", ""),
                        location=loc,
                        date_posted_raw=it.get("created"),
                        salary=self._salary(it),
                        full_description=it.get("description"),
                        original_apply_url=it.get("redirect_url", ""),
                        source_name=self.name,
                        source_job_id=str(it.get("id", "")),
                        candidate_required_location=loc,
                    )
                )
        return results

    @staticmethod
    def _salary(it: dict):
        lo, hi = it.get("salary_min"), it.get("salary_max")
        return f"${int(lo):,} - ${int(hi):,}" if lo and hi else None


class USAJobsSource(_KeyedSource):
    name = "USAJOBS"
    base_url = "https://data.usajobs.gov/api/search"
    enable_flag = "enable_usajobs"
    required_keys = ("usajobs_email", "usajobs_api_key")

    def fetch(self, keyword: str) -> List[RawJob]:
        headers = {
            "Host": "data.usajobs.gov",
            "User-Agent": settings.usajobs_email,
            "Authorization-Key": settings.usajobs_api_key,
        }
        results: List[RawJob] = []
        for page in range(1, self._max_pages + 1):
            time.sleep(settings.request_delay_seconds)
            self.pages_fetched += 1
            with httpx.Client(timeout=settings.request_timeout_seconds) as c:
                resp = c.get(
                    self.base_url,
                    params={"Keyword": keyword, "ResultsPerPage": 50, "Page": page},
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
            items = (data.get("SearchResult") or {}).get("SearchResultItems", [])
            if not items:
                break
            for it in items:
                d = it.get("MatchedObjectDescriptor", {})
                locs = ", ".join(
                    l.get("LocationName", "") for l in d.get("PositionLocation", [])
                ) or "United States"
                results.append(
                    RawJob(
                        title=d.get("PositionTitle", ""),
                        company_name=d.get("OrganizationName", ""),
                        location=locs,
                        date_posted_raw=d.get("PublicationStartDate"),
                        full_description=(d.get("UserArea", {}).get("Details", {}) or {}).get("JobSummary"),
                        original_apply_url=d.get("PositionURI", ""),
                        source_name=self.name,
                        source_job_id=str(d.get("PositionID", "")),
                        candidate_required_location=locs + " United States",
                    )
                )
        return results


class TheMuseSource(_KeyedSource):
    name = "The Muse"
    base_url = "https://www.themuse.com/api/public/jobs"
    enable_flag = "enable_the_muse"
    required_keys = ("the_muse_api_key",)

    def fetch(self, keyword: str) -> List[RawJob]:
        results: List[RawJob] = []
        for page in range(0, self._max_pages):
            params = {
                "api_key": settings.the_muse_api_key,
                "location": "Flexible / Remote",
                "page": page,
            }
            data = self._get_json(self.base_url, params=params)
            items = data.get("results", []) if isinstance(data, dict) else []
            if not items:
                break
            kw = keyword.lower()
            for it in items:
                blob = (it.get("name", "") + " " + (it.get("contents") or "")).lower()
                if "servicenow" not in blob and kw not in blob:
                    continue
                locs = ", ".join(l.get("name", "") for l in it.get("locations", []))
                results.append(
                    RawJob(
                        title=it.get("name", ""),
                        company_name=(it.get("company") or {}).get("name", ""),
                        location=locs or "Remote",
                        date_posted_raw=it.get("publication_date"),
                        full_description=it.get("contents"),
                        original_apply_url=(it.get("refs") or {}).get("landing_page", ""),
                        source_name=self.name,
                        source_job_id=str(it.get("id", "")),
                        candidate_required_location=locs,
                    )
                )
        return results


class JoobleSource(_KeyedSource):
    name = "Jooble"
    base_url = "https://jooble.org/api"
    enable_flag = "enable_jooble"
    required_keys = ("jooble_api_key",)

    def fetch(self, keyword: str) -> List[RawJob]:
        results: List[RawJob] = []
        for page in range(1, self._max_pages + 1):
            time.sleep(settings.request_delay_seconds)
            self.pages_fetched += 1
            with httpx.Client(timeout=settings.request_timeout_seconds) as c:
                resp = c.post(
                    f"{self.base_url}/{settings.jooble_api_key}",
                    json={"keywords": keyword, "location": "United States", "page": page},
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()
            items = data.get("jobs", []) if isinstance(data, dict) else []
            if not items:
                break
            for it in items:
                results.append(
                    RawJob(
                        title=it.get("title", ""),
                        company_name=it.get("company", ""),
                        location=it.get("location", ""),
                        date_posted_raw=it.get("updated"),
                        salary=it.get("salary") or None,
                        full_description=it.get("snippet"),
                        original_apply_url=it.get("link", ""),
                        source_name=self.name,
                        source_job_id=str(it.get("id", "")),
                        candidate_required_location=it.get("location", ""),
                    )
                )
        return results


ALL_KEYED = [AdzunaSource(), USAJobsSource(), TheMuseSource(), JoobleSource()]
