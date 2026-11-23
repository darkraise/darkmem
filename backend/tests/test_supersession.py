"""The write-time supersession detector's six-rule gate (doc 08 §2.1).

Every rule below has its own test, and each one is written so that deleting
*that* rule from ``candidate_stmt`` (or the speculative gate from
``detect_supersessions``) turns it red: each seeds one candidate the rule
admits and one it rejects, and asserts the exact flipped set. A suite that
only ever seeds admissible candidates stays green while the gate rots.

Two properties get extra weight because their failure is silent:

* **The ``(created_at, id)`` tie-break.** Same-batch rows share one
  server-side ``created_at``, so a bare ``<`` never fires within a batch and a
  bare ``<=`` flips both directions — and a mutually superseded pair vanishes
  from the default ``active`` view entirely.
* **The REPLACES-family trigger.** It is one behaviour in two files: the
  Phase-5 gate in ``pipeline.py`` decides whether the detector is called at
  all, and the detector filters the relations again. Widening one without the
  other is invisible from either file alone, so the family is tested from both
  ends — directly against the detector, and through ``process_batch``.
"""
from __future__ import annotations

import uuid
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.models.memory import Memory
from app.services.pipeline import is_supersession_trigger as pipeline_trigger
from app.services.relations import SUPERSESSION_WINDOW_DAYS
from app.services.supersession import detect_supersessions, is_supersession_trigger
from tests.test_pipeline_savepoints import savepoint_bed

NOW = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_batch_supersession_waits_for_delayed_older_graph_writes(setup_database):
    names = ("batch-first", "batch-second", "batch-third")
    async with savepoint_bed(list(names), "supersession-batch-order|4", entity_names=names) as bed:
        bed.memory_ids.sort()
        async with bed.factory() as session:
            await session.execute(text("UPDATE memories SET created_at = now() WHERE id = ANY(:ids)"), {"ids": bed.memory_ids})
            await session.commit()

        async def extract(content, system_prompt=None, **kwargs):
            index = names.index(content)
            entities = [{"name": content, "type": "tool"}]
            relationships = []
            if index:
                entities.append({"name": names[index - 1], "type": "tool"})
                relationships.append({"source": content, "target": names[index - 1], "type": "REPLACES"})
            return {"entities": entities, "relationships": relationships, "memory_type": "fact"}

        bed.pipe.extraction.extract = extract
        real_write = bed.pipe._write_memory
        newer_written = [asyncio.Event(), asyncio.Event(), asyncio.Event()]
        completion_order = []

        async def write_delayed(entry, *args, **kwargs):
            index = bed.memory_ids.index(entry["memory_id"])
            if index < 2:
                await asyncio.wait_for(newer_written[index + 1].wait(), 10)
            try:
                result = await real_write(entry, *args, **kwargs)
                completion_order.append(index)
                return result
            finally:
                newer_written[index].set()

        bed.pipe._write_memory = write_delayed
        results = await bed.pipe.process_batch([bed.entry(index, name) for index, name in enumerate(names)])
        assert completion_order == [2, 1, 0]
        assert [result["graph"] for result in results] == ["ok", "ok", "ok"]
        async with bed.factory() as session:
            assert await _status(session, bed.memory_ids[0]) == ("superseded", bed.memory_ids[1])
            assert await _status(session, bed.memory_ids[1]) == ("superseded", bed.memory_ids[2])
            assert await _status(session, bed.memory_ids[2]) == ("active", None)


@pytest.mark.asyncio
async def test_batch_reconciliation_failure_reports_matching_journal_and_outcome(setup_database, monkeypatch):
    import app.services.pipeline as pipeline_module

    real_detect = pipeline_module.detect_supersessions

    async def fail_reconciliation(*args, **kwargs):
        if kwargs.get("candidate_memory_ids") is not None:
            raise RuntimeError("post-write reconciliation failed")
        return await real_detect(*args, **kwargs)

    monkeypatch.setattr(pipeline_module, "detect_supersessions", fail_reconciliation)
    async with savepoint_bed(["older", "newer"], "supersession-reconcile-error|4") as bed:
        results = await bed.pipe.process_batch([bed.entry(index) for index in range(2)])
        assert [result["graph"] for result in results] == ["error", "error"]
        assert [result["vector"] for result in results] == ["ok", "ok"]
        assert [event for event, payload in bed.broadcasts] == ["pipeline.partial", "pipeline.partial"]
        async with bed.factory() as session:
            outcomes = (await session.execute(text(
                "SELECT payload->>'outcome' FROM events WHERE event_type = 'extracted' AND object_id = ANY(:ids)"
            ), {"ids": bed.memory_ids})).scalars().all()
        assert outcomes == ["partial", "partial"]



@pytest.mark.asyncio
async def test_a_failed_reconciliation_keeps_the_extracted_journal(setup_database):
    async with savepoint_bed(["older", "newer"], "supersession-reconcile-read|4") as bed:
        real_factory = bed.pipe.session_factory
        fired = []

        @asynccontextmanager
        async def failing_read_factory():
            async with real_factory() as session:
                real_execute = session.execute

                async def execute(statement, *args, **kwargs):
                    if "ORDER BY memories.created_at, memories.id" in str(statement):
                        fired.append(statement)
                        raise RuntimeError("reconciliation read failed")
                    return await real_execute(statement, *args, **kwargs)

                session.execute = execute
                yield session

        bed.pipe.session_factory = failing_read_factory
        results = await bed.pipe.process_batch([bed.entry(index) for index in range(2)])
        assert fired, "the reconciliation read was never reached, so nothing failed"
        assert [result["vector"] for result in results] == ["ok", "ok"]

        async with real_factory() as session:
            journalled = (await session.execute(text(
                "SELECT object_id FROM events WHERE event_type = 'extracted' AND object_id = ANY(:ids)"
            ), {"ids": bed.memory_ids})).scalars().all()
        assert sorted(journalled) == sorted(bed.memory_ids)

def _mem(**overrides) -> Memory:
    base = dict(
        id=uuid.uuid4(),
        content="candidate",
        source="test",
        source_agent=None,
        memory_type=None,
        importance=0.5,
        metadata_={},
        project="supersession-rules",
        status="active",
        technologies=["promtail"],
        created_at=NOW - timedelta(days=1),
    )
    base.update(overrides)
    return Memory(**base)


async def _detect(
    session,
    new: Memory,
    *,
    targets=("promtail",),
    memory_text="We replaced promtail with alloy.",
    rel_type="REPLACES",
    now=NOW,
):
    return await detect_supersessions(
        session,
        new_memory_id=new.id,
        new_memory_text=memory_text,
        new_memory_created_at=new.created_at,
        project=new.project,
        new_relations=[
            {"type": rel_type, "source": "alloy", "target": t} for t in targets
        ],
        now=now,
    )


async def _status(session, memory_id: uuid.UUID) -> tuple[str, uuid.UUID | None]:
    row = (
        await session.execute(
            text(
                "SELECT status, superseded_by FROM memories "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": str(memory_id)},
        )
    ).one()
    return row[0], row[1]


# ── Rule 1 — same project ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rule1_supersession_never_crosses_project(session):
    new = _mem(content="alloy now", technologies=["alloy"], created_at=NOW)
    same = _mem()
    other = _mem(project="some-other-project")
    session.add_all([new, same, other])
    await session.flush()

    flipped = await _detect(session, new)

    assert flipped == [same.id]
    assert (await _status(session, other.id))[0] == "active"


# ── Rule 2 — candidate must still be active ───────────────────────────


@pytest.mark.asyncio
async def test_rule2_only_active_candidates_are_flipped(session):
    new = _mem(content="alloy now", technologies=["alloy"], created_at=NOW)
    anchor = _mem(content="anchor", technologies=["unrelated"])
    session.add_all([new, anchor])
    await session.flush()

    active = _mem()
    deprecated = _mem(status="deprecated")
    superseded = _mem(status="superseded", superseded_by=anchor.id)
    session.add_all([active, deprecated, superseded])
    await session.flush()

    flipped = await _detect(session, new)

    assert flipped == [active.id]
    assert (await _status(session, deprecated.id))[0] == "deprecated"
    assert await _status(session, superseded.id) == ("superseded", anchor.id)


# ── Rule 3 — technologies overlap, lowercased on both sides ───────────


@pytest.mark.asyncio
async def test_rule3_requires_a_technologies_overlap(session):
    new = _mem(content="alloy now", technologies=["alloy"], created_at=NOW)
    mentions = _mem()
    unrelated = _mem(technologies=["fluentbit"])
    session.add_all([new, mentions, unrelated])
    await session.flush()

    flipped = await _detect(session, new)

    assert flipped == [mentions.id]
    assert (await _status(session, unrelated.id))[0] == "active"


@pytest.mark.asyncio
async def test_rule3_lowercases_the_target_to_match_technologies(session):
    """``memories.technologies`` is lowercase, so the target must be too.

    The two lowercasings are one contract: dropping the ``.lower()`` on the
    target silently stops every mixed-case replacement from ever matching.
    """
    new = _mem(content="alloy now", technologies=["alloy"], created_at=NOW)
    candidate = _mem(technologies=["promtail"])
    session.add_all([new, candidate])
    await session.flush()

    flipped = await _detect(session, new, targets=("Promtail",))

    assert flipped == [candidate.id]


# ── Rule 4 — the 90-day look-back window ──────────────────────────────


@pytest.mark.asyncio
async def test_rule4_window_bounds_the_blast_radius(session):
    new = _mem(content="alloy now", technologies=["alloy"], created_at=NOW)
    inside = _mem(created_at=NOW - timedelta(days=SUPERSESSION_WINDOW_DAYS - 1))
    outside = _mem(created_at=NOW - timedelta(days=SUPERSESSION_WINDOW_DAYS + 1))
    session.add_all([new, inside, outside])
    await session.flush()

    flipped = await _detect(session, new)

    assert flipped == [inside.id]
    assert (await _status(session, outside.id))[0] == "active"


# ── Rule 5 — strictly older, with the (created_at, id) tie-break ──────


@pytest.mark.asyncio
async def test_rule5_a_newer_candidate_is_never_superseded(session):
    new = _mem(content="alloy now", technologies=["alloy"], created_at=NOW)
    older = _mem(created_at=NOW - timedelta(hours=1))
    newer = _mem(created_at=NOW + timedelta(hours=1))
    session.add_all([new, older, newer])
    await session.flush()

    flipped = await _detect(session, new)

    assert flipped == [older.id]
    assert (await _status(session, newer.id))[0] == "active"


@pytest.mark.asyncio
async def test_rule5_tie_break_lets_within_batch_supersession_fire(session):
    """Same-batch rows share one ``created_at``; a bare ``<`` never fires.

    Every memory written by one ``process_batch`` transaction carries the same
    server-side timestamp, so without the id half of the tie-break a
    replacement never supersedes a predecessor captured in its own batch.
    """
    older = _mem(id=uuid.UUID(int=1), created_at=NOW)
    new = _mem(
        id=uuid.UUID(int=2),
        content="alloy now",
        technologies=["alloy"],
        created_at=NOW,
    )
    session.add_all([older, new])
    await session.flush()

    flipped = await _detect(session, new)

    assert flipped == [older.id]


@pytest.mark.asyncio
async def test_rule5_tie_break_blocks_the_mutual_flip(session):
    """The defect the tie-break exists for: both rows vanishing at once.

    Two same-batch memories carrying the same replacement each see the other
    as an equal-timestamp candidate. Without the ``id <`` half the detector
    flips both, and a mutually superseded pair disappears from the default
    ``active`` view with nothing left pointing at a live row.
    """
    low = _mem(id=uuid.UUID(int=1), technologies=["promtail", "alloy"], created_at=NOW)
    high = _mem(id=uuid.UUID(int=2), technologies=["promtail", "alloy"], created_at=NOW)
    session.add_all([low, high])
    await session.flush()

    # The lower id runs first: its higher-id peer must NOT flip.
    assert await _detect(session, low, targets=("alloy",)) == []
    # The higher id then supersedes the lower one — exactly one direction.
    assert await _detect(session, high, targets=("promtail",)) == [low.id]

    assert await _status(session, low.id) == ("superseded", high.id)
    assert (await _status(session, high.id))[0] == "active"


# ── Rule 6 — the per-target speculative gate ──────────────────────────


@pytest.mark.asyncio
async def test_rule6_speculative_clause_suppresses_its_own_target(session):
    new = _mem(content="maybe alloy", technologies=["alloy"], created_at=NOW)
    candidate = _mem()
    session.add_all([new, candidate])
    await session.flush()

    flipped = await _detect(
        session, new, memory_text="We might replace promtail with alloy."
    )

    assert flipped == []
    assert (await _status(session, candidate.id))[0] == "active"


@pytest.mark.asyncio
async def test_rule6_unrelated_speculation_does_not_suppress(session):
    """The gate is scoped per target, not to the whole memory."""
    new = _mem(content="alloy now", technologies=["alloy"], created_at=NOW)
    candidate = _mem()
    session.add_all([new, candidate])
    await session.flush()

    flipped = await _detect(
        session,
        new,
        memory_text=(
            "We replaced promtail with alloy. We might also try vector later."
        ),
    )

    assert flipped == [candidate.id]


@pytest.mark.asyncio
async def test_rule6_scopes_speculation_per_target_within_one_memory(session):
    """One memory, two targets: only the speculative one is suppressed."""
    new = _mem(content="alloy now", technologies=["alloy"], created_at=NOW)
    definitive = _mem(technologies=["promtail"])
    speculative = _mem(technologies=["fluentbit"])
    session.add_all([new, definitive, speculative])
    await session.flush()

    flipped = await _detect(
        session,
        new,
        targets=("promtail", "fluentbit"),
        memory_text=(
            "We replaced promtail with alloy. "
            "We are considering dropping fluentbit too."
        ),
    )

    assert flipped == [definitive.id]
    assert (await _status(session, speculative.id))[0] == "active"


@pytest.mark.asyncio
async def test_rule6_falls_back_to_whole_text_when_target_unmentioned(session):
    """No sentence names the target, so the whole text is the only signal."""
    new = _mem(content="alloy now", technologies=["alloy"], created_at=NOW)
    candidate = _mem()
    session.add_all([new, candidate])
    await session.flush()

    flipped = await _detect(
        session, new, memory_text="We are considering a different log shipper."
    )

    assert flipped == []


@pytest.mark.asyncio
async def test_rule6_whole_text_fallback_still_allows_a_definitive_memory(session):
    new = _mem(content="alloy now", technologies=["alloy"], created_at=NOW)
    candidate = _mem()
    session.add_all([new, candidate])
    await session.flush()

    flipped = await _detect(
        session, new, memory_text="The log shipping migration is done."
    )

    assert flipped == [candidate.id]


# ── The flip itself ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_flip_sets_status_and_pointer_together(session):
    new = _mem(content="alloy now", technologies=["alloy"], created_at=NOW)
    candidate = _mem()
    session.add_all([new, candidate])
    await session.flush()

    assert await _detect(session, new) == [candidate.id]
    assert await _status(session, candidate.id) == ("superseded", new.id)


@pytest.mark.asyncio
async def test_no_matching_target_leaves_every_row_untouched(session):
    new = _mem(content="alloy now", technologies=["alloy"], created_at=NOW)
    candidate = _mem()
    session.add_all([new, candidate])
    await session.flush()

    assert await _detect(session, new, rel_type="USES") == []
    assert (await _status(session, candidate.id))[0] == "active"


# ── The REPLACES family, from both ends ───────────────────────────────


def test_trigger_predicate_covers_the_whole_family():
    assert is_supersession_trigger("REPLACES")
    assert is_supersession_trigger("IMPROVES_ON")
    assert is_supersession_trigger("BUILDS_ON")
    assert is_supersession_trigger("improves_on")
    assert not is_supersession_trigger("USES")
    assert not is_supersession_trigger(None)


def test_pipeline_gate_and_detector_share_one_predicate():
    """Two files, one behaviour — they cannot be widened independently."""
    assert pipeline_trigger is is_supersession_trigger


@pytest.mark.asyncio
@pytest.mark.parametrize("rel_type", ["REPLACES", "IMPROVES_ON", "BUILDS_ON"])
async def test_detector_fires_for_every_family_member(session, rel_type):
    new = _mem(content="alloy now", technologies=["alloy"], created_at=NOW)
    candidate = _mem()
    session.add_all([new, candidate])
    await session.flush()

    flipped = await _detect(
        session, new, rel_type=rel_type, memory_text="Alloy now handles log shipping."
    )

    assert flipped == [candidate.id]


@pytest.mark.asyncio
async def test_phase5_gate_fires_for_a_family_relation(setup_database):
    """The pipeline half of the widening, through the real Phase-5 write.

    ``detect_supersessions`` is only reached when the Phase-5 gate decides the
    extraction carries a replacement, so a detector widened alone still never
    sees an ``IMPROVES_ON`` from ingest. This drives the whole write to prove
    the gate agrees with the filter behind it.
    """
    extraction = {
        "entities": [
            {"name": "Alloy", "type": "tool"},
            {"name": "promtail", "type": "tool"},
        ],
        "relationships": [
            {
                "source": "alloy",
                "target": "promtail",
                "type": "IMPROVES_ON",
                "weight": 0.9,
            }
        ],
        "memory_type": "fact",
    }
    async with savepoint_bed(
        ["alloy improves on promtail"],
        "supersede-family|4",
        entity_names=("alloy", "promtail"),
        extraction=extraction,
    ) as bed:
        candidate_id = uuid.uuid4()
        async with bed.factory() as s:
            s.add(
                Memory(
                    id=candidate_id,
                    content="we ship logs with promtail",
                    source="api",
                    importance=0.5,
                    metadata_={},
                    technologies=["promtail"],
                    created_at=datetime.now(timezone.utc) - timedelta(days=1),
                )
            )
            await s.commit()
        try:
            results = await bed.pipe.process_batch(
                [bed.entry(content="alloy improves on promtail")]
            )
            assert results[0]["graph"] == "ok"

            async with bed.factory() as s:
                status, pointer = await _status(s, candidate_id)
            assert status == "superseded"
            assert str(pointer) == str(bed.memory_id)
        finally:
            # Ahead of the bed teardown: the SET-NULL FK would otherwise strand
            # this row on 'superseded' with a null pointer and abort the delete.
            async with bed.factory() as s:
                await s.execute(
                    text("DELETE FROM memories WHERE id = CAST(:id AS uuid)"),
                    {"id": str(candidate_id)},
                )
                await s.commit()


@pytest.mark.asyncio
async def test_concurrent_supersessions_leave_one_pointer_and_one_event(setup_database):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from tests.conftest import test_engine

    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    now = datetime.now(timezone.utc)
    project = f"supersession-race-{uuid.uuid4().hex[:8]}"
    candidate = _mem(project=project, created_at=now - timedelta(days=1))
    first = _mem(project=project, technologies=[], created_at=now)
    second = _mem(project=project, technologies=[], created_at=now)
    async with factory() as seed:
        seed.add_all([candidate, first, second])
        await seed.commit()

    try:
        async with factory() as session_a, factory() as session_b, factory() as probe:
            await _detect(session_a, first, now=now)
            pid_b = (await session_b.execute(text("SELECT pg_backend_pid()"))).scalar_one()
            racing = asyncio.create_task(_detect(session_b, second, now=now))
            for _ in range(200):
                waiting = (await probe.execute(
                    text("SELECT count(*) FROM pg_locks WHERE pid = :pid AND NOT granted"),
                    {"pid": pid_b},
                )).scalar_one()
                await probe.rollback()
                if waiting:
                    break
                await asyncio.sleep(0.05)
            assert waiting, "the second writer never queued behind the first"
            await session_a.commit()
            await asyncio.wait_for(racing, 10)
            await session_b.commit()

        async with factory() as check:
            assert await _status(check, candidate.id) == ("superseded", first.id)
            events = (await check.execute(
                text(
                    "SELECT count(*) FROM events WHERE event_type = 'superseded' "
                    "AND object_id = CAST(:id AS uuid)"
                ),
                {"id": str(candidate.id)},
            )).scalar_one()
        assert events == 1
    finally:
        async with factory() as cleanup:
            await cleanup.execute(
                text("DELETE FROM memories WHERE id = CAST(:id AS uuid)"),
                {"id": str(candidate.id)},
            )
            await cleanup.execute(
                text("DELETE FROM memories WHERE id = ANY(CAST(:ids AS uuid[]))"),
                {"ids": [str(first.id), str(second.id)]},
            )
            await cleanup.commit()
