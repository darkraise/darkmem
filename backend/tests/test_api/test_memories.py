import pytest


pytestmark = pytest.mark.asyncio


async def test_create_memory(client, auth_headers):
    response = await client.post(
        "/api/v1/memories",
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
    create = await client.post("/api/v1/memories", json={"content": "Get this"}, headers=auth_headers)
    memory_id = create.json()["id"]

    response = await client.get(f"/api/v1/memories/{memory_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["content"] == "Get this"


async def test_get_memory_not_found(client, auth_headers):
    response = await client.get("/api/v1/memories/00000000-0000-0000-0000-000000000000", headers=auth_headers)
    assert response.status_code == 404


async def test_update_memory(client, auth_headers):
    create = await client.post("/api/v1/memories", json={"content": "Original"}, headers=auth_headers)
    memory_id = create.json()["id"]

    response = await client.put(f"/api/v1/memories/{memory_id}", json={"content": "Updated"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["content"] == "Updated"


async def test_delete_memory(client, auth_headers):
    create = await client.post("/api/v1/memories", json={"content": "Delete me"}, headers=auth_headers)
    memory_id = create.json()["id"]

    response = await client.delete(f"/api/v1/memories/{memory_id}", headers=auth_headers)
    assert response.status_code == 204

    response = await client.get(f"/api/v1/memories/{memory_id}", headers=auth_headers)
    assert response.status_code == 404


async def test_search_memories(client, auth_headers):
    await client.post("/api/v1/memories", json={"content": "Alpha", "tags": ["scope/a"]}, headers=auth_headers)
    await client.post("/api/v1/memories", json={"content": "Beta", "tags": ["scope/b"]}, headers=auth_headers)

    response = await client.post("/api/v1/memories/search", json={"tags_any": ["scope/a"]}, headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["content"] == "Alpha"


async def test_search_by_text(client, auth_headers):
    await client.post("/api/v1/memories", json={"content": "PostgreSQL rocks"}, headers=auth_headers)
    await client.post("/api/v1/memories", json={"content": "Redis is fast"}, headers=auth_headers)

    response = await client.post("/api/v1/memories/search", json={"query": "PostgreSQL"}, headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_batch_create(client, auth_headers):
    response = await client.post(
        "/api/v1/memories/batch",
        json={"entries": [{"content": "Batch 1"}, {"content": "Batch 2"}, {"content": "Batch 3"}]},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert len(response.json()) == 3


async def test_scope_enforcement(client, session):
    from app.api.auth import generate_api_key
    from app.models.api_key import ApiKey

    raw_key, key_hash = generate_api_key()
    key = ApiKey(name="read-only", key_hash=key_hash, scopes=["read"])
    session.add(key)
    await session.flush()

    headers = {"Authorization": f"Bearer {raw_key}"}

    get_resp = await client.post("/api/v1/memories/search", json={}, headers=headers)
    assert get_resp.status_code == 200

    post_resp = await client.post("/api/v1/memories", json={"content": "Nope"}, headers=headers)
    assert post_resp.status_code == 403
