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
    # Pin the precondition: if `DOC` ever parsed to zero blocks, the whole
    # test below would pass green with nothing actually exercised.
    assert filed.blocks_filed > 0
    child = child_table(PARENT_TABLE, FINGERPRINT)
    await session.execute(text(f"DELETE FROM {child}"))
    await session.commit()

    outcome = await refresh_block_embeddings(session, llm, batch=100)
    assert outcome.embedded == filed.blocks_filed
    assert outcome.fingerprint == FINGERPRINT
    assert outcome.converged is True

    again = await refresh_block_embeddings(session, llm, batch=100)
    assert again.embedded == 0, "a second pass must find nothing left to do"
    assert again.converged is True


@pytest.mark.asyncio
async def test_refresh_drains_a_backlog_larger_than_one_batch(session):
    """The multi-run drain is the entire reason the `batch` knob exists: a
    corpus bigger than one run's budget must converge over several ticks,
    each pass strictly shrinking the backlog, never re-doing settled work."""
    from app.services.document_door import put_document
    from app.services.embedder_registry import child_table
    from app.services.block_embeddings import PARENT_TABLE

    llm = StubEmbedder()
    filed = await put_document(session, llm, project="p", uri="docs/multi.md", content=DOC)
    assert filed.blocks_filed > 1, "need a real multi-block backlog for this test to mean anything"
    child = child_table(PARENT_TABLE, FINGERPRINT)
    await session.execute(text(f"DELETE FROM {child}"))
    await session.commit()

    total_embedded = 0
    runs = 0
    while True:
        outcome = await refresh_block_embeddings(session, llm, batch=1)
        if outcome.embedded == 0:
            assert outcome.converged is True
            break
        assert outcome.embedded == 1
        total_embedded += outcome.embedded
        runs += 1
        assert runs <= filed.blocks_filed, "drain did not converge within the expected number of runs"

    assert total_embedded == filed.blocks_filed
    assert runs == filed.blocks_filed, "batch=1 must take exactly one run per block"


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

    outcome = await refresh_block_embeddings(session, llm, batch=0)
    assert outcome.embedded == 0
    assert outcome.fingerprint is None


@pytest.mark.asyncio
async def test_refresh_finds_nothing_with_no_documents(session):
    llm = StubEmbedder()
    outcome = await refresh_block_embeddings(session, llm, batch=100)
    assert outcome.embedded == 0
    assert outcome.fingerprint is None
    assert outcome.converged is True


@pytest.mark.asyncio
async def test_refresh_raises_when_the_embed_lands_under_a_different_fingerprint(session, monkeypatch):
    """I3: a resolved-vs-actual fingerprint mismatch should be unreachable
    after the block-aware probe (I2's fix in app/repositories/vector.py).
    If it ever occurs anyway — a monkeypatched resolver stands in for that
    "anyway" here — refusing loudly is correct: silently absorbing it would
    re-spend up to `batch` embed calls against a paid embedder every tick,
    forever, with only a log line to show for it."""
    from app.services.document_door import put_document
    from app.services.embedder_registry import child_table, embedder_registry
    from app.services.block_embeddings import PARENT_TABLE

    llm = StubEmbedder()
    await put_document(session, llm, project="p", uri="docs/mismatch.md", content=DOC)
    child = child_table(PARENT_TABLE, FINGERPRINT)
    await session.execute(text(f"DELETE FROM {child}"))
    await session.commit()

    lie_fingerprint = "a-fingerprint-nothing-writes-under|3"

    async def _resolve_to_a_lie(session, llm):
        return lie_fingerprint

    monkeypatch.setattr(
        "app.services.block_embedding_refresh.resolve_read_fingerprint",
        _resolve_to_a_lie,
    )

    try:
        with pytest.raises(RuntimeError, match="resolved fingerprint"):
            await refresh_block_embeddings(session, llm, batch=100)
    finally:
        embedder_registry.forget(lie_fingerprint)
