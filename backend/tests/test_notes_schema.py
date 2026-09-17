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
async def test_blocks_carry_a_search_vector_that_blanks_source_types(session):
    """The keyword arm indexes prose. Code and html text is source, and
    indexing it makes every note that mentions a function name a hit for it."""
    doc = await session.scalar(text(
        "INSERT INTO documents (id, project, uri) "
        "VALUES (gen_random_uuid(), 'notes', 'd.md') RETURNING id"
    ))
    for block_type in ("paragraph", "code", "html"):
        await session.execute(
            text("INSERT INTO blocks (id, document_id, type, text) "
                 "VALUES (gen_random_uuid(), :d, :t, 'alpha beta')"),
            {"d": doc, "t": block_type},
        )
    hits = await session.scalar(text(
        "SELECT count(*) FROM blocks "
        "WHERE search_vector @@ plainto_tsquery('english', 'alpha')"
    ))
    assert hits == 1


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


# The generated column's blanking set is a taxonomy slice living inside a DDL
# string. Nothing sweeps it: `app.taxonomy` is Python, the expression is text
# inside `op.execute`, and a vocabulary change that renames or adds a block
# type cannot reach it. Nor is the drift loud -- a stale set does not error, it
# quietly indexes source as prose (or stops indexing prose at all), and the
# only symptom is worse search.
#
# It is also the most expensive object here to change late: Postgres cannot
# ALTER a stored generated column's expression, so a correction after the
# schema freeze is DROP COLUMN + ADD COLUMN, rewriting every `blocks` row and
# rebuilding the GIN index on a table whose embedding partition is already
# most of the database.
#
# So the partition below is pinned rather than the blanked set alone. Adding a
# block type fails this test until someone puts it in one bucket, which is the
# moment to decide whether it is prose or source.
SOURCE_BLOCK_TYPES = frozenset({"code", "html"})
"""Types whose text is source, not prose. Blanked from the search vector:
indexing them makes every note mentioning a function name a hit for it."""

PROSE_BLOCK_TYPES = frozenset({
    "paragraph", "heading", "list", "quote", "table", "table_row", "divider",
    "todo", "toggle", "callout",
})
"""Types whose text is prose. Indexed."""


def _blanked_types_in_the_generation_expression(expression: str) -> frozenset[str]:
    """The block types the stored expression actually blanks.

    Postgres normalises the DDL's `type IN ('code', 'html')` to
    `type = ANY (ARRAY['code'::text, 'html'::text])`, so the literals are read
    out of the CASE's WHEN clause rather than matched against the SQL we wrote
    -- what is asserted is what the database stored, not what the file says.
    """
    import re

    whens = re.findall(r"WHEN(.*?)THEN", expression, re.DOTALL | re.IGNORECASE)
    assert len(whens) == 1, (
        f"expected a single-branch CASE, found {len(whens)} WHEN clauses: "
        f"{expression}"
    )
    return frozenset(re.findall(r"'([^']*)'", whens[0]))


def test_the_block_type_vocabulary_is_partitioned_into_prose_and_source():
    """Every block type is classified, so adding one cannot skip the decision."""
    from app.taxonomy import BLOCK_TYPES, PAGE_BLOCK_TYPES

    assert not (SOURCE_BLOCK_TYPES & PROSE_BLOCK_TYPES), (
        "a block type cannot be both prose and source"
    )
    assert SOURCE_BLOCK_TYPES | PROSE_BLOCK_TYPES == set(BLOCK_TYPES) | set(PAGE_BLOCK_TYPES), (
        "the block-type vocabulary moved without the search-vector partition "
        "moving with it. Put each new or renamed type in SOURCE_BLOCK_TYPES "
        "or PROSE_BLOCK_TYPES, and if it lands in the source bucket, change "
        "the generated column in 0001_baseline.py too -- which, after the "
        "schema freeze, is a DROP COLUMN and a full table rewrite."
    )


@pytest.mark.asyncio
async def test_the_search_vector_blanks_exactly_the_source_types(session):
    """Read the blanking set out of the catalogue and pin it to the taxonomy."""
    from app.taxonomy import BLOCK_TYPES

    expression = await session.scalar(text(
        "SELECT generation_expression FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = 'blocks' "
        "AND column_name = 'search_vector'"
    ))
    assert expression, "blocks.search_vector is not a generated column"

    blanked = _blanked_types_in_the_generation_expression(expression)

    unknown = blanked - set(BLOCK_TYPES)
    assert not unknown, (
        f"the generated column blanks {sorted(unknown)}, which are not in "
        "app.taxonomy.BLOCK_TYPES -- a renamed block type left the DDL string "
        "behind, so those blocks are now indexed as prose"
    )
    assert blanked == SOURCE_BLOCK_TYPES, (
        f"the generated column blanks {sorted(blanked)} but the design blanks "
        f"{sorted(SOURCE_BLOCK_TYPES)}"
    )
