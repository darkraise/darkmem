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
from sqlalchemy import text
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
    # The outer transaction above is the isolation boundary, and SQLAlchemy's
    # default join_transaction_mode="conditional_savepoint" already runs this
    # session inside its own SAVEPOINT on it, so a commit() in a test cannot
    # reach it. The 1.x recipe that reopened that savepoint by hand from an
    # "after_transaction_end" listener is therefore redundant here, and it was
    # not harmless: it fired while an application-level session.begin_nested()
    # was still unwinding, and the InvalidRequestError that raised was caught
    # and reported by events.record_event as a journal failure on every call
    # in the suite, masking real ones.
    async_session = AsyncSession(bind=connection, expire_on_commit=False)

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


@pytest_asyncio.fixture
async def mcp_streamable_app():
    """Fresh streamable-HTTP app with its lifespan entered.

    FastMCP caches one StreamableHTTPSessionManager whose run() is
    once-per-instance, so the cached manager is dropped first; the app must
    be built AFTER the reset so its route handler and lifespan share the
    fresh manager. The lifespan runs in a dedicated task because anyio
    cancel scopes must enter and exit in the same task, and pytest-asyncio
    tears async fixtures down in a different task than setup.
    """
    from app.api.mcp.server import mcp as mcp_server

    # Null out the cached manager so streamable_http_app() creates a fresh
    # StreamableHTTPSessionManager; the SDK's _has_started flag makes each
    # instance single-use, so reusing one across tests raises RuntimeError.
    mcp_server._session_manager = None
    mcp_app = mcp_server.streamable_http_app()
    started = asyncio.Event()
    stop = asyncio.Event()

    async def _run_lifespan():
        async with mcp_app.router.lifespan_context(mcp_app):
            started.set()
            await stop.wait()

    runner = asyncio.create_task(_run_lifespan())
    startup = asyncio.create_task(started.wait())
    done, _ = await asyncio.wait({runner, startup}, return_when=asyncio.FIRST_COMPLETED)
    if runner in done:
        startup.cancel()
        runner.result()  # surfaces the startup exception instead of hanging
    try:
        yield mcp_app
    finally:
        stop.set()
        await runner


@pytest_asyncio.fixture
async def mcp_http_client(session, monkeypatch, mcp_streamable_app):
    """JSON-RPC client for MCP tool calls, wired to the per-test session.

    MCP tools open sessions via the module-level async_session_factory, not
    the FastAPI get_session dependency, so the factory is patched here;
    without it tool calls commit real rows outside the test transaction.
    """
    from contextlib import asynccontextmanager

    import app.api.mcp.server as mcp_module

    @asynccontextmanager
    async def _fake_ctx():
        yield session

    monkeypatch.setattr(mcp_module, "async_session_factory", lambda: _fake_ctx())
    transport = ASGITransport(app=mcp_streamable_app)
    async with AsyncClient(
        transport=transport,
        base_url="http://localhost:8000",
        headers={"Accept": "application/json"},
    ) as c:
        yield c
