# B4 — code indexing

Reviewer findings for the 2026-11-20 audit, as returned. Summary first where the reviewer gave one, then one entry per finding. Index and verification status: `docs/2026-11-20-codebase-audit.md`.

**Summary.** Findings by severity: 3 high, 13 medium, 9 low, plus 8 removal candidates and some doc drift.

The three most important:
1. **A repository can be stuck in `indexing` or `cloning` for good.** A deploy, restart or task cancel kills the run with `CancelledError`, which the `except Exception` handlers don't catch, and nothing resets the status at boot. Every later reindex is then refused (409); only manual SQL frees it. See `code_pipeline.py:535`, `repos.py:373`, `main.py:660,671`, `repo_manager.py:264-291`.
2. **Two eager ORM relationships load the whole symbol table, source code included, whenever a repository row is loaded.** That covers every repo route, every `repo_sync` tick and the list endpoint (about 1 s per request). Nothing reads these relationships. See `models/code.py:38,53`.
3. **Untracked secrets get indexed.** The file walk ignores `.gitignore`, so files like `.env` or credential notes in a `local_path` repo are embedded and served through `code_search`. See `code_pipeline.py:2074-2083`.

Answers to your specific questions:
- `code_reconcile.py` is live; only the standalone job was retired.
- `wiki_generator`, `enrichment_worker`, `process_tracer` and `community_detector` are all reachable, and both the UI and MCP read their output.
- The index-debt queue can't drop or double-drain work.
- `entity_merge` does fail the savepoint when a relation is missed.

The only dead module found is `named_bindings/wildcard_synthesis.py` (113 lines, no importer).

---

# B4 — Code-indexing subsystem audit (full report)

## Summary

The incremental-indexing bookkeeping holds up. Index debt cannot be dropped, the entity-merge savepoint fails when a relation is missed, and the claim is atomic. The serious problems are in the layers around that bookkeeping:

1. A repository caught mid-run by a restart or deploy stays `indexing`/`cloning` forever. No boot step releases the claim.
2. Two eager ORM relationships (`lazy="selectin"`) load every `CodeFile` and `CodeSymbol` row, source text included, whenever a `Repository` row is loaded. That covers every repo route, every `repo_sync` tick, and the list endpoint, which the frontend itself measured at about 1 second per request.
3. The file walk ignores `.gitignore`. A `local_path` repository's untracked secrets (`.env`, credential notes, dumps) are therefore chunked, embedded and served through `code_search`.

Beyond those three there are several correctness gaps in incremental runs: non-ASCII paths, cross-file base classes, permanently lost embeddings, and blast-radius lookups not scoped to a repository. The working-tree drift scan blocks the event loop. Per-file deletes scan the whole repository's edge table.

Counts: high 3, medium 13, low 9, plus dead-code and doc-drift items.

Answers to the dispatch questions:
- `code_reconcile.py` is **live**. Only the standalone *job* was retired. Its `compute_working_tree_drift` is called by `repo_sync`, and its `_file_hash` by `reindex_files`.
- `wiki_generator`, `enrichment_worker`, `process_tracer` and `community_detector` are all reachable:
  - wiki: reindex `generate_wiki`, read by `GET /code/wiki` and the SPA wiki tab;
  - enrichment: pipeline phase 13 and the `code_enrichment` job, read by MCP `code_symbol`/`code_file_symbols`/`code_context` and the SPA;
  - process and community detection: phases 10 and 9, read by the SPA code graph (`code-processes.ts`, `member_of`) and MCP `code_context`.

---

### 1. A repository interrupted by restart, deploy or task cancel is wedged in `indexing`/`cloning` permanently
- Kind: bug
- Severity: high
- Confidence: confirmed
- Where:
  - claim and busy statuses: `backend/app/services/repo_manager.py:264-291`
  - runs that miss `CancelledError`: `backend/app/services/code_pipeline.py:535`, `backend/app/api/routes/repos.py:373`
  - shutdown cancels running tasks: `backend/app/main.py:660,671`
  - `repo_sync` skips busy repos: `backend/app/services/job_runners.py:116-118,183`
- Evidence:
  - `claim_for_indexing` commits `status='indexing'`.
  - The run's cleanup is `except Exception`, which does not catch `asyncio.CancelledError` (a `BaseException`). Shutdown runs `job_registry.stop_all()` and `TaskRegistry.cancel_all()`, which cancel any in-flight index or clone.
  - Nothing in `backend/app` ever resets `indexing`/`cloning`. The only writers of `Repository.status` via `UPDATE` are the claim itself and `git_accounts.py:350`.
- Failure scenario:
  1. An index run or clone is in progress when the operator redeploys, which the owner rule requires after every landed change.
  2. After boot, `claim_for_indexing` refuses forever: reindex returns 409, the webhook returns 409, and MCP `code_reindex` returns `repo_busy`.
  3. `repo_sync`'s fetch lane skips the repo and its index lane loses the claim on every tick.
  4. `DELETE /repos/{id}/tasks/{task_id}` returns 404 because the in-memory task is gone.
  5. The only way out is manual SQL. Any half-written first index is also left behind, because the destructive cleanup never ran.
- Remedy: fix.
  - At startup (single worker, invariant 13), move every `indexing`/`cloning` row to `stale` when `last_indexed_commit` is set, otherwise to `error`, with a message naming the interruption.
  - Optionally also catch `CancelledError` in `CodePipeline.run` to write `stale`, then re-raise.
  - Add a test that seeds `status='indexing'` and boots.

### 2. `Repository.files` and `CodeFile.symbols` are eager (`selectin`): every repository load pulls the whole symbol table, source code included
- Kind: performance
- Severity: high
- Confidence: confirmed
- Where:
  - the relationships: `backend/app/models/code.py:38,53`
  - callers that load `Repository` rows:
    - `repo_manager.py:259` (`get`), `294` (`list_all`), `319`, `361`
    - `job_runners.py:87-99`: every `repo_sync` tick, then one `get` per armed repo
    - `git_accounts.py:319`
    - `wiki_generator.py:43`
    - `code_pipeline.py:282,555`
    - MCP `server.py:1476,1480,1592`
  - per-file `select(CodeFile)` that also loads symbols: `code_pipeline.py:1063,1923`
- Evidence:
  - Both relationships are declared `lazy="selectin"`.
  - Nothing reads `repo.files` or `code_file.symbols` (grep for `.files`/`.symbols` on ORM objects in backend finds only parser dataclasses).
  - `GET /repos` (`list_all`) does `select(Repository)` and so selectin-loads every file and every symbol, `source_code` TEXT included, for **every** repository. It then counts them again in SQL.
  - The frontend comment at `frontend/src/lib/websocket.ts:191-193` records that this list request takes about 1 second.
  - Deleting a repository goes through the ORM cascade (`cascade="all, delete-orphan"`), so its rows are deleted one by one in Python rather than by the database's `ON DELETE CASCADE`.
- Failure scenario:
  - The darkmem repo has 3,996 files and about 22.5k symbols.
  - Every `repo_sync` tick (default 60 s, floor 15 s, per armed repo), every repo GET/PUT/DELETE, every reindex/webhook call and MCP `code_repos` materialises tens of MB of ORM objects on the single worker.
  - The pipeline's long-lived session keeps all of them in its identity map for the whole run, because `expire_on_commit=False`.
- Remedy: simplify. Remove both relationships, or set them to `lazy="raise"`. The blast radius is small:
  - `repo_manager.delete` then relies on the existing FK `ON DELETE CASCADE`.
  - `_delete_file_data`'s `session.delete(existing)` becomes a direct `DELETE`; the DB cascade removes the symbols.
  - Check the tests that build repos through the ORM.

### 3. The file walk ignores `.gitignore`: untracked secrets in a `local_path` repo are embedded and served through code search
- Kind: security
- Severity: high
- Confidence: confirmed (whether a production repo currently holds such files is Unknown; settle with a `SELECT DISTINCT file_path FROM code_files` filtered for `.env`, `credential`, `secret`, `.pem` and `.sql`)
- Where:
  - the walk: `code_pipeline.py:2074-2083` (`_list_all_files`, `rglob("*")`), with the filters at `:43-50,2054-2071`
  - unknown-language files fall back to plain line chunks: `code_parser.py:305-316,344-352`
  - chunks are embedded and stored: `code_pipeline.py:1727-1835`
  - served by: `code_query.py:63-149`, MCP `code_search` (`read` scope)
- Evidence: no `git ls-files`, `check-ignore` or `.gitignore` handling exists anywhere in `backend/app/services`. The only exclusions are a fixed directory and extension list. Every other file, including dotfiles, Markdown notes, JSON/YAML config and SQL dumps under 500 KB, is chunked and embedded, and `chunk_content` is stored verbatim.
- Failure scenario:
  1. An operator registers a checkout by `local_path`.
  2. Its `.env`, `.claude/local-credentials.md` (the pattern this repo itself uses for keys) or `backups/*.sql` are indexed.
  3. Any key with `read` scope can then retrieve them with `code_search "API_KEY"`.
  4. The text also goes to the embedding provider.
  Managed clones only contain tracked files, so this risk sits with `local_path` repos and `index_uncommitted`.
- Remedy: fix. Build the file list from `git ls-files -z --cached --others --exclude-standard`, falling back to the walk only for a tree that is not a git repository. Keep `is_discoverable_path` as the second filter. The same list feeds `compute_working_tree_drift`, so both must change together, as the docstring at `code_reconcile.py:21-24` requires.

### 4. The working-tree drift scan hashes every file synchronously on the event loop
- Kind: performance
- Severity: medium
- Confidence: confirmed
- Where: `code_reconcile.py:62-95`, called from `job_runners.py:166`; also `code_pipeline.py:670,713` (`_list_all_files` in phase 01)
- Evidence: `compute_working_tree_drift` is `async`, but calls `_list_all_files` (`rglob`) and `_file_hash` (read plus sha256 of every file) directly, with no executor. `_parse_one` uses `run_in_executor` for the same work.
- Failure scenario: with `index_uncommitted` on, every `commit_poll_seconds` tick at an unchanged HEAD walks and hashes the whole tree (about 4k files and tens of MB here). That blocks the one uvicorn worker's loop for the duration: HTTP, MCP, websockets and other jobs all stall.
- Remedy: optimise. Run the scan in `run_in_executor`, or compare `(mtime, size)` first and hash only files whose stat changed.

### 5. Per-file deletes scan the whole repository's edge and node tables, so a full reindex is O(files × edges)
- Kind: performance
- Severity: medium
- Confidence: confirmed (from query shape and the index definitions at `0001_baseline.py:1023-1029`)
- Where: `code_pipeline.py:1922-1982`, called per file from `:743-749` and `:1087-1089`
- Evidence:
  - The edge delete ORs `source_key = :fp`, `target_key = :fp`, `split_part(source_key,'::',2) = :fp` and `split_part(target_key,'::',2) = :fp`. No index covers `split_part(...)`, so every call scans all of the repo's edges.
  - The node delete (`properties->>'file_path'`), the repo-wide orphan route/tool delete, `SELECT fingerprint FROM embedders` and one chunk delete per fingerprint also run once per file.
- Failure scenario: a `full=true` reindex or a diff-failure fallback over 4k files performs 4k scans of the repo's full edge set, plus 4k repo-wide orphan sweeps. An incremental run with 500 dependents does the same for each changed file. This bloats dead tuples on a host where autovacuum never runs.
- Remedy: optimise. Delete in one statement per phase, `split_part(...) = ANY(:files)`. Add expression indexes on `(repo_id, split_part(source_key,'::',2))` and on the target equivalent in a new revision. Run the orphan sweep once per run.

### 6. One failed embed loses that file's code chunks until the file changes again
- Kind: bug
- Severity: medium
- Confidence: confirmed
- Where: `code_pipeline.py:1087-1092,1783-1785,1810-1813`
- Evidence:
  1. Phase 03 deletes the old chunks for a changed file and commits the new `content_hash`.
  2. In phase 12, an embed exception only appends to `errors`, and the file is skipped.
  3. The next incremental run sees an equal hash and does not include the file.
  4. No sweep re-embeds missing code chunks: `upsert_code_chunks`'s only caller is phase 12.
- Failure scenario: an Ollama timeout on one file leaves that file absent from vector `code_search` until it is edited or a full reindex runs. The `pipeline_failures` row is resolved by the next clean run, so the loss becomes invisible.
- Remedy: fix. Either don't treat the file as indexed (or record it as debt) when its embed fails, or add a pass that embeds files with no chunk row under the active fingerprint.

### 7. Incremental diff parsing breaks on non-ASCII and special-character paths
- Kind: bug
- Severity: medium
- Confidence: confirmed (git's default `core.quotePath=true`)
- Where: `code_pipeline.py:2142-2169`
- Evidence: `git diff --name-status` is parsed by splitting on tab with no `-z`. Git quotes and octal-escapes any path containing bytes ≥ 0x80, quotes or tabs, so `src/é.py` arrives as `"src/\303\251.py"`.
- Failure scenario:
  - A changed path that git quoted is not found on disk and is counted as skipped. The stale graph and chunks for that file stay.
  - A deleted quoted path never matches its `CodeFile` row, so its symbols survive forever.
  - Only a full reindex or the drift scan repairs either.
- Remedy: fix. Use `git diff --name-status -z` and split on NUL.

### 8. Incremental runs mis-key cross-file base classes defined in unchanged files
- Kind: bug
- Severity: medium
- Confidence: confirmed
- Where: `code_pipeline.py:1045-1059`, `2345-2360`
- Evidence: `class_file_index` is built from `self._parsed` only, which in an incremental run holds just changed files, dependents and debt. The comment claims "changed or not". `base_file` therefore falls back to the child's own file.
- Failure scenario: editing `views.py` (`class V(BaseView)`, where `BaseView` lives in an unchanged `base.py`) rewrites the `extends` edge to `BaseView::views.py`, a node that does not exist. Overrides, inherited methods, inherited self-call resolution and blast radius through `extends` all go silent for that class until a full reindex.
- Remedy: fix. Build the index from the `code_graph_nodes` rows for class-like symbols (one query) and overlay the freshly parsed files.

### 9. Blast radius and symbol lookup ignore repository and owner
- Kind: bug
- Severity: medium
- Confidence: confirmed
- Where: `code_query.py:191-205`, `617-631`; MCP `server.py:1730-1734`; `schemas/code.py:217-219`
- Evidence: the owner segment of `split_symbol_key` is discarded. The query filters on name and `file_path` with no `repo_id`, then takes `.first()` with no `ORDER BY`. The MCP tool resolves by bare name across all repos with `.first()`.
- Failure scenario:
  - `run::src/main.py::Worker` may return `Scheduler.run`'s callers.
  - Two repos with `src/main.py` give an arbitrary repository's answer.
  - MCP `code_blast_radius("run")` silently picks one of many matching symbols.
- Remedy: fix. Add `repo_id` to `BlastRadiusRequest` and to `lookup_symbol`, honour the owner, and have MCP list candidates when more than one symbol matches.

### 10. MCP `code_symbol` probably raises on any hit (async lazy load of `s.file`)
- Kind: bug
- Severity: medium
- Confidence: plausible (settle by calling the tool against an indexed repo; no test exercises it with data)
- Where: `server.py:1636-1661`
- Evidence: the query selects only `CodeSymbol`. `CodeSymbol.file` is a default lazy many-to-one (`models/code.py:75`), so reading `s.file.file_path` on an `AsyncSession` should raise `MissingGreenlet`.
- Remedy: fix. Select `CodeFile.file_path` in the query, or delegate to `CodeQueryService.list_symbols`.

### 11. Unchanged dependent and debt files are re-embedded on every incremental run
- Kind: performance
- Severity: medium
- Confidence: confirmed
- Where: `code_pipeline.py:726-734,867-868,1743-1747,1827-1833`
- Evidence: up to 500 dependents plus up to 500 debt files join the changed set only to have their calls re-traced. Phase 03 skips them, but phase 12 re-embeds every parsed file. The `_apply_union_files` docstring acknowledges this.
- Failure scenario: a one-line change to a widely called utility re-embeds up to 1,000 unchanged files.
- Remedy: optimise. Embed only the files phase 03 actually rewrote, plus files with no chunk row under the active fingerprint.

### 12. MCP `code_search` returns nothing without an embedder, while REST answers from the keyword arm
- Kind: bug / doc-drift
- Severity: medium
- Confidence: confirmed for the door divergence; plausible for the read-only worker
- Where: `server.py:1578-1583` versus `code_query.py:72-146`
- Evidence: MCP returns a degraded empty result before calling the service. The service's `ILIKE` arm needs no LLM, and CLAUDE.md says code search answers on that arm on the read-only worker.
- Remedy: fix. Always call `search_code`; mark the reply degraded only as an annotation.

### 13. A transient fetch failure deletes the managed clone and re-clones it, with no claim held
- Kind: weak-assumption
- Severity: medium
- Confidence: confirmed (code path); the race requires timing
- Where: `repo_manager.py:504-519`, reached from the unclaimed fetch lane at `job_runners.py:116-130`
- Evidence: any `RuntimeError` from fetch or reset on a non-local repo leads to `rmtree` and a fresh clone. The fetch lane only reads `status`; it never claims.
- Failure scenario:
  - A network blip deletes the whole tree and re-downloads it. If the clone also fails, the tree stays missing.
  - A reindex that claims the repo during the clone window gets a diff error, falls back to a full pass, sees a partial tree, and `_find_removed_files` strips the graph data for every missing file.
- Remedy: fix. Re-clone only when the tree is actually corrupt (for example `git rev-parse` fails), not on a network error. Have the fetch lane take the claim (as `cloning`) for any rmtree or clone.

### 14. A file whose parse times out or raises is re-detected as drift on every tick
- Kind: weak-assumption
- Severity: medium
- Confidence: plausible
- Where: `code_pipeline.py:980-983,1016-1030` versus `code_reconcile.py:41-59,86-91`
- Evidence: the pipeline writes no `CodeFile` row for a file whose parse raised or timed out, but `_file_hash` still hashes it, so it always differs from the index.
- Failure scenario: a full pipeline run, including Leiden and a 60 s parse attempt, every poll interval, indefinitely.
- Remedy: fix. Record unparseable files with a marker row or a skip set keyed by hash.

### 15. Query-per-item loops in phases 03, 05 and 06
- Kind: performance
- Severity: medium
- Confidence: confirmed
- Where:
  - phase 03, `_store_graph`: `code_pipeline.py:2263-2430`, 2–3 single-row `INSERT`s per symbol, import, property and route
  - phase 05: `:1283-1291`, one `UPDATE` per file
  - phase 06: `:1451-1454` calling `heritage_resolver.py:203-252`, a BFS with 2 queries per ancestor for every unresolved `self.x()` call
- Evidence: phase 06 already batches its call-edge inserts with `jsonb_to_recordset`. Phase 07 loads the full `extends` and `has_method` maps once, but phase 06 does not reuse them.
- Failure scenario: roughly 60k+ round trips for a first index of about 22k symbols, plus thousands more in phase 06 for Python-heavy code.
- Remedy: optimise. Batch the `_store_graph` inserts per file, and resolve inherited calls from maps loaded once.

### 16. Phase 08 seeds every file's type environment with every symbol's return type, keyed by function name
- Kind: weak-assumption / performance
- Severity: low
- Confidence: confirmed
- Where: `code_pipeline.py:1346-1348,1615-1620`
- Evidence: the map is repo-global and last write wins, and every file's environment gets every entry: O(files × symbols), up to the 2,000-file cap.
- Failure scenario: a local variable named like any function (`config`, `client`) resolves to that function's return type in every file, producing confident (≥ 0.6) wrong member-call edges.
- Remedy: simplify. Seed only names imported into or defined in that file, or drop the seeding and measure the edge delta.

### 17. Leiden and process tracing rewrite the repo's whole community/process layer on every run, under non-deterministic keys
- Kind: design-critique / performance
- Severity: low
- Confidence: confirmed
- Where: `community_detector.py:191-256`, `process_tracer.py:73-87`
- Evidence: every run, including a one-file drift tick, deletes and re-inserts every `member_of` edge (about one per symbol) and every community and process node. Community keys embed the Leiden `comm_id`, which is not stable across runs.
- Failure scenario: about 20k dead tuples per run, and community node ids churn under the SPA's colour-by-community view.
- Remedy: optimise. Skip phases 09–10 when the call graph did not change, or move them to a post-index Tier-C refresh.

### 18. Property nodes are keyed by bare name and deleted together with the first owner's file
- Kind: bug
- Severity: low
- Confidence: confirmed
- Where: `code_pipeline.py:2362-2388,1952-1960`; consumed at `heritage_resolver.py:528-536`
- Evidence: the property key is the bare name, the first writer's `file_path` sticks, and `_delete_file_data` deletes nodes by that `file_path`.
- Failure scenario: reindexing `a.py` deletes a property node that `b.py`'s class shares, so `b.py`'s `has_property` edge dangles and its `accesses` edges vanish.
- Remedy: fix. File- and owner-qualify property keys.

### 19. Failure paths store unsanitised exception text; tokens sit in the git argv
- Kind: security
- Severity: low
- Confidence: confirmed (current git errors are already sanitised, so present exposure is likely nil)
- Where: `code_pipeline.py:541,573-576,584,602`; `repos.py:376,389`; `repo_manager.py:486-491,551-555`
- Evidence: `status_message`, `pipeline_failures.error_message` and the websocket error take raw `str(exc)`. The authenticated fetch URL puts the token in `/proc/<pid>/cmdline` for the length of the call.
- Remedy: fix. Route every stored or broadcast exception string through `_sanitize_url`. Pass credentials with `GIT_ASKPASS` or an `http.extraHeader` set through environment variables instead of the URL.

### 20. A local checkout's fetch lane fast-forwards whichever branch is checked out
- Kind: weak-assumption
- Severity: low
- Confidence: confirmed
- Where: `repo_manager.py:491-498`
- Evidence: fetch of `default_branch`, then `git merge --ff-only FETCH_HEAD`, with no check of which branch HEAD is on.
- Failure scenario: the operator's fresh feature branch is silently fast-forwarded to `origin/main`.
- Remedy: fix. Skip the merge unless `git symbolic-ref --short HEAD` equals `default_branch`.

### 21. Wiki: the config row is orphaned on repo delete, and the cache check is dead
- Kind: dead-code / bug
- Severity: low
- Confidence: confirmed
- Where: `wiki_generator.py:49-61,184-192`; `repo_manager.py:378-381`
- Evidence:
  - Nothing deletes the `wiki_{repo_id}` config row.
  - The only caller passes `force=True`, so the `_cached_at` comparison never runs.
  - That stamp is written before `last_indexed_at` advances anyway.
- Remedy: delete the row in `RepoManager.delete`; remove the `force` parameter and the cache branch.

### 22. `process_tracer` reads a `signature` property nothing writes
- Kind: dead-code
- Severity: low
- Confidence: confirmed
- Where: `process_tracer.py:139,166` versus `code_pipeline.py:2271-2277`
- Evidence: symbol node properties don't include `signature`, so the 1.4× framework-decorator multiplier never applies.
- Remedy: remove the input or write the signature onto the node.

### 23. `code_deriver` strips and rewrites every repo's assertions hourly, whether or not HEAD moved
- Kind: design-critique
- Severity: low
- Confidence: confirmed
- Where: `job_runners.py:236-280`; rationale at `code_deriver_job.py:28-39`
- Evidence: `last_indexed_commit` already provides the staleness signal the module's rationale says it lacks; a stamp compared against it (as `citation_reverify` does) would skip unchanged repos.
- Remedy: optimise. Optional at today's repository count.

### 24. `cancel_repo_task` does not check that the task belongs to the repository in the URL
- Kind: bug
- Severity: low
- Confidence: confirmed
- Where: `repos.py:637-655`
- Evidence: it cancels any task id, then marks the URL's repository `cancelled` if that repository is busy.
- Remedy: verify the task's `repo_id` before cancelling.

### 25. Doc and comment drift
- Kind: doc-drift
- Severity: low
- Confidence: confirmed
- Where and evidence:
  - `code_pipeline.py:38-41` says production uses `expire_on_commit=True`; `database.py:16` sets `False`.
  - `code_pipeline.py:87-89` says each progress label causes a Repositories refetch; the frontend no longer does (`websocket.ts:190-205`).
  - `repo_allowlist.py:7-9` says hints arrive over an "unauthenticated MCP door"; every MCP call now needs a key.
  - `CodeFile.last_commit_sha` is served on `CodeFileResponse` but never written by the pipeline, so it is always null.

## Removal candidates (ranked by lines saved and safety)

1. `services/named_bindings/wildcard_synthesis.py` (113 lines). No importer anywhere in backend, tests, scripts or frontend; it is mentioned only in `docs/superpowers/specs/2026-08-24-review-remediation.md`. Safe to delete.
2. The `Repository.files` and `CodeFile.symbols` relationships (`models/code.py:38,53`). No reader; removing them is the largest single performance win. Switch the two ORM-cascade deletes to SQL deletes first.
3. `TaskRegistry.get_all_running` (no caller) and `cleanup_completed` (never finds anything, because `_on_done` already pops finished tasks). About 25 lines.
4. The `CallResolver` keyword arguments `named_imports=` and `wildcard_imports=`. No caller passes them.
5. The `WikiGenerator.generate` `force` parameter and cache branch (about 11 lines).
6. `RepoManager.get_auth_token`, which only tests use.
7. `_implements_split`'s `implements_list` return value, which is computed and discarded.
8. The `CodeFile.last_commit_sha` column. Needs a new Alembic revision; lowest priority.

## Checked and found sound

- **Index debt is never dropped.** Overflow is committed before later phases can fail, and a claimed batch is removed only after a successful run. A failed settle re-offers the batch, duplicating work but losing nothing. A forced-full run settles the whole queue correctly, and the union-only early exit can only settle vanished entries. Debt files only add edges.
- **Debt and HEAD.** An unchanged HEAD with queued debt runs correctly, matching CLAUDE.md.
- **`claim_for_indexing`** is one atomic `UPDATE … RETURNING` used by every door, so two runs on one repo cannot both proceed. (#1 is about release, not acquisition.)
- **`entity_merge`.** A stranded relation raises inside the savepoint, and the caller logs and continues. The survivor rule, relation fold, fact rename and fold, fact-source move-not-copy, expire-not-delete and the keyset cursor all match CLAUDE.md.
- **Fusion identity.** `(repo_id, file_path, line_start)` is consistent across both arms, so they do fuse.
- **Path containment.** `_parse_one` resolves strictly and rejects escapes, symlinks included; union canonicalisation and classification re-check containment.
- **Git argument injection.** Branches can't start with `-` or contain whitespace. URL schemes are limited to https/http/ssh/git with a host, so no `ext::` or `file://`. Commit shas are regex-checked. No attacker-controlled value can reach an option position, even without `--`.
- **SSRF.** The auto-provision allowlist is closed by default and parse-only. Operator-entered URLs can name internal hosts, which is accepted for an admin surface that requires login.
- **Webhook authentication.** An `admin`-scoped key, checked before the handler runs, and every delivery is journalled. GitHub-native webhooks can't send a Bearer header, so the door suits custom senders only. That is a design limit, not a hole.
- **Credentials.** `_run_git` sanitises stderr and argv, and the clone scrubs the token from `.git/config`.
- Also checked: `citation_reverify`, `git_head`, `prepare_reindex`, the enrichment retry cap, and the wiki's bounded concurrency.

## Not covered

These were opened only partially or skimmed:
- `code_parser.py` lines 374–1100 (extraction helpers; the parser does no file I/O).
- `call_resolver.py` past line 140.
- `type_env.py`, `suffix_index.py`, `symbol_table.py`.
- The `import_resolvers` and `named_bindings` modules other than `wildcard_synthesis` (grep only).
- `git_forges.py` and `api/routes/git_accounts.py`.
- `entity_anchoring.py` (structure only).
