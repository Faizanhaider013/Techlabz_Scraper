"""Tests for the performance layer: concurrent fetch + TTL cache."""
from __future__ import annotations

import time

from app.scraper.concurrent_fetch import prefetch_all_sources, _fetch_source_blocking
from app.scraper.sources.base import RawJob
from app.utils.cache import TTLCache


# ---------------------------------------------------------------------------
# Fake source used to exercise the concurrent fetcher without real network I/O.
# ---------------------------------------------------------------------------
class _FakeSource:
    def __init__(self, name, *, delay=0.0, fail=None, failure_status="error"):
        self.name = name
        self.failure_status = failure_status
        self._delay = delay
        self._fail = fail  # exception to raise, or None
        self.pages_fetched = 0
        self._run_cache = {}
        self.calls = []

    def fetch(self, keyword):
        self.calls.append(keyword)
        if self._delay:
            time.sleep(self._delay)
        self.pages_fetched += 1
        if self._fail is not None:
            raise self._fail
        return [
            RawJob(
                title=f"{self.name} {keyword}",
                company_name="Acme",
                original_apply_url=f"https://x/{self.name}/{keyword}",
                source_name=self.name,
            )
        ]


class TestConcurrentFetch:
    def test_returns_jobs_per_source_and_keyword(self):
        sources = [_FakeSource("a"), _FakeSource("b")]
        out = prefetch_all_sources(sources, ["k1", "k2"])
        assert set(out) == {"a", "b"}
        assert len(out["a"].per_keyword["k1"]) == 1
        assert out["a"].per_keyword["k2"][0].title == "a k2"
        assert out["a"].pages_fetched == 2

    def test_runs_sources_concurrently(self):
        # Two sources that each sleep 0.2s should finish in ~0.2s, not ~0.4s.
        sources = [_FakeSource("a", delay=0.2), _FakeSource("b", delay=0.2)]
        start = time.perf_counter()
        prefetch_all_sources(sources, ["k1"])
        elapsed = time.perf_counter() - start
        assert elapsed < 0.35, f"expected concurrent (~0.2s), took {elapsed:.2f}s"

    def test_blocked_source_aborts_early(self):
        src = _FakeSource("blk", fail=RuntimeError("403"), failure_status="blocked")
        result = _fetch_source_blocking(src, ["k1", "k2", "k3"])
        assert result.status == "blocked"
        assert result.error is not None
        assert src.calls == ["k1"]  # stopped after the first failing keyword

    def test_transient_error_continues(self):
        src = _FakeSource("err", fail=ValueError("boom"), failure_status="error")
        result = _fetch_source_blocking(src, ["k1", "k2"])
        assert result.status == "error"
        assert src.calls == ["k1", "k2"]  # all keywords attempted
        assert result.per_keyword["k1"] == []

    def test_one_failing_source_does_not_kill_others(self):
        sources = [
            _FakeSource("good"),
            _FakeSource("bad", fail=RuntimeError("nope")),
        ]
        out = prefetch_all_sources(sources, ["k1"])
        assert out["good"].per_keyword["k1"][0].title == "good k1"
        assert out["bad"].error is not None


class TestTTLCache:
    def test_get_set_roundtrip(self):
        c = TTLCache()
        assert c.get("jobs", {"page": 1}) is None
        c.set("jobs", {"page": 1}, ["job"], ttl=10)
        assert c.get("jobs", {"page": 1}) == ["job"]

    def test_param_order_is_stable(self):
        c = TTLCache()
        c.set("jobs", {"a": 1, "b": 2}, "v", ttl=10)
        assert c.get("jobs", {"b": 2, "a": 1}) == "v"

    def test_distinct_params_do_not_collide(self):
        c = TTLCache()
        c.set("jobs", {"page": 1}, "p1", ttl=10)
        c.set("jobs", {"page": 2}, "p2", ttl=10)
        assert c.get("jobs", {"page": 1}) == "p1"
        assert c.get("jobs", {"page": 2}) == "p2"

    def test_expiry(self):
        c = TTLCache()
        c.set("jobs", {"page": 1}, "v", ttl=0.05)
        time.sleep(0.06)
        assert c.get("jobs", {"page": 1}) is None

    def test_clear_invalidates_everything(self):
        c = TTLCache()
        c.set("jobs", {"page": 1}, "v", ttl=100)
        c.clear()
        assert c.get("jobs", {"page": 1}) is None

    def test_none_params_ignored_in_key(self):
        c = TTLCache()
        c.set("jobs", {"page": 1, "source": None}, "v", ttl=10)
        assert c.get("jobs", {"page": 1}) == "v"
