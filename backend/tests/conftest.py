import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.api.auth import create_access_token, hash_password
from app.config import settings
from app.database import get_session
from app.main import app
from app.models.config import Config

BACKEND_DIR = Path(__file__).resolve().parent.parent

test_engine = create_async_engine(settings.test_database_url)


async def _reset_schema() -> None:
    async with test_engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))


def _run_alembic_upgrade() -> None:
    # Subprocess so Alembic's env.py can run its own asyncio.run without
    # colliding with pytest-asyncio's event loop, and so pydantic-settings
    # picks up the DATABASE_URL override from a fresh import of app.config.
    env = {**os.environ, "DATABASE_URL": settings.test_database_url}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "alembic upgrade head failed for the test database:\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    await _reset_schema()
    _run_alembic_upgrade()
    yield
    await _reset_schema()
    await test_engine.dispose()


@pytest_asyncio.fixture
async def session(setup_database):
    connection = await test_engine.connect()
    transaction = await connection.begin()
    async_session = AsyncSession(bind=connection, expire_on_commit=False)

    await connection.begin_nested()

    @event.listens_for(async_session.sync_session, "after_transaction_end")
    def restart_savepoint(session, trans):
        if trans.nested and not trans._parent.nested:
            session.begin_nested()

    yield async_session

    await async_session.close()
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture
async def client(session):
    async def override():
        yield session

    app.dependency_overrides[get_session] = override
    # The lifespan would normally set this on startup; the test client
    # never enters it, so initialise here to match production state.
    if not getattr(app.state, "llm_config_lock", None):
        app.state.llm_config_lock = asyncio.Lock()
    if not getattr(app.state, "repo_sync_wakeup", None):
        app.state.repo_sync_wakeup = asyncio.Event()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(session):
    hashed = hash_password("test-admin-password")
    session.add(Config(key="admin_password_hash", value={"hash": hashed}))
    await session.flush()

    token = create_access_token({"sub": "admin"})
    return {"Authorization": f"Bearer {token}"}
