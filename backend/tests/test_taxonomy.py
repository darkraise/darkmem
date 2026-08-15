"""The six closed vocabularies, their normalisers, and the LEGACY_* maps.

These tests exist to make invariant 5 — *only tabled values are ever stored* —
fail loudly rather than silently. Three failure modes they are built to catch:

1. **A legacy alias shadowing a promoted type.** If a name is promoted to a
   first-class member of a vocabulary while it is still a key in that
   vocabulary's ``LEGACY_*`` map, the exact-match branch wins and the alias is
   dead — but the reverse mistake (a legacy *value* that is not a member of the
   closed set) rewrites every matching row to a type nothing else recognises.
2. **A hard-coded copy of a vocabulary drifting.** Widening ``MEMORY_TYPES``
   without sweeping the extraction schema string, ``reason()``, the
   classification label space, or the UI's own list leaves that surface unable
   to see rows of the new type at all — a silent hide, not an error.
3. **A normaliser acquiring context.** The normalisers must stay pure functions
   of one raw string, or re-extraction stops being idempotent.
"""
from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

from app.taxonomy import (
    BLOCK_TYPES,
    ENTITY_TYPES,
    LEGACY_BLOCK_TYPE_MAP,
    LEGACY_ENTITY_TYPE_MAP,
    LEGACY_MEMORY_RELATION_TYPE_MAP,
    LEGACY_MEMORY_TYPE_MAP,
    LEGACY_RELATION_TYPE_MAP,
    MEMORY_RELATION_TYPES,
    MEMORY_TYPES,
    PROJECTED_MEMORY_RELATION_TYPES,
    RELATIONSHIP_TYPES,
    is_projected_memory_relation_type,
    normalize_block_type,
    normalize_entity_type,
    normalize_memory_relation_type,
    normalize_memory_type,
    normalize_relation_type,
    refine_entity_type,
)
from app.services.relations import REPLACES_FAMILY, TECH_TYPES, family_key

REPO_ROOT = Path(__file__).resolve().parents[2]


# ── Shape of the closed sets ────────────────────────────────────────


def test_vocabularies_have_their_documented_sizes():
    # Doc 06 §3's table. A count that moves without the table moving is the
    # taxonomy-first rule being skipped.
    assert len(ENTITY_TYPES) == 15
    assert len(RELATIONSHIP_TYPES) == 16
    assert len(TECH_TYPES) == 5
    assert len(MEMORY_TYPES) == 9
    assert len(MEMORY_RELATION_TYPES) == 5
    # Doc 16 §9's minimal block set. Widening it is TH1.03's to justify from a
    # parser that genuinely emits a sixth shape, not a convenience.
    assert len(BLOCK_TYPES) == 5


def test_memory_types_carry_the_two_layer_zero_recall_kinds():
    assert "episodic" in MEMORY_TYPES
    assert "procedural" in MEMORY_TYPES


def test_insight_and_profile_are_not_memory_types():
    # Knowledge moved to the vault; a derived-knowledge memory row is exactly
    # the model this reversed.
    assert "insight" not in MEMORY_TYPES
    assert "profile" not in MEMORY_TYPES
    assert normalize_memory_type("insight") == "fact"
    assert normalize_memory_type("profile") == "fact"


@pytest.mark.parametrize(
    "vocab",
    [ENTITY_TYPES, RELATIONSHIP_TYPES, MEMORY_TYPES, MEMORY_RELATION_TYPES, BLOCK_TYPES],
)
def test_vocabularies_have_no_duplicates(vocab):
    assert len(vocab) == len(set(vocab))


def test_case_conventions_hold():
    # Entity and memory types are stored lowercase; relation types uppercase.
    # The supersession detector and the `technologies` denorm both assume it.
    assert all(t == t.lower() for t in ENTITY_TYPES)
    assert all(t == t.lower() for t in MEMORY_TYPES)
    assert all(t == t.lower() for t in BLOCK_TYPES)
    assert all(t == t.upper() for t in RELATIONSHIP_TYPES)
    assert all(t == t.upper() for t in MEMORY_RELATION_TYPES)


def test_tech_types_are_a_subset_of_entity_types():
    # TECH_TYPES scopes the `memories.technologies` denorm by entity type; a
    # member outside ENTITY_TYPES can never match a stored row.
    assert TECH_TYPES <= set(ENTITY_TYPES)


# ── LEGACY_* map integrity ──────────────────────────────────────────


@pytest.mark.parametrize(
    "legacy_map, closed_set",
    [
        (LEGACY_ENTITY_TYPE_MAP, ENTITY_TYPES),
        (LEGACY_RELATION_TYPE_MAP, RELATIONSHIP_TYPES),
        (LEGACY_MEMORY_TYPE_MAP, MEMORY_TYPES),
        (LEGACY_MEMORY_RELATION_TYPE_MAP, MEMORY_RELATION_TYPES),
        (LEGACY_BLOCK_TYPE_MAP, BLOCK_TYPES),
    ],
)
def test_every_legacy_value_is_a_member_of_its_closed_set(legacy_map, closed_set):
    unknown = {v for v in legacy_map.values() if v not in set(closed_set)}
    assert not unknown, f"legacy map rewrites to non-members: {sorted(unknown)}"


@pytest.mark.parametrize(
    "legacy_map, closed_set",
    [
        (LEGACY_ENTITY_TYPE_MAP, ENTITY_TYPES),
        (LEGACY_RELATION_TYPE_MAP, RELATIONSHIP_TYPES),
        (LEGACY_MEMORY_TYPE_MAP, MEMORY_TYPES),
        (LEGACY_MEMORY_RELATION_TYPE_MAP, MEMORY_RELATION_TYPES),
        (LEGACY_BLOCK_TYPE_MAP, BLOCK_TYPES),
    ],
)
def test_no_legacy_key_shadows_a_first_class_type(legacy_map, closed_set):
    # Promoting a name to a first-class type means deleting its alias in the
    # same vocabulary; otherwise the alias is unreachable dead config that
    # reads as if it were still rewriting.
    shadowed = set(legacy_map) & set(closed_set)
    assert not shadowed, f"legacy aliases shadowed by promotion: {sorted(shadowed)}"


def test_legacy_key_case_matches_its_normaliser():
    # normalize_entity_type/-memory_type lowercase before lookup;
    # normalize_relation_type uppercases. A key in the wrong case never matches.
    assert all(k == k.lower() for k in LEGACY_ENTITY_TYPE_MAP)
    assert all(k == k.lower() for k in LEGACY_MEMORY_TYPE_MAP)
    assert all(k == k.upper() for k in LEGACY_RELATION_TYPE_MAP)
    assert all(k == k.upper() for k in LEGACY_MEMORY_RELATION_TYPE_MAP)


# ── Normalisers: exact → legacy → safe default ──────────────────────


@pytest.mark.parametrize("etype", ENTITY_TYPES)
def test_entity_exact_match_survives(etype):
    assert normalize_entity_type(etype) == etype


@pytest.mark.parametrize("rtype", RELATIONSHIP_TYPES)
def test_relation_exact_match_survives(rtype):
    assert normalize_relation_type(rtype) == rtype


@pytest.mark.parametrize("mtype", MEMORY_TYPES)
def test_memory_exact_match_survives(mtype):
    assert normalize_memory_type(mtype) == mtype


@pytest.mark.parametrize("mrtype", MEMORY_RELATION_TYPES)
def test_memory_relation_exact_match_survives(mrtype):
    assert normalize_memory_relation_type(mrtype) == mrtype


def test_documented_legacy_rewrites():
    # The three rewrites CLAUDE.md and doc 06 §3 name by example.
    assert normalize_entity_type("framework") == "tool"
    assert normalize_relation_type("RUNS_ON") == "DEPLOYED_ON"
    assert normalize_memory_type("debug") == "problem"


def test_new_memory_kinds_absorb_their_aliases():
    assert normalize_memory_type("workflow") == "procedural"
    assert normalize_memory_type("runbook") == "procedural"
    assert normalize_memory_type("session") == "episodic"
    assert normalize_memory_type("experience") == "episodic"


@pytest.mark.parametrize(
    "fn, unknown, default",
    [
        (normalize_entity_type, "quasar-drive", "concept"),
        (normalize_relation_type, "QUASAR_DRIVES", "RELATED_TO"),
        (normalize_memory_type, "quasar-drive", "fact"),
        (normalize_memory_relation_type, "QUASAR_DRIVES", "RELATES_TO"),
        (normalize_block_type, "quasar-block", "paragraph"),
    ],
)
def test_unknown_values_fall_to_the_safe_default(fn, unknown, default):
    assert fn(unknown) == default


@pytest.mark.parametrize(
    "fn, default",
    [
        (normalize_entity_type, "concept"),
        (normalize_relation_type, "RELATED_TO"),
        (normalize_memory_type, "fact"),
        (normalize_memory_relation_type, "RELATES_TO"),
        (normalize_block_type, "paragraph"),
    ],
)
def test_empty_and_none_fall_to_the_safe_default(fn, default):
    assert fn("") == default
    assert fn(None) == default
    assert fn("   ") == default


@pytest.mark.parametrize(
    "fn, raw, expected",
    [
        (normalize_entity_type, "  TOOL  ", "tool"),
        (normalize_relation_type, "  uses  ", "USES"),
        (normalize_memory_type, "  Decision ", "decision"),
        (normalize_memory_relation_type, "  follows ", "FOLLOWS"),
        (normalize_block_type, "  Heading ", "heading"),
    ],
)
def test_normalisers_strip_and_case_fold(fn, raw, expected):
    assert fn(raw) == expected


@pytest.mark.parametrize(
    "fn",
    [
        normalize_entity_type,
        normalize_relation_type,
        normalize_memory_type,
        normalize_memory_relation_type,
        normalize_block_type,
    ],
)
def test_normalisers_take_exactly_one_argument(fn):
    # Purity guard: a normaliser that grew an `area` or a classifier verdict
    # would make the same content normalise differently across reprocesses and
    # break idempotent re-extraction.
    params = list(inspect.signature(fn).parameters)
    assert params == params[:1], f"{fn.__name__} takes context beyond the raw string"


@pytest.mark.parametrize(
    "fn, raw",
    [
        (normalize_entity_type, "framework"),
        (normalize_relation_type, "RUNS_ON"),
        (normalize_memory_type, "workflow"),
        (normalize_memory_relation_type, "SUPPORTS"),
        (normalize_block_type, "fence"),
    ],
)
def test_normalisers_are_deterministic_across_calls(fn, raw):
    assert fn(raw) == fn(raw) == fn(raw)


def test_normalised_output_is_always_a_member_of_the_closed_set():
    junk = ["", "   ", "???", "Framework", "RUNS_ON", "insight", "SUPERSEDES", "42"]
    assert all(normalize_entity_type(v) in set(ENTITY_TYPES) for v in junk)
    assert all(normalize_relation_type(v) in set(RELATIONSHIP_TYPES) for v in junk)
    assert all(normalize_memory_type(v) in set(MEMORY_TYPES) for v in junk)
    assert all(
        normalize_memory_relation_type(v) in set(MEMORY_RELATION_TYPES) for v in junk
    )
    assert all(normalize_block_type(v) in set(BLOCK_TYPES) for v in junk)


def test_refine_entity_type_is_the_only_name_aware_nudge():
    assert refine_entity_type("darkraise-ui", "project") == "tool"
    assert refine_entity_type("darkmem", "project") == "project"
    # The nudge exists so first-party UI kits reach TECH_TYPES.
    assert refine_entity_type("darkraise-ui", "project") in TECH_TYPES


# ── Memory relations stay out of the entity graph ───────────────────


def test_memory_relation_types_never_enter_the_entity_relation_vocabulary():
    # An `entity_relations` row claiming one concept ELABORATES another is
    # meaningless; keeping the sets disjoint is what prevents it.
    overlap = (set(MEMORY_RELATION_TYPES) - {"DEPENDS_ON"}) & set(RELATIONSHIP_TYPES)
    assert not overlap, f"memory-relation types leaked into RELATIONSHIP_TYPES: {overlap}"


def test_elaborates_is_not_accepted_on_an_entity_edge():
    assert normalize_relation_type("ELABORATES") == "RELATED_TO"
    assert normalize_relation_type("FOLLOWS") == "RELATED_TO"


def test_supersedes_is_projected_and_never_a_normaliser_output():
    assert "SUPERSEDES" in PROJECTED_MEMORY_RELATION_TYPES
    assert "SUPERSEDES" not in MEMORY_RELATION_TYPES
    assert is_projected_memory_relation_type("supersedes") is True
    assert is_projected_memory_relation_type("RELATES_TO") is False
    assert normalize_memory_relation_type("SUPERSEDES") == "RELATES_TO"


def test_derived_from_is_cut_and_rewritten_rather_than_stored():
    assert "DERIVED_FROM" not in MEMORY_RELATION_TYPES
    assert normalize_memory_relation_type("DERIVED_FROM") == "RELATES_TO"


# ── REPLACES family collapse ────────────────────────────────────────


def test_replaces_family_collapses_to_one_bucket():
    assert {family_key(r) for r in REPLACES_FAMILY} == {"REPLACES"}


def test_every_replaces_family_member_normalises_into_the_closed_set():
    # BUILDS_ON is legacy-only; it must still land on a stored relation type.
    for rel in REPLACES_FAMILY:
        assert normalize_relation_type(rel) in set(RELATIONSHIP_TYPES)


# ── The sweep: no hard-coded copy of MEMORY_TYPES may drift ─────────


def test_extraction_schema_advertises_every_memory_type():
    from app.services.extraction_clean import _build_extraction_schema

    schema = _build_extraction_schema()
    for mtype in MEMORY_TYPES:
        assert mtype in schema, f"{mtype} missing from the extraction schema string"


def test_extraction_schema_advertises_every_entity_type():
    """The closed entity set reaches the model through the schema, not the prompt.

    The system prompt's "use ONLY these fifteen" sentence was folded into the
    schema string; this is what stops the fold from rotting into a request that
    names no closed set at all.
    """
    from app.services.extraction_clean import _build_extraction_schema

    schema = _build_extraction_schema()
    for etype in ENTITY_TYPES:
        assert etype in schema, f"{etype} missing from the extraction schema string"


def test_extraction_schema_advertises_every_relationship_type():
    """Same fold, relation side: the sixteen types live in the schema string."""
    from app.services.extraction_clean import _build_extraction_schema

    schema = _build_extraction_schema()
    for rtype in RELATIONSHIP_TYPES:
        assert rtype in schema, f"{rtype} missing from the extraction schema string"


def test_reason_type_hints_cover_every_memory_type():
    from app.services import memory as memory_service

    src = inspect.getsource(memory_service.MemoryService.reason)
    assert "KNOWN_TYPES = tuple(MEMORY_TYPES)" in src, (
        "reason()'s type hints must derive from MEMORY_TYPES, not a literal list"
    )


def test_simple_classification_labels_match_memory_types():
    from app.services.classification_areas import SIMPLE_NORMALIZATION, SIMPLE_TYPES

    assert set(SIMPLE_TYPES) == set(MEMORY_TYPES)
    unknown = {v for v in SIMPLE_NORMALIZATION.values() if v not in set(MEMORY_TYPES)}
    assert not unknown, f"classification aliases rewrite to non-members: {sorted(unknown)}"


def test_mcp_tool_descriptions_name_every_memory_type():
    src = (REPO_ROOT / "backend/app/api/mcp/server.py").read_text(encoding="utf-8")
    checked = 0
    for line in src.splitlines():
        stripped = line.strip()
        if not stripped.startswith("memory_type:"):
            continue
        if "One of" not in stripped and "Filter by type" not in stripped:
            continue
        checked += 1
        for mtype in MEMORY_TYPES:
            assert mtype in stripped, f"{mtype} missing from MCP description: {stripped}"
    # Without this the whole test passes vacuously the moment either docstring
    # is reworded past the phrase filter — which is exactly when the vocabulary
    # is most likely to have been edited.
    assert checked == 2, f"expected 2 memory_type docstring lines, matched {checked}"


def test_frontend_shares_one_vocabulary_source_that_matches_the_backend():
    # Doc 13: the UI's type filters are generated from a single shared source,
    # because a stale per-component list silently hides rows of a new type.
    ts = (REPO_ROOT / "frontend/src/lib/taxonomy.ts").read_text(encoding="utf-8")
    block = ts.split("export const MEMORY_TYPES = [", 1)[1].split("]", 1)[0]
    assert re.findall(r'"([a-z_]+)"', block) == MEMORY_TYPES


def test_no_frontend_component_keeps_its_own_memory_type_list():
    shared = REPO_ROOT / "frontend/src/lib/taxonomy.ts"
    offenders = []
    for path in (REPO_ROOT / "frontend/src").rglob("*.ts*"):
        if path == shared or "__tests__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        # Three or more memory types quoted in one file is a re-declared
        # vocabulary, not an incidental mention.
        hits = {m for m in MEMORY_TYPES if f'"{m}"' in text}
        if len(hits) >= 3:
            offenders.append(path.relative_to(REPO_ROOT))
    assert not offenders, f"vocabulary re-declared outside lib/taxonomy.ts: {offenders}"


def test_expanded_mode_can_still_reach_the_new_recall_kinds():
    """Simple mode is pinned to MEMORY_TYPES above, but expanded mode draws from
    the per-area label spaces — so a widening that misses the always-on `general`
    area leaves the new kinds unreachable on that path, silently."""
    from app.services.classification_areas import AREAS

    general = set(AREAS["general"].llm_types)
    assert {"episodic", "procedural"} <= general


def test_graph_colour_map_covers_every_memory_type():
    """A type missing from KNOWN_TYPE_INDICES falls through to the hash path, so
    its colour moves whenever the cluster space shifts. The map's own comment
    promises one index per value; nothing else enforces it."""
    ts = (REPO_ROOT / "frontend/src/features/graph/lib/graph-colors.ts").read_text(
        encoding="utf-8"
    )
    block = ts.split("const KNOWN_TYPE_INDICES: Record<string, number> = {", 1)[1]
    block = block.split("}", 1)[0]
    mapped = set(re.findall(r"^\s*([a-z_]+):", block, re.M))
    assert set(MEMORY_TYPES) <= mapped, (
        f"unmapped memory types: {sorted(set(MEMORY_TYPES) - mapped)}"
    )


# ── The extraction prompt is pinned, not swept ──────────────────────


def test_extraction_prompt_fingerprint_is_pinned():
    """The prompt cannot drift without a deliberate live re-record.

    The prompt text is part of the F1 bench's cache key, so editing it
    invalidates every cached raw output and `run_bench.py --algo-only` — the
    merge gate — can only be re-greened by a live re-measurement against the
    pinned model. The pin exists so that cost is always a decision.

    The value below is the fingerprint recorded with the 2026-07-28 cache
    archive in gate-ledger.md. If this fails, the cache is already invalid:
    re-record live and archive the new generation, or revert the prompt.
    """
    import hashlib

    from app.services import prompt

    fingerprint = hashlib.sha256(prompt.get("extraction").encode("utf-8")).hexdigest()[:16]
    assert fingerprint == "f59a62d1be7273a8"


# ── The update path normalises too (invariant 5) ────────────────────


@pytest.mark.asyncio
async def test_update_memory_normalises_an_untabled_type(session):
    """Create normalises via the pipeline; update has no pipeline pass when the
    content is unchanged, so without an explicit normalise a caller-supplied
    `memory_type` of "bogus" persists forever — invisible to every type filter
    that reads the closed set. Both the REST route and MCP `memory_update` land
    on this method."""
    from sqlalchemy import text as _text

    from app.models.memory import Memory
    from app.schemas.memory import MemoryUpdate
    from app.services.memory import MemoryService

    memory = Memory(content="body", source="api", project="default", memory_type="fact")
    session.add(memory)
    await session.flush()

    service = MemoryService(session)
    await service.update_memory(memory.id, MemoryUpdate(memory_type="bogus"), api_key_id=None)
    await session.flush()

    stored = (
        await session.execute(
            _text("SELECT memory_type FROM memories WHERE id = CAST(:i AS uuid)"),
            {"i": str(memory.id)},
        )
    ).scalar_one()
    assert stored == "fact"  # unknown -> the safe default, not "bogus"


@pytest.mark.asyncio
async def test_update_memory_maps_a_legacy_alias(session):
    from sqlalchemy import text as _text

    from app.models.memory import Memory
    from app.schemas.memory import MemoryUpdate
    from app.services.memory import MemoryService

    memory = Memory(content="body", source="api", project="default", memory_type="fact")
    session.add(memory)
    await session.flush()

    service = MemoryService(session)
    await service.update_memory(memory.id, MemoryUpdate(memory_type="debug"), api_key_id=None)
    await session.flush()

    stored = (
        await session.execute(
            _text("SELECT memory_type FROM memories WHERE id = CAST(:i AS uuid)"),
            {"i": str(memory.id)},
        )
    ).scalar_one()
    assert stored == "problem"
