"""Tests for the JobRegistry + /api/v1/jobs API."""
from __future__ import annotations

import asyncio

import pytest

from app.main import app


@pytest.fixture
async def stubbed_jobs(client):
    """Replace the test-stub registry with a 2-job registry whose
    runners record their calls so we can assert trigger semantics
    without touching real Postgres / git / LLM."""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from app.services.job_registry import Job, JobRegistry
    from app.config import settings
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    registry = JobRegistry(factory)

    calls: dict[str, int] = {"alpha": 0, "beta": 0}

    async def alpha_runner():
        calls["alpha"] += 1

    async def beta_runner():
        calls["beta"] += 1
        raise RuntimeError("beta-runner explicit failure")

    registry.register(Job(
        key="alpha",
        display_name="Alpha",
        description="Increments a counter.",
        default_cron="*/10 * * * *",
        min_interval_seconds=10,
        runner=alpha_runner,
    ))
    registry.register(Job(
        key="beta",
        display_name="Beta",
        description="Always raises.",
        default_cron="*/10 * * * *",
        min_interval_seconds=10,
        runner=beta_runner,
    ))

    from app.services.job_registry import FieldDescriptor

    async def gamma_runner():
        calls.setdefault("gamma", 0)
        calls["gamma"] += 1

    registry.register(Job(
        key="gamma",
        display_name="Gamma",
        description="Has config.",
        default_cron="*/10 * * * *",
        min_interval_seconds=10,
        runner=gamma_runner,
        config_schema=[FieldDescriptor(key="batch_size", label="Batch Size",
                                       default=5, min=1, max=100)],
    ))

    prev_registry = app.state.job_registry
    app.state.job_registry = registry
    try:
        yield {"registry": registry, "calls": calls}
    finally:
        await registry.stop_all()
        app.state.job_registry = prev_registry
        await engine.dispose()


@pytest.mark.asyncio
async def test_list_jobs_returns_registered(stubbed_jobs, client, auth_headers):
    response = await client.get("/api/v1/jobs", headers=auth_headers)
    assert response.status_code == 200
    keys = {j["key"] for j in response.json()["jobs"]}
    assert {"alpha", "beta"} <= keys


@pytest.mark.asyncio
async def test_list_jobs_requires_auth(stubbed_jobs, client):
    response = await client.get("/api/v1/jobs")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_job_changes_cron(stubbed_jobs, client, auth_headers):
    response = await client.put(
        "/api/v1/jobs/alpha",
        json={"cron": "*/2 * * * *"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["cron"] == "*/2 * * * *"
    assert body["key"] == "alpha"


@pytest.mark.asyncio
async def test_update_job_rejects_invalid_cron(stubbed_jobs, client, auth_headers):
    response = await client.put(
        "/api/v1/jobs/alpha",
        json={"cron": "not a cron"},
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_job_accepts_six_field_cron(stubbed_jobs, client, auth_headers):
    response = await client.put(
        "/api/v1/jobs/alpha",
        json={"cron": "*/30 * * * * *"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["cron"] == "*/30 * * * * *"


@pytest.mark.asyncio
async def test_update_unknown_job_returns_404(stubbed_jobs, client, auth_headers):
    response = await client.put(
        "/api/v1/jobs/does_not_exist",
        json={"enabled": False},
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_trigger_runs_runner_immediately(stubbed_jobs, client, auth_headers):
    response = await client.post(
        "/api/v1/jobs/alpha/trigger", headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["last_status"] == "ok"
    assert stubbed_jobs["calls"]["alpha"] == 1


@pytest.mark.asyncio
async def test_trigger_records_runner_failure(stubbed_jobs, client, auth_headers):
    response = await client.post(
        "/api/v1/jobs/beta/trigger", headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["last_status"] == "error"
    assert "beta-runner" in (body["last_error"] or "")
    assert stubbed_jobs["calls"]["beta"] == 1


@pytest.mark.asyncio
async def test_list_jobs_includes_config_schema(stubbed_jobs, client, auth_headers):
    response = await client.get("/api/v1/jobs", headers=auth_headers)
    gamma = next(j for j in response.json()["jobs"] if j["key"] == "gamma")
    assert gamma["config"] == {"batch_size": 5}
    assert gamma["config_schema"][0]["key"] == "batch_size"


@pytest.mark.asyncio
async def test_update_job_config_saves_value(stubbed_jobs, client, auth_headers):
    r = await client.put("/api/v1/jobs/gamma/config",
                         json={"config": {"batch_size": 25}}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["config"]["batch_size"] == 25


@pytest.mark.asyncio
async def test_update_job_config_rejects_unknown_key(stubbed_jobs, client, auth_headers):
    r = await client.put("/api/v1/jobs/gamma/config",
                         json={"config": {"nope": 1}}, headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_job_config_rejects_out_of_range(stubbed_jobs, client, auth_headers):
    r = await client.put("/api/v1/jobs/gamma/config",
                         json={"config": {"batch_size": 999}}, headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_job_config_unknown_job_404(stubbed_jobs, client, auth_headers):
    r = await client.put("/api/v1/jobs/missing/config",
                         json={"config": {"batch_size": 5}}, headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_disabling_job_stops_loop(stubbed_jobs, client, auth_headers):
    registry = stubbed_jobs["registry"]
    # Start the loop manually so we can assert disable cancels it.
    await registry.update_config("alpha", enabled=True, cron="*/5 * * * *")
    job = registry.get("alpha")
    # update_config restarted the loop; give the event loop a tick.
    await asyncio.sleep(0)
    response = await client.put(
        "/api/v1/jobs/alpha",
        json={"enabled": False},
        headers=auth_headers,
    )
    assert response.status_code == 200
    await asyncio.sleep(0)
    assert job.task is None or job.task.done()
