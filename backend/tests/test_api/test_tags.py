import pytest


pytestmark = pytest.mark.asyncio


async def test_list_tags_empty(client, auth_headers):
    response = await client.get("/api/v1/tags", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


async def test_list_tags_with_counts(client, auth_headers):
    await client.post("/api/v1/memories", json={"content": "A", "tags": ["project/test"]}, headers=auth_headers)
    await client.post("/api/v1/memories", json={"content": "B", "tags": ["project/test", "infra/db"]}, headers=auth_headers)

    response = await client.get("/api/v1/tags", headers=auth_headers)
    assert response.status_code == 200
    tags = response.json()
    assert len(tags) == 2

    test_tag = next(t for t in tags if t["name"] == "project/test")
    assert test_tag["memory_count"] == 2
    assert test_tag["category"] == "project"
