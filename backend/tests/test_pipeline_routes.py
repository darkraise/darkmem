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


@pytest.mark.asyncio
async def test_set_mode_ml_flips_all_three_flags(client, auth_headers, session):
    from app.models.config import Config
    from sqlalchemy import select

    resp = await client.post("/api/v1/pipeline/mode", json={"mode": "ml"}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "ml"
    assert body["stages"] == {
        "extraction": "ml", "classification": "ml", "retrieval": "ml",
    }

    row = (await session.execute(
        select(Config).where(Config.key == "feature_flags")
    )).scalar_one()
    assert row.value["ml_extraction"] is True
    assert row.value["ml_classification"] is True
    assert row.value["ml_retrieval"] is True


@pytest.mark.asyncio
async def test_set_mode_llm_flips_all_three_flags(client, auth_headers):
    resp = await client.post("/api/v1/pipeline/mode", json={"mode": "llm"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["mode"] == "llm"


@pytest.mark.asyncio
async def test_set_mode_rejects_invalid_value(client, auth_headers):
    resp = await client.post("/api/v1/pipeline/mode", json={"mode": "auto"}, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_set_mode_preserves_unrelated_flags(client, auth_headers, session):
    from app.models.config import Config
    from sqlalchemy import select

    session.add(Config(key="feature_flags", value={
        "hybrid_search_enabled": True,
        "ml_extraction": False,
        "ml_classification": False,
        "ml_retrieval": False,
    }))
    await session.flush()

    resp = await client.post("/api/v1/pipeline/mode", json={"mode": "ml"}, headers=auth_headers)
    assert resp.status_code == 200

    row = (await session.execute(
        select(Config).where(Config.key == "feature_flags")
    )).scalar_one()
    assert row.value["hybrid_search_enabled"] is True
