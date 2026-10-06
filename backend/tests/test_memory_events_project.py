"""A memory's journal rows carry its project.

The dashboard calendar and Activity read the journal by project, and the
capture, update and delete rows were written with project NULL, so a scoped
calendar read "No memory activity recorded yet" over a project with captures
that day. The pipeline's own `extracted` rows already carried it.
"""
from __future__ import annotations

import uuid

from sqlalchemy import text

from app.models.memory import Memory
from app.schemas.memory import MemoryCreate, MemoryUpdate
from app.services.memory import MemoryService


async def _projects(session, object_id):
    rows = await session.execute(text(
        "SELECT event_type, project FROM events WHERE object_id = :id ORDER BY created_at, id"
    ), {"id": object_id})
    return [tuple(r) for r in rows.all()]


async def test_a_capture_journals_its_project(session):
    result = await MemoryService(session).create_memory(
        MemoryCreate(content="Postgres listens on all addresses.", source="test", project="webapp"),
        api_key_id=None,
    )
    assert ("created", "webapp") in await _projects(session, result.ack.id)


async def test_an_unscoped_capture_journals_the_default_project(session):
    result = await MemoryService(session).create_memory(
        MemoryCreate(content="Postgres listens on all addresses.", source="test"),
        api_key_id=None,
    )
    assert ("created", "default") in await _projects(session, result.ack.id)


async def test_update_and_delete_journal_the_memorys_project(session):
    memory = Memory(
        id=uuid.uuid4(), content="before", source="test", project="research",
        importance=0.5, metadata_={},
    )
    session.add(memory)
    await session.commit()
    service = MemoryService(session)

    await service.update_memory(memory.id, MemoryUpdate(importance=0.9), None, actor="admin")
    await service.delete_memory(memory.id, None, broadcast=False, actor="admin")

    assert await _projects(session, memory.id) == [("update", "research"), ("delete", "research")]
