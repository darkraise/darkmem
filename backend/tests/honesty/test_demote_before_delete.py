"""honesty/demote-before-delete — reordering the sweep's demote/delete breaks it.

The spec is stated as a comparison rather than an assertion about the code: the
same fixture is swept twice, once in each order. The real order reclaims the
expired row; the reversed order raises ``chk_superseded_has_pointer`` and
reclaims nothing. That is what makes the ordering a rule instead of a habit — if
an edit ever made the two orders equivalent, the reversed run would stop raising
and this spec would say so.

The failure this prevents is not one skipped row. Postgres raises on the DELETE
statement itself, so a single dependent aborts the entire batch and every TTL'd
memory in the corpus stays forever.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.memory import Memory
from app.services.job_runners import make_expired_memory_cleanup_runner
from app.services.supersession import demote_dependents
from tests.conftest import test_engine

CONSTRAINT = "chk_superseded_has_pointer"

DELETE_EXPIRED = (
    "DELETE FROM memories WHERE id = ANY(CAST(:ids AS uuid[])) RETURNING id"
)


def _factory() -> async_sessionmaker:
    return async_sessionmaker(test_engine, expire_on_commit=False)


async def _seed(factory) -> tuple[uuid.UUID, uuid.UUID]:
    async with factory() as s:
        superseder = Memory(
            id=uuid.uuid4(),
            content="expiring superseder",
            source="test",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        s.add(superseder)
        await s.flush()
        dependent = Memory(
            id=uuid.uuid4(),
            content="retired by the expiring row",
            source="test",
            status="superseded",
            superseded_by=superseder.id,
        )
        s.add(dependent)
        await s.commit()
        return superseder.id, dependent.id


async def _reversed_sweep(factory) -> None:
    """The forbidden order: delete the expired rows, then demote dependents."""
    async with factory() as s:
        expired = (
            await s.execute(
                text(
                    "SELECT id FROM memories "
                    "WHERE expires_at IS NOT NULL AND expires_at < NOW()"
                )
            )
        ).scalars().all()
        if not expired:
            return
        ids = [str(i) for i in expired]
        await s.execute(text(DELETE_EXPIRED), {"ids": ids})
        await demote_dependents(s, ids)
        await s.commit()


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


async def _exists(factory, memory_id: uuid.UUID) -> bool:
    async with factory() as s:
        return (
            await s.execute(
                text("SELECT 1 FROM memories WHERE id = CAST(:id AS uuid)"),
                {"id": str(memory_id)},
            )
        ).scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_the_reversed_order_cannot_reclaim_anything(setup_database):
    factory = _factory()
    superseder_id, dependent_id = await _seed(factory)
    try:
        with pytest.raises(IntegrityError) as excinfo:
            await _reversed_sweep(factory)

        assert CONSTRAINT in str(excinfo.value)
        assert await _exists(factory, superseder_id), "the batch aborted whole"
    finally:
        await _teardown(factory, [superseder_id, dependent_id])


@pytest.mark.asyncio
async def test_the_shipped_order_reclaims_and_keeps_the_dependent_honest(
    setup_database,
):
    factory = _factory()
    superseder_id, dependent_id = await _seed(factory)
    try:
        await make_expired_memory_cleanup_runner(factory)()

        assert not await _exists(factory, superseder_id)
        async with factory() as s:
            row = (
                await s.execute(
                    text(
                        "SELECT status, superseded_by FROM memories "
                        "WHERE id = CAST(:id AS uuid)"
                    ),
                    {"id": str(dependent_id)},
                )
            ).one()
        assert row == ("deprecated", None)
    finally:
        await _teardown(factory, [superseder_id, dependent_id])
