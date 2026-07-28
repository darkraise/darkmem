"""MemoryService.search_memories: over-fetch past filtered rows, honour offset.

The semantic path fetches a fixed slice from semantic_search, then filters
type/source/technologies/tags in memory. Fetching exactly ``limit`` and
returning ``[:limit]`` under-returns whenever a filter drops rows, and ignores
``offset`` entirely (so the MCP offset parameter is a silent no-op).

Project, status and archived are no longer among those filters — every channel
scopes them in its own SQL (``test_pushdown_keyword_graph.py``), so a fixture
that relied on them being dropped here would be testing nothing.
"""
from __future__ import annotations

import uuid

from app.models.memory import Memory
from app.schemas.memory import MemorySearchRequest
from app.services.memory import MemoryService


def _mem(**ov) -> Memory:
    base = dict(
        id=uuid.uuid4(), content="c", source="test", importance=0.5,
        metadata_={}, status="active", is_archived=False,
    )
    base.update(ov)
    return Memory(**base)


class _FakePipeline:
    """Stand-in pipeline whose semantic_search honours its ``limit`` argument."""

    def __init__(self, ranked_ids):
        self.ranked_ids = ranked_ids
        self.last_limit = None
        self.last_filters = None

    async def semantic_search(self, query, limit=20, semantic_weight=0.7, filters=None):
        self.last_limit = limit
        self.last_filters = filters
        return [{"memory_id": str(m), "score": 1.0} for m in self.ranked_ids[:limit]]


async def test_search_memories_overfetches_past_filtered_rows(session):
    # The two top-ranked rows are the wrong memory_type (filtered out). With a
    # fixed fetch of limit=2 they would be the only rows fetched, yielding zero
    # results.
    a = _mem(memory_type="note")
    b = _mem(memory_type="note")
    c = _mem(content="hit-c", memory_type="fact")
    d = _mem(content="hit-d", memory_type="fact")
    session.add_all([a, b, c, d])
    await session.flush()

    svc = MemoryService(session, pipeline=_FakePipeline([a.id, b.id, c.id, d.id]))
    rows = await svc.search_memories(
        MemorySearchRequest(query="q", limit=2, offset=0, memory_type="fact"),
    )

    assert {r.content for r in rows} == {"hit-c", "hit-d"}


async def test_search_memories_honours_offset(session):
    mems = [_mem(content=f"m{i}") for i in range(5)]
    session.add_all(mems)
    await session.flush()

    svc = MemoryService(session, pipeline=_FakePipeline([m.id for m in mems]))
    rows = await svc.search_memories(MemorySearchRequest(query="q", limit=2, offset=2))

    assert [r.content for r in rows] == ["m2", "m3"]
