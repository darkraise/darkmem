"""The attachment cleanup job's three arms."""
from __future__ import annotations

import os
import time
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.config import settings
from app.services.page_attachment_cleanup import run_cleanup
from app.services.page_attachments import attachment_path, attachment_url

PAGE = "22222222-2222-2222-2222-222222222222"
OTHER_PAGE = "44444444-4444-4444-4444-444444444444"


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "attachments_dir", str(tmp_path))
    return tmp_path


def _age(path, seconds: float) -> None:
    past = time.time() - seconds
    os.utime(path, (past, past))


async def _pages(session, *, trashed: bool = False) -> None:
    for page_id, project in ((PAGE, "p"), (OTHER_PAGE, "q")):
        await session.execute(text(
            "INSERT INTO pages (id, project, order_index, content_hash, deleted_at) "
            f"VALUES ('{page_id}', '{project}', 0, 'h', "
            f"{'now()' if trashed and page_id == PAGE else 'NULL'})"
        ))


async def _attachment(session, *, age_hours: float, project: str = "p"):
    attachment_id = uuid4()
    path = attachment_path(attachment_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"data")
    await session.execute(text(
        "INSERT INTO page_attachments (id, project, filename, content_type, "
        "size_bytes, sha256, created_at) VALUES (CAST(:id AS uuid), :project, "
        "'a.bin', 'application/octet-stream', 4, 'x', "
        "now() - make_interval(secs => :age))"
    ), {"id": str(attachment_id), "project": project, "age": age_hours * 3600})
    return attachment_id


async def _block(session, page_id: str, body: str) -> None:
    await session.execute(text(
        "INSERT INTO blocks (id, page_id, order_index, type, text) "
        "VALUES (gen_random_uuid(), CAST(:page AS uuid), 0, 'paragraph', :text)"
    ), {"page": page_id, "text": body})


async def _row_exists(session, attachment_id) -> bool:
    return (await session.execute(text(
        "SELECT EXISTS (SELECT 1 FROM page_attachments WHERE id = CAST(:id AS uuid))"
    ), {"id": str(attachment_id)})).scalar_one()


async def test_unreferenced_old_rows_and_files_go(session, session_factory, root):
    await _pages(session)
    old = await _attachment(session, age_hours=200)
    report = await run_cleanup(session_factory, grace_hours=168, staging_max_age_hours=6)
    assert report.rows_deleted == 1 and report.files_unlinked == 1
    assert not await _row_exists(session, old)
    assert not attachment_path(old).exists()


async def test_young_unreferenced_rows_stay(session, session_factory, root):
    await _pages(session)
    young = await _attachment(session, age_hours=1)
    await run_cleanup(session_factory, grace_hours=168, staging_max_age_hours=6)
    assert await _row_exists(session, young)


async def test_referenced_rows_stay_including_from_trash_and_other_projects(
    session, session_factory, root,
):
    await _pages(session, trashed=True)
    in_trash = await _attachment(session, age_hours=200)
    pasted = await _attachment(session, age_hours=200)
    in_table = await _attachment(session, age_hours=200)
    await _block(session, PAGE, f"![a]({attachment_url(in_trash)})")
    await _block(session, OTHER_PAGE, f"see [f]({attachment_url(pasted)}) here")
    await _block(
        session, OTHER_PAGE,
        f"cell | ![x](/api/v1/pages/attachments/{str(in_table).upper()})",
    )
    report = await run_cleanup(session_factory, grace_hours=168, staging_max_age_hours=6)
    assert report.rows_deleted == 0
    for attachment_id in (in_trash, pasted, in_table):
        assert await _row_exists(session, attachment_id)


async def test_a_document_block_does_not_keep_an_attachment(session, session_factory, root):
    await _pages(session)
    old = await _attachment(session, age_hours=200)
    await session.execute(text(
        "INSERT INTO documents (id, project, uri, content_hash) "
        "VALUES ('11111111-1111-1111-1111-111111111111', 'p', 'a.md', 'h')"
    ))
    await session.execute(text(
        "INSERT INTO blocks (id, document_id, order_index, type, text) VALUES "
        "(gen_random_uuid(), '11111111-1111-1111-1111-111111111111', 0, "
        "'paragraph', :t)"
    ), {"t": attachment_url(old)})
    await run_cleanup(session_factory, grace_hours=168, staging_max_age_hours=6)
    assert not await _row_exists(session, old)


async def test_old_rowless_files_and_parts_go_young_ones_stay(session_factory, root):
    old_orphan = attachment_path(uuid4())
    young_orphan = attachment_path(uuid4())
    old_part = attachment_path(uuid4()).with_suffix(".part")
    for path in (old_orphan, young_orphan, old_part):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x")
    _age(old_orphan, 7200)
    _age(old_part, 7200)
    stray = root / "notes.txt"
    stray.write_bytes(b"x")
    _age(stray, 7200)
    report = await run_cleanup(session_factory, grace_hours=168, staging_max_age_hours=6)
    assert not old_orphan.exists() and not old_part.exists()
    assert young_orphan.exists() and stray.exists()
    assert report.rowless_files_removed == 1 and report.part_files_removed == 1


async def test_a_file_with_a_row_is_never_rowless(session, session_factory, root):
    await _pages(session)
    kept = await _attachment(session, age_hours=1)
    _age(attachment_path(kept), 7200)
    await run_cleanup(session_factory, grace_hours=168, staging_max_age_hours=6)
    assert attachment_path(kept).exists()


async def test_stale_staging_dirs_go(session_factory, root):
    staging = root / ".staging"
    old = staging / "old"
    young = staging / "young"
    for directory in (old, young):
        directory.mkdir(parents=True)
        (directory / "upload.zip").write_bytes(b"x")
    _age(old, 7 * 3600)
    report = await run_cleanup(session_factory, grace_hours=168, staging_max_age_hours=6)
    assert not old.exists() and young.exists()
    assert report.staging_dirs_removed == 1


async def test_a_clean_tree_reports_nothing(session_factory, root):
    report = await run_cleanup(session_factory, grace_hours=168, staging_max_age_hours=6)
    assert report.total() == 0
