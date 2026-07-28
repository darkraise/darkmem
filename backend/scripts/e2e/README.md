# API e2e suite (T1.64)

One documented entry point:

```
cd backend && python scripts/e2e/run_e2e.py
```

Nothing else needs to be true first — no fresh deployment, no pre-set password,
no already-running server. This is the normal starting condition, not a
failure mode: the script resets and migrates `TEST_DATABASE_URL` (default
`darkmem_test`, overridable — this lane runs against `darkmem_test_1`),
boots `app.main:app` as its own subprocess on a scratch port, seeds the
admin account through the real `POST /api/v1/setup` front door (password
only, no LLM config), runs `pytest scripts/e2e/tests -q` against it with
`E2E_BASE_URL` / `E2E_ADMIN_PASSWORD` set, and tears the stack down in a
`finally`.

## What's in `scripts/e2e/`

- `e2e_db.py` — drop/recreate + migrate `TEST_DATABASE_URL`. Mirrors
  `scripts/benchlib/bench_db.py`'s reset discipline against a third,
  separate database.
- `stack.py` — `boot(port, password) -> StackHandle`: spawns uvicorn, polls
  `/health`, seeds the admin account, and returns a handle whose
  `teardown()` kills the whole process group (TERM, a grace period, then
  KILL) — mirrors `scripts/gate.sh`'s own `cleanup()` trap.
- `run_e2e.py` — the one entry point. Exit code 2 (BLOCKED, matching
  `scripts/gate.sh`'s own "missing toolchain, not a red gate" precedent) if
  every collected test skipped this run — a suite that skips everything has
  proven nothing and must not report the same exit code as a suite that
  proved something. Any real pass or failure propagates pytest's own code.
- `tests/test_f1_capture.py` — F1 Capture (docs/planning/e2e-test-plan.md):
  REST and MCP both land a capture in the buffer, flush it, and — when an
  embedder is reachable — appear in search with `origin_key` intact. Three
  of the four tests are unconditional (accept and flush need no embedder);
  only the search leg may skip, and only with the real `pipeline_failures`
  error recorded for that run.

## Exercising the disposable stack manually (Playwright)

`auth.spec.ts`, `code-real-mode.spec.ts` and `code-wiki-empty.spec.ts` need a
live, authenticated backend. The shared dev stack (`darkmem`, T1.58 Ruling 4)
is one way to get one; `stack.py --keep-running` is the other, for a machine
that has never run `docker compose up` against `darkmem`:

```
# terminal 1 — disposable, migrated, seeded backend on :8000
cd backend && python -m scripts.e2e.stack --keep-running --port 8000 --password <pw>

# terminal 2 — .env-e2e (written by stack.py) exports E2E_DISPOSABLE_STACK=1
# and E2E_BASE_URL/E2E_ADMIN_PASSWORD, so auth.spec.ts / code-real-mode.spec.ts /
# code-wiki-empty.spec.ts skip seedAdminPassword() (which targets the shared
# dev stack's darkmem database, never this one) and rely on the password this
# stack was already seeded with at boot
cd frontend
source ../backend/scripts/e2e/.env-e2e
VITE_DEMO=0 npx playwright test tests/auth.spec.ts tests/code-real-mode.spec.ts tests/code-wiki-empty.spec.ts
```

`vite.config.ts`'s dev proxy already hardcodes `http://localhost:8000`, so
no frontend config changes are needed — the disposable stack binds the same
port the proxy already expects. `playwright.config.ts` also drops to a single
worker and one retry whenever `E2E_DISPOSABLE_STACK` is set: these specs
share the one live backend the stack boots, and running them in parallel
races its session/rate-limiter state — the same race can happen by hand,
not only under `gate.sh`.

`scripts/gate.sh --full`'s own "playwright e2e" step boots and tears down a
disposable stack the same way on every run, so this recipe is exercised
automatically at the gate, not only when a human follows it by hand.

## Honesty specs wired into this suite

See `docs/planning/e2e-test-plan.md`'s "The honesty suite" table for the
full list and owning tasks. Of the five E1-satisfiable specs:

- Three live in `frontend/tests/honesty/` and run through
  `npm run test:e2e` (Playwright, demo-fixture project):
  `labels-always-render`, `exclusions-on-empty`, `no-silent-drop`.
- Two live in `backend/tests/honesty/` and run through the ordinary
  backend floor (`pytest -q`, already collected — no wiring needed):
  `demote-before-delete`, `superseded-pointer`.

## `docs/e2e/scripts/` — retired, not ported

That directory is a manual, one-shot QA runbook against a live,
already-initialized deployment (its own stated precondition: "no admin
password set, empty database"), hardcodes a path that does not exist on
this machine, and its flow coverage is already spoken for piecemeal by the
owning tasks in `docs/planning/e2e-test-plan.md`'s coverage table. It is
retired in favor of this suite for automated runs; the scripts themselves
are not deleted (see `docs/e2e/README.md`'s header for the full
disposition).
