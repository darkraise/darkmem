import pytest
from sqlalchemy import text

from benchlib import bench_db

pytestmark = pytest.mark.usefixtures("_bench_db")


@pytest.mark.asyncio
async def test_reset_creates_empty_memories_table():
    await bench_db.reset_bench_db()
    async with bench_db.session_factory() as s:
        count = (await s.execute(text("SELECT count(*) FROM memories"))).scalar()
    assert count == 0
