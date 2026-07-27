import pytest

pytestmark = pytest.mark.asyncio


async def test_get_stats(client, auth_headers):
    response = await client.get("/api/v1/analytics/stats", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "memories" in data
    assert "tags" in data
    assert isinstance(data["sources"], list)


async def test_get_stats_after_creating_memories(client, auth_headers):
    await client.post(
        "/api/v1/memories?wait_process=true", json={"content": "Test", "source": "pytest"}, headers=auth_headers,
    )
    response = await client.get("/api/v1/analytics/stats", headers=auth_headers)
    data = response.json()
    assert data["memories"] >= 1
    assert "pytest" in data["sources"]
