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

    # Prefer minute-level cadence (default every 30 min); fall back to hours.
    minutes = int(getattr(settings, "scraper_interval_minutes", 0) or 0)
    _scheduler = BackgroundScheduler(timezone="UTC")
    if minutes > 0:
        trigger_kwargs = {"minutes": minutes}
        human = f"{minutes} minute(s)"
    else:
        hours = max(1, int(settings.scraper_interval_hours))
        trigger_kwargs = {"hours": hours}
        human = f"{hours} hour(s)"
    _scheduler.add_job(
        _scheduled_job,
        trigger="interval",
        id="scrape_job",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
        **trigger_kwargs,
    )
    _scheduler.start()
    logger.info("Scheduler started: scraping every %s.", human)
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped.")
