"""The single-document metadata writer (spec §4.2).

Every test files a real document through `put_document` first, so the writer
runs against a row a caller could actually have produced.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text

from app.services.document_door import (
    DocumentUriConflict,
    put_document,
    update_document_metadata,
)


FINGERPRINT = "test-fp-docupdate|3"


@pytest.fixture(autouse=True)
def _forget_probe_fingerprint():
    """`EmbedderRegistry` caches known fingerprints process-wide, but each
    test's DB writes roll back at teardown. Without forgetting, a later test
    skips re-registering a fingerprint whose child table no longer exists in
    its fresh transaction -- the same fixture test_block_verbs.py carries."""
    from app.services.embedder_registry import embedder_registry

    embedder_registry.forget(FINGERPRINT)
    yield
    embedder_registry.forget(FINGERPRINT)


class StubEmbedder:
    """The shape `block_embeddings` actually calls -- see the sibling stubs in
    test_block_verbs.py and test_document_door.py."""

    def __init__(self, fingerprint: str = FINGERPRINT):
        self.fingerprint = fingerprint

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
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


async def _read(session, document_id):
    row = (await session.execute(
        text(
            "SELECT title, uri, pinned_at, project, updated_at FROM documents "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": str(document_id)},
    )).mappings().one()
    return dict(row)


async def _tags(session, document_id) -> set[str]:
    rows = (await session.execute(
        text(
            "SELECT t.name FROM document_tags dt JOIN tags t ON t.id = dt.tag_id "
            "WHERE dt.document_id = CAST(:id AS uuid)"
        ),
        {"id": str(document_id)},
    )).scalars().all()
    return set(rows)


async def _latest_event(session, document_id):
    row = (await session.execute(
        text(
            "SELECT event_type, payload, project FROM events "
            "WHERE object_id = CAST(:id AS uuid) "
            "ORDER BY created_at DESC, id DESC LIMIT 1"
        ),
        {"id": str(document_id)},
    )).mappings().one()
    return dict(row)


@pytest.mark.asyncio
async def test_a_document_can_be_renamed_moved_and_pinned(session):
    _, doc = await _file(session, "# T\n\npara", "notes/a.md")
    await update_document_metadata(session, document_id=doc, title="New",
                                   uri="notes/new.md", pinned=True)
    row = await _read(session, doc)
    assert (row["title"], row["uri"]) == ("New", "notes/new.md")
    assert row["pinned_at"] is not None


@pytest.mark.asyncio
async def test_an_absent_field_leaves_its_column_untouched(session):
    _, doc = await _file(session, "# T\n\npara", "notes/b.md")
    await update_document_metadata(session, document_id=doc, title="Original")
    before = await _read(session, doc)
    assert (before["title"], before["uri"]) == ("Original", "notes/b.md")

    await update_document_metadata(session, document_id=doc, pinned=True)
    after = await _read(session, doc)
    assert (after["title"], after["uri"]) == (before["title"], before["uri"])


@pytest.mark.asyncio
async def test_an_absent_field_emits_no_assignment(session):
    """The column is not merely equal afterwards -- no SQL touches it.

    An UPDATE writing NULL over an unnamed column would pass the test above
    only by accident of the prior value, so the statement text is the check.
    """
    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    _, doc = await _file(session, "# T\n\npara", "notes/b2.md")
    statements: list[str] = []

    def _capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(Engine, "before_cursor_execute", _capture)
    try:
        await update_document_metadata(session, document_id=doc, pinned=True)
    finally:
        event.remove(Engine, "before_cursor_execute", _capture)

    updates = [s for s in statements if "UPDATE documents" in s]
    assert len(updates) == 1
    assert "pinned_at" in updates[0]
    assert "title" not in updates[0] and "uri" not in updates[0]


@pytest.mark.asyncio
async def test_present_tags_replace_rather_than_merge(session):
    """A merge-only verb cannot remove a tag, which is why this replaces."""
    _, doc = await _file(session, "# T\n\npara", "notes/c.md")
    await update_document_metadata(session, document_id=doc, tags=["a", "b"])
    await update_document_metadata(session, document_id=doc, tags=["b"])
    assert await _tags(session, doc) == {"b"}


@pytest.mark.asyncio
async def test_an_absent_tags_list_leaves_the_tag_set_alone(session):
    _, doc = await _file(session, "# T\n\npara", "notes/c2.md")
    await update_document_metadata(session, document_id=doc, tags=["a"])
    await update_document_metadata(session, document_id=doc, title="New")
    assert await _tags(session, doc) == {"a"}


@pytest.mark.asyncio
async def test_an_empty_tags_list_clears_the_tag_set(session):
    _, doc = await _file(session, "# T\n\npara", "notes/c3.md")
    await update_document_metadata(session, document_id=doc, tags=["a"])
    await update_document_metadata(session, document_id=doc, tags=[])
    assert await _tags(session, doc) == set()


@pytest.mark.asyncio
async def test_tags_resolve_through_the_shared_tag_table(session):
    """Both doors' tags are one row per name, so the document link must point
    at the tag a memory would have created rather than mint a second one."""
    from app.repositories.relational import PostgresTagRepository

    _, doc = await _file(session, "# T\n\npara", "notes/c4.md")
    existing = await PostgresTagRepository(session).get_or_create("project/x")
    await update_document_metadata(session, document_id=doc, tags=["project/x"])

    linked = (await session.execute(
        text(
            "SELECT tag_id FROM document_tags WHERE document_id = CAST(:id AS uuid)"
        ),
        {"id": str(doc)},
    )).scalars().all()
    assert linked == [existing.id]
    total = (await session.execute(
        text("SELECT count(*) FROM tags WHERE name = 'project/x'")
    )).scalar_one()
    assert total == 1


@pytest.mark.asyncio
async def test_pinned_false_clears_the_column(session):
    _, doc = await _file(session, "# T\n\npara", "notes/d.md")
    await update_document_metadata(session, document_id=doc, pinned=True)
    await update_document_metadata(session, document_id=doc, pinned=False)
    assert (await _read(session, doc))["pinned_at"] is None


@pytest.mark.asyncio
async def test_renaming_onto_an_occupied_path_refuses(session):
    _, first = await _file(session, "one", "notes/e.md")
    await _file(session, "two", "notes/f.md")
    with pytest.raises(DocumentUriConflict):
        await update_document_metadata(session, document_id=first,
                                       uri="notes/f.md")


@pytest.mark.asyncio
async def test_a_refused_rename_leaves_the_session_usable(session):
    """The conflicting UPDATE runs in its own SAVEPOINT, so the caller's
    transaction survives the refusal rather than aborting with it."""
    _, first = await _file(session, "one", "notes/e2.md")
    await _file(session, "two", "notes/f2.md")
    with pytest.raises(DocumentUriConflict):
        await update_document_metadata(session, document_id=first,
                                       uri="notes/f2.md")
    assert (await _read(session, first))["uri"] == "notes/e2.md"
    await update_document_metadata(session, document_id=first, title="Still works")
    assert (await _read(session, first))["title"] == "Still works"


@pytest.mark.asyncio
async def test_the_update_journals_one_event_carrying_no_document_text(session):
    _, doc = await _file(session, "# T\n\nsecret prose", "notes/g.md")
    await update_document_metadata(session, document_id=doc, title="New")
    row = await _latest_event(session, doc)
    assert row["event_type"] == "document_updated"
    assert "secret prose" not in json.dumps(row["payload"])
    assert row["payload"]["fields"] == ["title"]
