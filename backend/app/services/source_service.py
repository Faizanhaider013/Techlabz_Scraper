"""Keep the `sources` DB table in sync with the registered adapters.

The adapters are the single source of truth for compliance metadata; this syncs
that metadata into the database so the /api/sources endpoint can serve it.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Source
from app.scraper.sources import ALL_SOURCES
from app.utils.logger import get_logger

logger = get_logger("source_service")


def sync_sources(db: Session) -> None:
    for adapter in ALL_SOURCES:
        existing = db.execute(
            select(Source).where(Source.name == adapter.name)
        ).scalar_one_or_none()

        fields = dict(
            type=adapter.type,
            base_url=adapter.base_url,
            status=adapter.status,
            reason_if_skipped=adapter.reason_if_skipped,
            uses_api=adapter.uses_api,
            robots_checked=adapter.robots_checked,
            tos_checked=adapter.tos_checked,
        )
        if existing is None:
            db.add(Source(name=adapter.name, **fields))
        else:
            for key, value in fields.items():
                setattr(existing, key, value)
    db.commit()
    logger.info("Synced %d source adapter(s) into the database.", len(ALL_SOURCES))


def seed_keywords(db: Session) -> None:
    """Seed the keywords table from configured defaults if it is empty."""
    from app.config import settings
    from app.models import Keyword

    count = db.execute(select(Keyword)).first()
    if count is not None:
        return
    for term in settings.keywords:
        db.add(Keyword(term=term, active=True))
    db.commit()
    logger.info("Seeded %d default keyword(s).", len(settings.keywords))
