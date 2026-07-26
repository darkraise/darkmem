import pytest_asyncio

# Opt-in via `pytestmark = pytest.mark.usefixtures("_bench_db")`, not autouse:
# modules with no database dependency (e.g. ledger) must stay collectible and
# runnable without a reachable Postgres.
@pytest_asyncio.fixture(scope="session")
async def _bench_db():
    # reset_bench_db imports app modules, so importing bench_db here (which sets
    # DATABASE_URL first) must happen before anything touches app.database.
    from benchlib import bench_db
    await bench_db.reset_bench_db()
    yield
    await bench_db.engine.dispose()
