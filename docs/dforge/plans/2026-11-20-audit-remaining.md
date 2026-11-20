# Audit Remaining Items Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: dforge:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve every open row of `docs/dforge/registers/2026-11-20-audit-remaining.md`: the open findings of the 2026-11-20 codebase audit, the carried graph rows and the embedder incident's follow-ups on this host.

**Architecture:** Seventy-one sequential tasks grouped by the spec's sixteen work packages. Each task reproduces its findings with failing tests, applies the track file's remedy (or the spec's departure), and corrects the contract sentence it changes in the same commit. Three new linear Alembic revisions, no change to `0001_baseline.py`, and nothing pushed or deployed inside the run.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy async, Alembic, pytest with pytest-xdist; Postgres with pgvector; React, TypeScript, TanStack Router and Query, darkraise-ui, vitest, Storybook 10; bash; GitHub Actions; a browser extension tested with `node --test`.

**Spec:** docs/dforge/specs/2026-11-20-audit-remaining-design.md

**Execution:** inline — `claude --model opus --effort high` — the highest task total is 8 (Tasks 20, 30, 38, 48 and 56)

**Parallelism:** sequential — inline execution

**Task check:** none — full suite every 3 tasks

**Integration check:** `bash .dforge/gate-legs.sh`

**CI:** `.github/workflows/ci.yml .github/workflows/release.yml .github/workflows/cache-cleanup.yml` — platforms: uutils (ubuntu-latest), darkmem-linux — local: `bash .dforge/gate-legs.sh` — uncovered: uutils (ubuntu-latest)

**Worktree setup:** `docker compose -f docker-compose.dev.yml up -d postgres`, then confirm `.dforge/test-env.sh` and `.dforge/gate-legs.sh` exist (both are local, untracked files written with this plan)

**Plan review:** 2026-11-20 — dforge:judge-opus — executability 16 / coherence 17 / coverage 17 / assumptions 16 (round 2)

## Global Constraints

- **Verify first (spec rule 1).** Every finding starts with its failing test, or with the named query or command where no test can reproduce it. A finding whose test passes unchanged, or whose described code no longer exists, is not fixed: close its register row with `scripts/register set docs/dforge/registers/2026-11-20-audit-remaining.md <id> done --note "not reproduced: <evidence>"`, keep the passing test only if it pins behaviour no other test pins, and go on.
- **Where a finding lives.** Each task names its findings by id (`B1-3`, `F2-7`, `P1-9`). The finding's evidence, file locations and reviewer remedy are in `docs/2026-11-20-codebase-audit/<track>.md` under that id; read that entry before Step 1. Where this plan names no departure, the fix is the track file's remedy (spec rule 2). Line numbers in the track files date from 2026-11-20; find the code by the quoted name.
- **Contract sentences move with the code (spec rule 3).** A change to behaviour that `CLAUDE.md`, `docs/two-door-parity.md` or `docs/api-rest-conventions.md` states is corrected in place in the same commit, with no note saying it was corrected.
- **Schema (spec rule 4).** Never edit `backend/migrations/versions/0001_baseline.py`, not even a comment. A schema change is a new revision whose `down_revision` is the head at the time it is written; the chain stays linear with one head. A revision must upgrade a populated database in place.
- **Doors (spec rule 5).** After adding or removing a REST route or MCP tool, run the guards leg from `CLAUDE.md` ("The guards leg is mandatory…") and re-read the headline counts sentence in `docs/two-door-parity.md` and `CLAUDE.md`'s tool and job counts.
- **No removal without proof (spec rule 6).** Remove a module, export, script or dependency only after `rg` shows no importer outside its own tests; quote the search in the commit body.
- **Host limits (spec rule 7).** Run Python as `backend/.venv/bin/python` from `backend/`; there is no `python` on PATH. Backend tests take their database from `. ../.dforge/test-env.sh` (the dev Postgres on `127.0.0.1:5433`, database `darkmem_test`); never set `DATABASE_URL` in front of pytest and never point a test, harness or script at production (`127.0.0.1:5432`, container `darkmem-prod-postgres-1`). The one exception is a read-only `SELECT` (or an `EXPLAIN` of one) that a task step spells out, run through `docker exec darkmem-prod-postgres-1 psql`; nothing else in the run touches production. Exit 143 is SIGTERM from `earlyoom`, not a failure: read `free -h` and re-run before believing a red leg. Give every test, build and network command a timeout.
- **Never run Playwright bare.** Use `backend/scripts/e2e/run_playwright_e2e.py`; `npx playwright test` points `/api` at the live instance on `:8000`.
- **Nothing leaves this machine.** No `git push`, no image push (`DARKMEM_PUSH=0` on any build), no deploy and no write to production inside the run. `gh` is used read-only.
- **Single worker (invariant 13).** No `--workers`, `WEB_CONCURRENCY` or `deploy.replicas` anywhere; every launch path keeps `--no-proxy-headers`. In-process caches added by this plan rely on the single worker and say so in one comment.
- **Tests.** One test per behaviour at the lowest layer that can fail for it. A test contract names the file a new test is created in; when an existing test file already covers the same function, add the test there under the same test name. Frontend tests sit where the neighbouring tests of that feature sit. Never pin a test to serial; a test that fails only under `-n 4` is leaking state.
- **Frontend.** Check `ls frontend/node_modules/darkraise-ui/dist/components/` before building any UI; restyle a built-in, never re-implement one; a local component records which library gap it fills. Never run a repo-wide `prettier --write`. `routeTree.gen.ts` is generated. Demo mode (`VITE_DEMO=1`) makes no API request: every new hook passes `enabled: !DEMO` or its demo twin.
- **Generated SDK clients.** `sdks/ts/src/client.ts` and `sdks/python/darkmem_sdk/client.py` are generated; after a route or schema change run `make generate` in `sdks/`.
- **Secrets.** Keys live in `.claude/local-credentials.md` (gitignored) and never enter a tracked file, a test fixture or a commit.
- **Comments.** None unless the why is non-obvious. Never reference the task, plan or finding id in code.
- **Commits.** `<type>(<scope>): <subject>`, subject at most 50 characters, imperative, no attribution lines. One commit per task unless a task says otherwise. Never `--no-verify`. Leave the untracked `graph.jpg` alone.
- **Register.** When a task's commit lands, set each row its `**Items:**` line names with `scripts/register set <register> <id> done --note "<commit sha7>"` unless the row is closed `not reproduced`.
- **Plugin scripts.** `scripts/register` and `scripts/ui-proof` are dforge plugin scripts, not files of this repository: call each as `bash <plugin-root>/scripts/<name>`, where the plugin root is the path the session start prints.
- uutils (ubuntu-latest): a lock built on `mkdir` failing when the directory exists does not exclude a second process — create the lock file with `set -C` (noclobber), or use `flock`.
- uutils (ubuntu-latest): `timeout` signals only the command it started, so the command's children keep running — run the command in its own process group (`setsid`) and signal the group.

## Contracts

- **C1 — health body.** `GET /health` stays 200 and gains two keys: `classifier_unavailable: bool` (Task 11; true only while the stored classification purpose says `classifier_kind=local` and `torch` cannot be imported) and `pipeline_state: "ok" | "not_configured" | "read_only" | "failed_at_boot"` (Task 41).
- **C2 — buffer triage.** Each item of `GET /api/v1/memory-buffer` already carries `memory_id` (`UUID | None` in `BufferRowResponse`, a string or null on the wire: the pre-minted memory id from the row's metadata), which stays as it is, and gains one new field, `memory_exists: bool` (false when `memory_id` is null). The discard route `DELETE /api/v1/memory-buffer/{buffer_id}` keeps answering 204, deletes that memory through `MemoryService.delete_memory` when it exists, and reports it in the response header `X-Memory-Deleted: true|false`; the `buffer_discarded` event payload gains `memory_deleted: bool`.
- **C3 — code queries.** `CodeQueryService.resolve_repo(name_or_id: str) -> Repository` raises `RepoNotFound` or `RepoAmbiguous(candidates: list[Repository])`. `CodeQueryService.lookup_symbol(repo_id, name, file_path=None, owner=None, limit=50)` returns rows carrying `file_path` with no lazy load. `BlastRadiusRequest` gains a required `repo_id: UUID`; a symbol key that matches more than one symbol raises `SymbolAmbiguous(candidates)`, answered as HTTP 409 with `error.code = "symbol_ambiguous"` and `error.candidates` on REST and as an `ambiguous` envelope listing `candidates` on MCP. Every MCP code tool except `code_reindex` (the write door, which keeps its own repository lookup) reaches the database only through a `CodeQueryService` method.
- **C4 — removed wire keys.** After Tasks 17, 43 and 44: the flags answer of `GET /api/v1/config/feature-flags` carries no `w_context_boost`, `community_injection_enabled` or `flag_measurements`; the retrieval envelope's `excluded` object carries no `by_context_conflict`; `GET /api/v1/distribution` carries no `policy`, `watched` or `refresh`; `PUT /api/v1/distribution/policy` and `GET /api/v1/vectors/projection` do not exist.
- **C5 — session rotation.** `GET /api/v1/auth/me` and the answer of `POST /api/v1/auth/refresh` carry `expires_at` (ISO 8601, UTC). On a successful refresh or change-password the server closes every WebSocket bound to the presented token with code `4001` and reason `Session renewed`, before the blocklist write commits. A socket closed for expiry, epoch change or revocation keeps the existing reason `Session expired or revoked`.
- **C6 — config rows.** `app.services.config.patch_config_row(session, key, mutate) -> dict` locks the row (`SELECT … FOR UPDATE`, inserting it when absent), calls `mutate(current: dict) -> dict`, writes the result and commits.
- **C7 — revisions, in this order.** `backend/migrations/versions/0004_code_edge_file_indexes.py` (Task 30), `0005_drop_triple_embeddings.py` (Task 46), `0006_drop_blocks_search_vector.py` (Task 48). Each `down_revision` is the previous one; `0004` chains from `0003_board_views`.
- **C8 — fingerprint registration.** `embedder_registry.ensure_registered(session, fingerprint) -> None` is the one register-the-fingerprint helper (Task 33); no module keeps a private copy.
- **C9 — graph preview.** Each memory node of `GET /api/v1/graph/unified` carries `content` cut to at most 280 characters and `content_truncated: bool`; the full text is read from `GET /api/v1/memories/{id}`.
- **C10 — state boards.** `frontend/src/features/settings/components/settings-save-states.stories.tsx` (Task 55) and `frontend/src/components/app-chrome/load-failure-states.stories.tsx` (Task 50), each exporting one story per state, are the source of the A37 and A41 proof screenshots.
- **C11 — local helpers.** `.dforge/test-env.sh` exports `TEST_DATABASE_URL` and `BENCH_DATABASE_URL`; `.dforge/gate-legs.sh` runs every gate leg except the F1 bench and prints `ALL LEGS OK`.
- **C12 — lost-tag script.** `backend/scripts/restore_refine_project_tags.py` takes `--dry-run` (default), `--apply`, `--database-url <url>` and `--i-am-the-owner`. Without `--database-url` it reads `DATABASE_URL`, and then `--apply` without `--i-am-the-owner` exits 2 before any connection; with `--database-url` no owner flag is needed. A dry run prints one line per affected memory, `<memory_id>\t<comma-separated lost project/ tags>`, then `memories: <n>`, and writes nothing.
- **C13 — fact facets.** `FactListResponse.facets`: an object mapping each filterable field of the facts tab (the fields its select options are built from in `frontend/src/features/knowledge/use-facts.ts`) to the sorted list of distinct values among all facts in the request's project scope, independent of paging and of the other filters (Task 62).

## Assumptions (evidence)

- The riskiest assumption is that the findings are right as written. Evidence: the spec's own re-read of five findings on 2026-11-20 and the audit's fifteen fixes, each with a test that failed first. Global Constraints' verify-first rule bounds a wrong finding to its reproduction attempt, so no separate verifying task is needed.
- `./scripts/gate.sh` answers `GATE BLOCKED` on this checkout before any leg runs, because `backend/scripts/extraction_bench/.cache/manifest.json` is missing (gate preflight, read 2026-11-20; register row 228, the owner's). The Integration check is therefore `.dforge/gate-legs.sh`, every leg but the F1 bench; no task changes extraction prompts or schema, so the bench's subject is untouched.
- Task check rule 4: there is no `docs/dforge/gates.md`, the gate's last recorded runs in `.dforge/suites.tsv` are blocked or took over 200 s through per-session scripts, and `pytest-testmon` is not installed. Each task still runs its own tests.
- The dev Postgres container `darkmem-postgres-1` is up with `darkmem_test`, `darkmem_test_2..5` and `darkmem_bench` (`docker exec … psql`, 2026-11-20). Its password is `.env`'s `DB_PASSWORD`, which `.dforge/test-env.sh` reads.
- Alembic head is `0003_board_views` (`ls backend/migrations/versions`, 2026-11-20).
- Swap was at 7.2 of 8.0 GiB on 2026-11-20 (`free -h`), so `earlyoom` kills are likely during full-suite runs; exit 143 is re-run, not debugged.
- The 03:30 backup timer runs `scripts/backup.sh` from this checkout, so once Task 67 lands the branch's `backup.sh` is what runs against production that night (owner chose in-place work knowing this).
- Row ownership follows the spec: a finding two work packages list is closed by the first. Where a finding has a backend half and a frontend half, both tasks cite the row and the later one closes it.
- `frontend/src/*.ts(x)` and `*.css` count as UI files (`scripts/ui-proof paths`), so every task editing one carries a `**UI/UX:**` line even when it only deletes unused code; such a line cites OP-4.
- Register row 215 (requeue the 53 failed captures) and the deploy are production writes, which an auto run never performs. Row 215 is deferred with that reason; Task 71 holds the after-merge sequence, which is carried out once the run has finished and merged.
- The F1-19 preview (C9) means the graph page's text filter matches the first 280 characters of a memory and its tags, not the whole text. This follows the track's observation that the page needs content only for labels, the filter and the detail panel; the detail panel loads the full text on open.
- The SPA has no buffer list: `rg memory-buffer frontend/src` on 2026-11-20 matches one comment, and `triage-tab.tsx` lists `pipeline_failures` only. Ruling (the Opus ruling seat, `.dforge/rulings-preexec-4-report.md`): UX-12's confirmation lives in a new "Failed captures" section of the existing Activity → Triage tab, with Requeue and Discard. It adds no route and no tab, so OP-4 holds; it is hidden in demo mode; Requeue has no confirmation.
- `backend/scripts/e2e/run_e2e.py` reads no arguments today and exits 2 (`BLOCKED`) when the LAN endpoint does not serve the seeded extraction model (read 2026-11-20). Task 56 adds the argument pass-through and treats exit 2 as a missing toolchain, not a red test.
- Tasks 41 and 52 each read production once through a spelled-out `SELECT`; Global Constraints' Host limits names that exception. Every write and every other read uses the dev Postgres.
- P1-7 names no remedy in the track file. Decision: `release.sh` runs the floor gate and the three legs `CLAUDE.md` names for this host, and runs `gate.sh --full` only when called with `--full-gate`.

## Task index

1. Login attempt gate, off-loop bcrypt and the CORS fallback
2. API key verification cache
3. Destination, masked-secret and git credential hardening
4. Fork pull requests, pinned actions and guarded dev scripts
5. Read-only refusals on the reprocess routes and three MCP tools
6. Composition memory channel through search_ranked
7. Phase 5 write order, supersession predicate and GIN predicates
8. Extraction failure classes and the batch backstop
9. wait_process deadline and outcome
10. Discarding a failed capture deletes its memory
11. Local classifier refuses loudly
12. Buffer discard confirmation and classifier notice
13. Pipeline entry builder, importance and extraction module cleanups
14. Chat stream transaction, usage row and input bounds
15. One query embed and one compose pass
16. Shared RRF in code search and typed graph path ids
17. Remove the vector projection route and flag measurements
18. Lift and re-extraction interleave
19. Contradiction scan skip and vault journal hygiene
20. Vault lock scope and tick cost
21. Summary-only refine and the lost project-tag script
22. Strict journalling for dream and hygiene actions
23. Dream verdict memo and the unreachable contradiction arm
24. Article subject identity and synthesis budgets
25. Dream, article and research cleanups
26. Symbol and blast-radius queries in CodeQueryService
27. Remaining MCP code tools in CodeQueryService
28. Incremental indexing correctness
29. Clone, fetch and task-cancel safety
30. Drift scan and per-file delete cost
31. Stable code graph keys
32. Code indexing cleanups and last_commit_sha readers
33. Block vectors follow block text
34. Attachment lock scope
35. Document revision retention
36. Document read and write cost
37. Document door typing, attribution and dead exports
38. Function-scoped session and streaming twins
39. One config-row patch helper
40. Job state, floors and run records
41. Boot recovery, health state and partition maintenance
42. Socket revalidation cache and call-log flush
43. Remove the context-boost arm
44. Remove the inject trio and the Distribution policy
45. Settings without dead controls
46. Remove triple embeddings and drop its empty tables
47. Remove the fact-side stated-expiry arm
48. Drop blocks.search_vector and remove the PDF parser
49. Code screens: edit repository, blast radius, errors and copy
50. Load-failure pattern and its state board
51. Code canvas search dimming and re-centre
52. Graph payload preview and cluster names
53. Memory graph interactions
54. Graph render cost and dead exports
55. Settings save model and its state board
56. Session expiry and rotation on the server
57. Session renewal in the app
58. Shell lists, setup status and demo isolation
59. Unused frontend hooks and auth code
60. Chat streams per conversation
61. Document block editor refusals
62. Fact list facets
63. Knowledge queues: selection, paging and filter options
64. Notes, work log and board edits
65. Extension captures a settled reply once
66. Release tagging and CI suite coverage
67. Backup, restore and build script guards
68. Dead scripts and stale comments
69. Contract documents and counts
70. UI proof walkthrough
71. Revision proof on a restored backup and host reports

---

Every backend test command below is run from `backend/` after `. ../.dforge/test-env.sh`, with `timeout 900`; every frontend command from `frontend/`. Step 2 expects each new test to fail for the fault its contract names (or the verify-first rule applies); Step 4 expects every named test to pass.

### Task 1: Login attempt gate, off-loop bcrypt and the CORS fallback

**Files:**
- Modify: `backend/app/api/routes/auth.py`
- Modify: `backend/app/api/auth.py`
- Modify: `backend/app/services/login_rate_limit.py`
- Modify: `backend/app/main.py`
- Modify: `docker-compose.yml`
- Modify: `docker-compose.worker.yml`
- Test: `backend/tests/test_login_concurrency.py`
- Test: `backend/tests/test_cors_fallback.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 113, 116
**Depends on:** none
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 3 = 7
**Lenses:** security

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_login_concurrency.py::test_concurrent_wrong_passwords_verify_at_most_five` (integration, A7): given an initialised instance and twenty `POST /api/v1/auth/login` requests with a wrong password sent with `asyncio.gather` from one peer address, with `verify_password` wrapped by a counter, asserts the counter is at most 5 and the other responses are 429; fails today because the lockout is read before the first `await`, so all twenty verify.
- `::test_password_hashing_runs_off_the_event_loop` (integration, A7): given `verify_password` patched to record `threading.get_ident()`, one login records a thread id different from the event loop's; fails today because bcrypt runs inline. A second case does the same for `hash_password` through `POST /api/v1/auth/change-password`.
- `::test_in_flight_slot_is_released_on_error` (unit): given `verify_password` patched to raise, five failing logins followed by a wait past the lockout window leave the in-flight count for that address at 0.
- `backend/tests/test_cors_fallback.py::test_unset_cors_origins_allows_no_origin` (integration, A8): given `settings.cors_origins` empty, a `GET /api/v1/auth/me` with `Origin: http://localhost:3000` (and a second case with `http://localhost:5173`) returns no `access-control-allow-origin` header, and its `OPTIONS` preflight returns none either; fails today because `main.py` falls back to those two origins with credentials.
- `::test_configured_origin_is_still_allowed` (integration): given `cors_origins=["https://mem.example"]`, that origin gets `access-control-allow-origin: https://mem.example` and `access-control-allow-credentials: true`.
- `backend/tests/test_deployment_artifact.py::test_compose_files_pass_cors_origins` — extend the existing module: `docker-compose.yml` and `docker-compose.worker.yml` each set `CORS_ORIGINS` to `${CORS_ORIGINS:-[]}` on every app service.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_login_concurrency.py tests/test_cors_fallback.py tests/test_deployment_artifact.py`

- [ ] **Step 3: Implement**

1. B6-2: in the login handler, reserve an in-flight slot for the peer address in `login_rate_limit` before the first `await`; refuse with the existing 429 answer when `failed + in_flight >= threshold`; release the slot in a `finally`. The address is the one the limiter already keys on (transport peer, or the proxy rule when `trust_proxy_headers` is on); do not change that rule.
2. Run `verify_password` and `hash_password` through `asyncio.to_thread` at every awaited call site in `api/routes/auth.py` and the setup finalize path. Keep the 72-byte validation and the oversized-input failure path as they are.
3. B6-6: pass `settings.cors_origins` to `CORSMiddleware` with no fallback list; an empty list installs no allowed origin. Add `CORS_ORIGINS=${CORS_ORIGINS:-[]}` to the app services of both compose files.
4. Correct `CLAUDE.md`'s login-limiter sentence only if it states the old order; add nothing else.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_login_concurrency.py tests/test_cors_fallback.py tests/test_deployment_artifact.py tests/test_login_rate_limit_route.py tests/test_auth_security.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app/api backend/app/services/login_rate_limit.py backend/app/main.py backend/tests docker-compose.yml docker-compose.worker.yml
git commit -m "fix(auth): gate concurrent logins, drop CORS fallback"
```

### Task 2: API key verification cache

**Files:**
- Modify: `backend/app/services/api_keys.py`
- Modify: `backend/app/api/mcp/auth.py`
- Modify: `backend/app/api/routes/api_keys.py`
- Test: `backend/tests/test_api_key_cache.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 118
**Depends on:** none
**Evaluation:** files 1 - spec 2 - coupling 0 - risk 3 = 6
**Lenses:** security

- [ ] **Step 1: Write the failing test**

All in `backend/tests/test_api_key_cache.py`, with the bcrypt verify wrapped by a counter.

- `::test_second_call_within_window_verifies_no_bcrypt` (integration, A11): two keyed `tools/list` calls on `/mcp/` with one valid key verify bcrypt exactly once in total; fails today because every request verifies.
- `::test_entry_expires_after_sixty_seconds` (unit): with the cache clock advanced 61 s, the next call verifies again.
- `::test_revoked_key_is_refused_on_next_call` (integration, A11): after a cached call, `DELETE` (revoke) the key through its REST route; the next keyed call answers 401 and verifies no bcrypt.
- `::test_expired_key_is_refused_on_a_cache_hit` (integration, A11): a key whose `expires_at` passes after it was cached is refused 401 on its next call inside the 60 s window.
- `::test_verify_in_flight_during_revoke_caches_nothing` (unit): a verify that started before the revoke committed and finishes after it does not insert the principal (the revoked-id set is checked before insert), and the following call is refused.
- `::test_cache_key_is_a_digest` (unit): no cache key or value contains the presented token or its secret part; keys are 64-character hex strings.
- `::test_wrong_secret_for_cached_key_id_is_refused` (integration): a token with a cached key's id and a different secret answers 401.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_api_key_cache.py`

- [ ] **Step 3: Implement**

1. In `api_keys.py` add a module-level cache `sha256(token).hexdigest() -> (principal, key_id, expires_at, cached_at)` with a 60 s lifetime and a module-level set of revoked key ids. One comment says it relies on the single worker and on `restore-cycle.sh` stopping the app.
2. Verification: on a hit, refuse when the entry is older than 60 s, when `key_id` is in the revoked set, or when `expires_at` has passed (re-checked on every hit); otherwise return the principal without bcrypt. On a miss, verify as today and insert only if `key_id` is not in the revoked set at insert time.
3. The revoke path adds the key id to the revoked set after its commit and drops that key's entries.
4. Both the MCP auth path and the keyed REST dependency go through the one function; scope checks stay per call.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_api_key_cache.py tests/test_api_keys.py tests/test_mcp_auth.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/api_keys.py backend/app/api backend/tests/test_api_key_cache.py
git commit -m "perf(auth): cache verified API keys for 60 seconds"
```

### Task 3: Destination, masked-secret and git credential hardening

**Files:**
- Modify: `backend/app/services/backup_config.py`
- Modify: `backend/app/services/backup_ship.py`
- Modify: `backend/app/api/routes/llm_providers.py`
- Modify: `backend/app/services/repo_manager.py`
- Modify: `backend/app/services/code_pipeline.py`
- Modify: `backend/app/api/routes/repos.py`
- Test: `backend/tests/test_backup_config.py`
- Test: `backend/tests/test_masked_secret_rebinding.py`
- Test: `backend/tests/test_git_credential_exposure.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 117, 127, 89
**Depends on:** none
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 3 = 7
**Lenses:** security

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_backup_config.py::test_ssh_destination_refuses_option_shaped_fields` (unit, A9): saving an `ssh` destination with `user="-oProxyCommand=x"`, with `host="-oProxyCommand=x"`, with `host="a b"`, or with `remote_dir="/srv\n-rf"` raises the module's validation error naming the field; `user="backup"`, `host="192.168.0.50"` and `host="nas.lan"` save. Fails today because `_validate` checks none of them.
- `backend/tests/test_masked_secret_rebinding.py::test_destination_host_change_needs_the_secret_again` (integration, A10): a stored `worker` or `ssh` destination saved again with its secret field masked and a changed `host` (or URL) answers 422 with a message naming the secret field; the same save with the host unchanged succeeds and keeps the stored secret.
- `::test_provider_url_change_needs_the_key_again` (integration, A10): `PUT` on an LLM provider with `api_key` masked and a changed `base_url` or `api_kind` answers 422; with the key re-entered it succeeds. Fails today because the masked secret is resolved by name.
- `backend/tests/test_git_credential_exposure.py::test_token_never_appears_in_git_argv` (unit): with `asyncio.create_subprocess_exec` patched to capture arguments, an authenticated fetch and an authenticated clone pass no argument containing the token; the credential travels in the child environment.
- `::test_stored_failure_text_is_sanitised` (integration): an index run whose git step raises `RuntimeError("fatal: https://user:tok123@host/x.git not found")` stores a `status_message`, a `pipeline_failures.error_message` and a websocket error none of which contains `tok123`.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_backup_config.py tests/test_masked_secret_rebinding.py tests/test_git_credential_exposure.py`

- [ ] **Step 3: Implement**

1. B6-7: in `backup_config._validate`, `user` must match `^[A-Za-z0-9._-]+$` and not start with `-`; `host` must be a hostname or IP literal (no leading `-`, no whitespace); `remote_dir` holds no `\n` or `\r`. Keep `--` before positional arguments in `backup_ship`.
2. B6-18: a masked secret is accepted only when every connection field of that row (`host`, `port`, URL, `base_url`, `api_kind`, `user`) equals the stored value; otherwise 422 asking for the secret again. Apply in `backup_config` and the provider `PUT`. The judge-provider guard in `llm_provider_guard.py` is untouched.
3. B4-19: route every stored or broadcast exception string in `code_pipeline.py`, `repos.py` and `repo_manager.py` through the existing URL sanitiser; pass git credentials through the child environment (`GIT_ASKPASS` or `GIT_CONFIG_*` `http.extraHeader`) instead of the URL, and keep scrubbing `.git/config` after a clone.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_backup_config.py tests/test_masked_secret_rebinding.py tests/test_git_credential_exposure.py tests/test_code_pipeline.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests
git commit -m "fix(security): validate ssh fields, rebind secrets"
```

### Task 4: Fork pull requests, pinned actions and guarded dev scripts

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/release.yml`
- Modify: `.github/workflows/cache-cleanup.yml`
- Modify: `scripts/pick_runner.py`
- Modify: `scripts/start_dev_server.sh`
- Modify: `backend/scripts/e2e/e2e_db.py`
- Modify: `docs/runbook-ci.md`
- Test: `backend/tests/test_ci_workflows.py`
- Test: `backend/tests/test_dev_script_guards.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 191, 194, 197, 199
**Depends on:** none
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 3 = 7
**Lenses:** security, lang-bash

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_ci_workflows.py::test_fork_pull_request_never_reaches_self_hosted` (unit, A6): parsing `ci.yml`, every job whose `runs-on` can resolve to `darkmem-linux` or `self-hosted` carries an `if` that is false when `github.event.pull_request.head.repo.full_name != github.repository`; fails today because `e2e` has no such condition.
- `::test_picker_routes_a_fork_to_hosted` (unit, A6): `pick_runner` called with the fork marker set (the environment variable the workflow passes from the same expression) returns `ubuntu-latest` in every mode, including when no picker token is present; fails today because a tokenless picker queues on self-hosted.
- `::test_third_party_actions_are_pinned_to_shas` (unit): in all three workflow files, every `uses:` naming an action outside `actions/` and `github/` is pinned to a 40-character commit sha with the tag in a trailing comment.
- `::test_scan_job_does_not_write_the_publish_cache` (unit): the trivy scan job's build step has no `cache-to`, or a scope different from the publish job's `cache-from`.
- `backend/tests/test_dev_script_guards.py::test_start_dev_server_refuses_without_database_url` (integration, bash): the test never runs the script in place. It copies `scripts/start_dev_server.sh` into `<tmp>/scripts/`, creates `<tmp>/backend/.venv/bin/python` and, in a directory put first on `PATH`, `python`, `pip`, `alembic` and `uvicorn`, each a stub that appends its arguments to `<tmp>/calls.log` and exits 0, then runs the copy under `timeout 10` with `DATABASE_URL` unset. It asserts a non-zero exit that is not 124, a printed line naming `DATABASE_URL`, and an empty `calls.log`; a second case with `DATABASE_URL` set asserts the first logged call is the venv stub with `-m alembic upgrade head` and that no call came from the bare `python` stub. Fails today because the bare `python` stub is called with `-m alembic upgrade head` and the script exits 0. The stubs are what keep the red run from migrating port 5432 or binding `:8000`.
- `::test_e2e_reset_refuses_a_non_disposable_database` (unit): `e2e_db`'s reset raises before any SQL when the target database name does not match the suite's disposable pattern or the port is 5432; the destructive-SQL guard's exemption text no longer claims it never touches an ambient database.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_ci_workflows.py tests/test_dev_script_guards.py`

- [ ] **Step 3: Implement**

1. P1-2 (code half): add the head-repository condition to the `e2e` job and to every job on a picked runner; pass a fork marker into `pick-runner` and make `pick_runner.py` answer `ubuntu-latest` for it first. Do not change any GitHub setting; `docs/runbook-ci.md` gains one sentence on the rule.
2. P1-5: pin every third-party action to its commit sha (resolve each with `gh api repos/<owner>/<repo>/git/ref/tags/<tag>`, read-only), and separate the scan job's cache from the publish job's.
3. P1-10: `start_dev_server.sh` resolves `backend/.venv/bin/python`, exits 1 with a message when `DATABASE_URL` is unset, and keeps `--no-proxy-headers` and `--timeout-keep-alive 75`.
4. P1-8: `e2e_db.py` checks the database name and port before `DROP SCHEMA`, and its guard exemption states the check it now relies on.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_ci_workflows.py tests/test_dev_script_guards.py tests/test_single_worker_invariant.py`

- [ ] **Step 5: Commit**

```bash
git add .github scripts backend/scripts/e2e backend/tests docs/runbook-ci.md
git commit -m "fix(ci): keep fork pull requests off the LAN runner"
```

### Task 5: Read-only refusals on the reprocess routes and three MCP tools

**Files:**
- Modify: `backend/app/api/routes/analytics.py`
- Modify: `backend/app/api/routes/pipeline_failures.py`
- Modify: `backend/app/api/mcp/server.py`
- Modify: `CLAUDE.md`
- Test: `backend/tests/test_read_only_doors.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 6, 114
**Depends on:** none
**Evaluation:** files 1 - spec 2 - coupling 0 - risk 2 = 5

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_read_only_doors.py::test_reprocess_routes_and_three_mcp_tools_are_refused` (integration, A12): with `DARKMEM_READ_ONLY` on and the LLM orchestrator replaced by a spy, each of the two reprocess routes in `api/routes/analytics.py` and the two retry routes in `api/routes/pipeline_failures.py` answers 403 with `error.code = "read_only"`, and MCP `memory_reason`, `memory_overview` and `document_search` each answer the read-only refusal envelope; the spy records zero `embed` and zero `chat_completion` calls. Fails today because the four routes carry no `refuse_when_read_only` and the three tools dial the provider.
- `::test_read_only_parity_between_doors` (integration): for every REST route that `refuse_when_read_only` guards and that has an MCP twin in `docs/two-door-parity.md`'s generated block, the twin tool is refused too.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_read_only_doors.py`

- [ ] **Step 3: Implement**

1. B1-7: add `Depends(refuse_when_read_only)` to the four routes.
2. B6-3: refuse the three tools under `settings.read_only` before any provider call, with the envelope the other refused MCP paths use; keep `memory_search` and `code_search` answering on their keyword arms.
3. Add the routes and tools to the read-only list in `CLAUDE.md`'s backup-worker paragraph.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_read_only_doors.py tests/test_read_only_boot.py tests/test_door_parity.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app/api backend/tests/test_read_only_doors.py CLAUDE.md
git commit -m "fix(read-only): refuse reprocess and three MCP tools"
```

### Task 6: Composition memory channel through search_ranked

**Files:**
- Modify: `backend/app/services/layer_composition.py`
- Modify: `backend/app/services/hybrid_search.py`
- Modify: `CLAUDE.md`
- Test: `backend/tests/test_chat_retrieval_parity.py`
- Test: `backend/tests/test_access_rank_signals.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 19, 35
**Depends on:** none
**Evaluation:** files 1 - spec 2 - coupling 1 - risk 2 = 6

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_chat_retrieval_parity.py::test_the_doors_rank_alike_with_each_search_flag_flipped` (integration, A13): three cases, each seeding at least six memories with distinct `confidence` and `importance` and stubbing the reranker to a fixed scoring: with `hybrid_search_enabled` flipped to false, with `reranker_enabled` flipped to true, and with `confidence_rank_gamma` set to 0.5, the memory order returned by chat retrieval, by `POST /api/v1/knowledge/search`, by MCP `knowledge_search` and by `memory_search` is identical. Fails today because the composition's memory channel ignores the first two flags and its rows carry no `confidence` or `importance`.
- `backend/tests/test_access_rank_signals.py::test_access_is_recorded_with_hybrid_off` (integration): with `hybrid_search_enabled` false, a memory search (and a second case in read-only mode, where no write happens and no error is raised) calls `_record_access` for the returned ids in the non-read-only case; fails today because the pure-vector branch returns before it.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_chat_retrieval_parity.py tests/test_access_rank_signals.py`

- [ ] **Step 3: Implement**

1. B2-2: the composition's memory channel calls `HybridSearchService.search_ranked(with_trace=True)` and carries `confidence` and `importance` on each memory row so the rank arms read them. The parity test still asserts order, not shape.
2. B2-21: call `_record_access` in the pure-vector branch; the read-only branch stays write-free.
3. Correct `CLAUDE.md`'s "Chat retrieval is the same path" paragraph to name `search_ranked`.
4. The existing `test_an_activated_rank_arm_still_moves_one_door_and_not_the_other` pins the split this task removes for the confidence and importance arms: rewrite it to assert that an activated `w_importance` moves both doors to the same order, and keep its heat and recency cases as they are if they still hold.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_chat_retrieval_parity.py tests/test_access_rank_signals.py tests/test_layer_composition.py tests/test_ranking_arms_zero.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services backend/tests CLAUDE.md
git commit -m "fix(retrieval): chat honours the search flags"
```

### Task 7: Phase 5 write order, supersession predicate and GIN predicates

**Files:**
- Modify: `backend/app/services/pipeline.py`
- Modify: `backend/app/services/supersession.py`
- Modify: `backend/app/repositories/graph.py`
- Modify: `backend/app/services/fact_provenance.py`
- Test: `backend/tests/test_phase5_concurrency.py`
- Test: `backend/tests/test_supersession.py`
- Test: `backend/tests/test_graph_repo.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 2, 3, 4
**Depends on:** none
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 3 = 7

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_phase5_concurrency.py::test_shared_entities_written_in_opposite_order_both_commit` (integration, A16): two sessions run the Phase 5 graph write for two memories whose extractions list the same two entities and one relation in opposite orders, each pausing (an `asyncio.Event`) after its first upsert; both commit and neither raises a deadlock error. Fails today because the upserts follow extraction order.
- `backend/tests/test_supersession.py::test_concurrent_supersessions_leave_one_pointer_and_one_event` (integration, A15): two sessions each run `detect_supersessions` for a different new memory against one shared active candidate and commit one after the other; the candidate's `superseded_by` is the first committer's id, and exactly one `superseded` event exists for it. Fails today because the UPDATE has no `status = 'active'` predicate.
- `backend/tests/test_graph_repo.py::test_memory_id_predicates_use_the_gin_index` (integration, A17): with `enable_seqscan` off for the session and 200 seeded entities and relations, `EXPLAIN` of each of the statements behind `delete_by_memory_id`, the per-memory entity and relation reads and the provenance read names `ix_entities_memory_ids` or the relations' GIN index; fails today because `:mid = ANY(memory_ids)` cannot use it.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_phase5_concurrency.py tests/test_supersession.py tests/test_graph_repo.py`

- [ ] **Step 3: Implement**

1. B1-3: inside savepoint B sort entities by `(name, entity_type)` and relations by `(source, target, rel_type)` before writing; the strip stays first and inside the savepoint.
2. B1-4: add `status == 'active'` and `RETURNING id` to the supersession UPDATE and journal only the returned ids, on both the preexisting and the same-batch path.
3. B1-5: rewrite each `:mid = ANY(memory_ids)` predicate as `memory_ids @> ARRAY[CAST(:mid AS uuid)]` in `repositories/graph.py` and `fact_provenance.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_phase5_concurrency.py tests/test_supersession.py tests/test_graph_repo.py tests/test_pipeline_savepoints.py tests/test_graph_orphan_cleanup.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests
git commit -m "fix(pipeline): order phase 5 writes, guard supersede"
```

### Task 8: Extraction failure classes and the batch backstop

**Files:**
- Modify: `backend/app/services/extraction.py`
- Modify: `backend/app/services/pipeline.py`
- Modify: `backend/app/services/buffer_flush.py`
- Modify: `CLAUDE.md`
- Test: `backend/tests/test_pipeline_savepoints.py`
- Test: `backend/tests/test_buffer_flush.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 1, 7, 14
**Depends on:** none
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 2 = 6

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_buffer_flush.py::test_transient_extraction_failure_is_retried` (integration): with the real `ExtractionService` over an LLM stub raising a timeout (and second cases for HTTP 429 and a connection error), the flush leaves the buffer row `pending` with its attempt counted and no memory graph written; a later flush with the stub answering processes it to `done`. Fails today because every `_error` result marks the row done.
- `::test_deterministic_extraction_failure_settles_without_retry` (integration): with the stub returning unparseable JSON on every call, the row settles `done`, the memory keeps its vector, `extract` status is `error`, and one `pipeline_failures` row exists.
- `backend/tests/test_pipeline_savepoints.py::test_reconciliation_failure_keeps_committed_statuses` (integration): with the same-batch reconciliation SELECT patched to raise, every memory of the batch keeps the statuses its Phase 5 write committed, no `pipeline_failures` row is added for vector or graph, and the error is logged once. Fails today because the backstop overwrites them.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_pipeline_savepoints.py tests/test_buffer_flush.py`

- [ ] **Step 3: Implement**

1. B1-1 remainder: `extract()` marks its `_error` result `transient` for timeouts, connection errors, HTTP 429 and 5xx, and `deterministic` otherwise. The pipeline reports a transient failure as a hard step so `buffer_flush` returns the row to `pending` within `buffer_max_attempts`; a deterministic one keeps today's `extract="error"` path, which skips savepoint B.
2. B1-8: give the reconciliation block its own `try`/`except` that logs and keeps `normalized`.
3. B1-18: remove the `isinstance(extraction, Exception)` branch and the unreachable `except` in `run_extract`.
4. Add one sentence to `CLAUDE.md`'s buffer paragraph: a transient extraction failure is retried by the buffer.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_pipeline_savepoints.py tests/test_buffer_flush.py tests/test_buffer_flush_runner.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services backend/tests CLAUDE.md
git commit -m "fix(pipeline): retry transient extraction failures"
```

### Task 9: wait_process deadline and outcome

**Files:**
- Modify: `backend/app/services/wait_process.py`
- Modify: `backend/app/services/memory.py`
- Modify: `backend/app/services/buffer_flush.py`
- Modify: `backend/app/config.py`
- Modify: `backend/app/api/routes/memories.py`
- Modify: `backend/app/api/mcp/server.py`
- Modify: `CLAUDE.md`
- Test: `backend/tests/test_wait_process.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 5, 8, 18
**Depends on:** Task 8
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 3 = 7

- [ ] **Step 1: Write the failing test**

All in `backend/tests/test_wait_process.py`.

- `::test_deadline_returns_ack_and_flush_finishes` (integration, A18): with the pipeline stubbed to take longer than the wait timeout (patched to 0.2 s), `POST /api/v1/memories?wait_process=true` answers 202 with the `CaptureAck`; after the stub is released the buffer row is `done`, its `attempts` is 1, the memory has a vector, and the LLM stub was called once. Fails today because the flush is cancelled at the deadline and the row stays claimed.
- `::test_background_flush_is_tracked_and_cancelled_at_shutdown` (unit): the continuing flush is registered with the app's task tracker, runs on a session of its own, and is awaited or cancelled by the shutdown path with its row returned to `pending`.
- `::test_hard_failed_replay_answers_the_ack` (integration, A18): a capture whose inline flush hard-fails and is released back to `pending` answers 202 with the ack, never 201; fails today because the 201 decision ignores `ClaimedFlushResult.done`.
- `::test_wait_timeout_is_a_module_constant` (unit): `app.services.memory.BUFFER_WAIT_TIMEOUT_SECONDS == 10`, and `FEATURE_FLAGS_DEFAULTS` has no `buffer_wait_timeout_seconds` key.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_wait_process.py`

- [ ] **Step 3: Implement**

1. B1-6: at the deadline return the ack and let the flush continue as a tracked background task holding its own session and its LLM lease; never cancel it from the request. The claim, the attempt count and the `FOR UPDATE SKIP LOCKED` path are unchanged.
2. B1-9: answer 201 only when `ClaimedFlushResult.done` is true for that row.
3. B1-22: replace the flag with the module constant and remove its default from `config.py`; correct `CLAUDE.md`'s `buffer_wait_timeout_seconds` mention to the constant, and reword the three MCP tool descriptions in `server.py` that name the flag (`rg buffer_wait_timeout_seconds backend/app` lists them) to say the wait is 10 seconds.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_wait_process.py tests/test_memory_buffer.py tests/test_session_resource_lifetimes.py tests/test_prompt_agent_instructions.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests/test_wait_process.py CLAUDE.md
git commit -m "fix(capture): let a slow inline flush finish"
```

### Task 10: Discarding a failed capture deletes its memory

**Files:**
- Modify: `backend/app/services/buffer_monitor.py`
- Modify: `backend/app/api/routes/buffer.py`
- Modify: `backend/app/schemas/buffer.py`
- Modify: `CLAUDE.md`
- Test: `backend/tests/test_memory_buffer.py`

**Interfaces:**
- Consumes: none
- Produces: C2

**Items:** 9
**Depends on:** none
**Evaluation:** files 1 - spec 2 - coupling 2 - risk 2 = 7

- [ ] **Step 1: Write the failing test**

All in `backend/tests/test_memory_buffer.py`.

- `::test_buffer_items_report_their_memory` (integration): an `error` row whose memory row was materialised lists with `memory_id` equal to the pre-minted id and `memory_exists: true`; one whose memory was never written lists `memory_exists: false`.
- `::test_discard_deletes_the_materialised_memory` (integration, A55 server half): discarding the first row answers 204 with `X-Memory-Deleted: true`, the memory row is gone, and the `buffer_discarded` event payload carries `memory_deleted: true`; discarding the second answers 204 with `X-Memory-Deleted: false`. Fails today because the memory survives with no vector or graph.
- `::test_discard_demotes_dependents_first` (integration): when the materialised memory is referenced by another memory's `superseded_by`, the discard succeeds and that dependent is `deprecated` with `superseded_by` NULL.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_memory_buffer.py`

- [ ] **Step 3: Implement**

1. Per C2: add `memory_exists` to the list item schema (one query for existence over the page's ids, no per-row query; `memory_id` is already served and is not changed) and the `X-Memory-Deleted` header to the discard answer.
2. The discard calls `MemoryService.delete_memory` for an existing memory in the same transaction as the buffer row's settlement, journalling `buffer_discarded` as today with the new key.
3. Correct `CLAUDE.md`'s sentence on discard to say it deletes the materialised memory.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_memory_buffer.py tests/test_api/test_rest_conformance.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests/test_memory_buffer.py CLAUDE.md
git commit -m "fix(buffer): discard deletes the stranded memory"
```

### Task 11: Local classifier refuses loudly

**Files:**
- Modify: `backend/app/services/pipeline.py`
- Modify: `backend/app/services/ml_runtime.py`
- Modify: `backend/app/api/routes/config.py`
- Modify: `backend/app/main.py`
- Modify: `backend/pyproject.toml`
- Modify: `CLAUDE.md`
- Test: `backend/tests/test_local_classifier_availability.py`

**Interfaces:**
- Consumes: none
- Produces: C1 (`classifier_unavailable`)

**Items:** 13
**Depends on:** none
**Evaluation:** files 1 - spec 2 - coupling 2 - risk 2 = 7

- [ ] **Step 1: Write the failing test**

All in `backend/tests/test_local_classifier_availability.py`, with the torch import probe patched to fail.

- `::test_saving_local_without_torch_is_refused` (integration, A19): the purpose write that sets `classifier_kind=local` on `classification` answers 422 with a message naming torch; with the probe patched to succeed it saves. Fails today because the save is accepted.
- `::test_stored_local_row_classifies_with_the_llm` (integration, A19): with a stored `local` row and no torch, a processed batch fills `classified_type`, `summary`, `emotions` and `flags` through the LLM classifier under the single-call merge rule, and the error log line is emitted once across two batches.
- `::test_health_reports_classifier_unavailable` (integration, A19): `GET /health` answers 200 with `classifier_unavailable: true` in that state and `false` when the row says `llm`.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_local_classifier_availability.py`

- [ ] **Step 3: Implement**

1. One availability probe in `ml_runtime.py` (import check, cached per process). The purpose write refuses `local` with 422 while it fails.
2. The per-batch classifier choice keeps the LLM classifier when the probe fails, logs one error per process, and the health route reads the stored kind plus the probe for C1.
3. Replace the stale comment on the `ml` extra in `pyproject.toml` (it names a regex classifier and an ML Profiles tab) with one line saying what the extra enables.
4. `CLAUDE.md`'s Phase 2 paragraph gains the refusal and the fallback in one sentence.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_local_classifier_availability.py tests/test_health.py tests/test_llm_config.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/pyproject.toml backend/tests/test_local_classifier_availability.py CLAUDE.md
git commit -m "fix(classify): refuse local classifier without torch"
```

### Task 12: Buffer discard confirmation and classifier notice

**Files:**
- Create: `frontend/src/hooks/api/use-memory-buffer-api.ts`
- Create: `frontend/src/features/activity/components/failed-captures-section.tsx`
- Create: `frontend/src/features/activity/components/failed-captures-section.stories.tsx`
- Modify: `frontend/src/hooks/api/index.ts`
- Modify: `frontend/src/features/activity/components/triage-tab.tsx`
- Modify: `frontend/src/features/settings/components/llm-tab.tsx`
- Modify: `frontend/src/features/settings/use-llm-tab-binding.ts`
- Test: `frontend/src/hooks/api/__tests__/use-memory-buffer-api.test.tsx`
- Test: `frontend/src/hooks/api/__tests__/use-memory-buffer-api.demo.test.tsx`
- Test: `frontend/src/features/activity/__tests__/failed-captures-section.test.tsx`
- Test: `frontend/src/features/activity/__tests__/failed-captures-section.demo.test.tsx`
- Test: `frontend/src/features/settings/components/llm-tab.classifier.test.tsx`

**Interfaces:**
- Consumes: C1 (`classifier_unavailable`), C2
- Produces: none

**Items:** 9, 13
**UI/UX:** UX-12, UI-6
**Depends on:** Task 10, Task 11
**Evaluation:** files 2 - spec 2 - coupling 1 - risk 1 = 6

The SPA has no buffer list today: `triage-tab.tsx` lists `pipeline_failures` only and no frontend file calls `/api/v1/memory-buffer`. UX-12's confirmation therefore lives in a new "Failed captures" section of the existing Activity → Triage tab (ruling recorded in Assumptions): no new route, no new tab.

- [ ] **Step 1: Write the failing test**

The demo flag is set once per file with the hoisted `vi.mock("@/lib/demo-flag", …)` this repository uses, so the demo cases sit in their own `.demo.test.tsx` files, as `use-feed.demo.test.tsx` and `use-feed.real.test.tsx` do. `FailedCapturesSection` takes its data as props (`items`, `total`, `isLoading`, `isError`, `onRequeue`, `onDiscard`, the last two returning promises); the component tests render it with props, and `triage-tab.tsx` feeds it from the hooks.

- `use-memory-buffer-api.test.tsx::lists poison rows` (unit): `useMemoryBufferItems()` requests `GET /api/v1/memory-buffer?state=poison&limit=200` once and returns the answer's `items` and `total`. Fails today because the module does not exist.
- `use-memory-buffer-api.demo.test.tsx::sends nothing in demo mode` (unit): with the demo flag on, `useMemoryBufferItems()` sends no request and returns an empty list.
- `use-memory-buffer-api.test.tsx::discard and requeue invalidate the list` (unit): `useDiscardBufferItem().mutateAsync(id)` sends `DELETE /api/v1/memory-buffer/<id>` once and `useRequeueBufferItem().mutateAsync(id)` sends `POST /api/v1/memory-buffer/<id>/requeue` once; each success invalidates the `["memoryBuffer"]` query key, and the discard also invalidates `["memories"]`.
- `failed-captures-section.test.tsx::lists failed captures with their error` (unit): given two items as props the section titled "Failed captures" renders each row's `content_preview`, `project`, "`<attempts>` of `<max_attempts>` attempts" and `last_error`; with `total` 230 and 200 items it shows the line "Showing the newest 200 of 230"; with no items it renders the empty state titled "No failed captures"; with `isError` true it renders the failed state titled "Couldn't load failed captures".
- `::names the memory and deletes only on confirm` (unit, A55): for a row with `memory_exists: true`, pressing Discard opens the alert dialog titled "Discard this capture?" whose description contains the memory's short id (`shortId(memory_id)`) and the sentence "This also deletes the memory."; Cancel calls nothing; the destructive Discard button calls `onDiscard` once with the row's id and focus returns to the row's Discard button when the dialog closes.
- `::a row without a memory does not mention one` (unit): for `memory_exists: false` the dialog description is "The capture is removed from the queue." and contains no "memory".
- `::requeue runs at once and reports a refusal` (unit): pressing Requeue calls `onRequeue` once with the row's id and opens no dialog; a rejected promise keeps the row listed and shows an error toast.
- `::reports a failed discard` (unit): a rejected `onDiscard` keeps the row listed and shows an error toast.
- `failed-captures-section.demo.test.tsx::the triage tab shows no failed captures in demo mode` (unit): the Triage tab rendered with the demo flag on has no "Failed captures" heading and sends no `/api/v1/memory-buffer` request.
- `llm-tab.classifier.test.tsx::shows the unavailable line` (unit, A19): with `/health` answering `classifier_unavailable: true`, the classification purpose row shows "Local classifier unavailable, using the LLM classifier"; with `false` it does not; in demo mode no `/health` request is made.

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/hooks/api/__tests__/use-memory-buffer-api.test.tsx src/hooks/api/__tests__/use-memory-buffer-api.demo.test.tsx src/features/activity/__tests__/failed-captures-section.test.tsx src/features/activity/__tests__/failed-captures-section.demo.test.tsx src/features/settings/components/llm-tab.classifier.test.tsx`

- [ ] **Step 3: Implement**

1. `use-memory-buffer-api.ts`: the three hooks above, typed from `BufferRowResponse` plus C2's `memory_exists`, following `use-pipeline-api.ts`'s fetch, query-key and `enabled: !DEMO` conventions; export the module from `hooks/api/index.ts`.
2. `failed-captures-section.tsx`: a second `ModuleSurface` titled "Failed captures", taking the props named above, rendered by `triage-tab.tsx` under "Failure triage" from the three hooks and only when the demo flag is off. Rows reuse the tab's `listItemClass` row and its `EmptyState` kinds for the loading, empty and failed states; nothing here is a new local component the library already ships.
3. UX-12: Discard opens the same `AlertDialog` pattern the tab's Forget action uses, with the texts the tests name and the destructive variant on the confirm button; Requeue has no confirmation.
4. `failed-captures-section.stories.tsx`: one story per state, fed by props with no request: empty, one row, 200 rows of 230, a row whose `last_error` is a 400-character unbroken line, a failed load, and the discard dialog open for a row with a memory. Task 70 takes UX-12's screenshots from these stories.
5. UI-6: read `classifier_unavailable` through the existing health query (add `enabled: !DEMO`), and render the line as the library's inline warning text under the classification purpose.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/hooks/api src/features/activity src/features/settings && npm run typecheck`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/api frontend/src/features/activity frontend/src/features/settings
git commit -m "feat(ui): triage failed captures, flag classifier"
```

### Task 13: Pipeline entry builder, importance and extraction module cleanups

**Files:**
- Modify: `backend/app/services/pipeline.py`
- Modify: `backend/app/api/routes/pipeline_failures.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/services/analytics.py`
- Modify: `backend/app/api/routes/reembed.py`
- Modify: `backend/app/services/extraction.py`
- Modify: `backend/app/services/extraction_clean.py`
- Modify: `backend/app/services/classification_llm.py`
- Modify: `backend/app/services/memory.py`
- Modify: `backend/scripts/eval_round3/debug_clean.py`
- Test: `backend/tests/test_pipeline_entries.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 10, 11, 12, 15, 16, 17
**Depends on:** Task 8
**Evaluation:** files 3 - spec 2 - coupling 0 - risk 1 = 6

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_pipeline_entries.py::test_every_retry_door_carries_the_project` (integration): a memory in project `alpha` sent through the failure-retry route, through the reprocess route and through the boot replay each reaches `process_batch` with `project == "alpha"`; fails today because two of the three builders omit it.
- `::test_caller_importance_survives_extraction` (integration): a capture with `importance=0.9` whose extraction returns `0.3` (and a second case where extraction fails) stores `0.9`; a capture that left the default stores the extractor's value. Fails today because the extractor always wins.
- `::test_reasoning_budget_is_its_own_constant` (unit): `app.services.memory.REASONING_CONTEXT_CHARS` exists, and `_MAX_CONTENT_CHARS` is defined in exactly one module (an AST scan over `app/services`).
- Removals with no new test (the existing suite is their check): B1-12 delegates `pipeline._get_feature_flags` to `feature_flags.get_feature_flags_dict` and repoints both callers; B1-19 drops the `__all__` shim and star re-export, repointing the test modules and scripts that import pass helpers to `extraction_clean`; B1-20 makes `debug_clean.py` call `_build_extraction_schema()` and removes `EXTRACTION_SCHEMA`.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_pipeline_entries.py`

- [ ] **Step 3: Implement**

1. B1-11: one `build_pipeline_entry(memory)` helper in `pipeline.py`, used by all three sites.
2. B1-13: fill `importance` from the extractor only when the stored value equals the schema default.
3. B1-21: declare `_MAX_CONTENT_CHARS` once in `extraction_clean.py`, import it in `classification_llm.py`, and give reasoning `REASONING_CONTEXT_CHARS = 6000` in `memory.py`.
4. B1-12, B1-19, B1-20 as listed in Step 1; run `rg` for each removed name before deleting it.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_pipeline_entries.py tests/test_pipeline_savepoints.py tests/unit && .venv/bin/python -m pytest -q scripts/benchlib/tests`

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/scripts backend/tests
git commit -m "refactor(pipeline): one entry builder, fewer shims"
```

### Task 14: Chat stream transaction, usage row and input bounds

**Files:**
- Modify: `backend/app/services/chat.py`
- Modify: `backend/app/schemas/chat.py`
- Modify: `backend/app/services/llm.py`
- Modify: `backend/app/services/usage_recorder.py`
- Test: `backend/tests/test_chat.py`
- Test: `backend/tests/test_chat_stream_resources.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 21, 22, 33, 34
**Depends on:** none
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 2 = 6

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_chat_stream_resources.py::test_no_transaction_is_open_during_the_stream` (integration): with the LLM stream stubbed to pause on an event, while it is paused the chat session reports `in_transaction() is False`; fails today because the retrieval and prompt SELECTs leave one open.
- `::test_usage_row_survives_a_client_disconnect` (integration): cancelling the streaming task mid-answer still writes one `llm_usage` row with `ok = False` and `error_kind = "cancelled"`; fails today because the `finally` write is cancelled with the task.
- `backend/tests/test_chat.py::test_overlong_content_is_refused` (integration): a chat request whose `content` exceeds the schema's `max_length` (32,000 characters) answers 422 and stores no message.
- `::test_non_string_mention_is_refused_before_the_stream` (integration): a request whose `context.mentions` holds an integer answers 422 and stores no user message; fails today with an `AttributeError` after the user message is committed.
- Removal with no new test: B2-20 deletes `CLUSTER_RE` and the `cluster:` filter branch (`rg CLUSTER_RE backend` shows no other reader).

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_chat.py tests/test_chat_stream_resources.py`

- [ ] **Step 3: Implement**

1. B2-6: commit (or roll back) the chat session right after `_build_prompt`, before the stream starts; the answer write after the stream opens its own short transaction.
2. B2-7: record usage through a shielded call (or a spawned task that transfers the lease) and record `ok=False, error_kind="cancelled"` on `CancelledError`, then re-raise.
3. B2-19: a typed `ChatContext` model (`mentions: list[str]`, the other keys the service reads) and `max_length=32000` on `content`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_chat.py tests/test_chat_stream_resources.py tests/test_chat_history_budget.py tests/test_session_resource_lifetimes.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests
git commit -m "fix(chat): free the connection during the stream"
```

### Task 15: One query embed and one compose pass

**Files:**
- Modify: `backend/app/services/layer_composition.py`
- Modify: `backend/app/services/hybrid_search.py`
- Modify: `backend/app/services/articles_channel.py`
- Modify: `backend/app/services/facts_channel.py`
- Test: `backend/tests/test_layer_composition.py`
- Test: `backend/tests/test_rrf_fusion.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 23, 24, 30, 31
**Depends on:** Task 6
**Evaluation:** files 2 - spec 2 - coupling 1 - risk 2 = 7

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_layer_composition.py::test_project_scoped_search_embeds_the_query_once` (integration): a project-scoped `LayerCompositionService.search` with a live article in the project calls the LLM stub's `embed` exactly once; fails today with two calls (memory channel and articles channel).
- `::test_compose_runs_once_per_request` (integration): with `compose` wrapped by a counter, one search calls it once; fails today because a provisional pass feeds a reranker no production caller passes.
- `backend/tests/test_rrf_fusion.py::test_search_is_search_with_trace_results` (unit): for a seeded corpus and each of three queries, `HybridSearchService.search(...)` equals `(await search_with_trace(...)).results` element for element, and `search`'s body contains no fusion call of its own (an AST check that it delegates).
- Removal with no new test: B2-16 deletes `FactsChannel.search`, `_dispute_label` and the row's `dispute` key, and corrects the docstring that says `channel_status` has no consumer; tests that exist only for the removed method go with it.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_layer_composition.py tests/test_rrf_fusion.py`

- [ ] **Step 3: Implement**

1. B2-8 with B3b-21: embed once in `LayerCompositionService.search` and pass the vector and fingerprint to the memory and articles channels; the articles channel still reports `semantic_ran=False` when no vector is available.
2. B2-9: remove the provisional compose pass and the reranker block around it; keep `rerank_document_text`. The memory channel's own rerank (Task 6) is the only rerank.
3. B2-17: `search` returns `(await self.search_with_trace(...)).results`.
4. Keep the embed-failure behaviour: a failed query embed leaves the keyword arm answering alone with `semantic_failed`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_layer_composition.py tests/test_rrf_fusion.py tests/test_chat_retrieval_parity.py tests/test_articles_channel.py tests/test_block_retrieval.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services backend/tests
git commit -m "perf(retrieval): embed and compose once per search"
```

### Task 16: Shared RRF in code search and typed graph path ids

**Files:**
- Modify: `backend/app/services/rank_fusion.py`
- Modify: `backend/app/services/code_query.py`
- Modify: `backend/app/api/routes/graph.py`
- Modify: `backend/app/repositories/graph.py`
- Modify: `backend/app/services/graph.py`
- Test: `backend/tests/test_code_search_fusion.py`
- Test: `backend/tests/test_graph_path_ids.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 28, 29
**Depends on:** none
**Evaluation:** files 2 - spec 2 - coupling 1 - risk 1 = 6

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_code_search_fusion.py::test_code_query_declares_no_fusion_of_its_own` (unit): an AST scan of `code_query.py` finds no `1 / (` reciprocal-rank arithmetic and at least one call to `rank_fusion.rrf_fuse`; fails today on the two inline copies.
- `::test_one_failing_arm_leaves_the_other_answering` (integration): with the vector arm's statement patched to raise a database error, `search_code` returns the `ILIKE` arm's rows in the same session with no `InFailedSQLTransaction`, and its result marks the vector arm failed; fails today because the arms share one transaction and a failure is swallowed as an empty result.
- `::test_fusion_identity_is_repo_path_and_line` (unit): two hits sharing `file_path` and `line_start` in different repositories stay two results.
- `backend/tests/test_graph_path_ids.py::test_malformed_path_id_answers_422` (integration): the graph neighbour and path routes answer 422 for `not-a-uuid`; fails today with a 500.
- `::test_uppercase_seed_is_not_its_own_neighbour` (integration): requesting neighbours with the seed id in upper case never lists the seed.
- `::test_neighbours_are_a_stable_slice` (integration): with 30 neighbours seeded, two calls return the same 20 ids, ordered by id.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_code_search_fusion.py tests/test_graph_path_ids.py`

- [ ] **Step 3: Implement**

1. B2-14: `rrf_fuse` gains a `key=` parameter (default: the current id key); `code_query` calls it with `key=lambda r: (r.repo_id, r.file_path, r.line_start)` and runs each arm in its own savepoint, reporting a failed arm instead of an empty one. `RRF_K` stays declared only in `rank_fusion.py`.
2. B2-15: type the path ids `uuid.UUID` on the routes, compare normalised lower-case strings, and sort before the 20-row slice.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_code_search_fusion.py tests/test_graph_path_ids.py tests/test_rrf_fusion.py tests/test_graph_scale.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests
git commit -m "refactor(search): one RRF, typed graph path ids"
```

### Task 17: Remove the vector projection route and flag measurements

**Files:**
- Modify: `backend/app/api/routes/vectors.py`
- Modify: `backend/app/utils/math.py`
- Modify: `backend/app/services/feature_flags.py`
- Modify: `backend/app/services/content_surfaces.py`
- Modify: `docs/two-door-parity.md`
- Test: `backend/tests/test_removed_surfaces.py`

**Interfaces:**
- Consumes: none
- Produces: C4 (projection route, `flag_measurements`)

**Items:** 27, 32
**Depends on:** none
**Evaluation:** files 2 - spec 2 - coupling 1 - risk 1 = 6

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_removed_surfaces.py::test_vector_projection_route_is_gone` (integration): no route of the app object has the path `/api/v1/vectors/projection`, and `app.utils.math` has no `pca_2d`; fails today because both exist.
- `::test_flags_answer_carries_no_flag_measurements` (integration): the feature-flags `GET` answer has no `flag_measurements` key, also when a stored `config` row holds one.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_removed_surfaces.py`

- [ ] **Step 3: Implement**

1. B2-13: remove the projection route (delete `vectors.py` and its router registration if no other route remains in it), its row in `content_surfaces.py`, its row in `docs/two-door-parity.md`, and `pca_2d` once `rg pca_2d backend` shows no other caller. The frontend hook leaves in Task 45.
2. B2-18: remove the `flag_measurements` read from `feature_flags.py` and from the flags schema.
3. Run the guards leg; re-read the two prose counts.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_removed_surfaces.py tests/test_content_surface_scoping.py tests/test_door_parity.py tests/test_api/test_rest_conformance.py tests/test_sdk_generator.py tests/test_spa_edge.py`

- [ ] **Step 5: Commit**

```bash
git add -A backend/app backend/tests docs/two-door-parity.md
git commit -m "refactor(api): drop vector projection and flag badges"
```

### Task 18: Lift and re-extraction interleave

**Files:**
- Modify: `backend/app/services/fact_lift.py`
- Modify: `backend/app/services/entity_merge.py`
- Test: `backend/tests/test_fact_lift_interleave.py`
- Test: `backend/tests/test_entity_merge_sources_changed.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 37, 52
**Depends on:** none
**Evaluation:** files 1 - spec 2 - coupling 0 - risk 3 = 6

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_fact_lift_interleave.py::test_lift_waits_for_the_reextraction_and_reads_the_new_graph` (integration, A1): session A holds the pipeline's row lock on memory M and strips the relation behind fact F from M's graph without committing; session B starts `_lift_one` for F and is observed blocked (its task is not done after 0.3 s); A commits; B finishes; afterwards `fact_sources` holds no row for (F, M). Fails today because the lift reads M's assertion without the memory-row lock and keeps the source.
- `::test_lift_of_an_unrelated_memory_is_not_blocked` (integration): with M locked, a lift whose candidate sources do not include M finishes within 0.3 s.
- `backend/tests/test_entity_merge_sources_changed.py::test_fact_fold_emits_sources_changed_for_the_keeper` (integration): a merge whose fold moves `fact_sources` rows onto the keeper fact journals exactly one `sources_changed` event for the keeper inside the fold savepoint; a failed fold journals none. Fails today because the fold emits nothing.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_fact_lift_interleave.py tests/test_entity_merge_sources_changed.py`

- [ ] **Step 3: Implement**

1. B3a-1: in `_lift_one`, run `SELECT id FROM memories WHERE id = ANY(:ids) ORDER BY id FOR SHARE` as its own statement before the still-asserting read, so the lift waits for the pipeline's lock and then reads the committed graph. Keep invariant 15: nothing here is imported by capture or retrieval.
2. B3a-18: emit one `sources_changed` event for the keeper inside the fold savepoint.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_fact_lift_interleave.py tests/test_entity_merge_sources_changed.py tests/test_fact_lift.py tests/test_auto_research.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services backend/tests
git commit -m "fix(vault): lift waits for re-extraction"
```

### Task 19: Contradiction scan skip and vault journal hygiene

**Files:**
- Modify: `backend/app/services/contradiction_scan.py`
- Modify: `backend/app/services/verification_judge.py`
- Modify: `backend/app/services/verification_ladder.py`
- Modify: `backend/app/services/verification_recompute.py`
- Modify: `backend/app/repositories/knowledge_triples.py`
- Modify: `backend/app/services/human_adjudication.py`
- Modify: `CLAUDE.md`
- Test: `backend/tests/test_contradiction_scan.py`
- Test: `backend/tests/test_blocked_hold_journal.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 38, 39, 47, 50, 51
**Depends on:** none
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 2 = 6

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_contradiction_scan.py::test_unqualified_role_drains_nothing` (integration, A24): with no qualification record for the `contradiction` role at the served identity and 25 `sources_changed` events past the watermark, one scan tick runs zero drain queries (statement counter), writes zero journal rows, leaves the watermark unchanged, and its run result carries `skipped: "contradiction role unqualified"`. Fails today because it drains 20 events and commits clean verdicts.
- `::test_qualified_role_still_scans` (integration): with a record patched in for the role, the tick drains as before.
- `backend/tests/test_blocked_hold_journal.py::test_identical_blocked_hold_is_journalled_once` (integration): three recomputes of a fact held by the same contradiction counterpart write one `verified` event; a fourth with a different counterpart writes a second. Fails today with one row per visit. A second case asserts the same for a supersession-blocked hold.
- `::test_confirmed_fact_gets_no_suspicion_marker` (unit): `recompute_fact(..., contradiction_suspected=<finding>)` on a `confirmed` fact leaves `contradiction_suspected_at` and `contradiction_counterpart_id` NULL.
- `::test_dismissal_note_is_bounded` (integration): a dismissal with a 5,000-character note journals a `contradiction_dismissed` payload whose `note` has length `NOTE_MAX_LENGTH`.
- Prose with no test: B3a-15 and B3a-16 correct the stale comments in `verification_recompute.py`, `contradiction_scan.py`, `verification_judge.py`, `knowledge_triples.py` and `verification_ladder.py` (the `document_door` producer, "no qualification records exist", "ratification is unbuilt", "no production caller").

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_contradiction_scan.py tests/test_blocked_hold_journal.py`

- [ ] **Step 3: Implement**

1. B3a-2 with B3b-11: at run start ask the judge's own predicate whether a record qualifies the `contradiction` role at the served identity; when it does not, return the skip result without draining. Leave the batch default alone.
2. B3a-3: journal a blocked hold only when its evidence differs from the fact's latest `verified` payload. First read `scripts/benchlib/promotion_metrics.py`'s denominators and confirm none counts repeated holds; say so in the commit body.
3. B3a-12: pass `None` to `_suspicion_marker` when the current status is `confirmed`. B3a-17: `note[:NOTE_MAX_LENGTH]` in the dismissal payload.
4. `CLAUDE.md`'s contradiction-scan sentence ("so today it produces nothing") gains that an unqualified tick skips without draining.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_contradiction_scan.py tests/test_blocked_hold_journal.py tests/test_dream_jobs.py tests/test_auto_research.py && .venv/bin/python -m pytest -q scripts/benchlib/tests`

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests CLAUDE.md
git commit -m "fix(vault): skip unqualified scans, dedupe holds"
```

### Task 20: Vault lock scope and tick cost

**Files:**
- Modify: `backend/app/services/fact_lift.py`
- Modify: `backend/app/services/dream_jobs.py`
- Modify: `backend/app/services/fact_provenance.py`
- Modify: `backend/app/services/verification_recompute.py`
- Modify: `backend/app/services/supersession_hold.py`
- Modify: `backend/app/repositories/fact_sources.py`
- Modify: `backend/app/services/verification_ladder.py`
- Modify: `backend/app/services/claim_gates.py`
- Modify: `backend/app/services/facts_read.py`
- Test: `backend/tests/test_vault_tick_cost.py`
- Test: `backend/tests/test_vault_lock_scope.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 41, 42, 43, 44, 45, 46, 48, 49
**Depends on:** Task 18, Task 19
**Evaluation:** files 3 - spec 2 - coupling 0 - risk 3 = 8

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_vault_lock_scope.py::test_lift_commits_per_candidate_batch` (integration): a lift over three candidate batches commits after each (commit spy count 3), so a second session can lock a fact of batch one while batch three runs; fails today because the tick commits once.
- `::test_withdrawal_times_out_instead_of_waiting` (integration): with a fact row locked by another session, the Phase 5 source withdrawal inside savepoint B raises a lock-timeout error within 5 s and the savepoint rolls back; fails today because it waits without bound.
- `::test_withdrawal_leaves_lock_timeout_as_it_found_it` (integration): in a batch of two memories, `SHOW lock_timeout` read in the batch transaction after the first memory's savepoint B is released equals its value before the batch began. It passes today and guards Step 3's bound: it fails if the 5 s limit leaks past the withdrawal into the rest of the batch.
- `backend/tests/test_vault_tick_cost.py::test_idle_drain_advances_the_watermark` (integration): a recompute drain that returns fewer than `batch` rows stores a watermark equal to its `safe_until`; fails today because an idle drain never moves it.
- `::test_memory_source_join_uses_the_primary_key` (integration): with `enable_seqscan` off, `EXPLAIN` of the supersession-hold read and of `memory_sources_for_fact` names `memories_pkey`; fails today because of `CAST(m.id AS text)`.
- `::test_code_reconcile_is_skipped_when_no_repository_moved` (integration): two consecutive lift ticks with no `last_indexed_commit` change run the code-provenance read once (statement counter on the second tick: 0).
- `::test_ladder_config_is_resolved_once_per_tick` (integration): a recompute over ten facts reads each of the three ladder config rows once.
- `::test_promotion_record_is_read_once_per_response` (unit): building badges for 50 corroborated rows opens `promotion_metrics_record.json` once; a changed file mtime is picked up by the next response.
- `::test_get_fact_reads_the_latest_verified_event_once` (integration): `GET /api/v1/knowledge/facts/{id}` runs one statement against `events` for the verification evidence; fails today with two.
- Removal with no new test: B3a-14 deletes `facts_for_source` and `OriginProfile.required_origin_count` and keeps `count_distinct_origins` only if a test uses it as an oracle (`rg` decides; record the result in the commit body).

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_vault_tick_cost.py tests/test_vault_lock_scope.py`

- [ ] **Step 3: Implement**

1. B3a-6: commit the lift per candidate batch; bound the withdrawal's lock wait inside savepoint B to 5 s, so a timeout fails B as a `graph_write` failure the buffer retries. `SET LOCAL` outlives a released savepoint for the rest of the transaction, so read `current_setting('lock_timeout')` before the withdrawal and set it back once the withdrawal's statements have run, on the success path; a failed B restores it by rolling back. `SET` takes no bind parameter: set both the bound and the restore with `SELECT set_config('lock_timeout', :v, true)`.
2. B3a-7: when the drain returns fewer than `batch` rows, advance the watermark to `safe_until`. Add no index (spec departure).
3. B3a-8: join on `m.id = CASE WHEN <memory-kind ref has the canonical UUID shape> THEN CAST(fs.source_ref AS uuid) END` in both statements.
4. B3a-9: skip the code reconcile unless some repository's `last_indexed_commit` differs from the stamp stored in the lift's state row; drop the inert `adjudicate_contradiction` consult there.
5. B3a-10: resolve the ladder config once in `run_recompute` and pass it to `recompute_fact`. B3a-11 with B3a-D4: cache the promotion record on file mtime. B3a-13: reuse the evidence map `badges_for_facts` fetched.
6. `ladder_config.py` stays the resolver; nothing on a read surface imports `verification_ladder` or `contradiction_veto`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_vault_tick_cost.py tests/test_vault_lock_scope.py tests/test_fact_lift.py tests/test_dream_jobs.py tests/test_auto_research.py tests/test_pipeline_savepoints.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests
git commit -m "perf(vault): narrower locks and cheaper ticks"
```

### Task 21: Summary-only refine and the lost project-tag script

**Files:**
- Modify: `backend/app/services/memory_dream.py`
- Create: `backend/scripts/restore_refine_project_tags.py`
- Test: `backend/tests/test_memory_dream.py`
- Test: `backend/tests/test_dream_undo.py`
- Test: `backend/tests/test_restore_refine_project_tags.py`

**Interfaces:**
- Consumes: none
- Produces: C12

**Items:** 56
**Depends on:** none
**Evaluation:** files 1 - spec 2 - coupling 1 - risk 3 = 7

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_memory_dream.py::test_refine_changes_the_summary_and_never_the_tags` (integration, A20): a refine whose model answer carries a new summary and a "cleaned" tag list leaves the memory's tags (including `project/alpha`) exactly as they were, updates `summary`, and journals a `consolidated` event whose payload has no `tags` in `before` or `after`. Fails today because the model's list replaces the tags.
- `backend/tests/test_dream_undo.py::test_undo_restores_tags_from_an_older_refine_event` (integration, A20): a `consolidated` refine event already in the journal with `before.tags = ["project/alpha", "x"]` is undone, and the memory's tags are `["project/alpha", "x"]` again.
- `backend/tests/test_restore_refine_project_tags.py::test_dry_run_lists_lost_project_tags` (integration): with two refine events whose `before.tags` held `project/alpha` on memories that no longer carry it, and one on a memory that still does, the script's dry run prints exactly two lines in C12's form followed by `memories: 2`, and writes nothing.
- `::test_apply_restores_only_the_lost_project_tags` (integration): `--apply` adds `project/alpha` back to those two memories, changes no other tag, and a second `--apply` reports `memories: 0`.
- `::test_script_refuses_production_without_the_flag` (unit): without `--database-url`, the script reads `DATABASE_URL` and exits 2 when `--apply` is given without `--i-am-the-owner`.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_memory_dream.py tests/test_dream_undo.py tests/test_restore_refine_project_tags.py`

- [ ] **Step 3: Implement**

1. B3b-4: refine becomes a fixed `summary` update: stop parsing and writing tags, and remove `RefinableColumnError` and `build_refine_update` (B3b-R5). `dream_undo`'s tag restore stays untouched (B3b-R2 is not taken); do not add a savepoint, commit or `try` to `dream_undo`.
2. C12: the script reads `consolidated` events of the refine kind whose `payload.before.tags` held a `project/` tag absent from the memory's current tags, bounded by `created_at`, and restores only those tags through the tag repository with `validate_tag_lengths`.
3. The restore on this host is register row 232 and waits for the owner; this task runs the script only against the test database.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_memory_dream.py tests/test_dream_undo.py tests/test_restore_refine_project_tags.py tests/test_memory_dream_residue.py tests/test_dream_digest.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/memory_dream.py backend/scripts/restore_refine_project_tags.py backend/tests
git commit -m "fix(dream): refine the summary only, keep tags"
```

### Task 22: Strict journalling for dream and hygiene actions

**Files:**
- Modify: `backend/app/services/memory_dream.py`
- Modify: `backend/app/services/hygiene_queue.py`
- Modify: `backend/app/services/dream_digest.py`
- Modify: `backend/app/services/dream_journal.py`
- Modify: `backend/app/api/routes/dream_digest.py`
- Modify: `CLAUDE.md`
- Test: `backend/tests/test_dream_strict_journal.py`
- Test: `backend/tests/test_dream_digest.py`
- Test: `backend/tests/test_memory_dream.py`
- Test: `backend/tests/test_dream_undo.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 54, 60, 61, 64
**Depends on:** Task 21
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 2 = 6

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_dream_strict_journal.py::test_action_with_a_failed_journal_write_commits_nothing` (integration, A22): with `record_event` patched to return `False`, each of a dream supersede, a dream associate edge, a dream refine, a hygiene supersede and a hygiene prune leaves the memory row, its relations and its status exactly as before, and the tick or request reports the failure. Fails today because the action commits with no `consolidated` row.
- `::test_other_actions_of_the_tick_still_land` (integration): in a tick of three actions where the journal fails for the second only, the first and third commit with their rows.
- `backend/tests/test_dream_digest.py::test_derivation_associate_is_undoable_exactly_when_undo_succeeds` (integration, A21): for a derivation `associate` action (payload carrying `pass_key`), the digest's `undoable` flag is true and the undo answers 200; after the edge is removed by hand the flag is false and the undo answers 409. Fails today because the rebuilt payload drops `pass_key`.
- `backend/tests/test_memory_dream.py::test_asymmetric_proximity_writes_no_phantom_row` (integration): two rotations over memories A and B, where A's top-N probe yields the pair and B's does not, journal one `associate` row in total and leave the edge in place; fails today with one new row per rotation.
- `backend/tests/test_dream_undo.py::test_lock_timeout_answers_a_retryable_conflict` (integration): with the target memory row locked by another session, `POST` undo answers 409 with `error.code = "locked"` and writes nothing; fails today with a 500.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_dream_strict_journal.py tests/test_dream_digest.py tests/test_memory_dream.py tests/test_dream_undo.py`

- [ ] **Step 3: Implement**

1. B3b-8: inside each action's own savepoint, raise a module exception (`DreamJournalWriteFailed`, `HygieneJournalWriteFailed`) when `record_event` returns `False`, so the savepoint rolls back; the tick loop logs and continues. `CLAUDE.md`'s strict-caller paragraph names the two new callers and corrects its count.
2. B3b-2: carry `pass_key` into `DreamActionView` and the payload `annotate_undoability` rebuilds.
3. B3b-9: keep a proximity triple when either endpoint's probe produces it, and strip only edges re-measured below threshold.
4. B3b-13: map SQLSTATE `55P03` to 409 `locked` in the undo route; `dream_undo` itself gains no `try`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_dream_strict_journal.py tests/test_dream_digest.py tests/test_memory_dream.py tests/test_dream_undo.py tests/test_events.py tests/test_event_taxonomy_map.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests CLAUDE.md
git commit -m "fix(dream): make dream actions strict journal callers"
```

### Task 23: Dream verdict memo and the unreachable contradiction arm

**Files:**
- Modify: `backend/app/services/memory_dream.py`
- Modify: `backend/app/taxonomy.py`
- Test: `backend/tests/test_memory_dream.py`
- Test: `backend/tests/test_memory_relation_derivation.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 55, 62
**Depends on:** Task 22
**Evaluation:** files 1 - spec 2 - coupling 0 - risk 2 = 5

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_memory_dream.py::test_distinct_verdict_is_remembered_by_content` (integration): after the judge rules a pair `distinct`, the older memory's `metadata.dream.distinct.<counterpart_id>` holds both `content_sha` values, and the next rotation sends that pair to the judge zero times; after either memory's content changes, the pair is judged again. Fails today because the pair is re-judged every rotation.
- `::test_unchanged_existing_edge_is_not_rejudged` (integration): a pair that already has an edge and unchanged shas is skipped.
- `::test_pairs_past_the_fanout_are_counted` (integration): with `judge_fanout` 2 and five nominated pairs, the run result carries `truncated_pairs: 3`, and a second rotation reaches at least one of the three (the two memoed pairs no longer occupy the fanout).
- Removal with no new test: B3b-10 with B3b-R1 deletes the derivation contradiction arm, the `SIGNAL_CONTRADICTION` precedence slot and the four monkeypatched tests in `test_memory_relation_derivation.py`; `EXCLUSIVE_RELATION_FAMILIES` leaves `taxonomy.py` if `rg` shows no other reader.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_memory_dream.py tests/test_memory_relation_derivation.py`

- [ ] **Step 3: Implement**

1. B3b-3: write the memo at `memories.metadata.dream.distinct.<counterpart_id>` as `{"a_sha": …, "b_sha": …}` on the memory with the smaller id, the shape the `undone_subsume` tombstone uses, in the action's savepoint; `generate_pairs` reads it at nomination time. No revision.
2. Report `truncated_pairs` in the run result and the tick's log line.
3. B3b-10: remove the arm as listed.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_memory_dream.py tests/test_memory_relation_derivation.py tests/test_memory_dream_residue.py tests/test_dream_undo.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests
git commit -m "perf(dream): remember distinct verdicts"
```

### Task 24: Article subject identity and synthesis budgets

**Files:**
- Modify: `backend/app/services/article_synthesis.py`
- Modify: `backend/app/services/article_eligibility.py`
- Modify: `backend/app/services/articles_channel.py`
- Modify: `backend/app/services/dream_jobs.py`
- Modify: `backend/app/services/review_ranking.py`
- Test: `backend/tests/test_article_synthesis.py`
- Test: `backend/tests/test_article_eligibility.py`
- Test: `backend/tests/test_queue_ranking.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 58, 59, 63, 69, 70
**Depends on:** none
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 2 = 6

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_article_synthesis.py::test_same_name_subjects_get_their_own_facts` (integration, A23): entities `mercury` of type `tool` and `mercury` of type `concept`, each with three facts of its own, yield two articles whose gathered fact ids are disjoint and whose fact-set hashes differ; a new fact on the `tool` subject marks only that article stale. Fails today because gather, hash and staleness key on the name alone.
- `backend/tests/test_article_eligibility.py::test_zero_fact_pinned_subject_is_not_selected` (integration): with `synthesis_budget` 2, two pinned subjects holding no fact and two real subjects, `select_for_synthesis` returns the two real subjects.
- `backend/tests/test_article_synthesis.py::test_resynthesis_is_capped_per_tick` (integration): with five settled stale articles and `synthesis_budget` 2, one tick re-synthesises two; the others stay stale for the next tick.
- `backend/tests/test_dream_jobs.py::test_article_runner_logs_both_outcomes` (unit): the article runner's log record carries the synthesis and the re-synthesis counts, and its return value carries both for `job_runs`.
- `backend/tests/test_queue_ranking.py::test_dispute_onset_lookup_is_bounded_by_time` (integration): `EXPLAIN` of the dispute-onset statement shows partition pruning (fewer `events` children scanned than exist) for a dispute opened this month; fails today because the lateral has no `created_at` bound.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_article_synthesis.py tests/test_article_eligibility.py tests/test_queue_ranking.py tests/test_dream_jobs.py`

- [ ] **Step 3: Implement**

1. B3b-6: filter on `entity_type` through `subject_id` in the gather, hash, staleness and channel fact queries, so all four agree with eligibility's `name::entity_type` key. A fact whose `subject_id` is NULL keeps matching by name.
2. B3b-7: exclude zero-fact pinned subjects in `select_for_synthesis`. B3b-12: cap the re-synthesis ready list with `synthesis_budget`. B3b-19: log and return both outcomes. B3b-20: bound the lateral by `o.created_at`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_article_synthesis.py tests/test_article_eligibility.py tests/test_queue_ranking.py tests/test_dream_jobs.py tests/test_article_staleness.py tests/test_articles_channel.py tests/test_block_retrieval.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services backend/tests
git commit -m "fix(articles): key subjects on name and type"
```

### Task 25: Dream, article and research cleanups

**Files:**
- Modify: `backend/app/services/dream_jobs.py`
- Modify: `backend/app/services/dream_journal.py`
- Modify: `backend/app/services/memory_dream.py`
- Modify: `backend/app/services/dream_undo.py`
- Modify: `backend/app/services/articles_read.py`
- Modify: `backend/app/services/review_queue.py`
- Modify: `backend/app/services/article_synthesis.py`
- Modify: `backend/app/services/auto_research.py`
- Modify: `backend/app/api/mcp/server.py`
- Modify: `backend/app/services/hygiene_queue.py`
- Modify: `backend/app/services/verification_judge.py`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 57, 66, 67, 68
**Depends on:** Task 22, Task 23, Task 24
**Evaluation:** files 3 - spec 2 - coupling 0 - risk 1 = 6

- [ ] **Step 1: No new test, because every change here is a refactor with unchanged behaviour or prose no script reads, and the existing suites `tests/test_dream_jobs.py`, `tests/test_dream_undo.py`, `tests/test_auto_research.py`, `tests/test_articles_read_surface.py` and the invariant-15 scan in `tests/test_auto_research.py` fail on any behaviour change**

- [ ] **Step 2: Record the baseline**

Run: `.venv/bin/python -m pytest -q tests/test_dream_jobs.py tests/test_dream_undo.py tests/test_auto_research.py tests/test_articles_read_surface.py tests/test_memory_dream.py`
Expected: PASS before any edit.

- [ ] **Step 3: Implement**

1. B3b-15: one rotation-cursor helper and one locked memory projection in `dream_journal.py`, used by `dream_jobs.py`, `memory_dream.py` and `dream_undo.py`; one article-gate resolver shared by `articles_read.py` and `review_queue.py`; one fact-set hash query shared by `article_synthesis.py` and `articles_channel.py`. Keep any duplicate the invariant-15 scan forces, with one comment naming the scan.
2. B3b-16 with B3b-R3: `run_research` takes the findings list directly; delete the `ResearchGatherer` Protocol and `_SuppliedFindings`; correct the `server.py` comment that calls the keyed door unauthenticated. The tool still takes no `source`, `origin_key` or `ctx`.
3. B3b-18: correct the stale docstrings and annotations the finding lists (the 3-tuple return type, "still a placeholder", "reports nothing back", "no qualification record exists", the dead second docstring).
4. B3b-5: correct `CLAUDE.md`'s "Labels are gated by evidence records" paragraph to say the article surfaces gate on `article_claim_gate`, which opens on the minted entailment record at the served identity, with `groundedness_gate()` as its exception fallback; correct the `article_claim_gate` docstring to match.

- [ ] **Step 4: Run the suites again**

Run: `.venv/bin/python -m pytest -q tests/test_dream_jobs.py tests/test_dream_undo.py tests/test_auto_research.py tests/test_articles_read_surface.py tests/test_memory_dream.py tests/test_article_synthesis.py tests/test_block_retrieval.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app CLAUDE.md
git commit -m "refactor(dream): share cursor and gate helpers"
```

### Task 26: Symbol and blast-radius queries in CodeQueryService

**Files:**
- Modify: `backend/app/services/code_query.py`
- Modify: `backend/app/api/mcp/server.py`
- Modify: `backend/app/api/routes/code.py`
- Modify: `backend/app/schemas/code.py`
- Test: `backend/tests/test_mcp_code_tools.py`
- Test: `backend/tests/test_code_blast_radius_scope.py`

**Interfaces:**
- Consumes: none
- Produces: C3

**Items:** 78, 79, 125
**Depends on:** Task 16
**Evaluation:** files 1 - spec 2 - coupling 2 - risk 2 = 7

- [ ] **Step 1: Write the failing test**

Each test seeds an indexed repository through the code-graph tables (no parser run) and calls the MCP tool through `/mcp/` with a `read` key.

- `backend/tests/test_mcp_code_tools.py::test_code_symbol_answers_for_an_indexed_repository` (integration, A35): `code_symbol` for an existing symbol returns its name, kind and `file_path`, and at most 50 rows; fails today with `MissingGreenlet` on the lazy `s.file` (if the call succeeds unchanged, B6-4 is closed `not reproduced` and the limit assertion alone drives the change).
- `::test_repo_named_tools_refuse_an_ambiguous_name` (integration, A35): with two repositories named `app`, each of `code_symbol`, `code_file_symbols`, `code_context`, `code_dependencies`, `code_processes` and `code_communities` answers an `ambiguous` envelope listing both repository ids, and none raises; fails today with `MultipleResultsFound`.
- `backend/tests/test_code_blast_radius_scope.py::test_blast_radius_honours_repository_and_owner` (integration, A35): with `run::src/main.py::Worker` and `run::src/main.py::Scheduler` in repository R1 and a `run` in `src/main.py` of repository R2, a REST blast-radius request for the `Worker` key with `repo_id=R1` returns only `Worker.run`'s callers; fails today because owner and repository are ignored.
- `::test_ambiguous_symbol_lists_candidates` (integration, A35): MCP `code_blast_radius("run")` with `repo` R1 answers the `ambiguous` envelope with both candidates' keys; the REST route answers 409 with `error.code = "symbol_ambiguous"`.
- `::test_blast_radius_requires_a_repo_id` (integration): the REST request without `repo_id` answers 422.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_mcp_code_tools.py tests/test_code_blast_radius_scope.py`

- [ ] **Step 3: Implement**

1. Per C3: add `resolve_repo`, extend `lookup_symbol` (select `CodeFile.file_path` in the query, honour `repo_id`, `file_path` and owner, bounded by `limit`), and make blast radius take `repo_id` and raise `SymbolAmbiguous`.
2. Move the raw SQL of MCP `code_symbol`, `code_blast_radius`, `code_file_symbols` and `code_context` out of `server.py` into `CodeQueryService` methods; the tools become argument validation, one service call and envelope shaping. Use one session idiom for all of them. In `code_dependencies`, `code_processes` and `code_communities` replace only the repository-by-name lookup with `resolve_repo` and its `ambiguous` envelope here; their remaining queries move in Task 27.
3. The REST blast-radius route passes `repo_id` and maps `SymbolAmbiguous` to 409.
4. Run `make generate` in `sdks/` if the OpenAPI document changed, then the guards leg.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_mcp_code_tools.py tests/test_code_blast_radius_scope.py tests/test_code_search_fusion.py tests/test_door_parity.py tests/test_api/test_rest_conformance.py tests/test_sdk_generator.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests sdks
git commit -m "fix(code): scope symbol lookups to a repository"
```

### Task 27: Remaining MCP code tools in CodeQueryService

**Files:**
- Modify: `backend/app/services/code_query.py`
- Modify: `backend/app/api/mcp/server.py`
- Test: `backend/tests/test_mcp_code_tools.py`

**Interfaces:**
- Consumes: C3
- Produces: none

**Items:** 81, 124, 133
**Depends on:** Task 26
**Evaluation:** files 1 - spec 2 - coupling 1 - risk 2 = 6

- [ ] **Step 1: Write the failing test**

All in `backend/tests/test_mcp_code_tools.py`.

- `::test_code_search_without_an_embedder_answers_from_the_keyword_arm` (integration, A14): with no LLM orchestrator installed, MCP `code_search("parse_config")` returns the symbol whose name matches, and the reply carries `degraded: true` with a reason naming the semantic arm; fails today with an empty degraded result.
- `::test_code_rename_treats_underscore_and_percent_literally` (integration): with symbols `get_user` and `getXuser` (and `a%b` and `axxb`), `code_rename("get_user", …)` lists references to `get_user` only; fails today because `_` and `%` act as `LIKE` wildcards.
- `::test_code_processes_runs_a_bounded_number_of_statements` (integration): with twelve processes seeded, `code_processes` runs at most three statements (statement counter); fails today with one per process.
- `::test_mcp_code_tools_hold_no_sql` (unit): an AST scan of every `code_*` tool body in `server.py` except `code_reindex` (exempted by name, the one write door) finds no `select(`, `text(` or `session.execute` call; each scanned body reaches the database only through a `CodeQueryService` attribute. Fails today on the tools Task 26 did not move.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_mcp_code_tools.py`

- [ ] **Step 3: Implement**

1. B6-D2: move the queries of `code_search`, `code_rename`, `code_dependencies`, `code_processes`, `code_communities` and `code_changes` into `CodeQueryService`; every tool resolves its repository through `resolve_repo` (C3).
2. B4-12: `code_search` always calls `search_code` and adds the degraded annotation when the semantic arm did not run.
3. B6-15: match with `left(target_key, :n) = :name || '::'` instead of `LIKE`.
4. `code_reindex` stays the only MCP write door into the code subsystem and is not moved: it keeps its own repository lookup, as C3 says.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_mcp_code_tools.py tests/test_read_only_doors.py tests/test_mcp_auth.py tests/test_door_parity.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests/test_mcp_code_tools.py
git commit -m "refactor(mcp): code tools query through the service"
```

### Task 28: Incremental indexing correctness

**Files:**
- Modify: `backend/app/services/code_pipeline.py`
- Test: `backend/tests/test_code_pipeline_incremental.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 75, 76, 77, 80
**Depends on:** none
**Evaluation:** files 0 - spec 2 - coupling 0 - risk 2 = 4

- [ ] **Step 1: Write the failing test**

All in `backend/tests/test_code_pipeline_incremental.py`, each over a temporary git repository indexed once, changed, and indexed again incrementally.

- `::test_non_ascii_path_is_reindexed_and_removed` (integration, A34): after editing `src/é.py`, its symbols reflect the edit; after `git rm` of it, its `code_files` row and symbols are gone. Fails today because the quoted path from `git diff --name-status` matches nothing.
- `::test_subclass_keeps_its_extends_edge_to_an_unchanged_file` (integration, A34): with `class V(BaseView)` in `views.py` and `BaseView` in an unchanged `base.py`, editing `views.py` leaves an `extends` edge whose target key names `base.py`; fails today because the target is keyed on `views.py`.
- `::test_file_with_a_failed_embed_is_embedded_by_the_next_run` (integration, A33): with the embedder stub raising for `a.py` on run 2 and answering on run 3 (no file change between them), after run 3 `a.py` has chunk rows under the active fingerprint; fails today because an equal hash skips it forever.
- `::test_unchanged_dependent_is_not_reembedded` (integration, A33): editing `util.py`, which `caller.py` calls, sends chunks of `util.py` to the embedder stub and none of `caller.py`, while `caller.py`'s call edges are re-traced; fails today because every parsed file is re-embedded.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_code_pipeline_incremental.py`

- [ ] **Step 3: Implement**

1. B4-7: run `git diff --name-status -z` and split on NUL, handling the two-path form of renames.
2. B4-8: build `class_file_index` from the repository's class-like `code_graph_nodes` rows (one query) overlaid with the freshly parsed files; correct the comment that claims "changed or not".
3. B4-11 and B4-6 together: phase 12 embeds the files phase 03 rewrote plus every surviving file with no chunk row under the active fingerprint, bounded per run by the existing batch size; a failed embed therefore leaves a gap the next run fills.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_code_pipeline_incremental.py tests/test_code_pipeline.py tests/test_code_pipeline_union.py tests/test_code_pipeline_integration.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/code_pipeline.py backend/tests/test_code_pipeline_incremental.py
git commit -m "fix(code): incremental runs keep paths and edges"
```

### Task 29: Clone, fetch and task-cancel safety

**Files:**
- Modify: `backend/app/services/repo_manager.py`
- Modify: `backend/app/services/job_runners.py`
- Modify: `backend/app/api/routes/repos.py`
- Modify: `backend/app/services/task_registry.py`
- Modify: `CLAUDE.md`
- Test: `backend/tests/test_repo_fetch_safety.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 82, 88, 93
**Depends on:** none
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 3 = 7

- [ ] **Step 1: Write the failing test**

All in `backend/tests/test_repo_fetch_safety.py`, over temporary git repositories with the remote made unreachable where stated.

- `::test_failed_fetch_keeps_a_healthy_clone` (integration, A36): a managed clone whose fetch fails with a network error still has its working tree and `.git` afterwards, and no clone was started; fails today because any `RuntimeError` leads to `rmtree` and a re-clone.
- `::test_corrupt_clone_is_recloned_under_a_claim` (integration): a clone whose `git rev-parse HEAD` fails is re-cloned, and while the re-clone runs the repository's status is `cloning`, so `claim_for_indexing` refuses a concurrent reindex.
- `::test_fetch_lane_leaves_a_feature_branch_alone` (integration, A36): a local checkout on branch `feature` with a new commit on the remote's default branch keeps `feature` at its own commit after the fetch lane runs; with the checkout on the default branch it fast-forwards. Fails today because the merge runs on whatever branch is checked out.
- `::test_cancel_refuses_a_task_of_another_repository` (integration): `DELETE /api/v1/repos/{A}/tasks/{task of B}` answers 404, the task keeps running, and neither repository's status changes; fails today because the task is cancelled and A is marked.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_repo_fetch_safety.py`

- [ ] **Step 3: Implement**

1. B4-13: re-clone only when the tree is corrupt (`git rev-parse` fails), never on a fetch or network error; take the claim as `cloning` around any `rmtree` or clone in the fetch lane and release it in a handler a cancellation also reaches.
2. B4-20: skip the fast-forward unless `git symbolic-ref --short HEAD` equals `default_branch`.
3. B4-24: `TaskRegistry` records each task's `repo_id`; the cancel route checks it before cancelling.
4. `CLAUDE.md`'s code-indexing section gains one sentence each for the corrupt-only re-clone and the default-branch-only fast-forward.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_repo_fetch_safety.py tests/test_code_pipeline.py tests/test_boot_reconciliation.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests/test_repo_fetch_safety.py CLAUDE.md
git commit -m "fix(repos): never delete a healthy clone"
```

### Task 30: Drift scan and per-file delete cost

**Files:**
- Create: `backend/migrations/versions/0004_code_edge_file_indexes.py`
- Modify: `backend/app/services/code_reconcile.py`
- Modify: `backend/app/services/code_pipeline.py`
- Modify: `backend/app/services/heritage_resolver.py`
- Modify: `backend/app/services/job_runners.py`
- Modify: `backend/app/services/code_deriver_job.py`
- Test: `backend/tests/test_code_index_cost.py`
- Test: `backend/tests/test_schema_guard.py`

**Interfaces:**
- Consumes: none
- Produces: C7 (`0004_code_edge_file_indexes`)

**Items:** 73, 74, 83, 84, 92
**Depends on:** Task 28
**Evaluation:** files 3 - spec 2 - coupling 0 - risk 3 = 8

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_code_index_cost.py::test_drift_scan_hashes_off_the_event_loop` (integration): with `_file_hash` patched to record `threading.get_ident()`, `compute_working_tree_drift` hashes on a thread other than the loop's; fails today because it hashes inline.
- `::test_unchanged_stat_is_not_rehashed` (integration): a second scan of an untouched tree calls `_file_hash` zero times (the `(mtime, size)` pair matched).
- `::test_unparseable_file_is_not_drift` (integration): a file whose parse raises is recorded as a `code_files` row with its content hash and no symbols, and the next drift scan reports no drift for it; editing the file reports drift again. Fails today because no row is written.
- `::test_per_file_delete_uses_the_expression_indexes` (integration): after `alembic upgrade head`, `pg_indexes` holds `ix_code_edges_source_file` and `ix_code_edges_target_file`, and with `enable_seqscan` off the edge delete for a batch of files plans against them; fails today because the indexes do not exist.
- `::test_full_reindex_deletes_in_batches` (integration): a full reindex of a 40-file fixture runs at most 6 edge-delete statements and one orphan sweep (statement counter); fails today with one of each per file.
- `::test_store_graph_batches_its_inserts` (integration): phase 03 over a file with 100 symbols runs at most 10 INSERT statements; phase 05 runs one UPDATE for a batch of files; phase 06 loads the `extends` and `has_method` maps once.
- `::test_code_deriver_skips_a_repository_whose_head_did_not_move` (integration): two consecutive `code_deriver` ticks with an unchanged `last_indexed_commit` call `assert_repo_graph` once; after the commit moves, a third tick calls it again.
- `backend/tests/test_schema_guard.py::test_exactly_one_head` — existing test; it must still pass with the new revision.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_code_index_cost.py tests/test_schema_guard.py`

- [ ] **Step 3: Implement**

1. B4-5: revision `0004_code_edge_file_indexes` (`down_revision = "0003_board_views"`, as C7 fixes) creates `ix_code_edges_source_file` on `(repo_id, split_part(source_key, '::', 2))` and `ix_code_edges_target_file` on the target twin with `CREATE INDEX IF NOT EXISTS`; its downgrade drops both. The table is `code_edges` (`CodeEdge` in `app/models/code.py`). Then delete in one statement per phase with `split_part(...) = ANY(:files)` and run the orphan sweep once per run.
2. B4-4: run the scan through `run_in_executor`, comparing `(mtime, size)` first and hashing only files whose stat changed; keep discovery by `git_visible_files`.
3. B4-14: write the marker `code_files` row (content hash, no symbols, a `parse_error` status message) for a file whose parse raised or timed out. No revision.
4. B4-15: batch `_store_graph` inserts per file, the phase 05 update per batch, and reuse the maps phase 07 loads in phase 06.
5. B4-23: `code_deriver` stores `derived_at_sha` in its state row per repository and skips a repository whose `last_indexed_commit` equals it; update the rationale comment in `code_deriver_job.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_code_index_cost.py tests/test_schema_guard.py tests/test_code_pipeline.py tests/test_code_pipeline_integration.py tests/test_code_deriver.py`

- [ ] **Step 5: Commit**

```bash
git add backend/migrations/versions/0004_code_edge_file_indexes.py backend/app backend/tests
git commit -m "perf(code): batch deletes and index file keys"
```

### Task 31: Stable code graph keys

**Files:**
- Modify: `backend/app/services/code_pipeline.py`
- Modify: `backend/app/services/community_detector.py`
- Modify: `backend/app/services/process_tracer.py`
- Modify: `backend/app/services/heritage_resolver.py`
- Modify: `backend/app/services/citation_reverify.py`
- Test: `backend/tests/test_code_graph_keys.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 85, 86, 87, 91
**Depends on:** Task 30
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 3 = 7

- [ ] **Step 1: Write the failing test**

All in `backend/tests/test_code_graph_keys.py`.

- `::test_reindexing_one_file_keeps_another_files_property` (integration): classes `A` in `a.py` and `B` in `b.py` each declare a property `name`; after reindexing `a.py`, `B`'s `has_property` edge still resolves to a node, and both property nodes exist with keys that include their owner and file. Fails today because the bare-name node is deleted with `a.py`.
- `::test_community_keys_are_stable_across_runs` (integration): two runs over an unchanged repository produce the same set of community node keys and write zero `member_of` rows on the second run (statement counter on that table); fails today because keys embed the Leiden `comm_id` and the layer is rewritten.
- `::test_unchanged_call_graph_skips_phases_nine_and_ten` (integration): an incremental run that changes only a comment runs neither `community_detector` nor `process_tracer`.
- `::test_type_environment_is_seeded_per_file` (integration): with `def config()` returning `Settings` in `conf.py`, a local variable `config` in `other.py` that neither imports nor defines `config` gains no member-call edge to `Settings`; a file that imports `config` does. Fails today because the seed is repository-global.
- `::test_process_tracer_reads_no_signature` (unit): the tracer's scoring reads no `signature` property (source scan), and a decorated framework entry point still scores through the properties the pipeline writes.
- `::test_citation_symbol_keys_survive_the_rekey` (integration, spec WP7): a `fact_sources` row whose `detail.symbol_key` names a class and a function before the re-key resolves through `citation_reverify` afterwards and is not marked stale. Add a property case to the same test only when Step 3.5's search finds that a property key can be cited; when it cannot, the commit body says so and the test has the two cases.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_code_graph_keys.py`

- [ ] **Step 3: Implement**

1. B4-18: property keys become file- and owner-qualified, following the key order of `app/utils/graph_keys.py`; update the consumer in `heritage_resolver.py`.
2. B4-17: derive a community key from a stable property of its members (the smallest member key), and skip phases 09 and 10 when the run changed no call, extends or import edge.
3. B4-16: seed a file's type environment only with names it imports or defines.
4. B4-22: remove the `signature` input from the tracer's multiplier.
5. Citations: first list which node kinds a code citation's `symbol_key` can name (`rg symbol_key backend/app`). If property or community keys can be cited, rewrite the stored `fact_sources.detail.symbol_key` values to the new form in this commit through a data statement in the run that performs the re-key (not a revision), and make `citation_reverify` accept the new form; if they cannot, state that in the commit body. The post-merge full reindex (Task 71) re-keys the stored nodes.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_code_graph_keys.py tests/test_code_pipeline.py tests/test_code_pipeline_integration.py tests/test_code_graph_labels.py tests/test_code_deriver.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests/test_code_graph_keys.py
git commit -m "fix(code): stable property and community keys"
```

### Task 32: Code indexing cleanups and last_commit_sha readers

**Files:**
- Modify: `backend/app/services/wiki_generator.py`
- Modify: `backend/app/services/repo_manager.py`
- Modify: `backend/app/services/task_registry.py`
- Modify: `backend/app/services/call_resolver.py`
- Modify: `backend/app/services/code_pipeline.py`
- Modify: `backend/app/services/repo_allowlist.py`
- Modify: `backend/app/models/code.py`
- Modify: `backend/app/schemas/code.py`
- Modify: `backend/scripts/benchlib/promotion_corpus.py`
- Modify: `frontend/src/hooks/api/use-code-api.ts`
- Test: `backend/tests/test_code_cleanups.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 90, 94, 95, 96
**UI/UX:** OP-4 — removes a response field no screen shows; no contract item is built here
**Depends on:** Task 31
**Evaluation:** files 3 - spec 2 - coupling 0 - risk 2 = 7

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_code_cleanups.py::test_repo_delete_removes_its_wiki_row` (integration): deleting a repository that has a `wiki_<repo_id>` config row leaves no such row; fails today because nothing deletes it.
- `::test_last_commit_sha_has_no_reader_or_writer` (unit, A47 code half): a source scan over `backend/app`, `backend/scripts` and `frontend/src` finds no `last_commit_sha`; fails today on the model, the response schema, the hook type and the benchlib INSERT.
- `::test_last_commit_sha_column_still_exists` (integration, A47): after `alembic upgrade head`, `information_schema.columns` still lists `code_files.last_commit_sha`.
- Removals with no new test (each after its `rg` proof): `WikiGenerator.generate`'s `force` parameter and cache branch; `TaskRegistry.get_all_running` and `cleanup_completed`; `CallResolver`'s `named_imports=` and `wildcard_imports=` arguments; `RepoManager.get_auth_token` with the tests that exist only for it; `_implements_split`'s discarded `implements_list`. B4-25's three stale comments (`expire_on_commit`, the Repositories refetch, the "unauthenticated MCP door") are corrected in place.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_code_cleanups.py`

- [ ] **Step 3: Implement**

1. B4-21: delete the wiki config row in `RepoManager.delete`, in the same transaction as the repo row.
2. Removal 8, readers only: drop `last_commit_sha` from the ORM model, `CodeFileResponse`, the frontend type and the raw INSERT in `promotion_corpus.py`. The column stays (register row 231 carries the drop). Because the model no longer maps the column, confirm `tests/test_schema_guard.py` and any model-versus-schema drift test still pass, and say in the commit body that the column is kept deliberately.
3. The removals and comment corrections listed in Step 1.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_code_cleanups.py tests/test_code_pipeline.py tests/test_schema_guard.py tests/test_sdk_generator.py && .venv/bin/python -m pytest -q scripts/benchlib/tests && (cd ../frontend && npm run typecheck)`

- [ ] **Step 5: Commit**

```bash
git add backend frontend/src/hooks/api/use-code-api.ts sdks
git commit -m "refactor(code): remove dead indexing leftovers"
```

### Task 33: Block vectors follow block text

**Files:**
- Modify: `backend/app/services/block_verbs.py`
- Modify: `backend/app/services/document_door.py`
- Modify: `backend/app/services/document_ingest.py`
- Modify: `backend/app/services/block_embeddings.py`
- Modify: `backend/app/services/block_embedding_refresh.py`
- Modify: `backend/app/services/embedder_registry.py`
- Modify: `backend/app/services/worklog_embeddings.py`
- Modify: `backend/app/services/relation_embeddings.py`
- Modify: `backend/app/services/entity_anchoring.py`
- Modify: `backend/app/api/routes/documents.py`
- Modify: `CLAUDE.md`
- Test: `backend/tests/test_block_vector_lifecycle.py`

**Interfaces:**
- Consumes: none
- Produces: C8

**Items:** 97, 99, 111, 112
**Depends on:** none
**Evaluation:** files 3 - spec 2 - coupling 0 - risk 2 = 7

- [ ] **Step 1: Write the failing test**

All in `backend/tests/test_block_vector_lifecycle.py`.

- `::test_document_block_edit_with_a_failed_embed_answers_success` (integration, A25): a `block_update` on a document block that changes its text, with the embedder stub raising, answers 200 with `blocks_embedded: 0`, the block's new text is stored, and no `block_embeddings__<slug>` row exists for that block. Fails today with a 500 and the old-text vector left behind.
- `::test_unchanged_repush_with_dimensions_makes_no_embed_call` (integration, A28): with the embedding purpose's `dimensions` configured and every block already embedded, a byte-identical `document_put` answers `unchanged` and the embedder stub records zero calls; fails today with one.
- `::test_refile_embeds_only_changed_blocks` (integration, A28): re-filing a ten-block document with one paragraph changed sends exactly one text to the embedder stub, and the nine unchanged blocks (new ids) carry vectors equal to the ones their text had before.
- `::test_vector_inserts_are_batched` (integration): filing a 200-block document runs at most 5 INSERT statements into the embedding partition.
- `::test_unembeddable_block_does_not_poison_the_sweep` (integration): with the embedder stub raising for one block's text, two consecutive `block_embedding_refresh` ticks over a 60-block backlog embed the other 59, and the second tick sends that block's text at most once; fails today with a failed batch plus single-row retries of the whole batch on every tick.
- `::test_one_fingerprint_registration_helper` (unit): an AST scan of `app/services` finds `CREATE TABLE IF NOT EXISTS`-registering helpers only in `embedder_registry.py`; `block_embeddings`, `worklog_embeddings`, `relation_embeddings` and `entity_anchoring` call `ensure_registered`.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_block_vector_lifecycle.py`

- [ ] **Step 3: Implement**

1. B5-2: for documents too, delete the touched block's vectors for every unretired fingerprint inside the verb's savepoint when its text or type changes; after commit, catch an embed failure and answer `blocks_embedded=0`.
2. B5-4: across a re-file, carry vectors over by exact block text (read the old `(text, vector)` pairs before the strip, inside the filing savepoint, under the active fingerprint only); resolve the fingerprint from `llm_fingerprint()` when `dimensions` is configured; batch vector INSERTs through `unnest`. A stale provider response is still discarded by the existing revalidation.
3. B5-16: on a failed batch, bisect it so one bad block is isolated in `log2(n)` calls, and remember its id in the job's state row to skip it for the next 6 ticks.
4. B5-17: `embedder_registry.ensure_registered` (C8) replaces the private copies. `triple_embeddings.py` keeps its copy until Task 46 deletes the module.
5. Correct the two `CLAUDE.md` sentences this changes ("An edit re-embeds the whole document" and "Resolving the active fingerprint costs one real embed call per `unchanged` re-push").

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_block_vector_lifecycle.py tests/test_block_verbs.py tests/test_block_pipeline.py tests/test_block_retrieval.py tests/test_page_document_isolation.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests/test_block_vector_lifecycle.py CLAUDE.md
git commit -m "fix(blocks): vectors follow the block text"
```

### Task 34: Attachment lock scope

**Files:**
- Modify: `backend/app/services/page_attachments.py`
- Modify: `backend/app/api/routes/page_attachments.py`
- Modify: `backend/app/services/page_import.py`
- Modify: `CLAUDE.md`
- Test: `backend/tests/test_document_attachment_concurrency.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 98
**Depends on:** none
**Evaluation:** files 1 - spec 2 - coupling 0 - risk 3 = 6

- [ ] **Step 1: Write the failing test**

All in `backend/tests/test_document_attachment_concurrency.py`.

- `::test_upload_in_progress_does_not_block_a_page_write` (integration, A26): with an upload paused mid-stream (the body generator waits on an event) and a cleanup task waiting for the exclusive attachment lock, a block write on a page of another project completes within 2 s; fails today because the upload holds the shared lock for the whole stream and the queued exclusive request blocks every writer behind it.
- `::test_upload_holds_no_transaction_while_streaming` (integration): while the stream is paused, the request session reports `in_transaction() is False`.
- `::test_interrupted_upload_leaves_no_row_and_no_file` (integration): a stream that raises midway leaves no `page_attachments` row and no file other than a `.part`, which the same request removes.
- `::test_collected_reference_is_still_refused` (integration): an attachment URL collected between the stream and the placement is refused under the lock as before.
- `::test_notion_import_takes_the_lock_per_file` (integration): during a paused two-file Notion import, a page write in another project completes within 2 s.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_document_attachment_concurrency.py`

- [ ] **Step 3: Implement**

1. B5-3: stream to a `.part` file with no lock and no open transaction, then take the shared lifecycle lock only around `os.replace`, the INSERT and the COMMIT; move the route's project SELECT after the stream. The Notion import takes the lock per placed file, not for the import.
2. Keep the protocol `CLAUDE.md` states: writers revalidate attachment URLs under the lock, and cleanup preserves placed bytes when the commit outcome is uncertain. Correct the sentence there that describes when the lock is taken.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_document_attachment_concurrency.py tests/test_page_attachments.py tests/test_page_attachment_routes.py tests/test_page_attachment_placement.py tests/test_page_attachment_cleanup.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests/test_document_attachment_concurrency.py CLAUDE.md
git commit -m "fix(pages): stream uploads outside the lock"
```

### Task 35: Document revision retention

**Files:**
- Modify: `backend/app/services/document_ingest.py`
- Modify: `backend/app/services/document_revisions.py`
- Modify: `backend/app/repositories/documents.py`
- Modify: `backend/app/services/events.py`
- Modify: `backend/app/api/routes/documents.py`
- Modify: `backend/app/api/mcp/server.py`
- Modify: `CLAUDE.md`
- Test: `backend/tests/test_document_revisions.py`
- Test: `backend/tests/test_event_taxonomy_map.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 102
**Depends on:** none
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 3 = 7

- [ ] **Step 1: Write the failing test**

All but the last in `backend/tests/test_document_revisions.py`; revision ages are set by updating `created_at` in the test.

- `::test_prune_needs_both_conditions` (integration, A27): a document with 60 revisions of which the oldest 20 are 100 days old gets a content-changing put; afterwards exactly the 10 revisions that are both beyond the newest 50 and older than 90 days are gone. A document with 60 revisions all 10 days old loses none; a document with 30 revisions all 200 days old loses none. Fails today because nothing prunes.
- `::test_prune_is_scoped_to_the_filed_document` (integration, A27): a second document with 60 old revisions is untouched by a put to the first.
- `::test_prune_journals_one_count_only_event_first` (integration, A27): the put writes one `document_revisions_pruned` event with `object_type` document, the document id and `payload == {"pruned": 10}` (no content, no revision ids), and the statement log of the put (a `before_cursor_execute` listener on the test engine) shows the `INSERT INTO events` for that row ahead of the `DELETE FROM document_revisions`.
- `::test_a_failed_prune_delete_rolls_the_filing_back` (integration, A27): with the `DELETE FROM document_revisions` statement made to raise, the put fails, and afterwards the document's content, its 60 revisions and the `events` table are exactly as before the put: no new revision and no `document_revisions_pruned` row.
- `::test_unjournalled_prune_is_skipped_and_the_put_succeeds` (integration, A27): with `record_event` returning `False` for that event type, the put answers success, the new revision is stored, and all 61 revisions remain.
- `::test_before_cursor_naming_a_pruned_revision_answers_404` (integration, A27): `GET /api/v1/documents/{id}/revisions?before=<pruned id>` answers 404, and MCP `document_revisions` with the same cursor answers its not-found envelope.
- `::test_unchanged_repush_prunes_nothing` (integration): a byte-identical re-push writes no revision and prunes none.
- `backend/tests/test_event_taxonomy_map.py` — the existing map test must list `document_revisions_pruned`; add it to `EVENT_TYPES` first.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_document_revisions.py tests/test_event_taxonomy_map.py`

- [ ] **Step 3: Implement**

1. Add `document_revisions_pruned` to `EVENT_TYPES` and the taxonomy map (taxonomy first).
2. In the filing body, inside its SAVEPOINT and only when the filing wrote a revision: count the document's revisions past the newest `REVISION_KEEP_NEWEST = 50` with `created_at` older than `REVISION_KEEP_DAYS = 90` days; when the count is non-zero, journal the count-only event, and delete those rows only if the journal row landed. Both constants are module constants in `document_revisions.py`.
3. The revision list resolves `before` to a row of that document and answers 404 when it does not exist.
4. `CLAUDE.md`: the Revisions bullet states the rule and its two numbers; the retention paragraph's sentence about "every earlier content of a document in `document_revisions` until the document is deleted" is corrected to the new rule.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_document_revisions.py tests/test_event_taxonomy_map.py tests/test_events.py tests/test_block_pipeline.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests CLAUDE.md
git commit -m "feat(documents): prune old revisions past fifty"
```

### Task 36: Document read and write cost

**Files:**
- Modify: `backend/app/services/block_verbs.py`
- Modify: `backend/app/services/document_door.py`
- Modify: `backend/app/services/page_door.py`
- Modify: `backend/app/services/document_ingest.py`
- Modify: `backend/app/services/document_connections.py`
- Modify: `backend/app/api/routes/documents.py`
- Test: `backend/tests/test_document_cost.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 100, 103, 104, 109, 110
**Depends on:** Task 33
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 2 = 6

- [ ] **Step 1: Write the failing test**

All in `backend/tests/test_document_cost.py`.

- `::test_block_verb_rewrites_only_changed_rows` (integration): a `block_update` that changes one block's text in a 50-block page leaves the `xmin` of at least 45 other block rows unchanged; fails today because `_PLACE` rewrites every row.
- `::test_block_read_fetches_content_once` (integration): reading a 200-block document's blocks runs no statement containing `substring(` over `content`, and each block's `source` still equals the slice of `content` at its `char_span`.
- `::test_parse_runs_off_the_event_loop` (integration): with the markdown parser patched to record its thread, a `document_put` parses on a thread other than the loop's.
- `::test_block_cap_is_checked_before_any_insert` (integration): a document that parses to more than `MAX_BLOCKS` blocks is refused with `DocumentTooLarge` and zero INSERT statements into `blocks` (statement counter); fails today because every row is inserted before the check.
- `::test_connections_are_memoised_per_content` (integration): two connection reads of an unchanged document run the ANN probes once; a put that changes `content_hash`, or a rotation of the active fingerprint, runs them again.
- `::test_document_list_pages_before_counting_blocks` (integration): with `enable_seqscan` unchanged and 300 documents seeded, `EXPLAIN` of the list statement with `LIMIT 20` shows the block count computed for 20 documents (a LATERAL or correlated subquery under the Limit node), and the response's `block_count` values equal a direct count.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_document_cost.py`

- [ ] **Step 3: Implement**

1. B5-5: add `IS DISTINCT FROM` guards so `_PLACE` updates only rows whose `order_index`, `char_span`, `properties` or `parent_id` changed.
2. B5-8: fetch `content` once per read and slice by span in Python, in both `document_door.py` and `page_door.py`.
3. B5-9: parse through `asyncio.to_thread`, and check the draft block count against `MAX_BLOCKS` before `insert_blocks` (still inside the SAVEPOINT, so the refusal rolls back the row and the `document_filed` event).
4. B5-14: memoise connection results in process keyed on `(document_id, content_hash, fingerprint)`, bounded to 256 entries, with one comment naming the single worker.
5. B5-15: page `documents` first, then count blocks per listed document.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_document_cost.py tests/test_block_verbs.py tests/test_block_pipeline.py tests/test_page_document_isolation.py tests/test_document_parsers.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests/test_document_cost.py
git commit -m "perf(documents): cheaper block reads and writes"
```

### Task 37: Document door typing, attribution and dead exports

**Files:**
- Modify: `backend/app/api/routes/documents.py`
- Modify: `backend/app/api/mcp/server.py`
- Modify: `backend/app/services/document_door.py`
- Modify: `backend/app/services/block_pipeline.py`
- Modify: `backend/app/services/document_ingest.py`
- Modify: `backend/app/services/block_embeddings.py`
- Test: `backend/tests/test_document_door_inputs.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 105, 107, 108
**Depends on:** Task 36
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 1 = 5

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_document_door_inputs.py::test_malformed_block_ids_answer_422` (integration): `parent_id="nope"` on the document block insert route, `after_block_id="nope"` on insert and `new_parent_id="nope"` on move each answer 422; the MCP twins answer a validation tool error and never an unhandled exception. Fails today with a 500.
- `::test_subtree_rename_journals_its_actor` (integration): a `POST /api/v1/documents/rename` by a logged-in user journals `document_updated` rows whose `actor` is that user; the MCP `document_update` subtree mode with a `capture` key journals rows whose `api_key_id` is that key's id. Fails today with both NULL.
- Removals with no new test (after `rg` shows only test callers): `ingest_documents`, `DocumentSource`, `file_documents_isolated`, `DocumentFileJob`, `DocumentFileFailure`, `block_embeddings.resolve_read_fingerprint` and `block_vectors`, with the tests that exist only to cover them and the docstring mention in `scripts/import_docs_corpus.py`.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_document_door_inputs.py`

- [ ] **Step 3: Implement**

1. B5-13: type the three ids `UUID | None` on the document block routes and validate them in the MCP twins before the door call.
2. B5-10: thread `actor` and `api_key_id` through `rename_documents`, as `delete_documents` already takes them.
3. B5-12: the removals listed in Step 1; `tests/test_block_pipeline.py`'s reachability scan must still pass.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_document_door_inputs.py tests/test_block_pipeline.py tests/test_block_verbs.py tests/test_api/test_rest_conformance.py tests/test_sdk_generator.py`

- [ ] **Step 5: Commit**

```bash
git add -A backend/app backend/tests backend/scripts sdks
git commit -m "fix(documents): typed block ids, attributed renames"
```

### Task 38: Function-scoped session and streaming twins

**Files:**
- Modify: `backend/app/api/deps.py`
- Modify: `backend/app/database.py`
- Modify: `backend/app/api/routes/chat.py`
- Modify: `backend/app/api/routes/analytics.py`
- Modify: `CLAUDE.md`
- Test: `backend/tests/test_session_scope.py`
- Test: `backend/tests/test_session_resource_lifetimes.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 115
**Depends on:** Task 14
**Evaluation:** files 1 - spec 2 - coupling 2 - risk 3 = 8

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_session_scope.py::test_change_password_is_durable_before_the_response` (integration, A29): with the ASGI `send` wrapped, at the moment the `http.response.start` message of `POST /api/v1/auth/change-password` is sent, a second connection already reads the new password hash; fails today because the request-scoped session commits after the response.
- `::test_config_save_is_durable_before_the_response` (integration, A29): the same check on the system-prompts `PUT`, plus: the in-process prompt cache is updated only after the commit (a save whose commit is patched to raise leaves the cache at the old value).
- `::test_no_streaming_handler_resolves_a_function_scoped_dependency` (unit, A29): a scan over every route of the app object fails when a handler whose return annotation or body returns `StreamingResponse` depends, directly or through a sub-dependency, on the function-scoped session or on one of the six function-scoped providers; it passes for exactly two streaming routes, `POST /api/v1/chat/completions` and `POST /api/v1/analytics/reprocess/stream`, which use the request-scoped twins. Fails today because no such split exists.
- `::test_every_write_route_takes_the_function_scoped_session` (unit, A29): every route with method POST, PUT, PATCH or DELETE other than those two resolves the session through the function-scoped dependency.
- `backend/tests/test_session_resource_lifetimes.py::test_chat_stream_keeps_its_lease_until_the_stream_ends` (integration): the chat stream's LLM lease is still held while the body streams and released after the last chunk and after a client disconnect; the route's explicit commits leave no transaction open during the stream (Task 14's test still passes).

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_session_scope.py tests/test_session_resource_lifetimes.py`

- [ ] **Step 3: Implement**

1. B6-5: make the session dependency and the six generator providers in `api/deps.py` function-scoped (`Depends(..., scope="function")` behind one `SessionDep` alias; check FastAPI's rule that a function-scoped dependency may not depend on a request-scoped one). The commit then runs before the response on every write route, including login and change-password.
2. Add request-scoped twins of the chat and analytics providers, used only by the two streaming routes; those routes commit explicitly and hold the LLM lease through the stream.
3. Fix every test that relied on the old order; do not weaken an assertion to pass.
4. `CLAUDE.md`'s "Async session lifetime" bullet gains the rule: the session is function-scoped, and only the two streaming routes use request-scoped twins.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q -n 4 --dist loadfile tests/test_session_scope.py tests/test_session_resource_lifetimes.py tests/test_chat.py tests/test_chat_stream_resources.py tests/test_auth_security.py tests/test_auth_token_rotation.py tests/test_api`

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests CLAUDE.md
git commit -m "fix(api): commit before the response is sent"
```

### Task 39: One config-row patch helper

**Files:**
- Modify: `backend/app/services/config.py`
- Modify: `backend/app/api/routes/config.py`
- Modify: `backend/app/services/notifications.py`
- Modify: `backend/app/services/repo_allowlist.py`
- Test: `backend/tests/test_config_row_patch.py`

**Interfaces:**
- Consumes: none
- Produces: C6

**Items:** 128
**Depends on:** Task 38
**Evaluation:** files 1 - spec 2 - coupling 2 - risk 2 = 7

- [ ] **Step 1: Write the failing test**

All in `backend/tests/test_config_row_patch.py`.

- `::test_two_concurrent_saves_of_one_row_both_survive` (integration, A29): two sessions each call `patch_config_row` on `system_prompts`, one setting key `a` and one key `b`, with the first paused inside `mutate` until the second has started; the stored row holds both keys. The same case is run through the system-prompts, repo-allowlist and notifications routes with `asyncio.gather`. Fails today because those writers read-modify-write without the row lock.
- `::test_helper_creates_a_missing_row` (integration): patching a key with no row inserts it, and two concurrent first saves produce one row holding both changes.
- `::test_no_route_writes_a_config_row_outside_the_helper` (unit): an AST scan of `api/routes/config.py`, `services/notifications.py` and `services/repo_allowlist.py` finds no assignment to a `Config` row's `value` and no `insert(Config)` outside `services/config.py`.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_config_row_patch.py`

- [ ] **Step 3: Implement**

1. Per C6, add `patch_config_row` to `services/config.py`, built on the existing `_lock_config_row` (move that helper there if it lives in the route module).
2. Route every config-row writer in the three files through it. Validation stays in each route before the call; `mutate` is pure.
3. `job_registry`'s `job:<key>` rows are Task 40's and are not touched here.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_config_row_patch.py tests/test_config_graph_channels_and_ladder.py tests/test_session_scope.py tests/test_api/test_rest_conformance.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests/test_config_row_patch.py
git commit -m "fix(config): lock every config row write"
```

### Task 40: Job state, floors and run records

**Files:**
- Modify: `backend/app/services/job_registry.py`
- Modify: `backend/app/services/job_runners.py`
- Modify: `backend/app/api/routes/jobs.py`
- Modify: `backend/app/services/events.py`
- Modify: `CLAUDE.md`
- Test: `backend/tests/test_job_registry.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 119, 120, 121, 122, 134
**Depends on:** Task 39
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 2 = 6

- [ ] **Step 1: Write the failing test**

All in `backend/tests/test_job_registry.py`.

- `::test_code_floor_applies_to_a_stored_row` (integration, A30): a `job:<key>` row stored with `min_interval_seconds: 5` and a `Job` registered with a floor of 30 schedules no sooner than 30 s, and the jobs `GET` reports 30; fails today because the stored value wins.
- `::test_disable_answers_while_the_job_runs` (integration, A30): with a job's run paused inside its runner, `PUT /api/v1/jobs/{key}` disabling it and `PUT /api/v1/jobs/{key}/config` each answer within 1 s, and the change is in the row when the run ends; fails today because both wait on the run lock.
- `::test_last_run_comes_from_job_runs` (integration, A30): a job whose only `job_runs` row is older than 5,000 newer rows of other jobs still shows its `last_run_at`, `last_status` and `last_error` on the jobs `GET` after `job_run_cleanup` has run; fails today because the cleanup's row ceiling can drop it and the state lives in the config row.
- `::test_tick_writes_no_config_row` (integration): three scheduled ticks of a job update its `job:<key>` config row zero times (statement counter).
- `::test_stored_last_keys_are_ignored_and_dropped` (integration): a row holding `last_run_at` from an older build is served from `job_runs` instead, and the next save writes the row without any `last_*` key.
- `::test_failure_notification_dedupes_on_the_previous_run` (integration): two consecutive failures with the same error send one notification; a different error sends a second.
- `::test_manual_trigger_is_recorded` (integration): `POST` trigger writes a `job_runs` row with `trigger = "manual"`; a scheduled run writes `schedule`.
- `::test_idle_cleanup_journals_nothing` (integration): each of the three hourly cleanup jobs that journal `maintenance_run`, run with nothing to do, writes no `events` row and a `job_runs` row whose result carries zero counts; with work done it journals one row carrying the counts.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_job_registry.py`

- [ ] **Step 3: Implement**

1. B6-9: stop persisting `min_interval_seconds`; always read `Job.min_interval_seconds`, as `max_run_seconds` is read.
2. B6-D4: keep only operator choices in the `job:<key>` row. `last_*` for the Jobs screen and for the notification dedupe is read from the job's newest `job_runs` row; `job_run_cleanup` keeps at least the newest row of every job; stored `last_*` keys are ignored on read and dropped on the next save.
3. B6-10: guard config read-modify-write with a per-job config lock separate from the run lock. A manual trigger still takes the run lock and still answers 409 while it is held.
4. B6-12: pass `trigger="manual"` from `trigger()` through `_run_once` into `_record_run`.
5. B6-13: the three cleanup runners return their counts and journal `maintenance_run` only on error or non-zero work.
6. `CLAUDE.md`'s Scheduling paragraph: correct "State lives in `config` rows `job:<key>`" to say operator settings live there and run state in `job_runs`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_job_registry.py tests/test_code_deriver.py tests/test_graph_arm_jobs.py tests/test_dream_jobs.py tests/test_events.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests/test_job_registry.py CLAUDE.md
git commit -m "fix(jobs): run state from job_runs, floors from code"
```

### Task 41: Boot recovery, health state and partition maintenance

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/services/job_registry.py`
- Modify: `backend/app/services/job_runners.py`
- Modify: `backend/app/services/events.py`
- Modify: `CLAUDE.md`
- Test: `backend/tests/test_boot_reconciliation.py`
- Test: `backend/tests/test_health.py`

**Interfaces:**
- Consumes: C1 (`classifier_unavailable`, already served)
- Produces: C1 (`pipeline_state`)

**Items:** 123, 129, 132
**Depends on:** Task 11, Task 40
**Evaluation:** files 2 - spec 2 - coupling 1 - risk 2 = 7

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_boot_reconciliation.py::test_llm_setup_failure_still_reconciles_partitions` (integration, A31): a boot whose LLM setup raises still creates the `events` partitions (current month and three ahead) and runs the backfill reconciliation; fails today because both sit inside the LLM `try`.
- `backend/tests/test_health.py::test_health_reports_failed_at_boot` (integration, A31): after that boot `GET /health` answers 200 with `pipeline_state: "failed_at_boot"`; a normal boot answers `ok`; an uninitialised instance `not_configured`; a read-only instance `read_only`.
- `backend/tests/test_boot_reconciliation.py::test_pipeline_is_built_once_an_orchestrator_is_installed` (integration): after a failed LLM setup, saving a valid LLM configuration builds the pipeline, `pipeline_state` becomes `ok`, and the next `buffer_flush` tick drains; while it is missing the flush run records a skip reason instead of `ok`.
- `::test_partitions_exist_three_months_ahead_with_the_cleanup_disabled` (integration, A32): with `pipeline_failure_cleanup` disabled, advancing the scheduler loop's clock by one hour leaves an `events` partition for each of the next three months; fails today because maintenance rides on that job and looks one month ahead.
- `::test_job_count_is_still_twenty_seven` (unit): the registered roster has 27 jobs and none named for partition maintenance.
- `::test_lifespan_has_no_legacy_enrichment_copy` (unit): `app/main.py` contains no copy of the legacy `enrichment_config` row (source scan); a boot with only the old row present still starts.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_boot_reconciliation.py tests/test_health.py`

- [ ] **Step 3: Implement**

1. B6-14: move the partition and backfill reconciliations out of the LLM `try`; record the boot failure; build a missing pipeline when a configuration save installs an orchestrator; `buffer_flush` reports the skip; serve `pipeline_state` (C1).
2. B6-20: `_MONTHS_AHEAD = 3`, and the registry's scheduler loop calls `events_ensure_partition` reconciliation once an hour itself, outside any job; the arm on `pipeline_failure_cleanup` stays. Read-only mode never arms the loop, as today.
3. B6-D1: before removing the legacy `enrichment_config` copy, confirm that the live row carries `batch_size` with the read-only query Global Constraints' Host limits allows: `docker exec darkmem-prod-postgres-1 psql -U darkmem -d darkmem -Atc "select value ? 'batch_size' from config where key = 'enrichment_config'"`, expected `t`. If it prints `f` or no row, keep the copy and close that part `not reproduced: production still needs the copy`. Make the Postgres-only mode's failure visible through `pipeline_state`; keep the proxy guard.
4. `CLAUDE.md`: the events paragraph says reconciliation runs at boot, hourly from the scheduler loop and on `pipeline_failure_cleanup`, three months ahead; the health sentence names `pipeline_state`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_boot_reconciliation.py tests/test_health.py tests/test_read_only_boot.py tests/test_events.py tests/test_code_deriver.py tests/test_job_registry.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests CLAUDE.md
git commit -m "fix(boot): reconcile partitions outside the LLM try"
```

### Task 42: Socket revalidation cache and call-log flush

**Files:**
- Modify: `backend/app/api/websocket.py`
- Modify: `backend/app/api/routes/auth.py`
- Modify: `backend/app/services/mcp_call_log.py`
- Test: `backend/tests/test_websocket.py`
- Test: `backend/tests/test_mcp_call_log_flush.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 126, 130
**Depends on:** Task 38
**Evaluation:** files 1 - spec 2 - coupling 1 - risk 3 = 7

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_websocket.py::test_idle_socket_revalidates_without_a_query` (integration): an open socket idle for three one-second revalidation intervals runs zero database statements (statement counter); fails today with two per second.
- `::test_logout_closes_the_socket_within_two_seconds` (integration): after the socket's token is blocklisted through the logout route, the socket closes with reason `Session expired or revoked` within 2 s.
- `::test_password_change_closes_other_sessions_sockets` (integration): a password change closes a socket of another session within 2 s.
- `::test_expiry_closes_the_socket_without_a_query` (integration): a socket whose token expires is closed at its next interval.
- `::test_broadcast_does_not_wait_on_revalidation` (integration): with the revalidation source patched to take 1 s, a broadcast to ten sockets completes in under 0.5 s.
- `backend/tests/test_mcp_call_log_flush.py::test_failed_flush_keeps_its_batch` (integration): with the INSERT patched to raise once, the popped batch of 10 calls is written by the next flush; fails today because it is discarded.
- `::test_buffer_overflow_is_counted` (unit): when requeueing would exceed the buffer bound, the overflow is added to the dropped counter the summary route serves.
- `::test_failed_flush_backs_off` (unit): after a failure the next attempt is delayed, doubling up to 60 s, and resets on success.
- `::test_validation_error_text_carries_no_input` (unit): a tool call refused by argument validation, with a `content` argument holding `SECRET-MARK`, is logged with an `error` that names the error type and field location and does not contain `SECRET-MARK`.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_websocket.py tests/test_mcp_call_log_flush.py`

- [ ] **Step 3: Implement**

1. B6-21: keep the password-change epoch and the set of blocklisted token ids in process, loaded at boot and updated by the routes that change them (logout, refresh, change-password) after their commit; the one-second revalidation reads the cache and validates outside the send lock. One comment names the single worker and the restore cycle stopping the app. The one-second contract and both close reasons are unchanged; read-only mode, which blocklists nothing, keeps working.
2. B6-17: on a failed flush requeue the batch at the front, bounded by the buffer size, count any overflow as dropped, and back off; reduce validation errors to type and location before buffering.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_websocket.py tests/test_mcp_call_log_flush.py tests/test_auth_token_rotation.py tests/test_read_only_doors.py tests/test_mcp_auth.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests
git commit -m "perf(ws): revalidate sockets from memory"
```

### Task 43: Remove the context-boost arm

**Files:**
- Modify: `backend/app/services/rank_fusion.py`
- Modify: `backend/app/services/layer_composition.py`
- Modify: `backend/app/services/chat.py`
- Modify: `backend/app/services/memory.py`
- Modify: `backend/app/services/feature_flags.py`
- Modify: `backend/app/config.py`
- Modify: `backend/app/schemas/envelope.py`
- Modify: `backend/app/api/routes/knowledge_search.py`
- Modify: `backend/app/api/mcp/server.py`
- Modify: `backend/scripts/benchlib/arm_ablation.py`
- Modify: `docs/two-door-parity.md`
- Modify: `CLAUDE.md`
- Test: `backend/tests/test_context_boost_removed.py`

**Interfaces:**
- Consumes: none
- Produces: C4 (`w_context_boost`, `community_injection_enabled`, `by_context_conflict`)

**Items:** 20
**Depends on:** Task 15
**Evaluation:** files 2 - spec 2 - coupling 1 - risk 2 = 7

- [ ] **Step 1: Write the failing test**

All in `backend/tests/test_context_boost_removed.py`.

- `::test_no_context_boost_name_remains_in_the_backend` (unit, A45): a source scan over `backend/app` and `backend/scripts/benchlib` finds none of `w_context_boost`, `community_injection_enabled`, `by_context_conflict`, `CONTEXT_BOOST_FLAG`; fails today on each.
- `::test_stored_keys_are_not_served` (integration, A45): with a `feature_flags` config row holding `w_context_boost: 0.4` and `community_injection_enabled: true`, the flags `GET` answer carries neither key, and a flags `PUT` naming either answers 422.
- `::test_retrieval_order_is_unchanged` (integration, A45): for a seeded corpus of 30 memories and five fixed queries, the ids returned by `memory_search`, by chat retrieval and by `knowledge_search` equal a list recorded from the same seed before the removal (record the list in Step 2, on the unmodified code, into the test file).
- `::test_envelope_excluded_has_no_context_counter` (integration): the retrieval envelope of chat and of MCP `knowledge_search` has an `excluded` object without `by_context_conflict`.
- `backend/tests/test_ranking_arms_zero.py` — existing: `RANK_ARMS` lists `w_importance`, `w_heat`, `w_recency` only, and each is still inert at weight 0.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_context_boost_removed.py tests/test_ranking_arms_zero.py`
Before any edit, run the order case once with recording on and paste the five id lists into the test as its expected values.

- [ ] **Step 3: Implement**

1. Delete the context half of `rank_fusion.py` (the declared-context matching and its arm), the `declared_context` plumbing in `layer_composition.py`, `chat.py`, `memory.py`, `knowledge_search.py` and the MCP tool, the `by_context_conflict` counter in `schemas/envelope.py`, and `community_injection_enabled` with its graph channel row. Remove the three names from `FEATURE_FLAGS_DEFAULTS` and the flags schema; the reader serves only declared keys, so stored rows are not rewritten.
2. Remove `CONTEXT_BOOST_FLAG` and its arm from `scripts/benchlib/arm_ablation.py` with its tests.
3. `docs/two-door-parity.md` records the wire change (the envelope no longer carries `by_context_conflict`); `CLAUDE.md`'s Feature flags paragraph lists the three remaining ranking arms and drops `community_injection_enabled`.
4. The demo's copies and the Settings switch leave in Task 45.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_context_boost_removed.py tests/test_ranking_arms_zero.py tests/test_feature_flags_rank_arms.py tests/test_chat_retrieval_parity.py tests/test_layer_composition.py tests/test_door_parity.py tests/test_sdk_generator.py && .venv/bin/python -m pytest -q scripts/benchlib/tests`

- [ ] **Step 5: Commit**

```bash
git add -A backend docs/two-door-parity.md CLAUDE.md sdks
git commit -m "refactor(retrieval): remove the context-boost arm"
```

### Task 44: Remove the inject trio and the Distribution policy

**Files:**
- Modify: `backend/app/api/routes/distribution.py`
- Modify: `backend/app/services/inject_adapters.py`
- Modify: `backend/app/services/client_connect.py`
- Modify: `backend/app/services/content_surfaces.py`
- Modify: `backend/scripts/connect.py`
- Modify: `docs/two-door-parity.md`
- Modify: `CLAUDE.md`
- Test: `backend/tests/test_distribution.py`
- Test: `backend/tests/test_inject_adapters.py`
- Test: `backend/tests/test_connect_script.py`

**Interfaces:**
- Consumes: none
- Produces: C4 (`policy`, `watched`, `refresh`, the policy route)

**Items:** 25
**Depends on:** none
**Evaluation:** files 2 - spec 2 - coupling 1 - risk 2 = 7

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_distribution.py::test_inject_modules_and_policy_route_are_gone` (unit, A44): `importlib.util.find_spec` returns `None` for `app.services.inject_watch`, `inject_fill`, `inject_block` and `inject_journal`; no route of the app object matches `PUT /api/v1/distribution/policy`; fails today on all five.
- `::test_distribution_get_has_no_policy_keys` (integration, A44): the `GET` answer has no `policy`, `watched` or `refresh` key and still lists the adapters.
- `backend/tests/test_inject_adapters.py::test_watch_cadence_is_refused_with_a_reason` (unit): an adapter row declaring the `watch` cadence is refused with a message containing "watch cadence was removed"; the other cadences load.
- `backend/tests/test_connect_script.py::test_connect_entry_resolves_an_adapter` (integration, A44): calling `scripts/connect.py`'s entry function against a test session with a known client name returns that client's adapter and writes its config output to a temporary directory.
- `backend/tests/test_events.py` — existing: `inject` and `inject_curbed` are still in `EVENT_TYPES`, so journalled rows render.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_distribution.py tests/test_inject_adapters.py tests/test_connect_script.py`

- [ ] **Step 3: Implement**

1. After `rg` shows the only importers are each other, the distribution route, `inject_adapters` and their own tests: delete `inject_watch.py`, `inject_fill.py`, `inject_block.py`, `inject_journal.py` and `tests/test_inject_watch.py`, `test_inject_fill.py`, `test_inject_block.py`, `test_inject_events.py`.
2. `distribution.py`: remove the policy `PUT`, the `token_budget`, `watch_enabled` and `curbed` fields and the three `GET` keys; correct its module comment about the curb row's reader.
3. `inject_adapters.py`: drop the `watch` cadence and refuse a row declaring it. `client_connect.py` and `scripts/connect.py` keep working without the removed modules; add one module docstring line to each saying they are reached only from the CLI.
4. Remove the policy route's rows from `content_surfaces.py` and `docs/two-door-parity.md`, which also gains the sentence: "Any future inject writer ships with a server-enforced curb." Run the guards leg and re-read the two prose counts.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_distribution.py tests/test_inject_adapters.py tests/test_connect_script.py tests/test_events.py tests/test_content_surface_scoping.py tests/test_door_parity.py tests/test_api/test_rest_conformance.py tests/test_sdk_generator.py tests/test_spa_edge.py tests/test_inert_objects.py`

- [ ] **Step 5: Commit**

```bash
git add -A backend docs/two-door-parity.md CLAUDE.md sdks
git commit -m "refactor(inject): remove the unreached inject trio"
```

### Task 45: Settings without dead controls

**Files:**
- Modify: `frontend/src/features/settings/components/flags-tab.tsx`
- Modify: `frontend/src/features/settings/use-flags-tab-binding.ts`
- Modify: `frontend/src/features/settings/components/distribution-tab.tsx`
- Modify: `frontend/src/hooks/api/use-distribution-api.ts`
- Modify: `frontend/src/hooks/api/use-graph-api.ts`
- Modify: `frontend/src/features/chat/lib/retrieval.ts`
- Modify: `frontend/src/demo/data/settings-curated.ts`
- Test: `frontend/src/features/settings/components/flags-tab.dead-controls.test.tsx`
- Test: `frontend/src/features/settings/components/distribution-tab.test.tsx`
- Test: `frontend/src/features/chat/lib/retrieval.test.ts`

**Interfaces:**
- Consumes: C4
- Produces: none

**Items:** 20, 25, 27, 32
**UI/UX:** UI-4
**Depends on:** Task 17, Task 43, Task 44
**Evaluation:** files 2 - spec 2 - coupling 1 - risk 1 = 6

- [ ] **Step 1: Write the failing test**

- `flags-tab.dead-controls.test.tsx::shows no control that steers nothing` (unit, A45): the rendered Flags tab has no switch labelled for community injection, no "unmeasured" badge anywhere, and each of the importance, heat and recency arm rows shows the line "Turned on only after a measured retrieval win"; fails today on the switch and the badge.
- `distribution-tab.test.tsx::carries no token budget, watch switch or curb` (unit, A44): the rendered Distribution tab has no field labelled token budget, no watch switch and no curb control, sends no `PUT` to `/api/v1/distribution/policy` on any interaction, and still lists the adapters from the `GET`.
- `frontend/src/features/chat/lib/retrieval.test.ts::reads an envelope without by_context_conflict` (unit): an envelope whose `excluded` lacks the key produces the same exclusion summary as before minus the context line, and no `undefined` text.
- `::no removed name remains in the frontend` (unit, A45): a scan of `frontend/src` (through `import.meta.glob` with `?raw`) finds none of `w_context_boost`, `community_injection_enabled`, `by_context_conflict`, `useVectorProjection`, `flag_measurements`, `token_budget`, `watch_enabled`.

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/features/settings src/features/chat/lib`

- [ ] **Step 3: Implement**

1. Remove the community-injection switch, the measurement badge and its data path from the Flags tab and its binding; add the fixed line under each dormant rank arm as the library's helper text.
2. Remove the three Distribution controls, their mutation hook and the demo's copies; the tab keeps its adapter list and its empty state.
3. Remove `useVectorProjection` from `use-graph-api.ts`, the three names from `demo/data/settings-curated.ts` with their tests, and the `by_context_conflict` read from `retrieval.ts`.
4. Check the tab at 1280x800 and 1920x1080 in both themes through Storybook or the demo build before reporting; record the screenshot paths for Task 70.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/features/settings src/features/chat src/demo && npm run typecheck`

- [ ] **Step 5: Commit**

```bash
git add -A frontend/src
git commit -m "refactor(settings): remove controls that steer nothing"
```

### Task 46: Remove triple embeddings and drop its empty tables

**Files:**
- Create: `backend/migrations/versions/0005_drop_triple_embeddings.py`
- Modify: `backend/app/services/embedder_registry.py`
- Modify: `CLAUDE.md`
- Test: `backend/tests/test_drop_triple_embeddings.py`

**Interfaces:**
- Consumes: C7 (`0004_code_edge_file_indexes` as `down_revision`)
- Produces: C7 (`0005_drop_triple_embeddings`)

**Items:** 26
**Depends on:** Task 30, Task 33
**Evaluation:** files 1 - spec 2 - coupling 1 - risk 3 = 7

- [ ] **Step 1: Write the failing test**

All in `backend/tests/test_drop_triple_embeddings.py`.

- `::test_registration_creates_no_triple_table` (integration): registering a new fingerprint creates no table whose name starts with `triple_embeddings__`, and `_TABLE_TEMPLATES` has no `triple_embeddings` entry; fails today because every registration creates one with an HNSW index.
- `::test_revision_drops_empty_tables_and_keeps_a_populated_one` (integration): on a database migrated to `0004`, with two `triple_embeddings__<slug>` tables created by hand, one empty and one holding a row, `alembic upgrade 0005_drop_triple_embeddings` drops the empty one, leaves the populated one in place, logs a line naming it with `rows=1`, and exits 0.
- `::test_revision_is_a_no_op_without_such_tables` (integration): the upgrade succeeds on a database with no such table.
- `::test_module_is_gone` (unit): `importlib.util.find_spec("app.services.triple_embeddings")` is `None`.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_drop_triple_embeddings.py`

- [ ] **Step 3: Implement**

1. After `rg triple_embeddings backend/app backend/scripts` shows no production importer: delete `app/services/triple_embeddings.py` and `tests/test_triple_embeddings.py`, and remove the family from `embedder_registry._TABLE_TEMPLATES` and from any list derived from it.
2. Revision `0005_drop_triple_embeddings`: list tables in the current schema whose name matches `triple_embeddings\_\_%`; for each, `DROP TABLE` when `SELECT count(*)` is 0, else log `kept <name> rows=<n>` through the Alembic logger. A parent table `triple_embeddings`, if the baseline created one, is dropped only when it has no remaining child and no row. The downgrade recreates nothing and says so.
3. `CLAUDE.md`'s embedder paragraph drops `triple_embeddings` from the family list.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_drop_triple_embeddings.py tests/test_schema_guard.py tests/test_block_vector_lifecycle.py tests/test_block_retrieval.py`

- [ ] **Step 5: Commit**

```bash
git add -A backend CLAUDE.md
git commit -m "refactor(vault): drop the unused triple embeddings"
```

### Task 47: Remove the fact-side stated-expiry arm

**Files:**
- Modify: `backend/app/services/verification_recompute.py`
- Modify: `backend/app/repositories/knowledge_triples.py`
- Modify: `backend/app/services/entity_merge.py`
- Modify: `backend/app/services/fact_lift.py`
- Modify: `CLAUDE.md`
- Test: `backend/tests/test_stated_expiry_arm_removed.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 40
**Depends on:** Task 20
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 2 = 6

- [ ] **Step 1: Write the failing test**

All in `backend/tests/test_stated_expiry_arm_removed.py`.

- `::test_no_code_reads_or_writes_the_fact_column` (unit, A47): a source scan over `backend/app` finds the string `stated_expiry` only in files on the test's explicit allowlist: `app/services/stated_expiry.py`, plus each file that `rg -l stated_expiry backend/app` still lists after Step 3 for the memory-side derivation of `memories.expires_at` (write those paths into the allowlist with one comment each saying what the file uses it for; a fact-side file is never added); no line names `knowledge_triples.stated_expiry`, `StatedExpiryOutcome`, or a `stated_expiry` key in `knowledge_triples._COLUMNS`. Fails today on the close arm, the merge `LEAST` and `insert_open`.
- `::test_fact_column_and_index_still_exist` (integration, A47): after `alembic upgrade head`, `knowledge_triples.stated_expiry` and its partial index are present.
- `::test_memory_expiry_is_still_derived_from_a_stated_expiry` (integration, A47): `tests/test_self_expiring_memories.py`'s behaviour holds: a memory stating an expiry gets `memories.expires_at`.
- `::test_merge_fold_keeps_the_earlier_reference_and_valid_times` (integration): a fact merge still takes the earlier `reference_time` and `valid_at`.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_stated_expiry_arm_removed.py`

- [ ] **Step 3: Implement**

1. Remove the close arm in `verification_recompute.py`, `StatedExpiryOutcome`, the `stated_expiry` parameter of `insert_open`, the merge `LEAST` on that column, the column's entry in `knowledge_triples._COLUMNS`, and `tests/test_stated_expiry_facts.py`.
2. Keep `app/services/stated_expiry.py` and `tests/test_self_expiring_memories.py` untouched. The column and index stay (register row 230).
3. `CLAUDE.md`: the `repo_entity_merge` paragraph's "the belief window takes the earlier `reference_time` / `valid_at` / `stated_expiry`" loses `stated_expiry`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_stated_expiry_arm_removed.py tests/test_self_expiring_memories.py tests/test_fact_lift.py tests/test_dream_jobs.py tests/test_schema_guard.py`

- [ ] **Step 5: Commit**

```bash
git add -A backend CLAUDE.md
git commit -m "refactor(vault): remove the dead stated-expiry arm"
```

### Task 48: Drop blocks.search_vector and remove the PDF parser

**Files:**
- Create: `backend/migrations/versions/0006_drop_blocks_search_vector.py`
- Modify: `backend/tests/test_notes_schema.py`
- Modify: `backend/tests/test_pages_schema.py`
- Modify: `backend/app/services/document_parsers.py`
- Modify: `backend/app/services/block_pipeline.py`
- Modify: `backend/pyproject.toml`
- Modify: `backend/requirements.lock`
- Modify: `frontend/src/features/documents/components/block-editor.tsx`
- Modify: `CLAUDE.md`
- Test: `backend/tests/test_drop_blocks_search_vector.py`
- Test: `backend/tests/test_document_parsers.py`

**Interfaces:**
- Consumes: C7 (`0005_drop_triple_embeddings` as `down_revision`)
- Produces: C7 (`0006_drop_blocks_search_vector`)

**Items:** 101, 106
**UI/UX:** OP-4 — corrects one code comment in the block editor; no contract item is built here
**Depends on:** Task 46
**Evaluation:** files 2 - spec 2 - coupling 1 - risk 3 = 8

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_drop_blocks_search_vector.py::test_column_and_index_are_gone_and_rows_survive` (integration): on a database migrated to `0005` and holding one filed document and one page (blocks counted before), `alembic upgrade head` leaves no `blocks.search_vector` column and no `ix_blocks_search_vector`, and the `blocks` row count and every block's `text` are unchanged; fails today because the revision does not exist.
- `::test_document_and_page_writes_work_after_the_drop` (integration): a `document_put`, a block verb and a page create succeed on the upgraded schema.
- `backend/tests/test_notes_schema.py` and `backend/tests/test_pages_schema.py` — change their assertions from "the column and index exist" to "neither exists".
- `backend/tests/test_document_parsers.py::test_pdf_filing_is_a_designed_422` (integration, A48): filing content declared as PDF answers 422 through `UnsupportedSource`, on REST and as the MCP tool's envelope.
- `::test_lock_holds_no_pdf_dependency` (unit, A48): `requirements.lock` and `pyproject.toml` name none of `pdfplumber`, `pdfminer-six`, `pdfminer.six` or `pypdfium2`, and `app/services/document_parsers.py` has no `parse_pdf`; fails today on all.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_drop_blocks_search_vector.py tests/test_document_parsers.py tests/test_notes_schema.py tests/test_pages_schema.py`

- [ ] **Step 3: Implement**

1. B5-6: revision `0006_drop_blocks_search_vector` runs `DROP INDEX IF EXISTS ix_blocks_search_vector` and then `ALTER TABLE blocks DROP COLUMN IF EXISTS search_vector`; the downgrade re-adds the generated column and index with the baseline's definitions (copied, the baseline file itself untouched). Correct the comment in `block-editor.tsx` that mentions the column.
2. B5-11: after `rg` shows no importer, remove `parse_pdf`, its helpers and the PDF branch in `block_pipeline.py`, keeping the 422. Remove `pdfplumber` from `pyproject.toml` and regenerate the lock with exactly `uv pip compile --universal pyproject.toml -o requirements.lock`; `pillow` leaves the lock only if nothing else requires it. Confirm the diff removes only the PDF packages and their exclusive dependencies.
3. `CLAUDE.md`'s Documents paragraph: "PDF parsing exists but…" becomes a sentence saying a PDF is a designed 422 and no parser ships.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_drop_blocks_search_vector.py tests/test_document_parsers.py tests/test_notes_schema.py tests/test_pages_schema.py tests/test_schema_guard.py tests/test_block_pipeline.py tests/test_block_verbs.py tests/test_deployment_artifact.py && (cd ../frontend && npm run typecheck)`

- [ ] **Step 5: Commit**

```bash
git add -A backend frontend/src/features/documents/components/block-editor.tsx CLAUDE.md
git commit -m "refactor(documents): drop search_vector and PDF parser"
```

### Task 49: Code screens: edit repository, blast radius, errors and copy

**Files:**
- Modify: `frontend/src/features/code/schemas.ts`
- Modify: `frontend/src/features/code/components/real-repositories-view.tsx`
- Modify: `frontend/src/features/code/components/real-code-graph-view.tsx`
- Modify: `frontend/src/features/code/components/real-wiki-view.tsx`
- Modify: `frontend/src/features/code/components/code-graph-tab.tsx`
- Modify: `frontend/src/features/settings/components/backups-tab.tsx`
- Modify: `frontend/src/hooks/api/use-code-api.ts`
- Test: `frontend/src/features/code/components/__tests__/edit-repository.test.tsx`
- Test: `frontend/src/features/code/components/__tests__/code-graph-actions.test.tsx`

**Interfaces:**
- Consumes: C3 (`repo_id` on the blast-radius request, the 409 `symbol_ambiguous` answer)
- Produces: none

**Items:** 137, 139, 144, 145
**UI/UX:** UX-7, UI-3
**Depends on:** Task 26
**Evaluation:** files 2 - spec 2 - coupling 1 - risk 1 = 6

- [ ] **Step 1: Write the failing test**

- `edit-repository.test.tsx::saves a repository cloned from a URL` (unit, A3): with a fixture repository whose `local_path` is null, changing the branch and pressing Save sends one `PUT` carrying the new branch and no `path`; the dialog shows the clone location as text, not as an input. Fails today with "Path required" and no request.
- `::reports a failed save` (unit): a 500 from the `PUT` keeps the dialog open and shows the error; no unhandled rejection is raised.
- `code-graph-actions.test.tsx::asks for a symbol on a file-level node` (unit): with the folded graph and a file node selected, pressing Blast Radius sends no request and shows the message "Select a symbol to see its blast radius"; fails today because a file path is sent and the 404 is swallowed.
- `::sends the repository and toasts a failure` (unit): with a symbol selected the request body carries `repo_id`; a 500 shows an error toast; a 409 `symbol_ambiguous` lists the candidates for the operator to pick.
- `::copy mermaid reports failure and works without navigator.clipboard` (unit): with `navigator.clipboard` undefined, pressing Copy Mermaid copies through the library `clipboard` fallback and shows "Copied"; when the copy fails it shows the failure state, never "Copied".
- `::no screen writes the clipboard directly` (unit): a scan of `frontend/src` (through `import.meta.glob` with `?raw`, tests excluded) finds no `navigator.clipboard`.
- `real-wiki-view` case `::reports a failed generate` (unit): a rejected wiki generation shows an error toast.

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/features/code`

- [ ] **Step 3: Implement**

1. F1-1: drop `path` from `editRepoSchema`; render the path with the library's read-only text style.
2. F1-4: guard the action on the node kind, pass `repo_id`, and add `onError` to the mutation. F1-10: await the two `mutateAsync` calls inside their submit handlers and report a rejection.
3. F1-11 and UI-3: replace every direct clipboard write in `frontend/src` with the darkraise-ui `clipboard` component (read its `.d.ts` first). `rg navigator.clipboard frontend/src` lists them: `real-code-graph-view.tsx`, `code-graph-tab.tsx` and Settings' `backups-tab.tsx`.
4. Render the three screens through Storybook or the demo build at 1280x800 and 1920x1080, both themes, with a 64-character repository name and an unbroken URL; record the screenshot paths for Task 70.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/features/code && npm run typecheck`

- [ ] **Step 5: Commit**

```bash
git add frontend/src
git commit -m "fix(code-ui): save cloned repos, report failures"
```

### Task 50: Load-failure pattern and its state board

**Files:**
- Create: `frontend/src/components/app-chrome/load-failure-states.stories.tsx`
- Modify: `frontend/src/features/code/components/real-code-graph-view.tsx`
- Modify: `frontend/src/features/code/components/real-wiki-view.tsx`
- Modify: `frontend/src/components/app-chrome/project-switcher.tsx`
- Modify: `frontend/src/features/settings/components/llm-tab.tsx`
- Modify: `frontend/src/features/settings/use-llm-tab-binding.ts`
- Modify: `frontend/src/features/memory-graph/components/real-memory-graph-page.tsx`
- Test: `frontend/src/components/app-chrome/__tests__/load-failure-states.test.tsx`

**Interfaces:**
- Consumes: none
- Produces: C10 (`load-failure-states.stories.tsx`)

**Items:** 140, 149, 161, 173
**UI/UX:** UI-1
**Depends on:** Task 49
**Evaluation:** files 2 - spec 2 - coupling 1 - risk 1 = 6

- [ ] **Step 1: Write the failing test**

One table-driven test in `load-failure-states.test.tsx`, a row per surface: Code Graph, Wiki, the project switcher, the LLM tab and the graph page.

- `::shows a skeleton while loading` (unit, A41): with the surface's query pending, the library `skeleton` is rendered and no "No … yet" copy; fails today on Code Graph and Wiki, which show "No repositories indexed yet".
- `::shows Retry after a failed load` (unit, A41): with the query rejected, the library `empty-state` is rendered with the surface's failure title and a button named "Retry"; pressing it refetches once. Fails today on Code Graph, Wiki and the project switcher ("No project holds anything yet").
- `::shows the empty copy only after a successful empty load` (unit): with the query resolved to an empty list, the "No … yet" copy is rendered and no Retry.
- `::the LLM tab invents no values` (unit): with the purposes query rejected, the LLM tab renders no model name, no `qwen2.5:3b` and no purpose rows, only the failure state; fails today because it shows blank models and a fixture judge.

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/components/app-chrome src/features/code src/features/settings`

- [ ] **Step 3: Implement**

1. On each of the five surfaces branch on the query's `isPending`, `isError` and data in that order, using the library `skeleton` and `empty-state` directly (no local wrapper component); the Retry button calls the query's `refetch`.
2. F2-6: the LLM tab's binding returns an explicit `error` state instead of fixture values.
3. C10: the story file exports one story per surface and state (loading, failed, empty, populated) from the real components with mocked queries, following `constellation-board.stories.tsx`.
4. Screenshot every story at both viewports and themes for Task 70.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/components/app-chrome src/features/code src/features/settings src/features/memory-graph && npm run typecheck`

- [ ] **Step 5: Commit**

```bash
git add frontend/src
git commit -m "fix(ui): show failed loads with a retry"
```

### Task 51: Code canvas search dimming and re-centre

**Files:**
- Modify: `frontend/src/features/code/components/code-glow-canvas.tsx`
- Modify: `frontend/src/features/code/components/real-code-graph-view.tsx`
- Test: `frontend/src/features/code/components/__tests__/code-glow-canvas.test.tsx`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 141, 220, 221
**UI/UX:** UX-7
**Depends on:** Task 50
**Evaluation:** files 1 - spec 2 - coupling 0 - risk 1 = 4

- [ ] **Step 1: Write the failing test**

All in `code-glow-canvas.test.tsx`, with Sigma and the layout worker replaced by spies as the existing canvas tests do.

- `::typing in the search dims without rebuilding` (unit): five successive search strings create zero new Sigma instances and zero new layout workers, and the nodes that do not match carry the dimmed style while the camera state is unchanged; fails today with a new Sigma and worker per keystroke.
- `::a rebuild re-centres a persisting selection` (unit, register row 220): when the drawn node set changes while a node stays selected, the camera's animate call targets that node's position; fails today because the camera opens at Sigma's default.
- `::ring overlay follows the selected node` (unit, row 221): the ring overlay's position equals the selected node's display position after a camera update.
- `::camera follows during the core run` (unit, row 221): while the core layout runs with follow on, each layout frame issues one camera update toward the core's centroid, and none after the run stops.

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/features/code/components/__tests__/code-glow-canvas.test.tsx`

- [ ] **Step 3: Implement**

1. F1-6: keep `graph` stable across a search and pass the matching ids as `visibleIds`; the canvas dims through its node reducer and refreshes without restarting the layout or moving the camera.
2. Row 220: after a rebuild whose node set changed, re-centre on the persisting selection.
3. Rows 221: the tests above pin behaviour that exists; where one fails, fix the canvas, not the test.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/features/code && npm run typecheck`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/code
git commit -m "perf(code-ui): dim on search without a rebuild"
```

### Task 52: Graph payload preview and cluster names

**Files:**
- Modify: `backend/app/services/graph.py`
- Modify: `backend/app/schemas/graph.py`
- Modify: `backend/app/utils/cluster_names.py`
- Modify: `backend/tests/test_graph_scale.py`
- Test: `backend/tests/unit/test_cluster_names.py`
- Test: `backend/tests/test_graph_payload_preview.py`

**Interfaces:**
- Consumes: none
- Produces: C9

**Items:** 153, 224, 225, 226, 227
**Depends on:** none
**Evaluation:** files 1 - spec 2 - coupling 2 - risk 1 = 6

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_graph_payload_preview.py::test_memory_nodes_carry_a_preview` (integration): for a memory of 1,000 characters, its node in `GET /api/v1/graph/unified` has `content` of exactly 280 characters and `content_truncated: true`; a 100-character memory has its whole content and `false`. Fails today because the full content is served.
- `backend/tests/unit/test_cluster_names.py::test_two_clusters_never_share_a_name` (unit, row 224): two clusters whose computed names are both `gpu` are named `gpu` and `gpu 2`, the smaller cluster id keeping the bare name; three get `gpu`, `gpu 2`, `gpu 3`; a suffix that would pass `MAX_NAME_CHARS` still appears. Fails today with two identical names.
- `::test_term_inside_the_prefix_is_skipped` (unit, row 225): with prefix `darkraise-ai-plugins` and candidate terms `plugins` and `routing`, the name is `darkraise-ai-plugins · routing`; fails today with `… · plugins`.
- Measurement (row 226), no test: time `entity_terms_for_memories` for an `all_memories` view on production data under the read-only exception of Global Constraints' Host limits (the statement is one `SELECT`, the same one the live graph page already runs), with `docker exec darkmem-prod-postgres-1 psql -U darkmem -d darkmem -c "EXPLAIN (ANALYZE, BUFFERS) <the statement with the view's memory ids>"`; write the execution time and the memory count into the Note of row 226 and of row 4 of `docs/dforge/registers/2026-11-20-graph-cluster-quality.md`.
- Comment (row 227), no test: replace the stale "Louvain" wording in the kept comment of `tests/test_graph_scale.py`.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/unit/test_cluster_names.py tests/test_graph_payload_preview.py`

- [ ] **Step 3: Implement**

1. C9: cut node `content` in the service with a module constant `NODE_PREVIEW_CHARS = 280` and add the boolean to the node schema.
2. Row 224: after naming, suffix duplicates in cluster-id order. Row 225: skip a candidate term whose spelling key is contained in the prefix's key.
3. Record the measurement as Step 1 says.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/unit/test_cluster_names.py tests/test_graph_payload_preview.py tests/test_graph_scale.py tests/test_graph_cluster_quality_acceptance.py tests/test_sdk_generator.py`

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests docs/dforge/registers sdks
git commit -m "fix(graph): unique cluster names, preview content"
```

### Task 53: Memory graph interactions

**Files:**
- Modify: `frontend/src/features/memory-graph/components/real-memory-graph-page.tsx`
- Modify: `frontend/src/features/graph/lib/graph-utils.ts`
- Modify: `frontend/src/features/graph/components/graph-3d-renderer.tsx`
- Modify: `frontend/src/features/graph/components/graph-2d-renderer.tsx`
- Modify: `frontend/src/features/graph/components/graph-detail-panel.tsx`
- Test: `frontend/src/features/memory-graph/components/__tests__/real-memory-graph-page.test.tsx`
- Test: `frontend/src/features/graph/components/__tests__/graph-interactions.test.tsx`

**Interfaces:**
- Consumes: C9
- Produces: none

**Items:** 138, 146, 147, 148, 153, 219, 223
**UI/UX:** UX-8, UI-5
**Depends on:** Task 52
**Evaluation:** files 2 - spec 2 - coupling 1 - risk 1 = 6

- [ ] **Step 1: Write the failing test**

- `real-memory-graph-page.test.tsx::builds no 3D data in the 2D view` (unit, A4): with the view mode 2D and the 3D data builder of `graph-utils.ts` wrapped by a spy, three filter changes call it zero times; switching to 3D calls it once. Fails today because the memo is not gated on the view mode.
- `graph-utils` case `::3D build is linear in nodes` (unit): building for 5,000 clustered nodes calls no `Array.prototype.find` on the node list (the list is wrapped to count) and emits no link between two members of one cluster.
- `graph-interactions.test.tsx::clicking an entity in 3D shows that entity` (unit): a 3D click on an entity node leaves the detail panel showing that entity's name; fails today because the click handler clears the selected entity.
- `::colour mode recolours in place` (unit): changing colour mode creates no new 2D WebGL renderer and calls no 3D layout re-seed; node colours change.
- `::turning Regions off clears outlines and chips in the same frame` (unit, row 223): after toggling Regions off and flushing one animation frame, the hull canvas is cleared and no region chip is in the document; fails today until a later repaint.
- `::the deferred runner start is one frame late` (unit, row 219): the memory renderer calls `runner.start()` zero times before the first animation frame and once after it.
- `::the close button is named` (unit): the detail panel's close button has the accessible name "Close details".
- `::the detail panel loads the full text of a truncated node` (unit): opening a node with `content_truncated: true` requests `GET /api/v1/memories/{id}` once and shows the full text; a node with `false` requests nothing; in demo mode nothing is requested.

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/features/memory-graph src/features/graph`

- [ ] **Step 3: Implement**

1. F1-2: gate the 3D memo on the 3D view mode, look nodes up in a `Map`, and replace per-pair hidden links with one anchor per cluster.
2. F1-12: route an entity click to the entity selection. F1-13: remove colour mode from the rebuild dependencies of both renderers; the in-place recolour effects stay.
3. Row 223: clear the hull canvas and chips synchronously when Regions turns off. F1-14: `aria-label="Close details"`.
4. C9: the detail panel reads the full memory when the node is truncated; the page's text filter runs over the preview and tags.
5. Walk the graph page by keyboard and at both viewports and themes with the 20,000-node synthetic graph; record the screenshot paths for Task 70.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/features/memory-graph src/features/graph && npm run typecheck`

- [ ] **Step 5: Commit**

```bash
git add frontend/src
git commit -m "fix(graph-ui): no 3D work in 2D, entity clicks"
```

### Task 54: Graph render cost and dead exports

**Files:**
- Modify: `frontend/src/features/graph/lib/node-glow-program.ts`
- Modify: `frontend/src/features/graph/lib/graph-geometry.ts`
- Modify: `frontend/src/features/graph/lib/graph-scale.ts`
- Modify: `frontend/src/features/graph/lib/code-graph-theme.ts`
- Modify: `frontend/src/features/graph/lib/memory-graph-theme.ts`
- Modify: `frontend/src/features/graph/lib/cluster-runner.ts`
- Modify: `frontend/src/features/graph/lib/constellation-runner.ts`
- Modify: `frontend/src/features/code/components/code-explorer.tsx`
- Modify: `frontend/src/features/code/components/code-filters.tsx`
- Modify: `frontend/src/features/code/components/code-glow-canvas.tsx`
- Test: `frontend/src/features/graph/lib/__tests__/render-cost.test.ts`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 142, 143, 150, 151, 152, 154, 155, 222
**UI/UX:** OP-4 — no visible change; cost and dead code only
**Depends on:** Task 51, Task 53
**Evaluation:** files 3 - spec 2 - coupling 0 - risk 1 = 6

- [ ] **Step 1: Write the failing test**

All in `render-cost.test.ts`.

- `::the density grid is cached per layout version` (unit): ten `beforeRender` calls with an unchanged layout version and cell size build the grid once, and its keys are numbers; a changed layout version rebuilds it once. Fails today with a rebuild and string keys per frame.
- `::one theme observer serves every consumer` (unit): mounting `useMemoryGraphTheme` six times creates one `MutationObserver`; unmounting all six disconnects it.
- `::remembered positions are pruned to the drawn nodes` (unit): after a rebuild that drops 900 of 1,000 nodes, each renderer's remembered-position map holds 100 entries.
- `::symbolsByFile groups in linear time` (unit): grouping 5,000 symbols of one file performs no array spread per insert (the result equals the reference grouping, and the build of 50,000 symbols finishes within 200 ms).
- `::KIND_CHART has one definition` (unit): a scan of `frontend/src` finds one declaration of `KIND_CHART`.
- `::runners share their scheduling code` (unit): `cluster-runner.ts` and `constellation-runner.ts` import their worker, animation-frame and timer handling from one module, and `arrange` allocates no `Map` per frame (allocation spy over 50 frames).
- Removals with no new test (after an import search over `frontend/src`, stories and tests included): the dead exports F1-9 lists (the hull helpers and vis-network type in `graph-geometry.ts`, `lightenHex`, `clusterAnchors` and `seedAroundAnchor` unless Task 53 adopted them, the code-colour functions and `useCodeGraphTheme`, `groupMemories`, `placeIslands`, `zoomLevel`, `visibleLabelIds`, the unread `setGraphReady` state, the inner `GraphSkeleton`, the duplicate `stableHash`) with tests that exist only for them. Row 222: remove the `placeOuter` iteration of the 20,000-node timing loop that another test already covers.

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/features/graph/lib`

- [ ] **Step 3: Implement**

1. F1-7: cache `localSpacing`'s grid by `(cell size, layout version)` with numeric keys. F1-20: one module-level observer with reference counting. F1-21: prune `positionsRef` on rebuild. F1-18: push into per-file arrays.
2. F1-16: one `KIND_CHART`, and one function for the importance-to-weight mapping that both renderers call; each renderer keeps its own unit conversion, so node sizes on screen do not change.
3. F1-17: extract the shared runner scheduling into one module, reuse buffers in `arrange`, and make `collide()` use a grid over islands.
4. The removals listed in Step 1. Compare the graph and code pages against Task 53's screenshots: no pixel-visible change is expected.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/features/graph src/features/code src/features/memory-graph && npm run typecheck && npm run build`

- [ ] **Step 5: Commit**

```bash
git add -A frontend/src
git commit -m "perf(graph-ui): cache per-frame work, drop dead code"
```

### Task 55: Settings save model and its state board

**Files:**
- Create: `frontend/src/features/settings/components/settings-save-states.stories.tsx`
- Modify: `frontend/src/features/settings/components/flags-tab.tsx`
- Modify: `frontend/src/features/settings/use-flags-tab-binding.ts`
- Modify: `frontend/src/features/settings/components/purpose-dialog.tsx`
- Modify: `frontend/src/features/settings/components/distribution-tab.tsx`
- Modify: `frontend/src/features/settings/components/research-tab.tsx`
- Modify: `frontend/src/features/settings/components/notifications-tab.tsx`
- Test: `frontend/src/features/settings/components/__tests__/settings-save.test.tsx`

**Interfaces:**
- Consumes: none
- Produces: C10 (`settings-save-states.stories.tsx`)

**Items:** 160, 162, 163, 167
**UI/UX:** UX-1
**Depends on:** Task 45
**Evaluation:** files 2 - spec 2 - coupling 1 - risk 1 = 6

- [ ] **Step 1: Write the failing test**

All in `settings-save.test.tsx`; the dialog cases run as a table over every Flags dialog and the LLM purpose dialog.

- `::a refused save keeps the dialog open with the edits and the reason` (unit, A37): with the save answering 422 and `error.message = "below the floor"`, after pressing Save the dialog is still open, every edited field holds its edited value, and the text "below the floor" is shown inside the dialog; fails today because the Flags dialogs close on Save.
- `::a successful save closes with Saved` (unit, A37): the dialog stays open with Save in its pending state while the request runs, then closes and one "Saved" toast appears.
- `::typing in a number field enables Save without a blur` (unit): typing `5` into a number field of a pristine dialog enables Save before any blur; fails today because the field commits on blur.
- `::an out-of-range number shows an error` (unit): for both number field kinds, a value above the field's maximum shows the range error under the field and disables Save; neither kind clamps silently.
- `::a toggle that saves at once reverts on failure` (unit): for the Distribution and Research toggles, a failed save returns the switch to its old position and shows an error toast.
- `::Escape closes a dialog whose list popover is closed` (unit, F2-12): with `keepDialogOpenOnListEscape` removed, Escape with an open select closes only the select, and a second Escape closes the dialog.
- `::settings tabs share one failure style` (unit): the Notifications, Research and Flags tabs show a rejected load with the library `empty-state` and Retry.

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/features/settings`

- [ ] **Step 3: Implement**

1. F2-5 and F2-7: one dialog save path for Settings, in the tab bindings: await the mutation, keep the dialog open while it runs, close and toast on success, render the server's `error.message` in the dialog's footer on refusal. Inline forms and immediate toggles keep their shape and gain the revert.
2. F2-8: number fields use the library `number-input` with change-time commits and its own range error.
3. F2-12 remainder: remove `keepDialogOpenOnListEscape` and its seven call sites if the library dialog now handles the nested Escape; if the test shows it does not, keep it and close that part of row 167 with the evidence.
4. C10: the story file shows, for one Flags dialog and the purpose dialog: pristine, edited, saving, refused with reason, out-of-range, and the toggle's reverted state.
5. Walk each dialog by keyboard alone (Tab order, Enter saves, Escape closes, focus returns to the trigger) and screenshot every story at both viewports and themes for Task 70.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/features/settings && npm run typecheck`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/settings
git commit -m "fix(settings): dialogs wait for their save"
```

### Task 56: Session expiry and rotation on the server

**Files:**
- Modify: `backend/app/api/routes/auth.py`
- Modify: `backend/app/api/auth.py`
- Modify: `backend/app/api/websocket.py`
- Modify: `backend/scripts/e2e/run_e2e.py`
- Modify: `CLAUDE.md`
- Test: `backend/tests/test_auth_token_rotation.py`
- Test: `backend/tests/test_e2e_runner_args.py`
- Test: `backend/tests/test_websocket.py`
- Test: `backend/scripts/e2e/tests/test_session_rotation.py`

**Interfaces:**
- Consumes: none
- Produces: C5

**Items:** 164
**Depends on:** Task 42
**Evaluation:** files 1 - spec 2 - coupling 2 - risk 3 = 8
**Lenses:** security

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_auth_token_rotation.py::test_me_and_refresh_carry_expires_at` (integration): `GET /api/v1/auth/me` and the answer of `POST /api/v1/auth/refresh` carry `expires_at` equal to the token's `exp` as ISO 8601 UTC; fails today because neither does.
- `backend/tests/test_websocket.py::test_refresh_closes_the_presented_tokens_socket_with_4001_first` (integration): with a socket open on token T, `POST /api/v1/auth/refresh` with T closes that socket with code 4001 and reason `Session renewed`, and the close frame is sent before the blocklist row for T is committed (the commit is patched to wait on an event; the close arrives while it waits). Fails today because the socket is closed later as revoked.
- `::test_password_change_closes_own_socket_4001_and_others_as_revoked` (integration): a change-password with T closes T's socket with 4001 and a socket of another session with `Session expired or revoked`.
- `::test_read_only_refresh_also_closes_with_4001` (integration): under `DARKMEM_READ_ONLY`, where refresh reissues without blocklisting, T's socket still closes with 4001.
- `::test_a_new_socket_with_the_new_cookie_connects` (integration): after the refresh, a handshake with the new token succeeds and one with T is refused.
- `backend/scripts/e2e/tests/test_session_rotation.py::test_renewal_and_password_change_over_a_real_socket` (e2e, A38): against the disposable e2e stack, open a real WebSocket, call refresh, observe the 4001 close and reconnect with the new cookie; then change the password and observe the same; the reconnected socket receives a broadcast.
- `backend/tests/test_e2e_runner_args.py::test_extra_arguments_reach_pytest` (unit): with the model probe, `stack.boot` and `subprocess.run` patched, `run_e2e.main()` under `sys.argv = ["run_e2e.py", "-k", "session_rotation"]` calls pytest with `-k session_rotation` after its fixed arguments, and with no extra argument the command is today's; fails today because the runner reads no arguments.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_auth_token_rotation.py tests/test_websocket.py tests/test_e2e_runner_args.py`

- [ ] **Step 3: Implement**

1. Per C5: add `expires_at` to both answers.
2. The websocket module keeps a registry of open sockets by token id. Refresh and change-password, after validating the presented token and before committing the blocklist write, close that token's sockets with 4001 `Session renewed`; the commit follows. A failure after the close is safe: the client reconnects only after it holds a new cookie. Change-password then lets the epoch check close every other session's sockets as today.
3. The one-second revalidation, its cache (Task 42) and the existing close reason are unchanged.
4. `CLAUDE.md`'s auth paragraph gains one sentence: a rotation closes the presented token's sockets with 4001 before the blocklist commit.
5. `run_e2e.py` appends `sys.argv[1:]` to its pytest command, as `run_playwright_e2e.py` does for Playwright. Run the e2e test through it (it boots its own disposable stack); never against `:8000`. The runner exits 2 with a `BLOCKED:` line when the LAN endpoint does not serve the seeded extraction model: that is a missing toolchain, not a red test. On exit 2, keep the e2e test, quote the `BLOCKED:` line in the ledger and in the commit body, and go on; the integration tests above gate this task, and Task 70's walkthrough shows the renewal over a real socket.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_auth_token_rotation.py tests/test_websocket.py tests/test_read_only_doors.py tests/test_sdk_generator.py tests/test_e2e_runner_args.py`
Expected: PASS.

Then run: `timeout 1500 .venv/bin/python scripts/e2e/run_e2e.py -k session_rotation`
Expected: exit 0, or exit 2 with a `BLOCKED:` line handled as Step 3.5 says.

- [ ] **Step 5: Commit**

```bash
git add backend CLAUDE.md sdks
git commit -m "feat(auth): tell sockets when a session is renewed"
```

### Task 57: Session renewal in the app

**Files:**
- Create: `frontend/src/lib/session-renewal.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/websocket.ts`
- Modify: `frontend/src/routes/_authenticated.tsx`
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/features/settings/use-change-password.ts`
- Test: `frontend/src/lib/__tests__/session-renewal.test.ts`
- Test: `frontend/src/features/settings/__tests__/change-password-renewal.test.tsx`
- Test: `frontend/src/lib/__tests__/websocket-session.test.ts`

**Interfaces:**
- Consumes: C5
- Produces: none

**Items:** 158, 164, 172
**UI/UX:** UX-2
**Depends on:** Task 56
**Evaluation:** files 2 - spec 2 - coupling 1 - risk 2 = 7

- [ ] **Step 1: Write the failing test**

With fake timers and a mocked `fetch`, `localStorage`, `WebSocket` and router.

- `session-renewal.test.ts::renews a session with under an hour to spare` (unit, A38): with `expires_at` 59 minutes ahead, the minute check calls `POST /api/v1/auth/refresh` once, stores the new `expires_at`, and writes the renewal time to `localStorage` only after the response has arrived; with 61 minutes ahead it calls nothing. A `visibilitychange` to visible runs the same check at once. Fails today because the app never calls refresh.
- `::a second tab adopts the renewal` (unit, A38): a `storage` event carrying a newer renewal time makes the second tab re-read `/auth/me` and skip its own refresh.
- `::a refused renewal ends the session once` (unit): a 401 from refresh navigates to sign-in through the router (no `window.location` assignment) exactly once, with no retry.
- `::a tab that slept past expiry goes to sign-in by client navigation` (unit): with `expires_at` in the past at `visibilitychange`, the router navigates to sign-in and the notes draft registry module is still populated.
- `::a 401 within ten seconds of a renewal is retried once` (unit): an API call answering 401 at 3 s after a recorded renewal is retried once and succeeds; at 11 s it ends the session.
- `websocket-session.test.ts::reconnects after 4001 only once the renewal is recorded` (unit, A38): a close with code 4001 opens no new socket until the renewal record appears (own response or `storage` event), then opens one; with no record within 10 s the app goes to sign-in.
- `::an expired close with no recent renewal ends the session with no retry` (unit, A38): a close with reason `Session expired or revoked` and no renewal in the last 10 s navigates to sign-in and schedules no reconnect; fails today because the socket retries every 30 s forever. The same close 3 s after a renewal reconnects once.
- `::a refused handshake after a renewal is retried once` (unit): a handshake closed as "Unauthorized" within 10 s of a renewal is retried once.
- `frontend/src/features/settings/__tests__/change-password-renewal.test.tsx::a password change keeps its own tab signed in and connected` (unit, A38): when `useChangePassword`'s mutation resolves, `darkmem.session.renewed_at` is written (after the response, never before) and `/auth/me` is re-read for the new `expires_at`; a 4001 close arriving either before or after that response opens exactly one new socket once the record exists, and the router never navigates to sign-in. Fails today because a password change records nothing and the socket's close ends in the retry loop.
- `websocket-session.test.ts::StrictMode leaves one socket` (unit, F2-17): mounting the provider twice in `StrictMode` leaves exactly one open socket, and one event produces one toast.

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/lib src/features/settings/__tests__/change-password-renewal.test.tsx`

- [ ] **Step 3: Implement**

1. `session-renewal.ts` owns: the `expires_at` state from `/auth/me` and refresh, the minute timer and `visibilitychange` check, the refresh call, the `localStorage` renewal record (key `darkmem.session.renewed_at`, wrapped in try/catch) and its `storage` listener, and the 10-second window predicate the API client and the socket both ask. It is disabled in demo mode.
2. `api.ts`: replace the hard reload on 401 with one retry inside the window, else a router navigation to sign-in. `websocket.ts`: handle 4001, the expired reason and the refused handshake as the tests state; make connect idempotent so `StrictMode` cannot leave two sockets.
3. Start the module from the authenticated layout; stop it on sign-out. `use-change-password.ts` calls the module's renewal recorder on a successful change (the same function the refresh path calls) and re-reads `/auth/me`.
4. Prove in the running app for Task 70: shorten the session lifetime in the disposable e2e stack, keep a note draft and a document block edit open across a renewal, and record that the note draft survives while an unsent block edit is lost only on the slept-past-expiry path.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/lib src/features/notes src/features/settings && npm run typecheck`

- [ ] **Step 5: Commit**

```bash
git add frontend/src
git commit -m "feat(session): renew before expiry, keep drafts"
```

### Task 58: Shell lists, setup status and demo isolation

**Files:**
- Modify: `frontend/src/features/settings/use-maintenance-tab-binding.ts`
- Modify: `frontend/src/features/settings/use-llm-tab-binding.ts`
- Modify: `frontend/src/features/settings/components/research-tab.tsx`
- Modify: `frontend/src/features/setup/setupWizardStore.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/format.ts`
- Modify: `frontend/src/features/usage/format.ts`
- Modify: `frontend/src/routes/_guest/setup.tsx`
- Modify: `frontend/src/hooks/api/use-llm-providers-api.ts`
- Modify: `frontend/src/hooks/api/use-jobs-api.ts`
- Test: `frontend/src/lib/__tests__/format.test.ts`
- Test: `frontend/src/features/settings/__tests__/shell-lists.test.tsx`
- Test: `frontend/src/features/setup/__tests__/setup-status.test.tsx`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 157, 159, 168, 169, 170, 171, 173
**UI/UX:** UX-9, UX-10, UX-11
**Depends on:** Task 55, Task 57
**Evaluation:** files 3 - spec 2 - coupling 0 - risk 1 = 6

- [ ] **Step 1: Write the failing test**

- `format.test.ts::formatDuration rounds across the minute` (unit): `formatDuration(119.6)` is `"2m 0s"`, `formatDuration(59.6)` is `"1m 0s"`, `formatDuration(59.4)` is `"59s"`; fails today with `"1m 60s"`.
- `::one formatDateTime and one formatDuration` (unit): a scan of `frontend/src` finds one declaration of each.
- `shell-lists.test.tsx::the re-embed count follows an embedder change` (unit): after the WebSocket event that follows an embedder change, the Maintenance tab's re-embed count shows the refreshed value; fails today because the tab keeps a private query key.
- `::the maintenance tab does not poll jobs` (unit): over 30 s of fake time the tab issues at most one `/jobs` request.
- `::typed research budgets survive a settings reload` (unit): typing `7` into a budget field and then delivering a refetch of the research settings leaves `7` in the field; fails today because the reload overwrites it.
- `::demo mode sends no request from the LLM tab` (unit, A43): with `VITE_DEMO` on, mounting Settings → LLM and opening the purpose dialog calls `fetch` zero times; fails today on providers, the model probe and system prompts.
- `::queries pass a cancellation signal` (unit): unmounting a component while its list query is in flight aborts the request (`signal.aborted` is true), for the shared `apiFetch` path.
- `setup-status.test.tsx::a server error shows an error with Retry, not the wizard` (unit): `GET` setup status answering 500 renders the failure state with Retry and no wizard step; a 200 `initialized: false` renders the wizard. Fails today because the status code is ignored.
- `::vendor API keys never reach localStorage` (unit, A43): after typing an API key into the wizard's provider step and advancing two steps, no `localStorage` or `sessionStorage` value contains the key, and the key is still present in the in-memory store for the finalize call.

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/lib src/features/settings src/features/setup`

- [ ] **Step 3: Implement**

1. F2-13: keep `formatDateTime` and `formatDuration` in `lib/format.ts`, round total seconds before splitting, and import them everywhere else.
2. F2-2: the Maintenance binding uses the shared hooks and query keys. F2-18: `apiFetch` accepts and forwards `signal`, list hooks pass the query's signal, and the tab reads the one job value from the shared jobs query without its own 5 s poll.
3. F2-16: seed the Research form once and on explicit reset, not on every refetch.
4. F2-4: `enabled: !DEMO` (or the demo twin) on the providers, model-probe and system-prompts hooks.
5. F2-14: `checkSetupStatus` throws on a non-2xx status and the setup route renders the library `empty-state` with Retry. F2-15: exclude the API key fields from the wizard store's persistence.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/lib src/features/settings src/features/setup src/features/usage && npm run typecheck`

- [ ] **Step 5: Commit**

```bash
git add frontend/src
git commit -m "fix(shell): honest setup status and demo isolation"
```

### Task 59: Unused frontend hooks and auth code

**Files:**
- Modify: `frontend/src/hooks/api/index.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/websocket.ts`
- Modify: `frontend/src/features/knowledge/use-review-queue.ts`
- Modify: `frontend/src/hooks/api/use-blocks-api.ts`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 165, 166, 181
**UI/UX:** OP-4 — removes unused code only; no screen changes
**Depends on:** Task 57, Task 58
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 1 = 5

- [ ] **Step 1: No new test, because every removal is of an export with no production importer, and `npm run typecheck`, `npm test` and `npm run build` fail if a removed name is still imported anywhere**

- [ ] **Step 2: Prove each removal**

For every candidate, run `rg -n "<name>" frontend/src frontend/tests` and keep the output for the commit body. Candidates: the exported hooks under `hooks/api` with no production importer (F2-10 names `useReprocessStream`, `useHealth` unless Task 12 uses it, the re-embed hooks and the graph hooks; find the rest with a script that lists every export of `hooks/api/*.ts` and counts its importers outside `__tests__`); the WebSocket cache writes and refreshes that no query reads; `useSession`, `useLogout`, `LogoutButton`, `authAdapter.me` and `lib/api.ts`'s `login()` (F2-11); `useBlockMove`, and `rank_note` and `consequence` in `use-review-queue.ts` (F3-9a).
Expected: each listed name has no importer outside its own module and tests; a name that has one is kept and recorded.

- [ ] **Step 3: Implement**

1. Delete each proven-unused export with the tests that exist only for it. A hook Task 57 or Task 58 started using is kept.
2. Do not delete demo fixtures that a demo view reads.

- [ ] **Step 4: Run the checks**

Run: `npm run typecheck && npm test && npm run build`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A frontend/src
git commit -m "refactor(frontend): remove unimported hooks"
```

### Task 60: Chat streams per conversation

**Files:**
- Modify: `frontend/src/features/chat/hooks/use-chat-stream.ts`
- Modify: `frontend/src/features/chat/components/real-chat-page.tsx`
- Modify: `frontend/src/features/chat/components/chat-messages.tsx`
- Modify: `frontend/src/features/chat/components/chat-sidebar.tsx`
- Modify: `frontend/src/hooks/api/use-chat-api.ts`
- Test: `frontend/src/features/chat/hooks/__tests__/use-chat-stream.test.tsx`
- Test: `frontend/src/features/chat/components/__tests__/chat-page.test.tsx`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 174, 177, 184, 185
**UI/UX:** UX-3
**Depends on:** Task 57
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 2 = 6

- [ ] **Step 1: Write the failing test**

- `use-chat-stream.test.tsx::a send in a second conversation leaves the first stream running` (unit, A2): start a stream in conversation A, then send in B; A's `AbortController` is not aborted, A's stream runs to its end, and A's final answer is in A's message list when A is selected again. Fails today because one shared controller is aborted on every send.
- `::each conversation has its own stream state` (unit): while both stream, selecting A shows A's partial text and selecting B shows B's; stopping B leaves A streaming.
- `::a turn that never completes leaves its conversation listed` (unit): when a first turn's stream errors before completion, the conversation list is refetched and the new conversation appears in the sidebar; fails today because the client never learns of it.
- `chat-page.test.tsx::a failed delete says so and keeps the conversation` (unit): a 500 from the delete shows an error toast and the conversation stays listed and selected.
- `::a streaming token re-renders only the streaming message` (unit): with 20 finished messages rendered through a markdown component wrapped by a render counter, delivering 30 tokens re-renders the finished messages zero times; fails today because every token re-parses every message.

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/features/chat`

- [ ] **Step 3: Implement**

1. F3-1: keep stream state and the abort controller in a module-level map keyed by conversation id (a new conversation uses a temporary key until the server names it); the hook subscribes to its conversation's entry. Client only; the server contract is unchanged.
2. F3-9d: invalidate the conversation list when a stream ends, errors or is stopped. F3-9e: `onError` on the delete mutation.
3. F3-5: memoise each finished message's rendered markdown on `(id, content)`; only the streaming message re-renders.
4. Keep the retryable-draft rule `CLAUDE.md` states: a definite rejection exposes the draft, an uncertain delivery warns against a duplicate.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/features/chat && npm run typecheck`

- [ ] **Step 5: Commit**

```bash
git add frontend/src
git commit -m "fix(chat): one stream per conversation"
```

### Task 61: Document block editor refusals

**Files:**
- Create: `frontend/src/lib/hash-precondition.ts`
- Modify: `frontend/src/features/documents/components/block-editor.tsx`
- Modify: `frontend/src/features/documents/lib/mutation-queue.ts`
- Modify: `frontend/src/features/notes/lib/page-sync.ts`
- Test: `frontend/src/features/documents/lib/__tests__/mutation-queue.test.ts`
- Test: `frontend/src/features/documents/components/__tests__/block-editor.test.tsx`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 175, 179, 183
**UI/UX:** UX-4
**Depends on:** Task 57
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 2 = 6

- [ ] **Step 1: Write the failing test**

- `block-editor.test.tsx::a refused write keeps the edit box and the typed text` (unit, A39): typing new text into a block and saving, with the server answering 409 `hash_conflict` (and second cases for 422 and a network failure), leaves the edit box open containing the typed text and shows the reason beside it; fails today because the box closes and the text is lost.
- `mutation-queue.test.ts::no queued write follows a refusal` (unit, A39): with three writes queued and the first refused, the second and third are not sent; fails today because the queue re-reads the hash and sends the next.
- `::the queue resumes when the operator acts` (unit): after the operator chooses Retry (re-read the hash, resend the refused write) or Discard, the remaining writes are sent in order with each one's `expected_hash` taken from the previous answer.
- `::both editors use one hash-precondition helper` (unit): `mutation-queue.ts` and `page-sync.ts` import `nextExpectedHash` and `isHashConflict` from `lib/hash-precondition.ts` and declare neither locally.

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/features/documents src/features/notes`

- [ ] **Step 3: Implement**

1. F3-2: the edit box closes only on a confirmed write; on refusal or failure it stays with the text and an inline reason (the server's `error.message`, or "Could not save" for a network failure) plus Retry and Discard.
2. F3-7: a refusal pauses the queue; nothing is sent until the operator acts.
3. F3-9c: move the shared hash plumbing to `lib/hash-precondition.ts`. The notes save engine keeps its own conflict handling (retained read-only drafts); only the helper is shared.
4. Walk the editor by keyboard for Task 70: Escape with unsaved text asks before discarding.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/features/documents src/features/notes && npm run typecheck`

- [ ] **Step 5: Commit**

```bash
git add frontend/src
git commit -m "fix(documents-ui): keep text when a write is refused"
```

### Task 62: Fact list facets

**Files:**
- Modify: `backend/app/api/routes/facts.py`
- Modify: `backend/app/schemas/facts.py`
- Modify: `backend/app/services/facts_read.py`
- Test: `backend/tests/test_fact_facets.py`

**Interfaces:**
- Consumes: none
- Produces: C13

**Items:** 188
**Depends on:** Task 20
**Evaluation:** files 1 - spec 2 - coupling 2 - risk 1 = 6

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_fact_facets.py::test_facets_cover_facts_beyond_the_page` (integration): with 60 facts seeded, of which only the 55th has verification status `disputed`, `GET /api/v1/knowledge/facts?limit=20` returns 20 rows and a `facets` object whose status list contains `disputed`; fails today because the answer has no `facets`.
- `::test_facets_follow_the_project_scope_only` (integration): facets list values from the requested project and none from another, and do not shrink when a status filter is applied.
- `::test_facets_cost_one_statement` (integration): the facets add at most one statement to the list request.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_fact_facets.py`

- [ ] **Step 3: Implement**

1. Read `use-facts.ts` to list the fields its options come from, then compute their distinct values in one aggregate statement in `facts_read.py` and add `facets` to the schema.
2. `facts_read.py` stays free of `verification_ladder` and `contradiction_veto` imports (invariant 15's scan).
3. Run `make generate` in `sdks/` and the guards leg.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_fact_facets.py tests/test_auto_research.py tests/test_api/test_rest_conformance.py tests/test_sdk_generator.py`

- [ ] **Step 5: Commit**

```bash
git add backend sdks
git commit -m "feat(facts): serve filter facets with the list"
```

### Task 63: Knowledge queues: selection, paging and filter options

**Files:**
- Modify: `frontend/src/features/knowledge/components/hygiene-queue.tsx`
- Modify: `frontend/src/features/knowledge/components/review-queue.tsx`
- Modify: `frontend/src/features/knowledge/components/list-surface.tsx`
- Modify: `frontend/src/features/knowledge/components/facts-tab.tsx`
- Modify: `frontend/src/features/knowledge/use-facts.ts`
- Test: `frontend/src/features/knowledge/components/__tests__/hygiene-queue.test.tsx`
- Test: `frontend/src/features/knowledge/components/__tests__/queue-paging.test.tsx`
- Test: `frontend/src/features/knowledge/__tests__/use-facts-facets.test.ts`

**Interfaces:**
- Consumes: C13
- Produces: none

**Items:** 176, 182, 188
**UI/UX:** UX-5, UI-2, UX-9
**Depends on:** Task 62
**Evaluation:** files 2 - spec 2 - coupling 1 - risk 2 = 7

- [ ] **Step 1: Write the failing test**

- `hygiene-queue.test.tsx::a project change clears the selection` (unit, A40): select three rows, change project, run the bulk prune; the request names zero of the three ids and the confirmation shows the count of rows selected on screen. A page change clears the selection the same way. Fails today because selections survive both.
- `::a bulk action acts on exactly the selected rows on screen` (unit): with five rows selected on the visible page, "Supersede instead" and prune each send those five ids and name "5" in the confirmation; fails today because Supersede acts on the visible page and clears everything.
- `::a partial failure names the counts and keeps failed rows selected` (unit): when two of five actions fail, the toast reads "3 succeeded, 2 failed" and exactly the two failed rows stay selected.
- `queue-paging.test.tsx::both queues page with the library pagination` (unit): the review queue and the hygiene queue render the darkraise-ui `pagination` (its root role and "Next page" control), and a scan finds no hand-written pager in either file; next and previous change the page query.
- `use-facts-facets.test.ts::filter options come from the server facets` (unit): with one page loaded and `facets` listing a status no loaded row has, the status select offers it and `optionsComplete` is true; fails today because options come from loaded pages only.

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/features/knowledge`

- [ ] **Step 3: Implement**

1. F3-3: key the selection on `(project, page)` and reset it when either changes; bulk actions take their ids from the selection intersected with the rows on screen; settle each action and report the counts.
2. F3-9b: replace both hand-written pagers with the library `pagination` inside `list-surface.tsx`, so the two queues share one list pattern.
3. F3-9h: build the select options from `facets`; the demo path keeps deriving them from its fixture.
4. Walk both queues by keyboard and with zero, one and many rows at both viewports and themes; record the screenshot paths for Task 70.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/features/knowledge && npm run typecheck`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/knowledge
git commit -m "fix(knowledge-ui): selection follows the page"
```

### Task 64: Notes, work log and board edits

**Files:**
- Modify: `frontend/src/features/notes/page-pane.tsx`
- Modify: `frontend/src/features/notes/use-page-sync.ts`
- Modify: `frontend/src/features/notes/lib/page-sync.ts`
- Modify: `frontend/src/hooks/api/use-worklog-api.ts`
- Modify: `frontend/src/hooks/api/use-board-api.ts`
- Test: `frontend/src/features/notes/__tests__/page-rename.test.tsx`
- Test: `frontend/src/features/notes/__tests__/block-verbs-mirror.test.ts`
- Test: `frontend/src/hooks/api/__tests__/use-worklog-ledger.test.tsx`
- Test: `frontend/src/hooks/api/__tests__/use-board-edit.test.tsx`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 178, 180, 186, 187, 189
**UI/UX:** UX-6, UX-9
**Depends on:** Task 61
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 2 = 6

- [ ] **Step 1: Write the failing test**

- `page-rename.test.tsx::a failed rename shows an error and keeps the typed title` (unit): typing a new title with the `PATCH` answering 500 shows an error toast and leaves the typed title in the field; fails today silently, with the field reverting.
- `use-worklog-ledger.test.tsx::a live refetch fetches only newer entries` (unit): after the first read of 700 ledger entries (two pages), the next 5-second refetch sends one request with `after=<last held seq>`, and its two new entries are appended; fails today because every refetch pages from the start.
- `use-board-edit.test.tsx::two quick edits to one register both land` (unit): two edits fired in the same tick on one register are sent in order, the second carrying the `content_hash` the first answered, and both succeed; fails today because both carry the same hash and the second gets 409.
- `::a real conflict is still reported` (unit): a 409 on an edit whose hash came from the previous answer shows the conflict message and sends nothing further for that register.
- `page-sync` case `::the editor document is converted once per change batch` (unit): ten keystrokes within one debounce window call the document-to-tree conversion once; fails today with ten.
- `block-verbs-mirror.test.ts::every server refusal has a client mirror` (unit, the mirror note): reading `backend/app/services/block_verbs.py` from disk, every refusal reason name the module raises for pages (the string names passed to `PageBlockInvalid` and the other refusal exceptions) appears in `frontend/src/features/notes/lib/sync-tree.ts` or `block-properties.ts`; the test fails naming any reason the client lacks.

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/features/notes src/hooks/api`

- [ ] **Step 3: Implement**

1. F3-8: `onError` on the rename mutation, keeping the field's value.
2. F3-6: `useAllLedgerEntries` keeps the held entries and, on refetch, requests only `after` the last held `seq`.
3. F3-9f: serialise board edits per register through a promise chain that threads the returned hash.
4. F3-9g: convert the editor document on the save engine's debounce, not on every keystroke; the unload protection and retained-draft rules are unchanged.
5. The mirror test may find a gap: add the missing rule to `sync-tree.ts`, never weaken the test.

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/features/notes src/features/worklog src/features/board src/hooks/api && npm run typecheck`

- [ ] **Step 5: Commit**

```bash
git add frontend/src
git commit -m "fix(notes-ui): report rename failures, chain edits"
```

### Task 65: Extension captures a settled reply once

**Files:**
- Modify: `extension/src/content-autocapture.js`
- Modify: `extension/src/autocapture.js`
- Test: `extension/test/autocapture.test.js`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 190
**Depends on:** none
**Evaluation:** files 1 - spec 2 - coupling 0 - risk 2 = 5

- [ ] **Step 1: Write the failing test**

All in `extension/test/autocapture.test.js`, with a fake clock.

- `a reply that changes 30 times before settling is captured once` (unit, A5): a message whose text changes 30 times at 100 ms intervals and then stays unchanged produces zero capture requests during the changes and exactly one, carrying the final text, 3 seconds after the last change; fails today with one request per distinct partial text.
- `a settled message is not captured again` (unit): a later page mutation that leaves that message's text unchanged sends nothing.
- `an edited message is captured again after it settles` (unit): a text change after capture starts a new 3-second wait and sends the new text once.
- `a reply over the size limit is skipped whole` (unit): a message that settles above 20,000 characters sends nothing, and none of its shorter partial states was sent.
- `two messages settle independently` (unit): message A settling does not delay or trigger message B.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd extension && timeout 300 npm test`

- [ ] **Step 3: Implement**

1. P1-1: keep, per message element, the last seen text and a timer; a change resets the timer; when the text has been unchanged for `SETTLE_MS = 3000` the message is sent once and its text hash recorded. The existing dedupe stays as the second guard.
2. Clear timers when the observer disconnects or the element leaves the page.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd extension && timeout 300 npm test`

- [ ] **Step 5: Commit**

```bash
git add extension
git commit -m "fix(extension): capture a reply once it settles"
```

### Task 66: Release tagging and CI suite coverage

**Files:**
- Modify: `.github/workflows/release.yml`
- Modify: `.github/workflows/ci.yml`
- Modify: `backend/pyproject.toml`
- Modify: `backend/requirements.lock`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `scripts/release.sh`
- Modify: `CLAUDE.md`
- Test: `backend/tests/test_ci_workflows.py`
- Test: `backend/tests/test_declared_dependencies.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 192, 193, 196, 204, 214
**Depends on:** Task 4, Task 48
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 2 = 6

- [ ] **Step 1: Write the failing test**

- `backend/tests/test_ci_workflows.py::test_cancelled_tag_job_creates_no_release` (unit, A49): in `release.yml` the `github-release` job's `if` requires `needs.tag.result == 'success'`, and its `gh release create` carries `--verify-tag`; fails today because a cancelled `tag` still lets it run and create the tag on master's tip.
- `::test_ci_runs_extension_and_sdk_suites` (unit, A50): `ci.yml` has steps running `npm test` in `extension/`, pytest in `sdks/python`, the TypeScript SDK suite and `make build` in `sdks/`; none uses a fixed host port, container name or `--network host`. Fails today because CI skips all four.
- `backend/tests/test_declared_dependencies.py::test_numpy_is_declared` (unit, A50): `pyproject.toml`'s dependencies name `numpy`, and every top-level module `backend/app` imports resolves to a declared distribution (the existing importer map if one exists, else a scan limited to third-party imports); fails today for `numpy`.
- `::test_lucide_react_is_declared` (unit): `frontend/package.json` lists `lucide-react` under `dependencies`.
- `::test_release_script_runs_the_floor_gate_by_default` (unit): `scripts/release.sh` calls `gate.sh` without `--full` unless given `--full-gate`, and then runs the three legs `CLAUDE.md` names for this host.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_ci_workflows.py tests/test_declared_dependencies.py`

- [ ] **Step 3: Implement**

1. P1-3: the `if` and `--verify-tag` as tested. P1-15: add the four suite steps to the job that runs frontend tests (they need Node and the backend venv), following the workflow's existing setup steps.
2. P1-4: add `numpy` to `pyproject.toml` at the version the lock already resolves and regenerate the lock with `uv pip compile --universal pyproject.toml -o requirements.lock`; the diff must change only `numpy`'s `# via` lines.
3. Row 214: `npm install lucide-react@<the version darkraise-ui already resolves>` in `frontend/` so the lockfile changes by that one direct entry.
4. P1-7: `release.sh` as tested; correct `CLAUDE.md`'s sentence on `release.sh` if it says the script runs the full gate.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_ci_workflows.py tests/test_declared_dependencies.py tests/test_deployment_artifact.py && (cd ../frontend && npm run typecheck && npm run build)`

- [ ] **Step 5: Commit**

```bash
git add .github backend/pyproject.toml backend/requirements.lock backend/tests frontend/package.json frontend/package-lock.json scripts/release.sh CLAUDE.md
git commit -m "fix(ci): run every suite, verify the release tag"
```

### Task 67: Backup, restore and build script guards

**Files:**
- Modify: `scripts/backup.sh`
- Modify: `scripts/worker/restore-cycle.sh`
- Modify: `scripts/build-push.sh`
- Modify: `Dockerfile`
- Modify: `docker-compose.worker.yml`
- Modify: `docs/runbook-backup-worker.md`
- Modify: `CLAUDE.md`
- Test: `backend/tests/test_script_guards.py`
- Test: `backend/tests/test_deployment_artifact.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 198, 205, 206, 207, 213
**Depends on:** Task 66
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 3 = 7
**Lenses:** lang-bash

- [ ] **Step 1: Write the failing test**

The script tests run each script in a temporary directory with `pg_dump`, `docker`, `psql`, `alembic` and `git` replaced by stub executables on `PATH`; no test touches a real database or the real backup directory.

- `backend/tests/test_script_guards.py::test_wrong_database_dump_triggers_no_prune` (integration, A49): with 14 existing dumps and a stub `pg_dump` that emits a complete dump lacking the `public.memories` table and the `alembic_version` data, `backup.sh` exits non-zero, names the missing marker, keeps all 14 older dumps and moves the new file aside with a `.suspect` suffix; with a dump carrying both markers it prunes to `BACKUP_KEEP`. Fails today because any complete dump prunes.
- `::test_failed_dump_still_prunes_nothing` (integration): a `pg_dump` exiting 1 leaves every older dump.
- `::test_restore_cycle_fails_on_a_real_migrate_error` (integration, A49): with the migrate step exiting 1 and the snapshot's stamped baseline hash equal to the image's, `restore-cycle.sh` exits non-zero and swaps nothing; with the stamped hash differing (an older baseline) it exits 0 with the existing "older baseline" message. Fails today because every migrate failure exits 0.
- `::test_dirty_tree_is_not_tagged_with_the_head_sha` (integration, A49): with `git status --porcelain --untracked-files=no` reporting a change, `build-push.sh` (with `DARKMEM_PUSH=0` and a stub `docker`) tags `<sha>-dirty` and never the bare sha; with a clean tree it tags the bare sha. An untracked file alone does not make the tree dirty.
- `backend/tests/test_deployment_artifact.py::test_dockerfile_copies_with_ownership_and_installs_once` (unit): the `Dockerfile` contains no `chown -R`, copies application code with `COPY --chown=root:root` so the runtime user cannot write it, installs the app package once, and its Node stage is `node:22`; the writable paths the app needs (`ATTACHMENTS_DIR`, the dumps directory) are still owned by the runtime user.
- `::test_worker_compose_comment_matches_its_network` (unit): the receiver service's comment in `docker-compose.worker.yml` no longer says it has no network.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_script_guards.py tests/test_deployment_artifact.py`

- [ ] **Step 3: Implement**

1. P1-18: after a complete dump and before the prune, `backup.sh` checks the dump (through `gzip -dc | grep -m1`) for `CREATE TABLE public.memories` and for the `alembic_version` data block; on a miss it renames the file `.suspect`, prints the reason and exits 1 without pruning. The attachments family and `_is_snapshot` are untouched.
2. P1-9: `restore-cycle.sh` compares the snapshot's stamped baseline hash with the image's before reading a migrate failure as "older baseline"; any other failure exits 1. `docs/runbook-backup-worker.md` says an older worker image exits non-zero on a snapshot carrying newer revisions, so the worker image must move with the primary.
3. P1-17: the dirty suffix as tested, tracked changes only.
4. P1-16: `COPY --chown`, one install, `node:22`; then build once with `DARKMEM_PUSH=0 ./scripts/build-push.sh` (timeout 1800 s) and confirm with `docker run --rm --entrypoint sh <image> -c 'id -u; test ! -w /app/app'` that the code is not writable by the runtime user. Do not run `docker compose up`.
5. P1-24: correct the comment. `CLAUDE.md`'s Backups paragraph gains the marker check in one sentence.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q tests/test_script_guards.py tests/test_deployment_artifact.py tests/test_single_worker_invariant.py tests/test_worker_receiver.py && bash -n ../scripts/backup.sh ../scripts/worker/restore-cycle.sh ../scripts/build-push.sh`

- [ ] **Step 5: Commit**

```bash
git add scripts Dockerfile docker-compose.worker.yml docs/runbook-backup-worker.md backend/tests CLAUDE.md
git commit -m "fix(ops): guard backup prune and restore failures"
```

### Task 68: Dead scripts and stale comments

**Files:**
- Modify: `backend/scripts/cutover/__init__.py`
- Modify: `backend/alembic.ini`
- Modify: `backend/scripts/e2e/README.md`
- Modify: `scripts/publish_production_models.sh`
- Modify: `docs/runbook-deployment.md`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 200, 201, 202, 209, 210
**Depends on:** Task 67
**Evaluation:** files 3 - spec 2 - coupling 0 - risk 1 = 6

- [ ] **Step 1: No new test, because every change is a removal of a file nothing references or a comment no script reads, and `tests/test_inert_objects.py`, `tests/test_ci_workflows.py`, the benchlib suite and the cutover's remaining test fail if a removed file was still needed**

- [ ] **Step 2: Prove each removal**

Run `rg -n "<basename without extension>" --glob '!docs/2026-11-20-codebase-audit*' .` for every candidate and keep the output for the commit body.
Expected: no reference outside the file itself, its own tests and dated audit or plan documents. A file with a live reference is kept and its row closed with that evidence.

- [ ] **Step 3: Implement**

1. P1-11: delete the five broken, unreferenced seed and test scripts under `backend/scripts/` (the finding's signature is "no MCP auth, or the wrong `ProcessingPipeline` arguments": `seed_test_memories.py`, `seed_test_memories_mcp.py`, `test_batch.py`, `test_batch_100.py` and the fifth the `rg` pass identifies).
2. P1-12 remainder: delete `scripts/publish_production_models.sh` if nothing calls it; otherwise remove its `cd` into the deleted `fine-tuning/` directory and say what it now does.
3. P1-13: remove the 0006-to-baseline loader from `backend/scripts/cutover/` (`backfill.py`, `db.py`, `preflight.py`, `spec.py`, `stage.py`, `__main__.py` and their tests) and keep `llm_providers_transition.py` with its test; `docs/runbook-deployment.md` keeps the transition procedure and loses any step that names the removed loader.
4. P1-20: correct `alembic.ini`'s comment about its ignored URL and the stale part of `backend/scripts/e2e/README.md` (the `ml` extra's comment went in Task 11).
5. P1-21: delete `GITNEXUS_ALGORITHM_COMPARE.txt` and `gitnexus_graph.png` at the repository root. Leave `graph.jpg` alone: it is untracked and the owner's.

- [ ] **Step 4: Run the checks**

Run: `.venv/bin/python -m pytest -q tests/test_inert_objects.py tests/test_ci_workflows.py tests/test_deployment_artifact.py scripts/cutover && .venv/bin/python -m pytest -q scripts/benchlib/tests`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A backend/scripts scripts backend/alembic.ini docs/runbook-deployment.md GITNEXUS_ALGORITHM_COMPARE.txt gitnexus_graph.png
git commit -m "chore: remove dead scripts and stale comments"
```

### Task 69: Contract documents and counts

**Files:**
- Modify: `CLAUDE.md`
- Modify: `CONTRIBUTING.md`
- Modify: `docs/two-door-parity.md`
- Modify: `backend/app/api/mcp/scopes.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/config.py`

**Interfaces:**
- Consumes: none
- Produces: none

**Items:** 131, 135, 195
**Depends on:** Task 68
**Evaluation:** files 2 - spec 2 - coupling 0 - risk 1 = 5

- [ ] **Step 1: No new test, because this task changes prose and comments no script reads; the counts it states are checked by the guards leg (`tests/test_door_parity.py`, `tests/test_code_deriver.py`'s roster, `tests/test_prompt_agent_instructions.py`), which Step 4 runs**

- [ ] **Step 2: Collect the facts the prose must state**

Run, from `backend/`: `.venv/bin/python -c "from app.api.mcp.scopes import TOOL_SCOPES; import collections; print(len(TOOL_SCOPES), collections.Counter(TOOL_SCOPES.values()))"` and `.venv/bin/python -m pytest -q tests/test_code_deriver.py -k roster`; then `git diff master --stat -- CLAUDE.md docs/two-door-parity.md`.
Expected: the tool count and per-scope counts, a passing roster test (27 jobs), and the list of sentences earlier tasks already changed.

- [ ] **Step 3: Implement**

1. B6-22: correct the four stale statements in place: the tool count comment in `scopes.py`, the "placeholders" comment about the dream jobs in `main.py`, the curb row's reader (already gone with Task 44; confirm), and the `LLM_*` sentence: read `config.py` and either remove the fallback fields if nothing reads them (after `rg`), or correct `CLAUDE.md`'s "There are no `LLM_*` env vars" to say what the fallback does.
2. B6-D5: `CLAUDE.md`'s Layout section says `inject_adapters` and `client_connect` are reached only from `backend/scripts/connect.py`.
3. P1-6: `CONTRIBUTING.md` describes the current release model: a push to master releases, `release.sh` is the local pre-flight and writes no tag, the changelog section must exist first.
4. Read `CLAUDE.md` top to bottom against `git diff master` of the code: every sentence about behaviour this plan changed states the new behaviour (read-only list, strict-caller list and count, job state location, events partition reconciliation, `/health` keys, revision retention, embedder family list, feature flags, MCP code tools routing through the service, buffer discard, session rotation). The tool count per scope, the job count and the route counts in `docs/two-door-parity.md`'s headline sentence match Step 2's output.
5. Add nothing that narrates the change; state current rules only.

- [ ] **Step 4: Run the guards leg**

Run the guards-leg command from `CLAUDE.md` with `TEST_DATABASE_URL` from `.dforge/test-env.sh`.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md CONTRIBUTING.md docs/two-door-parity.md backend/app
git commit -m "docs: state what the code does after the audit"
```

### Task 70: UI proof walkthrough

**Files:**
- Create: `docs/dforge/ui-ux/proofs/2026-11-20-audit-remaining.md`
- Create: `docs/dforge/ui-ux/proofs/2026-11-20-audit-remaining.judge.md`

**Interfaces:**
- Consumes: C10, and the screenshots Tasks 45, 49, 50, 53, 55, 57 and 63 recorded (Tasks 12 and 61 record none; Step 3 captures theirs)
- Produces: none

**UI/UX:** OP-1, OP-2, OP-3, OP-4
**Depends on:** Task 69
**Evaluation:** files 1 - spec 2 - coupling 1 - risk 1 = 5

- [ ] **Step 1: No new test, because this task produces the proof report that `scripts/ui-proof check` reads; every behaviour it shows is already pinned by the tests of Tasks 12 and 45 to 64**

- [ ] **Step 2: Launch and seed**

Follow `skills/ui-ux/references/walkthrough.md` of the dforge plugin and `docs/dforge/ui-ux/profile.md`. Start Storybook and the `VITE_DEMO=1` vite server as tracked background tasks with their PIDs noted; for flows that need a server (UX-2, UX-12, UI-6) use the disposable e2e stack through `backend/scripts/e2e/run_playwright_e2e.py`, never `:8000`. Seed the worst-case data of OP-3: a 64-character repository name, an unbroken URL, zero, one and many rows, a refused save, a forced load failure and the 20,000-node synthetic graph.
Expected: every server answers and its PID is recorded.

- [ ] **Step 3: Walk and record**

1. Walk every changed flow by pointer and then by keyboard alone, at 1280x800 and 1920x1080, light and dark, forcing each state. Evidence goes to `.dforge/ui-ux/audit-remaining/`, one screenshot per item and state named `<id>-<viewport>-<theme>[-<state>].png`.
2. Run the automated checks the web platform guide lists (accessibility scan, console errors, overflow, contrast) on each changed screen.
3. Write the proof report with one row per contract item UI-1 to UI-6, UX-1 to UX-12 and OP-1 to OP-4, each naming its screenshot or its test. A41 (UI-1) and A37 (UX-1) cite the C10 state boards. A42's items (UI-2, UI-3, UI-5, UX-6, UX-7, UX-8, UX-9) each show the working behaviour at both viewports. An item no harness on this host can show is an `unverifiable` row with its reason; never write an `**Accepted by:**` line.
4. Stamp the report with `scripts/ui-proof stamp`, have the `dforge:judge-opus` seat review it into the `.judge.md` file, and fix the UI (not the check) for every `fix` verdict.
5. UX-12 and Task 61's refusals have no earlier screenshots; capture them here. The "Failed captures" section is shown from Task 12's stories (`failed-captures-section.stories.tsx`) in Storybook at both viewports and themes, by keyboard alone (Tab reaches Requeue and Discard, Enter opens the dialog, Escape closes it and returns focus), with zero rows, one row, and a row whose `last_error` is a 400-character unbroken line. Task 61's editor refusals, and every other flow that needs a server, are walked by a scratch Playwright spec, `frontend/tests/proof-audit-remaining.spec.ts`, run as `backend/scripts/e2e/run_playwright_e2e.py tests/proof-audit-remaining.spec.ts --project=chromium`: the spec seeds what it needs through the disposable stack's API, writes its screenshots to `.dforge/ui-ux/audit-remaining/`, and is deleted before Step 5's commit, never committed. The OP-4 row of the report states that the section is new on the existing Activity → Triage tab, adds no route or tab, and is hidden in demo mode.
6. Stop every server started in Step 2 and confirm no process of this task is left.

- [ ] **Step 4: Run the gate**

Run: `bash <plugin-root>/scripts/ui-proof check --base master --spec docs/dforge/specs/2026-11-20-audit-remaining-design.md`
Expected: exit 0.

- [ ] **Step 5: Commit**

```bash
git add docs/dforge/ui-ux/proofs
git commit -m "docs(ui-ux): prove the remaining audit UI items"
```

### Task 71: Revision proof on a restored backup and host reports

**Files:**
- Modify: `docs/dforge/registers/2026-11-20-audit-remaining.md`

**Interfaces:**
- Consumes: C7 (the three revisions), C12 (the lost-tag script)
- Produces: none

**Items:** 216
**Depends on:** Task 70
**Evaluation:** files 0 - spec 2 - coupling 1 - risk 3 = 6

- [ ] **Step 1: No new test, because this task runs the shipped revisions and scripts against a restored copy of production data and records what it observed; the revisions' own tests are in Tasks 30, 46 and 48**

- [ ] **Step 2: Restore the newest backup onto the dev Postgres**

1. Create a scratch database on the dev Postgres only: `docker exec darkmem-postgres-1 psql -U darkmem -d darkmem -c "CREATE DATABASE darkmem_restore_proof"`.
2. Load the newest dump of `/root/darkmem-backups` into it (`gzip -dc <dump> | docker exec -i darkmem-postgres-1 psql -U darkmem -d darkmem_restore_proof`, timeout 1800 s). The production container and port 5432 are never written.
3. Record `SELECT version_num FROM alembic_version`, `SELECT count(*) FROM blocks`, and the name and row count of every `triple_embeddings__%` table.
Expected: the restore completes, the stamp is `0003_board_views` or older, and the `blocks` count is above zero. Production holds filed documents, so a zero count means the wrong dump was restored: drop the scratch database, restore the next newest dump and repeat. If every dump has zero blocks, record A46 as not proven on this host with that evidence in rows 26 and 101 and go on.

- [ ] **Step 3: Run the revisions and reports**

1. Build the scratch database's URL the way `.dforge/test-env.sh` builds the test one, from `backend/`: `. ../.dforge/test-env.sh && export RESTORE_URL="${TEST_DATABASE_URL%/darkmem_test}/darkmem_restore_proof"`. Print only its host and database part, never the password.
2. From `backend/`: `DATABASE_URL="$RESTORE_URL" timeout 1800 .venv/bin/python -m alembic upgrade head`. Record the head, the `blocks` count after (it must equal the count before), that no `blocks.search_vector` column and no empty `triple_embeddings__%` table remains, and every kept table with its row count. A kept table gets a register row (`scripts/register add … --state deferred --note "<name> rows=<n>: left in place by revision 0005"`).
3. Run `EXPLAIN` for one per-file edge delete and record that it names `ix_code_edges_source_file`.
4. Run the lost-tag script's dry run against the restored copy: `.venv/bin/python scripts/restore_refine_project_tags.py --dry-run --database-url "$RESTORE_URL"`; record its `memories: <n>` line in the Note of register row 232.
5. Row 216: `gh api repos/{owner}/{repo}/actions/permissions/fork-pr-contributor-approval` and `gh repo view --json visibility` (reads only; the owner and repository come from `git remote get-url origin`). Record both answers in row 216's Note and set it `done`. Change no setting.
6. Drop the scratch database: `docker exec darkmem-postgres-1 psql -U darkmem -d darkmem -c "DROP DATABASE darkmem_restore_proof"`.
7. Write the A46 evidence (counts before and after, tables kept) into the Note of rows 26 and 101.

- [ ] **Step 4: Check the register**

Run: `bash <plugin-root>/scripts/register check docs/dforge/registers/2026-11-20-audit-remaining.md` and `bash <plugin-root>/scripts/register open docs/dforge/registers/2026-11-20-audit-remaining.md`
Expected: the check passes and no row is `open`, `planned` or `doing` (A52); every row is `done`, `verify` or `deferred` with its reason.

- [ ] **Step 5: Commit**

```bash
git add docs/dforge/registers
git commit -m "docs(register): record the revision proof"
```

**After the merge (not part of the auto run; performed on this host once finishing has merged into `master`, in this order, each step confirmed before the next):**

1. `bash .dforge/gate-legs.sh` on `master` prints `ALL LEGS OK`.
2. Compare production's `schema_baseline_sha` stamp with the checkout's (`docker exec darkmem-prod-postgres-1 psql …`), then `DARKMEM_PUSH=0 ./scripts/build-push.sh`; confirm the image tag equals `git rev-parse --short HEAD`.
3. `docker compose up -d`, wait for `healthy`, and confirm the change in the running image: `curl -s localhost:8000/health` carries `pipeline_state`, and `docker exec darkmem-prod-darkmem-1 ls /app/migrations/versions` lists `0006_drop_blocks_search_vector.py`. Production's `alembic_version` reads `0006_drop_blocks_search_vector`.
4. `VACUUM (ANALYZE) blocks` on production, since autovacuum never runs and the column drop rewrote nothing but left the index pages.
5. Start a `full=true` reindex of every repository through `POST /api/v1/repos/{id}/reindex` and wait for each to finish (Tasks 30 and 31 changed stored keys).
6. Probe the embedding purpose (one `embed` through the app's model-probe route). Only if it answers, requeue the 53 `error` buffer rows through `POST /api/v1/memory-buffer/{buffer_id}/requeue`, wait for the flush, and confirm each is `done` with a vector on its memory; otherwise record the requeue as blocked with the embedder's answer. Set register row 215 accordingly (A53).
7. Report to the owner: the lost-tag dry run's count (the restore itself waits for the owner's word, row 232), the fork-approval setting read in Task 71, that the backup worker's image must move with the primary, and that nothing was pushed, so no release was cut.
