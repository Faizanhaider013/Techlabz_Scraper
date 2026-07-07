"""Jobs API endpoints."""
from __future__ import annotations

from math import ceil
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas import JobBase, JobDetail, JobListResponse
from app.services import job_service
from app.utils.cache import cache

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _build_list_response(db: Session, **kwargs) -> JobListResponse:
    page = kwargs["page"]
    limit = kwargs["limit"]
    jobs, total = job_service.list_jobs(db, **kwargs)
    return JobListResponse(
        items=[JobBase.model_validate(j) for j in jobs],
        total=total,
        page=page,
        limit=limit,
        pages=max(1, ceil(total / limit)) if total else 0,
    )


@router.get("", response_model=JobListResponse)
def get_jobs(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="Free-text search on title/company/keyword"),
    keyword: Optional[str] = None,
    location: Optional[str] = None,
    days: Optional[int] = Query(10, description="Freshness lookback in days"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    source: Optional[str] = None,
    remote_type: Optional[str] = None,
    module: Optional[str] = Query(None, description="Filter by matched ServiceNow module code"),
    category: Optional[str] = Query(None, description="Filter by job category id"),
    sort: str = Query("newest", pattern="^(newest|oldest)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
):
    params = dict(
        q=q, keyword=keyword, location=location, days=days,
        start_date=start_date, end_date=end_date, source=source,
        remote_type=remote_type, module=module, category=category,
        sort=sort, page=page, limit=limit,
    )
    if settings.cache_enabled:
        cached = cache.get("jobs", params)
        if cached is not None:
            return cached
    response = _build_list_response(db, **params)
    if settings.cache_enabled:
        cache.set("jobs", params, response)
    return response


@router.get("/today", response_model=JobListResponse)
def get_today_jobs(
    db: Session = Depends(get_db),
    sort: str = Query("newest", pattern="^(newest|oldest)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
):
    params = dict(days=0, sort=sort, page=page, limit=limit)
    if settings.cache_enabled:
        cached = cache.get("jobs_today", params)
        if cached is not None:
            return cached
    response = _build_list_response(db, **params)
    if settings.cache_enabled:
        cache.set("jobs_today", params, response)
    return response


@router.get("/{job_id}", response_model=JobDetail)
def get_job_detail(job_id: int, db: Session = Depends(get_db)):
    job = job_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobDetail.model_validate(job)
