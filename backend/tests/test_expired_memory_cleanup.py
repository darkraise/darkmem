"""The expired-memory sweep: the CHECK it must not trip, and the provenance it
must not strand.

Two regression guards, both of which fail silently rather than loudly:

1. **Ordering.** A TTL'd *superseding* memory must be swept without aborting the
   batch on chk_superseded_has_pointer. fk_memories_superseded_by is ON DELETE
   SET NULL, so the runner must demote dependents (status->deprecated,
   superseded_by->NULL) before it deletes the superseder, in the same
   transaction.
2. **Provenance.** ``fact_sources.source_ref`` is a soft reference with no FK, so
   nothing cascades. A TTL'd memory that solely sources a fact must withdraw that
   provenance and expire the fact on the same terms as every other delete path
   (doc 05 §8.4) — otherwise the fact keeps serving as ``corroborated`` with
   ``expired_at`` NULL forever, which is the overcounting direction the truth
   core forbids. And because ``ProcessingPipeline.delete_memory`` swallows a
   failed withdrawal, the same end state is reachable with no bypass to route,
   so this job also carries the backstop that reaps orphaned provenance whatever
   stranded it.

These tests commit against the real test database rather than the rolled-back
``session`` fixture, because the runner opens its own sessions through a
factory. Every assertion is scoped to rows this file planted: the runner sweeps
the whole table, so a global count would be a shared-fixture accident waiting to
happen. ``events`` rows are left behind — the table is append-only by trigger.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models.memory import Memory
from app.repositories.fact_sources import FactSourceRepository
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services import fact_provenance
from app.services.fact_provenance import MEMORY_SOURCE_KIND, memory_source_ref
from app.services.job_runners import make_expired_memory_cleanup_runner
from app.services.triple_key import compute_triple_key

NOW = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)


async def plant_fact(session, *, subject, obj, project="default") -> str:
    fact = await KnowledgeTripleRepository(session).insert_open(
        triple_key=compute_triple_key(project, subject, "USES", obj),
        subject_name=subject,
        object_name=obj,
        rel_type="USES",
        fact=f"{subject} USES {obj}",
        reference_time=NOW,
        project=project,
    )
    return fact["id"]


async def plant_source(session, *, fact_id, source_ref, source_kind=MEMORY_SOURCE_KIND):
    await FactSourceRepository(session).add_source(
        fact_id=fact_id,
        source_kind=source_kind,
        source_ref=source_ref,
        origin_key=f"session-{source_ref[:8]}",
    )


async def plant_memory(session, *, expired: bool) -> uuid.UUID:
    memory = Memory(
        content="planted",
        source="test",
        expires_at=(
            datetime.now(timezone.utc) - timedelta(hours=1) if expired else None
        ),
    )
    session.add(memory)
    await session.flush()
    return memory.id


async def source_rows(session, fact_id) -> int:
    return (
        await session.execute(
            text("SELECT count(*) FROM fact_sources WHERE fact_id = CAST(:f AS uuid)"),
            {"f": str(fact_id)},
        )
    ).scalar_one()


async def expired_at(session, fact_id):
    return (
        await session.execute(
            text("SELECT expired_at FROM knowledge_triples WHERE id = CAST(:f AS uuid)"),
            {"f": str(fact_id)},
        )
    ).scalar_one()


async def emitted_for(session, source_ref) -> list[dict]:
    rows = await session.execute(
        text(
            "SELECT object_id, payload FROM events "
            "WHERE event_type = 'sources_changed' "
            "AND payload->>'memory_id' = CAST(:m AS text) "
            "ORDER BY created_at, id"
        ),
        {"m": str(source_ref)},
    )
    return [dict(row) for row in rows.mappings().all()]


def without_the_backstop(monkeypatch) -> list[str]:
    """Neutralise the backstop arm for a test about the *routing*.

    The two arms converge on the same end state — that is the point of having
    both — so a routing test run with the backstop live would still pass with
    the withdrawal deleted, healed a moment later by the reaper in the job's
    second session. That is a guard that reads stronger than it is. With the
    reaper stubbed out, only the sweep's own withdrawal can satisfy these
    assertions.

    Returns a call log the caller **must** assert on. Without that assertion the
    neutralisation is itself unpinned: if the runner ever binds the reaper at
    module-import time, this patch stops intercepting, the live backstop heals
    the strand, and the routing test goes green having proved nothing. A stub
    nobody checks was invoked is not a guard.
    """
    calls: list[str] = []

    async def _no_backstop(session):
        calls.append("reap")
        return []

    monkeypatch.setattr(
        fact_provenance, "reap_orphaned_memory_sources", _no_backstop
    )
    return calls


async def discard(factory, *, fact_ids=(), memory_ids=()) -> None:
    async with factory() as s:
        # knowledge_triples first: fact_sources.fact_id cascades, so this is
        # what removes the provenance rows too.
        await s.execute(
            text("DELETE FROM knowledge_triples WHERE id = ANY(CAST(:ids AS uuid[]))"),
            {"ids": [str(f) for f in fact_ids]},
        )
        await s.execute(
            text("DELETE FROM memories WHERE id = ANY(CAST(:ids AS uuid[]))"),
            {"ids": [str(m) for m in memory_ids]},
        )
        await s.commit()


@pytest.mark.asyncio
async def test_expired_cleanup_demotes_dependents_before_delete():
    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    a_id = b_id = None
    try:
        async with factory() as s:
            a = Memory(
                content="expired superseder",
                source="test",
                expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            )
            s.add(a)
            await s.flush()
            a_id = a.id
            b = Memory(
                content="superseded by A",
                source="test",
                status="superseded",
                superseded_by=a.id,
            )
            s.add(b)
            await s.flush()
            b_id = b.id
            await s.commit()

        run = make_expired_memory_cleanup_runner(factory)
        await run()  # must not raise IntegrityError on chk_superseded_has_pointer

        async with factory() as s:
            a_row = (await s.execute(select(Memory).where(Memory.id == a_id))).scalar_one_or_none()
            b_row = (await s.execute(select(Memory).where(Memory.id == b_id))).scalar_one_or_none()
        assert a_row is None, "expired superseder should be swept"
        assert b_row is not None, "dependent must survive — only demoted, not deleted"
        assert b_row.status == "deprecated"
        assert b_row.superseded_by is None
    finally:
        async with factory() as s:
            await s.execute(
                text("DELETE FROM memories WHERE id = ANY(CAST(:ids AS uuid[]))"),
                {"ids": [i for i in (a_id, b_id) if i is not None]},
            )
            await s.commit()
        await engine.dispose()


@pytest.mark.asyncio
async def test_expired_cleanup_withdraws_provenance_and_expires_its_last_fact(
    monkeypatch,
):
    """The bypass this task closes.

    The sweep used to delete straight out of ``memories`` with raw SQL, never
    reaching the withdrawal hook that hangs off the repository method every
    other delete path uses. ``source_ref`` has no FK, so the provenance row
    survived its memory and the fact went on serving as ``corroborated`` with
    ``expired_at`` NULL — the exact failure doc 08 §3.3's inline expiry exists to
    prevent, reached by the one delete path that skipped it.

    This fails if the sweep regresses to a bare DELETE.
    """
    backstop_calls = without_the_backstop(monkeypatch)
    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    fact_id = memory_id = None
    try:
        async with factory() as s:
            memory_id = await plant_memory(s, expired=True)
            fact_id = await plant_fact(s, subject="redis", obj="lua")
            await plant_source(s, fact_id=fact_id, source_ref=memory_source_ref(memory_id))
            await s.commit()

        await make_expired_memory_cleanup_runner(factory)()

        assert backstop_calls == ["reap"], (
            "the backstop stub was never invoked, so this test proves nothing "
            "about the sweep's own withdrawal"
        )
        async with factory() as s:
            assert await source_rows(s, fact_id) == 0, "provenance outlived its memory"
            assert await expired_at(s, fact_id) is not None, (
                "a fact whose last source was swept must stop being served now"
            )
            rows = await emitted_for(s, memory_source_ref(memory_id))
            assert len(rows) == 1
            assert rows[0]["payload"] == {
                "fact_id": fact_id,
                "memory_id": memory_source_ref(memory_id),
            }
    finally:
        await discard(factory, fact_ids=[fact_id], memory_ids=[memory_id])
        await engine.dispose()


@pytest.mark.asyncio
async def test_a_held_fact_lock_defers_only_its_memory(monkeypatch):
    """One fact held past the withdrawal's bound must not cost the whole tick."""
    without_the_backstop(monkeypatch)
    monkeypatch.setattr(fact_provenance, "WITHDRAWAL_LOCK_TIMEOUT", "200ms")
    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    held_fact = free_fact = held_memory = free_memory = None
    try:
        async with factory() as s:
            held_memory = await plant_memory(s, expired=True)
            free_memory = await plant_memory(s, expired=True)
            held_fact = await plant_fact(s, subject="kafka", obj="zookeeper")
            free_fact = await plant_fact(s, subject="nats", obj="jetstream")
            await plant_source(s, fact_id=held_fact, source_ref=memory_source_ref(held_memory))
            await plant_source(s, fact_id=free_fact, source_ref=memory_source_ref(free_memory))
            await s.commit()

        async with factory() as holder:
            await holder.execute(
                text("SELECT id FROM knowledge_triples WHERE id = CAST(:id AS uuid) FOR UPDATE"),
                {"id": held_fact},
            )
            counts = await make_expired_memory_cleanup_runner(factory)()
            await holder.rollback()

        assert counts["deferred"] == 1
        async with factory() as s:
            left = set((await s.execute(
                text("SELECT id FROM memories WHERE id = ANY(CAST(:ids AS uuid[]))"),
                {"ids": [held_memory, free_memory]},
            )).scalars().all())
            assert left == {held_memory}
            assert await source_rows(s, free_fact) == 0
            assert await source_rows(s, held_fact) == 1
    finally:
        await discard(
            factory, fact_ids=[held_fact, free_fact], memory_ids=[held_memory, free_memory],
        )
        await engine.dispose()


@pytest.mark.asyncio
async def test_expired_cleanup_leaves_a_fact_that_keeps_a_surviving_source(monkeypatch):
    """Belief is withdrawn on *no* surviving source, never on one fewer.

    Only the TTL'd memory's own row goes; the fact stays live because another
    memory still asserts it, and the enqueue still fires because its origin
    profile moved even though its belief did not.
    """
    backstop_calls = without_the_backstop(monkeypatch)
    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    fact_id = doomed = survivor = None
    try:
        async with factory() as s:
            doomed = await plant_memory(s, expired=True)
            survivor = await plant_memory(s, expired=False)
            fact_id = await plant_fact(s, subject="celery", obj="redis")
            await plant_source(s, fact_id=fact_id, source_ref=memory_source_ref(doomed))
            await plant_source(s, fact_id=fact_id, source_ref=memory_source_ref(survivor))
            await s.commit()

        await make_expired_memory_cleanup_runner(factory)()

        assert backstop_calls == ["reap"], "the backstop stub was never invoked"
        async with factory() as s:
            assert await source_rows(s, fact_id) == 1
            assert await expired_at(s, fact_id) is None
            assert len(await emitted_for(s, memory_source_ref(doomed))) == 1
            assert await emitted_for(s, memory_source_ref(survivor)) == []
            still_there = (
                await s.execute(select(Memory).where(Memory.id == survivor))
            ).scalar_one_or_none()
            assert still_there is not None
    finally:
        await discard(factory, fact_ids=[fact_id], memory_ids=[doomed, survivor])
        await engine.dispose()


@pytest.mark.asyncio
async def test_expired_cleanup_reaps_provenance_stranded_by_another_path():
    """The backstop arm, driven through the job.

    Routing the sweep cannot cover ``ProcessingPipeline.delete_memory``, which
    swallows a withdrawal that fails: nothing bypassed the hook there, so there
    is no bypass to route — only rows to heal afterwards. The end state is what
    this plants, and note that **nothing here is expired**: the arm must run on
    ticks that sweep no memory at all, or it would only ever heal on the one
    path that no longer strands.
    """
    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    fact_id = None
    vanished = memory_source_ref(uuid.uuid4())
    try:
        async with factory() as s:
            fact_id = await plant_fact(s, subject="uvicorn", obj="httptools")
            await plant_source(s, fact_id=fact_id, source_ref=vanished)
            await s.commit()

        await make_expired_memory_cleanup_runner(factory)()

        async with factory() as s:
            assert await source_rows(s, fact_id) == 0, "the backstop reaped nothing"
            assert await expired_at(s, fact_id) is not None
            assert len(await emitted_for(s, vanished)) == 1
    finally:
        await discard(factory, fact_ids=[fact_id])
        await engine.dispose()


@pytest.mark.asyncio
async def test_expired_cleanup_never_reaps_a_non_memory_source():
    """The destructive-failure guard, at the job level.

    ``source_ref`` carries no type discriminator, so "no ``memories`` row
    matches" is evidence of orphanhood only for the ``memory`` kind. A human
    reviewer's ref matches no ``memories`` row **by construction** — reaping it
    would destroy real provenance and expire the fact it solely sources, which
    is strictly worse than the stranding the backstop heals.

    The ref is uuid-shaped so that only the ``source_kind`` filter can save it,
    and the memory-kind orphan beside it proves the arm ran rather than finding
    nothing to do.
    """
    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    human_fact = orphan_fact = None
    reviewer = str(uuid.uuid4())
    vanished = memory_source_ref(uuid.uuid4())
    try:
        async with factory() as s:
            human_fact = await plant_fact(s, subject="pgvector", obj="postgres")
            orphan_fact = await plant_fact(s, subject="vite", obj="rollup")
            await plant_source(
                s, fact_id=human_fact, source_ref=reviewer, source_kind="human"
            )
            await plant_source(s, fact_id=orphan_fact, source_ref=vanished)
            await s.commit()

        await make_expired_memory_cleanup_runner(factory)()

        async with factory() as s:
            assert await source_rows(s, human_fact) == 1, "a human source was reaped"
            assert await expired_at(s, human_fact) is None
            assert await emitted_for(s, reviewer) == []
            assert await source_rows(s, orphan_fact) == 0, "the arm did not run"
    finally:
        await discard(factory, fact_ids=[human_fact, orphan_fact])
        await engine.dispose()


@pytest.mark.asyncio
async def test_expired_cleanup_never_reaps_a_ref_naming_a_live_memory():
    """The second destructive-failure guard: a mis-spelled ref is not an orphan.

    The backstop is an anti-join, so *failing to match is reaping*. A ref that
    names a live memory under a non-canonical spelling — braced, or upper-cased
    — matches no ``CAST(memories.id AS text)`` either, so an unguarded predicate
    destroys provenance whose memory is sitting right there. That also inverts
    what ``memory_source_ref``'s docstring promises a producer: that a badly
    spelled ref is *invisible* to the sweep, not deleted by it.

    Both survivors here point at a memory that still exists, so nothing about
    them is orphaned under any reading. The canonically-spelled orphan beside
    them proves the arm ran rather than finding nothing to do.
    """
    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    braced_fact = upper_fact = orphan_fact = live = None
    vanished = memory_source_ref(uuid.uuid4())
    try:
        async with factory() as s:
            live = await plant_memory(s, expired=False)
            braced_fact = await plant_fact(s, subject="ruff", obj="rust")
            upper_fact = await plant_fact(s, subject="mypy", obj="python")
            orphan_fact = await plant_fact(s, subject="esbuild", obj="go")
            await plant_source(s, fact_id=braced_fact, source_ref=f"{{{live}}}")
            await plant_source(s, fact_id=upper_fact, source_ref=str(live).upper())
            await plant_source(s, fact_id=orphan_fact, source_ref=vanished)
            await s.commit()

        await make_expired_memory_cleanup_runner(factory)()

        async with factory() as s:
            assert await source_rows(s, braced_fact) == 1, "a braced ref was reaped"
            assert await source_rows(s, upper_fact) == 1, "an upper-cased ref was reaped"
            assert await expired_at(s, braced_fact) is None
            assert await expired_at(s, upper_fact) is None
            assert await source_rows(s, orphan_fact) == 0, "the arm did not run"
    finally:
        await discard(
            factory,
            fact_ids=[braced_fact, upper_fact, orphan_fact],
            memory_ids=[live],
        )
        await engine.dispose()
