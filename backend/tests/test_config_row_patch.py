"""Config-row writes: one locked read-modify-write, so concurrent saves of
one row both survive and a first save never races another into a 500."""
from __future__ import annotations

import ast
import asyncio
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app import database
from app.api.auth import create_access_token
from app.database import get_session
from app.main import app
from app.models.config import Config
from app.services import prompt as prompt_module
from app.services.config import patch_config_row

pytestmark = pytest.mark.asyncio

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
SCANNED = ("api/routes/config.py", "services/notifications.py", "services/repo_allowlist.py")


@pytest_asyncio.fixture
async def committed(setup_database, monkeypatch):
    from tests.conftest import test_engine

    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    monkeypatch.setattr(database, "async_session_factory", factory)
    app.dependency_overrides.pop(get_session, None)
    keys: list[str] = []
    yield factory, keys
    async with factory() as s:
        await s.execute(delete(Config).where(Config.key.in_(keys)))
        await s.commit()


async def _stored(factory, key):
    async with factory() as s:
        return (await s.execute(select(Config.value).where(Config.key == key))).scalar_one_or_none()


async def test_two_concurrent_saves_of_one_row_both_survive(committed, monkeypatch):
    factory, keys = committed
    key = f"patch-test-{uuid.uuid4()}"
    keys.append(key)
    async with factory() as s:
        s.add(Config(key=key, value={"seed": 1}))
        await s.commit()

    second_started = asyncio.Event()

    async def first():
        async with factory() as s:
            real_flush = s.flush

            async def paused_flush(*args, **kwargs):
                await second_started.wait()
                await asyncio.sleep(0.2)
                return await real_flush(*args, **kwargs)

            s.flush = paused_flush
            return await patch_config_row(s, key, lambda current: {**current, "a": 1})

    async def second():
        await asyncio.sleep(0.05)
        second_started.set()
        async with factory() as s:
            return await patch_config_row(s, key, lambda current: {**current, "b": 2})

    await asyncio.wait_for(asyncio.gather(first(), second()), 10)
    assert await _stored(factory, key) == {"seed": 1, "a": 1, "b": 2}

    from app.services.notifications import NOTIFICATIONS_CONFIG_KEY
    from app.services.repo_allowlist import REPO_ALLOWLIST_KEY

    keys.extend([prompt_module.SYSTEM_PROMPTS_KEY, REPO_ALLOWLIST_KEY, NOTIFICATIONS_CONFIG_KEY])
    async with factory() as s:
        await s.execute(delete(Config).where(Config.key.in_(keys[1:])))
        await s.commit()
    purposes = prompt_module.list_purposes()[:2]
    before = prompt_module.get_overrides()
    headers = {"Authorization": f"Bearer {create_access_token({'sub': 'admin'})}"}
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            answers = await asyncio.gather(
                c.put("/api/v1/config/system-prompts",
                      json={"overrides": {purposes[0]: "first"}}, headers=headers),
                c.put("/api/v1/config/system-prompts",
                      json={"overrides": {purposes[1]: "second"}}, headers=headers),
                c.put("/api/v1/config/notifications",
                      json={"telegram": {"chat_id": "42"}}, headers=headers),
                c.put("/api/v1/config/notifications",
                      json={"notify_on": {"job_failure": False}}, headers=headers),
                c.put("/api/v1/config/repo-allowlist",
                      json={"patterns": ["github.com/a"]}, headers=headers),
                c.put("/api/v1/config/repo-allowlist",
                      json={"patterns": ["gitlab.com/b"]}, headers=headers),
            )
        assert [a.status_code for a in answers] == [200] * 6, [a.text for a in answers]
        assert await _stored(factory, prompt_module.SYSTEM_PROMPTS_KEY) == {
            purposes[0]: "first", purposes[1]: "second",
        }
        notifications = await _stored(factory, NOTIFICATIONS_CONFIG_KEY)
        assert notifications["telegram"]["chat_id"] == "42"
        assert notifications["notify_on"]["job_failure"] is False
        assert await _stored(factory, REPO_ALLOWLIST_KEY) in (
            {"patterns": ["github.com/a"]}, {"patterns": ["gitlab.com/b"]},
        )
    finally:
        prompt_module.set_overrides(before)


async def test_helper_creates_a_missing_row(committed):
    factory, keys = committed
    key = f"patch-test-{uuid.uuid4()}"
    keys.append(key)

    async with factory() as s:
        answer = await patch_config_row(s, key, lambda current: {**current, "made": True})
    assert answer == {"made": True}
    assert await _stored(factory, key) == {"made": True}

    racing = f"patch-test-{uuid.uuid4()}"
    keys.append(racing)

    async def save(field):
        async with factory() as s:
            await patch_config_row(s, racing, lambda current: {**current, field: True})

    await asyncio.wait_for(asyncio.gather(save("x"), save("y")), 10)
    async with factory() as s:
        count = (await s.execute(
            select(func.count()).select_from(Config).where(Config.key == racing)
        )).scalar_one()
    assert count == 1
    assert await _stored(factory, racing) == {"x": True, "y": True}


def _config_writes(tree: ast.AST) -> list[str]:
    found = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Attribute) and target.attr == "value":
                    found.append(f"line {node.lineno}: .value assignment")
        if isinstance(node, ast.Call):
            called = node.func
            name = called.id if isinstance(called, ast.Name) else getattr(called, "attr", "")
            if name == "Config":
                found.append(f"line {node.lineno}: Config(...) row built")
            if name in {"insert", "pg_insert"} and any(
                isinstance(arg, ast.Name) and arg.id == "Config" for arg in node.args
            ):
                found.append(f"line {node.lineno}: insert(Config)")
    return found


def test_no_route_writes_a_config_row_outside_the_helper():
    offenders = {}
    for relative in SCANNED:
        found = _config_writes(ast.parse((APP_ROOT / relative).read_text()))
        if found:
            offenders[relative] = found
    assert not offenders
