"""Unit tests for Phase 5 schema-v2 metadata helpers.

Covers `estimate_confidence`, the REPLACES-supersession detector, and the
defaults applied by the memories table after the 0005 migration.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.memory import Memory
from app.services.confidence import (
    CONFIDENCE_AUTH_TYPES,
    CONFIDENCE_DEFAULT,
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    estimate_confidence,
    rank_fusion_factor,
)
from app.services.supersession import detect_supersessions, is_speculative


def _minimal_memory_kwargs(**overrides):
    base = dict(
        content="test",
        source="test",
        source_agent=None,
        memory_type=None,
        importance=0.5,
        metadata_={},
    )
    base.update(overrides)
    return base


# --- estimate_confidence ---------------------------------------------------

def test_estimate_confidence_default():
    assert estimate_confidence("plain statement of fact", None) == CONFIDENCE_DEFAULT


def test_estimate_confidence_low_phrasing():
    assert estimate_confidence("we might switch to valkey later", None) == CONFIDENCE_LOW


def test_estimate_confidence_high_phrasing():
    assert estimate_confidence("pgvector is definitely the primary store", None) == CONFIDENCE_HIGH


def test_estimate_confidence_prefers_default_on_conflict():
    text = "I think X is definitely maybe correct"
    assert estimate_confidence(text, None) == CONFIDENCE_DEFAULT


def test_estimate_confidence_authoritative_type():
    assert estimate_confidence("the service runs on port 8080", "reference") == CONFIDENCE_AUTH_TYPES
    assert estimate_confidence("adopted bge-base for retrieval", "decision") == CONFIDENCE_AUTH_TYPES


def test_estimate_confidence_handles_missing_text():
    assert estimate_confidence(None, None) == CONFIDENCE_DEFAULT
    assert estimate_confidence("", "fact") == CONFIDENCE_DEFAULT


def test_estimate_confidence_word_boundary_avoids_false_match():
    # "might" should not fire inside "mighty", "proven" should not fire
    # inside "approvement". These would have matched the old substring rule.
    assert estimate_confidence("mighty fine system, no notes", None) == CONFIDENCE_DEFAULT
    assert estimate_confidence("approvement pipeline passes cleanly", None) == CONFIDENCE_DEFAULT


def test_estimate_confidence_is_case_insensitive():
    assert estimate_confidence("We Definitely shipped it", None) == CONFIDENCE_HIGH
    assert estimate_confidence("Maybe we should revisit", None) == CONFIDENCE_LOW


# --- rank_fusion_factor ----------------------------------------------------

def test_rank_fusion_factor_is_identity_when_gamma_zero():
    assert rank_fusion_factor(0.5, 0.0) == 1.0
    assert rank_fusion_factor(0.9, 0.0) == 1.0


def test_rank_fusion_factor_boosts_high_confidence():
    # 0.9 confidence, gamma=1.0 => 1 + 1*(0.9-0.75) = 1.15
    assert rank_fusion_factor(0.9, 1.0) == pytest.approx(1.15)


def test_rank_fusion_factor_dampens_low_confidence():
    # 0.5 confidence, gamma=1.0 => 1 + 1*(0.5-0.75) = 0.75
    assert rank_fusion_factor(0.5, 1.0) == pytest.approx(0.75)


def test_rank_fusion_factor_clamps_at_zero_for_pathological_gamma():
    # gamma=10 on confidence=0.5 would give 1 + 10*(0.5-0.75) = -1.5 without
    # the clamp, which would invert ranking when multiplied against a
    # positive base score. Clamp keeps the factor non-negative.
    assert rank_fusion_factor(0.5, 10.0) == 0.0
    assert rank_fusion_factor(0.0, 10.0) == 0.0


# --- is_speculative --------------------------------------------------------

def test_is_speculative_flags_speculative_phrasing():
    assert is_speculative("we might switch to typescript")
    assert is_speculative("considering replacing Redis with Valkey")
    assert is_speculative("we would consider moving off pgvector")


def test_is_speculative_passes_declarative_phrasing():
    assert not is_speculative("we switched from Redis to Valkey")
    assert not is_speculative("Valkey replaces Redis for cache")


# --- detect_supersessions --------------------------------------------------

@pytest.mark.asyncio
async def test_detect_supersessions_flips_old_active_memory(session):
    project = "darkmem-test"
    old = Memory(
        **_minimal_memory_kwargs(content="we use redis for cache"),
        project=project,
        status="active",
        technologies=["redis"],
    )
    new_id = uuid.uuid4()
    new = Memory(
        **_minimal_memory_kwargs(content="we switched from redis to valkey"),
        id=new_id,
        project=project,
        status="active",
        technologies=["valkey", "redis"],
    )
    session.add_all([old, new])
    await session.flush()

    flipped = await detect_supersessions(
        session,
        new_memory_id=new_id,
        new_memory_text="we switched from redis to valkey",
        project=project,
        new_relations=[{"type": "REPLACES", "source": "valkey", "target": "redis"}],
    )

    assert flipped == [old.id]
    await session.refresh(old)
    assert old.status == "superseded"
    assert old.superseded_by == new_id


@pytest.mark.asyncio
async def test_detect_supersessions_skips_speculative_source(session):
    project = "darkmem-test"
    old = Memory(
        **_minimal_memory_kwargs(content="we use redis"),
        project=project,
        status="active",
        technologies=["redis"],
    )
    session.add(old)
    await session.flush()

    flipped = await detect_supersessions(
        session,
        new_memory_id=uuid.uuid4(),
        new_memory_text="we might switch from redis to valkey",
        project=project,
        new_relations=[{"type": "REPLACES", "source": "valkey", "target": "redis"}],
    )

    assert flipped == []
    await session.refresh(old)
    assert old.status == "active"


@pytest.mark.asyncio
async def test_detect_supersessions_respects_project_scope(session):
    other = Memory(
        **_minimal_memory_kwargs(content="redis in other project"),
        project="other-project",
        status="active",
        technologies=["redis"],
    )
    session.add(other)
    await session.flush()

    flipped = await detect_supersessions(
        session,
        new_memory_id=uuid.uuid4(),
        new_memory_text="we switched from redis to valkey",
        project="this-project",
        new_relations=[{"type": "REPLACES", "source": "valkey", "target": "redis"}],
    )

    assert flipped == []
    await session.refresh(other)
    assert other.status == "active"


@pytest.mark.asyncio
async def test_detect_supersessions_respects_staleness_window(session):
    project = "darkmem-test"
    stale = Memory(
        **_minimal_memory_kwargs(content="old redis memory"),
        project=project,
        status="active",
        technologies=["redis"],
    )
    session.add(stale)
    await session.flush()
    # Force created_at way outside the 90-day window.
    stale.created_at = datetime.now(timezone.utc) - timedelta(days=365)
    await session.flush()

    flipped = await detect_supersessions(
        session,
        new_memory_id=uuid.uuid4(),
        new_memory_text="we switched from redis to valkey",
        project=project,
        new_relations=[{"type": "REPLACES", "source": "valkey", "target": "redis"}],
    )

    assert flipped == []
    await session.refresh(stale)
    assert stale.status == "active"


@pytest.mark.asyncio
async def test_detect_supersessions_requires_technology_containment(session):
    project = "darkmem-test"
    unrelated = Memory(
        **_minimal_memory_kwargs(content="postgres mention, not redis"),
        project=project,
        status="active",
        technologies=["postgres"],
    )
    session.add(unrelated)
    await session.flush()

    flipped = await detect_supersessions(
        session,
        new_memory_id=uuid.uuid4(),
        new_memory_text="we switched from redis to valkey",
        project=project,
        new_relations=[{"type": "REPLACES", "source": "valkey", "target": "redis"}],
    )

    assert flipped == []
    await session.refresh(unrelated)
    assert unrelated.status == "active"


# --- Memory-row defaults (from migration 0005) -----------------------------

@pytest.mark.asyncio
async def test_memory_defaults_are_populated(session):
    m = Memory(**_minimal_memory_kwargs(content="default check"))
    session.add(m)
    await session.flush()
    await session.refresh(m)

    assert m.project == "default"
    assert m.status == "active"
    assert list(m.technologies) == []
    assert m.confidence == pytest.approx(0.75)
    assert m.superseded_by is None


@pytest.mark.asyncio
async def test_memory_status_enum_rejects_garbage(session):
    from sqlalchemy.exc import DBAPIError

    m = Memory(
        **_minimal_memory_kwargs(content="bad status"),
        project="default",
        status="not-a-real-status",
    )
    session.add(m)
    with pytest.raises(DBAPIError):
        await session.flush()


@pytest.mark.asyncio
async def test_memory_find_by_project(session):
    a = Memory(**_minimal_memory_kwargs(content="a"), project="proj-a")
    b = Memory(**_minimal_memory_kwargs(content="b"), project="proj-b")
    session.add_all([a, b])
    await session.flush()

    rows = (await session.execute(select(Memory).where(Memory.project == "proj-a"))).scalars().all()
    assert [m.project for m in rows] == ["proj-a"]


# --- REL_MAP_5 coverage on the 10-type relation vocabulary ----------------

def test_rel_map_5_covers_every_10_type_label():
    """ExtractionMLService normalises 30 -> 10 then applies REL_MAP_5 to get
    5. The post-hoc step will silently drop a 10-type label if REL_MAP_5
    lacks a key for it. Lock the expected mapping so future taxonomy drift
    has to be intentional."""
    from app.services.relations import REL_MAP_5

    expected = {
        "USES": "USES",
        "DEPENDS_ON": "USES",
        "HAS_PART": "USES",
        "REPLACES": "REPLACES",
        "IS_A": "IS_A",
        "DEPLOYED_ON": "DEPLOYED_ON",
        "CAUSES": "CAUSES",
        "AUTHORED_BY": None,
        "HAPPENED_ON": None,
        "RELATED_TO": None,
    }
    for label, mapped in expected.items():
        assert label in REL_MAP_5, f"REL_MAP_5 missing 10-type label {label!r}"
        assert REL_MAP_5[label] == mapped, (
            f"REL_MAP_5[{label!r}] = {REL_MAP_5[label]!r}, expected {mapped!r}"
        )


def test_extraction_ml_drops_dropped_cluster_relations():
    """When the REBEL decoder emits a RELATED_TO triplet, the post-hoc
    REL_MAP_5 step in `_run_relations` must drop it rather than store it —
    otherwise the 5-type invariant on `entity_relations.rel_type` is broken.
    """
    from app.services.relations import REL_MAP_5
    from app.taxonomy import normalize_relation_type

    for raw in ("RELATED_TO", "HAPPENED_ON", "AUTHORED_BY", "KNOWS", "VISITED"):
        ten = normalize_relation_type(raw)
        five = REL_MAP_5.get(ten, ten)
        assert five is None, (
            f"dropped-cluster label {raw!r} survived as 10={ten!r} 5={five!r}; "
            "ExtractionMLService would store a non-5-type rel_type"
        )


def test_extraction_ml_preserves_core_clusters():
    """Core 10-type labels must collapse cleanly into the 5-type set."""
    from app.services.relations import REL_MAP_5, RELATION_TYPES_V2
    from app.taxonomy import normalize_relation_type

    for raw, expected_five in (
        ("USES", "USES"),
        ("DEPENDS_ON", "USES"),
        ("HAS_PART", "USES"),
        ("REPLACES", "REPLACES"),
        ("IS_A", "IS_A"),
        ("DEPLOYED_ON", "DEPLOYED_ON"),
        ("CAUSES", "CAUSES"),
    ):
        ten = normalize_relation_type(raw)
        five = REL_MAP_5.get(ten, ten)
        assert five == expected_five, f"{raw} -> {ten} -> {five}, expected {expected_five}"
        assert five in RELATION_TYPES_V2


def test_clean_extraction_collapses_10_type_to_5_type():
    """`clean_extraction` is the shared path for both the LLM and ML
    extraction paths; it must emit 5-type relation rows so downstream graph
    inserts never need further normalisation."""
    from app.services.extraction import clean_extraction

    result = {
        "memory_type": "fact",
        "importance": 0.5,
        "entities": [
            {"name": "pgvector", "type": "tool"},
            {"name": "postgres", "type": "database"},
            {"name": "someone", "type": "entity"},
            {"name": "2024-04-19", "type": "entity"},
        ],
        "relationships": [
            {"source": "pgvector", "target": "postgres", "type": "DEPENDS_ON"},
            {"source": "pgvector", "target": "postgres", "type": "HAS_PART"},
            {"source": "postgres", "target": "someone", "type": "AUTHORED_BY"},
            {"source": "postgres", "target": "2024-04-19", "type": "HAPPENED_ON"},
        ],
    }
    cleaned = clean_extraction(result, content="pgvector depends on postgres")

    kept_types = {r["type"] for r in cleaned["relationships"]}
    assert "USES" in kept_types, f"DEPENDS_ON/HAS_PART should collapse to USES; got {kept_types}"
    for dropped in ("AUTHORED_BY", "HAPPENED_ON"):
        assert dropped not in kept_types, (
            f"{dropped} must be dropped by REL_MAP_5; got {kept_types}"
        )
