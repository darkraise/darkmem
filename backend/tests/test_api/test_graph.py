import pytest

pytestmark = pytest.mark.asyncio


async def test_graph_entities_503_when_unavailable(client, auth_headers):
    response = await client.get("/api/v1/graph/entities", headers=auth_headers)
    # Graph repo is None in test env (no Neo4j), so 503
    assert response.status_code == 503
