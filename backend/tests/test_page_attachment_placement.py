from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

from app.config import settings
from app.services.page_attachments import (
    attachment_path,
    insert_attachment_row,
    place_staged,
)


def test_place_staged_moves_the_file_onto_its_sharded_path(tmp_path, monkeypatch):
    root = tmp_path / "attachments"
    monkeypatch.setattr(settings, "attachments_dir", str(root))
    staged = tmp_path / "staged.bin"
    staged.write_bytes(b"payload")
    attachment_id = uuid4()

    place_staged(staged, attachment_id)

    final = attachment_path(attachment_id)
    assert final.is_file()
    assert final.read_bytes() == b"payload"
    assert final.parent.name == str(attachment_id)[:2]
    assert not staged.exists()


def test_place_staged_creates_the_shard_directory(tmp_path, monkeypatch):
    root = tmp_path / "attachments"
    monkeypatch.setattr(settings, "attachments_dir", str(root))
    staged = tmp_path / "staged.bin"
    staged.write_bytes(b"x")
    attachment_id = uuid4()
    assert not attachment_path(attachment_id).parent.exists()

    place_staged(staged, attachment_id)

    assert attachment_path(attachment_id).is_file()


@pytest.mark.asyncio
async def test_insert_attachment_row_does_not_commit(session, monkeypatch):
    # The conftest session runs inside an outer transaction that DROPS a
    # commit() and whose rollback() ends the isolation boundary outright, so
    # "write, roll back, look for the row" proves nothing here. Spy instead.
    calls: list[int] = []
    original = session.commit

    async def spy() -> None:
        calls.append(1)
        await original()

    monkeypatch.setattr(session, "commit", spy)
    await insert_attachment_row(
        session,
        attachment_id=uuid4(),
        project="notes",
        page_id=None,
        filename="a.png",
        content_type="image/png",
        size_bytes=7,
        sha256="ab" * 32,
    )
    assert calls == [], "the helper committed; the import needs one transaction"


@pytest.mark.asyncio
async def test_insert_attachment_row_accepts_a_null_page(session):
    attachment_id = uuid4()
    await insert_attachment_row(
        session,
        attachment_id=attachment_id,
        project="notes",
        page_id=None,
        filename="a.bin",
        content_type="application/octet-stream",
        size_bytes=1,
        sha256="cd" * 32,
    )
    row = (
        await session.execute(
            text(
                "SELECT uploaded_for_page_id, project, filename "
                "FROM page_attachments WHERE id = CAST(:id AS uuid)"
            ),
            {"id": str(attachment_id)},
        )
    ).one()
    assert row.uploaded_for_page_id is None
    assert row.project == "notes"
    assert row.filename == "a.bin"
