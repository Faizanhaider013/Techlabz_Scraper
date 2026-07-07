from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas import StatsResponse
from app.services.stats_service import get_stats
from app.utils.cache import cache

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
def stats(
    db: Session = Depends(get_db),
    days: Optional[int] = Query(10, description="Freshness lookback in days"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
):
    params = dict(days=days, start_date=start_date, end_date=end_date)
    if settings.cache_enabled:
        cached = cache.get("stats", params)
        if cached is not None:
            return cached
    response = get_stats(db, days=days, start_date=start_date, end_date=end_date)
    if settings.cache_enabled:
        cache.set("stats", params, response)
    return response
