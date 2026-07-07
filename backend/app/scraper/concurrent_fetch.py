"""Concurrent source fetching.

The network fetch is the scraper's real bottleneck: N sources x M keywords x a
polite delay, run sequentially, dominates wall-clock time. This module runs every
source **concurrently** with ``asyncio.gather`` while keeping each source's own
keyword loop sequential -- so a source's per-run feed cache (``_run_cache``) and
page counter stay correct, and we never hammer a single host with parallel hits.

Each source adapter's ``fetch`` is synchronous (``httpx.Client`` + BeautifulSoup),
so we offload it to a worker thread with ``asyncio.to_thread`` and gather across
sources. Wall-clock for the fetch phase drops from *sum of all sources* to
*slowest single source*. A semaphore bounds how many sources hit the network at
once so we remain a polite client.

Only the I/O phase is parallelized. Classification, dedupe and DB writes stay in
the engine's single-threaded loop, so the SQLAlchemy Session and the cross-source
dedupe set are never touched concurrently.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Dict, List

from app.config import settings
from app.scraper.sources.base import BaseSource, RawJob
from app.utils.logger import get_logger

logger = get_logger("concurrent_fetch")


@dataclass
class SourceFetchResult:
    """Prefetched raw jobs for one source, plus fetch status for diagnostics."""

    name: str
    per_keyword: Dict[str, List[RawJob]] = field(default_factory=dict)
    error: str | None = None
    status: str = "ok"        # ok | blocked | error (source.failure_status on error)
    pages_fetched: int = 0


def _fetch_source_blocking(source: BaseSource, keywords: List[str]) -> SourceFetchResult:
    """Run one source's full keyword loop sequentially (executed in a thread).

    Mirrors the engine's original per-source fetch semantics: a "blocked" failure
    aborts the source (it fails identically for every keyword); a transient error
    is recorded and the remaining keywords still run.
    """
    result = SourceFetchResult(name=source.name)
    # Fresh per-run state (previously reset by the engine before its keyword loop).
    source.pages_fetched = 0
    source._run_cache = {}

    for keyword in keywords:
        try:
            result.per_keyword[keyword] = source.fetch(keyword)
        except Exception as exc:  # noqa: BLE001 - one source must not kill the run
            msg = f"{type(exc).__name__}: {exc}"
            result.error = msg
            result.status = source.failure_status
            result.per_keyword[keyword] = []
            logger.error("  [%s] fetch failed on %r: %s", source.name, keyword, msg)
            if source.failure_status == "blocked":
                break  # blocked fails identically for every keyword -> stop early
            continue

    result.pages_fetched = getattr(source, "pages_fetched", 0)
    return result


async def _gather_sources(sources: List[BaseSource], keywords: List[str],
                          concurrency: int) -> List[SourceFetchResult]:
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def _run(source: BaseSource) -> SourceFetchResult:
        async with semaphore:
            return await asyncio.to_thread(_fetch_source_blocking, source, keywords)

    return await asyncio.gather(*(_run(s) for s in sources))


def prefetch_all_sources(sources: List[BaseSource], keywords: List[str]) -> Dict[str, SourceFetchResult]:
    """Fetch every source's raw jobs, concurrently when enabled.

    Returns ``{source_name: SourceFetchResult}``. Falls back to sequential
    fetching when async scraping is disabled or an event loop is already running
    (so ``asyncio.run`` would raise).
    """
    if not sources:
        return {}

    use_async = settings.enable_async_scraping
    if use_async:
        try:
            asyncio.get_running_loop()
            # Already inside an event loop -> asyncio.run would fail. Go sequential.
            use_async = False
            logger.warning("Event loop already running; falling back to sequential fetch.")
        except RuntimeError:
            pass

    if use_async:
        results = asyncio.run(
            _gather_sources(sources, keywords, settings.scraper_max_concurrency)
        )
    else:
        results = [_fetch_source_blocking(s, keywords) for s in sources]

    return {r.name: r for r in results}
