"""The Tier-B flush claim and its buffer contract (T1.13, doc 05 §3).

The claim is the whole task, and both ways it can be wrong are silent. A row
processed twice produces duplicate graph contributions that read as model
inconsistency; a row stranded in `claimed` produces a capture the caller was
told had been accepted and that never appears. So the two claim tests here race
real claimers over a shared row set on separate connections — a sequential
claimer proves nothing about `FOR UPDATE SKIP LOCKED`, since it never contends.

The mutations these tests are built to catch, each verified by making it:

* Drop the locking clause from the claim sub-select and
  `test_concurrent_claimers_never_double_process` fails: without a
  `status='pending'` qual to recheck after the lock releases, the outer
  `b.id = c.id` matches for both claimers and each comes away holding the same
  row (eight claimers, three distinct rows, twenty-four claims).
* Drop only `SKIP LOCKED` and `test_a_locked_row_is_skipped_not_waited_on`
  fails: the second claimer blocks on the first claimer's uncommitted locks
  instead of stepping past them, and the bounded wait expires.
* Drop `SKIP LOCKED` from the stale-claim sweep and
  `test_a_reclaim_already_in_flight_is_skipped_not_blocked` fails the same way.

`flush_once` commits through `session_factory`, so these tests drive a real
committing factory bound to `test_engine` and tear their rows down by hand
rather than relying on the conftest `session` fixture's rollback.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.memory import MemoryBuffer
from app.services.embedder_registry import child_table
from app.services.buffer_flush import (
    BUFFER_FLUSH_CONFIG_SCHEMA,
    BUFFER_FLUSH_CRON,
    BUFFER_FLUSH_DEFAULTS,
    BUFFER_FLUSH_JOB_KEY,
    BUFFER_FLUSH_MAX_RUN_SECONDS,
    BUFFER_FLUSH_MIN_INTERVAL_SECONDS,
    _assert_replay_coverage,
    buffer_settings,
    claim_batch,
    detach,
    flush_once,
    reclaim_stale,
    stale_claims,
    sweep_done,
)
from app.services.job_registry import Job, JobRegistry, is_valid_cron
from app.services.memory_buffer import REPLAYED_METADATA_FIELDS, enqueue
from app.services.pipeline import _flag_cache_reset
from tests.conftest import test_engine
from tests.test_pipeline_phase1 import FakeEmbedder, cleanup, make_pipeline, seed_memories  # noqa: F401

EXTRACTION = {
    "entities": [{"name": "FlushTool", "type": "tool"}],
    "relationships": [],
    "memory_type": "fact",
    "summary": "a flushed summary",
    "emotions": [],
    "flags": [],
}
ENTITY_NAMES = ["FlushTool"]
TEST_TAGS = ["project/darkmem", "kind/decision"]


def factory():
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def _reap_flushed_memories(setup_database):
    """Every flush here commits real `memories` rows through its own sessions,
    beyond the reach of the conftest fixture's rollback. Neighbouring suites
    assert on global memory counts, so anything this module creates has to go
    back out the same way it came in."""
    async with factory()() as s:
        before = set((await s.execute(text("SELECT id FROM memories"))).scalars())
    yield
    async with factory()() as s:
        after = set((await s.execute(text("SELECT id FROM memories"))).scalars())
        leaked = [str(i) for i in after - before]
        if leaked:
            await s.execute(
                text("DELETE FROM pipeline_failures "
                     "WHERE entity_id = ANY(CAST(:ids AS uuid[]))"),
                {"ids": leaked},
            )
            await s.execute(
                text("DELETE FROM memories WHERE id = ANY(CAST(:ids AS uuid[]))"),
                {"ids": leaked},
            )
        await s.execute(
            text("DELETE FROM tags WHERE name = ANY(CAST(:names AS text[])) "
                 "AND NOT EXISTS (SELECT 1 FROM memory_tags WHERE tag_id = tags.id)"),
            {"names": TEST_TAGS},
        )
        await s.commit()


async def seed_buffer(n: int, *, project: str = "flush-test", **extra) -> list[uuid.UUID]:
    """Commit ``n`` pending buffer rows and return their buffer ids."""
    ids: list[uuid.UUID] = []
    async with factory()() as s:
        for i in range(n):
            row = await enqueue(
                s, content=f"flushtool note {i}", project=project, source="api", **extra
            )
            ids.append(row.id)
        await s.commit()
    return ids


async def buffer_rows(buffer_ids: list[uuid.UUID]) -> dict[uuid.UUID, MemoryBuffer]:
    async with factory()() as s:
        rows = (await s.execute(
            text("SELECT * FROM memory_buffer WHERE id = ANY(CAST(:ids AS uuid[]))"),
            {"ids": [str(i) for i in buffer_ids]},
        )).mappings().all()
    return {r["id"]: r for r in rows}


async def drop_buffer(buffer_ids: list[uuid.UUID]) -> None:
    if not buffer_ids:
        return
    async with factory()() as s:
        await s.execute(
            text("DELETE FROM memory_buffer WHERE id = ANY(CAST(:ids AS uuid[]))"),
            {"ids": [str(i) for i in buffer_ids]},
        )
        await s.commit()


async def set_job_config(values: dict) -> None:
    async with factory()() as s:
        await s.execute(
            text(
                "INSERT INTO config (key, value) "
                "VALUES (:k, CAST(:v AS jsonb)) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
            ),
            {
                "k": f"job:{BUFFER_FLUSH_JOB_KEY}",
                "v": __import__("json").dumps(
                    {"enabled": True, "cron": BUFFER_FLUSH_CRON, "config": values}
                ),
            },
        )
        await s.commit()


async def clear_job_config() -> None:
    async with factory()() as s:
        await s.execute(
            text("DELETE FROM config WHERE key = :k"),
            {"k": f"job:{BUFFER_FLUSH_JOB_KEY}"},
        )
        await s.commit()


async def backdate_claims(buffer_ids: list[uuid.UUID], seconds: int) -> None:
    """Fast-forward a claim's age. The abandonment is real; only the clock is
    simulated, because waiting out a 300s visibility window in a test is not."""
    async with factory()() as s:
        await s.execute(
            text(
                "UPDATE memory_buffer "
                "SET claimed_at = NOW() - CAST(:secs AS int) * INTERVAL '1 second' "
                "WHERE id = ANY(CAST(:ids AS uuid[]))"
            ),
            {"secs": seconds, "ids": [str(i) for i in buffer_ids]},
        )
        await s.commit()


class RecordingPipeline:
    """Stands in for ``ProcessingPipeline`` where the claim, not the pipeline, is
    under test. ``fail`` makes every entry report a hard vector failure."""

    def __init__(self, *, fail: bool = False, raises: BaseException | None = None):
        self.fail = fail
        self.raises = raises
        self.batches: list[list[dict]] = []

    async def process_batch(self, entries):
        self.batches.append(list(entries))
        if self.raises is not None:
            raise self.raises
        return [
            {
                "embed": "ok",
                "extract": "ok",
                "vector": "error" if self.fail else "ok",
                "graph": "ok",
                "error": "vector write exploded" if self.fail else None,
            }
            for _ in entries
        ]


# ── The claim: never twice, never stranded ──────────────────────────


async def test_concurrent_claimers_never_double_process(setup_database):
    """Done-when 1. Eight claimers start on the same instant over one shared row
    set; the union of what they claim must be the input set and every pairwise
    intersection empty. Fails when the locking clause is removed."""
    buffer_ids = await seed_buffer(24)
    claimers = 8
    per_claim = 3
    start = asyncio.Barrier(claimers)

    async def claimer(name: str) -> list[uuid.UUID]:
        async with factory()() as session:
            # Force the connection out of the pool before the barrier, so the
            # release is followed by the claim statement and nothing else.
            await session.execute(text("SELECT 1"))
            await start.wait()
            rows = await claim_batch(session, limit=per_claim, worker=name)
            claimed = [r.id for r in rows]
            await session.commit()
        return claimed

    try:
        results = await asyncio.wait_for(
            asyncio.gather(*[claimer(f"w{i}") for i in range(claimers)]),
            timeout=60,
        )

        flat = [bid for batch in results for bid in batch]
        assert len(flat) == len(set(flat)), "a row was claimed by two claimers"
        assert set(flat) == set(buffer_ids), "a row was stranded by the claim"
        for i, left in enumerate(results):
            for right in results[i + 1:]:
                assert not set(left) & set(right)

        rows = await buffer_rows(buffer_ids)
        assert {r["status"] for r in rows.values()} == {"claimed"}
        assert {r["attempts"] for r in rows.values()} == {1}
        assert all(r["claimed_by"] is not None for r in rows.values())
    finally:
        await drop_buffer(buffer_ids)


async def test_a_locked_row_is_skipped_not_waited_on(setup_database):
    """`SKIP LOCKED` is what makes a second claimer step past a held row instead
    of blocking on it. With the clause removed the bounded wait below expires."""
    buffer_ids = await seed_buffer(6)
    try:
        async with factory()() as holder:
            held = [r.id for r in await claim_batch(holder, limit=2, worker="holder")]
            assert len(held) == 2
            # holder has NOT committed: those two rows are locked right now.
            async with factory()() as other:
                rows = await asyncio.wait_for(
                    claim_batch(other, limit=10, worker="other"), timeout=10
                )
                got = [r.id for r in rows]
                await other.commit()
            await holder.commit()

        assert not set(held) & set(got)
        assert set(held) | set(got) == set(buffer_ids)
    finally:
        await drop_buffer(buffer_ids)


async def test_claim_takes_the_oldest_rows_first(setup_database):
    buffer_ids = await seed_buffer(5)
    try:
        async with factory()() as s:
            rows = await claim_batch(s, limit=2, worker="w")
            await s.commit()
        assert [r.id for r in rows] == buffer_ids[:2]
    finally:
        await drop_buffer(buffer_ids)


# ── Ruling 2: the claim batch is its own number ─────────────────────


async def test_claim_batch_default_is_thirty_two_not_the_capture_cap(setup_database):
    """`buffer_claim_batch` bounds internal flush throughput; the capture door's
    1-100 cap bounds one API/MCP submission. Reusing one for the other couples
    two boundaries that have to move independently."""
    await clear_job_config()
    settings = await buffer_settings(factory())
    assert settings["buffer_claim_batch"] == 32
    assert BUFFER_FLUSH_DEFAULTS["buffer_claim_batch"] == 32
    assert settings["buffer_claim_batch"] not in (1, 100)


async def test_claim_batch_is_read_from_the_config_row(setup_database):
    await set_job_config({"buffer_claim_batch": 2})
    buffer_ids = await seed_buffer(5)
    pipeline = RecordingPipeline()
    try:
        settings = await buffer_settings(factory())
        assert settings["buffer_claim_batch"] == 2
        stats = await flush_once(factory(), pipeline)
        assert stats["claimed"] == 2
        assert len(pipeline.batches[0]) == 2
    finally:
        await drop_buffer(buffer_ids)
        await clear_job_config()


async def test_config_schema_defaults_match_the_service_defaults(setup_database):
    """A schema default that drifts from the code default gives the UI one
    number and the runtime another."""
    assert {fd.key: fd.default for fd in BUFFER_FLUSH_CONFIG_SCHEMA} == BUFFER_FLUSH_DEFAULTS


# ── Fable review of T1.13, finding I-2: the ceiling can't outrun the lease ──


def test_visibility_floor_matches_the_max_run_ceiling_at_the_type_level():
    """`max_run_seconds` is a fixed 300s ceiling, not a config field — so the
    only reachable way to break `max_run_seconds <= buffer_claim_visibility_seconds`
    is a runtime-configured visibility BELOW that ceiling. Pinning this against
    the constant (not a copy of the number) catches either side moving."""
    visibility_field = next(
        fd for fd in BUFFER_FLUSH_CONFIG_SCHEMA if fd.key == "buffer_claim_visibility_seconds"
    )
    assert visibility_field.min == BUFFER_FLUSH_MAX_RUN_SECONDS


async def test_set_config_rejects_a_visibility_below_the_max_run_ceiling(setup_database):
    """Proves the invariant holds for every reachable runtime value, not just
    the default (Fable review of T1.13, finding I-2): with the pre-fix min=10,
    this call would have succeeded and left a live run's claim reclaimable
    before the runner watchdog even fires — exactly the window a concurrent
    `wait_process` claimer (T1.14) turns into a real double-process, since it
    claims through the same lease outside the scheduled job's lock."""
    registry = JobRegistry(factory())
    registry.register(Job(
        key=BUFFER_FLUSH_JOB_KEY,
        display_name="Buffer Flush",
        description="(I-2 regression)",
        default_cron=BUFFER_FLUSH_CRON,
        min_interval_seconds=BUFFER_FLUSH_MIN_INTERVAL_SECONDS,
        runner=lambda: flush_once(factory(), RecordingPipeline()),
        config_schema=BUFFER_FLUSH_CONFIG_SCHEMA,
        max_run_seconds=BUFFER_FLUSH_MAX_RUN_SECONDS,
    ))
    try:
        with pytest.raises(ValueError, match="buffer_claim_visibility_seconds.*>="):
            await registry.set_config(
                BUFFER_FLUSH_JOB_KEY,
                {"buffer_claim_visibility_seconds": 10},
            )
        # The floor itself, and anything at or above it, must still be settable.
        await registry.set_config(
            BUFFER_FLUSH_JOB_KEY,
            {"buffer_claim_visibility_seconds": BUFFER_FLUSH_MAX_RUN_SECONDS},
        )
    finally:
        await registry.stop_all()
        await clear_job_config()


# ── Ruling 4: a crashed claim is reclaimable ────────────────────────


async def test_a_crashed_flush_is_reclaimed_and_still_advances_attempts(setup_database):
    """Done-when 2. The crash is simulated through the real machinery: the job's
    `max_run_seconds` ceiling cancels a runner that hangs after claiming, which
    is exactly what a killed worker leaves behind. Recovery then runs through a
    normal flush tick, not through a cleanup call.

    The attempt count must survive the crash. Without that a capture that kills
    its worker every time never reaches `buffer_max_attempts` and loops forever.
    """
    await set_job_config({"buffer_claim_visibility_seconds": 60})
    buffer_ids = await seed_buffer(3)
    hung = RecordingPipeline()

    async def _never_returns(entries):
        hung.batches.append(list(entries))
        await asyncio.Event().wait()

    hung.process_batch = _never_returns

    registry = JobRegistry(factory())
    registry.register(Job(
        key=BUFFER_FLUSH_JOB_KEY,
        display_name="Buffer Flush",
        description="(crash simulation)",
        default_cron=BUFFER_FLUSH_CRON,
        min_interval_seconds=BUFFER_FLUSH_MIN_INTERVAL_SECONDS,
        runner=lambda: flush_once(factory(), hung),
        max_run_seconds=0.5,
    ))

    try:
        await registry.trigger(BUFFER_FLUSH_JOB_KEY)

        crashed = await buffer_rows(buffer_ids)
        assert {r["status"] for r in crashed.values()} == {"claimed"}
        assert {r["attempts"] for r in crashed.values()} == {1}

        # Visible while stranded — this is what the buffer monitor renders.
        await backdate_claims(buffer_ids, 120)
        async with factory()() as s:
            visible = await stale_claims(s, visibility_seconds=60)
        assert {r.id for r in visible} >= set(buffer_ids)

        healthy = RecordingPipeline()
        stats = await flush_once(factory(), healthy)
        assert stats["reclaimed"] == len(buffer_ids)
        assert stats["claimed"] == len(buffer_ids)
        assert stats["done"] == len(buffer_ids)

        settled = await buffer_rows(buffer_ids)
        assert {r["status"] for r in settled.values()} == {"done"}
        assert {r["attempts"] for r in settled.values()} == {2}
    finally:
        await registry.stop_all()
        await drop_buffer(buffer_ids)
        await clear_job_config()


async def test_reclaim_leaves_an_uncommitted_claim_alone(setup_database):
    """A claim in flight is not yet visible to another transaction, so the stale
    sweep cannot see it, let alone reset it underneath its holder."""
    buffer_ids = await seed_buffer(2)
    try:
        async with factory()() as holder:
            await claim_batch(holder, limit=2, worker="holder")
            async with factory()() as sweeper:
                reclaimed = await asyncio.wait_for(
                    reclaim_stale(sweeper, visibility_seconds=0, max_attempts=5),
                    timeout=10,
                )
                await sweeper.commit()
            await holder.commit()
        assert reclaimed == []
    finally:
        await drop_buffer(buffer_ids)


async def test_a_reclaim_already_in_flight_is_skipped_not_blocked(setup_database):
    """The stale sweep locks with `SKIP LOCKED` too. Two sweeps overlapping —
    a scheduled tick and a manual trigger against different processes — must not
    have the second one park on the first one's row locks for its whole run."""
    buffer_ids = await seed_buffer(1)
    try:
        async with factory()() as s:
            await claim_batch(s, limit=1, worker="w")
            await s.commit()
        await backdate_claims(buffer_ids, 3600)

        async with factory()() as first:
            assert await reclaim_stale(
                first, visibility_seconds=60, max_attempts=5
            ) == buffer_ids
            async with factory()() as second:
                also = await asyncio.wait_for(
                    reclaim_stale(second, visibility_seconds=60, max_attempts=5),
                    timeout=10,
                )
                await second.commit()
            await first.commit()
        assert also == []
    finally:
        await drop_buffer(buffer_ids)


async def test_a_stale_claim_past_its_attempts_goes_to_error(setup_database):
    """A capture that kills the worker every time terminates in triage rather
    than cycling through pending forever."""
    buffer_ids = await seed_buffer(1)
    try:
        async with factory()() as s:
            await claim_batch(s, limit=1, worker="w")
            await s.commit()
        await backdate_claims(buffer_ids, 3600)
        async with factory()() as s:
            reclaimed = await reclaim_stale(s, visibility_seconds=60, max_attempts=1)
            await s.commit()
        assert reclaimed == buffer_ids

        rows = await buffer_rows(buffer_ids)
        assert rows[buffer_ids[0]]["status"] == "error"
        assert "stale claim" in rows[buffer_ids[0]]["last_error"]
    finally:
        await drop_buffer(buffer_ids)


# ── Ruling 3: poison rows bounded, visible, triageable ──────────────


async def test_a_failing_row_retries_then_lands_in_error_and_is_kept(setup_database):
    """Done-when 4. Bounded by `buffer_max_attempts`, then `error` for triage —
    never deleted, and never retried forever."""
    await set_job_config({"buffer_max_attempts": 2})
    buffer_ids = await seed_buffer(1)
    pipeline = RecordingPipeline(fail=True)
    try:
        stats = await flush_once(factory(), pipeline)
        assert stats["failed"] == 1
        rows = await buffer_rows(buffer_ids)
        assert rows[buffer_ids[0]]["status"] == "pending"
        assert rows[buffer_ids[0]]["attempts"] == 1
        assert "vector write exploded" in rows[buffer_ids[0]]["last_error"]

        stats = await flush_once(factory(), pipeline)
        assert stats["failed"] == 1
        rows = await buffer_rows(buffer_ids)
        assert rows[buffer_ids[0]]["status"] == "error"
        assert rows[buffer_ids[0]]["attempts"] == 2

        # Bounded: a third tick must not pick it up again.
        stats = await flush_once(factory(), pipeline)
        assert stats["claimed"] == 0
        assert (await buffer_rows(buffer_ids))[buffer_ids[0]]["status"] == "error"
    finally:
        await drop_buffer(buffer_ids)
        await clear_job_config()


async def test_a_raising_pipeline_releases_the_whole_batch(setup_database):
    buffer_ids = await seed_buffer(3)
    pipeline = RecordingPipeline(raises=RuntimeError("embedder unreachable"))
    try:
        stats = await flush_once(factory(), pipeline)
        assert stats["failed"] == 3
        rows = await buffer_rows(buffer_ids)
        assert {r["status"] for r in rows.values()} == {"pending"}
        assert all("embedder unreachable" in r["last_error"] for r in rows.values())
        assert all(r["claimed_by"] is None for r in rows.values())
    finally:
        await drop_buffer(buffer_ids)


async def test_a_row_with_no_preminted_memory_id_goes_to_error_alone(setup_database):
    """A row written by some path other than `enqueue` can never be replayed. It
    must not take the batch it happens to share down with it."""
    good = await seed_buffer(1)
    orphan = uuid.uuid4()
    async with factory()() as s:
        s.add(MemoryBuffer(
            id=orphan, project="flush-test", content="no handle",
            source="api", status="pending", metadata_={},
        ))
        await s.commit()
    pipeline = RecordingPipeline()
    try:
        stats = await flush_once(factory(), pipeline)
        assert stats["rejected"] == 1
        assert stats["done"] == 1
        rows = await buffer_rows(good + [orphan])
        assert rows[orphan]["status"] == "error"
        assert "no pre-minted memory_id" in rows[orphan]["last_error"]
        assert rows[good[0]]["status"] == "done"
    finally:
        await drop_buffer(good + [orphan])


async def test_done_rows_are_retained_and_only_swept_when_old(setup_database):
    """Done-when 4. Success keeps the row; only the retention window removes it,
    and an `error` row is never swept because it is the triage queue."""
    buffer_ids = await seed_buffer(1)
    pipeline = RecordingPipeline()
    try:
        await flush_once(factory(), pipeline)
        rows = await buffer_rows(buffer_ids)
        assert rows[buffer_ids[0]]["status"] == "done"

        async with factory()() as s:
            swept = await sweep_done(s, retention_hours=24)
            await s.commit()
        assert swept == 0
        assert await buffer_rows(buffer_ids)

        async with factory()() as s:
            await s.execute(
                text("UPDATE memory_buffer SET created_at = NOW() - INTERVAL '48 hours', "
                     "claimed_at = NOW() - INTERVAL '48 hours' "
                     "WHERE id = ANY(CAST(:ids AS uuid[]))"),
                {"ids": [str(i) for i in buffer_ids]},
            )
            await s.commit()
        async with factory()() as s:
            swept = await sweep_done(s, retention_hours=24)
            await s.commit()
        assert swept == 1
        assert await buffer_rows(buffer_ids) == {}
    finally:
        await drop_buffer(buffer_ids)


async def test_the_sweep_never_touches_error_rows(setup_database):
    buffer_ids = await seed_buffer(1)
    try:
        async with factory()() as s:
            await s.execute(
                text("UPDATE memory_buffer SET status = 'error', "
                     "created_at = NOW() - INTERVAL '400 days' "
                     "WHERE id = ANY(CAST(:ids AS uuid[]))"),
                {"ids": [str(i) for i in buffer_ids]},
            )
            await s.commit()
        async with factory()() as s:
            assert await sweep_done(s, retention_hours=1) == 0
            await s.commit()
        assert (await buffer_rows(buffer_ids))[buffer_ids[0]]["status"] == "error"
    finally:
        await drop_buffer(buffer_ids)


# ── The replay: two ids, and nothing dropped ────────────────────────


async def test_the_memory_row_takes_the_preminted_id_not_the_buffer_id(setup_database):
    """Doc 05 §2.2. The buffer row's own id tracks the buffer entry; the memory
    id is the handle the 202 already returned. Replaying on the wrong one hands
    every caller a dangling reference."""
    async with factory()() as s:
        row = await enqueue(
            s, content="two ids", project="flush-test", source="api",
        )
        buffer_id = row.id
        memory_id = uuid.UUID(row.metadata_["memory_id"])
        await s.commit()
    assert buffer_id != memory_id

    pipeline = RecordingPipeline()
    try:
        await flush_once(factory(), pipeline)
        assert pipeline.batches[0][0]["memory_id"] == memory_id
        async with factory()() as s:
            found = (await s.execute(
                text("SELECT id FROM memories WHERE id = ANY(CAST(:ids AS uuid[]))"),
                {"ids": [str(memory_id), str(buffer_id)]},
            )).scalars().all()
        assert found == [memory_id]
    finally:
        async with factory()() as s:
            await s.execute(
                text("DELETE FROM memories WHERE id = CAST(:i AS uuid)"),
                {"i": str(memory_id)},
            )
            await s.commit()
        await drop_buffer([buffer_id])


async def test_every_captured_field_reaches_the_memory_row(setup_database):
    expires = datetime(2031, 5, 4, tzinfo=timezone.utc)
    async with factory()() as s:
        row = await enqueue(
            s,
            content="fully loaded capture",
            project="flush-test",
            source="mcp",
            origin_key="mcp:session-7",
            memory_type="decision",
            tags=list(TEST_TAGS),
            importance=0.9,
            expires_at=expires.isoformat(),
            source_agent="claude-code/1.0",
            metadata={"repo_hint": "github.com/x/y"},
        )
        buffer_id = row.id
        memory_id = uuid.UUID(row.metadata_["memory_id"])
        await s.commit()

    pipeline = RecordingPipeline()
    try:
        await flush_once(factory(), pipeline)
        async with factory()() as s:
            mem = (await s.execute(
                text("SELECT * FROM memories WHERE id = CAST(:i AS uuid)"),
                {"i": str(memory_id)},
            )).mappings().one()
            tags = (await s.execute(
                text("SELECT t.name FROM tags t JOIN memory_tags mt ON mt.tag_id = t.id "
                     "WHERE mt.memory_id = CAST(:i AS uuid) ORDER BY t.name"),
                {"i": str(memory_id)},
            )).scalars().all()

        assert mem["content"] == "fully loaded capture"
        assert mem["project"] == "flush-test"
        assert mem["source"] == "mcp"
        assert mem["origin_key"] == "mcp:session-7"
        assert mem["memory_type"] == "decision"
        assert mem["importance"] == pytest.approx(0.9)
        assert mem["expires_at"] == expires
        assert mem["source_agent"] == "claude-code/1.0"
        assert mem["metadata"] == {"repo_hint": "github.com/x/y"}
        assert tags == ["kind/decision", "project/darkmem"]

        entry = pipeline.batches[0][0]
        assert entry["memory_type"] == "decision"
        assert sorted(entry["tags"]) == ["kind/decision", "project/darkmem"]
        assert entry["created_at"]
    finally:
        async with factory()() as s:
            await s.execute(
                text("DELETE FROM memories WHERE id = CAST(:i AS uuid)"),
                {"i": str(memory_id)},
            )
            await s.commit()
        await drop_buffer([buffer_id])


async def test_a_replayed_field_with_no_home_fails_loudly(setup_database):
    """`REPLAYED_METADATA_FIELDS` exists to make an unreplayed capture field a
    visible omission. This is the check that makes it visible."""
    _assert_replay_coverage(REPLAYED_METADATA_FIELDS)
    with pytest.raises(RuntimeError, match="silently drop captured field"):
        _assert_replay_coverage(REPLAYED_METADATA_FIELDS + ("brand_new_capture_field",))


async def test_a_reclaimed_row_updates_its_memory_rather_than_duplicating(setup_database):
    """The id is minted at accept, so a second flush of the same row is an update
    of one memory, never a second one."""
    buffer_ids = await seed_buffer(1)
    memory_id = None
    try:
        failing = RecordingPipeline(fail=True)
        await flush_once(factory(), failing)
        memory_id = failing.batches[0][0]["memory_id"]

        healthy = RecordingPipeline()
        await flush_once(factory(), healthy)
        assert healthy.batches[0][0]["memory_id"] == memory_id

        async with factory()() as s:
            count = (await s.execute(
                text("SELECT count(*) FROM memories WHERE id = CAST(:i AS uuid)"),
                {"i": str(memory_id)},
            )).scalar_one()
        assert count == 1
        assert (await buffer_rows(buffer_ids))[buffer_ids[0]]["status"] == "done"
    finally:
        if memory_id is not None:
            async with factory()() as s:
                await s.execute(
                    text("DELETE FROM memories WHERE id = CAST(:i AS uuid)"),
                    {"i": str(memory_id)},
                )
                await s.commit()
        await drop_buffer(buffer_ids)


async def test_detach_keeps_the_two_ids_apart(setup_database):
    async with factory()() as s:
        row = await enqueue(s, content="detached", project="flush-test")
        await s.commit()
        captures, rejected = detach([row])
    try:
        assert rejected == []
        assert captures[0].buffer_id == row.id
        assert captures[0].memory_id != row.id
        assert "memory_id" not in captures[0].replay
    finally:
        await drop_buffer([row.id])


# ── Ruling 5: registered like every other job ───────────────────────


async def test_registered_with_a_cron_a_floor_and_a_shared_lock(setup_database):
    """Done-when 5. The registry contract: a valid cron, a floor that survives a
    runaway expression, and one lock shared by the loop and by `trigger`, so a
    manual run during a scheduled one reports busy instead of queueing."""
    assert is_valid_cron(BUFFER_FLUSH_CRON)
    assert len(BUFFER_FLUSH_CRON.split()) == 6, "six-field puts seconds first"
    assert BUFFER_FLUSH_MIN_INTERVAL_SECONDS >= 1
    # The registry cancels a run at this ceiling and the next tick's stale sweep
    # is what recovers its rows, so the ceiling may not outlast the window.
    assert BUFFER_FLUSH_MAX_RUN_SECONDS <= BUFFER_FLUSH_DEFAULTS[
        "buffer_claim_visibility_seconds"
    ]

    from app.services.job_registry import JobBusyError

    started = asyncio.Event()
    release = asyncio.Event()

    async def blocking_runner():
        started.set()
        await release.wait()

    registry = JobRegistry(factory())
    registry.register(Job(
        key=BUFFER_FLUSH_JOB_KEY,
        display_name="Buffer Flush",
        description="(lock contract)",
        default_cron=BUFFER_FLUSH_CRON,
        min_interval_seconds=BUFFER_FLUSH_MIN_INTERVAL_SECONDS,
        runner=blocking_runner,
        max_run_seconds=BUFFER_FLUSH_MAX_RUN_SECONDS,
    ))
    first = asyncio.create_task(registry.trigger(BUFFER_FLUSH_JOB_KEY))
    try:
        await asyncio.wait_for(started.wait(), timeout=10)
        with pytest.raises(JobBusyError):
            await registry.trigger(BUFFER_FLUSH_JOB_KEY)
    finally:
        release.set()
        await first
        await registry.stop_all()
        await clear_job_config()


def test_main_registers_the_buffer_flush_job():
    """The job has to be wired into the process that actually runs, not only be
    constructible; the lifespan is where every other job is registered."""
    import inspect

    import app.main as main

    source = inspect.getsource(main)
    assert "make_buffer_flush_runner" in source
    assert "key=BUFFER_FLUSH_JOB_KEY" in source


# ── End to end, against the real pipeline ───────────────────────────


async def test_flush_drives_the_real_pipeline_end_to_end(setup_database, monkeypatch):
    """The claim, the replay and `process_batch` together: a buffered capture
    becomes a memory with an embedding, a graph and an enrichment, and its
    buffer row settles on `done`."""
    fingerprint = "buffer-flush|4"
    _flag_cache_reset()
    buffer_ids = await seed_buffer(2)
    memory_ids: list[uuid.UUID] = []
    try:
        pipe = make_pipeline(
            factory(), FakeEmbedder([fingerprint]), EXTRACTION, monkeypatch
        )
        stats = await flush_once(factory(), pipe)
        assert stats["claimed"] == 2
        assert stats["done"] == 2

        rows = await buffer_rows(buffer_ids)
        memory_ids = [uuid.UUID(r["metadata"]["memory_id"]) for r in rows.values()]
        assert {r["status"] for r in rows.values()} == {"done"}

        async with factory()() as s:
            enriched = (await s.execute(
                text("SELECT summary, technologies FROM memories "
                     "WHERE id = ANY(CAST(:ids AS uuid[]))"),
                {"ids": [str(m) for m in memory_ids]},
            )).all()
            child = child_table("memory_embeddings", fingerprint)
            embedded = (await s.execute(
                text(f"SELECT count(*) FROM {child} "
                     "WHERE memory_id = ANY(CAST(:ids AS uuid[]))"),
                {"ids": [str(m) for m in memory_ids]},
            )).scalar_one()
        assert len(enriched) == 2
        assert all(row[0] == "a flushed summary" for row in enriched)
        assert all(row[1] == ["flushtool"] for row in enriched)
        assert embedded == 2
    finally:
        await drop_buffer(buffer_ids)
        await cleanup(factory(), memory_ids, [fingerprint], ENTITY_NAMES)


async def test_an_empty_buffer_is_a_cheap_no_op(setup_database):
    pipeline = RecordingPipeline()
    stats = await flush_once(factory(), pipeline)
    assert stats["claimed"] == 0
    assert pipeline.batches == []
