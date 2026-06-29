"""FastAPI application entry point.

On startup it creates tables, syncs source/keyword metadata and (optionally)
starts the background scheduler.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import categories, diagnostics, jobs, scraper, sources, stats
from app.config import settings
from app.database import SessionLocal, init_db
from app.scraper.scheduler import shutdown_scheduler, start_scheduler
from app.services.source_service import seed_keywords, sync_sources
from app.utils.logger import get_logger

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("Starting Job Aggregator API...")
    init_db()
    db = SessionLocal()
    try:
        sync_sources(db)
        seed_keywords(db)
    finally:
        db.close()
    start_scheduler()
    logger.info("Tracking keywords: %s", ", ".join(settings.keywords))
    yield
    # --- Shutdown ---
    shutdown_scheduler()
    logger.info("Job Aggregator API stopped.")


app = FastAPI(
    title="Job Aggregator API",
    description="Aggregates job postings from multiple compliant sources.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(scraper.router)
app.include_router(diagnostics.router)
app.include_router(sources.router)
app.include_router(stats.router)
app.include_router(categories.router)


@app.get("/", tags=["health"])
def root():
    return {
        "name": "Job Aggregator API",
        "status": "ok",
        "keywords": settings.keywords,
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
def health():
    return {"status": "healthy"}
