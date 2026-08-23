from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from app.repositories.fact_sources import FactSourceRepository
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services.block_fact_sources import record_block_source
from app.services.document_door import (
    DocumentTooLarge, MAX_BLOCKS, MAX_CONTENT_CHARS, delete_document, document_blocks,
    put_document, search_sections,
)
from app.services.triple_key import compute_triple_key

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
        # Matches the real `LLMOrchestrator`'s shape (a pure, session-less
        # formatter), kept for interface completeness. Nothing in
        # `document_door`'s own call graph reaches this bare anymore
        # (T-doc-door.6 review, round 4, 2026-08-24): both `put_document`'s
        # `unchanged` repair and `block_embedding_refresh`'s sweep resolve
        # their fingerprint from a real `embed()` call instead
        # (`block_embeddings.resolve_active_fingerprint`), never from this.
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
    assert result.title_applied is True


@pytest.mark.asyncio
async def test_document_blocks_with_an_explicit_empty_list_returns_nothing(session):
    """`block_ids=[]` names zero blocks and must return zero, distinct from
    `block_ids=None` ("no filter", returns the whole document). Not
    reachable through the HTTP route today -- FastAPI reports an absent
    query parameter as `None`, never `[]` -- but this is the in-process
    contract a future caller (e.g. an MCP tool) gets instead."""
    llm = StubEmbedder()
    result = await put_document(session, llm, project="p", uri="docs/a.md", content=DOC)
    assert result.blocks_filed > 0

    rows = await document_blocks(session, document_id=result.document_id, block_ids=[])
    assert rows == []


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
    assert again.title_applied is False


@pytest.mark.asyncio
async def test_unchanged_repush_embeds_blocks_that_lack_a_vector(session):
    """The repair path: an embed that failed post-commit must be fixable by
    pushing the same file again, which files nothing.

    Deletes a STRICT SUBSET of one document's vectors (never the whole
    partition) so "blocks lacking a vector" and "every block of the
    document" cannot coincide. Also deletes exactly one vector belonging to
    a SECOND, otherwise-fully-embedded document: dropping the
    `document_id` predicate from the unembedded-blocks query would then
    over-report by exactly one, failing the exact-count assertion below,
    and that second document's own gap must still be unfixed afterward —
    a's repair push must never reach into `other`'s blocks.
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

    other_block_ids = (await session.execute(
        text(
            "SELECT CAST(id AS text) AS id FROM blocks "
            "WHERE document_id = CAST(:document_id AS uuid) ORDER BY id"
        ),
        {"document_id": other.document_id},
    )).scalars().all()
    other_stale = other_block_ids[0]

    table = child_table(PARENT_TABLE, FINGERPRINT)
    await session.execute(
        text(f"DELETE FROM {table} WHERE block_id = ANY(CAST(:ids AS uuid[]))"),
        {"ids": stale},
    )
    await session.execute(
        text(f"DELETE FROM {table} WHERE block_id = CAST(:id AS uuid)"),
        {"id": other_stale},
    )

    repair = await put_document(
        session, llm, project="p", uri="docs/a.md", content=DOC,
    )
    assert repair.outcome == "unchanged"
    assert repair.blocks_filed == 0
    assert repair.blocks_embedded == len(stale)
    assert repair.title_applied is False

    other_still_missing = (await session.execute(
        text(f"SELECT 1 FROM {table} WHERE block_id = CAST(:id AS uuid)"),
        {"id": other_stale},
    )).first()
    assert other_still_missing is None


@pytest.mark.asyncio
async def test_unchanged_repair_targets_the_rotated_fingerprint_not_the_stale_full_one(session):
    """T-doc-door.6 review (round 3): the sweep's rotation case, reproduced
    for the `unchanged` repair push. A dims rotation on one model_id leaves
    `F_old` holding every existing block; the active embedder now reports
    `F_new`, whose own block partition is empty because no document has
    been re-filed since. Repair-pushing the same content must resolve to
    `F_new` and fill it — resolving from a data probe would find `F_old`
    already complete and report nothing to repair, exactly the "document
    exists and is unfindable" failure this whole door exists to avoid.
    """
    from app.services.block_embeddings import PARENT_TABLE
    from app.services.embedder_registry import child_table, embedder_registry

    old_llm = StubEmbedder(FINGERPRINT)
    filed = await put_document(
        session, old_llm, project="p", uri="docs/rotate-repair.md", content=DOC,
    )
    assert filed.blocks_filed > 0
    assert filed.blocks_embedded == filed.blocks_filed

    rotated_fingerprint = "test-fp-doc-door|4"

    class _RotatedDimsEmbedder(StubEmbedder):
        """`StubEmbedder` hardcodes 3-dim vectors regardless of the
        fingerprint passed to its constructor, which breaks a real "same
        model_id, different dims" rotation — this produces vectors matching
        its own declared dims instead."""

        def __init__(self, fingerprint: str, dims: int):
            super().__init__(fingerprint)
            self._dims = dims

        async def embed_batch_chunked(self, texts, chunk_size, concurrency):
            self.batches.append(list(texts))
            return ([[1.0] * self._dims for _ in texts], self.fingerprint)

        async def embed(self, value: str):
            return [1.0] * self._dims, self.fingerprint

    embedder_registry.forget(rotated_fingerprint)
    try:
        new_llm = _RotatedDimsEmbedder(rotated_fingerprint, dims=4)

        repair = await put_document(
            session, new_llm, project="p", uri="docs/rotate-repair.md", content=DOC,
        )

        assert repair.outcome == "unchanged"
        assert repair.blocks_filed == 0
        assert repair.blocks_embedded == filed.blocks_filed, (
            "every existing block is missing under the rotated fingerprint "
            "and must be repaired there, not silently skipped because the "
            "OLD partition happens to already be complete"
        )

        new_child = child_table(PARENT_TABLE, rotated_fingerprint)
        new_count = (
            await session.execute(text(f"SELECT COUNT(*) FROM {new_child}"))
        ).scalar_one()
        assert new_count == filed.blocks_filed

        old_child = child_table(PARENT_TABLE, FINGERPRINT)
        old_count = (
            await session.execute(text(f"SELECT COUNT(*) FROM {old_child}"))
        ).scalar_one()
        assert old_count == filed.blocks_filed, "the stranded old vectors are untouched"
    finally:
        embedder_registry.forget(rotated_fingerprint)


@pytest.mark.asyncio
async def test_unchanged_repair_raises_when_the_embed_lands_under_a_different_fingerprint(
    session, monkeypatch,
):
    """T-doc-door.6 review (round 4): mirrors `block_embedding_refresh`'s own
    mismatch guard. `fingerprint` (used to find the gaps) and
    `result.fingerprint` (what the batch embed call actually wrote under)
    are two separate real embed calls; if the active embedder's
    configuration changes between them within one request, the repair count
    this call reports would be computed against a partition it never
    verified the write actually landed in. Refusing loudly is correct."""
    llm = StubEmbedder()
    await put_document(session, llm, project="p", uri="docs/mismatch.md", content=DOC)

    from app.services.block_embeddings import PARENT_TABLE
    from app.services.embedder_registry import child_table, embedder_registry

    child = child_table(PARENT_TABLE, FINGERPRINT)
    await session.execute(text(f"DELETE FROM {child}"))
    await session.commit()

    lie_fingerprint = "a-fingerprint-nothing-writes-under|3"

    async def _resolve_to_a_lie(llm):
        return lie_fingerprint

    monkeypatch.setattr(
        "app.services.document_door.resolve_active_fingerprint", _resolve_to_a_lie,
    )

    try:
        with pytest.raises(RuntimeError, match="resolved fingerprint"):
            await put_document(
                session, llm, project="p", uri="docs/mismatch.md", content=DOC,
            )
    finally:
        embedder_registry.forget(lie_fingerprint)


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


@pytest.mark.asyncio
async def test_block_count_refusal_on_reupload_leaves_prior_blocks_intact(session):
    """The update path of the I1 fix: `file_document`'s strip-before-rewrite
    deletes an existing document's prior blocks before parsing the new
    content, all inside the SAVEPOINT `put_document` wraps around the
    filing and the bound check. An over-bound re-push must roll that strip
    back too, or a refusal would silently delete a document's working
    content while claiming nothing changed."""
    llm = StubEmbedder()
    first = await put_document(
        session, llm, project="p", uri="docs/a.md", content=DOC,
    )
    prior_block_ids = set((await session.execute(
        text(
            "SELECT CAST(id AS text) AS id FROM blocks "
            "WHERE document_id = CAST(:document_id AS uuid)"
        ),
        {"document_id": first.document_id},
    )).scalars().all())
    assert prior_block_ids

    with pytest.raises(DocumentTooLarge):
        await put_document(
            session, llm, project="p", uri="docs/a.md",
            content="\n\n".join(f"para {i}" for i in range(MAX_BLOCKS + 1)),
        )

    row = (await session.execute(
        text("SELECT id FROM documents WHERE project='p' AND uri='docs/a.md'")
    )).scalar_one()
    assert str(row) == first.document_id

    surviving_block_ids = set((await session.execute(
        text(
            "SELECT CAST(id AS text) AS id FROM blocks "
            "WHERE document_id = CAST(:document_id AS uuid)"
        ),
        {"document_id": first.document_id},
    )).scalars().all())
    assert surviving_block_ids == prior_block_ids


# ── delete_document closes the provenance window (fix round 2) ────────


async def _fact(session, *, subject: str = "postgres") -> str:
    row = await KnowledgeTripleRepository(session).insert_open(
        triple_key=compute_triple_key("p", subject, "RUNS_ON", "linux"),
        subject_name=subject,
        object_name="linux",
        rel_type="RUNS_ON",
        fact=f"{subject} runs on linux",
        reference_time=datetime(2026, 8, 16, tzinfo=timezone.utc),
        project="p",
    )
    return row["id"]


async def _blocks_of(session, document_id: str) -> list[str]:
    rows = (await session.execute(
        text(
            "SELECT CAST(id AS text) AS id FROM blocks "
            "WHERE document_id = CAST(:document_id AS uuid) ORDER BY id"
        ),
        {"document_id": document_id},
    )).scalars().all()
    return list(rows)


async def _sources_changed_count(session, fact_id: str) -> int:
    return (await session.execute(
        text(
            "SELECT count(*) FROM events WHERE event_type = 'sources_changed' "
            "AND object_type = 'fact' AND object_id = CAST(:f AS uuid)"
        ),
        {"f": fact_id},
    )).scalar_one()


@pytest.mark.asyncio
async def test_delete_with_a_remaining_source_enqueues_but_does_not_expire(session):
    """A fact that loses one of several sources gets an event and no expiry:
    it is still corroborated, just less so, and the ladder decides what that
    is worth on its own recompute -- not this function."""
    llm = StubEmbedder()
    fact_id = await _fact(session)
    first = await put_document(session, llm, project="p", uri="docs/first.md", content=DOC)
    second = await put_document(session, llm, project="p", uri="docs/second.md", content=DOC)
    first_blocks = await _blocks_of(session, first.document_id)
    second_blocks = await _blocks_of(session, second.document_id)
    await record_block_source(session, fact_id=fact_id, block_id=first_blocks[0])
    await record_block_source(session, fact_id=fact_id, block_id=second_blocks[0])
    before_events = await _sources_changed_count(session, fact_id)

    existed = await delete_document(session, document_id=first.document_id)

    assert existed is True
    expired_at = (await session.execute(
        text("SELECT expired_at FROM knowledge_triples WHERE id = CAST(:f AS uuid)"),
        {"f": fact_id},
    )).scalar_one()
    assert expired_at is None
    assert await FactSourceRepository(session).count_distinct_origins(fact_id) == 1
    assert await _sources_changed_count(session, fact_id) == before_events + 1


@pytest.mark.asyncio
async def test_delete_with_the_only_source_expires_the_fact(session):
    """A fact that loses its only source gets both: the event that reaches
    the recompute's fast arm, and the inline expiry doc 08 §3.3 permits at
    this tier -- the same deterministic action `fact_provenance._withdraw`
    already takes for a memory's last source."""
    llm = StubEmbedder()
    fact_id = await _fact(session)
    doc = await put_document(session, llm, project="p", uri="docs/sole.md", content=DOC)
    blocks = await _blocks_of(session, doc.document_id)
    await record_block_source(session, fact_id=fact_id, block_id=blocks[0])
    before_events = await _sources_changed_count(session, fact_id)

    existed = await delete_document(session, document_id=doc.document_id)

    assert existed is True
    expired_at = (await session.execute(
        text("SELECT expired_at FROM knowledge_triples WHERE id = CAST(:f AS uuid)"),
        {"f": fact_id},
    )).scalar_one()
    assert expired_at is not None
    assert await _sources_changed_count(session, fact_id) == before_events + 1


@pytest.mark.asyncio
async def test_delete_with_no_block_sources_writes_nothing_and_still_deletes(session):
    """The common case today: no `record_block_source` call ever ran against
    this document, so `withdraw_document` is a no-op and there is nothing to
    enqueue for -- but the document must still go."""
    llm = StubEmbedder()
    doc = await put_document(session, llm, project="p", uri="docs/bare.md", content=DOC)
    events_before = (await session.execute(
        text("SELECT count(*) FROM events WHERE event_type = 'sources_changed'")
    )).scalar_one()

    existed = await delete_document(session, document_id=doc.document_id)

    assert existed is True
    events_after = (await session.execute(
        text("SELECT count(*) FROM events WHERE event_type = 'sources_changed'")
    )).scalar_one()
    assert events_after == events_before
    row = (await session.execute(
        text("SELECT id FROM documents WHERE id = CAST(:id AS uuid)"),
        {"id": doc.document_id},
    )).first()
    assert row is None


@pytest.mark.asyncio
async def test_delete_of_a_missing_document_returns_false_and_writes_nothing(session):
    events_before = (await session.execute(
        text("SELECT count(*) FROM events WHERE event_type = 'sources_changed'")
    )).scalar_one()

    existed = await delete_document(
        session, document_id="33333333-3333-3333-3333-333333333333",
    )

    assert existed is False
    events_after = (await session.execute(
        text("SELECT count(*) FROM events WHERE event_type = 'sources_changed'")
    )).scalar_one()
    assert events_after == events_before


# ── search_sections resolves each hit's heading path ───────────────────


NESTED = (
    "# Guide\n\nIntro para.\n\n"
    "## Setup\n\nRun the installer.\n\n"
    "### Windows\n\nUse the msi.\n\n"
    "## Teardown\n\nDelete the folder.\n"
)

DOC_ALPHA = "# Alpha\n\n## Nested A\n\nBody A mentions installer.\n"
DOC_BETA = "# Beta\n\n## Nested B\n\nBody B mentions installer.\n"

EMPTY_HEADING_DOC = "# Guide\n\n## \n\nContent under a blank heading.\n"


def test_heading_path_terminates_on_a_synthetic_cycle():
    """Pure unit test of `_heading_path`, no DB round trip: a 2-node cycle
    (a's parent is b, b's parent is a) fed straight into `by_id`.

    This is the target used to prove the `for`-bounded walk is load-bearing
    (see the docstring on `_heading_path` and this task's report): removing
    the `seen` visited-set check but keeping the `for _ in range(...)` bound
    still terminates -- fast, deterministically -- but returns a path far
    longer than 2 elements, so the assertion below goes red on a plain
    mismatch rather than requiring a wall-clock timeout to notice a hang.
    """
    from app.services.document_door import _heading_path

    by_id = {
        "a": {"id": "a", "parent_id": "b", "text": "A", "type": "heading", "depth": 0},
        "b": {"id": "b", "parent_id": "a", "text": "B", "type": "heading", "depth": 1},
    }
    path, truncated = _heading_path("a", by_id)
    assert path == ("B", "A")
    assert truncated is True


@pytest.mark.asyncio
async def test_search_returns_the_heading_path_of_each_hit(session):
    llm = StubEmbedder()
    await put_document(session, llm, project="p", uri="docs/g.md", content=NESTED)

    hits = await search_sections(session, llm, query="installer", project="p")
    assert hits, "the stub embedder ranks everything equally; expect all blocks"
    deepest = next(h for h in hits if h.text.strip() == "Use the msi.")
    assert deepest.heading_path == ("Guide", "Setup", "Windows")
    assert deepest.path_truncated is False
    assert deepest.uri == "docs/g.md"
    assert deepest.id_kind == "block"
    assert deepest.layer == "document"


@pytest.mark.asyncio
async def test_search_includes_a_headings_own_text_in_its_path(session):
    """A heading block's own path includes itself, last -- `heading_path` is
    "the path down to and including this block if it is itself a heading",
    not merely its ancestors, so a two-level heading gets a two-element
    path, not a one-element one."""
    llm = StubEmbedder()
    await put_document(session, llm, project="p", uri="docs/g2.md", content=NESTED)

    hits = await search_sections(session, llm, query="teardown", project="p")
    teardown_heading = next(h for h in hits if h.text.strip() == "Teardown")
    assert teardown_heading.heading_path == ("Guide", "Teardown")
    assert teardown_heading.title == "Guide"

    delete_para = next(h for h in hits if h.text.strip() == "Delete the folder.")
    assert delete_para.heading_path == ("Guide", "Teardown")


@pytest.mark.asyncio
async def test_search_scopes_by_document_id(session):
    llm = StubEmbedder()
    a = await put_document(session, llm, project="p", uri="docs/a2.md", content=NESTED)
    await put_document(session, llm, project="p", uri="docs/b2.md", content=NESTED)

    hits = await search_sections(
        session, llm, query="installer", project="p", document_id=a.document_id,
    )
    assert hits
    assert all(h.document_id == a.document_id for h in hits)


@pytest.mark.asyncio
async def test_ancestors_do_not_mix_across_documents_with_different_trees(session):
    """`test_search_scopes_by_document_id` above uses two documents with
    byte-identical content, which would not notice ancestors bleeding
    between documents (any mix-up would look the same as the correct
    answer). Use two genuinely different heading trees instead, so a
    cross-document mix-up in `_ANCESTORS`' `by_id` dict would show up as a
    wrong path rather than passing by coincidence."""
    llm = StubEmbedder()
    alpha = await put_document(session, llm, project="p", uri="docs/alpha.md", content=DOC_ALPHA)
    beta = await put_document(session, llm, project="p", uri="docs/beta.md", content=DOC_BETA)

    hits = await search_sections(session, llm, query="installer", project="p")
    hit_a = next(
        h for h in hits
        if h.document_id == alpha.document_id and h.text.strip() == "Body A mentions installer."
    )
    hit_b = next(
        h for h in hits
        if h.document_id == beta.document_id and h.text.strip() == "Body B mentions installer."
    )
    assert hit_a.heading_path == ("Alpha", "Nested A")
    assert hit_b.heading_path == ("Beta", "Nested B")


@pytest.mark.asyncio
async def test_search_with_no_matching_blocks_returns_empty(session):
    llm = StubEmbedder()
    hits = await search_sections(session, llm, query="anything", project="empty-project")
    assert hits == []


@pytest.mark.asyncio
async def test_an_empty_heading_still_counts_as_a_level(session):
    """`## ` with nothing after it still parses to a heading block, with
    `text == ""`. Dropping it from the path (rather than appending the
    empty string) would silently shallow every path under it -- the same
    honesty failure `path_truncated` exists to flag for the depth cap, so
    the level must be preserved even though its title is blank."""
    llm = StubEmbedder()
    await put_document(session, llm, project="p", uri="docs/blank.md", content=EMPTY_HEADING_DOC)

    hits = await search_sections(session, llm, query="content", project="p")
    para = next(h for h in hits if h.text.strip() == "Content under a blank heading.")
    assert para.heading_path == ("Guide", "")


@pytest.mark.asyncio
async def test_a_parent_cycle_does_not_hang_the_walk(session):
    """`blocks.parent_id` has no constraint forbidding a cycle. Force one
    directly in the database (Guide's parent becomes Setup, whose own
    parent is already Guide) and assert on the *returned path*, not merely
    that the call completes within some wall-clock budget: `_heading_path`
    is now bounded by a `for` loop with a hard iteration ceiling, so it
    cannot hang the event loop even if `seen` regressed, and a wrong
    result -- not a timeout -- is what a regression would look like."""
    llm = StubEmbedder()
    doc = await put_document(session, llm, project="p", uri="docs/cycle.md", content=NESTED)

    heading_rows = (await session.execute(
        text(
            "SELECT CAST(id AS text) AS id, text FROM blocks "
            "WHERE document_id = CAST(:document_id AS uuid) AND type = 'heading' "
            "ORDER BY order_index"
        ),
        {"document_id": doc.document_id},
    )).mappings().all()
    guide = next(r["id"] for r in heading_rows if r["text"] == "Guide")
    setup = next(r["id"] for r in heading_rows if r["text"] == "Setup")
    await session.execute(
        text("UPDATE blocks SET parent_id = CAST(:p AS uuid) WHERE id = CAST(:c AS uuid)"),
        {"p": setup, "c": guide},
    )

    hits = await search_sections(session, llm, query="installer", project="p")

    deepest = next(h for h in hits if h.text.strip() == "Use the msi.")
    assert deepest.heading_path == ("Guide", "Setup", "Windows")
    assert deepest.path_truncated is True
