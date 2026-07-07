"""FastAPI application entry point.

On startup it creates tables, syncs source/keyword metadata and (optionally)
starts the background scheduler.
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import categories, diagnostics, jobs, scraper, sources, stats
from app.config import settings
from app.database import SessionLocal, engine, init_db
from app.scraper.scheduler import shutdown_scheduler, start_scheduler
from app.services.source_service import seed_keywords, sync_sources
from app.utils.cache import cache
from app.utils.logger import get_logger

logger = get_logger("main")

# Requests slower than this are logged at WARNING so regressions are visible.
_SLOW_REQUEST_MS = 300


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

# ---- CORS: allow Vercel production, Vercel preview, and localhost ----------
_cors_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "https://techlabz-scraper.vercel.app",
]
# Merge any additional origins from the CORS_ORIGINS env var (if set).
for origin in settings.cors_origin_list:
    if origin not in _cors_origins:
        _cors_origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    # Vercel preview deployments use dynamic subdomains — match them via regex.
    allow_origin_regex=r"^https://techlabz-scraper(-.*)?\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_request_latency(request: Request, call_next):
    """Measure and log every request's latency; expose it via X-Process-Time."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time"] = f"{elapsed_ms:.1f}ms"
    log = logger.warning if elapsed_ms > _SLOW_REQUEST_MS else logger.info
    log("%s %s -> %s in %.1fms", request.method, request.url.path,
        response.status_code, elapsed_ms)
    return response


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
    """Liveness + readiness probe: verifies DB connectivity and reports cache stats."""
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        db_ok = False
        logger.error("Health check DB probe failed: %s", exc)
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "up" if db_ok else "down",
        "cache": cache.stats(),
    }
