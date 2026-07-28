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
