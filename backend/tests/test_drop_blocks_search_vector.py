"""Revision 0006 drops ``blocks.search_vector`` and its index, keeping every row.

The revision test runs on the private ``<worker database>_rev`` database
``tests/test_drop_triple_embeddings.py`` defines; the shared worker database
is migrated to head and is never downgraded.
"""
from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.services.block_verbs import update_block
from app.services.document_door import put_document
from app.services.page_door import create_page
from tests.test_drop_triple_embeddings import (  # noqa: F401 — rev_database is a fixture
    REV_DSN,
    REV_URL,
    _alembic,
    _fetch,
    rev_database,
)

DOCUMENT_TEXT = "# Report\n\nThe body paragraph.\n\n```python\nprint('kept')\n```\n"
PAGE_TEXT = "A page paragraph.\n\n- one item\n"


class _ScriptedEmbedder:
    config = {"model": "probe", "base_url": "http://probe", "api_kind": "openai"}

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        return ([[1.0, 0.0, 0.0, 0.0] for _ in texts], "drop-sv-probe|4")

    async def embed(self, value: str):
        return [1.0, 0.0, 0.0, 0.0], "drop-sv-probe|4"


def _blocks() -> list[tuple]:
    return asyncio.run(_fetch(
        REV_DSN,
        "SELECT CAST(id AS text), document_id IS NOT NULL, text FROM blocks ORDER BY id",
    ))


def _column_and_index() -> tuple[list, list]:
    column = asyncio.run(_fetch(
        REV_DSN,
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = 'blocks' "
        "AND column_name = 'search_vector'",
    ))
    index = asyncio.run(_fetch(
        REV_DSN,
        "SELECT indexname FROM pg_indexes WHERE schemaname = 'public' "
        "AND indexname = 'ix_blocks_search_vector'",
    ))
    return column, index


async def _file_a_document_and_a_page() -> None:
    engine = create_async_engine(REV_URL)
    try:
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            await put_document(
                session, None, project="rev", uri="notes/report.md",
                content=DOCUMENT_TEXT, embed_inline=False,
            )
        async with factory() as session:
            await create_page(session, None, project="rev", title="Rev page", content=PAGE_TEXT)
            await session.commit()
    finally:
        await engine.dispose()


def test_column_and_index_are_gone_and_rows_survive(rev_database):
    result = _alembic("upgrade", "0005")
    assert result.returncode == 0, result.stderr
    asyncio.run(_file_a_document_and_a_page())
    before = _blocks()
    assert {owned_by_document for _, owned_by_document, _ in before} == {True, False}
    assert _column_and_index() == ([("search_vector",)], [("ix_blocks_search_vector",)])

    result = _alembic("upgrade", "head")

    assert result.returncode == 0, result.stderr
    assert _column_and_index() == ([], [])
    assert _blocks() == before


@pytest.mark.asyncio
async def test_document_and_page_writes_work_after_the_drop(session):
    llm = _ScriptedEmbedder()
    filed = await put_document(
        session, llm, project="after-drop", uri="notes/after.md",
        content=DOCUMENT_TEXT, embed_inline=False,
    )
    block_id = (await session.execute(
        text("SELECT CAST(id AS text) FROM blocks WHERE document_id = CAST(:d AS uuid) "
             "AND type = 'paragraph'"),
        {"d": str(filed.document_id)},
    )).scalar_one()

    await update_block(session, llm, block_id=block_id, text="The edited paragraph.")
    page = await create_page(session, llm, project="after-drop", title="After", content=PAGE_TEXT)

    texts = (await session.execute(
        text("SELECT text FROM blocks WHERE document_id = CAST(:d AS uuid) "
             "OR page_id = CAST(:p AS uuid)"),
        {"d": str(filed.document_id), "p": str(page.id)},
    )).scalars().all()
    assert "The edited paragraph." in texts
    assert "A page paragraph." in texts
