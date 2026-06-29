"""Jobs API endpoints."""
from __future__ import annotations

from math import ceil
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import JobBase, JobDetail, JobListResponse
from app.services import job_service

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=JobListResponse)
def get_jobs(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="Free-text search on title/company/keyword"),
    keyword: Optional[str] = None,
    location: Optional[str] = None,
    date_filter: str = Query("all", pattern="^(today|last_3_days|last_7_days|all)$"),
    source: Optional[str] = None,
    remote_type: Optional[str] = None,
    module: Optional[str] = Query(None, description="Filter by matched ServiceNow module code"),
    category: Optional[str] = Query(None, description="Filter by job category id"),
    sort: str = Query("newest", pattern="^(newest|oldest)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    jobs, total = job_service.list_jobs(
        db,
        q=q,
        keyword=keyword,
        location=location,
        date_filter=date_filter,
        source=source,
        remote_type=remote_type,
        module=module,
        category=category,
        sort=sort,
        page=page,
        limit=limit,
    )
    return JobListResponse(
        items=[JobBase.model_validate(j) for j in jobs],
        total=total,
        page=page,
        limit=limit,
        pages=max(1, ceil(total / limit)) if total else 0,
    )


@router.get("/today", response_model=JobListResponse)
def get_today_jobs(
    db: Session = Depends(get_db),
    sort: str = Query("newest", pattern="^(newest|oldest)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    jobs, total = job_service.list_jobs(
        db, date_filter="today", sort=sort, page=page, limit=limit
    )
    return JobListResponse(
        items=[JobBase.model_validate(j) for j in jobs],
        total=total,
        page=page,
        limit=limit,
        pages=max(1, ceil(total / limit)) if total else 0,
    )


@router.get("/{job_id}", response_model=JobDetail)
def get_job_detail(job_id: int, db: Session = Depends(get_db)):
    job = job_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobDetail.model_validate(job)
