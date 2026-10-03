# Comprehensive Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: dr-superpowers:subagent-driven-development. Steps use checkbox syntax for tracking.

**Goal:** Resolve all 26 independently validated review items with behavioral regressions and independent review.

**Status:** Implementation complete and merged into local `master` at `a8284309` on 2026-10-03. All nine tasks and 26 findings accepted by independent reviewers; merge-gate floor is GREEN and post-merge backend 7,947 passed/26 skipped, frontend 1,981 passed. This machine is redeployed and healthy on local image `1fd43c8c`, with backend and served SPA artifact identity verified. Existing frontend lint debt remains. Evidence: docs/planning/reviews/2026-10-03-comprehensive-review-remediation.md. Nothing is pushed remotely.

**Integration authorization:** On 2026-10-03 the owner additionally requests committing the fixes, merging into local `master` and redeploying this machine. Remote Git/image pushes, releases and remote-instance changes remain unauthorized.

**Architecture:** Preserve existing service boundaries and public contracts. Repair end-to-end invariants with shared transaction/resource lifetime coordination and scope-aware identities; fix frontend recovery and ownership at the state boundary.

**Tech Stack:** FastAPI, async SQLAlchemy/PostgreSQL/pgvector, React, TanStack Query, Vitest, pytest, Chrome MV3.

**Spec:** docs/superpowers/specs/2026-10-03-comprehensive-review-fixes.md

**Host:** codex
**Routing policy:** codex-v3
**Plan review:** AMEND resolved on 2026-10-03; executability 17/20, coherence 18/20, coverage 20/20, assumptions 18/20. Added acquisition-boundary leasing and cleanup-first reference validation.
**Final judge:** human-pinned codex gpt-6.1-sol / xhigh; independently verify all 26 findings and review-fix deltas.
**Execution:** subagent — codex gpt-6-sol / high — explicitly requested by owner; task pairs follow native rubric.

## Global Constraints

- Implementation work remains on `fix/comprehensive-review`; the subsequent owner authorization permits staging, committing, merging into local `master` and deploying this machine. No remote push, publication or release is authorized.
- Tests never target production or live providers. The authorized local deployment permits production backups, metadata/health checks and application restart; backend tests remain on dedicated development databases on port 5433.
- Never edit `0001_baseline.py`; avoid schema changes when compatible locks/version checks suffice. Any necessary migration must preserve populated data and requires separate review.
- Keep exactly one runtime worker. Existing provider feature gates, capture identities, append-only journals and fingerprint partitions remain binding.
- Use `apply_patch` for file changes. Do not add inline code comments or one-letter identifiers. Follow scoped repository instructions and existing UI components.
- Agents own disjoint write sets; Task 6 starts after Task 1 because both touch code_pipeline.py. No agent edits CLAUDE.md, the review report, plan, register, or controller ledger; controller reconciles documentation.
- Regression tests must demonstrate the failing behavior before implementation where executable. Concurrency correctness uses production entry points and transaction barriers, not only source scans.


## Contracts

- C1: Database fixtures use per-agent `darkmem_test_2..5` and their guarded private cutover derivatives on development PostgreSQL at 127.0.0.1:5433; no concurrent processes share a lane. The documented merge gate separately owns the development `darkmem_bench` harness database, never production or a pytest lane.
- C2: Task 1 and Task 6 share code_pipeline.py sequentially. Task 5 owns repositories/graph.py while Task 7 owns services/graph.py.
- C3: Task 4 owns block/page/attachment mutations and embedding code. Other tasks consume their existing interfaces without editing those files.
- C4: The controller owns CLAUDE.md updates, register status, report qualification corrections and the execution ledger. Workers propose exact documentation changes in their report.
- C5: Native review restrictions are instruction-only; review after a write wave settles, snapshot approved files before/after, and verify every review did not mutate the repository.

## Assumptions (evidence)

- User authorized implementation on the branch in this conversation and subsequently instructed verification/retry/resume; no additional design approval gate is needed for reversible scoped fixes.
- Development Postgres was started alone on 2026-10-03. Production remains port 5432/8000. Dedicated test lane connectivity and existence are verified before DB tests.
- No execution ledger existed for these findings; branch and reviewed HEAD were verified on 2026-10-03. Tasks begin from uncommitted reviewed base.
- Behavioral implementation details are selected by assigned implementers under the explicit requirements below and independently reviewed; no full implementation transcription is required.

## Task index

1. Repository ingestion boundaries
2. Note draft recovery
3. Verified backup preservation
4. Document and attachment concurrency safety
5. Memory and knowledge workflow correctness
6. Incremental code convergence and search identity
7. Session and model resource lifetimes
8. Browser auto-capture execution
9. Document, graph and chat interaction correctness

---

### Task 1: Repository ingestion boundaries

**Files:**
- Modify/Test: `backend/app/services/code_pipeline.py`
- Modify/Test: `backend/app/services/repo_manager.py`
- Modify/Test: `backend/app/services/reindex_files.py`
- Modify/Test: `backend/tests/test_code_pipeline.py`
- Modify/Test: `backend/tests/test_repos.py`
- Create regression files in the matching test directory when the named existing test is absent; record exact new paths before writing.

**Interfaces:**
- Consumes: existing service signatures and C1–C5.
- Produces: corrected behavior for register items 1, 2 with preserved external shape.

**Items:** 1, 2
**Implementer:** codex gpt-6-astra / medium
**Evaluation:** files=1, spec=1, coupling=1, risk=2; weighted routing score=7
**Assignment source:** rubric

**Requirements:** Reject escaping file targets at the actual parser read boundary, preserving safe existing explicit-path checks. Redact all URL userinfo for every forge in command errors, logs and timeout paths. Prove an external symlink cannot reach parsing or embeddings and synthetic GitLab tokens cannot survive diagnostics.

- [x] Trace the actual caller and failing behavior; inspect the relevant business contract and existing tests.
- [x] Add behavioral regression tests for each requirement; run them before editing implementation and record the expected failures.
- [x] Implement the smallest compatible correction in the approved write set, preserving existing contracts and deployed data.
- [x] Run covering regressions and adjacent affected tests with C1 isolation or frontend maxWorkers=1; record commands and outcomes.
- [x] Self-review the diff and write a report containing changed paths, each finding's resolution, verification evidence, assumptions and uncovered limitations. Do not commit.
- [x] Independent native review accepts the change; fix any confirmed gaps and rerun the covering tests.

### Task 2: Note draft recovery

**Files:**
- Modify/Test: `frontend/src/features/notes/lib/page-sync.ts`
- Modify/Test: `frontend/src/features/notes/use-page-sync.ts`
- Modify/Test: `frontend/src/features/notes/page-pane.tsx`
- Modify/Test: `frontend/src/features/notes/__tests__/page-sync.test.ts`
- Modify/Test: `frontend/src/features/notes/__tests__/use-page-sync.test.tsx`
- Create regression files in the matching test directory when the named existing test is absent; record exact new paths before writing.

**Interfaces:**
- Consumes: existing service signatures and C1–C5.
- Produces: corrected behavior for register items 4 with preserved external shape.

**Items:** 4
**Implementer:** codex gpt-6-astra / medium
**Evaluation:** files=1, spec=1, coupling=1, risk=2; weighted routing score=7
**Assignment source:** rubric

**Requirements:** Distinguish dirty desired state from stopped retry state; retain refused drafts across page/route navigation with explicit discard/recovery. Keep unload protection alive while module-level drafts or uploads remain after editor unmount. Test conflict, validation refusal, reopen and route-level unload protection.

- [x] Trace the actual caller and failing behavior; inspect the relevant business contract and existing tests.
- [x] Add behavioral regression tests for each requirement; run them before editing implementation and record the expected failures.
- [x] Implement the smallest compatible correction in the approved write set, preserving existing contracts and deployed data.
- [x] Run covering regressions and adjacent affected tests with C1 isolation or frontend maxWorkers=1; record commands and outcomes.
- [x] Self-review the diff and write a report containing changed paths, each finding's resolution, verification evidence, assumptions and uncovered limitations. Do not commit.
- [x] Independent native review accepts the change; fix any confirmed gaps and rerun the covering tests.

### Task 3: Verified backup preservation

**Files:**
- Modify/Test: `backend/app/services/backup_ship.py`
- Modify/Test: `backend/tests/test_backup_ship.py`
- Create regression files in the matching test directory when the named existing test is absent; record exact new paths before writing.

**Interfaces:**
- Consumes: existing service signatures and C1–C5.
- Produces: corrected behavior for register items 3 with preserved external shape.

**Items:** 3
**Implementer:** codex gpt-6-astra / medium
**Evaluation:** files=1, spec=1, coupling=1, risk=2; weighted routing score=7
**Assignment source:** rubric

**Requirements:** Failed checksum verification must never count a failed dump or attachment artifact as a retention survivor, on this or a later run. Quarantine/remove failed artifacts safely or restrict retention to verified artifacts. Preserve the previous verified destination copy at keep=1 and preserve destination independence and the separate systemd producer.

- [x] Trace the actual caller and failing behavior; inspect the relevant business contract and existing tests.
- [x] Add behavioral regression tests for each requirement; run them before editing implementation and record the expected failures.
- [x] Implement the smallest compatible correction in the approved write set, preserving existing contracts and deployed data.
- [x] Run covering regressions and adjacent affected tests with C1 isolation or frontend maxWorkers=1; record commands and outcomes.
- [x] Self-review the diff and write a report containing changed paths, each finding's resolution, verification evidence, assumptions and uncovered limitations. Do not commit.
- [x] Independent native review accepts the change; fix any confirmed gaps and rerun the covering tests.

### Task 4: Document and attachment concurrency safety

**Files:**
- Modify/Test: `backend/app/services/block_embeddings.py`
- Modify/Test: `backend/app/services/block_verbs.py`
- Modify/Test: `backend/app/services/page_attachment_cleanup.py`
- Modify/Test: `backend/app/services/page_attachments.py`
- Modify/Test: `backend/app/services/page_import.py`
- Modify/Test: `backend/app/services/page_door.py`
- Modify/Test: `backend/app/services/block_embedding_refresh.py`
- Modify/Test: `backend/tests/test_block_embeddings.py`
- Modify/Test: `backend/tests/test_page_attachment_cleanup.py`
- Modify/Test: `backend/tests/test_notion_import.py`
- Create regression files in the matching test directory when the named existing test is absent; record exact new paths before writing.

**Interfaces:**
- Consumes: existing service signatures and C1–C5.
- Produces: corrected behavior for register items 5, 7, 26 with preserved external shape.

**Items:** 5, 7, 26
**Implementer:** codex gpt-6-astra / xhigh
**Evaluation:** files=1, spec=1, coupling=1, risk=3; weighted routing score=9
**Assignment source:** rubric

**Requirements:** Reject stale embedding results atomically with the vector write using current block text and mutation-compatible locks, without changing existing schema. Coordinate attachment-reference writers and cleanup through one shared transaction-scoped locking protocol through commit, including full page replacement/import and all block mutation paths, with consistent page/root lock order. Revalidate references after acquiring the lock so cleanup-first execution cannot save an already-collected attachment URL; cleanup filesystem work must not invalidate a successfully committed reference. Preserve placed files whenever commit outcome is uncertain, including cancellation/connection errors; safely clean files only when noncommit is established. Add real two-session barriers covering both lock acquisition orders plus controlled provider completion and uncertain-commit tests.

- [x] Trace the actual caller and failing behavior; inspect the relevant business contract and existing tests.
- [x] Add behavioral regression tests for each requirement; run them before editing implementation and record the expected failures.
- [x] Implement the smallest compatible correction in the approved write set, preserving existing contracts and deployed data.
- [x] Run covering regressions and adjacent affected tests with C1 isolation or frontend maxWorkers=1; record commands and outcomes.
- [x] Self-review the diff and write a report containing changed paths, each finding's resolution, verification evidence, assumptions and uncovered limitations. Do not commit.
- [x] Independent native review accepts the change; fix any confirmed gaps and rerun the covering tests.

### Task 5: Memory and knowledge workflow correctness

**Files:**
- Modify/Test: `backend/app/services/fact_provenance.py`
- Modify/Test: `backend/app/services/fact_lift.py`
- Modify/Test: `backend/app/services/memory.py`
- Modify/Test: `backend/app/services/pipeline.py`
- Modify/Test: `backend/app/repositories/graph.py`
- Modify/Test: `backend/app/services/supersession.py`
- Modify/Test: `backend/app/services/hybrid_search.py`
- Modify/Test: `backend/tests/test_fact_provenance.py`
- Modify/Test: `backend/tests/test_supersession.py`
- Modify/Test: `backend/tests/test_retrieval_trace.py`
- Modify/Test: `backend/tests/test_graph_scale.py`
- Modify/Test: `backend/tests/test_merged_extraction.py`
- Modify/Test: `backend/tests/test_usage_attribution.py`
- Create regression files in the matching test directory when the named existing test is absent; record exact new paths before writing.

**Interfaces:**
- Consumes: existing service signatures and C1–C5.
- Produces: corrected behavior for register items 6, 8, 9, 10, 11 with preserved external shape.

**Items:** 6, 8, 9, 10, 11
**Implementer:** codex gpt-6-astra / xhigh
**Evaluation:** files=1, spec=1, coupling=1, risk=3; weighted routing score=9
**Assignment source:** rubric

**Requirements:** Lock affected facts consistently before withdrawing/counting sources, preserving facts gaining a different source concurrently. Apply tags_all on every semantic door. Make traced and ordinary candidate generation/ranking agree for all supported flags, including hybrid disabled, with no activation of dormant arms. Filter unified entity edges by selected-memory assertion provenance. Reconcile same-batch supersession after relevant writes become visible in (created_at,id) order. Prove transaction interleavings and traced/untraced parity.

- [x] Trace the actual caller and failing behavior; inspect the relevant business contract and existing tests.
- [x] Add behavioral regression tests for each requirement; run them before editing implementation and record the expected failures.
- [x] Implement the smallest compatible correction in the approved write set, preserving existing contracts and deployed data.
- [x] Run covering regressions and adjacent affected tests with C1 isolation or frontend maxWorkers=1; record commands and outcomes.
- [x] Self-review the diff and write a report containing changed paths, each finding's resolution, verification evidence, assumptions and uncovered limitations. Do not commit.
- [x] Independent native review accepts the change; fix any confirmed gaps and rerun the covering tests.

### Task 6: Incremental code convergence and search identity

**Files:**
- Modify/Test: `backend/app/services/code_pipeline.py`
- Modify/Test: `backend/app/services/code_query.py`
- Modify/Test: `backend/app/services/job_runners.py`
- Modify/Test: `backend/tests/test_index_debt.py`
- Modify/Test: `backend/tests/test_code_pipeline.py`
- Modify/Test: `backend/tests/test_code_search.py`
- Modify/Test: `docs/wiki/usage-guide.md`
- Create regression files in the matching test directory when the named existing test is absent; record exact new paths before writing.

**Interfaces:**
- Consumes: existing service signatures and C1–C5.
- Produces: corrected behavior for register items 12, 13, 14 with preserved external shape.

**Items:** 12, 13, 14
**Implementer:** codex gpt-6-astra / medium
**Evaluation:** files=1, spec=1, coupling=1, risk=2; weighted routing score=7
**Assignment source:** rubric

**Requirements:** Resolve imports against the complete surviving repository file universe while retaining incremental work subsets and unchanged symbol/binding metadata. Include repo_id in both search fusion identities. Preserve the current HEAD-trigger/opt-in policy for recurring indexing: document explicitly that debt drains on later pipeline runs/manual reindex, expose existing debt information accurately, and test retention/manual convergence. Do not silently add a recurring trigger for qualified finding 13.

- [x] Trace the actual caller and failing behavior; inspect the relevant business contract and existing tests.
- [x] Add behavioral regression tests for each requirement; run them before editing implementation and record the expected failures.
- [x] Implement the smallest compatible correction in the approved write set, preserving existing contracts and deployed data.
- [x] Run covering regressions and adjacent affected tests with C1 isolation or frontend maxWorkers=1; record commands and outcomes.
- [x] Self-review the diff and write a report containing changed paths, each finding's resolution, verification evidence, assumptions and uncovered limitations. Do not commit.
- [x] Independent native review accepts the change; fix any confirmed gaps and rerun the covering tests.

### Task 7: Session and model resource lifetimes

**Files:**
- Modify/Test: `backend/app/api/deps.py`
- Modify/Test: `backend/app/api/routes/overview.py`
- Modify/Test: `backend/app/api/routes/knowledge_search.py`
- Modify/Test: `backend/app/api/routes/worklog.py`
- Modify/Test: `backend/app/api/mcp/server.py`
- Modify/Test: `backend/app/main.py`
- Modify/Test: `backend/app/api/routes/code.py`
- Modify/Test: `backend/app/api/routes/repos.py`
- Modify/Test: `backend/app/api/routes/reembed.py`
- Modify/Test: `backend/app/services/contradiction_scan.py`
- Modify/Test: `backend/app/services/memory_dream.py`
- Modify/Test: `backend/app/services/memory_community_detection.py`
- Modify/Test: `backend/app/services/article_synthesis.py`
- Modify/Test: `backend/app/api/auth.py`
- Modify/Test: `backend/app/api/websocket.py`
- Modify/Test: `backend/app/api/routes/auth.py`
- Modify/Test: `backend/app/api/routes/setup.py`
- Modify/Test: `backend/app/api/routes/config.py`
- Modify/Test: `backend/app/api/routes/llm_providers.py`
- Modify/Test: `backend/app/api/routes/git_accounts.py`
- Modify/Test: `backend/app/services/llm.py`
- Modify/Test: `backend/app/services/chat.py`
- Modify/Test: `backend/app/services/graph.py`
- Modify/Test: `backend/tests/test_websocket.py`
- Modify/Test: `backend/tests/test_auth_security.py`
- Modify/Test: `backend/tests/test_llm_config.py`
- Create regression files in the matching test directory when the named existing test is absent; record exact new paths before writing.

**Interfaces:**
- Consumes: existing service signatures and C1–C5.
- Produces: corrected behavior for register items 15, 16, 18, 19 with preserved external shape.

**Items:** 15, 16, 18, 19
**Implementer:** codex gpt-6-astra / medium
**Evaluation:** files=1, spec=1, coupling=1, risk=2; weighted routing score=7
**Assignment source:** rubric

**Requirements:** Apply shared token payload/password-epoch validation at WebSocket handshake and enforce expiry/revocation for established sockets. Enforce bcrypt's 72 UTF-8-byte boundary with clear schema/user validation and safe login failure handling while preserving existing hashes. Retire superseded orchestrators only after active requests/streams finish using explicit lifetime accounting from acquisition through pre-dispatch awaits, completion, exceptions and cancellation, with no arbitrary-delay guarantee. Audit background consumers and coordinate required pipeline/job-runner acquisition changes with their Task 5/6 owners. Refuse outbound probes in read-only mode and use local graph-name fallbacks. Test capture then delayed first dispatch across configuration swap, connected-session revocation and zero worker egress.

- [x] Trace the actual caller and failing behavior; inspect the relevant business contract and existing tests.
- [x] Add behavioral regression tests for each requirement; run them before editing implementation and record the expected failures.
- [x] Implement the smallest compatible correction in the approved write set, preserving existing contracts and deployed data.
- [x] Run covering regressions and adjacent affected tests with C1 isolation or frontend maxWorkers=1; record commands and outcomes.
- [x] Self-review the diff and write a report containing changed paths, each finding's resolution, verification evidence, assumptions and uncovered limitations. Do not commit.
- [x] Independent native review accepts the change; fix any confirmed gaps and rerun the covering tests.

### Task 8: Browser auto-capture execution

**Files:**
- Modify/Test: `extension/src/content-autocapture.js`
- Modify/Test: `extension/src/autocapture.js`
- Modify/Test: `extension/src/background.js`
- Modify/Test: `extension/src/options.js`
- Modify/Test: `extension/manifest.json`
- Modify/Test: `extension/test/autocapture.test.js`
- Modify/Test: `extension/test/auto-capture-gate.test.js`
- Create regression files in the matching test directory when the named existing test is absent; record exact new paths before writing.

**Interfaces:**
- Consumes: existing service signatures and C1–C5.
- Produces: corrected behavior for register items 17 with preserved external shape.

**Items:** 17
**Implementer:** codex gpt-6-sol / high
**Evaluation:** files=1, spec=1, coupling=1, risk=1; weighted routing score=5
**Assignment source:** rubric

**Requirements:** Ship an observer executable as an actual classic content script without unbundled static imports. Keep credential ownership and opt-in permissions in the service worker. Reflect actual registration failures truthfully in status. Test compiling/executing the injected artifact in its real script mode, with browser API/DOM doubles as needed.

- [x] Trace the actual caller and failing behavior; inspect the relevant business contract and existing tests.
- [x] Add behavioral regression tests for each requirement; run them before editing implementation and record the expected failures.
- [x] Implement the smallest compatible correction in the approved write set, preserving existing contracts and deployed data.
- [x] Run covering regressions and adjacent affected tests with C1 isolation or frontend maxWorkers=1; record commands and outcomes.
- [x] Self-review the diff and write a report containing changed paths, each finding's resolution, verification evidence, assumptions and uncovered limitations. Do not commit.
- [x] Independent native review accepts the change; fix any confirmed gaps and rerun the covering tests.

### Task 9: Document, graph and chat interaction correctness

**Files:**
- Modify/Test: `frontend/src/lib/api.ts`
- Modify/Test: `frontend/src/features/documents/components/block-editor.tsx`
- Modify/Test: `frontend/src/hooks/api/use-blocks-api.ts`
- Modify/Test: `frontend/src/hooks/api/use-graph-api.ts`
- Modify/Test: `frontend/src/lib/websocket.ts`
- Modify/Test: `frontend/src/features/chat/components/real-chat-page.tsx`
- Modify/Test: `frontend/src/features/chat/components/chat-overlay.tsx`
- Modify/Test: `frontend/src/features/chat/hooks/use-chat-stream.ts`
- Modify/Test: `frontend/src/features/chat/components/chat-input.tsx`
- Modify/Test: `frontend/src/features/documents/__tests__/block-editor.test.tsx`
- Modify/Test: `frontend/src/features/chat/__tests__/real-chat-page.test.tsx`
- Create regression files in the matching test directory when the named existing test is absent; record exact new paths before writing.

**Interfaces:**
- Consumes: existing service signatures and C1–C5.
- Produces: corrected behavior for register items 20, 21, 22, 23, 24, 25 with preserved external shape.

**Items:** 20, 21, 22, 23, 24, 25
**Implementer:** codex gpt-6-astra / medium
**Evaluation:** files=1, spec=1, coupling=1, risk=2; weighted routing score=7
**Assignment source:** rubric

**Requirements:** Normalize document source promotion using structural/nesting context without stripping meaningful content; preserve multiline quotes/list/code information and send parent identity for insertion. Surface mutation failures. Reuse graph placeholders only within one project and invalidate graph/code query families on terminal events/reconnect. Associate live streams and completion navigation with originating conversation. Display accessible send errors and preserve retryable drafts without duplicating ambiguously persisted user turns. Add mounted-navigation, delayed-response and boundary round-trip tests.

- [x] Trace the actual caller and failing behavior; inspect the relevant business contract and existing tests.
- [x] Add behavioral regression tests for each requirement; run them before editing implementation and record the expected failures.
- [x] Implement the smallest compatible correction in the approved write set, preserving existing contracts and deployed data.
- [x] Run covering regressions and adjacent affected tests with C1 isolation or frontend maxWorkers=1; record commands and outcomes.
- [x] Self-review the diff and write a report containing changed paths, each finding's resolution, verification evidence, assumptions and uncovered limitations. Do not commit.
- [x] Independent native review accepts the change; fix any confirmed gaps and rerun the covering tests.
