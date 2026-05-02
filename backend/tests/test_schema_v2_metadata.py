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
        new_memory_created_at=datetime.now(timezone.utc) + timedelta(seconds=1),
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
        new_memory_created_at=datetime.now(timezone.utc) + timedelta(seconds=1),
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
        new_memory_created_at=datetime.now(timezone.utc) + timedelta(seconds=1),
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
        new_memory_created_at=datetime.now(timezone.utc) + timedelta(seconds=1),
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
        new_memory_created_at=datetime.now(timezone.utc) + timedelta(seconds=1),
        project=project,
        new_relations=[{"type": "REPLACES", "source": "valkey", "target": "redis"}],
    )

    assert flipped == []
    await session.refresh(unrelated)
    assert unrelated.status == "active"


@pytest.mark.asyncio
async def test_detect_supersessions_skips_newer_candidates(session):
    """When two memories carry the same REPLACES relation and both get
    processed (e.g., during a reprocess-all), the older one must NOT
    supersede the newer one. Without the strict-older guard the two
    flip each other to ``status='superseded'`` and both vanish from the
    default Memories view, which is the production bug from
    2026-05-01."""
    project = "darkmem-test"
    older_created = datetime.now(timezone.utc) - timedelta(hours=1)
    older = Memory(
        **_minimal_memory_kwargs(content="darkmem migrated from qdrant to pgvector"),
        project=project,
        status="active",
        technologies=["pgvector", "qdrant"],
    )
    newer = Memory(
        **_minimal_memory_kwargs(content="darkmem switched from qdrant to pgvector"),
        project=project,
        status="active",
        technologies=["pgvector", "qdrant"],
    )
    session.add_all([older, newer])
    await session.flush()
    older.created_at = older_created
    await session.flush()

    # Re-process the OLDER memory: it carries REPLACES too, but it must
    # not supersede the newer memory.
    flipped = await detect_supersessions(
        session,
        new_memory_id=older.id,
        new_memory_text=older.content,
        new_memory_created_at=older.created_at,
        project=project,
        new_relations=[{"type": "REPLACES", "source": "pgvector", "target": "qdrant"}],
    )

    assert flipped == []
    await session.refresh(newer)
    assert newer.status == "active"


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


# --- Relation taxonomy: full 16-type set is preserved end-to-end -----------

def test_relation_types_v2_matches_canonical_set():
    """``RELATION_TYPES_V2`` is the storage-side alias for the canonical
    relation type list. After Tier 1 they're the same set — anything the
    LLM emits is stored as-is, no collapse."""
    from app.services.relations import RELATION_TYPES_V2
    from app.taxonomy import RELATIONSHIP_TYPES

    assert set(RELATION_TYPES_V2) == set(RELATIONSHIP_TYPES)


def test_canonical_relation_types_include_expanded_set():
    """Lock the post-expansion type list so future taxonomy drift is
    intentional. If a type is added or removed, this test must be
    updated alongside the prompt."""
    from app.taxonomy import RELATIONSHIP_TYPES

    expected = {
        # Composition / dependency
        "USES", "DEPENDS_ON", "HAS_PART", "IMPLEMENTS", "EXTENDS",
        # Replacement / evolution
        "REPLACES", "IMPROVES_ON",
        # Identity
        "IS_A",
        # Hosting
        "DEPLOYED_ON",
        # Causality
        "CAUSES",
        # Attribution / temporal
        "AUTHORED_BY", "HAPPENED_ON",
        # Reference
        "MENTIONS", "CITES", "INSPIRED_BY",
        # Catch-all
        "RELATED_TO",
    }
    assert set(RELATIONSHIP_TYPES) == expected


def test_clean_extraction_preserves_specific_predicates():
    """``clean_extraction`` no longer collapses 10-type to 5-type. Specific
    predicates like DEPENDS_ON, HAS_PART, AUTHORED_BY, HAPPENED_ON now
    survive end-to-end."""
    from app.services.extraction import clean_extraction

    result = {
        "memory_type": "fact",
        "importance": 0.5,
        "entities": [
            {"name": "pgvector", "type": "tool"},
            {"name": "postgres", "type": "database"},
            {"name": "Traag et al.", "type": "person"},
            {"name": "Leiden", "type": "algorithm"},
        ],
        "relationships": [
            {"source": "pgvector", "target": "postgres", "type": "DEPENDS_ON"},
            {"source": "pgvector", "target": "postgres", "type": "HAS_PART"},
            {"source": "Leiden", "target": "Traag et al.", "type": "AUTHORED_BY"},
        ],
    }
    cleaned = clean_extraction(result, content="pgvector depends on postgres")

    kept_types = {r["type"] for r in cleaned["relationships"]}
    # Specific predicates survive — no longer demoted to USES.
    assert "DEPENDS_ON" in kept_types
    assert "HAS_PART" in kept_types
    assert "AUTHORED_BY" in kept_types


def test_legacy_relation_labels_normalize_to_canonical():
    """Legacy labels still in old DB rows or external sources route to
    the canonical set via ``normalize_relation_type``."""
    from app.taxonomy import normalize_relation_type

    cases = {
        "BUILDS_ON": "IMPROVES_ON",
        "RUNS_ON": "DEPLOYED_ON",
        "CONFIGURES": "USES",
        "PUBLISHED_IN": "AUTHORED_BY",
        "VISITED": "HAPPENED_ON",
        "KNOWS": "RELATED_TO",
        "totally_unknown": "RELATED_TO",
    }
    for raw, expected in cases.items():
        assert normalize_relation_type(raw) == expected, raw
