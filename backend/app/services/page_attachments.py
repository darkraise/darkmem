"""Page attachments: bytes on disk, one `page_attachments` row each.

A file is named by its attachment id and nothing else, so no string a caller
chose ever reaches a filesystem path. Every write lands as `<path>.part` and is
renamed into place, so a crash never leaves a truncated file under a final
name. The stored type is sniffed from the bytes; a client's claim is ignored.
"""
from __future__ import annotations

import hashlib
import logging
import os
import unicodedata
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, unquote
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)

ATTACHMENT_URL_PREFIX = "/api/v1/pages/attachments/"
OCTET_STREAM = "application/octet-stream"
INLINE_IMAGE_TYPES = frozenset({"image/png", "image/jpeg", "image/gif", "image/webp"})
STAGING_DIRNAME = ".staging"
FILENAME_MAX_CHARS = 255
DEFAULT_FILENAME = "file"
_SNIFF_BYTES = 16

_INSERT = text(
    "INSERT INTO page_attachments (id, project, uploaded_for_page_id, filename, "
    "content_type, size_bytes, sha256) VALUES (CAST(:id AS uuid), :project, "
    "CAST(:page AS uuid), :filename, :content_type, :size_bytes, :sha256)"
)
_SELECT = text(
    "SELECT id, project, filename, content_type, size_bytes, sha256 "
    "FROM page_attachments WHERE id = CAST(:id AS uuid)"
)


class AttachmentTooLarge(ValueError):
    """The body passed `attachment_max_bytes` while it was being read."""


class AttachmentsDirUnusable(RuntimeError):
    """`attachments_dir` cannot be created or written."""


@dataclass(frozen=True)
class StoredAttachment:
    id: UUID
    url: str
    filename: str
    content_type: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class AttachmentRow:
    id: UUID
    project: str
    filename: str
    content_type: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class _Written:
    id: UUID
    size_bytes: int
    sha256: str
    content_type: str


def attachments_root() -> Path:
    return Path(settings.attachments_dir)


def attachment_path(attachment_id: UUID) -> Path:
    name = str(attachment_id)
    return attachments_root() / name[:2] / name


def attachment_url(attachment_id: UUID) -> str:
    return f"{ATTACHMENT_URL_PREFIX}{attachment_id}"


def sniff_content_type(head: bytes) -> str:
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return OCTET_STREAM


def clean_filename(raw: str | None) -> str:
    name = unquote(raw or "", errors="replace")
    name = "".join(ch for ch in name if unicodedata.category(ch)[0] != "C")
    name = name.replace("/", "_").replace("\\", "_").strip()
    return name[:FILENAME_MAX_CHARS] or DEFAULT_FILENAME


def content_disposition(content_type: str, filename: str) -> str:
    disposition = "inline" if content_type in INLINE_IMAGE_TYPES else "attachment"
    fallback = (
        filename.encode("ascii", "ignore").decode("ascii")
        .replace('"', "").replace("\\", "").strip()
        or DEFAULT_FILENAME
    )
    return (
        f'{disposition}; filename="{fallback}"; '
        f"filename*=UTF-8''{quote(filename, safe='')}"
    )


def serving_headers(row: AttachmentRow) -> dict[str, str]:
    # nosniff plus a type we sniffed ourselves is what defeats a polyglot; the
    # CSP and the disposition act only when the file is opened as a document.
    return {
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "sandbox",
        "ETag": f'"{row.sha256}"',
        "Cache-Control": "private, max-age=31536000, immutable",
        "Content-Disposition": content_disposition(row.content_type, row.filename),
    }


async def _write_file(chunks: AsyncIterator[bytes], *, max_bytes: int) -> _Written:
    attachment_id = uuid4()
    final = attachment_path(attachment_id)
    part = final.with_name(final.name + ".part")
    final.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    size = 0
    head = b""
    try:
        with open(part, "wb") as fh:
            async for chunk in chunks:
                if not chunk:
                    continue
                size += len(chunk)
                if size > max_bytes:
                    raise AttachmentTooLarge(
                        f"attachment exceeds {max_bytes} bytes"
                    )
                if len(head) < _SNIFF_BYTES:
                    head += chunk[: _SNIFF_BYTES - len(head)]
                digest.update(chunk)
                fh.write(chunk)
        os.replace(part, final)
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    return _Written(attachment_id, size, digest.hexdigest(), sniff_content_type(head))


async def store_upload(
    session: AsyncSession,
    *,
    page_id: UUID,
    project: str,
    filename: str,
    chunks: AsyncIterator[bytes],
    max_bytes: int,
) -> StoredAttachment:
    written = await _write_file(chunks, max_bytes=max_bytes)
    try:
        await session.execute(_INSERT, {
            "id": str(written.id),
            "project": project,
            "page": str(page_id),
            "filename": filename,
            "content_type": written.content_type,
            "size_bytes": written.size_bytes,
            "sha256": written.sha256,
        })
        await session.commit()
    except Exception:
        # Exception, not BaseException: a cancellation may arrive after the
        # server acknowledged the COMMIT, and a row whose only bytes were
        # unlinked is a 404 no arm of the cleanup job can repair -- where the
        # file this keeps is row-less at worst, which arm 2 sweeps.
        attachment_path(written.id).unlink(missing_ok=True)
        raise
    return StoredAttachment(
        id=written.id,
        url=attachment_url(written.id),
        filename=filename,
        content_type=written.content_type,
        size_bytes=written.size_bytes,
        sha256=written.sha256,
    )


def place_staged(staged: Path, attachment_id: UUID) -> None:
    """Move an already-written staged file onto its final sharded path.

    `os.replace` rather than a copy: staging lives under the same
    `attachments_dir`, so the rename is atomic and costs no second write of a
    file that may be tens of megabytes.
    """
    final = attachment_path(attachment_id)
    final.parent.mkdir(parents=True, exist_ok=True)
    os.replace(staged, final)


async def insert_attachment_row(
    session: AsyncSession,
    *,
    attachment_id: UUID,
    project: str,
    page_id: UUID | None,
    filename: str,
    content_type: str,
    size_bytes: int,
    sha256: str,
) -> None:
    """Insert one row and DO NOT commit.

    `store_upload` commits because its file is already on disk and its caller
    has nothing else to write. An import writes its attachment rows, its pages
    and its journal row in one transaction, so it needs the insert without the
    commit.
    """
    await session.execute(_INSERT, {
        "id": str(attachment_id),
        "project": project,
        "page": None if page_id is None else str(page_id),
        "filename": filename,
        "content_type": content_type,
        "size_bytes": size_bytes,
        "sha256": sha256,
    })


async def get_attachment(session: AsyncSession, attachment_id: UUID) -> AttachmentRow | None:
    row = (await session.execute(_SELECT, {"id": str(attachment_id)})).first()
    if row is None:
        return None
    return AttachmentRow(
        id=row.id, project=row.project, filename=row.filename,
        content_type=row.content_type, size_bytes=row.size_bytes, sha256=row.sha256,
    )


def assert_attachments_dir_usable(*, read_only: bool) -> None:
    root = attachments_root()
    if read_only:
        # The backup worker serves what a restore unpacked; before the first
        # restore there is nothing to serve, which is not a reason to refuse.
        if not (root.is_dir() and os.access(root, os.R_OK | os.X_OK)):
            logger.warning("attachments_dir %s is not a readable directory", root)
        return
    try:
        root.mkdir(parents=True, exist_ok=True)
        probe = root / f".write-probe-{uuid4()}"
        probe.write_bytes(b"")
        probe.unlink()
    except OSError as exc:
        raise AttachmentsDirUnusable(
            f"attachments_dir {root} is not writable: {exc}"
        ) from exc
