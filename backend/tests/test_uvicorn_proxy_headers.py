"""Does --no-proxy-headers actually suppress uvicorn's peer rewrite?

This is the only automated check in the deployment surface that can fail
because the flag stopped *working* rather than stopped being *spelled*.
uvicorn's ProxyHeadersMiddleware is installed by default and trusts
127.0.0.1, so a loopback client can overwrite scope["client"] with an
X-Forwarded-For value it chose -- which, under the transport-peer posture,
is an attacker choosing its own login rate-limit bucket one layer below the
code that correctly refuses to read the header.

No in-process test can observe that layer: httpx's ASGI transport speaks
ASGI to the FastAPI app directly and never runs uvicorn's middleware. So
this boots real uvicorn as a subprocess, twice, against a probe app that
echoes the peer -- once with the argv the shipped entrypoint carries, and
once with --no-proxy-headers stripped from that same argv. The second boot
is the point: without it the test could not fail.

The argv is parsed out of entrypoint.sh rather than restated here, so the
test exercises the artifact instead of a constant it owns.
"""
from __future__ import annotations

import os
import shlex
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parents[1]
ENTRYPOINT = REPO_ROOT / "entrypoint.sh"

PROBE_TARGET = f"{Path(__file__).stem}:probe_app"
FORWARDED = "203.0.113.9"
LOOPBACK = "127.0.0.1"
BOOT_TIMEOUT_SECONDS = 30.0


async def probe_app(scope, receive, send):
    """Echo the peer address ASGI reports. Imports nothing from the app."""
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
        return
    client = scope.get("client") or ("unknown", 0)
    body = str(client[0]).encode()
    await send({
        "type": "http.response.start",
        "status": 200,
        "headers": [
            (b"content-type", b"text/plain"),
            (b"content-length", str(len(body)).encode()),
        ],
    })
    await send({"type": "http.response.body", "body": body})


def _shipped_uvicorn_argv() -> list[str]:
    lines = [ln for ln in ENTRYPOINT.read_text().splitlines() if "uvicorn" in ln]
    assert len(lines) == 1, f"expected one uvicorn line, found {len(lines)}"
    argv = shlex.split(lines[0])
    if argv and argv[0] == "exec":
        argv = argv[1:]
    assert argv[0] == "uvicorn", argv
    return argv


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind((LOOPBACK, 0))
        return probe.getsockname()[1]


def _probe_argv(shipped: list[str], port: int) -> list[str]:
    argv = [sys.executable, "-m", "uvicorn"] + shipped[1:]
    argv = [PROBE_TARGET if part == "app.main:app" else part for part in argv]
    assert PROBE_TARGET in argv, argv
    for flag, value in (("--host", LOOPBACK), ("--port", str(port))):
        index = argv.index(flag)
        argv[index + 1] = value
    return argv + ["--app-dir", str(TESTS_DIR)]


class _Server:
    def __init__(self, argv: list[str], port: int):
        self.argv = argv
        self.port = port
        self.process: subprocess.Popen | None = None

    def __enter__(self) -> "_Server":
        self.process = subprocess.Popen(
            self.argv,
            cwd=str(TESTS_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        deadline = time.monotonic() + BOOT_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(f"uvicorn exited early: {self.argv}")
            try:
                with socket.create_connection((LOOPBACK, self.port), timeout=0.5):
                    return self
            except OSError:
                time.sleep(0.05)
        raise RuntimeError(f"uvicorn never came up on {self.port}: {self.argv}")

    def __exit__(self, *_exc) -> None:
        if self.process is None:
            return
        os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            self.process.wait(timeout=10)


async def _echoed_peer(port: int) -> str:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"http://{LOOPBACK}:{port}/", headers={"X-Forwarded-For": FORWARDED},
        )
    assert response.status_code == 200
    return response.text


@pytest.fixture
def shipped_argv() -> list[str]:
    argv = _shipped_uvicorn_argv()
    assert "--no-proxy-headers" in argv, (
        "the shipped entrypoint no longer carries the flag; the differential "
        "below would compare two identical boots"
    )
    return argv


async def test_shipped_argv_ignores_a_forged_forwarded_for(shipped_argv):
    port = _free_port()
    server = _Server(_probe_argv(shipped_argv, port), port)
    with server:
        assert await _echoed_peer(port) == LOOPBACK
    assert server.process.poll() is not None


async def test_stripping_the_flag_lets_the_client_choose_its_own_peer(shipped_argv):
    """The half that makes this a differential rather than a green tick: with
    the flag removed from the same argv, the echoed peer must become the
    client-supplied header value. A run where both boots echo 127.0.0.1 means
    the harness is not exercising what it claims."""
    stripped = [part for part in shipped_argv if part != "--no-proxy-headers"]
    assert len(stripped) == len(shipped_argv) - 1

    port = _free_port()
    server = _Server(_probe_argv(stripped, port), port)
    with server:
        assert await _echoed_peer(port) == FORWARDED
    assert server.process.poll() is not None
