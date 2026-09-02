"""Off-host snapshot shipping (spec section 9.3-9.4, as amended after review M4).

This job does **not** call ``scripts/backup.sh`` and cannot: the app container
has no compose binary, no docker socket and no mount reaching the host's
``/root/darkmem-backups``. It runs the image's own ``pg_dump`` over the stack
network instead, which is why the runtime stage installs ``postgresql-client``.

Two independent producers is the design. The systemd timer writes
``darkmem-<stamp>.sql.gz`` into ``/root/darkmem-backups``; this job writes
``darkmem-app-<stamp>.sql.gz[.age]`` into ``/dumps``. Nothing serialises the
two -- different processes, and the per-job ``asyncio.Lock`` binds only
in-process -- so the job's default cron sits an hour clear of the timer and
both producers' ``.part`` discipline makes a rare overlap benign. The prune
below matches only this producer's prefix, so it can never delete a systemd
dump even if an operator points both at one directory.

Invariant 13: hashing and encryption are executor-offloaded or run as
subprocesses. The one thing that does run on the event loop is gzip inside the
dump's chunk loop; see ``run_dump``.
"""
from __future__ import annotations

import asyncio
import gzip
import hashlib
import logging
import os
import shutil
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from app.config import settings
from app.services.backup_config import DestinationConfig, load_destinations
from app.services.events import record_event

logger = logging.getLogger(__name__)

BACKUP_SHIP_JOB_KEY = "backup_ship"

#: The container-side bind mount. The host side defaults to
#: ``/srv/darkmem-dumps`` (docker-compose.yml) and must be writable by the
#: image's unprivileged `app` user -- a host bind mount is not chowned by
#: Docker the way a fresh named volume is.
DUMP_DIR = Path("/dumps")

#: This producer's filename prefix. The systemd producer's retention glob
#: ``darkmem-*.sql.gz`` would match it, which is why the two never share a
#: directory and why every prune here is prefix-scoped.
JOB_PREFIX = "darkmem-app-"

#: pg_dump writes this last and only on success. Checked against the raw
#: stream, so nothing has to be decompressed to run the check.
COMPLETION_MARKER = b"PostgreSQL database dump complete"

_CHUNK = 1 << 16
#: Enough to hold the marker plus pg_dump's trailing newline across any chunk
#: boundary, matching backup.sh's own `tail -c 512`.
_TAIL_BYTES = 512


class DumpIncomplete(RuntimeError):
    """pg_dump exited non-zero, or exited 0 having written a truncated stream."""


class DumpDirectoryUnusable(RuntimeError):
    """The dump directory does not exist or the process cannot write it."""


class EncryptFailed(RuntimeError):
    """`age` refused the recipient or failed to write the ciphertext."""


class VerifyMismatch(RuntimeError):
    """The bytes read back off a destination are not the bytes we sent.

    Its own type rather than a boolean so the journal can distinguish "the
    upload is not restorable" from "the upload never happened": both are
    failures, but only the first means a destination is holding a corrupt
    snapshot it will happily list as good.
    """

    def __init__(self, *, expected: str, got: str):
        super().__init__(f"read-back mismatch: expected {expected}, got {got}")
        self.expected = expected
        self.got = got


def _dump_argv() -> list[str]:
    """The dump command, read from settings at call time.

    A module-level constant would freeze the connection parameters at import,
    and tests replace this function wholesale to stand in a fake producer. The
    password is deliberately absent: it rides ``PGPASSWORD`` on the subprocess
    env, because an argv password is readable in ``ps`` for the dump's whole
    duration.
    """
    return [
        "pg_dump",
        "--clean",
        "--if-exists",
        "-h",
        settings.db_host,
        "-p",
        str(settings.db_port),
        "-U",
        settings.db_user,
        settings.db_name,
    ]


def _assert_writable(directory: Path) -> None:
    if not directory.is_dir():
        raise DumpDirectoryUnusable(
            f"{directory} does not exist. The dump mount is a host bind mount "
            f"and Docker does not chown one: create it owned by the image's "
            f"uid ({os.getuid()}) before the first ship."
        )
    if not os.access(directory, os.W_OK | os.X_OK):
        raise DumpDirectoryUnusable(
            f"{directory} is not writable by uid {os.getuid()}. A host bind "
            f"mount arrives owned by whoever created it; chown it to the "
            f"image's uid."
        )


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


async def run_dump(*, dest_dir: Path | None = None) -> Path:
    """Dump the database to a gzipped file, renamed only once it is known good.

    Written to ``<name>.part`` first for the same reason ``backup.sh`` does it:
    the file exists before pg_dump writes a byte and gzip exits 0 on empty
    input, so writing straight to the final name leaves a well-formed empty
    archive behind on every failure -- and retention sorts by mtime, so those
    artefacts are always the newest files on disk and outlive every real dump.

    Compression runs on the event loop inside the chunk loop below, which on a
    single worker (invariant 13) is a real stall for the dump's duration.
    Accepted at 04:30 against this corpus and stated rather than hidden; the
    repair, if it ever bites, is a ``pg_dump | gzip`` subprocess pipe, which
    keeps the marker check on the raw stream and moves the CPU out of the loop.
    """
    directory = Path(dest_dir) if dest_dir is not None else DUMP_DIR
    _assert_writable(directory)

    out = directory / f"{JOB_PREFIX}{_stamp()}.sql.gz"
    part = out.with_name(out.name + ".part")

    env = dict(os.environ, PGPASSWORD=settings.db_password)
    proc = await asyncio.create_subprocess_exec(
        *_dump_argv(),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )

    tail = b""
    try:
        with gzip.open(part, "wb") as sink:
            assert proc.stdout is not None
            while True:
                chunk = await proc.stdout.read(_CHUNK)
                if not chunk:
                    break
                sink.write(chunk)
                # A rolling tail of the RAW stream: the marker may straddle a
                # chunk boundary, and a per-chunk check would miss it.
                tail = (tail + chunk)[-_TAIL_BYTES:]
        stderr = (await proc.stderr.read()) if proc.stderr else b""
        code = await proc.wait()
        if code != 0:
            raise DumpIncomplete(
                f"pg_dump exited {code}: {stderr.decode('utf-8', 'replace')[-500:]}"
            )
        if COMPLETION_MARKER not in tail:
            raise DumpIncomplete(
                "pg_dump exited 0 but wrote no completion marker -- the stream "
                "was truncated. Nothing renamed."
            )
    except BaseException:
        part.unlink(missing_ok=True)
        if proc.returncode is None:
            proc.kill()
            await proc.wait()
        raise

    os.replace(part, out)
    return out


async def encrypt(path: Path, recipient: str) -> Path:
    """Encrypt to ``<path>.age`` with an X25519 recipient and drop the plaintext.

    Asymmetric on purpose: the recipient (public key) lives in the destinations
    config row and encrypts; the identity (private key) is the operator's and
    never enters this database, because a snapshot that carried its own
    decryption key would not be encrypted at rest. `age`'s passphrase mode is
    interactive-only, so this is also the only scriptable shape.
    """
    out = path.with_name(path.name + ".age")
    proc = await asyncio.create_subprocess_exec(
        "age",
        "-r",
        recipient,
        "-o",
        str(out),
        str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        out.unlink(missing_ok=True)
        raise EncryptFailed(
            f"age exited {proc.returncode}: "
            f"{stderr.decode('utf-8', 'replace')[-500:]}"
        )
    # Only now: a failed encrypt must never destroy the only copy of the dump.
    path.unlink(missing_ok=True)
    return out


def _sha256_sync(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


async def sha256_file(path: Path) -> str:
    """Hash off the event loop -- a multi-megabyte inline hash is a stall."""
    return await asyncio.to_thread(_sha256_sync, path)


# ---------------------------------------------------------------------------
# Destinations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SnapshotInfo:
    name: str
    size: int
    modified_at: datetime


class Destination(Protocol):
    """What every destination kind must serve.

    ``read_back_sha256`` is a full byte read-back on purpose, never a remote
    checksum the destination computes for us: section 9.4 rule 2 is about what
    *we* can read back, not what the remote claims about bytes we cannot see.
    """

    name: str
    retention_keep: int

    async def ship(self, local_path: Path) -> None: ...

    async def read_back_sha256(self, name: str) -> str: ...

    async def list_snapshots(self) -> list[SnapshotInfo]: ...

    async def prune(self, keep: int) -> list[str]: ...


def _is_snapshot(name: str) -> bool:
    """This producer's artefacts, and only them.

    A `.part` is an in-flight write and never a snapshot; the systemd
    producer's ``darkmem-<stamp>.sql.gz`` fails the prefix. Both exclusions
    are the difference between a retention pass and data loss.
    """
    return name.startswith(JOB_PREFIX) and (
        name.endswith(".sql.gz") or name.endswith(".sql.gz.age")
    )


def _survivors_and_deletions(
    entries: list[tuple[str, float]], keep: int
) -> list[str]:
    """Newest `keep` survive; the rest are returned for deletion.

    Ordered by ``(mtime, name)`` descending so two snapshots written inside one
    second still have a total order -- the stamp in the name breaks the tie,
    and it sorts lexically because it is zero-padded and big-endian.
    """
    ordered = sorted(entries, key=lambda e: (e[1], e[0]), reverse=True)
    return [name for name, _ in ordered[keep:]]


class LocalDestination:
    """The ``/dumps`` directory itself.

    ``ship`` is a copy rather than a no-op because an encrypted artefact is
    produced in a scratch subdirectory: the plaintext dump already sits here,
    but its ciphertext does not until this runs. A copy rather than a move
    because two destinations may share one recipient and therefore one file.
    """

    def __init__(self, *, name: str, directory: Path, retention_keep: int = 14):
        self.name = name
        self.directory = Path(directory)
        self.retention_keep = retention_keep

    async def ship(self, local_path: Path) -> None:
        target = self.directory / local_path.name
        if local_path.resolve() == target.resolve():
            return
        await asyncio.to_thread(shutil.copyfile, local_path, target)

    async def read_back_sha256(self, name: str) -> str:
        return await sha256_file(self.directory / name)

    async def list_snapshots(self) -> list[SnapshotInfo]:
        out = []
        for path in self.directory.iterdir():
            if not path.is_file() or not _is_snapshot(path.name):
                continue
            stat = path.stat()
            out.append(
                SnapshotInfo(
                    name=path.name,
                    size=stat.st_size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc),
                )
            )
        return sorted(out, key=lambda s: s.name)

    async def prune(self, keep: int) -> list[str]:
        entries = [
            (p.name, p.stat().st_mtime)
            for p in self.directory.iterdir()
            if p.is_file() and _is_snapshot(p.name)
        ]
        deleted = _survivors_and_deletions(entries, keep)
        for name in deleted:
            (self.directory / name).unlink(missing_ok=True)
        return deleted


def build_destination(cfg: DestinationConfig) -> Destination:
    if cfg.kind == "local":
        return LocalDestination(
            name=cfg.name, directory=DUMP_DIR, retention_keep=cfg.retention_keep
        )
    raise ValueError(f"{cfg.name}: no client for kind {cfg.kind!r}")


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------

#: Where per-recipient ciphertexts are staged. Inside the dump directory so
#: the encrypt is a local write, and dotted so no snapshot glob can see it.
_SCRATCH = ".enc"


async def _artifacts_for(
    dump: Path, recipients: list[str | None]
) -> dict[str | None, Path]:
    """One artefact per distinct recipient, plus the plaintext if anything wants it.

    Encrypting once per recipient rather than once per destination matters when
    several destinations share an operator's single age key, which is the
    common case: the alternative re-encrypts the whole dump per NAS.
    """
    artifacts: dict[str | None, Path] = {}
    scratch = dump.parent / _SCRATCH
    for recipient in recipients:
        if recipient is None:
            artifacts[None] = dump
            continue
        if recipient in artifacts:
            continue
        staged = scratch / hashlib.sha256(recipient.encode()).hexdigest()[:16]
        staged.mkdir(parents=True, exist_ok=True)
        copy = staged / dump.name
        await asyncio.to_thread(shutil.copyfile, dump, copy)
        artifacts[recipient] = await encrypt(copy, recipient)
    return artifacts


async def _journal(
    session_factory, *, event_type: str, payload: dict
) -> None:
    """One row per destination outcome.

    The boolean `record_event` returns is deliberately ignored: a ship is not a
    verification transition, and a snapshot that landed and verified must not
    be reported as failed because a journal row did not.
    """
    async with session_factory() as session:
        await record_event(
            session,
            event_type=event_type,
            object_type="system",
            source=BACKUP_SHIP_JOB_KEY,
            payload=payload,
        )
        await session.commit()


async def ship_all(session_factory) -> dict:
    """Dump once, then ship to every enabled destination in sequence.

    A destination's failure is caught, journalled and folded into the summary;
    it never skips the destinations behind it. One unplugged NAS must not mean
    a night with no off-host copy anywhere.
    """
    async with session_factory() as session:
        configured = await load_destinations(session, masked=False)
    enabled = [c for c in configured if c.enabled]

    summary: dict = {
        "dump": None,
        "shipped": 0,
        "verify_failed": [],
        "pruned": {},
    }
    if not enabled:
        # No dump at all: reading the whole database to produce a file nobody
        # asked for is real I/O against the live server.
        logger.info("backup_ship: no enabled destinations, nothing dumped")
        return summary

    dump = await run_dump()
    artifacts = await _artifacts_for(dump, [c.age_recipient for c in enabled])
    keep_plaintext = any(c.age_recipient is None for c in enabled)

    summary["dump"] = dump.name
    try:
        for cfg in enabled:
            artifact = artifacts[cfg.age_recipient]
            started = time.monotonic()
            destination = None
            try:
                destination = build_destination(cfg)
                await destination.ship(artifact)
                expected = await sha256_file(artifact)
                got = await destination.read_back_sha256(artifact.name)
                if got != expected:
                    raise VerifyMismatch(expected=expected, got=got)
            except VerifyMismatch as mismatch:
                summary["verify_failed"].append(cfg.name)
                await _journal(
                    session_factory,
                    event_type="backup_verify_failed",
                    payload={
                        "destination": cfg.name,
                        "file": artifact.name,
                        "expected": mismatch.expected,
                        "got": mismatch.got,
                    },
                )
            except Exception as exc:  # noqa: BLE001 - one destination, not the run
                logger.warning("backup_ship: %s failed: %s", cfg.name, exc)
                summary["verify_failed"].append(cfg.name)
                await _journal(
                    session_factory,
                    event_type="backup_verify_failed",
                    payload={
                        "destination": cfg.name,
                        "file": artifact.name,
                        "error": str(exc),
                    },
                )
            else:
                summary["shipped"] += 1
                await _journal(
                    session_factory,
                    event_type="backup_shipped",
                    payload={
                        "destination": cfg.name,
                        "file": artifact.name,
                        "bytes": artifact.stat().st_size,
                        "sha256": expected,
                        "elapsed_seconds": round(time.monotonic() - started, 3),
                    },
                )

            # Retention runs whatever this snapshot did: the failure is about
            # tonight's upload, not about the copies already on the destination.
            # A destination that could not be built at all has nothing to prune.
            if destination is None:
                continue
            try:
                summary["pruned"][cfg.name] = await destination.prune(
                    cfg.retention_keep
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("backup_ship: %s prune failed: %s", cfg.name, exc)
                summary["pruned"][cfg.name] = {"error": str(exc)}
    finally:
        scratch = dump.parent / _SCRATCH
        if scratch.exists():
            await asyncio.to_thread(shutil.rmtree, scratch, True)
        if not keep_plaintext:
            # Every destination demanded encryption; an unencrypted twin must
            # not outlive the run on local disk.
            dump.unlink(missing_ok=True)

    return summary
