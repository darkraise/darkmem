import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

# Pin the in-process engine to the test database before any app module imports
# it. database.py builds its engine from settings.database_url at import time;
# with DATABASE_URL unset that now derives the deployment default
# (postgres:5432), which is unreachable from a host-side test run.
_TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test",
)


def _ensure_worker_database(base_url: str, worker: str) -> str:
    """Give each pytest-xdist worker a database of its own.

    The session fixture below drops and re-migrates the whole schema, so two
    processes can never share one database. Each worker derives
    ``<base>_<worker>`` (``darkmem_test_gw0``, ...) and creates it on the same
    server, connecting through the base database, which must already exist.
    """
    import asyncpg

    base, _, name = base_url.rpartition("/")
    worker_name = f"{name}_{worker}"

    async def create() -> None:
        dsn = f"{base}/{name}".replace("postgresql+asyncpg://", "postgresql://", 1)
        conn = await asyncpg.connect(dsn)
        try:
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", worker_name
            )
            if not exists:
                await conn.execute(f'CREATE DATABASE "{worker_name}"')
        finally:
            await conn.close()

    asyncio.run(create())
    return f"{base}/{worker_name}"


if os.environ.get("PYTEST_XDIST_WORKER"):
    _TEST_DATABASE_URL = _ensure_worker_database(
        _TEST_DATABASE_URL, os.environ["PYTEST_XDIST_WORKER"]
    )
    # Settings, and the tests that read the variable directly, follow it.
    os.environ["TEST_DATABASE_URL"] = _TEST_DATABASE_URL
os.environ["DATABASE_URL"] = _TEST_DATABASE_URL

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete as sa_delete, text
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
    # The outer transaction above is the isolation boundary. SQLAlchemy's
    # default join_transaction_mode="conditional_savepoint" resolves to
    # "rollback_only" here -- there is no nested transaction on the connection,
    # so no SAVEPOINT is opened and the session joins the outer transaction
    # directly (orm/session.py:1210-1214). What that buys is one-directional:
    # should_commit is False, so a commit() in a test is dropped rather than
    # propagated, but a ROLLBACK is not, and one ends the boundary outright.
    #
    # So a test that drives a rollback path before its own writes LEAKS. Every
    # door that answers a refusal rolls back the session it was handed --
    # `document_update`'s uri_conflict/unresolved envelopes and
    # `document_delete`'s bare `except Exception` both do -- and once one has
    # run, anything the test writes afterwards autobegins a session-owned
    # transaction and commits for real, surviving the teardown rollback and
    # colliding with whatever module claims those ids next. Order such a test
    # writes-then-refusals. A second session is no escape: `session_factory`
    # binds to this same connection, so it resolves to "rollback_only" too and
    # its rollback ends the same boundary, while a session on its own
    # connection cannot see the test's uncommitted rows at all.
    #
    # The 1.x recipe that reopened a savepoint by hand from an
    # "after_transaction_end" listener does not apply here. It was removed as
    # harmful rather than as inert -- it fired while an application-level
    # session.begin_nested() was still unwinding, and the InvalidRequestError
    # that raised was caught and reported by events.record_event as a journal
    # failure on every call in the suite, masking real ones.
    async_session = AsyncSession(bind=connection, expire_on_commit=False)

    # A wait_process flush with no pipeline factory opens its sessions from the
    # app's factory, never the request's; binding those to this connection keeps
    # the capture's uncommitted buffer row visible to it and its writes undone.
    from contextlib import asynccontextmanager

    import app.services.memory as memory_module

    @asynccontextmanager
    async def _sessions_on_this_connection():
        own = AsyncSession(bind=connection, expire_on_commit=False)
        try:
            yield own
        finally:
            await own.close()

    previous_factory = memory_module.async_session_factory
    memory_module.async_session_factory = _sessions_on_this_connection

    yield async_session

    memory_module.async_session_factory = previous_factory
    await async_session.close()
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture
async def session_factory(session):
    """Sessions on the test's own connection.

    ``session`` runs inside an outer transaction that is rolled back after each
    test. A recorder opening a genuinely independent session would write on a
    different connection — invisible to the test *and* not rolled back, leaking
    rows across the suite. Binding the factory to the same connection keeps
    recorder writes both visible and undone. Production binds the real engine;
    this fixture is the only place the two differ.
    """
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def factory():
        # `session.bind` is the AsyncConnection the fixture opened;
        # `get_bind()` would hand back the sync one, which AsyncSession rejects.
        nested = AsyncSession(bind=session.bind, expire_on_commit=False)
        try:
            yield nested
        finally:
            await nested.close()

    return factory


@pytest_asyncio.fixture
async def clean_llm_usage(setup_database):
    """Empty ``llm_usage`` before a test that asserts on whole-table counts.

    The recorder writes on its own session by design, and since it is wired
    into the production orchestrator any test that drives a real LLM call
    through ``app.state.llm`` commits rows that outlive it -- the rollback the
    ``session`` fixture gives everything else does not reach them. A test that
    counts the whole table therefore cannot assume it starts empty; this makes
    it so rather than weakening the assertion to a filter.
    """
    from sqlalchemy import text as sa_text
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as s:
        await s.execute(sa_text("DELETE FROM llm_usage"))
        await s.commit()
    yield
    async with factory() as s:
        await s.execute(sa_text("DELETE FROM llm_usage"))
        await s.commit()


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
    # A config PUT installs a live orchestrator on app.state; left behind, it
    # made a later file's search dial an unreachable embedder for 95s.
    previous_llm = getattr(app.state, "llm", None)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
    app.state.llm = previous_llm


@pytest_asyncio.fixture(autouse=True)
def _reset_login_rate_limiter():
    """Login rate-limiter state is a process-global singleton; clear it between
    tests so failed-login attempts from the shared test-client IP don't
    accumulate across tests and trip a spurious lockout."""
    from app.api.websocket import session_revocations
    from app.services.login_rate_limit import login_rate_limiter
    login_rate_limiter.reset()
    session_revocations.reset()
    yield
    login_rate_limiter.reset()
    session_revocations.reset()


@pytest.fixture(autouse=True)
def _reset_embedder_cooldown():
    """A failed query embed parks the semantic arm for a minute, process-wide;
    one test's fake embedder must not park it for the next test's."""
    from app.services import hybrid_search
    hybrid_search._embedder_retry_at = 0.0
    yield
    hybrid_search._embedder_retry_at = 0.0


@pytest.fixture(autouse=True)
def _forget_document_connections():
    """Connections are memoised process-wide; a test's rolled-back corpus must
    not answer the next test's read."""
    from app.services.document_connections import forget_connections
    forget_connections()
    yield
    forget_connections()


@pytest_asyncio.fixture
async def auth_headers(session):
    hashed = hash_password("test-admin-password")
    session.add(Config(key="admin_password_hash", value={"hash": hashed}))
    await session.flush()

    token = create_access_token({"sub": "admin"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def stub_llm():
    """Point the app at a stub embedder for the document write door.

    The test app has no orchestrator configured, and `get_llm` reads
    `request.app.state.llm`, so the route under test needs one — the same
    way `test_documents_api.py`'s `scripted_llm` wires the Q&A door.
    """
    from tests.test_document_door import StubEmbedder

    llm = StubEmbedder()
    previous = getattr(app.state, "llm", None)
    app.state.llm = llm
    yield llm
    app.state.llm = previous


@pytest_asyncio.fixture
async def mcp_streamable_app():
    """Fresh streamable-HTTP app with its lifespan entered.

    v2's lowlevel ``Server.streamable_http_app()`` builds a new
    ``StreamableHTTPSessionManager`` and overwrites ``_session_manager``
    unconditionally on every call, so each call already gets a fresh,
    unstarted manager with no reset needed first. The lifespan runs in a
    dedicated task because anyio cancel scopes must enter and exit in the
    same task, and pytest-asyncio tears async fixtures down in a different
    task than setup.
    """
    from app.api.mcp.server import mcp as mcp_server, mcp_streamable_http_kwargs

    mcp_app = mcp_server.streamable_http_app(**mcp_streamable_http_kwargs())
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


@pytest_asyncio.fixture(scope="session")
async def mcp_credential(setup_database):
    """A committed API key granting both MCP scopes, for the whole session.

    /mcp requires a verified bearer on every request, so a client driving the
    door needs a real ``api_keys`` row. It has to be **committed**, not written
    through the per-test ``session`` fixture: the token verifier opens its own
    session on the application engine, a different physical connection, and a
    row held inside the fixture's never-committed outer transaction is
    invisible there. Session-scoped so the bcrypt verification cost is paid
    once rather than per test.

    Both scopes, because the door's readers and its writers are exercised from
    the same client; a test that needs a key *lacking* a scope mints its own.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.models.api_key import ApiKey
    from app.services.api_keys import issue_key

    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as s:
        row, credential = await issue_key(
            s, name="test-suite", scopes=["capture", "read"]
        )
        row_id = row.id
        await s.commit()

    yield credential

    async with factory() as s:
        await s.execute(sa_delete(ApiKey).where(ApiKey.id == row_id))
        await s.commit()


@pytest_asyncio.fixture
async def mcp_http_client(session, monkeypatch, mcp_streamable_app, mcp_credential):
    """JSON-RPC client for MCP tool calls, wired to the per-test session.

    MCP tools open sessions via the module-level async_session_factory, not
    the FastAPI get_session dependency, so the factory is patched here;
    without it tool calls commit real rows outside the test transaction.

    The bearer is the suite's own key rather than a patched-out auth check: the
    door refuses an unauthenticated call, and a fixture that disabled that
    would leave every MCP test asserting behaviour production does not have.
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
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {mcp_credential}",
        },
    ) as c:
        yield c


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "expect_refusals: this test deliberately provokes a supersede refusal "
        "the tree-wide collector in tests/test_memory_dream.py otherwise "
        "asserts never happens",
    )


@pytest.fixture(autouse=True)
def _corroboration_gate_closed_by_default(tmp_path, monkeypatch):
    """Pin the gate CLOSED for every test that does not deliberately open it.

    The suppression tests were written unfixtured on purpose — driving the real
    doors is the shape a review found missing — but "unfixtured" silently meant
    "reads whatever `app/services/` happens to contain", and the tree contained
    no record only because G-C had never cleared. **On 2026-08-16 it cleared and
    the record was minted, and 28 suppression assertions inverted in one commit
    without a single one of them being about the mint.** They did not catch a
    regression; they stopped testing suppression, which is the failure this
    fixture forecloses.

    So the precondition is stated rather than inherited. `PROMOTION_RECORD_PATH`
    points at a path that does not exist, and a test wanting the gate open asks
    for :func:`cleared_promotion_record`, which is requested after this one and
    therefore wins. The default direction matters and is the conservative one:
    autouse-*opening* would leave suppression untested everywhere at once, which
    is why the sibling fixture refuses to be autouse; autouse-*closing* makes
    every door drive assert the withheld rung unless it says otherwise.

    What this deliberately stops covering is whether the *shipped* record is
    well-formed — that is a property of the artifact, not of the gate, and
    `test_claim_serving_gates.test_the_shipped_record_if_present_is_one_the_gate_can_read`
    asserts it directly against the real path instead.
    """
    from app.services import claim_gates

    monkeypatch.setattr(
        claim_gates, "PROMOTION_RECORD_PATH", tmp_path / "no-such-record.json"
    )


@pytest.fixture
def cleared_promotion_record(tmp_path, monkeypatch):
    """Open T2.95's corroboration gate for a test that is not about the gate.

    Since T2.95 a promoted fact status is withheld at the serving boundary
    unless G-C's promotion-metrics record exists, so a test asserting a
    `corroborated` badge is, by default, asserting a label the product
    deliberately suppresses. Tests about badge *shape*, source grouping or
    composition want the gate open so they measure what they are about; tests
    about the gate itself must NOT use this fixture.

    Deliberately opt-in rather than autouse: an autouse version would open the
    gate for the whole suite and the suppression would go untested everywhere
    at once, which is the failure mode a default-open gate has.
    """
    from app.services import claim_gates

    record = tmp_path / "promotion_metrics_record.json"
    record.write_text(json.dumps({"gate_eligible": True, "source": "test fixture"}))
    monkeypatch.setattr(claim_gates, "PROMOTION_RECORD_PATH", record)
    return record


@pytest.fixture(autouse=True)
def _reset_graph_caches():
    from app.services.graph import reset_graph_caches

    reset_graph_caches()
    yield
    reset_graph_caches()


@pytest.fixture(autouse=True)
def _mcp_call_log_buffered_only(monkeypatch):
    """The MCP call log flushes from a background task on the application
    engine, which would commit rows outside every test's transaction. Tests
    that assert on the log drain it onto their own connection instead."""
    import app.services.mcp_call_log as mcp_call_log

    monkeypatch.setattr(mcp_call_log, "_auto_flush", False)
    mcp_call_log._reset_for_tests()
    yield
    mcp_call_log._reset_for_tests()
