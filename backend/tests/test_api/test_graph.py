import pytest

pytestmark = pytest.mark.asyncio


async def test_graph_entities_returns_200(client, auth_headers):
    response = await client.get("/api/v1/graph/entities", headers=auth_headers)
    assert response.status_code == 200
