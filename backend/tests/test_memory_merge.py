"""Merging one memory into another deletes the source, so it is a delete path.

Two things follow. Memories the source superseded must be demoted first, or the
delete trips ``chk_superseded_has_pointer`` and the merge answers 500. And a
merge whose target is its own source has nothing to merge into: taking it
through the delete would erase the memory.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.memory import Memory
from app.services.memory import MemoryService, SelfMergeError
from tests.conftest import test_engine


def _factory() -> async_sessionmaker:
    return async_sessionmaker(test_engine, expire_on_commit=False)


async def _row(factory, memory_id: uuid.UUID):
    async with factory() as s:
        return (
            await s.execute(
                text(
                    "SELECT content, status, superseded_by FROM memories "
                    "WHERE id = CAST(:id AS uuid)"
                ),
                {"id": str(memory_id)},
            )
        ).one_or_none()


async def _teardown(factory, ids) -> None:
    async with factory() as s:
        await s.execute(
            text(
                "UPDATE memories SET status='deprecated', superseded_by=NULL "
                "WHERE superseded_by = ANY(CAST(:ids AS uuid[]))"
            ),
            {"ids": [str(i) for i in ids]},
        )
        await s.execute(
            text("DELETE FROM memories WHERE id = ANY(CAST(:ids AS uuid[]))"),
            {"ids": [str(i) for i in ids]},
        )
        await s.commit()


@pytest.mark.asyncio
async def test_merging_a_superseder_demotes_what_it_superseded(setup_database):
    factory = _factory()
    source_id, target_id, dependent_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    async with factory() as s:
        s.add_all([
            Memory(id=source_id, content="valkey replaced redis", source="test"),
            Memory(id=target_id, content="cache layer notes", source="test"),
        ])
        await s.flush()
        s.add(Memory(
            id=dependent_id, content="we cache in redis", source="test",
            status="superseded", superseded_by=source_id,
        ))
        await s.commit()
    try:
        async with factory() as s:
            merged = await MemoryService(s).merge_memories(source_id, target_id, api_key_id=None)

        assert merged is not None
        assert merged.content == "cache layer notes\n\n---\n\nvalkey replaced redis"
        assert await _row(factory, source_id) is None
        assert (await _row(factory, dependent_id))[1:] == ("deprecated", None)
    finally:
        await _teardown(factory, [source_id, target_id, dependent_id])


@pytest.mark.asyncio
async def test_merging_a_memory_into_itself_is_refused_and_keeps_it(setup_database):
    factory = _factory()
    memory_id = uuid.uuid4()
    async with factory() as s:
        s.add(Memory(id=memory_id, content="only copy", source="test"))
        await s.commit()
    try:
        async with factory() as s:
            with pytest.raises(SelfMergeError):
                await MemoryService(s).merge_memories(memory_id, memory_id, api_key_id=None)

        assert (await _row(factory, memory_id))[0] == "only copy"
    finally:
        await _teardown(factory, [memory_id])
