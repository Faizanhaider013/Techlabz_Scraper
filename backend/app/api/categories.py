"""Categories API: enabled job categories and their current job counts."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Job
from app.scraper import job_taxonomy as jtax
from app.schemas import CategoryOut

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    enabled = set(settings.enabled_category_list)

    # Count stored remote+US jobs per primary category.
    rows = db.execute(
        select(Job.primary_category, func.count())
        .where(Job.is_remote.is_(True), Job.is_us.is_(True))
        .where(Job.primary_category.isnot(None))
        .group_by(Job.primary_category)
    ).all()
    counts = {str(cid): n for cid, n in rows}

    return [
        CategoryOut(
            category_id=cat.category_id,
            category_name=cat.category_name,
            enabled=cat.category_id in enabled,
            job_count=counts.get(cat.category_id, 0),
        )
        for cat in jtax.CATEGORIES.values()
    ]
