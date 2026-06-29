"""Per-source diagnostics accumulator (TODAY-only funnel).

Tracks the full funnel for one source during a run:
    raw -> parsed -> today -> ServiceNow -> remote -> US -> saved
plus rejection breakdowns (old date, unknown date, non-ServiceNow, non-remote,
non-US), duplicates, pages fetched, queries tried, samples, status and last
error. The engine fills these in and persists them to source_diagnostics so the
API/UI/CLI can explain exactly why the today count is what it is.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional

_SAMPLE_CAP = 8
_TOP_CAP = 10

# Status values: success | no_results | blocked | skipped | error | needs_api_key
STATUS_SUCCESS = "success"
STATUS_NO_RESULTS = "no_results"
STATUS_BLOCKED = "blocked"
STATUS_SKIPPED = "skipped"
STATUS_ERROR = "error"
STATUS_NEEDS_KEY = "needs_api_key"


@dataclass
class SourceDiag:
    source_name: str
    enabled: bool
    status: str = STATUS_SUCCESS
    raw_count: int = 0
    parsed_jobs: int = 0
    today_matches: int = 0
    servicenow_count: int = 0
    remote_count: int = 0
    us_count: int = 0
    saved_count: int = 0
    rejected_old_date: int = 0
    rejected_unknown_date: int = 0
    rejected_non_servicenow: int = 0
    rejected_low_relevance: int = 0
    rejected_non_remote: int = 0
    rejected_non_us: int = 0
    duplicate_count: int = 0
    pages_fetched: int = 0
    queries_tried: int = 0
    last_error: Optional[str] = None
    sample_raw_titles: List[str] = field(default_factory=list)
    sample_raw_dates: List[str] = field(default_factory=list)
    sample_rejections: List[str] = field(default_factory=list)
    near_matches: List[str] = field(default_factory=list)
    # Multi-stack coverage.
    sample_saved_titles: List[str] = field(default_factory=list)
    _saved_query_counts: Counter = field(default_factory=Counter)
    _module_counts: Counter = field(default_factory=Counter)
    _category_counts: Counter = field(default_factory=Counter)
    _keyword_counts: Counter = field(default_factory=Counter)
    # Per-query funnel: query -> {"raw","saved","rejected","reasons","category"}.
    _query_stats: Dict[str, dict] = field(default_factory=dict)

    def _qs(self, query: str) -> dict:
        return self._query_stats.setdefault(
            query, {"raw": 0, "saved": 0, "rejected": 0, "reasons": Counter(), "category": None}
        )

    def add_raw(self, title: str, raw_date, query: Optional[str] = None) -> None:
        if title and len(self.sample_raw_titles) < _SAMPLE_CAP:
            self.sample_raw_titles.append(title[:120])
        if len(self.sample_raw_dates) < _SAMPLE_CAP:
            self.sample_raw_dates.append(str(raw_date)[:40] if raw_date is not None else "—")
        if query:
            self._qs(query)["raw"] += 1

    def note_rejected(self, query: Optional[str], reason: str) -> None:
        if query:
            qs = self._qs(query)
            qs["rejected"] += 1
            qs["reasons"][reason] += 1

    def note_saved(
        self,
        query: Optional[str],
        title: str,
        modules: List[str],
        categories: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        primary_category: Optional[str] = None,
    ) -> None:
        if query:
            self._saved_query_counts[query] += 1
            qs = self._qs(query)
            qs["saved"] += 1
            if primary_category and not qs["category"]:
                qs["category"] = primary_category
        for m in modules or []:
            self._module_counts[m] += 1
        for c in categories or []:
            self._category_counts[c] += 1
        for k in keywords or []:
            self._keyword_counts[k] += 1
        if title and len(self.sample_saved_titles) < _SAMPLE_CAP:
            self.sample_saved_titles.append(title[:120])

    def top_categories_found(self) -> List[dict]:
        return [
            {"category": c, "count": n}
            for c, n in self._category_counts.most_common(_TOP_CAP)
        ]

    def top_keywords_found(self) -> List[dict]:
        return [
            {"keyword": k, "count": n}
            for k, n in self._keyword_counts.most_common(_TOP_CAP)
        ]

    def top_successful_queries(self) -> List[dict]:
        return [
            {"query": q, "saved": c}
            for q, c in self._saved_query_counts.most_common(_TOP_CAP)
        ]

    def top_matched_modules(self) -> List[dict]:
        return [
            {"module": m, "count": c}
            for m, c in self._module_counts.most_common(_TOP_CAP)
        ]

    def query_stats(self) -> List[dict]:
        out: List[dict] = []
        for query, qs in self._query_stats.items():
            if not (qs["raw"] or qs["saved"] or qs["rejected"]):
                continue
            top_reason = qs["reasons"].most_common(1)
            out.append({
                "query": query,
                "category": qs.get("category"),
                "raw_count": qs["raw"],
                "saved_count": qs["saved"],
                "rejected_count": qs["rejected"],
                "top_rejection_reason": top_reason[0][0] if top_reason else None,
            })
        out.sort(key=lambda r: (r["saved_count"], r["raw_count"]), reverse=True)
        return out

    def record(self, title: str, classification: dict) -> None:
        """Update funnel counters from one fully classified job."""
        if classification["date_known"]:
            self.parsed_jobs += 1
        if classification["is_today"]:
            self.today_matches += 1
        if classification["has_servicenow"]:
            self.servicenow_count += 1
        if classification["is_remote"]:
            self.remote_count += 1
        if classification["is_us"]:
            self.us_count += 1

        if not classification["allowed"]:
            reason = classification["reason"]
            bucket = {
                "old_date": "rejected_old_date",
                "unknown_date": "rejected_unknown_date",
                "not_servicenow": "rejected_non_servicenow",
                "not_relevant": "rejected_low_relevance",
                "not_remote": "rejected_non_remote",
                "not_us": "rejected_non_us",
            }.get(reason)
            if bucket:
                setattr(self, bucket, getattr(self, bucket) + 1)
            if len(self.sample_rejections) < _SAMPLE_CAP:
                self.sample_rejections.append(f"{title[:70]} -> {reason}")
            if classification.get("near_match") and len(self.near_matches) < _SAMPLE_CAP:
                self.near_matches.append(f"{title[:70]} -> {reason}")

    def finalize(self) -> None:
        if self.status in (STATUS_ERROR, STATUS_BLOCKED, STATUS_SKIPPED, STATUS_NEEDS_KEY):
            return
        self.status = STATUS_SUCCESS if self.saved_count > 0 else STATUS_NO_RESULTS
