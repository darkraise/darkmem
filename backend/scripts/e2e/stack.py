"""Boot a disposable, migrated, seeded darkmem stack for the API e2e suite.

``boot(port, password)`` does the whole sequence a fresh machine needs before
any e2e assertion can run:

1. ``e2e_db.reset_e2e_db()`` — drop/recreate + migrate ``TEST_DATABASE_URL``.
2. Spawn ``uvicorn app.main:app`` as a subprocess, ``DATABASE_URL`` pointed at
   the just-reset database, in its own session (``start_new_session=True``,
   mirroring ``scripts/gate.sh``'s own ``setsid`` discipline) so the whole
   process tree can be torn down as a group.
3. Poll ``GET /health`` until it answers (200 ``ok``/``degraded`` — 503 means
   pgvector is unreachable, keep polling; a connection error means the
   server hasn't bound the port yet) or a bounded timeout expires.
4. Seed the admin account through the real front door,
   ``POST /api/v1/setup`` with ``{"password": ...}`` and nothing else — a
   fresh database has no ``admin_password_hash`` row, so
   ``require_uninitialized`` passes and this succeeds with no LLM
   configuration at all (doc: T1.64 plan §2.1).

Run directly for the manual, disposable-Playwright recipe (T1.64 plan §2.2):

    python -m backend.scripts.e2e.stack --keep-running --port 8000 --password <pw>

which does steps 1-4 and then blocks, writing ``.env-e2e`` beside this file
so a human running Playwright against it can ``source`` the
``E2E_DISPOSABLE_STACK=1`` export without hand-typing it.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent
BACKEND_DIR = SCRIPTS_DIR.parent
# Standalone execution puts only this file's own directory on sys.path --
# backend/scripts/ has no __init__.py, so both `e2e` (this package) and
# `app` need to resolve explicitly, mirroring benchlib/run_smoke.py's setup.
for _path in (str(BACKEND_DIR), str(SCRIPTS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import httpx  # noqa: E402

# Overrides DATABASE_URL as a side effect of import — must happen before any
# app.* import anywhere in this process.
from e2e import e2e_db  # noqa: E402,F401  (ensures DATABASE_URL override first)

ENV_FILE = HERE / ".env-e2e"

HEALTH_POLL_TIMEOUT_S = 60
HEALTH_POLL_INTERVAL_S = 0.5
TEARDOWN_GRACE_S = 3


@dataclass
class StackHandle:
    process: subprocess.Popen
    base_url: str
    password: str

    def teardown(self) -> None:
        """Kill the whole process group: TERM, a grace period, then KILL.

        Mirrors ``scripts/gate.sh``'s own ``cleanup()`` trap — only ever
        signals the group this handle started.
        """
        if self.process.poll() is not None:
            return
        pgid = os.getpgid(self.process.pid)
        try:
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            return
        deadline = time.monotonic() + TEARDOWN_GRACE_S
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                return
            time.sleep(0.1)
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        self.process.wait(timeout=5)

    def __enter__(self) -> "StackHandle":
        return self

    def __exit__(self, *exc_info) -> None:
        self.teardown()


def _wait_for_health(base_url: str, timeout_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            resp = httpx.get(f"{base_url}/health", timeout=3.0)
            if resp.status_code in (200, 503):
                if resp.status_code == 200:
                    return
                last_error = RuntimeError(f"health 503: {resp.text}")
            else:
                last_error = RuntimeError(f"health {resp.status_code}: {resp.text}")
        except (httpx.ConnectError, httpx.ReadError, httpx.ConnectTimeout) as e:
            last_error = e
        time.sleep(HEALTH_POLL_INTERVAL_S)
    raise TimeoutError(
        f"stack did not answer /health as ok within {timeout_s}s: {last_error}"
    )


def _seed_admin(base_url: str, password: str) -> None:
    resp = httpx.post(
        f"{base_url}/api/v1/setup", json={"password": password}, timeout=10.0,
    )
    if resp.status_code != 200:
        raise RuntimeError(
            f"POST /api/v1/setup failed: {resp.status_code} {resp.text}"
        )


def boot(
    *, port: int, password: str, health_timeout_s: float = HEALTH_POLL_TIMEOUT_S,
) -> StackHandle:
    asyncio.run(e2e_db.reset_e2e_db())

    env = {**os.environ, "DATABASE_URL": e2e_db.TEST_DATABASE_URL}
    process = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "app.main:app",
            "--host", "0.0.0.0", "--port", str(port),
            "--no-proxy-headers",
        ],
        cwd=str(BACKEND_DIR),
        env=env,
        start_new_session=True,
    )

    base_url = f"http://127.0.0.1:{port}"
    try:
        _wait_for_health(base_url, health_timeout_s)
        _seed_admin(base_url, password)
    except Exception:
        handle = StackHandle(process=process, base_url=base_url, password=password)
        handle.teardown()
        raise

    return StackHandle(process=process, base_url=base_url, password=password)


def _write_env_file(base_url: str, password: str) -> None:
    ENV_FILE.write_text(
        "export E2E_DISPOSABLE_STACK=1\n"
        f"export E2E_BASE_URL={base_url}\n"
        f"export E2E_ADMIN_PASSWORD={password}\n"
    )


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--password", required=True)
    parser.add_argument(
        "--keep-running", action="store_true",
        help="boot and block instead of tearing down immediately",
    )
    args = parser.parse_args()

    handle = boot(port=args.port, password=args.password)
    print(f"stack up: {handle.base_url} (pid {handle.process.pid})")

    if not args.keep_running:
        handle.teardown()
        return

    _write_env_file(handle.base_url, args.password)
    print(f"wrote {ENV_FILE} — source it before running Playwright")
    print("Ctrl-C to tear down")

    def _on_signal(signum, frame):
        handle.teardown()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    try:
        handle.process.wait()
    finally:
        handle.teardown()
        ENV_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    _main()
