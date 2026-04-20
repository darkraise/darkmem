import pytest


@pytest.mark.asyncio
async def test_get_pipeline_requires_auth(client):
    resp = await client.get("/api/v1/pipeline")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_pipeline_returns_aggregator(client, auth_headers):
    resp = await client.get("/api/v1/pipeline", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] in ("ml", "llm", "mixed")
    assert set(body["llm"].keys()) == {
        "embedding", "extraction", "classification",
        "reasoning", "summarization", "reranker",
    }
