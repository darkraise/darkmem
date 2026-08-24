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


class _PoisonEmbedder(StubEmbedder):
    """Rejects any batch containing `poison`, embeds everything else.

    Models the real shape of the hazard: the failure is a property of one
    block's own text, so it takes down whichever chunk that block lands in
    and nothing else.
    """

    def __init__(self, poison: str, fingerprint: str = FINGERPRINT):
        super().__init__(fingerprint)
        self.poison = poison

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        self.batches.append(list(texts))
        if self.poison in texts:
            raise RuntimeError("embedder rejected this input")
        return ([[1.0, 0.0, 0.0] for _ in texts], self.fingerprint)


class _DeadEmbedder(StubEmbedder):
    """Fails every batch. The probe `embed` still works, so the run gets far
    enough to reach the isolation pass — which is the point: an outage must
    not be walked block by block."""

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        self.batches.append(list(texts))
        raise RuntimeError("embedder is down")


async def _unembedded_document(session, llm, uri: str):
    """File `DOC` and drop its vectors, leaving a full backlog to sweep."""
    from app.services.document_door import put_document
    from app.services.embedder_registry import child_table
    from app.services.block_embeddings import PARENT_TABLE

    filed = await put_document(session, llm, project="p", uri=uri, content=DOC)
    assert filed.blocks_filed > 3, (
        "the isolation tests below need a batch longer than _OUTAGE_PROBE"
    )
    await session.execute(text(f"DELETE FROM {child_table(PARENT_TABLE, FINGERPRINT)}"))
    await session.commit()
    return filed


@pytest.mark.asyncio
async def test_one_unembeddable_block_does_not_starve_the_ones_behind_it(session):
    """The batch fetch is `ORDER BY b.id`, so a batch that fails as a batch
    fails identically on every subsequent tick: without isolation, one block
    the embedder rejects means nothing behind it is ever swept, forever. The
    run must retry block-at-a-time, land the rest, and leave only the poison
    row in the backlog."""
    filed = await _unembedded_document(session, StubEmbedder(), "docs/poison.md")

    poison = (await session.execute(
        text("SELECT text FROM blocks ORDER BY id LIMIT 1")
    )).scalar_one()
    llm = _PoisonEmbedder(poison)

    outcome = await refresh_block_embeddings(session, llm, batch=100)

    assert outcome.failed == 1
    assert outcome.embedded == filed.blocks_filed - 1, (
        "every block except the poison one must have been written"
    )
    assert outcome.fingerprint == FINGERPRINT
    assert outcome.converged is False, (
        "a block left unembedded means the backlog is not clear, however "
        "short this run's own fetch came back"
    )

    from app.services.embedder_registry import child_table
    from app.services.block_embeddings import PARENT_TABLE
    written = (await session.execute(
        text(f"SELECT COUNT(*) FROM {child_table(PARENT_TABLE, FINGERPRINT)}")
    )).scalar_one()
    assert written == filed.blocks_filed - 1, "the successes must be committed"


@pytest.mark.asyncio
async def test_a_backlog_of_nothing_but_poison_fails_the_run(session):
    """The residue is loud, not silent. Once the isolable blocks are gone the
    backlog is the poison row alone, nothing can be embedded, and the run
    raises so the failure reaches `job_runs.last_error` rather than reporting
    a converged sweep over a block it never wrote."""
    await _unembedded_document(session, StubEmbedder(), "docs/poison-only.md")

    poison = (await session.execute(
        text("SELECT text FROM blocks ORDER BY id LIMIT 1")
    )).scalar_one()
    llm = _PoisonEmbedder(poison)

    first = await refresh_block_embeddings(session, llm, batch=100)
    assert first.failed == 1

    with pytest.raises(RuntimeError, match="embedder rejected this input"):
        await refresh_block_embeddings(session, llm, batch=100)


@pytest.mark.asyncio
async def test_an_embedder_outage_is_probed_not_walked(session):
    """Isolation exists for a poison row, not for a dead endpoint. An
    embedder that fails everything must be detected after a few attempts and
    re-raised, never retried once per block — that would spend a full batch
    of calls against a down service on every tick."""
    filed = await _unembedded_document(session, StubEmbedder(), "docs/outage.md")

    llm = _DeadEmbedder()
    with pytest.raises(RuntimeError, match="embedder is down"):
        await refresh_block_embeddings(session, llm, batch=100)

    from app.services.block_embedding_refresh import _OUTAGE_PROBE
    assert len(llm.batches) == 1 + _OUTAGE_PROBE, (
        f"expected the failed batch plus {_OUTAGE_PROBE} isolation probes, "
        f"got {len(llm.batches)} embed calls"
    )
    assert len(llm.batches) < 1 + filed.blocks_filed, (
        "the pass must give up before walking the whole batch"
    )
