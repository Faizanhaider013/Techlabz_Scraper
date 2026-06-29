"""Source adapter interface.

Every job source implements ``BaseSource``. Adapters return a list of ``RawJob``
objects for a given keyword; normalization, deduplication and persistence are
handled centrally by the engine, so adapters stay small and focused.

Compliance metadata (status / robots / TOS / reason) lives on the adapter so the
/api/sources endpoint and SOURCES_REPORT.md can be generated from a single source
of truth.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

import httpx

from app.config import settings
from app.utils.logger import get_logger


@dataclass
class RawJob:
    """Raw job payload returned by a source adapter (pre-normalization)."""

    title: str
    company_name: str
    original_apply_url: str
    source_name: str
    location: str = ""
    date_posted_raw: Optional[object] = None  # str | int | float
    job_type: Optional[str] = None
    salary: Optional[str] = None
    short_description: Optional[str] = None
    full_description: Optional[str] = None
    source_job_id: Optional[str] = None
    remote_type: Optional[str] = None

    # --- Extra source metadata used by the strict relevance filter --------
    tags: Optional[list] = None
    category: Optional[str] = None
    candidate_required_location: Optional[str] = None
    # Explicit remote flag from the source API (None if not provided).
    remote_flag: Optional[bool] = None


class BaseSource(ABC):
    # --- Identity ---------------------------------------------------------
    name: str = "base"
    type: str = "api"  # api | career_page | mock
    base_url: Optional[str] = None

    # --- Compliance metadata (drives sources report) ----------------------
    status: str = "active"  # active | skipped | blocked | needs_api_key
    reason_if_skipped: Optional[str] = None
    uses_api: bool = False
    robots_checked: bool = False
    tos_checked: bool = False
    # Diagnostics status to use if fetch() raises (e.g. "blocked" for sites that
    # 403 automated clients, "error" for transient API failures).
    failure_status: str = "error"
    # Pages actually fetched this run (the engine resets this to 0 per run).
    pages_fetched: int = 0

    def __init__(self) -> None:
        self.logger = get_logger(f"source.{self.name}")
        self.pages_fetched = 0
        self._run_cache: dict = {}

    @abstractmethod
    def fetch(self, keyword: str) -> List[RawJob]:
        """Return raw jobs matching ``keyword`` for this source."""
        raise NotImplementedError

    # --- Shared HTTP helper with polite rate limiting ---------------------
    def _get_json(self, url: str, *, params: dict | None = None, headers: dict | None = None):
        default_headers = {
            "User-Agent": (
                "JobAggregatorBot/1.0 (+https://example.com/bot; respects robots.txt)"
            ),
            "Accept": "application/json",
        }
        if headers:
            default_headers.update(headers)
        # Polite delay to avoid overloading the source.
        time.sleep(settings.request_delay_seconds)
        self.pages_fetched += 1
        with httpx.Client(timeout=settings.request_timeout_seconds) as client:
            resp = client.get(url, params=params, headers=default_headers)
            resp.raise_for_status()
            return resp.json()

    def _cached_get_json(self, url: str, *, params: dict | None = None,
                         headers: dict | None = None, ttl: float = 900):
        """Like _get_json but cached for one run, so the keyword loop fetches a
        feed/board only once instead of re-fetching for every keyword."""
        key = f"{url}|{sorted((params or {}).items())}"
        cached = self._run_cache.get(key)
        if cached is not None:
            return cached
        data = self._get_json(url, params=params, headers=headers)
        self._run_cache[key] = data
        return data
