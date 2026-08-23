import pytest
from sqlalchemy import text

from app.services.document_door import (
    DocumentTooLarge, MAX_BLOCKS, MAX_CONTENT_CHARS, put_document,
)

# `parse_fingerprint` requires `model_id|dims`; the stub reports 3-dim
# vectors, so the fingerprint must carry that dims suffix or
# `embedder_registry.register` raises before any partition exists.
FINGERPRINT = "test-fp-doc-door|3"


class StubEmbedder:
    """One fixed direction per text, under one fingerprint."""

    def __init__(self, fingerprint: str = FINGERPRINT):
        self.fingerprint = fingerprint
        self.batches: list[list[str]] = []

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        self.batches.append(list(texts))
        return ([[1.0, 0.0, 0.0] for _ in texts], self.fingerprint)

    async def embed(self, value: str):
        return [1.0, 0.0, 0.0], self.fingerprint

    def llm_fingerprint(self) -> str:
        # `resolve_read_fingerprint` calls this bare (pure, session-less) to
        # learn what the embedder *would* produce, before trusting any data.
        return self.fingerprint


DOC = "# Title\n\nFirst para.\n\n## Section\n\nSecond para.\n"


@pytest.fixture(autouse=True)
def _forget_probe_fingerprint():
    """`EmbedderRegistry` caches known fingerprints process-wide, but each
    test's DB writes roll back at teardown. Without forgetting, a later test
    would skip re-registering a fingerprint whose child table no longer
    exists in its fresh transaction."""
    from app.services.embedder_registry import embedder_registry

    embedder_registry.forget(FINGERPRINT)
    yield
    embedder_registry.forget(FINGERPRINT)


@pytest.mark.asyncio
async def test_put_files_and_embeds_every_block(session):
    llm = StubEmbedder()
    result = await put_document(
        session, llm, project="p", uri="docs/a.md", content=DOC,
    )
    assert result.outcome == "created"
    assert result.blocks_filed > 0
    assert result.blocks_embedded == result.blocks_filed


@pytest.mark.asyncio
async def test_refiling_identical_content_is_unchanged(session):
    llm = StubEmbedder()
    await put_document(session, llm, project="p", uri="docs/a.md", content=DOC)
    again = await put_document(
        session, llm, project="p", uri="docs/a.md", content=DOC,
    )
    assert again.outcome == "unchanged"
    assert again.blocks_filed == 0
    # Every block from the first filing is already embedded, so a clean
    # re-push — nothing deleted, nothing broken — must find no gap to
    # repair. Without this the None-vs-zero and the gap-scoping logic could
    # both silently over-report.
    assert again.blocks_embedded == 0


@pytest.mark.asyncio
async def test_unchanged_repush_embeds_blocks_that_lack_a_vector(session):
    """The repair path: an embed that failed post-commit must be fixable by
    pushing the same file again, which files nothing.

    Deletes a STRICT SUBSET of one document's vectors (never the whole
    partition) so "blocks lacking a vector" and "every block of the
    document" cannot coincide, and files a second, fully-embedded document
    first so an unscoped query — "any block anywhere lacking a vector" —
    would also fail this assertion by picking up the wrong document's rows.
    """
    llm = StubEmbedder()
    first = await put_document(
        session, llm, project="p", uri="docs/a.md", content=DOC,
    )
    other = await put_document(
        session, llm, project="p", uri="docs/other.md", content=DOC,
    )
    assert other.blocks_embedded == other.blocks_filed

    from app.services.block_embeddings import PARENT_TABLE
    from app.services.embedder_registry import child_table

    block_ids = (await session.execute(
        text(
            "SELECT CAST(id AS text) AS id FROM blocks "
            "WHERE document_id = CAST(:document_id AS uuid) ORDER BY id"
        ),
        {"document_id": first.document_id},
    )).scalars().all()
    assert len(block_ids) == first.blocks_filed
    assert len(block_ids) > 1, "need more than one block for a strict subset"
    stale = block_ids[:-1]  # leave the last block's vector intact

    table = child_table(PARENT_TABLE, FINGERPRINT)
    await session.execute(
        text(f"DELETE FROM {table} WHERE block_id = ANY(CAST(:ids AS uuid[]))"),
        {"ids": stale},
    )
    repair = await put_document(
        session, llm, project="p", uri="docs/a.md", content=DOC,
    )
    assert repair.outcome == "unchanged"
    assert repair.blocks_filed == 0
    assert repair.blocks_embedded == len(stale)


@pytest.mark.asyncio
async def test_refile_without_a_title_does_not_null_the_stored_one(session):
    llm = StubEmbedder()
    await put_document(
        session, llm, project="p", uri="docs/a.md", content=DOC, title="Kept",
    )
    await put_document(
        session, llm, project="p", uri="docs/a.md", content=DOC + "\nmore\n",
    )
    row = (await session.execute(
        text("SELECT title FROM documents WHERE project='p' AND uri='docs/a.md'")
    )).scalar_one()
    assert row == "Kept"


@pytest.mark.asyncio
async def test_title_falls_back_to_the_first_heading(session):
    llm = StubEmbedder()
    await put_document(session, llm, project="p", uri="docs/b.md", content=DOC)
    row = (await session.execute(
        text("SELECT title FROM documents WHERE project='p' AND uri='docs/b.md'")
    )).scalar_one()
    assert row == "Title"


@pytest.mark.asyncio
async def test_content_over_the_char_bound_is_refused(session):
    llm = StubEmbedder()
    with pytest.raises(DocumentTooLarge) as excinfo:
        await put_document(
            session, llm, project="p", uri="docs/big.md",
            content="x" * (MAX_CONTENT_CHARS + 1),
        )
    assert str(MAX_CONTENT_CHARS) in str(excinfo.value)


@pytest.mark.asyncio
async def test_block_count_over_the_bound_is_refused(session):
    llm = StubEmbedder()
    with pytest.raises(DocumentTooLarge) as excinfo:
        await put_document(
            session, llm, project="p", uri="docs/many.md",
            content="\n\n".join(f"para {i}" for i in range(MAX_BLOCKS + 1)),
        )
    assert "blocks" in str(excinfo.value)


@pytest.mark.asyncio
async def test_block_count_refusal_leaves_no_document_row(session):
    """A refusal must leave the document exactly as it was: `ingest_document`
    releases its own SAVEPOINT before returning, so without a SAVEPOINT of
    `put_document`'s own around the filing and the bound check, the document
    row, its blocks and its `document_filed` event would all still be
    staged in the caller's session for whatever commits it next — an
    oversized, unembedded document masquerading as a refusal."""
    llm = StubEmbedder()
    with pytest.raises(DocumentTooLarge):
        await put_document(
            session, llm, project="p", uri="docs/many.md",
            content="\n\n".join(f"para {i}" for i in range(MAX_BLOCKS + 1)),
        )
    row = (await session.execute(
        text("SELECT id FROM documents WHERE project='p' AND uri='docs/many.md'")
    )).first()
    assert row is None


@pytest.mark.asyncio
async def test_embed_blocks_returning_none_reports_zero_embedded(session, monkeypatch):
    """`embed_blocks` returning `None` means nothing was embedded and no
    fingerprint was measured; `put_document` must report that as zero, not
    as a successful embed of every filed block."""
    import app.services.document_door as document_door

    async def _embeds_nothing(session, llm, *, block_ids, **kwargs):
        return None

    monkeypatch.setattr(document_door, "embed_blocks", _embeds_nothing)

    llm = StubEmbedder()
    result = await put_document(
        session, llm, project="p", uri="docs/none.md", content=DOC,
    )
    assert result.outcome == "created"
    assert result.blocks_filed > 0
    assert result.blocks_embedded == 0
