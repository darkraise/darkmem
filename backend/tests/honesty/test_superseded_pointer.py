"""honesty/superseded-pointer — ``status='superseded'`` without a pointer is impossible.

A superseded memory is never dropped from the corpus; it is retained, labelled,
and reachable through its lineage (doc 01 §8). The pointer IS the lineage, so a
superseded row without one is a claim the UI shows as retired with nothing to
retire it in favour of — the exact silent-dishonesty state ``chk_superseded_has
_pointer`` exists to make unrepresentable. The guard is asserted here at the
database, not at the service layer, because every write path shares it and only
the constraint covers raw SQL.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models.memory import Memory
from app.services.supersession import detect_supersessions

CONSTRAINT = "chk_superseded_has_pointer"


def _mem(**overrides) -> Memory:
    base = dict(
        id=uuid.uuid4(),
        content="honesty",
        source="test",
        importance=0.5,
        metadata_={},
        project="honesty-superseded-pointer",
        status="active",
    )
    base.update(overrides)
    return Memory(**base)


@pytest.mark.asyncio
async def test_insert_superseded_without_a_pointer_is_rejected(session):
    with pytest.raises(IntegrityError) as excinfo:
        session.add(_mem(status="superseded"))
        await session.flush()
    assert CONSTRAINT in str(excinfo.value)


@pytest.mark.asyncio
async def test_promoting_to_superseded_without_a_pointer_is_rejected(session):
    row = _mem()
    session.add(row)
    await session.flush()

    with pytest.raises(IntegrityError) as excinfo:
        await session.execute(
            text(
                "UPDATE memories SET status='superseded' "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": str(row.id)},
        )
    assert CONSTRAINT in str(excinfo.value)


@pytest.mark.asyncio
async def test_clearing_a_live_pointer_is_rejected(session):
    successor = _mem()
    session.add(successor)
    await session.flush()
    retired = _mem(status="superseded", superseded_by=successor.id)
    session.add(retired)
    await session.flush()

    with pytest.raises(IntegrityError) as excinfo:
        await session.execute(
            text(
                "UPDATE memories SET superseded_by=NULL WHERE id = CAST(:id AS uuid)"
            ),
            {"id": str(retired.id)},
        )
    assert CONSTRAINT in str(excinfo.value)


@pytest.mark.asyncio
async def test_the_detector_flips_status_and_pointer_in_one_statement(session):
    """The positive half: the only path that produces 'superseded' sets both."""
    now = datetime.now(timezone.utc)
    project = "honesty-superseded-pointer"
    candidate = _mem(technologies=["promtail"], created_at=now - timedelta(days=1))
    successor = _mem(technologies=["alloy"], created_at=now)
    session.add_all([candidate, successor])
    await session.flush()

    flipped = await detect_supersessions(
        session,
        new_memory_id=successor.id,
        new_memory_text="We replaced promtail with alloy.",
        new_memory_created_at=successor.created_at,
        project=project,
        new_relations=[{"type": "REPLACES", "source": "alloy", "target": "promtail"}],
        now=now,
    )

    assert flipped == [candidate.id]
    row = (
        await session.execute(
            text(
                "SELECT status, superseded_by FROM memories "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": str(candidate.id)},
        )
    ).one()
    assert row == (("superseded"), successor.id)


@pytest.mark.asyncio
async def test_no_superseded_row_in_the_corpus_lacks_a_pointer(session):
    """The standing corpus-wide statement of the rule."""
    orphans = (
        await session.execute(
            text(
                "SELECT count(*) FROM memories "
                "WHERE status = 'superseded' AND superseded_by IS NULL"
            )
        )
    ).scalar_one()
    assert orphans == 0
