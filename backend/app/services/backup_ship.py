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
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings

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
