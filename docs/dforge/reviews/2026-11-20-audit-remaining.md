# Review record: 2026-11-20-audit-remaining

Plan: docs/dforge/plans/2026-11-20-audit-remaining.md
Retained: 2026-11-21

Review depth: full (spec,task-risk:1)
Acceptance QA: complete — 48 pass, 1 fail, 0 flaky, 0 cannot-test, 6 demo
final review lens security — 0 Critical, 0 Important, 2 Minor; fixed 2, rejected 0
final review lens ui-ux — 0 Critical, 1 Important, 6 Minor; fixed 7, rejected 0
final review lens silent-failures — 0 Critical, 3 Important, 5 Minor; fixed 7, rejected 1
final review lens test-quality — 0 Critical, 1 Important, 8 Minor; fixed 4, rejected 4
final review lens code-quality — 0 Critical, 1 Important, 5 Minor; fixed 3, rejected 3; parts lang-bash=0,lang-python=2,type-design=1,lang-typescript=1,docs-comments=2
Test ratio: 19067 test / 10969 code lines (a9213a7..e365292)
Final review: clean (commits a9213a7..e365292, 9 parked)

## Amendments

## A1 — Header
Reason: The Register bullet closes shared rows on the first half, contradicting the header's own Assumptions line.
Cost if wrong: One extra clause in the header and nothing else.
### Old
````text
- **Register.** When a task's commit lands, set each row its `**Items:**` line names with `scripts/register set <register> <id> done --note "<commit sha7>"` unless the row is closed `not reproduced`.
````
### New
````text
- **Register.** When a task's commit lands, set each row its `**Items:**` line names with `scripts/register set <register> <id> done --note "<commit sha7>"` unless the row is closed `not reproduced`, or a later task's `**Items:**` line also names it (rows 9, 13, 20, 25, 27, 32, 153, 164, 173 and 188): such a row stays `doing` until the last task naming it lands, and that task sets it `done` with its own sha.
````

## A2 — Task 32
Reason: The step omits two readers that its own source scan will find.
Cost if wrong: None; the scan forces the edits anyway.
### Old
````text
2. Removal 8, readers only: drop `last_commit_sha` from the ORM model, `CodeFileResponse`, the frontend type and the raw INSERT in `promotion_corpus.py`. The column stays (register row 231 carries the drop). Because the model no longer maps the column, confirm `tests/test_schema_guard.py` and any model-versus-schema drift test still pass, and say in the commit body that the column is kept deliberately.
````
### New
````text
2. Removal 8, readers only: drop `last_commit_sha` from the ORM model, `CodeFileResponse`, the file-row serialiser in `app/services/code_query.py` that copies it into the response, the frontend type, the two fixture rows in `frontend/src/features/code/__tests__/real-code-graph-view.test.tsx` and the raw INSERT in `promotion_corpus.py`. The column stays (register row 231 carries the drop). Because the model no longer maps the column, confirm `tests/test_schema_guard.py` and any model-versus-schema drift test still pass, and say in the commit body that the column is kept deliberately.
````

## A3 — Task 33
Reason: C8 forbids a private registration helper, yet the step keeps `triple_embeddings.py`'s copy until Task 46.
Cost if wrong: Two lines edited in a module Task 46 deletes.
### Old
````text
4. B5-17: `embedder_registry.ensure_registered` (C8) replaces the private copies. `triple_embeddings.py` keeps its copy until Task 46 deletes the module.
````
### New
````text
4. B5-17: `embedder_registry.ensure_registered` (C8) replaces the private copies, including the `_ensure_partition` in `triple_embeddings.py`, so C8 holds from this task on; Task 46 then deletes that module whole.
````

## A4 — Task 55
Reason: Task 45 removes the Distribution tab's only save-on-change switches, so this test case cannot be built.
Cost if wrong: None; Distribution has nothing left to revert.
### Old
````text
- `::a toggle that saves at once reverts on failure` (unit): for the Distribution and Research toggles, a failed save returns the switch to its old position and shows an error toast.
````
### New
````text
- `::a toggle that saves at once reverts on failure` (unit): for each Settings switch that still saves on change after Task 45 (the Research toggles, and any other `Switch` under `frontend/src/features/settings/components` whose `onCheckedChange` calls a mutation directly; the Distribution tab has none left, since its curb and watch switches left in Task 45), a failed save returns the switch to its old position and shows an error toast.
````

## A5 — Task 4
Reason: The fork `if` as specified is false on push events, and on picked jobs it makes the picker's fork rule unreachable; the spec asks for the e2e job plus the picker.
Cost if wrong: Fork PRs run hosted checks; the fork-approval setting remains the real barrier.
### Old
````text
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
````
### New
````text
- `backend/tests/test_ci_workflows.py::test_fork_pull_request_never_reaches_self_hosted` (unit, A6): parsing `ci.yml`, every job whose `runs-on` names `darkmem-linux` or `self-hosted` literally (today `e2e`) carries an `if` that is false for a `pull_request` event whose `github.event.pull_request.head.repo.full_name != github.repository` and true for every other event (a push to master and a `workflow_dispatch` still run it), and the `pick-runner` job receives a fork marker computed from the same expression; fails today because `e2e` has no such condition.
- `::test_picker_routes_a_fork_to_hosted` (unit, A6): `pick_runner` called with the fork marker set (the environment variable the workflow passes from the same expression) returns `ubuntu-latest` in every mode, including when no picker token is present; fails today because a tokenless picker queues on self-hosted.
- `::test_third_party_actions_are_pinned_to_shas` (unit): in all three workflow files, every `uses:` naming an action outside `actions/` and `github/` is pinned to a 40-character commit sha with the tag in a trailing comment.
- `::test_scan_job_does_not_write_the_publish_cache` (unit): the trivy scan job's build step has no `cache-to`, or a scope different from the publish job's `cache-from`.
- `backend/tests/test_dev_script_guards.py::test_start_dev_server_refuses_without_database_url` (integration, bash): the test never runs the script in place. It copies `scripts/start_dev_server.sh` into `<tmp>/scripts/`, creates `<tmp>/backend/.venv/bin/python` and, in a directory put first on `PATH`, `python`, `pip`, `alembic` and `uvicorn`, each a stub that appends its arguments to `<tmp>/calls.log` and exits 0, then runs the copy under `timeout 10` with `DATABASE_URL` unset. It asserts a non-zero exit that is not 124, a printed line naming `DATABASE_URL`, and an empty `calls.log`; a second case with `DATABASE_URL` set asserts the first logged call is the venv stub with `-m alembic upgrade head` and that no call came from the bare `python` stub. Fails today because the bare `python` stub is called with `-m alembic upgrade head` and the script exits 0. The stubs are what keep the red run from migrating port 5432 or binding `:8000`.
- `::test_e2e_reset_refuses_a_non_disposable_database` (unit): `e2e_db`'s reset raises before any SQL when the target database name does not match the suite's disposable pattern or the port is 5432; the destructive-SQL guard's exemption text no longer claims it never touches an ambient database.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest -q tests/test_ci_workflows.py tests/test_dev_script_guards.py`

- [ ] **Step 3: Implement**

1. P1-2 (code half): add the head-repository condition, written as `github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository`, to the `e2e` job and to any other job whose `runs-on` names a self-hosted label literally; jobs on a picked runner get no such `if`, so a fork pull request still runs them, hosted. Pass a fork marker computed from the same expression into `pick-runner` and make `pick_runner.py` answer `ubuntu-latest` for it first, before any token or mode check. Do not change any GitHub setting; `docs/runbook-ci.md` gains one sentence on the rule.
````

## A6 — Task 23
Reason: The test places the memo on "the older memory" while Step 3.1 places it on "the memory with the smaller id".
Cost if wrong: None for the choice; the added case guards the documented `jsonb_set` data-loss trap.
### Old
````text
- `backend/tests/test_memory_dream.py::test_distinct_verdict_is_remembered_by_content` (integration): after the judge rules a pair `distinct`, the older memory's `metadata.dream.distinct.<counterpart_id>` holds both `content_sha` values, and the next rotation sends that pair to the judge zero times; after either memory's content changes, the pair is judged again. Fails today because the pair is re-judged every rotation.
````
### New
````text
- `backend/tests/test_memory_dream.py::test_distinct_verdict_is_remembered_by_content` (integration): after the judge rules a pair `distinct`, the pair's memory with the smaller id holds `metadata.dream.distinct.<the other memory's id>` with both `content_sha` values (one case uses a memory whose metadata held no `dream` key before, so the memo must be written with the three nested `jsonb_set` levels `dream_undo.py` uses for the `undone_subsume` tombstone), and the next rotation sends that pair to the judge zero times; after either memory's content changes, the pair is judged again. Fails today because the pair is re-judged every rotation.
````

## A7 — Task 32
Reason: The commit does not stage the frontend fixture that the task's own scan forces it to edit.
Cost if wrong: None.
### Old
````text
git add backend frontend/src/hooks/api/use-code-api.ts sdks
````
### New
````text
git add backend frontend/src/hooks/api/use-code-api.ts frontend/src/features/code/__tests__/real-code-graph-view.test.tsx sdks
````

## A8 — Task 33
Reason: The private copies call `embedder_registry.register` and contain no `CREATE TABLE`, so the scan's first clause passes today and asserts nothing.
Cost if wrong: None.
### Old
````text
- `::test_one_fingerprint_registration_helper` (unit): an AST scan of `app/services` finds `CREATE TABLE IF NOT EXISTS`-registering helpers only in `embedder_registry.py`; `block_embeddings`, `worklog_embeddings`, `relation_embeddings` and `entity_anchoring` call `ensure_registered`.
````
### New
````text
- `::test_one_fingerprint_registration_helper` (unit): an AST scan of `app/services` finds no function named `_ensure_partition` in any module, and no direct call to `embedder_registry.register` in `block_embeddings`, `worklog_embeddings`, `relation_embeddings`, `entity_anchoring` or `triple_embeddings`, each of which calls `ensure_registered` instead; fails today on the four `_ensure_partition` copies and on `block_embeddings`' direct call.
````

## A9 — Task 43
Reason: A pasted list of ids cannot match a later run if the seeded memories get random ids.
Cost if wrong: None.
### Old
````text
- `::test_retrieval_order_is_unchanged` (integration, A45): for a seeded corpus of 30 memories and five fixed queries, the ids returned by `memory_search`, by chat retrieval and by `knowledge_search` equal a list recorded from the same seed before the removal (record the list in Step 2, on the unmodified code, into the test file).
````
### New
````text
- `::test_retrieval_order_is_unchanged` (integration, A45): for a corpus of 30 memories seeded with fixed ids (`uuid.UUID(int=n)` for n = 1..30), fixed content and an embedder stub whose vector is a function of the text alone, and five fixed queries, the ids returned by `memory_search`, by chat retrieval and by `knowledge_search` equal a list recorded from the same seed before the removal (record the list in Step 2, on the unmodified code, into the test file as those fixed ids).
````

## A10 — Task 46
Reason: Downgrading the shared worker database inside a test leaks state into later tests on that xdist worker.
Cost if wrong: One more `CREATE DATABASE` per run.
### Old
````text
- `::test_revision_drops_empty_tables_and_keeps_a_populated_one` (integration): on a database migrated to `0004`, with two `triple_embeddings__<slug>` tables created by hand, one empty and one holding a row, `alembic upgrade 0005_drop_triple_embeddings` drops the empty one, leaves the populated one in place, logs a line naming it with `rows=1`, and exits 0.
- `::test_revision_is_a_no_op_without_such_tables` (integration): the upgrade succeeds on a database with no such table.
````
### New
````text
- `::test_revision_drops_empty_tables_and_keeps_a_populated_one` (integration): on a scratch database the test creates through an admin connection (`CREATE DATABASE "<the worker's database>_rev"`, as `tests/test_cutover_backfill.py` does today) and drops in teardown, migrated with Alembic to `0004_code_edge_file_indexes`, with two `triple_embeddings__<slug>` tables created by hand, one empty and one holding a row, `alembic upgrade 0005_drop_triple_embeddings` drops the empty one, leaves the populated one in place, logs a line naming it with `rows=1`, and exits 0. The shared worker database is never downgraded.
- `::test_revision_is_a_no_op_without_such_tables` (integration): on the same kind of scratch database, the upgrade succeeds when no such table exists.
````

## A11 — Task 47
Reason: The fact model's ORM mapping of `stated_expiry` is a reader of the column, and the step never removes it.
Cost if wrong: None; the scan forces it, and naming it prevents an allowlist workaround.
### Old
````text
1. Remove the close arm in `verification_recompute.py`, `StatedExpiryOutcome`, the `stated_expiry` parameter of `insert_open`, the merge `LEAST` on that column, the column's entry in `knowledge_triples._COLUMNS`, and `tests/test_stated_expiry_facts.py`.
````
### New
````text
1. Remove the close arm in `verification_recompute.py`, `StatedExpiryOutcome`, the `stated_expiry` parameter of `insert_open`, the merge `LEAST` on that column, the column's entry in `knowledge_triples._COLUMNS`, the `stated_expiry` mapping and the comment above it on the fact model in `app/models/graph.py` (a released model that maps the column is a reader, which is what defers the drop), and `tests/test_stated_expiry_facts.py`. As Task 32 does for `last_commit_sha`, confirm `tests/test_schema_guard.py` and any model-versus-schema drift test still pass with the column unmapped, and say in the commit body that the column is kept deliberately.
````

## A12 — Task 48
Reason: Downgrading the shared worker database inside a test leaks state into later tests on that xdist worker.
Cost if wrong: One more `CREATE DATABASE` per run.
### Old
````text
- `backend/tests/test_drop_blocks_search_vector.py::test_column_and_index_are_gone_and_rows_survive` (integration): on a database migrated to `0005` and holding one filed document and one page (blocks counted before), `alembic upgrade head` leaves no `blocks.search_vector` column and no `ix_blocks_search_vector`, and the `blocks` row count and every block's `text` are unchanged; fails today because the revision does not exist.
````
### New
````text
- `backend/tests/test_drop_blocks_search_vector.py::test_column_and_index_are_gone_and_rows_survive` (integration): on a scratch database the test creates through an admin connection (`CREATE DATABASE "<the worker's database>_rev"`, the same fixture Task 46's revision test uses) and drops in teardown, migrated with Alembic to `0005_drop_triple_embeddings` and holding one filed document and one page (blocks counted before), `alembic upgrade head` leaves no `blocks.search_vector` column and no `ix_blocks_search_vector`, and the `blocks` row count and every block's `text` are unchanged; fails today because the revision does not exist. The shared worker database is never downgraded.
````

## A13 — Task 57
Reason: Spec A38 renews a session 23 hours old, which leaves exactly 60 minutes; the test does not pin that boundary.
Cost if wrong: The renewal moves one minute earlier.
### Old
````text
- `session-renewal.test.ts::renews a session with under an hour to spare` (unit, A38): with `expires_at` 59 minutes ahead, the minute check calls `POST /api/v1/auth/refresh` once, stores the new `expires_at`, and writes the renewal time to `localStorage` only after the response has arrived; with 61 minutes ahead it calls nothing. A `visibilitychange` to visible runs the same check at once. Fails today because the app never calls refresh.
````
### New
````text
- `session-renewal.test.ts::renews a session with an hour or less to spare` (unit, A38): with `expires_at` exactly 60 minutes ahead (a 24-hour session 23 hours old), and again with 59 minutes ahead, the minute check calls `POST /api/v1/auth/refresh` once, stores the new `expires_at`, and writes the renewal time to `localStorage` only after the response has arrived; with 61 minutes ahead it calls nothing. A `visibilitychange` to visible runs the same check at once. Fails today because the app never calls refresh.
````

## A14 — Task 67
Reason: `build-push.sh` tags `darkraise/darkmem:latest`, the tag production's compose runs, so a mid-run container recreation would deploy branch code and migrate production.
Cost if wrong: One scratch image to remove.
### Old
````text
4. P1-16: `COPY --chown`, one install, `node:22`; then build once with `DARKMEM_PUSH=0 ./scripts/build-push.sh` (timeout 1800 s) and confirm with `docker run --rm --entrypoint sh <image> -c 'id -u; test ! -w /app/app'` that the code is not writable by the runtime user. Do not run `docker compose up`.
````
### New
````text
4. P1-16: `COPY --chown`, one install, `node:22`; then build once from the repository root with `timeout 1800 docker build -t darkmem-audit-proof:local .` (never through `scripts/build-push.sh`, which also tags `darkraise/darkmem:latest`, the tag production's compose file runs) and confirm with `docker run --rm --entrypoint sh darkmem-audit-proof:local -c 'id -u; test ! -w /app/app'` that the code is not writable by the runtime user; then `docker rmi darkmem-audit-proof:local`. Do not run `docker compose up`.
````

## A15 — Task 68
Reason: `transform.py` and `verify.py` import the modules being deleted, and the loader's tests in `backend/tests/` are neither named nor staged.
Cost if wrong: None.
### Old
````text
3. P1-13: remove the 0006-to-baseline loader from `backend/scripts/cutover/` (`backfill.py`, `db.py`, `preflight.py`, `spec.py`, `stage.py`, `__main__.py` and their tests) and keep `llm_providers_transition.py` with its test; `docs/runbook-deployment.md` keeps the transition procedure and loses any step that names the removed loader.
4. P1-20: correct `alembic.ini`'s comment about its ignored URL and the stale part of `backend/scripts/e2e/README.md` (the `ml` extra's comment went in Task 11).
5. P1-21: delete `GITNEXUS_ALGORITHM_COMPARE.txt` and `gitnexus_graph.png` at the repository root. Leave `graph.jpg` alone: it is untracked and the owner's.

- [ ] **Step 4: Run the checks**

Run: `.venv/bin/python -m pytest -q tests/test_inert_objects.py tests/test_ci_workflows.py tests/test_deployment_artifact.py scripts/cutover && .venv/bin/python -m pytest -q scripts/benchlib/tests`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A backend/scripts scripts backend/alembic.ini docs/runbook-deployment.md GITNEXUS_ALGORITHM_COMPARE.txt gitnexus_graph.png
````
### New
````text
3. P1-13: remove the 0006-to-baseline loader from `backend/scripts/cutover/` (`backfill.py`, `db.py`, `preflight.py`, `spec.py`, `stage.py`, `transform.py`, `verify.py`, `__main__.py`) and its tests `backend/tests/test_cutover_backfill.py` and `backend/tests/test_cutover_transform.py`, once Step 2's search shows no importer of any of them outside the package and those tests; keep `__init__.py` (its docstring describes what remains), `llm_providers_transition.py` and `scripts/cutover/tests/test_llm_providers_transition.py`; `docs/runbook-deployment.md` keeps the transition procedure and loses any step that names the removed loader.
4. P1-20: correct `alembic.ini`'s comment about its ignored URL and the stale part of `backend/scripts/e2e/README.md` (the `ml` extra's comment went in Task 11).
5. P1-21: delete `GITNEXUS_ALGORITHM_COMPARE.txt` and `gitnexus_graph.png` at the repository root. Leave `graph.jpg` alone: it is untracked and the owner's.

- [ ] **Step 4: Run the checks**

Run: `.venv/bin/python -m pytest -q tests/test_inert_objects.py tests/test_ci_workflows.py tests/test_deployment_artifact.py scripts/cutover && .venv/bin/python -m pytest -q scripts/benchlib/tests`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A backend/scripts scripts backend/alembic.ini docs/runbook-deployment.md GITNEXUS_ALGORITHM_COMPARE.txt gitnexus_graph.png backend/tests/test_cutover_backfill.py backend/tests/test_cutover_transform.py
````

## A16 — Task 71
Reason: The spec records 0 documents on production and A46 requires seeding the restored copy when `blocks` is empty; the plan instead treats zero as a wrong dump and gives up on A46.
Cost if wrong: A few rows in a scratch database that Step 3.6 drops.
### Old
````text
Expected: the restore completes, the stamp is `0003_board_views` or older, and the `blocks` count is above zero. Production holds filed documents, so a zero count means the wrong dump was restored: drop the scratch database, restore the next newest dump and repeat. If every dump has zero blocks, record A46 as not proven on this host with that evidence in rows 26 and 101 and go on.
````
### New
````text
Expected: the restore completes and the stamp is `0003_board_views` or older. A zero `blocks` count does not mean a wrong dump (the spec read 0 documents on production on 2026-11-20). When the count is zero, seed the copy after Step 3.1 has set `RESTORE_URL` and before Step 3.2: from `backend/`, run a scratch Python snippet with `DATABASE_URL="$RESTORE_URL"` that files one two-paragraph markdown document through `document_door`'s put function with `embed_inline=False` and no LLM, creates one one-paragraph page through `page_door`'s create function, both in project `restore-proof`, and commits. Then re-read `SELECT count(*) FROM blocks` and record that non-zero count as the count before (spec A46). The snippet is not kept and is never pointed at production.
````

## A17 — Task 29
Reason: First step of the 88/89 swap; adding 89 before Task 3 drops it keeps every row cited.
Cost if wrong: None; A3 removes the interim 88.
### Old
````text
**Items:** 82, 88, 93
````
### New
````text
**Items:** 82, 88, 89, 93
````

## A18 — Task 3
Reason: Task 3 fixes B4-19, which is register row 88, not row 89 (B4-20).
Cost if wrong: None; traceability only.
### Old
````text
**Items:** 117, 127, 89
````
### New
````text
**Items:** 117, 127, 88
````

## A19 — Task 29
Reason: Last step of the swap; Task 29 fixes B4-20 (row 89), and row 88 is now cited by Task 3.
Cost if wrong: None; traceability only.
### Old
````text
**Items:** 82, 88, 89, 93
````
### New
````text
**Items:** 82, 89, 93
````
