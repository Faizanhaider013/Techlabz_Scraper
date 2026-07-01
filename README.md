# Remote Tech Jobs Aggregator — Scraper + Website

**Real remote software and technology jobs from trusted sources.**

Automatically collects job postings from multiple **compliant** job sources
across **many tech categories** (ServiceNow, PHP/Laravel, Node.js, React,
MERN/MEAN, Full Stack, Software Engineer, Python, DevOps/Cloud, Data/AI, and
QA/Automation), scores each job for **category relevance**, deduplicates them,
tags jobs **posted recently**, and serves them on a clean, searchable,
filterable website.

A job is saved/shown only if it passes **all** checks:

1. **Relevant** — the job matches at least one enabled category with a relevance
   score `>= MIN_RELEVANCE_SCORE` (default 70). Non-tech roles (sales, marketing,
   support, etc.) are rejected. ServiceNow stays **strict**: generic ITSM/CMDB/GRC
   without a ServiceNow-specific term never counts as ServiceNow.
2. **Remote** — clearly remote (explicit remote flag or remote wording; hybrid /
   onsite-only are rejected).
3. **US** (or Canada) — US-based or open to US/Canada candidates. Other
   countries / worldwide-only are rejected by default.

> It is better to show **0 jobs than irrelevant jobs**. The scraper never
> fabricates or pads results — no fake/mock jobs in production.

Everything is configurable via env (`JOB_MODE`, `ENABLED_JOB_CATEGORIES`,
`MIN_RELEVANCE_SCORE`, `REMOTE_ONLY`, `TARGET_COUNTRY`, `LOOKBACK_DAYS`).

## Supported categories

| id | category | examples |
|----|----------|----------|
| `servicenow` | ServiceNow | Developer, Admin, Consultant, ITSM/ITOM/CMDB/HRSD/CSM/SecOps |
| `php_laravel` | PHP / Laravel | PHP/Laravel/Symfony/WordPress/Magento |
| `node_backend` | Node.js / Backend | Node.js, Express, NestJS, API, GraphQL |
| `react_frontend` | React / Frontend | React, Next.js, Redux, UI |
| `mern` | MERN Stack | Mongo + Express + React + Node |
| `mean` | MEAN Stack | Mongo + Express + Angular + Node |
| `fullstack` | Full Stack | Full Stack (React/Node/Laravel/PHP/MERN/MEAN) |
| `software_engineer` | Software Engineer | Software/Application/Platform/Product Engineer |
| `python_backend` | Python / Backend | Python, Django, Flask, FastAPI |
| `devops_cloud` | DevOps / Cloud | DevOps, AWS/Azure/GCP, Kubernetes, SRE |
| `data_ai` | Data / AI | Data/ML/AI/NLP/LLM Engineer, Data Scientist |
| `qa_automation` | QA / Automation | QA, SDET, Selenium, Cypress, Playwright |

Categories, keywords, and scoring terms live in
[`backend/app/scraper/job_taxonomy.py`](./backend/app/scraper/job_taxonomy.py).
Run `python -m app.cli list-categories` / `list-keywords` to print them.

### Enable / disable categories & add keywords

- **Toggle categories:** set `ENABLED_JOB_CATEGORIES` in `backend/.env` to a
  comma-separated subset of the ids above (e.g.
  `ENABLED_JOB_CATEGORIES=react_frontend,node_backend,fullstack`).
- **Add keywords / a new category:** edit `job_taxonomy.py` — add to a category's
  `keywords`/`strong_terms`, or append a new `Category(...)` to `_DEFS` and add
  its id to `ENABLED_JOB_CATEGORIES`. No other code changes needed.
- **Tune precision:** raise/lower `MIN_RELEVANCE_SCORE` (higher = stricter).

### How relevance scoring works

`classify_job_category` scores a job against each enabled category:
`+100` exact keyword in title, `+80` keyword in description, `+50` strong stack
term in title, `+30` strong term in description, `+60` role-title + stack match,
`+20` weak/supporting term. The best category becomes `primary_category`; a job
is accepted when the best score reaches `MIN_RELEVANCE_SCORE`. Generic
ITSM/CMDB/GRC never reach the threshold on their own, preserving ServiceNow
precision (`SERVICENOW_STRICT_MODE=true`).

### How remote / US filtering works

Remote passes on an explicit remote flag or remote wording in
title/description/location/candidate-location (hybrid/onsite-only rejected). US
passes on United States / USA / U.S. / Remote US / US state names+codes;
`ALLOW_US_OR_CANADA=true` also accepts Canadian remote roles;
worldwide-only passes only if `ALLOW_WORLDWIDE_REMOTE_IF_US_NOT_EXCLUDED=true`.

---

## 0. Date window: today-only or last N days (configurable)

The portal enforces a strict **freshness window** on every job, controlled by two
env vars:

| `TODAY_ONLY` | `SCRAPER_LOOKBACK_DAYS` | Behaviour |
|--------------|--------------------------|-----------|
| `true` | (ignored) | **Strictly today** — only jobs dated the current calendar day in `APP_TIMEZONE`. |
| `false` | `14` | **Last 14 days** — jobs dated within the last 14 days (the current default). |
| `false` | `0` | No date gate (all dates). |

Whatever the window, a job is rejected if its date is **older than the window**,
or **unknown / unparseable** (those go to diagnostics as `rejected_unknown_date`).
There is no fuzzy "recent" pass — the window is exact. The green **Posted Today**
badge is shown only for jobs that are *genuinely* dated today, regardless of the
window. Both gates below read one source of truth: `settings.date_window_days`.

Two layers enforce this, so an old job can never appear:

1. **Save-time gate** — the scraper classifies each raw job through
   `date-window → ServiceNow → remote → US` (`relevance.classify_job`) and stores
   only jobs that pass *all four*. Out-of-window / unknown-date jobs are dropped
   and counted in diagnostics (`rejected_old_date`, `rejected_unknown_date`).
2. **Query-time gate (authoritative)** — `/api/jobs`, `/api/jobs/today` and
   `/api/stats` restrict results to rows whose `normalized_date_posted` falls
   within the freshness window in `APP_TIMEZONE`, computed from the live clock on
   every request. The `/api/jobs/today` endpoint is *always* strictly today. This
   deliberately does **not** trust the stored `is_posted_today` flag (frozen at
   scrape time, goes stale), so an out-of-window job can never resurface.

The frontend adds a third, defensive layer: a job card whose date is clearly in
the past is not rendered, and the green **Posted Today** badge only shows when
the date is genuinely today.

> **It is better to show 0 jobs than one inaccurate job.** Nothing is faked,
> seeded, padded, or relabelled. If no real ServiceNow remote-US role was posted
> today, the portal honestly shows none and the diagnostics explain why.

**Daily reset workflow** (wipe yesterday's data, collect today's):

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.cli reset-db        # drop + recreate + reseed (clears old jobs)
python -m app.cli scrape-today    # scrape, then prune anything not dated today
python -m app.cli diagnose-sources  # dry run: per-source funnel (why < 50?)
```

Relevant CLI commands:

| Command | Purpose |
|---------|---------|
| `scrape-today` | Run a scrape and keep **only** today's jobs (engine gate + prune). |
| `clean-non-today` | Delete every stored job whose normalized date is not today. |
| `clean-old-jobs` | Delete jobs older than today (alias of `clean-non-today`). |
| `diagnose-sources` | Dry run: fetch + classify, print the per-source funnel, save nothing. |

Today-only knobs in `backend/.env`: `TODAY_ONLY`, `APP_TIMEZONE`,
`MIN_TARGET_TODAY_JOBS`, `SCRAPER_LOOKBACK_DAYS`, `ALLOW_UNKNOWN_DATE`,
`ALLOW_YESTERDAY`, `ALLOW_LAST_3_DAYS`, `ALLOW_OLD_JOBS`, `MAX_PAGES_PER_SOURCE`.

---

## 1. Project overview

Two connected parts in a monorepo:

| Part | What it does |
|------|--------------|
| **Backend** (`backend/`) | FastAPI API + scraper engine + scheduler + database. Collects jobs from source adapters, normalizes them, removes duplicates, tags "posted today", logs every run, and serves a REST API. |
| **Frontend** (`frontend/`) | React + Tailwind website. Job cards, search, filters, sorting, a prominent **Posted Today** tab, job detail modal, stats dashboard, loading/empty states, fully responsive. |

The system ships with **48 registered sources** across three tiers:

- **Active API/feed sources** (RemoteOK, Remotive, Arbeitnow, Himalayas,
  We Work Remotely, Working Nomads, Jobspresso, Remote.co, and more)
- **ATS career board adapters** (Greenhouse, Lever, Ashby, Workday,
  SmartRecruiters, Recruitee, Teamtailor) — no API key required
- **Company Careers orchestrator** — discovers jobs across multiple ATS
  platforms for configured company names
- **Blocked/skipped stubs** for compliance-restricted sources (LinkedIn,
  Indeed, FlexJobs, etc.) — documented with reasons, never scraped

See [`SOURCES_REPORT.md`](./SOURCES_REPORT.md) for the full inventory.

---

## ServiceNow module coverage

This is a ServiceNow **ecosystem** scraper, not just a "ServiceNow Developer"
search. The taxonomy in
[`backend/app/scraper/servicenow_taxonomy.py`](./backend/app/scraper/servicenow_taxonomy.py)
and the query builder in
[`backend/app/scraper/query_builder.py`](./backend/app/scraper/query_builder.py)
drive searches across:

- **Roles** — Developer, Administrator, Consultant, Architect, Business Analyst,
  Engineer, Platform Owner, Implementation/Integration Specialist, and more.
- **Modules** — ITSM, ITOM, CMDB/CSDM, ITAM/SAM/HAM, HRSD, CSM, FSM, SecOps,
  IRM/GRC, SPM/ITBM, App Engine, Service Portal, Integration Hub, Discovery,
  Flow Designer, Virtual Agent, Performance Analytics, DevOps.
- **Technical platform terms** — GlideRecord, GlideAjax, Script Include,
  Business Rule, Client Script, UI Policy/Action, Flow Designer, IntegrationHub,
  MID Server, Transform/Import/Update Set, ATF, Service Portal, Employee Center,
  UI Builder, Scoped Application, and more.
- **Workflows & industry products** — FSO, TSM, Healthcare & Life Sciences SM,
  ESG, Legal Service Delivery, Source-to-Pay, etc.
- **Partner / company ATS boards** — many ServiceNow roles are posted directly by
  consulting firms on Greenhouse/Lever/Ashby (see below).

**How relevance works.** Every job is scored by
`score_servicenow_relevance` (in
[`relevance.py`](./backend/app/scraper/relevance.py)):

- A job is **accepted** if a direct ServiceNow phrase appears, the Now Platform is
  named, a strong ServiceNow-specific technical term is present, or the relevance
  score reaches the threshold (≥ 80).
- Generic **ITSM / CMDB / GRC / HRSD** jobs with **no** ServiceNow evidence are
  **rejected** — those terms exist outside ServiceNow and must not create false
  positives. Salesforce, Workday, and Jira Service Management roles are rejected.

Location scope is **US + Canada** remote (set `ALLOW_US_OR_CANADA=false` for
strict US-only). Each saved job stores its `relevance_score`, `matched_modules`,
`matched_terms`, `query_used`, and `days_old`, all surfaced in the UI and the
`/api/scraper/diagnostics` + `/api/scraper/query-diagnostics` endpoints.

Run `python -m app.cli list-modules` to print every group and the generated query
set.

## How to increase job count

The goal is **more real jobs, never fake or irrelevant ones**. If only 7 real
jobs exist, the portal shows 7. To widen genuine coverage:

1. **Add more ATS board names** in `backend/.env` (`GREENHOUSE_BOARDS`,
   `LEVER_COMPANIES`, `ASHBY_BOARDS`). ServiceNow partner firms worth
   investigating: `newrocket, thirdera, cprime, crossfuze, glidefast, accenture,
   deloitte, cognizant, infosys, capgemini, dxc, nttdata, kpmg, pwc, ey, wipro,
   hcltech, epam, cdw, guidehouse, leidos, saic, boozallen, bounteous, netimpact,
   acorio`. Verify which ATS each one uses — not all use Greenhouse/Lever/Ashby;
   a board that 404s is logged in diagnostics and otherwise ignored.
2. **Add API keys** for Adzuna, USAJOBS, The Muse, and Jooble (set the
   `ENABLE_*` flag **and** the key(s)).
3. **Increase `LOOKBACK_DAYS`** from 10 to 14 or 30 if you need a wider window.
4. **Increase `MAX_PAGES_PER_SOURCE`** for deeper pagination on paginated sources.
5. **Enable module/role/technical search** (`ENABLE_MODULE_SEARCH`,
   `ENABLE_ROLE_SEARCH`, `ENABLE_TECHNICAL_TERM_SEARCH`, `ENABLE_QUERY_EXPANSION`)
   — all on by default. Raise `MAX_QUERIES_PER_SOURCE` to use more of the taxonomy.
6. **Check diagnostics** (`python -m app.cli diagnose-sources` /
   `diagnose-queries`, or the Diagnostics tab) for blocked sources and the
   queries/modules that actually produce jobs.

---

## 2. Tech stack

- **Backend/API:** Python 3.11+, FastAPI, Uvicorn
- **Scraper:** httpx (+ BeautifulSoup available where HTML parsing is allowed)
- **Database:** PostgreSQL (production) with **SQLite fallback** for local dev — via SQLAlchemy 2.0
- **Scheduler:** APScheduler (in-process) or any cron via the CLI
- **Frontend:** React 18 + Vite + Tailwind CSS

---

## 3. Run the backend locally

```bash
cd backend
python -m venv .venv

# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# Windows (Git Bash):    source .venv/Scripts/activate
# macOS / Linux:         source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env          # SQLite is the default — zero extra setup

# Create tables + seed sources/keywords, then start the API:
python -m app.cli init-db
uvicorn app.main:app --reload --port 8000
```

API is now at <http://localhost:8000> · interactive docs at <http://localhost:8000/docs>.

**Optional — use PostgreSQL instead of SQLite:**

```bash
docker compose up -d          # starts Postgres on localhost:5432
# then in backend/.env set:
# DATABASE_URL=postgresql+psycopg2://jobuser:jobpass@localhost:5432/jobaggregator
```

---

## 4. Run the frontend locally

```bash
cd frontend
npm install
cp .env.example .env          # VITE_API_BASE_URL defaults to http://localhost:8000
npm run dev
```

Open <http://localhost:5173>.

---

## 4b. Windows PowerShell quick start

**Backend:**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m app.cli reset-db
python -m app.cli scrape-recent      # scrape last LOOKBACK_DAYS across all categories
python -m app.cli diagnose-sources   # dry run: per-source funnel table (why 0 jobs?)
python -m app.cli diagnose-queries   # dry run: per-query funnel table
python -m app.cli list-categories    # categories + enabled state
python -m app.cli list-keywords      # all category keywords
python -m app.cli list-sources       # show all 48 sources with status/method
python -m app.cli test-source remotive  # test a single source adapter
python -m app.cli test-company-careers  # test company career discovery
uvicorn app.main:app --reload --port 8000
```

**Frontend (new terminal):**

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

> To preview the UI with sample data, set `ENABLE_MOCK_DATA=true` in
> `backend\.env` before `reset-db`/`scrape` (see §5).

---

## 5. Run the scraper manually & manage data

```bash
cd backend

# Run one scrape now (cron-friendly, no server needed)
python -m app.cli scrape

# Scrape jobs from the last LOOKBACK_DAYS days (ServiceNow ecosystem expansion)
python -m app.cli scrape-recent

# Reset the database (DROP + recreate + reseed) — wipes old/irrelevant data
python -m app.cli reset-db

# Dry-run diagnostics: per-source and per-query funnels (nothing saved)
python -m app.cli diagnose-sources
python -m app.cli diagnose-queries

# Print job categories (+ enabled state) and all category keywords
python -m app.cli list-categories
python -m app.cli list-keywords

# Print every ServiceNow module group + the generated query set
python -m app.cli list-modules

# List all 48 registered sources with enabled/status/method
python -m app.cli list-sources

# Test a single source adapter (fetch + display raw results)
python -m app.cli test-source <source_name>

# Test company career discovery across ATS platforms
python -m app.cli test-company-careers

# Remove already-stored jobs that fail the strict filter (cleanup without reset)
python -m app.cli clean-irrelevant

# Print the source compliance report
python -m app.cli sources
```

API alternatives:

```bash
curl -X POST http://localhost:8000/api/scraper/run             # background
curl -X POST "http://localhost:8000/api/scraper/run?wait=true" # sync, returns totals
```

Or click **"Refresh Jobs"** in the website header (runs synchronously and
refreshes the list/stats; shows a clear message if zero relevant jobs were found).

### Seeing the UI with sample data (development)

The live compliant APIs frequently have **no** genuine ServiceNow remote-US
listings, so a real scrape may correctly store 0 jobs. To preview the full UI
with realistic sample data, enable the **development-only** mock source
(disabled by default, never used in production):

```bash
# backend/.env
ENABLE_MOCK_DATA=true
```

```bash
python -m app.cli reset-db
python -m app.cli scrape       # adds 3 sample ServiceNow remote-US jobs
```

Set it back to `false` for real data only.

---

## 5b. Diagnosing "why are there 0 jobs?"

The scraper never fails silently. Every run records a **per-source funnel** so you
can see exactly what happened:

```
source            raw  SvcNow  remote   US  saved  status       error/reason
Himalayas           2       2       2    1      1  success
Lever              10       2       5    3      1  success
Arbeitnow           2       2       1    0      0  error        HTTP 429 Too Many Requests
Remotive           34       0      34    5      0  no_results
Built In            0       0       0    0      0  blocked      HTTP 403 (anti-bot)
Hiring Cafe         0       0       0    0      0  blocked      HTTP 405 (no public API)
Jobright            0       0       0    0      0  skipped      disabled (ENABLE_JOBRIGHT=false)
Indeed/Glassdoor…   0       0       0    0      0  blocked      TOS / partner API only
```

- **CLI:** `python -m app.cli diagnose-sources` (dry run — fetches & classifies,
  saves nothing, prints the table above).
- **API:** `GET /api/scraper/diagnostics` returns the same data as JSON
  (per-source raw / ServiceNow / remote / US / saved counts, rejection reasons,
  `sample_titles`, `sample_rejections`, `near_matches`, `last_error`, `status`).
- **UI:** the **Source Diagnostics** tab shows a card per source.

Reading it:
- `raw > 0` but `saved = 0` → jobs were fetched but rejected; the `rejected_*`
  counts and `sample_rejections` show why (not ServiceNow / not remote / not US).
- `status = blocked / error` → the exact HTTP status / reason is in `last_error`.
- `near_matches` (when `DEBUG_SHOW_NEAR_MATCHES=true`) lists ServiceNow jobs that
  *just* missed on remote/US — diagnostics only, **never saved**.

Two filter knobs help tune results without ever saving fake jobs:
- `ALLOW_REMOTE_WORLDWIDE_IF_US_NOT_EXCLUDED` (default `false`) — when `true`, a
  ServiceNow remote job whose location is "worldwide/anywhere" (and names no
  non-US-only country) is treated as US-eligible.
- `DEBUG_SHOW_NEAR_MATCHES` (default `true`) — surface near-matches in diagnostics.

### Getting real jobs: configure ATS boards

The highest-quality ServiceNow source is **company ATS boards** (no API key).
`.env` ships with a working example (`LEVER_COMPANIES=cprime`, which currently
posts a real remote-US ServiceNow role). Add ServiceNow partner/consulting firms:

```env
GREENHOUSE_BOARDS=board1,board2
LEVER_COMPANIES=cprime,company2
ASHBY_BOARDS=org1
```

---

## 6. How scheduling works

When `ENABLE_SCHEDULER=true`, the API process starts an in-process **APScheduler**
job that runs the scraper every `SCRAPER_INTERVAL_HOURS` hours (default **4**,
recommended 3–6). Each run is recorded in the `scraper_runs` table.

For serverless/cron deployments, set `ENABLE_SCHEDULER=false` and schedule the
CLI instead:

```cron
# Every 4 hours
0 */4 * * *  cd /app/backend && /app/backend/.venv/bin/python -m app.cli scrape
```

---

## 7. How to add new keywords

Edit `DEFAULT_KEYWORDS` in `backend/.env` (comma-separated) and restart:

```env
DEFAULT_KEYWORDS=ServiceNow Developer,ServiceNow Admin,Salesforce Developer,DevOps Engineer
```

Keywords are also seeded into a `keywords` table; the scraper uses active DB
keywords if present, otherwise the env defaults. Nothing is hardcoded to ServiceNow.

> Keywords only decide *what to search for*. They do **not** decide what gets
> saved — that is the strict relevance filter below. Searching "ServiceNow
> Developer" will not save a generic developer job.

## 7b. Configuring the strict filter

All in `backend/.env` (see `.env.example`):

| Variable | Default | Meaning |
|----------|---------|---------|
| `REQUIRED_MATCH_TERM` | `servicenow` | Term a job's text must contain to be saved. `"Service Now"`, `"service-now"` are all normalized to `servicenow`. Change it to target another technology. |
| `REMOTE_ONLY` | `true` | When true, only clearly-remote jobs pass. Set `false` to allow any work mode. |
| `TARGET_COUNTRY` | `US` | `US` enables US-only matching. Set to `""` or `ANY` to disable country filtering. |
| `TARGET_LOCATIONS` | `United States,USA,US,U.S.,Remote US,Remote United States` | Extra phrases accepted as a US match. |
| `ENABLE_MOCK_DATA` | `false` | Dev-only sample data. Must stay `false` in production. |

**How it works (`backend/app/scraper/relevance.py`):** each raw job's text
(title, company, location, descriptions, tags, category,
`candidate_required_location`, source metadata — but **not** the search keyword)
is normalized (lowercased, whitespace-collapsed, `service now → servicenow`) and
run through `is_servicenow_job`, `is_remote_job`, and `is_us_job`. `is_allowed_job`
returns `(allowed, reasons)`; only `allowed` jobs proceed to dedupe and storage.
The same three flags are stored on each row and re-enforced at query time in
`/api/jobs`, `/api/jobs/today`, and `/api/stats`, so the API can never return
irrelevant jobs even if asked to.

---

## 8. How to add new job boards / sources

1. Create `backend/app/scraper/sources/source_xxx.py` subclassing `BaseSource`.
2. **Verify robots.txt + Terms of Service first; prefer an official API.**
3. Set the compliance metadata (`status`, `uses_api`, `robots_checked`,
   `tos_checked`, `reason_if_skipped`).
4. Implement `fetch(keyword) -> list[RawJob]`.
5. Register it in `backend/app/scraper/sources/__init__.py`.
6. Restart — `sync_sources()` updates the DB and `/api/sources` automatically.
7. Update [`SOURCES_REPORT.md`](./SOURCES_REPORT.md).
8. Run `python -m app.cli test-source <name>` to verify the adapter works.

Restricted sources (no API / scraping forbidden) should be added as a stub with
`status="blocked"` / `"needs_api_key"` and a clear reason — never enabled on a guess.

### Adding company ATS boards (no API key — best for ServiceNow)

The **Greenhouse / Lever / Ashby / Workday / SmartRecruiters / Recruitee /
Teamtailor** adapters pull jobs straight from employer career boards with no key.
Just list company/board tokens in `backend/.env`:

```env
# Original ATS adapters
GREENHOUSE_BOARDS=gitlab,thirdera      # boards.greenhouse.io/<token>
LEVER_COMPANIES=leverdemo              # jobs.lever.co/<token>
ASHBY_BOARDS=ramp                      # jobs.ashbyhq.com/<token>

# New ATS adapters (added June 2026)
WORKDAY_COMPANIES=salesforce,adobe     # <company>.wd5.myworkdayjobs.com
SMARTRECRUITERS_COMPANIES=visa,sap     # api.smartrecruiters.com/v1/companies/<id>
RECRUITEE_COMPANIES=example            # <company>.recruitee.com/api/offers/
TEAMTAILOR_COMPANIES=example           # <company>.teamtailor.com careers page
```

### Company Careers orchestrator

The `company_careers` adapter tries **multiple ATS platforms** for each company
name in `COMPANY_CAREER_TARGETS`. It automatically discovers whether a company
uses Greenhouse, Lever, or Ashby and fetches their public job listings:

```env
COMPANY_CAREER_TARGETS=stripe,gitlab,datadog,cloudflare,hashicorp
```

Test with: `python -m app.cli test-company-careers`

Add the tokens of **ServiceNow partner/consulting firms** (the employers who
actually hire ServiceNow people) to get genuine, compliant ServiceNow roles.
Empty lists are a safe no-op. Toggle the whole group with `ENABLE_COMPANY_ATS`.

> **Built In** and **Hiring Cafe** were investigated and are currently **blocked /
> needs-review** for compliance (HTTP 403 + disallowed search paths / no public
> API). Their `ENABLE_*` flags exist but a code-level compliance gate keeps them
> skipped until a compliant access path is implemented. See `SOURCES_REPORT.md`.

---

## 9. How deduplication works

Each job gets a canonical `dedupe_key` (a hash). Strategy, in priority order:

1. **Exact original apply URL** — normalized: lowercased host, trailing slash and
   tracking params (`utm_*`, `ref`, `src`, …) stripped, so slightly different
   URLs for the same job collapse.
2. **Fallback fingerprint** — `title + company_name + location`, lowercased,
   trimmed, punctuation removed.

The `dedupe_key` has a UNIQUE constraint. Duplicates are caught both **within a
run** (in-memory set) and **across runs** (DB lookup). When a duplicate is seen,
the existing job is refreshed (description/salary/posted-today) rather than
re-inserted — so the same job on multiple boards or runs stores **one** copy.

---

## 10. How "Posted Today" detection works

1. The scraper reads each source's raw posting date (`"Today"`, `"3 days ago"`,
   a unix timestamp, or an ISO date).
2. `date_utils.parse_date()` normalizes it to a timezone-aware datetime in
   `APP_TIMEZONE` (`normalized_date_posted`).
3. `is_posted_today` is set true when that date falls on the **current local
   calendar day**. Flags for all jobs are refreshed at the end of every run so
   they roll over correctly at midnight.
4. The website surfaces this as a green **Posted Today** badge, a dedicated
   **Posted Today** tab, and a "Today" date filter. Posted-today jobs always sort
   to the top.

---

## 11. How to deploy the backend

Target: **Render / Railway / Fly.io** + a managed PostgreSQL.

1. Provision a cloud PostgreSQL and set `DATABASE_URL` (use the
   `postgresql+psycopg2://…` form).
2. Set env vars: `DEFAULT_KEYWORDS`, `SCRAPER_INTERVAL_HOURS`, `APP_TIMEZONE`,
   `ENABLE_SCHEDULER`, `CORS_ORIGINS` (your frontend URL).
3. Start command:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
4. Tables auto-create on startup. To run the scraper as an external cron instead
   of in-process, set `ENABLE_SCHEDULER=false` and schedule `python -m app.cli scrape`.

---

## 12. How to deploy the frontend

Target: **Vercel** (or Netlify / any static host).

1. Project root: `frontend/`. Build command `npm run build`, output `dist/`.
2. Set `VITE_API_BASE_URL` to your deployed backend URL.
3. Add the frontend's URL to the backend's `CORS_ORIGINS`.

---

## 13. Known limitations

- Many of the 48 registered sources are broad **remote-focused** aggregators
  whose search endpoints often return loosely-related jobs. The strict filter
  discards everything that doesn't match an enabled category + remote + US,
  so on many days a real scrape may legitimately store **fewer jobs than raw
  results**. This is intended — see `ENABLE_MOCK_DATA` (§5) to preview the UI
  with sample data during development.
- Several best-effort sources (Remote4Me, Pangian, Outsourcely, etc.) may
  return 0 jobs if their sites block automated access — this is handled
  gracefully and reported in diagnostics.
- The big-name boards (LinkedIn, Indeed, Glassdoor, Naukri) are **not scraped**
  for compliance reasons — they require partner/official API access (see report).
- Source date formats vary; unparseable dates leave `normalized_date_posted`
  null (such jobs sort last and aren't counted as "today").
- In-process scheduler runs only while the API process is alive — use cron for
  serverless hosts.
- Out of scope for this phase: auth, applying through our site, payments, mobile
  app, email/SMS alerts (code is structured so these can be added later).

---

## 14. Sources included and skipped

**48 total sources** — run `python -m app.cli list-sources` for the live list.

| Tier | Sources |
|------|---------|
| **Active API/feed** | RemoteOK, Remotive, Arbeitnow, Himalayas, We Work Remotely, Working Nomads, Jobspresso, Remote.co, NoDesk, SkipTheDrive, Hubstaff Talent, Europe Remotely |
| **ATS adapters** (no key) | Greenhouse, Lever, Ashby, Workday, SmartRecruiters, Recruitee, Teamtailor |
| **Company Careers** | Multi-ATS discovery for configured company names |
| **Best-effort** | Waw Asia, Remote4Me, Pangian, Remotees, Outsourcely, Remote Freelance |
| **Keyed sources** | Adzuna, USAJOBS, The Muse, Jooble (require API keys) |
| **Blocked/skipped** | LinkedIn, Indeed, SimplyHired, Glassdoor, ZipRecruiter, FlexJobs, Toptal, Virtual Vocations, Stack Overflow Jobs (discontinued), RemoteHabits, Wellfound, Upwork, Freelancer, Built In, Hiring Cafe, Jobright, and more |

Full reasoning, official-API status, and PM notes: [`SOURCES_REPORT.md`](./SOURCES_REPORT.md).

---

## 2-Week Delivery Timeline

**Day 1–2 — Setup & design**
- Confirm job boards / compliance approach
- Set up monorepo (backend + frontend)
- Design database schema (jobs, scraper_runs, sources, keywords)
- Finalize stack (FastAPI + React/Tailwind + Postgres/SQLite)

**Day 3–5 — Scraper core**
- Working scraper for 2–3 compliant sources
- Capture all required fields
- Posting-date extraction & relative-date normalization

**Day 6–7 — Storage & deduplication**
- Save jobs to DB
- URL + title/company/location deduplication
- Tag "Posted Today"
- Add scheduling (every 4 hours)

**Day 8–10 — Website**
- Job list page, search, filters
- Posted Today view, apply links
- Responsive design, loading & empty states

**Day 11–12 — Connect & test**
- Wire website to live API data
- Add more sources where compliant
- Bug fixing & error handling hardening

**Day 13–14 — Polish & deliver**
- Final testing
- Deployment prep (Vercel + Render/Railway/Fly + cloud Postgres)
- README & handover

---

## API reference (quick)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET  | `/api/jobs` | List jobs — `q, keyword, location, date_filter, source, remote_type, sort, page, limit` |
| GET  | `/api/jobs/today` | Only jobs posted today |
| GET  | `/api/jobs/{id}` | Full job detail |
| POST | `/api/scraper/run` | Trigger a scrape (`?wait=true` for sync) |
| GET  | `/api/scraper/runs` | Scraper run history |
| GET  | `/api/sources` | Included & skipped sources with reasons |
| GET  | `/api/stats` | Dashboard stats (totals, top companies/locations, source/keyword breakdown) |
