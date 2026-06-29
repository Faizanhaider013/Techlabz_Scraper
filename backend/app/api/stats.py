"""Dashboard stats endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import StatsResponse
from app.services.stats_service import get_stats

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
def stats(db: Session = Depends(get_db)):
    return get_stats(db)
