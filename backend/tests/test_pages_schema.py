"""The schema half of the isolation guarantee.

`documents` must be unaffected by pages existing. These assertions are about
the shape that makes that true, not about behaviour -- behaviour is Task 13.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


async def test_a_block_must_have_exactly_one_owner(session):
    """Dropping NOT NULL from document_id does not weaken documents: a block
    with no owner is still refused, now by the CHECK rather than by NOT NULL."""
    with pytest.raises(IntegrityError, match="blocks_exactly_one_owner"):
        async with session.begin_nested():
            await session.execute(text(
                "INSERT INTO blocks (id, type, text) "
                "VALUES (gen_random_uuid(), 'paragraph', 'orphan')"
            ))


async def test_a_block_cannot_have_both_owners(session):
    await session.execute(text(
        "INSERT INTO documents (id, project, uri, content_hash) "
        "VALUES ('11111111-1111-1111-1111-111111111111', 'p', 'a.md', 'h')"
    ))
    await session.execute(text(
        "INSERT INTO pages (id, project, order_index, content_hash) "
        "VALUES ('22222222-2222-2222-2222-222222222222', 'p', 0, 'h')"
    ))
    with pytest.raises(IntegrityError, match="blocks_exactly_one_owner"):
        async with session.begin_nested():
            await session.execute(text(
                "INSERT INTO blocks (id, document_id, page_id, type, text) VALUES ("
                "gen_random_uuid(), "
                "'11111111-1111-1111-1111-111111111111', "
                "'22222222-2222-2222-2222-222222222222', 'paragraph', 'both')"
            ))


async def test_a_page_parent_must_be_in_the_same_project(session):
    """The composite FK is what makes a cross-project reparent impossible in
    the schema rather than merely refused at the door."""
    await session.execute(text(
        "INSERT INTO pages (id, project, order_index, content_hash) "
        "VALUES ('33333333-3333-3333-3333-333333333333', 'alpha', 0, 'h')"
    ))
    with pytest.raises(IntegrityError, match="fk_pages_parent"):
        async with session.begin_nested():
            await session.execute(text(
                "INSERT INTO pages (id, project, parent_id, order_index, content_hash) "
                "VALUES (gen_random_uuid(), 'beta', "
                "'33333333-3333-3333-3333-333333333333', 0, 'h')"
            ))


async def test_the_document_block_indexes_survive(session):
    """An earlier draft of the spec showed the CREATE TABLE without these two,
    which would have seq-scanned every subtree delete and dropped keyword
    search's index."""
    rows = (await session.execute(text(
        "SELECT indexname FROM pg_indexes WHERE tablename = 'blocks'"
    ))).scalars().all()
    for name in (
        "ix_blocks_document_order",
        "ix_blocks_page_order",
        "ix_blocks_parent",
        "ix_blocks_search_vector",
    ):
        assert name in rows, f"{name} is missing"
