"""The four block verbs (spec §8, increment 8).

Every test files a document through `put_document` first -- real parse, real
spans -- then drives the verbs, because the properties that matter are about
what happens to an existing tree.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.services.block_serializer import TreeBlock
from app.services.block_verbs import (
    BlockCycleError,
    BlockTargetUnresolved,
    delete_block,
    insert_block,
    move_block,
    update_block,
)
from app.services.document_door import DocumentNotConvertible, put_document
from app.services.document_ingest import compute_content_hash


FINGERPRINT = "test-fp-verbs|3"


@pytest.fixture(autouse=True)
def _forget_probe_fingerprint():
    """`EmbedderRegistry` caches known fingerprints process-wide, but each
    test's DB writes roll back at teardown. Without forgetting, a later test
    skips re-registering a fingerprint whose child table no longer exists in
    its fresh transaction -- the same fixture test_document_door.py carries,
    and for the same reason."""
    from app.services.embedder_registry import embedder_registry

    embedder_registry.forget(FINGERPRINT)
    yield
    embedder_registry.forget(FINGERPRINT)


class StubEmbedder:
    """The shape `block_embeddings` actually calls -- see the sibling stub in
    test_document_door.py. `batches` records what was handed to the embedder,
    which is how the touched-block-only property is asserted."""

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


async def _file(session, content: str, uri: str):
    llm = StubEmbedder()
    result = await put_document(
        session, llm, project="p", uri=uri, content=content,
    )
    await session.commit()
    return llm, result.document_id


async def _blocks(session, document_id):
    return (await session.execute(
        text(
            "SELECT CAST(id AS text) AS id, CAST(parent_id AS text) AS parent_id, "
            "order_index, type, text, lower(char_span) AS lo, upper(char_span) AS hi "
            "FROM blocks WHERE document_id = CAST(:id AS uuid) ORDER BY order_index"
        ),
        {"id": document_id},
    )).mappings().all()


async def _doc(session, document_id):
    return (await session.execute(
        text(
            "SELECT content, content_hash, properties->>'ingest_direction' AS direction, "
            "       properties->>'frontmatter' AS frontmatter "
            "FROM documents WHERE id = CAST(:id AS uuid)"
        ),
        {"id": document_id},
    )).mappings().one()


@pytest.mark.asyncio
async def test_update_regenerates_content_hash_and_every_span(session):
    llm, doc_id = await _file(session, "# T\n\npara one\n\npara two\n", "v/a.md")
    rows = await _blocks(session, doc_id)
    middle = next(r for r in rows if r["text"] == "para one")

    await update_block(session, llm, block_id=middle["id"],
                       text="para one made considerably longer than before")

    doc = await _doc(session, doc_id)
    assert doc["content_hash"] == compute_content_hash(doc["content"])
    # Every span still slices its own block's source back out of the
    # regenerated content -- the property that makes char_span meaningful.
    for row in await _blocks(session, doc_id):
        assert row["text"].split("\n")[0] in doc["content"][row["lo"]:row["hi"]]


@pytest.mark.asyncio
async def test_update_preserves_every_other_blocks_id(session):
    """The anti-strip-and-rewrite property: a put replaces every row, an edit
    must not."""
    llm, doc_id = await _file(session, "# T\n\nalpha\n\nbeta\n", "v/b.md")
    before = {r["id"] for r in await _blocks(session, doc_id)}
    target = next(r for r in await _blocks(session, doc_id) if r["text"] == "alpha")

    await update_block(session, llm, block_id=target["id"], text="alpha edited")

    assert {r["id"] for r in await _blocks(session, doc_id)} == before


@pytest.mark.asyncio
async def test_first_verb_converts_and_derives_markers(session):
    llm, doc_id = await _file(session, "* star\n\n1) one\n2) two\n", "v/c.md")
    assert (await _doc(session, doc_id))["direction"] is None

    rows = await _blocks(session, doc_id)
    await update_block(session, llm, block_id=rows[0]["id"], text="star")

    doc = await _doc(session, doc_id)
    assert doc["direction"] == "blocks"
    # The markers the parser discarded were read back out of the source, so
    # conversion is faithful rather than defaulting everything to "-".
    assert "* star" in doc["content"]
    assert "1) one" in doc["content"]


@pytest.mark.asyncio
async def test_conversion_refuses_a_document_it_cannot_reproduce(session):
    """Review M-2: an html_block has no block shape, so converting would
    regenerate the content without it."""
    llm, doc_id = await _file(
        session, "before\n\n<div class='x'>raw</div>\n\nafter\n", "v/d.md",
    )
    rows = await _blocks(session, doc_id)
    with pytest.raises(DocumentNotConvertible):
        await update_block(session, llm, block_id=rows[0]["id"], text="changed")

    doc = await _doc(session, doc_id)
    assert doc["direction"] is None            # nothing converted
    assert "<div class='x'>raw</div>" in doc["content"]


@pytest.mark.asyncio
async def test_frontmatter_survives_an_edit(session):
    """properties is merged with `||`, never written wholesale."""
    llm, doc_id = await _file(session, "---\ntitle: T\n---\n# H\n\nbody\n", "v/e.md")
    rows = await _blocks(session, doc_id)

    await update_block(session, llm, block_id=rows[-1]["id"], text="body edited")

    doc = await _doc(session, doc_id)
    assert doc["frontmatter"] == "title: T"
    assert doc["content"].startswith("---\ntitle: T\n---\n")


@pytest.mark.asyncio
async def test_insert_after_and_first_child_positions(session):
    llm, doc_id = await _file(session, "# T\n\nalpha\n\nbeta\n", "v/f.md")
    rows = await _blocks(session, doc_id)
    heading = rows[0]

    await insert_block(session, llm, document_id=doc_id, type="paragraph",
                       text="inserted first", parent_id=heading["id"])
    texts = [r["text"] for r in await _blocks(session, doc_id)]
    assert texts.index("inserted first") < texts.index("alpha")


@pytest.mark.asyncio
async def test_insert_normalises_an_unknown_type(session):
    llm, doc_id = await _file(session, "# T\n\nalpha\n", "v/g.md")
    result = await insert_block(session, llm, document_id=doc_id,
                                type="h2", text="Sub", properties={"level": 2})
    row = next(r for r in await _blocks(session, doc_id) if r["id"] == result.block_id)
    assert row["type"] == "heading"       # the writer normalises, per taxonomy


@pytest.mark.asyncio
async def test_move_reparents_and_reorders(session):
    """Review M-8: the returned object is not evidence. Re-read the row."""
    llm, doc_id = await _file(session, "# One\n\nalpha\n\n# Two\n\nbeta\n", "v/h.md")
    rows = await _blocks(session, doc_id)
    second_heading = [r for r in rows if r["type"] == "heading"][1]
    alpha = next(r for r in rows if r["text"] == "alpha")

    await move_block(session, llm, block_id=alpha["id"],
                     new_parent_id=second_heading["id"])

    moved = next(r for r in await _blocks(session, doc_id) if r["id"] == alpha["id"])
    assert moved["parent_id"] == second_heading["id"]


@pytest.mark.asyncio
async def test_move_into_own_subtree_refuses(session):
    llm, doc_id = await _file(session, "# One\n\nalpha\n", "v/i.md")
    rows = await _blocks(session, doc_id)
    heading = rows[0]
    child = rows[1]
    with pytest.raises(BlockCycleError):
        await move_block(session, llm, block_id=heading["id"],
                         new_parent_id=child["id"])


@pytest.mark.asyncio
async def test_delete_takes_the_subtree(session):
    llm, doc_id = await _file(session, "# One\n\nalpha\n\n# Two\n\nbeta\n", "v/j.md")
    rows = await _blocks(session, doc_id)
    first_heading = rows[0]

    await delete_block(session, llm, block_id=first_heading["id"])

    left = {r["text"] for r in await _blocks(session, doc_id)}
    assert "alpha" not in left and "One" not in left
    assert "beta" in left


@pytest.mark.asyncio
async def test_each_verb_journals_blocks_edited_without_text(session):
    llm, doc_id = await _file(session, "# T\n\nsecret prose here\n", "v/k.md")
    rows = await _blocks(session, doc_id)
    await update_block(session, llm, block_id=rows[-1]["id"], text="still secret")

    payload = (await session.execute(
        text(
            "SELECT payload FROM events WHERE event_type = 'blocks_edited' "
            "AND object_id = CAST(:id AS uuid) ORDER BY created_at DESC LIMIT 1"
        ),
        {"id": doc_id},
    )).scalar_one()
    assert payload["verb"] == "updated"
    assert "still secret" not in str(payload)     # write-time minimization


@pytest.mark.asyncio
async def test_a_verb_on_a_missing_block_refuses(session):
    llm = StubEmbedder()
    with pytest.raises(BlockTargetUnresolved):
        await update_block(session, llm,
                           block_id="00000000-0000-0000-0000-000000000000",
                           text="nope")


@pytest.mark.asyncio
async def test_update_embeds_only_the_touched_block(session):
    """Re-embedding the whole document on every keystroke is the cost model
    this door exists to avoid."""
    llm, doc_id = await _file(session, "# T\n\nalpha\n\nbeta\n", "v/l.md")
    rows = await _blocks(session, doc_id)
    llm.batches.clear()

    target = next(r for r in rows if r["text"] == "alpha")
    await update_block(session, llm, block_id=target["id"], text="alpha edited")

    embedded = [t for batch in llm.batches for t in batch]
    assert embedded == ["alpha edited"]


@pytest.mark.asyncio
async def test_a_move_embeds_nothing(session):
    """A move changes position, never text."""
    llm, doc_id = await _file(session, "# One\n\nalpha\n\n# Two\n\nbeta\n", "v/m.md")
    rows = await _blocks(session, doc_id)
    second = [r for r in rows if r["type"] == "heading"][1]
    alpha = next(r for r in rows if r["text"] == "alpha")
    llm.batches.clear()

    await move_block(session, llm, block_id=alpha["id"], new_parent_id=second["id"])

    assert llm.batches == []
