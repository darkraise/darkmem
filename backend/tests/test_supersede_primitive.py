"""The Tier-C supersede primitive and the status bridge (doc 08 §2.2, §3.4).

The hardest thing here is a **negative**: a memory that still asserts live facts
must be left alone. An assertion that nothing changed passes just as well when
the primitive is inert, when the fixture is wrong, and when the ids never
matched — so every negative below is proved by a **differential arm**: the same
fixture builder, one flipped bit, asserting the opposite outcome. The arm that
asserts the change is what proves the arm that asserts no change could have
failed. This is the comparison style ``tests/honesty/test_demote_before_delete``
uses, for the reason it gives there.

Two ordering rules are load-bearing and neither is observable from a single
outcome, so both get arms of their own:

* **Guard 2 is absolute and evaluated first** (ruled 2026-08-02). Every arm
  except the both-fail cell produces an identical outcome under the rejected
  chain-order, so that one cell is the only test that fails if an implementer
  builds guard 1 first.
* **A successor must be strictly newer.** Two spent memories, each the sole
  live source of the triple that invalidated the other's fact, otherwise
  supersede each other and both leave the active view. The refusal is a no-op,
  never a deprecation — routing it into guard 1's arm passes a reason-code
  assertion while still emptying the active view, which is why the mutual-flip
  arms assert the surviving active *count*.

**Timestamps are set explicitly wherever a flip is expected to succeed.** Rows
written in one transaction share a single server-side ``created_at``, so the
ordering falls to the id tie-break and ``uuid4`` ids order randomly — a fixture
built that way passes or fails per run. The no-op fixtures deliberately do not
carry the discipline: a non-active candidate reports its status reason before
the ordering predicate is evaluated at all, so those cells are
timestamp-independent by construction.
"""

from __future__ import annotations

import ast
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models.memory import Memory
from app.repositories.fact_sources import FactSourceRepository, MemorySource
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services.fact_provenance import memory_source_ref
from app.services.supersede import (
    apply_status_bridge,
    decide_status_bridge,
    deprecate,
    successor_is_newer,
    supersede,
)
from app.services.triple_key import compute_triple_key

PROJECT = "t245-supersede"
NOW = datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc)
STALE = NOW - timedelta(days=3)


def _mem(**overrides) -> Memory:
    base = dict(
        id=uuid.uuid4(),
        content="a memory",
        source="test",
        source_agent=None,
        memory_type=None,
        importance=0.5,
        metadata_={},
        project=PROJECT,
        status="active",
        technologies=[],
        created_at=NOW - timedelta(days=1),
        updated_at=STALE,
    )
    base.update(overrides)
    return Memory(**base)


async def _row(session, memory_id) -> dict | None:
    result = await session.execute(
        text(
            "SELECT status, CAST(superseded_by AS text) AS superseded_by, updated_at "
            "FROM memories WHERE id = CAST(:id AS uuid)"
        ),
        {"id": str(memory_id)},
    )
    row = result.mappings().first()
    return dict(row) if row is not None else None


async def _events(session, memory_id, event_type: str | None = None) -> list[dict]:
    sql = (
        "SELECT event_type, payload FROM events "
        "WHERE object_id = CAST(:id AS uuid) AND object_type = 'memory'"
    )
    params = {"id": str(memory_id)}
    if event_type is not None:
        sql += " AND event_type = CAST(:kind AS text)"
        params["kind"] = event_type
    sql += " ORDER BY created_at, id"
    result = await session.execute(text(sql), params)
    return [dict(row) for row in result.mappings().all()]


async def _dangling_pointers(session) -> int:
    """The CHECK's own predicate, asserted independently of Postgres."""
    result = await session.execute(
        text(
            "SELECT count(*) FROM memories "
            "WHERE status = 'superseded' AND superseded_by IS NULL"
        )
    )
    return int(result.scalar_one())


async def _pair(session, *, older_at=None, newer_at=None, successor_project=PROJECT):
    """One candidate and one successor, with the ordering pinned explicitly."""
    candidate = _mem(created_at=older_at or (NOW - timedelta(days=2)))
    successor = _mem(
        content="the replacement",
        created_at=newer_at or NOW,
        project=successor_project,
    )
    session.add_all([candidate, successor])
    await session.flush()
    return candidate, successor


# ───────────────────────── the happy flip ─────────────────────────


@pytest.mark.asyncio
async def test_supersede_sets_both_columns_and_reports_applied(session):
    candidate, successor = await _pair(session)

    result = await supersede(
        session, memory_id=candidate.id, superseded_by=successor.id
    )

    assert result.applied is True
    assert result.reason == "applied"
    assert result.status == "superseded"
    assert result.superseded_by == str(successor.id)

    row = await _row(session, candidate.id)
    assert row["status"] == "superseded"
    assert row["superseded_by"] == str(successor.id)


@pytest.mark.asyncio
async def test_deprecate_retires_without_a_pointer(session):
    candidate, _ = await _pair(session)

    result = await deprecate(session, memory_id=candidate.id)

    assert result.applied is True
    assert result.status == "deprecated"
    assert result.superseded_by is None

    row = await _row(session, candidate.id)
    assert row["status"] == "deprecated"
    assert row["superseded_by"] is None


@pytest.mark.asyncio
async def test_the_update_trigger_moves_updated_at(session):
    """The raw-SQL flip sets no ``updated_at``; the trigger must.

    The row is seeded with a stale ``updated_at`` precisely so the assertion
    has something to move away from — inside one transaction ``now()`` is
    constant, so a row inserted and flipped in the same transaction would show
    no movement even with the trigger working.
    """
    candidate, successor = await _pair(session)
    before = (await _row(session, candidate.id))["updated_at"]
    assert before == STALE

    await supersede(session, memory_id=candidate.id, superseded_by=successor.id)

    assert (await _row(session, candidate.id))["updated_at"] > before


@pytest.mark.asyncio
async def test_a_missing_memory_is_reported_not_raised(session):
    result = await supersede(
        session, memory_id=uuid.uuid4(), superseded_by=uuid.uuid4()
    )
    assert (result.applied, result.reason, result.status) == (False, "not_found", None)


@pytest.mark.asyncio
async def test_a_missing_successor_is_reported_not_a_constraint_error(session):
    """``status`` is what separates the two ``not_found`` shapes."""
    candidate, _ = await _pair(session)

    result = await supersede(
        session, memory_id=candidate.id, superseded_by=uuid.uuid4()
    )

    assert (result.applied, result.reason, result.status) == (
        False,
        "not_found",
        "active",
    )
    assert (await _row(session, candidate.id))["status"] == "active"


# ───────────────────────── the three pointer refusals ─────────────────────────


@pytest.mark.asyncio
async def test_a_memory_is_never_its_own_successor(session):
    candidate, _ = await _pair(session)

    result = await supersede(
        session, memory_id=candidate.id, superseded_by=candidate.id
    )

    assert (result.applied, result.reason) == (False, "self_reference")
    assert (await _row(session, candidate.id))["status"] == "active"
    assert await _events(session, candidate.id) == []


@pytest.mark.asyncio
async def test_supersession_never_crosses_the_project_boundary(session):
    candidate, successor = await _pair(session, successor_project="another-project")

    result = await supersede(
        session, memory_id=candidate.id, superseded_by=successor.id
    )

    assert (result.applied, result.reason) == (False, "cross_project")
    assert (await _row(session, candidate.id))["status"] == "active"


@pytest.mark.asyncio
async def test_an_older_successor_is_refused(session):
    candidate, successor = await _pair(
        session, older_at=NOW, newer_at=NOW - timedelta(days=2)
    )

    result = await supersede(
        session, memory_id=candidate.id, superseded_by=successor.id
    )

    assert (result.applied, result.reason) == (False, "successor_not_newer")
    assert (await _row(session, candidate.id))["status"] == "active"
    assert await _events(session, candidate.id) == []


@pytest.mark.asyncio
async def test_the_tie_break_admits_exactly_one_direction(session):
    """Equal timestamps are the ordinary case, not the exotic one.

    Rows written by one transaction share a server-side ``created_at``, so
    without the id half of the tie-break a same-transaction pair could never
    supersede in either direction — and with a bare ``>=`` it would supersede
    in both. The ids are pinned because ``uuid4`` would decide this at random.
    """
    low = _mem(id=uuid.UUID(int=1), created_at=NOW)
    high = _mem(id=uuid.UUID(int=2), created_at=NOW, content="the replacement")
    session.add_all([low, high])
    await session.flush()

    forward = await supersede(session, memory_id=low.id, superseded_by=high.id)
    backward = await supersede(session, memory_id=high.id, superseded_by=low.id)

    assert forward.reason == "applied"
    assert backward.reason == "successor_not_newer"
    assert (await _row(session, high.id))["status"] == "active"


def test_successor_is_newer_is_pure_and_orders_both_axes():
    """The predicate both entrances share, exercised without a session."""
    low, high = uuid.UUID(int=1), uuid.UUID(int=2)
    args = dict(candidate_created_at=NOW, candidate_id=low)

    assert successor_is_newer(
        **args, successor_created_at=NOW + timedelta(seconds=1), successor_id=low
    )
    assert not successor_is_newer(
        **args, successor_created_at=NOW - timedelta(seconds=1), successor_id=high
    )
    assert successor_is_newer(**args, successor_created_at=NOW, successor_id=high)
    assert not successor_is_newer(**args, successor_created_at=NOW, successor_id=low)


# ───────────────────────── D5 — monotonicity, all six cells ─────────────────────────


async def _seeded(session, status: str):
    """A candidate already in ``status``, plus a pointer target for it."""
    candidate, successor = await _pair(session)
    if status == "superseded":
        await supersede(session, memory_id=candidate.id, superseded_by=successor.id)
    elif status == "deprecated":
        await deprecate(session, memory_id=candidate.id)
    assert (await _row(session, candidate.id))["status"] == status
    return candidate, successor


@pytest.mark.parametrize(
    "start_status,operation,expect_reason,expect_status",
    [
        ("active", "supersede", "applied", "superseded"),
        ("active", "deprecate", "applied", "deprecated"),
        ("superseded", "supersede", "already_superseded", "superseded"),
        ("superseded", "deprecate", "already_superseded", "superseded"),
        ("deprecated", "supersede", "terminal", "deprecated"),
        ("deprecated", "deprecate", "terminal", "deprecated"),
    ],
)
@pytest.mark.asyncio
async def test_monotonicity_table(
    session, start_status, operation, expect_reason, expect_status
):
    """The bridge only ever *adds* a supersession, never reverts one.

    The ``superseded``/``deprecate`` cell is the one this rule exists for:
    deprecating a superseded row would null its pointer, which reverts a
    supersession the digest has already reported.
    """
    candidate, successor = await _seeded(session, start_status)
    later = _mem(created_at=NOW + timedelta(days=1), content="a third memory")
    session.add(later)
    await session.flush()

    if operation == "supersede":
        result = await supersede(
            session, memory_id=candidate.id, superseded_by=later.id
        )
    else:
        result = await deprecate(session, memory_id=candidate.id)

    assert result.reason == expect_reason
    assert result.applied is (expect_reason == "applied")

    row = await _row(session, candidate.id)
    assert row["status"] == expect_status
    if start_status == "superseded":
        assert row["superseded_by"] == str(successor.id), (
            "a non-active candidate was re-pointed or reverted; monotonicity "
            "means the pointer a digest already reported cannot move"
        )
    assert await _dangling_pointers(session) == 0


@pytest.mark.parametrize(
    "start_status,expect_reason",
    [("superseded", "already_superseded"), ("deprecated", "terminal")],
)
@pytest.mark.asyncio
async def test_a_status_refusal_outranks_an_ordering_refusal(
    session, start_status, expect_reason
):
    """N3: the candidate's own status is decided before its proposed pointer.

    A non-active candidate whose successor also happens to be older must report
    the status reason, deterministically and regardless of timestamps. This is
    what makes the monotonicity cells timestamp-independent by construction,
    which is why the explicit-``created_at`` discipline is deliberately *not*
    extended to them — without the precedence they would flip their reason per
    run on a shared timestamp and random ids.

    It is also the one property the code-level status check owns alone. The
    ``AND status = 'active'`` predicate on the write would refuse this too, but
    only *after* the ordering predicate had already answered, and it would
    answer with the wrong reason.
    """
    candidate, _ = await _seeded(session, start_status)
    older = _mem(
        created_at=NOW - timedelta(days=10), content="a backfilled memory"
    )
    session.add(older)
    await session.flush()

    result = await supersede(
        session, memory_id=candidate.id, superseded_by=older.id
    )

    assert result.reason == expect_reason, (
        "an ordering refusal outranked a status refusal; the candidate is the "
        "row being written, so a refusal about that row is the more specific "
        "answer and must not depend on what its proposed pointer looks like"
    )
    assert result.applied is False
    assert (await _row(session, candidate.id))["status"] == start_status


@pytest.mark.asyncio
async def test_the_check_predicate_holds_through_every_transition(session):
    """Asserted independently of Postgres enforcing it, at each step.

    Every step also asserts what the primitive *did*. The dangling-pointer
    count alone stays zero under a completely inert primitive, so on its own
    this arm would borrow its teeth from its neighbours and report success
    while nothing had been written at all.
    """
    candidate, successor = await _pair(session)
    assert await _dangling_pointers(session) == 0

    flipped = await supersede(
        session, memory_id=candidate.id, superseded_by=successor.id
    )
    assert (flipped.reason, flipped.status) == ("applied", "superseded")
    assert await _dangling_pointers(session) == 0

    refused = await deprecate(session, memory_id=candidate.id)
    assert (refused.reason, refused.status) == ("already_superseded", "superseded")
    assert await _dangling_pointers(session) == 0

    fresh, _ = await _pair(session)
    retired = await deprecate(session, memory_id=fresh.id)
    assert (retired.reason, retired.status) == ("applied", "deprecated")
    assert await _dangling_pointers(session) == 0

    terminal = await supersede(
        session, memory_id=fresh.id, superseded_by=successor.id
    )
    assert (terminal.reason, terminal.status) == ("terminal", "deprecated")
    assert await _dangling_pointers(session) == 0


@pytest.mark.asyncio
async def test_the_two_statement_form_is_what_the_check_rejects(session):
    """The proof that writing both columns in one statement is doing work.

    A row CHECK is evaluated once per row per statement, so the single-statement
    flip has no observable intermediate state. Split it and the first half
    raises — which is exactly what this provokes.
    """
    candidate, successor = await _pair(session)

    with pytest.raises(IntegrityError) as caught:
        async with session.begin_nested():
            await session.execute(
                text(
                    "UPDATE memories SET status = 'superseded' "
                    "WHERE id = CAST(:id AS uuid)"
                ),
                {"id": str(candidate.id)},
            )
            await session.execute(
                text(
                    "UPDATE memories SET superseded_by = CAST(:sup AS uuid) "
                    "WHERE id = CAST(:id AS uuid)"
                ),
                {"id": str(candidate.id), "sup": str(successor.id)},
            )

    assert "chk_superseded_has_pointer" in str(caught.value)


# ───────────────────────── D6 — journaling ─────────────────────────


@pytest.mark.asyncio
async def test_one_event_per_real_transition_and_none_per_no_op(session):
    candidate, successor = await _pair(session)

    await supersede(session, memory_id=candidate.id, superseded_by=successor.id)
    assert len(await _events(session, candidate.id, "superseded")) == 1

    await supersede(session, memory_id=candidate.id, superseded_by=successor.id)
    await deprecate(session, memory_id=candidate.id)
    assert len(await _events(session, candidate.id)) == 1, (
        "a declined call journalled; `events` is append-only, so 'a row means "
        "a transition' has to hold by construction"
    )


@pytest.mark.asyncio
async def test_the_payload_carries_the_read_pointer_not_a_literal_null(session):
    candidate, successor = await _pair(session)
    fact_id = uuid.uuid4()

    await supersede(
        session,
        memory_id=candidate.id,
        superseded_by=successor.id,
        invalidating_fact_id=fact_id,
    )

    payload = (await _events(session, candidate.id, "superseded"))[0]["payload"]
    assert payload["before"] == {"status": "active", "superseded_by": None}
    assert payload["after"] == {
        "status": "superseded",
        "superseded_by": str(successor.id),
    }
    assert payload["reason"] == "status_bridge"
    assert payload["invalidating_fact_id"] == str(fact_id)
    assert "superseded_by" in payload["before"], (
        "the undo needs to restore status and pointer together, and an "
        "implicitly-NULL pointer makes that derivable only by knowing that a "
        "pre-supersession pointer is always NULL"
    )


@pytest.mark.asyncio
async def test_the_deprecate_payload_records_the_null_successor(session):
    candidate, _ = await _pair(session)
    fact_id = uuid.uuid4()

    await deprecate(
        session, memory_id=candidate.id, invalidating_fact_id=fact_id
    )

    payload = (await _events(session, candidate.id, "deprecated"))[0]["payload"]
    assert payload["before"] == {"status": "active", "superseded_by": None}
    assert payload["after"] == {"status": "deprecated", "superseded_by": None}
    assert payload["invalidating_fact_id"] == str(fact_id)


# ───────────────────────── D7 — the mutual flip ─────────────────────────


@pytest.mark.asyncio
async def test_the_mutual_flip_leaves_one_memory_active(session):
    """Both memories vanishing is the failure the ordering rule exists to stop.

    The count is asserted, not only the reason code: a refusal routed into the
    deprecate arm would satisfy a reason assertion while still emptying the
    active view.
    """
    first = _mem(created_at=NOW - timedelta(days=1), project="t245-mutual")
    second = _mem(created_at=NOW, project="t245-mutual", content="the other one")
    session.add_all([first, second])
    await session.flush()

    forward = await supersede(session, memory_id=first.id, superseded_by=second.id)
    backward = await supersede(session, memory_id=second.id, superseded_by=first.id)

    assert forward.reason == "applied"
    assert backward.reason == "successor_not_newer"

    result = await session.execute(
        text(
            "SELECT count(*) FROM memories "
            "WHERE project = 't245-mutual' AND status = 'active'"
        )
    )
    assert int(result.scalar_one()) == 1


@pytest.mark.asyncio
async def test_the_refusal_is_a_no_op_and_never_a_deprecation(session):
    first = _mem(created_at=NOW - timedelta(days=1), project="t245-mutual-b")
    second = _mem(created_at=NOW, project="t245-mutual-b", content="the other one")
    session.add_all([first, second])
    await session.flush()

    await supersede(session, memory_id=first.id, superseded_by=second.id)
    await supersede(session, memory_id=second.id, superseded_by=first.id)

    row = await _row(session, second.id)
    assert row["status"] == "active", (
        "the refused candidate was retired; falling through to the deprecate "
        "arm reinstates the two-memories-vanish outcome the rule prevents"
    )
    assert row["superseded_by"] is None
    assert await _events(session, second.id) == []


# ───────────────────────── the status bridge ─────────────────────────


async def _triple(session, *, subject: str, project: str = PROJECT) -> str:
    row = await KnowledgeTripleRepository(session).insert_open(
        triple_key=compute_triple_key(project, subject, "RUNS_ON", "linux"),
        subject_name=subject,
        object_name="linux",
        rel_type="RUNS_ON",
        fact=f"{subject} runs on linux",
        reference_time=NOW,
        project=project,
    )
    return row["id"]


async def _source(session, fact_id, memory_id=None, *, kind="memory", ref=None) -> None:
    await FactSourceRepository(session).add_source(
        fact_id=fact_id,
        source_kind=kind,
        source_ref=ref or memory_source_ref(memory_id),
        origin_key=f"origin:{ref or memory_id}",
    )


def _subject(prefix: str) -> str:
    """A fresh subject per call.

    ``ux_knowledge_triples_open`` admits one currently-open belief per
    ``triple_key``, and the key is derived from the names — so two invocations
    of a builder inside one test would collide on the second insert. Tests that
    need two independent fixtures are exactly the differential arms, so the
    builders have to be re-entrant.
    """
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _candidate_asserting(session, *, other_open: bool):
    """M, sourcing the invalidated fact and one other.

    ``other_open`` is the single flipped bit the guard-2 arms differ by: with
    it set the second fact is still currently open, so the memory is not spent.
    """
    memory = _mem(created_at=NOW - timedelta(days=2))
    session.add(memory)
    await session.flush()

    triples = KnowledgeTripleRepository(session)
    invalidated = await _triple(session, subject=_subject("postgres"))
    other = await _triple(session, subject=_subject("redis"))
    await _source(session, invalidated, memory.id)
    await _source(session, other, memory.id)

    await triples.close_window(invalidated, NOW)
    if not other_open:
        await triples.close_window(other, NOW)
    return memory


async def _successor_asserting(session, *, project: str = PROJECT):
    """S, the sole source of the triple that invalidated M's fact."""
    successor = _mem(created_at=NOW, project=project, content="the replacement")
    session.add(successor)
    await session.flush()
    invalidating = await _triple(
        session, subject=_subject("postgres-16"), project=project
    )
    await _source(session, invalidating, successor.id)
    return successor, invalidating


@pytest.mark.asyncio
async def test_guard2_fails_so_nothing_changes(session):
    """A memory still asserting a live fact is left alone. (T1)"""
    memory = await _candidate_asserting(session, other_open=True)
    successor, invalidating = await _successor_asserting(session)

    decision, result = await apply_status_bridge(
        session,
        invalidating_fact_id=invalidating,
        candidate_memory_id=memory.id,
    )

    assert decision.outcome == "no_change"
    assert decision.guard2_holds is False
    assert decision.guard1_holds is None, (
        "guard 1 was consulted after guard 2 failed; the ruled order says "
        "guard 2's answer dominates and guard 1 is not asked"
    )
    assert result is None

    row = await _row(session, memory.id)
    assert (row["status"], row["superseded_by"]) == ("active", None)
    assert await _events(session, memory.id) == []


@pytest.mark.asyncio
async def test_guard2_holds_so_the_memory_is_superseded(session):
    """The differential arm: one timestamp separates this from T1. (T1b)"""
    memory = await _candidate_asserting(session, other_open=False)
    successor, invalidating = await _successor_asserting(session)

    decision, result = await apply_status_bridge(
        session,
        invalidating_fact_id=invalidating,
        candidate_memory_id=memory.id,
    )

    assert decision.outcome == "supersede"
    assert decision.guard2_holds is True
    assert decision.guard1_holds is True
    assert decision.successor_newer is True
    assert decision.successor_id == str(successor.id)
    assert result is not None and result.applied is True

    row = await _row(session, memory.id)
    assert (row["status"], row["superseded_by"]) == (
        "superseded",
        str(successor.id),
    )


@pytest.mark.asyncio
async def test_the_two_guards_fail_differently(session):
    """The Done-when's "they fail differently", in executable form. (T2)

    Collapsing the two failures into one outcome fails this directly.
    """
    guard2_failed = await _candidate_asserting(session, other_open=True)
    _, invalidating_a = await _successor_asserting(session)
    await apply_status_bridge(
        session,
        invalidating_fact_id=invalidating_a,
        candidate_memory_id=guard2_failed.id,
    )

    guard1_failed = await _candidate_asserting(session, other_open=False)
    _, invalidating_b = await _successor_asserting(session)
    second_source = _mem(created_at=NOW, content="another claimant")
    session.add(second_source)
    await session.flush()
    await _source(session, invalidating_b, second_source.id)
    await apply_status_bridge(
        session,
        invalidating_fact_id=invalidating_b,
        candidate_memory_id=guard1_failed.id,
    )

    guard2_row = await _row(session, guard2_failed.id)
    guard1_row = await _row(session, guard1_failed.id)

    assert (guard2_row["status"], guard2_row["superseded_by"]) == ("active", None)
    assert (guard1_row["status"], guard1_row["superseded_by"]) == (
        "deprecated",
        None,
    )
    assert guard2_row["status"] != guard1_row["status"]


@pytest.mark.asyncio
async def test_the_both_fail_cell_is_absolute_no_change(session):
    """Guard 2 dominates even when guard 1 also fails. (T2b)

    This is the only arm that detects the rejected chain-order: every other
    cell produces an identical outcome under it. A memory asserting one
    invalidated fact whose replacement has several sources, plus one fact still
    open, is ordinary — any memory carrying more than one fact is a candidate.
    """
    memory = await _candidate_asserting(session, other_open=True)
    _, invalidating = await _successor_asserting(session)
    second_source = _mem(created_at=NOW, content="another claimant")
    session.add(second_source)
    await session.flush()
    await _source(session, invalidating, second_source.id)

    decision, result = await apply_status_bridge(
        session,
        invalidating_fact_id=invalidating,
        candidate_memory_id=memory.id,
    )

    assert decision.outcome == "no_change"
    assert decision.guard2_holds is False
    assert decision.guard1_holds is None
    assert result is None

    row = await _row(session, memory.id)
    assert (row["status"], row["superseded_by"]) == ("active", None)
    assert await _events(session, memory.id) == [], (
        "the both-fail cell wrote a transition; under the rejected chain-order "
        "this memory is deprecated while it still asserts a live fact"
    )


@pytest.mark.asyncio
async def test_guard1_fails_on_two_sources_so_the_memory_is_deprecated(session):
    """Spent, but with no single live replacement to point at. (T3)"""
    memory = await _candidate_asserting(session, other_open=False)
    _, invalidating = await _successor_asserting(session)
    second_source = _mem(created_at=NOW, content="another claimant")
    session.add(second_source)
    await session.flush()
    await _source(session, invalidating, second_source.id)

    decision, result = await apply_status_bridge(
        session,
        invalidating_fact_id=invalidating,
        candidate_memory_id=memory.id,
    )

    assert decision.outcome == "deprecate"
    assert decision.guard1_holds is False
    assert decision.live_source_count == 2
    assert result is not None and result.applied is True

    row = await _row(session, memory.id)
    assert (row["status"], row["superseded_by"]) == ("deprecated", None)


@pytest.mark.asyncio
async def test_guard1_fails_when_no_memory_sources_the_triple(session):
    """A code-kind source is not a successor a pointer can name. (T3b)"""
    memory = await _candidate_asserting(session, other_open=False)
    invalidating = await _triple(session, subject=_subject("postgres-16"))
    await _source(session, invalidating, kind="code", ref="repo-42:src/db.py")

    decision, _ = await apply_status_bridge(
        session,
        invalidating_fact_id=invalidating,
        candidate_memory_id=memory.id,
    )

    assert decision.outcome == "deprecate"
    assert decision.live_source_count == 0
    assert (await _row(session, memory.id))["status"] == "deprecated"


@pytest.mark.asyncio
async def test_guard1_fails_on_a_cross_project_successor(session):
    """Supersession never crosses the isolation boundary. (T3c)"""
    memory = await _candidate_asserting(session, other_open=False)
    successor, invalidating = await _successor_asserting(session, project="q")

    decision, _ = await apply_status_bridge(
        session,
        invalidating_fact_id=invalidating,
        candidate_memory_id=memory.id,
    )

    assert decision.outcome == "deprecate"
    assert decision.guard1_holds is False
    row = await _row(session, memory.id)
    assert (row["status"], row["superseded_by"]) == ("deprecated", None)
    assert (await _row(session, successor.id))["status"] == "active"


@pytest.mark.asyncio
async def test_the_candidate_is_excluded_before_the_count_is_taken(session):
    """A memory cannot be its own successor, but it can co-source. (T3d)

    Counting first and rejecting any self-source would deprecate a memory that
    has a perfectly good successor.
    """
    memory = await _candidate_asserting(session, other_open=False)
    successor, invalidating = await _successor_asserting(session)
    await _source(session, invalidating, memory.id)
    # The candidate co-sources the invalidating triple, so that triple has to
    # be closed too or the candidate is not spent and guard 2 — absolute, and
    # asked first — would decline before guard 1 is reached at all.
    await KnowledgeTripleRepository(session).close_window(invalidating, NOW)

    decision, _ = await apply_status_bridge(
        session,
        invalidating_fact_id=invalidating,
        candidate_memory_id=memory.id,
    )

    assert decision.outcome == "supersede"
    assert decision.live_source_count == 1
    assert decision.successor_id == str(successor.id)
    assert (await _row(session, memory.id))["superseded_by"] == str(successor.id)


@pytest.mark.asyncio
async def test_guard2_reads_the_minted_ref_not_the_given_spelling(session):
    """Guard 2's lookup is fail-open, so the ref spelling is load-bearing. (T7)

    A braced, upper-cased id matches no stored row. Without the single minter
    the provenance read returns ``(0, 0)``, the floor declines, and a spent
    memory silently stops being retired — the drill that proves this arm can
    fail.
    """
    memory = await _candidate_asserting(session, other_open=False)
    successor, invalidating = await _successor_asserting(session)
    noisy = "{" + str(memory.id).upper() + "}"

    decision, _ = await apply_status_bridge(
        session,
        invalidating_fact_id=invalidating,
        candidate_memory_id=noisy,
    )

    assert decision.sourced_total == 2
    assert decision.sourced_open == 0
    assert decision.outcome == "supersede"
    assert (await _row(session, memory.id))["superseded_by"] == str(successor.id)


@pytest.mark.asyncio
async def test_an_unlifted_memory_is_not_retired_on_absent_evidence(session):
    """Guard 2's floor: zero provenance is unlifted, not spent.

    Fact lifting runs on a cadence, so a young memory routinely sources
    nothing. Without the floor guard 2 holds vacuously and guard 1 then finds a
    perfectly good successor, so the bridge retires memories wholesale on the
    absence of evidence.
    """
    memory = _mem(created_at=NOW - timedelta(days=2))
    session.add(memory)
    await session.flush()
    successor, invalidating = await _successor_asserting(session)

    decision, result = await apply_status_bridge(
        session,
        invalidating_fact_id=invalidating,
        candidate_memory_id=memory.id,
    )

    assert (decision.sourced_total, decision.sourced_open) == (0, 0)
    assert decision.outcome == "no_change"
    assert decision.guard2_holds is False
    assert result is None
    assert (await _row(session, memory.id))["status"] == "active"


@pytest.mark.asyncio
async def test_the_bridge_refuses_an_older_successor_without_deprecating(session):
    """The ordering refusal short-circuits to no change, never to deprecate."""
    memory = await _candidate_asserting(session, other_open=False)
    successor = _mem(
        created_at=NOW - timedelta(days=5), content="a backfilled memory"
    )
    session.add(successor)
    await session.flush()
    invalidating = await _triple(session, subject=_subject("postgres-16"))
    await _source(session, invalidating, successor.id)

    decision, result = await apply_status_bridge(
        session,
        invalidating_fact_id=invalidating,
        candidate_memory_id=memory.id,
    )

    assert decision.outcome == "no_change"
    assert decision.guard1_holds is True
    assert decision.successor_newer is False
    assert result is None

    row = await _row(session, memory.id)
    assert (row["status"], row["superseded_by"]) == ("active", None)
    assert await _events(session, memory.id) == []


@pytest.mark.asyncio
async def test_a_vanished_candidate_declines_without_consulting_the_guards(session):
    """The arm a deleted memory reaches, with its record honest about it.

    A memory can be deleted while its provenance rows survive until the
    backstop reaps them, so "no row" does not imply "sources nothing". The
    counts are reported as zero because nothing was read, not as a claim about
    what the store holds.
    """
    _, invalidating = await _successor_asserting(session)

    decision, result = await apply_status_bridge(
        session,
        invalidating_fact_id=invalidating,
        candidate_memory_id=uuid.uuid4(),
    )

    assert decision.outcome == "no_change"
    assert (decision.sourced_total, decision.sourced_open) == (0, 0)
    assert decision.guard2_holds is False
    assert decision.guard1_holds is None
    assert result is None


def test_the_decision_is_pure_and_needs_no_session():
    """``decide_status_bridge`` is replayable from its inputs alone.

    Deliberately synchronous and fixture-free: requesting the session fixture
    to prove a function does not need one would undercut the claim.
    """
    candidate_id = str(uuid.UUID(int=7))
    successor = MemorySource(
        memory_id=str(uuid.UUID(int=8)),
        project=PROJECT,
        status="superseded",
        created_at=NOW,
    )

    decision = decide_status_bridge(
        memory_id=candidate_id,
        invalidating_fact_id=uuid.UUID(int=9),
        candidate_project=PROJECT,
        candidate_created_at=NOW - timedelta(days=1),
        sourced_total=2,
        sourced_open=0,
        invalidating_sources=(successor,),
    )

    assert decision.outcome == "supersede"
    assert decision.successor_id == successor.memory_id
    assert decision.sourced_total == 2
    assert decision.live_source_count == 1


@pytest.mark.asyncio
async def test_a_superseded_successor_still_counts_as_live(session):
    """"Live source memory" is row existence, never ``status='active'``.

    A successor that was itself superseded later in the same cycle is still the
    memory that replaced this one; requiring it to be active would deprecate
    the candidate and destroy the lineage the pointer exists to record.
    """
    memory = await _candidate_asserting(session, other_open=False)
    successor, invalidating = await _successor_asserting(session)
    latest = _mem(created_at=NOW + timedelta(days=1), content="the newest")
    session.add(latest)
    await session.flush()
    await supersede(session, memory_id=successor.id, superseded_by=latest.id)
    assert (await _row(session, successor.id))["status"] == "superseded"

    decision, _ = await apply_status_bridge(
        session,
        invalidating_fact_id=invalidating,
        candidate_memory_id=memory.id,
    )

    assert decision.outcome == "supersede"
    assert (await _row(session, memory.id))["superseded_by"] == str(successor.id)


# ───────────────────────── the single-path scans ─────────────────────────
#
# What these prove, and what they do not. Together they raise the cost of a
# second door: a consolidation module cannot hand-roll the flip (claim A) and
# cannot name the write-time detector (claim B), so the straightforward ways to
# bypass this module fail the build. They do **not** establish that
# consolidation *cannot* reach the fast path — claim B forbids a direct
# reference only, and a job that drives the ingest pipeline reaches the
# detector transitively with nothing tripping. These are a tripwire that makes
# a second writer's arrival loud, which is what the promotion blocker's own
# scan is and what it claims to be. Overclaiming one would be worse than the
# gap it hides, because a reader trusts a guard.
#
# They are AST walks rather than line scans on purpose. The line-scan
# precedent reads whole lines and skips only `#` comments, which is why one
# module has to avoid naming its own applier in a docstring. Four modules here
# legitimately discuss the detector in prose, and a line scan would either fail
# the build or need four exemptions that also blind it.

BACKEND = Path(__file__).resolve().parent.parent

_POINTER = "superseded_by"
_DETECTOR = "detect_supersessions"
_DETECTOR_MODULE = "app.services.supersession"
_RAW_MEMORY_UPDATE = re.compile(r"UPDATE\s+memories", re.IGNORECASE)

# Claim A: only these two modules write the pointer. The primitive is the slow
# path and the detector is the fast one; doc 08 §2.2 keeps them as two writers
# of one pointer under one CHECK.
_ALLOWED_POINTER_WRITERS = {
    "app/services/supersede.py",
    "app/services/supersession.py",
    # T2.13's undo door. **Not a third supersede door**, and the narrower claim
    # is enforced below rather than taken on trust: this module never writes
    # `'superseded'`, it only restores the status a `consolidated` event
    # journalled as the memory's state *before* the pass touched it, and it
    # journals the reversal with a readback that makes an unjournalled undo
    # unreachable. Doc 08 §2.1 already names undo alongside demote-first as a
    # pointer-affecting path ("undo (§7) and demote-first (§2.2) can never
    # leave a stored edge disagreeing with the pointer"), and doc 08 §7
    # requires the write to exist; the two-module allowlist predates the path.
    # The atomic-set contract this scan protects is unchanged — the restore
    # moves `status` and `superseded_by` in one statement under the one CHECK.
    "app/services/dream_undo.py",
}

# The narrowing that keeps the entry above from being a blank cheque.
_UNDO_MODULE = "app/services/dream_undo.py"

# Claim B: only the pipeline names the write-time detector.
_ALLOWED_DETECTOR_REFERENCES = {"app/services/pipeline.py"}


class _PointerWriteVisitor(ast.NodeVisitor):
    """Rules A1, A2, A2b and A3 — the write forms that exist today.

    Each rule's blind spot is stated rather than implied. A3 cannot see a flip
    written with a bound parameter (``SET status = :st``). A2 and A2b enumerate
    write shapes and miss a computed attribute name by construction. A1 is
    deliberately blind to a bare ``Name`` target so the model's own column
    declaration is not flagged, and A2 is scoped to two call shapes so a
    response construction reading the column is not.
    """

    def __init__(self, rel: str):
        self.rel = rel
        self.offenders: list[str] = []

    def _flag(self, node: ast.AST, rule: str, detail: str) -> None:
        self.offenders.append(f"{self.rel}:{node.lineno}: {rule} {detail}")

    def _check_target(self, target: ast.AST, node: ast.AST) -> None:
        if isinstance(target, ast.Attribute) and target.attr == _POINTER:
            self._flag(node, "A1", "attribute assignment")
        elif isinstance(target, (ast.Tuple, ast.List)):
            for element in target.elts:
                self._check_target(element, node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            self._check_target(target, node)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._check_target(node.target, node)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._check_target(node.target, node)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        writes_a_row = (isinstance(func, ast.Attribute) and func.attr == "values") or (
            isinstance(func, ast.Name) and func.id == "Memory"
        )
        if writes_a_row:
            if any(keyword.arg == _POINTER for keyword in node.keywords):
                self._flag(node, "A2", "pointer keyword on a row write")
            # A literal dict carrying the pointer key reaches these two call
            # shapes two ways, and each hangs off a different node. Passed
            # positionally — `.values({"superseded_by": s})` — it is an arg and
            # produces no keyword node at all. Splatted — `.values(**{...})` —
            # it rides a keyword whose `arg` is None, so the keyword rule above
            # steps over it. Both are literal dicts inside the shapes this rule
            # claims to cover, not the computed name the blind-spot note
            # reserves.
            dicts = [
                argument for argument in node.args if isinstance(argument, ast.Dict)
            ]
            dicts += [
                keyword.value
                for keyword in node.keywords
                if keyword.arg is None and isinstance(keyword.value, ast.Dict)
            ]
            for literal in dicts:
                if any(
                    isinstance(key, ast.Constant) and key.value == _POINTER
                    for key in literal.keys
                ):
                    self._flag(node, "A2", "pointer key in a values dict")
        if (
            isinstance(func, ast.Name)
            and func.id == "setattr"
            and len(node.args) >= 2
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value == _POINTER
        ):
            self._flag(node, "A2b", "setattr on the pointer")
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if (
            isinstance(node.value, str)
            and _RAW_MEMORY_UPDATE.search(node.value)
            and "superseded" in node.value
        ):
            self._flag(node, "A3", "raw-SQL status flip")
        self.generic_visit(node)


class _DetectorReferenceVisitor(ast.NodeVisitor):
    """Rule B1 — a direct reference to the write-time detector.

    Narrower than "any import of the detector's module": that module also
    holds the shared demotion helper, which the TTL sweep and the interactive
    delete both import legitimately, and flagging them would be a false
    positive against claim B's own wording. A bare module handle is still
    flagged, because it makes the detector reachable as an attribute.

    Relative imports are matched as well as absolute ones. An unaliased
    relative import is still caught at the use site by the name rule, but
    ``from .supersession import detect_supersessions as d`` escapes both
    halves at once — the module string is bare ``supersession`` so the import
    rule misses it, and the alias erases the name so the use site does too.
    """

    def __init__(self, rel: str):
        self.rel = rel
        self.offenders: list[str] = []

    def _flag(self, node: ast.AST, detail: str) -> None:
        self.offenders.append(f"{self.rel}:{node.lineno}: B1 {detail}")

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == _DETECTOR_MODULE:
                self._flag(node, "module import")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        names = {alias.name for alias in node.names}
        module = node.module or ""
        relative = node.level > 0
        names_the_module = module == _DETECTOR_MODULE or (
            relative and module.split(".")[-1] == "supersession"
        )
        if names_the_module and _DETECTOR in names:
            self._flag(node, "named import of the detector")
        elif "supersession" in names and (
            module == "app.services" or (relative and module == "")
        ):
            self._flag(node, "module handle")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id == _DETECTOR:
            self._flag(node, "name reference")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr == _DETECTOR:
            self._flag(node, "attribute reference")
        self.generic_visit(node)


def _scan(paths, visitor_class, allowlist, root=BACKEND) -> list[str]:
    offenders: list[str] = []
    for path in paths:
        rel = str(path.relative_to(root))
        if rel in allowlist:
            continue
        visitor = visitor_class(rel)
        visitor.visit(ast.parse(path.read_text()))
        offenders.extend(visitor.offenders)
    return offenders


def _forbidden_pointer_writes(paths, root=BACKEND) -> list[str]:
    return _scan(paths, _PointerWriteVisitor, _ALLOWED_POINTER_WRITERS, root)


def _forbidden_detector_references(paths, root=BACKEND) -> list[str]:
    return _scan(paths, _DetectorReferenceVisitor, _ALLOWED_DETECTOR_REFERENCES, root)


def _app_sources() -> list[Path]:
    paths = [p for p in (BACKEND / "app").rglob("*.py") if "__pycache__" not in str(p)]
    assert len(paths) > 100, (
        f"only found {len(paths)} files under app/ — the scans below would "
        "pass vacuously; check BACKEND / the glob path"
    )
    return paths


def test_only_the_two_writers_touch_the_supersession_pointer():
    offenders = _forbidden_pointer_writes(_app_sources())
    assert not offenders, (
        "app code outside the primitive and the write-time detector writes "
        "`memories.superseded_by`:\n" + "\n".join(offenders) + "\nConsolidation "
        "supersedes through the primitive, so a hand-rolled flip is a second "
        "door past its guards and its journal."
    )


def test_the_undo_door_never_writes_a_supersession():
    """The undo module is allowlisted for the pointer, and this is the reason.

    A third module writing `superseded_by` is only acceptable while it can
    exclusively *un*-supersede. It writes the status as a bound parameter taken
    from a journalled before-value and validated against the enum, so the
    module contains no `'superseded'` literal outside that validator — the
    moment one appears, the allowlist entry has outgrown its justification and
    this fails.

    **What this scan does not establish.** It enforces two syntactic
    properties: no `'superseded'` literal outside the enum validator, and no
    literal status inside a raw `UPDATE memories`. It cannot see that the
    bound value is a *journalled* before-value rather than something the
    module computed, which is a runtime property and lives in
    `tests/test_dream_undo.py`'s behavioural assertions. Nor does it prove the
    value can never be `'superseded'`: with today's producer that is
    unreachable, because the pass only ever journals a before-status of
    `'active'` — a different producer journalling a `consolidated` subsume
    from another starting status would make it reachable, and the preflight
    enum check would admit it. Stated rather than implied, because a reader
    trusts a guard.
    """
    tree = ast.parse((BACKEND / _UNDO_MODULE).read_text())

    # The one legitimate mention: the enum allowlist the journalled status is
    # validated against before it is restored.
    validator = next(
        (
            node for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(t, ast.Name) and t.id == "_LEGAL_STATUSES"
                for t in node.targets
            )
        ),
        None,
    )
    assert validator is not None, (
        f"{_UNDO_MODULE} no longer validates the journalled status against the "
        "enum before restoring it"
    )
    exempt = {id(n) for n in ast.walk(validator)}

    stray = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and node.value == "superseded"
        and id(node) not in exempt
    ]
    assert not stray, (
        f"{_UNDO_MODULE} names the superseded status outside its validator at "
        f"line(s) {stray}; it is allowlisted for the pointer only because it "
        "restores a journalled prior status and can never create one."
    )

    # And the status it does write is a bound parameter, never a literal.
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and _RAW_MEMORY_UPDATE.search(node.value)
        ):
            assert not re.search(r"status\s*=\s*'", node.value), (
                f"{_UNDO_MODULE} writes a literal status at line {node.lineno}"
            )


def test_only_the_pipeline_names_the_write_time_detector():
    offenders = _forbidden_detector_references(_app_sources())
    assert not offenders, (
        "app code outside Phase 5 references the write-time detector:\n"
        + "\n".join(offenders)
        + "\nThe detector is the fast path and belongs to ingest; a "
        "consolidation caller reaching it bypasses the primitive."
    )


@pytest.mark.parametrize(
    "rule,body",
    [
        ("A1", "def f(m, s):\n    m.superseded_by = s\n"),
        (
            "A2-keyword",
            "def f(u, s):\n    return u.values(status='superseded', "
            "superseded_by=s)\n",
        ),
        (
            "A2-dict",
            "def f(u, s):\n    return u.values({'superseded_by': s})\n",
        ),
        (
            "A2-model",
            "def f(s):\n    return Memory(content='x', superseded_by=s)\n",
        ),
        (
            "A2-splat-values",
            "def f(u, s):\n    return u.values(**{'superseded_by': s})\n",
        ),
        (
            "A2-splat-model",
            "def f(s):\n    return Memory(**{'superseded_by': s})\n",
        ),
        ("A2b", "def f(m, s):\n    setattr(m, 'superseded_by', s)\n"),
        (
            "A3",
            "SQL = \"UPDATE memories SET status='superseded', "
            "superseded_by=:s WHERE id=:i\"\n",
        ),
    ],
)
def test_the_pointer_scan_flags_every_rule(tmp_path, rule, body):
    """In-suite negative control — the guard's teeth proven every run."""
    fake = tmp_path / "app" / "services"
    fake.mkdir(parents=True, exist_ok=True)
    violation = fake / f"eager_{rule.replace('-', '_').lower()}.py"
    violation.write_text(body)

    offenders = _forbidden_pointer_writes([violation], root=tmp_path)

    assert offenders, (
        f"the real guard failed to flag a synthesised {rule} violation; the "
        "tree-wide scan would be reporting success while blind"
    )


@pytest.mark.parametrize(
    "shape,body",
    [
        ("named-import", "from app.services.supersession import detect_supersessions\n"),
        ("module-import", "import app.services.supersession\n"),
        ("module-handle", "from app.services import supersession\n"),
        (
            "attribute",
            "import app.services.supersession as s\n"
            "async def go(x):\n    await s.detect_supersessions(x)\n",
        ),
        ("relative-import", "from .supersession import detect_supersessions\n"),
        # The one shape that escapes both halves at once: the bare module
        # string dodges the import rule and the alias erases the name the use
        # site would otherwise carry.
        (
            "relative-aliased",
            "from .supersession import detect_supersessions as d\n"
            "async def go(x):\n    await d(x)\n",
        ),
        ("relative-handle", "from . import supersession\n"),
    ],
)
def test_the_detector_scan_flags_every_shape(tmp_path, shape, body):
    fake = tmp_path / "app" / "services"
    fake.mkdir(parents=True, exist_ok=True)
    violation = fake / f"eager_{shape.replace('-', '_')}.py"
    violation.write_text(body)

    offenders = _forbidden_detector_references([violation], root=tmp_path)

    assert offenders, (
        f"the real guard failed to flag a synthesised {shape} reference"
    )


def test_the_detector_scan_admits_the_shared_demotion_helper(tmp_path):
    """The narrowing is deliberate, so it is pinned rather than assumed.

    The delete paths import a sibling helper out of the detector's module and
    must keep passing; a rule that flagged them would be a false positive
    against claim B's own wording, and the exemption is the kind of thing that
    silently widens into "the module is fine" if nothing holds it.
    """
    fake = tmp_path / "app" / "services"
    fake.mkdir(parents=True, exist_ok=True)
    innocent = fake / "sweeper.py"
    innocent.write_text(
        "from app.services.supersession import demote_dependents\n"
        "async def sweep(session, ids):\n"
        "    await demote_dependents(session, ids)\n"
    )

    assert _forbidden_detector_references([innocent], root=tmp_path) == []


def test_the_detector_scan_admits_a_relative_sibling_import(tmp_path):
    """The relative arm must not widen into "any neighbouring module".

    The detector's module is a sibling of every other service, so a rule keyed
    on relative imports is one careless ``endswith`` away from flagging
    ``from .supersession_hold import ...`` and every legitimate relative import
    of the shared demotion helper.
    """
    fake = tmp_path / "app" / "services"
    fake.mkdir(parents=True, exist_ok=True)
    innocent = fake / "neighbour.py"
    innocent.write_text(
        "from .supersession import demote_dependents\n"
        "from .supersession_hold import detect_supersession_hold\n"
    )

    assert _forbidden_detector_references([innocent], root=tmp_path) == []


def test_the_primitive_never_removes_a_row():
    """Doc 08 §2.2's demote-first clause, discharged by construction.

    The primitive issues one ``UPDATE`` and nothing else, so the SET-NULL
    hazard is unreachable from it — which is only true while it stays that way.
    A later edit that adds a removal fails here rather than aborting a sweep in
    production, where the symptom is that no expired row is ever reclaimed.
    """
    source = (BACKEND / "app" / "services" / "supersede.py").read_text()
    tree = ast.parse(source)

    removals = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and re.search(r"DELETE\s+FROM", node.value, re.IGNORECASE)
    ]
    assert removals == []

    orm_deletes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "delete"
    ]
    assert orm_deletes == []

    assert "demote_" + "dependents" not in source, (
        "the primitive reached for the demotion helper; it has no delete to "
        "demote before, and joining the delete paths is not its job"
    )
