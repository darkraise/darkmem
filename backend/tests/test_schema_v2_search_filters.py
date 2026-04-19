"""Phase 7 tests — the retrieval filters land on the repository layer."""
from __future__ import annotations

import uuid

import pytest

from app.models.memory import Memory
from app.repositories.relational import PostgresMemoryRepository


def _mem(**overrides) -> Memory:
    base = dict(
        id=uuid.uuid4(),
        content="placeholder",
        source="test",
        importance=0.5,
        metadata_={},
    )
    base.update(overrides)
    return Memory(**base)


@pytest.mark.asyncio
async def test_status_filter_hides_superseded_by_default(session):
    """Default status=['active'] must hide superseded + deprecated memories."""
    successor_id = uuid.uuid4()
    active = _mem(content="active", project="p", status="active")
    dep = _mem(content="deprecated", project="p", status="deprecated")
    suc_target = _mem(id=successor_id, content="new", project="p", status="active")
    sup = _mem(
        content="superseded",
        project="p",
        status="superseded",
        superseded_by=successor_id,
    )
    session.add_all([active, dep, suc_target, sup])
    await session.flush()

    repo = PostgresMemoryRepository(session)
    rows = await repo.search_by_tags(project="p", status=["active"], limit=50)
    statuses = {r.status for r in rows}
    contents = {r.content for r in rows}
    assert statuses == {"active"}
    assert contents == {"active", "new"}


@pytest.mark.asyncio
async def test_status_filter_includes_superseded_on_explicit_request(session):
    successor_id = uuid.uuid4()
    session.add_all([
        _mem(content="active", project="p", status="active"),
        _mem(id=successor_id, content="new", project="p", status="active"),
        _mem(
            content="superseded",
            project="p",
            status="superseded",
            superseded_by=successor_id,
        ),
    ])
    await session.flush()

    repo = PostgresMemoryRepository(session)
    rows = await repo.search_by_tags(
        project="p", status=["active", "superseded"], limit=50,
    )
    assert {r.status for r in rows} == {"active", "superseded"}


@pytest.mark.asyncio
async def test_project_filter_scopes_results(session):
    session.add_all([
        _mem(content="a-proj", project="a"),
        _mem(content="b-proj", project="b"),
    ])
    await session.flush()

    repo = PostgresMemoryRepository(session)
    rows = await repo.search_by_tags(project="a", limit=50)
    assert [r.project for r in rows] == ["a"]


@pytest.mark.asyncio
async def test_technologies_any_matches_overlap(session):
    session.add_all([
        _mem(content="uses redis", technologies=["redis", "postgres"]),
        _mem(content="uses valkey", technologies=["valkey"]),
        _mem(content="unrelated"),
    ])
    await session.flush()

    repo = PostgresMemoryRepository(session)
    rows = await repo.search_by_tags(technologies_any=["redis"], limit=50)
    assert {r.content for r in rows} == {"uses redis"}

    rows = await repo.search_by_tags(technologies_any=["redis", "valkey"], limit=50)
    assert {r.content for r in rows} == {"uses redis", "uses valkey"}


@pytest.mark.asyncio
async def test_paginated_search_respects_schema_v2_filters(session):
    session.add_all([
        _mem(content="active-a", project="p", status="active"),
        _mem(content="dep-a", project="p", status="deprecated"),
        _mem(content="active-b", project="q", status="active"),
    ])
    await session.flush()

    repo = PostgresMemoryRepository(session)
    items, total = await repo.search_by_tags_paginated(
        project="p", status=["active"], limit=50, offset=0,
    )
    assert total == 1
    assert [m.content for m in items] == ["active-a"]
