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

# The port the disposable stack binds, and the one the vite proxy is
# pointed at through `E2E_API_TARGET`. Overridable because the default
# collides with a darkmem instance running on the same machine — including
# the maintainer's own, which is where this gate runs. On a collision the
# health check finds the *other* instance and the run seeds an admin
# against it, so the override is a safety valve rather than a convenience.
PLAYWRIGHT_PORT = int(os.environ.get("E2E_PLAYWRIGHT_PORT", "8000"))


def main() -> int:
    password = secrets.token_urlsafe(16)
    # T2.90: seeds one real Layer-2 fact (via the real fact_lift, over
    # hand-seeded Layer-1 rows — see e2e/seed_facts.py) so
    # knowledge-real-mode.spec.ts has something to find on the Facts tab.
    handle = stack.boot(port=PLAYWRIGHT_PORT, password=password, seed_facts=True)
    try:
        env = {
            **os.environ,
            "E2E_DISPOSABLE_STACK": "1",
            "E2E_BASE_URL": handle.base_url,
            # The vite dev server proxies /api, /health and /ws here; left
            # unset it would proxy to :8000 while the stack listens
            # elsewhere, and every real-mode spec would talk to whatever
            # else holds that port.
            "E2E_API_TARGET": handle.base_url,
            "E2E_ADMIN_PASSWORD": password,
            "VITE_DEMO": "0",
        }
        if handle.seeded_fact is not None:
            env["E2E_SEEDED_FACT_SUBJECT"] = handle.seeded_fact.subject_name
            env["E2E_SEEDED_FACT_TEXT"] = handle.seeded_fact.fact_text
        result = subprocess.run(
            ["npm", "run", "test:e2e"], cwd=str(FRONTEND_DIR), env=env,
        )
        return result.returncode
    finally:
        handle.teardown()


if __name__ == "__main__":
    sys.exit(main())
