"""The events writer and the journaling convention (T1.07).

audit_log is dropped by the baseline (doc 04 §7/§8.1); ``events`` is the sole
audit substrate from day one. T0.12c built the narrow writer to keep the
security audit trail alive; this module also covers T1.07's generalisation:
capture, extraction/pipeline outcomes, and supersession all route through the
same ``record_event`` helper (doc 05 §2.3), and a journal failure must never
fail the operation it journals.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.models.memory import Memory
from app.schemas.memory import MemoryCreate
from app.services.events import record_event
from app.services.memory import MemoryService
from app.services.supersession import detect_supersessions


@pytest.mark.asyncio
async def test_record_event_writes_a_row(session):
    await record_event(
        session,
        event_type="auth_login_success",
        object_type="system",
        payload={"ip": "10.0.0.1"},
    )
    await session.commit()
    row = (
        await session.execute(
            text("SELECT event_type, object_type, payload FROM events "
                 "WHERE event_type = 'auth_login_success'")
        )
    ).one()
    assert row.event_type == "auth_login_success"
    assert row.object_type == "system"
    assert row.payload == {"ip": "10.0.0.1"}


@pytest.mark.asyncio
async def test_record_event_defaults_payload_to_empty_object(session):
    await record_event(session, event_type="auth_logout", object_type="system")
    await session.commit()
    payload = (
        await session.execute(
            text("SELECT payload FROM events WHERE event_type = 'auth_logout'")
        )
    ).scalar_one()
    assert payload == {}


# ── T1.07: capture, extraction/pipeline outcome, supersession ───────


@pytest.mark.asyncio
async def test_capture_writes_a_created_event(session):
    """`MemoryService.create_memory` journals the capture at accept time,
    independent of any downstream extraction outcome — the buffered contract
    (T1.14) writes this event before any flush runs, `wait_process` or not."""
    svc = MemoryService(session, pipeline=None)
    result = await svc.create_memory(
        MemoryCreate(content="capture journals", source="test", project="evt-capture"),
        api_key_id=None,
    )
    memory_id = result.ack.id

    row = (
        await session.execute(
            text(
                "SELECT event_type, object_type, object_id FROM events "
                "WHERE event_type = 'created' AND object_id = CAST(:mid AS uuid)"
            ),
            {"mid": str(memory_id)},
        )
    ).one()
    assert row.event_type == "created"
    assert row.object_type == "memory"
    assert row.object_id == memory_id


@pytest.mark.asyncio
async def test_pipeline_outcome_writes_an_extracted_event_with_payload(setup_database):
    """The flush's per-memory outcome (doc 05 §2.3) gains a durable twin of
    the transient pipeline.completed/partial/failed broadcast.

    ``_write_memory`` opens and commits its own session via
    ``session_factory`` and nests savepoints inside it, so — same as
    ``test_pipeline_savepoints.py`` — it cannot run on the conftest
    ``session`` fixture (which already holds a restarting nested savepoint);
    this drives it against a real committing factory and tears the seeded
    rows down explicitly. ``events`` rows are append-only and are not (and
    cannot be) cleaned up.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.services.embedder_registry import child_table
    from app.services.pipeline import ProcessingPipeline
    from tests.conftest import test_engine

    fp = "evt-writer-outcome|2"
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    child = child_table("memory_embeddings", fp)
    memory_id = uuid.uuid4()

    async with factory() as s:
        await s.execute(
            text(
                "INSERT INTO embedders (fingerprint, model_id, dims, source) "
                "VALUES (:fp, 'm', 2, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
            ),
            {"fp": fp},
        )
        await s.execute(text(
            f"CREATE TABLE IF NOT EXISTS {child} ("
            " memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,"
            " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
            " embedding vector(2) NOT NULL,"
            " payload JSONB NOT NULL DEFAULT '{}'::jsonb,"
            " PRIMARY KEY (memory_id, fingerprint))"
        ))
        s.add(Memory(
            id=memory_id, content="extraction journals", source="test", source_agent=None,
            memory_type=None, importance=0.5, metadata_={}, project="evt-extract",
        ))
        await s.commit()

    try:
        pipeline = ProcessingPipeline(object(), factory)
        status = await pipeline._write_memory(
            entry={
                "memory_id": memory_id, "content": "extraction journals", "source": "test",
                "tags": [], "memory_type": None, "created_at": "",
            },
            vector=[0.1, 0.2],
            content_fingerprint=fp,
            entity_fingerprint=fp,
            extraction={"entities": [], "relationships": []},
            llm_classification=None,
            name_to_embedding={},
            canonical_map={},
        )
        assert status["vector"] == "ok"
        assert status["graph"] == "ok"

        async with factory() as s:
            row = (
                await s.execute(
                    text(
                        "SELECT event_type, object_type, project, payload FROM events "
                        "WHERE event_type = 'extracted' AND object_id = CAST(:mid AS uuid)"
                    ),
                    {"mid": str(memory_id)},
                )
            ).one()
        assert row.event_type == "extracted"
        assert row.object_type == "memory"
        assert row.project == "evt-extract"
        assert row.payload["outcome"] == "completed"
        assert row.payload["entities_count"] == 0
    finally:
        async with factory() as s:
            await s.execute(text("DELETE FROM memories WHERE id = :id"), {"id": str(memory_id)})
            await s.execute(text(f"DROP TABLE IF EXISTS {child}"))
            await s.execute(text("DELETE FROM embedders WHERE fingerprint = :fp"), {"fp": fp})
            await s.commit()


@pytest.mark.asyncio
async def test_supersession_writes_a_superseded_event_with_before_after(session):
    project = "evt-supersede"
    new_id = uuid.uuid4()
    old = Memory(
        content="we use redis", source="test", source_agent=None, memory_type=None,
        importance=0.5, metadata_={}, project=project, technologies=["redis"], status="active",
    )
    new = Memory(
        id=new_id, content="switched to valkey", source="test", source_agent=None,
        memory_type=None, importance=0.5, metadata_={}, project=project,
        technologies=["valkey"], status="active",
    )
    session.add_all([old, new])
    await session.flush()

    flipped = await detect_supersessions(
        session,
        new_memory_id=new_id,
        new_memory_text="We replaced redis with valkey.",
        new_memory_created_at=datetime.now(timezone.utc) + timedelta(seconds=1),
        project=project,
        new_relations=[{"type": "REPLACES", "source": "valkey", "target": "redis"}],
    )
    assert flipped == [old.id]

    row = (
        await session.execute(
            text(
                "SELECT event_type, object_type, object_id, project, payload FROM events "
                "WHERE event_type = 'superseded' AND object_id = CAST(:oid AS uuid)"
            ),
            {"oid": str(old.id)},
        )
    ).one()
    assert row.event_type == "superseded"
    assert row.object_type == "memory"
    assert row.project == project
    assert row.payload["before"] == {"status": "active"}
    assert row.payload["after"] == {"status": "superseded", "superseded_by": str(new_id)}


# ── The load-bearing guarantee: journaling never blocks the hot path ─


@pytest.mark.asyncio
async def test_record_event_swallows_a_real_db_failure(session, caplog):
    """A NULL event_type violates the NOT NULL constraint at the DB level —
    a real journal-write failure, not just a raised Python exception — the
    same class of failure a missing partition or a bad payload would cause.
    record_event must swallow it, log it loudly, and leave the caller's own
    transaction exactly as usable as before the call."""
    with caplog.at_level("ERROR", logger="app.services.events"):
        await record_event(session, event_type=None, object_type="memory")

    assert "failed to journal" in caplog.text

    # The caller's transaction must still be usable — a poisoned transaction
    # would make even a trivial SELECT fail until a full rollback.
    result = await session.execute(text("SELECT 1"))
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_capture_survives_a_journal_failure(session, monkeypatch):
    """End-to-end proof of the third done-when box: a capture that succeeds
    must not fail because its audit write failed. Points record_event's
    INSERT at a table that does not exist — a real DB-level failure, like an
    exhausted partition — and asserts create_memory still returns the
    created memory, with the memory row itself actually committed (proof the
    journal failure did not poison the transaction that persisted it)."""
    import app.services.events as events_module

    broken_insert = text(
        "INSERT INTO events_table_does_not_exist "
        "(event_type, object_type, object_id, project, actor, api_key_id, source, payload) "
        "VALUES (:event_type, :object_type, CAST(:object_id AS uuid), :project, "
        ":actor, CAST(:api_key_id AS uuid), :source, CAST(:payload AS jsonb))"
    )
    monkeypatch.setattr(events_module, "_INSERT", broken_insert)

    svc = MemoryService(session, pipeline=None)
    result = await svc.create_memory(
        MemoryCreate(content="survives a broken journal", source="test"),
        api_key_id=None, wait_process=True,
    )
    memory = result.memory
    assert memory is not None
    assert memory.content == "survives a broken journal"

    row = (
        await session.execute(
            text("SELECT content FROM memories WHERE id = CAST(:mid AS uuid)"),
            {"mid": str(memory.id)},
        )
    ).scalar_one()
    assert row == "survives a broken journal"
