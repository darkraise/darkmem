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
from app.services.document_ingest import DocumentHashConflict, compute_content_hash


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
    """Review M-2: a link reference definition is consumed into the parser's
    `env` and mints no block, so converting would regenerate the content
    without it and leave every reference dangling. (Raw HTML used to stand
    here; it has a block shape since 2026-09-07 and converts now.)"""
    llm, doc_id = await _file(
        session, "see [the doc][ref]\n\n[ref]: https://example.test\n", "v/d.md",
    )
    rows = await _blocks(session, doc_id)
    with pytest.raises(DocumentNotConvertible):
        await update_block(session, llm, block_id=rows[0]["id"], text="changed")

    doc = await _doc(session, doc_id)
    assert doc["direction"] is None            # nothing converted
    assert "[ref]: https://example.test" in doc["content"]


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
async def test_a_document_edit_journals_object_type_document(session):
    """The journal's `object_type` rides the owner descriptor, so an edit to
    the wrong owner's rows would file under the wrong object and misplace the
    row on `GET /events/timeline`."""
    llm, doc_id = await _file(session, "# T\n\nalpha\n", "v/objtype.md")
    rows = await _blocks(session, doc_id)
    await update_block(session, llm, block_id=rows[-1]["id"], text="beta")

    object_type = (await session.execute(
        text(
            "SELECT object_type FROM events WHERE event_type = 'blocks_edited' "
            "AND object_id = CAST(:id AS uuid) ORDER BY created_at DESC LIMIT 1"
        ),
        {"id": doc_id},
    )).scalar_one()
    assert object_type == "document"


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


async def _hash_of(session, document_id):
    return (await session.execute(
        text("SELECT content_hash FROM documents WHERE id = CAST(:id AS uuid)"),
        {"id": document_id},
    )).scalar_one()


@pytest.mark.asyncio
async def test_a_stale_expected_hash_refuses_every_verb(session):
    """All four verbs rewrite content_hash, so all four take the precondition.
    Insert and move rewrite it as much as update does, so a caller that
    preconditions only its updates still clobbers a concurrent insert."""
    llm, doc = await _file(session, "# T\n\npara", "notes/cas.md")
    block = (await _blocks(session, doc))[0]["id"]
    stale = "0" * 64

    for call in (
        lambda: update_block(session, llm, block_id=block, text="x",
                             expected_hash=stale),
        lambda: insert_block(session, llm, document_id=doc, type="paragraph",
                             text="x", expected_hash=stale),
        lambda: move_block(session, llm, block_id=block, expected_hash=stale),
        lambda: delete_block(session, llm, block_id=block, expected_hash=stale),
    ):
        with pytest.raises(DocumentHashConflict):
            await call()


@pytest.mark.asyncio
async def test_the_conflict_names_the_hash_that_actually_holds(session):
    llm, doc = await _file(session, "# T\n\npara", "notes/cas2.md")
    block = (await _blocks(session, doc))[0]["id"]
    live = await _hash_of(session, doc)

    with pytest.raises(DocumentHashConflict) as caught:
        await update_block(session, llm, block_id=block, text="x",
                           expected_hash="0" * 64)

    assert caught.value.expected_hash == "0" * 64
    assert caught.value.current_hash == live


@pytest.mark.asyncio
async def test_a_matching_expected_hash_applies_the_edit(session):
    llm, doc = await _file(session, "# T\n\npara", "notes/cas3.md")
    block = (await _blocks(session, doc))[0]["id"]

    result = await update_block(session, llm, block_id=block, text="edited",
                                expected_hash=await _hash_of(session, doc))

    assert result.content_hash == await _hash_of(session, doc)
    assert [b["text"] for b in await _blocks(session, doc)][0] == "edited"


@pytest.mark.asyncio
async def test_omitting_the_hash_stays_last_writer_wins(session):
    """The precondition is opt-in. Every shipped caller omits it today."""
    llm, doc = await _file(session, "# T\n\npara", "notes/cas4.md")
    block = (await _blocks(session, doc))[0]["id"]
    await update_block(session, llm, block_id=block, text="edited")
    assert [b["text"] for b in await _blocks(session, doc)][0] == "edited"


def test_the_row_lock_precedes_the_hash_comparison():
    """What makes the precondition a compare-and-set rather than a
    check-then-act, asserted on the source because no fixture can assert it on
    behaviour: `tests/conftest.py` binds the session factory to one connection,
    so two sessions cannot contend for the lock and a comparison hoisted above
    it would leave every test in this file green.
    """
    import ast
    import inspect
    import textwrap

    from app.services import block_verbs

    body = ast.parse(
        textwrap.dedent(inspect.getsource(block_verbs._mutate))
    ).body[0]

    # The `session.execute` call that takes the lock, not a read of
    # `owner.lock`: an alias such as `stmt = owner.lock` is an attribute read
    # that acquires nothing, and a bare attribute match would count it.
    locks = [
        node.lineno
        for node in ast.walk(body)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "execute"
        and node.args
        and isinstance(node.args[0], ast.Attribute)
        and node.args[0].attr == "lock"
    ]
    # The comparison itself, not a mention of the parameter: the signature and
    # the docstring name it too, and neither decides the ordering.
    compares = [
        node.lineno
        for node in ast.walk(body)
        if isinstance(node, ast.If)
        and any(
            isinstance(inner, ast.Name) and inner.id == "expected_hash"
            for inner in ast.walk(node.test)
        )
        and any(
            isinstance(inner, ast.Name) and inner.id == "DocumentHashConflict"
            for inner in ast.walk(node)
        )
    ]

    assert locks, "_mutate no longer takes the document row lock"
    assert compares, "_mutate no longer compares expected_hash"
    assert min(locks) < min(compares), (
        "the expected_hash comparison must happen under the row lock: above "
        "it, a concurrent writer can move content_hash between the check and "
        "the write and both lanes win"
    )


async def _page(session, *, project="p", content="", title="P"):
    """A page with one paragraph block, written directly: no page door exists
    yet."""
    from app.utils.ids import new_id

    page_id, block_id = new_id(), new_id()
    await session.execute(
        text(
            "INSERT INTO pages (id, project, order_index, title, content, "
            "content_hash) VALUES (CAST(:id AS uuid), :project, 0, :title, "
            "CAST(:content AS text), :hash)"
        ),
        {"id": str(page_id), "project": project, "title": title,
         "content": content, "hash": compute_content_hash(content)},
    )
    await session.execute(
        text(
            "INSERT INTO blocks (id, page_id, order_index, type, text) "
            "VALUES (CAST(:id AS uuid), CAST(:page AS uuid), 0, 'paragraph', "
            "CAST(:text AS text))"
        ),
        {"id": str(block_id), "page": str(page_id), "text": "page prose"},
    )
    return str(page_id), str(block_id)


@pytest.mark.asyncio
async def test_a_page_block_resolves_to_the_page_owner(session):
    """`_document_of` read one column, so a page block resolved to None and
    every verb built on it silently targeted nothing."""
    from app.services.block_verbs import PAGE_OWNER, _owner_of

    page_id, block_id = await _page(session, content="page prose\n")

    owner, owner_id = await _owner_of(session, block_id, PAGE_OWNER)
    assert owner.kind == "page"
    assert owner_id == page_id


@pytest.mark.asyncio
async def test_a_document_block_still_resolves_to_the_document_owner(session):
    from app.services.block_verbs import _owner_of

    _, doc_id = await _file(session, "# T\n\nalpha\n", "v/owner.md")
    rows = await _blocks(session, doc_id)

    owner, owner_id = await _owner_of(session, rows[-1]["id"])
    assert owner.kind == "document"
    assert owner_id == doc_id


@pytest.mark.asyncio
async def test_a_page_edit_journals_object_type_page(session):
    """The journal's `object_type` rides the owner descriptor; filing a page
    edit as a document would misplace it on `GET /events/timeline`."""
    from app.services.block_verbs import PAGE_OWNER

    llm = StubEmbedder()
    page_id, block_id = await _page(session, content="page prose\n")

    result = await update_block(session, llm, block_id=block_id,
                                text="page prose edited", owner=PAGE_OWNER)

    assert result.owner_kind == "page"
    assert result.owner_id == page_id
    assert result.document_id is None
    object_type = (await session.execute(
        text(
            "SELECT object_type FROM events WHERE event_type = 'blocks_edited' "
            "AND object_id = CAST(:id AS uuid) ORDER BY created_at DESC LIMIT 1"
        ),
        {"id": page_id},
    )).scalar_one()
    assert object_type == "page"


@pytest.mark.asyncio
async def test_a_page_edit_rewrites_the_page_content(session):
    from app.services.block_verbs import PAGE_OWNER

    llm = StubEmbedder()
    page_id, block_id = await _page(session, content="page prose\n")

    await update_block(session, llm, block_id=block_id, text="rewritten",
                       owner=PAGE_OWNER)

    row = (await session.execute(
        text(
            "SELECT content, content_hash FROM pages "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": page_id},
    )).mappings().one()
    assert "rewritten" in row["content"]
    assert row["content_hash"] == compute_content_hash(row["content"])


@pytest.mark.asyncio
async def test_a_verb_against_a_trashed_page_refuses(session):
    from app.services.block_verbs import PAGE_OWNER

    llm = StubEmbedder()
    page_id, block_id = await _page(session, content="page prose\n")
    await session.execute(
        text("UPDATE pages SET deleted_at = now() WHERE id = CAST(:id AS uuid)"),
        {"id": page_id},
    )

    with pytest.raises(BlockTargetUnresolved):
        await update_block(session, llm, block_id=block_id, text="nope",
                           owner=PAGE_OWNER)


@pytest.mark.asyncio
async def test_inserting_into_a_page_names_the_page_owner(session):
    from app.services.block_verbs import PAGE_OWNER

    llm = StubEmbedder()
    page_id, _ = await _page(session, content="page prose\n")

    result = await insert_block(session, llm, document_id=page_id,
                                type="paragraph", text="added",
                                owner=PAGE_OWNER)

    assert result.owner_kind == "page"
    texts = [r["text"] for r in (await session.execute(
        text(
            "SELECT text FROM blocks WHERE page_id = CAST(:id AS uuid) "
            "ORDER BY order_index"
        ),
        {"id": page_id},
    )).mappings().all()]
    assert "added" in texts


@pytest.mark.asyncio
async def test_a_missing_page_is_refused_by_its_own_noun(session):
    """The unresolved message rides the descriptor: a page id in a sentence
    saying "document" sends the reader to the wrong table."""
    from app.services.block_verbs import PAGE_OWNER

    llm = StubEmbedder()
    with pytest.raises(BlockTargetUnresolved) as caught:
        await insert_block(session, llm,
                           document_id="00000000-0000-0000-0000-000000000000",
                           type="paragraph", text="x", owner=PAGE_OWNER)
    assert "page" in str(caught.value)
    assert "document" not in str(caught.value)


@pytest.mark.asyncio
async def test_a_page_edit_never_runs_the_conversion_pass(session):
    """A page has no authored source to reproduce, so content the serialiser
    cannot round-trip must not refuse the edit -- the refusal's remedy is
    `document_put`, which a page has no door for."""
    from app.services.block_verbs import PAGE_OWNER

    llm = StubEmbedder()
    page_id, block_id = await _page(
        session, content="[ref]: https://example.test\n"
    )

    result = await update_block(session, llm, block_id=block_id, text="edited",
                                owner=PAGE_OWNER)

    assert result.owner_kind == "page"


@pytest.mark.asyncio
async def test_a_bare_block_id_verb_refuses_a_page_block(session):
    """The MCP shape: a block id and no owner. The verbs verify the owner the
    caller named rather than discovering it, so a page block is refused on a
    door that has not been given pages."""
    llm = StubEmbedder()
    page_id, block_id = await _page(session, content="page prose\n")

    for verb in (
        lambda: update_block(session, llm, block_id=block_id, text="x"),
        lambda: move_block(session, llm, block_id=block_id),
        lambda: delete_block(session, llm, block_id=block_id),
    ):
        with pytest.raises(BlockTargetUnresolved):
            await verb()


@pytest.mark.asyncio
async def test_a_page_insert_names_the_page_in_its_parent_refusal(session):
    from app.services.block_verbs import PAGE_OWNER

    llm = StubEmbedder()
    page_id, _ = await _page(session, content="page prose\n")

    with pytest.raises(BlockTargetUnresolved) as caught:
        await insert_block(
            session, llm, document_id=page_id, type="paragraph", text="x",
            parent_id="00000000-0000-0000-0000-000000000000",
            owner=PAGE_OWNER,
        )
    assert "document" not in str(caught.value)


@pytest.mark.asyncio
async def test_a_page_block_edit_embeds_into_the_page_family(session):
    """A page vector in `block_embeddings` would surface in document search."""
    from app.services.block_embeddings import PAGE_PARENT_TABLE, PARENT_TABLE
    from app.services.block_verbs import PAGE_OWNER
    from app.services.embedder_registry import child_table

    llm = StubEmbedder()
    _, block_id = await _page(session, content="page prose\n")

    await update_block(session, llm, block_id=block_id, text="edited",
                       owner=PAGE_OWNER)

    async def count(parent):
        exists = (await session.execute(
            text("SELECT to_regclass(:t)"), {"t": child_table(parent, FINGERPRINT)},
        )).scalar_one()
        if exists is None:
            return 0
        return (await session.execute(
            text(f"SELECT count(*) FROM {child_table(parent, FINGERPRINT)} "
                 "WHERE block_id = CAST(:id AS uuid)"),
            {"id": block_id},
        )).scalar_one()

    assert await count(PAGE_PARENT_TABLE) == 1
    assert await count(PARENT_TABLE) == 0


def test_the_document_write_statement_renders_unchanged():
    from app.services.block_verbs import _WRITE_DOC

    assert str(_WRITE_DOC) == """
    UPDATE documents
    SET content = CAST(:content AS text),
        content_hash = CAST(:hash AS text),
        properties = COALESCE(properties, '{}'::jsonb)
                     || jsonb_build_object('ingest_direction', 'blocks')
    WHERE id = CAST(:id AS uuid)
    """
