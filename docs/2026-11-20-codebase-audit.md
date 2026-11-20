# Codebase audit — 2026-11-20

Audited at `6db8cb5d` (master). Changes made during the audit sit uncommitted
on branch `audit/2026-11-20-review`. Scope was the whole tree: `backend/`,
`frontend/`, `extension/`, `sdks/`, `scripts/`, CI and the deployment
artefacts.

## Method, and what it does not cover

Eleven read-only reviewers each took one disjoint track and read its core
files in full. Their findings are in `docs/2026-11-20-codebase-audit/`, one
file per track, with every finding carrying file and line. Each file ends
with the modules its reviewer did not open; treat those as unreviewed.

Beside the reviewers, three mechanical passes ran over the whole tree:

- an import-reachability graph of `backend/app` from the real entry points;
- an import graph of `frontend/src` from `main.tsx` and the routes, checked
  against `knip`;
- `vulture` over `backend/app`, with every hit cross-referenced against
  tests and scripts.

Production state was read directly from this host's database, which is a
clone of 192.168.0.199 taken on 2026-11-18, and one query was run against
the live `.199` instance over MCP.

A finding is marked **verified** below when it was re-read in the code, or
reproduced by a failing test, after the reviewer reported it. Everything
else is the reviewer's own confirmation and has not been checked twice.

## 1. Production incident found during the audit

**The embedding server has been unreachable since 2026-11-03, and nothing
reported it.** Verified against production data and the live instance.

- `llm_providers.ollama` points at `http://192.168.0.196:11434`. From this
  host and from inside the app container the address answers *no route to
  host*.
- Every embedding call since 2026-11-03 failed: 3,802 calls, none
  successful. The last successful day was 2026-10-29. A failed call takes
  about 29 seconds on average, spent in the client's connect retries.
- **Search.** Any `memory_search` with a query raised instead of answering.
  Confirmed on `.199` on 2026-11-20: a query search returned *Error
  executing tool memory_search* while a tag-only search answered. Chat and
  `knowledge_search` use the same path.
- **Capture.** 53 memories captured between 2026-11-03 and 2026-11-18 have
  no vector, no entity graph and no classification. Their `memory_buffer`
  rows sit in `error` with *pipeline failed at content_embedding*.
- **Jobs.** `relation_embedding_refresh` and `block_embedding_refresh`
  failed on every hourly run in the retained 14 days of history (239 and
  238 errors, no success).
- **Why nobody saw it.** `buffer_flush` records `ok` for a tick whose rows
  all failed. The `pipeline_failures` rows carry the message *Unknown
  error*. Whether job-failure notifications are configured on `.199` was
  not checked.

What this pass changed: search now answers on the keyword arm when the
query embed fails (section 2). What is still owed, and is not a code
change:

1. Restore or repoint the embedding provider on `.199`.
2. Requeue the 53 `error` rows from Activity → buffer triage once the
   embedder answers. Nothing requeues them automatically.
3. Turn on job-failure notifications in Settings. Production has no
   notification settings row, so the alert channel that exists is off.

The outage is now visible where it was not (section 2): a flush tick whose
every capture failed is a failed run, the failure row carries the real
reason, and a configured notification arrives once per outage.

## 2. Fixed in this pass

Each fix has a test that failed before the change.

| Fix | Where | Test |
|---|---|---|
| Search degrades to the keyword arm when the query embed fails, reports `semantic_failed`, and does not redial the embedder for 60 s | `services/hybrid_search.py` | `tests/test_hybrid_search_degradation.py` |
| A failed extraction no longer replaces a memory's existing graph with nothing (B1-1) | `services/pipeline.py` | `tests/test_pipeline_savepoints.py` |
| `article_synthesis` wraps its project cursor; it had been parked on the last project and visiting nothing (B3b-1) | `services/dream_jobs.py` | `tests/test_dream_jobs.py` |
| Merging memories demotes what the source superseded, and refuses a self-merge that used to delete the memory (B1-2) | `services/memory.py`, `api/routes/memories.py` | `tests/test_memory_merge.py` |
| Block spans no longer shift after a form feed, vertical tab, U+0085 or U+2028 (B5-1) | `services/document_parsers.py` | `tests/test_document_parsers.py` |
| A long chat keeps its newest turns when the prompt budget runs out (B2-3) | `services/chat.py` | `tests/test_chat_history_budget.py` |
| A repository left `indexing` or `cloning` by a restart is released at boot (B4-1, B6-1) | `services/repo_manager.py`, `main.py` | `tests/test_repo_indexing_modes.py` |
| Loading a repository no longer loads all its files and symbols; deletes rely on the database cascade (B4-2) | `models/code.py` | `tests/test_repository_relationships.py` |
| A flush tick whose every claimed capture failed records `error`, not `ok` | `services/job_runners.py` | `tests/test_buffer_flush_runner.py` |
| An embedding failure's reason reaches the failure row instead of "Unknown error" | `services/pipeline.py` | `tests/test_pipeline_phase1.py` |
| Job-failure notifications escape the error text and are sent once per repeating failure (B6-11) | `services/notifications.py`, `services/job_registry.py` | `tests/test_notifications.py`, `tests/test_job_registry.py` |
| `ppr_snapshot` and `relation_embedding_refresh` skip their tick while their rank arm is off (B2-5) | `services/job_runners.py` | `tests/test_graph_arm_jobs.py` |
| The code indexer lists files through git, so ignored files are no longer indexed, embedded or served by code search (B4-3) | `services/code_pipeline.py`, `services/reindex_files.py` | `tests/test_reindex_files.py` |
| Mermaid export stays valid past 26 steps and escapes names (F1-3) | `frontend/src/demo/explore.ts` | `demo/__tests__/explore.test.ts` |
| Saving LLM settings reports a refused save instead of "Saved" (F2-1) | `frontend/src/features/settings/use-llm-tab-binding.ts` | `settings-llm.real.test.tsx` |

Notes on three of them:

- **B1-1.** `ExtractionService.extract` never raises. An outage, a 429 and
  an unparseable reply all return an empty result marked `_error`, which
  the pipeline labelled `partial` and then wrote. On a re-extraction that
  stripped the prior graph, emptied `technologies` and withdrew the
  memory's fact sources. The existing test stubbed `extract` to raise,
  which production cannot do.
- **B3b-1.** Production confirms it: `article_synthesis_state` held
  `telegram-notify-export`, the last of 28 projects, and the job's 11 runs
  in 14 days totalled 2 seconds.
- **B5-1.** Documents filed before the fix keep their old spans until
  reparsed with `backend/scripts/reparse_documents.py`. Production holds no
  documents today, so nothing is owed there.

## 3. Removed in this pass

8,167 lines across 40 files, each proven to have no live importer.

- **Backend, 1,555 lines.** `services/entity_registry.py`,
  `entity_detector.py` and `dialect.py` (MemPalace ports that only imported
  each other); `ml_seed.py` (seeds the dropped `ml_profiles` table);
  `named_bindings/wildcard_synthesis.py`; the two unused `Protocol` modules
  `named_bindings/base.py` and `import_resolvers/base.py`;
  `schemas/pipeline_failures.py`; the placeholder `app/db/` package.
- **Frontend, 4,246 lines in 25 files.** The superseded code-graph
  renderer and its panels in `features/graph` (`code-graph-renderer`,
  `code-analysis-panel`, `knowledge-graph-renderer`, `process-flow-modal`,
  `process-panel`, `code-inspector-panel`, `code-graph-search`,
  `code-processes`, `node-circle-bordered-program`) with the tests that
  covered only them; `memory-command-palette`; `lib/form-resolvers`,
  `lib/source-colors`; `components/placeholder-tabs`; `hooks/useApi`; the
  unused `index.ts` and `schemas.ts` of `features/jobs` and
  `features/settings`. Also the dependency `graphology-layout-noverlap` and
  an 18-line CSS block, whose only user was the deleted renderer.
- **Scripts, 2,366 lines.** `scripts/eval_*.js` and their two report files,
  left from an earlier review and hard-coded to a Windows path.

## 4. Open findings, most severe first

The reviewers graded 15 findings high, 83 medium and 122 low; two of the
highs are one finding seen from two tracks, so 14 distinct. Section 2 fixed
eight of those and several mediums. The six open highs follow.

### High

- **F3-1, bug.** Sending in a second chat conversation aborts the first
  one's stream, and the server saves an answer only when its stream
  completes, so the first answer is lost.
- **F1-1, bug.** Verified. The Edit Repository dialog cannot save a
  repository cloned from a URL: its schema requires a `path`, and a cloned
  repository has none. Recorded as open in a plan dated 2026-08-24.
- **F1-2, performance.** The memory graph rebuilds its 3D data in 2D view
  with an O(n²) lookup, stalling the tab at the 50,000-node setting.
- **B3a-1, bug, plausible.** `fact_lift` and re-extraction can interleave
  so a fact keeps a source the memory no longer asserts, inflating the
  distinct-origin count that decides promotion. Needs a two-session test
  to settle.
- **P1-1, bug.** The browser extension's auto-capture stores every partial
  state of a streaming reply as its own memory.
- **P1-2, security.** `ci.yml` runs on `pull_request` and the e2e jobs
  always use the self-hosted LAN runner. The repository is public, so a
  fork's pull request can run code on that runner unless fork approval is
  required. Check the repository's fork-approval setting.

### Medium, grouped

- **Auth and exposure.** Login runs bcrypt on the event loop and checks the
  lockout before an `await`, so concurrent attempts exceed five guesses
  (B6-2). The CORS fallback grants credentialed access to
  `localhost:3000` and `:5173` (B6-6, verified). SSH backup `user` and
  `host` reach the `ssh` argv unvalidated (B6-7). Every MCP request pays a
  fresh bcrypt, about 167 ms (B6-8).
- **Read-only worker.** MCP `memory_reason`, `memory_overview` and
  `document_search` (B6-3) and the REST reprocess and failure-retry routes
  (B1-7) are not refused there, so the worker can spend on a provider.
- **Door parity.** Chat and `knowledge_search` ignore
  `hybrid_search_enabled`, `reranker_enabled` and the confidence weight
  that `memory_search` honours (B2-2). MCP `code_search` returns nothing
  without an embedder while REST answers on its `ILIKE` arm (B4-12).
- **Writes acknowledged before they are durable.** `get_session` commits
  after the response is sent, so several config routes answer 200 first
  (B6-5).
- **Concurrency.** Phase 5 writers lock shared entity rows in extraction
  order (B1-3). The supersession UPDATE has no `status='active'` predicate
  (B1-4). Tier-C ticks hold fact locks for the whole tick (B3a-6). The
  attachment upload streams 50 MB inside the global lifecycle lock (B5-3).
- **Queries that scan.** `:id = ANY(memory_ids)` cannot use the GIN index;
  it should be `memory_ids @> ARRAY[...]` (B1-5). The `sources_changed`
  drain has no index and runs every two minutes (B3a-7). Per-file deletes
  in the code pipeline scan the repository's whole edge table (B4-5).
- **Silent staleness.** A document block edit keeps the old vector when its
  embed fails (B5-2). One failed embed loses a file's code chunks until the
  file changes again (B4-6). `git diff` parsing breaks on non-ASCII paths
  (B4-7).
- **Frontend data loss.** The documents block editor discards typed text on
  any refused write (F3-2). Hygiene-queue selections survive a project
  change, so a prune can retire rows that are not on screen (F3-3). Flags
  dialogs close before the write lands (F2-7).
- **Release and CI.** A cancelled `tag` job still lets `github-release`
  create the tag on master's tip (P1-3). `numpy` is imported but undeclared
  (P1-4). `scripts/start_dev_server.sh` runs `alembic upgrade head` against
  the default port 5432, which is production on this host (P1-10,
  verified).

## 5. Redundant or over-built for the current setup

Production today: 4,840 memories from one operator's coding clients, 9,875
facts, no documents, no indexed code, no chat conversations, no articles.
**All 9,875 facts are `candidate`; none has ever been promoted.** That is
the context for this ledger. Each item is named in `CLAUDE.md` as contract.

**Rulings.** The owner delegated these on 2026-11-20. The rule applied: gate
or remove what has no reader today and costs something on every tick; keep
what is a safety rail, what an open roadmap item still needs, and anything
whose removal needs a schema revision or a dependency relock, since those
are the two changes most able to hurt a populated production database.

- **Gated.** `ppr_snapshot` and `relation_embedding_refresh` now skip while
  their arm is off. The code, tests and tables stay, so arming an arm is
  still a flag flip.
- **Removed.** The test-only `ProcessingPipeline._apply_rank_fusion_factor`.
- **Kept as it is.** The LLM `contradiction_scan`: its tests pin what a
  refused run reports, and it costs 0.6 seconds every six hours in
  production. The bar floors and licences: they are the guard against
  loosening a threshold to make a run pass. The provider leases: correct,
  and the refactor that would retire them touches about 40 call sites.
- **Kept, removal recommended next.** `triple_embeddings.py`, the
  `stated_expiry` arm and `blocks.search_vector` each need an Alembic
  revision that drops something. The PDF parser needs a lock regeneration.
  Each is safe in principle and should ship alone, tested against a
  restored backup.
- **Left for the owner.** `classifier_kind=local`, the `inject_*` trio,
  the context-boost half of `rank_fusion` and the demo views are product
  decisions, not dead code.

| Mechanism | What runs in production | Cost to keep | Removal forfeits |
|---|---|---|---|
| `ppr_snapshot` and `relation_embedding_refresh` jobs with the PPR and dual-level arms (B2-5) | Gated in this pass. Before it, both ran hourly regardless of their flags; the relation job cost 1,200 or more embeds a day and holds a 130 MB partition | About 1,050 app lines, 1,570 test lines, two jobs | Flipping the flags without new code |
| LLM `contradiction_scan` (B3a-D1, B3a-2) | Drains the same 20 events every six hours, then is refused by the unqualified judge, and writes duplicate journal rows | About 2,700 lines of code and tests, one job, two columns, a route | Contradiction surfacing once a judge is qualified |
| `triple_embeddings.py` (B3a-5) | Nothing. No production caller; its table is empty | 461 lines, a 647-line test, an empty table and HNSW index per embedder | The deferred vector arm of the scan above |
| `knowledge_triples.stated_expiry` arm (B3a-4) | Runs every two minutes and can never match: the column has no writer | The arm, a partial index, merge logic, a test | Nothing |
| Bar floors, licences and clamps (B3a-D3) | Resolve to defaults on every recompute | About 720 backend lines, a settings form, three config rows | Loosening a threshold without a deploy |
| `inject_watch`, `inject_fill`, `inject_block` (B2-11) | Reached only by tests, so the Distribution tab's budget and watch switch control nothing | 550 lines, 937 test lines | The unbuilt injection feature |
| Context boost in `rank_fusion` and `community_injection_enabled` (B2-4) | No door passes a declared context; the flag has no reader | About 260 lines, a counter that is always 0, a UI switch | Nothing today |
| LLM provider leases (B2-10) | Correct, and exist only to drain an HTTP client that is vendor-neutral | About 40 wrap sites | Nothing, if one client lives for the process |
| `classifier_kind=local` (B1-15) | Cannot run: torch is not in `requirements.lock`, so it silently falls back to the LLM classifier | About 300 lines, three test files | The in-process classifier |
| PDF parser (B5-11) | Unreachable: `content` is `str` on both doors | `pdfplumber`, `pdfminer-six`, `pillow`, `pypdfium2` in the image | PDF ingest, which is a designed 422 |
| `blocks.search_vector` and its GIN index (B5-6) | No reader; every block write pays `to_tsvector` and index maintenance | A column and an index | Nothing |
| Demo views parallel to the real ones (F1-22) | Demo mode only | About 3,400 lines | The demo |

Smaller removals with no ruling needed, not done in this pass:
about 18 unused hooks in `frontend/src/hooks/api` (F2-10); unused auth code
(F2-11); test-only exports listed in F1-9; `ingest_documents` and four
helpers with only test callers (B5-12); the derivation contradiction arm
in `memory_dream` (B3b-10); five broken seed scripts and
`publish_production_models.sh`, which changes into a deleted directory
(P1-11, P1-12); `frontend/nginx.conf`, used by no build path (P1-19).

## 6. Weak assumptions

- **Nothing alerts.** Section 1 ran 17 days unseen. A job that fails every
  run, a buffer whose rows all fail and a provider that never answers each
  record `ok` or a row nobody is shown.
- **`lucide-react` is not declared.** 152 files import it and it arrives
  only as a dependency of `darkraise-ui`. A `darkraise-ui` release that
  drops or bumps it breaks the build.
- **`events` partitions are created one month ahead by a job the UI can
  disable** (B6-20). With it off, strict journal writers fail after a
  month.
- **`min_interval_seconds` is persisted on first save** (B6-9), so raising
  a job's floor in code never reaches an existing install.
- **`document_revisions` has no retention** (B5-7): a full copy up to 1 MB
  per content-changing put.
- **Job state is rewritten into `config` on every tick** (B6-D4), about
  29,000 updates a day on a host where autovacuum never runs.

## 7. UI and UX consistency

- **Settings has five save models** (F2-5): a dialog that closes at once,
  a dialog with no error path, a dialog that stays open until the save
  lands, an inline form with a Save button, and save-on-blur. It also has
  three ways of showing a load failure and three confirmation styles.
- **Empty versus failed.** Code Graph and Wiki show "No repositories
  indexed yet" while loading and after an error (F1-5). The project
  switcher says "No project holds anything yet" when its load fails
  (F2-18). The LLM tab shows fixture values as if real when its load fails
  (F2-6).
- **Session end.** The app never calls `/auth/refresh`, so every session
  ends with a full reload after 24 hours, and both editors lose in-memory
  drafts (F2-9, F3-4). The WebSocket ignores the server's session-expired
  close and retries forever (F2-3).
- **Library reuse.** The pager is hand-written twice although
  `darkraise-ui` ships `pagination` (F3-9). Copy Mermaid uses
  `navigator.clipboard`, which is undefined on the plain-HTTP deployment,
  while three other screens use the library's `clipboard` (F1-11).
- **Demo mode still calls the API** from Settings → LLM (F2-4).

## 8. Document drift found

`CLAUDE.md` was corrected where this pass changed behaviour. These
statements are still wrong and were left for the owner:

- "`groundedness_gate` … stays closed: no article may be served labelled
  grounded": the article surfaces gate on `article_claim_gate`, which opens
  on the minted entailment record (B3b-5).
- "There are no `LLM_*` env vars": `config.py` still accepts them as the
  fallback (B6-22).
- `CONTRIBUTING.md` describes the release model that tags publish; a push
  to master releases (P1-6).
