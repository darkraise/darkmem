"""The work-log vector family: its child table, and the writer that fills it."""
from __future__ import annotations

from sqlalchemy import text

from app.services.embedder_registry import EmbedderInfo, EmbedderRegistry, child_table

FAMILY_FP = "worklog-family-test|4"


async def _register_family_fingerprint(session) -> None:
    await EmbedderRegistry().register(
        session,
        EmbedderInfo(fingerprint=FAMILY_FP, model_id="worklog-family-test", dims=4, source="llm"),
    )


async def _indexes(session, table: str) -> list[str]:
    return list((await session.execute(
        text("SELECT indexdef FROM pg_indexes WHERE schemaname = 'public' AND tablename = :t"),
        {"t": table},
    )).scalars().all())


async def test_registering_a_fingerprint_creates_the_family_without_an_ann_index(session):
    await _register_family_fingerprint(session)
    table = child_table("worklog_embeddings", FAMILY_FP)

    columns = set((await session.execute(
        text("SELECT column_name FROM information_schema.columns "
             "WHERE table_schema = 'public' AND table_name = :t"),
        {"t": table},
    )).scalars().all())
    assert columns == {"entry_id", "fingerprint", "project", "embedding", "created_at"}

    indexes = await _indexes(session, table)
    assert not [d for d in indexes if "hnsw" in d], indexes
    assert any("(project)" in d for d in indexes), indexes


async def test_every_other_family_keeps_its_ann_index(session):
    await _register_family_fingerprint(session)
    indexes = await _indexes(session, child_table("page_embeddings", FAMILY_FP))
    assert any("hnsw" in d for d in indexes), indexes
