"""Deduplication helpers.

Strategy (in priority order):
  1. Exact match on the original apply URL (normalized).
  2. Fallback match on title + company_name + location (normalized).

Normalization lowercases, trims, collapses whitespace and strips punctuation /
tracking query parameters so that slightly different URLs collapse to one job.
"""
from __future__ import annotations

import hashlib
import re
from urllib.parse import urlsplit, urlunsplit

_PUNCT_RE = re.compile(r"[^\w\s]")
_WS_RE = re.compile(r"\s+")
# Common tracking params we strip so the same job on different links matches.
_TRACKING_PARAMS = ("utm_", "ref", "src", "source", "gh_src", "trk")


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    value = value.lower().strip()
    value = _PUNCT_RE.sub(" ", value)
    value = _WS_RE.sub(" ", value)
    return value.strip()


def normalize_url(url: str | None) -> str:
    """Lowercase host, drop tracking query params, strip trailing slash/fragment."""
    if not url:
        return ""
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return url.strip().lower()

    query_pairs = []
    if parts.query:
        for pair in parts.query.split("&"):
            key = pair.split("=", 1)[0].lower()
            if any(key.startswith(t) for t in _TRACKING_PARAMS):
                continue
            query_pairs.append(pair)

    path = parts.path.rstrip("/")
    cleaned = urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), path, "&".join(query_pairs), "")
    )
    return cleaned.lower()


def compute_dedupe_key(
    *, company_name: str, title: str, location: str, original_apply_url: str | None, source_name: str
) -> str:
    """Return a stable fingerprint using Company, Title, Location, Application URL, and Source.

    Hashed for exact duplicate detection.
    """
    c = normalize_text(company_name)
    t = normalize_text(title)
    l = normalize_text(location)
    u = normalize_url(original_apply_url)
    s = normalize_text(source_name)
    basis = f"{c}|{t}|{l}|{u}|{s}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:40]
