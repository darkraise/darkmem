"""Consolidated 10-type entity and relation taxonomy for the ML extraction heads.

The LLM and ML extraction paths both emit values from these lists. Values
pre-dating the taxonomy consolidation are mapped in via the LEGACY_* tables
(both at DB-migration time and at runtime by :func:`normalize_entity_type` /
:func:`normalize_relation_type`).

Keep in sync with:
  * fine-tuning/scripts/_build_coding10_splits.py (entity TYPE_MAP, 35 -> 10)
  * fine-tuning/scripts/_build_rebel_coding10_splits.py (REL_MAP, 30 -> 10)
  * fine-tuning/models/PRODUCTION.md (canonical list)
"""

from __future__ import annotations


ENTITY_TYPES: list[str] = [
    "tool",
    "service",
    "database",
    "language",
    "protocol",
    "project",
    "algorithm",
    "artifact",
    "concept",
    "entity",
]

RELATIONSHIP_TYPES: list[str] = [
    "USES",
    "DEPENDS_ON",
    "REPLACES",
    "IS_A",
    "HAS_PART",
    "DEPLOYED_ON",
    "CAUSES",
    "AUTHORED_BY",
    "HAPPENED_ON",
    "RELATED_TO",
]

_ENTITY_TYPE_SET: frozenset[str] = frozenset(ENTITY_TYPES)
_RELATIONSHIP_TYPE_SET: frozenset[str] = frozenset(RELATIONSHIP_TYPES)


LEGACY_ENTITY_TYPE_MAP: dict[str, str] = {
    "person": "entity",
    "organization": "entity",
    "team": "entity",
    "company": "entity",
    "date": "entity",
    "place": "entity",
    "event": "entity",
    "technology": "tool",
    "framework": "tool",
    "library": "tool",
    "pattern": "tool",
    "platform": "service",
    "infrastructure": "service",
    "api": "service",
    "system": "service",
    "standard": "protocol",
    "specification": "protocol",
    "method": "algorithm",
    "search algorithm": "algorithm",
    "index type": "tool",
    "file": "artifact",
    "command": "artifact",
    "config": "artifact",
    "error": "artifact",
    "theory": "concept",
    "field": "concept",
    "publication": "concept",
    "finding": "concept",
    "claim": "concept",
    "data structure": "concept",
    "approach": "concept",
    "constant": "concept",
}


LEGACY_RELATION_TYPE_MAP: dict[str, str] = {
    "CONFIGURES": "USES",
    "APPLIES_TO": "USES",
    "COMMUNICATES_WITH": "USES",
    "IMPLEMENTS": "USES",
    "IMPROVES_ON": "REPLACES",
    "BUILDS_ON": "REPLACES",
    "EXTENDS": "HAS_PART",
    "LOCATED_IN": "DEPLOYED_ON",
    "PRODUCES": "CAUSES",
    "FIXES": "CAUSES",
    "PUBLISHED_IN": "AUTHORED_BY",
    "WORKS_AT": "AUTHORED_BY",
    "VISITED": "HAPPENED_ON",
    "LIVES_IN": "HAPPENED_ON",
    "ALTERNATIVE_TO": "RELATED_TO",
    "KNOWS": "RELATED_TO",
    "SUPPORTS": "RELATED_TO",
    "CONTRADICTS": "RELATED_TO",
    "PREFERS": "RELATED_TO",
    "FEELS_ABOUT": "RELATED_TO",
    "PLANS_TO": "RELATED_TO",
}


def normalize_entity_type(raw_type: str) -> str:
    """Return a value from ENTITY_TYPES. Unknown values fall back to ``concept``."""
    if not raw_type:
        return "concept"
    t = raw_type.strip().lower()
    if t in _ENTITY_TYPE_SET:
        return t
    mapped = LEGACY_ENTITY_TYPE_MAP.get(t)
    if mapped:
        return mapped
    return "concept"


def normalize_relation_type(raw_type: str) -> str:
    """Return a value from RELATIONSHIP_TYPES. Unknown values fall back to ``RELATED_TO``."""
    if not raw_type:
        return "RELATED_TO"
    t = raw_type.strip().upper()
    if t in _RELATIONSHIP_TYPE_SET:
        return t
    mapped = LEGACY_RELATION_TYPE_MAP.get(t)
    if mapped:
        return mapped
    return "RELATED_TO"


MEMORY_TYPES: list[str] = [
    "fact",
    "decision",
    "preference",
    "problem",
    "reference",
    "architecture",
    "milestone",
]
