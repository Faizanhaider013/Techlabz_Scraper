"""Source adapter registry.

Add a new source by importing its adapter class and appending an instance to
``ALL_SOURCES``. The engine only runs adapters whose ``status == 'active'``.

Active by default (compliant public APIs):
    RemoteOK, Remotive, Arbeitnow, Himalayas, Greenhouse, Lever, Ashby
Dev-only (off unless ENABLE_MOCK_DATA=true):
    MockDev
Blocked / needs review (never queried, shown in the report with reasons):
    Built In, Hiring Cafe, LinkedIn, Indeed, SimplyHired, Glassdoor,
    ZipRecruiter, Jobright
"""
from __future__ import annotations

from typing import List

from app.scraper.sources.base import BaseSource
from app.scraper.sources.source_one import RemoteOKSource
from app.scraper.sources.source_two import RemotiveSource
from app.scraper.sources.source_three import ArbeitnowSource
from app.scraper.sources.himalayas import HimalayasSource
from app.scraper.sources.company_ats import (
    AshbySource,
    GreenhouseSource,
    LeverSource,
)
from app.scraper.sources.source_mock import MockDevSource
from app.scraper.sources.builtin import BuiltInSource
from app.scraper.sources.hiringcafe import HiringCafeSource
from app.scraper.sources.jobright import JobrightSource
from app.scraper.sources.keyed_sources import ALL_KEYED
from app.scraper.sources.blocked_sources import ALL_BLOCKED

ALL_SOURCES: List[BaseSource] = [
    # --- Active compliant public APIs ---
    RemoteOKSource(),
    RemotiveSource(),
    ArbeitnowSource(),
    HimalayasSource(),
    GreenhouseSource(),
    LeverSource(),
    AshbySource(),
    # --- Key-gated API sources (active only when enabled + key present) ---
    *ALL_KEYED,
    # --- Development-only sample data (active only when ENABLE_MOCK_DATA=true) ---
    MockDevSource(),
    # --- Best-effort attempts; report blocked/skipped in diagnostics ---
    BuiltInSource(),
    HiringCafeSource(),
    JobrightSource(),
    # --- Policy-blocked (never queried) ---
    *ALL_BLOCKED,
]


def active_sources() -> List[BaseSource]:
    return [s for s in ALL_SOURCES if s.status == "active"]
