"""The `block_embeddings` writer — first writer to T0.13's inert template (TH1.05).

Three properties carry this module, mirroring the discipline
`test_relation_embeddings.py` and `test_triple_embeddings.py` already
established for the sibling target-new families.

**Register-before-insert is drilled, not merely exercised.** A happy-path test
that reaches a live table after registration proves the writer works when the
guard is intact; it says nothing about whether the guard is *load-bearing*.
`test_skipping_registration_breaks_the_insert` disables the register call and
shows the insert fails outright — the table genuinely does not exist until
`ensure_partition` creates it — then restores the guard and shows the same
call succeeds.

**Naming goes through `child_table(PARENT_TABLE, fingerprint)` only.**
`test_every_child_table_is_reached_through_the_parent_constant` walks the
module's own AST rather than trusting a docstring, exactly as the relation
writer's suite does.

**No cross-fingerprint comparison is proven, not asserted.** Two fingerprints
embed the *same* block id; a read scoped to one fingerprint returns only that
fingerprint's vector, even though the other fingerprint's row for the same id
exists right next to it. If the read ever joined or unioned across
`__<slug>` tables, this is the test that would catch it.
"""
from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.services import block_embeddings as be_mod
from app.services.document_ingest import BlockDraft, file_document

BACKEND = Path(__file__).resolve().parent.parent
MODULE_PATH = BACKEND / "app" / "services" / "block_embeddings.py"

FINGERPRINT = "block-probe|8"
OTHER_FINGERPRINT = "block-probe-other|4"

PROJECT = "th105-blocks"


class FakeEmbedder:
    """Returns a fixed-shape vector per text under one fingerprint.

    Deliberately not a similarity model: this module's correctness is about
    which rows land under which fingerprint, never about geometry.
    """

    def __init__(self, fingerprint: str = FINGERPRINT, dims: int = 8):
        self.fingerprint = fingerprint
        self.dims = dims
        self.texts: list[str] = []
        self.calls = 0

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        self.calls += 1
        self.texts.extend(texts)
        return (
            [[float(i)] * self.dims for i, _ in enumerate(texts)],
            self.fingerprint,
        )


class MiscountingEmbedder(FakeEmbedder):
    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        vectors, fp = await super().embed_batch_chunked(texts, chunk_size, concurrency)
        return vectors[:-1], fp


@pytest.fixture(autouse=True)
def _forget_probe_fingerprints():
    """The registry cache is process-wide while the test database is rolled
    back; without this a later test finds the fingerprint "known", skips the
    DDL, and inserts into a child table its own transaction never created."""
    from app.services.embedder_registry import embedder_registry

    for fp in (FINGERPRINT, OTHER_FINGERPRINT):
        embedder_registry.forget(fp)
    yield
    for fp in (FINGERPRINT, OTHER_FINGERPRINT):
        embedder_registry.forget(fp)


async def _file_blocks(session, *texts: str) -> tuple[str, list[str]]:
    """File one document with `texts` as its blocks; return (document_id, block_ids)."""
    drafts = [BlockDraft(text=t, type="paragraph") for t in texts]
    ingest = await file_document(
        session,
        project=PROJECT,
        content="\n\n".join(texts),
        parse=lambda: drafts,
        title="probe",
        source_type="note",
    )
    await session.flush()
    rows = (await session.execute(
        text("SELECT id FROM blocks WHERE document_id = CAST(:d AS uuid) ORDER BY order_index"),
        {"d": str(ingest.document_id)},
    )).scalars().all()
    return str(ingest.document_id), [str(r) for r in rows]


async def _created_at(session, table: str, block_id: str) -> str:
    return str((await session.execute(
        text(f"SELECT created_at FROM {table} WHERE block_id = CAST(:id AS uuid)"),
        {"id": block_id},
    )).scalar_one())


# ── the write itself ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_block_embeds_its_own_text(session):
    _doc_id, block_ids = await _file_blocks(session, "first block", "second block")
    embedder = FakeEmbedder()

    result = await be_mod.embed_blocks(session, embedder, block_ids=block_ids)

    assert result is not None
    assert result.fingerprint == FINGERPRINT
    assert result.written == 2
    assert embedder.texts == ["first block", "second block"]

    vectors = await be_mod.block_vectors(
        session, fingerprint=FINGERPRINT, block_ids=block_ids,
    )
    assert set(vectors) == set(block_ids)
    for vec in vectors.values():
        assert len(vec) == 8


@pytest.mark.asyncio
async def test_an_empty_or_unmatched_request_writes_nothing(session):
    embedder = FakeEmbedder()

    assert await be_mod.embed_blocks(session, embedder, block_ids=[]) is None
    assert embedder.calls == 0

    assert await be_mod.embed_blocks(
        session, embedder, block_ids=[str(uuid4())],
    ) is None
    assert embedder.calls == 0


@pytest.mark.asyncio
async def test_an_empty_text_block_is_still_embedded(session):
    """A block's text may legitimately be an empty string; a writer that
    silently skipped it would leave a retrievable block with no vector and no
    record of why."""
    _doc_id, block_ids = await _file_blocks(session, "")
    embedder = FakeEmbedder()

    result = await be_mod.embed_blocks(session, embedder, block_ids=block_ids)

    assert result is not None
    assert result.written == 1
    assert embedder.texts == [""]


@pytest.mark.asyncio
async def test_a_short_vector_batch_refuses_to_write_any(session):
    _doc_id, block_ids = await _file_blocks(session, "one", "two")
    embedder = MiscountingEmbedder()

    with pytest.raises(RuntimeError, match="refusing to write"):
        await be_mod.embed_blocks(session, embedder, block_ids=block_ids)

    from app.services.embedder_registry import child_table
    table = child_table(be_mod.PARENT_TABLE, FINGERPRINT)
    found = (await session.execute(text(f"SELECT to_regclass('{table}')"))).scalar()
    if found is not None:
        count = (await session.execute(text(f"SELECT count(*) FROM {table}"))).scalar()
        assert count == 0


@pytest.mark.asyncio
async def test_re_embedding_refreshes_the_vector_and_keeps_created_at(session):
    from app.services.embedder_registry import child_table

    _doc_id, block_ids = await _file_blocks(session, "content")
    embedder = FakeEmbedder()

    first = await be_mod.embed_blocks(session, embedder, block_ids=block_ids)
    assert first is not None
    table = child_table(be_mod.PARENT_TABLE, FINGERPRINT)
    created_first = await _created_at(session, table, block_ids[0])

    class ShiftedEmbedder(FakeEmbedder):
        async def embed_batch_chunked(self, texts, chunk_size, concurrency):
            return [[9.0] * self.dims for _ in texts], self.fingerprint

    second = await be_mod.embed_blocks(session, ShiftedEmbedder(), block_ids=block_ids)
    assert second is not None
    created_second = await _created_at(session, table, block_ids[0])
    assert created_first == created_second

    vectors = await be_mod.block_vectors(
        session, fingerprint=FINGERPRINT, block_ids=block_ids,
    )
    assert vectors[block_ids[0]] == [9.0] * 8


# ── register-before-insert, drilled ──────────────────────────────────


@pytest.mark.asyncio
async def test_skipping_registration_breaks_the_insert(session, monkeypatch):
    """The guard is load-bearing, not decorative: disable it and the insert
    fails outright, because the table genuinely does not exist without it."""
    _doc_id, block_ids = await _file_blocks(session, "guarded content")
    embedder = FakeEmbedder()

    async def _noop_ensure_partition(_session, _fingerprint):
        return None

    monkeypatch.setattr(be_mod, "ensure_partition", _noop_ensure_partition)

    # The failing insert runs inside its own SAVEPOINT so recovering from it
    # rolls back that savepoint and nothing else. A bare `session.rollback()`
    # here — which is what this test did until 2026-08-24 — deassociates the
    # outer transaction the `session` fixture uses as its isolation boundary
    # (the SAWarning it logged said so), so everything this test wrote after
    # it escaped into the next test in the same process. Harmless under
    # pytest's alphabetical file order and not under any other: it reddened
    # four `test_block_embedding_refresh.py` tests, whose sweep is corpus-wide
    # by design and therefore sees a stray block from any other file.
    with pytest.raises(Exception) as excinfo:
        async with session.begin_nested():
            await be_mod.embed_blocks(session, embedder, block_ids=block_ids)
    assert "block_embeddings__" in str(excinfo.value) or "does not exist" in str(
        excinfo.value
    ).lower()

    monkeypatch.undo()

    _doc_id2, block_ids2 = await _file_blocks(session, "guarded content again")
    result = await be_mod.embed_blocks(session, FakeEmbedder(), block_ids=block_ids2)
    assert result is not None
    assert result.written == 1


# ── naming discipline ────────────────────────────────────────────────


def test_every_child_table_is_reached_through_the_parent_constant():
    tree = ast.parse(MODULE_PATH.read_text())
    parents = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "child_table"):
            first = node.args[0]
            parents.add(first.value if isinstance(first, ast.Constant) else first.id)
    assert parents == {"PARENT_TABLE"}
    assert be_mod.PARENT_TABLE == "block_embeddings"


def test_the_module_never_calls_llm_fingerprint():
    """The `|0` sentinel trap (T2.68, T2.83): under a phantom fingerprint a
    bulk read would find nothing under a table nothing real ever wrote to,
    with no error and no symptom."""
    tree = ast.parse(MODULE_PATH.read_text())
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        and node.func.attr == "llm_fingerprint"
    ]
    assert not calls


def test_the_template_is_no_longer_inert():
    from tests.test_inert_objects import INERT_TEMPLATES

    assert "block_embeddings" not in INERT_TEMPLATES, (
        "TH1.05 is this template's first writer; leaving it listed inert means "
        "the suite asserts nothing writes to a table this module writes to"
    )


# ── no cross-fingerprint comparison, proven ──────────────────────────


@pytest.mark.asyncio
async def test_a_read_under_one_fingerprint_never_sees_another(session):
    """Two fingerprints embed the SAME block id. A read scoped to one
    fingerprint must return only that fingerprint's vector — proof, not
    assertion, that the two live in genuinely separate tables rather than a
    shared table filtered by a predicate that could be dropped by mistake."""
    _doc_id, block_ids = await _file_blocks(session, "shared block")
    block_id = block_ids[0]

    embedder_a = FakeEmbedder(fingerprint=FINGERPRINT, dims=8)
    embedder_b = FakeEmbedder(fingerprint=OTHER_FINGERPRINT, dims=4)

    await be_mod.embed_blocks(session, embedder_a, block_ids=[block_id])
    await be_mod.embed_blocks(session, embedder_b, block_ids=[block_id])

    from app.services.embedder_registry import child_table
    table_a = child_table(be_mod.PARENT_TABLE, FINGERPRINT)
    table_b = child_table(be_mod.PARENT_TABLE, OTHER_FINGERPRINT)
    assert table_a != table_b

    only_a = await be_mod.block_vectors(
        session, fingerprint=FINGERPRINT, block_ids=[block_id],
    )
    only_b = await be_mod.block_vectors(
        session, fingerprint=OTHER_FINGERPRINT, block_ids=[block_id],
    )

    assert set(only_a) == {block_id}
    assert set(only_b) == {block_id}
    assert len(only_a[block_id]) == 8
    assert len(only_b[block_id]) == 4

    # Both rows genuinely exist, one per table, keyed on the same block_id —
    # proving the isolation is structural (two tables) rather than a filter
    # over one shared table that happened not to be exercised above.
    count_a = (await session.execute(
        text(f"SELECT count(*) FROM {table_a} WHERE block_id = CAST(:id AS uuid)"),
        {"id": block_id},
    )).scalar_one()
    count_b = (await session.execute(
        text(f"SELECT count(*) FROM {table_b} WHERE block_id = CAST(:id AS uuid)"),
        {"id": block_id},
    )).scalar_one()
    assert count_a == 1
    assert count_b == 1


@pytest.mark.asyncio
async def test_resolve_read_fingerprint_delegates_to_the_shared_resolver(session):
    """Never re-derived from static config — the same discipline the sibling
    writers carry, delegated to `PostgresVectorRepository` rather than
    duplicated."""
    from app.repositories.vector import EmbedderFingerprintUnresolved

    class NoDataEmbedder:
        def llm_fingerprint(self):
            return "nothing-embedded-yet|8"

    with pytest.raises(EmbedderFingerprintUnresolved):
        await be_mod.resolve_read_fingerprint(session, NoDataEmbedder())


@pytest.mark.asyncio
async def test_resolve_active_fingerprint_uses_a_real_embed_not_a_probe():
    """`resolve_active_fingerprint` is the resolver for a caller whose job
    is to fill a possibly-EMPTY partition (the refresh sweep,
    `document_door`'s `unchanged` repair): it must report whatever the
    active embedder produces right now, not whatever fingerprint already
    happens to hold data. Proven here with no database at all — the
    fingerprint comes straight from the embed call's own return value."""

    class RecordingEmbedder:
        def __init__(self):
            self.embedded_values: list[str] = []

        async def embed(self, value):
            self.embedded_values.append(value)
            return [1.0, 0.0], "recorded-fingerprint|2"

    llm = RecordingEmbedder()
    resolved = await be_mod.resolve_active_fingerprint(llm)

    assert resolved == "recorded-fingerprint|2"
    assert len(llm.embedded_values) == 1, "exactly one embed call, never more"


@pytest.mark.asyncio
async def test_resolve_active_fingerprint_never_raises_unresolved():
    """Unlike `resolve_read_fingerprint`, a real embed always yields a real
    fingerprint — there is no "nothing registered under this model yet"
    bootstrap case to guard against, even on a completely fresh install."""

    class FreshInstallEmbedder:
        async def embed(self, value):
            return [1.0], "brand-new-model|1"

    resolved = await be_mod.resolve_active_fingerprint(FreshInstallEmbedder())
    assert resolved == "brand-new-model|1"
