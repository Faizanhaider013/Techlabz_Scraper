"""Lightweight in-process TTL cache for read endpoints.

The read API (``/api/jobs``, ``/api/jobs/today``, ``/api/stats``) serves the same
handful of query shapes repeatedly between 30-minute scrapes. Caching those
responses turns most requests into a dict lookup (sub-millisecond) instead of a
Postgres round-trip (COUNT + ORDER BY + LIMIT, or a GROUP BY for stats).

Design notes
------------
* In-process + thread-safe (``threading.Lock``). Good enough for a single Render
  web instance. To scale horizontally, swap ``_store`` for Redis behind the same
  ``get`` / ``set`` / ``clear`` interface -- callers never change.
* Cache is keyed by a ``namespace`` + the exact query params, so different filter
  combinations never collide.
* A monotonically increasing ``_version`` acts as a global invalidation stamp:
  ``clear()`` bumps it and every previously stored entry is instantly ignored.
  The scraper calls ``clear()`` after each run so new jobs appear immediately.
* Entries also expire after ``ttl`` seconds as a safety net (e.g. the "posted
  today" window rolling over at midnight even without a scrape).
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Optional

from app.config import settings


class TTLCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, int, Any]] = {}
        self._lock = threading.Lock()
        self._version = 0
        self.hits = 0
        self.misses = 0

    def _make_key(self, namespace: str, params: dict) -> str:
        # Sort params for a stable key regardless of dict ordering.
        parts = "&".join(f"{k}={params[k]}" for k in sorted(params) if params[k] is not None)
        return f"{namespace}?{parts}"

    def get(self, namespace: str, params: dict) -> Optional[Any]:
        key = self._make_key(namespace, params)
        now = time.monotonic()
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self.misses += 1
                return None
            expires_at, version, value = entry
            if version != self._version or now >= expires_at:
                # Stale (invalidated by a scrape) or expired.
                self._store.pop(key, None)
                self.misses += 1
                return None
            self.hits += 1
            return value

    def set(self, namespace: str, params: dict, value: Any, ttl: Optional[float] = None) -> None:
        key = self._make_key(namespace, params)
        ttl = settings.cache_ttl_seconds if ttl is None else ttl
        with self._lock:
            self._store[key] = (time.monotonic() + ttl, self._version, value)

    def clear(self) -> None:
        """Invalidate everything (called after a scrape writes new jobs)."""
        with self._lock:
            self._version += 1
            self._store.clear()

    def get_or_set(self, namespace: str, params: dict, producer: Callable[[], Any],
                   ttl: Optional[float] = None) -> Any:
        cached = self.get(namespace, params)
        if cached is not None:
            return cached
        value = producer()
        self.set(namespace, params, value, ttl=ttl)
        return value

    def stats(self) -> dict:
        total = self.hits + self.misses
        with self._lock:
            size = len(self._store)
        return {
            "entries": size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / total, 3) if total else 0.0,
        }


# Process-wide singleton used by the read endpoints and invalidated by the engine.
cache = TTLCache()
