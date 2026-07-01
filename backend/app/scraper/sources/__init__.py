"""Source adapter registry.

Add a new source by importing its adapter class and appending an instance to
``ALL_SOURCES``. The engine only runs adapters whose ``status == 'active'``.

Active by default (compliant public APIs / feeds):
    RemoteOK, Remotive, Arbeitnow, Himalayas, Greenhouse, Lever, Ashby,
    WeWorkRemotely, WorkingNomads, Jobspresso, Remote.co, NoDesk,
    SkipTheDrive, HubstaffTalent, EuropeRemotely, WawAsia, Remote4Me,
    Pangian, Remotees, Outsourcely, RemoteFreelance, CompanyCareers,
    SmartRecruiters, Workday, Recruitee, Teamtailor

Dev-only (off unless ENABLE_MOCK_DATA=true):
    MockDev

Blocked / needs review (never queried, shown in the report with reasons):
    LinkedIn, Indeed, SimplyHired, Glassdoor, ZipRecruiter, FlexJobs,
    Toptal, VirtualVocations, StackOverflowJobs, RemoteHabits, Wellfound,
    Upwork, Freelancer, RemoteRocketship, RemoteOfAsia, RemoteOKEurope,
    Built In, Hiring Cafe, Jobright
"""
from __future__ import annotations

from typing import List

from app.scraper.sources.base import BaseSource
from app.scraper.sources.source_one import RemoteOKSource
from app.scraper.sources.source_two import RemotiveSource
from app.scraper.sources.source_three import ArbeitnowSource
from app.scraper.sources.himalayas import HimalayasSource
from app.scraper.sources.company_ats import (
    AshbySource,
    GreenhouseSource,
    LeverSource,
)
from app.scraper.sources.source_mock import MockDevSource
from app.scraper.sources.builtin import BuiltInSource
from app.scraper.sources.hiringcafe import HiringCafeSource
from app.scraper.sources.jobright import JobrightSource
from app.scraper.sources.keyed_sources import ALL_KEYED
from app.scraper.sources.blocked_sources import ALL_BLOCKED

# --- New source adapters ---
from app.scraper.sources.weworkremotely import WeWorkRemotelySource
from app.scraper.sources.workingnomads import WorkingNomadsSource
from app.scraper.sources.jobspresso import JobspressoSource
from app.scraper.sources.remote_co import RemoteCoSource
from app.scraper.sources.nodesk import NoDeskSource
from app.scraper.sources.skipthedrive import SkipTheDriveSource
from app.scraper.sources.hubstaff_talent import HubstaffTalentSource
from app.scraper.sources.europeremotely import EuropeRemotelySource
from app.scraper.sources.waw_asia import WawAsiaSource
from app.scraper.sources.remote4me import Remote4MeSource
from app.scraper.sources.pangian import PangianSource
from app.scraper.sources.remotees import RemoteesSource
from app.scraper.sources.outsourcely import OutsourcelySource
from app.scraper.sources.remotefreelance import RemoteFreelanceSource
from app.scraper.sources.company_careers import CompanyCareersSource

# --- Additional ATS adapters ---
from app.scraper.sources.ats_smartrecruiters import SmartRecruitersSource
from app.scraper.sources.ats_workday import WorkdaySource
from app.scraper.sources.ats_recruitee import RecruiteeSource
from app.scraper.sources.ats_teamtailor import TeamtailorSource

ALL_SOURCES: List[BaseSource] = [
    # --- Active compliant public APIs ---
    RemoteOKSource(),
    RemotiveSource(),
    ArbeitnowSource(),
    HimalayasSource(),
    GreenhouseSource(),
    LeverSource(),
    AshbySource(),
    # --- New active job board sources ---
    WeWorkRemotelySource(),
    WorkingNomadsSource(),
    JobspressoSource(),
    RemoteCoSource(),
    NoDeskSource(),
    SkipTheDriveSource(),
    HubstaffTalentSource(),
    EuropeRemotelySource(),
    WawAsiaSource(),
    Remote4MeSource(),
    PangianSource(),
    RemoteesSource(),
    OutsourcelySource(),
    RemoteFreelanceSource(),
    CompanyCareersSource(),
    # --- Additional ATS adapters ---
    SmartRecruitersSource(),
    WorkdaySource(),
    RecruiteeSource(),
    TeamtailorSource(),
    # --- Key-gated API sources (active only when enabled + key present) ---
    *ALL_KEYED,
    # --- Development-only sample data (active only when ENABLE_MOCK_DATA=true) ---
    MockDevSource(),
    # --- Best-effort attempts; report blocked/skipped in diagnostics ---
    BuiltInSource(),
    HiringCafeSource(),
    JobrightSource(),
    # --- Policy-blocked (never queried) ---
    *ALL_BLOCKED,
]


def active_sources() -> List[BaseSource]:
    return [s for s in ALL_SOURCES if s.status == "active"]
