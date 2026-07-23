import pytest_asyncio


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _bench_db():
    # reset_bench_db imports app modules, so importing bench_db here (which sets
    # DATABASE_URL first) must happen before anything touches app.database.
    from benchlib import bench_db
    await bench_db.reset_bench_db()
    yield
    await bench_db.engine.dispose()
