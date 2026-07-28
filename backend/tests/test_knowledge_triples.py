"""The belief axis is independent of the verification axis, and never deletes.

A Layer-2 fact can be expired yet confirmed (doc 08 §3): belief and
verification are orthogonal, and a method that moved both would make
"well-verified but no longer current" unrepresentable. These tests pin both
directions of that independence, plus the invalidate-not-delete contract that
makes "what did we believe as of date X" answerable at all.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

import app.repositories.knowledge_triples as knowledge_triples_module
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services.events import EVENT_TYPES
from app.services.triple_key import compute_triple_key

PROJECT = "t201-belief-axis"
NOW = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)


def _key(subject: str = "ada", rel: str = "WORKS_AT", obj: str = "acme") -> str:
    return compute_triple_key(PROJECT, subject, rel, obj)


async def _open(
    repo: KnowledgeTripleRepository,
    *,
    subject: str = "ada",
    rel: str = "WORKS_AT",
    obj: str = "acme",
    valid_at: datetime | None = None,
    **overrides,
) -> dict:
    return await repo.insert_open(
        triple_key=_key(subject, rel, obj),
        subject_name=subject,
        object_name=obj,
        rel_type=rel,
        fact=f"{subject} {rel} {obj}",
        reference_time=NOW,
        project=PROJECT,
        valid_at=valid_at,
        **overrides,
    )


async def _set_status(session, triple_id: str, status: str) -> None:
    """Move the verification axis by hand.

    Deliberately direct SQL: the verification writer refuses ``confirmed``
    because only a human may ratify, and this fixture is not a human. The
    refusal and this shortcut are meant to be on different paths.
    """
    await session.execute(
        text(
            "UPDATE knowledge_triples SET verification_status = CAST(:s AS text) "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"s": status, "id": str(triple_id)},
    )


async def _events_for(session, triple_id: str) -> list[dict]:
    result = await session.execute(
        text(
            "SELECT event_type, object_type, payload FROM events "
            "WHERE object_id = CAST(:id AS uuid) ORDER BY created_at, id"
        ),
        {"id": str(triple_id)},
    )
    return [dict(row) for row in result.mappings().all()]


async def _read(session, triple_id: str) -> dict:
    result = await session.execute(
        text(
            "SELECT valid_at, invalid_at, expired_at, verification_status, "
            "subject_name, object_name, rel_type, fact, project, triple_key "
            "FROM knowledge_triples WHERE id = CAST(:id AS uuid)"
        ),
        {"id": str(triple_id)},
    )
    return dict(result.mappings().one())


# ── Axis independence ───────────────────────────────────────────────


async def test_expire_leaves_a_confirmed_status_confirmed(session):
    repo = KnowledgeTripleRepository(session)
    row = await _open(repo)
    await _set_status(session, row["id"], "confirmed")

    expired = await repo.expire(row["id"])

    assert expired["expired_at"] is not None
    assert expired["verification_status"] == "confirmed"
    assert (await _read(session, row["id"]))["verification_status"] == "confirmed"


async def test_close_window_leaves_a_corroborated_status_corroborated(session):
    repo = KnowledgeTripleRepository(session)
    row = await _open(repo, valid_at=NOW)
    await _set_status(session, row["id"], "corroborated")

    closed = await repo.close_window(row["id"], NOW + timedelta(days=30))

    assert closed["invalid_at"] == NOW + timedelta(days=30)
    assert closed["verification_status"] == "corroborated"


async def test_moving_verification_status_leaves_the_belief_axis_untouched(session):
    repo = KnowledgeTripleRepository(session)
    row = await _open(repo, valid_at=NOW)
    await repo.close_window(row["id"], NOW + timedelta(days=30))
    before = await _read(session, row["id"])

    await _set_status(session, row["id"], "disputed")

    after = await _read(session, row["id"])
    assert after["verification_status"] == "disputed"
    assert after["valid_at"] == before["valid_at"] == NOW
    assert after["invalid_at"] == before["invalid_at"] == NOW + timedelta(days=30)
    assert after["expired_at"] is None and before["expired_at"] is None


async def test_confirmed_but_expired_fact_is_representable(session):
    repo = KnowledgeTripleRepository(session)
    row = await _open(repo, valid_at=NOW)
    await _set_status(session, row["id"], "confirmed")
    await repo.close_window(row["id"], NOW + timedelta(days=30))

    await repo.expire(row["id"])

    persisted = await _read(session, row["id"])
    assert persisted["verification_status"] == "confirmed"
    assert persisted["expired_at"] is not None

    live_ids = [r["id"] for r in await repo.get_live(project=PROJECT)]
    assert row["id"] not in live_ids

    inside_window = [
        r["id"] for r in await repo.as_of(NOW + timedelta(days=1), project=PROJECT)
    ]
    assert inside_window == [row["id"]]


# ── Invalidate, never delete ────────────────────────────────────────


async def test_expire_is_a_resave_not_a_delete(session):
    repo = KnowledgeTripleRepository(session)
    row = await _open(repo, valid_at=NOW, confidence=0.5, source_file="notes.md")

    await repo.expire(row["id"])

    persisted = await _read(session, row["id"])
    assert persisted["expired_at"] is not None
    assert persisted["valid_at"] == NOW
    assert persisted["invalid_at"] is None
    assert persisted["fact"] == "ada WORKS_AT acme"
    assert persisted["subject_name"] == "ada"
    assert persisted["object_name"] == "acme"
    assert persisted["rel_type"] == "WORKS_AT"
    assert persisted["triple_key"] == _key()

    count = await session.execute(
        text(
            "SELECT count(*) FROM knowledge_triples WHERE id = CAST(:id AS uuid)"
        ),
        {"id": row["id"]},
    )
    assert count.scalar_one() == 1


async def test_expiring_an_already_expired_row_keeps_the_original_time(session):
    """A fact was disbelieved once; a second expire must not rewrite when.

    The prior withdrawal is seeded by direct SQL rather than by a first
    ``expire()`` call, because ``now()`` is transaction-constant and two calls
    inside one transaction would agree even without the guard.
    """
    repo = KnowledgeTripleRepository(session)
    row = await _open(repo, valid_at=NOW)
    withdrawn_at = NOW - timedelta(days=7)
    await session.execute(
        text(
            "UPDATE knowledge_triples SET expired_at = CAST(:e AS timestamptz) "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"e": withdrawn_at, "id": row["id"]},
    )

    reexpired = await repo.expire(row["id"])

    assert reexpired["expired_at"] == withdrawn_at


async def test_module_issues_no_delete_statement(session):
    source = Path(knowledge_triples_module.__file__).read_text(encoding="utf-8")
    assert re.search(r"\bDELETE\s+FROM\b", source, re.IGNORECASE) is None


async def test_as_of_window_is_half_open_at_the_boundary_instant(session):
    """Two adjacent windows must match at the shared instant exactly once.

    The boundary is the only place both comparison operators are load-bearing.
    An upper bound of `invalid_at >= t` would return both stints here, and a
    lower bound of `valid_at < t` would return neither, so the single-element
    assertion below fails under either inversion. Away from the boundary both
    regressions are invisible.
    """
    repo = KnowledgeTripleRepository(session)
    boundary = NOW + timedelta(days=365)
    first_stint = await _open(repo, valid_at=NOW)
    await repo.close_window(first_stint["id"], boundary)
    second_stint = await _open(repo, valid_at=boundary)

    at_boundary = [r["id"] for r in await repo.as_of(boundary, project=PROJECT)]
    assert at_boundary == [second_stint["id"]]

    just_before = [
        r["id"]
        for r in await repo.as_of(boundary - timedelta(microseconds=1), project=PROJECT)
    ]
    assert just_before == [first_stint["id"]]


# ── The partial-unique and the ordering that satisfies it ───────────


async def test_disjoint_windows_leave_two_live_rows(session):
    repo = KnowledgeTripleRepository(session)
    first_stint = await _open(repo, valid_at=NOW)
    await repo.close_window(first_stint["id"], NOW + timedelta(days=365))
    second_stint = await _open(repo, valid_at=NOW + timedelta(days=730))

    assert first_stint["triple_key"] == second_stint["triple_key"]

    live = await repo.get_live(triple_key=_key())
    assert {r["id"] for r in live} == {first_stint["id"], second_stint["id"]}
    assert all(r["expired_at"] is None for r in live)

    gap = [r["id"] for r in await repo.as_of(NOW + timedelta(days=500), project=PROJECT)]
    assert gap == []
    inside_first = [
        r["id"] for r in await repo.as_of(NOW + timedelta(days=1), project=PROJECT)
    ]
    assert inside_first == [first_stint["id"]]


async def test_stale_on_arrival_closes_the_older_row_before_inserting(session):
    repo = KnowledgeTripleRepository(session)
    older = await _open(repo, valid_at=NOW)

    await repo.close_window(older["id"], NOW + timedelta(days=30))
    newer = await _open(repo, valid_at=NOW + timedelta(days=30))

    older_row = await _read(session, older["id"])
    newer_row = await _read(session, newer["id"])
    assert older_row["invalid_at"] == NOW + timedelta(days=30)
    assert newer_row["invalid_at"] is None
    assert newer_row["expired_at"] is None
    assert older_row["triple_key"] == newer_row["triple_key"]


# ── Journaling (T2.01 step 6) ───────────────────────────────────────


async def test_invalidated_is_in_the_closed_vocabulary():
    assert "invalidated" in EVENT_TYPES


async def test_insert_open_journals_nothing(session):
    repo = KnowledgeTripleRepository(session)
    row = await _open(repo, valid_at=NOW)

    assert await _events_for(session, row["id"]) == []


async def test_close_window_journals_exactly_one_invalidated_event_with_null_before(session):
    """The first close on an open row: `invalid_at` starts NULL, so the
    journalled "before" must be NULL too, not the new value duplicated."""
    repo = KnowledgeTripleRepository(session)
    row = await _open(repo, valid_at=NOW)

    await repo.close_window(row["id"], NOW + timedelta(days=30))

    events = await _events_for(session, row["id"])
    assert len(events) == 1
    event = events[0]
    assert event["event_type"] == "invalidated"
    assert event["object_type"] == "fact"
    assert event["payload"]["before"]["invalid_at"] is None
    assert event["payload"]["after"]["invalid_at"] == (NOW + timedelta(days=30)).isoformat()


async def test_close_window_journals_the_prior_invalid_at_as_before(session):
    """A second close on an already-closed row must carry the row's actual
    prior `invalid_at`, not NULL, as "before"."""
    repo = KnowledgeTripleRepository(session)
    row = await _open(repo, valid_at=NOW)
    first_close = NOW + timedelta(days=30)
    second_close = NOW + timedelta(days=60)
    await repo.close_window(row["id"], first_close)

    await repo.close_window(row["id"], second_close)

    events = await _events_for(session, row["id"])
    assert len(events) == 2
    second_event = events[1]
    assert second_event["event_type"] == "invalidated"
    assert second_event["payload"]["before"]["invalid_at"] == first_close.isoformat()
    assert second_event["payload"]["after"]["invalid_at"] == second_close.isoformat()


async def test_expire_journals_exactly_one_expired_event(session):
    repo = KnowledgeTripleRepository(session)
    row = await _open(repo, valid_at=NOW)

    expired = await repo.expire(row["id"])

    events = await _events_for(session, row["id"])
    assert len(events) == 1
    event = events[0]
    assert event["event_type"] == "expired"
    assert event["object_type"] == "fact"
    assert event["payload"]["before"]["expired_at"] is None
    assert event["payload"]["after"]["expired_at"] == expired["expired_at"].isoformat()


async def test_set_verification_status_journals_exactly_one_verified_event(session):
    repo = KnowledgeTripleRepository(session)
    row = await _open(repo, valid_at=NOW)

    await repo.set_verification_status(row["id"], "corroborated")

    events = await _events_for(session, row["id"])
    assert len(events) == 1
    event = events[0]
    assert event["event_type"] == "verified"
    assert event["object_type"] == "fact"
    assert event["payload"]["before"]["verification_status"] == "candidate"
    assert event["payload"]["after"]["verification_status"] == "corroborated"


async def test_set_verification_status_refusing_confirmed_journals_nothing(session):
    repo = KnowledgeTripleRepository(session)
    row = await _open(repo, valid_at=NOW)

    with pytest.raises(ValueError, match="T2.05"):
        await repo.set_verification_status(row["id"], "confirmed")

    assert await _events_for(session, row["id"]) == []


async def test_set_verification_status_refusing_unknown_value_journals_nothing(session):
    repo = KnowledgeTripleRepository(session)
    row = await _open(repo, valid_at=NOW)

    with pytest.raises(ValueError):
        await repo.set_verification_status(row["id"], "bogus")

    assert await _events_for(session, row["id"]) == []


# ── Verification-status writer ──────────────────────────────────────


async def test_set_verification_status_refuses_confirmed(session):
    repo = KnowledgeTripleRepository(session)
    row = await _open(repo, valid_at=NOW)

    with pytest.raises(ValueError, match="T2.05"):
        await repo.set_verification_status(row["id"], "confirmed")

    assert (await _read(session, row["id"]))["verification_status"] == "candidate"


async def test_set_verification_status_refuses_unknown_value(session):
    repo = KnowledgeTripleRepository(session)
    row = await _open(repo, valid_at=NOW)

    with pytest.raises(ValueError):
        await repo.set_verification_status(row["id"], "bogus")

    assert (await _read(session, row["id"]))["verification_status"] == "candidate"


@pytest.mark.parametrize("status", ["candidate", "corroborated", "disputed"])
async def test_set_verification_status_round_trips_permitted_values(session, status):
    repo = KnowledgeTripleRepository(session)
    row = await _open(repo, valid_at=NOW)

    await repo.set_verification_status(row["id"], status)

    assert (await _read(session, row["id"]))["verification_status"] == status


async def test_set_verification_status_leaves_belief_axis_untouched(session):
    repo = KnowledgeTripleRepository(session)
    row = await _open(repo, valid_at=NOW)
    await repo.close_window(row["id"], NOW + timedelta(days=30))
    await repo.expire(row["id"])
    before = await _read(session, row["id"])

    await repo.set_verification_status(row["id"], "corroborated")

    after = await _read(session, row["id"])
    assert after["verification_status"] == "corroborated"
    assert after["valid_at"] == before["valid_at"]
    assert after["invalid_at"] == before["invalid_at"]
    assert after["expired_at"] == before["expired_at"]


async def test_a_second_open_row_on_one_key_is_rejected(session):
    """Why the close-then-insert ordering is a contract and not a preference."""
    repo = KnowledgeTripleRepository(session)
    older = await _open(repo, valid_at=NOW)

    with pytest.raises(IntegrityError, match="ux_knowledge_triples_open"):
        async with session.begin_nested():
            await _open(repo, valid_at=NOW + timedelta(days=30))

    await repo.close_window(older["id"], NOW + timedelta(days=30))
    newer = await _open(repo, valid_at=NOW + timedelta(days=30))
    assert newer["invalid_at"] is None
