"""The page door's create, get and list halves (spec 2026-09-08, §7)."""
from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

from app.services.document_ingest import compute_content_hash
from app.services.page_door import (
    PageTargetUnresolved,
    create_page,
    get_page,
    list_pages,
)


FINGERPRINT = "test-fp-pages|3"


@pytest.fixture(autouse=True)
def _forget_probe_fingerprint():
    """`EmbedderRegistry` caches known fingerprints process-wide while each
    test's writes roll back at teardown, so a later test would skip
    registering a fingerprint whose child table no longer exists."""
    from app.services.embedder_registry import embedder_registry

    embedder_registry.forget(FINGERPRINT)
    yield
    embedder_registry.forget(FINGERPRINT)


class StubEmbedder:
    def __init__(self, fingerprint: str = FINGERPRINT):
        self.fingerprint = fingerprint
        self.batches: list[list[str]] = []

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        self.batches.append(list(texts))
        return ([[1.0, 0.0, 0.0] for _ in texts], self.fingerprint)

    async def embed(self, value: str):
        return [1.0, 0.0, 0.0], self.fingerprint

    def llm_fingerprint(self) -> str:
        return self.fingerprint


@pytest.fixture
def llm():
    return StubEmbedder()


async def _blocks_of(session, page_id):
    rows = await session.execute(
        text(
            "SELECT type, text, order_index FROM blocks "
            "WHERE page_id = CAST(:id AS uuid) ORDER BY order_index"
        ),
        {"id": str(page_id)},
    )
    return [dict(r) for r in rows.mappings().all()]


async def _page_row(session, page_id):
    row = await session.execute(
        text("SELECT * FROM pages WHERE id = CAST(:id AS uuid)"),
        {"id": str(page_id)},
    )
    return dict(row.mappings().one())


@pytest.mark.asyncio
async def test_a_child_requires_its_parent_to_exist(session, llm):
    """The Notion invariant, and the reason pages are not documents: a
    document files to any path unconditionally, a page does not."""
    with pytest.raises(PageTargetUnresolved):
        await create_page(session, llm, project="p", title="orphan",
                          parent_id=str(uuid4()))


@pytest.mark.asyncio
async def test_creating_with_content_parses_it_into_blocks(session, llm):
    """Without this path the first caller writes `content` straight onto the
    row and recreates content-first state on an object with no conversion
    pass."""
    page = await create_page(session, llm, project="p", title="n",
                             content="# Title\n\nA paragraph.\n")
    blocks = await _blocks_of(session, page.id)
    assert [b["type"] for b in blocks] == ["heading", "paragraph"]


@pytest.mark.asyncio
async def test_the_stored_content_is_the_serialiser_output(session, llm):
    """`content` is regenerated rather than stored verbatim, which is what
    keeps a page block-first and means no conversion is ever owed."""
    page = await create_page(session, llm, project="p", title="n",
                             content="#   Title\n")
    row = await _page_row(session, page.id)
    assert row["content"] == "# Title\n"


@pytest.mark.asyncio
async def test_siblings_are_appended_in_dense_order(session, llm):
    a = await create_page(session, llm, project="p", title="a")
    b = await create_page(session, llm, project="p", title="b")
    assert [p.order_index for p in (a, b)] == [0, 1]


@pytest.mark.asyncio
async def test_an_empty_page_has_a_hash_to_precondition_against(session, llm):
    """NOT NULL with the create route writing compute_content_hash(''): a NULL
    would leave the first `expected_hash` a client sends nothing to compare
    against."""
    page = await create_page(session, llm, project="p", title="n")
    row = await _page_row(session, page.id)
    assert row["content"] == ""
    assert row["content_hash"] == compute_content_hash("")


@pytest.mark.asyncio
async def test_the_list_excludes_trashed_pages_and_content(session, llm):
    kept = await create_page(session, llm, project="p", title="kept")
    trashed = await create_page(session, llm, project="p", title="trashed")
    await session.execute(
        text("UPDATE pages SET deleted_at = now() WHERE id = CAST(:id AS uuid)"),
        {"id": str(trashed.id)},
    )
    rows = await list_pages(session, "p")
    assert [r["title"] for r in rows] == ["kept"]
    assert str(rows[0]["id"]) == str(kept.id)
    assert all("content" not in r for r in rows)


@pytest.mark.asyncio
async def test_the_keyed_read_serves_blocks_and_withholds_content(session, llm):
    page = await create_page(session, llm, project="p", title="n",
                             content="# T\n\nbody\n")
    bare = await get_page(session, str(page.id))
    assert bare.content is None
    assert [b["type"] for b in bare.blocks] == ["heading", "paragraph"]
    full = await get_page(session, str(page.id), include_content=True)
    assert full.content == "# T\n\nbody\n"


@pytest.mark.asyncio
async def test_the_keyed_read_refuses_a_trashed_page(session, llm):
    page = await create_page(session, llm, project="p", title="n")
    await session.execute(
        text("UPDATE pages SET deleted_at = now() WHERE id = CAST(:id AS uuid)"),
        {"id": str(page.id)},
    )
    with pytest.raises(PageTargetUnresolved):
        await get_page(session, str(page.id))


@pytest.mark.asyncio
async def test_a_page_embeds_into_the_page_partition(session, llm):
    """Sharing `block_embeddings__<slug>` would put page vectors in an index
    whose owner filter runs after the scan."""
    from app.services.embedder_registry import child_table

    page = await create_page(session, llm, project="p", title="n",
                             content="# T\n\nbody\n")
    table = child_table("page_embeddings", FINGERPRINT)
    count = (
        await session.execute(
            text(
                f"SELECT count(*) FROM {table} e JOIN blocks b ON b.id = e.block_id "
                "WHERE b.page_id = CAST(:id AS uuid)"
            ),
            {"id": str(page.id)},
        )
    ).scalar_one()
    assert count == 2
    shared = child_table("block_embeddings", FINGERPRINT)
    leaked = (
        await session.execute(
            text(
                f"SELECT count(*) FROM {shared} e JOIN blocks b ON b.id = e.block_id "
                "WHERE b.page_id = CAST(:id AS uuid)"
            ),
            {"id": str(page.id)},
        )
    ).scalar_one()
    assert leaked == 0


@pytest.mark.asyncio
async def test_after_id_inserts_between_its_siblings(session, llm):
    a = await create_page(session, llm, project="p", title="a")
    c = await create_page(session, llm, project="p", title="c")
    b = await create_page(session, llm, project="p", title="b",
                          after_id=str(a.id))
    rows = await list_pages(session, "p")
    assert [r["title"] for r in rows] == ["a", "b", "c"]
    assert b.order_index == 1
    assert [r["order_index"] for r in rows] == [0, 1, 2]
    assert str(c.id) == str(rows[2]["id"])
