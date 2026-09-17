"""Pages must not reach documents (owner requirement, doc 05 pages epic).

Every one of the six channels below excludes a page block from a document
surface because `blocks.document_id` is NULL for a page-owned block, never
because a filter tests `page_id` or a similar label. That distinction is the
whole point of this file: a future refactor that replaces a NULL-driven
`INNER JOIN` with a `LEFT JOIN` (or wraps a comparison in `COALESCE`) can
silently reopen the channel, because nothing about the returned shape looks
wrong -- there is simply one more row. Each test below breaks exactly the
predicate its own channel relies on and confirms the result changes.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import text

from app.services.block_embedding_refresh import refresh_block_embeddings
from app.services.block_embeddings import PAGE_PARENT_TABLE, PARENT_TABLE, ensure_partition
from app.services.document_connections import connections_for_document
from app.services.document_door import document_outline, put_document, search_sections
from app.services.embedder_registry import child_table
from app.services.page_door import create_page

V1 = "/api/v1"

FINGERPRINT = "test-fp-page-doc-isolation|3"

DOC_TEXT = "# Doc Heading\n\nDocument paragraph darkmem-doc-sentinel text.\n"
PAGE_TEXT = "# Page Heading\n\nPage paragraph darkmem-page-sentinel text.\n"


class StubEmbedder:
    """One fixed direction for every text, under one fingerprint -- the same
    shape `test_page_door.py` and `test_document_door.py` each define; kept
    local so this file owns one fingerprint shared by both a document and a
    page embed, which is what lets the leak helper below plant a page
    vector directly inside the document partition."""

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


@pytest.fixture(autouse=True)
def _forget_probe_fingerprint():
    from app.services.embedder_registry import embedder_registry

    embedder_registry.forget(FINGERPRINT)
    yield
    embedder_registry.forget(FINGERPRINT)


@pytest.fixture
def llm():
    return StubEmbedder()


@pytest.fixture
def stub_llm(llm):
    """Point the app at the same embedder the fixture below embeds with, so
    a route call and the direct service calls that built the fixture agree
    on one fingerprint."""
    from app.main import app

    previous = getattr(app.state, "llm", None)
    app.state.llm = llm
    yield llm
    app.state.llm = previous


@dataclass
class Isolation:
    project: str
    document_id: str
    document_block_ids: list[str]
    page_id: str
    page_block_ids: list[str]


async def _owned_blocks(session, *, document_id: str | None = None, page_id: str | None = None):
    if document_id is not None:
        rows = await session.execute(
            text(
                "SELECT CAST(id AS text) AS id, text, type FROM blocks "
                "WHERE document_id = CAST(:owner AS uuid) ORDER BY order_index"
            ),
            {"owner": document_id},
        )
    else:
        rows = await session.execute(
            text(
                "SELECT CAST(id AS text) AS id, text, type FROM blocks "
                "WHERE page_id = CAST(:owner AS uuid) ORDER BY order_index"
            ),
            {"owner": page_id},
        )
    return [dict(r) for r in rows.mappings().all()]


async def _leak_page_block_into_document_partition(session, llm, block_id: str) -> None:
    """Plant a copy of a page block's vector inside the document family's
    own partition -- the scenario `search_blocks` and `document_connections`
    guard against regardless of how such a row would get there. The block
    row itself is untouched: `blocks.document_id` for `block_id` stays NULL,
    which is exactly the NULL semantics each channel is pinned on."""
    fingerprint = llm.llm_fingerprint()
    await ensure_partition(session, fingerprint, parent=PARENT_TABLE)
    table = child_table(PARENT_TABLE, fingerprint)
    await session.execute(
        text(
            f"INSERT INTO {table} (block_id, fingerprint, embedding) "
            "VALUES (CAST(:bid AS uuid), CAST(:fp AS text), CAST(:embedding AS vector)) "
            "ON CONFLICT (block_id, fingerprint) DO NOTHING"
        ),
        {"bid": block_id, "fp": fingerprint, "embedding": "[1,0,0]"},
    )


@pytest_asyncio.fixture
async def isolation(session, llm, stub_llm) -> Isolation:
    """One project holding one document with blocks and one page with
    blocks, filed through the doors that ship. The document embeds inline; the
    page's blocks are left for the sweep, as a page create leaves them."""
    project = "page-doc-isolation"
    filed = await put_document(
        session, llm, project=project, uri="docs/isolation-a.md", content=DOC_TEXT,
    )
    doc_blocks = await _owned_blocks(session, document_id=filed.document_id)
    assert doc_blocks, "fixture precondition: the document must parse to blocks"
    assert filed.blocks_embedded == len(doc_blocks)

    page = await create_page(session, llm, project=project, title="Notes", content=PAGE_TEXT)
    page_blocks = await _owned_blocks(session, page_id=str(page.id))
    assert page_blocks, "fixture precondition: the page must parse to blocks"

    return Isolation(
        project=project,
        document_id=filed.document_id,
        document_block_ids=[b["id"] for b in doc_blocks],
        page_id=str(page.id),
        page_block_ids=[b["id"] for b in page_blocks],
    )


@pytest.mark.asyncio
async def test_a_page_is_absent_from_document_search(session, llm, isolation):
    """`block_embeddings.py:344` inner-joins documents, so a page row drops.
    Pinned because that is NULL semantics, not a written filter."""
    page_heading_id = isolation.page_block_ids[0]
    await _leak_page_block_into_document_partition(session, llm, page_heading_id)

    hits = await search_sections(
        session, llm, query="sentinel", project=isolation.project, limit=50,
    )
    assert hits, "the document's own blocks must still be found"
    assert page_heading_id not in {h.block_id for h in hits}
    assert "Page Heading" not in {h.text for h in hits}


@pytest.mark.asyncio
async def test_a_page_is_absent_from_document_connections(session, llm, isolation):
    """`document_connections.py:184` filters `tb.document_id <> :document_id`,
    and `NULL <> x` is never true."""
    # A second real document is required: `resolve_shared_fingerprint`
    # refuses to resolve a fingerprint at all unless the project already
    # holds another document's block under it, so without this the query
    # under test would never run.
    other = await put_document(
        session, llm, project=isolation.project, uri="docs/isolation-b.md",
        content="# Other Heading\n\nOther paragraph darkmem-other-sentinel text.\n",
    )
    assert other.blocks_embedded

    page_heading_id = isolation.page_block_ids[0]
    await _leak_page_block_into_document_partition(session, llm, page_heading_id)

    result = await connections_for_document(session, document_id=isolation.document_id)
    assert result.embedded is True
    assert result.items, "the real second document must still surface as a connection"
    other_ids = {item.other_block_id for item in result.items}
    other_texts = {item.other_block_text for item in result.items}
    assert page_heading_id not in other_ids
    assert "Page paragraph darkmem-page-sentinel text." not in other_texts


@pytest.mark.asyncio
async def test_a_page_is_absent_from_a_document_outline(session, llm, isolation):
    """`document_outline`'s query filters `document_id = :document_id`; a
    page's heading has `document_id` NULL, the same NULL-semantics reliance
    as the search and connections channels, this time direct against
    `blocks` rather than through a partition."""
    nodes = await document_outline(session, document_id=isolation.document_id)
    assert nodes, "the document's own heading must still appear"
    assert isolation.page_block_ids[0] not in {n.block_id for n in nodes}
    assert "Page Heading" not in {n.text for n in nodes}


@pytest.mark.asyncio
async def test_a_page_block_is_not_addressable_through_a_document_route(
    session, llm, isolation, client, auth_headers,
):
    """`_assert_block_is_in` at routes/documents.py:993-1002 404s it.

    Called directly, not only through the route: `block_verbs._owner_of`
    and `_mutate`'s own `meta is None` check would independently 404 this
    same request further downstream, so a break confined to this route-level
    guard alone would not surface through the full HTTP path. Calling the
    exact cited function is what isolates its own contribution; the HTTP
    round trip below confirms the door still 404s end to end.
    """
    from app.api.routes.documents import _assert_block_is_in

    with pytest.raises(HTTPException) as exc_info:
        await _assert_block_is_in(
            session, UUID(isolation.document_id), UUID(isolation.page_block_ids[0]),
        )
    assert exc_info.value.status_code == 404

    response = await client.patch(
        f"{V1}/documents/{isolation.document_id}/blocks/{isolation.page_block_ids[0]}",
        json={"text": "nope"},
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_a_page_block_is_not_claimed_by_the_document_embedding_sweep(
    session, llm, isolation,
):
    """Task 3's predicate. Without it the sweep has no owner predicate at all."""
    outcome = await refresh_block_embeddings(session, llm, batch=1000, page_batch=0)
    assert outcome.embedded == 0
    assert outcome.converged is True

    table = child_table(PARENT_TABLE, llm.llm_fingerprint())
    swept_ids = set((await session.execute(
        text(f"SELECT CAST(block_id AS text) AS id FROM {table}"),
    )).scalars().all())
    assert set(isolation.page_block_ids).isdisjoint(swept_ids)


@pytest.mark.asyncio
async def test_page_vectors_live_in_their_own_partition(session, llm, isolation):
    """The one that matters most: sharing block_embeddings would put page
    vectors in an HNSW index whose owner filter runs after the scan, starving
    document connections of candidates as the notes corpus grows."""
    await refresh_block_embeddings(session, llm, batch=0, page_batch=100)
    fingerprint = llm.llm_fingerprint()
    page_table = child_table(PAGE_PARENT_TABLE, fingerprint)
    document_table = child_table(PARENT_TABLE, fingerprint)

    in_page_partition = set((await session.execute(
        text(f"SELECT CAST(block_id AS text) AS id FROM {page_table}"),
    )).scalars().all())
    in_document_partition = set((await session.execute(
        text(f"SELECT CAST(block_id AS text) AS id FROM {document_table}"),
    )).scalars().all())

    assert set(isolation.page_block_ids) <= in_page_partition
    assert set(isolation.page_block_ids).isdisjoint(in_document_partition)
