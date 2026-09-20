"""Importing a Notion export into one project's page tree.

Three phases: the body streams to staging, the plan is built off the event loop
with no database access, and one transaction writes everything. Exactly one
import runs at a time and a second is refused before its bytes are read, so a
caller learns it is queued without first uploading a gigabyte.
"""
from __future__ import annotations

import asyncio
import errno
import shutil
import time
from collections.abc import AsyncIterator, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.events import record_event
from app.services.notion_archive import NotionArchive, open_archive
from app.services.notion_content import (
    StagedAsset,
    preprocess,
    resolve_target,
    scan_links,
    translate_page,
)
from app.services.notion_tree import NotionExportInvalid, NotionTree, build_tree
from app.services.page_attachments import (
    STAGING_DIRNAME,
    attachment_path,
    attachments_root,
    clean_filename,
    insert_attachment_row,
    place_staged,
)
from app.services.page_door import (
    _LOCK_ROOT,
    MAX_BLOCKS,
    MAX_CONTENT_CHARS,
    _insert_page,
    root_lock_key,
)

MAX_WARNINGS = 500
PAGES_IMPORTED_EVENT = "pages_imported"
# Staging may hold the zip, a Part export's extracted members, and each
# referenced attachment at once. Text expands further but is never staged as a
# file; `notion_import_max_uncompressed_bytes` bounds that side.
SPACE_FACTOR = 3

# In-process, and valid for the reason the login limiter's state is: invariant
# 13 gives one worker and one event loop.
_import_lock = asyncio.Lock()


class ImportBusy(RuntimeError):
    """Another import holds the lock."""


class ImportTooLarge(ValueError):
    """The body passed `notion_import_max_bytes`."""


class ImportNoSpace(RuntimeError):
    """The attachments filesystem cannot hold the upload and its extraction."""


class ImportTimedOut(RuntimeError):
    """The import passed `notion_import_max_seconds`."""


def _timed_out() -> ImportTimedOut:
    return ImportTimedOut(
        f"the import passed its {settings.notion_import_max_seconds}s bound "
        "(notion_import_max_seconds)"
    )


@dataclass(frozen=True)
class ImportWarning:
    path: str | None
    kind: str
    detail: str


@dataclass(frozen=True)
class ImportReport:
    root_page_id: UUID
    pages_created: int
    databases: int
    attachments_stored: int
    attachment_bytes: int
    warnings: list[ImportWarning]
    warnings_omitted: int


@dataclass
class _Warnings:
    kept: list[ImportWarning] = field(default_factory=list)
    omitted: int = 0

    def add(self, path: str | None, kind: str, detail: str) -> None:
        if len(self.kept) < MAX_WARNINGS:
            self.kept.append(ImportWarning(path or None, kind, detail))
        else:
            self.omitted += 1


@dataclass(frozen=True)
class _Plan:
    tree: NotionTree
    assets: dict[str, StagedAsset]
    blocks: dict[UUID, list]


def _unreported(path: str, kind: str, detail: str) -> None:
    """The reference scan runs the text pre-pass a second time; the translation
    is the pass that reports what it changed, once."""


def _free_bytes() -> int:
    return shutil.disk_usage(attachments_root()).free


def _require_space(needed: int) -> None:
    if needed and _free_bytes() < needed * SPACE_FACTOR:
        raise ImportNoSpace(
            f"the attachments filesystem has less than {needed * SPACE_FACTOR} "
            "bytes free"
        )


async def _stage_body(
    body: AsyncIterator[bytes], staging: Path, max_bytes: int,
) -> Path:
    target = staging / "upload.zip"
    size = 0
    with open(target, "wb") as handle:
        async for chunk in body:
            if not chunk:
                continue
            size += len(chunk)
            if size > max_bytes:
                raise ImportTooLarge(f"the export exceeds {max_bytes} bytes")
            handle.write(chunk)
    return target


def _build_plan(
    zip_path: Path, staging: Path, deadline: float,
    warn: Callable[[str, str, str], None],
) -> tuple[NotionArchive, _Plan]:
    """Everything between the upload and the write. No database access.

    Note every page's source is read three times — once by `build_tree` for its
    title and property block, once by the reference scan below, once by the
    translation — and the archive's running counter is cumulative, so
    `notion_import_max_uncompressed_bytes` bounds roughly a third of that figure
    in text. Accepted: the ceiling is 5 GB against a measured 37 MB.
    """
    archive = open_archive(
        zip_path, staging / "parts",
        max_entries=settings.notion_import_max_entries,
        max_uncompressed_bytes=settings.notion_import_max_uncompressed_bytes,
        warn=warn,
    )
    try:
        tree = build_tree(archive, max_pages=settings.notion_import_max_pages, warn=warn)

        # Only assets something links to. An unreferenced one would become a row
        # and a file that nothing in the corpus points at, for the cleanup job to
        # collect a week later. The scan runs on the pre-processed text the
        # translation will rewrite, not the raw source: a reference-style link
        # is not a link until its definition has been inlined.
        referenced: set[str] = set()
        for node in tree.pages:
            if node.entry is None:
                continue
            source = preprocess(
                archive.read_text(node.entry), node.entry.name, _unreported,
            )
            for span in scan_links(source):
                target = unquote(span.destination.split("#")[0])
                referenced.add(resolve_target(target, node.entry.name))

        assets: dict[str, StagedAsset] = {}
        refused: set[str] = set()
        asset_dir = staging / "assets"
        for name, entry in tree.assets.items():
            if name not in referenced:
                continue
            attachment_id = uuid4()
            destination = asset_dir / str(attachment_id)
            size, digest, content_type = archive.extract(entry, destination)
            if size > settings.attachment_max_bytes:
                destination.unlink(missing_ok=True)
                refused.add(name)
                warn(name, "oversize_attachment",
                     f"{size} bytes is over the {settings.attachment_max_bytes} bound")
                continue
            assets[name] = StagedAsset(
                attachment_id=attachment_id, staged_path=destination,
                filename=clean_filename(name.rsplit("/", 1)[-1]),
                content_type=content_type, size_bytes=size, sha256=digest,
            )

        blocks: dict[UUID, list] = {}
        total = 0
        for node in tree.pages:
            if time.monotonic() > deadline:
                raise _timed_out()
            rendered = translate_page(
                node, tree, archive, assets=assets, refused=frozenset(refused),
                max_blocks=MAX_BLOCKS, max_content_chars=MAX_CONTENT_CHARS, warn=warn,
            )
            total += len(rendered)
            if total > settings.notion_import_max_blocks:
                raise NotionExportInvalid(
                    f"the export exceeds {settings.notion_import_max_blocks} blocks"
                )
            blocks[node.uuid] = rendered
    except BaseException:
        archive.close()
        raise
    return archive, _Plan(tree=tree, assets=assets, blocks=blocks)


async def import_notion_export(
    session: AsyncSession,
    *,
    project: str,
    body: AsyncIterator[bytes],
    declared_length: int | None,
    actor: str | None,
) -> ImportReport:
    # Checked before acquiring, and acquired with no await in between, so the
    # window this shape usually opens does not exist here (invariant 13).
    if _import_lock.locked():
        raise ImportBusy("an import is already running")
    async with _import_lock:
        return await _run_import(
            session, project=project, body=body,
            declared_length=declared_length, actor=actor,
        )


async def _run_import(
    session: AsyncSession,
    *,
    project: str,
    body: AsyncIterator[bytes],
    declared_length: int | None,
    actor: str | None,
) -> ImportReport:
    warnings = _Warnings()
    staging = attachments_root() / STAGING_DIRNAME / str(uuid4())
    placed: list[UUID] = []
    archive: NotionArchive | None = None
    planned = False
    deadline = time.monotonic() + settings.notion_import_max_seconds
    # A dedicated single-thread executor, not the default one: that also serves
    # bcrypt MCP auth, git subprocesses and code parsing. It does NOT serialise
    # imports -- the lock above does.
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="notion-import")
    try:
        staging.mkdir(parents=True, exist_ok=True)
        if declared_length:
            _require_space(declared_length)
        zip_path = await _stage_body(
            body, staging, settings.notion_import_max_bytes
        )
        _require_space(zip_path.stat().st_size)

        loop = asyncio.get_running_loop()
        archive, plan = await loop.run_in_executor(
            executor, _build_plan, zip_path, staging, deadline, warnings.add,
        )
        planned = True
        zip_path.unlink(missing_ok=True)

        await session.execute(_LOCK_ROOT, {"key": root_lock_key(project)})

        # Files BEFORE rows: a file with no row is swept by the cleanup job,
        # while a row with no file is a permanent 404 nothing repairs.
        for staged in plan.assets.values():
            await asyncio.to_thread(
                place_staged, staged.staged_path, staged.attachment_id
            )
            placed.append(staged.attachment_id)
        for staged in plan.assets.values():
            await insert_attachment_row(
                session,
                attachment_id=staged.attachment_id,
                project=project,
                page_id=None,
                filename=staged.filename,
                content_type=staged.content_type,
                size_bytes=staged.size_bytes,
                sha256=staged.sha256,
            )

        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        root = await _insert_page(
            session, project=project, parent_id=None, after_id=None,
            title=f"Notion import — {stamp} UTC", tree=[],
            properties=None, actor=actor,
        )

        ids: dict[UUID, UUID] = {}
        for node in plan.tree.pages:
            if time.monotonic() > deadline:
                raise _timed_out()
            parent = ids[node.parent_uuid] if node.parent_uuid else root.id
            properties = {"notion_id": node.notion_id} if node.notion_id else None
            written = await _insert_page(
                session, project=project, parent_id=str(parent), after_id=None,
                title=node.title, tree=plan.blocks[node.uuid],
                properties=properties, actor=actor, page_id=node.uuid,
            )
            ids[node.uuid] = written.id

        signals = plan.tree.signal_counts
        if signals.get("database") or signals.get("link"):
            warnings.add(
                None, "derived_hierarchy",
                "hierarchy derived from the export: "
                f"{signals.get('database', 0)} by database membership, "
                f"{signals.get('link', 0)} by a standalone link, "
                f"{signals.get('root', 0)} left at the root",
            )

        await record_event(
            session,
            event_type=PAGES_IMPORTED_EVENT,
            object_type="page",
            object_id=root.id,
            project=project,
            actor=actor,
            payload={
                "pages_created": len(plan.tree.pages),
                "databases": len(plan.tree.databases),
                "attachments_stored": len(plan.assets),
                "warnings": len(warnings.kept) + warnings.omitted,
            },
        )
        await session.commit()
        return ImportReport(
            root_page_id=root.id,
            pages_created=len(plan.tree.pages),
            databases=len(plan.tree.databases),
            attachments_stored=len(plan.assets),
            attachment_bytes=sum(a.size_bytes for a in plan.assets.values()),
            warnings=warnings.kept,
            warnings_omitted=warnings.omitted,
        )
    except BaseException as exc:
        await session.rollback()
        for attachment_id in placed:
            await asyncio.to_thread(
                attachment_path(attachment_id).unlink, True
            )
        # Staging and extraction are the only phases that write bytes the disk
        # can refuse; past them a full disk is not the explanation and saying so
        # would be a guess.
        if not planned and isinstance(exc, OSError) and exc.errno == errno.ENOSPC:
            raise ImportNoSpace(
                "the attachments filesystem ran out of space during the import"
            ) from exc
        raise
    finally:
        if archive is not None:
            archive.close()
        executor.shutdown(wait=False)
        await asyncio.to_thread(shutil.rmtree, staging, True)
