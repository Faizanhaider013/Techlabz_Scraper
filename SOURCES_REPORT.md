# Sources Report

Complete inventory of all job sources integrated (or evaluated) by the scraper.
Each source is documented with its access method, compliance status, and implementation state.

## Source Summary Table

| Source | Domain | Status | Method | Requires Key? | Requires Login? | Implemented? | Risk Level | Notes |
|--------|--------|--------|--------|---------------|-----------------|--------------|------------|-------|
| RemoteOK | remoteok.com | ✅ Active | Public JSON API | No | No | Yes | Low | Full feed, client-side filter |
| Remotive | remotive.com | ✅ Active | Public REST API | No | No | Yes | Low | Server-side search, `?search=` param |
| Arbeitnow | arbeitnow.com | ✅ Active | Public JSON API | No | No | Yes | Low | Paginated feed, keyword filter |
| Himalayas | himalayas.app | ✅ Active | Public JSON API | No | No | Yes | Low | Remote-only board, paginated |
| Greenhouse | greenhouse.io | ✅ Active | Public Board API | No | No | Yes | Low | Per-board JSON, configured via env |
| Lever | lever.co | ✅ Active | Public Postings API | No | No | Yes | Low | Per-company JSON, configured via env |
| Ashby | ashbyhq.com | ✅ Active | Public Board API | No | No | Yes | Low | Per-org JSON, configured via env |
| We Work Remotely | weworkremotely.com | ✅ Active | Public RSS feed | No | No | Yes | Low | Multiple category feeds |
| Working Nomads | workingnomads.com | ✅ Active | Public JSON API | No | No | Yes | Low | `/api/exposed_jobs/` endpoint |
| Jobspresso | jobspresso.co | ✅ Active | Public RSS feed | No | No | Yes | Low | RSS feed at `/feed/` |
| Remote.co | remote.co | ✅ Active | Public RSS feed | No | No | Yes | Low | Developer category RSS |
| NoDesk | nodesk.co | ✅ Active | Public RSS feed | No | No | Yes | Low | Remote jobs RSS feed |
| SkipTheDrive | skipthedrive.com | ✅ Active | Public RSS feed | No | No | Yes | Low | RSS feed at `/feed/` |
| Hubstaff Talent | talent.hubstaff.com | ✅ Active | Public JSON API | No | No | Yes | Low | `/api/v1/jobs` endpoint |
| Europe Remotely | europeremotely.com | ✅ Active | Public RSS feed | No | No | Yes | Low | Europe-focused; US filter applies |
| Waw Asia | waw.asia | ✅ Active | Public RSS feed | No | No | Yes | Low | Asia-focused; US filter applies |
| Remote4Me | remote4me.com | ✅ Active | Public RSS feed | No | No | Yes | Medium | Aggregator, may block |
| Pangian | pangian.com | ✅ Active | Public RSS feed | No | No | Yes | Medium | May require login for some |
| Remotees | remotees.com | ✅ Active | Public RSS feed | No | No | Yes | Medium | Small board |
| Outsourcely | outsourcely.com | ✅ Active | Public RSS feed | No | Partial | Yes | Medium | May need login for full data |
| Remote Freelance | remotefreelance.com | ✅ Active | Public RSS feed | No | No | Yes | Medium | Small freelance board |
| Company Careers | Multi-ATS | ✅ Active | GH/Lever/Ashby APIs | No | No | Yes | Low | Tries 27 companies |
| SmartRecruiters | smartrecruiters.com | ✅ Active | Public JSON API | No | No | Yes | Low | Needs company tokens |
| Workday | myworkdayjobs.com | ✅ Active | Public JSON API | No | No | Yes | Medium | Auto-discovers tenant URLs |
| Recruitee | recruitee.com | ✅ Active | Public JSON API | No | No | Yes | Low | Needs company subdomains |
| Teamtailor | teamtailor.com | ✅ Active | Public JSON API | No | No | Yes | Low | Needs company subdomains |
| Adzuna | adzuna.com | 🔑 Needs Key | REST API | Yes | No | Yes | Low | ENABLE_ADZUNA + keys |
| USAJOBS | usajobs.gov | 🔑 Needs Key | REST API | Yes | No | Yes | Low | ENABLE_USAJOBS + keys |
| The Muse | themuse.com | 🔑 Needs Key | REST API | Yes | No | Yes | Low | ENABLE_THE_MUSE + key |
| Jooble | jooble.org | 🔑 Needs Key | REST API | Yes | No | Yes | Low | ENABLE_JOOBLE + key |
| Built In | builtin.com | ⚠️ Blocked | HTML scraping | No | No | Best-effort | High | 403 anti-bot, JS-rendered |
| Hiring Cafe | hiringcafe.com | ⚠️ Blocked | HTML scraping | No | No | Best-effort | High | No public API |
| Jobright | jobright.ai | ⚠️ Blocked | HTML scraping | No | No | Best-effort | High | Anti-bot protections |
| LinkedIn | linkedin.com | 🚫 Blocked | N/A | N/A | Yes | Stub | Critical | TOS prohibits scraping |
| Indeed | indeed.com | 🚫 Blocked | N/A | N/A | No | Stub | Critical | Publisher API retired |
| SimplyHired | simplyhired.com | 🚫 Blocked | N/A | N/A | No | Stub | Critical | Indeed network, blocked |
| Glassdoor | glassdoor.com | 🚫 Blocked | N/A | N/A | Yes | Stub | Critical | Partner-gated API |
| ZipRecruiter | ziprecruiter.com | 🚫 Blocked | N/A | N/A | No | Stub | Critical | TOS restricts crawling |
| FlexJobs | flexjobs.com | 🚫 Blocked | N/A | N/A | Yes (paid) | Stub | Critical | Paywalled membership |
| Toptal | toptal.com | ⏭️ Skipped | N/A | N/A | N/A | Stub | N/A | Talent marketplace, not job board |
| Virtual Vocations | virtualvocations.com | ⏭️ Skipped | N/A | N/A | Yes (paid) | Stub | N/A | Paywalled membership |
| Stack Overflow Jobs | stackoverflow.com | ⏭️ Skipped | N/A | N/A | N/A | Stub | N/A | Discontinued in 2022 |
| RemoteHabits | remotehabits.com | ⏭️ Skipped | N/A | N/A | N/A | Stub | N/A | Content site, no job board |
| Wellfound | wellfound.com | 🚫 Blocked | N/A | N/A | Yes | Stub | High | Login + anti-bot required |
| Upwork | upwork.com | 🚫 Blocked | N/A | N/A | Yes | Stub | Critical | Gated marketplace |
| Freelancer | freelancer.com | 🚫 Blocked | N/A | N/A | Yes | Stub | Critical | Gated marketplace |
| Remote Rocketship | remoterocketship.com | ⏭️ Skipped | N/A | N/A | N/A | Stub | N/A | No verified public source |
| Remote of Asia | N/A | ⏭️ Skipped | N/A | N/A | N/A | Stub | N/A | No verified source |
| RemoteOK Europe | remoteok.com | ⏭️ Skipped | N/A | N/A | N/A | Stub | N/A | Handled by RemoteOK adapter |

## Source Status Legend

| Status | Meaning |
|--------|---------|
| ✅ Active | Source is queried during scraper runs |
| 🔑 Needs Key | Source requires API key(s) to activate |
| ⚠️ Blocked | Best-effort attempt made; blocked by anti-bot/403 |
| 🚫 Blocked | Compliance-blocked; never queried |
| ⏭️ Skipped | Source is not viable (discontinued, no job board, etc.) |

## Company Career Targets

The **CompanyCareers** source attempts to discover job listings for each configured
company by trying common ATS platforms (Greenhouse, Lever, Ashby).

### Configured Companies (via `COMPANY_CAREER_TARGETS`)

Samsara, 1Password, Grafana Labs, Humana, MongoDB, Wiz, Oscilar, Circle,
Palo Alto Networks, Veeam Software, Lumenalta, Ruby Labs, Caylent, Yuno,
micro1, Hostinger, Kraken, Scopely, LaunchDarkly, Fleetio, Trafilea,
Absorb Software, GoGuardian, Polygon Labs, Workweek, Automattic, Deel

### ATS Platforms Supported

| ATS | API Endpoint | Public? | Notes |
|-----|-------------|---------|-------|
| Greenhouse | `boards-api.greenhouse.io/v1/boards/{slug}/jobs` | Yes | Most common |
| Lever | `api.lever.co/v0/postings/{slug}` | Yes | Common for startups |
| Ashby | `api.ashbyhq.com/posting-api/job-board/{slug}` | Yes | Growing adoption |
| Workday | `{company}.wd*.myworkdayjobs.com/wday/cxs/{company}/External/jobs` | Yes | Enterprise ATS |
| SmartRecruiters | `api.smartrecruiters.com/v1/companies/{id}/postings` | Yes | Mid-market ATS |
| Recruitee | `{company}.recruitee.com/api/offers/` | Yes | EU-popular ATS |
| Teamtailor | `{company}.teamtailor.com/jobs.json` | Yes | Modern ATS |
| Comeet | — | TBD | Not yet implemented |

## Compliance Notes

1. **No login bypass**: Sources requiring authentication are marked as blocked stubs.
2. **No CAPTCHA solving**: Anti-bot protections are respected; blocked sources report the reason.
3. **No stealth browsers**: Only standard HTTP clients (httpx) with polite User-Agent.
4. **Rate limiting**: 1.5s delay between requests to any single source.
5. **robots.txt respected**: All active sources have been checked for robots.txt compliance.
6. **Public APIs only**: We use only officially provided or obviously public endpoints.

## How to Add a New Source

1. Create a new file in `backend/app/scraper/sources/` extending `BaseSource`.
2. Implement the `fetch(keyword: str) -> List[RawJob]` method.
3. Add a config toggle `enable_<source>: bool` in `config.py`.
4. Import and instantiate in `backend/app/scraper/sources/__init__.py`.
5. Add to `.env.example`.
6. Update this report.
7. Test with `python -m app.cli test-source <name>`.
