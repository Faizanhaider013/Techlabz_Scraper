"""Date parsing / normalization and the strict 'Posted Today' gate.

The portal is TODAY-only: a job is treated as "posted today" only if its date
resolves to the current calendar day in APP_TIMEZONE. Unknown, yesterday, or
older dates always fail. There is no fuzzy "recent" pass.

Public API:
  * get_today_range(timezone) -> (start, end) datetimes covering today
  * parse_source_date(raw_date, source_name) -> date | None
  * normalize_relative_date(raw_date, timezone) -> date | None
  * is_posted_today(raw_date, normalized_date, timezone) -> bool
  * parse_date(raw) -> datetime | None   (low-level helper)
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Optional, Tuple

from dateutil import parser as date_parser

try:  # Python 3.9+ stdlib timezone database
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("date_utils")

_RELATIVE_RE = re.compile(
    r"(?P<num>\d+)\s*(?P<unit>second|minute|hour|day|week|month|year)s?\s*ago",
    re.IGNORECASE,
)
# Phrases we confidently treat as "today".
_TODAY_WORDS = {
    "today",
    "just now",
    "just posted",
    "posted today",
    "moments ago",
    "0 days ago",
    "0 day ago",
}
_YESTERDAY_WORDS = {"yesterday", "1 day ago", "a day ago", "1 days ago"}
# Vague phrases that carry NO exact date -> never today.
_VAGUE_WORDS = {"recent", "recently", "new", "featured", "active", ""}


def _tz(tz_name: Optional[str] = None):
    """Resolve an IANA timezone name to a tzinfo (falls back to UTC)."""
    name = tz_name or settings.app_timezone
    if ZoneInfo is None:
        return timezone.utc
    try:
        return ZoneInfo(name)
    except Exception:  # pragma: no cover - bad config
        logger.warning("Invalid timezone %r, falling back to UTC", name)
        return timezone.utc


# Backwards-compatible helpers used elsewhere.
def app_tz():
    return _tz()


def now_local() -> datetime:
    return datetime.now(tz=_tz())


def _to_local(dt: datetime, tz_name: Optional[str] = None) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_tz(tz_name))


def get_today_range(tz_name: Optional[str] = None) -> Tuple[datetime, datetime]:
    """Return (start_of_today, end_of_today) as tz-aware datetimes."""
    now = datetime.now(tz=_tz(tz_name))
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start, end


def normalize_relative_date(raw_date: str, tz_name: Optional[str] = None) -> Optional[date]:
    """Convert a relative phrase ("Today", "3 days ago", "yesterday") to a date.

    Returns None for vague phrases that carry no exact date.
    """
    if raw_date is None:
        return None
    text = str(raw_date).strip().lower()
    if text in _VAGUE_WORDS:
        return None

    today = datetime.now(tz=_tz(tz_name)).date()
    if text in _TODAY_WORDS:
        return today
    if text in _YESTERDAY_WORDS:
        return today - timedelta(days=1)

    match = _RELATIVE_RE.fullmatch(text) or _RELATIVE_RE.search(text)
    if match:
        num = int(match.group("num"))
        unit = match.group("unit").lower()
        deltas = {
            "second": timedelta(seconds=num),
            "minute": timedelta(minutes=num),
            "hour": timedelta(hours=num),
            "day": timedelta(days=num),
            "week": timedelta(weeks=num),
            "month": timedelta(days=30 * num),
            "year": timedelta(days=365 * num),
        }
        return (datetime.now(tz=_tz(tz_name)) - deltas[unit]).date()
    return None


def parse_date(raw, tz_name: Optional[str] = None) -> Optional[datetime]:
    """Best-effort parse of any supported posting-date representation.

    Returns a tz-aware datetime in the target timezone, or None if unknown/vague.
    """
    if raw is None:
        return None

    # Numeric -> unix timestamp (seconds).
    if isinstance(raw, (int, float)):
        try:
            return _to_local(datetime.fromtimestamp(float(raw), tz=timezone.utc), tz_name)
        except (OSError, ValueError, OverflowError):
            return None

    text = str(raw).strip()
    if not text or text.lower() in _VAGUE_WORDS:
        return None

    # Relative phrases first (today / yesterday / N units ago).
    rel = normalize_relative_date(text, tz_name)
    if rel is not None:
        # Anchor to current time-of-day so it stays within the right calendar day.
        now = datetime.now(tz=_tz(tz_name))
        return now.replace(year=rel.year, month=rel.month, day=rel.day)
    # If the text was a recognised relative form but returned None, stop here.
    if text.lower() in _TODAY_WORDS or text.lower() in _YESTERDAY_WORDS:
        return None

    # All-numeric string -> probably a unix timestamp.
    if text.isdigit():
        try:
            return _to_local(datetime.fromtimestamp(int(text), tz=timezone.utc), tz_name)
        except (OSError, ValueError, OverflowError):
            pass

    # Absolute / ISO formats.
    try:
        dt = date_parser.parse(text)
    except (ValueError, OverflowError, TypeError):
        logger.debug("Could not parse date: %r (source hint ignored)", raw)
        return None
    # A naive value (e.g. "2026-05-14") is a calendar date/time in the TARGET
    # timezone -- attaching UTC then converting would shift the day. Only values
    # with an explicit offset are converted.
    if dt.tzinfo is None:
        return dt.replace(tzinfo=_tz(tz_name))
    return dt.astimezone(_tz(tz_name))


def parse_source_date(raw_date, source_name: Optional[str] = None) -> Optional[date]:
    """Parse a source date string/number into a calendar date (or None)."""
    dt = parse_date(raw_date)
    return dt.date() if dt is not None else None


def _resolve_date(raw_date=None, normalized_date=None) -> Optional[date]:
    """Resolve a raw source value or a pre-normalized date(time) to a calendar date."""
    if normalized_date is not None:
        return (
            normalized_date.date()
            if isinstance(normalized_date, datetime)
            else normalized_date
        )
    if raw_date is not None:
        return parse_source_date(raw_date)
    return None


def get_window_range(days: int = 0, tz_name: Optional[str] = None) -> Tuple[datetime, datetime]:
    """Return (start, end) covering the freshness window in the target timezone.

    ``days=0`` -> just today (00:00 today .. 23:59 today). ``days=7`` -> the start
    of 7 days ago through the end of today (i.e. the last 7 days, inclusive).
    """
    start_today, end_today = get_today_range(tz_name)
    return start_today - timedelta(days=days), end_today


def is_within_window(
    raw_date=None,
    normalized_date=None,
    days: int = 0,
    tz_name: Optional[str] = None,
) -> bool:
    """True if the job's date falls within the last ``days`` days (inclusive).

    ``days=0`` is equivalent to the strict "posted today" gate. Unknown /
    unparseable dates always return False, and future dates are rejected.
    """
    today = datetime.now(tz=_tz(tz_name)).date()
    resolved = _resolve_date(raw_date, normalized_date)
    if resolved is None:
        return False
    earliest = today - timedelta(days=max(0, days))
    return earliest <= resolved <= today


def is_posted_today(
    raw_date=None,
    normalized_date=None,
    tz_name: Optional[str] = None,
) -> bool:
    """Strict TODAY gate.

    True only if the job's date resolves to the current calendar day in the
    target timezone. Unknown / yesterday / older dates all return False.
    Accepts either a pre-normalized date(time) or a raw source value.
    """
    return is_within_window(raw_date, normalized_date, days=0, tz_name=tz_name)
