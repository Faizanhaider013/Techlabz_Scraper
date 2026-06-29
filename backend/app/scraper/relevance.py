"""Strict relevance filtering: ServiceNow + Remote + US.

The project targets ONLY remote, US-based ServiceNow jobs. Every job must pass
all three checks below before it is deduplicated, saved, or shown:

    1. is_servicenow_job  -> text must mention "servicenow" / "service now"
    2. is_remote_job      -> job must be clearly remote
    3. is_us_job          -> job must be US-based / open to US candidates

Crucially, a job is NEVER considered relevant just because the scraper loop is
running under a "ServiceNow Developer" keyword. The matched keyword is excluded
from the searchable text so a generic remote developer job cannot sneak in.
"""
from __future__ import annotations

import re
from typing import List, Tuple

from app.config import settings
from app.scraper import job_taxonomy as jtax
from app.scraper import servicenow_taxonomy as tax

# Fields searched for the ServiceNow term. Per spec the signal must come from the
# ROLE ("title, description, tags, category, or source text") -- the employer's
# company name is deliberately NOT a signal, so e.g. a Recruiter role at the
# company "ServiceNow" does not match unless the role itself is about ServiceNow.
# The scraper keyword is also excluded so the loop keyword cannot cause a match.
_SERVICENOW_FIELDS = (
    "title",
    "short_description",
    "full_description",
    "description",
    "tags",
    "category",
    "source_text",
)
# Role-level signal fields (no free-text description). Used in high-precision
# mode so incidental description mentions (past clients, tool usage) don't match.
_SERVICENOW_ROLE_FIELDS = (
    "title",
    "tags",
    "category",
    "source_text",
)

# Fields searched for remote signals.
_REMOTE_FIELDS = (
    "title",
    "location",
    "short_description",
    "full_description",
    "description",
    "job_type",
    "remote_type",
    "workplace_type",
    "candidate_required_location",
    "tags",
)

# Fields searched for the US/location signal. We deliberately avoid the long
# description here so phrases like "join us" cannot be mistaken for "US".
_US_FIELDS = (
    "location",
    "candidate_required_location",
    "remote_type",
    "title",
    "region",
    "country",
)

# US state abbreviations and full names. Used to recognize concrete US locations
# from ATS boards (e.g. "Austin, TX", "Remote - California") that don't spell out
# "United States". Two-letter codes are only matched in a ", XX" context to avoid
# false positives.
_US_STATE_ABBR = {
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi", "id",
    "il", "in", "ia", "ks", "ky", "la", "me", "md", "ma", "mi", "mn", "ms",
    "mo", "mt", "ne", "nv", "nh", "nj", "nm", "ny", "nc", "nd", "oh", "ok",
    "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv",
    "wi", "wy", "dc",
}
_US_STATE_NAMES = (
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine",
    "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
    "missouri", "montana", "nebraska", "nevada", "new hampshire", "new jersey",
    "new mexico", "new york", "north carolina", "north dakota", "ohio",
    "oklahoma", "oregon", "pennsylvania", "rhode island", "south carolina",
    "south dakota", "tennessee", "texas", "utah", "vermont", "virginia",
    "washington", "west virginia", "wisconsin", "wyoming",
)
_US_STATE_ABBR_RE = re.compile(r",\s*(" + "|".join(_US_STATE_ABBR) + r")\b")

_WS_RE = re.compile(r"\s+")
_SERVICE_NOW_RE = re.compile(r"service[\s\-_]*now", re.IGNORECASE)

_REMOTE_TERMS = (
    "remote",
    "work from home",
    "wfh",
    "work anywhere",
    "fully remote",
    "remote-first",
    "remote first",
    "distributed",
    "telecommute",
)
_HYBRID_TERMS = ("hybrid",)

# Countries / regions that, on their own, fail the US filter.
_NON_US_ONLY = (
    "brazil",
    "india",
    "pakistan",
    "europe",
    "united kingdom",
    "canada",
    "germany",
    "spain",
    "portugal",
    "france",
    "latam",
    "latin america",
    "south america",
    "central america",
    "mexico",
    "argentina",
    "africa",
    "asia",
    "australia",
    "philippines",
    "ukraine",
    "poland",
)


def normalize_text(text) -> str:
    """Lowercase, collapse whitespace, and unify ServiceNow spellings.

    "Service Now", "service-now", "service_now" all become "servicenow".
    """
    if text is None:
        return ""
    if isinstance(text, (list, tuple, set)):
        text = " ".join(str(x) for x in text)
    t = str(text).lower().replace(" ", " ")
    t = _SERVICE_NOW_RE.sub("servicenow", t)
    t = _WS_RE.sub(" ", t)
    return t.strip()


def mentions_target_term(*parts) -> bool:
    """True if the combined text is a candidate for any enabled job category.

    Used by feed adapters for a lightweight pre-filter so feed sources surface
    candidates for the full scoring pass. In multi-stack mode a job matches if it
    hits any enabled category keyword/strong term; in legacy ServiceNow mode it
    matches on a ServiceNow phrase, the Now Platform, or a strong technical term.
    The authoritative accept/reject decision is always made later by the scorer.
    """
    blob = normalize_text(" ".join(str(p) for p in parts if p))
    if settings.multi_stack_mode:
        return jtax.text_matches_any(blob, settings.enabled_category_list)
    term = normalize_text(settings.required_match_term) or "servicenow"
    if term in blob or "now platform" in blob:
        return True
    return bool(tax.detect_strong_terms(blob))


def _join_fields(job: dict, keys) -> str:
    parts: List[str] = []
    for key in keys:
        value = job.get(key)
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            parts.append(" ".join(str(x) for x in value))
        else:
            parts.append(str(value))
    return normalize_text(" ".join(parts))


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------
# Fields whose text feeds the relevance scorer (company_name deliberately
# excluded so an employer literally named "ServiceNow" doesn't auto-match).
_SCORE_BODY_FIELDS = (
    "short_description",
    "full_description",
    "description",
    "tags",
    "category",
    "source_text",
)


def score_servicenow_relevance(job: dict) -> dict:
    """Score how strongly a job relates to the ServiceNow ecosystem.

    Returns::

        {
          "score": int,
          "matched_terms": list[str],
          "matched_modules": list[str],   # module codes
          "matched_roles": list[str],
          "is_servicenow": bool,
          "reason": str,
        }

    Scoring (additive):
        +100 "servicenow" in the title
        +80  "servicenow" in the description / body
        +70  "now platform" present
        +50  a strong ServiceNow-specific technical term present
        +40  a module term present WITH ServiceNow nearby
        +20  only a generic module term present (ITSM/CMDB/HRSD ...)

    Acceptance (``is_servicenow``): a job is accepted when a direct ServiceNow
    phrase appears anywhere, the Now Platform is named, a strong ServiceNow-only
    technical term is present, OR the score reaches the threshold (>= 80).
    Generic ITSM/CMDB/GRC jobs with no ServiceNow evidence are rejected.
    """
    title_text = normalize_text(job.get("title"))
    body_text = _join_fields(job, _SCORE_BODY_FIELDS)
    full_text = (title_text + " " + body_text).strip()

    sn_in_title = "servicenow" in title_text
    sn_in_body = "servicenow" in body_text
    sn_anywhere = sn_in_title or sn_in_body
    now_platform = "now platform" in full_text

    strong_terms = tax.detect_strong_terms(full_text)
    core_terms = tax.detect_core_terms(full_text)
    matched_modules = tax.detect_modules(full_text)
    matched_roles = tax.detect_roles(full_text)
    generic_only = bool(matched_modules) and not (sn_anywhere or now_platform or strong_terms)

    score = 0
    if sn_in_title:
        score += 100
    if sn_in_body:
        score += 80
    if now_platform:
        score += 70
    if strong_terms:
        score += 50
    if matched_modules and (sn_anywhere or now_platform):
        score += 40
    elif matched_modules:
        score += 20

    is_servicenow = bool(
        sn_anywhere or now_platform or strong_terms or score >= 80
    )

    if is_servicenow:
        reason = "servicenow_match"
    elif generic_only:
        reason = "generic_only_no_servicenow"
    else:
        reason = "no_servicenow_evidence"

    matched_terms: List[str] = []
    for term in core_terms + strong_terms:
        if term not in matched_terms:
            matched_terms.append(term)

    return {
        "score": score,
        "matched_terms": matched_terms,
        "matched_modules": matched_modules,
        "matched_roles": matched_roles,
        "is_servicenow": is_servicenow,
        "reason": reason,
    }


def is_servicenow_job(job: dict) -> bool:
    """True if the job is part of the ServiceNow ecosystem (see scorer)."""
    return score_servicenow_relevance(job)["is_servicenow"]


# ---------------------------------------------------------------------------
# Multi-category classification (multi-stack mode)
# ---------------------------------------------------------------------------
def _enabled_category_ids() -> List[str]:
    if settings.multi_stack_mode:
        return settings.enabled_category_list
    return ["servicenow"]


def score_job_relevance(job: dict, category) -> dict:
    """Score a job for one category.

    ``category`` may be a category id, a ``job_taxonomy.Category``, or a dict
    with a ``category_id`` key. Returns ``{"relevance_score", "matched_keywords"}``.
    """
    if isinstance(category, str):
        cat = jtax.CATEGORIES.get(category)
    elif isinstance(category, dict):
        cat = jtax.CATEGORIES.get(category.get("category_id"))
    else:
        cat = category
    if cat is None:
        return {"relevance_score": 0, "matched_keywords": []}

    title_norm = normalize_text(job.get("title"))
    body_norm = _join_fields(job, _SCORE_BODY_FIELDS)
    score, matched, excluded = jtax.score_category(cat, title_norm, body_norm)
    if excluded:
        score = 0
    return {"relevance_score": score, "matched_keywords": matched}


def classify_job_category(job: dict) -> dict:
    """Classify a job across all enabled categories.

    Returns::

        {
          "is_relevant": bool,
          "primary_category": str | None,
          "matched_categories": list[str],
          "matched_keywords": list[str],
          "relevance_score": int,
          "reason": str,
        }
    """
    title_norm = normalize_text(job.get("title"))
    body_norm = _join_fields(job, _SCORE_BODY_FIELDS)

    scored: List[tuple] = []  # (category_id, score, matched)
    for cat in jtax.enabled_categories(_enabled_category_ids()):
        score, matched, excluded = jtax.score_category(cat, title_norm, body_norm)
        if excluded or score <= 0:
            continue
        # ServiceNow strict mode: only count ServiceNow when a genuine ServiceNow
        # signal exists (a ServiceNow phrase / Now Platform / strong term), never
        # generic ITSM/CMDB/GRC alone.
        if cat.category_id == "servicenow" and settings.servicenow_strict_mode:
            if not is_servicenow_job(job):
                continue
        scored.append((cat.category_id, score, matched))

    threshold = settings.min_relevance_score
    if not scored:
        return {
            "is_relevant": False,
            "primary_category": None,
            "matched_categories": [],
            "matched_keywords": [],
            "relevance_score": 0,
            "reason": "no_category_match",
        }

    scored.sort(key=lambda r: r[1], reverse=True)
    primary_id, best_score, _ = scored[0]
    matched_categories = [cid for cid, s, _m in scored if s >= threshold]
    matched_keywords: List[str] = []
    for cid, s, m in scored:
        if s >= threshold:
            for kw in m:
                if kw not in matched_keywords:
                    matched_keywords.append(kw)
    is_relevant = best_score >= threshold
    if not is_relevant:
        # Keep the strongest near-match info for diagnostics.
        matched_keywords = scored[0][2]

    primary = primary_id if is_relevant else None
    reason = (
        f"matched {jtax.category_name(primary_id)} (score {best_score})"
        if is_relevant
        else f"below threshold (best {best_score} < {threshold})"
    )
    return {
        "is_relevant": is_relevant,
        "primary_category": primary,
        "matched_categories": matched_categories,
        "matched_keywords": matched_keywords[:12],
        "relevance_score": best_score,
        "reason": reason,
    }


def is_remote_job(job: dict) -> bool:
    """True if the job is clearly remote.

    Passes on an explicit remote flag or a remote keyword. Fails when the only
    signal is hybrid/onsite, or when there is no remote indicator at all.
    """
    if job.get("remote") is True:
        return True

    text = _join_fields(job, _REMOTE_FIELDS)
    has_remote = any(term in text for term in _REMOTE_TERMS)
    if not has_remote:
        return False

    # "hybrid" without any stronger full-remote signal is treated as not remote.
    if any(term in text for term in _HYBRID_TERMS):
        if "fully remote" not in text and "100% remote" not in text:
            return False
    return True


_WORLDWIDE_TERMS = ("worldwide", "anywhere", "global", "international")


# Canadian location signals (accepted alongside the US when ALLOW_US_OR_CANADA).
_CANADA_TERMS = (
    "canada",
    "canadian",
    "ontario",
    "quebec",
    "british columbia",
    "alberta",
    "manitoba",
    "saskatchewan",
    "nova scotia",
    "toronto",
    "vancouver",
    "montreal",
    "ottawa",
    "calgary",
    "edmonton",
)
_CANADA_ABBR_RE = re.compile(r",\s*(on|qc|bc|ab|mb|sk|ns|nb|nl|pe)\b")


def _non_us_only_terms() -> tuple:
    """Non-US-only countries; Canada is dropped when US-or-Canada is allowed."""
    if settings.allow_us_or_canada:
        return tuple(c for c in _NON_US_ONLY if c != "canada")
    return _NON_US_ONLY


def is_canada_job(job: dict) -> bool:
    text = _join_fields(job, _US_FIELDS)
    if not text:
        return False
    if any(re.search(r"\b" + re.escape(c) + r"\b", text) for c in _CANADA_TERMS):
        return True
    return bool(_CANADA_ABBR_RE.search(text))


def mentions_non_us_only(job: dict) -> bool:
    """True if the location text names a non-US-only country/region."""
    text = _join_fields(job, _US_FIELDS)
    return any(re.search(r"\b" + re.escape(c) + r"\b", text) for c in _non_us_only_terms())


def is_us_job(job: dict) -> bool:
    """True if the job is US-based or open to US candidates."""
    if not settings.country_filter_enabled:
        return True

    text = _join_fields(job, _US_FIELDS)
    if not text:
        return False

    # Extra accepted location strings from configuration. Only multi-word
    # phrases (e.g. "Remote US", "Remote United States") are matched by substring;
    # short single tokens like "US"/"USA" are handled by the precise regex checks
    # below to avoid false positives (e.g. "Belarus" containing "us").
    for loc in settings.target_location_list:
        nloc = normalize_text(loc)
        if nloc and " " in nloc and nloc in text:
            return True

    if re.search(r"\bunited states\b", text):
        return True
    if re.search(r"\bu\.?\s?s\.?\s?a\b", text):  # usa / u.s.a / u s a
        return True
    if "u.s." in text or re.search(r"\bus\b", text):
        return True
    if "north america" in text:
        return True
    # "america" but not "latin/south/central america".
    if re.search(r"\bamerica\b", text) and not re.search(
        r"(latin|south|central)\s+america", text
    ):
        return True

    # Concrete US locations from ATS boards: full state names, or ", XX" codes.
    if any(re.search(r"\b" + name + r"\b", text) for name in _US_STATE_NAMES):
        return True
    if _US_STATE_ABBR_RE.search(text):
        return True

    # Audience is US + Canada: accept clear Canadian signals too.
    if settings.allow_us_or_canada and is_canada_job(job):
        return True

    # Optional relaxation: worldwide/anywhere remote with no excluded country.
    if settings.allow_remote_worldwide_if_us_not_excluded:
        if any(w in text for w in _WORLDWIDE_TERMS) and not mentions_non_us_only(job):
            return True

    return False


def is_allowed_job(job: dict) -> Tuple[bool, List[str], dict]:
    """Return (allowed, reasons, classification).

    ``reasons`` carries stable machine tokens used for run statistics:
    "not_relevant", "not_remote", "not_us", or "allowed". ``classification`` is
    the multi-category result from ``classify_job_category``.
    """
    reasons: List[str] = []

    classification = classify_job_category(job)
    relevant = classification["is_relevant"]
    remote_ok = is_remote_job(job) if settings.remote_only else True
    us_ok = is_us_job(job) if settings.country_filter_enabled else True

    if not relevant:
        reasons.append("not_relevant")
    if not remote_ok:
        reasons.append("not_remote")
    if not us_ok:
        reasons.append("not_us")

    allowed = relevant and remote_ok and us_ok
    if allowed:
        reasons.append("allowed")
    return allowed, reasons, classification


def classify_job(job: dict, normalized_date=None) -> dict:
    """Full funnel classification for one job, used by diagnostics + saving.

    Order (per TODAY-only spec): today -> ServiceNow -> remote -> US.
    Returns each stage flag, a machine reason token, and a ``near_match`` flag
    (ServiceNow job that failed a downstream filter).
    """
    from app.scraper.date_utils import is_posted_today, is_within_window  # avoid circular import

    raw_date = job.get("date_posted_raw")
    date_known = normalized_date is not None
    # is_today drives the "Posted Today" badge + diagnostics today_matches.
    is_today = is_posted_today(raw_date=raw_date, normalized_date=normalized_date)
    # date_ok is the actual gate: strict today (window 0) or the last N days.
    if settings.date_filter_active:
        date_ok = is_within_window(
            raw_date=raw_date,
            normalized_date=normalized_date,
            days=settings.date_window_days,
        )
    else:
        date_ok = True

    cls = classify_job_category(job)
    relevant = cls["is_relevant"]
    matched_categories = cls["matched_categories"]
    has_sn = "servicenow" in matched_categories
    remote_ok = is_remote_job(job) if settings.remote_only else True
    us_ok = is_us_job(job) if settings.country_filter_enabled else True
    allowed = date_ok and relevant and remote_ok and us_ok

    if allowed:
        reason = "allowed"
    elif not date_ok:
        reason = "unknown_date" if not date_known else "old_date"
    elif not relevant:
        reason = "not_relevant"
    elif not remote_ok:
        reason = "not_remote"
    else:
        reason = "not_us"

    # ServiceNow modules are still surfaced for ServiceNow jobs (nice in the UI).
    matched_modules = score_servicenow_relevance(job)["matched_modules"] if has_sn else []

    return {
        "date_known": date_known,
        "is_today": is_today,
        "has_servicenow": has_sn,
        "is_remote": remote_ok,
        "is_us": us_ok,
        "allowed": allowed,
        "reason": reason,
        "near_match": relevant and not allowed,
        # Multi-category classification carried through for persistence + diagnostics.
        "is_relevant": relevant,
        "primary_category": cls["primary_category"],
        "matched_categories": matched_categories,
        "matched_keywords": cls["matched_keywords"],
        "relevance_score": cls["relevance_score"],
        "score": cls["relevance_score"],
        "matched_terms": cls["matched_keywords"],
        "matched_modules": matched_modules,
        "matched_roles": [],
    }
