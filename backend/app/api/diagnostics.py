"""Scraper diagnostics endpoint.

Returns the per-source funnel from the most recent scraper run so the UI and
operators can see exactly why the portal has the job count it has.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SourceDiagnostic
from app.schemas import (
    DiagnosticsResponse,
    QueryDiagnosticOut,
    QueryDiagnosticsResponse,
    SourceDiagnosticOut,
)

router = APIRouter(prefix="/api/scraper", tags=["diagnostics"])


def _load_json(value) -> list:
    if not value:
        return []
    try:
        data = json.loads(value)
        return data if isinstance(data, list) else []
    except (ValueError, TypeError):
        return []


def _merge_counts(rows, attr: str, key: str, value_key: str) -> list:
    """Merge per-source [{key: x, value_key: n}] lists into a sorted roll-up."""
    totals: dict = {}
    for r in rows:
        for item in _load_json(getattr(r, attr)):
            if isinstance(item, dict) and key in item:
                totals[item[key]] = totals.get(item[key], 0) + int(item.get(value_key, 0))
    merged = [{key: k, value_key: v} for k, v in totals.items()]
    merged.sort(key=lambda d: d[value_key], reverse=True)
    return merged[:10]


def _latest_run(db: Session):
    return db.execute(
        select(SourceDiagnostic.run_id, SourceDiagnostic.created_at)
        .order_by(SourceDiagnostic.id.desc())
        .limit(1)
    ).first()


@router.get("/diagnostics", response_model=DiagnosticsResponse)
def get_diagnostics(db: Session = Depends(get_db)):
    # Find the most recent run that produced diagnostics.
    latest_run = _latest_run(db)

    if latest_run is None:
        return DiagnosticsResponse()

    run_id, created_at = latest_run
    rows = db.execute(
        select(SourceDiagnostic)
        .where(SourceDiagnostic.run_id == run_id)
        .order_by(SourceDiagnostic.saved_count.desc(), SourceDiagnostic.source_name)
    ).scalars().all()

    sources = [
        SourceDiagnosticOut(
            source_name=r.source_name,
            enabled=r.enabled,
            status=r.status,
            raw_count=r.raw_count,
            parsed_jobs=r.parsed_jobs,
            today_matches=r.today_matches,
            servicenow_count=r.servicenow_count,
            remote_count=r.remote_count,
            us_count=r.us_count,
            saved_count=r.saved_count,
            rejected_old_date=r.rejected_old_date,
            rejected_unknown_date=r.rejected_unknown_date,
            rejected_non_servicenow=r.rejected_non_servicenow,
            rejected_low_relevance=r.rejected_low_relevance,
            rejected_non_remote=r.rejected_non_remote,
            rejected_non_us=r.rejected_non_us,
            duplicate_count=r.duplicate_count,
            pages_fetched=r.pages_fetched,
            queries_tried=r.queries_tried,
            sample_titles=_load_json(r.sample_titles),
            sample_raw_dates=_load_json(r.sample_raw_dates),
            sample_rejections=_load_json(r.sample_rejections),
            near_matches=_load_json(r.near_matches),
            sample_saved_titles=_load_json(r.sample_saved_titles),
            top_successful_queries=_load_json(r.top_successful_queries),
            top_matched_modules=_load_json(r.top_matched_modules),
            top_categories_found=_load_json(r.top_categories_found),
            top_keywords_found=_load_json(r.top_keywords_found),
            reason=r.reason,
            error_message=r.error_message,
            last_run_at=r.created_at,
        )
        for r in rows
    ]

    return DiagnosticsResponse(
        run_id=run_id,
        last_run_at=created_at,
        total_raw=sum(s.raw_count for s in sources),
        total_saved=sum(s.saved_count for s in sources),
        top_successful_queries=_merge_counts(rows, "top_successful_queries", "query", "saved"),
        top_matched_modules=_merge_counts(rows, "top_matched_modules", "module", "count"),
        top_categories_found=_merge_counts(rows, "top_categories_found", "category", "count"),
        top_keywords_found=_merge_counts(rows, "top_keywords_found", "keyword", "count"),
        sources=sources,
    )


@router.get("/query-diagnostics", response_model=QueryDiagnosticsResponse)
def get_query_diagnostics(db: Session = Depends(get_db)):
    """Per-(source, query) funnel for the most recent run."""
    latest_run = _latest_run(db)
    if latest_run is None:
        return QueryDiagnosticsResponse()

    run_id, created_at = latest_run
    rows = db.execute(
        select(SourceDiagnostic).where(SourceDiagnostic.run_id == run_id)
    ).scalars().all()

    queries = []
    for r in rows:
        for item in _load_json(r.query_stats):
            if not isinstance(item, dict):
                continue
            queries.append(
                QueryDiagnosticOut(
                    query=item.get("query", ""),
                    source=r.source_name,
                    category=item.get("category"),
                    raw_count=item.get("raw_count", 0),
                    saved_count=item.get("saved_count", 0),
                    rejected_count=item.get("rejected_count", 0),
                    top_rejection_reason=item.get("top_rejection_reason"),
                )
            )
    queries.sort(key=lambda q: (q.saved_count, q.raw_count), reverse=True)
    return QueryDiagnosticsResponse(run_id=run_id, last_run_at=created_at, queries=queries)
