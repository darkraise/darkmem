"""The page_attachments table's shape."""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

PAGE = "22222222-2222-2222-2222-222222222222"
ATTACHMENT = "33333333-3333-3333-3333-333333333333"


async def _page(session) -> None:
    await session.execute(text(
        "INSERT INTO pages (id, project, order_index, content_hash) "
        f"VALUES ('{PAGE}', 'p', 0, 'h')"
    ))


async def _attachment(session, **overrides) -> None:
    row = {
        "id": ATTACHMENT, "project": "p", "page": PAGE, "filename": "a.png",
        "content_type": "image/png", "size_bytes": 3, "sha256": "x" * 64,
    }
    row.update(overrides)
    await session.execute(text(
        "INSERT INTO page_attachments (id, project, uploaded_for_page_id, "
        "filename, content_type, size_bytes, sha256) VALUES (CAST(:id AS uuid), "
        ":project, CAST(:page AS uuid), :filename, :content_type, :size_bytes, "
        ":sha256)"
    ), row)


async def test_purging_the_page_keeps_the_attachment(session):
    """Ownership is the project's: the page link is provenance only."""
    await _page(session)
    await _attachment(session)
    await session.execute(text(f"DELETE FROM pages WHERE id = '{PAGE}'"))
    page = (await session.execute(text(
        "SELECT uploaded_for_page_id FROM page_attachments "
        f"WHERE id = '{ATTACHMENT}'"
    ))).scalar_one()
    assert page is None


async def test_created_at_defaults(session):
    await _page(session)
    await _attachment(session)
    created = (await session.execute(text(
        f"SELECT created_at FROM page_attachments WHERE id = '{ATTACHMENT}'"
    ))).scalar_one()
    assert created is not None


@pytest.mark.parametrize("filename", ["", "x" * 256])
async def test_filename_is_bounded(session, filename):
    await _page(session)
    with pytest.raises(IntegrityError, match="chk_page_attachments_filename"):
        async with session.begin_nested():
            await _attachment(session, filename=filename)


async def test_size_is_not_negative(session):
    await _page(session)
    with pytest.raises(IntegrityError, match="chk_page_attachments_size"):
        async with session.begin_nested():
            await _attachment(session, size_bytes=-1)


async def test_no_project_foreign_key(session):
    """Every scoped table keeps a bare project column; projects register lazily."""
    await _attachment(session, project="never-registered", page=None)
