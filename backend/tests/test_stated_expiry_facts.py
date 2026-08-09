"""The fact-side stated expiry: recorded at lift, spent by the arm (T2.85).

Doc 08 §3.1 and §9 contradicted each other on where a fact's *stated* expiry
goes, and the ruling (2026-08-06) is that it goes in neither place they named.
This suite is the ruling in executable form, and the two probes below are the
ones the analysis measured in a rolled-back transaction before the column
existed — they are what makes the two rejected readings concrete rather than
argued.

**Probe A — §9's literal reading (`invalid_at` written at lift).** A future
`invalid_at` drops the fact out of `OPEN_BELIEF_PREDICATE` on the day it is
written, because that predicate is `expired_at IS NULL AND invalid_at IS NULL`
with no time comparison. The fact leaves the retrieval channel years early and
nothing errors.

**Probe B — §3.1's literal reading (`expired_at` written at lift).** `as_of`
deliberately ignores `expired_at`, so a historical question asked for an
instant *after* the stated date still answers "believed". The fact is served
as current five months past its own expiry.

`stated_expiry` is the third position: recorded at write time, spent only once
the date passes, and then written to `invalid_at` — the column that actually
means "this belief's window closed".
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.repositories.knowledge_triples import (
    OPEN_BELIEF_PREDICATE,
    KnowledgeTripleRepository,
)
from app.services.verification_recompute import (
    StatedExpiryOutcome,
    _close_stated_expiries,
)

NOW = datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)
PAST = NOW - timedelta(days=30)
FUTURE = NOW + timedelta(days=365)

PROJECT = "t285-expiry"


async def mint(session, *, key: str, stated_expiry=None, project=PROJECT):
    return await KnowledgeTripleRepository(session).insert_open(
        triple_key=key,
        subject_name="licence", object_name="2026", rel_type="VALID_UNTIL",
        fact=f"the {key} licence is valid until 2026-12-31",
        reference_time=NOW - timedelta(days=90),
        project=project,
        stated_expiry=stated_expiry,
    )


async def open_ids(session) -> set[str]:
    rows = await session.execute(
        text(
            f"SELECT CAST(id AS text) FROM knowledge_triples "
            f"WHERE project = CAST(:p AS text) AND {OPEN_BELIEF_PREDICATE}"
        ),
        {"p": PROJECT},
    )
    return {row[0] for row in rows}


async def column(session, fact_id, name):
    return (
        await session.execute(
            text(f"SELECT {name} FROM knowledge_triples WHERE id = CAST(:i AS uuid)"),
            {"i": fact_id},
        )
    ).scalar_one()


# ── recorded at lift, and only recorded ──────────────────────────────


async def test_a_stated_expiry_is_recorded_without_closing_the_window(session):
    """Probe A, refused. The fact stays believed until the date arrives; a
    future `invalid_at` would have removed it from the channel today."""
    row = await mint(session, key="k-future", stated_expiry=FUTURE)

    assert await column(session, row["id"], "stated_expiry") is not None
    assert await column(session, row["id"], "invalid_at") is None
    assert await column(session, row["id"], "expired_at") is None
    assert row["id"] in await open_ids(session)


async def test_a_fact_with_no_stated_expiry_records_none(session):
    row = await mint(session, key="k-none")
    assert await column(session, row["id"], "stated_expiry") is None
    assert row["id"] in await open_ids(session)


# ── spent by the arm, once the date passes ───────────────────────────


async def test_the_arm_closes_the_window_when_the_date_has_passed(session):
    row = await mint(session, key="k-past", stated_expiry=PAST)

    outcome = await _close_stated_expiries(session, moment=NOW, batch_size=100)

    assert outcome.windows_closed == 1
    assert await column(session, row["id"], "invalid_at") == PAST
    # Probe B, refused: `expired_at` stays NULL, so `as_of` still answers the
    # historical question correctly for instants before the stated date.
    assert await column(session, row["id"], "expired_at") is None
    assert row["id"] not in await open_ids(session)


async def test_a_future_expiry_is_left_alone(session):
    row = await mint(session, key="k-not-yet", stated_expiry=FUTURE)

    outcome = await _close_stated_expiries(session, moment=NOW, batch_size=100)

    assert outcome.windows_closed == 0
    assert await column(session, row["id"], "invalid_at") is None
    assert row["id"] in await open_ids(session)


async def test_the_arm_is_idempotent(session):
    await mint(session, key="k-twice", stated_expiry=PAST)

    first = await _close_stated_expiries(session, moment=NOW, batch_size=100)
    second = await _close_stated_expiries(session, moment=NOW, batch_size=100)

    assert first.windows_closed == 1
    assert second.windows_closed == 0


async def test_a_window_already_closed_is_never_reopened(session):
    """The arm writes `invalid_at` only where it is NULL. A fact whose window
    the disjoint-window pass already closed at a different instant must keep
    that instant — overwriting it would rewrite history the pass established."""
    row = await mint(session, key="k-closed", stated_expiry=PAST)
    earlier = PAST - timedelta(days=10)
    await KnowledgeTripleRepository(session).close_window(row["id"], earlier)

    outcome = await _close_stated_expiries(session, moment=NOW, batch_size=100)

    assert outcome.windows_closed == 0
    assert await column(session, row["id"], "invalid_at") == earlier


async def test_an_expired_fact_is_left_alone(session):
    """`expired_at` means the sources were withdrawn. Closing a window on a
    withdrawn fact would assert a belief transition that never happened."""
    row = await mint(session, key="k-expired", stated_expiry=PAST)
    await session.execute(
        text("UPDATE knowledge_triples SET expired_at = CAST(:t AS timestamptz) "
             "WHERE id = CAST(:i AS uuid)"),
        {"t": NOW, "i": row["id"]},
    )

    outcome = await _close_stated_expiries(session, moment=NOW, batch_size=100)

    assert outcome.windows_closed == 0
    assert await column(session, row["id"], "invalid_at") is None


async def test_a_zero_batch_disables_the_arm(session):
    await mint(session, key="k-disabled", stated_expiry=PAST)
    outcome = await _close_stated_expiries(session, moment=NOW, batch_size=0)
    assert outcome == StatedExpiryOutcome()


# ── the invariant the ruling was chosen to preserve ──────────────────


async def test_the_open_belief_predicate_is_unchanged(session):
    """Option 2 was chosen because it leaves the predicate and its four partial
    indexes byte-identical. A time comparison here — the shape option 1 needed
    — is what no partial index can carry."""
    assert "now()" not in OPEN_BELIEF_PREDICATE.lower()
    assert "current_timestamp" not in OPEN_BELIEF_PREDICATE.lower()
    assert "expired_at IS NULL" in OPEN_BELIEF_PREDICATE
    assert "invalid_at IS NULL" in OPEN_BELIEF_PREDICATE


async def test_one_open_belief_per_key_still_holds(session):
    """The unique index keeps its meaning: closing a window frees the key, so
    a successor may open — which is exactly the transition a stated expiry is
    supposed to permit."""
    from sqlalchemy.exc import IntegrityError

    await mint(session, key="k-unique", stated_expiry=PAST)
    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            await mint(session, key="k-unique")

    await _close_stated_expiries(session, moment=NOW, batch_size=100)
    successor = await mint(session, key="k-unique")
    assert successor["id"] in await open_ids(session)


async def test_the_sweep_index_exists_and_matches_the_arm(session):
    """The arm's predicate and the index's must not drift: a mismatch turns an
    indexed sweep into a full scan of every open fact, silently."""
    row = (
        await session.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE indexname = 'ix_knowledge_triples_stated_expiry'"
            )
        )
    ).scalar_one_or_none()

    assert row is not None, "the stated-expiry sweep index is missing"
    for clause in ("expired_at IS NULL", "invalid_at IS NULL", "stated_expiry IS NOT NULL"):
        assert clause.lower() in row.lower()
