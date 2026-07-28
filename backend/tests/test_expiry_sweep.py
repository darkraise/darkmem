"""The TTL expiry sweep and its demote-before-delete order (doc 08 §2.3).

``fk_memories_superseded_by`` is ON DELETE SET NULL, so deleting a superseding
memory nulls every dependent's ``superseded_by`` while their status stays
``superseded`` — which violates ``chk_superseded_has_pointer``. Postgres raises
on the DELETE statement itself, so one such dependent does not merely skip one
row: it aborts the whole batch and no TTL'd memory is ever reclaimed.

The order is therefore load-bearing, and the proof here is by **reordering**,
not by reading: ``test_reordering_demote_and_delete_breaks_the_constraint``
runs the two statements the other way round against the same fixture and
asserts the constraint fires. If a future edit made the order irrelevant, that
test would go green and say so.

These tests drive the real runner against a committing factory rather than the
conftest ``session`` fixture, because the runner opens and commits its own
session; rows are torn down by hand.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.memory import Memory
from app.services import memory as memory_service
from app.services import supersession as supersession_module
from app.services.job_runners import make_expired_memory_cleanup_runner
from app.services.supersession import demote_dependents
from tests.conftest import test_engine


def _factory() -> async_sessionmaker:
    return async_sessionmaker(test_engine, expire_on_commit=False)


async def _seed_superseder_with_dependent(
    factory, *, expired: bool = True
) -> tuple[uuid.UUID, uuid.UUID]:
    """One memory past its TTL, and one memory it superseded."""
    async with factory() as s:
        superseder = Memory(
            id=uuid.uuid4(),
            content="the replacement",
            source="test",
            expires_at=(
                datetime.now(timezone.utc) - timedelta(hours=1)
                if expired
                else datetime.now(timezone.utc) + timedelta(days=7)
            ),
        )
        s.add(superseder)
        await s.flush()
        dependent = Memory(
            id=uuid.uuid4(),
            content="the retired claim",
            source="test",
            status="superseded",
            superseded_by=superseder.id,
        )
        s.add(dependent)
        await s.commit()
        return superseder.id, dependent.id


async def _teardown(factory, ids) -> None:
    async with factory() as s:
        await s.execute(
            text(
                "UPDATE memories SET status='deprecated', superseded_by=NULL "
                "WHERE superseded_by = ANY(CAST(:ids AS uuid[]))"
            ),
            {"ids": [str(i) for i in ids]},
        )
        await s.execute(
            text("DELETE FROM memories WHERE id = ANY(CAST(:ids AS uuid[]))"),
            {"ids": [str(i) for i in ids]},
        )
        await s.commit()


async def _row(factory, memory_id: uuid.UUID):
    async with factory() as s:
        return (
            await s.execute(
                text(
                    "SELECT status, superseded_by FROM memories "
                    "WHERE id = CAST(:id AS uuid)"
                ),
                {"id": str(memory_id)},
            )
        ).one_or_none()


@pytest.mark.asyncio
async def test_sweep_demotes_dependents_and_reclaims_the_expired_row(setup_database):
    factory = _factory()
    superseder_id, dependent_id = await _seed_superseder_with_dependent(factory)
    try:
        await make_expired_memory_cleanup_runner(factory)()

        assert await _row(factory, superseder_id) is None
        assert await _row(factory, dependent_id) == ("deprecated", None)
    finally:
        await _teardown(factory, [superseder_id, dependent_id])


@pytest.mark.asyncio
async def test_reordering_demote_and_delete_breaks_the_constraint(setup_database):
    """Delete first, demote second — the order the sweep must never use.

    This is the whole reason ``demote_dependents`` runs ahead of the DELETE.
    The failure is not a skipped row: the statement itself raises, so the
    batch aborts and nothing past ``expires_at`` is ever reclaimed.
    """
    factory = _factory()
    superseder_id, dependent_id = await _seed_superseder_with_dependent(factory)
    try:
        with pytest.raises(IntegrityError) as excinfo:
            async with factory() as s:
                await s.execute(
                    text("DELETE FROM memories WHERE id = ANY(CAST(:ids AS uuid[]))"),
                    {"ids": [str(superseder_id)]},
                )
                await demote_dependents(s, [superseder_id])
                await s.commit()

        assert "chk_superseded_has_pointer" in str(excinfo.value)
        assert await _row(factory, superseder_id) is not None
        assert await _row(factory, dependent_id) == ("superseded", superseder_id)
    finally:
        await _teardown(factory, [superseder_id, dependent_id])


@pytest.mark.asyncio
async def test_sweep_only_touches_rows_past_their_expiry(setup_database):
    factory = _factory()
    keep_ids = []
    async with factory() as s:
        no_ttl = Memory(id=uuid.uuid4(), content="no ttl", source="test")
        future = Memory(
            id=uuid.uuid4(),
            content="future ttl",
            source="test",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        s.add_all([no_ttl, future])
        await s.commit()
        keep_ids = [no_ttl.id, future.id]

    expired_id, dependent_id = await _seed_superseder_with_dependent(factory)
    try:
        await make_expired_memory_cleanup_runner(factory)()

        assert await _row(factory, expired_id) is None
        for kept in keep_ids:
            assert await _row(factory, kept) == ("active", None)
    finally:
        await _teardown(factory, [expired_id, dependent_id, *keep_ids])


@pytest.mark.asyncio
async def test_sweep_is_a_noop_when_nothing_has_expired(setup_database):
    factory = _factory()
    superseder_id, dependent_id = await _seed_superseder_with_dependent(
        factory, expired=False
    )
    try:
        await make_expired_memory_cleanup_runner(factory)()

        assert await _row(factory, superseder_id) is not None
        assert await _row(factory, dependent_id) == ("superseded", superseder_id)
    finally:
        await _teardown(factory, [superseder_id, dependent_id])


# ── one demotion, two delete paths ────────────────────────────────────


def test_interactive_path_binds_the_shared_demotion():
    """Not a copy each — the same function object.

    Two hand-written copies of the same UPDATE drift, and the drift is
    invisible until a dependent survives one path and aborts the other.
    """
    assert memory_service.demote_dependents is demote_dependents


@pytest.mark.asyncio
async def test_sweep_delegates_to_the_shared_demotion(setup_database, monkeypatch):
    """The sweep resolves its demotion from ``supersession``, not a local copy."""
    calls: list[list[str]] = []

    async def _spy(session, memory_ids):
        calls.append([str(m) for m in memory_ids])
        return await demote_dependents(session, memory_ids)

    monkeypatch.setattr(supersession_module, "demote_dependents", _spy)

    factory = _factory()
    superseder_id, dependent_id = await _seed_superseder_with_dependent(factory)
    try:
        await make_expired_memory_cleanup_runner(factory)()

        assert calls, "the sweep never reached the shared demotion"
        assert str(superseder_id) in calls[0]
        assert await _row(factory, dependent_id) == ("deprecated", None)
    finally:
        await _teardown(factory, [superseder_id, dependent_id])


@pytest.mark.asyncio
async def test_interactive_delete_runs_the_identical_demotion(setup_database):
    """The interactive path leaves dependents in exactly the sweep's state."""
    from app.services.memory import MemoryService

    factory = _factory()
    superseder_id, dependent_id = await _seed_superseder_with_dependent(factory)
    try:
        async with factory() as s:
            service = MemoryService(s)
            assert await service.delete_memory(superseder_id, None, broadcast=False)
            await s.commit()

        assert await _row(factory, superseder_id) is None
        assert await _row(factory, dependent_id) == ("deprecated", None)
    finally:
        await _teardown(factory, [superseder_id, dependent_id])


@pytest.mark.asyncio
async def test_demote_dependents_is_a_noop_on_an_empty_id_list(setup_database):
    factory = _factory()
    superseder_id, dependent_id = await _seed_superseder_with_dependent(factory)
    try:
        async with factory() as s:
            await demote_dependents(s, [])
            await s.commit()

        assert await _row(factory, dependent_id) == ("superseded", superseder_id)
    finally:
        await _teardown(factory, [superseder_id, dependent_id])
