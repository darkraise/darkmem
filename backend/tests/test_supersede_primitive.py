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

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models.memory import Memory
from app.services.supersede import (
    deprecate,
    successor_is_newer,
    supersede,
)

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


@pytest.mark.asyncio
async def test_the_check_predicate_holds_through_every_transition(session):
    """Asserted independently of Postgres enforcing it, at each step."""
    candidate, successor = await _pair(session)
    assert await _dangling_pointers(session) == 0

    await supersede(session, memory_id=candidate.id, superseded_by=successor.id)
    assert await _dangling_pointers(session) == 0

    await deprecate(session, memory_id=candidate.id)
    assert await _dangling_pointers(session) == 0

    fresh, _ = await _pair(session)
    await deprecate(session, memory_id=fresh.id)
    assert await _dangling_pointers(session) == 0

    await supersede(session, memory_id=fresh.id, superseded_by=successor.id)
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
