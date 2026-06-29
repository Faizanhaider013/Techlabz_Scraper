# Backend — Job Aggregator API

FastAPI service: scraper engine, scheduler, database, and REST API.

## Quick start

```bash
python -m venv .venv
source .venv/Scripts/activate        # Windows Git Bash; use .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env

python -m app.cli reset-db           # create/refresh schema + seed sources/keywords
python -m app.cli scrape             # collect jobs now (strict ServiceNow+Remote+US filter)
uvicorn app.main:app --reload --port 8000
```

Windows PowerShell: activate with `.\.venv\Scripts\Activate.ps1` and copy env with
`Copy-Item .env.example .env`.

Docs: <http://localhost:8000/docs>

Run tests: `python -m pytest tests/ -q`

To preview the UI with sample data, set `ENABLE_MOCK_DATA=true` in `.env` before
`reset-db`/`scrape` (dev only; off in production).

## Layout

```
app/
  main.py            FastAPI app + lifespan (init DB, sync sources, start scheduler)
  config.py          Settings (env-driven; keywords are configurable here)
  database.py        Engine/session; Postgres + SQLite fallback
  models.py          ORM: jobs, scraper_runs, sources, keywords
  schemas.py         Pydantic request/response models
  cli.py             CLI: init-db | reset-db | scrape | clean-irrelevant | sources
  scraper/
    relevance.py     STRICT filter: is_servicenow_job / is_remote_job / is_us_job / is_allowed_job
  api/               jobs.py, scraper.py, sources.py, stats.py
  scraper/
    engine.py        Orchestrates fetch -> normalize -> dedupe -> persist -> log
    scheduler.py     APScheduler interval job
    normalizer.py    RawJob -> DB record
    dedupe.py        URL + title/company/location fingerprinting
    date_utils.py    Relative/absolute date parsing + is_posted_today
    sources/
      base.py        BaseSource interface + RawJob + polite HTTP helper
      source_one.py      RemoteOK  (public API, active)
      source_two.py      Remotive  (public API, active)
      source_three.py    Arbeitnow (public API, active)
      source_restricted_example.py   LinkedIn (blocked, documented)
  services/          job_service.py, stats_service.py, source_service.py
  utils/logger.py    Console logging
```

## Environment variables

See `.env.example`. Key ones: `DATABASE_URL`, `DEFAULT_KEYWORDS`,
`SCRAPER_INTERVAL_HOURS`, `APP_TIMEZONE`, `ENABLE_SCHEDULER`, `CORS_ORIGINS`,
`REQUEST_DELAY_SECONDS`.

## Adding a source

Subclass `BaseSource`, set compliance metadata, implement `fetch()`, register in
`scraper/sources/__init__.py`. **Check robots.txt + TOS first; prefer official
APIs.** See `../SOURCES_REPORT.md`.
