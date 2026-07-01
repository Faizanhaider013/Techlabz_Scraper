"""Company career sources: multi-ATS discovery for named companies.

This adapter attempts to discover career pages for each configured company by
trying common ATS patterns (Greenhouse, Lever, Ashby). The company list is
configurable via COMPANY_CAREER_TARGETS.

For each company, we try:
1. Greenhouse: boards-api.greenhouse.io/v1/boards/{slug}/jobs
2. Lever: api.lever.co/v0/postings/{slug}
3. Ashby: api.ashbyhq.com/posting-api/job-board/{slug}

We use the company name slugified (lowercase, spaces->hyphens). Most companies
will 404 on most ATS platforms — that's expected and logged quietly.

Compliance: all public APIs, no login, no CAPTCHA bypass.
"""
from __future__ import annotations

import re
from typing import List

import httpx

from app.config import settings
from app.scraper.sources.base import BaseSource, RawJob

_NON_REMOTE_WT = ("hybrid", "on-site", "onsite")


def _slugify(name: str) -> str:
    """Convert company name to a URL slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


class CompanyCareersSource(BaseSource):
    name = "CompanyCareers"
    type = "api"
    base_url = "https://boards-api.greenhouse.io"
    uses_api = True
    robots_checked = True
    tos_checked = True

    def __init__(self) -> None:
        super().__init__()
        self.status = "active" if settings.enable_company_careers else "skipped"
        if self.status == "skipped":
            self.reason_if_skipped = "Disabled via ENABLE_COMPANY_CAREERS=false."

    def fetch(self, keyword: str) -> List[RawJob]:
        results: List[RawJob] = []
        targets = settings.company_career_target_list
        if not targets:
            return results

        for company_name in targets:
            slug = _slugify(company_name)
            if not slug:
                continue

            # Try Greenhouse first
            gh_jobs = self._try_greenhouse(slug, company_name)
            if gh_jobs:
                results.extend(gh_jobs)
                continue

            # Try Lever
            lever_jobs = self._try_lever(slug, company_name)
            if lever_jobs:
                results.extend(lever_jobs)
                continue

            # Try Ashby
            ashby_jobs = self._try_ashby(slug, company_name)
            if ashby_jobs:
                results.extend(ashby_jobs)

        self.logger.info("CompanyCareers returned %d jobs across %d companies for '%s'",
                         len(results), len(targets), keyword)
        return results

    def _try_greenhouse(self, slug: str, company_name: str) -> List[RawJob]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
        try:
            data = self._cached_get_json(url)
        except (httpx.HTTPError, ValueError):
            return []

        results: List[RawJob] = []
        for item in data.get("jobs", []) if isinstance(data, dict) else []:
            location = (item.get("location") or {}).get("name") or ""
            results.append(
                RawJob(
                    title=item.get("title", ""),
                    company_name=company_name,
                    location=location,
                    date_posted_raw=item.get("first_published") or item.get("updated_at"),
                    full_description=item.get("content") or "",
                    original_apply_url=item.get("absolute_url", ""),
                    source_name=self.name,
                    source_job_id=f"gh-{slug}-{item.get('id', '')}",
                    remote_flag=None,
                    candidate_required_location=location,
                )
            )
        return results

    def _try_lever(self, slug: str, company_name: str) -> List[RawJob]:
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        try:
            data = self._cached_get_json(url)
        except (httpx.HTTPError, ValueError):
            return []

        results: List[RawJob] = []
        for item in data if isinstance(data, list) else []:
            cats = item.get("categories") or {}
            location = cats.get("location") or ""
            workplace = (item.get("workplaceType") or "").lower()
            remote_flag = workplace == "remote" or "remote" in location.lower()
            if any(w in workplace for w in _NON_REMOTE_WT):
                remote_flag = False
            created_ms = item.get("createdAt")
            created_s = int(created_ms) / 1000 if created_ms else None

            results.append(
                RawJob(
                    title=item.get("text", ""),
                    company_name=company_name,
                    location=location,
                    date_posted_raw=created_s,
                    full_description=item.get("descriptionPlain") or item.get("description") or "",
                    original_apply_url=item.get("hostedUrl") or item.get("applyUrl", ""),
                    source_name=self.name,
                    source_job_id=f"lever-{slug}-{item.get('id', '')}",
                    remote_type="remote" if remote_flag else None,
                    remote_flag=remote_flag,
                    candidate_required_location=location,
                )
            )
        return results

    def _try_ashby(self, slug: str, company_name: str) -> List[RawJob]:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"
        try:
            data = self._cached_get_json(url)
        except (httpx.HTTPError, ValueError):
            return []

        results: List[RawJob] = []
        for item in data.get("jobs", []) if isinstance(data, dict) else []:
            location = item.get("location") or ""
            workplace = (item.get("workplaceType") or "").lower()
            remote_flag = bool(item.get("isRemote")) and not any(
                w in workplace for w in _NON_REMOTE_WT
            )

            results.append(
                RawJob(
                    title=item.get("title", ""),
                    company_name=company_name,
                    location=location,
                    date_posted_raw=item.get("publishedAt"),
                    job_type=item.get("employmentType"),
                    full_description=item.get("descriptionPlain") or item.get("descriptionHtml") or "",
                    original_apply_url=item.get("jobUrl") or item.get("applyUrl", ""),
                    source_name=self.name,
                    source_job_id=f"ashby-{slug}-{item.get('id', '')}",
                    remote_type="remote" if remote_flag else None,
                    remote_flag=remote_flag,
                    candidate_required_location=location,
                )
            )
        return results
