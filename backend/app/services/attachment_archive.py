"""The attachment artefact family: what its names look like, how one is built,
and what the ship job remembers between runs (spec §5.1, §5.3).

Separate from `backup_ship` for two reasons. That module is already a thousand
lines, and the family predicate has to be importable by anything that lists or
prunes -- a prune that guessed at a name would be a retention pass over the
wrong artefacts, which is data loss rather than a bug.
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Config
from app.services.page_attachments import STAGING_DIRNAME, attachments_root

logger = logging.getLogger(__name__)

DUMP_PREFIX = "darkmem-app-"
ATTACHMENTS_PREFIX = "darkmem-app-attachments-"

ATTACHMENTS_STATE_KEY = "backup_ship_attachments_state"

_STAMP_FORMAT = "%Y%m%d-%H%M%S"
#: tar's own exit code for "file changed as we read it". Expected against a
#: live volume the cleanup job may be unlinking from, and accepted; any other
#: non-zero status is a real failure.
_TAR_FILE_CHANGED = 1


class ArchiveIncomplete(RuntimeError):
    """The archive holds no files while the database holds rows.

    The tarball's equivalent of pg_dump's completion marker. Without it a
    mis-mounted or empty volume produces a well-formed archive under the
    canonical name, whose manifest then reads as current forever.
    """


@dataclass(frozen=True)
class Family:
    """One artefact family's naming, and the only way to classify a name.

    Prefix *and* suffix, because the attachments prefix is a strict extension
    of the dump prefix: `darkmem-app-attachments-...` starts with
    `darkmem-app-`, and only the suffix separates them. A `.part` matches
    neither, which is what keeps an in-flight write out of a prune's set.
    """

    prefix: str
    suffixes: tuple[str, ...]

    def matches(self, name: str) -> bool:
        if not name.startswith(self.prefix):
            return False
        if self is DUMPS and name.startswith(ATTACHMENTS_PREFIX):
            return False
        return any(name.endswith(suffix) for suffix in self.suffixes)

    def stamp_of(self, name: str) -> str | None:
        """The stamp token, for comparing against a recorded one."""
        if not self.matches(name):
            return None
        core = name[len(self.prefix):].split(".")[0]
        try:
            datetime.strptime(core, _STAMP_FORMAT)
        except ValueError:
            return None
        return core

    def stamp_datetime(self, name: str) -> datetime:
        """The display value. An unparseable name falls back to the epoch
        rather than raising: a listing that 500s over one foreign file is the
        worse surface."""
        token = self.stamp_of(name)
        if token is None:
            return datetime.fromtimestamp(0, timezone.utc)
        return datetime.strptime(token, _STAMP_FORMAT).replace(tzinfo=timezone.utc)


DUMPS = Family(DUMP_PREFIX, (".sql.gz", ".sql.gz.age"))
ATTACHMENTS = Family(ATTACHMENTS_PREFIX, (".tar.gz", ".tar.gz.age"))


@dataclass(frozen=True)
class ArchiveState:
    """What the last tarball this job produced was, and of which set.

    Its own `config` row rather than `job:backup_ship`, which the job registry
    validates against a `config_schema` whose `FieldDescriptor.default` is
    typed `int` and so cannot carry either of these strings.
    """

    stamp: str
    manifest_hash: str


async def load_state(session: AsyncSession) -> ArchiveState | None:
    row = (
        await session.execute(
            select(Config).where(Config.key == ATTACHMENTS_STATE_KEY)
        )
    ).scalar_one_or_none()
    if row is None or not row.value:
        return None
    stamp = row.value.get("stamp")
    manifest = row.value.get("manifest_hash")
    if not stamp or not manifest:
        return None
    return ArchiveState(stamp=stamp, manifest_hash=manifest)


async def save_state(session: AsyncSession, state: ArchiveState) -> None:
    payload = {"stamp": state.stamp, "manifest_hash": state.manifest_hash}
    row = (
        await session.execute(
            select(Config).where(Config.key == ATTACHMENTS_STATE_KEY)
        )
    ).scalar_one_or_none()
    if row:
        row.value = payload
    else:
        session.add(Config(key=ATTACHMENTS_STATE_KEY, value=payload))
    await session.commit()


def _count_members(listing: str) -> int:
    """Regular files in tar's own `-v` output.

    Counted from the listing tar already produces rather than by reading the
    archive back: a second pass over a multi-gigabyte artefact costs the whole
    decompression for a number tar just told us.
    """
    return sum(
        1
        for line in listing.splitlines()
        if line.strip() and not line.rstrip().endswith("/")
    )


async def build_archive(dest_dir: Path, stamp: str, *, expect_rows: int) -> Path:
    """Tar the attachment store into `dest_dir`, `.part` then `os.replace`.

    A subprocess rather than `tarfile`: compressing gigabytes on the event loop
    would stall the single worker (invariant 13) for the whole run.
    """
    dest_dir = Path(dest_dir)
    out = dest_dir / f"{ATTACHMENTS_PREFIX}{stamp}.tar.gz"
    part = out.with_name(out.name + ".part")
    root = attachments_root()

    argv = [
        "tar",
        "-czvf",
        "-",
        "-C",
        str(root),
        "--exclude=*.part",
        f"--exclude=./{STAGING_DIRNAME}",
        "--ignore-failed-read",
        "--warning=no-file-changed",
        ".",
    ]
    try:
        with open(part, "wb") as sink:
            proc = await asyncio.create_subprocess_exec(
                *argv, stdout=sink, stderr=asyncio.subprocess.PIPE
            )
            listing = (await proc.stderr.read()) if proc.stderr else b""
            code = await proc.wait()
        if code not in (0, _TAR_FILE_CHANGED):
            raise ArchiveIncomplete(
                f"tar exited {code}: "
                f"{listing.decode('utf-8', 'replace')[-500:]}"
            )
        members = _count_members(listing.decode("utf-8", "replace"))
        if expect_rows > 0 and members == 0:
            raise ArchiveIncomplete(
                f"{root} archived no files while page_attachments holds "
                f"{expect_rows} rows -- the attachment store is empty or not "
                f"mounted. Nothing renamed."
            )
        if members < expect_rows:
            logger.warning(
                "attachment archive holds %s files against %s rows; the "
                "cleanup job may have unlinked one mid-run",
                members,
                expect_rows,
            )
    except BaseException:
        part.unlink(missing_ok=True)
        raise

    os.replace(part, out)
    return out
