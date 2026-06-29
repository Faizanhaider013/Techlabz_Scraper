"""Smart query builder (multi-stack).

Generates an ordered, de-duplicated, capped list of search queries from the
enabled job categories in the taxonomy -- roles and stacks across PHP/Laravel,
Node.js, React, MERN/MEAN, Full Stack, Software Engineer, Python, DevOps,
Data/AI, QA, and ServiceNow -- not just "ServiceNow Developer".

Query variants per keyword:
  * "<keyword> Remote US"   (US-focused remote)
  * "<keyword> Remote"      (remote)
  * "<keyword>"             (base)

Queries are interleaved round-robin across categories so every enabled category
is represented before the MAX_QUERIES_PER_SOURCE cap is reached.

Gated by config:
  * ENABLE_QUERY_EXPANSION  - master switch (off -> legacy settings.keywords)
  * ENABLE_STACK_SEARCH     - include Remote / Remote US stack variants
  * ENABLED_JOB_CATEGORIES  - which categories to search
  * MAX_QUERIES_PER_SOURCE  - hard cap on the generated list
"""
from __future__ import annotations

from collections import OrderedDict
from typing import List

from app.config import settings
from app.scraper import job_taxonomy as jtax


def _category_variants(category) -> List[str]:
    """Ordered query variants for one category."""
    variants: List[str] = []
    for kw in category.keywords:
        if settings.enable_stack_search:
            variants.append(f"{kw} Remote US")
            variants.append(f"{kw} Remote")
        variants.append(kw)
    return variants


def query_categories() -> "OrderedDict[str, List[str]]":
    """Category name -> its generated query variants (for diagnostics + CLI)."""
    cats: "OrderedDict[str, List[str]]" = OrderedDict()
    for cat in jtax.enabled_categories(settings.enabled_category_list):
        cats[cat.category_name] = _category_variants(cat)
    return cats


def _dedupe(queries: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for q in queries:
        key = q.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(q.strip())
    return out


def build_search_queries() -> List[str]:
    """Generate the ordered, de-duplicated, capped query list for a scrape run.

    Interleaves categories round-robin so each enabled category is represented
    within the MAX_QUERIES_PER_SOURCE cap. Falls back to ``settings.keywords``
    when query expansion is disabled.
    """
    if not settings.enable_query_expansion:
        return settings.keywords

    per_cat = [
        _category_variants(cat)
        for cat in jtax.enabled_categories(settings.enabled_category_list)
    ]
    if not per_cat:
        return settings.keywords

    # Round-robin merge: take the i-th variant from each category in turn.
    merged: List[str] = []
    longest = max(len(v) for v in per_cat)
    for i in range(longest):
        for variants in per_cat:
            if i < len(variants):
                merged.append(variants[i])

    deduped = _dedupe(merged)
    cap = max(1, settings.max_queries_per_source)
    return deduped[:cap]
