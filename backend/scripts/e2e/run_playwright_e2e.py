"""Boot a disposable stack on its own port, run `npm run test:e2e` against
it, tear it down. The `scripts/gate.sh --full` "playwright e2e" step's own
script (T1.64 plan §6.2) — one command so `run_gate`'s process-group
teardown wraps the whole sequence, not just the npm subprocess.

`vite.config.ts`'s dev proxy reads `E2E_API_TARGET` and only falls back to
`http://localhost:8000`, so the stack does **not** have to bind 8000 — this
script exports the target it actually booted. (This docstring claimed the
opposite until 2026-08-12, which is how the colliding default outlived the
override that was added to escape it.) `E2E_DISPOSABLE_STACK=1` is
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
# pointed at through `E2E_API_TARGET`.
#
# **Dedicated, not 8000.** The default was 8000 until 2026-08-12, which is
# the port a running darkmem holds — so on any machine actually running the
# product (the homelab cutover being the whole point) uvicorn failed to
# bind, `_wait_for_health` got its 200 from the *live* instance, and the run
# POSTed `/api/v1/setup` at production. It surfaced as a `GATE RED` with
# "Setup already completed", which is the benign outcome: against an
# instance that had *not* completed setup, this leg would have seeded an
# admin password into a live install and then driven a browser suite
# through it.
#
# The env override was added earlier as a safety valve for exactly this and
# left the default colliding, which made the valve the only thing standing
# between the gate and a live instance. `run_e2e.py` had it right all along
# with a hardcoded 8321; this is its neighbour.
PLAYWRIGHT_PORT = int(os.environ.get("E2E_PLAYWRIGHT_PORT", "8322"))


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
