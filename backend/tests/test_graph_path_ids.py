"""Path ids on the graph routes: typed, case-insensitive and sliced stably."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.models.memory import Memory

pytestmark = pytest.mark.asyncio


async def _memory(session, content: str, memory_id: uuid.UUID | None = None) -> Memory:
    row = Memory(
        id=memory_id or uuid.uuid4(), content=content, source="test",
        importance=0.5, metadata_={}, project="alpha",
    )
    session.add(row)
    await session.flush()
    return row


async def _hub(session, memory_ids: list[uuid.UUID]) -> None:
    await session.execute(
        text(
            "INSERT INTO entities (id, name, entity_type, memory_ids) "
            "VALUES (gen_random_uuid(), :name, 'tool', CAST(:mids AS uuid[]))"
        ),
        {"name": f"hub-{uuid.uuid4().hex[:8]}", "mids": [str(m) for m in memory_ids]},
    )
    await session.flush()


@pytest.mark.parametrize("path", [
    "/api/v1/graph/memory-context/not-a-uuid",
    "/api/v1/graph/entities/not-a-uuid/neighbors",
])
async def test_malformed_path_id_answers_422(client, auth_headers, path):
    response = await client.get(path, headers=auth_headers)

    assert response.status_code == 422, response.text


async def test_uppercase_seed_is_not_its_own_neighbour(client, session, auth_headers):
    seed = await _memory(session, "seed capture")
    peer = await _memory(session, "peer capture")
    await _hub(session, [seed.id, peer.id])

    response = await client.get(
        f"/api/v1/graph/memory-context/{str(seed.id).upper()}", headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    assert [n["id"] for n in response.json()["neighbors"]] == [str(peer.id)]


async def test_neighbours_are_a_stable_slice(client, session, auth_headers):
    seed = await _memory(session, "seed capture")
    peers = [await _memory(session, f"peer {i}") for i in range(30)]
    await _hub(session, [seed.id, *(p.id for p in peers)])

    answers = []
    for _ in range(2):
        response = await client.get(
            f"/api/v1/graph/memory-context/{seed.id}", headers=auth_headers,
        )
        assert response.status_code == 200, response.text
        answers.append([n["id"] for n in response.json()["neighbors"]])

    assert answers[0] == answers[1] == sorted(str(p.id) for p in peers)[:20]
