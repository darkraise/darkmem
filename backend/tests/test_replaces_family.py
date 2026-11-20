"""Tests for the REPLACES-family collapse (REPLACES / IMPROVES_ON / BUILDS_ON).

The replacement family is the set of relation types that all describe
"X supersedes Y". ``family_key`` maps every member to the canonical
``"REPLACES"`` bucket; this is what lets the rescue/dedup layers treat an
LLM-emitted ``IMPROVES_ON`` and a rescue-emitted ``REPLACES`` for the same
pair as duplicates.

Boundary note (asserted explicitly below): the collapse is a dedup/equivalence
mechanism, NOT a type rewrite. The stored ``rel_type`` stays whatever the
extractor emitted; the family only governs which relations are *equivalent* —
in the extraction-layer dedup keys, in ``_drop_uses_when_replaces_exists``, and
in the supersession trigger, which fires for any family member because they all
assert "X supersedes Y" (doc 08 §2.1).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models.memory import Memory
from app.services.relations import REPLACES_FAMILY, family_key
from app.services.supersession import detect_supersessions


# ── family_key bucketing ──────────────────────────────────────────────


def test_family_key_collapses_improves_on_to_replaces():
    assert family_key("IMPROVES_ON") == "REPLACES"


def test_family_key_collapses_builds_on_to_replaces():
    assert family_key("BUILDS_ON") == "REPLACES"


def test_family_key_keeps_replaces_as_replaces():
    assert family_key("REPLACES") == "REPLACES"


def test_family_key_is_case_insensitive():
    assert family_key("improves_on") == "REPLACES"
    assert family_key("builds_on") == "REPLACES"


def test_family_key_passes_through_unrelated_types():
    assert family_key("USES") == "USES"
    assert family_key("DEPENDS_ON") == "DEPENDS_ON"


def test_replaces_family_membership():
    assert {"REPLACES", "IMPROVES_ON", "BUILDS_ON"} == set(REPLACES_FAMILY)


# ── observable effect: family collapse in USES-dedup ──────────────────


def test_improves_on_blocks_uses_dedup_like_replaces():
    """An IMPROVES_ON between a pair suppresses a redundant USES on that pair,
    proving IMPROVES_ON is treated as part of the REPLACES family."""
    from app.services.extraction_clean import _drop_uses_when_replaces_exists

    rels = [
        {"source": "alloy", "target": "promtail", "type": "IMPROVES_ON"},
        {"source": "promtail", "target": "alloy", "type": "USES"},
    ]
    out = _drop_uses_when_replaces_exists(rels)
    assert len(out) == 1
    assert out[0]["type"] == "IMPROVES_ON"


def test_builds_on_blocks_uses_dedup_like_replaces():
    from app.services.extraction_clean import _drop_uses_when_replaces_exists

    rels = [
        {"source": "phoenix", "target": "triton", "type": "BUILDS_ON"},
        {"source": "triton", "target": "phoenix", "type": "USES"},
    ]
    out = _drop_uses_when_replaces_exists(rels)
    assert len(out) == 1
    assert out[0]["type"] == "BUILDS_ON"


# ── supersession trigger: every family member flips a candidate ───────


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


@pytest.mark.asyncio
async def test_detect_supersessions_triggers_on_literal_replaces(session):
    """A literal REPLACES relation flips the same-project active candidate."""
    project = "replaces-family-test"
    new_id = uuid.uuid4()
    old = Memory(
        **_minimal_memory_kwargs(content="we use promtail for log shipping"),
        project=project,
        technologies=["promtail"],
        status="active",
    )
    new = Memory(
        id=new_id,
        **_minimal_memory_kwargs(content="we switched from promtail to alloy"),
        project=project,
        technologies=["alloy"],
        status="active",
    )
    session.add_all([old, new])
    await session.flush()

    flipped = await detect_supersessions(
        session,
        new_memory_id=new_id,
        new_memory_text="we switched from promtail to alloy",
        new_memory_created_at=datetime.now(timezone.utc) + timedelta(seconds=1),
        project=project,
        new_relations=[{"type": "REPLACES", "source": "alloy", "target": "promtail"}],
    )
    assert flipped == [old.id]


@pytest.mark.asyncio
async def test_detect_supersessions_triggers_on_raw_improves_on(session):
    """A raw ``IMPROVES_ON`` supersedes exactly as a ``REPLACES`` does.

    The detector matches the family bucket, not the literal type: the three
    members all assert "X supersedes Y", so an extraction that emitted
    ``IMPROVES_ON`` must not leave the predecessor standing as active while an
    otherwise identical ``REPLACES`` retires it.
    """
    project = "replaces-family-test"
    new_id = uuid.uuid4()
    old = Memory(
        **_minimal_memory_kwargs(content="we use promtail for log shipping"),
        project=project,
        technologies=["promtail"],
        status="active",
    )
    new = Memory(
        id=new_id,
        **_minimal_memory_kwargs(content="alloy improves on promtail"),
        project=project,
        technologies=["alloy"],
        status="active",
    )
    session.add_all([old, new])
    await session.flush()

    flipped = await detect_supersessions(
        session,
        new_memory_id=new_id,
        new_memory_text="alloy improves on promtail",
        new_memory_created_at=datetime.now(timezone.utc) + timedelta(seconds=1),
        project=project,
        new_relations=[{"type": "IMPROVES_ON", "source": "alloy", "target": "promtail"}],
    )
    assert flipped == [old.id]
