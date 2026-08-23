import pytest
from sqlalchemy import text

from app.services.block_embedding_refresh import refresh_block_embeddings
from tests.test_document_door import DOC, FINGERPRINT, StubEmbedder

# A second live fingerprint under the same model_id as FINGERPRINT, dims=4
# instead of 3 — the rotation scenario the round-2 review's headline case
# turns on: two live siblings sharing one model_id, one holding stale data,
# one being what the active embedder now actually produces.
ROTATED_FINGERPRINT = "test-fp-doc-door|4"


class _RotatedDimsEmbedder(StubEmbedder):
    """Same shape as `StubEmbedder`, but produces vectors matching its own
    declared dims. `StubEmbedder` hardcodes 3-dim vectors regardless of the
    fingerprint passed to its constructor, which is fine when every test
    fingerprint shares dims=3 but breaks a real "same model_id, different
    dims" rotation, which is exactly the case under test below."""

    def __init__(self, fingerprint: str, dims: int):
        super().__init__(fingerprint)
        self._dims = dims

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        self.batches.append(list(texts))
        return ([[1.0] * self._dims for _ in texts], self.fingerprint)

    async def embed(self, value: str):
        return [1.0] * self._dims, self.fingerprint


@pytest.fixture(autouse=True)
def _forget_probe_fingerprints():
    """`EmbedderRegistry` caches known fingerprints process-wide, but each
    test's DB writes roll back at teardown. Without forgetting, a later test
    would skip re-registering a fingerprint whose child table no longer
    exists in its fresh transaction."""
    from app.services.embedder_registry import embedder_registry

    embedder_registry.forget(FINGERPRINT)
    embedder_registry.forget(ROTATED_FINGERPRINT)
    yield
    embedder_registry.forget(FINGERPRINT)
    embedder_registry.forget(ROTATED_FINGERPRINT)


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
    assert outcome.fingerprint is None, "batch=0 must short-circuit before spending the probe embed call"


@pytest.mark.asyncio
async def test_refresh_finds_nothing_with_no_documents(session):
    """A real embed call always yields a real fingerprint (unlike a data
    probe, this cannot come back unconfirmed), so the probe still resolves
    on a completely empty install — there is simply nothing for the anti-join
    to find missing."""
    llm = StubEmbedder()
    outcome = await refresh_block_embeddings(session, llm, batch=100)
    assert outcome.embedded == 0
    assert outcome.fingerprint == FINGERPRINT
    assert outcome.converged is True


@pytest.mark.asyncio
async def test_refresh_raises_when_the_embed_lands_under_a_different_fingerprint(session, monkeypatch):
    """I3: a resolved-vs-actual fingerprint mismatch should now only be
    reachable if the active embedder's configuration changes between the
    probe call and the batch embed call within one run — a monkeypatched
    probe stands in for that race here. Refusing loudly is correct: silently
    absorbing it would report a batch as converged under a fingerprint this
    run never actually verified."""
    from app.services.document_door import put_document
    from app.services.embedder_registry import child_table, embedder_registry
    from app.services.block_embeddings import PARENT_TABLE

    llm = StubEmbedder()
    await put_document(session, llm, project="p", uri="docs/mismatch.md", content=DOC)
    child = child_table(PARENT_TABLE, FINGERPRINT)
    await session.execute(text(f"DELETE FROM {child}"))
    await session.commit()

    lie_fingerprint = "a-fingerprint-nothing-writes-under|3"

    async def _resolve_to_a_lie(llm):
        return lie_fingerprint

    monkeypatch.setattr(
        "app.services.block_embedding_refresh.resolve_active_fingerprint",
        _resolve_to_a_lie,
    )

    try:
        with pytest.raises(RuntimeError, match="probe resolved fingerprint"):
            await refresh_block_embeddings(session, llm, batch=100)
    finally:
        embedder_registry.forget(lie_fingerprint)


@pytest.mark.asyncio
async def test_refresh_targets_the_rotated_fingerprint_not_the_stale_full_one(session):
    """The round-2 review's headline case: a dims rotation on one model_id
    leaves `F_old` holding every existing block; the active embedder now
    reports `F_new`, whose own block partition is still empty because no
    document has been filed since the rotation. The sweep must resolve to
    `F_new` (matching what retrieval would resolve for a real query) and
    treat every existing block as missing there — never fall back to F_old
    just because F_old's own partition happens to already be complete."""
    from app.services.document_door import put_document
    from app.services.embedder_registry import child_table
    from app.services.block_embeddings import PARENT_TABLE

    old_llm = StubEmbedder(FINGERPRINT)
    filed = await put_document(session, old_llm, project="p", uri="docs/rotated.md", content=DOC)
    assert filed.blocks_filed > 0
    assert filed.blocks_embedded == filed.blocks_filed

    old_child = child_table(PARENT_TABLE, FINGERPRINT)
    old_count_before = (
        await session.execute(text(f"SELECT COUNT(*) FROM {old_child}"))
    ).scalar_one()
    assert old_count_before == filed.blocks_filed

    # The rotation: the active embedder now reports a different fingerprint
    # under the same model_id. No document has been filed under it yet, so
    # its block partition does not exist until this sweep (or a future
    # filing) creates it.
    new_llm = _RotatedDimsEmbedder(ROTATED_FINGERPRINT, dims=4)

    outcome = await refresh_block_embeddings(session, new_llm, batch=100)

    assert outcome.fingerprint == ROTATED_FINGERPRINT
    assert outcome.embedded == filed.blocks_filed, (
        "every existing block is missing under the rotated fingerprint and "
        "must be re-embedded there, not silently skipped because the OLD "
        "partition happens to already be complete"
    )
    assert outcome.converged is True

    new_child = child_table(PARENT_TABLE, ROTATED_FINGERPRINT)
    new_count = (
        await session.execute(text(f"SELECT COUNT(*) FROM {new_child}"))
    ).scalar_one()
    assert new_count == filed.blocks_filed

    # The stranded old vectors are untouched, not deleted or migrated.
    old_count_after = (
        await session.execute(text(f"SELECT COUNT(*) FROM {old_child}"))
    ).scalar_one()
    assert old_count_after == old_count_before

    # A second run under the rotated embedder finds nothing left to do.
    again = await refresh_block_embeddings(session, new_llm, batch=100)
    assert again.embedded == 0
    assert again.fingerprint == ROTATED_FINGERPRINT
