import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.api.auth import COOKIE_NAME, create_access_token, hash_password, verify_password
from app.api.routes.auth import ChangePasswordRequest
from app.api.routes.setup import SetupRequest


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint,body", [
    ("/api/v1/config/llm-providers/probe-models", {"api_kind": "openai", "base_url": "http://example.invalid"}),
    ("/api/v1/config/llm-providers/test/probe-models", {}),
    ("/api/v1/git-accounts/verify", {"provider": "github", "token": "test"}),
    ("/api/v1/setup/probe-models", {"api_kind": "openai", "base_url": "http://example.invalid"}),
    ("/api/v1/config/notifications/test", {}),
])
async def test_read_only_probe_routes_refuse_before_egress(monkeypatch, endpoint, body):
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    from app.api.auth import require_auth
    from app.api.routes import config, git_accounts, llm_providers, setup
    from app.services import notifications
    from app.config import settings

    monkeypatch.setattr(settings, "read_only", True)
    outbound = AsyncMock(side_effect=AssertionError("outbound probe"))
    monkeypatch.setattr(llm_providers, "_probe", outbound)
    monkeypatch.setattr(git_accounts, "verify_token", outbound)
    monkeypatch.setattr(notifications, "get_settings", AsyncMock(return_value={}))
    monkeypatch.setattr(notifications, "send_telegram", outbound)
    app = FastAPI()
    app.dependency_overrides[require_auth] = lambda: None
    for router in (llm_providers.router, git_accounts.router, setup.router, config.router):
        app.include_router(router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(endpoint, json=body)
    assert response.status_code == 403
    outbound.assert_not_called()


@pytest.mark.parametrize("password", ["x" * 73, "界" * 25])
def test_password_schemas_enforce_utf8_byte_limit(password):
    with pytest.raises(ValidationError, match="72"):
        SetupRequest(password=password)
    with pytest.raises(ValidationError, match="72"):
        ChangePasswordRequest(current_password="password", new_password=password)


def test_oversized_login_is_safe_and_existing_hashes_work():
    hashed = hash_password("correct-password")
    assert verify_password("correct-password", hashed)
    assert not verify_password("界" * 25, hashed)
    assert not verify_password("password", "malformed")
    assert SetupRequest(password="界" * 24).password == "界" * 24


@pytest.mark.asyncio
@pytest.mark.parametrize("dependency_name", ["get_llm", "get_chat_service", "get_graph_service", "get_code_pipeline", "get_memory_service", "get_analytics_service"])
async def test_dependency_holds_lease_before_first_dispatch_and_releases_on_cancel(monkeypatch, dependency_name):
    import httpx
    from app.api import deps
    from app.api.routes import config
    from app.services.llm import LLMOrchestrator
    from app.services.pipeline import ProcessingPipeline

    old = LLMOrchestrator({})
    await old._client.aclose()
    old._client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200)))
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(llm=old, pipeline=ProcessingPipeline(old, None))))
    factory = getattr(deps, dependency_name)
    dependency = factory(request) if dependency_name == "get_llm" else factory(request, session=None)
    service = await anext(dependency)
    if dependency_name == "get_llm":
        captured = service
    elif dependency_name in {"get_memory_service", "get_analytics_service"}:
        captured = service.pipeline.llm
    else:
        captured = service.llm
    tasks = []

    def spawn(coroutine, **kwargs):
        task = asyncio.create_task(coroutine)
        tasks.append(task)
        return task

    monkeypatch.setattr(config, "spawn", spawn)
    config._replace_orchestrator(request, SimpleNamespace())
    retired = tasks[0]
    await asyncio.sleep(0)
    assert not retired.done()
    assert not captured._client.is_closed
    assert (await captured._client.get("http://provider.invalid")).status_code == 200
    await dependency.aclose()
    await asyncio.wait_for(retired, 1)
    assert captured._client.is_closed


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel_before_start", [False, True])
async def test_detached_task_leases_from_spawn_through_completion(cancel_before_start):
    from app.services.llm import LLMOrchestrator, spawn_with_llm

    old = LLMOrchestrator({})
    entered = asyncio.Event()
    resume = asyncio.Event()

    async def work():
        entered.set()
        await resume.wait()
        assert not old._client.is_closed

    task = spawn_with_llm(old, work())
    retired = asyncio.create_task(old.close())
    if cancel_before_start:
        task.cancel()
    else:
        await entered.wait()
        assert not retired.done()
        resume.set()
    await asyncio.gather(task, return_exceptions=True)
    await asyncio.wait_for(retired, 1)
    assert old._client.is_closed


@pytest.mark.asyncio
async def test_detached_spawn_failure_releases_lease():
    from app.services.llm import LLMOrchestrator, spawn_with_llm

    old = LLMOrchestrator({})

    async def work():
        pass

    def refuse(coroutine):
        raise RuntimeError("spawn refused")

    with pytest.raises(RuntimeError, match="spawn refused"):
        spawn_with_llm(old, work(), spawn=refuse)
    await asyncio.wait_for(old.close(), 1)
    assert old._client.is_closed


@pytest.mark.asyncio
async def test_lease_cancellation_drains_without_delay():
    from app.services import llm as llm_module

    old = llm_module.LLMOrchestrator({})
    acquired = asyncio.Event()

    async def consumer():
        with llm_module.lease_llm(old):
            acquired.set()
            await asyncio.Event().wait()

    task = asyncio.create_task(consumer())
    await asyncio.wait_for(acquired.wait(), 1)
    retired = asyncio.create_task(old.close())
    await asyncio.sleep(0)
    assert not retired.done()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await asyncio.wait_for(retired, 1)
    assert old._client.is_closed


@pytest.mark.asyncio
@pytest.mark.parametrize("revoked_at_handshake", [True, False])
@pytest.mark.parametrize("revocation", ["epoch", "blocklist", "expiry"])
async def test_websocket_password_epoch_and_connected_revocation(monkeypatch, revoked_at_handshake, revocation):
    from datetime import datetime, timedelta, timezone
    import jwt
    from app.api import auth, websocket
    from app import database

    revoked = revoked_at_handshake

    @asynccontextmanager
    async def session_factory():
        yield SimpleNamespace()

    async def password_changed(*args):
        return revoked and revocation == "epoch"

    async def token_revoked(*args):
        return revoked and revocation == "blocklist"

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            current = datetime.now(timezone.utc)
            return current + timedelta(days=2) if revoked and revocation == "expiry" else current

    monkeypatch.setattr(database, "async_session_factory", session_factory)
    monkeypatch.setattr(auth, "is_token_revoked", token_revoked)
    monkeypatch.setattr(auth, "_password_changed_after", password_changed)
    monkeypatch.setattr(websocket, "AUTH_CHECK_INTERVAL_SECONDS", 0.01, raising=False)
    manager = websocket.EventManager()
    monkeypatch.setattr(websocket, "event_manager", manager)
    accepted = asyncio.Event()
    closed = asyncio.Event()

    class Socket:
        cookies = {COOKIE_NAME: create_access_token({"sub": "admin"})}

        async def accept(self):
            accepted.set()

        async def receive_text(self):
            await asyncio.Event().wait()

        async def close(self, **kwargs):
            closed.set()

    monkeypatch.setattr(jwt.api_jwt, "datetime", Clock)
    task = asyncio.create_task(websocket.websocket_endpoint(Socket()))
    try:
        if not revoked_at_handshake:
            await asyncio.wait_for(accepted.wait(), 1)
            revoked = True
        await asyncio.wait_for(closed.wait(), 0.3)
        await asyncio.wait_for(task, 0.3)
        assert not manager.connections
        assert accepted.is_set() != revoked_at_handshake
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_broadcast_revalidates_before_delivering_private_events():
    from fastapi import HTTPException
    from app.api.websocket import EventManager

    class Socket:
        accept = AsyncMock()
        close = AsyncMock()
        send_text = AsyncMock()

    socket = Socket()
    manager = EventManager()
    validator = AsyncMock(side_effect=HTTPException(401, "revoked"))
    await manager.connect(socket, validator)
    await manager.broadcast("unknown.test", {})
    socket.send_text.assert_not_called()
    socket.close.assert_awaited_once()
    assert not manager.connections


@pytest.mark.asyncio
async def test_stream_dependency_stays_leased_until_body_finishes():
    from fastapi import Depends, FastAPI
    from fastapi.responses import StreamingResponse
    from httpx import ASGITransport, AsyncClient
    from app.api.deps import get_llm
    from app.api.routes.config import _replace_orchestrator
    from app.services.llm import LLMOrchestrator

    app = FastAPI()
    old = LLMOrchestrator({})
    app.state.llm = old
    acquired = asyncio.Event()
    resume = asyncio.Event()

    @app.get("/stream")
    async def stream(llm=Depends(get_llm)):
        async def body():
            acquired.set()
            await resume.wait()
            assert not llm._client.is_closed
            yield "finished"
        return StreamingResponse(body())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response_task = asyncio.create_task(client.get("/stream"))
        await asyncio.wait_for(acquired.wait(), 1)
        _replace_orchestrator(SimpleNamespace(app=app), SimpleNamespace())
        await asyncio.sleep(0)
        assert not old._client.is_closed
        resume.set()
        response = await asyncio.wait_for(response_task, 1)
        assert response.text == "finished"
    await asyncio.wait_for(old.close(), 1)


@pytest.mark.asyncio
async def test_read_only_health_does_not_probe_provider(monkeypatch):
    import httpx
    from app import database, main
    from app.config import settings

    @asynccontextmanager
    async def session_factory():
        yield SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: 1)))

    monkeypatch.setattr(settings, "read_only", True)
    monkeypatch.setattr(database, "async_session_factory", session_factory)
    monkeypatch.setattr(main.app.state, "llm", SimpleNamespace(config={"embedding": SimpleNamespace(base_url="http://provider.invalid", api_kind="openai", api_key=None)}), raising=False)
    outbound = AsyncMock(side_effect=AssertionError("health egress"))
    monkeypatch.setattr(httpx.AsyncClient, "get", outbound)
    response = await main.health()
    assert response.status_code == 200
    outbound.assert_not_called()


@pytest.mark.asyncio
async def test_reembed_capture_await_handoff_and_cancel_before_start(monkeypatch):
    from app.api.routes import reembed
    from app.services.llm import LLMOrchestrator

    old = LLMOrchestrator({})
    monkeypatch.setattr(old, "llm_fingerprint", lambda: "test-fingerprint")
    captured = asyncio.Event()
    resume = asyncio.Event()
    tasks = []

    async def count_missing(*args):
        captured.set()
        await resume.wait()
        assert not old._client.is_closed
        return {"memories": 1}

    def spawn(coroutine, **kwargs):
        task = asyncio.create_task(coroutine)
        task.cancel()
        tasks.append(task)
        return task

    monkeypatch.setattr(reembed.ReembedService, "count_missing", count_missing)
    monkeypatch.setattr(reembed, "spawn", spawn)
    operation = asyncio.create_task(reembed._dispatch_single_category("memories", SimpleNamespace(llm=old), None))
    await asyncio.wait_for(captured.wait(), 1)
    retired = asyncio.create_task(old.close())
    await asyncio.sleep(0)
    assert not retired.done()
    resume.set()
    assert (await operation)["accepted"]
    await asyncio.gather(*tasks, return_exceptions=True)
    await asyncio.wait_for(retired, 1)
    assert not reembed.reembed_locks.is_locked("memories")
