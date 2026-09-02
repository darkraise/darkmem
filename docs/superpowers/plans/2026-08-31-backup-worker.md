# Backup Worker Implementation Plan (Increment 7)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

> **Implementer assignments:** each task names its implementer agent in an
> `**Implementer:**` line. When executing with
> superpowers:subagent-driven-development, REQUIRED SUB-SKILL:
> dcc-superpower-companions:dispatching-tiered-implementers. Under
> superpowers:executing-plans these lines are inert; ignore them.

**Status: LANDED 2026-09-02.** All thirteen tasks are done, `./scripts/gate.sh` is
green (6735 backend, 1356 frontend, 1055 benchlib), and this machine is redeployed
and verified: `/backups/inventory` and `read_only_token_rotation_disabled` are on the
running image's `/openapi.json`, `app.worker_receiver` imports and serves 4 routes
inside it, and `settings.read_only` reads **False** on production, so nothing about
the owner's live instance changed. The ship path was re-drilled end to end on the
deployed build after increment 7's `stream()` refactor: a 252 MB dump landed,
verified by read-back hash, and the new `stream()` returned the same 252,138,634
bytes the hash was taken over.

**The worker machine itself is not provisioned** -- it is a second box, and
`docs/runbook-backup-worker.md` is its procedure. Task 13 Step 5's end-to-end check
(configure a `worker` destination, ship, run one cycle by hand, confirm the posture
and a 403 capture) is therefore **outstanding and owner-owned**; nothing in this
repo's gate runs there.

**One correction to the plan, found by the work.** Review M-6's `FOR UPDATE`
inventory was itself wrong in both directions: `services/wait_process.py` and
`services/memory_buffer.py` only *discuss* the lock in a docstring (the real one is
`buffer_flush.flush_claimed`), and increment 8's `services/block_verbs.py` and
`services/document_door.py` were missing, having landed after the amendment was
written. Three successive prose inventories of one grep's output disagreed with the
grep, which is the argument for the scan: `tests/test_read_only_role.py` asserts the
set as an equality read off the failure, never off a document.

**Goal:** A second machine runs the same darkmem image against nightly-restored snapshots and serves them **read-only** — enforced by a `SELECT`-only Postgres role beneath every code path, not by any door — with a separate receiver process accepting shipped snapshots, a restore loop that runs outside the app and swaps databases with the app stopped, and (§9.6) `restore.sh --from <destination>` plus a snapshot-inventory UI with the exact command and **no in-app restore button**.

**Depends on increment 6** (`docs/superpowers/plans/2026-08-31-backup-offhost.md`): the destination config row (`backup_config.py`), the `Destination` protocol and artifacts (`backup_ship.py`, `darkmem-app-*.sql.gz.age`), and the `/dumps` mount.

**Spec:** `docs/superpowers/specs/2026-08-31-project-artifact-store-design.md` §9.5 (as redesigned after B1) and §9.6.
**Review:** B1 is upheld in full and is the design. Where spec and review disagree, the review wins.

## The B1 inventory — every write on a read path, and its handling

B1's finding: a door-layer `READ_ONLY` posture cannot hold, because the biggest writers never pass a door. This section enumerates them **against the working tree** (all citations verified 2026-08-31) and states each one's handling. The enforcement layers are, in order: (1) the `darkmem_viewer` Postgres role — `SELECT` and nothing else, the floor no application bug can dig under; (2) process separation — migrations, stamping and restores run privileged while the app is stopped; (3) the demoted `DARKMEM_READ_ONLY` flag — ergonomics that make known writers no-op quietly and known write doors refuse clearly, **not** the guarantee.

**A. Boot writes that happen before any request (handled by process separation + flag):**

| # | Writer | Cite | Under the role | Handling |
|---|---|---|---|---|
| A1 | `alembic upgrade head` + `schema_guard` stamp (`INSERT … ON CONFLICT` into `config`) | `entrypoint.sh:3-16`; `backend/app/schema_guard.py` (the upsert near :75-77) | fails / refuses | Worker compose **overrides `command:`** to launch uvicorn directly, skipping `entrypoint.sh` entirely — the dev compose's own precedent (`docker-compose.dev.yml:23`). The restore loop (Task 9) runs both **privileged, against the side database, before the swap**. |
| A2 | `embedder_registry.reconcile` — partition DDL | `backend/app/main.py:98` (wrapped :96-101) | fails, caught, logged | Skip under flag (Task 2). The restored snapshot already carries its partitions; nothing to reconcile, and depending on a caught exception for correctness is the "silently fails to hold" shape B1 condemns. |
| A3 | `reconcile_event_partitions` — partition DDL | `main.py:107` (wrapped) | fails, caught | Skip under flag. The worker journals nothing (see C-group), so future-month children are not needed. |
| A4 | `backfill_projects` — `INSERT … ON CONFLICT DO NOTHING` | `main.py:121` (wrapped) | fails, caught | Skip under flag. |
| A5 | `embedder_registry.register` for the LLM fingerprint — INSERT + DDL | `main.py:131` (wrapped) | fails, caught | Skip under flag. |
| A6 | **`job_registry.set_config("code_enrichment", …)` — UNGUARDED** | `main.py:568-578` | **raises out of `lifespan`; the app never boots** | Skip the write under flag (Task 2). **This one is not in the review** — B1 lists the guarded boot writers and `start_all`, but this config write has no `try` around it, so under the role it does not degrade, it takes the worker down at boot. |
| A7 | `job_registry.start_all()` — arms all jobs (24 with increment 6: `buffer_flush` would make live LLM calls with the snapshot's restored credentials; **`backup_ship` would ship snapshots of snapshots**; `expired_memory_cleanup` DELETEs) | `main.py:581` | each job errors at its first write; LLM jobs spend money *before* their first write | **Never called** under flag (Task 2). The role alone is insufficient here — a job's external calls (LLM, git, egress) happen client-side of the database, so disarming the scheduler is load-bearing, not ergonomic. |

**B. Reads that write, already degrading (log-and-swallow) — the role makes them inert; the flag makes them quiet:**

| # | Writer | Cite | Handling |
|---|---|---|---|
| B1 | Memory access bumps on every hybrid search | `backend/app/services/hybrid_search.py:288` → `access_stats.spawn_record_access` (`access_stats.py:132`; flush swallows errors by module contract) | Guard the spawn on the flag → no-op (Task 4). |
| B2 | Fact access bumps on every facts-channel read | `backend/app/services/facts_channel.py:245` → `fact_access_stats.spawn_record_access` (`fact_access_stats.py:113`, UPSERT at :69-83) | Same guard (Task 4). |
| B3 | `mark_key_used` — `api_keys.last_used_at` bump on every MCP call, own committed session | `backend/app/services/api_keys.py:279-305` | Guard on the flag (Task 4). |
| B4 | Journal rows on read/auth flows via `record_event`, which **never raises** and returns `False` on failure: login success/failure audits (`backend/app/api/routes/auth.py:103-121`), the `resumed` row on checkpoint resume-fill (`backend/app/services/resume_inject.py:75-77`) | `events.py:224` | Left to degrade — `record_event`'s contract already absorbs it — the worker's log notes the posture once at boot instead of once per request (Task 2 logs it). The four `JournalWriteFailed` raisers are all on write doors (verification transitions, adjudication) that the role blocks earlier. |
| B5 | `UsageRecorder.record` — `llm_usage` row per LLM/embed call, incl. the search query embed | `backend/app/services/usage_recorder.py` (`record` commits inside its own try/except, :127-191) | Left to degrade (already swallowed); becomes rare because the only LLM calls left are query embeds (see E). |

**C. Flows that hard-fail under the role and need explicit handling (Tasks 3–4):**

| # | Flow | Cite | Failure mode under role | Handling |
|---|---|---|---|---|
| C1 | `POST /auth/refresh` — blocklists the presented jti (INSERT + commit) before reissuing | `auth.py:191-207` | 500 → the SPA viewer silently dies at access-token expiry, the surface's main user | Under flag: **skip the blocklist insert, still reissue.** Stated cost: on the worker only, a captured pre-refresh token stays valid until its own `exp`. Acceptable for a read-only viewer; printed on the security-posture response so it is never silent. |
| C2 | `POST /auth/logout` — blocklist INSERT + journal + commit | `auth.py:126-140` | 500; cookie never cleared | Under flag: skip insert and commit, still clear the cookie. Same stated cost as C1. |
| C3 | `POST /auth/change-password` — config UPDATE + blocklist | `auth.py:143-193` | 500 mid-handler | Refuse 403 up front: changing a snapshot's password is meaningless (the next restore overwrites it) and a half-failed attempt is confusing. |
| C4 | `POST /api/v1/chat` — commits the user message **before** the LLM stream, then spends tokens on the snapshot's restored credentials | `backend/app/services/chat.py:174-180` (and :247-263) | 500 after the commit fails; or money spent then 500 | Refuse 403 at the route under flag — this is B1's cost concern (live LLM calls against restored credentials), not just a write. |
| C5 | `POST /api/v1/jobs/{key}/trigger` — runs a job on demand even though `start_all` never ran | `backend/app/api/routes/jobs.py:193` | the job runs; LLM/egress jobs spend before failing | Refuse 403 under flag (Task 2, beside the boot gate it completes). |
| C6 | Every other write door — captures (REST + MCP), settings PUTs, buffer requeue/discard, reembed, ratify, hygiene actions, `document_put`/`delete` | many | `asyncpg.exceptions.InsufficientPrivilegeError` (SQLSTATE 42501) wrapped in `sqlalchemy.exc.ProgrammingError` → 500 | **One global exception handler** (Task 3) maps SQLSTATE 42501 → HTTP 403 `{"read_only": true}`. This replaces the maintained per-route allowlist B1 rejected: the route inventory can rot, the SQLSTATE cannot. |

**D. Read shapes that must keep working — proven, not assumed (Task 5's integration test runs them under the real role):** hybrid/keyword search, facts reads, `GET /events` + timeline + calendar, checkpoints latest, documents get/outline/search, code-graph reads, login (in-memory rate limiter, `auth.py`; only journal writes, which degrade), `GET /auth/security-posture`, the SPA itself. Also verified there: **no read path uses `SELECT … FOR UPDATE`** (which needs row-lock privilege beyond SELECT). **The writer inventory this plan originally gave was wrong** (cross-plan review M-6, 2026-09-02): it named "the buffer claim and `_lock_config_row`", but `_lock_config_row` takes a *transaction advisory lock* and its own comment says `FOR UPDATE` "would not do" (`api/routes/config.py:427-430`), and `job_registry.py` issues none at all. The real set is twelve modules — `repositories/knowledge_triples.py` (`:509,563,963,1138`) and `services/{buffer_flush, memory_buffer, human_adjudication, fact_lift, dream_undo, wait_process, verification_ladder, entity_merge, verification_recompute, memory_dream, supersede}.py` — every one of them a writer path, which is what makes the D-group conclusion hold. Note a plain text grep also returns `api/routes/config.py:430` and `models/memory.py:91`, which are *prose mentions in docstrings*, not uses; the scan below must not count them as either. The setup wizard 403s on `require_uninitialized` because the snapshot carries `admin_password_hash` — correct, no handling needed. Repo *file* reads degrade (no clones in the worker's `repo_data` volume) while DB-backed code-graph reads work — accepted and stated in the runbook.

**E. External calls that survive on purpose:** the **query embed** on semantic search — a search surface that cannot embed cannot search, so the worker requires the snapshot's embedding endpoint to be reachable (operating requirement, stated in the runbook §prereqs; on this owner's topology that is the LAN Ollama, reachable from any LAN worker). The **reranker is clamped off** under the flag (Task 4) — an LLM scoring call per search against restored credentials is exactly the class A7 disarms, and unlike the embed it is optional. No other retrieval-path external call exists.

**F. The restore/serve collision (B1's last bullet):** `restore.sh` swaps via `ALTER DATABASE … RENAME`, which requires no live connections. The loop (Task 9) therefore **verifies before swapping**: replay into a side database, migrate + stamp it privileged, grant to the viewer role — all while the app serves the *previous* database — and only on success stop the app, swap, start. A snapshot from an older baseline fails `schema_guard` **on the side database**, the swap never happens, and the worker keeps serving what it had: the viewer never goes down for exactly the snapshots one most wants to inspect, closing B1's schema-mismatch scenario. `schema_guard` running only at boot is satisfied because the app always boots after a swap.

**Amendments (2026-09-02, cross-plan adversarial review of all eight plans).** Five defects, fixed in place; the B1 read-only redesign itself was reviewed line by line and found carried correctly. **B-2 (blocker)** — Task 11's new REST route is declared single-door in a docstring, which records nothing; it now takes a `PARITY_TABLE` row, an `EXPECTED_STATUS` entry and a regenerated parity doc (Step 2b). **B-1 twin (blocker)** — the receiver writes `/dumps` from a host bind mount as the same unprivileged user increment 6's job does, with the same root-owned-directory failure; Task 8 now carries the fix and a write probe. **M-6** — the `FOR UPDATE` inventory underpinning Task 5's own enforcement proof was wrong (`_lock_config_row` uses an advisory lock, `job_registry` uses none, and the real set is twelve modules); the scan now derives from the real set and ignores docstring mentions. **m-4** — `docker-compose.worker.yml` lands outside invariant 13's fixed-list worker-count tripwire. **m-5** — `read_only` reaches the posture JSON but no page renders it.

## Global Constraints

- **The role is the guarantee; the flag is ergonomics.** No task may justify skipping a role-side control because the flag already covers it, and no flag behaviour may be described as enforcement — in code comments, runbook or UI copy.
- **Backend tests** from `backend/`: `python -m pytest -q` (dev-compose Postgres 127.0.0.1:5433, `darkmem_test`). Task 5's role test creates a scratch cluster role and drops it in teardown.
- **Merge gate** `./scripts/gate.sh`; never bare Playwright; `--full` unreliable on this host.
- **No schema change anywhere in this plan.**
- **Two-door rule scope:** the inventory read (Task 11) is an ops surface, REST-only — the same standing `documents.reads` has (`docs/two-door-parity.md`). **A docstring does not record that status** (review B-2): single-door is declared by a `Surface` row in `PARITY_TABLE` with a stated reason, plus an `EXPECTED_STATUS` entry, plus a regenerated parity doc, all in the same commit as the route. Task 11 Step 2b. No MCP twin.
- **No in-app restore button** (§9.6). The UI renders the exact command; if a task finds itself adding a POST that restores, the plan is being violated, not extended.
- **Secrets:** the receiver bearer token and the age identity live in env/files on the worker host, never in the database (a snapshot must not carry its own decryption key — increment 6's rule) and never in a tracked file.
- **Redeploy rule:** backend/frontend/compose changes → Task 13 redeploys *this* machine. The worker machine itself is the owner's to provision from the runbook; nothing in the gate runs there.
- **Commits** `<type>(<scope>): <subject>`, ≤50 chars, atomic.

## File Structure

```
backend/app/config.py                          # Task 1: read_only flag
backend/app/api/routes/auth.py                 # Task 1: posture field; Task 3: C1-C3
backend/tests/test_security_posture.py         # Task 1
backend/app/main.py                            # Task 2: boot gates; Task 3: 42501 handler
backend/app/api/routes/jobs.py                 # Task 2: C5 trigger refusal
backend/tests/test_read_only_boot.py           # Task 2 (new)
backend/tests/test_read_only_doors.py          # Tasks 3-4 (new)
backend/app/services/access_stats.py           # Task 4: B1 guard
backend/app/services/fact_access_stats.py      # Task 4: B2 guard
backend/app/services/api_keys.py               # Task 4: B3 guard
backend/app/services/feature_flags.py          # Task 4: reranker clamp
backend/app/api/routes/chat.py                 # Task 4: C4 refusal
scripts/worker/viewer-grants.sql               # Task 5 (new)
backend/tests/test_read_only_role.py           # Task 5 (new)
backend/app/worker_receiver.py                 # Task 6 (new)
backend/tests/test_worker_receiver.py          # Task 6 (new)
backend/app/services/backup_ship.py            # Task 7: WorkerDestination
backend/app/services/backup_config.py          # Task 7: "worker" kind
docker-compose.worker.yml                      # Task 8 (new)
backend/tests/test_deployment_artifact.py      # Task 8: worker-compose assertions
scripts/worker/restore-cycle.sh                # Task 9 (new)
docs/runbook-backup-worker.md                  # Task 9 (new)
backend/app/services/backup_pull.py            # Task 10 (new)
scripts/restore.sh                             # Task 10: --from
backend/app/api/routes/backups.py              # Task 11 (new)
backend/tests/test_door_parity.py              # Task 11: PARITY_TABLE row (review B-2)
backend/tests/test_api/test_rest_conformance.py  # Task 11: EXPECTED_STATUS (B-2)
docs/two-door-parity.md                        # Task 11: regenerated + headline
frontend/src/features/settings/use-security-tab-binding.ts  # Task 12: read_only (m-5)
frontend/src/features/settings/components/backups-tab.tsx  # Task 12
CHANGELOG.md                                   # Task 13
```

---

### Task 1: The demoted flag and its honest reporting

**Files:**
- Modify: `backend/app/config.py` (`Settings`, :58ff)
- Modify: `backend/app/api/routes/auth.py` (`SecurityPostureResponse` :215-227, `auth_security_posture` :233-260)
- Modify: `backend/tests/test_security_posture.py`

**Interfaces:**
- Produces: `settings.read_only: bool` (env `DARKMEM_READ_ONLY`) — consumed by Tasks 2–4 and the worker compose; `read_only` + `read_only_token_rotation_disabled` on `GET /auth/security-posture`.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4

- [x] **Step 1: Failing test** in `tests/test_security_posture.py`: the posture response carries `read_only: false` by default; with `settings.read_only` monkeypatched true it reports `read_only: true` and `read_only_token_rotation_disabled: true` (the C1/C2 cost, reported the way `cookie_secure_clamped` reports its clamp — an operator must be able to tell the posture from the page, `auth.py:220-221`'s own comment is the precedent).
- [x] **Step 2:** In `Settings`:

```python
    # The backup worker's app-side posture (spec §9.5 as redesigned after B1).
    # NOT the enforcement: that is the SELECT-only darkmem_viewer role beneath
    # every code path. This flag only (a) skips boot writers and never arms
    # the job registry, (b) makes known write-on-read paths no-op instead of
    # erroring under the role, (c) refuses the doors whose failure mode is
    # money or a broken viewer session rather than a clean DB refusal.
    read_only: bool = Field(
        default=False,
        validation_alias=AliasChoices("DARKMEM_READ_ONLY", "READ_ONLY"),
    )
```

(`AliasChoices` from pydantic; keep `read_only` as the field name so `settings.read_only` reads naturally.) Add both fields to `SecurityPostureResponse` and the route return.
- [x] **Step 3:** `python -m pytest -q tests/test_security_posture.py` green.

---

### Task 2: Boot gating — the app that never writes at startup

**Files:**
- Modify: `backend/app/main.py` (:96-140, :568-581)
- Modify: `backend/app/api/routes/jobs.py` (:193ff)
- Create: `backend/tests/test_read_only_boot.py`

**Interfaces:**
- Consumes: `settings.read_only` (Task 1).
- Produces: a lifespan that, under the flag, performs zero DB writes and arms zero jobs; a trigger route that refuses.

**Implementer:** dcc-superpower-companions:impl-opus-medium
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 2 = 5

- [x] **Step 1: Failing tests** (`tests/test_read_only_boot.py`). Two shapes:
  - **An AST/source test in the roster-test style** (`tests/test_code_deriver.py:1490` shape): parse `app/main.py` and assert `start_all` is reached only under a `not settings.read_only` guard — i.e. the `await job_registry.start_all()` call node sits inside an `if` whose test names `read_only`. Same assertion for the `set_config("code_enrichment", …)` call (A6 — the unguarded boot write that would keep the worker from booting at all).
  - **Behavioural**: monkeypatch `settings.read_only = True`, spy on `JobRegistry.start_all`, `embedder_registry.reconcile`, `reconcile_event_partitions`, `backfill_projects`, `embedder_registry.register`; drive the lifespan (the app-factory fixture other boot tests use — see `tests/test_dream_jobs.py`'s lifespan idiom); assert none was called and one log line states the posture.
  - **Trigger refusal**: `POST /api/v1/jobs/buffer_flush/trigger` under the flag → 403 with `read_only` in the detail.
- [x] **Step 2: Implement.** In `lifespan`, wrap A2–A5 in one block:

```python
        if settings.read_only:
            logger.info(
                "DARKMEM_READ_ONLY: boot reconciliations, project backfill and "
                "embedder registration skipped; job registry will not be armed. "
                "Enforcement is the database role, not this flag."
            )
        else:
            ...  # the existing four reconciliation blocks, unchanged, indented
```

Guard A6 (`main.py:568-578`) and A7 (`:581`) the same way: `if not settings.read_only: … set_config … ; await job_registry.start_all()`. Job **registration** stays unconditional (harmless, in-memory, keeps the Jobs page rendering); only arming and the legacy config copy are gated. In `jobs.py`, at the top of `trigger_job`: `if settings.read_only: raise HTTPException(403, "read-only instance: jobs cannot be triggered")`.
- [x] **Step 3:** targeted + full suite green. The AST test is what keeps a future boot writer from landing unguarded — extend its skip-list assertion message to say so.

---

### Task 3: Auth flows and the 42501 door

**Files:**
- Modify: `backend/app/api/routes/auth.py` (C1 :191-207, C2 :126-140, C3 :143-193)
- Modify: `backend/app/main.py` (exception handler registration, beside the existing handlers)
- Create: `backend/tests/test_read_only_doors.py`

**Interfaces:**
- Consumes: `settings.read_only`.
- Produces: refresh/logout that work without writing; a global SQLSTATE-42501 → 403 mapping every unlisted write door inherits.

**Implementer:** dcc-superpower-companions:impl-opus-high
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 3 = 6
(Risk 3: auth token semantics change under a flag — the tests must pin that the *default* posture is byte-identical to today's.)

- [x] **Step 1: Failing tests:**
  - Default posture unchanged: refresh still blocklists (assert the `token_blocklist` row) — the regression pin.
  - Under the flag: refresh returns 200 + a fresh cookie and writes **no** row; logout returns 200, clears the cookie, writes no row; change-password → 403 before touching the session.
  - The handler: a route that INSERTs (use `POST /api/v1/memories` against a session whose execute is patched to raise a `ProgrammingError` wrapping an object with `sqlstate == "42501"`) returns 403 with body `{"error": {"code": "read_only", …}}` matching the `ErrorEnvelope` shape (`app/schemas/envelope.py`); any other `ProgrammingError` still surfaces as 500.
- [x] **Step 2: Implement.**
  - C1/C2: `if not settings.read_only:` around the `session.add(TokenBlocklist(...))` + journal + `commit()` block; the reissue path runs either way. Comment states the cost and points at the posture endpoint reporting it (Task 1).
  - C3: first line of `auth_change_password`: 403 with "read-only instance: the next restore would overwrite this password anyway".
  - Handler in `main.py`:

```python
    from sqlalchemy.exc import DBAPIError

    @app.exception_handler(DBAPIError)
    async def _read_only_refusal(request, exc):
        # The SELECT-only role refusing a write is the read-only worker
        # working as designed (B1: enforcement below every code path). One
        # SQLSTATE check replaces the per-route allowlist the review
        # rejected — routes rot, the error code cannot.
        if getattr(getattr(exc, "orig", None), "sqlstate", None) == "42501":
            return JSONResponse(status_code=403, content=jsonable_encoder(
                ErrorEnvelope(error=ErrorDetail(
                    code="read_only",
                    message="This instance is read-only; writes are refused at the database.",
                ))))
        raise exc
```

(Adapt to the file's existing handler idiom and the real `ErrorDetail` fields; catch `DBAPIError`, the base that covers `ProgrammingError`, and re-raise everything that is not 42501. asyncpg's `InsufficientPrivilegeError.sqlstate` is `"42501"`; the test pins the attribute path.)

**Why the non-42501 re-raise is correct rather than accidental** (cross-plan review m-16, 2026-09-02): `raise exc` from inside a Starlette exception handler propagates to `ServerErrorMiddleware`, which reaches the existing `@app.exception_handler(Exception)` at `main.py:883` and produces the ordinary 500 envelope. A reader checking whether the non-privilege branch loses its error handling will otherwise have to derive this; say it in a comment at the handler, because "re-raise" reads like a gap when it is the design.
- [x] **Step 3:** suite green, including the untouched auth tests.

---

### Task 4: Silencing the read-path writers, chat refusal, reranker clamp

**Files:**
- Modify: `backend/app/services/access_stats.py` (`spawn_record_access`, :132)
- Modify: `backend/app/services/fact_access_stats.py` (`spawn_record_access`, :113)
- Modify: `backend/app/services/api_keys.py` (`mark_key_used`, :279)
- Modify: `backend/app/services/feature_flags.py` (`get_feature_flags_dict`, :13-21)
- Modify: `backend/app/api/routes/chat.py` (the POST handler)
- Modify: `backend/tests/test_read_only_doors.py`

**Interfaces:**
- Consumes: `settings.read_only`.
- Produces: no-op bumps, a clamped `reranker_enabled`, a refused chat door.

**Implementer:** dcc-superpower-companions:impl-opus-medium
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 2 = 5

- [x] **Step 1: Failing tests:** under the flag — `spawn_record_access([...])` schedules nothing (both modules: assert the module's `_pending_counts` stays empty); `mark_key_used` returns without opening a session (patch the factory, assert uncalled); `get_feature_flags_dict` returns `reranker_enabled=False` even when the DB row says true, and leaves every other flag untouched; `POST /api/v1/chat` → 403 before any LLM construction. Default posture: all behave exactly as today (regression pins).
- [x] **Step 2: Implement** — each is a two-line guard at the top of the function, verbatim shape:

```python
    if settings.read_only:  # B-group, plan 2026-08-31-backup-worker: quiet no-op;
        return              # the viewer role is what actually enforces
```

For the clamp, after the merge in `get_feature_flags_dict`:

```python
    if settings.read_only:
        # An LLM scoring call per search against the snapshot's restored
        # credentials is the spend class the disarmed scheduler exists to
        # stop; the query embed stays (search cannot work without it).
        merged["reranker_enabled"] = False
```

Chat: `if settings.read_only: raise HTTPException(403, …)` at the route top.
- [x] **Step 3:** suite green. Note in the test module docstring which writers are deliberately **not** guarded (B4 journal rows, B5 usage rows) and why: `record_event` and `UsageRecorder` already never raise, and guarding them would spread the flag into shared writers for no behavioural gain.

---

### Task 5: The viewer role — provisioning script and the proof it holds

**Files:**
- Create: `scripts/worker/viewer-grants.sql`
- Create: `backend/tests/test_read_only_role.py`

**Interfaces:**
- Produces: the grants file the restore loop applies each cycle (Task 9); the executable proof that reads work and writes fail under it.

**Implementer:** dcc-superpower-companions:impl-opus-medium
**Evaluation:** files 1 - spec 1 - coupling 0 - risk 3 = 5
(Risk 3: this file IS the enforcement floor.)

- [x] **Step 1: The grants file** — idempotent, parameterised by psql vars, applied to the **side** database after replay+migrate, before the swap:

```sql
-- The backup worker's SELECT-only role (spec §9.5 as redesigned; review B1).
-- Applied by restore-cycle.sh to every freshly restored database BEFORE the
-- swap. Grants are re-run each cycle because the side database is created
-- fresh each time — no ALTER DEFAULT PRIVILEGES subtlety to rot.
-- Usage: psql -v viewer_password='...' -v dbname='...' -f viewer-grants.sql
SELECT format('CREATE ROLE darkmem_viewer LOGIN PASSWORD %L', :'viewer_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'darkmem_viewer') \gexec
SELECT format('ALTER ROLE darkmem_viewer PASSWORD %L', :'viewer_password') \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO darkmem_viewer', :'dbname') \gexec
GRANT USAGE ON SCHEMA public TO darkmem_viewer;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO darkmem_viewer;
```

No `GRANT` on sequences, functions or with any write verb — additions to this file are additions to the attack surface and take a recorded reason.
- [x] **Step 2: The integration test** (`tests/test_read_only_role.py`), against the test database: create a scratch role `darkmem_viewer_test` (drop in teardown — roles are cluster-global; use a fixture with `DROP ROLE IF EXISTS` guarded by ownership of test objects via `DROP OWNED`), apply the grants file's statements, open a second engine as that role, and assert:
  - `SELECT` against `memories`, `knowledge_triples`, `events`, `documents`, `session_checkpoints`, and one `memory_embeddings__<slug>` partition (register a fingerprint first with the privileged engine) all succeed;
  - `INSERT` into `memories`, `UPDATE` on `config`, `DELETE` on `events`, `SELECT … FOR UPDATE` on `memory_buffer`, and `CREATE TABLE` each raise with SQLSTATE 42501 — asserting the code, not the message;
  - a source scan pinning the D-group claim, **written against the real inventory** (review M-6). Two corrections to how it is built: derive the expectation from the twelve writer modules listed in section D, not from the three-name allowlist this plan first gave; and match on *code*, not raw text, since `api/routes/config.py:430` and `models/memory.py:91` mention `FOR UPDATE` only in a docstring. Concretely: walk `rg -l "with_for_update|FOR UPDATE" backend/app`, drop hits whose only matches are inside comments or docstrings, assert the remainder equals the recorded writer set exactly (a *new* writer fails the test and takes a recorded classification — that is the point), and separately assert the **pure-read** modules named in section D (`hybrid_search`, `facts_channel`, `block_query`, `checkpoints`, `events`, `code_query`) contain no hit at all. `document_door` is deliberately **not** in that list: it serves reads *and* writes (`put_document`, `delete_document`), and increment 8 adds a `FOR UPDATE` on the document row to close its own conversion race — which fails under the viewer role with 42501 and reaches the 403 handler, exactly as a write should. Its read verbs (`document_blocks`, `document_outline`, `search_sections`) take no lock, and that is what section D's claim actually rests on; asserting the whole module is lock-free would be asserting something false about a writer. Equality rather than subset: an allowlist a future author widens to go green proves nothing, which is the failure this test exists to prevent.
- [x] **Step 3:** targeted test green against the dev-compose Postgres; full suite green.

---

### Task 6: The receiver — a separate process, not the app

**Files:**
- Create: `backend/app/worker_receiver.py`
- Create: `backend/tests/test_worker_receiver.py`

**Interfaces:**
- Produces: an ASGI app (`python -m uvicorn app.worker_receiver:app`) consumed by the worker compose (Task 8) and by increment-6's ship side through Task 7's client. Shares **nothing** with the darkmem app but the `/dumps` filesystem — no `app.database`, no `app.main`, no session factory.

**Implementer:** dcc-superpower-companions:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 2 = 5

- [x] **Step 1: Failing tests** (httpx `ASGITransport` against the app, `tmp_path` as the dir): PUT streams to `<name>.part` then renames — a client that disconnects mid-body leaves only a `.part`, never a listed snapshot; wrong/absent bearer → 401; a name failing `^darkmem-app-[A-Za-z0-9._-]+\.sql\.gz(\.age)?$` → 422 (path traversal and foreign-prefix uploads both die here); GET streams bytes back (the read-back verify); GET list excludes `.part`; DELETE removes; over `RECEIVER_MAX_BYTES` → 413.
- [x] **Step 2: Implement** — starlette (already a fastapi dependency), ~120 lines, module docstring first:

```python
"""Snapshot receiver — the worker's ONE write door, deliberately outside the
darkmem app (spec §9.5, review B1: an https write door inside a read-only
instance is a contradiction). Writes files to RECEIVER_DIR and does nothing
else: no database, no session, no import from app.main or app.database.
Content arrives age-encrypted (increment 6 encrypts before egress), so the
bearer token is authorisation, not confidentiality; front TLS if the path
crosses untrusted networks (runbook §receiver)."""
```

Env: `RECEIVER_TOKEN` (required, refuse to start under 32 chars), `RECEIVER_DIR` (default `/dumps`), `RECEIVER_MAX_BYTES` (default 10 GiB). Bearer check via `hmac.compare_digest`. Routes: `PUT /snapshots/{name}`, `GET /snapshots`, `GET /snapshots/{name}`, `DELETE /snapshots/{name}`. Stream request body chunkwise to the `.part`, `os.fsync`, `os.replace`. A `test_receiver_imports_nothing_from_the_app` walks the module's import closure and fails if `app.database`, `app.main` or any `app.services.*` module is reachable — the process-separation claim, pinned structurally (the `test_block_pipeline.py` closure-walk idiom).
- [x] **Step 3:** suite green.

---

### Task 7: The `worker` destination kind

**Files:**
- Modify: `backend/app/services/backup_config.py` (`KINDS` += `"worker"`; `WorkerSettings {url, token}`; token joins `SECRET_FIELDS`; non-local encrypt rule already covers it)
- Modify: `backend/app/services/backup_ship.py` (`WorkerDestination` over httpx: ship = streamed PUT, read-back = streamed GET into sha256, list, prune = DELETE beyond keep)
- Modify: `backend/tests/test_backup_ship.py`, `backend/tests/test_backup_config.py`

**Interfaces:**
- Consumes: increment 6's protocol and config service; Task 6's wire contract.
- Produces: the §9.2 table's fourth destination.

**Implementer:** dcc-superpower-companions:impl-opus-medium
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 2 = 5

- [x] **Step 1: Failing tests:** config round-trip masks the token; a worker destination without an age recipient is refused (rule 1 — the receiver stores ciphertext only); `WorkerDestination` tested against Task 6's real ASGI app via httpx `ASGITransport` — ship, read-back-verify, list, prune, and the mismatch path journaling `backup_verify_failed` through `ship_all`.
- [x] **Step 2: Implement.** httpx `AsyncClient` per operation, explicit timeouts, streamed both directions (`content=aiter_bytes` on PUT; `resp.aiter_bytes()` into the hash on GET — hashing offloaded per chunk is fine, the chunks are small).
- [x] **Step 3:** suite green.

---

### Task 8: The worker compose file

**Files:**
- Create: `docker-compose.worker.yml`
- Modify: `backend/tests/test_deployment_artifact.py`

**Interfaces:**
- Consumes: the image, Task 1's flag, Task 6's receiver, the viewer role name.
- Produces: the worker stack definition Tasks 9's runbook provisions.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 2 = 4

- [x] **Step 1: Failing tests** in `test_deployment_artifact.py` (its compose-parsing helpers): the worker app service (a) sets `DARKMEM_READ_ONLY=true`, (b) sets `DB_USER=darkmem_viewer` (never the owner role), (c) **overrides `command:`** so `entrypoint.sh` (alembic + stamp) never runs, and the command carries `--no-proxy-headers` (the existing `test_no_compose_command_re_enables_proxy_headers` at :86 must also pick the new file up — extend its file list), (d) the receiver service runs `app.worker_receiver`, not `app.main`, and shares only the dumps volume with the app; (e) the compose `name` is not `darkmem-prod` (the project-name collision the prod file's header documents).
- [x] **Step 2: Write the file**, key content:

```yaml
# The backup worker (spec §9.5, redesigned after review B1). Same image, same
# SPA — but the app connects as the SELECT-only darkmem_viewer role, never
# migrates (command overrides entrypoint.sh; restore-cycle.sh migrates and
# stamps privileged, app stopped), and never arms the job registry
# (DARKMEM_READ_ONLY). The receiver is the ONE write door and it is a
# separate process that shares only the dump directory with the app.
name: darkmem-worker
services:
  darkmem:
    image: darkraise/darkmem:${DARKMEM_VERSION:-latest}
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
    environment:
      - ENVIRONMENT=production
      - DARKMEM_READ_ONLY=true
      - DB_HOST=postgres
      - DB_USER=darkmem_viewer
      - DB_NAME=darkmem
      - DB_PASSWORD=${VIEWER_PASSWORD:?set VIEWER_PASSWORD in .env}
      - JWT_SECRET=${JWT_SECRET:?…}
      - COOKIE_SECURE=${COOKIE_SECURE:-false}
    ports: ["8000:8000"]
    ...
  receiver:
    image: darkraise/darkmem:${DARKMEM_VERSION:-latest}
    command: ["uvicorn", "app.worker_receiver:app", "--host", "0.0.0.0", "--port", "8100"]
    environment:
      - RECEIVER_TOKEN=${RECEIVER_TOKEN:?…}
      - RECEIVER_DIR=/dumps
    ports: ["8100:8100"]
    volumes: ["${DARKMEM_DUMP_DIR:-/srv/darkmem-dumps}:/dumps"]
  postgres:
    # same pgvector image/command shape as prod; POSTGRES_* are the OWNER
    # role's — the app never sees these, only VIEWER_PASSWORD.
    ...
```

(Fill the elided blocks from `docker-compose.yml`'s postgres/healthcheck/network shape; healthchecks on all three.) Note the app has **no dumps volume** — it never reads or writes snapshots; only the receiver and the host-side loop touch them.

**The receiver's `/dumps` mount carries increment 6's B-1 defect and needs the same fix** (cross-plan review, 2026-09-02). The receiver runs the same image, so it runs as the same unprivileged `app` user (`Dockerfile:87-88`), and a host bind mount is not chowned by Docker. Every upload would fail on its first write with the directory owned by root — and on the worker host this is the *only* thing the receiver does, so the failure is total. Two changes: the default becomes `${DARKMEM_DUMP_DIR:-/srv/darkmem-dumps}` to match increment 6 (never under `/root`, which is 0700), and the runbook's worker-provisioning section (Task 9) creates it before first boot:

```bash
APP_UID=$(docker run --rm darkraise/darkmem:latest id -u)
sudo install -d -o "$APP_UID" -g "$APP_UID" -m 0750 /srv/darkmem-dumps
docker compose -f docker-compose.worker.yml up -d receiver
docker compose -f docker-compose.worker.yml exec -T receiver \
  sh -c 'touch /dumps/.probe && rm /dumps/.probe' && echo "receiver mount writable"
```

The receiver should also refuse to start when `RECEIVER_DIR` is not writable, rather than accepting an upload and failing on the write: a receiver that 500s every POST after a green boot is the same silent shape increment 6's B-1 has.
- [x] **Step 3b: Bring the new compose file under invariant 13's tripwire** (cross-plan review m-4, 2026-09-02)

`test_no_compose_file_sets_a_worker_count` (`test_deployment_artifact.py:108-112`) is parametrised over a fixed `[PROD_COMPOSE, DEV_COMPOSE]` list, so `docker-compose.worker.yml` lands **outside** the guard that keeps `WEB_CONCURRENCY` and `UVICORN_WORKERS` out of an ops file. Add a `WORKER_COMPOSE` constant and include it in that parametrisation. Invariant 13 binds every launch path, and a worker running the same app with the same in-process schedulers, limiter and WebSocket fan-out is a launch path; a compose file nothing checks is exactly where a second worker gets added later "just for the viewer".

- [x] **Step 4:** tests green.

---

### Task 9: The restore loop — outside the app, verify before swap

**Files:**
- Create: `scripts/worker/restore-cycle.sh`
- Create: `docs/runbook-backup-worker.md`
- Modify: `backend/tests/test_deployment_artifact.py` (script staleness pins, the `test_restore_*` stub-compose idiom at :290-473)

**Interfaces:**
- Consumes: `docker-compose.worker.yml`, `viewer-grants.sql`, the age identity file, `restore.sh`'s staged-cleanup patterns (`scripts/restore.sh:31-99` — read it before writing a line).
- Produces: the nightly cycle a systemd timer on the worker host runs.

**Implementer:** dcc-superpower-companions:impl-opus-high
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 3 = 6
(Risk 3: this script drops and renames databases on a schedule.)

- [x] **Step 1: The sequence**, exactly (F-group of the inventory):
  1. Pick the newest `darkmem-app-*.sql.gz.age` in `$DUMP_DIR` that is **not** the one recorded in `$STATE_FILE` as already serving (idempotent re-run).
  2. `age -d -i "$AGE_IDENTITY"` to a temp `.sql.gz`; verify the pg_dump completion marker (`restore.sh:17-26`'s exact check); refuse and log on failure — the previous database keeps serving.
  3. Replay into side DB `darkmem_restore_$$` as the **owner** role (`docker compose -f docker-compose.worker.yml exec -T postgres psql …`, `restore.sh:74-84`'s shape including `ON_ERROR_STOP` and the staged `cleanup` trap).
  4. **Privileged migrate + stamp against the side DB, app still serving the old one**: `docker compose -f docker-compose.worker.yml run --rm --no-deps -e DB_USER=darkmem -e DB_PASSWORD="$OWNER_PASSWORD" -e DB_NAME="$SIDE_DB" darkmem sh -c "python -m alembic upgrade head && python -m app.schema_guard"` (the image's CMD is `./entrypoint.sh`, so `run … sh -c` replaces it cleanly — Dockerfile `CMD` line). **A non-zero exit here — an older-baseline snapshot failing `schema_guard` — drops the side DB and exits 0 with a loud log line: the viewer keeps serving the previous snapshot.** This is the B1 schema-mismatch answer; the runbook states it in its own section.
  5. Apply `viewer-grants.sql` to the side DB (`-v viewer_password="$VIEWER_PASSWORD" -v dbname="$SIDE_DB"`).
  6. `docker compose … stop darkmem` → `DROP DATABASE IF EXISTS darkmem` (no live connections now; receiver holds none by construction — Task 6's no-database pin) → `ALTER DATABASE "$SIDE_DB" RENAME TO darkmem` → `docker compose … start darkmem`. Downtime = the swap, seconds.
  7. Record the served snapshot name in `$STATE_FILE`; prune decrypted temp files.
  Every stage failure follows `restore.sh`'s stage-tracking `cleanup()` pattern with hand-finish instructions; the one stage that must never be reachable with the app stopped and no database is guarded the way `restore.sh:88-99` guards its rename.
- [x] **Step 2: Tests** with the stub-compose harness `test_restore_*` uses: marker refusal before any compose call; migrate-failure path drops the side DB and never stops the app; the stop→drop→rename→start order; grants applied before the swap.
- [x] **Step 3: The runbook** (`docs/runbook-backup-worker.md`): prerequisites (a LAN machine with docker, the image, `age` on the host, reachability of the snapshot source and of the embedding endpoint — inventory group E), provisioning (env file: `VIEWER_PASSWORD`, `OWNER_PASSWORD`/`DB_PASSWORD`, `JWT_SECRET`, `RECEIVER_TOKEN`, `AGE_IDENTITY` path), the systemd service+timer units (nightly, `Persistent=true`, after the expected ship hour), the schema-mismatch behaviour, what read-only honestly means (role = floor, flag = ergonomics, C1/C2 token-rotation cost), and what does NOT work on the worker by design (chat, captures, jobs, repo file browsing). State plainly: **the receiver is the only write door and it writes files, not rows.**

---

### Task 10: `restore.sh --from <destination>` and the pull helper

**Files:**
- Create: `backend/app/services/backup_pull.py`
- Modify: `scripts/restore.sh`
- Modify: `backend/tests/test_backup_ship.py` (pull tests), `backend/tests/test_deployment_artifact.py` (restore.sh flag tests beside :290-473)

**Interfaces:**
- Consumes: destination clients (inc 6 + Task 7), the `/dumps` bind mount (inc 6 Task 1).
- Produces: `python -m app.services.backup_pull <name-or---latest> --destination <dest> --out /dumps`; `restore.sh --from <dest> [--identity FILE] [SNAPSHOT]`.

**Implementer:** dcc-superpower-companions:impl-opus-medium
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 2 = 5

- [x] **Step 1: `backup_pull`** — a `__main__`-runnable async module: load the named destination (unmasked), `list_snapshots()`, resolve `--latest` or the given name, stream it into `--out` via a `.part` rename, **verify the download's sha256 against a fresh `read_back_sha256`** (a pulled snapshot gets the same distrust as an uploaded one), print the resulting container path on stdout as the last line (the shell contract). Tests: fake destination, latest resolution, `.part` discipline, checksum-mismatch refusal.
- [x] **Step 2: `restore.sh --from`.** Argument parsing ahead of the existing positional (keep `restore.sh FILE.sql.gz` byte-compatible — the deployment-artifact tests at :204-473 pin its behaviour and must stay green). With `--from`:
  1. `$COMPOSE exec -T darkmem python -m app.services.backup_pull --destination "$FROM" --latest --out /dumps` → read the printed path; map `/dumps/<file>` to `${DARKMEM_DUMP_DIR:-/srv/darkmem-dumps}/<file>` on the host.
  2. If the file ends `.age`: require `age` on the host and `--identity FILE` (or `$AGE_IDENTITY`); decrypt to a temp `.sql.gz`; **the identity never leaves the host** — decryption cannot happen in the container because the container must never hold the identity (inc 6's rule, restated here).
  3. Fall through to the existing marker-check → confirm → side-DB replay flow unchanged.
- [x] **Step 3:** new tests green (stub compose harness: `--from` invokes the pull through compose exec, refuses an `.age` with no identity, decrypts then proceeds); existing restore tests untouched and green.

---

### Task 11: Snapshot inventory endpoint

**Files:**
- Create: `backend/app/api/routes/backups.py`
- Modify: `backend/app/main.py` (router include, beside the other `include_router` lines)
- Create: `backend/tests/test_backups_inventory.py`

**Interfaces:**
- Consumes: destination clients (`list_snapshots`), the `backup_shipped`/`backup_verify_failed` journal (inc 6).
- Produces: `GET /api/v1/backups/inventory` → per destination: `{name, kind, snapshots: [{name, size, modified_at}], last_outcome: {event_type, at, sha256?} | null, error: str | null}`.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 1 = 4

- [x] **Step 1: Failing tests:** two fake destinations (one listing, one whose `list_snapshots` raises — the response carries its `error` string and the other destination's rows intact: one unreachable NAS must not blank the whole inventory); `last_outcome` is the newest matching `events` row per destination (SQL over `events` filtered `event_type IN (…) AND payload->>'destination' = :name` — an indexless payload filter is fine at this row count; say so in a comment).
- [x] **Step 2: Implement.** REST-only, stated in the docstring with the `documents.reads` parity citation (`docs/two-door-parity.md`). Auth via the standard `require_auth` dependency. No verb here mutates anything — this is §9.6's "make the decision informed" surface, and it works identically on prod and on the worker (where it reads through the viewer role untouched).

- [x] **Step 2b: Classify the route, or the gate is red** (cross-plan review B-2, 2026-09-02)

"REST-only, stated in the route docstring" is not how single-door status is recorded — a docstring satisfies no test. Two enumeration-driven guards walk `app.routes` and fail on any route nobody classified, and neither file was in this plan's File Structure:

1. **`backend/tests/test_door_parity.py`** — add a `Surface` (`test_every_rest_route_is_classified`, `:1362-1380`):

```python
    Surface(
        name="backups.inventory",
        status=REST_ONLY,
        rest=(("GET", f"{V1}/backups/inventory"),),
        mcp=(),
        reason=(
            "An operator's read of where this instance's own encrypted "
            "snapshots landed and whether each verified, so a human can decide "
            "whether to restore. Restoring is deliberately a shell command and "
            "never a route (spec section 9.6), so the read exists to inform a "
            "person at a console; an agent has no restore verb to inform. It "
            "also enumerates destination names an agent has no reason to know."
        ),
    ),
```

`test_every_single_door_surface_states_a_real_reason` requires at least 80 characters and rejects the `_NON_REASONS` placeholders — write it for a reader who will question the decision.

2. **`backend/tests/test_api/test_rest_conformance.py`** — add `("GET", "/api/v1/backups/inventory"): 200` to `EXPECTED_STATUS` (`test_every_route_status_code_matches_the_convention`, `:297-310`).

3. **Regenerate `docs/two-door-parity.md`** — it is generated from `PARITY_TABLE`, never hand-edited (`test_door_parity.py:9-11`, `:1834-1849`) — and update its headline to the counts `test_the_committed_table_reports_its_own_counts` (`:1851-1875`) derives. **Read the number off the failing assertion, never from another plan**: increment 6 adds a surface too, and increment 8's plan states literal totals computed before either of these existed.

Add `backend/tests/test_door_parity.py`, `backend/tests/test_api/test_rest_conformance.py` and `docs/two-door-parity.md` to this task's Files list.
- [x] **Step 3:** suite green; `/openapi.json` shows the route.

---

### Task 12: Inventory UI and the exact command — no restore button

**Files:**
- Modify: `frontend/src/features/settings/components/backups-tab.tsx` (inc 6's tab gains an Inventory section)
- Modify: `frontend/src/features/settings/use-backups-tab-binding.ts` (inventory query; `worker` kind in the destination form types)
- Modify: `frontend/src/features/settings/__tests__/backups.test.tsx`

**Interfaces:**
- Consumes: Task 11's endpoint; Task 7's `worker` kind.
- Produces: §9.6's informed-decision surface.

**Implementer:** dcc-superpower-companions:impl-opus-low
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 1 = 4

- [x] **Step 1: Failing tests:** the section renders per-destination snapshot rows (name, age, size, verification badge from `last_outcome`); a destination with `error` renders the error inline; the restore command block renders exactly `./scripts/restore.sh --from <name> --latest` for the selected destination with a copy button; **assert no element posts anything** — the section's queries are GET-only and there is no restore action (test: no button whose handler calls `apiFetch` with a non-GET on this section).
- [x] **Step 2: Implement** with darkraise-ui `card`/`timeline`/`empty-state`; the copy explains the posture in one sentence: *"Restoring replaces the live database; it is deliberately a shell command, not a button."* Add `worker` to the destination form's kind options (url + token fields, token masked).

**Render the read-only posture on the Security tab too** (cross-plan review m-5, 2026-09-02). Task 1 adds `read_only` and `read_only_token_rotation_disabled` to `SecurityPostureResponse`, and its own rationale is that "an operator must be able to tell the posture from the page" — but no task renders them, so today's `"never silent"` is true of the JSON and false of the SPA. Add both to the Security tab beside the existing `cookie_secure_clamped` line (`frontend/src/features/settings/use-security-tab-binding.ts:50` already types the posture object), with copy that says what the flag does *not* do: the role is the enforcement, the flag is ergonomics, and token rotation is disabled while it is on. Add that file and the Security tab component to this task's Files list.
- [x] **Step 3:** `npm test -- backups && npm run typecheck && npm run build` green.

---

### Task 13: Gate, changelog, deploy

**Files:**
- Modify: `CHANGELOG.md`

**Implementer:** dcc-superpower-companions:impl-sonnet-medium
**Evaluation:** files 0 - spec 0 - coupling 0 - risk 2 = 2

- [x] **Step 1:** `./scripts/gate.sh` green.
- [x] **Step 2:** CHANGELOG section (coordinate with the other 2026-08-31 plans; one push, one section).
- [x] **Step 3:** Atomic commits: `feat(worker): read-only posture behind a SELECT-only role`, `feat(worker): snapshot receiver and restore cycle`, `feat(backup): restore --from and snapshot inventory`.
- [x] **Step 4: Redeploy this machine** (the backend and SPA changed — the flag defaults off, so prod behaviour is unchanged, but the inventory endpoint and UI must reach the running image):

```bash
DARKMEM_PUSH=0 ./scripts/build-push.sh && docker compose up -d
curl -s http://127.0.0.1:8000/openapi.json | grep -o '/backups/inventory'
curl -s -b "$COOKIE_JAR" http://127.0.0.1:8000/api/v1/auth/security-posture | grep read_only
```

- [x] **Step 5: Worker bring-up is the owner's procedure**, from `docs/runbook-backup-worker.md` — a second machine is provisioned there, not from this host's gate. Verify end-to-end when it exists: configure a `worker` destination on prod pointing at the receiver, "Run now", watch `backup_shipped` with `verified: true`, run one `restore-cycle.sh` by hand on the worker, log into the worker's SPA and confirm the posture banner fields on `/auth/security-posture`, a search works, and a capture attempt returns the 403 `read_only` envelope.

## Rollback

Everything is additive behind a default-off flag: revert and redeploy, prod unaffected at every intermediate state. The worker stack is a separate compose project on a separate machine — `docker compose -f docker-compose.worker.yml down` removes it wholesale. `restore.sh`'s legacy invocation is pinned unchanged by the existing artifact tests. The viewer role, if ever created on the prod cluster by mistake, holds SELECT only — but drop it anyway (`DROP OWNED BY darkmem_viewer; DROP ROLE darkmem_viewer;`).

## Notes on scope

- **What the posture honestly is** (say this wherever the feature is described): writes are prevented by the database role; the flag only prevents *spend* (LLM calls from jobs/chat/reranker) and *noise* (500s and error-log spam where a quiet no-op or a clean 403 is correct). A reader who takes away "the flag makes it read-only" has been misled, and the runbook, the posture endpoint and the code comments all carry the correction.
- **Found beyond the review:** (a) inventory item A6 — the unguarded `set_config("code_enrichment", …)` boot write at `main.py:568-578`, which under the role does not degrade but prevents boot entirely; (b) C5 — `POST /jobs/{key}/trigger` runs a job on demand even with the scheduler disarmed; (c) the C1/C2 refresh/logout blocklist writes, which would kill the SPA viewer session the worker exists to serve; (d) the query-embed/reranker split in group E — semantic search *requires* one live external call per search, which no read-only design can remove without removing search.
- **Not built, on purpose:** TLS termination for the receiver (content is ciphertext; token is authz; the runbook says when to front TLS) — a cert-management feature is out of scope. A keyword-only search fallback when the embedder is unreachable — the failure is loud and the requirement stated instead. Any scheduler on the worker app — the restore loop is a host-side systemd timer precisely so the app process never owns the operation that drops its own database (B1's last bullet).
- **Increment ordering:** Tasks 1–5 are independent of increment 6 and can land first; Tasks 7, 10, 11, 12 consume increment 6's modules and must follow it.
