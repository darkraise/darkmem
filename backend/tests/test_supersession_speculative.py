"""The speculative-replacement gate must be scoped to the REPLACES clause.

A whole-memory check means one 'might' anywhere suppresses every supersession
for that memory, so a definitive replacement is lost whenever the memory also
contains an unrelated speculative aside.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models.memory import Memory
from app.services.supersession import detect_supersessions


def _mk(**ov) -> Memory:
    base = dict(content="t", source="test", source_agent=None, memory_type=None,
                importance=0.5, metadata_={})
    base.update(ov)
    return Memory(**base)


@pytest.mark.asyncio
async def test_supersedes_despite_unrelated_speculation(session):
    project = "spec-test"
    new_id = uuid.uuid4()
    old = _mk(content="we use redis", project=project, technologies=["redis"], status="active")
    new = _mk(id=new_id, content="x", project=project, technologies=["valkey"], status="active")
    session.add_all([old, new])
    await session.flush()

    # Definitive replacement of redis, plus an unrelated speculative aside.
    text = "We definitively replaced redis with valkey. We might also try kafka later."
    flipped = await detect_supersessions(
        session, new_memory_id=new_id, new_memory_text=text,
        new_memory_created_at=datetime.now(timezone.utc) + timedelta(seconds=1),
        project=project,
        new_relations=[{"type": "REPLACES", "source": "valkey", "target": "redis"}],
    )
    assert flipped == [old.id]


@pytest.mark.asyncio
async def test_skips_target_in_speculative_clause(session):
    project = "spec-test-2"
    new_id = uuid.uuid4()
    old = _mk(content="we use redis", project=project, technologies=["redis"], status="active")
    new = _mk(id=new_id, content="x", project=project, technologies=["valkey"], status="active")
    session.add_all([old, new])
    await session.flush()

    text = "We might replace redis with valkey."
    flipped = await detect_supersessions(
        session, new_memory_id=new_id, new_memory_text=text,
        new_memory_created_at=datetime.now(timezone.utc) + timedelta(seconds=1),
        project=project,
        new_relations=[{"type": "REPLACES", "source": "valkey", "target": "redis"}],
    )
    assert flipped == []
