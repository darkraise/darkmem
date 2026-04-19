"""Schema-v2 relation + entity constants shared across the backend.

Mirrors the 5-type coding-native relation set defined in
`fine-tuning/SCHEMA_V2_PLAN.md` so the pipeline, search filters, and
backfill scripts agree on a single authoritative set.
"""
from __future__ import annotations


# 5-type relation set for the coding-native schema.
RELATION_TYPES_V2: tuple[str, ...] = (
    "USES",
    "REPLACES",
    "IS_A",
    "DEPLOYED_ON",
    "CAUSES",
)


# Collapses historical 10-type (and their 30-type ancestors) relation labels
# into the 5-type set. Values that map to None are dropped outright by the
# Phase 6.5 relationship backfill. Mirrors
# fine-tuning/scripts/_build_rebel_coding5_splits.REL_MAP_5.
REL_MAP_5: dict[str, str | None] = {
    # USES cluster
    "USES": "USES",
    "CONFIGURES": "USES",
    "APPLIES_TO": "USES",
    "COMMUNICATES_WITH": "USES",
    "IMPLEMENTS": "USES",
    "DEPENDS_ON": "USES",
    "HAS_PART": "USES",
    "EXTENDS": "USES",
    # REPLACES cluster
    "REPLACES": "REPLACES",
    "IMPROVES_ON": "REPLACES",
    "BUILDS_ON": "REPLACES",
    # IS_A
    "IS_A": "IS_A",
    # DEPLOYED_ON cluster
    "DEPLOYED_ON": "DEPLOYED_ON",
    "LOCATED_IN": "DEPLOYED_ON",
    # CAUSES cluster
    "CAUSES": "CAUSES",
    "PRODUCES": "CAUSES",
    "FIXES": "CAUSES",
    # Dropped sources — explicit None so membership stays authoritative.
    "RELATED_TO": None,
    "KNOWS": None,
    "SUPPORTS": None,
    "CONTRADICTS": None,
    "PREFERS": None,
    "FEELS_ABOUT": None,
    "PLANS_TO": None,
    "VISITED": None,
    "LIVES_IN": None,
    "HAPPENED_ON": None,
    "AUTHORED_BY": None,
    "PUBLISHED_IN": None,
    "WORKS_AT": None,
}


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


REPLACES_CONFIDENCE_THRESHOLD: float = 0.7

# Textual markers that indicate speculative or low-confidence REPLACES
# phrasing; when the source memory matches any of these the supersession
# detector short-circuits. The relation extractor does not currently emit
# per-relation confidence, so this rule stands in until it does.
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
