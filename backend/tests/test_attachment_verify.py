"""Does every row have its file, and every file its row (spec §10)."""
from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text as sa_text

from app.config import settings
from app.services.attachment_verify import verify


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "attachments_dir", str(tmp_path))
    return tmp_path


async def _row(session, attachment_id) -> None:
    await session.execute(
        sa_text(
            "INSERT INTO page_attachments "
            "(id, project, filename, content_type, size_bytes, sha256) "
            "VALUES (CAST(:id AS uuid), 'default', 'f.png', 'image/png', 1, 'ab')"
        ),
        {"id": str(attachment_id)},
    )


def _file(root, attachment_id) -> None:
    shard = root / str(attachment_id)[:2]
    shard.mkdir(parents=True, exist_ok=True)
    (shard / str(attachment_id)).write_bytes(b"payload")


async def test_a_matched_pair_verifies(session, root):
    attachment_id = uuid4()
    await _row(session, attachment_id)
    _file(root, attachment_id)

    report = await verify(session)

    assert report.ok()
    assert report.missing_files == []
    assert report.rowless_files == []


async def test_a_row_without_a_file_is_reported(session, root):
    attachment_id = uuid4()
    await _row(session, attachment_id)

    report = await verify(session)

    assert not report.ok()
    assert report.missing_files == [str(attachment_id)]


async def test_a_file_without_a_row_is_reported(session, root):
    attachment_id = uuid4()
    _file(root, attachment_id)

    report = await verify(session)

    assert not report.ok()
    assert report.rowless_files == [str(attachment_id)]


async def test_an_in_flight_part_is_not_a_rowless_file(session, root):
    shard = root / "ab"
    shard.mkdir(parents=True)
    (shard / "deadbeef.part").write_bytes(b"x")

    report = await verify(session)

    assert report.ok()
