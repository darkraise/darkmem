"""Boot a disposable stack on :8000, run `npm run test:e2e` against it, tear
it down. The `scripts/gate.sh --full` "playwright e2e" step's own script
(T1.64 plan §6.2) — one command so `run_gate`'s process-group teardown wraps
the whole sequence, not just the npm subprocess.

`vite.config.ts`'s dev proxy hardcodes `http://localhost:8000` (measured,
unchanged), so the disposable stack must bind that exact port — this script
does not take a `--port` option for that reason. `E2E_DISPOSABLE_STACK=1` is
exported into the `npm test:e2e` subprocess's environment so `auth.spec.ts` /
`code-real-mode.spec.ts` take the disposable-stack branch of their
`beforeAll` guard and never call `seedAdminPassword()` against `darkmem`.

Run from `backend/`: `python scripts/e2e/run_playwright_e2e.py`
"""
from __future__ import annotations

import os
import secrets
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent
BACKEND_DIR = SCRIPTS_DIR.parent
REPO_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = REPO_ROOT / "frontend"

for _path in (str(BACKEND_DIR), str(SCRIPTS_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from e2e import stack  # noqa: E402

PLAYWRIGHT_PORT = 8000


def main() -> int:
    password = secrets.token_urlsafe(16)
    handle = stack.boot(port=PLAYWRIGHT_PORT, password=password)
    try:
        env = {
            **os.environ,
            "E2E_DISPOSABLE_STACK": "1",
            "E2E_BASE_URL": handle.base_url,
            "E2E_ADMIN_PASSWORD": password,
            "VITE_DEMO": "0",
        }
        result = subprocess.run(
            ["npm", "run", "test:e2e"], cwd=str(FRONTEND_DIR), env=env,
        )
        return result.returncode
    finally:
        handle.teardown()


if __name__ == "__main__":
    sys.exit(main())
