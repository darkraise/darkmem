"""The closed vocabularies and their pure normalisers (doc 06 §3).

Five vocabularies govern the model. Four live here — ``ENTITY_TYPES``,
``RELATIONSHIP_TYPES``, ``MEMORY_TYPES``, ``MEMORY_RELATION_TYPES`` — and
``TECH_TYPES`` (the ``ENTITY_TYPES`` subset feeding the ``memories.technologies``
denorm) lives in ``app.services.relations`` beside the graph code that reads it.

Every value the LLM or a caller emits passes through a normaliser before it is
stored. Each normaliser is a **three-step fallthrough**: exact match against the
closed set, then a ``LEGACY_*_TYPE_MAP`` rewrite of a historical name, then a
safe default (``concept`` / ``RELATED_TO`` / ``fact`` / ``RELATES_TO``).

The normalisers are **pure functions of a single raw string**. That purity is
load-bearing for idempotent re-extraction: the same content must normalise the
same way on every reprocess, so a normaliser must never take a classifier
verdict, an area, or any other context as a parameter, and must never touch the
database.

Widening a vocabulary is **taxonomy-first**: the value lands here and every
hard-coded copy of the vocabulary is swept before any feature emits it, because
a widened set changes the extraction schema string and re-extraction is then no
longer bit-identical.
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
    # Layer-0 recall kinds. `insight` and `profile` deliberately do NOT join:
    # synthesised knowledge moved out of the memory table into the vault, so
    # they are no longer memory kinds at all.
    "episodic",
    "procedural",
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
    # episodic family (what happened, in sequence)
    "episode": "episodic",
    "experience": "episodic",
    "narrative": "episodic",
    # `session` and `workflow` were previously named as forbidden emissions and
    # fell through to `fact`; the two new kinds give them a real home.
    "session": "episodic",
    # procedural family (how to carry something out)
    "procedure": "procedural",
    "howto": "procedural",
    "how-to": "procedural",
    "runbook": "procedural",
    "playbook": "procedural",
    "workflow": "procedural",
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


# ── Memory-relation types (doc 06 §3.1) ─────────────────────────────
# Memory relations connect *statements* (this decision CONTRADICTS that earlier
# one); entity relations connect *concepts* (postgres DEPLOYED_ON linux). The two
# sets stay apart because a shared set would let `normalize_relation_type` accept
# `ELABORATES` on an entity-to-entity edge, where it is meaningless.
#
# This vocabulary is landed taxonomy-first and has no writer yet: the
# `memory_relations` table is inert, and doc 08's consolidation passes are the
# first writers.

MEMORY_RELATION_TYPES: list[str] = [
    "CONTRADICTS",
    "ELABORATES",
    "DEPENDS_ON",
    "FOLLOWS",
    "RELATES_TO",
]

# `SUPERSEDES` is projected at read time from ``memories.superseded_by`` and is
# never stored as a `memory_relations` row, so it is never a normaliser output
# either — the write-side vocabulary is exactly the five above.
PROJECTED_MEMORY_RELATION_TYPES: tuple[str, ...] = ("SUPERSEDES",)

_MEMORY_RELATION_TYPE_SET: frozenset[str] = frozenset(MEMORY_RELATION_TYPES)


LEGACY_MEMORY_RELATION_TYPE_MAP: dict[str, str] = {
    # The entity-relation catch-all spelling, for callers that reach for the
    # name they know from `RELATIONSHIP_TYPES`.
    "RELATED_TO": "RELATES_TO",
    "SUPPORTS": "ELABORATES",
    "EXPANDS_ON": "ELABORATES",
    "REFINES": "ELABORATES",
    "CLARIFIES": "ELABORATES",
    "CONFLICTS_WITH": "CONTRADICTS",
    "DISAGREES_WITH": "CONTRADICTS",
    # NOTE: no `PRECEDES` alias. "A PRECEDES B" asserts A is EARLIER; a pure
    # type-string normaliser cannot swap endpoints, so rewriting the type
    # alone would store "A FOLLOWS B" and silently invert the temporal
    # order. Unknowns fall to RELATES_TO, which loses the direction claim
    # instead of reversing it. A writer that needs PRECEDES must invert the
    # endpoints itself, before normalising.
    "REQUIRES": "DEPENDS_ON",
    # `DERIVED_FROM` is cut for v1 — the reshape removed its only writer when
    # knowledge left the memory table. Reintroducing it as a first-class type
    # means deleting this alias in the same change, or the normaliser will keep
    # rewriting the new type away.
    "DERIVED_FROM": "RELATES_TO",
}


def normalize_memory_relation_type(raw_type: str | None) -> str:
    """Return one of the five stored ``MEMORY_RELATION_TYPES``.

    Unknown values — including the projected ``SUPERSEDES``, which no writer may
    store — fall back to ``RELATES_TO``.
    """
    if not raw_type:
        return "RELATES_TO"
    t = raw_type.strip().upper()
    if t in _MEMORY_RELATION_TYPE_SET:
        return t
    mapped = LEGACY_MEMORY_RELATION_TYPE_MAP.get(t)
    if mapped:
        return mapped
    return "RELATES_TO"


def is_projected_memory_relation_type(raw_type: str | None) -> bool:
    """True for a memory-relation type that is derived at read time rather than
    stored. A writer that reaches one of these is asking for a row that must not
    exist, and the normaliser will not produce it."""
    return (raw_type or "").strip().upper() in PROJECTED_MEMORY_RELATION_TYPES
