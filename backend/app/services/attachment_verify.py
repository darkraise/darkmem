"""Does every row have its file, and every file its row (spec §10).

Run after any restore. A dump newer than its paired tarball, a tarball that
paired with nothing, and a worker cycle killed between the database rename and
the symlink swap all leave rows whose files are absent, and nothing else
reports that.

Read-only on purpose: it opens no write transaction and unlinks nothing. The
repair for a missing file is another restore, never a delete, and the repair
for a row-less file is the cleanup job -- which has its own refusal for exactly
the bulk case this reports.

    docker compose exec darkmem python -m app.services.attachment_verify
"""
from __future__ import annotations

import asyncio
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy import text

from app.services.page_attachments import attachment_path, attachments_root

_ROWS = text("SELECT id FROM page_attachments ORDER BY created_at, id")
_SHARD = re.compile(r"[0-9a-f]{2}")
#: Enough to act on. A restore that went wrong is wrong in bulk, and printing
#: ten thousand ids helps nobody read the count above them.
_SAMPLE = 20


@dataclass(frozen=True)
class VerifyReport:
    missing_files: list[str]
    rowless_files: list[str]

    def ok(self) -> bool:
        return not self.missing_files and not self.rowless_files


def _missing(ids: list[str]) -> list[str]:
    return [i for i in ids if not attachment_path(UUID(i)).is_file()]


def _on_disk(root: Path) -> set[str]:
    """Every file named like an attachment id. A `.part` is an in-flight
    upload and a dot-directory is staging; neither is a row's file."""
    found: set[str] = set()
    if not root.is_dir():
        return found
    for shard in root.iterdir():
        if not (shard.is_dir() and _SHARD.fullmatch(shard.name)):
            continue
        for entry in shard.iterdir():
            if not entry.is_file() or entry.name.endswith(".part"):
                continue
            try:
                attachment_id = UUID(entry.name)
            except ValueError:
                continue
            if str(attachment_id) == entry.name:
                found.add(entry.name)
    return found


async def verify(session) -> VerifyReport:
    ids = [str(row[0]) for row in (await session.execute(_ROWS)).all()]
    missing = await asyncio.to_thread(_missing, ids)
    on_disk = await asyncio.to_thread(_on_disk, attachments_root())
    return VerifyReport(
        missing_files=missing,
        rowless_files=sorted(on_disk - set(ids)),
    )


def _print(title: str, items: list[str]) -> None:
    print(f"{title}: {len(items)}")
    for item in items[:_SAMPLE]:
        print(f"  {item}")
    if len(items) > _SAMPLE:
        print(f"  ... and {len(items) - _SAMPLE} more")


async def _main() -> int:
    from app.database import async_session_factory

    async with async_session_factory() as session:
        report = await verify(session)
    _print("rows whose file is missing", report.missing_files)
    _print("files with no row", report.rowless_files)
    return 0 if report.ok() else 1


if __name__ == "__main__":  # pragma: no cover - shell entry point
    sys.exit(asyncio.run(_main()))
