"""A content edit journals one `extracted` row: the pipeline's own.

The update door used to log a second `extracted` row after the pipeline
returned, carrying the step statuses but no `outcome`; the Activity pipeline
view read every such row as a failed run beside the completed one.
"""
from __future__ import annotations

import uuid

from sqlalchemy import text

from app.models.memory import Memory
from app.schemas.memory import MemoryUpdate
from app.services.memory import MemoryService


class _RecordingPipeline:
    """Returns a completed status and journals nothing, like a pipeline whose
    own `extracted` row is not under test here."""

    def __init__(self):
        self.calls = 0

    async def process_memory(self, **kwargs):
        self.calls += 1
        return {"embed": "ok", "extract": "ok", "vector": "ok", "graph": "ok", "error": None}


async def test_a_content_edit_adds_no_second_extracted_row(session):
    memory = Memory(
        id=uuid.uuid4(), content="before", source="test", importance=0.5, metadata_={},
    )
    session.add(memory)
    await session.commit()
    pipeline = _RecordingPipeline()

    await MemoryService(session, pipeline=pipeline).update_memory(
        memory.id, MemoryUpdate(content="after"), None, actor="admin",
    )

    assert pipeline.calls == 1
    rows = (await session.execute(text(
        "SELECT event_type FROM events WHERE object_id = :id ORDER BY id"
    ), {"id": memory.id})).scalars().all()
    assert rows == ["update"]
