"""Expired-memory sweep vs the chk_superseded_has_pointer CHECK.

Regression guard: a TTL'd *superseding* memory must be swept without aborting the
batch on the constraint. fk_memories_superseded_by is ON DELETE SET NULL, so the
runner must demote dependents (status->deprecated, superseded_by->NULL) before it
deletes the superseder, in the same transaction."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models.memory import Memory
from app.services.job_runners import make_expired_memory_cleanup_runner


@pytest.mark.asyncio
async def test_expired_cleanup_demotes_dependents_before_delete():
    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    a_id = b_id = None
    try:
        async with factory() as s:
            a = Memory(
                content="expired superseder",
                source="test",
                expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            )
            s.add(a)
            await s.flush()
            a_id = a.id
            b = Memory(
                content="superseded by A",
                source="test",
                status="superseded",
                superseded_by=a.id,
            )
            s.add(b)
            await s.flush()
            b_id = b.id
            await s.commit()

        run = make_expired_memory_cleanup_runner(factory)
        await run()  # must not raise IntegrityError on chk_superseded_has_pointer

        async with factory() as s:
            a_row = (await s.execute(select(Memory).where(Memory.id == a_id))).scalar_one_or_none()
            b_row = (await s.execute(select(Memory).where(Memory.id == b_id))).scalar_one_or_none()
        assert a_row is None, "expired superseder should be swept"
        assert b_row is not None, "dependent must survive — only demoted, not deleted"
        assert b_row.status == "deprecated"
        assert b_row.superseded_by is None
    finally:
        async with factory() as s:
            await s.execute(
                text("DELETE FROM memories WHERE id = ANY(CAST(:ids AS uuid[]))"),
                {"ids": [i for i in (a_id, b_id) if i is not None]},
            )
            await s.commit()
        await engine.dispose()
