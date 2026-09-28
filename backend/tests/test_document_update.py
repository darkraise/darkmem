"""The single-document metadata writer (spec §4.2).

Every test files a real document through `put_document` first, so the writer
runs against a row a caller could actually have produced.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text

from uuid import uuid4

from app.services.document_door import (
    DOCUMENTS_DELETED_EVENT,
    DocumentJournalWriteFailed,
    DocumentNothingToChange,
    DocumentTargetUnresolved,
    DocumentUriConflict,
    delete_documents,
    put_document,
    rename_documents,
    update_document_metadata,
)
from app.services.document_ingest import DocumentHashConflict


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
    """`source_type` is explicit because a subtree prefix such as `notes/a` is
    itself a filed document with no suffix to infer a parser from."""
    llm = StubEmbedder()
    result = await put_document(
        session, llm, project="p", uri=uri, content=content,
        source_type="md",
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


async def _event_count(session, document_id) -> int:
    return (await session.execute(
        text("SELECT count(*) FROM events WHERE object_id = CAST(:id AS uuid)"),
        {"id": str(document_id)},
    )).scalar_one()


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
async def test_a_title_only_call_against_a_missing_id_refuses(session):
    missing = uuid4()
    with pytest.raises(DocumentTargetUnresolved):
        await update_document_metadata(session, document_id=missing, title="New")
    assert await _event_count(session, missing) == 0


@pytest.mark.asyncio
async def test_a_tags_only_call_against_a_missing_id_refuses(session):
    missing = uuid4()
    with pytest.raises(DocumentTargetUnresolved):
        await update_document_metadata(session, document_id=missing, tags=["a"])
    assert await _event_count(session, missing) == 0


@pytest.mark.asyncio
async def test_an_entirely_empty_call_against_a_missing_id_refuses(session):
    missing = uuid4()
    with pytest.raises(DocumentNothingToChange):
        await update_document_metadata(session, document_id=missing)
    assert await _event_count(session, missing) == 0


@pytest.mark.asyncio
async def test_a_call_naming_no_field_refuses_and_journals_nothing(session):
    """An empty call used to journal `{"fields": []}` against a real document,
    which `events` can never take back."""
    _, doc = await _file(session, "body", "notes/empty.md")
    before = await _event_count(session, doc)
    with pytest.raises(DocumentNothingToChange):
        await update_document_metadata(session, document_id=doc)
    assert await _event_count(session, doc) == before


@pytest.mark.asyncio
async def test_the_update_journals_one_event_carrying_no_document_text(session):
    _, doc = await _file(session, "# T\n\nsecret prose", "notes/g.md")
    await update_document_metadata(session, document_id=doc, title="New")
    row = await _latest_event(session, doc)
    assert row["event_type"] == "document_updated"
    assert "secret prose" not in json.dumps(row["payload"])
    assert row["payload"]["fields"] == ["title"]


async def _uris(session, project: str) -> set[str]:
    rows = (await session.execute(
        text("SELECT uri FROM documents WHERE project = CAST(:p AS text)"),
        {"p": project},
    )).scalars().all()
    return set(rows)


@pytest.mark.asyncio
async def test_a_subtree_rename_rewrites_every_descendant(session):
    for uri in ("notes/a", "notes/a/one.md", "notes/a/two.md"):
        await _file(session, "body", uri)
    assert await rename_documents(session, project="p", uri_prefix="notes/a",
                                  new_uri_prefix="notes/b") == 3
    assert await _uris(session, "p") == {
        "notes/b", "notes/b/one.md", "notes/b/two.md"}


@pytest.mark.asyncio
async def test_a_prefix_containing_a_wildcard_does_not_over_match(session):
    """`_` and `%` are LIKE metacharacters. A prefix of `notes/a_b` must not
    match `notes/axb`."""
    await _file(session, "body", "notes/a_b/one.md")
    await _file(session, "body", "notes/axb/two.md")
    await _file(session, "body", "notes/a%c/three.md")
    await _file(session, "body", "notes/aXc/four.md")
    await rename_documents(session, project="p", uri_prefix="notes/a_b",
                           new_uri_prefix="notes/z")
    await rename_documents(session, project="p", uri_prefix="notes/a%c",
                           new_uri_prefix="notes/y")
    assert await _uris(session, "p") == {
        "notes/z/one.md", "notes/axb/two.md",
        "notes/y/three.md", "notes/aXc/four.md",
    }


@pytest.mark.asyncio
async def test_a_sibling_sharing_the_prefix_as_a_name_is_untouched(session):
    """`notes/ab` starts with `notes/a` but is not inside it."""
    await _file(session, "body", "notes/a/one.md")
    await _file(session, "body", "notes/ab")
    assert await rename_documents(session, project="p", uri_prefix="notes/a",
                                  new_uri_prefix="notes/b") == 1
    assert await _uris(session, "p") == {"notes/b/one.md", "notes/ab"}


@pytest.mark.asyncio
async def test_another_project_sharing_the_prefix_is_untouched(session):
    await _file(session, "body", "notes/a/one.md")
    llm = StubEmbedder()
    await put_document(session, llm, project="q", uri="notes/a/one.md",
                       content="body", source_type="md")
    await session.commit()
    assert await rename_documents(session, project="p", uri_prefix="notes/a",
                                  new_uri_prefix="notes/b") == 1
    assert await _uris(session, "q") == {"notes/a/one.md"}


@pytest.mark.asyncio
async def test_a_rename_onto_the_prefix_it_already_holds_refuses(session):
    """It would journal one `document_updated` row per document for a call
    that moves nothing, into an append-only table."""
    _, doc = await _file(session, "body", "notes/a/one.md")
    before = await _event_count(session, doc)
    with pytest.raises(DocumentNothingToChange):
        await rename_documents(session, project="p", uri_prefix="notes/a",
                               new_uri_prefix="notes/a")
    assert await _event_count(session, doc) == before


@pytest.mark.asyncio
async def test_a_rename_into_its_own_subtree_is_order_independent(session):
    """The rows move one at a time through a unique index, so `notes/a/x`'s
    move must precede `notes/a`'s. Iterating in id order made which one went
    first a coin flip on UUID sort: the same call either raised
    `DocumentUriConflict` or produced this result."""
    await _file(session, "body", "notes/a")
    await _file(session, "body", "notes/a/x")
    assert await rename_documents(session, project="p", uri_prefix="notes/a",
                                  new_uri_prefix="notes/a/x") == 2
    assert await _uris(session, "p") == {"notes/a/x", "notes/a/x/x"}


@pytest.mark.asyncio
async def test_a_rename_out_to_an_ancestor_prefix_is_order_independent(session):
    """The mirror image: moving a subtree up, the row that must move first is
    the shallowest, not the deepest."""
    await _file(session, "body", "notes/a/x/t.md")
    await _file(session, "body", "notes/a/x/x/t.md")
    assert await rename_documents(session, project="p", uri_prefix="notes/a/x",
                                  new_uri_prefix="notes/a") == 2
    assert await _uris(session, "p") == {"notes/a/t.md", "notes/a/x/t.md"}


@pytest.mark.asyncio
async def test_a_rename_onto_an_occupied_path_refuses(session):
    await _file(session, "one", "notes/a/one.md")
    await _file(session, "two", "notes/b/one.md")
    with pytest.raises(DocumentUriConflict):
        await rename_documents(session, project="p", uri_prefix="notes/a",
                               new_uri_prefix="notes/b")


@pytest.mark.asyncio
async def test_each_renamed_document_journals_its_own_update(session):
    _, first = await _file(session, "body", "notes/a/one.md")
    _, second = await _file(session, "body", "notes/a/two.md")
    await rename_documents(session, project="p", uri_prefix="notes/a",
                           new_uri_prefix="notes/b")
    for doc in (first, second):
        row = await _latest_event(session, doc)
        assert row["event_type"] == "document_updated"
        assert row["payload"]["fields"] == ["uri"]


@pytest.mark.asyncio
async def test_the_rename_rewrites_links_and_matches_none_today(session):
    """Nothing in this tree writes `document_links` yet, so the two link
    statements are asserted to run and to affect zero rows -- manufacturing
    link rows no producer creates would test the fixture, not the code."""
    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    await _file(session, "body", "notes/a/one.md")
    statements: list[str] = []

    def _capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(Engine, "before_cursor_execute", _capture)
    try:
        await rename_documents(session, project="p", uri_prefix="notes/a",
                               new_uri_prefix="notes/b")
    finally:
        event.remove(Engine, "before_cursor_execute", _capture)

    link_updates = [s for s in statements if "UPDATE document_links" in s]
    assert len(link_updates) == 2
    remaining = (await session.execute(
        text("SELECT count(*) FROM document_links")
    )).scalar_one()
    assert remaining == 0


@pytest.mark.asyncio
async def test_a_subtree_delete_removes_every_descendant(session):
    for uri in ("notes/a", "notes/a/one.md", "notes/a/two.md", "notes/b.md"):
        await _file(session, "body", uri)
    assert await delete_documents(session, project="p", uri_prefix="notes/a") == 3
    assert await _uris(session, "p") == {"notes/b.md"}


@pytest.mark.asyncio
async def test_a_subtree_delete_does_not_over_match_a_wildcard(session):
    """`_` and `%` are LIKE metacharacters; the match must not use LIKE."""
    await _file(session, "body", "notes/a_b/one.md")
    await _file(session, "body", "notes/axb/two.md")
    assert await delete_documents(session, project="p", uri_prefix="notes/a_b") == 1
    assert await _uris(session, "p") == {"notes/axb/two.md"}


@pytest.mark.asyncio
async def test_a_subtree_delete_is_scoped_to_its_project(session):
    await _file(session, "body", "notes/a/one.md")
    llm = StubEmbedder()
    await put_document(session, llm, project="q", uri="notes/a/one.md",
                       content="body", source_type="md")
    await session.commit()
    assert await delete_documents(session, project="p", uri_prefix="notes/a") == 1
    assert await _uris(session, "q") == {"notes/a/one.md"}


@pytest.mark.asyncio
async def test_a_subtree_delete_journals_one_row_per_document(session):
    _, first = await _file(session, "body", "notes/a/one.md")
    _, second = await _file(session, "body", "notes/a/two.md")
    await delete_documents(session, project="p", uri_prefix="notes/a")
    for doc in (first, second):
        assert await _event_count(session, doc) >= 1
        row = await _latest_event(session, doc)
        assert row["event_type"] == "documents_deleted"
        assert row["payload"]["uri_prefix"] == "notes/a"
        # Write-time minimization: ids and the prefix, never content.
        assert "content" not in row["payload"]


@pytest.mark.asyncio
async def test_an_empty_prefix_is_refused(session):
    """At the SQL an empty prefix degenerates to `left(uri, 1) = '/'` and
    matches nothing, which would report a successful delete of zero rows."""
    await _file(session, "body", "notes/a/one.md")
    with pytest.raises(DocumentNothingToChange):
        await delete_documents(session, project="p", uri_prefix="")
    assert await _uris(session, "p") == {"notes/a/one.md"}


@pytest.mark.asyncio
async def test_a_subtree_delete_refuses_when_the_journal_write_fails(
    session, monkeypatch
):
    """The strict journal contract: an unaudited bulk delete must not commit."""
    await _file(session, "body", "notes/a/one.md")
    await _file(session, "body", "notes/a/two.md")

    async def _fails(*args, **kwargs):
        return False

    monkeypatch.setattr("app.services.document_door.record_event", _fails)
    with pytest.raises(DocumentJournalWriteFailed):
        await delete_documents(session, project="p", uri_prefix="notes/a")
    # The assertion that matters: a raise after the DELETE would satisfy the
    # one above and still have destroyed the subtree.
    assert await _uris(session, "p") == {"notes/a/one.md", "notes/a/two.md"}


@pytest.mark.asyncio
async def test_a_subtree_delete_journals_the_caller_identity(session):
    """The refusal above protects an audit row; these are what make it one."""
    _, doc = await _file(session, "body", "notes/a/one.md")
    key_id = uuid4()
    assert await delete_documents(
        session, project="p", uri_prefix="notes/a",
        actor="agent-key", api_key_id=key_id,
    ) == 1
    row = (await session.execute(
        text(
            "SELECT event_type, actor, CAST(api_key_id AS text) AS api_key_id "
            "FROM events WHERE object_id = CAST(:id AS uuid) "
            "ORDER BY created_at DESC, id DESC LIMIT 1"
        ),
        {"id": str(doc)},
    )).mappings().one()
    assert row["event_type"] == DOCUMENTS_DELETED_EVENT
    assert row["actor"] == "agent-key"
    assert row["api_key_id"] == str(key_id)


async def _content_hash(session, document_id):
    return (await session.execute(
        text("SELECT content_hash FROM documents WHERE id = CAST(:id AS uuid)"),
        {"id": str(document_id)},
    )).scalar_one()


async def _updated_events(session, document_id) -> int:
    return (await session.execute(
        text(
            "SELECT count(*) FROM events WHERE event_type = 'document_updated' "
            "AND object_id = CAST(:id AS uuid)"
        ),
        {"id": str(document_id)},
    )).scalar_one()


@pytest.mark.asyncio
async def test_a_matching_expected_hash_moves_the_document(session):
    _, doc = await _file(session, "# T\n\npara", "notes/h1.md")
    await update_document_metadata(
        session, document_id=doc, uri="archive/notes/h1.md",
        expected_hash=await _content_hash(session, doc),
    )
    assert (await _read(session, doc))["uri"] == "archive/notes/h1.md"
    assert await _updated_events(session, doc) == 1


@pytest.mark.asyncio
async def test_a_stale_expected_hash_refuses_and_moves_nothing(session):
    _, doc = await _file(session, "# T\n\npara", "notes/h2.md")
    current = await _content_hash(session, doc)
    with pytest.raises(DocumentHashConflict) as refused:
        await update_document_metadata(
            session, document_id=doc, uri="archive/notes/h2.md",
            expected_hash="stale",
        )
    assert refused.value.current_hash == current
    assert refused.value.expected_hash == "stale"
    assert (await _read(session, doc))["uri"] == "notes/h2.md"
    assert await _updated_events(session, doc) == 0


@pytest.mark.asyncio
async def test_an_expected_hash_against_a_missing_id_is_unresolved(session):
    with pytest.raises(DocumentTargetUnresolved):
        await update_document_metadata(
            session, document_id=uuid4(), uri="x.md", expected_hash="h",
        )


@pytest.mark.asyncio
async def test_a_tags_only_call_checks_the_hash_under_its_lock(session):
    _, doc = await _file(session, "# T\n\npara", "notes/h3.md")
    with pytest.raises(DocumentHashConflict):
        await update_document_metadata(
            session, document_id=doc, tags=["topic/x"], expected_hash="stale",
        )
    assert await _tags(session, doc) == set()
    assert await _updated_events(session, doc) == 0


@pytest.mark.asyncio
async def test_a_tags_only_call_with_a_matching_hash_writes(session):
    _, doc = await _file(session, "# T\n\npara", "notes/h4.md")
    await update_document_metadata(
        session, document_id=doc, tags=["topic/x"],
        expected_hash=await _content_hash(session, doc),
    )
    assert await _tags(session, doc) == {"topic/x"}


@pytest.mark.asyncio
async def test_an_expected_hash_alone_names_nothing_to_change(session):
    _, doc = await _file(session, "# T\n\npara", "notes/h5.md")
    with pytest.raises(DocumentNothingToChange):
        await update_document_metadata(
            session, document_id=doc,
            expected_hash=await _content_hash(session, doc),
        )


@pytest.mark.asyncio
async def test_the_update_journals_the_caller_identity(session):
    _, doc = await _file(session, "# T\n\npara", "notes/h6.md")
    key_id = uuid4()
    await update_document_metadata(
        session, document_id=doc, title="New", actor="sync-key", api_key_id=key_id,
    )
    row = (await session.execute(
        text(
            "SELECT actor, CAST(api_key_id AS text) AS api_key_id FROM events "
            "WHERE event_type = 'document_updated' AND object_id = CAST(:id AS uuid)"
        ),
        {"id": str(doc)},
    )).mappings().one()
    assert (row["actor"], row["api_key_id"]) == ("sync-key", str(key_id))
