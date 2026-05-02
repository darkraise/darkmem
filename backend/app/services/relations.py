"""Relation + entity constants shared across the backend.

The 10→5 collapse from the ML era has been removed: the LLM emits the
full ``RELATIONSHIP_TYPES`` set and we store all of them as-is. This
module re-exports the canonical sets for back-compat.
"""
from __future__ import annotations

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
