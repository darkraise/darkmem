"""Multi-value source / memory_type filtering (source_any / memory_type_any).

The memories browse forwarded only a single source/type and narrowed multiple
selections client-side over the current page, so the displayed page and the
total count disagreed. Supporting array filters server-side makes the count and
the page reflect the same query.
"""
from __future__ import annotations

import uuid

import pytest

from app.models.memory import Memory
from app.repositories.relational import PostgresMemoryRepository


def _mem(**ov) -> Memory:
    base = dict(
        id=uuid.uuid4(), content="c", source="test", importance=0.5,
        metadata_={}, status="active",
    )
    base.update(ov)
    return Memory(**base)


@pytest.mark.asyncio
async def test_source_any_filters_multiple_sources(session):
    session.add_all([
        _mem(content="a", source="cli"),
        _mem(content="b", source="api"),
        _mem(content="c", source="mcp"),
    ])
    await session.flush()

    repo = PostgresMemoryRepository(session)
    rows = await repo.search_by_tags(source_any=["cli", "api"], limit=50)
    assert {r.source for r in rows} == {"cli", "api"}


@pytest.mark.asyncio
async def test_memory_type_any_filters_multiple_types(session):
    session.add_all([
        _mem(content="a", memory_type="fact"),
        _mem(content="b", memory_type="decision"),
        _mem(content="c", memory_type="preference"),
    ])
    await session.flush()

    repo = PostgresMemoryRepository(session)
    rows = await repo.search_by_tags(memory_type_any=["fact", "decision"], limit=50)
    assert {r.memory_type for r in rows} == {"fact", "decision"}
