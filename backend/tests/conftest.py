import asyncio
import os
import subprocess
import sys
from pathlib import Path

# Pin the in-process engine to the test database before any app module imports
# it. database.py builds its engine from settings.database_url at import time;
# with DATABASE_URL unset that now derives the deployment default
# (postgres:5432), which is unreachable from a host-side test run.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test",
)

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
    # Stand up a minimal JobRegistry so handlers that read/write
    # ``app.state.job_registry`` and the repo-sync wakeup event find
    # something live. We register only the repo_sync job (with a no-op
    # runner) because that is all the existing route handlers depend on.
    if not getattr(app.state, "job_registry", None):
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from app.services.job_registry import Job, JobRegistry
        test_factory = async_sessionmaker(test_engine, expire_on_commit=False)
        registry = JobRegistry(test_factory)
        async def _noop():
            return None
        registry.register(Job(
            key="repo_sync",
            display_name="Repository Sync",
            description="(test stub)",
            default_cron="*/5 * * * *",
            min_interval_seconds=30,
            runner=_noop,
        ))
        app.state.job_registry = registry
        app.state.repo_sync_wakeup = registry.get("repo_sync").wakeup
    elif not getattr(app.state, "repo_sync_wakeup", None):
        repo_job = app.state.job_registry.get("repo_sync")
        app.state.repo_sync_wakeup = repo_job.wakeup if repo_job else asyncio.Event()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(autouse=True)
def _reset_login_rate_limiter():
    """Login rate-limiter state is a process-global singleton; clear it between
    tests so failed-login attempts from the shared test-client IP don't
    accumulate across tests and trip a spurious lockout."""
    from app.services.login_rate_limit import login_rate_limiter
    login_rate_limiter.reset()
    yield
    login_rate_limiter.reset()


@pytest_asyncio.fixture
async def auth_headers(session):
    hashed = hash_password("test-admin-password")
    session.add(Config(key="admin_password_hash", value={"hash": hashed}))
    await session.flush()

    token = create_access_token({"sub": "admin"})
    return {"Authorization": f"Bearer {token}"}
