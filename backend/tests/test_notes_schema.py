"""The schema objects the personal notes workspace is built on.

Asserted against the live test database rather than against the baseline's
text, because what matters is what `alembic upgrade head` actually produced.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_projects_carries_an_enforced_personal_singleton(session):
    await session.execute(text(
        "INSERT INTO projects (name, kind) VALUES ('notes', 'personal')"
    ))
    # The database refuses a second personal space. This is the whole reason
    # `kind` is a column rather than a `properties` label.
    with pytest.raises(Exception):
        await session.execute(text(
            "INSERT INTO projects (name, kind) VALUES ('other', 'personal')"
        ))


@pytest.mark.asyncio
async def test_kind_defaults_to_project_and_is_constrained(session):
    await session.execute(text("INSERT INTO projects (name) VALUES ('p1')"))
    kind = await session.scalar(
        text("SELECT kind FROM projects WHERE name = 'p1'")
    )
    assert kind == "project"
    with pytest.raises(Exception):
        await session.execute(text(
            "INSERT INTO projects (name, kind) VALUES ('p2', 'nonsense')"
        ))


@pytest.mark.asyncio
async def test_a_link_survives_its_target_being_deleted(session):
    """An unresolved link is a first-class stub, so losing the target must
    null the pointer rather than delete the row -- otherwise deleting a note
    silently erases every backlink to it instead of showing them as stubs."""
    doc_a = await session.scalar(text(
        "INSERT INTO documents (id, project, uri) "
        "VALUES (gen_random_uuid(), 'notes', 'a.md') RETURNING id"
    ))
    doc_b = await session.scalar(text(
        "INSERT INTO documents (id, project, uri) "
        "VALUES (gen_random_uuid(), 'notes', 'b.md') RETURNING id"
    ))
    await session.execute(
        text(
            "INSERT INTO document_links "
            "(id, source_document_id, target_document_id, target_uri) "
            "VALUES (gen_random_uuid(), :a, :b, 'b.md')"
        ),
        {"a": doc_a, "b": doc_b},
    )
    await session.execute(
        text("DELETE FROM documents WHERE id = :b"), {"b": doc_b}
    )
    row = (await session.execute(text(
        "SELECT source_document_id, target_document_id, target_uri "
        "FROM document_links"
    ))).one()
    assert row.source_document_id == doc_a
    assert row.target_document_id is None
    assert row.target_uri == "b.md"


@pytest.mark.asyncio
async def test_deleting_a_document_takes_its_links_tags_and_revisions(session):
    doc = await session.scalar(text(
        "INSERT INTO documents (id, project, uri) "
        "VALUES (gen_random_uuid(), 'notes', 'c.md') RETURNING id"
    ))
    # An outbound link to a note that does not exist yet, so the row can only
    # go by the SOURCE-side cascade. Test 3 above pins the target side, where
    # the row survives; nothing else pins this side, where it must not.
    await session.execute(
        text("INSERT INTO document_links "
             "(id, source_document_id, target_document_id, target_uri) "
             "VALUES (gen_random_uuid(), :d, NULL, 'nowhere.md')"),
        {"d": doc},
    )
    tag = await session.scalar(text(
        "INSERT INTO tags (name) VALUES ('t1') RETURNING id"
    ))
    await session.execute(
        text("INSERT INTO document_tags (document_id, tag_id) "
             "VALUES (:d, :t)"),
        {"d": doc, "t": tag},
    )
    await session.execute(
        text("INSERT INTO document_revisions "
             "(id, document_id, content, content_hash) "
             "VALUES (gen_random_uuid(), :d, 'x', 'h')"),
        {"d": doc},
    )
    await session.execute(text("DELETE FROM documents WHERE id = :d"), {"d": doc})
    assert await session.scalar(text("SELECT count(*) FROM document_links")) == 0
    assert await session.scalar(text("SELECT count(*) FROM document_tags")) == 0
    assert await session.scalar(
        text("SELECT count(*) FROM document_revisions")
    ) == 0


@pytest.mark.asyncio
async def test_document_revisions_record_who_filed_and_page_newest_first(session):
    columns = {
        name: (data_type, nullable)
        for name, data_type, nullable in (await session.execute(text(
            "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'document_revisions'"
        ))).all()
    }
    assert columns["actor"] == ("text", "YES")
    assert columns["api_key_id"] == ("uuid", "YES")
    index = await session.scalar(text(
        "SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_document_revisions_document'"
    ))
    assert index.endswith("(document_id, created_at DESC, id DESC)")


@pytest.mark.asyncio
async def test_documents_can_be_pinned_and_ordered_by_recency(session):
    await session.execute(text(
        "INSERT INTO documents (id, project, uri, pinned_at) "
        "VALUES (gen_random_uuid(), 'notes', 'e.md', now())"
    ))
    pinned = await session.scalar(text(
        "SELECT count(*) FROM documents WHERE pinned_at IS NOT NULL"
    ))
    assert pinned == 1
    # The recents read is (project, updated_at); assert the index exists so a
    # later reader is not doing a seq scan over the corpus.
    assert await session.scalar(text(
        "SELECT count(*) FROM pg_indexes "
        "WHERE tablename = 'documents' AND indexname = 'ix_documents_project_updated'"
    )) == 1


@pytest.mark.asyncio
async def test_blocks_carry_no_search_vector(session):
    """Nothing read the keyword column or its GIN index; block retrieval is
    cosine-only, so both are dropped rather than kept current on every write."""
    column = await session.scalar(text(
        "SELECT count(*) FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = 'blocks' "
        "AND column_name = 'search_vector'"
    ))
    index = await session.scalar(text(
        "SELECT count(*) FROM pg_indexes WHERE indexname = 'ix_blocks_search_vector'"
    ))
    assert (column, index) == (0, 0)
