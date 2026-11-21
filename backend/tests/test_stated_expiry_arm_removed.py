"""The fact-side stated-expiry arm is gone; the memory-side derivation stays.

``knowledge_triples.stated_expiry`` keeps its column and partial index (a
released build still maps it), but nothing in the app writes, folds or spends
it. A memory that states its own expiry still gets ``memories.expires_at``.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.test_repo_entity_merge import _entity, _fact

APP = Path(__file__).resolve().parents[1] / "app"

# The only files in backend/app that may name `stated_expiry`. Fact-side files
# never belong here.
ALLOWED = {
    # derives memories.expires_at from a memory's own stated retention
    "services/stated_expiry.py",
    # calls derive_stated_expiry in Phase 5 savepoint A for memories.expires_at
    "services/pipeline.py",
}


def test_no_code_reads_or_writes_the_fact_column():
    naming = {
        path.relative_to(APP).as_posix()
        for path in APP.rglob("*.py")
        if "stated_expiry" in path.read_text(encoding="utf-8")
    }
    assert naming <= ALLOWED, sorted(naming - ALLOWED)

    for path in APP.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "knowledge_triples.stated_expiry" not in source, path
        assert "StatedExpiryOutcome" not in source, path

    repository = (APP / "repositories" / "knowledge_triples.py").read_text(encoding="utf-8")
    columns = re.search(r'_COLUMNS = """(.*?)"""', repository, re.S)
    assert columns is not None
    assert "stated_expiry" not in columns.group(1)


@pytest.mark.asyncio
async def test_fact_column_and_index_still_exist(session):
    column = (await session.execute(text(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = 'knowledge_triples' "
        "AND column_name = 'stated_expiry'"
    ))).scalar()
    index = (await session.execute(text(
        "SELECT indexdef FROM pg_indexes WHERE schemaname = 'public' "
        "AND indexname = 'ix_knowledge_triples_stated_expiry'"
    ))).scalar()
    assert column == "timestamp with time zone"
    assert index is not None and "WHERE" in index


EXTRACTION = {
    "entities": [{"name": "ArmRemovedTool", "type": "tool"}],
    "relationships": [],
    "memory_type": "fact",
    "summary": "",
    "emotions": [],
    "flags": [],
}


@pytest.mark.asyncio
async def test_memory_expiry_is_still_derived_from_a_stated_expiry(setup_database, monkeypatch):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.services.pipeline import _flag_cache_reset
    from tests.conftest import test_engine
    from tests.test_pipeline_phase1 import FakeEmbedder, cleanup, make_pipeline, seed_memories

    fingerprint = "arm-removed|4"
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    _flag_cache_reset()
    content = "This note is valid until 2026-12-31."
    memory_ids = await seed_memories(factory, [content])
    try:
        pipe = make_pipeline(factory, FakeEmbedder([fingerprint]), EXTRACTION, monkeypatch)
        await pipe.process_batch([
            {"memory_id": memory_ids[0], "content": content, "source": "api"}
        ])
        async with factory() as s:
            expires_at = (await s.execute(
                text("SELECT expires_at FROM memories WHERE id = CAST(:id AS uuid)"),
                {"id": str(memory_ids[0])},
            )).scalar_one()
        assert expires_at == datetime(2027, 1, 1, tzinfo=UTC)
    finally:
        await cleanup(factory, memory_ids, [fingerprint], ["ArmRemovedTool"])


@pytest.mark.asyncio
async def test_merge_fold_keeps_the_earlier_reference_and_valid_times(session):
    from app.services.entity_merge import merge_entities

    # Names of their own: a committed `postgresql` row another file leaves in
    # this worker would collide with the merge module's calibration pair.
    tag = uuid4().hex[:8]
    survivor = await _entity(
        session, f"pg-{tag}", "database", repo_ids=[uuid4()],
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    loser = await _entity(
        session, f"pgsql-{tag}", "database", memory_ids=[uuid4()],
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
    other = await _entity(session, f"app-{tag}", "project")
    early = datetime(2025, 6, 1, tzinfo=UTC)
    kept = await _fact(
        session, subject_id=other, object_id=survivor,
        subject_name=f"app-{tag}", object_name=f"pg-{tag}",
        reference_time=datetime(2026, 3, 1, tzinfo=UTC),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    folded = await _fact(
        session, subject_id=other, object_id=loser,
        subject_name=f"app-{tag}", object_name=f"pgsql-{tag}",
        reference_time=early, created_at=datetime(2026, 2, 1, tzinfo=UTC),
    )
    for fact_id, valid_at in ((kept, datetime(2026, 3, 1, tzinfo=UTC)), (folded, early)):
        await session.execute(
            text("UPDATE knowledge_triples SET valid_at = CAST(:v AS timestamptz) "
                 "WHERE id = CAST(:id AS uuid)"),
            {"v": valid_at, "id": fact_id},
        )
    await session.flush()

    await merge_entities(session, survivor, loser)

    row = (await session.execute(
        text("SELECT reference_time, valid_at, expired_at FROM knowledge_triples "
             "WHERE id = CAST(:k AS uuid)"),
        {"k": kept},
    )).one()
    assert row.reference_time == early
    assert row.valid_at == early
    assert row.expired_at is None
