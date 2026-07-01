"""Multi-stack job taxonomy: the single source of truth for the categories,
keywords, and scoring terms the scraper searches for and classifies against.

The portal is no longer hardcoded to ServiceNow. Each category defines:

  * category_id       - stable id (used in env, API, DB, frontend)
  * category_name     - human label
  * keywords          - exact role/stack phrases (a title/desc hit is decisive)
  * strong_terms      - distinctive tech tokens for the stack
  * weak_terms        - supporting/generic terms (never decisive on their own)
  * excluded_terms    - terms that disqualify the category for a job
  * default_enabled   - whether the category is on by default

ServiceNow keeps its strong precision: its keywords all contain a ServiceNow
phrase and its weak terms (ITSM/CMDB/...) can never reach the acceptance
threshold on their own, so generic ITSM/CMDB/GRC jobs are not misclassified.

Scoring helpers here are pure (config-independent); the relevance filter wraps
them with the configured enabled-category list and threshold.
"""
from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Normalization (shared shape with relevance.normalize_text)
# ---------------------------------------------------------------------------
_WS_RE = re.compile(r"\s+")
_SERVICE_NOW_RE = re.compile(r"service[\s\-_]*now", re.IGNORECASE)


def normalize(text) -> str:
    if text is None:
        return ""
    if isinstance(text, (list, tuple, set)):
        text = " ".join(str(x) for x in text)
    t = str(text).lower()
    t = _SERVICE_NOW_RE.sub("servicenow", t)
    t = _WS_RE.sub(" ", t)
    return t.strip()


# Generic role words: a title that pairs one of these with a stack strong term
# is a strong role-title match for that category.
ROLE_WORD_RE = re.compile(
    r"\b(developer|engineer|programmer|architect|consultant|administrator|admin|"
    r"analyst|specialist|sdet|tester|scientist|sre)\b"
)


def _compile_terms(terms: List[str]):
    """Compile an alternation of word-boundary term matches (or None)."""
    if not terms:
        return None
    parts = sorted({normalize(t) for t in terms if t and t.strip()}, key=len, reverse=True)
    if not parts:
        return None
    return re.compile(r"\b(?:" + "|".join(re.escape(p) for p in parts) + r")\b")


@dataclass
class Category:
    category_id: str
    category_name: str
    keywords: List[str]
    strong_terms: List[str] = field(default_factory=list)
    weak_terms: List[str] = field(default_factory=list)
    excluded_terms: List[str] = field(default_factory=list)
    default_enabled: bool = True
    # Compiled lazily after construction.
    _kw_re: object = field(default=None, repr=False)
    _strong_re: object = field(default=None, repr=False)
    _weak_re: object = field(default=None, repr=False)
    _excl_re: object = field(default=None, repr=False)
    _orig: Dict[str, str] = field(default_factory=dict, repr=False)

    def compile(self) -> "Category":
        self._kw_re = _compile_terms(self.keywords)
        self._strong_re = _compile_terms(self.strong_terms)
        self._weak_re = _compile_terms(self.weak_terms)
        self._excl_re = _compile_terms(self.excluded_terms)
        # Map normalized -> original casing for nicer matched_keywords output.
        for t in self.keywords + self.strong_terms:
            self._orig.setdefault(normalize(t), t)
        return self


# ---------------------------------------------------------------------------
# Category definitions
# ---------------------------------------------------------------------------
_DEFS: List[Category] = [
    Category(
        category_id="servicenow",
        category_name="ServiceNow",
        keywords=[
            "ServiceNow", "Service Now", "Service-Now", "Now Platform",
            "ServiceNow Developer", "ServiceNow Administrator", "ServiceNow Consultant",
            "ServiceNow Architect", "ServiceNow ITSM", "ServiceNow ITOM",
            "ServiceNow CMDB", "ServiceNow HRSD", "ServiceNow CSM", "ServiceNow SecOps",
            "ServiceNow IRM", "ServiceNow GRC", "ServiceNow SPM", "ServiceNow App Engine",
            "ServiceNow Service Portal", "ServiceNow Integration Hub",
            "ServiceNow Flow Designer", "ServiceNow Discovery",
            "ServiceNow Developer Remote", "ServiceNow Consultant Remote",
            "ServiceNow Architect Remote",
        ],
        strong_terms=[
            "GlideRecord", "GlideAjax", "Script Include", "Business Rule",
            "Client Script", "Flow Designer", "IntegrationHub", "Integration Hub",
            "MID Server", "Update Set", "Transform Map", "Now Assist",
            "App Engine Studio", "Service Portal", "Catalog Item", "Record Producer",
            "Scoped Application", "ACL",
        ],
        weak_terms=["ITSM", "ITOM", "CMDB", "HRSD", "CSM", "SecOps", "GRC", "IRM", "SPM", "Discovery"],
    ),
    Category(
        category_id="mern",
        category_name="MERN Stack",
        keywords=[
            "MERN Stack Developer", "MERN Developer", "MERN Stack Engineer",
            "MongoDB Express React Node", "Full Stack MERN Developer",
            "React Node MongoDB Developer", "MERN Full Stack Engineer",
        ],
        strong_terms=["MERN"],
        weak_terms=["mongodb", "express", "react", "node"],
    ),
    Category(
        category_id="mean",
        category_name="MEAN Stack",
        keywords=[
            "MEAN Stack Developer", "MEAN Developer", "MEAN Stack Engineer",
            "MongoDB Express Angular Node", "Angular Node Developer",
            "MEAN Full Stack Engineer",
        ],
        strong_terms=["MEAN"],
        weak_terms=["mongodb", "express", "angular", "node"],
    ),
    Category(
        category_id="node_backend",
        category_name="Node.js",
        keywords=[
            "Node.js Developer", "Node Developer", "Node.js Engineer",
            "Backend Developer Node.js", "Express.js Developer", "NestJS Developer",
            "API Developer Node.js", "REST API Developer Node.js",
            "JavaScript Backend Developer", "TypeScript Backend Developer",
        ],
        strong_terms=[
            "Node.js", "Node", "Express", "Express.js", "NestJS",
        ],
        weak_terms=["backend", "server-side", "rest api", "api"],
    ),
    Category(
        category_id="php",
        category_name="PHP",
        keywords=[
            "PHP Developer", "PHP Engineer", "PHP Backend Developer",
            "Symfony Developer", "CodeIgniter Developer", "WordPress Developer",
            "WooCommerce Developer", "Magento Developer", "Drupal Developer",
            "PHP API Developer", "PHP MySQL Developer",
        ],
        strong_terms=[
            "PHP", "Symfony", "CodeIgniter", "WordPress", "WooCommerce",
            "Magento", "Drupal",
        ],
        weak_terms=["mysql", "backend"],
    ),
    Category(
        category_id="laravel",
        category_name="Laravel",
        keywords=[
            "Laravel Developer", "Laravel Engineer", "Laravel Backend Developer",
            "PHP Laravel Developer", "Laravel Full Stack Developer",
        ],
        strong_terms=[
            "Laravel", "Blade", "Eloquent", "Composer",
        ],
        weak_terms=["mysql", "backend"],
    ),
    Category(
        category_id="react_frontend",
        category_name="Frontend",
        keywords=[
            "Frontend Developer", "Frontend Engineer", "Front End Developer",
            "Front End Engineer", "React Developer", "React.js Developer", "React Engineer",
            "Frontend Developer React", "Frontend Engineer React",
            "JavaScript Developer React", "TypeScript React Developer",
            "Next.js Developer", "NextJS Developer", "Redux Developer",
            "UI Developer", "Web Frontend Developer",
            "Vue Developer", "Vue.js Developer", "Angular Developer",
        ],
        strong_terms=[
            "React", "React.js", "Redux", "Next.js", "NextJS", "JSX",
            "Vue", "Vue.js", "VueJS", "Angular", "AngularJS",
            "JavaScript", "TypeScript", "JS", "TS", "UI", "Frontend", "Front-end", "Front End",
        ],
        weak_terms=["frontend", "front-end", "ui", "javascript", "typescript"],
    ),
]

CATEGORIES: "OrderedDict[str, Category]" = OrderedDict(
    (c.category_id, c.compile()) for c in _DEFS
)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def _unique(seq: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for s in seq:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def score_category(cat: Category, title_norm: str, body_norm: str) -> Tuple[int, List[str], bool]:
    """Score one category against pre-normalized title/body text.

    Returns (score, matched_terms_original_cased, excluded).
    """
    if cat._excl_re and (cat._excl_re.search(title_norm) or cat._excl_re.search(body_norm)):
        return 0, [], True

    kw_title = cat._kw_re.findall(title_norm) if cat._kw_re else []
    kw_body = cat._kw_re.findall(body_norm) if cat._kw_re else []
    strong_title = cat._strong_re.findall(title_norm) if cat._strong_re else []
    strong_body = cat._strong_re.findall(body_norm) if cat._strong_re else []
    weak_hit = bool(cat._weak_re and (cat._weak_re.search(title_norm) or cat._weak_re.search(body_norm)))
    role_in_title = bool(ROLE_WORD_RE.search(title_norm))

    score = 0
    if kw_title:
        score += 100
    if kw_body:
        score += 80
    if strong_title:
        score += 50
    if strong_body:
        score += 30
    if role_in_title and (kw_title or strong_title):
        score += 60
    if weak_hit:
        score += 20

    matched_norm = _unique(kw_title + kw_body + strong_title + strong_body)
    matched = [cat._orig.get(m, m) for m in matched_norm]
    return score, matched, False


def enabled_categories(enabled_ids: List[str]) -> List[Category]:
    return [CATEGORIES[c] for c in enabled_ids if c in CATEGORIES]


def text_matches_any(text, enabled_ids: List[str]) -> bool:
    """Fast pre-filter: does the text hit any enabled category keyword/strong term?"""
    n = normalize(text)
    if not n:
        return False
    for cat in enabled_categories(enabled_ids):
        if cat._kw_re and cat._kw_re.search(n):
            return True
        if cat._strong_re and cat._strong_re.search(n):
            return True
    return False


def all_category_ids() -> List[str]:
    return list(CATEGORIES.keys())


def category_name(category_id: str) -> str:
    cat = CATEGORIES.get(category_id)
    return cat.category_name if cat else category_id


def iter_keywords() -> "OrderedDict[str, List[str]]":
    """Category -> keyword list, for the list-keywords CLI."""
    return OrderedDict((c.category_name, list(c.keywords)) for c in CATEGORIES.values())
