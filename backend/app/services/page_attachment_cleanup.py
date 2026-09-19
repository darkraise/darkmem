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
import os
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
_LOG_SAMPLE = 50
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
# The cast is not decoration: an uncast array param is only inferable
# because the left operand is a uuid column, which any rewrite of this
# predicate would take away (CLAUDE.md, "asyncpg needs CAST").
_KNOWN_IDS = text(
    "SELECT id FROM page_attachments WHERE id = ANY(CAST(:ids AS uuid[]))"
)


@dataclass
class CleanupReport:
    rows_deleted: int = 0
    files_unlinked: int = 0
    rowless_files_removed: int = 0
    part_files_removed: int = 0
    staging_dirs_removed: int = 0
    # Inside total() on purpose: a run that removed nothing but failed on
    # something still owes a job_runs row carrying the count.
    files_failed: int = 0

    def total(self) -> int:
        return sum(asdict(self).values())


def _log_removed(what: str, items: list) -> None:
    """The sweep is irreversible, so what it took is worth more than a count.

    Bounded rather than complete: a run that collects a backlog must not write
    a log line proportional to it.
    """
    if not items:
        return
    sample = ", ".join(str(item) for item in items[:_LOG_SAMPLE])
    overflow = len(items) - _LOG_SAMPLE
    logger.info(
        "page_attachment_cleanup: %s (%d): %s%s",
        what, len(items), sample,
        f", and {overflow} more" if overflow > 0 else "",
    )


def _unlink(paths: list[Path]) -> tuple[int, int]:
    removed = 0
    failed = 0
    for path in paths:
        try:
            path.unlink()
            removed += 1
        except FileNotFoundError:
            pass
        except OSError as exc:
            logger.warning(
                "page_attachment_cleanup: could not remove %s: %s", path, exc
            )
            failed += 1
    return removed, failed


def _scan(root: Path, now: float) -> tuple[list[tuple[UUID, Path]], list[Path]]:
    files: list[tuple[UUID, Path]] = []
    parts: list[Path] = []
    if not root.is_dir():
        return files, parts
    for shard in root.iterdir():
        if not (shard.is_dir() and _SHARD.fullmatch(shard.name)):
            continue
        try:
            # Materialised inside the guard: iterdir() is lazy, so an
            # unreadable shard raises during iteration, not at the call.
            entries = list(shard.iterdir())
        except OSError as exc:
            logger.warning(
                "page_attachment_cleanup: could not scan %s: %s", shard, exc
            )
            continue
        for entry in entries:
            try:
                stat = entry.stat()
            except FileNotFoundError:
                continue
            except OSError as exc:
                logger.warning(
                    "page_attachment_cleanup: could not stat %s: %s", entry, exc
                )
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


def _remove_stale_staging(
    root: Path, max_age_seconds: float, now: float
) -> tuple[int, int]:
    staging = root / STAGING_DIRNAME
    if not staging.is_dir():
        return 0, 0
    removed = 0
    failed = 0
    try:
        # Materialised inside the guard for the reason the shard scan is, and
        # counted as a failure so the run still owes a job_runs row.
        entries = list(staging.iterdir())
    except OSError as exc:
        logger.warning(
            "page_attachment_cleanup: could not scan %s: %s", staging, exc
        )
        return 0, 1
    for entry in entries:
        try:
            stale = entry.is_dir() and now - entry.stat().st_mtime > max_age_seconds
        except FileNotFoundError:
            continue
        except OSError as exc:
            logger.warning(
                "page_attachment_cleanup: could not stat %s: %s", entry, exc
            )
            continue
        if stale:
            shutil.rmtree(entry, ignore_errors=True)
            # rmtree swallows its own errors, so the tree itself is the verdict.
            if not os.path.lexists(entry):
                removed += 1
            else:
                logger.warning(
                    "page_attachment_cleanup: could not remove staging dir %s", entry
                )
                failed += 1
    return removed, failed


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
            _log_removed("deleted unreferenced rows", ids)
            report.files_unlinked, failed = await asyncio.to_thread(
                _unlink, [attachment_path(i) for i in ids]
            )
            report.files_failed += failed

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
        _log_removed("removing row-less files", rowless)
        report.rowless_files_removed, failed = await asyncio.to_thread(_unlink, rowless)
        report.files_failed += failed
    report.part_files_removed, failed = await asyncio.to_thread(_unlink, parts)
    report.files_failed += failed
    report.staging_dirs_removed, failed = await asyncio.to_thread(
        _remove_stale_staging, root, staging_max_age_hours * 3600, now
    )
    report.files_failed += failed
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
