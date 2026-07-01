"""Normalize raw source jobs into the canonical job dict stored in the DB."""
from __future__ import annotations

import re
from typing import Optional

from app.scraper.date_utils import is_posted_today, parse_date
from app.scraper.dedupe import compute_dedupe_key
from app.scraper.sources.base import RawJob

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")

_REMOTE_HINTS = ("remote", "work from home", "wfh", "anywhere", "distributed")
_HYBRID_HINTS = ("hybrid",)
_ONSITE_HINTS = ("on-site", "onsite", "in office", "in-office")


def strip_html(text: Optional[str]) -> str:
    if not text:
        return ""
    text = _TAG_RE.sub(" ", text)
    text = text.replace("&amp;", "&").replace("&nbsp;", " ")
    return _WS_RE.sub(" ", text).strip()


def make_short_description(full: Optional[str], limit: int = 280) -> str:
    cleaned = strip_html(full)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rsplit(" ", 1)[0] + "..."


def detect_remote_type(raw: RawJob) -> Optional[str]:
    if raw.remote_type:
        return raw.remote_type
    haystack = " ".join(
        filter(None, [raw.title, raw.location, raw.job_type, raw.short_description])
    ).lower()
    if any(h in haystack for h in _HYBRID_HINTS):
        return "hybrid"
    if any(h in haystack for h in _REMOTE_HINTS):
        return "remote"
    if any(h in haystack for h in _ONSITE_HINTS):
        return "onsite"
    return None


def normalize(raw: RawJob, keyword_matched: str) -> dict:
    """Convert a RawJob from a source adapter into a DB-ready dict."""
    normalized_date = parse_date(raw.date_posted_raw)
    if normalized_date is not None:
        from datetime import timezone
        normalized_date = normalized_date.astimezone(timezone.utc)
    full_desc = strip_html(raw.full_description) or None
    short_desc = raw.short_description or make_short_description(raw.full_description)

    title = (raw.title or "").strip()
    company = (raw.company_name or "").strip()
    location = (raw.location or "").strip()

    return {
        "title": title,
        "company_name": company,
        "location": location,
        "date_posted_raw": (str(raw.date_posted_raw).strip() if raw.date_posted_raw is not None else None),
        "posted_date": normalized_date,
        "is_posted_today": is_posted_today(
            raw_date=raw.date_posted_raw, normalized_date=normalized_date
        ),
        "job_type": (raw.job_type or None),
        "salary": (raw.salary or None),
        "short_description": short_desc or None,
        "full_description": full_desc,
        "original_apply_url": (raw.original_apply_url or "").strip(),
        "source_name": raw.source_name,
        "source_job_id": (str(raw.source_job_id) if raw.source_job_id is not None else None),
        "keyword_matched": keyword_matched,
        "remote_type": detect_remote_type(raw),
        "dedupe_key": compute_dedupe_key(
            company_name=company,
            title=title,
            location=location,
            original_apply_url=raw.original_apply_url,
            source_name=raw.source_name,
        ),
    }
