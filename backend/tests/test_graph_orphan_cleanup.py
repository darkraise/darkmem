"""Doc 06 §6, §9 (inv. 8) — the hourly `graph_orphan_cleanup` backstop.

What this sweep is *for* narrowed on 2026-07-28. T1.26 taught
``delete_by_memory_id`` to reconsider the endpoints of the relations it deletes,
so the strip no longer manufactures the ghosts it used to leave behind. This job
is therefore a backstop for ghosts arriving by **other** routes — a raw
``DELETE FROM memories`` that never called the strip, a swallowed cleanup error,
rows inherited from an older build — and never the primary mechanism.
``test_a_clean_re_extraction_leaves_the_sweep_nothing_to_do`` pins that boundary
so a regression in the strip cannot hide behind the sweep.

The sweep is **unscoped by design**, and that is the point rather than an
oversight: a ghost's last asserting memory is *gone*, so there is no memory to
scope by and a scoped sweep could not reach it at all. It is a maintenance pass
over the whole graph, not a surface handing rows back to a caller, so the
read-path isolation rules do not apply to it.

Why it exists at all is Phase-4 dedup. An entity keeps its row in
``entity_embeddings__<slug>`` while it lives, and the ANN probe matches on that
vector alone; a ghost is therefore a live dedup target, and a fresh
``february outage`` snaps onto a stale ``march outage`` from a memory deleted
months ago. ``test_a_dedup_probe_cannot_match_a_ghost_the_sweep_pruned`` is that
scenario end to end, and it is the reason the job's cadence is hourly rather
than daily.
"""
from __future__ import annotations

import ast
import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.memory import Memory
from app.repositories.graph import PostgresGraphRepository
from app.services.embedder_registry import child_table
from app.services.job_registry import (
    Job,
    JobBusyError,
    JobRegistry,
    next_fire_delta_seconds,
)
from app.services.job_runners import make_graph_orphan_cleanup_runner
from tests.conftest import test_engine

JOB_KEY = "graph_orphan_cleanup"
FP = "orphan-sweep|4"


def _registered_job_kwargs() -> dict[str, dict]:
    """Every ``Job(...)`` registered in the lifespan, keyed by job key.

    The registrations are literals inside ``lifespan``, which tests never enter,
    so they are read from the source rather than from a live registry. Parsed
    rather than grepped so the assertions below are about values, not about the
    formatting of the call.
    """
    source = Path(__file__).resolve().parents[1] / "app" / "main.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "Job"):
            continue
        kwargs = {}
        for kw in node.keywords:
            try:
                kwargs[kw.arg] = ast.literal_eval(kw.value)
            except ValueError:
                kwargs[kw.arg] = kw.value
        key = kwargs.get("key")
        if isinstance(key, str):
            out[key] = kwargs
    return out


async def _mk_memory(session, mid: uuid.UUID) -> None:
    session.add(Memory(id=mid, content="x", source="test"))
    await session.flush()


async def _entity_names(session) -> set[str]:
    rows = (await session.execute(text("SELECT name FROM entities"))).scalars().all()
    return set(rows)


async def _seed_entity_partition(session) -> str:
    await session.execute(
        text("INSERT INTO embedders (fingerprint, model_id, dims, source) "
             "VALUES (:fp, 'm', 4, 'llm') ON CONFLICT (fingerprint) DO NOTHING"),
        {"fp": FP},
    )
    child = child_table("entity_embeddings", FP)
    await session.execute(text(
        f"CREATE TABLE IF NOT EXISTS {child} ("
        " entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        " embedding vector(4) NOT NULL,"
        " PRIMARY KEY (entity_id, fingerprint))"
    ))
    return child


def test_the_job_is_registered_hourly_with_its_own_floor():
    job = _registered_job_kwargs()[JOB_KEY]
    assert job["default_cron"] == "0 * * * *"
    assert job["min_interval_seconds"] == 60
    assert job["max_run_seconds"] == 300

    # Hourly means hourly: the next fire from mid-hour is the top of the next
    # one, and the floor never pushes it out.
    now = datetime(2026, 7, 28, 13, 25, 0, tzinfo=timezone.utc)
    delta = next_fire_delta_seconds(
        job["default_cron"], now, floor=job["min_interval_seconds"],
    )
    assert delta == pytest.approx(35 * 60)


@pytest.mark.asyncio
async def test_a_manual_trigger_while_the_loop_holds_the_lock_reports_busy():
    """The same per-job lock, not a second one: a sweep and a manual run of it
    cannot interleave two unscoped DELETEs over the same tables."""
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    registry = JobRegistry(factory)
    registered = _registered_job_kwargs()[JOB_KEY]
    registry.register(Job(
        key=JOB_KEY,
        display_name=registered["display_name"],
        description=registered["description"],
        default_cron=registered["default_cron"],
        min_interval_seconds=registered["min_interval_seconds"],
        runner=make_graph_orphan_cleanup_runner(factory),
        max_run_seconds=registered["max_run_seconds"],
    ))
    try:
        job = registry.get(JOB_KEY)
        async with job.lock:
            with pytest.raises(JobBusyError):
                await registry.trigger(JOB_KEY)
        # Released: the same trigger now runs the real sweep to completion.
        await registry.trigger(JOB_KEY)
        assert (await registry.load_config(JOB_KEY)).last_status == "ok"
    finally:
        await registry.stop_all()


@pytest.mark.asyncio
async def test_the_registered_runner_is_the_unscoped_sweep():
    """The job body reaches ``prune_orphan_entities`` and commits it.

    Runs on its own committing sessions, because the runner opens one through
    the factory and would otherwise see none of the fixture's uncommitted rows.
    """
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    ghost_name = "orphan-sweep-runner-ghost"
    dead_memory = uuid.uuid4()
    async with factory() as s:
        repo = PostgresGraphRepository(s)
        await repo.create_entity(
            name=ghost_name, entity_type="tool", properties={},
            memory_id=dead_memory,
        )
        await s.commit()

    try:
        await make_graph_orphan_cleanup_runner(factory)()
        async with factory() as s:
            remaining = (await s.execute(
                text("SELECT count(*) FROM entities WHERE name = :n"),
                {"n": ghost_name},
            )).scalar_one()
        assert remaining == 0
    finally:
        async with factory() as s:
            await s.execute(
                text("DELETE FROM entities WHERE name = :n"), {"n": ghost_name},
            )
            await s.commit()


@pytest.mark.asyncio
async def test_the_sweep_reaches_a_ghost_no_scoped_pass_could_find(session):
    """Ruling 5: unscoped is the mechanism, not a missing filter.

    The ghost's only asserter was deleted by a route that never called
    ``delete_by_memory_id``. There is no memory left to scope a sweep by, so a
    scoped pass has nothing to start from — the full-table pass is the only one
    that can reach it.
    """
    repo = PostgresGraphRepository(session)
    live, deleted = uuid.uuid4(), uuid.uuid4()
    await _mk_memory(session, live)
    await _mk_memory(session, deleted)
    await repo.create_entity(name="keeper", entity_type="tool", properties={},
                             memory_id=live)
    await repo.create_entity(name="sweep-ghost", entity_type="tool",
                             properties={}, memory_id=deleted)
    await session.execute(
        text("DELETE FROM memories WHERE id = CAST(:m AS uuid)"),
        {"m": str(deleted)},
    )

    stats = await repo.prune_orphan_entities()

    names = await _entity_names(session)
    assert "keeper" in names
    assert "sweep-ghost" not in names
    assert stats["entities_pruned"] == 1


@pytest.mark.asyncio
async def test_a_dedup_probe_cannot_match_a_ghost_the_sweep_pruned(session):
    """The sweep's whole purpose, stated as the dedup outcome.

    Before the sweep the ANN probe canonicalizes a fresh entity onto the ghost;
    after it, the same probe finds nothing, because the ghost's row in the
    per-fingerprint embedding partition went with it (FK ON DELETE CASCADE).
    Both probes are same-typed and same-fingerprint, so the only variable is the
    sweep.
    """
    repo = PostgresGraphRepository(session)
    child = await _seed_entity_partition(session)
    live, deleted = uuid.uuid4(), uuid.uuid4()
    await _mk_memory(session, live)
    await _mk_memory(session, deleted)

    ghost = await repo.create_entity(
        name="march outage", entity_type="event", properties={},
        memory_id=deleted,
    )
    await session.execute(
        text(f"INSERT INTO {child} (entity_id, fingerprint, embedding) "
             "VALUES (CAST(:e AS uuid), :fp, CAST(:v AS vector))"),
        {"e": ghost["id"], "fp": FP, "v": "[1,0,0,0]"},
    )
    await session.execute(
        text("DELETE FROM memories WHERE id = CAST(:m AS uuid)"),
        {"m": str(deleted)},
    )

    probe = [0.999, 0.01, 0, 0]
    before = await repo.find_similar_entity(
        probe, fingerprint=FP, threshold=0.85, entity_type="event",
    )
    assert before is not None and before["id"] == ghost["id"]

    await repo.prune_orphan_entities()

    after = await repo.find_similar_entity(
        probe, fingerprint=FP, threshold=0.85, entity_type="event",
    )
    assert after is None
    orphan_vectors = (await session.execute(
        text(f"SELECT count(*) FROM {child} WHERE entity_id = CAST(:e AS uuid)"),
        {"e": ghost["id"]},
    )).scalar_one()
    assert orphan_vectors == 0


@pytest.mark.asyncio
async def test_the_sweep_never_takes_an_entity_a_relation_still_needs(session):
    """``entity_relations``' endpoint FK is ON DELETE CASCADE, so pruning an
    entity a live relation points at silently destroys another memory's edge."""
    repo = PostgresGraphRepository(session)
    live = uuid.uuid4()
    await _mk_memory(session, live)
    await repo.create_entity(name="endpoint-only", entity_type="concept",
                             properties={}, memory_id=uuid.uuid4())
    await repo.create_entity(name="asserted", entity_type="concept",
                             properties={}, memory_id=live)
    await repo.create_relationship(
        source_name="endpoint-only", target_name="asserted",
        rel_type="RELATED_TO", properties={}, weight=0.5, memory_id=live,
        source_type="concept", target_type="concept",
    )

    stats = await repo.prune_orphan_entities()

    assert {"endpoint-only", "asserted"} <= await _entity_names(session)
    assert stats == {"relations_pruned": 0, "entities_pruned": 0}


@pytest.mark.asyncio
async def test_a_clean_re_extraction_leaves_the_sweep_nothing_to_do(session):
    """Ruling 4's boundary: T1.26 made the strip self-sufficient.

    The strip already reconsiders the endpoints of the relations it deletes, so
    a re-extraction that drops an edge cleans up after itself. If this ever
    starts pruning something, the strip regressed — the sweep would paper over
    it for up to an hour, and Phase-4 dedup would match the ghost in between.
    """
    repo = PostgresGraphRepository(session)
    asserter, endpoint_owner = uuid.uuid4(), uuid.uuid4()
    await _mk_memory(session, asserter)
    await _mk_memory(session, endpoint_owner)

    await repo.create_entity(name="alpha", entity_type="tool", properties={},
                             memory_id=asserter)
    await repo.create_entity(name="beta", entity_type="tool", properties={},
                             memory_id=endpoint_owner)
    await repo.create_relationship(
        source_name="alpha", target_name="beta", rel_type="RELATED_TO",
        properties={}, weight=0.5, memory_id=asserter,
        source_type="tool", target_type="tool",
    )
    await session.execute(
        text("DELETE FROM memories WHERE id = CAST(:m AS uuid)"),
        {"m": str(endpoint_owner)},
    )

    await repo.delete_by_memory_id(asserter)

    stats = await repo.prune_orphan_entities()
    assert stats == {"relations_pruned": 0, "entities_pruned": 0}


@pytest.mark.asyncio
async def test_concurrent_triggers_serialise_on_the_one_lock():
    """Two overlapping manual runs must not both enter the unscoped DELETEs."""
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    registry = JobRegistry(factory)
    entered = 0
    peak = 0
    gate = asyncio.Event()

    async def _runner() -> None:
        nonlocal entered, peak
        entered += 1
        peak = max(peak, entered)
        await gate.wait()
        entered -= 1

    registry.register(Job(
        key="orphan_lock_probe", display_name="P", description="d",
        default_cron="0 * * * *", min_interval_seconds=60, runner=_runner,
    ))
    try:
        first = asyncio.create_task(registry.trigger("orphan_lock_probe"))
        await asyncio.sleep(0)
        with pytest.raises(JobBusyError):
            await registry.trigger("orphan_lock_probe")
        gate.set()
        await first
        assert peak == 1
    finally:
        await registry.stop_all()
