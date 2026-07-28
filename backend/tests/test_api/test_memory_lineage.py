"""T1.47's reverse supersession lineage: `MemoryResponse.predecessors`.

Doc 07 §7 / doc 13 §4 describe the forward direction (a superseded memory's
`superseded_by` reaches its successor); this is the reverse — "what did this
memory replace." There is no dedicated query surface for it before this
change (`MemorySearchRequest` has no `superseded_by` filter), so these tests
exercise the new `PostgresMemoryRepository.get_predecessors` /
`MemoryService.get_memory` / `MemoryResponse.predecessors` path.

Every supersession pair below is produced by the real detector
(`detect_supersessions`), never hand-set on the row, so a future change to
what `detect_supersessions` writes (T1.36's shape) breaks these tests instead
of silently drifting from them.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models.memory import Memory
from app.services.supersession import detect_supersessions

pytestmark = pytest.mark.asyncio

NOW = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)


def _mem(**overrides) -> Memory:
    base = dict(
        id=uuid.uuid4(),
        content="candidate",
        source="test",
        source_agent=None,
        memory_type=None,
        importance=0.5,
        metadata_={},
        project="lineage-test",
        status="active",
        technologies=[],
        created_at=NOW - timedelta(days=1),
    )
    base.update(overrides)
    return Memory(**base)


async def test_predecessors_reflects_a_real_supersession_pair(client, session, auth_headers):
    old = _mem(content="we run promtail for log shipping", technologies=["promtail"])
    new = _mem(
        content="we switched from promtail to alloy",
        technologies=["alloy"],
        created_at=NOW,
    )
    session.add_all([old, new])
    await session.flush()

    flipped = await detect_supersessions(
        session,
        new_memory_id=new.id,
        new_memory_text=new.content,
        new_memory_created_at=new.created_at,
        project=new.project,
        new_relations=[{"type": "REPLACES", "source": "alloy", "target": "promtail"}],
        now=NOW,
    )
    assert flipped == [old.id]
    await session.flush()

    response = await client.get(f"/api/v1/memories/{new.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert len(data["predecessors"]) == 1
    predecessor = data["predecessors"][0]
    assert predecessor["id"] == str(old.id)
    assert predecessor["content"] == "we run promtail for log shipping"
    assert predecessor["status"] == "superseded"

    # The forward direction still holds on the predecessor's own row.
    predecessor_response = await client.get(f"/api/v1/memories/{old.id}", headers=auth_headers)
    assert predecessor_response.json()["superseded_by"] == str(new.id)
    assert predecessor_response.json()["predecessors"] == []


async def test_predecessors_is_an_empty_list_never_null_when_nothing_was_replaced(
    client, session, auth_headers,
):
    lone = _mem(content="a memory nothing has ever replaced")
    session.add(lone)
    await session.flush()

    response = await client.get(f"/api/v1/memories/{lone.id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["predecessors"] == []


async def test_predecessors_is_bounded_and_newest_first(client, session, auth_headers):
    from app.repositories.relational import MEMORY_PREDECESSORS_LIMIT

    successor = _mem(content="the one everything below replaced", technologies=["alloy"])
    session.add(successor)
    await session.flush()

    overflow = MEMORY_PREDECESSORS_LIMIT + 3
    predecessors = [
        _mem(
            content=f"predecessor {i}",
            status="superseded",
            superseded_by=successor.id,
            created_at=NOW - timedelta(days=overflow - i),
        )
        for i in range(overflow)
    ]
    session.add_all(predecessors)
    await session.flush()

    response = await client.get(f"/api/v1/memories/{successor.id}", headers=auth_headers)
    body = response.json()["predecessors"]
    assert len(body) == MEMORY_PREDECESSORS_LIMIT
    returned_created_ats = [row["created_at"] for row in body]
    assert returned_created_ats == sorted(returned_created_ats, reverse=True)


async def test_predecessors_stays_null_on_search_results_not_computed_there(
    client, session, auth_headers,
):
    """`predecessors` is single-get-only (an N+1 per row on a list would be
    the wrong trade); search rows must carry the honest "not computed"
    `None`, never a fabricated `[]` that would read as "confirmed empty."
    """
    memory = _mem(content="search result lineage probe")
    session.add(memory)
    await session.flush()

    response = await client.post(
        "/api/v1/memories/search",
        json={"query": "search result lineage probe", "project": "lineage-test", "status": ["active"]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    rows = [row for row in response.json() if row["id"] == str(memory.id)]
    assert len(rows) == 1
    assert rows[0]["predecessors"] is None
