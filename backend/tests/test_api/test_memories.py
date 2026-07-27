import pytest


pytestmark = pytest.mark.asyncio


async def test_create_memory(client, auth_headers):
    response = await client.post(
        "/api/v1/memories?wait_process=true",
        json={"content": "Test memory", "tags": ["project/test"], "source": "test"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "Test memory"
    assert data["tags"] == ["project/test"]
    assert data["source"] == "test"
    assert "id" in data


async def test_create_memory_unauthorized(client):
    response = await client.post("/api/v1/memories", json={"content": "No auth"})
    assert response.status_code in (401, 403)


async def test_get_memory(client, auth_headers):
    create = await client.post(
        "/api/v1/memories?wait_process=true", json={"content": "Get this"}, headers=auth_headers,
    )
    memory_id = create.json()["id"]

    response = await client.get(f"/api/v1/memories/{memory_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["content"] == "Get this"


async def test_get_memory_not_found(client, auth_headers):
    response = await client.get("/api/v1/memories/00000000-0000-0000-0000-000000000000", headers=auth_headers)
    assert response.status_code == 404


async def test_update_memory(client, auth_headers):
    create = await client.post(
        "/api/v1/memories?wait_process=true", json={"content": "Original"}, headers=auth_headers,
    )
    memory_id = create.json()["id"]

    response = await client.put(f"/api/v1/memories/{memory_id}", json={"content": "Updated"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["content"] == "Updated"


async def test_delete_memory(client, auth_headers):
    create = await client.post(
        "/api/v1/memories?wait_process=true", json={"content": "Delete me"}, headers=auth_headers,
    )
    memory_id = create.json()["id"]

    response = await client.delete(f"/api/v1/memories/{memory_id}", headers=auth_headers)
    assert response.status_code == 204

    response = await client.get(f"/api/v1/memories/{memory_id}", headers=auth_headers)
    assert response.status_code == 404


async def test_bulk_delete_memories(client, auth_headers):
    ids = []
    for i in range(3):
        r = await client.post(
            "/api/v1/memories?wait_process=true", json={"content": f"bulk {i}"}, headers=auth_headers,
        )
        ids.append(r.json()["id"])
    missing = "00000000-0000-0000-0000-000000000000"

    response = await client.post(
        "/api/v1/memories/delete",
        json={"ids": ids + [missing]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["deleted"] == 3
    assert body["not_found"] == [missing]

    for mid in ids:
        gone = await client.get(f"/api/v1/memories/{mid}", headers=auth_headers)
        assert gone.status_code == 404


async def test_bulk_delete_requires_ids(client, auth_headers):
    response = await client.post("/api/v1/memories/delete", json={"ids": []}, headers=auth_headers)
    assert response.status_code == 422


async def test_search_memories(client, auth_headers):
    await client.post(
        "/api/v1/memories?wait_process=true", json={"content": "Alpha", "tags": ["scope/a"]}, headers=auth_headers,
    )
    await client.post(
        "/api/v1/memories?wait_process=true", json={"content": "Beta", "tags": ["scope/b"]}, headers=auth_headers,
    )

    response = await client.post("/api/v1/memories/search", json={"tags_any": ["scope/a"]}, headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["content"] == "Alpha"


async def test_search_by_text(client, auth_headers):
    await client.post(
        "/api/v1/memories?wait_process=true", json={"content": "PostgreSQL rocks"}, headers=auth_headers,
    )
    await client.post(
        "/api/v1/memories?wait_process=true", json={"content": "Redis is fast"}, headers=auth_headers,
    )

    response = await client.post("/api/v1/memories/search", json={"query": "PostgreSQL"}, headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_batch_create(client, auth_headers):
    response = await client.post(
        "/api/v1/memories/batch?wait_process=true",
        json={"entries": [{"content": "Batch 1"}, {"content": "Batch 2"}, {"content": "Batch 3"}]},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert len(response.json()) == 3


async def test_create_memory_defaults_to_the_buffered_ack(client, auth_headers):
    """Done-when 4: the bypass is opt-in, not the default, on the front door
    itself — a plain POST with no `wait_process` gets the 202 accept, never
    the full body `wait_process=true` returns."""
    response = await client.post(
        "/api/v1/memories", json={"content": "buffered by default"}, headers=auth_headers,
    )
    assert response.status_code == 202
    assert response.json()["status"] == "accepted"


async def test_batch_create_defaults_to_the_buffered_ack(client, auth_headers):
    response = await client.post(
        "/api/v1/memories/batch",
        json={"entries": [{"content": "batch default 1"}, {"content": "batch default 2"}]},
        headers=auth_headers,
    )
    assert response.status_code == 202
    body = response.json()
    assert len(body) == 2
    assert all(entry["status"] == "accepted" for entry in body)
