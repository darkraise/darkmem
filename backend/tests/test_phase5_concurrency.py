"""Phase 5 graph writes from concurrent memories take row locks in one order.

Each memory's savepoint B holds its entity and relation upserts until the
memory's commit, so two writers that upsert shared rows in different orders
can deadlock, and the loser reports ``graph=error``.
"""
from __future__ import annotations

import asyncio
import contextlib

import pytest

from app.repositories.graph import PostgresGraphRepository
from tests.test_pipeline_savepoints import VECTOR, savepoint_bed

NAMES = ("phase5-alpha", "phase5-beta")


def _extraction(order: tuple[str, str]) -> dict:
    return {
        "entities": [{"name": name, "type": "tool"} for name in order],
        "relationships": [
            {"source": NAMES[0], "target": NAMES[1], "type": "USES", "weight": 0.5},
        ],
        "memory_type": "fact",
    }


@pytest.mark.asyncio
async def test_shared_entities_written_in_opposite_order_both_commit(
    setup_database, monkeypatch
):
    async with savepoint_bed(
        ["first writer", "second writer"], "phase5-order|4", entity_names=NAMES,
    ) as bed:
        first_upsert = {memory_id: asyncio.Event() for memory_id in bed.memory_ids}
        real_create = PostgresGraphRepository.create_entity

        async def create_then_pause(self, name, entity_type, properties, memory_id):
            created = await real_create(self, name, entity_type, properties, memory_id)
            mine = first_upsert[memory_id]
            if not mine.is_set():
                mine.set()
                other = next(e for m, e in first_upsert.items() if m != memory_id)
                with contextlib.suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(other.wait(), 3)
            return created

        monkeypatch.setattr(PostgresGraphRepository, "create_entity", create_then_pause)

        statuses = await asyncio.gather(*[
            bed.pipe._write_memory(
                bed.entry(index), VECTOR, bed.fingerprint, bed.fingerprint,
                _extraction(order), None, {}, {},
            )
            for index, order in enumerate((NAMES, tuple(reversed(NAMES))))
        ])

        assert [status["graph"] for status in statuses] == ["ok", "ok"], statuses
        for index in range(2):
            assert await bed.entity_names(index) == set(NAMES)
            assert await bed.relation_types(index) == {"USES"}
