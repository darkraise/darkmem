import pytest
from sqlalchemy import text

from app.services.block_embedding_refresh import refresh_block_embeddings
from tests.test_document_door import DOC, FINGERPRINT, StubEmbedder


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
async def test_refresh_embeds_blocks_that_have_no_vector(session):
    from app.services.document_door import put_document
    from app.services.embedder_registry import child_table
    from app.services.block_embeddings import PARENT_TABLE

    llm = StubEmbedder()
    filed = await put_document(session, llm, project="p", uri="docs/a.md", content=DOC)
    child = child_table(PARENT_TABLE, FINGERPRINT)
    await session.execute(text(f"DELETE FROM {child}"))
    await session.commit()

    embedded = await refresh_block_embeddings(session, llm, batch=100)
    assert embedded == filed.blocks_filed

    again = await refresh_block_embeddings(session, llm, batch=100)
    assert again == 0, "a second pass must find nothing left to do"


@pytest.mark.asyncio
async def test_refresh_batch_zero_disables_the_sweep(session):
    from app.services.document_door import put_document
    from app.services.embedder_registry import child_table
    from app.services.block_embeddings import PARENT_TABLE

    llm = StubEmbedder()
    await put_document(session, llm, project="p", uri="docs/b.md", content=DOC)
    child = child_table(PARENT_TABLE, FINGERPRINT)
    await session.execute(text(f"DELETE FROM {child}"))
    await session.commit()

    embedded = await refresh_block_embeddings(session, llm, batch=0)
    assert embedded == 0


@pytest.mark.asyncio
async def test_refresh_finds_nothing_with_no_documents(session):
    llm = StubEmbedder()
    embedded = await refresh_block_embeddings(session, llm, batch=100)
    assert embedded == 0
