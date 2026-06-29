"""Source adapter: RemoteOK public API.

RemoteOK exposes a public JSON feed at https://remoteok.com/api intended for
programmatic consumption. We filter the feed client-side by keyword. This is an
allowed, API-style access pattern (no HTML scraping, polite rate limiting,
attribution preserved via the original job URL).

Compliance: see SOURCES_REPORT.md.
"""
from __future__ import annotations

from typing import List

import httpx

from app.config import settings
from app.scraper.relevance import mentions_target_term
from app.scraper.sources.base import BaseSource, RawJob


class RemoteOKSource(BaseSource):
    name = "RemoteOK"
    type = "api"
    base_url = "https://remoteok.com/api"
    uses_api = True
    robots_checked = True
    tos_checked = True

    def __init__(self) -> None:
        super().__init__()
        self.status = "active" if settings.enable_remoteok else "skipped"
        if self.status == "skipped":
            self.reason_if_skipped = "Disabled via ENABLE_REMOTEOK=false."

    def fetch(self, keyword: str) -> List[RawJob]:
        try:
            # Single keyword-independent feed -> cached for the whole run.
            data = self._cached_get_json(self.base_url)
        except (httpx.HTTPError, ValueError) as exc:
            self.logger.warning("RemoteOK fetch failed: %s", exc)
            raise

        if not isinstance(data, list):
            return []

        results: List[RawJob] = []
        for item in data:
            # The first element is feed legal/metadata, not a job.
            if not isinstance(item, dict) or "position" not in item:
                continue

            # Pre-filter on the required term so all ServiceNow roles surface.
            if not mentions_target_term(
                item.get("position"), item.get("description"), item.get("tags"),
            ):
                continue

            tags = item.get("tags") or []
            location = item.get("location") or "Remote"
            results.append(
                RawJob(
                    title=item.get("position", "") or item.get("title", ""),
                    company_name=item.get("company", ""),
                    location=location,
                    date_posted_raw=item.get("date") or item.get("epoch"),
                    job_type=", ".join(tags[:3]) if isinstance(tags, list) else None,
                    salary=self._format_salary(item),
                    full_description=item.get("description"),
                    original_apply_url=item.get("url") or item.get("apply_url", ""),
                    source_name=self.name,
                    source_job_id=str(item.get("id") or item.get("slug") or ""),
                    remote_type="remote",
                    # RemoteOK only lists remote roles -> explicit remote flag.
                    remote_flag=True,
                    tags=tags if isinstance(tags, list) else None,
                    candidate_required_location=location,
                )
            )
        self.logger.info("RemoteOK returned %d jobs for '%s'", len(results), keyword)
        return results

    @staticmethod
    def _format_salary(item: dict) -> str | None:
        lo, hi = item.get("salary_min"), item.get("salary_max")
        if lo and hi:
            return f"${int(lo):,} - ${int(hi):,}"
        return None
