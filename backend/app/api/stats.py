from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import StatsResponse
from app.services.stats_service import get_stats

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
def stats(
    db: Session = Depends(get_db),
    days: Optional[int] = Query(10, description="Freshness lookback in days"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
):
    return get_stats(db, days=days, start_date=start_date, end_date=end_date)
