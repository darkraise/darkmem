"""Fetch a snapshot back off a destination (increment 7 Task 10, spec §9.6).

The counterpart to ``backup_ship``, and the reason ``scripts/restore.sh``
grew a ``--from``: an operator restoring in anger should not have to know
whether the newest copy is on a NAS, in a bucket or on the worker.

**A pulled snapshot gets the same distrust as an uploaded one.** After the
download the destination is asked for the bytes again and the two hashes are
compared, because what is about to happen to this file is a replay into a
database -- the one place a silently corrupt copy costs more than the
transfer did.

Runnable as a module, and the last line of stdout is the path, which is the
shell contract ``restore.sh`` reads:

    python -m app.services.backup_pull --destination nas --latest --out /dumps
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import sys
from pathlib import Path

from app.services.attachment_archive import ATTACHMENTS, DUMPS, Family
from app.services.backup_ship import SnapshotInfo, build_destination

_CHUNK = 1 << 16


class SnapshotNotFound(RuntimeError):
    """The destination holds nothing by that name -- or nothing at all."""


class PullVerifyFailed(RuntimeError):
    """What came down is not what the destination says it holds."""


async def _destination_for(name: str):
    """Resolve one configured destination, unmasked.

    Its own function so the shell entry point and the tests reach the config
    the same way, and so a test can substitute a destination without a
    database.
    """
    from app.database import async_session_factory
    from app.services.backup_config import load_destinations

    async with async_session_factory() as session:
        configured = await load_destinations(session, masked=False)
    match = next((c for c in configured if c.name == name), None)
    if match is None:
        raise SnapshotNotFound(
            f"no destination named {name!r}; configured: "
            f"{[c.name for c in configured]}"
        )
    return build_destination(match)


async def paired_name(destination, dump_name: str) -> str:
    """The attachment tarball that goes with `dump_name`.

    The newest set captured at or before the dump. Correct because an unchanged
    set writes no tarball, so the newest at or before a dump is what was live
    when it was taken. The stamp is zero-padded and big-endian, so this is a
    lexical comparison and no mtime is trusted.
    """
    stamp = DUMPS.stamp_of(dump_name)
    if stamp is None:
        raise SnapshotNotFound(f"{dump_name!r} is not a dump this job produced")
    candidates = [
        s.name
        for s in await destination.list_snapshots(ATTACHMENTS)
        if (ATTACHMENTS.stamp_of(s.name) or "") <= stamp
    ]
    if not candidates:
        raise SnapshotNotFound(
            f"{destination.name} holds no attachment tarball at or before "
            f"{stamp}; restoring this dump serves rows whose files are gone"
        )
    return max(candidates)


async def pull(
    destination, *, name: str | None, out_dir: Path, family: Family = DUMPS
) -> Path:
    """Download one snapshot into `out_dir`, verified, and return its path.

    `name=None` means the newest, resolved by the stamp in the filename: it is
    zero-padded and big-endian, so lexical order is chronological and no
    destination's idea of an mtime is trusted (a copy resets one).
    """
    snapshots = await destination.list_snapshots(family)
    if not snapshots:
        raise SnapshotNotFound(f"{destination.name} holds no {family.prefix}* artefact")

    if name is None:
        chosen = max(snapshots, key=lambda s: s.name).name
    else:
        if not any(s.name == name for s in snapshots):
            raise SnapshotNotFound(
                f"{destination.name} does not hold {name!r}; newest is "
                f"{max(snapshots, key=lambda s: s.name).name}"
            )
        chosen = name

    out_dir = Path(out_dir)
    target = out_dir / chosen
    part = target.with_name(target.name + ".part")

    digest = hashlib.sha256()
    try:
        with open(part, "wb") as sink:
            async for chunk in destination.stream(chosen):
                digest.update(chunk)
                sink.write(chunk)
            sink.flush()
            os.fsync(sink.fileno())

        # The remote is asked again rather than trusted from the same read: a
        # transfer that dropped bytes would hash consistently with itself.
        expected = await destination.read_back_sha256(chosen)
        if expected != digest.hexdigest():
            raise PullVerifyFailed(
                f"{chosen} does not match {destination.name}: destination "
                f"reports {expected}, downloaded {digest.hexdigest()}"
            )
    except BaseException:
        part.unlink(missing_ok=True)
        raise

    os.replace(part, target)
    return target


async def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fetch a snapshot back off a configured backup destination."
    )
    parser.add_argument("--destination", required=True, help="configured destination name")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--latest", action="store_true", help="the newest snapshot")
    group.add_argument("--name", help="one snapshot by name")
    parser.add_argument(
        "--family", choices=("dump", "attachments"), default="dump",
        help="which artefact family to fetch",
    )
    group.add_argument(
        "--paired-with",
        help="the dump whose attachment tarball to fetch (implies --family attachments)",
    )
    parser.add_argument("--out", default="/dumps", help="directory to write into")
    args = parser.parse_args(argv)

    destination = await _destination_for(args.destination)
    if args.paired_with:
        path = await pull(
            destination,
            name=await paired_name(destination, args.paired_with),
            out_dir=Path(args.out),
            family=ATTACHMENTS,
        )
    else:
        family = ATTACHMENTS if args.family == "attachments" else DUMPS
        path = await pull(
            destination,
            name=None if args.latest else args.name,
            out_dir=Path(args.out),
            family=family,
        )
    # The shell contract: the path is the LAST line, so a caller can `tail -1`
    # it without parsing anything the client library might log above.
    print(path)
    return 0


if __name__ == "__main__":  # pragma: no cover - shell entry point
    sys.exit(asyncio.run(_main()))
