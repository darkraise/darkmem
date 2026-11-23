from __future__ import annotations

import asyncio
import errno
from pathlib import Path

import pytest
from sqlalchemy import text

from app.config import settings
from app.services.page_import import (
    ImportBusy,
    ImportNoSpace,
    ImportTimedOut,
    ImportTooLarge,
    import_notion_export,
)
from tests.fixtures.notion.builder import (
    DATABASE_EXPORT,
    FLAT_EXPORT,
    PNG,
    Entry,
    build_fixture,
)


@pytest.fixture
def attachments_dir(tmp_path, monkeypatch):
    root = tmp_path / "attachments"
    root.mkdir()
    monkeypatch.setattr(settings, "attachments_dir", str(root))
    return root


async def _body(path: Path, chunk: int = 4096):
    data = path.read_bytes()
    for start in range(0, len(data), chunk):
        yield data[start:start + chunk]


async def _run(session, tmp_path, entries=FLAT_EXPORT, project="notes",
               declared: bool = True):
    path = build_fixture(entries, tmp_path / "export.zip")
    return await import_notion_export(
        session, project=project, body=_body(path),
        declared_length=path.stat().st_size if declared else None,
        actor="tester",
    )


def _staging_is_clean(attachments_dir: Path) -> bool:
    staging = attachments_dir / ".staging"
    return not staging.exists() or not list(staging.iterdir())


@pytest.mark.asyncio
async def test_an_import_creates_the_root_and_its_pages(session, attachments_dir, tmp_path):
    report = await _run(session, tmp_path)
    title = (
        await session.execute(
            text("SELECT title FROM pages WHERE id = CAST(:id AS uuid)"),
            {"id": str(report.root_page_id)},
        )
    ).scalar_one()
    assert title.startswith("Notion import — ")
    assert report.pages_created == 6
    total = (
        await session.execute(
            text("SELECT count(*) FROM pages WHERE project = 'notes'")
        )
    ).scalar_one()
    assert total == report.pages_created + 1


@pytest.mark.asyncio
async def test_the_root_page_is_not_counted(session, attachments_dir, tmp_path):
    report = await _run(session, tmp_path)
    children = (
        await session.execute(
            text("SELECT count(*) FROM pages WHERE parent_id = CAST(:id AS uuid)"),
            {"id": str(report.root_page_id)},
        )
    ).scalar_one()
    assert children >= 1
    assert report.pages_created == 6


@pytest.mark.asyncio
async def test_attachments_are_stored_once_with_a_row_and_a_file(
    session, attachments_dir, tmp_path
):
    report = await _run(session, tmp_path)
    assert report.attachments_stored == 1
    assert report.attachment_bytes > 0
    rows = (
        await session.execute(
            text("SELECT id, content_type FROM page_attachments WHERE project = 'notes'")
        )
    ).all()
    assert len(rows) == 1
    assert rows[0].content_type == "image/png"
    shard = attachments_dir / str(rows[0].id)[:2] / str(rows[0].id)
    assert shard.is_file()


@pytest.mark.asyncio
async def test_a_reference_style_image_is_stored_and_linked(
    session, attachments_dir, tmp_path
):
    entries = [
        Entry("A 00000000000000000000000000000001.md",
              b"# A\n\n![shot][pic]\n\n[pic]: image.png\n"),
        Entry("image.png", PNG),
    ]
    report = await _run(session, tmp_path, entries=entries)
    assert report.attachments_stored == 1
    assert [w for w in report.warnings if w.kind == "missing_file"] == []
    content = (
        await session.execute(
            text("SELECT content FROM pages WHERE title = 'A'")
        )
    ).scalar_one()
    assert "/api/v1/pages/attachments/" in content


@pytest.mark.asyncio
async def test_an_unstaged_export_file_is_warned_about(
    session, attachments_dir, tmp_path, monkeypatch
):
    # A link the reference scan cannot reach still points at a file the export
    # holds; the rewrite used to assume the stager had reported it.
    from app.services import page_import

    monkeypatch.setattr(page_import, "scan_links", lambda _source: [])
    entries = [
        Entry("A 00000000000000000000000000000001.md",
              b"# A\n\n![shot](image.png)\n"),
        Entry("image.png", PNG),
    ]
    report = await _run(session, tmp_path, entries=entries)
    assert report.attachments_stored == 0
    assert [w.kind for w in report.warnings] == ["missing_file"]


@pytest.mark.asyncio
async def test_an_oversize_attachment_is_warned_about_once(
    session, attachments_dir, tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "attachment_max_bytes", 1)
    entries = [
        Entry("A 00000000000000000000000000000001.md",
              b"# A\n\n![shot](image.png)\n"),
        Entry("image.png", PNG),
    ]
    report = await _run(session, tmp_path, entries=entries)
    assert [w.kind for w in report.warnings] == ["oversize_attachment"]


@pytest.mark.asyncio
async def test_an_attachment_two_pages_share_is_stored_once(
    session, attachments_dir, tmp_path
):
    entries = [
        Entry("A 00000000000000000000000000000001.md", b"# A\n\n![shot](image.png)\n"),
        Entry("B 00000000000000000000000000000002.md", b"# B\n\n![shot](image.png)\n"),
        Entry("image.png", PNG),
    ]
    report = await _run(session, tmp_path, entries=entries)
    assert report.attachments_stored == 1
    rows = (
        await session.execute(
            text("SELECT id FROM page_attachments WHERE project = 'notes'")
        )
    ).scalars().all()
    assert len(rows) == 1
    assert len([p for p in attachments_dir.rglob("*") if p.is_file()]) == 1
    contents = (
        await session.execute(
            text("SELECT content FROM pages WHERE title IN ('A', 'B') ORDER BY title")
        )
    ).scalars().all()
    url = f"/api/v1/pages/attachments/{rows[0]}"
    assert [url in c for c in contents] == [True, True]


@pytest.mark.asyncio
async def test_the_journal_records_one_import(session, attachments_dir, tmp_path):
    report = await _run(session, tmp_path)
    payload = (
        await session.execute(
            text(
                "SELECT payload FROM events WHERE event_type = 'pages_imported' "
                "AND object_id = CAST(:id AS uuid)"
            ),
            {"id": str(report.root_page_id)},
        )
    ).scalar_one()
    assert payload["pages_created"] == report.pages_created
    assert "title" not in payload and "path" not in payload


@pytest.mark.asyncio
async def test_the_staging_directory_is_removed_on_success(
    session, attachments_dir, tmp_path
):
    await _run(session, tmp_path)
    assert _staging_is_clean(attachments_dir)


@pytest.mark.asyncio
async def test_a_failure_in_the_write_rolls_back_and_unlinks(
    session, attachments_dir, tmp_path, monkeypatch
):
    # The test must not roll back itself: the conftest session's rollback ends
    # the isolation boundary, and re-reading `pages` afterwards would report 0
    # whether or not the import rolled back — a stub with no `except` passes it.
    from app.services import page_import

    rollbacks: list[int] = []
    original = session.rollback

    async def spy() -> None:
        rollbacks.append(1)
        await original()

    async def boom(*args, **kwargs):
        raise RuntimeError("injected")

    monkeypatch.setattr(session, "rollback", spy)
    monkeypatch.setattr(page_import, "_insert_page", boom)
    with pytest.raises(RuntimeError):
        await _run(session, tmp_path)

    assert rollbacks, "the import swallowed the failure without rolling back"
    placed = [p for p in attachments_dir.rglob("*") if p.is_file()]
    assert placed == [], "a placed attachment file survived the failure"
    assert _staging_is_clean(attachments_dir)


@pytest.mark.asyncio
async def test_a_failure_between_files_and_rows_leaves_no_final_file(
    session, attachments_dir, tmp_path, monkeypatch
):
    # The rows are written after the files, so this is the window in which a
    # file exists with no row. The other failure test injects at `_insert_page`,
    # which is past it.
    from app.services import page_import

    rollbacks: list[int] = []
    original = session.rollback

    async def spy() -> None:
        rollbacks.append(1)
        await original()

    async def boom(*args, **kwargs):
        raise RuntimeError("injected")

    monkeypatch.setattr(session, "rollback", spy)
    monkeypatch.setattr(page_import, "insert_attachment_row", boom)
    with pytest.raises(RuntimeError):
        await _run(session, tmp_path)

    assert rollbacks, "the import swallowed the failure without rolling back"
    survivors = [
        p for p in attachments_dir.rglob("*")
        if p.is_file() and ".staging" not in p.parts
    ]
    assert survivors == [], "a placed attachment file survived the failure"
    assert _staging_is_clean(attachments_dir)


@pytest.mark.asyncio
async def test_a_second_import_is_refused_while_one_runs(session, attachments_dir, tmp_path):
    from app.services import page_import

    released = asyncio.Event()

    async def blocker():
        async with page_import._import_lock:
            await released.wait()

    holder = asyncio.create_task(blocker())
    await asyncio.sleep(0)
    try:
        with pytest.raises(ImportBusy):
            await _run(session, tmp_path)
    finally:
        released.set()
        await holder


@pytest.mark.asyncio
async def test_a_body_over_the_ceiling_is_refused(
    session, attachments_dir, tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "notion_import_max_bytes", 64)
    with pytest.raises(ImportTooLarge):
        await _run(session, tmp_path)


@pytest.mark.asyncio
async def test_a_declared_length_over_the_ceiling_is_refused_before_the_body(
    session, attachments_dir, tmp_path, monkeypatch
):
    # The free-space stub would answer first if the order were the other way
    # round, so this pins which refusal a caller gets as well as that the body
    # is never read.
    from app.services import page_import

    monkeypatch.setattr(settings, "notion_import_max_bytes", 64)
    monkeypatch.setattr(
        page_import.shutil, "disk_usage",
        lambda _: type("U", (), {"total": 1, "used": 1, "free": 1})(),
    )
    read: list[int] = []

    async def body():
        read.append(1)
        yield b"x"

    with pytest.raises(ImportTooLarge):
        await import_notion_export(
            session, project="notes", body=body(),
            declared_length=10_000, actor="tester",
        )
    assert read == []


@pytest.mark.asyncio
async def test_placed_files_are_preserved_when_the_rollback_fails(
    session, attachments_dir, tmp_path, monkeypatch
):
    from app.services import page_import

    async def boom(*args, **kwargs):
        raise RuntimeError("injected")

    async def broken_connection():
        raise RuntimeError("the connection is gone")

    monkeypatch.setattr(page_import, "_insert_page", boom)
    monkeypatch.setattr(session, "rollback", broken_connection)
    with pytest.raises(RuntimeError):
        await _run(session, tmp_path)

    survivors = [
        p for p in attachments_dir.rglob("*")
        if p.is_file() and ".staging" not in p.parts
    ]
    assert len(survivors) == 1


@pytest.mark.asyncio
async def test_a_failed_withdrawal_rollback_keeps_the_import_error(
    session, attachments_dir, tmp_path, monkeypatch
):
    from app.services import page_import

    async def invalid(*args, **kwargs):
        raise page_import.NotionExportInvalid("injected")

    real_execute, real_rollback = session.execute, session.rollback
    rollbacks: list[int] = []

    async def execute(statement, *args, **kwargs):
        if statement is page_import._DELETE_ATTACHMENTS:
            raise RuntimeError("the connection is gone")
        return await real_execute(statement, *args, **kwargs)

    async def rollback():
        rollbacks.append(1)
        if len(rollbacks) > 1:
            raise RuntimeError("the connection is gone")
        await real_rollback()

    monkeypatch.setattr(page_import, "_insert_page", invalid)
    monkeypatch.setattr(session, "execute", execute)
    monkeypatch.setattr(session, "rollback", rollback)
    with pytest.raises(page_import.NotionExportInvalid):
        await _run(session, tmp_path)
    assert len(rollbacks) == 2


@pytest.mark.asyncio
async def test_insufficient_space_is_refused_before_the_upload(
    session, attachments_dir, tmp_path, monkeypatch
):
    from app.services import page_import

    monkeypatch.setattr(
        page_import.shutil, "disk_usage",
        lambda _: type("U", (), {"total": 1, "used": 1, "free": 1})(),
    )
    with pytest.raises(ImportNoSpace):
        await _run(session, tmp_path)


@pytest.mark.asyncio
async def test_insufficient_space_is_refused_after_the_upload(
    session, attachments_dir, tmp_path, monkeypatch
):
    from app.services import page_import

    monkeypatch.setattr(
        page_import.shutil, "disk_usage",
        lambda _: type("U", (), {"total": 1, "used": 1, "free": 1})(),
    )
    with pytest.raises(ImportNoSpace):
        await _run(session, tmp_path, declared=False)
    assert _staging_is_clean(attachments_dir)


@pytest.mark.asyncio
async def test_a_full_disk_while_staging_is_refused_as_no_space(
    session, attachments_dir, tmp_path, monkeypatch
):
    from app.services import page_import

    class _FullDisk:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def write(self, data):
            raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(
        page_import, "open", lambda *a, **k: _FullDisk(), raising=False
    )
    with pytest.raises(ImportNoSpace):
        await _run(session, tmp_path)
    assert _staging_is_clean(attachments_dir)


@pytest.mark.asyncio
async def test_warnings_are_capped_and_counted(
    session, attachments_dir, tmp_path, monkeypatch
):
    from app.services import page_import

    monkeypatch.setattr(page_import, "MAX_WARNINGS", 2)
    body = "\n\n".join(f"![m{i}](gone{i}.png)" for i in range(6))
    entries = [
        Entry("A 00000000000000000000000000000001.md", f"# A\n\n{body}\n".encode("utf-8")),
    ]
    report = await _run(session, tmp_path, entries=entries)
    assert len(report.warnings) == 2
    assert report.warnings_omitted == 4


@pytest.mark.asyncio
async def test_the_hierarchy_summary_survives_the_warning_cap(
    session, attachments_dir, tmp_path, monkeypatch
):
    from app.services import page_import

    monkeypatch.setattr(page_import, "MAX_WARNINGS", 1)
    report = await _run(session, tmp_path)
    assert [w.kind for w in report.warnings] == ["derived_hierarchy"]
    assert report.warnings_omitted >= 1


@pytest.mark.asyncio
async def test_the_hierarchy_summary_names_each_signal(
    session, attachments_dir, tmp_path
):
    report = await _run(session, tmp_path)
    summary = next(w for w in report.warnings if w.kind == "derived_hierarchy")
    assert summary.path is None
    assert "by database membership" in summary.detail


@pytest.mark.asyncio
async def test_a_database_page_and_its_rows_land_under_the_root(
    session, attachments_dir, tmp_path
):
    report = await _run(session, tmp_path, entries=DATABASE_EXPORT)
    assert report.databases == 2
    rows = (
        await session.execute(
            text(
                "SELECT p.title FROM pages p JOIN pages parent "
                "ON p.parent_id = parent.id WHERE parent.title = 'Board'"
            )
        )
    ).scalars().all()
    assert rows == ["Ship"]


@pytest.mark.asyncio
async def test_pages_keep_their_notion_id(session, attachments_dir, tmp_path):
    await _run(session, tmp_path)
    found = (
        await session.execute(
            text(
                "SELECT properties->>'notion_id' AS nid FROM pages "
                "WHERE title = 'Home'"
            )
        )
    ).scalar_one()
    assert found == "0" * 31 + "1"


@pytest.mark.asyncio
async def test_the_deadline_refuses_and_leaves_nothing_behind(
    session, attachments_dir, tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "notion_import_max_seconds", 0)
    with pytest.raises(ImportTimedOut):
        await _run(session, tmp_path)

    assert _staging_is_clean(attachments_dir)
    survivors = [
        p for p in attachments_dir.rglob("*")
        if p.is_file() and ".staging" not in p.parts
    ]
    assert survivors == [], "a placed attachment file survived the deadline"
