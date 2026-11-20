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
import json
import uuid
from datetime import datetime, timezone

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.memory import MemoryBuffer
from app.services.embedder_registry import child_table
from app.services.buffer_flush import (
    BUFFER_FLUSH_CONFIG_SCHEMA,
    BUFFER_FLUSH_CRON,
    BUFFER_FLUSH_DEADLINE_SECONDS,
    BUFFER_FLUSH_DEFAULTS,
    BUFFER_FLUSH_JOB_KEY,
    BUFFER_FLUSH_MAX_RUN_SECONDS,
    BUFFER_FLUSH_MIN_INTERVAL_SECONDS,
    BUFFER_FLUSH_SETTLE_MARGIN_SECONDS,
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
from app.services.pipeline import ProcessingPipeline, _flag_cache_reset
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


async def drain_and_analyze_buffer() -> None:
    """Leave `memory_buffer` in the steady state a drained queue actually has:
    a heap with pages, and a `reltuples` autovacuum last recorded as zero.

    At that statistic the planner costs the claim's row set as one row and puts
    it on the inner side of a nested loop, where it is re-executed once per
    outer row. Each re-execution steps past the rows this same command already
    claimed, so an unmaterialized sub-select hands back a further row every
    time and the bound is silently unenforced. Driving the tests below off the
    statistic rather than off a race is what makes that reachable on demand
    instead of once in every few runs.

    `ANALYZE` writes `relpages`/`reltuples` through `heap_inplace_update`,
    which is not transactional, so this state outlives the caller and every
    later test in the session sees it too.
    """
    async with factory()() as s:
        await s.execute(text(
            "INSERT INTO memory_buffer (id, project, content) "
            "SELECT gen_random_uuid(), 'claim-stats-probe', 'filler' "
            "FROM generate_series(1, 200)"
        ))
        await s.execute(
            text("DELETE FROM memory_buffer WHERE project = 'claim-stats-probe'")
        )
        await s.commit()
    async with factory()() as s:
        await s.execute(text("ANALYZE memory_buffer"))
        stats = (await s.execute(text(
            "SELECT relpages, reltuples FROM pg_class WHERE relname = 'memory_buffer'"
        ))).one()
        await s.commit()
    # Without this the tests below would still pass on a plan that never
    # rescans, and would guard nothing.
    assert stats.relpages > 0 and stats.reltuples == 0, (
        f"planner statistics not in the drained state: {stats!r}"
    )


async def test_claim_holds_its_limit_when_the_planner_rescans_the_claim(setup_database):
    """`buffer_claim_batch` has to bound the claim under every plan the planner
    may pick, not only the ones that evaluate the row set once. This is the
    property the deadline valve rests on: `claim_limit` halving the batch does
    nothing if the SQL then claims the backlog anyway."""
    await drain_and_analyze_buffer()
    buffer_ids = await seed_buffer(8)
    try:
        async with factory()() as s:
            rows = await claim_batch(s, limit=3, worker="w")
            await s.commit()
        assert [r.id for r in rows] == buffer_ids[:3]
        by_id = await buffer_rows(buffer_ids)
        assert [by_id[i]["status"] for i in buffer_ids] == (
            ["claimed"] * 3 + ["pending"] * 5
        )
        assert [by_id[i]["attempts"] for i in buffer_ids] == [1] * 3 + [0] * 5
    finally:
        await drop_buffer(buffer_ids)


async def test_a_single_row_claim_rescanned_does_not_take_the_backlog(setup_database):
    """The narrowest bound is the one a rescan overruns most visibly, and it is
    the bound `claim_limit` converges on after repeated deadlines."""
    await drain_and_analyze_buffer()
    buffer_ids = await seed_buffer(12)
    try:
        async with factory()() as s:
            rows = await claim_batch(s, limit=1, worker="w")
            await s.commit()
        assert [r.id for r in rows] == buffer_ids[:1]
        by_id = await buffer_rows(buffer_ids)
        assert sum(r["status"] == "pending" for r in by_id.values()) == 11
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


# ── Fable review of T1.13, finding I-1: one poison row, one victim ──


async def test_an_unmaterializable_row_fails_alone(setup_database):
    """A capture whose own data cannot be written must settle by itself.

    The reviewer's driver: one buffered capture carrying a 302-character tag
    (`tags.name` is `String(255)`) plus two innocent neighbours, claimed in one
    batch. Before the fix `materialize` raised for the batch and `_replay`'s
    single handler released all three, so two 202-acknowledged captures with
    nothing wrong with them walked the attempts ladder into `error` beside the
    poison one, all three carrying the same uninformative `DBAPIError`. At the
    default claim batch of 32 that is up to 31 innocent captures per tick.
    """
    await set_job_config({"buffer_max_attempts": 2})
    first = await seed_buffer(1)
    poison = await seed_buffer(1, tags=["x" * 302])
    last = await seed_buffer(1)
    innocent = first + last
    pipeline = RecordingPipeline()
    memory_ids: list[uuid.UUID] = []
    try:
        stats = await flush_once(factory(), pipeline)
        assert stats["claimed"] == 3
        assert stats["done"] == 2, "the innocent rows must still flush"
        assert stats["failed"] == 1

        rows = await buffer_rows(innocent + poison)
        memory_ids = [uuid.UUID(r["metadata"]["memory_id"]) for r in rows.values()]
        assert {rows[i]["status"] for i in innocent} == {"done"}
        assert {rows[i]["attempts"] for i in innocent} == {1}
        assert rows[poison[0]]["status"] == "pending"

        # Triage has to be able to name the culprit from `last_error` alone.
        assert rows[poison[0]]["last_error"] is not None
        assert "too long" in rows[poison[0]]["last_error"]
        assert all(rows[i]["last_error"] is None for i in innocent)

        # And the poison row still walks its own attempts ladder into triage.
        stats = await flush_once(factory(), pipeline)
        assert stats["claimed"] == 1
        rows = await buffer_rows(poison)
        assert rows[poison[0]]["status"] == "error"
        assert rows[poison[0]]["attempts"] == 2
    finally:
        async with factory()() as s:
            await s.execute(
                text("DELETE FROM memories WHERE id = ANY(CAST(:ids AS uuid[]))"),
                {"ids": [str(m) for m in memory_ids]},
            )
            await s.commit()
        await drop_buffer(innocent + poison)
        await clear_job_config()


async def test_the_innocent_rows_of_a_poisoned_batch_reach_the_pipeline(setup_database):
    """The isolation is real work, not just bookkeeping: the surviving captures
    have to be handed to `process_batch`, with the poison one left out."""
    innocent = await seed_buffer(2)
    poison = await seed_buffer(1, tags=["y" * 400])
    pipeline = RecordingPipeline()
    memory_ids: list[uuid.UUID] = []
    try:
        await flush_once(factory(), pipeline)
        assert len(pipeline.batches) == 1
        entries = pipeline.batches[0]
        assert len(entries) == 2
        rows = await buffer_rows(innocent + poison)
        memory_ids = [uuid.UUID(r["metadata"]["memory_id"]) for r in rows.values()]
        assert {e["memory_id"] for e in entries} == {
            uuid.UUID(rows[i]["metadata"]["memory_id"]) for i in innocent
        }
    finally:
        async with factory()() as s:
            await s.execute(
                text("DELETE FROM memories WHERE id = ANY(CAST(:ids AS uuid[]))"),
                {"ids": [str(m) for m in memory_ids]},
            )
            await s.commit()
        await drop_buffer(innocent + poison)


# ── Fable review of T1.13, finding I-3: slow is not poisonous ──────


class SlowPipeline:
    """Healthy but too slow for the deadline: every call outlives it."""

    def __init__(self):
        self.batch_sizes: list[int] = []

    async def process_batch(self, entries):
        self.batch_sizes.append(len(entries))
        await asyncio.Event().wait()


async def _reap_memories_of(buffer_ids: list[uuid.UUID]) -> None:
    rows = await buffer_rows(buffer_ids)
    async with factory()() as s:
        await s.execute(
            text("DELETE FROM memories WHERE id = ANY(CAST(:ids AS uuid[]))"),
            {"ids": [str(r["metadata"]["memory_id"]) for r in rows.values()]},
        )
        await s.commit()


async def test_a_deadline_requeues_the_batch_and_halves_the_next_claim(setup_database):
    """A deadline is nobody's failure, so it costs no attempt — and the next
    claim halves, so the flush converges on a batch the ceiling can carry
    instead of failing identically forever."""
    await set_job_config({"buffer_max_attempts": 2, "buffer_claim_batch": 4})
    buffer_ids = await seed_buffer(4)
    slow = SlowPipeline()
    try:
        stats = await flush_once(factory(), slow, deadline_seconds=0.05)
        assert slow.batch_sizes == [4]
        assert stats["timed_out"] == 4
        assert stats["failed"] == 0

        rows = await buffer_rows(buffer_ids)
        assert {r["status"] for r in rows.values()} == {"pending"}
        assert {r["attempts"] for r in rows.values()} == {0}
        assert {r["metadata"]["flush_timeouts"] for r in rows.values()} == {1}
        assert all("deadline" in r["last_error"] for r in rows.values())

        await flush_once(factory(), slow, deadline_seconds=0.05)
        assert slow.batch_sizes == [4, 2]
        await flush_once(factory(), slow, deadline_seconds=0.05)
        assert slow.batch_sizes == [4, 2, 1]
    finally:
        await _reap_memories_of(buffer_ids)
        await drop_buffer(buffer_ids)
        await clear_job_config()


async def test_a_lone_row_outliving_the_deadline_still_reaches_triage(setup_database):
    """The refund cannot livelock. Once the shrink has put a row in a batch of
    its own, the whole deadline was its to use, so a timeout there is the row's
    own failure and walks the ordinary attempts ladder into `error`."""
    await set_job_config({"buffer_max_attempts": 1, "buffer_claim_batch": 1})
    buffer_ids = await seed_buffer(1)
    slow = SlowPipeline()
    try:
        stats = await flush_once(factory(), slow, deadline_seconds=0.05)
        assert stats["timed_out"] == 0
        assert stats["failed"] == 1
        rows = await buffer_rows(buffer_ids)
        assert rows[buffer_ids[0]]["status"] == "error"
        assert rows[buffer_ids[0]]["attempts"] == 1
        assert "deadline" in rows[buffer_ids[0]]["last_error"]
    finally:
        await _reap_memories_of(buffer_ids)
        await drop_buffer(buffer_ids)
        await clear_job_config()


async def test_a_slow_batch_does_not_march_the_backlog_into_error(setup_database):
    """Finding I-3. A run cancelled at the fixed ceiling never reached a settle,
    so every claimed row burned the attempt it took at claim time; at
    `buffer_max_attempts` ticks the whole co-claimed batch reached `error`
    without any row being individually poisonous, and the oldest-first claim fed
    the next batch into the same grinder.

    The bound that replaces it: no row settles to `error` for a deadline it did
    not exhaust on its own. Four ticks against a pipeline that never returns
    leave exactly the head row in triage and the backlog behind it untouched.
    """
    await set_job_config({"buffer_max_attempts": 1, "buffer_claim_batch": 8})
    buffer_ids = await seed_buffer(8)
    slow = SlowPipeline()
    try:
        for _ in range(4):
            await flush_once(factory(), slow, deadline_seconds=0.05)
        assert slow.batch_sizes == [8, 4, 2, 1]

        rows = await buffer_rows(buffer_ids)
        assert rows[buffer_ids[0]]["status"] == "error"
        backlog = buffer_ids[1:]
        assert {rows[i]["status"] for i in backlog} == {"pending"}
        assert {rows[i]["attempts"] for i in backlog} == {0}
    finally:
        await _reap_memories_of(buffer_ids)
        await drop_buffer(buffer_ids)
        await clear_job_config()


async def test_a_deadline_never_outlasts_the_registry_ceiling():
    """The margin is the whole point: a deadline at or past the ceiling would be
    cancelled before it could settle anything, which is the state finding I-3
    describes."""
    assert BUFFER_FLUSH_DEADLINE_SECONDS < BUFFER_FLUSH_MAX_RUN_SECONDS
    assert BUFFER_FLUSH_SETTLE_MARGIN_SECONDS > 0


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


# ── Extraction failure classes ──────────────────────────────────────


class ExtractionLLM:
    """The extraction purpose's provider: raises ``error`` or answers ``reply``."""

    def __init__(self, *, error: Exception | None = None, reply: str | None = None):
        self.error = error
        self.reply = reply if reply is not None else json.dumps(EXTRACTION)

    async def chat_completion(self, purpose, **kwargs):
        if self.error is not None:
            raise self.error
        return self.reply


def _rate_limited() -> Exception:
    request = httpx.Request("POST", "http://llm.test/v1/chat/completions")
    response = httpx.Response(429, request=request, text="slow down")
    try:
        raise httpx.HTTPStatusError("429", request=request, response=response)
    except httpx.HTTPStatusError as e:
        try:
            raise RuntimeError("LLM extraction call failed (429): slow down") from e
        except RuntimeError as wrapped:
            return wrapped


async def _graph_rows(memory_id: uuid.UUID) -> int:
    async with factory()() as s:
        return (await s.execute(
            text("SELECT count(*) FROM entities "
                 "WHERE memory_ids @> ARRAY[CAST(:m AS uuid)]"),
            {"m": str(memory_id)},
        )).scalar_one()


def _real_extraction_pipeline(fingerprint: str, llm: ExtractionLLM):
    pipe = ProcessingPipeline(FakeEmbedder([fingerprint]), factory())
    pipe.extraction.llm = llm
    return pipe


@pytest.mark.parametrize(
    "error",
    [
        httpx.ReadTimeout("read timed out"),
        _rate_limited(),
        httpx.ConnectError("connection refused"),
    ],
    ids=["timeout", "rate-limited", "connection"],
)
async def test_transient_extraction_failure_is_retried(setup_database, error):
    fingerprint = "buffer-transient|4"
    _flag_cache_reset()
    buffer_ids = await seed_buffer(1)
    memory_ids: list[uuid.UUID] = []
    llm = ExtractionLLM(error=error)
    try:
        pipe = _real_extraction_pipeline(fingerprint, llm)
        stats = await flush_once(factory(), pipe)
        row = (await buffer_rows(buffer_ids))[buffer_ids[0]]
        memory_ids = [uuid.UUID(row["metadata"]["memory_id"])]
        assert stats["failed"] == 1
        assert row["status"] == "pending"
        assert row["attempts"] == 1
        assert await _graph_rows(memory_ids[0]) == 0

        llm.error = None
        stats = await flush_once(factory(), pipe)
        row = (await buffer_rows(buffer_ids))[buffer_ids[0]]
        assert stats["done"] == 1
        assert row["status"] == "done"
        assert await _graph_rows(memory_ids[0]) == 1
    finally:
        await drop_buffer(buffer_ids)
        await cleanup(factory(), memory_ids, [fingerprint], ENTITY_NAMES)


async def test_deterministic_extraction_failure_settles_without_retry(setup_database):
    fingerprint = "buffer-deterministic|4"
    _flag_cache_reset()
    buffer_ids = await seed_buffer(1)
    memory_ids: list[uuid.UUID] = []
    try:
        pipe = _real_extraction_pipeline(fingerprint, ExtractionLLM(reply="no json here"))
        stats = await flush_once(factory(), pipe)
        row = (await buffer_rows(buffer_ids))[buffer_ids[0]]
        memory_ids = [uuid.UUID(row["metadata"]["memory_id"])]
        assert stats["done"] == 1
        assert row["status"] == "done"
        assert row["attempts"] == 1

        async with factory()() as s:
            child = child_table("memory_embeddings", fingerprint)
            embedded = (await s.execute(
                text(f"SELECT count(*) FROM {child} WHERE memory_id = CAST(:m AS uuid)"),
                {"m": str(memory_ids[0])},
            )).scalar_one()
            extract = (await s.execute(
                text("SELECT payload->>'extract' FROM events "
                     "WHERE event_type = 'extracted' AND object_id = CAST(:m AS uuid)"),
                {"m": str(memory_ids[0])},
            )).scalars().all()
            failures = (await s.execute(
                text("SELECT failed_step FROM pipeline_failures "
                     "WHERE entity_id = CAST(:m AS uuid)"),
                {"m": str(memory_ids[0])},
            )).scalars().all()
        assert embedded == 1
        assert extract == ["error"]
        assert failures == ["extraction"]
        assert await _graph_rows(memory_ids[0]) == 0
    finally:
        await drop_buffer(buffer_ids)
        await cleanup(factory(), memory_ids, [fingerprint], ENTITY_NAMES)
