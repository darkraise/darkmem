"""Phase 5 graph writes from concurrent memories take row locks in one order.

Each memory's savepoint B holds its entity and relation upserts until the
memory's commit, so two writers that upsert shared rows in different orders
can deadlock, and the loser reports ``graph=error``. A strip that locks a
memory's prior rows before its sorted upserts can still close a cycle with a
second writer, so a deadlocked savepoint B is retried.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.repositories.graph import PostgresGraphRepository
from tests.test_pipeline_savepoints import VECTOR, savepoint_bed

NAMES = ("phase5-alpha", "phase5-beta")
SWAP_NAMES = ("phase5-xi", "phase5-zeta")
REL_NAMES = ("phase5-rel-a", "phase5-rel-b", "phase5-rel-c")
PIPELINE_LOGGER = "app.services.pipeline"


def _extraction(order: tuple[str, str]) -> dict:
    return {
        "entities": [{"name": name, "type": "tool"} for name in order],
        "relationships": [
            {"source": NAMES[0], "target": NAMES[1], "type": "USES", "weight": 0.5},
        ],
        "memory_type": "fact",
    }


def _entities_only(names: tuple[str, ...]) -> dict:
    return {
        "entities": [{"name": name, "type": "tool"} for name in names],
        "relationships": [],
        "memory_type": "fact",
    }


def _retry_warnings(caplog, memory_id=None) -> list[str]:
    return [
        record.getMessage() for record in caplog.records
        if record.name == PIPELINE_LOGGER
        and record.levelno == logging.WARNING
        and " of 3" in record.getMessage()
        and (memory_id is None or str(memory_id) in record.getMessage())
    ]


async def _failure_rows(bed) -> int:
    async with bed.factory() as s:
        return (await s.execute(
            text("SELECT count(*) FROM pipeline_failures "
                 "WHERE entity_id = ANY(CAST(:ids AS uuid[]))"),
            {"ids": [str(m) for m in bed.memory_ids]},
        )).scalar_one()


async def _relation_count(bed, index: int) -> int:
    async with bed.factory() as s:
        return (await s.execute(
            text("SELECT count(*) FROM entity_relations "
                 "WHERE CAST(:m AS uuid) = ANY(memory_ids)"),
            {"m": str(bed.memory_ids[index])},
        )).scalar_one()


class _Deadlock(Exception):
    sqlstate = "40P01"


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
                    await asyncio.wait_for(other.wait(), 0.5)
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


@pytest.mark.asyncio
async def test_swapped_prior_and_new_sets_both_commit(setup_database, monkeypatch, caplog):
    async with savepoint_bed(
        ["writer a", "writer b"], "phase5-swap|4", entity_names=SWAP_NAMES,
    ) as bed:
        for index, prior in enumerate(((SWAP_NAMES[1],), (SWAP_NAMES[0],))):
            status = await bed.pipe._write_memory(
                bed.entry(index), VECTOR, bed.fingerprint, bed.fingerprint,
                _entities_only(prior), None, {}, {},
            )
            assert status["graph"] == "ok", status
            assert await bed.entity_names(index) == set(prior)

        stripped = {memory_id: asyncio.Event() for memory_id in bed.memory_ids}
        real_strip = PostgresGraphRepository.delete_by_memory_id

        async def strip_then_wait(self, memory_id):
            result = await real_strip(self, memory_id)
            mine = stripped[memory_id]
            if not mine.is_set():
                mine.set()
                other = next(e for m, e in stripped.items() if m != memory_id)
                with contextlib.suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(other.wait(), 2)
            return result

        monkeypatch.setattr(PostgresGraphRepository, "delete_by_memory_id", strip_then_wait)
        caplog.set_level(logging.WARNING, logger=PIPELINE_LOGGER)

        statuses = await asyncio.gather(*[
            bed.pipe._write_memory(
                bed.entry(index), VECTOR, bed.fingerprint, bed.fingerprint,
                _entities_only(SWAP_NAMES), None, {}, {},
            )
            for index in range(2)
        ])

        assert [status["graph"] for status in statuses] == ["ok", "ok"], statuses
        # Both committing proves the retry only if the two writers really
        # crossed: without a deadlock this would pass with no retry at all.
        assert _retry_warnings(caplog), "the interleaving was missed: no deadlock retry ran"
        for index in range(2):
            assert await bed.entity_names(index) == set(SWAP_NAMES)
        assert await _failure_rows(bed) == 0


@pytest.mark.asyncio
async def test_three_deadlocks_keep_the_vector_and_the_prior_graph(
    setup_database, monkeypatch, caplog
):
    async with savepoint_bed(["deadlocked writer"], "phase5-dead|4") as bed:
        seeded = await bed.pipe._write_memory(
            bed.entry(), VECTOR, bed.fingerprint, bed.fingerprint,
            dict(bed.extraction), None, {}, {},
        )
        assert seeded["graph"] == "ok", seeded
        prior_entities = await bed.entity_names()
        prior_relations = await bed.relation_types()
        assert prior_entities

        calls = 0

        async def deadlocked_strip(self, memory_id):
            nonlocal calls
            calls += 1
            raise DBAPIError("UPDATE entities", {}, _Deadlock("deadlock detected"))

        monkeypatch.setattr(PostgresGraphRepository, "delete_by_memory_id", deadlocked_strip)
        caplog.set_level(logging.WARNING, logger=PIPELINE_LOGGER)

        status = await bed.pipe._write_memory(
            bed.entry(), VECTOR, bed.fingerprint, bed.fingerprint,
            _entities_only(("phase5-dead-new",)), None, {}, {},
        )

        assert status["graph"] == "error", status
        assert "40P01" in status["error"]
        assert calls == 3
        assert await bed.embedding_rows() == 1
        assert await bed.entity_names() == prior_entities
        assert await bed.relation_types() == prior_relations
        warnings = _retry_warnings(caplog, bed.memory_id)
        assert len(warnings) == 2, warnings
        assert "attempt 1 of 3" in warnings[0]
        assert "attempt 2 of 3" in warnings[1]


@pytest.mark.asyncio
async def test_a_non_deadlock_graph_error_runs_savepoint_b_once(
    setup_database, monkeypatch, caplog
):
    async with savepoint_bed(["failing writer"], "phase5-once|4") as bed:
        calls = 0

        async def failing_strip(self, memory_id):
            nonlocal calls
            calls += 1
            raise RuntimeError("graph boom")

        monkeypatch.setattr(PostgresGraphRepository, "delete_by_memory_id", failing_strip)
        caplog.set_level(logging.WARNING, logger=PIPELINE_LOGGER)

        status = await bed.pipe._write_memory(
            bed.entry(), VECTOR, bed.fingerprint, bed.fingerprint,
            dict(bed.extraction), None, {}, {},
        )

        assert status["graph"] == "error", status
        assert "40P01" not in status["error"]
        assert calls == 1
        assert _retry_warnings(caplog) == []


@pytest.mark.asyncio
async def test_shared_relations_written_in_opposite_order_both_commit(
    setup_database, monkeypatch, caplog
):
    async with savepoint_bed(
        ["relation seed", "first relation writer", "second relation writer"],
        "phase5-rels|4", entity_names=REL_NAMES,
    ) as bed:
        seeded = await bed.pipe._write_memory(
            bed.entry(0), VECTOR, bed.fingerprint, bed.fingerprint,
            _entities_only(REL_NAMES), None, {}, {},
        )
        assert seeded["graph"] == "ok", seeded

        a, b, c = REL_NAMES
        relations = (
            {"source": a, "target": b, "type": "USES", "weight": 0.5},
            {"source": a, "target": c, "type": "DEPENDS_ON", "weight": 0.5},
        )
        writers = bed.memory_ids[1:]
        first_relation = {memory_id: asyncio.Event() for memory_id in writers}
        real_relate = PostgresGraphRepository.create_relationship

        async def relate_then_pause(self, *args, **kwargs):
            created = await real_relate(self, *args, **kwargs)
            memory_id = kwargs["memory_id"]
            mine = first_relation[memory_id]
            if not mine.is_set():
                mine.set()
                other = next(e for m, e in first_relation.items() if m != memory_id)
                with contextlib.suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(other.wait(), 0.5)
            return created

        monkeypatch.setattr(PostgresGraphRepository, "create_relationship", relate_then_pause)
        caplog.set_level(logging.WARNING, logger=PIPELINE_LOGGER)

        statuses = await asyncio.gather(*[
            bed.pipe._write_memory(
                bed.entry(index), VECTOR, bed.fingerprint, bed.fingerprint,
                {"entities": [], "relationships": list(order), "memory_type": "fact"},
                None, {}, {},
            )
            for index, order in ((1, relations), (2, tuple(reversed(relations))))
        ])

        assert [status["graph"] for status in statuses] == ["ok", "ok"], statuses
        for index in (1, 2):
            assert await bed.relation_types(index) == {"USES", "DEPENDS_ON"}
            assert await _relation_count(bed, index) == 2
        assert _retry_warnings(caplog) == []
