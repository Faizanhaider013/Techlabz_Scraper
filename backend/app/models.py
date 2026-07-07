"""SQLAlchemy ORM models: jobs, scraper_runs, sources, keywords."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        # dedupe_key is the canonical fingerprint of a job; it must be unique.
        UniqueConstraint("dedupe_key", name="uq_jobs_dedupe_key"),
        Index("ix_jobs_is_posted_today", "is_posted_today"),
        Index("ix_jobs_posted_date", "posted_date"),
        Index("ix_jobs_keyword", "keyword_matched"),
        Index("ix_jobs_source", "source_name"),
        Index("ix_jobs_company", "company_name"),
        Index("ix_jobs_location", "location"),
        Index("ix_jobs_primary_category", "primary_category"),
        # The default listing filters on (is_remote, is_us) and orders by
        # (is_posted_today, posted_date desc). A composite index lets Postgres
        # satisfy the hot path with a single index scan.
        Index("ix_jobs_listing", "is_remote", "is_us", "posted_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    company_name: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    location: Mapped[str] = mapped_column(String(512), nullable=False, default="")

    # Raw, as reported by the source (e.g. "3 days ago", "2026-06-25").
    date_posted_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Normalized, timezone-aware posting date.
    posted_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_posted_today: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    job_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    salary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    short_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    original_apply_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    keyword_matched: Mapped[str | None] = mapped_column(String(255), nullable=True)
    remote_type: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Multi-stack relevance enrichment (from the relevance scorer).
    relevance_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    primary_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    matched_categories: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list of ids
    matched_keywords: Mapped[str | None] = mapped_column(Text, nullable=True)    # JSON list
    matched_terms: Mapped[str | None] = mapped_column(Text, nullable=True)       # JSON list (alias of keywords)
    matched_modules: Mapped[str | None] = mapped_column(Text, nullable=True)     # JSON list (ServiceNow modules)
    query_used: Mapped[str | None] = mapped_column(String(255), nullable=True)
    days_old: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Strict relevance flags. Only jobs that pass all three are stored, but the
    # flags are persisted so the API can defensively re-enforce them at query time.
    is_servicenow: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_remote: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_us: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Canonical fingerprint used for deduplication.
    dedupe_key: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )


class ScraperRun(Base):
    __tablename__ = "scraper_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # running | success | partial | failed
    status: Mapped[str] = mapped_column(String(32), default="running", nullable=False)
    total_found: Mapped[int] = mapped_column(Integer, default=0)
    total_new: Mapped[int] = mapped_column(Integer, default=0)
    total_duplicates: Mapped[int] = mapped_column(Integer, default=0)

    # Strict-filter breakdown for observability.
    total_raw_fetched: Mapped[int] = mapped_column(Integer, default=0)
    total_skipped_irrelevant: Mapped[int] = mapped_column(Integer, default=0)
    total_skipped_non_remote: Mapped[int] = mapped_column(Integer, default=0)
    total_skipped_non_us: Mapped[int] = mapped_column(Integer, default=0)
    total_relevant: Mapped[int] = mapped_column(Integer, default=0)
    # JSON-encoded list of error strings.
    errors: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON-encoded per-source summary.
    source_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger: Mapped[str] = mapped_column(String(32), default="manual")  # manual|scheduled


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(64), default="api")  # api|career_page|mock
    base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # active | skipped | blocked | needs_api_key
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    reason_if_skipped: Mapped[str | None] = mapped_column(Text, nullable=True)
    uses_api: Mapped[bool] = mapped_column(Boolean, default=False)
    robots_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    tos_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )


class SourceDiagnostic(Base):
    __tablename__ = "source_diagnostics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_name: Mapped[str] = mapped_column(String(128), nullable=False)
    run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # success | no_results | blocked | skipped | error
    status: Mapped[str] = mapped_column(String(32), default="success")
    raw_count: Mapped[int] = mapped_column(Integer, default=0)
    parsed_jobs: Mapped[int] = mapped_column(Integer, default=0)
    today_matches: Mapped[int] = mapped_column(Integer, default=0)
    servicenow_count: Mapped[int] = mapped_column(Integer, default=0)
    remote_count: Mapped[int] = mapped_column(Integer, default=0)
    us_count: Mapped[int] = mapped_column(Integer, default=0)
    saved_count: Mapped[int] = mapped_column(Integer, default=0)
    rejected_old_date: Mapped[int] = mapped_column(Integer, default=0)
    rejected_unknown_date: Mapped[int] = mapped_column(Integer, default=0)
    rejected_non_servicenow: Mapped[int] = mapped_column(Integer, default=0)
    rejected_low_relevance: Mapped[int] = mapped_column(Integer, default=0)
    rejected_non_remote: Mapped[int] = mapped_column(Integer, default=0)
    rejected_non_us: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0)
    pages_fetched: Mapped[int] = mapped_column(Integer, default=0)
    queries_tried: Mapped[int] = mapped_column(Integer, default=0)
    # JSON-encoded lists / text.
    sample_titles: Mapped[str | None] = mapped_column(Text, nullable=True)
    sample_raw_dates: Mapped[str | None] = mapped_column(Text, nullable=True)
    sample_rejections: Mapped[str | None] = mapped_column(Text, nullable=True)
    near_matches: Mapped[str | None] = mapped_column(Text, nullable=True)
    # ServiceNow ecosystem diagnostics (JSON-encoded).
    sample_saved_titles: Mapped[str | None] = mapped_column(Text, nullable=True)
    top_successful_queries: Mapped[str | None] = mapped_column(Text, nullable=True)
    top_matched_modules: Mapped[str | None] = mapped_column(Text, nullable=True)
    top_categories_found: Mapped[str | None] = mapped_column(Text, nullable=True)
    top_keywords_found: Mapped[str | None] = mapped_column(Text, nullable=True)
    query_stats: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )


class Keyword(Base):
    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    term: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
