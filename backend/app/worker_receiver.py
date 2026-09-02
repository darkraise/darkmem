"""Snapshot receiver -- the worker's ONE write door, deliberately outside the
darkmem app (spec §9.5, review B1: an https write door inside a read-only
instance is a contradiction).

Writes files to ``RECEIVER_DIR`` and does nothing else: no database, no
session, no import from ``app.main`` or ``app.database``. That separation is
what makes "the worker is read-only" true rather than approximately true, so
``tests/test_worker_receiver.py`` walks this module's import closure and fails
the build if any of those becomes reachable.

Content arrives age-encrypted -- increment 6 encrypts before egress -- so the
bearer token is **authorisation, not confidentiality**. Front TLS if the path
crosses untrusted networks; the runbook says when.

The dump directory is a host bind mount and Docker does not chown one, so the
process refuses to start when it cannot write there. A receiver that boots
green and 500s every upload is the same silent shape increment 6's review B-1
found on the ship side.
"""
from __future__ import annotations

import contextlib
import hmac
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route

logger = logging.getLogger(__name__)

#: Exactly increment 6's own artefact names, anchored. A path separator, a
#: `..`, and a foreign prefix all fail here rather than at the filesystem.
SNAPSHOT_NAME = re.compile(r"^darkmem-app-[A-Za-z0-9._-]+\.sql\.gz(\.age)?$")

#: Below this a token is not a secret. Refused at start rather than accepted
#: and quietly weak.
MIN_TOKEN_CHARS = 32

_CHUNK = 1 << 20


class ReceiverMisconfigured(RuntimeError):
    """The process cannot serve its one job and says so instead of starting."""


def _receiver_dir() -> Path:
    return Path(os.environ.get("RECEIVER_DIR", "/dumps"))


def _max_bytes() -> int:
    return int(os.environ.get("RECEIVER_MAX_BYTES", str(10 * 1024**3)))


def _token() -> str:
    token = os.environ.get("RECEIVER_TOKEN", "")
    if len(token) < MIN_TOKEN_CHARS:
        raise ReceiverMisconfigured(
            f"RECEIVER_TOKEN must be at least {MIN_TOKEN_CHARS} characters; "
            f"this is the only thing standing between the internet and this "
            f"directory"
        )
    return token


def _assert_writable(directory: Path) -> None:
    if not directory.is_dir() or not os.access(directory, os.W_OK | os.X_OK):
        raise ReceiverMisconfigured(
            f"RECEIVER_DIR {directory} is not writable by uid {os.getuid()}. A "
            f"host bind mount arrives owned by whoever created it and Docker "
            f"does not chown one: create it owned by the image's uid before "
            f"starting the receiver."
        )


def _authorised(request) -> bool:
    header = request.headers.get("authorization", "")
    scheme, _, presented = header.partition(" ")
    if scheme.lower() != "bearer" or not presented:
        return False
    return hmac.compare_digest(presented, _token())


def _unauthorised() -> JSONResponse:
    return JSONResponse({"error": "unauthorized"}, status_code=401)


def _resolve(name: str) -> Path | None:
    """The snapshot path, or None when the name is not one of ours.

    Validated by pattern rather than by resolving and comparing prefixes: a
    name that cannot contain a separator cannot traverse, and refusing a
    foreign prefix here is also what keeps the receiver from becoming a
    general-purpose file drop.
    """
    if not SNAPSHOT_NAME.match(name):
        return None
    return _receiver_dir() / name


async def put_snapshot(request):
    if not _authorised(request):
        return _unauthorised()
    name = request.path_params["name"]
    target = _resolve(name)
    if target is None:
        return JSONResponse({"error": "invalid snapshot name"}, status_code=422)

    part = target.with_name(target.name + ".part")
    limit = _max_bytes()
    written = 0
    try:
        with open(part, "wb") as sink:
            async for chunk in request.stream():
                written += len(chunk)
                if written > limit:
                    raise _TooLarge()
                sink.write(chunk)
            sink.flush()
            os.fsync(sink.fileno())
    except _TooLarge:
        part.unlink(missing_ok=True)
        return JSONResponse({"error": "snapshot too large"}, status_code=413)
    except BaseException:
        # A client that disconnects mid-body leaves a `.part` and nothing
        # else: a torn upload must never be listable as a snapshot, because a
        # restore would happily select it as the newest good one.
        part.unlink(missing_ok=True)
        raise

    os.replace(part, target)
    return JSONResponse({"name": name, "bytes": written}, status_code=201)


class _TooLarge(Exception):
    pass


async def list_snapshots(request):
    if not _authorised(request):
        return _unauthorised()
    directory = _receiver_dir()
    items = []
    for path in sorted(directory.iterdir()):
        if not path.is_file() or not SNAPSHOT_NAME.match(path.name):
            continue
        stat = path.stat()
        items.append(
            {
                "name": path.name,
                "size": stat.st_size,
                "modified_at": datetime.fromtimestamp(
                    stat.st_mtime, timezone.utc
                ).isoformat(),
            }
        )
    return JSONResponse({"snapshots": items})


async def get_snapshot(request):
    if not _authorised(request):
        return _unauthorised()
    target = _resolve(request.path_params["name"])
    if target is None:
        return JSONResponse({"error": "invalid snapshot name"}, status_code=422)
    if not target.is_file():
        return JSONResponse({"error": "not found"}, status_code=404)

    def _body():
        with open(target, "rb") as handle:
            while True:
                chunk = handle.read(_CHUNK)
                if not chunk:
                    return
                yield chunk

    return StreamingResponse(_body(), media_type="application/octet-stream")


async def delete_snapshot(request):
    if not _authorised(request):
        return _unauthorised()
    target = _resolve(request.path_params["name"])
    if target is None:
        return JSONResponse({"error": "invalid snapshot name"}, status_code=422)
    if not target.is_file():
        return JSONResponse({"error": "not found"}, status_code=404)
    target.unlink()
    # A bare 204, not a JSON `null`: a No Content response carrying a body is
    # what makes some clients treat a successful delete as a parse failure.
    return Response(status_code=204)


def _startup() -> None:
    """Refuse to serve rather than accept an upload we cannot store.

    Both checks fail the process, not the request. A weak token and an
    unwritable directory each turn a green boot into a receiver that answers
    every real upload with a 500, which on the worker host means no snapshot
    arrives and nothing says so.
    """
    _token()
    _assert_writable(_receiver_dir())
    logger.info(
        "snapshot receiver serving %s; this process holds no database "
        "connection and writes files, not rows",
        _receiver_dir(),
    )


@contextlib.asynccontextmanager
async def _lifespan(_app):
    _startup()
    yield


app = Starlette(
    routes=[
        Route("/snapshots", list_snapshots, methods=["GET"]),
        Route("/snapshots/{name}", put_snapshot, methods=["PUT"]),
        Route("/snapshots/{name}", get_snapshot, methods=["GET"]),
        Route("/snapshots/{name}", delete_snapshot, methods=["DELETE"]),
    ],
    lifespan=_lifespan,
)
