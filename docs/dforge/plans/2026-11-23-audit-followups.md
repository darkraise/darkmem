# Audit Follow-ups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: dforge:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the 106 open rows that `docs/dforge/specs/2026-11-23-audit-followups-design.md` assigns from `docs/dforge/registers/2026-11-20-audit-remaining.md`: the minor findings and discovered items of the 2026-11-20 plan, and the 18 adjacent findings of the 2026-11-23 row check.

**Architecture:** Thirty-seven sequential tasks in the spec's twelve work packages. Task 1 reproduces the Phase 5 deadlock before any retry exists; every other task reproduces its rows with a failing test (or the named command), applies the row check's fix or the spec's departure, and corrects the contract sentence it changes in the same commit. No Alembic revision, no new route or MCP tool, nothing pushed or deployed inside the run.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy async, pytest with pytest-xdist; Postgres with pgvector; React, TypeScript, TanStack Router and Query, darkraise-ui, vitest on happy-dom, Playwright, Storybook 10; bash; the generated Python and TypeScript SDKs.

**Spec:** docs/dforge/specs/2026-11-23-audit-followups-design.md

**Execution:** inline — `claude --model opus --effort high` — the highest task total is 8 (Tasks 1 and 21), both risk 3

**Parallelism:** sequential — inline execution

**Task check:** `bash .dforge/gate-legs.sh` — the full suite last passed in 266 s

**Integration check:** `bash .dforge/gate-legs.sh`

**CI:** `.github/workflows/ci.yml .github/workflows/release.yml .github/workflows/cache-cleanup.yml` — platforms: uutils (ubuntu-latest), darkmem-linux — local: `bash .dforge/gate-legs.sh` — uncovered: uutils (ubuntu-latest)

**Worktree setup:** `docker compose -f docker-compose.dev.yml up -d postgres`, then confirm `.dforge/test-env.sh` and `.dforge/gate-legs.sh` exist (local, untracked files from the 2026-11-20 plan)

**Plan review:** 2026-11-23 — dforge:judge-opus — executability 13 / coherence 17 / coverage 18 / assumptions 13 (round 1)

## Global Constraints

- **Verify first (spec rule 1).** Every row starts with its failing test, or with the named command where no test can reproduce it. A row whose test passes unchanged, or whose described code no longer exists, is not fixed: close it with `bash <plugin-root>/scripts/register set docs/dforge/registers/2026-11-20-audit-remaining.md <id> done --note "not reproduced: <evidence>"`. A test contract marked *guard* pins code that is right today (rows 246, 255, 300); its Step 2 proves the test can fail by reverting the named line locally, seeing it red, and restoring it.
- **Where a row lives.** Each task names its rows by register number. The row's evidence, file locations and default fix are its `### #<row>` entry in `.dforge/row-check/lane-{a,b1,b2,c,d}-report.md` (grep for the heading, never read a whole report). Where this plan names no departure, the fix is that entry's (spec rule 2). Line numbers there date from 2026-11-23; find the code by the quoted name.
- **Contract sentences move with the code (spec rule 3).** A change to behaviour that `CLAUDE.md` or `docs/two-door-parity.md` states is corrected in place in the same commit, with no note saying it was corrected.
- **No schema change (spec rule 4).** No task adds an Alembic revision or edits `0001_baseline.py`. A task that finds it needs one stops and records the need through the auto run's ruling ladder.
- **Doors (spec rule 5).** No route or MCP tool is added. After removing a request field, a header or a served field (Tasks 19, 33, 34), run the guards leg from `CLAUDE.md` ("The guards leg is mandatory…"), `make generate` in `sdks/`, and re-read the headline counts sentence in `docs/two-door-parity.md` and `CLAUDE.md`'s tool and job counts.
- **No removal without proof (spec rule 6).** Remove a module, export or helper only after `rg` shows no importer outside its own tests; quote the search in the commit body.
- **Host limits (spec rule 7).** Run Python as `backend/.venv/bin/python` from `backend/`; there is no `python` on PATH. Backend tests take their database from `. ../.dforge/test-env.sh` (the dev Postgres on `127.0.0.1:5433`, database `darkmem_test`); never set `DATABASE_URL` in front of pytest and never point a test, harness or script at production (`127.0.0.1:5432`, container `darkmem-prod-postgres-1`). Exit 143 is SIGTERM from `earlyoom`: read `free -h` and re-run before believing a red leg. Give every test, build and network command a timeout.
- **`scripts/backup.sh` runs against production from this checkout at 03:30 host time** (the systemd timer). Task 22 edits and tests it in one sitting and commits before stopping; never leave it half-edited.
- **Never run Playwright bare.** Use `backend/scripts/e2e/run_playwright_e2e.py <spec> --project=chromium`; `npx playwright test` points `/api` at the live instance on `:8000`.
- **Nothing leaves this machine.** No `git push`, no image push, no deploy, no requeue and no write to production inside the run. The 2026-11-20 plan's after-merge deploy sequence runs once, after this plan merges (owner ruling, 2026-11-23), outside the run.
- **Single worker (invariant 13).** No `--workers`, `WEB_CONCURRENCY` or `deploy.replicas` anywhere. An in-process cache or single-flight added here relies on the single worker and says so in one comment.
- **Tests.** One test per behaviour at the lowest layer that can fail for it. A contract names the file a test goes in; when an existing file already covers the same function, the test goes there. Never pin a test to serial; a test that fails only under `-n 4` is leaking state.
- **Frontend.** Check `ls frontend/node_modules/darkraise-ui/dist/components/` before building any UI; restyle a built-in, never re-implement one; a local component records which library gap it fills. Never run a repo-wide `prettier --write`. `routeTree.gen.ts` is generated. Demo mode (`VITE_DEMO=1`) makes no API request: a new hook passes `enabled: !DEMO` or its demo twin. Frontend commands run from `frontend/`: `timeout 900 npx vitest run <paths>` and `timeout 600 npm run typecheck`.
- **Generated SDK clients.** `sdks/ts/src/client.ts` and `sdks/python/darkmem_sdk/client.py` are generated: edit `sdks/generate.py` and run `make generate` in `sdks/`.
- **Comments.** None unless the why is non-obvious. Never reference the task, plan or row number in code.
- **Commits.** `<type>(<scope>): <subject>`, subject at most 50 characters, imperative, no attribution lines. One commit per task. Never `--no-verify`. Leave the untracked `graph.jpg` alone.
- **Register.** When a task's commit lands, set each row its `**Items:**` line names with `bash <plugin-root>/scripts/register set docs/dforge/registers/2026-11-20-audit-remaining.md <id> done --note "<commit sha7>"`, unless the row was closed `not reproduced` or the task says otherwise. A row two tasks cite (308, 342) is closed by the later one.
- **Plugin scripts.** `scripts/register` and `scripts/ui-proof` are dforge plugin scripts, called as `bash <plugin-root>/scripts/<name>`, where the plugin root is the path the session start prints.
- uutils (ubuntu-latest): a lock built on `mkdir` failing when the directory exists does not exclude a second process — create the lock file with `set -C` (noclobber), or use `flock`.
- uutils (ubuntu-latest): `timeout` signals only the command it started, so the command's children keep running — run the command in its own process group (`setsid`) and signal the group.

## Contracts

- **C1 — deadlock retry.** `backend/app/services/pipeline.py` defines `DEADLOCK_SQLSTATE = "40P01"`, `DEADLOCK_ATTEMPTS = 3` (attempts in all, first one included) and `_is_deadlock(exc: BaseException) -> bool`, true only for a `sqlalchemy.exc.DBAPIError` whose `getattr(exc.orig, "sqlstate", None) == DEADLOCK_SQLSTATE`. Each retried deadlock logs one WARNING whose message contains the memory id and `attempt <n> of 3`. A savepoint that ends on a deadlock records an error string containing `40P01`. Produced by Task 1, consumed by Task 2.
- **C2 — no declared context in the SDKs.** After Task 33 neither generated client has a `declareContext` / `declare_context` verb or a `CONTEXT_HEADER` constant, and no SDK verb sends `X-Darkmem-Context` or a `context` body field. Task 34 relies on it: the generator refuses a verb naming a header or body field the contract does not serve, so the SDK side goes first.
- **C3 — local helpers.** `.dforge/test-env.sh` exports `TEST_DATABASE_URL` (dev Postgres, `darkmem_test`) and `BENCH_DATABASE_URL`; `.dforge/gate-legs.sh` runs every gate leg except the F1 bench and prints `ALL LEGS OK`. Consumed by every task's checks.
- **C4 — API error message.** `frontend/src/lib/api.ts`: an `ApiError`'s `message` is the envelope's `error.message` when the body carries one, else the body's string `detail`, else `API error: <status>`; `ApiError.status` is the HTTP status. The same rule holds on the upload path. Produced by Task 24, consumed by Task 25 (Run now's 409 test reads `status`).
- **C5 — proof states.** `frontend/src/components/app-chrome/load-failure-states.stories.tsx` gains one story per failed Backups read (destinations, inventory, outcomes) (Task 25), and `frontend/src/features/activity/components/failed-captures-section.stories.tsx` gains a story with a requeue held pending (Task 27). Task 36 screenshots them.

## Assumptions (evidence)

- The riskiest assumption is that retrying savepoint B is safe and that the deadlock is reachable through the real code paths. PostgreSQL releases a lock taken after a savepoint when the savepoint is rolled back (https://www.postgresql.org/docs/17/explicit-locking.html), and today's handler already rolls back to the savepoint and commits savepoint A afterwards (`pipeline.py` `_write_memory`, the `except Exception` after the `begin_nested()` that opens with `delete_by_memory_id`, read 2026-11-23). Reachability is unverified — Task 1 verifies it: its reproduction must be red before the retry is written, and if it cannot be made red, row 254 is deferred as "cannot tell" and the retry is not built.
- `./scripts/gate.sh` answers `GATE BLOCKED` on this checkout because the F1 bench cache is missing (register row 228, the owner's; handoff 2026-11-23). The Integration check is therefore `.dforge/gate-legs.sh`, every leg but the F1 bench. The retrieval eval cannot run either, so row 355's re-run is register row 413, deferred.
- Task check rule 2: `.dforge/suites.tsv`'s last passing run of `bash .dforge/gate-legs.sh` took 266 s (commit `5ee451b`, read 2026-11-23).
- Alembic head is `0006_drop_blocks_search_vector` (`ls backend/migrations/versions`, 2026-11-23).
- The dev Postgres `darkmem-postgres-1` is up with `darkmem_test`, `darkmem_test_2..5` and `darkmem_bench`, and has no `darkmem_e2e` database (`docker exec … psql`, 2026-11-23); Task 21 creates it.
- Swap was at 7.2 of 8.0 GiB on 2026-11-23 07:44 +07 (`free -h`), so `earlyoom` kills are likely during full-suite runs.
- CI's e2e job already names `darkmem_e2e` explicitly (`.github/workflows/ci.yml`, `POSTGRES_DB` and both database URLs, read 2026-11-23), so Task 21's default change does not move CI.
- `@tanstack/react-router` (^1.168) exports `useBlocker` (`frontend/node_modules/@tanstack/react-router/dist/esm/index.d.ts`, 2026-11-23); nothing in `frontend/src` uses it yet. darkraise-ui ships `alert-dialog`, `banner` and `empty-state` (`dist/components/`, 2026-11-23).
- `axe-core` is installed and `frontend/tests/knowledge.spec.ts` already runs it (`rg axe frontend/tests`, 2026-11-23); Task 30 uses that check for row 381's unverified findings.
- happy-dom computes no layout and applies no stylesheet cascade, so A33's computed opacity is tested in Playwright (Task 29) and A31's resize through a stubbed `ResizeObserver`.
- Unverified — Task 7 verifies it: the source of row 269's SAWarning. Unverified — Task 20 verifies it: which test file leaves the `(postgresql, database)` entity (row 351). Unverified — Task 19 verifies it: whether `semantic_deferred_to` appears in the OpenAPI document. Unverified — Task 31 verifies it: whether `rawFetch` forwards a `signal`.
- `frontend/src/*.ts(x)` and `*.css` are UI files (`scripts/ui-proof paths`, 2026-11-23), so every task editing one carries a `**UI/UX:**` line; a task that changes nothing a user sees cites OP-4.
- Plan review round 1 (`dforge:judge-opus`, 2026-11-23) scored executability 13 and assumptions 13, borderline. Decision: no second round, since no score was 8 or below and no finding was Critical; all seven Important findings (Tasks 2, 3, 9, 15, 22 twice, 28) and the seven Minor ones were fixed in place.
- `age` is not on this host (`command -v age`, 2026-11-23); Task 22's restore-cycle tests stub it on `PATH`.
- Row ownership: the spec lists row 288 under WP6, but A3 tests it together with row 398's delete, so Task 2 closes it.

## Task index

1. Phase 5 deadlock reproduction and savepoint B retry
2. Memory delete strip and bounded source withdrawal
3. Deterministic ties in fusion and every memory arm
4. Hybrid-off embed outage and the memory context limit
5. wait_process session, outcome and attempt charge
6. Batch journal fallback, dead partial branch and fixture copy
7. Early-closed streams and the buffer test warning
8. Login refusal reason, one epoch key and CORS test setup
9. Session revocation reload and the renewed mark
10. MCP call log put-back and API key cache tests
11. Repository credentials and re-clone failure status
12. Deriver version and the code-lift stamp
13. Indexing skip digest, enrichment snapshot and graph tests
14. Fact lock taken NOWAIT in the lift
15. Refine prompt, bench isolation and vault prose
16. Board edits keep block vectors
17. Block verbs prune document revisions
18. Uploads, Notion import and page create
19. Session-scope scan, facts trace field and stale docstrings
20. Test isolation and document parser tests
21. E2e reset guard and its own database
22. Backup suspect pruning and restore-cycle bounds
23. CI workflow and layout budget tests
24. Provider key prompt and envelope error messages
25. Backups failed states and Run now status
26. Stopped-processing banner on Settings LLM
27. Failed-captures busy state and no inject log
28. Document editor caret and leave guard
29. Dark disabled controls, Mermaid copy and canvas resize
30. Review queue and chat row nesting
31. Abort signals and dead query keys
32. Canvas mirror arrays, dead helper, Storybook index and comments
33. Remove the SDK declareContext verb
34. Remove declared context from the search door
35. Remove the demo context chip and its design text
36. UI proof walkthrough
37. Close: gate legs, door counts and the register

---

### Task 1: Phase 5 deadlock reproduction and savepoint B retry

**Files:**
- Modify: `backend/app/services/pipeline.py` (`ProcessingPipeline._write_memory`, the savepoint B block)
- Modify: `CLAUDE.md` (Pipeline phases, the "Write" step)
- Test: `backend/tests/test_phase5_concurrency.py`

**Interfaces:**
- Consumes: none
- Produces: C1

**Items:** 254, 255, 256
**Depends on:** none
**Evaluation:** files 1 - spec 2 - coupling 2 - risk 3 = 8
**Lenses:** lang-python, silent-failures

- [ ] **Step 1: Write the failing test**

All in `backend/tests/test_phase5_concurrency.py`, using its `savepoint_bed` and event-pause pattern.

- `::test_swapped_prior_and_new_sets_both_commit` (integration, A1): seed memory A asserting only entity `phase5-zeta` and memory B asserting only `phase5-xi` through a first `_write_memory` each; then re-extract both concurrently with extraction `{phase5-xi, phase5-zeta}`, wrapping `PostgresGraphRepository.delete_by_memory_id` so each writer, after its own first strip returns, waits (2 s bound) until the other writer has stripped too. The barrier is one-shot per writer: a retried strip does not wait again. Asserts both statuses are `graph == "ok"`, both memories assert exactly `{phase5-xi, phase5-zeta}`, and no `pipeline_failures` row exists for either. Fails today because Postgres aborts one writer's savepoint B with SQLSTATE `40P01` and it reports `graph=error`.
- `::test_three_deadlocks_keep_the_vector_and_the_prior_graph` (integration, A2): seed a memory with a prior graph; re-extract it with `delete_by_memory_id` patched to raise `DBAPIError(…, orig=<object with sqlstate "40P01">)` on every call. Asserts `graph == "error"`, the status error contains `40P01`, the patched strip ran 3 times, the memory's vector row exists, the prior graph is intact, and the log holds exactly two WARNING records naming the memory id, with `attempt 1 of 3` and `attempt 2 of 3`. Fails today because savepoint B runs once.
- `::test_shared_relations_written_in_opposite_order_both_commit` (integration, *guard*, row 255): two writers whose relationships list two shared relations in opposite order, each pausing after its first `create_relationship`; asserts both `graph == "ok"` and both relation sets present. Passes today; Step 2 reverts the relation sort in `_write_memory` to see it red.
- Extend `::test_shared_entities_written_in_opposite_order_both_commit` (row 256): its `asyncio.wait_for` bound drops from 3 s to 0.5 s; asserts unchanged.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_phase5_concurrency.py`
Expected: the A1 and A2 tests FAIL; the guard fails only while the relation sort is reverted.

**Stop rule.** If after three honest attempts at the interleaving (moving the pause point between the strip and the first upsert, then between entity and relation upserts) A1 stays green, do not write the retry: set row 254 `deferred --note "cannot tell: the two-session reproduction could not force the strip-versus-upsert cycle; seat trace in lane-b1-report.md #254"`, keep the guard and the 0.5 s bound, commit those as `test(pipeline): pin Phase 5 relation order`, and close 255 and 256. Row 254's register state `deferred` is the record that C1 does not exist; Task 2 reads it.

- [ ] **Step 3: Implement**

1. In `_write_memory`, run the savepoint B block (the `async with session.begin_nested():` that opens with `graph_repo.delete_by_memory_id(memory_id)` and ends with `reconcile_memory_sources`) up to `DEADLOCK_ATTEMPTS` times. When the block raises and `_is_deadlock(exc)` holds with attempts left, log the C1 warning and run the whole block again, strip included. Read the SQLSTATE as `fact_lift._share_lock_memories` reads `_LOCK_NOT_AVAILABLE`, never from message text.
2. Any other exception, and the third deadlock, take today's `except Exception` path unchanged (`graph=error`, savepoint A kept); for a deadlock the status error reads `Graph write failed (SQLSTATE 40P01): <exc>`.
3. Fable cautions, both binding: the second attempt runs with `mem_record` (and every ORM object loaded before the savepoint) expired by the rollback, so the retried body may assign to it but must not read one of its attributes outside an awaited load — capture the values it needs before the first attempt or `await session.refresh(...)`; and a cycle through a lock taken in savepoint A (the memory row) is not released by rolling back savepoint B, so it ends at the third attempt as `graph=error`, as today.
4. `CLAUDE.md`, Pipeline phases, step 5: add after the strip bullet's first sentence: "When Postgres aborts savepoint B as a deadlock (SQLSTATE `40P01`) it is run again, strip included, up to three attempts in all; any other error, and a third deadlock, end as `graph=error` with savepoint A kept."

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 900 .venv/bin/python -m pytest -q tests/test_phase5_concurrency.py tests/test_pipeline_savepoints.py tests/test_supersession.py`
Expected: PASS, and `test_phase5_concurrency.py` finishes in under 10 s.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/pipeline.py backend/tests/test_phase5_concurrency.py CLAUDE.md
git commit -m "fix(pipeline): retry a deadlocked graph write"
```

### Task 2: Memory delete strip and bounded source withdrawal

**Files:**
- Modify: `backend/app/services/pipeline.py` (`ProcessingPipeline.delete_memory`)
- Modify: `backend/app/services/fact_provenance.py` (`withdraw_memory_sources`, `reconcile_memory_sources`)
- Test: the file that already tests `ProcessingPipeline.delete_memory` (`rg -l "\.delete_memory\(" backend/tests`), else create `backend/tests/test_memory_delete_cleanup.py`

**Interfaces:**
- Consumes: C1
- Produces: none

**Items:** 398, 288
**Depends on:** Task 1
**Evaluation:** files 1 - spec 2 - coupling 1 - risk 3 = 7
**Lenses:** silent-failures

- [ ] **Step 1: Write the failing test**

- `::test_a_delete_that_loses_one_deadlock_still_strips` (integration, A3): seed a memory with a vector, an entity it asserts and a `fact_sources` row; patch the graph strip to raise a `40P01` `DBAPIError` on its first call only; call `delete_memory`. Asserts the entity's `memory_ids` no longer holds the id, the vector row is gone, the `fact_sources` row is withdrawn, and the strip ran twice. Fails today because the exception rolls back the whole transaction and is swallowed.
- `::test_a_withdrawal_lock_timeout_keeps_the_strip` (integration, A3 and row 288): a second session holds the fact row `FOR UPDATE`; `WITHDRAWAL_LOCK_TIMEOUT` is patched to `200ms`; `delete_memory` returns within 5 s with the vector deleted and the graph strip committed, the `fact_sources` row still present (left to the hourly reap), and one WARNING record containing `55P03`. Fails today because the withdrawal waits on the lock without bound in the same transaction as the strip.
- `::test_withdrawal_restores_the_callers_lock_timeout` (integration, row 288): after `withdraw_memory_sources` on a session whose `lock_timeout` is `7s`, `current_setting('lock_timeout')` reads `7s` again.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q <the test file>`
Expected: FAIL on the first two tests.

- [ ] **Step 3: Implement**

1. `fact_provenance.py`: one helper (an async context manager) sets `WITHDRAWAL_LOCK_TIMEOUT` and puts the caller's previous value back afterwards; `reconcile_memory_sources` and `withdraw_memory_sources` both run `_withdraw` inside it. The `CAST(m.id AS text)` reap join is left as it is (row check: a uuid-side join can raise on a non-canonical ref).
2. `delete_memory`: the vector delete stays outside the savepoints; the graph strip runs in its own `begin_nested()` savepoint under the C1 retry; the fact-source withdrawal runs after it in a second savepoint. A failure in the second savepoint rolls back only the withdrawal and logs one WARNING with its SQLSTATE; the commit keeps the strip. A strip that exhausts its attempts logs the SQLSTATE and the delete still commits the vector delete (`graph_orphan_cleanup` heals the rest). No exception leaves `delete_memory`, as today. Correct the comment above the withdrawal that says it shares the strip's transaction.
3. The spec binds the two Fable cautions on the retry to this task too: a retried strip must not read an attribute of any ORM object loaded before its savepoint (the rollback expires it; capture values first or `await session.refresh(...)`), and a cycle through a lock taken outside the strip savepoint (here, the vector delete's rows) is not released by rolling it back, so it ends at the third attempt and is logged and healed as above.
4. If row 254 is `deferred` in the register (Task 1's stop rule: C1 does not exist), keep both savepoints and the lock bound, run the strip once, do not write A3's first test, and close row 398 with a Note saying its deadlock retry waits on row 254.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 900 .venv/bin/python -m pytest -q <the test file> tests/test_phase5_concurrency.py tests/test_fact_provenance*.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/pipeline.py backend/app/services/fact_provenance.py backend/tests
git commit -m "fix(pipeline): keep a memory delete's graph strip"
```

### Task 3: Deterministic ties in fusion and every memory arm

**Files:**
- Modify: `backend/app/services/rank_fusion.py` (`rrf_fuse`)
- Modify: `backend/app/services/hybrid_search.py` (keyword arm SQL, semantic arm, `_dual_level_search`, the hybrid-off branch, `apply_rank_fusion_factor`)
- Test: `backend/tests/test_rrf_fusion.py`, `backend/tests/test_hybrid_search.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 355
**Depends on:** none
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 2 = 6

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_rrf_fusion.py::test_equal_fused_scores_order_by_row_key` (unit, A4): two ranked lists that give rows `"b"` and `"a"` equal fused scores, fed in both input orders; asserts the output order is `["a", "b"]` both times. Fails today because ties keep insertion order.
- `backend/tests/test_hybrid_search.py::test_identical_memories_order_is_stable` (integration, A4), parametrized over `hybrid_search_enabled` true and false: two memories with identical content and fixed ids `00000000-0000-4000-8000-00000000000a` and `…000b`, inserted with the larger id first and, after a reset, with the smaller id first, so physical order and id order disagree in one case; five identical searches in each case all return `…000a` first. Fails today because tied rows follow the arms' physical order.
- `backend/tests/test_hybrid_search.py::test_rank_fusion_factor_orders_ties_by_id` (unit): rows with equal `rrf_score` and equal confidence come back ordered by id; with `preserve_order=True` the given order is returned untouched.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_rrf_fusion.py tests/test_hybrid_search.py`
Expected: FAIL on the three new tests.

- [ ] **Step 3: Implement**

1. `rrf_fuse` sorts by `(-rrf_score, str(key))`, so every RRF consumer (memory, code, work log, facts, articles) gets the tie-break once. Keys are compared as strings: hybrid search ids are strings and vector repository ids are `UUID` (the memory_id type drift invariant).
2. Keyword arm: `ORDER BY rank DESC, m.id`. Semantic arm, the inert dual-level channel and the hybrid-off branch (which reads `PostgresVectorRepository.search` directly): sort the fetched rows in Python by `(-score, str(memory_id))` after the fetch; never add a second SQL `ORDER BY` key to an HNSW query (it stops pgvector using the index).
3. `apply_rank_fusion_factor` sorts by `(-rrf_score, str(id))`; with `preserve_order=True` it still returns the rerank's order unsorted.
4. Tied rows change rank, so fused scores can move; the eval re-run is register row 413 (deferred). Say so in the commit body.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 900 .venv/bin/python -m pytest -q tests/test_rrf_fusion.py tests/test_hybrid_search.py tests/test_chat_retrieval_parity.py tests/test_code_search.py tests/test_layer_composition.py tests/test_dual_level_channel.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/rank_fusion.py backend/app/services/hybrid_search.py backend/tests
git commit -m "fix(search): break ranking ties by row id"
```

### Task 4: Hybrid-off embed outage and the memory context limit

**Files:**
- Modify: `backend/app/services/hybrid_search.py` (the hybrid-off, pure-vector branch)
- Modify: `backend/app/services/graph.py` (`GraphService.get_memory_context`, `_fetch_neighbor_memories`)
- Test: `backend/tests/test_hybrid_search_degradation.py`, `backend/tests/test_pushdown_keyword_graph.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 276, 400, 279
**Depends on:** Task 3
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 2 = 6

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_hybrid_search_degradation.py::test_hybrid_off_outage_dials_the_embedder_once` (integration, A5): `hybrid_search_enabled` false and an embedder whose embed raises; two searches in a row each raise; the embedder's embed was called exactly once across both. Fails today because the branch calls `self.llm.embed` directly and never sets or reads the cooldown.
- `::test_hybrid_off_shared_failed_embed_is_not_retried` (integration, row 276): a search passed an `embedded` result marked failed makes no embed call and raises. Fails today because the branch embeds again.
- `backend/tests/test_pushdown_keyword_graph.py::test_memory_context_fills_from_in_scope_neighbours` (integration, A6): a seed memory shares an entity with 25 neighbour memories whose 10 smallest ids are out of scope (5 in another project, 5 `deprecated`); `get_memory_context` returns exactly the 15 in-scope neighbours. Fails today because the 20 smallest ids are taken before the scope filter, leaving 10.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_hybrid_search_degradation.py tests/test_pushdown_keyword_graph.py`
Expected: FAIL on the three new tests.

- [ ] **Step 3: Implement**

1. The hybrid-off branch embeds through `embed_query`, the helper that starts the `EMBEDDER_RETRY_COOLDOWN_SECONDS` cooldown; a failed embed, a shared failed `embedded`, or an active cooldown raises at once without dialling again.
2. `get_memory_context` passes every neighbour id; `_fetch_neighbor_memories` applies the project and status scope, then `ORDER BY id LIMIT 20`, in SQL, binding the ids as one array parameter (`CAST(:ids AS uuid[])`).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 900 .venv/bin/python -m pytest -q tests/test_hybrid_search_degradation.py tests/test_pushdown_keyword_graph.py tests/test_hybrid_search.py tests/test_pushdown_remaining_channels.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/hybrid_search.py backend/app/services/graph.py backend/tests
git commit -m "fix(search): honour the embed cooldown with hybrid off"
```

### Task 5: wait_process session, outcome and attempt charge

**Files:**
- Modify: `backend/app/services/memory.py` (`MemoryService._drive_wait_process`)
- Modify: `backend/app/services/wait_process.py` (`drive`, the cap comments, the deadline release)
- Modify: `backend/app/services/buffer_flush.py` (`release_interrupted_claims`, only if the lone-row charge needs a parameter there)
- Modify: `CLAUDE.md` (Capture is buffered)
- Test: `backend/tests/test_wait_process.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 261, 262, 263, 264, 267, 399
**Depends on:** none
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 3 = 7
**Lenses:** silent-failures

- [ ] **Step 1: Write the failing test**

All in `backend/tests/test_wait_process.py`.

- `::test_no_pipeline_flush_never_uses_the_request_session` (integration, A8): a pipeline with no `session_factory`, the app's session factory replaced by a recording one, and a claim stalled past a deadline patched to 0.2 s; a REST capture with `wait_process=true` answers; afterwards no statement ran on the request's session, and the flush ran on a session from the recording factory. Fails today because the fallback is `as_session_factory(self.session)`.
- `::test_a_pipeline_flush_runs_on_its_own_session` (integration, *guard*, row 262): the pipeline's factory builds sessions over a separate `AsyncSession(test_engine)` and records them; the request session is never among them. Step 2 points the factory at the request session to see it red.
- `::test_a_raising_inline_flush_answers_the_ack_and_logs_once` (integration, A40): a flush whose claim raises `RuntimeError` makes the capture answer 202 with the `CaptureAck`, and the log holds exactly one ERROR record for it. Fails today because `task.result()` re-raises into the request and `_forget` logs it as well.
- `::test_a_lone_inline_row_cut_at_its_deadline_is_charged` (integration, A9): a one-row inline flush cut at its own deadline leaves the row `pending` with `attempts` 1. Fails today because the cut refunds.
- `::test_a_multi_row_cut_and_a_shutdown_cut_refund` (integration, A9): a batch capture's inline flush of three rows cut at its deadline leaves each `pending` with `attempts` 0; a one-row flush cut by app shutdown leaves `attempts` 0.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_wait_process.py`
Expected: FAIL on A8, A40 and the lone-row charge.

- [ ] **Step 3: Implement**

1. Row 261: with no pipeline factory the inline flush uses the app's `async_session_factory`, never the request session.
2. Row 264: `drive` catches the task's exception where it reads `task.result()` and answers the plain ack; `_forget` stays the one log line.
3. Row 399: a deadline cut of a lone row charges one attempt, as `buffer_flush`'s scheduled lone-row deadline path does; a cut of several rows, and any cut at shutdown, refund as today.
4. Row 263: the module docstring names `BUFFER_WAIT_TIMEOUT_SECONDS`, not the removed flag. Row 267: reword the comments above `MAX_CONTINUING_FLUSHES` to say the cap counts every `wait_process` flush in flight, inside or past its window.
5. `CLAUDE.md`, Capture is buffered: "either way with any row it still holds returned to `pending`" becomes "either way with any row it still holds returned to `pending` (a lone row cut at that deadline is charged an attempt, as the scheduled lone-row path is; a cut of several rows, or at shutdown, refunds it)"; "While eight such flushes are running" becomes "While eight `wait_process` flushes are in flight".

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 900 .venv/bin/python -m pytest -q tests/test_wait_process.py tests/test_memory_buffer.py tests/test_buffer_flush*.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services backend/tests/test_wait_process.py CLAUDE.md
git commit -m "fix(capture): own session and charge for inline flush"
```

### Task 6: Batch journal fallback, dead partial branch and fixture copy

**Files:**
- Modify: `backend/app/services/pipeline.py` (the same-batch reconciliation's `except`)
- Modify: `backend/app/services/pipeline_failures.py` (`derive_memory_failed_step`)
- Test: `backend/tests/test_supersession.py`, `backend/tests/unit/test_pipeline_failures_helpers.py`, `backend/tests/test_pipeline_savepoints.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 259, 260, 285
**Depends on:** Task 1
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 2 = 6

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_supersession.py::test_a_failed_reconciliation_keeps_the_extracted_journal` (integration, A7): a two-memory batch whose reconciliation session's read raises; afterwards each batch member has exactly one `extracted` event. Fails today because the events were written in the failed session.
- `backend/tests/test_pipeline_savepoints.py::test_the_shared_extraction_is_unchanged_by_a_run` (integration, row 285): a run whose fake embedder gives `pgvector` and `faiss` the same vector (so Phase 4 canonicalises one onto the other), run twice; afterwards the module-level `EXTRACTION` equals a `copy.deepcopy` taken at import and `EXTRACTION["entities"][0]["name"] == "Pgvector"`. Fails today because `dict(...)` shares the nested lists.
- Row 259 is dead code: drop the `partial` case from `backend/tests/unit/test_pipeline_failures_helpers.py`; no new test.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_supersession.py tests/test_pipeline_savepoints.py`
Expected: FAIL on the two new tests.

- [ ] **Step 3: Implement**

1. Row 260: in the reconciliation's `except`, open a fresh `self.session_factory()` session, record each batch member's `extracted` event with its updated status and commit; a failure there logs and goes on.
2. Row 285: `copy.deepcopy` replaces `dict(...)` everywhere `test_pipeline_savepoints.py` copies `EXTRACTION`, including the `_ExtractionLLM(EXTRACTION)` argument.
3. Row 259: delete the `extract == "partial"` branch and its docstring lines in `derive_memory_failed_step`; keep the SPA's `extraction_partial` label for stored rows.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 900 .venv/bin/python -m pytest -q tests/test_supersession.py tests/test_pipeline_savepoints.py tests/unit/test_pipeline_failures_helpers.py tests/test_pipeline_failures*.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services backend/tests
git commit -m "fix(pipeline): journal a batch whose reconcile fails"
```

### Task 7: Early-closed streams and the buffer test warning

**Files:**
- Modify: `backend/app/services/llm.py` (the streaming generator's handlers)
- Modify: the file Step 1 names as the SAWarning's source
- Test: `backend/tests/test_chat_stream_resources.py`, `backend/tests/test_memory_buffer.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 275, 269
**Depends on:** none
**Evaluation:** files 1 - spec 2 - coupling 0 - risk 1 = 4

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_chat_stream_resources.py::test_a_stream_closed_early_records_not_ok` (integration, A41): drive the streaming generator one chunk and `aclose()` it; the `llm_usage` row has `ok` false and `error_kind` `"closed"`. Fails today because `GeneratorExit` is a `BaseException` and the `finally` records `ok=True`.
- Row 269: run `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_memory_buffer.py -W error::sqlalchemy.exc.SAWarning`. The failing test names the source. If nothing fails, close row 269 `not reproduced` with that command's output and leave the file alone.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_chat_stream_resources.py`
Expected: FAIL on the new test.

- [ ] **Step 3: Implement**

1. Row 275: catch `GeneratorExit` beside the `CancelledError` handler, set `ok, error_kind = False, "closed"`, and re-raise.
2. Row 269: fix the located source (the row check suspects `test_status_is_check_constrained` rolling back the fixture session); the fix stays in tests unless the warning comes from app code.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_chat_stream_resources.py tests/test_memory_buffer.py -W error::sqlalchemy.exc.SAWarning`
Expected: PASS with no SAWarning.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/llm.py backend/tests
git commit -m "fix(llm): record an early-closed stream as failed"
```

### Task 8: Login refusal reason, one epoch key and CORS test setup

**Files:**
- Modify: `backend/app/services/login_rate_limit.py` (`acquire`)
- Modify: `backend/app/api/routes/auth.py` (the login refusal detail, the `PASSWORD_CHANGED_AT_KEY` definition)
- Modify: `backend/app/api/auth.py` (keeps the one definition)
- Test: `backend/tests/test_login_rate_limit_route.py`, `backend/tests/test_cors_fallback.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 237, 394, 238, 397
**Depends on:** none
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 2 = 6

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_login_rate_limit_route.py::test_in_flight_saturation_says_in_progress` (integration, A10): five logins held in flight (bcrypt verification patched to wait on an event) with no prior failures; a sixth answers 429 whose detail matches `Too many login attempts in progress; retry in \d+s` and contains no `failed login attempts`. Fails today because every refusal says "Too many failed login attempts".
- `::test_failures_still_say_failed` (integration): after five failed logins the next refusal's detail starts `Too many failed login attempts; retry in`.
- Row 394: no test; Step 4's `rg` check proves one definition.
- Rows 238 and 397 change the test itself: `test_cors_fallback.py`'s first test sets `allow_origins` to `[]` on the CORS middleware entry and resets `app.middleware_stack`, as `test_configured_origin_is_still_allowed` does, and the mid-test `monkeypatch.undo()` is replaced by a `pytest.MonkeyPatch.context()` block, so the autouse conftest patches stay in force.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_login_rate_limit_route.py`
Expected: FAIL on the in-flight test.

- [ ] **Step 3: Implement**

1. `acquire` reports which gate refused alongside the seconds (in-flight saturation or failures); the login route words the in-flight case "Too many login attempts in progress; retry in {n}s" and keeps today's wording for failures.
2. `routes/auth.py` imports `PASSWORD_CHANGED_AT_KEY` from `app.api.auth` instead of defining it.
3. Apply the two `test_cors_fallback.py` changes.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_login_rate_limit_route.py tests/test_cors_fallback.py tests/test_login_rate_limit*.py tests/test_auth*.py && rg -n "PASSWORD_CHANGED_AT_KEY =" app`
Expected: PASS, and `rg` prints exactly one line, in `app/api/auth.py`.

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests
git commit -m "fix(auth): name the gate that refused a login"
```

### Task 9: Session revocation reload and the renewed mark

**Files:**
- Modify: `backend/app/api/websocket.py` (`SessionRevocations`, the socket loop)
- Modify: `backend/app/api/routes/auth.py` (refresh and change-password around `close_renewed_sockets`)
- Modify: `CLAUDE.md` (Setup, auth, runtime config: the in-process copy sentence)
- Test: `backend/tests/test_websocket.py`, `backend/scripts/e2e/tests/test_session_rotation.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 331, 371, 370, 368
**Depends on:** Task 8
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 3 = 7
**Lenses:** security, silent-failures

- [ ] **Step 1: Write the failing test**

All in `backend/tests/test_websocket.py` unless named.

- `::test_an_out_of_band_revocation_closes_the_socket_after_reload` (integration, A11): open a socket, insert a `token_blocklist` row for its token through a fresh session (no auth route), advance the reload clock past 60 s (patch `app.api.websocket._now`, the module-level `time.monotonic` alias Step 3 adds); the socket closes with reason `Session expired or revoked`, with no restart. Fails today because the copy is loaded once per process.
- `::test_reload_is_single_flight_merges_and_survives_a_failed_read` (integration, row 331): with a stale copy, twenty concurrent `refresh_if_stale()` calls run one database read; a revocation recorded in memory during that read survives it; a read that raises keeps the copy, and two consecutive failures log one WARNING.
- `::test_a_cancelled_refresh_forgets_the_renewed_mark` (integration, A12): hold `_send_lock`, start `POST /api/v1/auth/refresh`, cancel it while it waits to close sockets; the presented token's jti is not in `session_revocations._renewed`. Fails today because the `try` that calls `forget_renewed` starts after `close_renewed_sockets`.
- Row 370 changes the test itself: `_shut(renewed_task)` moves into the `finally` (with `renewed_task` initialised to `None` and guarded).
- Row 368 changes the e2e test itself: in `backend/scripts/e2e/tests/test_session_rotation.py` the `try` opens before the change-password call, and the `finally` restores the password only when that change answered 200.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_websocket.py`
Expected: FAIL on A11 and A12.

- [ ] **Step 3: Implement**

1. `SessionRevocations` replaces `_loaded` with the time of its last read, taken from a module-level `_now = time.monotonic`; `async refresh_if_stale(session_factory) -> None` (single-flight: concurrent callers await one in-flight read, through the existing `_lock`; the socket loop passes `async_session_factory`, as its `load` call does today) re-reads the blocklist and the password epoch when the copy is older than 60 seconds, merging into the copy (`load` already merges with `setdefault` and `set_epoch` takes the maximum) and never replacing it; a failed read keeps the copy and logs once until a read succeeds. The socket loop calls it before each revalidation. One comment states it relies on the single worker. Correct the class docstring's claim that the auth routes are the only writers.
2. In both routes, start the `try` before `close_renewed_sockets`, so a cancellation or error there reaches `forget_renewed`.
3. `CLAUDE.md`: "that logout, refresh and change-password update after their commit, so an idle socket costs no query" becomes "that logout, refresh and change-password update after their commit and that is re-read from the database once it is 60 seconds old (one query a minute per process), so a revocation written outside the app reaches open sockets within a minute".
4. Apply the two test-file changes. The e2e change is checked by `cd backend && timeout 900 .venv/bin/python scripts/e2e/run_e2e.py`; exit 2 (`BLOCKED`, no extraction model on the LAN endpoint) is a missing toolchain, not a red test — then check it with `.venv/bin/python -m py_compile scripts/e2e/tests/test_session_rotation.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 900 .venv/bin/python -m pytest -q tests/test_websocket.py tests/test_auth*.py tests/test_login_rate_limit_route.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api backend/tests/test_websocket.py backend/scripts/e2e/tests/test_session_rotation.py CLAUDE.md
git commit -m "fix(ws): re-read session revocations each minute"
```

### Task 10: MCP call log put-back and API key cache tests

**Files:**
- Modify: `backend/app/services/mcp_call_log.py` (`flush_once`, the outage classifier)
- Test: `backend/tests/test_mcp_call_log_flush.py`, `backend/tests/test_api_key_cache.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 392, 393, 241, 242
**Depends on:** none
**Evaluation:** files 1 - spec 2 - coupling 0 - risk 2 = 5

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_mcp_call_log_flush.py::test_a_pool_timeout_puts_the_batch_back` (integration, A13): the INSERT raises `sqlalchemy.exc.TimeoutError`; afterwards the whole batch is back in the buffer, a backoff is set, and the dropped count is unchanged. Fails today because the row-by-row pass drops the batch.
- `::test_a_cancelled_flush_puts_the_batch_back` (integration, A13): cancel `flush_once` while its INSERT is awaiting; `CancelledError` propagates and the popped batch is back in the buffer, uncounted as dropped. Fails today because the batch is popped before the `try` and `except Exception` misses the cancellation.
- Rows 241 and 242 change the tests themselves: an autouse fixture in `test_api_key_cache.py` clears `api_keys._verified`, `_revoked_ids` and `_last_marked` before and after each test; the expired-key test patches the clock `authenticate` reads, calls `/mcp/` at the later time, and asserts 401.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_mcp_call_log_flush.py`
Expected: FAIL on both new tests.

- [ ] **Step 3: Implement**

1. The outage classifier counts `sqlalchemy.exc.TimeoutError` as an outage, so the batch is put back with backoff.
2. `flush_once` puts its popped batch back on `CancelledError` (then re-raises) as it does on an outage.
3. Apply the two test-file changes.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_mcp_call_log_flush.py tests/test_api_key_cache.py tests/test_mcp_call_log*.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/mcp_call_log.py backend/tests
git commit -m "fix(mcp): keep call-log batches on timeout or cancel"
```

### Task 11: Repository credentials and re-clone failure status

**Files:**
- Modify: `backend/app/services/code_pipeline.py` (the four failure-path log lines)
- Modify: `backend/app/services/repo_manager.py` (`_auth_env` and its callers, `_reclone`)
- Test: `backend/tests/test_repo_lifecycle_journal.py`, `backend/tests/test_repos.py`, `backend/tests/test_repo_fetch_safety.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 244, 245, 246, 300, 301
**Depends on:** none
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 3 = 7
**Lenses:** security

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_repo_lifecycle_journal.py::test_a_credentialed_failure_never_logs_the_token` (integration, A14): after one good index, a run that raises `RuntimeError("https://u:tok@host/r.git")` writes `tok` to no `caplog` record. Fails today because the stale-graph warning and three other lines log the raw exception.
- `backend/tests/test_repos.py::test_a_background_failure_is_sanitised` (integration, A14, *guard*, row 246): the spawned `CodePipeline.run` raises an error carrying URL userinfo; neither the `repo.indexing_failed` broadcast payload, the repository row's `status_message` nor any log record contains the secret. Step 2 removes the route's `_sanitize_url` call to see it red.
- `backend/tests/test_repos.py::test_the_auth_header_is_scoped_to_the_origin` (unit, A15), parametrized: `https://git.lan:8443/o/r.git` configures the header under `http.https://git.lan:8443/.extraHeader`; `https://github.com/o/r.git` under `http.https://github.com/.extraHeader`; `https://u:p@git.lan:8443/o/r.git` under a key with no userinfo; and no `GIT_CONFIG_KEY_<n>` equals `http.extraHeader`. Fails today because the key is unscoped.
- Extend `backend/tests/test_repo_fetch_safety.py::test_a_failed_reclone_releases_its_claim` (A16): it now asserts status `error`, a `status_message` with no userinfo, and the claim released. Fails today because the prior status `ready` is restored.
- `backend/tests/test_repo_fetch_safety.py::test_a_cancelled_reclone_restores_its_prior_status` (integration, A16, *guard*, row 300): `_clone_repo` awaits an event; the task is cancelled; the status is the prior one, not `cloning`. Step 2 moves the restore out of the `finally` to see it red.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_repo_lifecycle_journal.py tests/test_repos.py tests/test_repo_fetch_safety.py`
Expected: FAIL on rows 244, 245 and 301's tests.

- [ ] **Step 3: Implement**

1. Row 244: every failure-path log line in `code_pipeline.py` writes `cause` or `_sanitize_url(str(exc))`, never the raw exception.
2. Row 245: `_auth_env` takes the repository URL and keys the header `http.<scheme>://<host>[:<port>]/.extraHeader`, built from the URL with its userinfo removed and its port kept when it names one, so a git-lfs or submodule fetch to another host carries no token.
3. Row 301: when `_replace_clone` raises (not a cancellation), `_reclone` writes `status='error'` with the sanitised message in place of the prior status; cancellation and success restore the prior status as today; both release the claim.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 900 .venv/bin/python -m pytest -q tests/test_repo_lifecycle_journal.py tests/test_repos.py tests/test_repo_fetch_safety.py tests/test_repo*.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services backend/tests
git commit -m "fix(repos): scope git auth and redact failure logs"
```

### Task 12: Deriver version and the code-lift stamp

**Files:**
- Modify: `backend/app/services/code_deriver_job.py` (add `CODE_DERIVER_VERSION`)
- Modify: `backend/app/services/job_runners.py` (the `code_deriver` runner's skip and stamp)
- Modify: `backend/app/services/fact_lift.py` (`_code_graph_stamp`)
- Modify: `backend/app/services/repo_manager.py` (`RepoManager.delete`)
- Test: `backend/tests/test_code_deriver.py`, `backend/tests/test_deriver_lift.py`, `backend/tests/test_repo_lifecycle_journal.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 304, 308
**Depends on:** Task 11
**Evaluation:** files 3 - spec 2 - coupling 0 - risk 2 = 7

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_code_deriver.py::test_a_raised_deriver_version_rederives_an_unmoved_head` (integration, A17): a repository whose `code_deriver_state` entry is `{"head": <its last_indexed_commit>, "version": CODE_DERIVER_VERSION - 1}` is derived by the next run (`assert_repo_graph` called once) and its entry then carries the current version; a second run skips it; a legacy bare-string entry also re-derives once. Fails today because the stamp holds the head alone.
- `backend/tests/test_deriver_lift.py::test_an_idle_deriver_tick_triggers_no_code_reconcile` (integration, A17): `run_code_lift` twice around a `code_deriver` tick that derived nothing; `reconcile_code_sources` ran once. Fails today because the stamp hashes the newest `job_runs` id, which every tick moves.
- `backend/tests/test_repo_lifecycle_journal.py::test_deleting_a_repo_drops_its_deriver_state_key` (integration, row 308): after `RepoManager.delete`, the `code_deriver_state` row has no key for that repository. Fails today.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_code_deriver.py tests/test_deriver_lift.py tests/test_repo_lifecycle_journal.py`
Expected: FAIL on the three new tests. The file's job-roster test (derived from `app/main.py`'s AST) stays green: this task registers no job.

- [ ] **Step 3: Implement**

1. `CODE_DERIVER_VERSION = 1` in `code_deriver_job.py`. The runner stores each repository's entry as `{"head": <sha>, "version": CODE_DERIVER_VERSION}` and skips only an entry whose head equals `last_indexed_commit` and whose version equals the constant; any other shape, including today's bare string, reads as stale (each repository re-derives once after the deploy).
2. `_code_graph_stamp` hashes the `code_deriver_state` value instead of the newest job-run id, so a tick that derived nothing reconciles nothing.
3. `RepoManager.delete` removes the repository's key from `code_deriver_state` (jsonb `-`) in the same transaction as the row delete.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 900 .venv/bin/python -m pytest -q tests/test_code_deriver.py tests/test_deriver_lift.py tests/test_repo_lifecycle_journal.py tests/test_job*.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services backend/tests
git commit -m "fix(code): re-derive on a deriver version change"
```

Leave row 308 open; Task 13 closes it.

### Task 13: Indexing skip digest, enrichment snapshot and graph tests

**Files:**
- Modify: `backend/app/services/code_pipeline.py` (`_CALL_GRAPH_DIGEST_SQL`, `_snapshot_symbol_enrichment`)
- Modify: `backend/app/services/index_debt.py` (module docstring)
- Test: `backend/tests/test_code_graph_keys.py`, `backend/tests/test_code_index_cost.py`; docstrings in `backend/tests/test_incremental_dependents.py` and `backend/tests/test_summary_carryover.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 401, 308, 404, 302
**Depends on:** Task 12
**Evaluation:** files 3 - spec 2 - coupling 0 - risk 2 = 7

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_code_graph_keys.py::test_reordering_functions_reruns_the_process_tracer` (integration, row 401): swapping the order of two functions in a route file, with no call or visibility change, reruns the process tracer and its entry points follow the new order; adding a comment line above every function (ranks unchanged) does not rerun it. Fails today because the digest omits position.
- Extend `backend/tests/test_code_graph_keys.py::test_community_keys_are_stable_across_runs` (row 404): spy on `partition_graph`'s raw membership before and after `a0.py` is added and assert at least one raw community id changed, before the existing stability assertions. Fails if adding `a0.py` stops renumbering.
- `backend/tests/test_code_index_cost.py::test_the_enrichment_snapshot_is_one_read` (integration, row 308): an incremental run rewriting three files issues exactly one snapshot SELECT. Fails today with three.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_code_graph_keys.py tests/test_code_index_cost.py`
Expected: FAIL on rows 401 and 308's tests; row 404's extension passes if Leiden renumbers (it pins the premise).

- [ ] **Step 3: Implement**

1. Row 401: the digest hashes each function's rank by `line_start` within its file (a `row_number()` over `properties->>'line_start'` per file), never the raw line.
2. Row 308: `_snapshot_symbol_enrichment` reads every rewritten file's symbols in one `WHERE file_id = ANY(...)` query, grouped by file.
3. Row 302: `_delete_file_data` becomes `_delete_files_data` in `index_debt.py`'s docstring and the two test docstrings.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 900 .venv/bin/python -m pytest -q tests/test_code_graph_keys.py tests/test_code_index_cost.py tests/test_incremental_dependents.py tests/test_summary_carryover.py tests/test_code_*.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services backend/tests
git commit -m "fix(code): rerun tracing when entry order moves"
```

### Task 14: Fact lock taken NOWAIT in the lift

**Files:**
- Modify: `backend/app/services/fact_lift.py` (`_OPEN_FACT`, `_open_fact_id`, the deferral path)
- Test: `backend/tests/test_fact_lift_interleave.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 286
**Depends on:** Task 12
**Evaluation:** files 1 - spec 2 - coupling 0 - risk 3 = 6
**Lenses:** silent-failures

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_fact_lift_interleave.py::test_a_held_fact_lock_defers_the_candidate` (integration, A18): a second session holds the candidate's `knowledge_triples` row `FOR UPDATE` past the lift's lock deadline (patched short); `run_lift` returns within the deadline plus 2 s with `outcome.deferred == 1`, the "fact lifting deferred" INFO record, and no record at ERROR or above. Fails today because `_OPEN_FACT` blocks on the lock.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_fact_lift_interleave.py`
Expected: FAIL (the lift waits for the holder).

- [ ] **Step 3: Implement**

`_OPEN_FACT` takes its lock `FOR UPDATE NOWAIT` inside the same retry-until-deadline loop as `_share_lock_memories` (`55P03` retried after `_MEMORY_LOCK_POLL_SECONDS`); at the deadline it raises a deferral the lift already counts as `deferred` (reuse `MemoriesBusy` or a sibling the same `except` catches).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 900 .venv/bin/python -m pytest -q tests/test_fact_lift_interleave.py tests/test_fact_lift*.py tests/test_deriver_lift.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/fact_lift.py backend/tests/test_fact_lift_interleave.py
git commit -m "fix(facts): defer a lift that meets a held fact"
```

### Task 15: Refine prompt, bench isolation and vault prose

**Files:**
- Modify: `backend/app/services/memory_dream.py` (`build_refine_messages`)
- Modify: `backend/scripts/benchlib/tests/conftest.py`
- Modify: `backend/app/services/verification_recompute.py` (`run_recompute` docstring), `backend/app/services/contradiction_scan.py` (one comment line)
- Modify: `backend/scripts/restore_refine_project_tags.py` (shebang, usage lines)
- Test: `backend/tests/test_memory_dream.py`, `backend/scripts/benchlib/tests/test_xdist_refusal.py` (create); comment and docstring edits in `backend/tests/test_deriver_lift.py`, `backend/tests/test_restore_refine_project_tags.py`, `backend/tests/test_claim_serving_gates.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 296, 297, 289, 291, 294, 295, 298, 412
**Depends on:** none
**Evaluation:** files 3 - spec 2 - coupling 0 - risk 1 = 6

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_memory_dream.py::test_the_refine_prompt_carries_no_tags` (unit, row 296): for a memory tagged `project/x` and `secret-tag`, no message `build_refine_messages` returns contains `CURRENT TAGS`, `project/x` or `secret-tag`. Fails today.
- `backend/scripts/benchlib/tests/test_xdist_refusal.py::test_an_xdist_run_is_refused` (integration, row 297): a subprocess `.venv/bin/python -m pytest scripts/benchlib/tests/test_xdist_refusal.py -n 2 -q -k nothing` (with an env marker that stops recursion) exits non-zero and its output contains `.venv/bin/python -m pytest scripts/benchlib/tests -q`. Fails today because the conftest runs under xdist.
- Rows 289, 291, 294, 295, 298 and 412 are prose: no test.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_memory_dream.py; timeout 600 .venv/bin/python -m pytest -q scripts/benchlib/tests/test_xdist_refusal.py`
Expected: FAIL on both new tests.

- [ ] **Step 3: Implement**

1. Row 296: remove the tags line and the `CURRENT TAGS` block from `build_refine_messages`. The refine prompt changes, so any test pinning its text moves with it, and any harness cache keyed on it misses (no bench re-run here).
2. Row 297: the benchlib conftest refuses in the controller, from `pytest_configure`, when `config.getoption("numprocesses", None)` is set and the process is not a worker (`not hasattr(config, "workerinput")`), through `pytest.exit(<message>, returncode=4)` naming the serial command `.venv/bin/python -m pytest scripts/benchlib/tests -q` (the bench database is one fixture set loaded once; the gate and CI run it serially). Refusing in the controller keeps the message in the run's own output.
3. Row 289: drop "matching ``run_lift``'s contract" from `run_recompute`'s docstring. Row 291: the docstring of `test_a_suspected_contradiction_does_not_withhold_the_born_rung` names the deterministic veto (`open_contradiction=True`) as the veto consult. Row 294: delete the dead `DATABASE_URL` setenv in `test_restore_refine_project_tags.py`. Row 295: the script's shebang becomes `#!/usr/bin/env python3` and its usage lines say `.venv/bin/python`. Row 298: the `AGGREGATES_NAMING_THE_RUNG` comment says the consumer is the synthesis selection path, which renders no count. Row 412: wrap the overlong producer-list comment line in `contradiction_scan.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 900 .venv/bin/python -m pytest -q tests/test_memory_dream.py tests/test_memory_dream_residue.py tests/test_deriver_lift.py tests/test_restore_refine_project_tags.py tests/test_claim_serving_gates.py && timeout 900 .venv/bin/python -m pytest -q scripts/benchlib/tests`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services backend/scripts backend/tests
git commit -m "fix(dream): drop tags from the refine prompt"
```

### Task 16: Board edits keep block vectors

**Files:**
- Modify: `backend/app/services/document_door.py` (`put_document`, the `embed_inline=False` path)
- Modify: `backend/app/services/block_embeddings.py` (a read of the non-retired fingerprints holding a document's vectors, if none exists)
- Modify: `CLAUDE.md` (Documents: the `embed_inline=False` bullet)
- Test: `backend/tests/test_board_edit.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 315
**Depends on:** none
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 2 = 6

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_board_edit.py::test_a_register_edit_keeps_unchanged_block_vectors` (integration, A19): a register document whose blocks hold vectors under two registered, non-retired fingerprints (vectors inserted directly); a board row edit filed with no orchestrator; afterwards every block whose text did not change has its vector under each of the two fingerprints, the edited row's block has none, and no embed call was made (the `llm` is `None`). Fails today because no fingerprint is resolved without an embedder, so nothing is carried.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_board_edit.py`
Expected: FAIL on the new test.

- [ ] **Step 3: Implement**

1. With `embed_inline=False`, `put_document` carries unchanged blocks' vectors under every fingerprint with `retired_at IS NULL` whose `block_embeddings` partition holds a vector for the document, through `carry_document_vectors` (it already takes the fingerprint), with no embed call; the newest fingerprint alone may not be the one search reads.
2. `CLAUDE.md`, the `embed_inline=False` bullet: after "embeds nothing," add "carries unchanged blocks' vectors under every non-retired fingerprint that holds vectors for the document,".

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 900 .venv/bin/python -m pytest -q tests/test_board_edit.py tests/test_block_pipeline.py tests/test_block_retrieval.py tests/test_document_*.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services CLAUDE.md backend/tests/test_board_edit.py
git commit -m "fix(board): carry block vectors across an edit"
```

### Task 17: Block verbs prune document revisions

**Files:**
- Modify: `backend/app/services/block_verbs.py` (each verb's write pass for a document owner)
- Modify: `backend/app/services/document_ingest.py` (the prune helper reachable from the verbs; `__all__` gains `REVISIONS_PRUNED_EVENT`)
- Modify: `CLAUDE.md` (Documents: the Retention sentence and the wrap of the journal Retention paragraph)
- Test: `backend/tests/test_document_revisions.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 324, 322, 323
**Depends on:** Task 16
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 3 = 7
**Lenses:** silent-failures

- [ ] **Step 1: Write the failing test**

All in `backend/tests/test_document_revisions.py`.

- `::test_a_block_verb_prunes_expired_revisions` (integration, A39): a converted document holding 60 revisions, 10 of them past its newest 50 and older than 90 days (`created_at` backdated); one `block_update` deletes exactly those 10, leaves 50, and journals one `document_revisions_pruned` row whose payload count is 10 and holds no content. Fails today because only a content filing prunes.
- `::test_a_block_verb_prune_without_its_journal_row_is_skipped` (integration): with `record_event` patched to return `False`, the verb succeeds and all 60 revisions remain.
- `::test_a_page_block_verb_prunes_nothing` (integration): a page block verb runs no revision prune and journals no `document_revisions_pruned` row.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_document_revisions.py`
Expected: FAIL on the first test.

- [ ] **Step 3: Implement**

1. A block verb on a document runs the filing's revision prune inside its savepoint, by the same rule (`REVISION_KEEP_NEWEST`, `REVISION_KEEP_DAYS`) and the same count-only journal row, skipped when that row does not land; a failed delete refuses the verb, as it refuses a put. Page owners never prune.
2. Row 322: add `"REVISIONS_PRUNED_EVENT"` to `document_ingest.__all__`.
3. Rows 324 and 323, `CLAUDE.md`, Revisions bullet: "a filing that writes a revision first deletes the document's earlier revisions…" gains ", and each block verb on a document runs the same prune" after the 50-and-90-day clause. Re-wrap the Events journal Retention paragraph whose line runs past the wrap ("…younger than 90 days stay). Pasted secrets go through").

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 900 .venv/bin/python -m pytest -q tests/test_document_revisions.py tests/test_block_verbs*.py tests/test_document_*.py tests/test_events.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services CLAUDE.md backend/tests/test_document_revisions.py
git commit -m "fix(documents): prune revisions on block edits"
```

### Task 18: Uploads, Notion import and page create

**Files:**
- Modify: `backend/app/api/routes/page_attachments.py` (upload route)
- Modify: `backend/app/services/page_attachments.py` (remove `store_upload`; `insert_attachment_row` docstring)
- Modify: `backend/app/services/page_import.py` (`_withdraw_attachments`)
- Modify: `backend/app/services/page_door.py` (`create_page`)
- Test: `backend/tests/test_page_attachments.py`, `backend/tests/test_page_import.py`, `backend/tests/test_page_door.py`, `backend/tests/test_document_attachment_concurrency.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 319, 321, 325, 317, 320, 316
**Depends on:** none
**Evaluation:** files 3 - spec 2 - coupling 0 - risk 2 = 7

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_page_attachments.py::test_an_upload_whose_part_was_collected_answers_408` (integration, A20): the staged `.part` is deleted between stage and place; the upload answers 408 with `error.code` `request_timeout`. Fails today with 500.
- `backend/tests/test_page_import.py::test_a_failed_withdrawal_rollback_keeps_the_import_error` (integration, row 321): an import failing with `NotionExportInvalid` whose withdrawal's execute and rollback both raise; the caller receives `NotionExportInvalid`. Fails today because the rollback's error replaces it.
- `backend/tests/test_page_door.py::test_create_page_checks_reproduction_off_the_loop` (unit, row 325): with `reproduces_source` wrapped to record `threading.current_thread()`, a `create_page` call runs it on a thread other than the event loop's. Fails today.
- Rows 317, 320 and 316 change no behaviour: no new test. Row 316 changes the two concurrency tests themselves: each `await asyncio.sleep(0.2)` after `run_cleanup` starts becomes a poll of `pg_locks` (advisory, `granted = false`, `mode = 'ExclusiveLock'`) bounded at 5 s.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_page_attachments.py tests/test_page_import.py tests/test_page_door.py`
Expected: FAIL on the three new tests.

- [ ] **Step 3: Implement**

1. Row 319: the upload route catches `FileNotFoundError` from `place_upload` and answers 408, `error.code` `request_timeout`, message "The upload stalled past the cleanup window; send it again."
2. Row 321: the rollback in `_withdraw_attachments`' `except` is guarded by its own `try/except Exception` that logs.
3. Row 325: `split_frontmatter` and `reproduces_source` run inside the same `asyncio.to_thread` call as the parse.
4. Row 317 (rule 6): `rg -n "store_upload" backend` shows only tests; move those callers to `stage_upload` + `place_upload` and delete `store_upload`. Row 320: `insert_attachment_row`'s docstring says an import commits each attachment row in a transaction of its own before writing its pages. Row 316: the `pg_locks` poll above.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 900 .venv/bin/python -m pytest -q tests/test_page_attachments.py tests/test_page_import.py tests/test_page_door.py tests/test_document_attachment_concurrency.py tests/test_page_*.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests
git commit -m "fix(pages): answer 408 for a collected upload"
```

### Task 19: Session-scope scan, facts trace field and stale docstrings

**Files:**
- Modify: `backend/app/services/facts_channel.py` (remove `SEMANTIC_ARM_OWNER` and `FactChannelTrace.semantic_deferred_to`)
- Modify: `backend/app/services/embedder_registry.py`, `backend/app/services/block_embeddings.py` (module docstrings)
- Modify: `backend/app/services/dream_undo.py`, `backend/app/services/buffer_flush.py`, `backend/app/api/routes/repos.py` (docstrings)
- Test: `backend/tests/test_session_scope.py`, `backend/tests/test_facts_channel.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 345, 347, 346, 348, 402, 327, 328, 329
**Depends on:** none
**Evaluation:** files 3 - spec 2 - coupling 0 - risk 1 = 6

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_session_scope.py::test_a_helper_built_stream_must_declare_itself` (unit, row 327): a fixture module holding a route whose same-module helper builds a `StreamingResponse` and whose endpoint has no `StreamingResponse` return annotation; the scan's undeclared-stream check reports that route by path. Fails today because detection is a text match on the endpoint's own source.
- Row 328 changes the test itself: keep the `checked` floor and add one comment saying it guards against a vacuous pass when route resolution breaks.
- Rows 345 and 347 remove a field no app code reads: first run `cd backend && . ../.dforge/test-env.sh && .venv/bin/python -c "import json; from app.main import app; print('semantic_deferred_to' in json.dumps(app.openapi()))"`. If it prints `True`, the field is on the wire and rule 5's legs run in Step 4; drop the field's assertion in `test_facts_channel.py`.
- Rows 346, 348, 402 and 329 are prose: no test.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_session_scope.py`
Expected: FAIL on the new test.

- [ ] **Step 3: Implement**

1. Row 327: a route endpoint is streaming when its body, or the body of a same-module function it calls by name, constructs `StreamingResponse` (AST walk); every streaming endpoint must carry a `StreamingResponse` return annotation, and the scan fails naming any that does not. Existing streaming routes keep passing.
2. Rows 345 and 347 (rule 6, `rg -n "SEMANTIC_ARM_OWNER|semantic_deferred_to" backend`): remove the constant, the field and its comment.
3. Row 346: `embedder_registry`'s docstring says registration creates one child table per family in `_TABLE_TEMPLATES`. Rows 348 and 402: `block_embeddings`' module docstring is re-wrapped to the file's width and its "nothing hooks into `file_document`… this task's" sentence becomes a statement that `document_door` and the hourly sweep drive it. Row 329: the three docstrings say "per-request (function-scoped)" for `SessionDep`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 900 .venv/bin/python -m pytest -q tests/test_session_scope.py tests/test_facts_channel.py tests/test_layer_composition.py tests/test_block_retrieval.py`
Expected: PASS. When Step 1 printed `True`, also run the guards leg from `CLAUDE.md` and `make generate` in `sdks/` (expect no client diff), and read the two prose counts.

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests
git commit -m "test(api): catch undeclared streaming routes"
```

### Task 20: Test isolation and document parser tests

**Files:**
- Modify: the test file Step 1 finds leaving a committed `(postgresql, database)` entity
- Modify: `backend/tests/test_repo_entity_merge.py`
- Modify: `backend/tests/test_document_parsers.py`, `backend/tests/test_document_routes.py`, `backend/tests/conftest.py` (`stub_llm` moves)
- Modify: `docs/two-door-parity.md` (the `documents.write` row)

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 351, 403, 352, 353, 354
**Depends on:** none
**Evaluation:** files 3 - spec 2 - coupling 0 - risk 1 = 6

- [ ] **Step 1: Write the failing test**

- Locate the leak (row 351): for each of `test_pipeline_savepoints`, `test_extraction_salvage`, `test_extraction`, `test_usage_attribution`, `test_merged_extraction`, `test_entity_shaping` and `test_communities`, run `cd backend && TEST_DATABASE_URL=<test-env.sh's URL with darkmem_test_2> timeout 600 .venv/bin/python -m pytest -q tests/<file>.py` and then `docker exec darkmem-postgres-1 psql -U darkmem -d darkmem_test_2 -Atc "SELECT name, entity_type FROM entities"`. The file after which a row remains is the leaker (more than one may leak). If none leaves a row, close 351 `not reproduced` with the reads and keep only 403's hardening.
- `backend/tests/test_repo_entity_merge.py::test_merge_runs_beside_a_committed_postgresql_entity` (integration, A21): a module fixture commits a `('postgresql', 'database')` entity from a separate session before the file's tests and removes it afterwards; every test in the file passes. Fails today because the calibration pair collides with it and `_names` asserts over the whole table.
- A42 is checked by command in Step 4: after running the leaking file, the `entities` read above returns no row.
- Row 353 changes the test itself: each `parametrize` entry carries its expected refusal fragment ("cannot infer a source_type" for the suffix case, "no parser serves" for the `source_type` case) and the assertion checks that fragment alone.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_repo_entity_merge.py`
Expected: FAIL on the new test.

- [ ] **Step 3: Implement**

1. Row 351: the leaking file removes what it commits (a `finally` or fixture teardown).
2. Row 403: `test_repo_entity_merge.py` seeds under names it owns or tolerates an existing row, and its `_names` assertions cover only the names it seeded.
3. Row 354: `stub_llm` moves to `backend/tests/conftest.py`; the mid-file import and its `noqa` go.
4. Row 352: the `documents.write` row of `docs/two-door-parity.md` gains one clause naming MCP's `unsupported_source` envelope as the twin of REST's 422 (outside any generated block).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 900 .venv/bin/python -m pytest -q tests/test_repo_entity_merge.py tests/test_document_parsers.py tests/test_document_routes.py tests/<leaking file> && timeout 1500 .venv/bin/python -m pytest -q -n 4 --dist loadfile tests/test_repo_entity_merge.py tests/test_pipeline_savepoints.py tests/test_extraction*.py tests/test_usage_attribution.py tests/test_merged_extraction.py tests/test_entity_shaping.py tests/test_communities.py`, then the `entities` read on the leaking file's lane database.
Expected: PASS. A42: run the leaking file serially on `darkmem_test_2` again (the Step 1 command), then the `entities` read on `darkmem_test_2`; it returns no row.

- [ ] **Step 5: Commit**

```bash
git add backend/tests docs/two-door-parity.md
git commit -m "test(graph): stop leaking a committed entity"
```

### Task 21: E2e reset guard and its own database

**Files:**
- Modify: `backend/scripts/e2e/e2e_db.py` (`assert_disposable_target`, the database default, the alembic subprocess)
- Modify: `backend/scripts/e2e/run_e2e.py` (the BLOCKED message)
- Modify: `backend/scripts/e2e/README.md`
- Modify: `scripts/gate.sh`, `scripts/release.sh` (the e2e legs)
- Modify: `CLAUDE.md` (Host environment: the database list)
- Test: `backend/tests/test_dev_script_guards.py`, `backend/tests/test_e2e_runner_args.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 250, 372, 395
**Depends on:** none
**Evaluation:** files 3 - spec 2 - coupling 0 - risk 3 = 8
**Lenses:** security, lang-bash

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_dev_script_guards.py::test_the_e2e_reset_refuses_every_loopback_alias` (unit, A22), parametrized: `assert_disposable_target` refuses `127.0.0.2:5432`, `[::1]:5432`, `0.0.0.0:5432` and `localhost:5432`, and accepts `localhost:5433` and `127.0.0.1:5433`. Fails today for `127.0.0.2` and `0.0.0.0`.
- `::test_the_e2e_database_defaults_to_darkmem_e2e` (unit, A22): with no database variable set, the resolved target's database is `darkmem_e2e`. Fails today (`darkmem_test`).
- `::test_gate_and_release_e2e_legs_name_darkmem_e2e` (unit, A22): the API e2e leg of `scripts/gate.sh` and of `scripts/release.sh` each name `darkmem_e2e`. Fails today.
- `::test_the_alembic_upgrade_is_bounded` (unit, row 395): with `subprocess.run` patched to record its kwargs, the e2e database's upgrade passes `timeout=600`. Fails today.
- `backend/tests/test_e2e_runner_args.py::test_blocked_names_the_model_url_variable` (unit, row 372): the BLOCKED message contains `DARKMEM_OLLAMA_BASE_URL`. Fails today.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_dev_script_guards.py tests/test_e2e_runner_args.py`
Expected: FAIL on the five new tests.

- [ ] **Step 3: Implement**

1. Row 250: parse the host with `ipaddress`; on port 5432 refuse any address that `is_loopback` or `is_unspecified`, plus `localhost` and the empty host. Keep the database-name guard.
2. Row 372: the database defaults to `darkmem_e2e` (the name guard already admits it); the e2e legs of `gate.sh` and `release.sh` pass `darkmem_e2e` explicitly; the module docstring and `README.md` say it is a third, separate database and give its one-time `docker exec darkmem-postgres-1 psql -U darkmem -d darkmem -c "CREATE DATABASE darkmem_e2e;"`; the BLOCKED message names `DARKMEM_OLLAMA_BASE_URL`. Run that `CREATE DATABASE` once on the dev Postgres now. CI already names `darkmem_e2e`; leave `ci.yml` alone.
3. Row 395: the `alembic upgrade head` subprocess gets `timeout=600`.
4. `CLAUDE.md`, Host environment, "Databases on the dev Postgres": add "`darkmem_e2e` is the API e2e suite's (create it once with `docker exec darkmem-postgres-1 psql -U darkmem -d darkmem -c "CREATE DATABASE darkmem_e2e;"`)".

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_dev_script_guards.py tests/test_e2e_runner_args.py tests/test_ci_workflows.py && bash -n ../scripts/gate.sh ../scripts/release.sh`
Expected: PASS and no syntax error.

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/e2e backend/tests scripts/gate.sh scripts/release.sh CLAUDE.md
git commit -m "fix(e2e): refuse loopback aliases, own database"
```

### Task 22: Backup suspect pruning and restore-cycle bounds

**Files:**
- Modify: `scripts/backup.sh` (suspect-dump pruning, the size comment)
- Modify: `scripts/worker/restore-cycle.sh` (bounded probe, replay and migrate; cleanup after a timeout)
- Modify: `docs/runbook-backup-worker.md` (one line on a timed-out cycle)
- Test: `backend/tests/test_backup_script.py`, `backend/tests/test_restore_cycle_script.py` (create)

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 377, 378, 379, 396
**Depends on:** none
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 3 = 7
**Lenses:** lang-bash, silent-failures

Edit, test and commit `scripts/backup.sh` in one sitting, well before 03:30 host time (Global Constraints).

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_backup_script.py::test_suspect_dumps_keep_the_newest_three` (integration, A23): a destination seeded with four `darkmem-*.sql.gz.suspect` files of ascending mtime and two real dumps; a run whose dump is suspect leaves exactly three suspect files (the new one and the two newest seeded), and both real dumps untouched with their bytes and mtimes. Fails today because suspects are never pruned.
Harness for both restore-cycle tests: `COMPOSE_CMD` points at a stub script (the script builds `$COMPOSE` from it) that appends its argv to a log file and tells calls apart by argv — `run … alembic` (migrate), `run … baseline_sha` (the image probe), `exec … psql` with `RENAME` (the swap) and other `exec` calls (create, replay, grants, which succeed), `stop`/`start` (succeed). `age` is not installed on this host (`command -v age` printed nothing, 2026-11-23), so a stub `age` first on `PATH` copies its input to its output (honouring `-o` or writing to stdout, whichever form the script uses); the environment sets `AGE_IDENTITY` (any file in `tmp_path`), `OWNER_PASSWORD` and `VIEWER_PASSWORD`, and the snapshot fixture is a gzip whose plain text ends in the marker `-- PostgreSQL database dump complete`, named as the script expects an encrypted snapshot to be named.

- `backend/tests/test_restore_cycle_script.py::test_an_overrunning_migrate_swaps_nothing` (integration, A23): the stub's migrate `exec sleep 60`, with `RESTORE_MIGRATE_TIMEOUT=2`; the script exits non-zero within 20 s, the log holds no swap call, its output names the migrate timeout, and the log holds a cleanup call that terminates the side database's backends and drops it. Fails today because the run is unbounded (the test's own subprocess timeout of 30 s ends it).
- `::test_an_overrunning_image_probe_exits_non_zero` (integration): the stub's migrate fails (exit 1), so the script reaches the image-hash probe, which `exec sleep 60`, with `RESTORE_PROBE_TIMEOUT=2`; the script exits non-zero within 20 s with no swap call.
- Rows 379 and 396 are style and a comment: no test.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_backup_script.py tests/test_restore_cycle_script.py`
Expected: FAIL on the three new tests.

- [ ] **Step 3: Implement**

1. Row 377: after renaming a suspect dump, `backup.sh` keeps the newest three `darkmem-*.sql.gz.suspect` files under their own glob and removes older ones; the dump prune glob and `_is_snapshot` are untouched.
2. Row 378: `restore-cycle.sh` wraps the image probe in `timeout "${RESTORE_PROBE_TIMEOUT:-120}"`, and the replay and the migrate in `timeout "${RESTORE_REPLAY_TIMEOUT:-3600}"` and `timeout "${RESTORE_MIGRATE_TIMEOUT:-3600}"`; the bound wraps the compose command, and exit 124 is tested before the baseline-hash comparison, so a timeout swaps nothing and exits non-zero with a message naming the step. Use `timeout --kill-after=10`, and run the bounded command so the signal reaches its children (Global Constraints, uutils). The worker's real cycle time is Unknown here; the bounds are overridable for that reason.
3. A timeout kills only the local compose client: the replay's `psql` keeps running inside the Postgres container, and the migrate's `run --rm` container can outlive its client. So on exit 124 from the replay or the migrate the script terminates the side database's backends (`pg_terminate_backend` over `pg_stat_activity WHERE datname = '$SIDE_DB'`), drops the side database, and removes the migrate's run container (give it a `--name` carrying the PID so it can be removed by name), each step tolerant of having nothing to do. The stub test checks that the cleanup is issued, not that it frees a real container; `docs/runbook-backup-worker.md` gains one line saying a timed-out cycle cleans its side database and how to check for a leftover one.
4. Row 379: remove the extra blank line above `_seed_dumps`. Row 396: the comment on dump sizes says nightly dumps are about 250 MB.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 900 .venv/bin/python -m pytest -q tests/test_backup_script.py tests/test_restore_cycle_script.py tests/test_deployment_artifact.py tests/test_read_only_role.py && bash -n ../scripts/backup.sh ../scripts/worker/restore-cycle.sh`
Expected: PASS and no syntax error.

- [ ] **Step 5: Commit**

```bash
git add scripts/backup.sh scripts/worker/restore-cycle.sh docs/runbook-backup-worker.md backend/tests
git commit -m "fix(backup): prune suspects, bound restore steps"
```

### Task 23: CI workflow and layout budget tests

**Files:**
- Modify: `backend/tests/test_ci_workflows.py`
- Modify: `frontend/src/features/graph/lib/__tests__/cluster-layout.test.ts`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 251, 252, 247
**UI/UX:** OP-4 — changes a test's threshold; no contract item is built here
**Depends on:** none
**Evaluation:** files 1 - spec 1 - coupling 0 - risk 0 = 2

- [ ] **Step 1: No new test, because all three changes are to tests themselves: an unused constant, an assertion message and a wall-clock threshold**

- [ ] **Step 2: Apply the changes**

1. Row 251: delete `TRUSTED_HEAD` and the stray blank line above it.
2. Row 252: before the `rsplit("@", 1)`, `assert "@" in action, f"{workflow}: {action} is not pinned to a commit sha"`.
3. Row 247: the `layoutIslands` budget test asserts a median of at most 500 ms and logs the measured median with `console.info`, so it holds while the host swaps.

- [ ] **Step 3: Run the tests**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_ci_workflows.py && cd ../frontend && timeout 900 npx vitest run src/features/graph/lib/__tests__/cluster-layout.test.ts`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_ci_workflows.py frontend/src/features/graph/lib/__tests__/cluster-layout.test.ts
git commit -m "test: tidy CI pin checks and layout budget"
```

### Task 24: Provider key prompt and envelope error messages

**Files:**
- Modify: `frontend/src/features/settings/components/provider-dialog.tsx`
- Modify: `frontend/src/lib/api.ts` (`apiFetch` error path and the upload path)
- Test: `frontend/src/features/settings/__tests__/settings-providers.real.test.tsx`, `frontend/src/lib/__tests__/api-fetch-headers.test.ts`, `frontend/src/lib/__tests__/api-upload.test.ts`

**Interfaces:**
- Consumes: none
- Produces: C4

**Items:** 249, 407
**UI/UX:** UX-1, UX-7
**Depends on:** none
**Evaluation:** files 2 - spec 2 - coupling 1 - risk 1 = 6

- [ ] **Step 1: Write the failing test**

- `settings-providers.real.test.tsx` › "a keyed provider's changed address asks for the key again" (integration, A24): editing a provider whose key is stored (masked) and changing its base URL disables Save and shows "The address or API kind changed. Enter the API key again." under the key field; clicking Save sends no request (fetch spy); typing a key enables Save. The same holds for an API kind change. Fails today because Save sends the mask and the server answers 422.
- `api-fetch-headers.test.ts` › "a refusal's message is the envelope's error.message" (unit, A32): a 422 whose body is `{"error": {"code": "invalid", "message": "Base URL is not reachable"}}` with no `detail` rejects with an `ApiError` whose `message` is "Base URL is not reachable" and `status` 422; a body with neither key gives "API error: 422". Fails today ("API error: 422").
- `api-upload.test.ts` › the same envelope rule on the upload path (unit, A32).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && timeout 900 npx vitest run src/features/settings/__tests__/settings-providers.real.test.tsx src/lib/__tests__/api-fetch-headers.test.ts src/lib/__tests__/api-upload.test.ts`
Expected: FAIL on the new cases.

- [ ] **Step 3: Implement**

1. Row 249: when the provider has a stored key, the key field is untouched, and the base URL or API kind differs from the stored row, the dialog shows the UX-1 sentence under the key field (described by the field through `aria-describedby`) and disables Save; typing a key clears both. The server's 422 stays as it is.
2. Row 407, per C4: the error message reads `error.message` first, then a string `detail`, then `API error: <status>`, on both paths.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && timeout 900 npx vitest run src/features/settings src/lib && timeout 600 npm run typecheck`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/settings frontend/src/lib
git commit -m "fix(settings): ask for the key after an address edit"
```

### Task 25: Backups failed states and Run now status

**Files:**
- Modify: `frontend/src/features/settings/use-backups-tab-binding.ts`
- Modify: `frontend/src/features/settings/components/backups-tab.tsx`
- Modify: `frontend/src/components/app-chrome/load-failure-states.stories.tsx`
- Test: `frontend/src/features/settings/__tests__/backups.test.tsx`

**Interfaces:**
- Consumes: C4
- Produces: C5 (Backups stories)

**Items:** 366, 406
**UI/UX:** UI-1, UX-6
**Depends on:** Task 24
**Evaluation:** files 2 - spec 2 - coupling 1 - risk 1 = 6

- [ ] **Step 1: Write the failing test**

All in `backups.test.tsx` (A29).

- "a failed destinations read shows the failed state with Retry": the destinations request answers 500; the library `empty-state` in its failed kind renders with a Retry button; clicking Retry requests destinations again. Same case for the inventory read and for the outcomes read. Fails today: destinations show a plain red line with no Retry, and inventory and outcome failures render as empty.
- "an empty inventory appears only after a successful read": while the inventory read is failed, the empty-inventory text is absent.
- "Run now reports a busy run only on 409": a 409 shows the in-progress message; a 500 whose body carries `error.message` "Dump failed" shows "Dump failed" and not the in-progress message. Fails today because the binding matches `409` in the error text.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && timeout 900 npx vitest run src/features/settings/__tests__/backups.test.tsx`
Expected: FAIL on the new cases.

- [ ] **Step 3: Implement**

1. The binding exposes each of its three queries' failure and refetch, and detects a busy Run now by `ApiError.status === 409` (C4).
2. `backups-tab.tsx` renders `EmptyState kind="failed"` with Retry for each failed read, in the same form as `distribution-tab.tsx`; the empty inventory renders only after a successful read.
3. `load-failure-states.stories.tsx` gains one story per failed Backups read (C5).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && timeout 900 npx vitest run src/features/settings src/components/app-chrome && timeout 600 npm run typecheck`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/settings frontend/src/components/app-chrome
git commit -m "fix(backups): show failed reads with Retry"
```

### Task 26: Stopped-processing banner on Settings LLM

**Files:**
- Modify: `frontend/src/hooks/api/use-pipeline-api.ts` (`HealthStatus`)
- Modify: `frontend/src/features/settings/use-llm-tab-binding.ts`
- Modify: `frontend/src/features/settings/components/llm-tab.tsx`
- Test: `frontend/src/features/settings/components/llm-tab.classifier.test.tsx`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 330
**UI/UX:** UI-2
**Depends on:** none
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 1 = 5

- [ ] **Step 1: Write the failing test**

- `llm-tab.classifier.test.tsx` › "shows the stopped-processing banner while the boot setup failed" (integration, A30): with `/health` answering `pipeline_state: "failed_at_boot"`, the tab shows "Processing is stopped: the model setup failed at startup. Captures are still queued. Save a working model configuration to start it."; with `ok`, `not_configured`, `read_only` and `unknown` it does not. Fails today because nothing reads `pipeline_state`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && timeout 900 npx vitest run src/features/settings/components/llm-tab.classifier.test.tsx`
Expected: FAIL on the new case.

- [ ] **Step 3: Implement**

`HealthStatus` gains `pipeline_state: "ok" | "not_configured" | "failed_at_boot" | "read_only" | "unknown"`; the binding exposes it; the tab shows the UI-2 text in darkraise-ui's `banner` component (its warning variant, per its `.d.ts`), at the top of the tab, only for `failed_at_boot`. Demo mode keeps making no request.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && timeout 900 npx vitest run src/features/settings src/hooks/api && timeout 600 npm run typecheck`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/api/use-pipeline-api.ts frontend/src/features/settings
git commit -m "feat(settings): say when processing stopped at boot"
```

### Task 27: Failed-captures busy state and no inject log

**Files:**
- Modify: `frontend/src/features/activity/components/failed-captures-section.tsx`
- Modify: `frontend/src/features/activity/components/failed-captures-section.stories.tsx`
- Modify: `frontend/src/features/settings/components/distribution-tab.tsx` (remove `RecentInjects`)
- Test: `frontend/src/features/activity/__tests__/failed-captures-section.test.tsx`, `frontend/src/features/settings/__tests__/settings-distribution.real.test.tsx`

**Interfaces:**
- Consumes: none
- Produces: C5 (failed-captures pending story)

**Items:** 388, 405
**UI/UX:** UX-2, UI-6
**Depends on:** none
**Evaluation:** files 2 - spec 2 - coupling 1 - risk 1 = 6

- [ ] **Step 1: Write the failing test**

- `failed-captures-section.test.tsx` › "a pending requeue disables both of its row's buttons" (integration, A25): while a row's requeue request is held pending, that row's Requeue and Discard are disabled and another row's are not; when it settles both return. The same for a pending discard. Fails today because Discard has no `disabled`.
- `settings-distribution.real.test.tsx` › "renders no inject log" (integration, A38): the Distribution tab renders no "Inject log" heading and requests no events of type `inject` or `inject_curbed`. Fails today.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && timeout 900 npx vitest run src/features/activity/__tests__/failed-captures-section.test.tsx src/features/settings/__tests__/settings-distribution.real.test.tsx`
Expected: FAIL on the new cases.

- [ ] **Step 3: Implement**

1. Row 388: the Discard trigger takes `disabled={busy}` beside Requeue; the `if (busy) return` guard stays.
2. Row 405 (rule 6 for `RecentInjects`): remove the inject log and its query from `distribution-tab.tsx`. The Activity tab's inject rendering (`use-day-events.ts`, `day-tab.tsx`, `activity-inject-records.test.tsx`) stays: 192.168.0.199's journal may hold inject rows.
3. `failed-captures-section.stories.tsx` gains a story with a requeue held pending (C5).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && timeout 900 npx vitest run src/features/activity src/features/settings && timeout 600 npm run typecheck`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/activity frontend/src/features/settings
git commit -m "fix(ui): hold row buttons while a capture action runs"
```

### Task 28: Document editor caret and leave guard

**Files:**
- Modify: `frontend/src/features/documents/components/block-editor.tsx` (caret, `beforeunload`, a held-write callback)
- Create: `frontend/src/features/documents/components/document-leave-guard.tsx` (the router blocker and its dialog)
- Modify: `frontend/src/features/documents/components/editable-document.tsx` (mounts the guard beside `BlockEditor`)
- Test: `frontend/src/features/documents/__tests__/block-editor.test.tsx`, `frontend/src/features/documents/__tests__/block-editor-concurrent-writes.test.tsx`, `frontend/src/features/documents/__tests__/document-leave-guard.test.tsx` (create)

The router blocker lives outside `BlockEditor`, because every existing `BlockEditor` test renders it with no router; `BlockEditor` itself stays router-free.

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 389, 376
**UI/UX:** UX-3, UX-4
**Depends on:** none
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 2 = 6

- [ ] **Step 1: Write the failing test**

- `block-editor.test.tsx` › "opening a block puts the caret at the end" (integration, A26): opening a block whose text is `hello world` leaves the edit box's `selectionStart` and `selectionEnd` at 11. Fails today (0).
- `block-editor-concurrent-writes.test.tsx` › "a held write cancels beforeunload" (integration, A28): with a write saving, refused, or queued behind a refused one, a dispatched `beforeunload` event is `defaultPrevented`; with none held it is not, and the listener is gone after the editor unmounts. Fails today.
- `block-editor-concurrent-writes.test.tsx` › "reports its held-write state" (integration, A27 wiring): `onHeldWritesChange` is called with `"saving"` while a write is in flight, `"refused"` when it is refused (and while later writes queue behind it), and `"none"` after Discard. Fails today because the prop does not exist.
- `document-leave-guard.test.tsx` › "a refused write asks before in-app navigation" (integration, A27): inside a memory-history router, with the guard given `held="refused"` and a focus target holding an edit box with text, navigating opens a dialog titled "Leave without saving?" with body "This block's edit has not been saved." and buttons "Stay" and "Leave and discard"; Stay and Escape each close it with the route unchanged and focus on the edit box holding its text (or on the block when the held write has no edit box); Leave and discard completes the navigation and calls the guard's `onDiscard`. With `held="saving"` or `"none"` the navigation completes with no dialog. Fails today because the guard does not exist.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && timeout 900 npx vitest run src/features/documents/__tests__/block-editor.test.tsx src/features/documents/__tests__/block-editor-concurrent-writes.test.tsx src/features/documents/__tests__/document-leave-guard.test.tsx`
Expected: FAIL on the four new cases.

- [ ] **Step 3: Implement**

1. Row 389: after `focus()`, set the selection to the end of the text.
2. Row 376, in `BlockEditor`: a `beforeunload` listener is active while any write is held (saving, refused or queued), as `features/notes/use-page-sync.ts` does; an optional `onHeldWritesChange(state: "none" | "saving" | "refused")` prop reports the held state (`"refused"` covers writes queued behind a refused one), and the editor exposes a way for its parent to return focus to the held block's edit box, or to the block when it has none.
3. Row 376, in `DocumentLeaveGuard` (props `held`, `restoreFocus`, `onDiscard`): TanStack Router's `useBlocker` blocks in-app navigation only while `held === "refused"` (a write merely in flight still lands, because the write queue outlives the editor) and opens the library `alert-dialog` with the UX-4 copy. `editable-document.tsx`, which sits under the app router, mounts it beside `BlockEditor` and wires the three props; `onDiscard` clears the held writes the same way the existing Discard does.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && timeout 900 npx vitest run src/features/documents && timeout 600 npm run typecheck`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/documents
git commit -m "feat(documents): guard leaving with an unsaved block"
```

### Task 29: Dark disabled controls, Mermaid copy and canvas resize

**Files:**
- Modify: `frontend/src/styles/globals.css`
- Modify: `frontend/src/features/code/components/real-code-graph-view.tsx` (the Copy Mermaid `Clipboard`)
- Modify: `frontend/src/features/code/components/code-glow-canvas.tsx`
- Test: `frontend/src/features/code/components/__tests__/code-glow-canvas-resize.test.tsx` (create), `frontend/tests/disabled-opacity.spec.ts` (create)

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 390, 356, 380
**UI/UX:** UI-3, UI-4, UX-5
**Depends on:** none
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 1 = 5

- [ ] **Step 1: Write the failing test**

- `code-glow-canvas-resize.test.tsx` › "a container resize refreshes the renderer" (integration, A31): with Sigma mocked and `ResizeObserver` stubbed, mounting the canvas observes its container; firing the observer with a new size calls the renderer's `refresh` once, with no window `resize` event; unmounting disconnects the observer. Fails today because nothing observes the container.
- `frontend/tests/disabled-opacity.spec.ts` › "a disabled button dims to 0.38 in the dark theme" (e2e, A33): on the app's login page, with `data-mode="dark"` on the root element, a `<button class="dr-btn" disabled>` added to the page has a computed `opacity` of `0.38`, and `0.5` in the light theme. Fails today (`0.5` in both).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && timeout 900 npx vitest run src/features/code/components/__tests__/code-glow-canvas-resize.test.tsx; cd ../backend && timeout 1200 .venv/bin/python scripts/e2e/run_playwright_e2e.py tests/disabled-opacity.spec.ts --project=chromium`
Expected: FAIL on both.

- [ ] **Step 3: Implement**

1. Row 390: `globals.css` sets `--disabled-opacity: 0.38` under the existing `[data-mode="dark"]` override, with a comment naming the library gap (darkraise-ui defines the token once, with no dark value). The token is global, so disabled inputs and selects dim with it; Task 36 checks they stay readable.
2. Row 356: the Copy Mermaid `Clipboard` takes `justify-self-end` in place of `self-end`.
3. Row 380: `code-glow-canvas.tsx` observes its container with a `ResizeObserver` and calls the renderer's `refresh()` on a size change; it disconnects on unmount. The pane widths are row 411 (declined).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && timeout 900 npx vitest run src/features/code && timeout 600 npm run typecheck; cd ../backend && timeout 1200 .venv/bin/python scripts/e2e/run_playwright_e2e.py tests/disabled-opacity.spec.ts --project=chromium`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/styles/globals.css frontend/src/features/code frontend/tests/disabled-opacity.spec.ts
git commit -m "fix(ui): dim dark disabled controls, refit canvas"
```

### Task 30: Review queue and chat row nesting

**Files:**
- Modify: `frontend/src/features/knowledge/components/review-queue.tsx`
- Modify: `frontend/src/features/chat/components/chat-sidebar.tsx`
- Modify: `frontend/tests/knowledge.spec.ts` (only if its axe check does not yet reach the review queue)
- Test: `frontend/src/features/chat/__tests__/chat-sidebar.test.tsx`, `frontend/src/features/knowledge/components/__tests__/review-tab.test.tsx`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 381, 382
**UI/UX:** UI-5
**Depends on:** none
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 1 = 5

- [ ] **Step 1: Write the failing test**

- First, settle row 381's unverified axe findings: run the axe check `frontend/tests/knowledge.spec.ts` already uses against the review queue with a fact row, through `cd backend && timeout 1200 .venv/bin/python scripts/e2e/run_playwright_e2e.py tests/knowledge.spec.ts --project=chromium` (extending that spec with the review queue view if it does not reach it). Each finding (list, target-size, nested-interactive, aria-valid-attr-value, label) that holds and is within these two files is fixed here; any other is added as its own row with `bash <plugin-root>/scripts/register add docs/dforge/registers/2026-11-20-audit-remaining.md "<finding>" --state deferred --note "<why>"` and named in the commit body.
- `chat-sidebar.test.tsx` › "a conversation row holds select and Delete as siblings" (integration, A38): the row's Delete button is not a descendant of its select control, the select control is a `button`, Enter on it selects the conversation, and clicking Delete does not select it. Fails today because the row is a `div role="button"` containing Delete.
- `review-tab.test.tsx` › "a fact row puts no block element inside a paragraph" (integration, A38): the rendered fact row has no `div` inside a `p`. Fails today because the Badge (a `div`) sits in a `<p>`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && timeout 900 npx vitest run src/features/chat/__tests__/chat-sidebar.test.tsx src/features/knowledge/components/__tests__/review-tab.test.tsx`
Expected: FAIL on the two new cases.

- [ ] **Step 3: Implement**

1. Row 381: the fact row's `<p>` wrappers around the Badge become `<div>`, keeping the classes.
2. Row 382: each conversation row is a plain container holding a select `<button>` (stretched across the title block) and the Delete button as siblings; `stopPropagation` goes. The row's look and keyboard order (select, then Delete) are unchanged.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && timeout 900 npx vitest run src/features/chat src/features/knowledge && timeout 600 npm run typecheck`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/chat frontend/src/features/knowledge frontend/tests
git commit -m "fix(ui): un-nest chat row and review badge"
```

### Task 31: Abort signals and dead query keys

**Files:**
- Modify: `frontend/src/hooks/api/use-memory-api.ts`, `frontend/src/hooks/api/use-usage-api.ts`, `frontend/src/hooks/api/use-setup-api.ts`
- Modify: `frontend/src/hooks/api/use-memory-buffer-api.ts`, `frontend/src/hooks/api/use-code-api.ts`
- Modify: `frontend/src/lib/query-keys.ts`
- Test: `frontend/src/hooks/api/__tests__/use-pages-reads.test.tsx` (or the neighbouring hook test of `usePaginatedSearch`), `frontend/src/hooks/api/__tests__/use-memory-buffer-api.test.tsx`, `frontend/src/lib/__tests__/query-keys.test.ts`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 374, 375, 408
**UI/UX:** OP-4 — passes abort signals and removes no-op invalidations; nothing a user sees changes
**Depends on:** none
**Evaluation:** files 3 - spec 2 - coupling 0 - risk 1 = 6

- [ ] **Step 1: Write the failing test**

- "the paginated memory search passes its abort signal" (integration, row 374): rendering `usePaginatedSearch` issues its POST with an `AbortSignal` in the fetch init, and the signal aborts when the query is superseded. The same for `useSubjectTotals` and `useSetupProviderModels`. Fails today because their `queryFn` ignores `signal`. First read `rawFetch` in `use-setup-api.ts`: if it does not forward its init, make it.
- Rows 375 and 408 remove no-op calls: no new test; remove the two `use-memory-buffer-api.test.tsx` assertions that pin the `["memories"]` invalidation.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && timeout 900 npx vitest run src/hooks/api`
Expected: FAIL on the new cases.

- [ ] **Step 3: Implement**

1. Row 374: each of the three `queryFn`s takes `({ signal })` and passes it to the fetch.
2. Rows 375 and 408 (rule 6, `rg -n '"memories"\]|"repoStats"|"codeSymbols"' frontend/src`): remove the nine invalidations of `["memories"]`, `["repoStats"]` and `["codeSymbols"]` and those three entries of `query-keys.ts`, then adjust `query-keys.test.ts` if it lists them.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && timeout 900 npx vitest run src/hooks src/lib && timeout 600 npm run typecheck`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks frontend/src/lib
git commit -m "fix(api): abort superseded search queries"
```

### Task 32: Canvas mirror arrays, dead helper, Storybook index and comments

**Files:**
- Modify: `frontend/src/features/graph/lib/constellation-runner.ts` (`mirror`), `frontend/src/features/graph/lib/constellation-layout.ts` (an in-place twin of `fitCoreToFarthest`)
- Delete: `frontend/src/lib/portal-overlays.ts`, `frontend/src/lib/__tests__/portal-overlays.test.tsx`
- Modify: `frontend/.storybook/preview.tsx`
- Modify: comments in `frontend/src/features/activity/use-day-events.ts`, `frontend/src/features/activity/components/day-tab.tsx`, `frontend/src/demo/types.ts`, `frontend/src/features/activity/event-taxonomy.ts`
- Test: `frontend/src/features/graph/lib/__tests__/constellation-layout.test.ts`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 363, 365, 359, 343
**UI/UX:** OP-4 — removes per-frame allocation and dead code and fixes Storybook chrome; nothing a user sees changes
**Depends on:** Task 27
**Evaluation:** files 3 - spec 2 - coupling 0 - risk 1 = 6

- [ ] **Step 1: Write the failing test**

- `constellation-layout.test.ts` › "the in-place fit matches fitCoreToFarthest" (unit, row 363): for three seeded layouts, the in-place twin writes into caller-owned arrays the same positions `fitCoreToFarthest` returns, within 1e-9. Fails today because the twin does not exist.
- `constellation-layout.test.ts` › "the runner's mirror reuses its arrays across frames" (unit, row 363): two consecutive frames of the runner's mirror write into the same backing arrays (identity equal) and build no `Map`. Fails today.
- Rows 365, 359 and 343 change no tested behaviour: no new test.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && timeout 900 npx vitest run src/features/graph/lib/__tests__/constellation-layout.test.ts`
Expected: FAIL on both new cases.

- [ ] **Step 3: Implement**

1. Row 363: `mirror()` writes into arrays it keeps between frames, through the in-place twin.
2. Row 365 (rule 6, `rg -n "portal-overlays|ignorePortaledOverlayPointerDown" frontend`): delete the file and its own test.
3. Row 359: the Storybook preview's root route gets an index child route rendering nothing, so no story shows "Not Found".
4. Row 343: the four comments stop naming the removed `inject_journal` and `inject_watch` modules, and `event-taxonomy.ts`'s header says neither inject event has a producer any more.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && timeout 900 npx vitest run src/features/graph src/features/activity src/lib && timeout 600 npm run typecheck && SB=$(mktemp -d) && timeout 900 npx storybook build --test -o "$SB" >/dev/null; rc=$?; rm -rf "$SB"; test $rc = 0`
Expected: PASS, and the Storybook build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "perf(graph): reuse arrays in the canvas mirror"
```

### Task 33: Remove the SDK declareContext verb

**Files:**
- Modify: `sdks/generate.py` (the `declareContext` verb, `CONTEXT_HEADER` and its guards)
- Modify (generated by `make generate`): `sdks/ts/src/client.ts`, `sdks/python/darkmem_sdk/client.py`
- Test: `sdks/python/tests/test_surface.py`, `sdks/ts/src/client.test.ts`, `backend/tests/test_sdk_generator.py`, `backend/tests/test_sdk_contract_conformance.py`

**Interfaces:**
- Consumes: none
- Produces: C2

**Items:** 342
**Depends on:** none
**Evaluation:** files 2 - spec 2 - coupling 1 - risk 2 = 7

- [ ] **Step 1: Extend the test `backend/tests/test_sdk_generator.py` (the test that pins the verb set)**

- The pinned verb set drops `declareContext` / `declare_context`, and a new assertion checks that neither generated client contains `declareContext`, `declare_context`, `CONTEXT_HEADER` or `X-Darkmem-Context` (A35, SDK half). Fails today because the verb and constant are generated.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_sdk_generator.py`
Expected: FAIL.

- [ ] **Step 3: Implement**

1. Remove the verb, `CONTEXT_HEADER` and the generator guards that exist only for them from `sdks/generate.py`; run `make generate` in `sdks/`.
2. Remove their cases from `test_surface.py`, `client.test.ts` and `test_sdk_contract_conformance.py`.
3. This is a breaking change for SDK callers (owner ruling); the commit body says so.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sdks && timeout 300 make generate && cd ../backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_sdk_generator.py tests/test_sdk_contract_conformance.py && cd ../sdks/python && timeout 300 ../../backend/.venv/bin/python -m pytest -q && cd ../ts && timeout 300 npm test`
Expected: PASS, and a second `make generate` leaves no diff.

- [ ] **Step 5: Commit**

```bash
git add sdks backend/tests
git commit -m "feat(sdk)!: remove the declareContext verb"
```

Leave row 342 open; Task 35 closes it.

### Task 34: Remove declared context from the search door

**Files:**
- Modify: `backend/app/schemas/memory.py` (`MemorySearchRequest.context`)
- Delete: `backend/app/api/context_resolution.py`
- Modify: `backend/app/services/memory.py` (the resolution in `_search_memories_paginated_traced` and its note in `search_memories`)
- Modify: `backend/app/schemas/envelope.py` (`ContextEcho`, `DeclaredByTier`, the envelope's `context` echo)
- Modify: `backend/app/repositories/project_registry.py` (`get_applies_when_default`, only if Step 3's search finds no other importer)
- Test: `backend/tests/test_envelope.py`

**Interfaces:**
- Consumes: C2
- Produces: none

**Items:** 342
**Depends on:** Task 33
**Evaluation:** files 2 - spec 2 - coupling 1 - risk 2 = 7

- [ ] **Step 1: Extend the test `backend/tests/test_envelope.py` (the envelope's context echo test)**

- The echo test is replaced by one asserting (A35, door half): `MemorySearchRequest.model_fields` has no `context`; a traced `POST /api/v1/memories/search` carrying the `X-Darkmem-Context` header answers an envelope with no `context` key; and the OpenAPI document names no `x-darkmem-context` parameter and no `ContextEcho` schema. Fails today.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 600 .venv/bin/python -m pytest -q tests/test_envelope.py`
Expected: FAIL.

- [ ] **Step 3: Implement**

1. Rule 6: `rg -n "context_resolution|ContextEcho|DeclaredByTier|get_applies_when_default|x-darkmem-context" backend` lists every importer; remove the field, the module, the resolution and echo in `memory.py`, and the envelope types; remove `get_applies_when_default` only if nothing else imports it.
2. Remove or adjust every other backend test the search names (they assert the removed surface).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . ../.dforge/test-env.sh && timeout 900 .venv/bin/python -m pytest -q tests/test_envelope.py tests/test_sdk_generator.py tests/test_sdk_contract_conformance.py tests/test_memory*.py`, then the guards leg from `CLAUDE.md` on `darkmem_test_2`, then `cd ../sdks && timeout 300 make generate` (expect no diff).
Expected: PASS; the guards leg passes apart from assertions this task removed.

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat(api)!: remove declared search context"
```

Leave row 342 open; Task 35 closes it.

### Task 35: Remove the demo context chip and its design text

**Files:**
- Delete: `frontend/src/components/app-chrome/context-chip.tsx`, `frontend/src/components/app-chrome/__tests__/context-chip.test.tsx`
- Delete: `frontend/src/stores/context-store.ts`, `frontend/src/stores/__tests__/context-store.test.ts` (only if Step 3's search finds no other importer)
- Modify: `frontend/src/components/app-chrome/header-controls.tsx`, and `frontend/src/routes`' memories page if it reads the store
- Modify: `docs/two-door-parity.md`, `docs/design/12-api-and-mcp-contract.md`, `docs/design/15-distribution-and-integration.md`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 342
**UI/UX:** OP-4 — removes a demo-only chip; no screen is added
**Depends on:** Task 34
**Evaluation:** files 3 - spec 2 - coupling 0 - risk 1 = 6

- [ ] **Step 1: No new test, because the removal leaves no behaviour to pin; `frontend/src/__tests__/removed-names.test.ts` gains `declareContext` and `X-Darkmem-Context` in its list of names that must not reappear**

- [ ] **Step 2: Remove**

1. Rule 6: `rg -n "context-chip|ContextChip|context-store|useContextStore|SHOW_CONTEXT" frontend/src` lists every importer; remove the chip, its mount in `header-controls.tsx`, and the store with its demo search use when nothing else reads it.
2. `docs/design/12` and `docs/design/15`: remove the declared-context sections (or the sentences that describe the header, the request field, the echo and the verb), leaving a one-line statement that declared context was removed on 2026-11-23 because nothing ranked by it. `docs/two-door-parity.md`: remove or correct any row that names the context field, header or echo.
3. Re-read the headline counts sentence in `docs/two-door-parity.md` and `CLAUDE.md`'s tool and job counts; correct either if it moved.

- [ ] **Step 3: Run the checks**

Run: `cd frontend && timeout 900 npx vitest run src/components src/stores src/__tests__ src/routes && timeout 600 npm run typecheck && timeout 900 npm run build && cd ../backend && timeout 1200 .venv/bin/python scripts/e2e/run_playwright_e2e.py tests/demo-makes-no-api-calls.spec.ts --project=chromium`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend docs/two-door-parity.md docs/design
git commit -m "refactor(ui): remove the declared-context chip"
```

### Task 36: UI proof walkthrough

**Files:**
- Create: `docs/dforge/ui-ux/proofs/2026-11-23-audit-followups.md`
- Create: `docs/dforge/ui-ux/proofs/2026-11-23-audit-followups.judge.md`

**Interfaces:**
- Consumes: C5, and the tests of Tasks 24 to 30
- Produces: none

**UI/UX:** OP-1, OP-2, OP-3, OP-4
**Depends on:** Task 35
**Evaluation:** files 1 - spec 2 - coupling 1 - risk 1 = 5

- [ ] **Step 1: No new test, because this task produces the proof report that `scripts/ui-proof check` reads; every behaviour it shows is pinned by the tests of Tasks 24 to 30**

- [ ] **Step 2: Launch and seed**

Follow the dforge plugin's `skills/ui-ux/references/walkthrough.md` and `docs/dforge/ui-ux/profile.md`. Start Storybook and the `VITE_DEMO=1` vite server as tracked background tasks with their PIDs noted; for flows that need a server (UX-1, UX-4, UX-6, UI-1, UI-2) use the disposable e2e stack through `backend/scripts/e2e/run_playwright_e2e.py`, never `:8000`. Seed OP-3's worst-case data: a forced failure on each Backups read, a keyed provider with a 200-character base URL, a requeue held pending, a 2,000-character block, a refused block write, and zero, one and many rows.
Expected: every server answers and its PID is recorded.

- [ ] **Step 3: Walk and record**

1. Walk every changed flow by pointer and then by keyboard alone, at 1280x800 and 1920x1080, light and dark, forcing each state. Evidence goes to `.dforge/ui-ux/audit-followups/`, one screenshot per item and state named `<id>-<viewport>-<theme>[-<state>].png`.
2. A34 (demo): in the dark theme, a disabled button, input and select each sit beside their enabled twin, each visibly dimmer and still readable (contrast of their text against the background recorded), and the Copy Mermaid trigger keeps its own width at the end of its row.
3. Run the automated checks the web platform guide lists (accessibility scan, console errors, overflow, contrast) on each changed screen.
4. Write the proof report with one row per contract item UI-1 to UI-6, UX-1 to UX-7 and OP-1 to OP-4, each naming its screenshot or its test; UI-1 and UX-2 cite the C5 stories. An item no harness on this host can show is an `unverifiable` row with its reason; never write an `**Accepted by:**` line. The OP-4 row states the out-of-scope items (rows 411, 362, 357) and that no screen was added.
5. Stamp the report with `bash <plugin-root>/scripts/ui-proof stamp docs/dforge/ui-ux/proofs/2026-11-23-audit-followups.md`, have a `dforge:judge-opus` seat review it into the `.judge.md` file, and fix the UI (not the check) for every `fix` verdict. A scratch Playwright spec used for seeding is deleted before the commit.
6. Stop every server started in Step 2 and confirm no process of this task is left.

- [ ] **Step 4: Run the gate**

Run: `bash <plugin-root>/scripts/ui-proof check --base master --spec docs/dforge/specs/2026-11-23-audit-followups-design.md`
Expected: exit 0.

- [ ] **Step 5: Commit**

```bash
git add docs/dforge/ui-ux/proofs
git commit -m "docs(ui-ux): prove the audit follow-up UI items"
```

### Task 37: Close: gate legs, door counts and the register

**Files:**
- Modify: `docs/dforge/registers/2026-11-20-audit-remaining.md` (through `scripts/register` only)

**Interfaces:**
- Consumes: C3
- Produces: none

**Depends on:** Task 36
**Evaluation:** files 0 - spec 1 - coupling 1 - risk 1 = 3

- [ ] **Step 1: No new test, because this task runs the existing checks and settles the register**

- [ ] **Step 2: Run the checks**

1. A36: `cd backend && .venv/bin/python -m alembic heads` prints only `0006_drop_blocks_search_vector (head)`, and `git diff master --stat -- backend/migrations` is empty.
2. The guards leg from `CLAUDE.md` on `darkmem_test_2` passes; no route or MCP tool was added (`git diff master -- backend/app/api/mcp/scopes.py` shows no added tool).
3. The Integration check: `free -h`, then `timeout 3000 bash .dforge/gate-legs.sh` prints `ALL LEGS OK`.

- [ ] **Step 3: Settle the register**

A37: every row a task closed is `done` with its commit; `bash <plugin-root>/scripts/register check docs/dforge/registers/2026-11-20-audit-remaining.md` passes and `bash <plugin-root>/scripts/register open --spec docs/dforge/specs/2026-11-23-audit-followups-design.md` lists no `open`, `planned` or `doing` row. The 2026-11-20 plan's after-merge deploy sequence, and row 215 behind it, run once after this plan merges, outside the run (owner ruling).

- [ ] **Step 4: Commit**

```bash
git add docs/dforge/registers/2026-11-20-audit-remaining.md
git commit -m "docs(register): close the audit follow-ups"
```
