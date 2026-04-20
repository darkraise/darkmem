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


@pytest.mark.asyncio
async def test_unload_invalid_group_returns_422(client, auth_headers):
    resp = await client.post("/api/v1/pipeline/unload?group=bogus", headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_unload_when_nothing_loaded_returns_empty(client, auth_headers, monkeypatch):
    from app.services import ml_models as mm
    monkeypatch.setattr(mm, "_INSTANCE", None)
    resp = await client.post("/api/v1/pipeline/unload", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["unloaded"] == []


@pytest.mark.asyncio
async def test_unload_group_calls_unload_function(client, auth_headers, monkeypatch):
    from app.services import ml_models as mm
    calls = []
    def fake_unload(name: str):
        calls.append(name)
    monkeypatch.setattr(mm, "unload_group", fake_unload)

    fake_instance = type("Fake", (), {
        "extraction_loaded": True,
        "classification_loaded": False,
        "retriever_loaded": False,
    })()
    monkeypatch.setattr(mm, "_INSTANCE", fake_instance)

    resp = await client.post("/api/v1/pipeline/unload?group=extraction", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "extraction" in body["unloaded"]
    assert calls == ["extraction"]


@pytest.mark.asyncio
async def test_metrics_requires_auth(client):
    resp = await client.get("/api/v1/pipeline/metrics")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_metrics_returns_expected_keys(client, auth_headers, monkeypatch):
    from app.services import system_metrics as sm
    monkeypatch.setattr(sm, "snapshot", lambda: {
        "cpu_percent": 12.0,
        "ram_used_mb": 4096,
        "ram_total_mb": 16384,
        "gpu_util_percent": 50,
        "vram_used_mb": 3072,
        "vram_total_mb": 12288,
    })
    resp = await client.get("/api/v1/pipeline/metrics", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["cpu_percent"] == 12.0
    assert body["vram_total_mb"] == 12288
    assert "groups" in body


@pytest.mark.asyncio
async def test_metrics_graceful_null_fields(client, auth_headers, monkeypatch):
    from app.services import system_metrics as sm
    monkeypatch.setattr(sm, "snapshot", lambda: {
        "cpu_percent": None, "ram_used_mb": None, "ram_total_mb": None,
        "gpu_util_percent": None, "vram_used_mb": None, "vram_total_mb": None,
    })
    resp = await client.get("/api/v1/pipeline/metrics", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["cpu_percent"] is None
