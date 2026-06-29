"""Background scheduler using APScheduler.

When ENABLE_SCHEDULER is true the API process starts an in-process scheduler that
runs the scraper every SCRAPER_INTERVAL_HOURS hours. For cron-based deployments,
disable the scheduler and call ``python -m app.cli scrape`` from cron instead.
"""
from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.database import SessionLocal
from app.scraper.engine import run_scraper
from app.utils.logger import get_logger

logger = get_logger("scheduler")

_scheduler: BackgroundScheduler | None = None


def _scheduled_job() -> None:
    db = SessionLocal()
    try:
        run_scraper(db, trigger="scheduled")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Scheduled scraper run crashed: %s", exc)
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler | None:
    global _scheduler
    if not settings.enable_scheduler:
        logger.info("Scheduler disabled (ENABLE_SCHEDULER=false).")
        return None
    if _scheduler is not None:
        return _scheduler

    interval = max(1, int(settings.scraper_interval_hours))
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        _scheduled_job,
        trigger="interval",
        hours=interval,
        id="scrape_job",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler started: scraping every %d hour(s).", interval)
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped.")
