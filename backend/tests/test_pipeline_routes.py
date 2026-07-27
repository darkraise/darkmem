import pytest
from app.services.config import PURPOSES


@pytest.mark.asyncio
async def test_get_pipeline_requires_auth(client):
    resp = await client.get("/api/v1/pipeline")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_pipeline_returns_aggregator(client, auth_headers):
    resp = await client.get("/api/v1/pipeline", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert set(body["llm"].keys()) == set(PURPOSES)
    assert "relation_rescue" in body
    assert "prompts" in body


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
