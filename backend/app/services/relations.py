"""Relation + entity constants shared across the backend.

The 10→5 collapse from the ML era has been removed: the LLM emits the
full ``RELATIONSHIP_TYPES`` set and we store all of them as-is. This
module re-exports the canonical sets for back-compat.
"""
from __future__ import annotations

import re

from app.taxonomy import RELATIONSHIP_TYPES


# Public alias for callers that imported the schema-v2 name. Now points at
# the full canonical relation type list.
RELATION_TYPES_V2: tuple[str, ...] = tuple(RELATIONSHIP_TYPES)


# Replacement-family relations: REPLACES, IMPROVES_ON, and the legacy
# BUILDS_ON all describe "X supersedes Y" in the prompt taxonomy. The
# rescue dedup uses this group to avoid emitting one variant when the LLM
# has already produced another.
REPLACES_FAMILY: frozenset[str] = frozenset({"REPLACES", "IMPROVES_ON", "BUILDS_ON"})


def family_key(rel_type: str) -> str:
    """Return the canonical bucket for relation-type equivalence in dedup.

    Today the only family is REPLACES; everything else is its own bucket.
    Used by the rescue layer's dedup keys so e.g. an LLM-emitted REPLACES
    suppresses a rescue-emitted IMPROVES_ON for the same pair.
    """
    rt = (rel_type or "").upper()
    if rt in REPLACES_FAMILY:
        return "REPLACES"
    return rt


# Entity types that count as "technologies" for the `memories.technologies`
# array. Used by the extraction pipeline and retrieval filters to scope
# searches to "memories that mention tech X" without joining the entities
# table.
TECH_TYPES: frozenset[str] = frozenset({
    "tool",
    "service",
    "database",
    "language",
    "protocol",
})


# ── Entity-merge discriminator ──────────────────────────────────────────
# Phase-4 dedup probes the global entity set with an ANN query at cosine 0.85
# and canonicalizes a fresh entity onto a near neighbour. That recall is right
# for surface variants ('postgres'/'postgresql', typos, casing) but WRONG for
# entities that differ only by a discriminating token — 'february outage' vs
# 'march outage', two ISO dates, 'v2' vs 'v3', 'us-east-1' vs 'us-west-2' —
# which embed almost identically yet are distinct. ``names_distinct`` is the
# lexical precision gate the embedding recall lacks.
_MONTHS: frozenset[str] = frozenset({
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
})
_TOKEN_SPLIT = re.compile(r"[\s\-_./:]+")


def _tokens(name: str) -> list[str]:
    return [t for t in _TOKEN_SPLIT.split((name or "").lower()) if t]


def _norm_alnum(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower())


def names_distinct(a: str, b: str) -> bool:
    """True when ``a`` and ``b`` are DISTINCT entities that must not be merged
    despite a high embedding similarity, because they differ by a discriminating
    token: a numeric/date/version component or a month.

    Returns False (mergeable) for pure formatting variants ('gpt-4'/'gpt4',
    'darkraise-ui'/'darkraise ui') and for embedding-similar surface variants
    that carry no discriminator ('postgres'/'postgresql', typos) — so the ANN
    dedup keeps its recall while losing the false collapses."""
    if _norm_alnum(a) == _norm_alnum(b):
        return False  # same string modulo punctuation/case -> one entity
    ta, tb = _tokens(a), _tokens(b)
    num_a = frozenset(t for t in ta if any(c.isdigit() for c in t))
    num_b = frozenset(t for t in tb if any(c.isdigit() for c in t))
    if num_a != num_b:
        return True  # different numbers / dates / versions
    month_a = frozenset(t for t in ta if t in _MONTHS)
    month_b = frozenset(t for t in tb if t in _MONTHS)
    if month_a != month_b:
        return True  # different months
    return False


REPLACES_CONFIDENCE_THRESHOLD: float = 0.7

# Textual markers that indicate speculative or low-confidence REPLACES
# phrasing; when the source memory matches any of these the supersession
# detector short-circuits.
SPECULATIVE_REPLACES_MARKERS: frozenset[str] = frozenset({
    "might",
    "could",
    "would",
    "may switch",
    "considering",
    "thinking about",
    "planning to switch",
    "would consider",
})

# Supersession look-back window in days.
SUPERSESSION_WINDOW_DAYS: int = 90
