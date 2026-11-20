"""When a request's writes become durable: before its response is sent.

A request-scoped session commits after the response has gone out, so a client
that refetches on a 200 can read the old value. The session and the providers
built on it are function-scoped; only the two streaming routes keep a session
open past the handler, through request-scoped twins.
"""
from __future__ import annotations

import inspect
import uuid

import jwt
import pytest
import pytest_asyncio
from fastapi.responses import StreamingResponse
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app import database
from app.api import deps
from app.api.auth import ALGORITHM, create_access_token, hash_password, verify_password
from app.config import settings
from app.database import get_session
from app.main import app
from app.models.config import Config
from app.models.token_blocklist import TokenBlocklist
from app.services import prompt as prompt_module

pytestmark = pytest.mark.asyncio

STREAMING_ROUTES = {
    ("POST", "/api/v1/chat/completions"),
    ("POST", "/api/v1/analytics/reprocess/stream"),
}
FUNCTION_SCOPED_PROVIDERS = {
    deps.get_memory_service,
    deps.get_chat_service,
    deps.get_analytics_service,
    deps.get_llm,
    deps.get_graph_service,
    deps.get_code_pipeline,
}
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _resolved(dependant):
    for sub in dependant.dependencies:
        yield sub
        yield from _resolved(sub)


def _streams(route: APIRoute) -> bool:
    annotation = inspect.signature(route.endpoint).return_annotation
    if inspect.isclass(annotation) and issubclass(annotation, StreamingResponse):
        return True
    return "StreamingResponse(" in inspect.getsource(route.endpoint)


def _api_routes():
    return [route for route in app.routes if isinstance(route, APIRoute)]


async def test_no_streaming_handler_resolves_a_function_scoped_dependency():
    streaming = [route for route in _api_routes() if _streams(route)]
    assert {(m, r.path) for r in streaming for m in r.methods} == STREAMING_ROUTES

    for route in streaming:
        resolved = list(_resolved(route.dependant))
        function_scoped = [
            d.call.__name__ for d in resolved
            if d.scope == "function"
            and (d.call is get_session or d.call in FUNCTION_SCOPED_PROVIDERS)
        ]
        assert not function_scoped, (route.path, function_scoped)
        providers = [d.call.__name__ for d in resolved if d.call in FUNCTION_SCOPED_PROVIDERS]
        assert not providers, (route.path, providers)
        sessions = [d for d in resolved if d.call is get_session]
        assert sessions and all(d.computed_scope == "request" for d in sessions), route.path


async def test_every_write_route_takes_the_function_scoped_session():
    checked = 0
    for route in _api_routes():
        for method in route.methods & WRITE_METHODS:
            if (method, route.path) in STREAMING_ROUTES:
                continue
            resolved = list(_resolved(route.dependant))
            late = [
                d.call.__name__ for d in resolved
                if (d.call is get_session or d.call in FUNCTION_SCOPED_PROVIDERS)
                and d.scope != "function"
            ]
            assert not late, (method, route.path, late)
            if any(d.call is get_session for d in resolved):
                checked += 1
    assert checked > 100


@pytest_asyncio.fixture
async def committed(setup_database, monkeypatch):
    """The real `get_session`, on a factory whose commits land."""
    from tests.conftest import test_engine

    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    monkeypatch.setattr(database, "async_session_factory", factory)
    app.dependency_overrides.pop(get_session, None)
    yield factory


async def _request_probing_at_response_start(method, path, *, json, headers, probe):
    """Send one request; at `http.response.start`, run `probe` on another connection."""
    seen = []

    async def probing(scope, receive, send):
        async def send_after_probe(message):
            if message["type"] == "http.response.start":
                seen.append(await probe())
            await send(message)

        await app(scope, receive, send_after_probe)

    async with AsyncClient(transport=ASGITransport(app=probing), base_url="http://test") as c:
        response = await c.request(method, path, json=json, headers=headers)
    return response, seen


async def test_change_password_is_durable_before_the_response(committed):
    token = create_access_token({"sub": "admin"})
    jti = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])["jti"]
    async with committed() as s:
        await s.execute(delete(Config).where(Config.key.in_(
            ["admin_password_hash", "admin_password_changed_at"]
        )))
        s.add(Config(key="admin_password_hash", value={"hash": hash_password("old-password-1")}))
        await s.commit()

    async def stored_hash():
        async with committed() as other:
            row = (await other.execute(
                select(Config.value).where(Config.key == "admin_password_hash")
            )).scalar_one()
        return row["hash"]

    try:
        response, seen = await _request_probing_at_response_start(
            "POST", "/api/v1/auth/change-password",
            json={"current_password": "old-password-1", "new_password": "new-password-2"},
            headers={"Authorization": f"Bearer {token}"},
            probe=stored_hash,
        )
        assert response.status_code == 200, response.text
        assert len(seen) == 1
        assert verify_password("new-password-2", seen[0])
    finally:
        async with committed() as s:
            await s.execute(delete(Config).where(Config.key.in_(
                ["admin_password_hash", "admin_password_changed_at"]
            )))
            await s.execute(delete(TokenBlocklist).where(TokenBlocklist.jti == jti))
            await s.commit()


async def test_config_save_is_durable_before_the_response(committed, monkeypatch):
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.api.mcp.server import refresh_mcp_instructions

    purpose = prompt_module.list_purposes()[0]
    text = f"durable prompt {uuid.uuid4()}"
    before = prompt_module.get_overrides()
    headers = {"Authorization": f"Bearer {create_access_token({'sub': 'admin'})}"}

    async def stored_prompts():
        async with committed() as other:
            return (await other.execute(
                select(Config.value).where(Config.key == prompt_module.SYSTEM_PROMPTS_KEY)
            )).scalar_one_or_none()

    async def failing_commit(self):
        raise RuntimeError("commit refused")

    try:
        response, seen = await _request_probing_at_response_start(
            "PUT", "/api/v1/config/system-prompts",
            json={"overrides": {purpose: text}}, headers=headers, probe=stored_prompts,
        )
        assert response.status_code == 200, response.text
        assert seen == [{purpose: text}]
        assert prompt_module.get_overrides()[purpose] == text

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        with monkeypatch.context() as patch:
            patch.setattr(AsyncSession, "commit", failing_commit)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                refused = await c.put(
                    "/api/v1/config/system-prompts",
                    json={"overrides": {purpose: "never committed"}}, headers=headers,
                )
        assert refused.status_code == 500
        assert prompt_module.get_overrides()[purpose] == text
        assert await stored_prompts() == {purpose: text}
    finally:
        async with committed() as s:
            await s.execute(
                delete(Config).where(Config.key == prompt_module.SYSTEM_PROMPTS_KEY)
            )
            await s.commit()
        prompt_module.set_overrides(before)
        refresh_mcp_instructions()
