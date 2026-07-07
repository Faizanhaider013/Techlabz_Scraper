-- ---------------------------------------------------------------------------
-- Migration 001: performance indexes + dedupe constraint
--
-- Idempotent (IF NOT EXISTS) so it is safe to run repeatedly. On a live
-- Postgres, prefer CREATE INDEX CONCURRENTLY to avoid locking the table:
--   run each statement outside a transaction and add CONCURRENTLY.
--
-- SQLAlchemy's create_all() also creates these from app/models.py on startup;
-- this file exists so DBAs / Render release commands can apply them explicitly.
-- ---------------------------------------------------------------------------

-- Unique fingerprint that prevents duplicate job rows
-- (SHA256 of company + title + location + apply URL + source, see dedupe.py).
ALTER TABLE jobs
    ADD CONSTRAINT uq_jobs_dedupe_key UNIQUE (dedupe_key);

-- Hot-path listing filter/sort: WHERE is_remote AND is_us ORDER BY posted_date.
CREATE INDEX IF NOT EXISTS ix_jobs_listing
    ON jobs (is_remote, is_us, posted_date);

-- Single-column indexes used by filters, stats GROUP BY, and the "today" gate.
CREATE INDEX IF NOT EXISTS ix_jobs_posted_date       ON jobs (posted_date);
CREATE INDEX IF NOT EXISTS ix_jobs_source            ON jobs (source_name);
CREATE INDEX IF NOT EXISTS ix_jobs_company           ON jobs (company_name);
CREATE INDEX IF NOT EXISTS ix_jobs_location          ON jobs (location);
CREATE INDEX IF NOT EXISTS ix_jobs_primary_category  ON jobs (primary_category);
CREATE INDEX IF NOT EXISTS ix_jobs_is_posted_today   ON jobs (is_posted_today);
CREATE INDEX IF NOT EXISTS ix_jobs_keyword           ON jobs (keyword_matched);

-- Keep planner statistics fresh after a large backfill.
ANALYZE jobs;
