"""Reembed counts must not crash when the active partition does not exist yet.

Right after an embedder rotation (or on a fresh install where the active
fingerprint has never been embedded), the per-fingerprint child table does not
exist. count_missing left-anti-joins that table, so it raised UndefinedTable and
500'd GET /reembed/obsolete-counts. An absent partition means every row is
missing from it.

The count is exact in that state; the *listing* is withheld, because a filter
that cannot single any row out would page a content preview of the whole table.
`tests/test_content_surface_scoping.py` owns that decision and its reasoning.
"""
from __future__ import annotations

import uuid

from app.models.memory import Memory
from app.services.reembed import ReembedService


async def test_count_missing_treats_absent_partition_as_all_missing(session):
    session.add(
        Memory(id=uuid.uuid4(), content="x", source="test", importance=0.5, metadata_={})
    )
    await session.flush()

    svc = ReembedService(session)
    counts = await svc.count_missing("ghostmodel|512")  # partition never created

    assert counts["memories"] >= 1


async def test_list_obsolete_memories_handles_absent_partition(session):
    session.add(
        Memory(id=uuid.uuid4(), content="y", source="test", importance=0.5, metadata_={})
    )
    await session.flush()

    svc = ReembedService(session)
    items, total, partition_missing = await svc.list_obsolete_memories("ghostmodel|512", limit=10)

    assert total >= 1
    assert partition_missing is True
    assert items == []
