"""Pydantic schemas for API request/response validation."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


def _as_list(value: Any) -> List[str]:
    """Parse a JSON-encoded string column into a list (tolerant of bad data)."""
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    try:
        data = json.loads(value)
        return [str(v) for v in data] if isinstance(data, list) else []
    except (ValueError, TypeError):
        return []


class JobBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company_name: str
    location: str
    date_posted_raw: Optional[str] = None
    normalized_date_posted: Optional[datetime] = None
    is_posted_today: bool
    job_type: Optional[str] = None
    salary: Optional[str] = None
    short_description: Optional[str] = None
    original_apply_url: str
    source_name: str
    source_job_id: Optional[str] = None
    keyword_matched: Optional[str] = None
    remote_type: Optional[str] = None
    # Multi-stack relevance enrichment.
    relevance_score: int = 0
    primary_category: Optional[str] = None
    matched_categories: List[str] = []
    matched_keywords: List[str] = []
    matched_modules: List[str] = []
    days_old: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("matched_categories", "matched_keywords", "matched_modules", mode="before")
    @classmethod
    def _parse_lists(cls, v):
        return _as_list(v)


class JobDetail(JobBase):
    """Full job, including the long description and full match detail."""

    full_description: Optional[str] = None
    matched_terms: List[str] = []
    query_used: Optional[str] = None

    @field_validator("matched_terms", mode="before")
    @classmethod
    def _parse_terms(cls, v):
        return _as_list(v)


class JobListResponse(BaseModel):
    items: List[JobBase]
    total: int
    page: int
    limit: int
    pages: int


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    base_url: Optional[str] = None
    status: str
    reason_if_skipped: Optional[str] = None
    uses_api: bool
    robots_checked: bool
    tos_checked: bool


class ScraperRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: str
    total_found: int
    total_raw_fetched: int = 0
    total_relevant: int = 0
    total_skipped_irrelevant: int = 0
    total_skipped_non_remote: int = 0
    total_skipped_non_us: int = 0
    total_new: int
    total_duplicates: int
    errors: Optional[str] = None
    source_summary: Optional[str] = None
    trigger: str


class CountItem(BaseModel):
    label: str
    count: int


class StatsResponse(BaseModel):
    # TODAY-focused headline counts.
    total_jobs: int           # total today jobs when TODAY_ONLY (else all-time)
    today_jobs: int
    posted_today: int
    last_3_days: int
    last_7_days: int
    # Source coverage + rejection breakdown from the latest run.
    sources_attempted: int = 0
    sources_with_results: int = 0
    rejected_old_jobs: int = 0
    rejected_unknown_date: int = 0
    rejected_non_servicenow: int = 0
    rejected_non_remote: int = 0
    rejected_non_us: int = 0
    today_only: bool = True
    window_days: int = 0   # 0 = today only; N = jobs from the last N days
    modules_covered: int = 0
    sources_checked: int = 0
    total_categories: int = 0
    module_breakdown: List[CountItem] = []
    category_breakdown: List[CountItem] = []
    top_companies: List[CountItem]
    top_locations: List[CountItem]
    source_breakdown: List[CountItem]
    keyword_breakdown: List[CountItem]


class SourceDiagnosticOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_name: str
    enabled: bool
    status: str
    raw_count: int
    parsed_jobs: int = 0
    today_matches: int = 0
    servicenow_count: int
    remote_count: int
    us_count: int
    saved_count: int
    rejected_old_date: int = 0
    rejected_unknown_date: int = 0
    rejected_non_servicenow: int = 0
    rejected_low_relevance: int = 0
    rejected_non_remote: int
    rejected_non_us: int
    duplicate_count: int
    pages_fetched: int = 0
    queries_tried: int = 0
    sample_titles: List[str] = []
    sample_raw_dates: List[str] = []
    sample_rejections: List[str] = []
    near_matches: List[str] = []
    sample_saved_titles: List[str] = []
    top_successful_queries: List[dict] = []
    top_matched_modules: List[dict] = []
    top_categories_found: List[dict] = []
    top_keywords_found: List[dict] = []
    reason: Optional[str] = None
    error_message: Optional[str] = None
    last_run_at: Optional[datetime] = None


class DiagnosticsResponse(BaseModel):
    run_id: Optional[int] = None
    last_run_at: Optional[datetime] = None
    total_raw: int = 0
    total_saved: int = 0
    # Run-wide roll-ups across all sources.
    top_successful_queries: List[dict] = []
    top_matched_modules: List[dict] = []
    top_categories_found: List[dict] = []
    top_keywords_found: List[dict] = []
    sources: List[SourceDiagnosticOut] = []


class QueryDiagnosticOut(BaseModel):
    query: str
    source: str
    category: Optional[str] = None
    raw_count: int = 0
    saved_count: int = 0
    rejected_count: int = 0
    top_rejection_reason: Optional[str] = None


class QueryDiagnosticsResponse(BaseModel):
    run_id: Optional[int] = None
    last_run_at: Optional[datetime] = None
    queries: List[QueryDiagnosticOut] = []


class CategoryOut(BaseModel):
    category_id: str
    category_name: str
    enabled: bool
    job_count: int = 0


class ScraperRunTriggerResponse(BaseModel):
    message: str
    run_id: Optional[int] = None
    total_found: int = 0
    total_relevant: int = 0
    total_new: int = 0
    total_duplicates: int = 0
    status: str = "running"
