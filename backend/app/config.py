"""Application configuration.

All settings are loaded from environment variables (and an optional .env file).
Keywords and the scraper interval are configurable here so that tracking new
roles never requires a code change.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite:///./job_aggregator.db"

    # Scraper / scheduler
    scraper_interval_hours: int = 4
    enable_scheduler: bool = True
    request_delay_seconds: float = 1.5
    request_timeout_seconds: float = 20.0

    # Keywords are stored as a comma separated string and parsed into a list.
    # Expanded query set to maximise real ServiceNow coverage.
    default_keywords: str = (
        "ServiceNow,ServiceNow Developer,ServiceNow Administrator,"
        "ServiceNow Consultant,ServiceNow Architect,ServiceNow Engineer,"
        "ServiceNow Platform Engineer,ServiceNow ITSM,ServiceNow CMDB,"
        "ServiceNow HRSD,ServiceNow CSM,ServiceNow Discovery,ServiceNow SecOps,"
        "ServiceNow Business Analyst,ServiceNow Integration Specialist,"
        "ServiceNow Technical Consultant,ServiceNow Solution Consultant,"
        "ServiceNow Implementation Specialist,ServiceNow Workflow,"
        "ServiceNow Platform Owner,ServiceNow App Engine"
    )

    # Timezone used for the "Posted Today" calculation.
    app_timezone: str = "America/New_York"

    # ----- TODAY-only / freshness window -----------------------------------
    today_only: bool = True
    min_target_today_jobs: int = 50
    # Freshness window in days (0 = strictly today). Accepts either env name;
    # LOOKBACK_DAYS (the documented name) wins over SCRAPER_LOOKBACK_DAYS.
    scraper_lookback_days: int = Field(
        default=10,
        validation_alias=AliasChoices("LOOKBACK_DAYS", "SCRAPER_LOOKBACK_DAYS"),
    )
    allow_unknown_date: bool = False
    allow_yesterday: bool = False
    allow_last_3_days: bool = False
    allow_old_jobs: bool = False
    max_pages_per_source: int = 10

    # ----- Target volume + query expansion ---------------------------------
    min_target_jobs: int = 50
    max_target_jobs: int = 100
    max_queries_per_source: int = 5
    enable_query_expansion: bool = True
    enable_module_search: bool = True
    enable_role_search: bool = True
    enable_technical_term_search: bool = True
    enable_stack_search: bool = True

    # ----- Multi-stack job mode (categories) -------------------------------
    # "multi_stack" = search all enabled categories; "servicenow" = legacy
    # ServiceNow-only behaviour.
    job_mode: str = "multi_stack"
    enabled_job_categories: str = (
        "servicenow,mern,mean,node_backend,php,laravel,react_frontend"
    )
    # Minimum relevance score for a job to be accepted (avoids false positives).
    min_relevance_score: int = 70
    # ServiceNow category keeps high precision: generic ITSM/CMDB/GRC without a
    # ServiceNow-specific term never qualifies as a ServiceNow job.
    servicenow_strict_mode: bool = True

    # ----- Strict relevance filtering (ServiceNow + Remote + US) -----------
    # A job MUST contain this term (after normalization) to be saved/shown.
    required_match_term: str = "servicenow"
    # Require the term in the ROLE signal (title/tags/category), not just an
    # incidental free-text mention (e.g. ServiceNow named as a past client, or
    # used as a tool). True = high precision ("real ServiceNow roles only").
    servicenow_require_in_title: bool = True
    # When true, only clearly-remote jobs are saved/shown.
    remote_only: bool = True
    # Target country for the location filter. "US" enables US-only matching.
    # Set to "" / "ANY" to disable country filtering.
    target_country: str = "US"
    # Extra location strings accepted as a US match (comma separated).
    target_locations: str = "United States,USA,US,U.S.,Remote US,Remote United States"
    # Accept Canadian remote roles in addition to US.
    allow_us_or_canada: bool = False
    # Development-only mock data. Disabled by default; never used in production.
    enable_mock_data: bool = False

    # ----- Per-source toggles ---------------------------------------------
    enable_remoteok: bool = True
    enable_remotive: bool = True
    enable_arbeitnow: bool = True
    enable_himalayas: bool = True
    enable_builtin: bool = True          # best-effort; reports blocked in diagnostics if 403
    enable_hiring_cafe: bool = True      # best-effort; reports blocked in diagnostics if no public API
    enable_company_ats: bool = True
    enable_jobright: bool = False
    enable_indeed: bool = False
    enable_simplyhired: bool = False
    enable_glassdoor: bool = False
    enable_ziprecruiter: bool = False

    # ----- New job board source toggles -----------------------------------
    enable_jobspresso: bool = True
    enable_virtual_vocations: bool = False
    enable_stackoverflow_jobs: bool = False
    enable_outsourcely: bool = True
    enable_toptal: bool = False
    enable_skipthedrive: bool = True
    enable_nodesk: bool = True
    enable_remotehabits: bool = False
    enable_remote4me: bool = True
    enable_pangian: bool = True
    enable_remotees: bool = True
    enable_europe_remotely: bool = True
    enable_remoteok_europe: bool = True
    enable_remote_of_asia: bool = False
    enable_flexjobs: bool = False
    enable_remote_co: bool = True
    enable_weworkremotely: bool = True
    enable_wellfound: bool = False
    enable_linkedin: bool = False
    enable_upwork: bool = False
    enable_freelancer: bool = False
    enable_working_nomads: bool = True
    enable_remote_freelance: bool = True
    enable_remote_rocketship: bool = False
    enable_waw_asia: bool = True
    enable_hubstaff_talent: bool = True
    enable_company_careers: bool = True

    # ----- Key-gated API sources (off unless enabled AND key present) ------
    enable_adzuna: bool = False
    enable_usajobs: bool = False
    enable_the_muse: bool = False
    enable_jooble: bool = False
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    usajobs_email: str = ""
    usajobs_api_key: str = ""
    the_muse_api_key: str = ""
    jooble_api_key: str = ""

    # ----- Company career / ATS configuration -----------------------------
    company_career_targets: str = (
        "Samsara,1Password,Grafana Labs,Humana,MongoDB,Wiz,Oscilar,Circle,"
        "Palo Alto Networks,Veeam Software,Lumenalta,Ruby Labs,Caylent,Yuno,"
        "micro1,Hostinger,Kraken,Scopely,LaunchDarkly,Fleetio,Trafilea,"
        "Absorb Software,GoGuardian,Polygon Labs,Workweek,Automattic,Deel"
    )
    workday_companies: str = ""
    smartrecruiters_companies: str = ""
    recruitee_companies: str = ""
    teamtailor_companies: str = ""
    comeet_companies: str = ""

    # ----- Debug / filter tuning ------------------------------------------
    # Show near-matches (ServiceNow jobs that failed remote/US) in diagnostics
    # only. Never saved as real jobs.
    debug_show_near_matches: bool = True
    # If a ServiceNow remote job's location is worldwide/anywhere (no US named)
    # AND no non-US-only country is named, treat it as US-eligible.
    allow_remote_worldwide_if_us_not_excluded: bool = False

    # ----- Company ATS boards (no API key needed) -------------------------
    # Comma-separated board/company tokens. Empty -> that platform is a no-op.
    greenhouse_boards: str = ""          # e.g. "gitlab,thirdera"
    lever_companies: str = ""            # e.g. "leverdemo"
    ashby_boards: str = ""               # e.g. "ramp"

    # CORS
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def date_window_days(self) -> int:
        """Freshness window (in days) for the date gate.

        0  = strictly today.
        N  = today plus the previous N days (e.g. 7 -> "posted in the last 7 days").

        ``today_only`` forces a strict today gate (0). Otherwise the window is
        ``scraper_lookback_days`` (env: LOOKBACK_DAYS / SCRAPER_LOOKBACK_DAYS).
        Both the save-time filter (relevance) and the query-time filter
        (jobs/stats) read this single source of truth.
        """
        if self.today_only:
            return 0
        return max(0, self.scraper_lookback_days)

    @property
    def date_filter_active(self) -> bool:
        """True when any date gate applies (strict today OR a positive lookback)."""
        return self.today_only or self.scraper_lookback_days > 0

    @property
    def keywords(self) -> List[str]:
        """Configured keyword list (de-duplicated, trimmed, order preserved)."""
        seen = set()
        result: List[str] = []
        for raw in self.default_keywords.split(","):
            kw = raw.strip()
            if kw and kw.lower() not in seen:
                seen.add(kw.lower())
                result.append(kw)
        return result

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def target_location_list(self) -> List[str]:
        return [loc.strip() for loc in self.target_locations.split(",") if loc.strip()]

    @property
    def country_filter_enabled(self) -> bool:
        return self.target_country.strip().upper() not in ("", "ANY", "GLOBAL", "WORLDWIDE")

    @staticmethod
    def _csv(value: str) -> List[str]:
        return [v.strip() for v in value.split(",") if v.strip()]

    @property
    def enabled_category_list(self) -> List[str]:
        """Enabled job-category ids (lowercased, order preserved)."""
        return [c.lower() for c in self._csv(self.enabled_job_categories)]

    @property
    def multi_stack_mode(self) -> bool:
        return self.job_mode.strip().lower() == "multi_stack"

    @property
    def greenhouse_board_list(self) -> List[str]:
        return self._csv(self.greenhouse_boards)

    @property
    def lever_company_list(self) -> List[str]:
        return self._csv(self.lever_companies)

    @property
    def ashby_board_list(self) -> List[str]:
        return self._csv(self.ashby_boards)

    @property
    def company_career_target_list(self) -> List[str]:
        return self._csv(self.company_career_targets)

    @property
    def workday_company_list(self) -> List[str]:
        return self._csv(self.workday_companies)

    @property
    def smartrecruiters_company_list(self) -> List[str]:
        return self._csv(self.smartrecruiters_companies)

    @property
    def recruitee_company_list(self) -> List[str]:
        return self._csv(self.recruitee_companies)

    @property
    def teamtailor_company_list(self) -> List[str]:
        return self._csv(self.teamtailor_companies)

    @property
    def comeet_company_list(self) -> List[str]:
        return self._csv(self.comeet_companies)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
