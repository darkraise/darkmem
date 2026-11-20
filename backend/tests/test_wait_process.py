"""`wait_process` — the interactive Tier-A bypass over the buffer (T1.14,
doc 05 §2.2).

T1.12 landed capture additively (`POST /memories/capture(/batch)`,
MCP `memory_capture`/`memory_capture_batch`) because nothing drained the
buffer yet and no synchronous escape existed; `POST /memories`,
`POST /memories/batch`, `memory_add`, and `memory_batch_add` stayed
synchronous and buffer-blind. T1.14 flips those four doors onto the buffered
contract and folds the additive scaffolding back into them: buffered by
default, with `wait_process=true` as the opt-in synchronous escape.

The four Done-when boxes, each with its own test group below:

1. `wait_process` writes the buffer row, then drives THAT row's flush
   synchronously — never the scheduled flush, and never skipping the buffer
   write itself.
2. Bounded by `buffer_wait_timeout_seconds`; on timeout it degrades to the
   plain 202 accept rather than hanging or losing the capture.
3. The bypass runs the identical pipeline — never a second code path. The
   sharpest version of this is Ruling 3: the synchronous driver must claim
   through the same `FOR UPDATE SKIP LOCKED` lease T1.13's scheduled flush
   uses, or a concurrent scheduled flush processes the row twice.
4. The default stays buffered; the bypass is opt-in per call, on both REST
   and MCP (invariant 17).
"""
from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import select, text

from app.models.config import Config
from app.models.memory import MemoryBuffer
from app.schemas.memory import MemoryCreate
from app.services import wait_process
from app.services.buffer_flush import (
    _mark_done,
    as_session_factory,
    claim_batch,
    claim_specific,
    detach,
    materialize,
)
from app.services.memory import MemoryService
from tests.test_buffer_flush import (
    RecordingPipeline,
    buffer_rows,
    drop_buffer,
    factory,
    seed_buffer,
)

pytestmark = pytest.mark.asyncio


def _pipeline(session, **kwargs) -> RecordingPipeline:
    """A recording pipeline whose own sessions share the test's connection, so
    the flush sees the fixture's uncommitted buffer rows."""
    pipeline = RecordingPipeline(**kwargs)
    pipeline.session_factory = as_session_factory(session)
    return pipeline


# ── Done-when 1: writes the buffer row, then drives THAT row's flush ───


async def test_wait_process_writes_the_buffer_row_then_drives_that_rows_flush(session):
    pipeline = _pipeline(session)
    svc = MemoryService(session, pipeline=pipeline)

    result = await svc.create_memory(
        MemoryCreate(content="wait process direct", source="test"),
        api_key_id=None, wait_process=True,
    )

    assert result.memory is not None
    assert result.memory.content == "wait process direct"
    assert len(pipeline.batches) == 1
    assert pipeline.batches[0][0]["memory_id"] == result.memory.id

    # The claim's raw-SQL UPDATE runs outside the ORM unit of work, so the
    # session's identity map (still holding this test's own earlier load) has
    # to be told to look again rather than serve its stale copy.
    session.expire_all()
    rows = (await session.execute(select(MemoryBuffer))).scalars().all()
    assert len(rows) == 1, "the buffer row must exist regardless of wait_process"
    assert rows[0].status == "done"


async def test_wait_process_batch_runs_one_process_batch_call_not_per_entry(session):
    """Done-when 3, batch shape: the bypass reuses process_batch's own
    batching rather than looping a synchronous call per entry."""
    pipeline = _pipeline(session)
    svc = MemoryService(session, pipeline=pipeline)
    entries = [MemoryCreate(content=f"batch item {i}", source="test") for i in range(3)]

    results = await svc.batch_create_memories(entries, api_key_id=None, wait_process=True)

    assert all(r.memory is not None for r in results)
    assert len(pipeline.batches) == 1
    assert len(pipeline.batches[0]) == 3


# ── Done-when 4: default stays buffered; opt-in per call ───────────────


async def test_wait_process_default_is_buffered_not_opted_in(session):
    pipeline = RecordingPipeline()
    svc = MemoryService(session, pipeline=pipeline)

    result = await svc.create_memory(
        MemoryCreate(content="default is buffered", source="test"), api_key_id=None,
    )

    assert result.memory is None
    assert result.ack.status == "accepted"
    assert pipeline.batches == []

    rows = (await session.execute(select(MemoryBuffer))).scalars().all()
    assert len(rows) == 1
    assert rows[0].status == "pending"  # untouched: nothing drove its flush


async def test_wait_process_rest_and_mcp_both_support_the_bypass(client, auth_headers, session, monkeypatch):
    """Both front doors accept the bypass over the same service layer
    (invariant 17) — REST via a query param, MCP via a tool kwarg."""
    from app.main import app
    import app.api.mcp.server as mcp_server

    pipeline = _pipeline(session)
    app.state.pipeline = pipeline
    try:
        rest_response = await client.post(
            "/api/v1/memories?wait_process=true",
            json={"content": "synchronous rest capture"},
            headers=auth_headers,
        )
        assert rest_response.status_code == 201
        assert rest_response.json()["content"] == "synchronous rest capture"
    finally:
        app.state.pipeline = None

    @asynccontextmanager
    async def _fake_ctx():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _fake_ctx())
    mcp_server.set_pipeline(pipeline)
    try:
        raw = await mcp_server.memory_add(content="synchronous mcp capture", wait_process=True)
    finally:
        mcp_server.set_pipeline(None)
    body = json.loads(raw)
    assert body["content"] == "synchronous mcp capture"

    assert len(pipeline.batches) == 2


async def test_wait_process_rest_and_mcp_default_to_the_plain_ack(client, auth_headers, session, monkeypatch):
    import app.api.mcp.server as mcp_server

    rest_response = await client.post(
        "/api/v1/memories", json={"content": "rest default"}, headers=auth_headers,
    )
    assert rest_response.status_code == 202
    assert rest_response.json()["status"] == "accepted"

    @asynccontextmanager
    async def _fake_ctx():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", lambda: _fake_ctx())
    mcp_server.set_pipeline(None)
    raw = await mcp_server.memory_add(content="mcp default")
    body = json.loads(raw)
    assert body["status"] == "accepted"


# ── Done-when 2: bounded, and honestly degrades — never hangs, never lies ──


async def test_wait_process_degrades_to_the_ack_on_expiry(session, monkeypatch):
    """A `drive()` that settles nothing degrades to the plain buffered ack,
    bounded by the module constant — captured through a monkeypatched `drive`
    rather than a real timing race."""
    captured: dict = {}

    async def _fake_drive(factory_, pipeline_, *, buffer_ids, timeout_seconds, max_attempts, **kw):
        captured["timeout_seconds"] = timeout_seconds
        captured["buffer_ids"] = buffer_ids
        return frozenset()  # nothing settled: simulates an expired deadline

    import app.services.memory as memory_module
    monkeypatch.setattr(memory_module, "_drive_wait_process_flush", _fake_drive)

    svc = MemoryService(session, pipeline=_pipeline(session))
    result = await svc.create_memory(
        MemoryCreate(content="config wiring probe", source="test"),
        api_key_id=None, wait_process=True,
    )

    assert captured["timeout_seconds"] == memory_module.BUFFER_WAIT_TIMEOUT_SECONDS
    assert len(captured["buffer_ids"]) == 1
    assert result.memory is None
    assert result.ack.status == "accepted"

    rows = (await session.execute(select(MemoryBuffer))).scalars().all()
    assert len(rows) == 1  # the buffer write itself was never in question


async def test_wait_timeout_is_a_module_constant():
    import app.services.memory as memory_module
    from app.config import FEATURE_FLAGS_DEFAULTS

    assert memory_module.BUFFER_WAIT_TIMEOUT_SECONDS == 10
    assert "buffer_wait_timeout_seconds" not in FEATURE_FLAGS_DEFAULTS


async def test_wait_process_times_out_deterministically_without_a_real_sleep(setup_database):
    """Ruling 2: the timeout path is proven with a fake clock/sleep pair, not
    a real wall-clock wait — a hung pipeline call never returns, and the
    virtual clock alone decides when the bound is hit."""
    buffer_ids = await seed_buffer(1)
    hang_pipeline = RecordingPipeline()
    release = asyncio.Event()

    async def _hangs(entries):
        hang_pipeline.batches.append(list(entries))
        await release.wait()
        return [
            {"embed": "ok", "extract": "ok", "vector": "ok", "graph": "ok"} for _ in entries
        ]

    hang_pipeline.process_batch = _hangs

    virtual_time = {"t": 0.0}

    def fake_clock() -> float:
        return virtual_time["t"]

    async def fake_sleep(seconds: float) -> None:
        virtual_time["t"] += seconds
        # A tiny real yield — not a wait scaled to `seconds` — so the
        # concurrently running claim/materialize (real asyncpg I/O) gets an
        # actual event-loop turn to finish before the hang point. The
        # *deadline* is still decided entirely by the virtual clock above;
        # this never waits anywhere near `timeout_seconds` of real time.
        await asyncio.sleep(0.01)

    memory_id = None
    try:
        settled = await wait_process.drive(
            factory(), hang_pipeline, buffer_ids=buffer_ids,
            timeout_seconds=1.0, max_attempts=5,
            poll_interval_seconds=0.1, clock=fake_clock, sleep=fake_sleep,
        )
        assert settled == frozenset()
        assert virtual_time["t"] >= 1.0

        rows = await buffer_rows(buffer_ids)
        row = rows[buffer_ids[0]]
        # Claimed (materialize ran before the hang point) and still being
        # flushed: the deadline answered the caller, it did not stop the work.
        assert row["status"] == "claimed"
        memory_id = uuid.UUID(row["metadata"]["memory_id"])

        async with factory()() as s:
            exists = (await s.execute(
                text("SELECT 1 FROM memories WHERE id = CAST(:i AS uuid)"), {"i": str(memory_id)},
            )).scalar_one_or_none()
        assert exists == 1, "materialize commits before the pipeline call, timeout or not"
    finally:
        release.set()
        await asyncio.gather(*wait_process.continuing_flushes(), return_exceptions=True)
        if memory_id is not None:
            async with factory()() as s:
                await s.execute(
                    text("DELETE FROM memories WHERE id = CAST(:i AS uuid)"), {"i": str(memory_id)},
                )
                await s.commit()
        await drop_buffer(buffer_ids)


# ── Done-when 3 / Ruling 3: the identical claim, never a second path ───


async def test_claim_specific_skips_a_locked_row_rather_than_waiting_on_it(setup_database):
    """The exact property Ruling 3 depends on, proven directly against
    `claim_specific` (the function `wait_process` calls) rather than through
    the higher-level `drive()`, and bounded by a real `asyncio.wait_for`: if
    `FOR UPDATE SKIP LOCKED` were dropped, the outer UPDATE would block on the
    still-open holder transaction's row lock and this call would time out
    after 10s instead of returning almost immediately — mirroring
    `test_a_locked_row_is_skipped_not_waited_on`'s proof for the scheduled
    flush's own claim."""
    buffer_ids = await seed_buffer(3)
    try:
        async with factory()() as holder:
            held = await claim_batch(holder, limit=1, worker="holder")
            assert len(held) == 1
            # holder has NOT committed: that one row is locked right now.
            async with factory()() as other:
                rows = await asyncio.wait_for(
                    claim_specific(other, buffer_ids=buffer_ids, worker="other"),
                    timeout=10,
                )
                got = {r.id for r in rows}
                await other.commit()
            await holder.commit()
        assert held[0].id not in got
        assert got == set(buffer_ids) - {held[0].id}
    finally:
        await drop_buffer(buffer_ids)


async def test_wait_process_never_reprocesses_a_row_a_concurrent_flush_already_claimed(
    setup_database,
):
    """The single most likely defect (Ruling 3): while a concurrent claimer
    (standing in for the scheduled `buffer_flush` job) holds the row
    uncommitted, `wait_process`'s own claim attempt must be skipped — never
    blocked, never a second claim of the same row — and once the concurrent
    flush finishes for real, `process_batch` must have run exactly once."""
    buffer_ids = await seed_buffer(1)
    pipeline = RecordingPipeline()
    memory_id = None
    try:
        async with factory()() as holder:
            held = await claim_batch(holder, limit=1, worker="scheduled")
            assert len(held) == 1
            # holder has NOT committed: the row is locked right now, exactly
            # like a scheduled flush that has claimed but not yet replayed.

            settled = await wait_process.drive(
                factory(), pipeline, buffer_ids=buffer_ids,
                timeout_seconds=0.3, max_attempts=5, poll_interval_seconds=0.02,
            )
            # Raced away, not reprocessed: wait_process's own claim found
            # nothing (SKIP LOCKED), so its poll ran out the bound while the
            # row was still held elsewhere.
            assert settled == frozenset()
            assert pipeline.batches == []

            # Now the "scheduled flush" finishes for real, through the
            # SAME shared pipeline instance.
            captures, rejected = detach(held)
            assert rejected == []
            entries = await materialize(holder, captures)
            await holder.commit()

        statuses = await pipeline.process_batch(entries)
        assert len(pipeline.batches) == 1, "wait_process must never have run it too"

        async with factory()() as settle_session:
            await _mark_done(settle_session, [c.buffer_id for c in captures])
            await settle_session.commit()

        memory_id = entries[0]["memory_id"]
        rows = await buffer_rows(buffer_ids)
        assert rows[buffer_ids[0]]["status"] == "done"
    finally:
        if memory_id is not None:
            async with factory()() as s:
                await s.execute(
                    text("DELETE FROM memories WHERE id = CAST(:i AS uuid)"), {"i": str(memory_id)},
                )
                await s.commit()
        await drop_buffer(buffer_ids)


# ── The deadline answers the caller; it never stops the flush ──────────


async def test_deadline_returns_ack_and_flush_finishes(client, auth_headers, session, monkeypatch):
    import app.services.memory as memory_module
    from app.main import app
    from app.services.embedder_registry import child_table
    from app.services.pipeline import ProcessingPipeline, _flag_cache_reset
    from tests.test_buffer_flush import EXTRACTION
    from tests.test_pipeline_phase1 import FakeEmbedder

    gate = asyncio.Event()

    class SlowExtractionLLM:
        calls = 0

        async def chat_completion(self, purpose, **kwargs):
            SlowExtractionLLM.calls += 1
            await gate.wait()
            return json.dumps(EXTRACTION)

    fingerprint = "wait-deadline|4"
    _flag_cache_reset()
    pipeline = ProcessingPipeline(FakeEmbedder([fingerprint]), as_session_factory(session))
    pipeline.extraction.llm = SlowExtractionLLM()
    monkeypatch.setattr(memory_module, "BUFFER_WAIT_TIMEOUT_SECONDS", 0.5)
    app.state.pipeline = pipeline
    try:
        response = await client.post(
            "/api/v1/memories?wait_process=true",
            json={"content": "a slow inline flush"},
            headers=auth_headers,
        )
    finally:
        app.state.pipeline = None
    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    memory_id = response.json()["id"]

    gate.set()
    await asyncio.gather(*wait_process.continuing_flushes())

    row = (await session.execute(
        select(MemoryBuffer).where(MemoryBuffer.metadata_["memory_id"].astext == memory_id)
        .execution_options(populate_existing=True)
    )).scalar_one()
    assert row.status == "done"
    assert row.attempts == 1
    vectors = (await session.execute(
        text(f"SELECT count(*) FROM {child_table('memory_embeddings', fingerprint)} "
             "WHERE memory_id = CAST(:m AS uuid)"),
        {"m": memory_id},
    )).scalar_one()
    assert vectors == 1
    assert SlowExtractionLLM.calls == 1


async def test_background_flush_is_tracked_and_cancelled_at_shutdown(setup_database):
    import inspect

    import app.main as main_module

    buffer_ids = await seed_buffer(1)
    pipeline = RecordingPipeline()
    started = asyncio.Event()

    async def _hangs(entries):
        pipeline.batches.append(list(entries))
        started.set()
        await asyncio.Event().wait()

    pipeline.process_batch = _hangs
    opened: list[object] = []
    real_factory = factory()

    @asynccontextmanager
    async def recording_factory():
        async with real_factory() as s:
            opened.append(s)
            yield s

    memory_id = None
    try:
        settled = await wait_process.drive(
            recording_factory, pipeline, buffer_ids=buffer_ids,
            timeout_seconds=0.2, max_attempts=5, poll_interval_seconds=0.02,
        )
        assert settled == frozenset()
        await asyncio.wait_for(started.wait(), 5)
        continuing = wait_process.continuing_flushes()
        assert len(continuing) == 1
        assert opened, "the flush runs on a session the factory opened for it"
        row = (await buffer_rows(buffer_ids))[buffer_ids[0]]
        assert row["status"] == "claimed"
        memory_id = uuid.UUID(row["metadata"]["memory_id"])

        await wait_process.drain_continuing_flushes(grace_seconds=0.1)

        assert all(task.cancelled() for task in continuing)
        assert wait_process.continuing_flushes() == frozenset()
        row = (await buffer_rows(buffer_ids))[buffer_ids[0]]
        assert row["status"] == "pending"
        assert row["attempts"] == 0
        assert row["claimed_by"] is None
        assert "drain_continuing_flushes" in inspect.getsource(main_module.lifespan)
    finally:
        if memory_id is not None:
            async with factory()() as s:
                await s.execute(
                    text("DELETE FROM memories WHERE id = CAST(:i AS uuid)"), {"i": str(memory_id)},
                )
                await s.commit()
        await drop_buffer(buffer_ids)


async def test_hard_failed_replay_answers_the_ack(client, auth_headers, session):
    from app.main import app

    pipeline = _pipeline(session, fail=True)
    app.state.pipeline = pipeline
    try:
        response = await client.post(
            "/api/v1/memories?wait_process=true",
            json={"content": "a replay that hard-fails"},
            headers=auth_headers,
        )
    finally:
        app.state.pipeline = None
    assert len(pipeline.batches) == 1
    assert response.status_code == 202
    assert response.json()["status"] == "accepted"


async def test_a_capture_past_the_continuing_cap_is_left_to_the_scheduled_flush(
    setup_database, monkeypatch,
):
    monkeypatch.setattr(wait_process, "MAX_CONTINUING_FLUSHES", 0)
    buffer_ids = await seed_buffer(1)
    pipeline = RecordingPipeline()
    try:
        settled = await wait_process.drive(
            factory(), pipeline, buffer_ids=buffer_ids,
            timeout_seconds=0.2, max_attempts=5,
        )
        assert settled == frozenset()
        assert pipeline.batches == []
        assert wait_process.continuing_flushes() == frozenset()
        row = (await buffer_rows(buffer_ids))[buffer_ids[0]]
        assert (row["status"], row["attempts"]) == ("pending", 0)
    finally:
        await drop_buffer(buffer_ids)


async def test_a_continuing_flush_past_its_deadline_releases_its_rows(
    setup_database, monkeypatch,
):
    monkeypatch.setattr(wait_process, "BUFFER_FLUSH_DEADLINE_SECONDS", 0.3)
    buffer_ids = await seed_buffer(1)
    pipeline = RecordingPipeline()

    async def _hangs(entries):
        pipeline.batches.append(list(entries))
        await asyncio.Event().wait()

    pipeline.process_batch = _hangs
    memory_id = None
    try:
        settled = await wait_process.drive(
            factory(), pipeline, buffer_ids=buffer_ids,
            timeout_seconds=0.05, max_attempts=5, poll_interval_seconds=0.01,
        )
        assert settled == frozenset()
        await asyncio.gather(*wait_process.continuing_flushes(), return_exceptions=True)
        row = (await buffer_rows(buffer_ids))[buffer_ids[0]]
        memory_id = uuid.UUID(row["metadata"]["memory_id"])
        assert (row["status"], row["attempts"], row["claimed_by"]) == ("pending", 0, None)
        assert "deadline" in row["last_error"]
    finally:
        if memory_id is not None:
            async with factory()() as s:
                await s.execute(
                    text("DELETE FROM memories WHERE id = CAST(:i AS uuid)"), {"i": str(memory_id)},
                )
                await s.commit()
        await drop_buffer(buffer_ids)
