"""Source adapters: company ATS public job boards (Greenhouse, Lever, Ashby).

These Applicant Tracking Systems expose **public, unauthenticated** JSON board
APIs per employer -- no API key required. They are the cleanest, most compliant
way to collect genuine ServiceNow roles directly from employers (e.g. ServiceNow
partner/consulting firms).

The company/board lists are configured via the environment:
    GREENHOUSE_BOARDS=gitlab,thirdera
    LEVER_COMPANIES=leverdemo
    ASHBY_BOARDS=ramp

Each adapter fetches every configured board, maps the jobs, and filters locally
by keyword. The strict ServiceNow + Remote + US filter is applied centrally by
the engine before anything is saved, so empty/irrelevant boards simply yield 0.
"""
from __future__ import annotations

from typing import List

import httpx

from app.config import settings
from app.scraper.sources.base import BaseSource, RawJob

_NON_REMOTE_WT = ("hybrid", "on-site", "onsite")


class _ATSBase(BaseSource):
    """Shared plumbing for ATS adapters with configurable board lists."""

    type = "api"
    uses_api = True
    robots_checked = True
    tos_checked = True

    def _boards(self) -> List[str]:  # pragma: no cover - overridden
        return []

    def _activate(self) -> None:
        if not settings.enable_company_ats:
            self.status = "skipped"
            self.reason_if_skipped = "Disabled via ENABLE_COMPANY_ATS=false."
        elif not self._boards():
            # Active but no boards configured -> it runs as a harmless no-op.
            self.status = "active"
            self.reason_if_skipped = None
        else:
            self.status = "active"
            self.reason_if_skipped = None


class GreenhouseSource(_ATSBase):
    name = "Greenhouse"
    base_url = "https://boards-api.greenhouse.io/v1/boards"

    def __init__(self) -> None:
        super().__init__()
        self._activate()

    def _boards(self) -> List[str]:
        return settings.greenhouse_board_list

    def fetch(self, keyword: str) -> List[RawJob]:
        results: List[RawJob] = []
        for board in self._boards():
            url = f"{self.base_url}/{board}/jobs?content=true"
            try:
                data = self._cached_get_json(url)
            except (httpx.HTTPError, ValueError) as exc:
                self.logger.warning("Greenhouse board '%s' failed: %s", board, exc)
                continue
            for item in data.get("jobs", []) if isinstance(data, dict) else []:
                location = (item.get("location") or {}).get("name") or ""
                content = item.get("content") or ""
                # Return every board job; the engine's ServiceNow+Remote+US funnel
                # decides what is saved (and records the full diagnostics).
                results.append(
                    RawJob(
                        title=item.get("title", ""),
                        company_name=item.get("company_name") or board.replace("-", " ").title(),
                        location=location,
                        date_posted_raw=item.get("first_published") or item.get("updated_at"),
                        full_description=content,
                        original_apply_url=item.get("absolute_url", ""),
                        source_name=self.name,
                        source_job_id=str(item.get("id", "")),
                        candidate_required_location=location,
                        # Greenhouse has no explicit remote flag; let the text decide.
                        remote_flag=None,
                    )
                )
        self.logger.info("Greenhouse returned %d jobs for '%s'", len(results), keyword)
        return results


class LeverSource(_ATSBase):
    name = "Lever"
    base_url = "https://api.lever.co/v0/postings"

    def __init__(self) -> None:
        super().__init__()
        self._activate()

    def _boards(self) -> List[str]:
        return settings.lever_company_list

    def fetch(self, keyword: str) -> List[RawJob]:
        results: List[RawJob] = []
        for company in self._boards():
            url = f"{self.base_url}/{company}?mode=json"
            try:
                data = self._cached_get_json(url)
            except (httpx.HTTPError, ValueError) as exc:
                self.logger.warning("Lever company '%s' failed: %s", company, exc)
                continue
            for item in data if isinstance(data, list) else []:
                cats = item.get("categories") or {}
                location = cats.get("location") or ""
                country = item.get("country") or ""
                workplace = (item.get("workplaceType") or "").lower()
                desc = item.get("descriptionPlain") or item.get("description") or ""

                remote_flag = workplace == "remote" or "remote" in location.lower()
                if any(w in workplace for w in _NON_REMOTE_WT):
                    remote_flag = False

                created_ms = item.get("createdAt")
                created_s = int(created_ms) / 1000 if created_ms else None

                results.append(
                    RawJob(
                        title=item.get("text", ""),
                        company_name=company.replace("-", " ").title(),
                        location=location or country,
                        date_posted_raw=created_s,
                        job_type=cats.get("commitment"),
                        full_description=desc,
                        original_apply_url=item.get("hostedUrl") or item.get("applyUrl", ""),
                        source_name=self.name,
                        source_job_id=str(item.get("id", "")),
                        remote_type="remote" if remote_flag else (workplace or None),
                        remote_flag=remote_flag,
                        candidate_required_location=f"{location} {country}".strip(),
                    )
                )
        self.logger.info("Lever returned %d jobs for '%s'", len(results), keyword)
        return results


class AshbySource(_ATSBase):
    name = "Ashby"
    base_url = "https://api.ashbyhq.com/posting-api/job-board"

    def __init__(self) -> None:
        super().__init__()
        self._activate()

    def _boards(self) -> List[str]:
        return settings.ashby_board_list

    def fetch(self, keyword: str) -> List[RawJob]:
        results: List[RawJob] = []
        for org in self._boards():
            url = f"{self.base_url}/{org}?includeCompensation=true"
            try:
                data = self._cached_get_json(url)
            except (httpx.HTTPError, ValueError) as exc:
                self.logger.warning("Ashby board '%s' failed: %s", org, exc)
                continue
            for item in data.get("jobs", []) if isinstance(data, dict) else []:
                location = item.get("location") or ""
                desc = item.get("descriptionPlain") or item.get("descriptionHtml") or ""

                workplace = (item.get("workplaceType") or "").lower()
                remote_flag = bool(item.get("isRemote")) and not any(
                    w in workplace for w in _NON_REMOTE_WT
                )
                # Collect every country mentioned (primary + secondary) for US filtering.
                countries = self._collect_locations(item)

                results.append(
                    RawJob(
                        title=item.get("title", ""),
                        company_name=org.replace("-", " ").title(),
                        location=location or ", ".join(countries),
                        date_posted_raw=item.get("publishedAt"),
                        job_type=item.get("employmentType"),
                        salary=self._format_comp(item),
                        full_description=desc,
                        original_apply_url=item.get("jobUrl") or item.get("applyUrl", ""),
                        source_name=self.name,
                        source_job_id=str(item.get("id", "")),
                        remote_type="remote" if remote_flag else (workplace or None),
                        remote_flag=remote_flag,
                        candidate_required_location=f"{location} {' '.join(countries)}".strip(),
                    )
                )
        self.logger.info("Ashby returned %d jobs for '%s'", len(results), keyword)
        return results

    @staticmethod
    def _collect_locations(item: dict) -> list[str]:
        out: list[str] = []
        for sec in item.get("secondaryLocations") or []:
            loc = sec.get("location")
            if loc:
                out.append(loc)
            country = (
                (sec.get("address") or {}).get("postalAddress", {}).get("addressCountry")
            )
            if country:
                out.append(country)
        country = (item.get("address") or {}).get("postalAddress", {}).get("addressCountry")
        if country:
            out.append(country)
        return out

    @staticmethod
    def _format_comp(item: dict) -> str | None:
        comp = item.get("compensation") or {}
        summary = comp.get("compensationTierSummary")
        return summary if isinstance(summary, str) and summary else None
