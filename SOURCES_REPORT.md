# Sources Compliance Report

This report documents every job source the system is aware of, whether it is
**included** (actively scraped) or **skipped/blocked**, and the compliance
reasoning behind each decision. It is generated from the same adapter metadata
that powers the `GET /api/sources` endpoint, so the API and this document never
drift apart.

> **Responsible scraping policy** (enforced in code):
> 1. Prefer official APIs over HTML scraping.
> 2. Check robots.txt and Terms of Service before enabling a source.
> 3. Never scrape a source that forbids it — mark it skipped with a reason instead.
> 4. Apply polite delays / rate limiting between requests (`REQUEST_DELAY_SECONDS`).
> 5. Store only the minimum job fields needed.
> 6. Always link back to the original posting (`original_apply_url`).
> 7. Never proceed silently on an uncertain source — record a blocker note here.

---

## ✅ Included sources (active)

| Source | Type | Official API? | robots/TOS reviewed | Supports remote? | Supports US location filter? | Notes |
|--------|------|---------------|---------------------|------------------|------------------------------|-------|
| **RemoteOK** | Public JSON API | Yes — `https://remoteok.com/api` | Yes | Yes (remote-only board) | Partial — `location` field varies; backend US filter applied | Public machine-readable feed. Filtered by keyword client-side, request delay applied, links back to each job's URL. |
| **Remotive** | Public REST API | Yes — `https://remotive.com/api/remote-jobs` | Yes | Yes (remote-only board) | Yes — `candidate_required_location` mapped, backend US filter applied | Documented public API with a `search` param. No key. Attribution preserved. |
| **Arbeitnow** | Public Job Board API | Yes — `https://www.arbeitnow.com/api/job-board-api` | Yes | Yes — real `remote` flag mapped | Partial — `location` mapped, backend US filter applied | Free public API, no key. Pagination capped to ~3 pages/run for politeness. |
| **Himalayas** | Public Remote Jobs API | Yes — `https://himalayas.app/jobs/api` | Yes — robots.txt allows everything except `/apply` | Yes (remote-only board) | Yes — `locationRestrictions` mapped (e.g. ["United States"]) | Free public JSON feed, no key. Feed is keyword-independent, so we fetch the freshest ~300 listings once per run (cached) and filter locally. Toggle: `ENABLE_HIMALAYAS`. |
| **Greenhouse** | Public ATS board API | Yes — `https://boards-api.greenhouse.io/v1/boards/{board}/jobs` | Yes — public per-employer boards | Inferred from `location.name` text | Yes — backend US filter + US-state recognition | **No API key.** Per-employer boards configured via `GREENHOUSE_BOARDS`. Best source of genuine ServiceNow roles (add ServiceNow partner firms). |
| **Lever** | Public ATS board API | Yes — `https://api.lever.co/v0/postings/{company}?mode=json` | Yes — public per-employer boards | Yes — `workplaceType` mapped | Yes — `location`+`country` mapped, US-state recognition | **No API key.** Configured via `LEVER_COMPANIES`. |
| **Ashby** | Public ATS board API | Yes — `https://api.ashbyhq.com/posting-api/job-board/{org}` | Yes — public per-employer boards | Yes — `isRemote`/`workplaceType` mapped | Yes — `addressCountry` + secondary locations mapped | **No API key.** Configured via `ASHBY_BOARDS`. |
| **MockDev** *(dev only)* | Local mock | N/A | N/A | Yes | Yes | **Disabled by default.** Active only when `ENABLE_MOCK_DATA=true`. Provides 3 sample ServiceNow remote-US jobs so the pipeline/UI can be demonstrated. Never used in production. |

> **Company ATS boards (Greenhouse / Lever / Ashby)** are the highest-quality,
> fully-compliant way to collect real ServiceNow roles — they pull jobs directly
> from employers with **no API key**. Populate `GREENHOUSE_BOARDS` /
> `LEVER_COMPANIES` / `ASHBY_BOARDS` in `.env` with the board tokens of ServiceNow
> partner/consulting firms (e.g. found at `boards.greenhouse.io/<token>`,
> `jobs.lever.co/<token>`, `jobs.ashbyhq.com/<token>`). Empty lists are a safe no-op.

These sources prove the end-to-end pipeline (collect → normalize → **strict
filter** → dedupe → tag "posted today" → store → serve) using only officially
provided, key-free APIs.

> **Known limitation — broad APIs:** these boards' search endpoints return
> loosely-related remote jobs (e.g. searching "ServiceNow Developer" returns
> generic remote developers). The backend's **strict relevance filter removes all
> non-ServiceNow / non-remote / non-US jobs before saving**, so the stored data
> stays clean. On days with no genuine ServiceNow remote-US postings, a real
> scrape correctly stores 0 jobs rather than padding with irrelevant ones.

> **Keyword note:** the architecture is keyword/term-agnostic — change
> `REQUIRED_MATCH_TERM`, `TARGET_COUNTRY` and `DEFAULT_KEYWORDS` to target any
> role/country without code changes.

---

## ⛔ Skipped / blocked sources

Built In, Hiring Cafe and Jobright now make a **real best-effort public request**
on each run (no login, no stealth browser, no anti-bot bypass). When the data is
not publicly accessible they raise a descriptive error and the run reports them
as `blocked` with the exact HTTP status — visible in `GET /api/scraper/diagnostics`
and the **Source Diagnostics** UI tab. The remaining boards are policy-blocked
stubs (never queried) so they stay visible here with reasons.

| Source | Runtime status | How determined | Reason |
|--------|---------------|----------------|--------|
| **Built In** | `blocked` | **Live attempt** (httpx + BeautifulSoup) | Returns **HTTP 403** to automated clients; listings are JavaScript-rendered. robots.txt also disallows the keyword search path (`Disallow: /jobs*?search=`). Not bypassed per policy. **TODO (PM):** official feed / allowed structured endpoint. |
| **Hiring Cafe** | `blocked` | **Live attempt** (POST probe) | Public probe returns **HTTP 405**; no documented public API and robots.txt disallows the search mechanism (`Disallow: /*?searchState=*`). **TODO (PM):** confirm an official public/partner API. |
| **Jobright** | `skipped` (disabled) → `blocked` if enabled | **Live attempt when enabled** | SPA with no server-rendered jobs and no confirmed public API; data behind an account. `ENABLE_JOBRIGHT=false` by default. **TODO (PM):** confirm access. |
| **Indeed** | `blocked` | Policy review | Direct scraping skipped for compliance + blocking risk. Open Publisher API retired/approval-gated. **TODO (PM):** evaluate Publisher/Employer API. |
| **SimplyHired** | `blocked` | Policy review | Part of the Indeed network; scraping skipped for compliance/blocking risk. No approved public API. |
| **Glassdoor** | `blocked` | Policy review | Jobs/content restricted; scraping prohibited by TOS; API partner-gated. **TODO (PM):** evaluate partner program. |
| **ZipRecruiter** | `blocked` | Policy review | TOS restrict scraping/crawling. Partner/publisher API required. |
| **LinkedIn** | `blocked` | Policy review | TOS prohibit unauthorized scraping; no free public jobs API. Requires partner API. |

> **Why "0 jobs" can be correct:** active sources are checked every run and the
> per-source funnel (raw → ServiceNow → remote → US → saved) is recorded. If no
> job passes all three filters, the portal honestly shows 0 rather than padding
> with unrelated jobs — and the diagnostics prove the sources were attempted and
> show every rejection reason.

> **Compliance note:** the `ENABLE_BUILTIN` and `ENABLE_HIRING_CAFE` env flags
> exist for forward-compatibility, but a hard compliance gate in code keeps both
> sources skipped today regardless of the flag. They activate only after a
> compliant access path is implemented.

---

## How to add / activate a new source

1. Create `backend/app/scraper/sources/source_xxx.py` subclassing `BaseSource`.
2. Fill in the compliance metadata: `status`, `uses_api`, `robots_checked`,
   `tos_checked`, and `reason_if_skipped` (if not active).
3. **Verify robots.txt and Terms of Service first.** Prefer an official API.
4. Implement `fetch(keyword)` returning a list of `RawJob`.
5. Register the adapter in `backend/app/scraper/sources/__init__.py`.
6. Re-run the backend — `sync_sources()` updates the DB and `/api/sources`.
7. Update the tables above.

If you are ever unsure whether a source is allowed, set `status="needs_api_key"`
or `"blocked"` with a clear `reason_if_skipped` and add a **TODO (PM)** note here
— never enable it on a guess.

---

## Notes for the Project Manager

- The MVP ships with **3 fully compliant, key-free API sources**. This is enough
  to demonstrate every acceptance criterion end-to-end.
- The big-name boards (LinkedIn, Indeed, Glassdoor, Naukri) are **intentionally
  not scraped**. Each needs a business/legal decision (partner API, paid access)
  before integration. They are listed above as blockers, not silently dropped.
- For richer ServiceNow-specific volume, the cleanest next step is adding
  **company career-page adapters** (e.g. Greenhouse / Lever / Ashby public board
  APIs for specific employers), which are generally API-accessible and allowed.
