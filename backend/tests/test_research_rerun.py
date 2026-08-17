"""The re-derivation trigger (T3.28's second half).

The shape is the owner's 2026-08-16 ruling — "the trigger surface re-runs the
subject of a previously filed research run" — implemented as re-derivation
rather than re-filing, because re-filing is provably either impossible or
inert. `research_rerun`'s module docstring carries that argument; these tests
pin the consequences of it, and the one property that made the shape worth
choosing: **the trigger never reaches the loop**, so invariant 15's scan needs
no second sanctioned crossing.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.models.memory import Memory
from app.services import research_rerun
from app.services.events import record_event
from app.services.research_config import RESEARCH_SOURCE


async def _filed_run(session, *, subject="pgvector HNSW", project="default",
                     contents=("a finding", "another finding"),
                     source=RESEARCH_SOURCE):
    """A research run as `run_research` leaves it: memories plus its journal."""
    memories = []
    for content in contents:
        memory = Memory(
            id=uuid.uuid4(), content=content, source=source, project=project,
            origin_key=f"research:{uuid.uuid4()}",
            metadata_={"research": {"subject": subject, "source_id": "https://x"}},
        )
        session.add(memory)
        memories.append(memory)
    await session.flush()

    run_id = uuid.uuid4()
    await record_event(
        session,
        event_type=research_rerun.RESEARCH_RUN_EVENT,
        object_type="system",
        project=project,
        source=RESEARCH_SOURCE,
        payload={
            "run_id": str(run_id), "subject": subject, "filed": len(memories),
            "memory_ids": [str(m.id) for m in memories],
            "origins_manufactured": True,
        },
    )
    await session.flush()
    row = (await session.execute(text(
        "SELECT id, created_at FROM events WHERE payload->>'run_id' = :run_id"
    ), {"run_id": str(run_id)})).mappings().one()
    return row["id"], row["created_at"], memories


class _Reprocessor:
    """Stands in for `AnalyticsService.reprocess_selected`.

    The re-derivation itself is the pipeline's, tested where the pipeline is;
    what this file owns is which ids reach it and when it is not called at all.
    """

    def __init__(self, errors: int = 0):
        self.calls: list[list] = []
        self.errors = errors

    async def __call__(self, memory_ids):
        self.calls.append(list(memory_ids))
        return {
            "processed": len(memory_ids) - self.errors,
            "errors": self.errors,
            "total": len(memory_ids),
        }


@pytest.mark.asyncio
async def test_a_run_re_derives_exactly_the_memories_it_filed(session):
    event_id, occurred_at, memories = await _filed_run(session)
    reprocess = _Reprocessor()

    outcome = await research_rerun.rerun_research_run(
        session, event_id=event_id, occurred_at=occurred_at, reprocess=reprocess
    )

    assert reprocess.calls == [sorted((m.id for m in memories), key=str)]
    assert (outcome.filed, outcome.reprocessed, outcome.missing) == (2, 2, 0)
    assert outcome.subject == "pgvector HNSW"


@pytest.mark.asyncio
async def test_a_deleted_memory_is_reported_missing_not_silently_dropped(session):
    """The asymmetry the shape rests on: the journal records what a run filed
    but never the finding text, so a deleted researched memory cannot be
    restored. Re-derivation reaches the survivors and *says* it reached fewer
    than the run filed."""
    event_id, occurred_at, memories = await _filed_run(session)
    await session.delete(memories[0])
    await session.flush()
    reprocess = _Reprocessor()

    outcome = await research_rerun.rerun_research_run(
        session, event_id=event_id, occurred_at=occurred_at, reprocess=reprocess
    )

    assert reprocess.calls == [[memories[1].id]]
    assert (outcome.filed, outcome.reprocessed, outcome.missing) == (2, 1, 1)


@pytest.mark.asyncio
async def test_a_run_with_nothing_left_is_refused_rather_than_reported_as_done(session):
    """"Re-ran, 0 processed" and "there is nothing left of this run" are
    different facts, and only the second is true. Refusing keeps the surface
    from rendering an empty success."""
    event_id, occurred_at, memories = await _filed_run(session)
    for memory in memories:
        await session.delete(memory)
    await session.flush()
    reprocess = _Reprocessor()

    with pytest.raises(research_rerun.RerunRefused, match="no evidence left"):
        await research_rerun.rerun_research_run(
            session, event_id=event_id, occurred_at=occurred_at, reprocess=reprocess
        )
    assert reprocess.calls == [], "a refused re-run must touch nothing"


@pytest.mark.asyncio
async def test_a_non_research_memory_at_a_journalled_id_is_not_re_derived(session):
    """The `source` guard. `memory_ids` comes out of a journal payload; a row
    that is not a researched capture must not be reprocessed because a payload
    named its id."""
    event_id, occurred_at, _ = await _filed_run(session, source="api")
    reprocess = _Reprocessor()

    with pytest.raises(research_rerun.RerunRefused, match="no evidence left"):
        await research_rerun.rerun_research_run(
            session, event_id=event_id, occurred_at=occurred_at, reprocess=reprocess
        )


@pytest.mark.asyncio
async def test_another_event_type_is_refused_rather_than_having_its_payload_read(session):
    """Every `events` row has a payload and most have no `memory_ids`; one that
    did would be reprocessed as if it were a research run."""
    await record_event(
        session, event_type="memory_created", object_type="memory",
        object_id=uuid.uuid4(), project="default",
        payload={"memory_ids": [str(uuid.uuid4())]},
    )
    await session.flush()
    row = (await session.execute(text(
        "SELECT id, created_at FROM events WHERE event_type = 'memory_created'"
    ))).mappings().one()

    with pytest.raises(research_rerun.RerunRefused, match="not a 'research_run'"):
        await research_rerun.rerun_research_run(
            session, event_id=row["id"], occurred_at=row["created_at"],
            reprocess=_Reprocessor(),
        )


@pytest.mark.asyncio
async def test_a_wrong_timestamp_is_refused_rather_than_scanning_every_partition(session):
    """`events` is RANGE-partitioned under a composite `(id, created_at)` key,
    so the lookup carries the bound the listing handed back (T2.13's undo
    discipline). A wrong bound must fail loudly, never widen into a full scan."""
    event_id, occurred_at, _ = await _filed_run(session)

    with pytest.raises(research_rerun.RerunRefused, match="no event"):
        await research_rerun.rerun_research_run(
            session, event_id=event_id,
            occurred_at=occurred_at + timedelta(days=1),
            reprocess=_Reprocessor(),
        )


@pytest.mark.asyncio
async def test_the_listing_reports_live_counts_beside_filed_counts(session):
    event_id, _, memories = await _filed_run(session, subject="uv vs pip")
    await session.delete(memories[0])
    await session.flush()

    runs, total = await research_rerun.list_research_runs(session)

    assert total >= 1
    run = next(r for r in runs if r.event_id == event_id)
    assert (run.subject, run.filed, run.live) == ("uv vs pip", 2, 1)


@pytest.mark.asyncio
async def test_errors_from_the_pipeline_ride_the_outcome(session):
    event_id, occurred_at, _ = await _filed_run(session)
    outcome = await research_rerun.rerun_research_run(
        session, event_id=event_id, occurred_at=occurred_at,
        reprocess=_Reprocessor(errors=1),
    )
    assert (outcome.reprocessed, outcome.errors) == (1, 1)


# ── the property that made this shape worth choosing ─────────────────────


def test_the_trigger_never_reaches_the_research_loop():
    """Invariant 15's scan, applied to exactly the modules this task added.

    T3.27 bought one scoped exemption for the MCP door because that door files
    evidence. Re-derivation files nothing, so it needs none — and taking one
    anyway would have widened a guard that is doing its job. This fails the
    build if a later edit reaches for the loop to "just check whether it is
    enabled", which is the plausible first step back across the line.
    """
    import ast
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1]
    for rel in ("app/services/research_rerun.py", "app/api/routes/config.py"):
        tree = ast.parse((root / rel).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert node.module != "app.services.auto_research", (
                    f"{rel} imports the research loop; the re-derivation "
                    "surface must not, and needs nothing from it"
                )
            if isinstance(node, ast.Attribute):
                assert node.attr != "auto_research", f"{rel} reaches auto_research"
            if isinstance(node, ast.Constant) and node.value == "auto_research":
                assert rel != "app/services/research_rerun.py", (
                    "research_rerun names the loop module as a literal"
                )
