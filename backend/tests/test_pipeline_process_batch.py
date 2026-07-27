"""End-to-end ``ProcessingPipeline.process_batch`` integration tests.

This file was a docstring-only placeholder for two passes. Both defects that
escaped in the meantime were Phase-1-failure-path defects — most recently a
journal argument bound inside savepoint A, which a failed Phase 1 skips
entirely, so every memory in the batch took an ``UnboundLocalError`` instead of
an outcome while the backend floor stayed green. The three difficulties the
placeholder cited are solved here rather than deferred again:

* ``process_batch`` commits through its own ``session_factory``, so these tests
  drive a real committing factory bound to ``test_engine`` and tear their rows
  down by hand instead of relying on the conftest ``session`` fixture's
  rollback. Rows in ``events`` are the exception — that table is append-only by
  trigger, so the session-end schema reset is its only cleanup.
* ``embedder_registry._known`` is process-global, so every fingerprint used
  here is unique to its test and ``embedder_registry.forget`` runs in teardown.
* The embed and extraction calls are mocked (``tests.test_pipeline_phase1``
  holds the shared harness); everything below them — the partitions, the graph,
  the failure journal, the events journal — is the real thing against the real
  database.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.services.embedder_registry import child_table
from app.services.pipeline import _flag_cache_reset
from tests.conftest import test_engine
from tests.test_pipeline_phase1 import (
    FakeEmbedder,
    cleanup,
    make_pipeline,
    seed_memories,
)

EXTRACTION = {
    "entities": [
        {"name": "BatchTool", "type": "tool"},
        {"name": "BatchLib", "type": "tool"},
    ],
    "relationships": [
        {"source": "BatchTool", "target": "BatchLib", "type": "USES", "weight": 0.8},
    ],
    "memory_type": "fact",
    "summary": "a batch summary",
    "emotions": [],
    "flags": [],
}
ENTITY_NAMES = ["BatchTool", "BatchLib"]


async def extracted_outcomes(factory, memory_ids) -> dict[str, str]:
    async with factory() as s:
        rows = (await s.execute(
            text("SELECT object_id, payload->>'outcome' FROM events "
                 "WHERE event_type = 'extracted' "
                 "AND object_id = ANY(CAST(:ids AS uuid[]))"),
            {"ids": [str(m) for m in memory_ids]},
        )).all()
    return {str(object_id): outcome for object_id, outcome in rows}


@pytest.mark.asyncio
async def test_process_batch_writes_memory_and_reports_completion(
    setup_database, monkeypatch
):
    fingerprint = "batch-happy|4"
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    contents = ["batchtool uses batchlib", "batchtool is configured once"]
    memory_ids = await seed_memories(factory, contents)

    try:
        pipe = make_pipeline(
            factory, FakeEmbedder([fingerprint]), EXTRACTION, monkeypatch
        )
        results = await pipe.process_batch([
            {"memory_id": mem_id, "content": content, "source": "api"}
            for mem_id, content in zip(memory_ids, contents)
        ])

        assert len(results) == len(memory_ids)
        for status in results:
            assert status["embed"] == "ok"
            assert status["extract"] == "ok"
            assert status["vector"] == "ok"
            assert status["graph"] == "ok"
            assert status["error"] is None

        child = child_table("memory_embeddings", fingerprint)
        async with factory() as s:
            embedded = (await s.execute(
                text(f"SELECT count(*) FROM {child} "
                     f"WHERE memory_id = ANY(CAST(:ids AS uuid[]))"),
                {"ids": [str(m) for m in memory_ids]},
            )).scalar_one()
            entities = (await s.execute(
                text("SELECT name FROM entities "
                     "WHERE name = ANY(CAST(:names AS text[])) ORDER BY name"),
                {"names": [n.lower() for n in ENTITY_NAMES]},
            )).scalars().all()
            relations = (await s.execute(
                text("SELECT count(*) FROM entity_relations WHERE rel_type = 'USES'")
            )).scalar_one()
            enriched = (await s.execute(
                text("SELECT summary, technologies FROM memories WHERE id = CAST(:m AS uuid)"),
                {"m": str(memory_ids[0])},
            )).first()
            open_failures = (await s.execute(
                text("SELECT count(*) FROM pipeline_failures "
                     "WHERE entity_id = ANY(CAST(:ids AS uuid[])) "
                     "AND resolved_at IS NULL"),
                {"ids": [str(m) for m in memory_ids]},
            )).scalar_one()

        assert embedded == len(memory_ids)
        assert entities == ["batchlib", "batchtool"]
        assert relations >= 1
        assert enriched[0] == "a batch summary"
        assert sorted(enriched[1]) == ["batchlib", "batchtool"]
        assert open_failures == 0

        outcomes = await extracted_outcomes(factory, memory_ids)
        assert set(outcomes) == {str(m) for m in memory_ids}
        assert set(outcomes.values()) == {"completed"}
    finally:
        await cleanup(factory, memory_ids, [fingerprint], ENTITY_NAMES)


@pytest.mark.asyncio
async def test_phase_one_failure_marks_every_memory_and_skips_writes(
    setup_database, monkeypatch
):
    """Done-when 1: an embed failure marks the whole batch and writes nothing.

    Every assertion here is a live one. ``embed == "error"`` (rather than the
    ``"unknown"`` the exception-normalisation path stamps) is what distinguishes
    a real per-memory outcome from an exception that escaped ``_write_memory``,
    and the ``extracted`` journal row proves the per-memory journal ran on a
    path where no savepoint opened at all.
    """
    fingerprint = "batch-embedfail|4"
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    contents = ["embed fails one", "embed fails two", "embed fails three"]
    memory_ids = await seed_memories(factory, contents)

    try:
        embedder = FakeEmbedder([fingerprint])
        embedder.fail_calls = {0}
        pipe = make_pipeline(factory, embedder, EXTRACTION, monkeypatch)
        results = await pipe.process_batch([
            {"memory_id": mem_id, "content": content, "source": "api"}
            for mem_id, content in zip(memory_ids, contents)
        ])

        assert len(results) == len(memory_ids)
        for status in results:
            assert isinstance(status, dict)
            assert status["embed"] == "error"
            assert status["vector"] == "skipped"
            assert status["graph"] == "skipped"

        async with factory() as s:
            partition = (await s.execute(
                text("SELECT to_regclass(:t)"),
                {"t": child_table("memory_embeddings", fingerprint)},
            )).scalar_one()
            registered = (await s.execute(
                text("SELECT 1 FROM embedders WHERE fingerprint = :fp"),
                {"fp": fingerprint},
            )).first()
            entities = (await s.execute(
                text("SELECT count(*) FROM entities "
                     "WHERE name = ANY(CAST(:names AS text[]))"),
                {"names": [n.lower() for n in ENTITY_NAMES]},
            )).scalar_one()
            crossrefs = (await s.execute(
                text("SELECT count(*) FROM memory_crossrefs "
                     "WHERE memory_id = ANY(CAST(:ids AS uuid[]))"),
                {"ids": [str(m) for m in memory_ids]},
            )).scalar_one()
            failures = (await s.execute(
                text("SELECT count(*) FROM pipeline_failures "
                     "WHERE entity_id = ANY(CAST(:ids AS uuid[])) "
                     "AND resolved_at IS NULL"),
                {"ids": [str(m) for m in memory_ids]},
            )).scalar_one()

        assert partition is None
        assert registered is None
        assert entities == 0
        assert crossrefs == 0
        assert failures == len(memory_ids)

        outcomes = await extracted_outcomes(factory, memory_ids)
        assert set(outcomes) == {str(m) for m in memory_ids}
    finally:
        await cleanup(factory, memory_ids, [fingerprint], ENTITY_NAMES)
