"""The durable Tier-B ingest buffer and its pre-minted UUIDv7 ids (T1.10).

Three properties carry the tier, and each has a failure mode that looks like
success from the outside:

1. **The id is minted at accept.** A 202 hands the caller a handle before the
   pipeline has run, and the same value becomes the `memories` row's id. If it
   were re-minted at flush, every handle a caller held would dangle.
2. **The buffer is durable.** Its whole reason to exist over an in-process queue
   is surviving a restart, so the row must be committed to Postgres and readable
   from a session that shares nothing with the one that wrote it.
3. **Nothing captured is dropped.** The buffer has fewer columns than a capture
   has fields, so the remainder rides `metadata_` and replays verbatim. A field
   that reaches Tier A but not the pipeline is data loss reported as a success.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory, MemoryBuffer
from app.services.memory_buffer import (
    REPLAYED_METADATA_FIELDS,
    buffered_memory_id,
    enqueue,
    get,
    pending,
)
from app.utils.ids import new_id


# ── UUIDv7 ──────────────────────────────────────────────────────────


def test_new_id_is_a_uuid7():
    assert new_id().version == 7


def test_new_ids_are_time_ordered():
    # The whole reason doc 04 §2 picks v7 over v4: ids sort by mint time, so
    # B-tree inserts stay local instead of scattering across the index.
    ids = [new_id() for _ in range(50)]
    assert ids == sorted(ids)


def test_new_ids_are_unique():
    assert len({new_id() for _ in range(1000)}) == 1000


# ── The id is minted at accept and carried through unchanged ────────


@pytest.mark.asyncio
async def test_enqueue_mints_uuid7_for_both_ids(session):
    row = await enqueue(session, content="hello", project="default")
    assert row.id.version == 7
    assert buffered_memory_id(row).version == 7


@pytest.mark.asyncio
async def test_the_buffer_id_and_the_memory_id_are_distinct(session):
    """Doc 05 §2.2 keeps them apart: the buffer row's id tracks the buffer entry,
    the pre-minted memory id is the caller's durable reference. Collapsing them
    would make the flush's upsert-on-a-known-id contract ambiguous."""
    row = await enqueue(session, content="hello", project="default")
    assert row.id != buffered_memory_id(row)


@pytest.mark.asyncio
async def test_enqueue_honours_a_caller_minted_id(session):
    # The 202 path mints the handle before this row is written so it can ack
    # first; the buffer must store that exact value, not one of its own.
    handle = new_id()
    row = await enqueue(session, content="hello", project="default", memory_id=handle)
    assert buffered_memory_id(row) == handle
    assert row.id != handle  # the buffer's own handle is its own


@pytest.mark.asyncio
async def test_buffer_id_carries_through_to_the_memories_row(session):
    buffered = await enqueue(session, content="carry me", project="default")
    handle = buffered_memory_id(buffered)

    # What flush does with the id, isolated from the pipeline: the memories row
    # takes the buffered id rather than minting a fresh one.
    session.add(Memory(id=handle, content="carry me", source="api", project="default"))
    await session.flush()

    memory = (await session.get(Memory, handle))
    assert memory is not None
    assert memory.id == handle
    assert memory.id.version == 7


@pytest.mark.asyncio
async def test_memory_ids_default_to_uuid7(session):
    memory = Memory(content="unbuffered", source="api", project="default")
    session.add(memory)
    await session.flush()
    assert memory.id.version == 7


# ── Durability across a process restart ─────────────────────────────


@pytest.mark.asyncio
async def test_buffer_row_survives_a_restart(session):
    """Durability is the tier's reason to exist, so it is proven against a
    genuinely separate connection rather than the writing session's identity
    map — which would return the object from memory and prove nothing."""
    from tests.conftest import test_engine

    handle = new_id()
    async with AsyncSession(test_engine) as writer:
        written = await enqueue(
            writer,
            content="survives",
            project="default",
            source="mcp",
            memory_id=handle,
        )
        buffer_id = written.id
        await writer.commit()

    # A new session over a new connection — what a restarted process has.
    try:
        async with AsyncSession(test_engine) as reader:
            row = await get(reader, buffer_id)
            assert row is not None
            assert row.content == "survives"
            # The pre-minted memory id survived the restart too — it is the
            # caller's durable reference, so losing it would strand the handle
            # the 202 already returned.
            assert buffered_memory_id(row) == handle
            assert row.source == "mcp"
            assert row.status == "pending"
            assert row.attempts == 0
    finally:
        async with AsyncSession(test_engine) as cleanup:
            await cleanup.execute(
                text("DELETE FROM memory_buffer WHERE id = CAST(:id AS uuid)"),
                {"id": str(buffer_id)},
            )
            await cleanup.commit()


# ── The row persists what capture resolved ──────────────────────────


@pytest.mark.asyncio
async def test_row_persists_content_source_project_and_status(session):
    row = await enqueue(
        session, content="body", project="darkmem", source="claude-code"
    )
    assert row.content == "body"
    assert row.project == "darkmem"
    assert row.source == "claude-code"
    assert row.status == "pending"


@pytest.mark.asyncio
async def test_origin_key_is_persisted(session):
    # origin_key has no column of its own — doc 04 §8.6 enumerates the table and
    # routes every other captured field through `metadata`. It still has to
    # survive: every E2 corroboration count is COUNT(DISTINCT origin_key).
    row = await enqueue(
        session,
        content="body",
        project="default",
        source="mcp",
        origin_key="mcp:session-42",
    )
    assert row.metadata_["origin_key"] == "mcp:session-42"


@pytest.mark.asyncio
async def test_every_replayed_field_round_trips(session):
    expires = datetime(2027, 1, 1, tzinfo=timezone.utc).isoformat()
    row = await enqueue(
        session,
        content="body",
        project="default",
        source="mcp",
        origin_key="mcp:s1",
        memory_type="decision",
        tags=["project/darkmem"],
        importance=0.9,
        expires_at=expires,
        source_agent="claude-code/1.0",
        metadata={"repo_hint": "github.com/x/y"},
    )
    for field in REPLAYED_METADATA_FIELDS:
        assert field in row.metadata_, f"{field} was dropped by the buffer"
    assert row.metadata_["memory_type"] == "decision"
    assert row.metadata_["tags"] == ["project/darkmem"]
    assert row.metadata_["importance"] == 0.9
    assert row.metadata_["expires_at"] == expires
    assert row.metadata_["source_agent"] == "claude-code/1.0"
    assert row.metadata_["metadata"] == {"repo_hint": "github.com/x/y"}


@pytest.mark.asyncio
async def test_an_unknown_capture_field_is_kept_not_dropped(session):
    row = await enqueue(
        session, content="body", project="default", some_future_field="value"
    )
    assert row.metadata_["some_future_field"] == "value"


@pytest.mark.asyncio
async def test_absent_fields_do_not_become_null_entries(session):
    row = await enqueue(session, content="body", project="default")
    # The memory id always rides metadata, so it is never wholly empty; what must
    # not appear is a key for a field the caller did not supply.
    assert set(row.metadata_) == {"memory_id"}


# ── Status vocabulary and the pending scan ──────────────────────────


@pytest.mark.asyncio
async def test_status_is_check_constrained(session):
    row = await enqueue(session, content="body", project="default")
    await session.flush()
    with pytest.raises(IntegrityError):
        await session.execute(
            text("UPDATE memory_buffer SET status = 'elsewhere' WHERE id = CAST(:id AS uuid)"),
            {"id": str(row.id)},
        )
    await session.rollback()


@pytest.mark.asyncio
async def test_pending_returns_oldest_first_and_only_pending(session):
    first = await enqueue(session, content="a", project="default")
    second = await enqueue(session, content="b", project="default")
    third = await enqueue(session, content="c", project="default")
    third.status = "done"
    await session.flush()

    rows = await pending(session)
    ids = [r.id for r in rows]
    assert third.id not in ids
    assert ids.index(first.id) < ids.index(second.id)


@pytest.mark.asyncio
async def test_get_returns_none_for_an_unknown_id(session):
    assert await get(session, uuid.uuid4()) is None
