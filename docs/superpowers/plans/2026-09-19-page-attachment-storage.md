# Page Attachment Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: the skill the **Execution:** line names — dr-superpowers:subagent-driven-development for `subagent`, dr-superpowers:executing-plans for `inline`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store files for pages on a disk volume with metadata in Postgres, serve them safely over REST, and collect unreferenced ones with an hourly job.

**Architecture:** A `page_attachments` table in the one-revision baseline holds metadata; bytes live at `<attachments_dir>/<id[:2]>/<id>`, written as `.part` then renamed. A new REST module takes a raw-body upload (streamed, size-capped while reading) and serves files with `nosniff` and a disposition decided by magic-byte sniffing. Lifetime is project-scoped: an attachment lives while any page block in the database references its URL, and the `page_attachment_cleanup` job deletes the rest after a grace period.

**Tech Stack:** FastAPI, Starlette `Request.stream()` / `FileResponse`, SQLAlchemy async raw SQL, asyncpg, pytest-asyncio, Docker Compose.

**Spec:** docs/superpowers/specs/2026-09-19-notion-import-design.md

**Execution:** subagent — `claude --model sonnet --effort high` — five of six tasks are heavy (risk 3 or total ≥ 5).

**Program:** docs/superpowers/specs/2026-09-19-notion-import-design.md — sub-project 1 of 4 — next: Attachment backups (spec §3.7: backup.sh tarball, backup_ship family, worker generations)

**Plan review:** 2026-09-19 — dr-superpowers:judge-opus — executability 15 / coherence 18 / coverage 18 / assumptions 15 (round 2)

## Global Constraints

- Greenfield until the freeze: no migration, no compatibility shim. A schema change regenerates `backend/migrations/versions/0001_baseline.py` in place; never add a `0002`.
- No user-controlled string ever reaches a filesystem path. Files are named by attachment id only.
- Every file write goes to `<path>.part`, then `os.replace` onto the final path.
- The client's `Content-Type` is never checked and never persisted; the stored type comes from `sniff_content_type` only.
- `Content-Disposition: inline` only for `image/png`, `image/jpeg`, `image/gif`, `image/webp`; everything else is `attachment`.
- Every attachment response carries `X-Content-Type-Options: nosniff` and `Content-Security-Policy: sandbox`.
- Pages and attachments are REST-only: no MCP tool, no scope.
- `attachment_max_bytes` default is `52428800` (50 MB). `grace_hours` default 168, `staging_max_age_hours` default 6.
- Backend tests run from `backend/` as `.venv/bin/python -m pytest -q ...` with `TEST_DATABASE_URL` pointing at a lane database (`darkmem_test_2`..`_5`), never at a real database.
- Every Bash test command carries an explicit timeout (use the Bash tool's `timeout` parameter, e.g. 600000).
- **Deploy is not a task in this plan.** Task 1 regenerates the baseline, so the running instance's `schema_guard` refuses its next boot until the database is dropped and recreated (CLAUDE.md "The schema is ONE revision"; `docs/runbook-deployment.md`). That is destructive for the live corpus, so no task deploys: after the branch merges, the controller asks the owner before running the drop/recreate/re-seed redeploy. No implementer runs `docker compose up`, runs `scripts/build-push.sh` at all (it tags `darkraise/darkmem:latest`, which production runs), or touches the `:8000` instance; Task 3's image check builds under a throwaway tag and removes it.
- Commits follow `<type>(<scope>): <subject>` (≤ 50 chars, imperative).
- Comments only where the WHY is non-obvious; never reference the task or the plan.

## Contracts

- **Table** `page_attachments(id uuid PK, project text NOT NULL, uploaded_for_page_id uuid NULL FK pages(id) ON DELETE SET NULL, filename text NOT NULL (1..255 chars), content_type text NOT NULL, size_bytes bigint NOT NULL ≥ 0, sha256 text NOT NULL, created_at timestamptz NOT NULL DEFAULT now())`; indexes `ix_page_attachments_project (project)` (spec §3.1) and `ix_page_attachments_created (created_at)` (a deliberate extra: the cleanup job's `created_at <` predicate). (Task 1)
- **Settings** in `app/config.py` `Settings`: `attachments_dir: str = "./data/attachments"` (env `ATTACHMENTS_DIR`), `attachment_max_bytes: int = 52428800` (env `ATTACHMENT_MAX_BYTES`). (Task 2)
- **Module** `app/services/page_attachments.py` (Task 2) exports:
  - `ATTACHMENT_URL_PREFIX = "/api/v1/pages/attachments/"`
  - `INLINE_IMAGE_TYPES: frozenset[str]`, `OCTET_STREAM = "application/octet-stream"`, `STAGING_DIRNAME = ".staging"`
  - `class AttachmentTooLarge(ValueError)`, `class AttachmentsDirUnusable(RuntimeError)`
  - `@dataclass(frozen=True) class StoredAttachment: id: UUID; url: str; filename: str; content_type: str; size_bytes: int; sha256: str`
  - `@dataclass(frozen=True) class AttachmentRow: id: UUID; project: str; filename: str; content_type: str; size_bytes: int; sha256: str`
  - `attachments_root() -> Path`, `attachment_path(attachment_id: UUID) -> Path`, `attachment_url(attachment_id: UUID) -> str`
  - `sniff_content_type(head: bytes) -> str`, `clean_filename(raw: str | None) -> str`
  - `content_disposition(content_type: str, filename: str) -> str`, `serving_headers(row: AttachmentRow) -> dict[str, str]`
  - `async store_upload(session, *, page_id: UUID, project: str, filename: str, chunks: AsyncIterator[bytes], max_bytes: int) -> StoredAttachment` (commits)
  - `async get_attachment(session, attachment_id: UUID) -> AttachmentRow | None`
  - `assert_attachments_dir_usable(*, read_only: bool) -> None`
- **Routes** in `app/api/routes/page_attachments.py`, `router = APIRouter(prefix="/api/v1/pages", tags=["pages"])` (Task 4):
  - `POST /api/v1/pages/{page_id}/attachments` → 201 `{id, url, filename, content_type, size_bytes}`; 404 unknown or trashed page; 413 over the cap; 403 on a read-only instance.
  - `GET /api/v1/pages/attachments/{attachment_id}` → 200 file; 404 in the error envelope when the row or file is missing.
- **Job** in `app/services/page_attachment_cleanup.py` (Task 6): `PAGE_ATTACHMENT_CLEANUP_JOB_KEY = "page_attachment_cleanup"`, `PAGE_ATTACHMENT_CLEANUP_CONFIG_SCHEMA`, `make_page_attachment_cleanup_runner(app, session_factory)`, `async run_cleanup(session_factory, *, grace_hours: int, staging_max_age_hours: int, now: float | None = None) -> CleanupReport`.

## Assumptions (evidence)

- Pages have no ORM model; the page door uses raw SQL (`backend/app/services/page_door.py:447-538`, `ls backend/app/models` 2026-09-19). Attachments follow the raw-SQL shape.
- The `pages` table is created at `backend/migrations/versions/0001_baseline.py:1333-1367`; `downgrade()` drops tables by name in the list starting at `:1665`, with `"pages"` at `:1690`.
- The test `client` fixture overrides `get_session` with the test's own `session` (`backend/tests/conftest.py:158-162`), so rows a test inserts through `session` are visible to routes, and a route's `commit()` is dropped rather than propagated (`conftest.py:69-104`).
- `test_schema_guard.py:29-31` computes the baseline hash rather than pinning it, so regenerating the baseline breaks no test.
- A named volume mounted on a path absent from the image is created root-owned; `Dockerfile:94` chowns `/app` to the unprivileged `app` user only for paths that exist at build time. Unverified on this host — Task 3's Step 5 verifies it by building the image.
- Starlette's `FileResponse` sets `etag` with `setdefault`, so a caller-supplied `ETag` header survives (`starlette/responses.py:337-339`, confirmed by the round-1 plan review 2026-09-19); Task 4's Step 1 test asserts the exact value.
- `refuse_when_read_only` lives at `backend/app/api/deps.py:92-125` and is keyed on `settings.read_only`.
- The direct job roster is a hand-written set in `backend/tests/test_code_deriver.py:1517-1526`; `BLOCK_CHANNEL_MODULES` is at `backend/tests/test_block_retrieval.py:370-394`.
- The parity doc is regenerated from `render_markdown()` (`backend/tests/test_door_parity.py:2074-2124`); its headline today reads `80 surfaces: 25 two-door, 55 single-door with a stated reason (48 REST-only, 7 MCP-only), 0 divergent` (`docs/two-door-parity.md:13`).

## Task index

1. Baseline table for page attachments
2. Attachment storage service
3. Attachment volume in the image and compose
4. Attachment upload and serve routes
5. Register the attachment routes with the guards
6. Attachment cleanup job

---

### Task 1: Baseline table for page attachments

**Files:**
- Modify: `backend/migrations/versions/0001_baseline.py:1367` (insert after the `pages_touch_updated_at` trigger) and `:1690` (downgrade list)
- Test: `backend/tests/test_page_attachments_schema.py` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: the `page_attachments` table (Contracts: **Table**).

**Implementer:** dr-superpowers:impl-opus-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 3 = 6

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_page_attachments_schema.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q tests/test_page_attachments_schema.py`
Expected: FAIL with `relation "page_attachments" does not exist`.

- [ ] **Step 3: Write the implementation**

In `backend/migrations/versions/0001_baseline.py`, immediately after the `op.execute(... "CREATE TRIGGER pages_touch_updated_at ..." ...)` call that ends the pages block (line 1367), insert:

```python
    # Attachment metadata; the bytes live on disk, named by `id` alone. The
    # project owns an attachment, not a page: a block copied to another page
    # keeps its image, so the page link is provenance and SET NULL on purge.
    # No FK on `project`, like every scoped table (projects register lazily).
    op.execute(
        """
        CREATE TABLE page_attachments (
            id                   UUID NOT NULL,
            project              TEXT NOT NULL,
            uploaded_for_page_id UUID REFERENCES pages(id) ON DELETE SET NULL,
            filename             TEXT NOT NULL,
            content_type         TEXT NOT NULL,
            size_bytes           BIGINT NOT NULL,
            sha256               TEXT NOT NULL,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT page_attachments_pkey PRIMARY KEY (id),
            CONSTRAINT chk_page_attachments_filename
                CHECK (char_length(filename) BETWEEN 1 AND 255),
            CONSTRAINT chk_page_attachments_size CHECK (size_bytes >= 0)
        )
        """
    )
    op.execute("CREATE INDEX ix_page_attachments_project ON page_attachments (project)")
    op.execute("CREATE INDEX ix_page_attachments_created ON page_attachments (created_at)")
```

In `downgrade()`'s table list, insert `"page_attachments",` on the line before `"pages",` (line 1690).

- [ ] **Step 4: Run test to verify it passes**

Run: `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q tests/test_page_attachments_schema.py tests/test_pages_schema.py tests/test_schema_guard.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/migrations/versions/0001_baseline.py backend/tests/test_page_attachments_schema.py
git commit -m "feat(pages): add page_attachments table"
```

---

### Task 2: Attachment storage service

**Files:**
- Modify: `backend/app/config.py:112` (after `spa_dir`)
- Create: `backend/app/services/page_attachments.py`
- Test: `backend/tests/test_page_attachments.py` (create)

**Interfaces:**
- Consumes: Contracts **Table** (Task 1).
- Produces: Contracts **Settings** and **Module** `app/services/page_attachments.py`.

**Implementer:** dr-superpowers:impl-opus-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 3 = 6

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_page_attachments.py`:

```python
"""Attachment bytes on disk and their row."""
from __future__ import annotations

import hashlib
import os
from uuid import UUID

import pytest
from sqlalchemy import text

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


async def test_store_upload_writes_file_and_row(session, root, page):
    stored = await pa.store_upload(
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


async def test_store_upload_over_the_cap_leaves_nothing(session, root, page):
    with pytest.raises(pa.AttachmentTooLarge):
        await pa.store_upload(
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
        await pa.store_upload(
            session, page_id=PAGE, project="p", filename="a.bin",
            chunks=broken(), max_bytes=1000,
        )
    assert [p for p in root.rglob("*") if p.is_file()] == []


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q tests/test_page_attachments.py`
Expected: FAIL with `ImportError: cannot import name 'page_attachments'`.

- [ ] **Step 3: Write the implementation**

In `backend/app/config.py`, after the `spa_dir: str | None = None` line (112), add:

```python
    # Page attachments on disk. Relative for host-side dev; the image mounts a
    # named volume at /app/data/attachments and sets ATTACHMENTS_DIR to it.
    attachments_dir: str = "./data/attachments"
    attachment_max_bytes: int = 52_428_800
```

Create `backend/app/services/page_attachments.py`:

```python
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
    except BaseException:
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q tests/test_page_attachments.py`
Expected: PASS (one test skipped when running as root).

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/app/services/page_attachments.py backend/tests/test_page_attachments.py
git commit -m "feat(pages): add attachment storage service"
```

---

### Task 3: Attachment volume in the image and compose

**Files:**
- Modify: `Dockerfile:94`
- Modify: `docker-compose.yml:59-94` (app `environment:` and `volumes:`) and `:155-157` (top-level `volumes:`)
- Modify: `backend/app/main.py:61` (top of `lifespan`, after `llm = None`)
- Test: `backend/tests/test_deployment_artifact.py` (append)

**Interfaces:**
- Consumes: `assert_attachments_dir_usable`, `AttachmentsDirUnusable` (Contracts **Module**, Task 2).
- Produces: nothing other tasks consume.

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 2 = 5

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_deployment_artifact.py`:

```python
def test_the_image_creates_the_attachments_dir_before_chowning_app():
    """A named volume mounted on a path the image lacks is created root-owned,
    and the unprivileged `app` user then cannot write a single attachment."""
    dockerfile = _unwrapped(DOCKERFILE)
    mkdir = dockerfile.find("/app/data/attachments")
    chown = dockerfile.find("chown -R app:app /app")
    assert mkdir != -1, "the Dockerfile never creates /app/data/attachments"
    assert chown != -1 and mkdir < chown, (
        "/app/data/attachments must exist before `chown -R app:app /app`"
    )


def test_prod_app_service_mounts_the_attachment_volume():
    service = _compose(PROD_COMPOSE)["services"][APP_SERVICE]
    assert "attachment_data:/app/data/attachments" in service["volumes"], service["volumes"]
    assert "attachment_data" in _compose(PROD_COMPOSE)["volumes"]
    env = _service_env(PROD_COMPOSE, APP_SERVICE)
    assert env["ATTACHMENTS_DIR"] == "/app/data/attachments"


def test_boot_checks_the_attachments_dir_outside_any_degrading_try():
    """The lifespan's LLM and registry setup sits in a broad try that logs and
    continues; a check inside it would let an unwritable volume boot green."""
    source = (REPO_ROOT / "backend" / "app" / "main.py").read_text()
    check = source.find("assert_attachments_dir_usable(read_only=settings.read_only)")
    first_try = source.find("from app.services.config import get_llm_config")
    assert check != -1, "lifespan never checks the attachments dir"
    assert check < first_try, "the attachments dir check must precede the lifespan's first try"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_deployment_artifact.py -k attachment`
Expected: FAIL (`the Dockerfile never creates /app/data/attachments`).

- [ ] **Step 3: Write the implementation**

`Dockerfile`, replace line 94:

```dockerfile
RUN addgroup --system app && adduser --system --ingroup app app && chown -R app:app /app
```

with:

```dockerfile
# The attachments volume mounts here; the directory must exist before the
# chown, or Docker creates the named volume root-owned and `app` cannot write.
RUN mkdir -p /app/data/attachments \
    && addgroup --system app && adduser --system --ingroup app app && chown -R app:app /app
```

`docker-compose.yml`, in the `darkmem` service's `environment:` list, after `- MCP_ALLOWED_HOSTS=${MCP_ALLOWED_HOSTS:-}`, add:

```yaml
      - ATTACHMENTS_DIR=/app/data/attachments
```

In the same service's `volumes:` list, after `- repo_data:/app/data/repositories`, add:

```yaml
      # Page attachments. Named, not bound: Docker copies the image's
      # ownership of /app/data/attachments into a fresh named volume.
      - attachment_data:/app/data/attachments
```

In the top-level `volumes:` mapping at the end of the file, after `repo_data:`, add:

```yaml
  attachment_data:
```

`backend/app/main.py`, in `lifespan`, directly after the line `llm = None` (line 61) and before the system-prompt `try`, insert:

```python
    # Outside every degrading try below: an unwritable attachments volume
    # must refuse boot, not start an app whose uploads all fail.
    from app.services.page_attachments import assert_attachments_dir_usable

    assert_attachments_dir_usable(read_only=settings.read_only)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_deployment_artifact.py`
Expected: PASS.

- [ ] **Step 5: Verify the image**

Run (from the repo root, 900 s timeout): `docker build -t darkmem-attachments-check:local . && docker run --rm --entrypoint sh darkmem-attachments-check:local -c 'ls -ld /app/data/attachments'; docker rmi darkmem-attachments-check:local`
Expected: the directory is owned by `app app`. Never build this branch as `darkraise/darkmem:latest` (what `build-push.sh` tags): that is the tag production runs, and its regenerated baseline would stop the live instance at the next `docker compose up -d`.

- [ ] **Step 6: Commit**

```bash
git add Dockerfile docker-compose.yml backend/app/main.py backend/tests/test_deployment_artifact.py
git commit -m "feat(deploy): add the attachments volume"
```

---

### Task 4: Attachment upload and serve routes

**Files:**
- Create: `backend/app/api/routes/page_attachments.py`
- Modify: `backend/app/main.py:21` (import) and `:997` (`include_router`, directly after `pages_routes`)
- Test: `backend/tests/test_page_attachment_routes.py` (create)

**Interfaces:**
- Consumes: Contracts **Module** (Task 2): `store_upload`, `get_attachment`, `attachment_path`, `serving_headers`, `clean_filename`, `AttachmentTooLarge`; Contracts **Settings**.
- Produces: Contracts **Routes**.

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 3 = 5

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_page_attachment_routes.py`:

```python
"""Page attachments over REST."""
from __future__ import annotations

import hashlib
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.config import settings

V1 = "/api/v1"
PAGE = "22222222-2222-2222-2222-222222222222"
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


async def _upload(client, auth_headers, page_id, body, **headers):
    return await client.post(
        f"{V1}/pages/{page_id}/attachments", content=body,
        headers={**auth_headers, **headers},
    )


async def test_upload_then_get(client, auth_headers, root, page):
    created = await _upload(
        client, auth_headers, page, PNG,
        **{"X-Filename": "shot%201.png", "Content-Type": "text/html"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["content_type"] == "image/png"
    assert body["filename"] == "shot 1.png"
    assert body["size_bytes"] == len(PNG)
    assert body["url"] == f"/api/v1/pages/attachments/{body['id']}"

    got = await client.get(body["url"], headers=auth_headers)
    assert got.status_code == 200
    assert got.content == PNG
    assert got.headers["content-type"] == "image/png"
    assert got.headers["x-content-type-options"] == "nosniff"
    assert got.headers["content-security-policy"] == "sandbox"
    assert got.headers["content-disposition"].startswith("inline;")
    assert got.headers["etag"] == f'"{hashlib.sha256(PNG).hexdigest()}"'


async def test_html_is_served_as_a_download(client, auth_headers, root, page):
    created = await _upload(
        client, auth_headers, page, b"<html><script>alert(1)</script>",
        **{"X-Filename": "x.html", "Content-Type": "text/html"},
    )
    got = await client.get(created.json()["url"], headers=auth_headers)
    assert got.headers["content-type"] == "application/octet-stream"
    assert got.headers["content-disposition"].startswith("attachment;")


async def test_missing_filename_defaults(client, auth_headers, root, page):
    created = await _upload(client, auth_headers, page, b"abc")
    assert created.json()["filename"] == "file"


async def test_declared_length_over_the_cap_is_413(client, auth_headers, root, page, monkeypatch):
    monkeypatch.setattr(settings, "attachment_max_bytes", 10)
    response = await _upload(client, auth_headers, page, b"x" * 11)
    assert response.status_code == 413
    assert [p for p in root.rglob("*") if p.is_file()] == []


async def test_streamed_body_over_the_cap_is_413(client, auth_headers, root, page, monkeypatch):
    monkeypatch.setattr(settings, "attachment_max_bytes", 10)

    async def body():
        yield b"x" * 6
        yield b"x" * 6

    response = await client.post(
        f"{V1}/pages/{page}/attachments", content=body(), headers=auth_headers,
    )
    assert response.status_code == 413
    assert [p for p in root.rglob("*") if p.is_file()] == []


async def test_upload_to_an_unknown_page_is_404(client, auth_headers, root):
    response = await _upload(client, auth_headers, str(uuid4()), b"abc")
    assert response.status_code == 404


async def test_upload_to_a_trashed_page_is_404(client, auth_headers, root, page, session):
    await session.execute(text(f"UPDATE pages SET deleted_at = now() WHERE id = '{PAGE}'"))
    response = await _upload(client, auth_headers, page, b"abc")
    assert response.status_code == 404


async def test_upload_is_refused_on_a_read_only_instance(client, auth_headers, root, page, monkeypatch):
    monkeypatch.setattr(settings, "read_only", True)
    response = await _upload(client, auth_headers, page, b"abc")
    assert response.status_code == 403
    assert [p for p in root.rglob("*") if p.is_file()] == []


async def test_get_missing_is_404(client, auth_headers, root):
    response = await client.get(f"{V1}/pages/attachments/{uuid4()}", headers=auth_headers)
    assert response.status_code == 404


async def test_get_with_row_but_no_file_is_404(client, auth_headers, root, page):
    created = await _upload(client, auth_headers, page, b"abc")
    for path in root.rglob("*"):
        if path.is_file():
            path.unlink()
    response = await client.get(created.json()["url"], headers=auth_headers)
    assert response.status_code == 404


async def test_both_routes_need_auth(client, root, page):
    assert (await client.post(f"{V1}/pages/{page}/attachments", content=b"a")).status_code == 401
    assert (await client.get(f"{V1}/pages/attachments/{uuid4()}")).status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q tests/test_page_attachment_routes.py`
Expected: FAIL with 404 or 405 on the upload (route not registered).

- [ ] **Step 3: Write the implementation**

Create `backend/app/api/routes/page_attachments.py`:

```python
"""Page attachments over REST.

Provides:
  - POST /api/v1/pages/{page_id}/attachments
  - GET  /api/v1/pages/attachments/{attachment_id}

REST-only, like the page tree. The upload body is the raw file, not a
multipart form: FastAPI's `UploadFile` spools the whole body before the
handler runs, so a cap on it could only ever be checked after the bytes
landed. The request's own Content-Type is ignored -- a browser sends the
file's type, and the stored type is sniffed from the bytes.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.api.deps import refuse_when_read_only
from app.config import settings
from app.database import get_session
from app.services.page_attachments import (
    AttachmentTooLarge,
    attachment_path,
    clean_filename,
    get_attachment,
    serving_headers,
    store_upload,
)

router = APIRouter(prefix="/api/v1/pages", tags=["pages"])

_LIVE_PAGE_PROJECT = text(
    "SELECT project FROM pages WHERE id = CAST(:id AS uuid) AND deleted_at IS NULL"
)


class AttachmentResponse(BaseModel):
    id: UUID
    url: str
    filename: str
    content_type: str
    size_bytes: int


def _too_large() -> HTTPException:
    return HTTPException(
        status.HTTP_413_CONTENT_TOO_LARGE,
        f"attachment exceeds {settings.attachment_max_bytes} bytes",
    )


@router.post(
    "/{page_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(refuse_when_read_only)],
)
async def upload_attachment_route(
    page_id: UUID,
    request: Request,
    x_filename: str | None = Header(default=None),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> AttachmentResponse:
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > settings.attachment_max_bytes:
        raise _too_large()
    project = (
        await session.execute(_LIVE_PAGE_PROJECT, {"id": str(page_id)})
    ).scalar_one_or_none()
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no live page with id {page_id}")
    try:
        stored = await store_upload(
            session,
            page_id=page_id,
            project=project,
            filename=clean_filename(x_filename),
            chunks=request.stream(),
            max_bytes=settings.attachment_max_bytes,
        )
    except AttachmentTooLarge as exc:
        raise _too_large() from exc
    return AttachmentResponse(
        id=stored.id, url=stored.url, filename=stored.filename,
        content_type=stored.content_type, size_bytes=stored.size_bytes,
    )


@router.get("/attachments/{attachment_id}", response_class=FileResponse)
async def get_attachment_route(
    attachment_id: UUID,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    row = await get_attachment(session, attachment_id)
    path = attachment_path(attachment_id)
    if row is None or not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no attachment with id {attachment_id}")
    return FileResponse(path, media_type=row.content_type, headers=serving_headers(row))
```

`backend/app/main.py`: in the long `from app.api.routes import ...` line (21), add `page_attachments as page_attachments_routes,` directly after `pages as pages_routes,`. After `app.include_router(pages_routes.router)` (line 997), add:

```python
app.include_router(page_attachments_routes.router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q tests/test_page_attachment_routes.py tests/test_page_routes.py tests/test_spa_edge.py`
Expected: PASS. httpx sets `Content-Length` for a `bytes` body, so `test_declared_length_over_the_cap_is_413` exercises the declared-length refusal; the generator body in `test_streamed_body_over_the_cap_is_413` carries no length and exercises the streaming counter.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/page_attachments.py backend/app/main.py backend/tests/test_page_attachment_routes.py
git commit -m "feat(pages): add attachment upload and serve routes"
```

---

### Task 5: Register the attachment routes with the guards

**Files:**
- Modify: `backend/app/services/content_surfaces.py:727` (after the last `/api/v1/pages` entry)
- Modify: `backend/tests/test_api/test_rest_conformance.py:214` (`EXPECTED_STATUS`) and `:414-425` (error-shape cases)
- Modify: `backend/tests/test_door_parity.py:1563` (after the `pages.write` surface)
- Modify: `docs/two-door-parity.md` (generated block and headline, line 13)
- Modify: `backend/app/api/deps.py:92-118` (`refuse_when_read_only` docstring)
- Modify: `CLAUDE.md:1920` (page route sentence) and `:2098-2102` (the `refuse_when_read_only` list in the backup-worker invariant)
- Modify: `docs/runbook-backup-worker.md:60` (refused-doors table)

**Interfaces:**
- Consumes: Contracts **Routes** (Task 4).
- Produces: nothing other tasks consume.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 0 = 3

- [ ] **Step 1: Run the guards to see them fail**

Run (from `backend/`, 600 s timeout): `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q tests/test_content_surface_scoping.py tests/test_door_parity.py tests/test_api/test_rest_conformance.py`
Expected: FAIL, naming the two unclassified routes.

- [ ] **Step 2: Classify the routes in `content_surfaces.py`**

After the line `"DELETE /api/v1/pages/{page_id}/blocks/{block_id}",` add:

```python
    # Page attachments: a page's file bytes and their metadata. No
    # `memories` row crosses; REST-only for the pages.attachments row.
    "POST /api/v1/pages/{page_id}/attachments",
    "GET /api/v1/pages/attachments/{attachment_id}",
```

- [ ] **Step 3: Add the conformance expectations**

In `EXPECTED_STATUS`, after `("DELETE", "/api/v1/pages/{page_id}/blocks/{block_id}"): 204,` add:

```python
    ("POST", "/api/v1/pages/{page_id}/attachments"): 201,
    ("GET", "/api/v1/pages/attachments/{attachment_id}"): 200,
```

In `test_error_shape_is_uniform_across_the_surface`'s `cases` list, after the `/graph/entities/...` entry, add:

```python
        ("GET", f"/api/v1/pages/attachments/{missing}", None, 404),
```

- [ ] **Step 4: Add the parity surface**

In `PARITY_TABLE`, directly after the `pages.write` `Surface(...)` entry, add:

```python
    Surface(
        name="pages.attachments",
        status=REST_ONLY,
        rest=(
            ("POST", f"{V1}/pages/{{page_id}}/attachments"),
            ("GET", f"{V1}/pages/attachments/{{attachment_id}}"),
        ),
        mcp=(),
        reason=(
            "The files a page's blocks embed. Single-door for the same reason "
            "pages.write is: they belong to the operator's authored tree, not "
            "to an agent's context path, and nothing here generates or labels "
            "content. An MCP twin later is additive and an owner decision."
        ),
    ),
```

- [ ] **Step 5: Regenerate the parity doc**

Run (from `backend/`): `.venv/bin/python -c "from tests.test_door_parity import render_markdown; print(render_markdown())" > /tmp/claude-parity-table.md`
Replace everything between `<!-- BEGIN GENERATED PARITY TABLE -->` and `<!-- END GENERATED PARITY TABLE -->` in `docs/two-door-parity.md` with that file's contents (keep one blank line inside each marker, matching the existing layout). Then change line 13's headline to:

```markdown
**81 surfaces: 25 two-door, 56 single-door with a stated reason (49 REST-only, 7 MCP-only), 0 divergent.**
```

Delete `/tmp/claude-parity-table.md`.

- [ ] **Step 6: Amend `refuse_when_read_only`'s docstring**

In `backend/app/api/deps.py`, replace the docstring's first line and its final paragraph so it reads:

```python
    """Refuse a door that needs an external service or writes a file (owner ruling 2026-09-03).

    ...(keep the first middle paragraph, "A backup worker is for viewing...", unchanged)...

    Declared as a dependency rather than written at the top of each handler,
    and placed BEFORE the service dependencies that build an orchestrator, so
    the refusal lands before anything is constructed or called. That ordering
    is the point on every door this guards: each one dispatches an LLM, an
    embedder or a git fetch, or writes a file, *first* and writes a row
    *second*, so the SELECT-only viewer role would stop them only after the
    spend, the connection or the file had already happened.

    This is deliberately NOT the per-route allowlist review B1 rejected for
    *writes* -- those are caught generically by the SQLSTATE 42501 handler,
    which needs no list. This list exists because an external call is not a
    write the database sees, and neither is a file written to disk before any
    row: a page attachment upload lands its bytes first, so the viewer role
    would refuse it only after the file existed.
    """
```

In the same function, change the refusal `detail` to:

```python
            detail=(
                "read-only instance: this needs an external service or writes "
                "a file, and a backup worker is for viewing and backup/restore only"
            ),
```

- [ ] **Step 7: Update CLAUDE.md**

In `CLAUDE.md`, in the Pages paragraph, replace `thirteen routes under \`/api/v1/pages\` (\`api/routes/pages.py\`), no` with `thirteen routes under \`/api/v1/pages\` (\`api/routes/pages.py\`) plus the two attachment routes in \`api/routes/page_attachments.py\` (upload and serve, files on the \`attachment_data\` volume at \`ATTACHMENTS_DIR\`), no`. In the backup-worker invariant (around `CLAUDE.md:2098`), replace these wrapped lines exactly:

```
  indistinguishable from "no matches". And the doors that would spend or dial
  out before they write are refused at a shared `refuse_when_read_only`
  dependency (`api/deps.py`): `memories/reason`, `documents/qa`, every
  `reembed` POST, repo create/reindex/reindex-files/webhook, chat, job
  triggers. That list
```

with:

```
  indistinguishable from "no matches". And the doors that would spend, dial
  out or write a file before they write a row are refused at a shared
  `refuse_when_read_only` dependency (`api/deps.py`): `memories/reason`,
  `documents/qa`, every `reembed` POST, repo create/reindex/reindex-files/webhook,
  chat, job triggers, page attachment upload. That list
```

In `docs/runbook-backup-worker.md`, after the table row that begins `| Document search, \`memories/reason\``, add:

```markdown
| Page attachment upload | 403 — it writes the file before any row, so the viewer role alone would refuse it only after the file existed |
```

- [ ] **Step 8: Run the guards leg**

Run (from `backend/`, 600 s timeout):

```bash
TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  .venv/bin/python -m pytest -q tests/test_content_surface_scoping.py tests/test_door_parity.py \
    tests/test_prompt_agent_instructions.py tests/test_api/test_rest_conformance.py \
    tests/test_sdk_generator.py tests/test_spa_edge.py tests/test_events.py \
    tests/test_mcp_auth.py tests/test_inert_objects.py tests/test_api/test_tags.py \
    tests/test_block_pipeline.py tests/test_block_retrieval.py tests/test_auto_research.py \
    tests/test_event_taxonomy_map.py
```

Expected: PASS. A failure here names a guard these steps did not list; fix it the way its assertion message says, then re-run.

- [ ] **Step 9: Commit**

```bash
git add backend/app/services/content_surfaces.py backend/tests/test_api/test_rest_conformance.py backend/tests/test_door_parity.py docs/two-door-parity.md docs/runbook-backup-worker.md backend/app/api/deps.py CLAUDE.md
git commit -m "chore(pages): classify the attachment routes"
```

---

### Task 6: Attachment cleanup job

**Files:**
- Create: `backend/app/services/page_attachment_cleanup.py`
- Modify: `backend/app/main.py` (register the job after the `LLM_USAGE_CLEANUP_JOB_KEY` registration, around line 361)
- Modify: `backend/tests/test_code_deriver.py:1526` (roster set)
- Modify: `backend/tests/test_block_retrieval.py:393` (`BLOCK_CHANNEL_MODULES`)
- Modify: `CLAUDE.md` (Jobs section: count and live list; single-worker invariant)
- Modify: `backend/tests/test_citation_reverifier.py:1110-1117` (`_NUMBER_WORDS`)
- Test: `backend/tests/test_page_attachment_cleanup.py` (create)

**Interfaces:**
- Consumes: Contracts **Module** (Task 2): `attachments_root`, `attachment_path`, `STAGING_DIRNAME`; Contracts **Table**.
- Produces: Contracts **Job**.

**Implementer:** dr-superpowers:impl-opus-high
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 3 = 6

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_page_attachment_cleanup.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q tests/test_page_attachment_cleanup.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.page_attachment_cleanup'`.

- [ ] **Step 3: Write the implementation**

Create `backend/app/services/page_attachment_cleanup.py`:

```python
"""Hourly collection of page attachments nothing needs.

An attachment lives while any page block references its URL -- any page, in
any project, trashed pages included -- so emptying the trash is what releases
one, and a block pasted into another page keeps its file. Three arms: rows past
the grace period that no page block references (then their files), files older
than an hour with no row (a crash between rename and commit), and import
staging directories past their age limit.
"""
from __future__ import annotations

import asyncio
import logging
import re
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy import text

from app.services.job_registry import FieldDescriptor
from app.services.page_attachments import (
    STAGING_DIRNAME,
    attachment_path,
    attachments_root,
)

logger = logging.getLogger(__name__)

PAGE_ATTACHMENT_CLEANUP_JOB_KEY = "page_attachment_cleanup"
GRACE_HOURS_DEFAULT = 168
STAGING_MAX_AGE_HOURS_DEFAULT = 6
ROWLESS_MIN_AGE_SECONDS = 3600
_ID_BATCH = 500
_SHARD = re.compile(r"[0-9a-f]{2}")

PAGE_ATTACHMENT_CLEANUP_CONFIG_SCHEMA = [
    FieldDescriptor(
        key="grace_hours", label="Grace period (hours)",
        default=GRACE_HOURS_DEFAULT, min=1, max=8760,
        help="An unreferenced attachment younger than this is kept, so an "
             "upload whose block has not been saved yet survives.",
    ),
    FieldDescriptor(
        key="staging_max_age_hours", label="Import staging max age (hours)",
        default=STAGING_MAX_AGE_HOURS_DEFAULT, min=1, max=168,
        help="Import staging directories older than this are removed.",
    ),
]

_HAS_EXPIRED = text(
    "SELECT EXISTS (SELECT 1 FROM page_attachments "
    "WHERE created_at < now() - make_interval(hours => :grace))"
)
# One statement, so nothing can reference a row between the scan and the
# delete. Global rather than per project: a URL pasted into another project's
# page keeps its file alive.
_DELETE_UNREFERENCED = text(
    """
    WITH referenced AS (
        SELECT DISTINCT CAST(lower(m[1]) AS uuid) AS id
        FROM blocks b,
             regexp_matches(
                 b.text,
                 '/api/v1/pages/attachments/([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})',
                 'g'
             ) AS m
        WHERE b.page_id IS NOT NULL
          AND b.text LIKE '%/api/v1/pages/attachments/%'
    )
    DELETE FROM page_attachments a
    WHERE a.created_at < now() - make_interval(hours => :grace)
      AND NOT EXISTS (SELECT 1 FROM referenced r WHERE r.id = a.id)
    RETURNING a.id
    """
)
_KNOWN_IDS = text("SELECT id FROM page_attachments WHERE id = ANY(:ids)")


@dataclass
class CleanupReport:
    rows_deleted: int = 0
    files_unlinked: int = 0
    rowless_files_removed: int = 0
    part_files_removed: int = 0
    staging_dirs_removed: int = 0

    def total(self) -> int:
        return sum(asdict(self).values())


def _unlink(paths: list[Path]) -> int:
    removed = 0
    for path in paths:
        try:
            path.unlink()
            removed += 1
        except FileNotFoundError:
            pass
    return removed


def _scan(root: Path, now: float) -> tuple[list[tuple[UUID, Path]], list[Path]]:
    files: list[tuple[UUID, Path]] = []
    parts: list[Path] = []
    if not root.is_dir():
        return files, parts
    for shard in root.iterdir():
        if not (shard.is_dir() and _SHARD.fullmatch(shard.name)):
            continue
        for entry in shard.iterdir():
            try:
                stat = entry.stat()
            except FileNotFoundError:
                continue
            if not entry.is_file() or now - stat.st_mtime < ROWLESS_MIN_AGE_SECONDS:
                continue
            if entry.name.endswith(".part"):
                parts.append(entry)
                continue
            try:
                attachment_id = UUID(entry.name)
            except ValueError:
                continue
            if str(attachment_id) == entry.name and entry.name[:2] == shard.name:
                files.append((attachment_id, entry))
    return files, parts


def _remove_stale_staging(root: Path, max_age_seconds: float, now: float) -> int:
    staging = root / STAGING_DIRNAME
    if not staging.is_dir():
        return 0
    removed = 0
    for entry in staging.iterdir():
        try:
            stale = entry.is_dir() and now - entry.stat().st_mtime > max_age_seconds
        except FileNotFoundError:
            continue
        if stale:
            shutil.rmtree(entry, ignore_errors=True)
            removed += 1
    return removed


async def run_cleanup(
    session_factory,
    *,
    grace_hours: int,
    staging_max_age_hours: int,
    now: float | None = None,
) -> CleanupReport:
    report = CleanupReport()
    now = time.time() if now is None else now

    async with session_factory() as session:
        if (await session.execute(_HAS_EXPIRED, {"grace": grace_hours})).scalar_one():
            ids = [
                row[0] for row in
                (await session.execute(_DELETE_UNREFERENCED, {"grace": grace_hours})).all()
            ]
            await session.commit()
            report.rows_deleted = len(ids)
            report.files_unlinked = await asyncio.to_thread(
                _unlink, [attachment_path(i) for i in ids]
            )

    root = attachments_root()
    files, parts = await asyncio.to_thread(_scan, root, now)
    if files:
        known: set[UUID] = set()
        async with session_factory() as session:
            for start in range(0, len(files), _ID_BATCH):
                batch = [attachment_id for attachment_id, _ in files[start:start + _ID_BATCH]]
                known.update(
                    row[0] for row in (await session.execute(_KNOWN_IDS, {"ids": batch})).all()
                )
        rowless = [path for attachment_id, path in files if attachment_id not in known]
        report.rowless_files_removed = await asyncio.to_thread(_unlink, rowless)
    report.part_files_removed = await asyncio.to_thread(_unlink, parts)
    report.staging_dirs_removed = await asyncio.to_thread(
        _remove_stale_staging, root, staging_max_age_hours * 3600, now
    )
    return report


def make_page_attachment_cleanup_runner(app, session_factory):
    async def run() -> dict | int:
        grace = GRACE_HOURS_DEFAULT
        staging = STAGING_MAX_AGE_HOURS_DEFAULT
        registry = getattr(app.state, "job_registry", None)
        if registry is not None:
            cfg = await registry.load_config(PAGE_ATTACHMENT_CLEANUP_JOB_KEY)
            grace = int(cfg.config.get("grace_hours", GRACE_HOURS_DEFAULT))
            staging = int(cfg.config.get("staging_max_age_hours", STAGING_MAX_AGE_HOURS_DEFAULT))
        report = await run_cleanup(
            session_factory, grace_hours=grace, staging_max_age_hours=staging,
        )
        if not report.total():
            # 0, not {}: a no-op run writes no job_runs row.
            return 0
        logger.info("page_attachment_cleanup: %s", asdict(report))
        return asdict(report)
    return run
```

`backend/app/main.py`: directly after the `job_registry.register(Job(key=LLM_USAGE_CLEANUP_JOB_KEY, ...))` call, add:

```python
    from app.services.page_attachment_cleanup import (
        PAGE_ATTACHMENT_CLEANUP_CONFIG_SCHEMA,
        PAGE_ATTACHMENT_CLEANUP_JOB_KEY,
        make_page_attachment_cleanup_runner,
    )

    job_registry.register(Job(
        key=PAGE_ATTACHMENT_CLEANUP_JOB_KEY,
        display_name="Page Attachment Cleanup",
        description=(
            "Deletes page attachments no page block references once they are "
            "past the grace period, files left with no row by a crash, and "
            "stale import staging directories. Trashed pages still count as "
            "references, so emptying the trash is what releases a file."
        ),
        default_cron="20 * * * *",
        min_interval_seconds=600,
        runner=make_page_attachment_cleanup_runner(app, async_session_factory),
        config_schema=PAGE_ATTACHMENT_CLEANUP_CONFIG_SCHEMA,
    ))
```

`backend/tests/test_code_deriver.py`: in the `expected` set, change `"LLM_USAGE_CLEANUP_JOB_KEY", "BACKUP_SHIP_JOB_KEY",` to `"LLM_USAGE_CLEANUP_JOB_KEY", "BACKUP_SHIP_JOB_KEY", "PAGE_ATTACHMENT_CLEANUP_JOB_KEY",`.

`backend/tests/test_block_retrieval.py`: in `BLOCK_CHANNEL_MODULES`, after `"app.services.page_door",` add:

```python
    # Reads page block text to find which attachments are still referenced.
    "app.services.page_attachment_cleanup",
```

`CLAUDE.md`, Jobs section: change `**Twenty-four** registered jobs` to `**Twenty-five** registered jobs`, and prefix the parenthetical with `count corrected 2026-09-19: page_attachment_cleanup moved the prior **Twenty-four** up by one; ` ahead of the existing `count corrected 2026-09-02: ...`. Change `The eighteen live ones:` to `The nineteen live ones:` and append `, \`page_attachment_cleanup\`` after `` `backup_ship` `` in that list (before the full stop). In the next sentence listing constant-registered keys, add `page_attachment_cleanup` to the key list and `PAGE_ATTACHMENT_CLEANUP_JOB_KEY` to the constant list. In the single-worker invariant, change `24 today` to `25 today`.

`backend/tests/test_citation_reverifier.py`: `_NUMBER_WORDS` (line 1110) ends at `twenty-four`, so the CLAUDE.md count guard would raise `KeyError` on "Twenty-five". Change its last string line to:

```python
        "twenty twenty-one twenty-two twenty-three twenty-four twenty-five".split()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 .venv/bin/python -m pytest -q tests/test_page_attachment_cleanup.py tests/test_code_deriver.py tests/test_block_retrieval.py tests/test_citation_reverifier.py`
Expected: PASS.

- [ ] **Step 5: Run the guards leg**

Run (from `backend/`, 600 s timeout):

```bash
TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  .venv/bin/python -m pytest -q tests/test_content_surface_scoping.py tests/test_door_parity.py \
    tests/test_prompt_agent_instructions.py tests/test_api/test_rest_conformance.py \
    tests/test_sdk_generator.py tests/test_spa_edge.py tests/test_events.py \
    tests/test_mcp_auth.py tests/test_inert_objects.py tests/test_api/test_tags.py \
    tests/test_block_pipeline.py tests/test_block_retrieval.py tests/test_auto_research.py \
    tests/test_event_taxonomy_map.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/page_attachment_cleanup.py backend/app/main.py backend/tests/test_page_attachment_cleanup.py backend/tests/test_code_deriver.py backend/tests/test_block_retrieval.py backend/tests/test_citation_reverifier.py CLAUDE.md
git commit -m "feat(pages): add attachment cleanup job"
```
