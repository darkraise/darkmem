"""Consolidated 10-type entity and relation taxonomy.

The LLM extraction path emits values from these lists. Values pre-dating
the taxonomy consolidation are mapped in via the LEGACY_* tables (both at
DB-migration time and at runtime by :func:`normalize_entity_type` /
:func:`normalize_relation_type`).
"""

from __future__ import annotations


ENTITY_TYPES: list[str] = [
    # Tech stack (Tier 1)
    "tool",
    "service",
    "database",
    "language",
    "protocol",
    "project",
    "algorithm",
    "artifact",
    # Generic / fallback
    "concept",
    "entity",
    # Real-world subjects (Tier 2 expansion)
    "person",
    "organization",
    "event",
    "place",
    "paper",
]

RELATIONSHIP_TYPES: list[str] = [
    # Composition / dependency
    "USES",
    "DEPENDS_ON",
    "HAS_PART",
    "IMPLEMENTS",
    "EXTENDS",
    # Replacement / evolution
    "REPLACES",
    "IMPROVES_ON",
    # Identity
    "IS_A",
    # Hosting / location
    "DEPLOYED_ON",
    # Causality
    "CAUSES",
    # Attribution / temporal
    "AUTHORED_BY",
    "HAPPENED_ON",
    # Reference / inspiration
    "MENTIONS",
    "CITES",
    "INSPIRED_BY",
    # Catch-all
    "RELATED_TO",
]

_ENTITY_TYPE_SET: frozenset[str] = frozenset(ENTITY_TYPES)
_RELATIONSHIP_TYPE_SET: frozenset[str] = frozenset(RELATIONSHIP_TYPES)


LEGACY_ENTITY_TYPE_MAP: dict[str, str] = {
    # ``person``, ``organization``, ``event``, ``place``, ``paper`` are
    # first-class entity types now — only true legacy aliases remain.
    "team": "organization",
    "company": "organization",
    "date": "entity",  # bare dates are values; this only catches the rare
                       # case the model insists on emitting one.
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
    "publication": "paper",
    "finding": "concept",
    "claim": "concept",
    "data structure": "concept",
    "approach": "concept",
    "constant": "concept",
}


LEGACY_RELATION_TYPE_MAP: dict[str, str] = {
    # IMPLEMENTS, EXTENDS, IMPROVES_ON are first-class types now; legacy
    # rows that used those labels survive unchanged.
    "CONFIGURES": "USES",
    "APPLIES_TO": "USES",
    "COMMUNICATES_WITH": "USES",
    "BUILDS_ON": "IMPROVES_ON",
    "LOCATED_IN": "DEPLOYED_ON",
    "RUNS_ON": "DEPLOYED_ON",
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


# A `project`-typed entity whose NAME ends in a clear library/SDK suffix is
# really a `tool` (a reusable dependency). The extractor over-applies `project`
# to first-party UI kits like "darkraise-ui"; keeping them `tool` is what lets
# them flow into the TECH_TYPES-based ``memories.technologies`` denorm that
# supersession and retrieval read.
_LIBRARY_NAME_SUFFIXES: tuple[str, ...] = ("-ui", "-kit", "-sdk", ".js", "-js")


def refine_entity_type(name: str, etype: str) -> str:
    """Name-aware nudge applied after :func:`normalize_entity_type`. A `project`
    whose name is unmistakably a library/SDK is re-typed `tool`."""
    if etype == "project" and name:
        if name.strip().lower().endswith(_LIBRARY_NAME_SUFFIXES):
            return "tool"
    return etype


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

_MEMORY_TYPE_SET = set(MEMORY_TYPES)


# Caller- or model-supplied aliases mapped to a canonical MEMORY_TYPE so a hint
# like ``debug`` lands on ``problem`` instead of silently defaulting to ``fact``.
LEGACY_MEMORY_TYPE_MAP: dict[str, str] = {
    # problem family (bugs, errors, root causes, workarounds, gotchas)
    "debug": "problem",
    "bug": "problem",
    "gotcha": "problem",
    "workaround": "problem",
    "root_cause": "problem",
    "root-cause": "problem",
    "issue": "problem",
    "error": "problem",
    # milestone family (completed / shipped / released)
    "release": "milestone",
    "shipped": "milestone",
    "completed": "milestone",
    "achievement": "milestone",
    # decision family
    "choice": "decision",
    "tradeoff": "decision",
    "trade-off": "decision",
    # preference family (recurring rules / habits / style)
    "habit": "preference",
    "rule": "preference",
    "style": "preference",
    # reference family (named standards / specs / docs)
    "spec": "reference",
    "standard": "reference",
    "citation": "reference",
    # architecture family
    "design": "architecture",
}


def normalize_memory_type(raw_type: str | None) -> str:
    """Return a value from MEMORY_TYPES. Known aliases (e.g. ``debug`` →
    ``problem``) are mapped first; otherwise unknown values fall back to
    ``fact``."""
    if not raw_type:
        return "fact"
    t = raw_type.strip().lower()
    if t in _MEMORY_TYPE_SET:
        return t
    mapped = LEGACY_MEMORY_TYPE_MAP.get(t)
    if mapped:
        return mapped
    return "fact"
