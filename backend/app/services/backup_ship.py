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
import shlex
import shutil
import tempfile
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from app.config import settings
from app.services.attachment_archive import DUMPS, Family
from app.services.backup_config import DestinationConfig, load_destinations
from app.services.events import BACKUP_SHIPPED, BACKUP_VERIFY_FAILED, record_event

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
#: S3 reads in larger chunks than local I/O: each one crosses a thread
#: boundary, so 64 KiB would mean sixteen thousand hops per gigabyte.
_S3_CHUNK = 1 << 20
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


async def run_dump(*, dest_dir: Path | None = None, stamp: str | None = None) -> Path:
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

    `stamp` lets one run give the dump and its attachment tarball the same
    stamp, which is what makes the restore pairing rule's equality case work.
    Absent, it mints its own as before.
    """
    directory = Path(dest_dir) if dest_dir is not None else DUMP_DIR
    _assert_writable(directory)

    out = directory / f"{JOB_PREFIX}{stamp or _stamp()}.sql.gz"
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

    It is derived from ``stream``, which is also what ``backup_pull`` reads --
    so a verify and a restore-time pull read the destination through exactly
    one code path. Two readers would be two chances to disagree about what the
    destination holds.
    """

    name: str
    retention_keep: int

    async def ship(self, local_path: Path, *, timeout: float | None = None) -> None: ...

    async def stream(self, name: str): ...

    async def read_back_sha256(
        self, name: str, *, timeout: float | None = None
    ) -> str: ...

    async def list_snapshots(self, family: Family = DUMPS) -> list[SnapshotInfo]: ...

    async def prune(self, keep: int, family: Family = DUMPS) -> list[str]: ...


async def _hash_stream(destination, name: str) -> str:
    """The one read-back. Chunked, so a multi-gigabyte snapshot is never
    materialised just to be hashed."""
    digest = hashlib.sha256()
    async for chunk in destination.stream(name):
        digest.update(chunk)
    return digest.hexdigest()


def _is_snapshot(name: str) -> bool:
    """This producer's dumps, and only them.

    Kept as a module function because it reads at every call site as "is this
    ours". The classification itself lives on `Family`, where the attachments
    family shares it -- and where the two prefixes, one a strict extension of
    the other, are separated in one place instead of at every listing.
    """
    return DUMPS.matches(name)


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

    async def ship(self, local_path: Path, *, timeout: float | None = None) -> None:
        # `timeout` is accepted and ignored: a local copy has no transfer to bound.
        target = self.directory / local_path.name
        if local_path.resolve() == target.resolve():
            return
        await asyncio.to_thread(shutil.copyfile, local_path, target)

    async def stream(self, name: str):
        path = self.directory / name
        with open(path, "rb") as handle:
            while True:
                chunk = await asyncio.to_thread(handle.read, _CHUNK)
                if not chunk:
                    return
                yield chunk

    async def read_back_sha256(
        self, name: str, *, timeout: float | None = None
    ) -> str:
        # Ignored for the same reason as `ship`: there is no transfer here.
        return await sha256_file(self.directory / name)

    async def list_snapshots(self, family: Family = DUMPS) -> list[SnapshotInfo]:
        out = []
        for path in self.directory.iterdir():
            if not path.is_file() or not family.matches(path.name):
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

    async def prune(self, keep: int, family: Family = DUMPS) -> list[str]:
        entries = [
            (p.name, p.stat().st_mtime)
            for p in self.directory.iterdir()
            if p.is_file() and family.matches(p.name)
        ]
        deleted = _survivors_and_deletions(entries, keep)
        for name in deleted:
            (self.directory / name).unlink(missing_ok=True)
        return deleted


def _stamp_of(name: str) -> datetime:
    """The stamp a dump's name carries. `tests/test_backups_inventory.py`
    imports this, so it stays put rather than moving onto `Family`."""
    return DUMPS.stamp_datetime(name)


def build_destination(cfg: DestinationConfig) -> Destination:
    if cfg.kind == "local":
        return LocalDestination(
            name=cfg.name, directory=DUMP_DIR, retention_keep=cfg.retention_keep
        )
    if cfg.kind == "ssh":
        return SshDestination(cfg)
    if cfg.kind == "s3":
        return S3Destination(cfg)
    if cfg.kind == "worker":
        return WorkerDestination(cfg)
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


async def _journal_shipped(session_factory, payload: dict) -> None:
    """One row per destination that landed and verified.

    Written inline rather than through a helper that forwards `event_type`:
    `tests/test_events.py`'s scan resolves the literal at the `record_event`
    call site, and a forwarded variable is an indirection it cannot follow.

    The boolean `record_event` returns is deliberately ignored. A ship is not a
    verification transition, so a snapshot that landed and verified must not be
    reported as failed because a journal row was not written.
    """
    async with session_factory() as session:
        await record_event(
            session,
            event_type=BACKUP_SHIPPED,
            object_type="system",
            source=BACKUP_SHIP_JOB_KEY,
            payload=payload,
        )
        await session.commit()


async def _journal_verify_failed(session_factory, payload: dict) -> None:
    """One row per destination that did not end up holding what we sent."""
    async with session_factory() as session:
        await record_event(
            session,
            event_type=BACKUP_VERIFY_FAILED,
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
                await _journal_verify_failed(
                    session_factory,
                    {
                        "destination": cfg.name,
                        "file": artifact.name,
                        "expected": mismatch.expected,
                        "got": mismatch.got,
                    },
                )
            except Exception as exc:  # noqa: BLE001 - one destination, not the run
                logger.warning("backup_ship: %s failed: %s", cfg.name, exc)
                summary["verify_failed"].append(cfg.name)
                await _journal_verify_failed(
                    session_factory,
                    {
                        "destination": cfg.name,
                        "file": artifact.name,
                        "error": str(exc),
                    },
                )
            else:
                summary["shipped"] += 1
                await _journal_shipped(
                    session_factory,
                    {
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


# ---------------------------------------------------------------------------
# The ssh destination
# ---------------------------------------------------------------------------

#: An upload of a database dump is allowed to take a long time; a read-back is
#: allowed to take less, because it is a straight read of a file that already
#: landed. Both are bounded so a hung transfer cannot hold the job's slot until
#: `max_run_seconds` kills the whole run.
SHIP_TIMEOUT_SECONDS = 3600
READ_BACK_TIMEOUT_SECONDS = 900

#: The attachment tarball is the whole page-attachment volume, not a
#: compressed schema, so both directions get their own larger bound rather
#: than forcing one constant to serve two artefact sizes. They are passed
#: through the `timeout=` parameter on `ship` and `read_back_sha256`; defining
#: them without passing them would leave a multi-gigabyte transfer cut off at
#: the dump's 3600/900.
ATTACHMENTS_SHIP_TIMEOUT_SECONDS = 7200
ATTACHMENTS_READ_BACK_TIMEOUT_SECONDS = 3600

#: The job's whole-run bound. One destination's worst case is now both
#: artefacts in both directions; a kill mid-verify leaves the attachments
#: state row unwritten and repeats the decision tomorrow, so the budget buys
#: room for the destination in flight rather than for every destination.
BACKUP_SHIP_MAX_RUN_SECONDS = 21600


class SshDestination:
    """scp/ssh with a pinned host key.

    Key material is written into a per-operation scratch directory and removed
    in a ``finally``: ssh will not read an identity file the world can see, and
    a private key that outlives the operation needing it is a credential lying
    on disk for no reason.

    There is no end-to-end test against a real sshd -- this host has no such
    fixture -- so what is proven is the argv, the pinned host key, the ``.part``
    discipline and the prefix-scoped prune. A transfer against a live server is
    an operator bring-up step, not a suite step.
    """

    def __init__(self, cfg: DestinationConfig):
        if cfg.ssh is None:
            raise ValueError(f"{cfg.name}: ssh settings required")
        self.name = cfg.name
        self.retention_keep = cfg.retention_keep
        self.ssh = cfg.ssh

    # -- argv ------------------------------------------------------------

    def _remote_dir(self) -> str:
        remote = self.ssh.remote_dir.strip()
        if not remote or remote == "/":
            raise ValueError(
                f"{self.name}: remote_dir {self.ssh.remote_dir!r} -- a prune "
                f"rooted at / or at nothing is not a retention pass"
            )
        return remote.rstrip("/")

    def _ssh_base_argv(self, scratch: Path) -> list[str]:
        """Write the key material into `scratch` and return the shared options."""
        known_hosts = scratch / "known_hosts"
        known_hosts.write_text(self.ssh.host_key.strip() + "\n")
        identity = scratch / "identity"
        identity.write_text(self.ssh.private_key)
        identity.chmod(0o600)
        return [
            "-i",
            str(identity),
            "-o",
            "BatchMode=yes",
            # Pinned, never trust-on-first-use: `accept-new` would learn the
            # key on exactly the connection an attacker would want to be on.
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            f"UserKnownHostsFile={known_hosts}",
            "-o",
            "IdentitiesOnly=yes",
        ]

    def _target(self) -> str:
        return f"{self.ssh.user}@{self.ssh.host}"

    # -- process ---------------------------------------------------------

    async def _run(self, argv, *, timeout: float, on_chunk=None) -> bytes:
        """Run one command, raising on a non-zero exit with stderr's tail.

        With `on_chunk` the stdout is streamed into it and ``b""`` comes back:
        a read-back of a multi-gigabyte snapshot must never land in memory just
        to be hashed. Without it the output is buffered and returned, which is
        right for a directory listing.
        """
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        async def _pump() -> bytes:
            buffered = bytearray()
            assert proc.stdout is not None
            while True:
                chunk = await proc.stdout.read(_CHUNK)
                if not chunk:
                    break
                if on_chunk is None:
                    buffered.extend(chunk)
                else:
                    on_chunk(chunk)
            return bytes(buffered)

        try:
            out = await asyncio.wait_for(_pump(), timeout=timeout)
            stderr = (await proc.stderr.read()) if proc.stderr else b""
            code = await asyncio.wait_for(proc.wait(), timeout=60)
        except BaseException:
            if proc.returncode is None:
                proc.kill()
                await proc.wait()
            raise
        if code != 0:
            raise RuntimeError(
                f"{argv[0]} exited {code}: "
                f"{stderr.decode('utf-8', 'replace')[-500:]}"
            )
        return out

    @asynccontextmanager
    async def _scratch(self):
        directory = Path(tempfile.mkdtemp(prefix="darkmem-ssh-"))
        try:
            yield directory, self._ssh_base_argv(directory)
        finally:
            await asyncio.to_thread(shutil.rmtree, directory, True)

    # -- the protocol ----------------------------------------------------

    async def ship(self, local_path: Path, *, timeout: float | None = None) -> None:
        remote_dir = self._remote_dir()
        remote = f"{remote_dir}/{local_path.name}"
        async with self._scratch() as (_, base):
            await self._run(
                ["scp", "-P", str(self.ssh.port), *base, str(local_path),
                 f"{self._target()}:{remote}.part"],
                timeout=timeout or SHIP_TIMEOUT_SECONDS,
            )
            # Rename only once the bytes are all there, so a torn upload is
            # never listed as a snapshot a restore could select.
            await self._run(
                ["ssh", "-p", str(self.ssh.port), *base, self._target(), "--",
                 f"mv -- {shlex.quote(remote + '.part')} {shlex.quote(remote)}"],
                timeout=timeout or READ_BACK_TIMEOUT_SECONDS,
            )

    async def stream(self, name: str):
        """Chunks off a remote `cat`, straight from the subprocess.

        Deliberately not routed through `_run`: that helper pushes into a sink
        it is given, and bridging a push into a pull from inside the same event
        loop is how you deadlock a generator. Reading the pipe here is both
        simpler and the only shape that streams.
        """
        remote = f"{self._remote_dir()}/{name}"
        async with self._scratch() as (_, base):
            proc = await asyncio.create_subprocess_exec(
                "ssh", "-p", str(self.ssh.port), *base, self._target(), "--",
                f"cat -- {shlex.quote(remote)}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                assert proc.stdout is not None
                while True:
                    chunk = await proc.stdout.read(_CHUNK)
                    if not chunk:
                        break
                    yield chunk
                stderr = (await proc.stderr.read()) if proc.stderr else b""
                code = await proc.wait()
                if code != 0:
                    raise RuntimeError(
                        f"ssh cat exited {code}: "
                        f"{stderr.decode('utf-8', 'replace')[-300:]}"
                    )
            finally:
                if proc.returncode is None:
                    proc.kill()
                    await proc.wait()

    async def read_back_sha256(
        self, name: str, *, timeout: float | None = None
    ) -> str:
        remote = f"{self._remote_dir()}/{name}"
        digest = hashlib.sha256()
        async with self._scratch() as (_, base):
            buffered = await self._run(
                ["ssh", "-p", str(self.ssh.port), *base, self._target(), "--",
                 f"cat -- {shlex.quote(remote)}"],
                timeout=timeout or READ_BACK_TIMEOUT_SECONDS,
                on_chunk=digest.update,
            )
        if buffered:
            digest.update(buffered)
        return digest.hexdigest()

    async def _remote_names(
        self, base: list[str], family: Family, *, timeout: float | None = None
    ) -> list[str]:
        out = await self._run(
            ["ssh", "-p", str(self.ssh.port), *base, self._target(), "--",
             f"ls -1 -- {shlex.quote(self._remote_dir())}"],
            timeout=timeout or READ_BACK_TIMEOUT_SECONDS,
        )
        return [
            line
            for line in out.decode("utf-8", "replace").splitlines()
            if family.matches(line.strip())
        ]

    async def list_snapshots(self, family: Family = DUMPS) -> list[SnapshotInfo]:
        """Names only. `ls -1` carries no size and no mtime, and parsing
        `ls -l` across remote locales is a worse answer than reporting what
        is actually known -- the stamp in the name is the ordering key."""
        async with self._scratch() as (_, base):
            names = await self._remote_names(base, family)
        return [
            SnapshotInfo(name=n, size=0, modified_at=family.stamp_datetime(n))
            for n in sorted(names)
        ]

    async def prune(self, keep: int, family: Family = DUMPS) -> list[str]:
        remote_dir = self._remote_dir()
        async with self._scratch() as (_, base):
            names = await self._remote_names(base, family)
            # Ordered by the stamp in the name, which sorts lexically because
            # it is zero-padded and big-endian. A remote mtime would need an
            # `ls -l` parse across an unknown locale.
            doomed = sorted(names, reverse=True)[keep:]
            for name in doomed:
                await self._run(
                    ["ssh", "-p", str(self.ssh.port), *base, self._target(), "--",
                     f"rm -f -- {shlex.quote(remote_dir + '/' + name)}"],
                    timeout=READ_BACK_TIMEOUT_SECONDS,
                )
        return doomed


# ---------------------------------------------------------------------------
# The S3 destination
# ---------------------------------------------------------------------------


class S3Destination:
    """AWS, R2, B2 or MinIO -- one client, distinguished by ``endpoint_url``.

    boto3 is synchronous, so every call goes through ``asyncio.to_thread``: an
    upload on the event loop would stall the single worker (invariant 13) for
    the length of the transfer. The client is built per operation rather than
    cached, because a credential rotation in the config row must reach the next
    ship with no restart.
    """

    def __init__(self, cfg: DestinationConfig, *, client_factory=None):
        if cfg.s3 is None:
            raise ValueError(f"{cfg.name}: s3 settings required")
        self.name = cfg.name
        self.retention_keep = cfg.retention_keep
        self.s3 = cfg.s3
        self._factory = client_factory or self._client

    def _client(self):
        import boto3

        return boto3.client(
            "s3",
            endpoint_url=self.s3.endpoint_url,
            region_name=self.s3.region,
            aws_access_key_id=self.s3.access_key_id,
            aws_secret_access_key=self.s3.secret_access_key,
        )

    def _key(self, name: str) -> str:
        return f"{self.s3.prefix}{name}"

    async def ship(self, local_path: Path, *, timeout: float | None = None) -> None:
        # Accepted and ignored: boto3 carries its own client timeouts.
        client = self._factory()
        await asyncio.to_thread(
            client.upload_file,
            str(local_path),
            self.s3.bucket,
            self._key(local_path.name),
        )

    def _open_object(self, client, key: str):
        return client.get_object(Bucket=self.s3.bucket, Key=key)["Body"]

    async def stream(self, name: str):
        """Chunked, never one `.read()`.

        An attachment tarball is the whole page-attachment volume, and this
        process runs under a 1 GB memory limit: materialising the object to
        verify or to pull it would be the largest allocation here by orders of
        magnitude. Each chunk crosses a thread boundary because boto3's body is
        synchronous.
        """
        client = self._factory()
        body = await asyncio.to_thread(self._open_object, client, self._key(name))
        try:
            while True:
                chunk = await asyncio.to_thread(body.read, _S3_CHUNK)
                if not chunk:
                    return
                yield chunk
        finally:
            await asyncio.to_thread(body.close)

    async def read_back_sha256(self, name: str, *, timeout: float | None = None) -> str:
        """Hash the object's own bytes, never its ETag.

        An ETag is a multipart-dependent digest of what the *service* thinks it
        stored; rule 2 asks what we can read back. Derived from `stream`, so a
        verify and a restore-time pull read the destination through one path.

        `timeout` is accepted and ignored, as on `ship`: boto3 carries its own
        client timeouts, and dropping the parameter here would make an S3
        destination raise `TypeError` the moment a caller passes a bound.
        """
        return await _hash_stream(self, name)

    def _list_all(self, client, family: Family) -> list[tuple[str, int]]:
        """Every page. Pruning off a truncated first page would compute the
        newest `keep` from an arbitrary slice and delete everything real."""
        out: list[tuple[str, int]] = []
        token = None
        while True:
            kwargs = {"Bucket": self.s3.bucket, "Prefix": self.s3.prefix}
            if token:
                kwargs["ContinuationToken"] = token
            page = client.list_objects_v2(**kwargs)
            for obj in page.get("Contents", []):
                name = obj["Key"][len(self.s3.prefix):]
                if family.matches(name):
                    out.append((name, obj.get("Size", 0)))
            if not page.get("IsTruncated"):
                return out
            token = page["NextContinuationToken"]

    async def list_snapshots(self, family: Family = DUMPS) -> list[SnapshotInfo]:
        client = self._factory()
        entries = await asyncio.to_thread(self._list_all, client, family)
        return [
            SnapshotInfo(name=n, size=size, modified_at=family.stamp_datetime(n))
            for n, size in sorted(entries)
        ]

    async def prune(self, keep: int, family: Family = DUMPS) -> list[str]:
        client = self._factory()
        entries = await asyncio.to_thread(self._list_all, client, family)
        # The stamp sorts lexically, so key order is snapshot order -- no
        # LastModified parse, and no dependence on what the service reports.
        doomed = sorted((n for n, _ in entries), reverse=True)[keep:]
        for name in doomed:
            await asyncio.to_thread(
                client.delete_object, Bucket=self.s3.bucket, Key=self._key(name)
            )
        return doomed


# ---------------------------------------------------------------------------
# The worker destination
# ---------------------------------------------------------------------------


class WorkerDestination:
    """A darkmem backup worker's snapshot receiver (increment 7, spec §9.5).

    Speaks the receiver's four verbs over https. Both directions stream: a
    snapshot is a database dump, and buffering one in memory to send or to
    hash would be the largest allocation this process ever makes.

    The bearer token is authorisation, not confidentiality -- the receiver
    stores ciphertext because increment 6 encrypts before egress, which is why
    a `worker` destination without an age recipient is refused at save.
    """

    def __init__(self, cfg: DestinationConfig, *, client_factory=None):
        if cfg.worker is None:
            raise ValueError(f"{cfg.name}: worker settings required")
        self.name = cfg.name
        self.retention_keep = cfg.retention_keep
        self.worker = cfg.worker
        self._factory = client_factory or self._client

    def _client(self):
        import httpx

        return httpx.AsyncClient(
            base_url=self.worker.url.rstrip("/"),
            headers={"Authorization": f"Bearer {self.worker.token}"},
            timeout=SHIP_TIMEOUT_SECONDS,
        )

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.worker.token}"}

    @staticmethod
    def _raise_for(response, what: str) -> None:
        if response.status_code >= 400:
            raise RuntimeError(
                f"receiver {what} returned {response.status_code}: "
                f"{response.text[:300]}"
            )

    async def ship(self, local_path: Path, *, timeout: float | None = None) -> None:
        # Accepted and ignored: httpx bounds each read, write and connect, never
        # the transfer as a whole, so a larger bound would buy nothing here.
        async def _body():
            # Async, and each read offloaded: httpx refuses a sync iterator on
            # an AsyncClient, and a multi-hundred-megabyte file read in the
            # loop would stall the single worker for the whole upload.
            with open(local_path, "rb") as handle:
                while True:
                    chunk = await asyncio.to_thread(handle.read, _CHUNK)
                    if not chunk:
                        return
                    yield chunk

        async with self._factory() as client:
            response = await client.put(
                f"/snapshots/{local_path.name}",
                content=_body(),
                headers=self._headers(),
            )
        self._raise_for(response, "upload")

    async def stream(self, name: str):
        async with self._factory() as client:
            async with client.stream(
                "GET", f"/snapshots/{name}", headers=self._headers()
            ) as response:
                self._raise_for(response, "read-back")
                async for chunk in response.aiter_bytes():
                    yield chunk

    async def read_back_sha256(
        self, name: str, *, timeout: float | None = None
    ) -> str:
        # Ignored for the same reason as `ship`: an httpx bound is per
        # operation, not per transfer.
        return await _hash_stream(self, name)

    async def _listing(self, family: Family) -> list[dict]:
        async with self._factory() as client:
            response = await client.get("/snapshots", headers=self._headers())
        self._raise_for(response, "listing")
        # The receiver already excludes `.part` files and foreign prefixes, so
        # this filter is the belt: two independent refusals is what keeps an
        # in-flight upload out of a prune's deletion set.
        return [
            item
            for item in response.json().get("snapshots", [])
            if family.matches(item["name"])
        ]

    async def list_snapshots(self, family: Family = DUMPS) -> list[SnapshotInfo]:
        return [
            SnapshotInfo(
                name=item["name"],
                size=item.get("size", 0),
                modified_at=family.stamp_datetime(item["name"]),
            )
            for item in sorted(await self._listing(family), key=lambda i: i["name"])
        ]

    async def prune(self, keep: int, family: Family = DUMPS) -> list[str]:
        names = [item["name"] for item in await self._listing(family)]
        doomed = sorted(names, reverse=True)[keep:]
        async with self._factory() as client:
            for name in doomed:
                response = await client.delete(
                    f"/snapshots/{name}", headers=self._headers()
                )
                self._raise_for(response, "delete")
        return doomed
