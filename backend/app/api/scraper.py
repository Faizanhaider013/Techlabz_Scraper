"""Scraper control / history endpoints."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models import ScraperRun
from app.schemas import ScraperRunOut, ScraperRunTriggerResponse
from app.scraper.engine import run_scraper
from app.utils.logger import get_logger

router = APIRouter(prefix="/api/scraper", tags=["scraper"])
logger = get_logger("api.scraper")


def _run_in_background() -> None:
    db = SessionLocal()
    try:
        run_scraper(db, trigger="manual")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Background scraper run failed: %s", exc)
    finally:
        db.close()


@router.post("/run", response_model=ScraperRunTriggerResponse)
def trigger_scraper(
    background_tasks: BackgroundTasks,
    wait: bool = Query(False, description="Run synchronously and return totals"),
    db: Session = Depends(get_db),
):
    """Manually trigger a scraper run.

    By default the run executes in the background and returns immediately. Pass
    ``?wait=true`` to run synchronously and receive the totals in the response
    (useful for the very first seeding run).
    """
    if wait:
        run = run_scraper(db, trigger="manual")
        return ScraperRunTriggerResponse(
            message="Scraper run completed.",
            run_id=run.id,
            total_found=run.total_found,
            total_relevant=run.total_relevant,
            total_new=run.total_new,
            total_duplicates=run.total_duplicates,
            status=run.status,
        )

    background_tasks.add_task(_run_in_background)
    return ScraperRunTriggerResponse(
        message="Scraper run started in the background. Check /api/scraper/runs for results.",
        status="running",
    )


@router.get("/runs", response_model=list[ScraperRunOut])
def list_runs(
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
):
    runs = (
        db.execute(select(ScraperRun).order_by(desc(ScraperRun.started_at)).limit(limit))
        .scalars()
        .all()
    )
    return [ScraperRunOut.model_validate(r) for r in runs]
