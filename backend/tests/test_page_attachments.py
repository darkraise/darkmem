"""Attachment bytes on disk and their row."""
from __future__ import annotations

import asyncio
import hashlib
import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.services import page_attachments as pa

PAGE = UUID("22222222-2222-2222-2222-222222222222")
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "attachments_dir", str(tmp_path))
    return tmp_path


@pytest.fixture
async def page(session):
    await session.execute(text(
        "INSERT INTO pages (id, project, order_index, content_hash) "
        f"VALUES ('{PAGE}', 'p', 0, 'h')"
    ))
    return PAGE


async def _chunks(*parts: bytes):
    for part in parts:
        yield part


async def _store(session, *, chunks, max_bytes, **place):
    staged = await pa.stage_upload(chunks, max_bytes=max_bytes)
    return await pa.place_upload(session, staged, **place)


@pytest.mark.parametrize("head, expected", [
    (b"\x89PNG\r\n\x1a\n....", "image/png"),
    (b"\xff\xd8\xff\xe0....", "image/jpeg"),
    (b"GIF89a....", "image/gif"),
    (b"GIF87a....", "image/gif"),
    (b"RIFF\x00\x00\x00\x00WEBPVP8 ", "image/webp"),
    (b"\x89PNG\r\n\x1a\n<html><script>", "image/png"),
    (b"<svg xmlns=", "application/octet-stream"),
    (b"<html><script>", "application/octet-stream"),
    (b"", "application/octet-stream"),
])
def test_sniff_content_type(head, expected):
    assert pa.sniff_content_type(head) == expected


@pytest.mark.parametrize("raw, expected", [
    (None, "file"),
    ("", "file"),
    ("a%20b.png", "a b.png"),
    ("evil%0d%0aSet-Cookie:x", "evilSet-Cookie:x"),
    ("../../etc/passwd", ".._.._etc_passwd"),
    ("x" * 300, "x" * 255),
])
def test_clean_filename(raw, expected):
    assert pa.clean_filename(raw) == expected


def test_path_is_sharded_by_id_and_nothing_else(root):
    attachment_id = UUID("ab345678-1234-1234-1234-123456789012")
    assert pa.attachment_path(attachment_id) == root / "ab" / str(attachment_id)


def test_disposition_is_inline_only_for_raster_images():
    assert pa.content_disposition("image/png", "a.png").startswith("inline;")
    assert pa.content_disposition(pa.OCTET_STREAM, "a.svg").startswith("attachment;")


def test_disposition_encodes_non_ascii_names():
    header = pa.content_disposition(pa.OCTET_STREAM, 'straße "q".pdf')
    assert 'filename="strae q.pdf"' in header
    assert "filename*=UTF-8''stra%C3%9Fe%20%22q%22.pdf" in header


def test_serving_headers():
    row = pa.AttachmentRow(
        id=PAGE, project="p", filename="a.png", content_type="image/png",
        size_bytes=3, sha256="f" * 64,
    )
    headers = pa.serving_headers(row)
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Content-Security-Policy"] == "sandbox"
    assert headers["ETag"] == f'"{"f" * 64}"'
    assert headers["Cache-Control"] == "private, max-age=31536000, immutable"
    assert headers["Content-Disposition"].startswith("inline;")


async def test_stage_then_place_writes_file_and_row(session, root, page):
    stored = await _store(
        session, page_id=PAGE, project="p", filename="a.png",
        chunks=_chunks(PNG[:5], PNG[5:]), max_bytes=1024,
    )
    path = pa.attachment_path(stored.id)
    assert path.read_bytes() == PNG
    assert not path.with_name(path.name + ".part").exists()
    assert stored.content_type == "image/png"
    assert stored.size_bytes == len(PNG)
    assert stored.sha256 == hashlib.sha256(PNG).hexdigest()
    assert stored.url == f"/api/v1/pages/attachments/{stored.id}"
    row = await pa.get_attachment(session, stored.id)
    assert row is not None and row.project == "p" and row.filename == "a.png"


async def test_an_upload_over_the_cap_leaves_nothing(session, root, page):
    with pytest.raises(pa.AttachmentTooLarge):
        await _store(
            session, page_id=PAGE, project="p", filename="a.bin",
            chunks=_chunks(b"x" * 600, b"x" * 600), max_bytes=1000,
        )
    assert [p for p in root.rglob("*") if p.is_file()] == []
    count = (await session.execute(text("SELECT count(*) FROM page_attachments"))).scalar_one()
    assert count == 0


async def test_a_failing_stream_leaves_no_part_file(session, root, page):
    async def broken():
        yield b"abc"
        raise ConnectionError("client went away")

    with pytest.raises(ConnectionError):
        await _store(
            session, page_id=PAGE, project="p", filename="a.bin",
            chunks=broken(), max_bytes=1000,
        )
    assert [p for p in root.rglob("*") if p.is_file()] == []


async def test_a_failing_insert_unlinks_the_file(session, root, page):
    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            await _store(
                session, page_id=uuid4(), project="p", filename="a.png",
                chunks=_chunks(PNG), max_bytes=1024,
            )
    assert [p for p in root.rglob("*") if p.is_file()] == []


class _CancelledCommit:
    """A commit the server may already have made durable."""

    async def execute(self, *args, **kwargs):
        return None

    async def commit(self):
        raise asyncio.CancelledError()


async def test_a_cancelled_commit_keeps_the_file(root):
    """A row-less file is what the cleanup job sweeps; a file-less row is
    forever, so cancellation must not take the bytes with it."""
    with pytest.raises(asyncio.CancelledError):
        await _store(
            _CancelledCommit(), page_id=PAGE, project="p", filename="a.png",
            chunks=_chunks(PNG), max_bytes=1024,
        )
    assert [p.name for p in root.rglob("*") if p.is_file()] != []


async def test_get_attachment_missing_is_none(session):
    assert await pa.get_attachment(session, PAGE) is None


def test_dir_check_creates_and_probes(root, monkeypatch):
    target = root / "nested"
    monkeypatch.setattr(settings, "attachments_dir", str(target))
    pa.assert_attachments_dir_usable(read_only=False)
    assert target.is_dir()
    assert list(target.iterdir()) == []


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory mode bits")
def test_dir_check_refuses_an_unwritable_dir(root):
    root.chmod(0o500)
    try:
        with pytest.raises(pa.AttachmentsDirUnusable):
            pa.assert_attachments_dir_usable(read_only=False)
    finally:
        root.chmod(0o700)


def test_dir_check_on_a_read_only_instance_only_warns(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(settings, "attachments_dir", str(tmp_path / "absent"))
    pa.assert_attachments_dir_usable(read_only=True)
    assert "attachments_dir" in caplog.text
