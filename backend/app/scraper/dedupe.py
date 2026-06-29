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
    *, original_apply_url: str | None, title: str, company_name: str, location: str
) -> str:
    """Return a stable fingerprint used as the unique dedupe_key.

    Prefers the normalized URL; otherwise uses title|company|location.
    """
    url = normalize_url(original_apply_url)
    if url:
        basis = f"url::{url}"
    else:
        basis = "tcl::" + "|".join(
            normalize_text(x) for x in (title, company_name, location)
        )
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:40]
