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


@pytest.mark.asyncio
async def test_reset_forgets_embedder_registrations_so_partitions_get_recreated():
    """embedder_registry (app/services/embedder_registry.py) is a
    process-wide singleton that marks a fingerprint "known" for the life
    of the process and never re-checks the DB. A caller resetting the
    bench DB a second time in one process -- run_smoke.py's two-pass
    affordability gate does exactly this -- would otherwise have its
    second _register_fingerprint() silently no-op against a schema that
    no longer has the partition tables, and every embedding write after
    it fails with UndefinedTableError."""
    from app.services.embedder_registry import EmbedderInfo, child_table, embedder_registry

    fingerprint = "bench-test-embedder|3"
    info = EmbedderInfo(fingerprint=fingerprint, model_id="bench-test-embedder", dims=3, source="llm")

    async with bench_db.session_factory() as session:
        await embedder_registry.register(session, info)
    assert embedder_registry.is_known(fingerprint)

    table = child_table("memory_embeddings", fingerprint)
    async with bench_db.session_factory() as session:
        count = (await session.execute(text(f"SELECT count(*) FROM {table}"))).scalar()
    assert count == 0

    await bench_db.reset_bench_db()

    # The table this fingerprint pointed at was just dropped; the registry
    # must no longer claim the fingerprint is known.
    assert not embedder_registry.is_known(fingerprint)

    # Re-registering after the reset must actually recreate the table
    # (not no-op), and the connection used to query it must not be a
    # pre-reset one carrying a stale asyncpg statement-cache entry.
    async with bench_db.session_factory() as session:
        await embedder_registry.register(session, info)
        count = (await session.execute(text(f"SELECT count(*) FROM {table}"))).scalar()
    assert count == 0
