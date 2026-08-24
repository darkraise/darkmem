# Review Remediation — Programme Spec

**Date:** 2026-08-24
**Status:** proposed, awaiting the decisions in §7
**Source:** whole-codebase review of master, 24 slices, 74 agents, 210 claims raised and 182 confirmed, plus 12 unique findings from a diff-scoped pass over the uncommitted graph work. **194 confirmed findings: 2 critical, 17 high, 92 medium, 83 low.**

This is the spec the remediation plans argue from. It does not contain implementation
steps; those live in the plan documents named in §3, one per stage, written when the
stage is reached. What this document owns is the *shape* of the work: why it is
grouped the way it is, what order it must run in, and which questions are the owner's
rather than the implementer's.

---

## 1. The problem this spec is answering

The tree is green. `tsc -b` is clean, the backend suite is **6179 passed / 22 skipped**,
the frontend suite is **1233 passing**, and there is exactly one alembic revision as
required. Not one of the 19 critical or high findings is caught by any of that. Several
sit directly underneath a test that passes while the behaviour it names is broken —
`tests/test_push_webhook.py:725` drives the wedged-repository path and asserts only the
returned status string; `settings-flags.real.test.tsx:459` asserts that a spinner stops
after a write the user is never told failed.

That is the problem. Not that these 194 things are wrong — they are ordinary defects and
every codebase has them — but that the instruments the repository already trusts report
clean while they are present.

## 2. The organising principle

**Group by defect class, not by directory, and give every class a test that enumerates
its population.**

This is not a stylistic preference. It is the review's own strongest cross-cutting
finding, stated in its words:

> A guard written once and copied into N modules is missing from the (N+1)th, and each
> slice reviewer only sees its own copy. The short-embed-return assertion exists verbatim
> in four embedding writers and in Phase 1 of the pipeline, is a warning-only degradation
> in Phase 3, and is entirely absent in `code_pipeline.py`'s phase 12. Three separate
> reviewers each reported the instance in their own slice as if it were a local bug; it is
> one rule with two holes.

And its corollary, which the repository has already paid for more than once:

> The pattern that works is the derived test; the pattern that keeps failing is the careful
> comment.

So the 175 medium and low findings are not 175 tasks. They are **47 packages and 35
singletons**, and each package closes a class with one mechanism plus one test that walks
the whole population — an AST scan, a registry enumeration, a derived roster, a generated
case list. Per-site assertions are the weaker answer and are used only where no population
can be enumerated.

The 19 critical and high findings are handled as individual grounded tasks, because each
one is a distinct bug on a reached path and the cost of getting one wrong is higher than
the cost of not batching it.

### What the whole finding set has in common

- A guard written once and copied into N modules is missing from the (N+1)th, and each slice reviewer only sees its own copy. The short-embed-return assertion exists verbatim in four embedding writers and in Phase 1 of the pipeline, is a warning-only degradation in Phase 3, and is entirely absent in `code_pipeline.py`'s phase 12. Three separate reviewers each reported the instance in their own slice as if it were a local bug; it is one rule with two holes. The same shape appears in the four private `_ensure_partition` copies (all four agree today, nothing makes them agree tomorrow) and in the `0.85` dedup threshold (two callers pass it explicitly, the repository declares a third copy as a default no caller uses).
- The tree repeatedly fixes one instance of a class and leaves its siblings, and the fix's own docstring names the class. `tests/test_mcp_surface_parity.py:48` closed `project` on `memory_search` and explains the defect in general terms while four sibling filters stay REST-only. `config.py:357-360` explains that a flag in `FEATURE_FLAGS_DEFAULTS` with no response field reads to the UI as "no config row exists" — and `buffer_wait_timeout_seconds` is in exactly that state right now. `event-taxonomy.ts` records that three rounds each found one missing event type and fixed only that one, then built the scan that ended it. The pattern that works is the derived test; the pattern that keeps failing is the careful comment.
- An index existing is being read as evidence that it is used. Four GIN indexes on `uuid[]` columns are created in the baseline and every query against them is written `x = ANY(col)`, which no GIN index can answer. The facts reviewer verified this empirically for one site in one file; the same operator sits in the Phase-5 strip that runs on every single capture, in the `technologies` denorm recompute, in the repo-assertion strip and in four `fact_lift` joins. `tests/test_pushdown_index.py` proves the *review queue's* partial index with a real EXPLAIN; nothing does the same for the array columns.
- Case is normalised on write and assumed on read. `technologies`, entity names and `source` are all forced lowercase by their writers, CLAUDE.md states the lowercasing as a cross-cutting invariant, and the read-side filters (`MemorySearchRequest.technologies_any`, `source_any`, `memory_type_any`) compare raw caller strings. The one test that covers the filter passes an already-lowercase value, so it cannot fail. The general shape: an invariant enforced at one boundary and merely believed at the other, with the believing side owned by a different slice.
- Stale prose about what has and has not shipped is the most common defect in the tree, and it is not cosmetic — CLAUDE.md itself records that a stale "article_synthesis is a placeholder" line sent a reader hunting for code to write instead of at an empty corpus. Slice reviewers found three instances (`main.py:570`, `content_surfaces.py:335`, `review-queue.tsx:314`); there are at least six more (`review_queue.py:118`, `pin_suggestions.py:98` and `:166`, `triple_embeddings.py:68`, `review-queue.tsx:573`, `distribution.py:15`), and one of them carries a behavioural deferral (`topic_detection`'s missing `growth_threshold`/`fact_floor` config fields) that its owning task never honoured. The enforcing scans in this repo all check code shapes; none of them checks a claim.
- Where a scan *does* exist, it is honest about its bounds and the bounds are then quietly overstated one level up. `_reachability_scan.py`, `test_chat_retrieval_parity.py`'s two RRF legs, `test_event_taxonomy_map.py` and `test_api_kind_dispatch.py` each state precisely what they cannot see; CLAUDE.md then restates them as tree-wide ("a second RRF constant declared anywhere outside rank_fusion.py" — the scan covers `backend/app` only and says so; "a test fails the build if one [compares api_kind to a vendor name]" — the scan matches `ast.Compare` nodes only, so a dict keyed on vendor names or a `match` statement passes). No live violation of either exists today, so this is a documentation-vs-enforcement gap rather than a bug — but it is the gap that lets the next violation land believing it was checked.
- Guards that were written for one row generalise badly. `llm_provider_guard` freezes `base_url`/`api_kind` on the verification provider because repointing an identity from a settings form is a real capability — but the same repoint on any other provider hands the stored credential to a caller-named host, which is the same capability with a different consequence. The narrow scope is stated ("field-scoped, not row-scoped") without noticing that the row scope is the leaky half.
- Dev-shaped defaults survive into the production artifact because nothing asserts against them. The CORS fallback names two ports that were never darkmem's, was written up twice in the docs as a thing to fix, and is still live — precisely because no test in `backend/tests` mentions CORS at all. The same pattern shows up in the slice reviewers' list (demo fixtures pinned to counts that moved, comments claiming placeholders that shipped): where the codebase pins a claim with a test it stays true, and where it pins it with a comment it drifts.
- Several safeguards in this tree are named accurately in prose and implemented as something weaker. `_MAX_TRACKED` is called a "cap on tracked IPs" and is an expiry pass; the slice reviewers found the same shape in `enrichment_worker`'s unreachable retry branch and in `promotion_journal_completeness_bar`, which no predicate reads. The comment is doing the reviewing that the code should be doing, and a reader who trusts it stops looking.

## 3. Stage map

Fifteen stages plus a prerequisite. Every stage leaves the tree shippable.

| # | Stage | Contains | Gate |
|---|---|---|---|
| 0 | Land the in-flight working tree | F04, working-tree: frontend graph work (panel-resize.ts, panel-resize-handle.tsx, graph-summary*.ts(x), focus-model.ts, use-graph-layout.ts, graph-2d-… | `floor` |
| 1 | Stop the two unrecoverable data losses | F03, F07, F08, harness-ambient-database | `floor` |
| 2 | Make the shipped image able to index a repository | F09+F10, F16 | `--full` |
| 3 | Backend correctness singletons | F01+F02, F05, F06 | `floor` |
| 4 | Frontend correctness singletons | F19, F17, F18, F11+F15, F12, F13, F14 | `--full` |
| 5 | Auth and outbound-request safety | one-session-token-validator, probe-target-and-credential-binding | `floor` |
| 6 | Subtraction and cheap structure | dead-modules-import-closure, feature-flag-wire-roster, gin-unusable-array-predicates, embedder-registry-read-discipline, job-registry-row-vs-registry,… | `floor` |
| 7 | The memory primitive and the door contracts | memory-delete-demotion, half-applied-normalisation, door-accepts-what-the-layer-below-refuses, capped-result-reported-as-complete, sibling-door-parame… | `--full` |
| 8 | Loops that advance, errors that roll back | embed-length-contract, swallowed-db-error-poisons-the-transaction, gather-exception-discarded, sweeps-that-never-advance | `--full` |
| 9 | The LLM boundary and per-request fan-out | vendor-quirk-leakage, llm-response-shape-guards, article-subject-basis, unbounded-fanout-on-a-request-path | `--full` |
| 10 | Derived read state | review-state-derivation, per-row-io-on-a-page-render, composition-row-contract, resolver-arms-that-never-execute | `floor` |
| 11 | Frontend authority layer | unreachable-modules-and-exports, auth-failure-classified-as-a-verdict, no-request-is-ever-cancelled, demo-guard-per-call-site, query-key-registry-unde… | `floor` |
| 12 | Frontend truth in rendering | read-state-rendered-as-a-result, capped-list-rendered-as-a-total, write-announced-before-it-resolves, selection-outlives-the-rows-it-indexes, one-requ… | `--full` |
| 13 | Extension auto-capture reconciler | extension-autocapture-one-reconciler | `floor` |
| 14 | The prose truth pass | prose-that-states-a-property-the-code-lacks | `floor` |
| 15 | Baseline and ORM integrity | baseline-integrity-derived-tests | `--full` |

Plans written so far, in full bite-sized detail:

| Stage | Plan document |
|---|---|
| 1 | `docs/superpowers/plans/2026-08-24-r1-unrecoverable-data-loss.md` |
| 2 | `docs/superpowers/plans/2026-08-24-r2-shipped-image.md` |
| 3 | `docs/superpowers/plans/2026-08-24-r3-backend-highs.md` |
| 4 | `docs/superpowers/plans/2026-08-24-r4-frontend-highs.md` |

**Stages 5–15 are deliberately not written yet.** Each is a package or a group of packages
whose fix has been specified at the mechanism-and-pinning-test level in §5 but not grounded
against the current code line by line. Writing bite-sized TDD steps for Stage 12's 27-site
package today would be guesswork against a tree that Stages 4, 6 and 11 will have changed.
Each gets its own plan document when its predecessor lands — which is also when the code it
edits is finally still.

## 4. Stage 0 — the prerequisite, and one honest note

**The working tree is dirty and three tasks depend on it.**
`frontend/src/features/graph/lib/panel-resize.ts`,
`frontend/src/features/graph/components/panel-resize-handle.tsx` and
`frontend/src/test/pending-timers.ts` are **untracked**, so R4's Tasks 1–3 edit files that
do not exist on master. Nothing can be scheduled until that work is committed.

**One thing in that tree is not yours.** While grounding the fix specs for this spec, the
planning agent assigned to F04 (`code_pipeline.py`'s up-to-date short-circuit flushing
instead of committing) wrote its fix and its test into the working tree rather than only
describing them. `backend/app/services/code_pipeline.py` and
`backend/tests/test_push_webhook.py` are modified as a result. **That was an overstep — the
request was for a plan, not an implementation.** The change is correct and carries a real
test (`test_the_up_to_date_short_circuit_releases_the_claim`), so it has been left in place
rather than reverted, but it is yours to accept or discard:

```bash
# to see it
git diff backend/app/services/code_pipeline.py backend/tests/test_push_webhook.py
# to discard it and treat F04 as an ordinary task
git checkout -- backend/app/services/code_pipeline.py backend/tests/test_push_webhook.py
```

If you keep it, commit it as its own atomic commit — `fix(code-index): commit the
up-to-date claim release` — separate from the graph work it is currently mixed into.

`.playwright-mcp/` is also untracked. It predates this session and has been left alone.

## 5. Package register

47 packages covering 140 of the medium and low findings. Sites, effort and risk are the
packaging pass's estimates; the pinning test is the part that matters, because it is what
makes the class stay closed.

| Package | Sites | Effort | Risk | What it closes |
|---|---|---|---|---|
| `read-state-rendered-as-a-result` | 27 | 12h | medium | A read that failed, or never ran, is rendered as an observed absence |
| `unreachable-modules-and-exports` | 26 | 3h | low | 4,295 lines and 28 exported hooks that no route can reach, carrying live-looking defects |
| `write-announced-before-it-resolves` | 17 | 6h | medium | Settings writes report success on the click, not on the response |
| `embed-length-contract` | 11 | 3h | low | One vector per input text, asserted in the primitive instead of in five copies |
| `gin-unusable-array-predicates` | 11 | 3h | low | `:param = ANY(array_column)` rewritten to containment so the four GIN indexes are reachable |
| `copy-claims-a-shipped-thing-is-unshipped` | 10 | 4h | low | Seven surfaces tell the operator a shipped subsystem does not exist yet |
| `prose-that-states-a-property-the-code-lacks` | 10 | 3h | low | Comments and docstrings asserting shipped things are unshipped, and callers that do not exist |
| `confirmgate-triggers-keyboard-unreachable` | 9 | 2h | low | Every ConfirmGate trigger sets tabIndex={-1}, so no destructive settings action can be reached by keyboard |
| `demo-guard-per-call-site` | 9 | 6h | medium | The demo guard is copied into every query hook, so the next hook takes the whole demo down |
| `query-key-registry-under-enumerates` | 9 | 3h | low | The query-key completeness guard scans a quarter of the tree and cannot see a hyphen |
| `demo-fixtures-assert-what-the-product-forbids` | 8 | 8h | medium | The demo teaches rules the real product does not have |
| `door-accepts-what-the-layer-below-refuses` | 8 | 4h | low | Values a route accepts that the layer beneath rejects, surfacing as 500 instead of 422 |
| `no-request-is-ever-cancelled` | 6 | 3h | low | Superseded and abandoned requests keep running with nobody to read them |
| `per-row-io-on-a-page-render` | 6 | 4h | low | Work that should be paid once per page paid once per row |
| `sweeps-that-never-advance` | 6 | 6h | medium | Batch loops whose selection predicate the write is supposed to change, and does not |
| `unbounded-fanout-on-a-request-path` | 6 | 6h | medium | Per-request work bounded only by the row limit, on a single-worker deployment |
| `capped-list-rendered-as-a-total` | 5 | 5h | medium | A truncated list is labelled with a number the surface never received |
| `capped-result-reported-as-complete` | 5 | 4h | low | Truncation and estimate signals dropped at the door |
| `dead-modules-import-closure` | 5 | 2.5h | low | Five modules under app/services with no importer, one of them describing a seeding path the baseline removed |
| `embedder-registry-read-discipline` | 5 | 2h | low | A partition chosen without the retired/newest ordering, systematically the stale one |
| `extension-autocapture-one-reconciler` | 5 | 4h | medium | Four writers of the auto-capture state and no authority, so the badge can assert a mode that is not running |
| `probe-target-and-credential-binding` | 5 | 4h | medium | A caller-supplied base_url is fetched by the server, once unauthenticated and once carrying a stored key |
| `composition-row-contract` | 4 | 5h | medium | Rows entering the fusion and the injection journal without the identity the consumers read |
| `half-applied-normalisation` | 4 | 3h | low | One side of a comparison normalised and the other not |
| `memory-delete-demotion` | 4 | 3h | low | Move the superseded_by demotion into the delete primitive, not into each caller |
| `one-definition-two-copies` | 4 | 2.5h | low | A key and a bar resolved in two places that can drift apart |
| `resolver-arms-that-never-execute` | 4 | 5h | medium | Code-graph resolution paths that are structurally unreachable while their comments describe them working |
| `article-subject-basis` | 3 | 3h | medium | Eligibility counts one bucket and the article is written from a wider one |
| `auth-failure-classified-as-a-verdict` | 3 | 3h | medium | A transport failure and a wrong password both resolve to "you are not signed in" |
| `baseline-integrity-derived-tests` | 3 | 3h | low | Nothing compares the single baseline revision against the ORM models, and they have drifted |
| `benchlib-unexercised-branches` | 3 | 2.5h | low | Harness modules whose non-empty branch has never run |
| `feature-flag-wire-roster` | 3 | 1h | low | Every FEATURE_FLAGS_DEFAULTS key must exist on the feature-flags response and update models |
| `focus-model-recomputed-at-the-call-site` | 3 | 4h | medium | The graph's focus helpers are called and their answers partly re-derived by hand |
| `gather-exception-discarded` | 3 | 1.5h | low | asyncio.gather asked to collect exceptions whose return value is thrown away |
| `harness-ambient-database` | 3 | 2h | low | Eval scripts that open the ambient DATABASE_URL with no destructive-target guard |
| `job-registry-row-vs-registry` | 3 | 2.5h | low | Persisted job state that overrides the registered constant, and a column served but never written |
| `llm-response-shape-guards` | 3 | 3h | low | Parsers that trust the shape of a model response the tree elsewhere refuses to trust |
| `one-request-per-keystroke` | 3 | 3h | low | A query keyed on a raw input value fires a full backend round trip per character |
| `orphan-on-delete-no-fk` | 3 | 2.5h | low | Deletes keyed on a derived handle instead of the durable identity, leaving rows nothing can reach |
| `review-state-derivation` | 3 | 2h | low | Clearing one opener without re-deriving review_state leaves a queue row with no stated reason |
| `sibling-door-parameter-parity` | 3 | 4h | medium | One door passes N filters, its sibling passes N-4, with no error on either side |
| `swallowed-db-error-poisons-the-transaction` | 3 | 5h | medium | A caught database error left un-rolled-back, so the next statement on the same session dies |
| `vendor-quirk-leakage` | 3 | 3h | medium | Vendor-specific behaviour outside the quirk table, invisible to the scan that exists to catch it |
| `gold-retired-predicate` | 2 | 1h | low | One gold-pair liveness rule with two readings |
| `one-session-token-validator` | 2 | 2h | low | The WebSocket handshake validates a JWT by hand and is missing the password-change arm |
| `reset-respells-the-defaults` | 2 | 2h | low | "Reset graph view" restores a state the page never opens in |
| `selection-outlives-the-rows-it-indexes` | 2 | 4h | medium | A bulk selection survives a project change and a page turn, so it acts on rows the user cannot see |

#### `read-state-rendered-as-a-result` — A read that failed, or never ran, is rendered as an observed absence

**27 sites · 12h · risk medium**

One defect class: a surface receives `data ?? []` and reports what it found, with no third state for 'the read did not happen'. `ModuleSurface` already ships an `error` state whose own comment cites invariant 14, and `EmptyState`'s docstring already says `failed` must never render as an absence — the guard exists and was copied into some surfaces and not others. Nine of ten `ModuleSurface` state expressions still lead with `isLoading ? "empty"` and never test `isError`, and their `meta` line asserts counts ("0 registered · 0 running") the surface never observed. `ListSurface`, the second copy of the same header, takes `populated: boolean` and cannot express error at all — all eight of its call sites are structurally incapable of the guard. Two detail-by-id surfaces fold a transport failure into "not found", asserting the row does not exist. Fixing these one file at a time is what produced the split in the first place.

- **The one mechanism:** One `ReadState` discriminated union and one classifier, `readState(query)` → `{status:"pending"} | {status:"error", error} | {status:"ready", data}`, where a disabled query (`enabled:false`, the demo case) classifies as `pending`, never as an empty `ready`. `ModuleSurface` and `ListSurface` both take `read: ReadState` instead of `state`/`populated` and derive their own chip, and suppress a count-bearing `meta` unless the status is `ready`. `EmptyState` gains a `read`-driven variant so the kind is chosen by the classifier rather than typed by hand. `ListSurface` folds into `ModuleSurface` or re-exports it — two headers with different state vocabularies is the drift itself. For the by-id surfaces, reuse the state machine `useFactDetail` (src/features/knowledge/use-facts.ts:365) already implements: 404→not_found, 422→invalid, everything else→failed with a retry. `graph-detail-panel.tsx:403` gets the same treatment for cause rather than status: distinguish "this memory is filtered off the canvas" from "no edge cleared the threshold" instead of asserting the second.
- **The pinning test:** `frontend/src/components/darkmem/__tests__/read-state-single-door.test.ts`. `typescript` is already a devDependency; use `ts.createSourceFile` + `forEachChild` (regex cannot read a JSX attribute expression). Walk every `.tsx` under `src/`, collect every `JsxOpeningElement`/`JsxSelfClosingElement` whose tag is `ModuleSurface`, `ListSurface` or `EmptyState`, and read its `read`/`state`/`kind` attribute. Fail on any site whose initializer is a `ConditionalExpression` — a hand-rolled state ternary is exactly the shape that omits the error arm — unless it is a call to `readState(...)`. String-literal initializers pass only in files whose source contains none of `isError`, `isPending`, `isLoading` (a static staged/target-design surface with no query in scope). Assert `scanned.length >= 40` so a walk that finds nothing fails loudly rather than passing vacuously — the same guard `query-keys.test.ts` already uses (`toBeGreaterThan(10)`). Extend `empty-state-single-door.test.ts`'s offender walk to the two surface headers in the same pass.
- **Sites:** `frontend/src/features/activity/components/jobs-tab.tsx:387`, `frontend/src/features/activity/components/triage-tab.tsx:120`, `frontend/src/features/activity/components/day-tab.tsx:202`, `frontend/src/features/activity/components/feed-tab.tsx:76`, `frontend/src/features/activity/components/pipeline-tab.tsx:140`, `frontend/src/features/activity/components/pipeline-tab.tsx:161`, `frontend/src/features/activity/components/checkpoints-tab.tsx:272`, `frontend/src/features/activity/components/checkpoints-tab.tsx:303`, `frontend/src/features/settings/components/research-tab.tsx:65`, `frontend/src/features/knowledge/components/list-surface.tsx:6`, `frontend/src/features/knowledge/components/topics-tab.tsx:214`, `frontend/src/features/knowledge/components/topics-tab.tsx:226`, `frontend/src/features/knowledge/components/topics-tab.tsx:237`, `frontend/src/features/knowledge/components/review-queue.tsx:479`, `frontend/src/features/knowledge/components/review-queue.tsx:547`, `frontend/src/features/knowledge/components/articles-tab.tsx:243`, `frontend/src/features/knowledge/components/facts-tab.tsx:368`, `frontend/src/features/code/components/real-repositories-view.tsx:413`, `frontend/src/features/code/components/repositories-tab.tsx:215`, `frontend/src/features/activity/components/dream-tab.tsx:701`, `frontend/src/features/activity/components/dream-tab.tsx:781`, `frontend/src/features/documents/components/documents-view.tsx:205`, `frontend/src/features/documents/components/documents-view.tsx:225`, `frontend/src/features/knowledge/components/article-detail-live.tsx:339`, `frontend/src/features/memories/components/real-memory-detail-view.tsx:162`, `frontend/src/components/app-chrome/project-switcher.tsx:102`, `frontend/src/features/graph/components/graph-detail-panel.tsx:403`
- **Owner decision:** Whether `ListSurface` is deleted in favour of `ModuleSurface` (one header, one vocabulary, eight call sites migrate) or kept and widened to the same `ReadState` prop. Recommended: fold it — two headers rendering the same three states differently is the drift this package closes.

#### `unreachable-modules-and-exports` — 4,295 lines and 28 exported hooks that no route can reach, carrying live-looking defects

**26 sites · 3h · risk low**

One defect class: nothing in the tree can tell a maintainer that a module is unreachable, so dead code accumulates and reads as the reference implementation. A reachability walk from `src/main.tsx`, `src/app.tsx` and the non-test files under `src/routes/` reaches 312 of 496 modules; 23 non-test modules totalling 4,295 lines are unreachable, and they are not inert to a reader: `knowledge-graph-renderer.tsx` still spells the 0.35 that `focus-model.ts`'s `groundEdgeAlpha` exists to prevent (R079), `code-graph-renderer.tsx` re-arms ForceAtlas2 with no stop timer (R080), `jobs-panel.tsx` has drifted from the ruled 409-is-busy behaviour (R115), and `useSession` would infinite-loop the first component that called it (R116/R144, the same finding reported twice). Deleting the named files closes seven findings and leaves sixteen more modules unreachable with nothing to say so; the scan is the fix.

- **The one mechanism:** Delete the unreachable modules, their tests, and the 28 `export function use*` in `src/hooks/api/*` with no production caller (measured: `useUpdateConversation`, `useRepoStats`, `useCodeSearch`, `useFullGraph`, `useGraphEntities`, `useVectorProjection`, `useReason`, `useKnowledgeEntities`, `useKnowledgeTimeline`, `useMemories`, `useDeleteMemory`, `useBulkDeleteMemory`, `useSearchMemories`, `useTags`, `useHealth`, `useReprocessStream`, `useOverview`, `usePipelineFailureCounts`, `useRetryBatchProgress`, `useObsoleteCounts`, `useReembedMemories`, `useReembedCodeChunks`, `useReembedEntities`, `useReembedAll`, `usePruneObsoleteCache`, `useReembedBatchProgress`, `useReposPath`, `useUpdateReposPath`). Anything kept deliberately gets a file-level comment naming the task that lands it and an entry in the scan's allowlist — the pattern `CodeBucketsUnavailable` already uses — so 'staged' is a declaration rather than an absence of callers.
- **The pinning test:** `frontend/src/__tests__/no-unreachable-modules.test.ts`, a reachability walk rather than a per-file assertion. Roots: `src/main.tsx`, `src/app.tsx`, `src/routeTree.gen.ts`, and every non-test file under `src/routes/`. Resolve `@/…` and relative specifiers through the extension ladder `["", ".ts", ".tsx", "/index.ts", "/index.tsx"]`, follow both `from "…"` and dynamic `import("…")`, and fail listing every `.ts`/`.tsx` under `src/` not reached, excluding `__tests__`, `*.test.*`, `*.stories.*`, `src/test/` and `src/vite-env.d.ts`, minus a named `STAGED` allowlist each of whose entries must carry a reason string. Critically, the roots must exclude `src/routes/**/__tests__` — including them is what makes `jobs-panel.tsx` read as reachable through its own test. A second block enumerates `export function use*` in `src/hooks/api/*.ts` and fails on any with no non-test importer. Verified today: the walk reports 23 dead modules / 4,295 LOC and 28 uncalled hooks, so it goes red on this tree and green only after the deletions.
- **Sites:** `frontend/src/features/graph/components/code-graph-renderer.tsx:1`, `frontend/src/features/graph/components/code-analysis-panel.tsx:1`, `frontend/src/features/graph/components/code-inspector-panel.tsx:1`, `frontend/src/features/graph/components/code-graph-search.tsx:1`, `frontend/src/features/graph/components/knowledge-graph-renderer.tsx:1`, `frontend/src/features/graph/components/process-flow-modal.tsx:1`, `frontend/src/features/graph/components/process-panel.tsx:1`, `frontend/src/features/graph/lib/code-processes.ts:1`, `frontend/src/features/graph/lib/node-circle-bordered-program.ts:1`, `frontend/src/features/jobs/components/jobs-panel.tsx:1`, `frontend/src/features/jobs/index.ts:1`, `frontend/src/features/jobs/schemas.ts:1`, `frontend/src/features/settings/components/security-panel.tsx:1`, `frontend/src/features/settings/index.ts:1`, `frontend/src/features/settings/schemas.ts:1`, `frontend/src/features/memories/components/memory-command-palette.tsx:1`, `frontend/src/components/placeholder-tabs.tsx:1`, `frontend/src/demo/data/generate.ts:1`, `frontend/src/hooks/useApi.ts:1`, `frontend/src/lib/form-resolvers.ts:1`, `frontend/src/lib/portal-overlays.ts:1`, `frontend/src/lib/settings-tab.ts:1`, `frontend/src/lib/source-colors.ts:1`, `frontend/src/features/auth/hooks/useSession.ts:4`, `frontend/src/hooks/api/use-pipeline-api.ts:83`, `frontend/src/hooks/api/use-pipeline-api.ts:380`
- **Owner decision:** Whether the code-graph family (9 modules, ~2,900 lines) is abandoned work to delete or staged work for a task not yet started. Recommended: delete — `features/code/` holds the live code-graph renderer, and a second copy that has already drifted on three separate rules is a liability, recoverable from git if the task ever lands.

#### `write-announced-before-it-resolves` — Settings writes report success on the click, not on the response

**17 sites · 6h · risk medium**

One defect class: a mutation is fired and the user-visible success signal is emitted as the *next statement*, so the announcement is unconditional and the error is unreachable. There are 66 `.mutate`/`.mutateAsync` sites; 39 pass neither callback and 6 pass `onSuccess` with no `onError`. Several sites already have the right shape (`usage-page.tsx:191`, `add-repo-dialog.tsx:57`, `real-repositories-view.tsx:483` all pass `onSuccess` inside the options object) — the guard exists and was not copied to the settings and jobs bindings. The damage is not a missing toast: an operator who saw "Saved" for an LLM purpose write that 4xx'd, or "saved — takes effect on the next scheduled tick" for a cron the server rejected, has a false model of the running system. R086 is the same defect inverted — the provider dialog's `no_embedding_purposes` warning renders inside a component that has already unmounted on success, so a real warning is unreachable for the same structural reason a real error is.

- **The one mechanism:** One `useAnnouncedMutation(mutation, { success, failure })` wrapper returning a `run(vars)` that passes both callbacks into `.mutate` and cannot announce before the promise settles; `failure` defaults to the 409-aware note `use-maintenance-tab-binding.ts:113` already writes (`err instanceof ApiError && err.status === 409 ? busyNote(label) : …`), so the ruled busy-is-not-an-error behaviour is inherited rather than re-typed. Success chips (`setSaved(true)`) and dialog dismissals (`onOpenChange(false)`) move inside `onSuccess`; a response the user must see (`no_embedding_purposes`) is raised as a toast from `onSuccess` so it survives the unmount rather than rendering into a dead tree. `model-prices-panel.tsx` additionally validates before enabling Save — `Number("")` is 0, and a cleared override currently saves a real $0/Mtok rate under a green toast.
- **The pinning test:** `frontend/src/hooks/api/__tests__/writes-announce-on-resolution.test.ts`, an AST scan over the whole `.mutate` population rather than the five reported sites. Using `ts.createSourceFile`, collect every `CallExpression` whose callee is a `PropertyAccessExpression` named `mutate` or `mutateAsync` in every non-test `.ts`/`.tsx` under `src/` (66 today; assert `>= 50` so the scan cannot go vacuous). Two assertions per site: (a) it passes a second argument carrying both `onSuccess` and `onError`, unless its receiver was produced by `useAnnouncedMutation`; (b) the statement immediately following it in the same `Block` calls no identifier in the success-announcement set — `toast.success`, `setSaved`, `announceSave`, `onOpenChange`, or any `set*Note`. (b) is what catches the shape that has no callbacks at all and would otherwise pass a naive check, and it is derived from the block structure rather than from a list of known-bad files.
- **Sites:** `frontend/src/features/settings/use-llm-tab-binding.ts:208`, `frontend/src/features/settings/use-llm-tab-binding.ts:212`, `frontend/src/features/settings/use-maintenance-tab-binding.ts:85`, `frontend/src/features/settings/use-maintenance-tab-binding.ts:92`, `frontend/src/features/settings/use-maintenance-tab-binding.ts:99`, `frontend/src/features/jobs/use-jobs-binding.ts:31`, `frontend/src/features/jobs/use-jobs-binding.ts:32`, `frontend/src/features/jobs/components/job-config-sections.tsx:81`, `frontend/src/features/jobs/components/job-config-sections.tsx:175`, `frontend/src/features/settings/components/provider-dialog.tsx:155`, `frontend/src/features/settings/components/provider-dialog.tsx:172`, `frontend/src/features/settings/components/provider-dialog.tsx:279`, `frontend/src/features/settings/components/security-tab.tsx:459`, `frontend/src/features/settings/components/security-tab.tsx:530`, `frontend/src/features/settings/components/system-prompt-dialog.tsx:92`, `frontend/src/features/code/components/real-code-graph-view.tsx:175`, `frontend/src/features/usage/components/model-prices-panel.tsx:33`
- **Owner decision:** None.

#### `embed-length-contract` — One vector per input text, asserted in the primitive instead of in five copies

**11 sites · 3h · risk low**

This is the review's headline class in its purest form: the guard "the embedder returned N vectors for M rows; refusing to write vectors under ids they may not belong to" is hand-written in five modules and missing from four call sites, and each missing site silently commits one row's embedding under another row's primary key. Fixing site-by-site guarantees the sixth copy is missing again; asserting it inside `embed_batch`/`embed_batch_chunked` makes every present and future caller inherit it, and the four unguarded sites already have exception handling that degrades correctly once the primitive raises (Phase 3 returns cache hits only, re-embed records the error and breaks, code_pipeline skips the file and records `embed:{fp}`) -- so one edit closes four defects and deletes five duplicates.

- **The one mechanism:** Raise in `LLMOrchestrator.embed_batch` when `len(vectors) != len(texts)` and again in `embed_batch_chunked` on the concatenated result (both, because `scripts/benchlib/caching_llm.CachingLLM` overrides `embed_batch` and assembles its own list from cache hits plus live misses -- an assert only in the base method is bypassed on that path). Then delete the five hand-written caller-side length checks so there is one statement of the rule, and delete Phase 3's warn-then-zip branch (pipeline.py:449-457) entirely: its `except Exception` already returns `dict(hits), fingerprint`, which is exactly the behaviour R002 asks for.
- **The pinning test:** backend/tests/test_embed_length_contract.py, three parts. (1) Contract: parametrised over `[LLMOrchestrator, *LLMOrchestrator.__subclasses__()]` after importing `scripts.benchlib.caching_llm`, drive `embed_batch_chunked` with a stub transport that drops one element and assert RuntimeError naming both counts -- the subclass list is the registry, so a future orchestrator subclass is enumerated automatically. (2) Roster: AST-walk backend/app and backend/scripts collecting every Call whose attribute is `embed_batch` or `embed_batch_chunked`, and assert the set of (module, enclosing function) equals a pinned frozenset of the 9 production callers, so a tenth writer cannot land without a reviewer classifying it. (3) Anti-drift: AST-walk backend/app asserting no module outside app/services/llm.py contains a `Compare` of `len(vectors)` against `len(...)` -- a re-introduced local copy is the drift this package removes.
- **Sites:** `backend/app/services/llm.py:313`, `backend/app/services/llm.py:363`, `backend/app/services/pipeline.py:453`, `backend/app/services/reembed.py:452`, `backend/app/services/reembed.py:575`, `backend/app/services/code_pipeline.py:1445`, `backend/app/services/entity_anchoring.py:194`, `backend/app/services/relation_embeddings.py:175`, `backend/app/services/block_embeddings.py:116`, `backend/app/services/triple_embeddings.py:198`, `backend/app/services/pipeline.py:937`
- **Owner decision:** none

#### `gin-unusable-array-predicates` — `:param = ANY(array_column)` rewritten to containment so the four GIN indexes are reachable

**11 sites · 3h · risk low**

The baseline creates four GIN indexes on `memory_ids`/`repo_ids` for exactly these lookups, and PostgreSQL cannot use a GIN index for `scalar = ANY(array_column)` -- only `@>`, `&&`, `<@`. Eleven predicates are written in the unusable form, including `delete_by_memory_id`, which runs inside Phase 5 savepoint B for every memory ingested, and `technologies_for_memory`, which runs per memory in the same savepoint. The comment above graph.py:495 claims the opposite. Important scoping correction to the reviewer's list: `fact_lift.py:254/331/737` and the `EXISTS (SELECT 1 FROM memories m WHERE m.id = ANY(r.memory_ids))` forms are a DIFFERENT shape -- the scalar there is the indexed column and the array is the outer row, which is indexable on the pk side; rewriting those to containment would lose an index rather than gain one. They are excluded deliberately.

- **The one mechanism:** Rewrite each of the eleven predicates as `memory_ids @> ARRAY[CAST(:mid AS uuid)]` / `repo_ids @> ARRAY[CAST(:rid AS uuid)]`. Semantics are identical for a non-null scalar and the parameters are already cast, so nothing else changes. Correct the comment above graph.py:495 in the same edit.
- **The pinning test:** backend/tests/test_array_predicate_index.py, two arms. (1) Population scan: read every raw SQL string in backend/app (AST string constants), regex every `= ANY(` occurrence, classify by its right operand -- `CAST(:x AS <type>[])` is an IN-list and fine, a bare column is not -- and assert the set of "scalar left, bare array column right" predicates is empty except an allowlist naming the pk-side JOIN/EXISTS forms with their reason. (2) Plan assertion against the migrated test database: `SET enable_seqscan = off`, then EXPLAIN each of `delete_by_memory_id`'s two statements, `technologies_for_memory` and `_ASSERTED_TRIPLES`, asserting the plan text names the GIN index; with `= ANY(col)` no index exists to fall back to, so the assertion is data-independent and fails on a regression even with an empty table.
- **Sites:** `backend/app/repositories/graph.py:163`, `backend/app/repositories/graph.py:233`, `backend/app/repositories/graph.py:501`, `backend/app/repositories/graph.py:512`, `backend/app/repositories/graph.py:598`, `backend/app/repositories/graph.py:609`, `backend/app/repositories/graph.py:697`, `backend/app/repositories/graph.py:750`, `backend/app/repositories/graph.py:826`, `backend/app/repositories/graph.py:839`, `backend/app/services/fact_provenance.py:175`
- **Owner decision:** none

#### `copy-claims-a-shipped-thing-is-unshipped` — Seven surfaces tell the operator a shipped subsystem does not exist yet

**10 sites · 4h · risk low**

One defect class: a 'staged' claim is written as free prose at the surface, so it goes stale silently when the thing it describes ships and no test can notice. `use-buffer-monitor.ts:6` types the non-demo branch as `{ mode: "unavailable" }` on the reasoning that "No REST route reads memory_buffer yet" — `backend/app/api/routes/buffer.py:35` mounts `/api/v1/memory-buffer`, and CLAUDE.md names that route as the triage door for poison rows, so the one surface for triaging an errored capture renders an honest-looking gap instead. `review-queue.tsx:314` and `:573` both say `article_synthesis` "is still a placeholder job" — `SHIPPED_DREAM_JOBS` lists it and `test_the_family_holds_no_placeholders_left` asserts the family holds none. The demo's dream monitor says all six Tier-C jobs are not yet registered; all six shipped. And two claims are not merely stale but wrong in a way that misleads an operator into a bad deploy: the Security tab reports an "X-Real-IP (bundled-nginx, trusted proxy)" posture the app does not have (the default is the transport peer with no header read), and the buffer copy says `wait_process=true` "bypasses the buffer entirely" when it enqueues the row and drives that row's own flush inline.

- **The one mechanism:** A `STAGED_CLAIMS` registry in `frontend/src/demo/staged-claims.ts`. Every 'not live' / 'no REST surface' / 'still a placeholder' string moves into it as `{ id, copy, absent: { route?, job?, symbol? } }` naming the artefact whose absence the copy asserts, and every surface renders `STAGED_CLAIMS[id].copy` rather than a literal. Then correct the seven claims: `useBufferMonitor` widens to a live branch bound to `GET /api/v1/memory-buffer/stats` and `GET /api/v1/memory-buffer?status=error`, the review queue's two article strings describe "no synthesis run has produced this article", the dream monitor names what is actually missing (a REST surface reporting which dream job is running) rather than the jobs, the `wait_process` note restates the contract, the security posture becomes the real default, and the flags fixture header stops calling `w_context_boost` measured while it carries `unmeasured: true`.
- **The pinning test:** `backend/tests/test_staged_claims.py`, following the established cross-language pattern of `test_taxonomy.py::test_frontend_shares_one_vocabulary_source_that_matches_the_backend`. Parse `frontend/src/demo/staged-claims.ts`, and for every entry assert the artefact it claims is absent really is: a `route` must not resolve against `app.main.app.routes`; a `job` must not appear in the roster derived by `test_code_deriver.py`'s `_direct_job_registrations` AST scan nor in `dream_jobs.SHIPPED_DREAM_JOBS`; a `symbol` must not be importable. The population is the registry, so the day a route or a job ships, its staged claim goes red on the next backend run. Add a companion vitest asserting no non-test `.tsx` under `src/` contains the literal substrings `"still a placeholder"`, `"nothing reads them over the API"` or `"not yet live"` outside the registry module — otherwise the next claim is written as prose again.
- **Sites:** `frontend/src/features/activity/use-buffer-monitor.ts:6`, `frontend/src/features/activity/components/monitors-tab.tsx:158`, `frontend/src/features/activity/components/monitors-tab.tsx:161`, `frontend/src/demo/types.ts:470`, `frontend/src/features/knowledge/components/review-queue.tsx:314`, `frontend/src/features/knowledge/components/review-queue.tsx:573`, `frontend/src/demo/data/activity-curated.ts:240`, `frontend/src/demo/data/activity-curated.ts:249`, `frontend/src/demo/data/settings-curated.ts:329`, `frontend/src/demo/data/settings-curated.ts:10`
- **Owner decision:** Whether the buffer monitor is actually bound to the shipped route in this package (real UI work: two reads, Retry → `POST .../{id}/requeue`, Forget → `DELETE .../{id}`) or only the false claim is corrected and the binding deferred. Recommended: correct the copy and register the claim now (30 minutes), open the binding as its own task — poison-row triage has no UI at all today and deserves more than a package footnote.

#### `prose-that-states-a-property-the-code-lacks` — Comments and docstrings asserting shipped things are unshipped, and callers that do not exist

**10 sites · 3h · risk low**

Six statements in shipped code assert a property the tree does not have. CLAUDE.md records that this exact shape already cost real time once: the G-E gate's blocker was written up as "T3.02 is unshipped" because the same stale sentence lives in five modules, sending a reader to write code that already existed. The claims are: the dream-job family is all placeholders (all six shipped 2026-08-16); the article surface has no producer; both judge qualification records are absent (the entailment record is on disk and a test already asserts it); a docstring justifying an unbounded query by naming two callers that `rg` cannot find; and a comment claiming pydantic preserves a string's shape when lax mode coerces it. None is a runtime bug on its own -- and each is a documented reason a later reader will make the wrong decision.

- **The one mechanism:** Rewrite each claim to the current state, and where a claim enumerates a roster, point it at the test that pins the roster rather than restating it (`SHIPPED_DREAM_JOBS` / `test_the_family_holds_no_placeholders_left` for the family; `test_the_canonical_records_are_absent_on_this_branch`'s MINTED set for the judge records). Invert the two `fact_sources` docstrings to say what is true -- no production caller today, retained as the reverse-lookup primitive -- so the sentence becomes testable. R165 additionally carries a behavioural half: add `growth_threshold` and `fact_floor` to `TOPIC_DETECTION_CONFIG_SCHEMA` and thread them from the job's config row, which is what the deferral note assigned to T2.53 and T2.53 shipped without.
- **The pinning test:** backend/tests/test_no_stale_shipped_claims.py: scan every .py under backend/app (and, coordinated with the frontend lane, .tsx under frontend/src) for a banned-claim list -- `"is a placeholder"`, `"still a placeholder"`, `PlaceholderJobRunner` outside app/services/dream_jobs.py, and any sentence naming a key in `SHIPPED_DREAM_JOBS` within 80 characters of "placeholder" -- with an allowlist for dream_jobs.py's own definition. Second arm, for the inverted docstrings: AST-walk backend/app asserting `facts_for_source` and `count_distinct_origins` have no call site outside tests, so the new docstring claim is the one pinned rather than the old one. NOTE: frontend/src/features/knowledge/components/review-queue.tsx:314 and :573 carry the same stale sentence; the scan fails until that lane lands its half, so the two landings must be sequenced.
- **Sites:** `backend/app/main.py:570`, `backend/app/services/content_surfaces.py:335`, `backend/app/services/verification_judge.py:292`, `backend/app/services/pin_suggestions.py:98`, `backend/app/services/pin_suggestions.py:166`, `backend/app/services/review_queue.py:118`, `backend/app/services/triple_embeddings.py:68`, `backend/app/repositories/fact_sources.py:786`, `backend/app/repositories/fact_sources.py:538`, `backend/app/api/routes/config.py:720`
- **Owner decision:** none

#### `confirmgate-triggers-keyboard-unreachable` — Every ConfirmGate trigger sets tabIndex={-1}, so no destructive settings action can be reached by keyboard

**9 sites · 2h · risk low**

One defect class, one component, eight call sites, and the component's own comment states the rule the call sites break: `confirm-gate.tsx:31` says "The inner trigger stays the interactive element (keyboard included); this wrapper only catches its bubbled click". Every one of the eight `<ConfirmGate trigger={<Button tabIndex={-1} …>}>` call sites removes the trigger from the tab order, and the wrapper listens only for `onClick` with no `role`, no `tabIndex` and no key handler — so there is no key sequence that arms the panel. Change password, re-embed, prune caches, and every destructive maintenance action are mouse-only. This is a class rather than eight bugs because the trigger's focusability is a property of the gate and is currently a decision each caller re-makes.

- **The one mechanism:** Drop `tabIndex={-1}` from all eight call sites — the inner `Button` is already the focusable element and the wrapper only needs the bubbled click, exactly as its comment says. Make the property un-re-decidable by having `ConfirmGate` render the trigger itself from `triggerLabel`/`triggerVariant`/`triggerIcon` props instead of accepting an arbitrary `ReactNode`, so a caller has nowhere to put a `tabIndex`. If the `ReactNode` prop must stay, the wrapper takes `role="button"`, `tabIndex={disabled ? -1 : 0}` and an Enter/Space handler, and the scan below stops it being defeated from outside.
- **The pinning test:** `frontend/src/features/settings/__tests__/confirm-gate-keyboard.test.tsx`, two halves. (1) An AST scan enumerating the population: `ts.createSourceFile` over every non-test `.tsx` under `src/`, collect every `<ConfirmGate>` element, walk its `trigger` attribute's JSX subtree, and fail listing any that carries a `tabIndex` attribute — this enumerates all call sites, present and future, rather than the eight known ones. (2) One render case per `tone` value (`caution`, `danger`, `primary`, read from the component's own union so a new tone forces a case): render, `await userEvent.tab()` until focus lands on the trigger, press Enter, and assert the armed panel appears — proving the wrapper actually responds to the keyboard rather than merely permitting focus.
- **Sites:** `frontend/src/features/settings/components/change-password-dialog.tsx:144`, `frontend/src/features/settings/components/maintenance-tab.tsx:194`, `frontend/src/features/settings/components/maintenance-tab.tsx:221`, `frontend/src/features/settings/components/maintenance-tab.tsx:250`, `frontend/src/features/settings/components/maintenance-tab.tsx:308`, `frontend/src/features/settings/components/maintenance-tab.tsx:331`, `frontend/src/features/settings/components/maintenance-tab.tsx:353`, `frontend/src/features/settings/components/maintenance-tab.tsx:407`, `frontend/src/features/settings/components/confirm-gate.tsx:31`
- **Owner decision:** None.

#### `demo-guard-per-call-site` — The demo guard is copied into every query hook, so the next hook takes the whole demo down

**9 sites · 6h · risk medium**

One defect class: `enabled: !DEMO` is a convention re-typed at each of 81 `useQuery` declarations rather than a property of the query layer. The (N+1)th omission is not a missing number — `apiFetch`'s 401 handler hard-navigates to /login, so one unguarded read destroys every demo route. The spec that guards this says in its own header comment that it has already shipped twice; `useClassificationAreas()` in use-flags-tab-binding.ts:285 sits three lines below `useFeatureFlags(!DEMO)`, `useRepoAllowlist(!DEMO)` and `useVerificationLadder(!DEMO)` and is the third. Fixing the six named call sites reproduces the class exactly; the guard has to stop being copyable.

- **The one mechanism:** One `useApiQuery` / `useApiInfiniteQuery` wrapper in `src/hooks/api/use-api-query.ts` that ANDs the caller's `enabled` with `!DEMO` and is the only module in the tree allowed to import `useQuery`/`useInfiniteQuery` from `@tanstack/react-query`. Migrating the 81 declaration sites is a mechanical rename; after it, forgetting the guard is not expressible.
- **The pinning test:** Two tests. (1) `frontend/src/hooks/api/__tests__/one-query-door.test.ts`, modelled byte-for-byte on the existing `src/components/darkmem/__tests__/empty-state-single-door.test.ts`: walk every `.ts`/`.tsx` under `src/`, exclude `__tests__`, and fail listing every file other than `src/hooks/api/use-api-query.ts` whose source imports `useQuery` or `useInfiniteQuery` from `@tanstack/react-query`. It enumerates the entire query population by import, not by call. (2) `frontend/tests/demo-makes-no-api-calls.spec.ts` stops hand-listing `DEMO_ROUTES`: export the `nav` array from `src/routes/_authenticated.tsx` and each tabbed route's `TAB_VALUES` (`settings.tsx`, `activity.tsx`, `knowledge.tsx`, `code.tsx`), flatten `href`s and cross them with their tab values to build the list, and assert `routes.length >= 21` so a derivation that silently returns nothing fails instead of passing vacuously. Today's list is 12 of ~21 and omits /settings entirely, which is why R082 is invisible to the gate.
- **Sites:** `frontend/src/features/settings/use-flags-tab-binding.ts:285`, `frontend/src/features/settings/components/providers-panel.tsx`, `frontend/src/features/settings/components/purpose-dialog.tsx`, `frontend/src/features/settings/components/job-history-retention.tsx`, `frontend/src/features/settings/components/security-tab.tsx`, `frontend/src/features/settings/components/research-tab.tsx`, `frontend/src/features/settings/components/security-panel.tsx:44`, `frontend/src/hooks/api/use-config-api.ts:275`, `frontend/tests/demo-makes-no-api-calls.spec.ts:20`
- **Owner decision:** Whether the guard lives in a query wrapper (81 mechanical call-site renames, guard becomes unforgettable) or stays per-hook with only the AST scan enforcing it (no churn, but the guard is still copied N times and the scan needs a per-file allowlist). Recommended: the wrapper.

#### `query-key-registry-under-enumerates` — The query-key completeness guard scans a quarter of the tree and cannot see a hyphen

**9 sites · 3h · risk low**

One defect class, and it is the archetype in its purest form: the guard that is supposed to enumerate the population enumerates only part of it, so every key outside its window ships unclassified and the project switcher never re-keys it. Two independent holes, both measured. The regex is `"([a-zA-Z]+)"`, so `api-keys` and `checkpoint-latest` — both live leading domains — are invisible. And the scan reads only `src/hooks/api`, so six live domains declared elsewhere (`reembedObsoleteCounts`, `wiki`, `jobRuns`, `setupStatus`, `authMe`, `securityPosture`) are never classified at all. The same blindness runs the other way: `QUERY_KEY_SCOPE` carries `obsoleteCounts`, `pipeline`, `retryBatchProgress` and `reembedBatchProgress`, which no mounted query declares — `websocket.ts:133` invalidates `["obsoleteCounts"]` after a re-embed batch while the Maintenance tab queries `["reembedObsoleteCounts"]`, so the completion push refreshes nothing and the operator watches a stale count. The stale-entry test passes because it accepts a mention anywhere, including in the invalidation that is itself the bug.

- **The one mechanism:** Split the one scan into two and widen both. `declaredDomains()` collects the leading string of every `queryKey:` array and every `useProjectScopedKey`/`projectScopedKey` first argument, over all non-test `.ts`/`.tsx` under `src/`, with the charset `"([A-Za-z][A-Za-z0-9-]*)"`. `referencedDomains()` collects the same from `invalidateQueries` and `setQueryData` only. Then: every declared domain must be classified; every `QUERY_KEY_SCOPE` entry must be *declared*, not merely referenced; every referenced domain must be declared somewhere. The third assertion is what makes `["obsoleteCounts"]` and `["pipeline"]` fail — an invalidation aimed at a key nothing queries is a no-op, and today nothing can say so. Collapse `obsoleteCounts`/`reembedObsoleteCounts` to one key, classify the six unclassified domains, and delete the entries the third assertion strands. R123's project-isolation proof re-points at `useMemorySearchPage`, the hook the Memories page actually mounts, rather than at `useMemories`, which this package deletes.
- **The pinning test:** The widened `frontend/src/lib/__tests__/query-keys.test.ts` is itself the pin — the change is to the enumeration, not to an assertion. Keep the existing non-vacuity guard (`expect(discovered.length).toBeGreaterThan(10)`) and raise it to the measured count (62 leading keys today), so a regex that silently stops matching fails instead of passing with an empty set. Add a fourth case asserting `declaredDomains()` and `referencedDomains()` are computed by two different functions over two different source patterns — a single scan that conflates the two is the defect being closed.
- **Sites:** `frontend/src/lib/__tests__/query-keys.test.ts:39`, `frontend/src/lib/__tests__/query-keys.test.ts:45`, `frontend/src/lib/query-keys.ts:1`, `frontend/src/lib/websocket.ts:133`, `frontend/src/hooks/api/use-config-api.ts:75`, `frontend/src/features/settings/use-maintenance-tab-binding.ts:70`, `frontend/src/hooks/api/use-api-keys-api.ts:35`, `frontend/src/hooks/api/use-checkpoints-api.ts:37`, `frontend/src/hooks/api/__tests__/use-memory-api-project-scope.test.tsx:10`
- **Owner decision:** None.

#### `demo-fixtures-assert-what-the-product-forbids` — The demo teaches rules the real product does not have

**8 sites · 8h · risk medium**

One defect class: the demo fixtures are hand-authored data that no rule validates, so they encode claims the backend would refuse. Nine of the demo memory graph's seventeen edges use eight relation types outside the closed taxonomy (`PARTITIONED_BY`, `PART_OF`, …) — on a real install `normalize_relation_type` rewrites every one of them to `RELATED_TO`, so a reader learns a graph vocabulary that does not exist. Thirty-one bulk demo memories are `superseded_by` a row created *earlier* than themselves, inverting the detector's own ordering rule. One curated L0 row wears a verification-ladder badge the real Memories view never renders. Article badges are generated in the L2 fact grammar rather than `build_article_claim`'s L3 sentence. `SETUP_API_KINDS` carries a second hard-coded embeddings-capability table beside `llm_quirks.py` and `api-kinds.ts`. And `jobs.json` ships 7 jobs while a test pins them as "the seven registered jobs" — 24 are registered. Every one is machine-checkable against a rule that already exists somewhere in the tree.

- **The one mechanism:** Stop hand-authoring what a rule can decide. Export `RELATIONSHIP_TYPES` and `ENTITY_TYPES` from `frontend/src/lib/taxonomy.ts` beside the existing `MEMORY_TYPES` and type `DemoMemoryRelation.rel_type` / `DemoFact.rel_type` against them, rewriting the nine out-of-vocabulary edges to their normalised targets. Derive `SetupKindFixture.supports_embedding` at the call site from `apiKindSupportsEmbedding(kind)` instead of storing it. Pick the demo successor by timestamp rather than by index. Drop the ladder badge from the L0 fixture. Add `buildGroundedByClaim` as a port of `build_article_claim` and route `ratifyArticle` through it. Repoint the code-search fact at what `CodeQueryService.search_code` does — it fuses a vector arm and an ILIKE arm under RRF and has no `ts_rank` arm because the code-chunk partitions carry no FTS column.
- **The pinning test:** `backend/tests/test_demo_fixture_conformance.py`, extending the pattern `test_taxonomy.py` already establishes (it parses `frontend/src/lib/taxonomy.ts` today). Four enumerations, each over the whole fixture population rather than the reported rows: (1) every `rel_type` and `entity_type` literal in `frontend/src/demo/data/*.ts` must be a member of `RELATIONSHIP_TYPES`/`ENTITY_TYPES`; (2) every job key in `frontend/src/demo/data/jobs.json` must be a member of the roster `_direct_job_registrations` derives from `app/main.py`'s AST plus `SHIPPED_DREAM_JOBS`; (3) every `kind`/`supports_embedding` pair in `SETUP_API_KINDS` must agree with `llm_quirks.VendorQuirks[kind]`; (4) `frontend/src/lib/taxonomy.ts` must mirror `RELATIONSHIP_TYPES` and `ENTITY_TYPES` exactly, the same assertion `MEMORY_TYPES` already carries. Beside it, a vitest runs the *real* validators over the fixtures: every demo memory with `superseded_by` must resolve to a counterpart whose `created_at` is strictly greater (id tie-break), and every demo article claim must satisfy `validateBadgeClaim` in its L3 shape.
- **Sites:** `frontend/src/demo/data/memory-graph-curated.ts:59`, `frontend/src/demo/memories.ts:356`, `frontend/src/demo/data/memories-curated.ts:59`, `frontend/src/demo/store.ts:144`, `frontend/src/demo/data/settings-curated.ts:559`, `frontend/src/demo/data/jobs.json:1`, `frontend/src/demo/data/knowledge-curated.ts:350`, `frontend/src/lib/taxonomy.ts:11`
- **Owner decision:** Whether `jobs.json` is extended to the full 24-job roster (the demo then shows what the scheduler really runs) or stays a sample and says so (the test asserts membership plus `length > 0`, and the copy and the test name drop the count). Recommended: keep it a sample and relabel — a 24-row demo board is noise, and membership plus an honest label closes the false claim.

#### `door-accepts-what-the-layer-below-refuses` — Values a route accepts that the layer beneath rejects, surfacing as 500 instead of 422

**8 sites · 4h · risk low**

Four doors declare a contract wider than the primitive behind them, so the excess becomes an unhandled 500 rather than a client error: a negative `limit` reaches raw SQL (4 routes), a non-UUID path id reaches `CAST(:id AS uuid)` (2 routes), a >72-byte password reaches bcrypt 5.0 which raises rather than truncating, and an unknown `provider_name` reaches a NOT NULL FK at commit. Each was found in its own file by its own reviewer; every sibling route in the tree already does the right thing, which is what makes a derived route-table walk the correct instrument rather than four more per-route tests.

- **The one mechanism:** Bound the value where FastAPI can answer 422: `limit: int = Query(100, ge=1, le=200)` / `offset: int = Query(0, ge=0)` on the four routes; `memory_id: UUID` / `entity_id: UUID` on the two graph routes (str() at the service call); extend `_assert_llm_block_admissible` to assert every `spec.provider_name` is a `DEFAULT_PROVIDER_ROWS` name or one of `body.llm.providers` (it already runs before the password commit for exactly this reason), plus `max_length` on `SetupProvider.name`/`base_url`; and add a byte-length validator (<= 72) on every password field, applied symmetrically in `hash_password`/`verify_password`.
- **The pinning test:** backend/tests/test_door_input_bounds.py, a walk over the live `app.routes`: (a) every query param named `limit`/`offset` carries ge (and le for limit); (b) every path param whose name ends `_id` is annotated `UUID` unless listed in an exclusion map with a reason (`task_id`, `cycle_id`, `subject_id` are non-UUID identities today); (c) every `str` field on a request-body model carries `max_length` unless allowlisted (content/query prose); (d) every field named `password` or `*_password` carries the 72-byte validator. All four rules are derived from the route table and the model fields, so route N+1 is enumerated by construction.
- **Sites:** `backend/app/api/routes/pipeline_failures.py:62`, `backend/app/api/routes/reembed.py:76`, `backend/app/api/routes/reembed.py:95`, `backend/app/api/routes/reembed.py:114`, `backend/app/api/routes/graph.py:68`, `backend/app/api/routes/graph.py:77`, `backend/app/api/routes/setup.py:499`, `backend/app/api/auth.py:37`
- **Owner decision:** none

#### `no-request-is-ever-cancelled` — Superseded and abandoned requests keep running with nobody to read them

**6 sites · 3h · risk low**

One defect class: no `queryFn` in the tree forwards TanStack's `AbortSignal`, and the chat stream never aborts on unmount, so work the user has already navigated away from keeps consuming the backend. Cycling four repositories in the Code Graph picker re-keys `["codeGraph", repoId]` four times and fetches four full graph payloads; the three superseded ones are decoded and thrown away. Sending a long chat message and clicking Memories two seconds later leaves `/api/v1/chat/completions` open, and the backend keeps generating tokens into a reader nobody reads while holding a DB session and spending real LLM budget. `apiFetch` already accepts a `signal` with no change needed — nothing passes one.

- **The one mechanism:** The `useApiQuery` wrapper from the demo-guard package is the same door: it builds the `queryFn` and threads `({ signal }) => apiFetch(url, { signal })` for every query at once, so cancellation is a property of the query layer rather than a per-hook decision. `useChatStream` gains `useEffect(() => () => abortRef.current?.abort(), [])`, which makes `reader.read()` reject with `AbortError` — a case its existing `catch` at line 153 already swallows correctly.
- **The pinning test:** `frontend/src/hooks/api/__tests__/queries-are-cancellable.test.ts`: an AST scan enumerating every `queryFn:` property initializer in every non-test `.ts`/`.tsx` under `src/` (81 today; assert `>= 60`), failing any whose parameter list does not destructure `signal` and whose body does not pass it on. Once the wrapper lands the scan reduces to "no `queryFn` is written outside `use-api-query.ts`", which is the stronger form. For the stream, one behavioural case: render `RealChatPage`, start a send against a stubbed reader, unmount, and assert the `AbortController` was aborted and the reader was released.
- **Sites:** `frontend/src/lib/api.ts:72`, `frontend/src/features/chat/hooks/use-chat-stream.ts:38`, `frontend/src/hooks/api/use-code-api.ts:1`, `frontend/src/hooks/api/use-graph-api.ts:1`, `frontend/src/hooks/api/use-memory-api.ts:1`, `frontend/src/hooks/api/use-knowledge-api.ts:1`
- **Owner decision:** Whether this lands as part of the demo-guard package's wrapper migration (one churn instead of two over the same 81 sites) or separately. Recommended: land it in the same wrapper change.

#### `per-row-io-on-a-page-render` — Work that should be paid once per page paid once per row

**6 sites · 4h · risk low**

Three surfaces do per-row work that the tree already knows how to do once. `row_labels` leaves `gate=None` at three of its four call sites, so `_load_record` does `Path.exists()` + `open()` + `json.load()` on the promotion record for EVERY served fact row -- synchronous filesystem I/O inside async handlers on the list, chat/search composition and review-queue paths -- while `articles_read._item` already demonstrates resolving it once per page. `embed_blocks` writes vectors with a Python loop issuing one `session.execute` per block, inline in `put_document` where `MAX_BLOCKS` is 5000, while `documents.insert_blocks` one module over already uses the executemany form. And `get_crossrefs`'s inbound arm has no LIMIT and is serialised inline into the single-memory detail response, on the same page where the file's own `MEMORY_PREDECESSORS_LIMIT` exists with a comment explaining why the analogous reverse lookup is bounded.

- **The one mechanism:** Resolve once and pass down: `facts_read.list_facts`/`get_fact`, `layer_composition.compose` and `review_queue.list_open_facts` each call `corroboration_gate()` once and thread the `ClaimGate` into `row_labels(gate=...)`, with an mtime-keyed cache inside `_load_record` as a backstop. Collapse the block-vector loop to one `session.execute(text(...), [params...])`, the shape `insert_blocks` already uses. Add `LIMIT :limit` to `get_crossrefs` with a module-level cap beside `MEMORY_PREDECESSORS_LIMIT`.
- **The pinning test:** backend/tests/test_page_render_budgets.py: a counting fixture that patches `fact_badge._load_record` and counts `session.execute` calls, asserting a declared budget per surface -- record loads == 1 for a 20-row fact list, a chat compose and a review-queue page; execute calls == 1 for a 50-block embed write. The roster of surfaces is enumerated from the routes that render fact rows (derived from the response models declaring `served_status`), so a fourth fact surface must declare its budget. Plus an assertion that every non-paginated reverse lookup in app/repositories carries a module-level LIMIT constant, derived by scanning those methods' SQL for an absent LIMIT.
- **Sites:** `backend/app/services/fact_badge.py:640`, `backend/app/services/facts_read.py:180`, `backend/app/services/layer_composition.py:513`, `backend/app/services/review_queue.py:217`, `backend/app/services/block_embeddings.py:125`, `backend/app/repositories/vector.py:638`
- **Owner decision:** none

#### `sweeps-that-never-advance` — Batch loops whose selection predicate the write is supposed to change, and does not

**6 sites · 6h · risk medium**

Three loops assume progress rather than guaranteeing it. The relation-embedding rotation arm selects `ORDER BY created_at, relation_id LIMIT :limit` from the partition while the re-embed upsert deliberately leaves `created_at` untouched, so every tick re-embeds the identical oldest slice and the module's stated guarantee -- "a drifted vector is corrected within one full rotation rather than never" -- is false; a test asserts the property that causes the stall. Both re-embed backfill loops re-select with the same unordered, unoffset query and count `processed += len(rows)` regardless of what was inserted, so a vendor answering `{"data": []}` with HTTP 200 spins forever at one embedder call per iteration. And `reprocess_all` materialises the whole `memories` table and, in the streaming variant, creates one Task per memory before the semaphore throttles anything. `entity_merge` already does this correctly with a keyset cursor in a config row -- the pattern exists and was not copied.

- **The one mechanism:** Extract `entity_merge`'s config-row keyset cursor (`(created_at, id)` with wrap-on-short-window) into a small shared helper and give the rotation arm and both backfill loops one; add the invariant that an iteration which wrote zero rows stops rather than re-selecting, and count `processed` from what was actually inserted. Page `reprocess_all`/`reprocess_all_stream` on the same cursor and create tasks per window.
- **The pinning test:** backend/tests/test_sweep_progress.py: derive the job roster from `app/main.py`'s AST the way `tests/test_code_deriver.py` already derives it, and require every registered job to appear in a COVERAGE table declaring one of `cursor` / `exact-arm-only` / `bounded-full-scan` with a reason -- job 25 cannot register without being classified. For every `cursor` entry, a property test: seed `batch + 1` rows, run two consecutive ticks, assert the second selects a set disjoint from the first (or wraps). Plus a direct re-embed test with a stub embedder returning `[]`, asserting the loop terminates and reports an error rather than looping.
- **Sites:** `backend/app/services/relation_embeddings.py:130`, `backend/app/services/relation_embeddings.py:310`, `backend/app/services/reembed.py:420`, `backend/app/services/reembed.py:545`, `backend/app/services/analytics.py:33`, `backend/app/services/analytics.py:147`
- **Owner decision:** Should reprocess_all stay an HTTP route or move behind the job registry's per-job lock? (decision D4)

#### `unbounded-fanout-on-a-request-path` — Per-request work bounded only by the row limit, on a single-worker deployment

**6 sites · 6h · risk medium**

Three request paths schedule work proportional to their input with no ceiling and no cache, on a process that invariant 13 pins to one uvicorn worker. `GET /graph/unified` gathers one `chat_completion` per cluster with nothing memoised, so a single authenticated request can schedule ~500 coroutines against the extraction purpose and pay it again on every re-render, and `_compute_similarity_edges` runs a Python O(n^2) loop (up to ~500k iterations) on the shared event loop first. `_resolve_inherited_call` runs for every unresolved `self.`/`this.` member call -- a large population precisely because `TypeEnvironment.resolve('self')` always returns None -- and issues two uncached DB round trips per visited class, per call site, while phase 07 beside it already loads the whole parent map in one query. And a claim's cited `fact_ids` are neither de-duplicated nor bounded, so the entailment bill is claims x cited-facts while the module docstring claims the hub cap bounds it.

- **The one mechanism:** Declare a ceiling and cache the repeat: name only the largest N clusters with a model call and fall back to `f"Cluster {cid}"`, keyed on the sorted member ids so a re-render is free, and move the pair loop into numpy (`np.triu_indices` + threshold mask); load the extends/implements and has_method edges once per run into dicts and walk ancestors in memory (or memoise `find_inherited_method` on `(class_key, method_name)` for the phase); de-duplicate `cited` while preserving order in `_parse` and bound the (claim, fact) pairs per article, returning UNMEASURED with a reason when the bound is hit.
- **The pinning test:** backend/tests/test_request_fanout_budgets.py: a counting stub (LLM calls, `session.execute` calls) plus a pinned BUDGET table naming each entry point and its ceiling as a function of input size -- `/graph/unified` at 200 rows makes at most N model calls and zero on a repeat render; phase 06 over 50 unresolved member calls issues O(classes) queries, not O(call sites); an article with 12 claims each citing the same fact 5 times spends 12 judge calls. The table is checked against the route roster so a new endpoint that calls the LLM per row must declare its budget or be exempted with a reason.
- **Sites:** `backend/app/services/graph.py:224`, `backend/app/services/graph.py:250`, `backend/app/services/code_pipeline.py:1094`, `backend/app/services/article_synthesis.py:488`, `backend/app/services/article_synthesis.py:1`, `backend/app/services/heritage_resolver.py:1`
- **Owner decision:** none

#### `capped-list-rendered-as-a-total` — A truncated list is labelled with a number the surface never received

**5 sites · 5h · risk medium**

One defect class: a list is capped — by the client's `.slice`, by the route's own limit, or by both — and the count the user reads is presented as the whole set. The three lists in one change already disagree with each other: `MiniGraph` caps at 5 and discloses "5 of N", but N is the route's already-truncated neighbour list, so a memory with 200 neighbours reads "5 of 20"; `EntityDetail` caps at 20 and discloses nothing, so "Linked Memories (60)" followed by 20 rows reads as a payload that lost 40; "Similar memories" caps at nothing and fills the panel. `ArticlesTab` reports one 50-row page as "50 subjects" against a corpus of 130 and computes its exclusion strip from that page. And `averageDegree` in the graph summary is a bare headline statistic computed over an edge list the route capped at 1000 — the sibling measure `isolatedCount` is honestly labelled "no visible edge" while this one is not. The unifying error is that the surface reports a count without saying which population it counted.

- **The one mechanism:** One capped-list primitive: `capped(items, limit)` → `{ shown, total, hiddenCount, upstreamCapped }`, and one heading that renders the disclosure from it, replacing `NeighborHeading`'s ad-hoc `count` and MiniGraph's inline "5 of N". `upstreamCapped` is set when the source is the route's own limited payload, and the heading then renders "≥ M" rather than "M" — a denominator the client cannot verify is never printed as if it could. The graph detail panel's three lists move into a `SECTIONS` registry (`{ key, label, items, limit, hint, upstreamCapped }`) rendered by one component. `averageDegree` either carries a truncation flag from `similarity_edges` or is labelled a visible-only measure in the headline; `ArticlesTab` reads `live.data.total` and renders "50 of 130 loaded" with a Load-more, and derives its withheld strip from the same page it is describing.
- **The pinning test:** `frontend/src/features/graph/components/__tests__/graph-detail-neighbors.test.tsx` walks the `SECTIONS` registry instead of naming the three lists. For each section: render with `limit` items and assert no disclosure; render with `limit + 1` and assert the "N of M" affordance is present with the correct N and M; render with `upstreamCapped: true` and assert the denominator renders as "≥ M". A fourth list added to the panel without a registry entry renders nothing and fails the companion assertion that every list-rendering `.map` in the file is reached through `SECTIONS` (an AST check that the component body contains no `CallExpression` on `.slice` outside the primitive). Assert `SECTIONS.length >= 3` so an emptied registry fails rather than passing vacuously.
- **Sites:** `frontend/src/features/graph/components/graph-detail-panel.tsx:166`, `frontend/src/features/graph/components/graph-detail-panel.tsx:406`, `frontend/src/features/graph/components/mini-graph.tsx:70`, `frontend/src/features/graph/lib/graph-summary-stats.ts:171`, `frontend/src/features/knowledge/components/articles-tab.tsx:243`
- **Owner decision:** Whether `/graph/unified` gains a real neighbour total and a truncation flag on `similarity_edges` (a backend change, so the numbers become true) or the frontend labels every capped denominator as a lower bound (frontend-only, the numbers stay honest but less useful). Recommended: label first — it is frontend-only and the truthful version ships this week; widen the route separately if the exact totals are wanted.

#### `capped-result-reported-as-complete` — Truncation and estimate signals dropped at the door

**5 sites · 4h · risk low**

Three doors tell a client a partial answer is a complete one. `get_full_graph` returns `truncated` -- the repository comment says the flag exists precisely because an unordered, unscoped LIMIT returns an arbitrary slice -- and the route drops it and the response model does not declare it. Paginated semantic search reports `total = len(filtered)`, structurally capped at `limit + offset + 50`, and `PageInfo.build` derives page counts from it. `retry-all` retries at most 1000 failures but reports the unpaginated total and hardcodes the terminal broadcast's `current` to that total, so the UI says the batch finished in full. Same class, three doors, and a repository test that pins the flag while the door that exists for it never emits it.

- **The one mechanism:** One convention: a capped read carries its cap to the wire. Add `truncated: bool = False` to `FullGraphResponse` and pass it; use `len(failures)` as the batch total everywhere in `retry_all` and set the terminal broadcast's `current` to `processed + errors`; add `total_is_estimate: bool` and a `has_more` derived from whether the over-fetch filled to `PaginatedMemoryResponse`, and set them on the semantic path (the keyword fallback keeps its real COUNT and reports `total_is_estimate=False`).
- **The pinning test:** backend/tests/test_truncation_signals.py: AST-walk backend/app/repositories and backend/app/services for functions whose return is a dict literal containing a `truncated`/`entities_truncated`/`capped` key, and assert each producer name appears in a pinned map to a response-model field that declares it -- the population is derived from the producers, so a fourth cap signal cannot be added and silently dropped. Plus route-level assertions: `/graph/full` at limit=1 over 2 entities emits `truncated=true`; `retry-all` over 1001 failures reports total=1000 and the terminal broadcast's current equals the processed count.
- **Sites:** `backend/app/api/routes/graph.py:27`, `backend/app/schemas/graph.py:37`, `backend/app/api/routes/pipeline_failures.py:155`, `backend/app/services/memory.py:548`, `backend/app/services/memory.py:713`
- **Owner decision:** Is an estimated `total` acceptable on the semantic path, or must it be a true count? (decision D6)

#### `dead-modules-import-closure` — Five modules under app/services with no importer, one of them describing a seeding path the baseline removed

**5 sites · 2.5h · risk low**

`entity_detector.py` (394 lines), `entity_registry.py` (479), `dialect.py` (404), `ml_seed.py` and `named_bindings/wildcard_synthesis.py` are unreachable from `app.main`; the only cross-references are dead-module-to-dead-module (`entity_registry` imports `entity_detector`; `to_entity_codes` documents output "for use with dialect.compress()"). They read as part of the extraction slice to anyone reviewing entity handling, `ml_seed`'s docstring instructs the reader about a startup hook that does not exist against a table the baseline never creates, and `wildcard_synthesis` advertises Go/Ruby/C++/Swift wildcard expansion that phase 05 does not have. I verified reachability by walking the import graph from `app.main`: 249 of 272 modules are reached, and these five are in the unreached set.

- **The one mechanism:** Delete all five, plus `entity_registry.to_entity_codes`'s section header, and drop the Go/Ruby/C++/Swift claim from `named_bindings/__init__.py`'s docstring so the gap is visible rather than advertised as filled. Update `scripts/eval_cores.js` and `scripts/eval_workflow.js`, which list the first three as review targets. If any module is being held for planned work, it moves out of app/services and its docstring names the task that will wire it.
- **The pinning test:** backend/tests/test_module_reachability.py: walk the import graph (AST ImportFrom/Import, including function-level imports) from a seed set of entry points -- `app.main`, `app.schema_guard`, `migrations.env` -- over every module under backend/app, and assert every unreached module appears in a PARKED allowlist whose entries carry a one-line reason. The current unreached set is 23 (mostly packages, ABCs and dynamically imported modules such as `app.services.triple_embeddings`); after the deletions the allowlist is ~18 classified entries, and a new orphan fails the build.
- **Sites:** `backend/app/services/entity_detector.py:1`, `backend/app/services/entity_registry.py:1`, `backend/app/services/dialect.py:1`, `backend/app/services/ml_seed.py:22`, `backend/app/services/named_bindings/wildcard_synthesis.py:59`
- **Owner decision:** none

#### `embedder-registry-read-discipline` — A partition chosen without the retired/newest ordering, systematically the stale one

**5 sites · 2h · risk low**

`find_fingerprint_for_memory` scans `SELECT fingerprint FROM embedders` with no ORDER BY and no `retired_at IS NULL`, returning the first partition that happens to hold the memory. After a rotation a memory legitimately lives in two partitions (nothing deletes the old rows), and a tiny table seq-scans in heap order, so the OLDER fingerprint wins deterministically. Its sibling `resolve_read_fingerprint` sixty lines above gets this right and spends a long docstring on exactly this hazard -- so the two read paths disagree about which partition is authoritative, which is the copy-drift shape this review is organised around.

- **The one mechanism:** Order the scan the way `resolve_read_fingerprint` does -- `WHERE retired_at IS NULL ORDER BY registered_at DESC` -- and route the other bare registry scans in this file through one private helper so the ordering rule has a single statement.
- **The pinning test:** backend/tests/test_embedder_read_discipline.py: text-scan backend/app for `FROM embedders` and assert every occurrence outside `app/services/embedder_registry.py` is inside the one helper (the population today is five, all in vector.py). Behavioural: register two fingerprints, write the memory into both partitions, and assert the newer live one is returned -- and that a retired newer one is skipped.
- **Sites:** `backend/app/repositories/vector.py:543`, `backend/app/repositories/vector.py:494`, `backend/app/repositories/vector.py:217`, `backend/app/repositories/vector.py:755`, `backend/app/repositories/vector.py:766`
- **Owner decision:** none

#### `extension-autocapture-one-reconciler` — Four writers of the auto-capture state and no authority, so the badge can assert a mode that is not running

**5 sites · 4h · risk medium**

The extension's auto-capture state lives in four places -- the stored flag, the browser permission, the registered dynamic content script and the badge/title -- and each is written by a different path with no reconciler. Ticking the box writes the flag but never asks the worker to sync; registration rides `permissions.onAdded`, which does not fire when the permission is already held, so the box reads active while nothing is registered. Turning it off revokes `scripting` BEFORE the unregister, so `chrome.scripting` is undefined and both unregister calls throw synchronously into a swallow -- the orphaned registration then outlives the browser session because `persistAcrossSessions` defaults true. A clicked capture overwrites the mode title permanently. And a persistent post failure (expired token, wrong base URL, darkmem down) drops every turn silently while the badge keeps asserting `REC`, which `autocapture.js` itself calls the state that must not be quiet.

- **The one mechanism:** Make `syncAutoCapture()` the single authority and the single writer of registration, badge and title: call it at module scope and on `chrome.runtime.onStartup`; have both options branches message the worker after writing the flag (so the flag write is the trigger, not the permission event); unregister while `scripting` is still granted and only then revoke; check `chrome.scripting` explicitly rather than detecting its absence as a swallowed TypeError; and derive the badge from state that includes a consecutive-failure counter, so three failed posts flip it to an error state naming the last error and a success resets it. Per-event notifications end by restoring the mode title through the same function.
- **The pinning test:** extension/test/autocapture-state.test.js, in the house style of the existing `auto-capture-gate.test.js` source scan: assert that `chrome.scripting.registerContentScripts`, `unregisterContentScripts`, `chrome.action.setBadgeText` and `setTitle` appear in exactly one function (the reconciler) across src/*.js -- the file listing is the population, so a fifth writer fails the build -- and that every assignment to AUTO_CAPTURE_KEY in options.js is followed by a sync message in the same block. Plus node:test units with a fake chrome: the off path unregisters before `permissions.remove`; a sync with `chrome.scripting` undefined returns without throwing; three failed posts flip the badge and a success resets it.
- **Sites:** `extension/src/options.js:56`, `extension/src/options.js:65`, `extension/src/background.js:198`, `extension/src/background.js:85`, `extension/src/background.js:201`
- **Owner decision:** none

#### `probe-target-and-credential-binding` — A caller-supplied base_url is fetched by the server, once unauthenticated and once carrying a stored key

**5 sites · 4h · risk medium**

Two doors fetch a URL the caller chose. `POST /api/v1/setup/probe-models` is gated only by `require_uninitialized`, does no validation of `base_url`, and returns `HTTP {status}: {resp.text[:200]}` or `network error: {exc}` -- a request-forgery primitive plus a 200-byte read oracle open to any network peer before an admin password exists. `PUT /api/v1/config/llm-providers/{name}` lets `base_url` move while deliberately preserving the stored `api_key` (the guard in front of it returns immediately for every provider that is not the verification one), and the probe route then sends that key as a Bearer header to the new host -- defeating the mask the GET route exists to enforce. One rule closes both: a stored credential may only be sent to the endpoint it was entered for, and a caller-chosen endpoint is fetched only through one validated entry point.

- **The one mechanism:** One `probe_target(api_kind, base_url, api_key, *, authenticated: bool)` helper that both routes call: it validates the scheme (http/https only), disallows redirects, refuses to attach a stored key when `base_url` differs from the one the key was stored against, and on the unauthenticated door collapses every failure to a fixed "probe failed" string so the door stops being a read oracle. On the write side, treat a `base_url`/`api_kind` change on ANY provider as credential-invalidating: refuse the PUT with 409 unless the body supplies a new `api_key` (see decision D8).
- **The pinning test:** backend/tests/test_outbound_probe_targets.py: AST-walk backend/app for every `httpx.AsyncClient(` construction and every `client.get/post` whose URL argument is not a module constant; assert the roster equals a pinned table where each entry is classified `fixed-host` (notifications, health self-probe), `config-resolved` (LLMOrchestrator) or `caller-supplied` -- and every `caller-supplied` entry must route through `probe_target`. Plus behavioural: an unauthenticated probe against a server returning 418 with a body reveals nothing of that body; a PUT moving `base_url` with no `api_key` in the body is refused; and after such a move the stored key is never sent.
- **Sites:** `backend/app/api/routes/llm_providers.py:204`, `backend/app/api/routes/llm_providers.py:122`, `backend/app/api/routes/setup.py:95`, `backend/app/api/routes/setup.py:107`, `backend/app/services/llm_quirks.py:177`
- **Owner decision:** How hard to lock the pre-setup probe, given that the documented topology probes a LAN address (Ollama at 192.168.0.196) and localhost? (decision D7) And clear-the-key vs 409 on an endpoint move (decision D8).

#### `composition-row-contract` — Rows entering the fusion and the injection journal without the identity the consumers read

**4 sites · 5h · risk medium**

Two halves of one contract failure in the composition layer. The PPR and dual-level arms return bare `{memory_id, score}` while the semantic and keyword arms return `payload` plus `scope_labels`; `rrf_fuse` builds the fused entry from the first list that saw the row, so a memory found only by a graph arm reaches `layer_composition` with a null project and serialises with `text: ""` -- the unlabelled escape that `app/utils/scope_labels.py` exists to prevent. And `inject_watch._ids_of` reconstructs which rows were injected by slicing a PREFIX of the composed rows using a count, while `inject_fill._pass` skips rows (unverified L2 labels, a `_render` returning None), so the journalled id list names rows that were never pushed and omits rows that were -- in the module whose entire purpose is doc 13 SS6.5's promise that a human can see what the agent was told.

- **The one mechanism:** Rows carry their own identity and the fill reports the rows it admitted, rather than either being re-derived downstream: give both graph arms the same row shape as the base arms (the dual-level statement already joins `memories m`, so add `SCOPE_LABEL_COLUMNS` and the content/payload projection and stamp `**scope_labels(row)`; PPR resolves payload and labels for its projected ids in one bounded read), and add `FillResult.admitted: dict[str, list[str]]` populated by `_pass`, which `_ids_of` reads instead of slicing a prefix.
- **The pinning test:** backend/tests/test_composition_row_contract.py: enumerate the fusion arms from `HybridSearchService`'s own arm list (make it a module-level tuple of (name, callable) if it is not one, so the population is a registry rather than a reading of the function body) and assert every arm's rows carry the scope-label keys and a content/payload key -- arm N+1 is enumerated by construction. Plus a fill test with one skipped row ahead of an admitted row in the same layer, asserting the journalled ids are the admitted ones.
- **Sites:** `backend/app/services/hybrid_search.py:398`, `backend/app/services/layer_composition.py:1`, `backend/app/services/inject_watch.py:175`, `backend/app/services/inject_fill.py:1`
- **Owner decision:** none

#### `half-applied-normalisation` — One side of a comparison normalised and the other not

**4 sites · 3h · risk low**

Three comparisons fold case or shape on one operand only. The repo allowlist lowercases the whole pattern including its path, while `_normalize` lowercases only the host and `_path_matches` then does a case-sensitive comparison -- so a mixed-case org can never be allowlisted, and every fixture in the SSRF table is already lowercase so nothing catches it. `MemorySearchRequest.technologies_any` / `source_any` / `memory_type_any` are raw `list[str]` compared against columns the tree guarantees lowercase, in both the in-memory path and the SQL `&&` fallback. And the checkpoint guard tests the composed origin key for an `unknown:` prefix to catch the merge-to-one fallback bucket, which a client legitimately declaring `source="unknown"` also produces, so its every checkpoint is refused as undeclared.

- **The one mechanism:** Normalise at the boundary that owns the guarantee: lowercase only the host part in `_split_pattern` and leave the path as typed (or fold both sides -- pick one and apply it to both); add a `field_validator` on `MemorySearchRequest` lowercasing the three `*_any` filters plus `source`/`memory_type` (the latter through `normalize_memory_type` so a legacy alias resolves); and test the fallback bucket by reconstructing the exact string `resolve_origin_key` builds (`f"{UNKNOWN_ORIGIN_PREFIX}:{source}:{project}"`) instead of by prefix.
- **The pinning test:** backend/tests/test_normalisation_boundaries.py: a derived roster of the columns the tree guarantees lowercase (`memories.technologies`, `memories.source`, `memories.memory_type`, `entities.name`) mapped to the request-model fields that filter them; assert each such field carries a lowercasing validator, so a new filter field is enumerated. Plus mixed-case rows added to both the accepted and hostile tables in tests/test_repo_hint_ssrf.py, and an equality assertion that the checkpoint guard's sentinel equals `resolve_origin_key`'s own fallback string rather than a prefix of it.
- **Sites:** `backend/app/services/repo_allowlist.py:180`, `backend/app/services/memory.py:467`, `backend/app/repositories/relational.py:156`, `backend/app/services/checkpoints.py:147`
- **Owner decision:** none

#### `memory-delete-demotion` — Move the superseded_by demotion into the delete primitive, not into each caller

**4 sites · 3h · risk low**

CLAUDE.md states the rule without exception -- demote dependents before deleting a memory or `chk_superseded_has_pointer` aborts the batch -- and leaves it to caller discipline. There are two callers of `PostgresMemoryRepository.delete`: `delete_memory` demotes, `merge_memories` does not. The same function also deletes the row it just updated when `source_id == target_id`, commits that delete, and then 500s. Both defects exist because the merge door has no behavioural test at all (`rg merge_memories` finds only the route and the service). Making the demotion a property of the primitive removes the caller-discipline requirement that produced the gap.

- **The one mechanism:** Call `demote_dependents(self.session, [memory_id])` inside `PostgresMemoryRepository.delete` before `session.delete(memory)`, and drop the now-redundant call from `MemoryService.delete_memory` (the TTL sweep keeps its own, because it deletes through raw SQL for the batch and must demote the whole id list in one statement). Separately, refuse `source_id == target_id` in `merge_memories` before any write, and add the same guard as a validator on `MemoryMergeRequest` so both doors answer 422 identically.
- **The pinning test:** backend/tests/test_memory_delete_paths.py: derive the roster of memory-row removal sites by AST-walking backend/app for `session.delete(<x>)` where `<x>` is typed/named `Memory`, plus a text scan for `DELETE FROM memories`; assert the roster is exactly {`repositories/relational.py::PostgresMemoryRepository.delete`, `services/job_runners.py::expired_memory_cleanup`}. Then, parametrised over that roster, seed A superseded by B, remove B through that path, and assert A ends `deprecated` with `superseded_by IS NULL` and no IntegrityError. A third path added later fails the roster assertion before it can ship without a demotion.
- **Sites:** `backend/app/repositories/relational.py:97`, `backend/app/services/memory.py:895`, `backend/app/services/memory.py:873`, `backend/app/services/job_runners.py:385`
- **Owner decision:** none

#### `one-definition-two-copies` — A key and a bar resolved in two places that can drift apart

**4 sites · 2.5h · risk low**

Two instances of the same shape the tree already fights elsewhere (two AST scans fail the build on a second RRF constant). `buffer_monitor` imports `STALE_CLAIM_PREDICATE`, `buffer_settings` and `count_stale_claims` from `buffer_flush` and says in its docstring why it owns no second definition of "stale" -- then hardcodes the string `'flush_timeouts'` where `buffer_flush` exports `FLUSH_TIMEOUTS_KEY`. And the two faithfulness bars are resolved by two modules against two different licence rows (`verification_bar_licences` vs `faithfulness_bar_licences`), so a licence written in one is invisible to the other and the runtime admission decision and the reported bar can be two numbers.

- **The one mechanism:** Import `FLUSH_TIMEOUTS_KEY` and interpolate it into `_REQUEUE_SQL`, as `buffer_flush`'s own statements do. Make one resolver authoritative for `faithfulness_gate_precision_bar`/`faithfulness_gate_recall_bar`: have `get_verification_bars` delegate those two keys to `faithfulness_bars.get_faithfulness_bars`, so one licence row governs each key and the clamp reports once.
- **The pinning test:** backend/tests/test_single_definition.py: AST-collect every module-level `str` constant in backend/app/services whose name ends `_KEY`, and assert its literal value appears in no other module (allowlisting the SQL that interpolates the imported constant); this is the same instrument the tree already uses for RRF_K, generalised to the key population. Plus a behavioural pair: write a config row below the floor and a licence in each of the two licence rows in turn, and assert `get_verification_bars` and `get_faithfulness_bars` return the same effective value in all four combinations.
- **Sites:** `backend/app/services/buffer_monitor.py:191`, `backend/app/services/buffer_flush.py:150`, `backend/app/services/verification_judge.py:625`, `backend/app/services/faithfulness_bars.py:1`
- **Owner decision:** none

#### `resolver-arms-that-never-execute` — Code-graph resolution paths that are structurally unreachable while their comments describe them working

**4 sites · 5h · risk medium**

Two resolution capabilities are dead in a way no test would notice, because the fallbacks return None quietly. `PurePosixPath` does not collapse `..` (I confirmed: `str(PurePosixPath('src/a/../utils'))` is unchanged), so every `../`-relative TS/JS import produces a lookup key no repo-relative path can equal, and the `call_resolver` fallback uses `Path(...).resolve()` against the process CWD, which cannot match either. And `_walk_for_types` writes bindings under `function:foo`/`class:Bar` scopes while every caller in the tree calls `env.resolve(name)` with the default `scope="file"`, so the entire function-scoped half is unreachable, `resolve('self')` always returns None, and propagated cross-file `file::` bindings become the only ones visible -- which then shadow local variables. Nothing under backend/tests exercises any resolver module.

- **The one mechanism:** Normalise lexically in the resolver (split on '/', drop '.', pop on '..', bail to None on an escape above the repo root) and pass the call site's enclosing scope into `TypeEnvironment.resolve` -- phase_06 already computes `enclosing_name`/`enclosing_owner`, so the `function:Owner.name` key is available; until a local binding exists, a propagated `file::` binding must not win over one.
- **The pinning test:** backend/tests/unit/test_resolver_matrix.py: derive the case list from the language->resolver registry (`import_resolvers`' language map and `named_bindings._LANGUAGE_MAP`), and for every registered language assert a canonical matrix resolves non-None: `./x`, `../x`, `../../x/index.ts`, a scoped member call, and an escaping `../../../etc/passwd` that must resolve to None. A language added to the registry gets its row in the matrix automatically, which is the property missing today -- both defects survived because the registry has no test at all.
- **Sites:** `backend/app/services/import_resolvers/typescript_resolver.py:98`, `backend/app/services/type_env.py:26`, `backend/app/services/call_resolver.py:79`, `backend/app/services/heritage_resolver.py:483`
- **Owner decision:** none

#### `article-subject-basis` — Eligibility counts one bucket and the article is written from a wider one

**3 sites · 3h · risk medium**

`article_eligibility._CANDIDATES_SQL` groups subjects on the whole soft key `(name, entity_type)`, with a comment explaining that pooling by name alone "summed two floors into one neither had earned". Both `synthesise_subject` and `resynthesise_subject` then discard the type half, and every downstream query -- `_FACTS_SQL`, `_ALL_VERIFIED_IDS_SQL` and `articles_channel._LIVE_HASHES_SQL` -- matches on `lower(t.subject_name)` with no type constraint. Same-name/different-type subjects are an expected state (Phase 4's dedup is type-constrained precisely so they stay separate), so the gate is measuring a different population than the article is written from, and the staleness hash is computed over the wider one.

- **The one mechanism:** Pick one basis and generate the predicate from one place: either constrain the three fact queries by the decoded entity type (join `entities e ON e.id = t.subject_id` and compare `COALESCE(e.entity_type,'concept')`) or make the eligibility gate group by name alone -- whichever the owner prefers, the predicate becomes one helper the three statements interpolate, since they must share a basis by construction rather than by review.
- **The pinning test:** backend/tests/test_article_subject_basis.py: (1) AST-scan the three modules asserting the literal `lower(t.subject_name)` appears only inside the shared predicate helper -- the population is the three statements, and a fourth query on the subject inherits the basis; (2) behavioural: seed two same-name subjects of different entity types, each just under the fact floor, and assert the eligibility candidate set and the fact set the synthesis reads are the same set.
- **Sites:** `backend/app/services/article_synthesis.py:863`, `backend/app/services/article_eligibility.py:1`, `backend/app/services/articles_channel.py:1`
- **Owner decision:** none

#### `auth-failure-classified-as-a-verdict` — A transport failure and a wrong password both resolve to "you are not signed in"

**3 sites · 3h · risk medium**

One defect class in the API client: an auth outcome with three possible meanings is collapsed to two, and the collapse always lands on the destructive branch. `checkAuth()` returns a boolean, so a restarted API container or one stale keep-alive socket through the vite proxy reads as 'not authenticated' and logs the operator out of a valid session (CLAUDE.md's own deploy sequence — `docker compose up -d` — is the trigger). The mirror image is `adapter.ts:11`: login omits `on401: "surface"`, so the server's "Invalid password" is discarded and replaced with the generic "Unauthorized", and the operator is told the session expired rather than that they mistyped. `apiFetch` already documents and implements `on401: "surface"` for exactly this reason on change-password; login is the (N+1)th caller that needed it and did not get it. A drifted second `login`/`logout` pair in `lib/api.ts` is what let the two implementations diverge unnoticed.

- **The one mechanism:** One outcome type for every auth-path read: `"authenticated" | "unauthenticated" | "unknown"`, where only `unauthenticated` (401/403) may call `useAuthStore.logout()` or navigate, and `unknown` (transport throw, 5xx, anything else) leaves the store untouched so the route renders and the next real request re-decides. Pass `on401: "surface"` on the login call so the server's `detail` reaches `LoginForm`, and delete the unused duplicate `login`/`logout` in `lib/api.ts` so there is one implementation to keep correct.
- **The pinning test:** `frontend/src/lib/__tests__/auth-outcome.test.ts`, a generated case list over the whole response space rather than the two reported cases: for each of `{200, 204, 400, 401, 403, 404, 422, 500, 502, 503}` plus a `fetch` that rejects with a `TypeError`, stub `global.fetch`, call `checkAuth()`, and assert the returned outcome and — the load-bearing half — that `useAuthStore.getState().logout` was called for exactly `{401, 403}` and for nothing else. The table is the enumeration; adding a status handled by a new branch without adding its row leaves the row set incomplete, so pair it with an assertion that the cases cover every status literal appearing in `src/lib/api.ts`, read from the source. A second case asserts the login path surfaces the server `detail` verbatim.
- **Sites:** `frontend/src/lib/api.ts:103`, `frontend/src/features/auth/adapter.ts:11`, `frontend/src/lib/api.ts:112`
- **Owner decision:** None.

#### `baseline-integrity-derived-tests` — Nothing compares the single baseline revision against the ORM models, and they have drifted

**3 sites · 3h · risk low**

`schema_guard` catches "this database was built from a different baseline"; nothing catches "the baseline disagrees with the models the code queries", which is the other half of the same hazard and the one that costs a column. I ran `compare_metadata` against a freshly migrated database: the ORM declares one index the schema does not create (`ix_token_blocklist_jti`, deliberately dropped at 0001_baseline.py:1093 as redundant under the UNIQUE, with the model never updated) and twelve columns where the ORM promises NOT NULL and the database permits NULL -- all in the same direction, all with server defaults, so ordinary inserts are fine and the raw-SQL insert paths in the graph repository are not. Separately, `downgrade()` drops every table but leaks `events_forbid_write()` and `events_ensure_partition(date)`, so upgrade after downgrade fails on the leftover and the database is stuck at base. Nothing exercises the down path.

- **The one mechanism:** Land the two derived assertions first, then close the deltas they expose. Assertion one: migrate the test database to head and assert `compare_metadata` reports no `add_column`/`remove_column`/`add_index`/`modify_nullable` outside a dated allowlist (`remove_index` is expected -- the baseline owns index creation, and `memories.search_vector` is a trigger-maintained column the ORM deliberately does not declare). Assertion two: upgrade -> downgrade -> upgrade round-trip. The only fix that touches no schema is deleting the stale `ix_token_blocklist_jti` declaration from the model; the twelve nullability deltas and the two DROP FUNCTION lines both edit 0001_baseline.py, which is regenerated in place and hashed by schema_guard -- see the decisions.
- **The pinning test:** backend/tests/test_baseline_matches_models.py, both arms as above. The allowlist is the derived roster: each entry names the object and why the baseline owns it without an ORM model (events and its partitions, documents, blocks, fact_sources, fact_access_stats, project_repositories, the per-fingerprint child tables) or why the delta is accepted and when it will be closed. A new column added to a model but not the baseline fails immediately, which is exactly the production drift CLAUDE.md leads with.
- **Sites:** `backend/app/models/token_blocklist.py:20`, `backend/migrations/versions/0001_baseline.py:1513`, `backend/migrations/versions/0001_baseline.py:1093`
- **Owner decision:** Both fixes edit 0001_baseline.py, which schema_guard hashes by file bytes -- so any edit makes every deployed database refuse to boot until its stamp is re-adopted. (decisions D1 and D2)

#### `benchlib-unexercised-branches` — Harness modules whose non-empty branch has never run

**3 sites · 2.5h · risk low**

Two benchlib modules raise on the exact path the gate cares about, and both survived because no test imports them. `run_step9_independence` partitions findings by verdict class reading `finding.score`, but `DuplicateFinding` has fields `left`, `right`, `similarity` and no `score` -- so the report completes only while no duplicate is found, and raises after everything else has been computed the moment one is. `round5_frame.derive_frame` calls `r4.count_seed_splits`, which skips every pair with `id > 'eg-0041'` and raises unless it counted exactly 41; round 4's gold starts at `eg-0418`, so the self-check counts 0 and always raises, and the docstring's claim that the archive supplies round 5's splits is not what the code does (`splits = r4.T2_25_SPLITS_PINNED`).

- **The one mechanism:** Use `finding.similarity`; give `count_seed_splits` explicit `last_id` and `expected_total` parameters and pass round 4's own boundary and pair count from `round5_frame`; and make the docstring and the code agree on whether round 5's splits come from the archive or stay pinned to T2.25's.
- **The pinning test:** backend/scripts/benchlib/tests/test_runner_branches.py: derive the roster from the file listing (`scripts/benchlib/run_*.py` plus the `*_frame.py` modules) and assert each has a test module that drives its non-empty branch -- a fixture with one duplicate pair for step 9, a two-pair archive for the frames. The roster is the directory listing, so a new runner without a branch test fails collection; note also that `pyproject.toml`'s `testpaths` excludes scripts/benchlib/tests from a plain `pytest -q`, so this only runs under ./scripts/gate.sh.
- **Sites:** `backend/scripts/benchlib/run_step9_independence.py:182`, `backend/scripts/benchlib/round5_frame.py:127`, `backend/scripts/benchlib/round4_frame.py:1`
- **Owner decision:** none

#### `feature-flag-wire-roster` — Every FEATURE_FLAGS_DEFAULTS key must exist on the feature-flags response and update models

**3 sites · 1h · risk low**

`buffer_wait_timeout_seconds` is a live knob -- `memory.py:247` reads it to bound every `wait_process=true` capture and both MCP capture tools advertise it by name -- but it is absent from `FeatureFlagsResponse` and `FeatureFlagsUpdate`. Pydantic's default `extra="ignore"` drops it before `model_dump(exclude_unset=True)`, so it can be neither read nor written through the only door that writes the `feature_flags` row. The file's own comments record this exact miss happening twice before (the rank arms, then the graph arms), which is what makes it a class rather than an oversight: the defaults dict is a 20-key registry and nothing derives the wire models from it.

- **The one mechanism:** Add `buffer_wait_timeout_seconds: int` to `FeatureFlagsResponse` and `buffer_wait_timeout_seconds: int | None = Field(default=None, ge=1, le=120)` to `FeatureFlagsUpdate`, and surface it beside the other tunables in the Flags tab's `TUNABLE_KEYS` (frontend, coordinate with that lane).
- **The pinning test:** backend/tests/test_feature_flag_wire_roster.py: `assert set(FEATURE_FLAGS_DEFAULTS) <= set(FeatureFlagsResponse.model_fields)` and `<= set(FeatureFlagsUpdate.model_fields)`, plus a round-trip parametrised over every key in FEATURE_FLAGS_DEFAULTS: PUT the key with a legal value, GET it back, assert the effective value moved. The roster is the defaults dict itself, so key 21 is enumerated the day it is added.
- **Sites:** `backend/app/api/routes/config.py:340`, `backend/app/api/routes/config.py:385`, `backend/app/config.py:220`
- **Owner decision:** none

#### `focus-model-recomputed-at-the-call-site` — The graph's focus helpers are called and their answers partly re-derived by hand

**3 sites · 4h · risk medium**

One defect class: `focus-model.ts` exists so the emphasis rules have one home, and the renderer calls it and then re-implements pieces of it. `graph-2d-renderer.tsx:550` destructures `{ zIndex, ground }` from `edgeEmphasis` and discards `lit`, then immediately re-tests `src === sel || tgt === sel` and `src === hov || tgt === hov` by hand to pick the edge size — so the helper and the size rule are two implementations of one predicate, and `edge-emphasis.test.ts` covers only the helper. Meanwhile hover-lighting for nodes is bolted on as a separate `!litNode` guard around the dim call, while `labelVisible` is still handed `tier` from `focusTier`, which knows nothing about the pointer: with a node selected and the pointer on an unrelated node, that node's neighbourhood is un-dimmed and its edges are lit, and every one of those nodes renders nameless. The helper is right; the call site's private copy of half of it is what is wrong.

- **The one mechanism:** Make the helpers total so the reducers consume only helper output. `focusTier` takes the selection *and* the pointer (and both neighbour flags) and returns the one tier every downstream rule reads — `labelVisible`, the dim strength and the ground choice all take that tier, so a node lit by hover is lit for the label rule too. `edgeEmphasis` returns everything the edge reducer needs, `lit` included, and the reducer drives its size branches from `lit` rather than re-testing the endpoints.
- **The pinning test:** `frontend/src/features/graph/lib/__tests__/focus-model-consistency.test.ts`, a generated case list over the full state space rather than the two reported symptoms: the cross product of `selectedId ∈ {null, "a"}` × `hoveredId ∈ {null, "a", "b"}` × `isSelectionNeighbour ∈ {t,f}` × `isHoverNeighbour ∈ {t,f}` × `isHub ∈ {t,f}` × `zoomedIn ∈ {t,f}` — 96 cases — asserting two invariants in every one: a node that is not receded has a visible label, and a lit edge has both endpoints un-receded. Both of today's defects are single cases in that grid. Pair it with an AST scan over the two reducers in `graph-2d-renderer.tsx` failing on any comparison against `selectedNodeIdRef`/`hoveredNodeRef` outside the helper call, which is what stops the private copy being re-added.
- **Sites:** `frontend/src/features/graph/components/graph-2d-renderer.tsx:492`, `frontend/src/features/graph/components/graph-2d-renderer.tsx:550`, `frontend/src/features/graph/lib/focus-model.ts:11`
- **Owner decision:** None.

#### `gather-exception-discarded` — asyncio.gather asked to collect exceptions whose return value is thrown away

**3 sites · 1.5h · risk low**

`_enrich_one` writes into `summaries[idx]` only on success and has no try/except; the exception is captured into the gather's return value, which line 88 discards. So `summaries.get(i)` is never an Exception, the `elif isinstance(result_val, Exception)` retry branch cannot execute, `MAX_ENRICH_ATTEMPTS` and the `enrichment_attempts.asc()` ordering are dead, and every failed call falls through to `enrichment_status='failed'` with `attempts=0` -- which the batch selector (`status == 'pending'`) never revisits. One rate-limit blip strands those summaries for the life of the row, and the comment above the dead branch states the opposite. `pipeline.py:1191` does the same call correctly (assigns the results and tests isinstance), so the shape is known here.

- **The one mechanism:** Record the exception where the classification will see it: `try: summaries[idx] = await self.llm.chat_completion(...) except Exception as exc: summaries[idx] = exc` inside `_enrich_one` (leaving `return_exceptions=True` as belt and braces).
- **The pinning test:** backend/tests/test_enrichment_retry.py: (1) AST-walk backend/app for `asyncio.gather(..., return_exceptions=True)` awaited as a bare statement (return value unused) and assert each such site appears in an allowlist stating that every task has its own handler -- two sites today, one of which is the defect; (2) behavioural: a stub LLM raising once leaves `enrichment_attempts == 1` and `enrichment_status == 'pending'`, and raising `MAX_ENRICH_ATTEMPTS` times leaves it `'failed'`. Nothing in backend/tests references `MAX_ENRICH_ATTEMPTS` or `enrichment_attempts` today.
- **Sites:** `backend/app/services/enrichment_worker.py:88`, `backend/app/services/enrichment_worker.py:100`, `backend/app/services/analytics.py:184`
- **Owner decision:** none

#### `harness-ambient-database` — Eval scripts that open the ambient DATABASE_URL with no destructive-target guard

**3 sites · 2h · risk low**

`scripts/eval_round3/purge_eval.py` opens `app.database.async_session_factory` -- on this host that resolves to the live compose Postgres -- and its first statement is `UPDATE memories SET status='active', superseded_by=NULL WHERE status='superseded'` with no project, agent or tag scope. Every other statement in the same function is eval-scoped, so the unscoped one reads as a slip, not a design. benchlib already owns the answer (`benchlib/db_target.assert_destructive_target_allowed`), and the class is "a harness module that reaches a database without passing through it"; the population is enumerable from imports, so the (N+1)th script cannot be written without being classified.

- **The one mechanism:** Delete `backend/scripts/eval_round3/` (superseded by benchlib's retrieval and extraction harnesses; `run.py` reads `mem.llm_classified_type` which T1.42e removed and `debug_clean.py` imports an `EXTRACTION_SCHEMA` that no longer exists, so neither runs today anyway). If the owner keeps them (see decision), scope the resurrection UPDATE to `source_agent IN ('eval-r3','claude-code-eval')`, route every script through `assert_destructive_target_allowed(settings.database_url, actor=...)`, add a `--commit` flag defaulting to a dry-run count as `backfill_metadata_v2.py` already does, and make the MCP target an explicit argument that refuses port 8000.
- **The pinning test:** backend/tests/test_script_db_targets.py: AST-walk every module under backend/scripts, collect those that import `app.database.async_session_factory` / `create_async_engine` / `async_sessionmaker`, and assert each either calls `assert_destructive_target_allowed` somewhere in its module body or appears in a READ_ONLY allowlist whose entries carry a one-line reason. The population is derived from imports, not from a hand list, so a new script under scripts/ is enumerated the moment it opens a session.
- **Sites:** `backend/scripts/eval_round3/purge_eval.py:27`, `backend/scripts/eval_round3/run.py:119`, `backend/scripts/eval_round3/debug_clean.py:1`
- **Owner decision:** Delete scripts/eval_round3/ outright, or repair and guard it? (decision D5)

#### `job-registry-row-vs-registry` — Persisted job state that overrides the registered constant, and a column served but never written

**3 sites · 2.5h · risk low**

Two ways the `job:<key>` config row and the registered job disagree. `load_config` synthesises `min_interval_seconds` from the registered constant only while no row with a `cron` key exists; `_run_once` then saves `cfg.to_dict()` including it, so from the first run the floor is a database value that no operator surface can edit (`JobUpdate` carries only `enabled` and `cron`, and `config_schema` holds no such field) and later changes to the registered constant never reach a deployed install. And `job_runs.trigger` is declared NOT NULL with a `'schedule'` server default and served on `GET /api/v1/jobs/{key}/runs`, but `_record_run` never sets it -- `_run_once` carries no argument saying which caller invoked it -- so the manual-run badge can never appear.

- **The one mechanism:** The registry owns registered constants and the row owns operator-set fields: drop `min_interval_seconds` from `JobConfig.to_dict()`/`from_dict` and read `job.min_interval_seconds` in `_loop`. Give `_run_once` a keyword-only `trigger: str = "schedule"`, pass `"manual"` from `JobRegistry.trigger`, thread it into `_record_run` and set it on the `JobRun`.
- **The pinning test:** backend/tests/test_job_config_roster.py: parametrised over the full registered job roster (derived from `app/main.py`'s AST the way tests/test_code_deriver.py already derives it, so all 24 are covered and job 25 is enumerated automatically) -- for each job, save its config, mutate the registered constant in-process, reload, and assert the effective floor is the registered one, not the persisted one. Plus a direct assertion that a manual `trigger(key)` writes a `job_runs` row with `trigger='manual'` and a scheduled tick writes `'schedule'`.
- **Sites:** `backend/app/services/job_registry.py:132`, `backend/app/services/job_registry.py:458`, `backend/app/api/routes/jobs.py:133`
- **Owner decision:** none

#### `llm-response-shape-guards` — Parsers that trust the shape of a model response the tree elsewhere refuses to trust

**3 sites · 3h · risk low**

`article_synthesis._parse` guards the hazard explicitly (`if not isinstance(data, dict): raise DraftRefused(...)`), so the discipline exists; two sibling parsers are missing it in different ways. `grounded_qa._parse` wraps only `json.loads`, so a valid JSON array/string/number makes `payload.get(...)` raise AttributeError, which `except (ValueError, TypeError)` does not catch and which reaches `POST /api/v1/documents/qa` as a 500 instead of the empty-sentence list the module's contract produces. And `proposition_lift._span` applies its bool exclusion to `span_start` only, so a JSON `true` in `span_end` passes `isinstance(end, int)` and writes a `char_span` of `[0, True]` into `memories.metadata.document_provenance` -- exactly the unusable pair the function's docstring says must be dropped rather than clamped.

- **The one mechanism:** One `parse_json_object(raw, *, logger) -> dict | None` helper beside the other LLM utilities, used by every response parser, plus a shared `_as_index(value)` that excludes bool before int for both span operands (bool is an int subclass, so the exclusion must be on both or on neither).
- **The pinning test:** backend/tests/test_llm_response_shape.py: AST-walk backend/app/services for every `json.loads(` call and assert each either is inside `parse_json_object` or appears in an allowlist with a reason -- the population of response parsers is derived, so the next one inherits the guard. Plus a parametrised table over the helper: `[]`, `"str"`, `3`, `null`, `{}` and a well-formed object, and a span table covering `true`/`false` in each operand position.
- **Sites:** `backend/app/services/grounded_qa.py:199`, `backend/app/services/proposition_lift.py:218`, `backend/app/services/article_synthesis.py:488`
- **Owner decision:** none

#### `one-request-per-keystroke` — A query keyed on a raw input value fires a full backend round trip per character

**3 sites · 3h · risk low**

One defect class: a controlled input's state is passed straight into a query key or an effect dependency, so every keystroke is a request. Typing the 8-character query "postgres" on the Memories page issues eight `POST /memories/search/paginated`, each embedding a prefix against the Ollama endpoint at 192.168.0.196, each running the full hybrid search, each writing an `llm_usage` row — and the list blanks between them because nothing keeps the previous page. The setup wizard does the same with three purposes mounted: a hand-typed 51-character API key fires ~153 `POST /setup/probe-models`, each an outbound call to the vendor. The repo already owns the fix — `useDebouncedValue` is used for the graph's similarity threshold, cluster size, spacing and tightness — it just lives under `features/graph/hooks/` where the other surfaces did not find it. R099 and R142 are the same site reported twice.

- **The one mechanism:** Promote `useDebouncedValue` to `src/hooks/use-debounced-value.ts` (re-exported from its old path so the graph's four call sites are untouched) and make it the only way an input-bound value reaches a query. Memories search passes `useDebouncedValue(query, 300)` into `useMemorySearchPage` and keeps `query` for the input; `usePaginatedSearch` takes `placeholderData: keepPreviousData` so a refinement does not blank the list. The wizard's probe effect drops `api_key`/`base_url` from its dependency list and re-probes on `providerName` change plus the explicit Test button `ProviderRow` already renders — a credential should not be sent to a vendor at every intermediate prefix.
- **The pinning test:** `frontend/src/hooks/__tests__/inputs-are-debounced.test.ts`: an AST scan that enumerates the population of input-bound identifiers. For every non-test `.tsx` under `src/`, find each `<Input>`/`<Textarea>` whose `value` attribute is a plain identifier, then within the same component body fail if that identifier appears in a `queryKey` array, in a `use*Query`/`use*Search`/`use*Page` call's argument list, or in a `useEffect` dependency array, unless it was produced by `useDebouncedValue`. Assert the scanned controlled-input count is `>= 8` so a walk that matches nothing fails. Pair it with one behavioural case per fixed site: fake timers, type 8 characters, advance 300ms, assert exactly one fetch.
- **Sites:** `frontend/src/features/memories/components/real-memories-view.tsx:113`, `frontend/src/features/setup/components/StepLLM.tsx:284`, `frontend/src/features/graph/hooks/use-debounced-value.ts:1`
- **Owner decision:** None.

#### `orphan-on-delete-no-fk` — Deletes keyed on a derived handle instead of the durable identity, leaving rows nothing can reach

**3 sites · 2.5h · risk low**

Two deletions miss rows because they resolve what to remove through a key that is not the identity. Deleting a repository removes the row, its auth-token config row, the clone, the failures and the graph assertions -- but `WikiGenerator` writes to a `config` row keyed `wiki_{repo_id}` and nothing deletes it; once the repository is gone the key is not derivable from any surviving row. `withdraw_document` resolves the `fact_sources` to delete by listing the document's CURRENT block ids, and block ids are minted fresh on every re-file (the module's own docstring says so), so every source minted against a previous version is both unreconciled at edit time and invisible at delete time -- while the module docstring states the rule as "removing a document withdraws its blocks' provenance" and every block source already carries the DOCUMENT as its origin_key.

- **The one mechanism:** Withdraw by the durable identity, and put that identity in one constant. Delete the `wiki_{repo_id}` config row in the same transaction as the auth-token cleanup, with `WikiGenerator` exposing the key format as a module constant so the two sites cannot drift. Replace `_DELETE_SOURCES_SQL` with a delete on `source_kind = :kind AND origin_key = :document_id` (keeping the block listing only to report a count), and add a re-file hook mirroring `fact_provenance.reconcile_memory_sources`.
- **The pinning test:** backend/tests/test_orphans_on_delete.py: a pinned roster of every "foreign identity carried without a foreign key" -- derived by scanning for config keys built by f-string from a row id, plus `fact_sources.source_ref` writers, plus `entities.repo_ids`/`entity_relations.repo_ids` -- with one delete-path test per entry asserting no row survives the owner's deletion. The roster is what forces the next FK-less handle to be classified; per-site tests alone would not have found either of these.
- **Sites:** `backend/app/services/repo_manager.py:313`, `backend/app/services/block_fact_sources.py:107`, `backend/app/services/block_fact_sources.py:51`
- **Owner decision:** none

#### `review-state-derivation` — Clearing one opener without re-deriving review_state leaves a queue row with no stated reason

**3 sites · 2h · risk low**

`derive_review_state` is total and the clear is the absence of EVERY opener; `dismiss_contradiction_suspicion` clears the two suspicion columns but passes the default `UNSET_REVIEW_STATE`, so when the suspicion was the only opener the fact stays `review_state='open'`, keeps listing on the review queue, and `_fact_reason` -- finding no distinguishing column -- returns `"unspecified"`, the shape both modules' docstrings call the defect they closed. The reviewer sees a queue entry with no reason and nothing to act on until the slow reconciliation arm catches up.

- **The one mechanism:** Derive and write in the same UPDATE the function already holds a FOR UPDATE for: read the fact's other openers (`verification_status == 'disputed'`, `demotion_pending_since IS NOT NULL`) and pass `review_state=REVIEW_STATE_OPEN if another opener stands else None` into `set_verification_status` -- the same co-location the ladder is required to use.
- **The pinning test:** backend/tests/test_review_state_openers.py: parametrise over `verification_ladder.REVIEW_OPENERS` -- the registry is the population -- and for each opener: open it, clear it through its own door, and assert `review_state` and the queue's rendered reason agree (cleared when it was the only opener; still open with the surviving opener's reason when another stands). Adding a fifth opener adds its case automatically, which is the property `derive_review_state`'s design already assumes and no test enforces.
- **Sites:** `backend/app/services/human_adjudication.py:396`, `backend/app/services/verification_ladder.py:1`, `backend/app/services/review_queue.py:1`
- **Owner decision:** none

#### `sibling-door-parameter-parity` — One door passes N filters, its sibling passes N-4, with no error on either side

**3 sites · 4h · risk medium**

Two paths that the tree documents as the same path silently take fewer arguments. MCP `memory_search` cannot express `status`, `technologies_any`, `source_any` or `memory_type_any`; because `status` defaults to `["active"]`, an MCP agent cannot reach a superseded or deprecated memory through search at all, while `docs/two-door-parity.md` records the only asymmetry as a wire one. And `_search_memories_paginated_traced` calls `search_with_trace` without the `ppr_weight` / `dual_weight` / `access_signals` arguments the untraced path derives through `rank_fusion.ppr_list_weight` -- whose docstring names this exact failure: "identical while both were off, divergent the moment one was flipped, with no error on either side." Both are inert today (the arms sit at 0), which is precisely why only a derived test will catch them.

- **The one mechanism:** Add the four filters to `memory_search` and pass them through (as T1.42c did for `project`). Build the `HybridSearchService` kwargs for both the traced and untraced paths in one helper, so a new arm is added once; the traced multiplier dict is built by the same code as `pipeline._apply_rank_fusion_factor`.
- **The pinning test:** backend/tests/test_door_parameter_parity.py, both arms derived: (1) `set(MemorySearchRequest.model_fields) - EXCLUDED <= set(inspect.signature(memory_search).parameters)`, where EXCLUDED is an explicit, reasoned set (`with_trace`, `context` -- the tool has no envelope for them); adding a request field forces a decision. (2) AST-compare the keyword sets passed to `HybridSearchService.search` and `.search_with_trace` at their call sites and assert they are equal, plus a behavioural parity test driving both `with_trace` values at a non-zero `w_ppr` and asserting identical id order.
- **Sites:** `backend/app/api/mcp/server.py:195`, `backend/app/services/memory.py:615`, `backend/app/services/pipeline.py:1315`
- **Owner decision:** none

#### `swallowed-db-error-poisons-the-transaction` — A caught database error left un-rolled-back, so the next statement on the same session dies

**3 sites · 5h · risk medium**

`AnalyticsService.get_stats` documents the hazard and rolls back -- "an aborted graph COUNT leaves the session in a failed-transaction state; roll back so the response (and any later reuse of this session) doesn't inherit the poison" -- and `get_overview` forty lines below is a copy of the same try/except with the rollback dropped and the log downgraded to DEBUG, so the five queries that follow all raise `InFailedSQLTransactionError` and the endpoint 500s where its sibling degrades. The same shape appears in `article_synthesis`: the comment says an embedder outage must not un-write a complete article, which holds for an `llm.embed()` failure but not for the INSERT that `write_article_embedding` issues on the same session -- the swallow leaves the session inactive, the caller's commit raises, and the article, its journal row and its citations are gone while `outcome.written` was already incremented.

- **The one mechanism:** Two forms of one rule: an optional read that may fail gets a shared `guarded_optional_read(session, coro)` helper that catches `SQLAlchemyError`, logs at WARNING with exc_info and rolls back before returning None (both analytics methods call it, so the rollback cannot be dropped from one copy again); an optional WRITE gets a savepoint -- wrap both `write_article_embedding` calls in `async with session.begin_nested():` inside the existing try -- and `outcome.written += 1` moves after `await session.commit()`.
- **The pinning test:** backend/tests/test_swallowed_db_errors.py: AST-walk backend/app for every `Try` whose handler does not re-raise and whose body awaits a call on a session or repository, and assert each either calls `rollback()`/`begin_nested()` or appears in an allowlist entry naming why it is safe (own session, per-task handler, no shared transaction). My scan of the current tree returns 34 candidates, so the initial classification pass is most of this package's cost -- and it is the deliverable: after it, an unclassified swallow fails the build. Plus behavioural: a stub graph repo raising on `get_stats` leaves `/analytics/overview` answering 200 with null counts, and a failing embedding INSERT leaves the article committed.
- **Sites:** `backend/app/services/analytics.py:238`, `backend/app/services/article_synthesis.py:887`, `backend/app/services/article_synthesis.py:1741`
- **Owner decision:** none

#### `vendor-quirk-leakage` — Vendor-specific behaviour outside the quirk table, invisible to the scan that exists to catch it

**3 sites · 3h · risk medium**

CLAUDE.md fixes `api_kind` as the only axis a vendor difference is expressed on and requires every quirk to be one `VendorQuirks` row; `tests/test_api_kind_dispatch.py` enforces it by walking `ast.Compare` nodes. Two couplings evade that scan because neither is a comparison. `_append_no_think` appends the Qwen chat-template directive `/no_think` for EVERY compat vendor whenever `cfg.reasoning` is False, with no quirk field governing it -- OpenAI, Anthropic, Google, DeepSeek and z.ai receive it as ordinary prompt text. And `_log_usage` writes out the three vendor cache-hit field names in a fixed order forty lines below `extract_usage`, whose docstring says the lookup is read from the quirk row precisely so this cannot happen; they have already diverged in meaning, since `anthropic`/`google`/`zai` declare `cache_hit_fields=()` and `_log_usage` still reports a ratio off a bare `cached_tokens` key.

- **The one mechanism:** Express both in the quirk table: add `appends_no_think: bool` to `VendorQuirks` and gate line 687 on it, and pass `api_kind` into `_log_usage` so its counts come from `extract_usage(payload, quirks_for(api_kind))` -- one resolution feeding both the log line and the priced row.
- **The pinning test:** Extend the existing scans rather than adding a parallel one: in tests/test_api_kind_dispatch.py and tests/test_llm_usage_extraction.py, walk every string constant in app/services/llm.py (not only `ast.Compare` operands) and fail on any literal equal to a vendor name or to a member of the union of `VendorQuirks.cache_hit_fields` across all rows. The banned literal set is DERIVED from the quirk table, so adding a vendor or a cache field extends the scan automatically -- which is what the current Compare-only scan cannot do.
- **Sites:** `backend/app/services/llm.py:688`, `backend/app/services/llm.py:647`, `backend/app/services/llm_quirks.py:1`
- **Owner decision:** Setting appends_no_think=False for DeepSeek changes the extraction prompt, so the F1 baseline must be re-measured under the gate ledger's rules. (decision D3)

#### `gold-retired-predicate` — One gold-pair liveness rule with two readings

**2 sites · 1h · risk low**

`find_duplicate_propositions` and `cross_gold_near_overlap` treat any pair carrying a `retired` key as retired, while every loader and scorer in the tree (`entailment_gold`, `retrieval_gold`, `judge_qualification`, `faithfulness_gate`) uses truthiness. The gold files happen to carry `retired` only as `true` today -- 29 of 309 pairs in entailment/gold.json -- so the two readings agree by accident of the data, and the loaders accept an explicit `false` without complaint. A pair written `"retired": false` is silently skipped by the duplicate screen, which is the anti-tuning instrument.

- **The one mechanism:** Use `pair.get("retired")` in both functions, keeping the `retirement_kind` clause, so every reader of the key shares the loaders' reading.
- **The pinning test:** backend/scripts/benchlib/tests/test_retired_predicate.py: text/AST-scan every module under scripts/benchlib for a read of the `"retired"` key and assert each is a truthiness test rather than a presence test (`in`, `.get(...) is not None`, `"retired" in pair`) -- the population is every gold reader, so the next one cannot introduce a third reading. Plus a fixture pair carrying `"retired": false` that must be screened.
- **Sites:** `backend/scripts/benchlib/duplicate_propositions.py:114`, `backend/scripts/benchlib/duplicate_propositions.py:1`
- **Owner decision:** none

#### `one-session-token-validator` — The WebSocket handshake validates a JWT by hand and is missing the password-change arm

**2 sites · 2h · risk low**

`require_auth` gates a session on two checks -- the jti blocklist AND `_password_changed_after(iat)`, which CLAUDE.md names as how a password change revokes pre-change tokens. `websocket_endpoint` reimplements the check inline and performs only the first, so a token every REST route refuses still opens `/ws` and streams the live event fan-out for the life of the socket, never re-authenticated. There are exactly two `jwt.decode` call sites in backend/app, which makes the population trivially enumerable and the guard trivially centralisable.

- **The one mechanism:** Extract `authenticate_session_token(token: str, session) -> TokenPayload` from `require_auth` (decode, TokenPayload validation, blocklist, password-change arm) and have both `require_auth` and `websocket_endpoint` call it; the socket maps its failure to close(1008) instead of a 401.
- **The pinning test:** backend/tests/test_session_token_validation.py: (1) AST-walk backend/app asserting `jwt.decode` appears exactly once, inside `app/api/auth.authenticate_session_token` -- any future door that decodes a token itself fails the build; (2) behavioural, parametrised over both doors: mint a token, bump `admin_password_changed_at`, and assert both `/api/v1/memories` and the `/ws` handshake refuse it, and that a blocklisted jti is refused on both. There is no handshake test today at all, so both arms are new coverage.
- **Sites:** `backend/app/api/websocket.py:86`, `backend/app/api/auth.py:117`
- **Owner decision:** none

#### `reset-respells-the-defaults` — "Reset graph view" restores a state the page never opens in

**2 sites · 2h · risk low**

One defect class: the initial state is written twice — once as a `useState` seed and once as a literal inside `handleReset` — and the two copies have already diverged on the three values that got named constants. The page opens with `DEFAULT_SIZE_MODE` (`"importance"`), `DEFAULT_COLOR_MODE` (`"cluster"`) and `DEFAULT_HULL_MODE` (`"none"`); Reset writes `"connections"`, `"type"` and `"none"`, so clicking it lands the user in a colour and size encoding the graph has never opened in, and the cluster hulls and the summary's cluster readout stop agreeing with the canvas. The remaining five values (0.5, 3, 300, 100, 50) happen to match today and are the same latent hazard — five literals with no relationship to the `useState` seeds that produced them. One site, but the population is the eight controls, and the sixth one added will diverge the same way.

- **The one mechanism:** One `DEFAULT_GRAPH_VIEW` object holding all eight values, exported beside the three existing `DEFAULT_*` constants (which become its members). `useGraphLayout` and the page seed every `useState` from it; `handleReset` applies it field by field and contains no literal at all.
- **The pinning test:** `frontend/src/features/graph/hooks/__tests__/graph-defaults.test.ts` gains a derived case rather than per-control assertions. Render `RealMemoryGraphPage`, read every toolbar control's value at mount into a snapshot, then — driving from `Object.keys(DEFAULT_GRAPH_VIEW)`, so the roster is the defaults object itself — change each control to a value different from its default, click "Reset graph view", and assert the snapshot returns exactly. A ninth control added to `DEFAULT_GRAPH_VIEW` but not to `handleReset` fails on its own key; a control added to neither is caught by a companion AST assertion that `handleReset`'s body contains no `NumericLiteral` and no `StringLiteral` — every argument must be a property access on the defaults object.
- **Sites:** `frontend/src/features/memory-graph/components/real-memory-graph-page.tsx:163`, `frontend/src/features/graph/hooks/use-graph-layout.ts:13`
- **Owner decision:** None.

#### `selection-outlives-the-rows-it-indexes` — A bulk selection survives a project change and a page turn, so it acts on rows the user cannot see

**2 sites · 4h · risk medium**

One defect class: `useSelection` holds a `Set<string>` of ids that is neither scoped to the query that produced them nor able to resolve a row that is no longer on screen. Ticking 5 low-confidence memories under project `alpha` and then typing `beta` reloads the list with nothing checked while the toolbar still reads "5 rows selected" and Prune stays enabled — clicking it prunes alpha's rows from a screen showing beta's. The same decoupling runs the other way on the duplicates arm: 3 pairs ticked on page 1 and 2 on page 2 read as "5 pairs selected", but "Supersede instead" rebuilds `items` from the current page's rows only, so the dialog silently offers 2 and the other 3 are dropped with no message. Both are the selection set and its data disagreeing about which population is live.

- **The one mechanism:** One `useSelection<T>(rows, { resetKey })` that holds `Map<string, T>` rather than `Set<string>` and clears whenever `resetKey` changes. Carrying the row object means direction can be computed for any selected pair regardless of the current page, so "Supersede instead" acts on everything the toolbar counts; keying on the scope means the count and the enabled state cannot outlive the query that produced them. All three hygiene arms take `resetKey={project}`.
- **The pinning test:** `frontend/src/features/knowledge/__tests__/hygiene-selection.test.tsx` drives from an `ARMS` registry (`duplicates`, `lowConfidence`, `expiring`) exported by `hygiene-queue.tsx`, so a fourth arm forces a case rather than inheriting silence. Per arm, two generated cases: (1) select two rows, change the `project` prop, assert the toolbar count is 0 and every bulk action is disabled; (2) select rows on page 1, advance the page, select more, and assert the payload handed to the bulk mutation contains the union — read off a captured `mutate` argument, not off the rendered dialog text. Assert `ARMS.length >= 3`.
- **Sites:** `frontend/src/features/knowledge/components/hygiene-queue.tsx:450`, `frontend/src/features/knowledge/components/hygiene-queue.tsx:673`
- **Owner decision:** None.


## 6. Singletons

35 findings that genuinely belong to no class and are fixed one at a time.

| Site | What | Effort |
|---|---|---|
| `backend/app/api/routes/config.py:121` | The live orchestrator is swapped into app.state before the transaction authorising it commits | 45m |
| `backend/app/api/routes/repos.py:370` | DELETE /repos/{repo_id}/tasks/{task_id} cancels a task belonging to another repo | 60m |
| `backend/app/api/spa.py:57` | SPA fallback answers a missing /assets/ chunk with index.html and 200 | 20m |
| `backend/app/api/websocket.py:54` | broadcast holds one global lock across the whole fan-out | 60m |
| `backend/app/database.py:23` | Connect-time pgvector SETs run inside a transaction the handler never commits | 60m |
| `backend/app/services/code_pipeline.py:290` | A forced_files run stamps last_indexed_commit at the post-pull HEAD while indexing the pre-pull drift set | 90m |
| `backend/app/services/code_pipeline.py:667` | The serial parse path has no per-file error isolation, and the parser walkers have no depth bound | 120m |
| `backend/app/services/code_query.py:46` | Code-search RRF key omits repo_id, so same-path hits from different repos merge | 45m |
| `backend/app/services/document_parsers.py:169` | A markdown heading opened inside a list item or blockquote outlives its container | 60m |
| `backend/app/services/job_registry.py:506` | PUT /api/v1/jobs/{key} waits on the per-job lock for the whole run with no 409 path | 45m |
| `backend/app/services/llm.py:434` | A truncated completion records no token counts, though the usage envelope was in hand | 45m |
| `backend/app/services/notifications.py:128` | Telegram job-failure messages interpolate unescaped error text under parse_mode=HTML | 30m |
| `backend/app/services/pipeline.py:92` | The shared feature-flag refresh Task is awaited unshielded | 15m |
| `backend/scripts/benchlib/backfill_attempt_pair_hashes.py:88` | Ledger backfill rewrites the append-only JSONL from parsed rows, deleting killed-run fragments | 45m |
| `extension/src/content-autocapture.js:72` | firstSweep snapshots at document_idle, so a conversation rendered afterwards is captured in full | 120m |
| `frontend/src/features/activity/use-day-events.ts:173` | The day-drill window's `until` is the next midnight and the backend filter is inclusive | 40m |
| `frontend/src/features/chat/hooks/use-chat-stream.ts:116` | A newly created conversation's id is lost when the stream does not reach `done` | 60m |
| `frontend/src/features/code/components/code-canvas.tsx:115` | The canvas announces itself as "Demo code graph" when rendering the real backend graph | 15m |
| `frontend/src/features/code/components/code-canvas.tsx:121` | CodeCanvas does a linear node scan twice per edge on every render | 20m |
| `frontend/src/features/code/components/real-code-graph-view.tsx:456` | Blast-radius risk chip never highlights: the backend returns uppercase, the UI compares lowercase | 20m |
| `frontend/src/features/dashboard/year-heatmap.tsx:26` | The contribution calendar labels every journal event as a captured memory | 30m |
| `frontend/src/features/graph/components/graph-summary.tsx:55` | deriveGraphSummary and similarNeighbors re-run on every pointermove of a panel drag | 40m |
| `frontend/src/features/graph/components/panel-resize-handle.tsx:45` | The resize handle omits touch-action: none and preventDefaults pointerdown | 25m |
| `frontend/src/features/graph/components/panel-resize-handle.tsx:89` | nudge calls onResize then onCommit, and onCommit nulls the state onResize just set | 15m |
| `frontend/src/features/jobs/cron-describe.ts:81` | describeCron drops the weekday / month-day scope on stepped and starred expressions | 60m |
| `frontend/src/features/memories/components/real-memories-view.tsx:64` | Infinite scroll grows `limit` past the server's 500 cap and wipes the list | 40m |
| `frontend/src/features/settings/components/flags-tab.tsx:294` | ArmInput sends out-of-range weights while the sibling TunableInput clamps | 45m |
| `frontend/src/features/settings/components/research-tab.tsx:140` | A non-numeric research budget serialises to JSON null and the route drops it as omitted | 30m |
| `frontend/src/features/setup/components/StepRepoPath.tsx:20` | Confirming a base path runs the repo-detection filesystem walk twice | 40m |
| `frontend/src/features/setup/setupWizardStore.ts:195` | The setup wizard persists every LLM provider API key to localStorage in plaintext | 45m |
| `frontend/src/features/usage/components/usage-charts.tsx:51` | The 24h spend chart labels hourly buckets with a date | 40m |
| `frontend/src/hooks/api/use-hygiene-queue-api.ts:233` | Hygiene bulk supersede/prune change memory lifecycle but invalidate only the hygiene caches | 50m |
| `scripts/publish_production_models.sh:40` | publish_production_models.sh cds into a deleted directory and aborts before its working half | 30m |
| `scripts/release.sh:57` | The version-sync guard is an unanchored substring grep that dependency pins satisfy | 30m |
| `sdks/python/tests/test_surface.py:78` | The class-member whitelist hardcodes Python 3.13-only dunders while the package declares >=3.11 | 20m |

## 6b. Findings that resolve to a decision, not a fix

Two findings have no package and no singleton because there is no fix to specify until
someone chooses what the surface is for. Both are in §7; they are named here so the
coverage arithmetic closes at 194 rather than 192.

| Finding | Site | Decision |
|---|---|---|
| R077 | `frontend/src/features/graph/components/graph-summary.tsx:71` | The Lifecycle bar can only ever draw one band, because `/graph/unified` serves `active` rows only. Widen the route, or delete the section. |
| R121 | `frontend/src/routes/_authenticated.tsx:211` | `ContextChip` is mounted in every authenticated header and its declaration reaches no request body. Wire it into retrieval, or label it as not yet applied. |

## 7. Decision register

These are not implementation choices. Each one changes what the product does, costs
something irreversible, or trades one failure mode for another — and each is stated with a
recommended default so that not answering is also a decision, made visibly.

**Answer the decision before starting the stage that carries it, not during.**

#### D1. R072 fixes two missing DROP FUNCTION lines in 0001_baseline.py's downgrade(). schema_guard hashes the baseline file BY BYTES, so any edit -- including one to a code path production never runs -- makes every deployed database's stamp mismatch and the app refuse to boot until the stamp is re-adopted. Fix now, or fold it into the next baseline regeneration?

**Why it is yours, not the implementer's.** CLAUDE.md requires schema changes to serialise through one owner per epic, and this one converts a two-line fix into a fleet-wide deploy step. The guard has no override flag on purpose, so the cost is paid by whoever deploys next, not by whoever lands the edit.

**Recommended default.** Do not edit the baseline for this alone. Land the upgrade -> downgrade -> upgrade round-trip test now, marked xfail with the two leaked functions named as the reason, and make the two DROP FUNCTION lines part of the next baseline regeneration (which already carries the recreate procedure). If the owner wants it now, the deploy needs only step 4 of docs/runbook-deployment.md -- delete the schema_baseline_sha config row and let the guard re-adopt -- because the upgrade half is unchanged, so the live schema really is identical to the new baseline's output. That shortcut is valid ONLY while the edit is confined to downgrade().

#### D2. R074: twelve columns where the ORM declares NOT NULL and the baseline permits NULL (entities.memory_ids/repo_ids/properties/created_at, entity_relations x5, code_edges.properties, code_graph_nodes.properties, token_blocklist.revoked_at). Close them by tightening the schema, or by relaxing the ORM declarations to match?

**Why it is yours, not the implementer's.** Tightening means regenerating 0001_baseline.py and running the full runbook procedure against every deployed database; relaxing means the models stop asserting an invariant the code arguably relies on (the graph repository inserts through raw SQL, which is the path that could write a NULL array).

**Recommended default.** Land the compare_metadata test now with all thirteen deltas in a dated allowlist, and fix immediately only the one that touches no schema: delete the stale `ix_token_blocklist_jti` declaration from app/models/token_blocklist.py (the baseline dropped that index deliberately as redundant under the UNIQUE). Carry the twelve nullability deltas to the schema freeze, where they become an ordinary additive revision. The test is the deliverable -- after it, a NEW drift cannot land, which is the failure mode that cost production five columns.

#### D3. R049: DeepSeek, OpenAI, Anthropic, Google and z.ai all currently receive the Qwen `/no_think` directive as ordinary prompt text. Setting `appends_no_think=False` for them changes the extraction prompt. Flip it now, or land the quirk field behaviour-preserving and flip on a measured run?

**Why it is yours, not the implementer's.** The F1 baseline and every gate re-measurement are fixed to deepseek-v4-flash; changing the prompt invalidates the comparison, and the gate ledger rules say a prompt change is re-measured, not landed as a cleanup.

**Recommended default.** Add the `appends_no_think` field and set it True on exactly the vendors receiving it today, so the coupling moves into the quirk table with no wire-body change and the AST scan starts enforcing it. Schedule the actual flip as its own change with an F1 re-measurement on deepseek-v4-flash, recorded in the gate ledger.

#### D4. R050: should POST /api/v1/analytics/reprocess-all remain an HTTP route, or move behind the job registry so it holds a per-job lock?

**Why it is yours, not the implementer's.** It is an operator-facing capability; moving it changes how the operator invokes it and whether two concurrent reprocesses are possible, which is a product decision rather than a correctness one.

**Recommended default.** Keep the route, but page it on a (created_at, id) keyset with a bounded window and create tasks per window rather than per corpus. Revisit the job-registry move only if concurrent invocation turns out to matter -- invariant 13's single worker means one process, but not one caller.

#### D5. R154/R159: delete backend/scripts/eval_round3/ entirely, or repair and guard it?

**Why it is yours, not the implementer's.** It is round-3 evaluation history; whether it still has archival or reproduction value is the owner's call, not the reviewer's.

**Recommended default.** Delete it. benchlib's retrieval and extraction harnesses supersede it, run.py and debug_clean.py both fail at import or first attribute read against today's models, and purge_eval.py's first statement can resurrect every superseded memory in whatever database DATABASE_URL resolves to -- on this host, production. If it is kept, it must take assert_destructive_target_allowed, an eval-scoped WHERE clause, a --commit flag defaulting to a dry run, and an explicit MCP target that refuses port 8000.

#### D6. R011: is an estimated `total` acceptable on the paginated semantic search path, or must the door report a true match count?

**Why it is yours, not the implementer's.** A true count means the hybrid channel returns its own pre-slice cardinality -- extra work on every search -- versus a wire change that admits the number is a window size. Both are defensible; the client contract is the owner's.

**Recommended default.** Admit the estimate on the wire: add `total_is_estimate: bool` and a `has_more` derived from whether the over-fetch filled, and keep the keyword fallback's real COUNT reporting `total_is_estimate=False`. The alternative pays a count on every semantic search to fix a page-number display.

#### D7. R058: how far should the pre-setup probe-models door be locked down? The obvious SSRF fix (refuse loopback/link-local/private ranges) would break the product's own documented topology.

**Why it is yours, not the implementer's.** CLAUDE.md records the live embeddings endpoint as Ollama at http://192.168.0.196:11434 and localhost as a normal target, so a private-range refusal breaks the first-run wizard for the intended deployment. Trading that away is a product decision.

**Recommended default.** Keep private and loopback targets reachable, and remove the oracle instead: require an http/https scheme, disable redirects, cap the timeout, and on the UNAUTHENTICATED door collapse every failure to a fixed "probe failed" string so the response no longer discloses the upstream status line, body prefix or connection error. The authenticated twin can keep the detailed error, since it is already behind require_auth.

#### D8. R166: when a provider's base_url or api_kind changes and the body carries no new api_key, should the stored key be cleared or should the write be refused with 409?

**Why it is yours, not the implementer's.** Clearing silently disables every purpose using that provider until the operator re-enters the key; refusing blocks a legitimate endpoint move until they have the key to hand. Which failure is preferable is an operations judgement.

**Recommended default.** Refuse with 409 naming the reason and requiring the api_key in the same request. An operator moving an endpoint has the credential; a purpose silently losing its key fails at the next model call, far from the edit that caused it.

#### D9. R148: what should 'opting in does not back-fill' mean -- a wall-clock cutoff recorded at opt-in, or seed-only on the first stable render of each conversation?

**Why it is yours, not the implementer's.** options.html states the promise to the human at the moment they click, so the mechanism and the copy have to be decided together; the two options make different promises about a conversation opened days after opt-in.

**Recommended default.** Per-conversation seed-only on first stable render, plus the recorded opt-in time as a floor -- it covers both the initial page and the sidebar-navigation case (where the script is not re-injected and today every message is sent), and it keeps the options.html sentence literally true. Update that copy in the same change.

#### D10. The Lifecycle bar in the graph summary can only ever draw one band, because `/graph/unified` serves `active` rows only. Widen the route to carry a `statuses` parameter so superseded and deprecated nodes reach the graph, or delete the Lifecycle section and the status chip?

**Why it is yours, not the implementer's.** Both answers are defensible and they are different products. Widening the route is a backend change to a retrieval-adjacent surface and makes the memory graph show lifecycle, which is a feature decision about what the graph is for — CLAUDE.md describes it as a browsing surface that retrieval does not consult, and adding superseded nodes changes what a reader takes it to mean. Deleting the section removes a shipped affordance. Meanwhile the current state is the worst of the three: a full-width success band reading "active 200" that a reader takes as "nothing in this corpus has been superseded", which is an assertion the surface never observed.

**Recommended default.** Delete the Lifecycle section and the status chip now, and open widening the route as its own task if the graph is wanted as a lifecycle surface. A section that can only draw one band is a claim, not a measurement, and deleting it is reversible in a way that a misread corpus is not.

#### D11. `ContextChip` is mounted in every authenticated page's header and its declaration reaches no request — `useContextStore` has exactly one consumer, the chip itself. Wire `declared.axes` into `MemorySearchRequest.context`, or label the popover as not yet applied to retrieval?

**Why it is yours, not the implementer's.** Wiring it is a retrieval-behaviour change: it makes a header control alter what search and chat return, which is the kind of change CLAUDE.md says must be measured rather than intuited, and the task that owns it (T3.14) has not landed. Leaving it silent is the current state and is worse than either option — an operator declares `env=prod`, sees a solid pill on every page, searches, and gets rows the declaration was supposed to scope, with nothing anywhere saying the control is inert.

**Recommended default.** Label it. Add "not yet applied to retrieval" to the popover and keep the trigger in its inactive style until the declaration is actually read, so the chip stops making a promise the request body does not keep. Wiring waits for the task that owns the measurement.

#### D12. The demo-guard and cancellation packages both want one `useApiQuery` wrapper, which means renaming 81 `useQuery` declarations. Accept that churn once, or keep the per-hook conventions and enforce them with allowlisted AST scans instead?

**Why it is yours, not the implementer's.** This is a house-architecture call with a real trade: the wrapper makes both guards (demo gating and abort-signal threading) unforgettable and removes an entire class, but it touches every data-fetching module in one commit and is hard to review line by line. The scan-only alternative changes almost nothing and still catches the next omission, but leaves the guard copied 81 times, which is the failure mode this whole review is organised around. It also determines whether the two packages land as one change or two.

**Recommended default.** Take the wrapper, once, and land the demo guard and the abort signal in the same migration. The rename is mechanical and typechecked; the alternative preserves exactly the structure that has already taken the demo down twice by the spec's own account.

#### D13. The reachability scan finds 23 unreachable modules totalling 4,295 lines, of which the code-graph family is 9 modules and ~2,900 lines. Delete them, or declare them staged work with an allowlist entry naming the task that lands them?

**Why it is yours, not the implementer's.** Deleting ~4,300 lines is not reversible without a git archaeology step, and someone may be holding the code-graph family as the intended replacement for `features/code/`'s renderer. But keeping it is not free either: it has already drifted on three separate rules independently (the 0.35 the focus model exists to prevent, the FA2 auto-stop, the ruled 409-is-busy behaviour), and every reviewer who opens it spends effort on a path no user reaches.

**Recommended default.** Delete. `features/code/` holds the live code-graph renderer, `JobsPage` + `job-config-sections.tsx` hold everything `jobs-panel.tsx` does, and git holds the rest. Anything genuinely staged gets an allowlist entry with the task name — a declaration, not an absence of callers.

#### D14. `useBufferMonitor` reports "no REST surface yet" although `GET /api/v1/memory-buffer` has shipped. Bind the monitor to the real routes in this pass (stats tiles, the error list, Retry → requeue, Forget → discard), or correct the false claim now and open the binding as its own task?

**Why it is yours, not the implementer's.** It is a scope call between an hour of copy correction and a day of real UI work, and the stake is operational: CLAUDE.md says `error` buffer rows are retained until resolved and triaged over this route, so today a poisoned capture has no UI at all — an operator has to reach the database. Correcting the copy alone makes the gap honest but does not close it.

**Recommended default.** Correct the claim now inside the staged-claims package (30 minutes) and open the binding as its own task. The pinning test then goes red on the claim itself, so the gap cannot quietly persist once the route exists — which is exactly the situation this finding describes.

#### D15. [F03] Should a `local_path` repository update its working tree at all? This plan keeps

**Why it is yours, not the implementer's.** Carried by the grounded fix task; see the plan document for the full statement.

**Recommended default.** Stated in the task's own decision block.

#### D16. [F05] One product-visible choice the repo owner may want to overrule: a reconcile run that dies before `CodePipeline.run` writes its own status now leaves the repository at `status='stale'` with the exception string in `status_message`. `stale` mirrors what the pipeline's own failure handler writes for a repo that still has a graph to serve, and it keeps the repo claimable by the next tick — but it is a user-visible badge in the repositories view for a failure that produced no partial index. The alternatives are `error` (louder, but the pipeline reserves that for a repo with nothing to keep) or restoring `ready` (silent, and hides a repo whose drift nothing can reconcile). Nothing else in the task is open.

**Why it is yours, not the implementer's.** Carried by the grounded fix task; see the plan document for the full statement.

**Recommended default.** Stated in the task's own decision block.

#### D17. [F07] Should `backup.sh` also stop passing `--clean --if-exists`? Once restore.sh

**Why it is yours, not the implementer's.** Carried by the grounded fix task; see the plan document for the full statement.

**Recommended default.** Stated in the task's own decision block.

#### D18. [F08] Only one, and it is scope rather than a blocker: after this fix a failed backup is loud but still only in the systemd journal — `darkmem-backup.service` has no `OnFailure=` unit and nothing notifies the operator. Fourteen silent failed nights now leave the operator with 14 genuine but increasingly stale dumps instead of 14 empty ones, which is strictly better but still not a signal. Whether to add an `OnFailure=` notification unit (or a healthcheck-style touchfile) is the repo owner's call and is deliberately not part of this task.

**Why it is yours, not the implementer's.** Carried by the grounded fix task; see the plan document for the full statement.

**Recommended default.** Stated in the task's own decision block.

#### D19. [F09+F10] One adjacent defect found while verifying this, deliberately NOT folded into the

**Why it is yours, not the implementer's.** Carried by the grounded fix task; see the plan document for the full statement.

**Recommended default.** Stated in the task's own decision block.

#### D20. [F11+F15] Two, both for the repo owner.

**Why it is yours, not the implementer's.** Carried by the grounded fix task; see the plan document for the full statement.

**Recommended default.** Stated in the task's own decision block.

#### D21. [F13] Adjacent bug found while reading the same function, deliberately NOT fixed here because it needs an owner call on what the field is for.

**Why it is yours, not the implementer's.** Carried by the grounded fix task; see the plan document for the full statement.

**Recommended default.** Stated in the task's own decision block.

#### D22. [F14] Whether the backend's two error yields in backend/app/services/chat.py (lines 148 and 192) should also carry `conversation_id`. Without it, a turn that fails on the very first message of a brand-new thread leaves the frontend unable to name the conversation the backend just created and committed — this task's unconditional sidebar-list invalidation surfaces the thread but cannot open it. Adding the field is a two-line change but widens the chat SSE contract, so it is left for the repo owner rather than folded in here.

**Why it is yours, not the implementer's.** Carried by the grounded fix task; see the plan document for the full statement.

**Recommended default.** Stated in the task's own decision block.

#### D23. [F16] CORS_ORIGINS only accepts a JSON array, because config.py types it as list[str]

**Why it is yours, not the implementer's.** Carried by the grounded fix task; see the plan document for the full statement.

**Recommended default.** Stated in the task's own decision block.

#### D24. [F17] None blocking. One adjacent defect worth the owner's attention, deliberately left out of this task: the detail panel's close button (`frontend/src/features/graph/components/graph-detail-panel.tsx:60-68`) is an icon-only `<Button>` wrapping a bare lucide `<X />` with no `aria-label` and no text, so it has no accessible name at all — a screen reader announces it as an unlabelled button, and the test above has to reach it positionally (`within(panel).getAllByRole("button")[0]`) rather than by name. Adding `aria-label="Close details panel"` is a one-line fix but is a different defect from F17 and belongs in its own change.

**Why it is yours, not the implementer's.** Carried by the grounded fix task; see the plan document for the full statement.

**Recommended default.** Stated in the task's own decision block.

#### D25. [F18] Should a press that drifts a pixel or two horizontally also be treated as a click? The fix as written closes the reported bug (zero horizontal movement) exactly, but a 1px accidental drag still overwrites a stored 800px preference with ~481px, because by the component's definition that is a resize. Closing it means a slop threshold — ignore the drag until the pointer has moved, say, 3px from where it went down — which is standard practice but does make sub-threshold fine adjustments impossible with the mouse (the arrow keys already move in 24px steps, so there is no fine keyboard path either). That is a feel decision for the repo owner, not something to slip in under a correctness fix, so it is not in the implementation above.

**Why it is yours, not the implementer's.** Carried by the grounded fix task; see the plan document for the full statement.

**Recommended default.** Stated in the task's own decision block.


## 8. Stage detail

### Stage 0 — Land the in-flight working tree

**Goal.** master carries the graph/test-harness work and the code_pipeline commit-on-release fix that later stages edit, so every subsequent task starts from a clean, tracked base.

**Contains.** `F04`, `working-tree: frontend graph work (panel-resize.ts, panel-resize-handle.tsx, graph-summary*.ts(x), focus-model.ts, use-graph-layout.ts, graph-2d-renderer.tsx, graph-detail-panel.tsx, mini-graph.tsx, real-memory-graph-page.tsx)`, `working-tree: frontend test harness (src/test/pending-timers.ts, src/test/setup.ts, src/test/__tests__/)`

**Why here.** Nothing can be sequenced before this. `git status` shows frontend/src/features/graph/lib/panel-resize.ts, .../components/panel-resize-handle.tsx and frontend/src/test/pending-timers.ts as UNTRACKED — F17, F18 and F19 all edit files that do not exist on master, so scheduling them first would mean re-creating work that is already written. Separately, backend/app/services/code_pipeline.py and backend/tests/test_push_webhook.py are already MODIFIED with exactly F04's fix (the `await self.session.flush()` on the up-to-date short-circuit is already changed to `await self.session.commit()` with a WHY comment). Treating F04 as unstarted work would produce a duplicate diff against a dirty file. Split the tree into atomic commits by concern rather than one blob; delete or gitignore the untracked .playwright-mcp/ scratch directory instead of committing it.

**Ships as.** Branch off master, several atomic commits (fix(code-index): commit the up-to-date claim release / feat(graph): ... / test(frontend): ...). Fast-forward merge. REDEPLOY REQUIRED — backend/app and frontend/src both change.

**Gate.** `./scripts/gate.sh`

### Stage 1 — Stop the two unrecoverable data losses

**Goal.** darkmem can no longer destroy an operator's own git checkout, a restore can no longer drop a live database it then fails to repopulate, a failed backup can no longer masquerade as a good one, and no eval script can purge whatever DATABASE_URL happens to point at.

**Contains.** `F03`, `F07`, `F08`, `harness-ambient-database`

**Why here.** These are the only findings whose failure mode has no undo. F03 hard-resets a working tree darkmem does not own; F07 drops a live database before it knows the dump will restore; F08 leaves a truncated dump under the keep name so the retention prune (BACKUP_KEEP=14) then discards the last good one. harness-ambient-database belongs with them rather than in the medium tail: backend/scripts/eval_round3/purge_eval.py opens the ambient DATABASE_URL with no destructive-target guard, which on this host — where the same machine runs production Postgres — is the same class of accident as F07. It also collides with nothing, so it is free to carry here. Order inside the stage: F07 before F08, because F07's open decision (whether backup.sh should stop emitting `--clean --if-exists`) is a question about backup.sh that only makes sense once restore.sh recreates the database, and F08 is the change that will be sitting in that file.

**Ships as.** One branch per finding off stage 0's tip, merged in the order F03 → F07 → F08 → harness-ambient-database. REDEPLOY REQUIRED, but only because of F03: scripts/backup.sh, scripts/restore.sh and backend/scripts/ are not copied into the image (the Dockerfile takes backend/app, backend/migrations, alembic.ini, entrypoint.sh and the SPA dist only), so F07, F08 and the harness guard change operator procedure and nothing the container runs. Confirm F03 in the running image with `docker exec darkmem-prod-darkmem-1 grep -n 'ff-only' app/services/repo_manager.py`.

**Gate.** `./scripts/gate.sh`

### Stage 2 — Make the shipped image able to index a repository

**Goal.** A container built from this tree can clone and index a repository at all: git exists on PATH and /app/data/repositories is writable by uid 100. CORS stops falling back to two hardcoded localhost origins.

**Contains.** `F09+F10`, `F16`

**Why here.** F09 and F10 are one deploy or neither — git absent and the clone directory unwritable are two halves of the same symptom, and shipping either alone leaves repository indexing broken in the image while the tree looks fixed. Verified against the tree: the runtime stage installs no git, and REPOS_BASE_DIR is `./data/repositories` (repo_manager.py:19) relative to WORKDIR /app, a path the image never creates — so docker-compose.yml's `repo_data:/app/data/repositories` mount materialises a root-owned volume that the `app` user cannot write. F16 rides along because it is the other change to the running artifact's boot configuration (main.py:816's `settings.cors_origins or ["http://localhost:3000", "http://localhost:5173"]`, plus docker-compose.yml and .env.example) and batching it here buys one deploy instead of two. Ops does not parallelise: this stage changes the artifact every later stage is verified against, so it merges alone and nothing else merges during its deploy window.

**Ships as.** One branch, F09+F10 committed before F16 (both append to backend/tests/test_deployment_artifact.py and would otherwise conflict mechanically). REDEPLOY REQUIRED and it is the point of the stage: ./scripts/gate.sh --full → DARKMEM_PUSH=0 ./scripts/build-push.sh → docker compose up -d → wait for healthy. Then confirm in the image, not the tree: `docker exec darkmem-prod-darkmem-1 git --version`, `docker exec -u app darkmem-prod-darkmem-1 touch /app/data/repositories/.wcheck`, and the CORS change on the built file. compose reuses an image whose tag did not move, so a skipped build redeploys the old bits and still reports Started. Never DARKMEM_PUSH=1 — image push is CI-only.

**Gate.** `./scripts/gate.sh --full`

### Stage 3 — Backend correctness singletons

**Goal.** The article-synthesis rotation cursor cannot be lost mid-run, a code_reconcile tick takes the indexing claim it needs, and MCP code_symbol stops raising MissingGreenlet on every hit.

**Contains.** `F01+F02`, `F05`, `F06`

**Why here.** Three independent backend fixes with no shared files between them, all cheap, all behind the ops stage because F05 is the third writer of backend/app/services/repo_manager.py and must not be rebasing while stage 2 edits it. F05 also needs stage 2 landed for its own verification to mean anything: a reconcile run that cannot clone because git is missing never reaches the claim path this task repairs. F06 is a 20-minute fix on a door that is currently broken for every caller, so it should not sit behind the medium tail.

**Ships as.** Three parallel branches off stage 2's tip, merged in any order (no shared files). REDEPLOY REQUIRED — all three are backend/app.

**Gate.** `./scripts/gate.sh`

### Stage 4 — Frontend correctness singletons

**Goal.** Settings saves that the backend refuses are visible, demo mode stops 401-redirecting off the Settings tabs, a failed article read renders as a failure, the edit-repository dialog shows the repository the operator picked, chat stream errors surface, and the graph detail panel behaves in a narrow split.

**Contains.** `F19`, `F17`, `F18`, `F11+F15`, `F12`, `F13`, `F14`

**Why here.** Developed in parallel with stages 1–3 off stage 0's tip — frontend and backend share no files here — but merged after stage 2's deploy is confirmed, so the browser verification happens against an image that already carries the ops change. Order inside the stage matters in two places. F19 goes FIRST: it tightens the pending-timer sweep to track setInterval, which can newly fail existing suites that leak intervals, and every later frontend task should be written against the strict sweep rather than have it dropped on top. F17 goes before F18: F18's panel-resize-handle.tsx consumes the clamp/float logic F17 changes in panel-resize.ts. F12 goes before the read-state package in stage 12 because it establishes the pattern that package generalises across 27 surfaces; F11+F15 goes before the demo-guard package in stage 11 for the same reason and in the same files.

**Ships as.** One branch per finding, merged F19 → F17 → F18 → then F11+F15, F12, F13, F14 in any order. REDEPLOY REQUIRED — frontend/src ships in the image as the built SPA; confirm the new bundle is serving rather than the previous one.

**Gate.** `./scripts/gate.sh --full`

### Stage 5 — Auth and outbound-request safety

**Goal.** The WebSocket handshake validates a token through the one session validator (password-change arm included), and a caller-supplied base_url can no longer steer a server-side fetch that carries a stored provider key.

**Contains.** `one-session-token-validator`, `probe-target-and-credential-binding`

**Why here.** First stage of the medium tail, promoted above everything else in it on severity rather than on the packaged label. probe-target-and-credential-binding is server-side request forgery with credential exposure: routes/llm_providers.py:122/204 and routes/setup.py:95/107 fetch an operator-supplied URL, once unauthenticated (the setup door is trust-on-first-use, gated only by require_uninitialized) and once carrying the stored api_key. one-session-token-validator is an auth bypass window — the WebSocket path hand-rolls JWT validation at websocket.py:86 and omits the `iat` arm that auth.py:117 uses to revoke every pre-change token, so a password change does not close a live socket. Both are small and neither collides with anything already merged. probe-target must land before vendor-quirk-leakage in stage 9: both edit backend/app/services/llm_quirks.py, and the quirk table's model-probe endpoint is exactly the field the SSRF fix constrains.

**Ships as.** Two parallel branches, merged in either order. REDEPLOY REQUIRED — backend/app.

**Gate.** `./scripts/gate.sh`

### Stage 6 — Subtraction and cheap structure

**Goal.** Five unreachable modules are gone, the feature-flag wire roster is derived rather than hand-listed, GIN indexes are actually reachable, the embedder registry is read with its retired/newest ordering, and job state stops overriding the registered constant.

**Contains.** `dead-modules-import-closure`, `feature-flag-wire-roster`, `gin-unusable-array-predicates`, `embedder-registry-read-discipline`, `job-registry-row-vs-registry`, `orphan-on-delete-no-fk`, `gold-retired-predicate`, `benchlib-unexercised-branches`

**Why here.** Deletion and mechanical rewrites before the behavioural packages, so the later stages have less surface to touch. dead-modules-import-closure removes app/services/entity_detector.py, entity_registry.py, dialect.py, ml_seed.py and named_bindings/wildcard_synthesis.py — ml_seed.py in particular describes a seeding path the baseline removed, and leaving it in place means the stage 14 prose pass has to decide whether to correct comments in a module nothing imports. embedder-registry-read-discipline precedes per-row-io in stage 10: both edit backend/app/repositories/vector.py and correctness (picking the stale partition) comes before the per-page batching. orphan-on-delete-no-fk sits here because backend/app/services/repo_manager.py:313 is its site and stage 3's F05 was that file's last writer. The two benchlib packages carry no artifact change at all and ride along for free.

**Ships as.** Parallel branches; only vector.py and repo_manager.py have downstream claimants, so merge order within the stage is free. REDEPLOY REQUIRED — backend/app modules are deleted and changed. The benchlib and gold packages alone would need none (backend/scripts is not in the image).

**Gate.** `./scripts/gate.sh`

### Stage 7 — The memory primitive and the door contracts

**Goal.** The superseded_by demotion lives in the delete primitive instead of four callers, both sides of every compared value are normalised, a door rejects with 422 what the layer beneath would 500 on, a truncated result says so, and the two sibling doors pass the same filter set.

**Contains.** `memory-delete-demotion`, `half-applied-normalisation`, `door-accepts-what-the-layer-below-refuses`, `capped-result-reported-as-complete`, `sibling-door-parameter-parity`

**Why here.** This is the longest collision chain in the programme and it needs one owner working it front to back: backend/app/services/memory.py is claimed by four of these five packages (873/895, 467, 548/713, 615) and backend/app/repositories/relational.py by two (97, 156). Sequenced so the primitive moves before its callers are re-read: memory-delete-demotion → half-applied-normalisation → door-accepts → capped-result → sibling-door-parameter-parity. door-accepts precedes capped-result on both api/routes/graph.py and api/routes/pipeline_failures.py because rejecting a bad value is a smaller diff than adding truncation fields to the same response, and the truncation work should land on routes that already validate. sibling-door-parameter-parity comes last in the chain because it is the one that touches backend/app/api/mcp/server.py (after stage 3's F06) and backend/app/services/pipeline.py (before stage 8's embed-length-contract touches pipeline.py:453). This stage changes response models, so the OpenAPI document moves — the SDKs are generated off the live document and the generator refuses when a verb names a field the contract does not serve, so re-run `make generate` in sdks/ in the same commit rather than letting the gate's sdk arms discover it.

**Ships as.** ONE branch worked sequentially by one owner, not five parallel lanes — five lanes on memory.py conflict every time. REDEPLOY REQUIRED — backend/app.

**Gate.** `./scripts/gate.sh --full`

### Stage 8 — Loops that advance, errors that roll back

**Goal.** One vector per input text is asserted in the embed primitive instead of in five copies, a caught database error no longer poisons the next statement on the same session, gathered exceptions are read rather than discarded, and the batch sweeps advance their own selection predicate.

**Contains.** `embed-length-contract`, `swallowed-db-error-poisons-the-transaction`, `gather-exception-discarded`, `sweeps-that-never-advance`

**Why here.** These four are one chain on two files. backend/app/services/reembed.py is claimed by embed-length-contract (452, 575) and sweeps-that-never-advance (420, 545) — adjacent lines in the same loops — and backend/app/services/analytics.py by three of them (33/147, 184, 238). Order inside the stage: embed-length-contract first (it is the enabling assertion and the lowest-risk diff), then swallowed-db-error, then gather-exception-discarded, then sweeps-that-never-advance last. The rollback fix must precede the sweep repair for a concrete reason, not tidiness: a sweep that currently never advances re-selects the same rows and mostly re-runs the same statements, so once it does advance it will execute far more statements per session and a transaction left poisoned by a swallowed error becomes a live failure mode rather than a latent one. embed-length-contract also takes backend/app/services/code_pipeline.py:1445 (after stage 0's F04) and backend/app/services/llm.py:313/363 (before stage 9's vendor-quirk-leakage takes 647/688 in the same file).

**Ships as.** One branch worked sequentially — reembed.py and analytics.py cannot take concurrent lanes. REDEPLOY REQUIRED — backend/app.

**Gate.** `./scripts/gate.sh --full`

### Stage 9 — The LLM boundary and per-request fan-out

**Goal.** Vendor-specific behaviour is back inside the quirk table where the AST scan can see it, model responses are shape-checked before they are parsed, article eligibility and article authorship count the same bucket, and per-request fan-out is bounded by something other than the row limit.

**Contains.** `vendor-quirk-leakage`, `llm-response-shape-guards`, `article-subject-basis`, `unbounded-fanout-on-a-request-path`

**Why here.** backend/app/services/article_synthesis.py is claimed at the SAME LINE (488) by llm-response-shape-guards and unbounded-fanout-on-a-request-path, plus at 863 by article-subject-basis and at 887/1741 by the stage 8 package — so this file needs one hand and a stated order: llm-response-shape-guards → article-subject-basis → unbounded-fanout. The fan-out bound must be applied last because article-subject-basis changes which subject set is being fanned out over; bounding the wrong set and then changing the set is two chances to get the bound wrong. vendor-quirk-leakage follows stage 5's probe-target fix in llm_quirks.py and stage 8's embed-length-contract in llm.py. Fan-out matters more here than the site count suggests: invariant 13 fixes this deployment at exactly one uvicorn worker, so unbounded per-request work has no second process to absorb it.

**Ships as.** One branch worked sequentially by one owner. REDEPLOY REQUIRED — backend/app. Note the F1 baseline and every gate re-measurement are fixed to deepseek-v4-flash; a re-measurement on -pro is not comparable.

**Gate.** `./scripts/gate.sh --full`

### Stage 10 — Derived read state

**Goal.** Clearing one review opener re-derives review_state, page renders stop paying per-row IO, rows enter fusion and the injection journal carrying the identity their consumers read, and the code-graph resolver arms either execute or say they do not.

**Contains.** `review-state-derivation`, `per-row-io-on-a-page-render`, `composition-row-contract`, `resolver-arms-that-never-execute`

**Why here.** Last of the backend behavioural work, after the primitives and the doors have settled. review-state-derivation precedes per-row-io and the stage 14 prose pass on backend/app/services/review_queue.py (its own site, then 217, then 118). per-row-io follows embedder-registry-read-discipline from stage 6 on backend/app/repositories/vector.py:638 — correctness of which partition is read before batching how it is read. One invariant to hold while doing review-state-derivation: invariant 15's tree-wide source scan matches any line naming the ladder module, prose included, which is exactly why app/services/ladder_config.py was split out of verification_ladder.py — resolve thresholds through ladder_config, and do not put an app.services.contradiction_veto import on a read surface.

**Ships as.** Parallel branches except review_queue.py and vector.py, which serialise. REDEPLOY REQUIRED — backend/app.

**Gate.** `./scripts/gate.sh`

### Stage 11 — Frontend authority layer

**Goal.** 4,295 lines of unreachable code are gone, a transport failure stops being reported as a sign-out, superseded requests are cancelled, the demo guard has one authority instead of nine copies, and the query-key registry scans the whole tree.

**Contains.** `unreachable-modules-and-exports`, `auth-failure-classified-as-a-verdict`, `no-request-is-ever-cancelled`, `demo-guard-per-call-site`, `query-key-registry-under-enumerates`

**Why here.** unreachable-modules-and-exports goes first in the stage and first among all remaining frontend work: it deletes files that read-state-rendered-as-a-result (27 sites), capped-list and query-key-registry would otherwise spend effort on, and the widened key scan should not enumerate keys in modules about to be removed. The load-bearing order is inside frontend/src/lib/api.ts: auth-failure-classified-as-a-verdict (103, 112) MUST land before no-request-is-ever-cancelled (72). Introducing AbortController first, while a failed fetch still resolves to "you are not signed in", converts every cancelled request into a spurious logout — the cancellation fix would ship a worse bug than the one it closes. demo-guard-per-call-site follows stage 4's F11+F15 in the same files and is where F11+F15's deferred hazard gets closed: purpose-dialog.tsx fires probe.mutate on open, and a mutation cannot be gated by an `enabled` flag, so it needs the authority this package builds. no-request-is-ever-cancelled also follows F14 on use-chat-stream.ts:38.

**Ships as.** One branch, merged in the stated order (unreachable → auth-failure → no-request-cancelled → demo-guard → query-key-registry). REDEPLOY REQUIRED — frontend/src.

**Gate.** `./scripts/gate.sh`

### Stage 12 — Frontend truth in rendering

**Goal.** A read that failed or never ran stops rendering as an observed absence, a capped list stops being labelled with a total nobody sent, a settings write reports on the response rather than the click, and a bulk selection cannot act on rows the user cannot see.

**Contains.** `read-state-rendered-as-a-result`, `capped-list-rendered-as-a-total`, `write-announced-before-it-resolves`, `selection-outlives-the-rows-it-indexes`, `one-request-per-keystroke`, `reset-respells-the-defaults`, `focus-model-recomputed-at-the-call-site`, `confirmgate-triggers-keyboard-unreachable`, `demo-fixtures-assert-what-the-product-forbids`, `copy-claims-a-shipped-thing-is-unshipped`

**Why here.** The largest frontend stage and deliberately last, because every package in it edits surfaces the earlier stages just changed. read-state-rendered-as-a-result generalises stage 4's F12 across 27 sites and must follow it on articles-tab.tsx; capped-list-rendered-as-a-total then takes articles-tab.tsx:243 and the graph surfaces stage 0 committed. write-announced-before-it-resolves follows demo-guard on use-flags-tab-binding.ts and query-key-registry on use-maintenance-tab-binding.ts:70 — the registry has to enumerate the keys before the write path starts invalidating on a resolved response. reset-respells-the-defaults follows F17 on real-memory-graph-page.tsx:163. copy-claims-a-shipped-thing-is-unshipped goes at the very end of the stage for the same reason the backend prose pass goes at the end of the programme: it rewrites operator-facing copy asserting what exists, and anything merging after it invalidates the copy again. demo-fixtures-assert-what-the-product-forbids should follow stage 6's feature-flag-wire-roster so the demo fixture stops encoding a partial flag roster.

**Ships as.** Parallel branches where files are disjoint; articles-tab.tsx, the settings bindings and the graph panels each serialise. REDEPLOY REQUIRED — frontend/src.

**Gate.** `./scripts/gate.sh --full`

### Stage 13 — Extension auto-capture reconciler

**Goal.** One authority owns the auto-capture state, so the badge cannot assert a mode that is not running.

**Contains.** `extension-autocapture-one-reconciler`

**Why here.** Fully independent lane — extension/ shares no file with anything else in the programme and the browser shell is not in the runtime image, so this can be developed at any point after stage 0 and merged whenever it is ready. Placed here only because it is the lowest-urgency item with no claimants waiting on it. The gate's `extension tests` arm (Node's built-in runner, no dependency tree) is what covers it; nothing else in the floor touches this directory.

**Ships as.** One branch, merged independently. NO REDEPLOY — extension/ is not copied into the image and is distributed as a browser shell.

**Gate.** `./scripts/gate.sh`

### Stage 14 — The prose truth pass

**Goal.** No comment or docstring in backend/app asserts a property the code lacks, describes a caller that does not exist, or says a shipped subsystem is unshipped.

**Contains.** `prose-that-states-a-property-the-code-lacks`

**Why here.** Must be last among everything that changes backend behaviour, and that is the whole argument for its position. It rewrites comments at main.py:570 (after stage 2's F16), verification_judge.py:292 (after stage 6's one-definition-two-copies at 625), review_queue.py:118 (after stage 10's review-state-derivation and per-row-io), content_surfaces.py:335 and pin_suggestions.py — every one of those files is edited by an earlier stage, so landing the prose pass first would guarantee it describes a tree that no longer exists by the time the programme finishes. This repository has repeatedly paid for stale prose: the job roster read "Sixteen" through four landings and three independent lanes rediscovered it, which is why the roster is now derived from app/main.py's AST rather than written down.

**Ships as.** One branch, docs(...) commits. REDEPLOY REQUIRED in the letter of the rule — backend/app bytes change — though nothing the image does changes; batch it with whatever else is deploying rather than cutting a deploy for comments alone.

**Gate.** `./scripts/gate.sh`

### Stage 15 — Baseline and ORM integrity

**Goal.** Something compares the single baseline revision against the ORM models, and the drift between them is resolved rather than only reported.

**Contains.** `baseline-integrity-derived-tests`

**Why here.** Alone, last, one owner, no concurrent lane of any kind. backend/migrations/versions/0001_baseline.py is a single shared mutable file that is regenerated in place and never appended to — two lanes editing it conflict every time, and the gate asserts exactly one revision (the `schema-frozen` tag does not exist, so the assertion is live). The stage carries a decision that must be settled before any code is written: if the drift at token_blocklist.py:20 against baseline lines 1093 and 1513 is fixed by correcting the ORM MODEL, this is an ordinary backend change. If it is fixed by regenerating the BASELINE, it is a full schema event — drop and recreate every deployed database, re-seed admin_password_hash, all eight llm_purpose_configs rows and the two provider rows, and note that llm_seed.py does not reproduce the verification row at the qualified judge identity fd39e7b2c47fa375, whose entailment record is expensive to re-mint. app/schema_guard.py stamps a hash of the baseline file and refuses to start when it disagrees with the database, with no override flag, so a regenerated baseline against a database that was not recreated is a container that will not boot.

**Ships as.** One branch, one owner, merged when nothing else is in flight. REDEPLOY REQUIRED, and if the baseline is regenerated the deploy includes recreating and re-seeding the production database per docs/runbook-deployment.md — not a plain `docker compose up -d`.

**Gate.** `./scripts/gate.sh --full`


## 9. Collision register

Every file two or more tasks edit. The rule is one owner per file per stage; the ones that
bite are the shared mutable files, where two lanes conflict every time.

| File | Claimants | Resolution |
|---|---|---|
| `backend/app/services/repo_manager.py` | 4 | Four claimants, the worst backend collision. Order: F03 (stage 1, the data-loss fix) → F09+F10 (stage 2, the clone-directory half) → F05 (stage 3, the indexing claim) → orphan-on-delete-no-fk (stage 6, line 313). One owner per stage; never two lanes at once. |
| `backend/tests/test_deployment_artifact.py` | 3 | All three append test functions to a 194-line file. F07 first (stage 1). Inside stage 2, F09+F10 commits before F16 — otherwise the two append at the same offset and conflict mechanically for no semantic reason. |
| `backend/tests/test_repos.py` | 2 | F03 first (stage 1). F09+F10's assertions about the container clone path land on top in stage 2. |
| `scripts/backup.sh` | 2 | F07 does not edit the file but its open question (drop `--clean --if-exists` from future dumps) lands in it. Merge F07 first so the owner answers that question against a restore path that already recreates the database. |
| `backend/app/services/code_pipeline.py` | 3 | F04's diff is ALREADY in the working tree uncommitted — commit it in stage 0 rather than rewriting it. Then embed-length-contract (1445, stage 8) → unbounded-fanout (1094, stage 9). |
| `backend/app/services/memory.py` | 4 | Four packages, four line ranges, one file. All in stage 7 under ONE owner working sequentially: memory-delete-demotion (873/895) → half-applied-normalisation (467) → capped-result (548/713) → sibling-door (615). Splitting these into parallel lanes conflicts every time. |
| `backend/app/repositories/relational.py` | 2 | memory-delete-demotion first (line 97, moving the demotion into the delete primitive), then half-applied-normalisation (line 156). |
| `backend/app/api/routes/graph.py` | 2 | door-accepts first (68, 77), then capped-result (27 plus schemas/graph.py:37). Validate at the door before you add truncation fields to what the door returns. |
| `backend/app/api/routes/pipeline_failures.py` | 2 | Same pairing and same order: door-accepts (62) then capped-result (155). |
| `backend/app/services/reembed.py` | 2 | Adjacent lines in the same loops (452/575 vs 420/545). embed-length-contract first — assert the postcondition in the primitive, then repair the loop that calls it. |
| `backend/app/services/analytics.py` | 3 | All three in stage 8, in this order: swallowed-db-error (238) → gather-exception-discarded (184) → sweeps-that-never-advance (33, 147). The rollback fix must precede the sweep repair, because a sweep that finally advances runs many more statements per session and turns a poisoned transaction from latent into live. |
| `backend/app/services/llm.py` | 2 | Different functions (313/363 embed path vs 647/688 dispatch path) but one file. embed-length-contract first (stage 8), vendor-quirk-leakage second (stage 9). |
| `backend/app/services/llm_quirks.py` | 2 | probe-target first (stage 5, line 177 — the model-probe endpoint is the field the SSRF fix constrains), vendor-quirk-leakage second (stage 9, restructuring the table around it). |
| `backend/app/services/article_synthesis.py` | 4 | llm-response-shape-guards and unbounded-fanout claim the SAME LINE (488) — they cannot be two tasks in two hands. Order: swallowed-db-error (887, 1741; stage 8) → llm-response-shape-guards (488) → article-subject-basis (863) → unbounded-fanout (488). The fan-out bound goes last because article-subject-basis changes the set being fanned out over. |
| `backend/app/services/review_queue.py` | 3 | review-state-derivation (stage 10) → per-row-io (217, stage 10) → prose (118, stage 14). Behaviour, then performance, then the comment describing both. |
| `backend/app/repositories/vector.py` | 2 | embedder-registry-read-discipline first (494/543/755/766, stage 6): choosing the right partition is correctness, batching how it is read is performance. per-row-io takes 638 in stage 10. |
| `backend/app/services/verification_judge.py` | 2 | one-definition-two-copies first (625, stage 6), prose second (292, stage 14). |
| `backend/app/main.py` | 2 | F16 first (stage 2, the CORS fallback at line 816), prose last (570, stage 14). |
| `backend/app/api/mcp/server.py` | 2 | F06 first (stage 3 — the door currently raises on every hit), sibling-door-parameter-parity second (195, stage 7). |
| `backend/app/services/job_runners.py` | 2 | F05 first (stage 3, the reconcile claim), memory-delete-demotion second (385, stage 7 — that call site is one of the four callers the demotion moves out of). |
| `backend/app/services/pipeline.py` | 2 | sibling-door-parameter-parity first (1315, stage 7), embed-length-contract second (453, stage 8) — a consequence of stage 7 preceding stage 8, not of the lines themselves. |
| `backend/migrations/versions/0001_baseline.py` | 1 | Sole claimant, and it stays that way. The baseline is a single shared mutable file regenerated in place; it serialises through one owner with no concurrent lane, in stage 15, and only after the owner decides whether the fix corrects the ORM model or regenerates the baseline (the second recreates every deployed database). |
| `frontend/src/features/graph/lib/panel-resize.ts` | 2 | The file is UNTRACKED today. Stage 0 commits it; F17 then edits it in stage 4. F18's panel-resize-handle.tsx consumes it, so F17 before F18. |
| `frontend/src/test/pending-timers.ts` | 2 | Also UNTRACKED. Stage 0 commits it, F19 extends it to setInterval first thing in stage 4 — before the rest of the frontend work, so later suites are written against the strict sweep. |
| `frontend/src/features/memory-graph/components/real-memory-graph-page.tsx` | 3 | Modified uncommitted today. Stage 0 → F17 (stage 4) → reset-respells-the-defaults (163, stage 12). |
| `frontend/src/lib/api.ts` | 2 | THE ORDER IS LOAD-BEARING: auth-failure-classified-as-a-verdict (103, 112) MUST land before no-request-is-ever-cancelled (72). Adding cancellation while a failed fetch still resolves to "you are not signed in" turns every cancelled request into a spurious logout. |
| `frontend/src/features/chat/hooks/use-chat-stream.ts` | 2 | F14 first (stage 4, surfacing the stream error), no-request-is-ever-cancelled second (38, stage 11). |
| `frontend/src/features/knowledge/components/articles-tab.tsx` | 3 | F12 first (stage 4) — it is the pattern the 27-site package generalises. Then read-state (stage 12), then capped-list (243, stage 12). |
| `frontend/src/features/settings/use-flags-tab-binding.ts` | 3 | F11+F15 first (stage 4). The file already carries the copied `!DEMO` guard at lines 279–301 that demo-guard-per-call-site (285) hoists in stage 11. write-announced-before-it-resolves lands last (stage 12). |
| `frontend/src/features/settings/components/providers-panel.tsx` | 2 | F11+F15 first (stage 4), demo-guard second (stage 11). Same pairing for research-tab.tsx. purpose-dialog.tsx has only one claimant — demo-guard — because F11+F15 explicitly deferred it: its probe.mutate on open cannot be gated by an `enabled` flag. |
| `frontend/src/hooks/api/use-config-api.ts` | 2 | F11+F15 first (stage 4), query-key-registry second (75, stage 11). |
| `frontend/src/features/settings/use-maintenance-tab-binding.ts` | 2 | query-key-registry first (70, stage 11), write-announced second (85/92/99, stage 12) — the registry must enumerate the keys before the write path starts invalidating on a resolved response. |
| `frontend/src/features/graph/components/graph-detail-panel.tsx, mini-graph.tsx, graph-summary-stats.ts, focus-model.ts, graph-2d-renderer.tsx` | 3 | All modified or untracked today. Stage 0 commits them; capped-list (graph-detail-panel 166/406, mini-graph 70, graph-summary-stats 171) and focus-model-recomputed (graph-2d-renderer 492/550, focus-model 11) both land in stage 12 and touch disjoint files within that set, so they can run as two lanes there. |
| `NOT A COLLISION: repositories/graph.py vs services/graph.py vs api/routes/graph.py` | 4 | Three different files sharing one basename. gin-unusable owns backend/app/repositories/graph.py (163/233/501/512/598/609), unbounded-fanout owns backend/app/services/graph.py (224/250), and only door-accepts and capped-result share backend/app/api/routes/graph.py. Do not serialise these four on a name match. |

## 10. Ordering notes

- The working tree is dirty and three tasks depend on it. frontend/src/features/graph/lib/panel-resize.ts, .../components/panel-resize-handle.tsx and frontend/src/test/pending-timers.ts are UNTRACKED, so F17, F18 and F19 edit files that do not exist on master. Stage 0 exists to land that work; nothing else can be scheduled until it does.
- F04 is already written. backend/app/services/code_pipeline.py and backend/tests/test_push_webhook.py are MODIFIED in the working tree with exactly the fix the task describes — the flush on the up-to-date short-circuit is already a commit, with a WHY comment about _spawn_repo_index closing its session without committing. Commit it in stage 0 rather than re-implementing it. Also: .playwright-mcp/ is untracked scratch — delete or gitignore it, do not commit it.
- What is and is not in the image, which decides who needs a redeploy. The Dockerfile's runtime stage copies backend/app/, backend/migrations/, alembic.ini, entrypoint.sh and the built SPA — nothing else. So scripts/backup.sh, scripts/restore.sh, backend/scripts/eval_round3/ and backend/scripts/benchlib/ change operator and harness behaviour and need NO redeploy; extension/ needs none either. Everything under backend/app and frontend/src does.
- F09+F10's real defect is visible in the tree. The runtime stage installs no git, and repo_manager.py:19 sets REPOS_BASE_DIR to ./data/repositories relative to WORKDIR /app — a path the image never creates. docker-compose.yml mounts repo_data there, so Docker materialises a root-owned volume the uid-100 app user cannot write. Both halves are Dockerfile lines and they ship together or not at all.
- Redeploy verification must inspect the image, not the tree. compose reuses an image whose tag did not move, so a skipped or failed build redeploys the old bits and still reports Started. For stage 2 that means `docker exec darkmem-prod-darkmem-1 git --version` and a write test into /app/data/repositories as the app user. Never DARKMEM_PUSH=1 — image push is CI-only, and this is a deploy, not a release.
- What --full is actually for, per stage. It adds four arms: the retrieval eval replay (which needs DEEPSEEK_API_KEY exported or the gate exits GATE BLOCKED at preflight, and which fails only on a crash or a cross-fingerprint refusal, never on the numbers), the API e2e suite (boots its own disposable stack, so it is the only automated thing that exercises a booted app over HTTP), the Playwright run (the only arm driving a real browser), and a port-hygiene diff. Stage 2 needs it for the e2e stack boot and the port diff after compose edits. Stage 4 and stage 12 need it for Playwright — jsdom cannot assert a pointer drag, a dialog remount or a stream error surface. Stage 7 needs it for the API e2e arm, because that is where a 500 becoming a 422 is observed at the HTTP layer. Stages 8 and 9 need it for the retrieval eval, which is the only arm that runs the embedding and ranking path end to end. Stage 15 needs it because it is a schema event. Every other stage runs the floor.
- Stage 7 changes response models, so the OpenAPI document moves. sdks/ts/src/client.ts and sdks/python/darkmem_sdk/client.py are generated and the generator refuses when a verb names a route, body field or header the contract does not serve. Re-run `make generate` in sdks/ in the same commit; the gate's sdk build and sdk test arms will otherwise discover it as a red gate rather than as a task.
- Frontend and backend genuinely parallelise, ops does not. Stages 1, 3 and 4 can be developed concurrently off stage 0's tip. Stage 2 must merge and deploy alone, with nothing else merging in its window, because it changes the artifact every later stage is verified against. Stage 13 (extension) is a free-floating lane that can merge at any point after stage 0.
- F19 may light up existing suites. Tracking setInterval in the pending-timer sweep will fail any test that leaks one, and the frontend suite has never been held to that. Budget collateral fixes inside stage 4 rather than treating them as scope creep — and note the suite baselines here are backend 6179 passing / 22 skipped, so a change in that count is a signal.
- Parallel lanes need their own test database. darkmem_test_2..5 exist for exactly this; keep darkmem_test for whoever is running the controller gate. conftest pins DATABASE_URL to TEST_DATABASE_URL and then runs DROP SCHEMA public CASCADE — never point a lane at a real database, which is the same hazard harness-ambient-database closes for the eval scripts.
- Two invariant tripwires sit inside stage 10's and stage 6's work. Invariant 15's tree-wide scan matches any line naming the ladder module, prose included — which is why ladder_config.py was split out of verification_ladder.py — so review-state-derivation must resolve thresholds through ladder_config and must not put an app.services.contradiction_veto import on a read surface. And the block channel's AST scan fails the build if a block-channel module names any KnowledgeTripleRepository method outside the allowlist (expire plus the reads), which constrains orphan-on-delete-no-fk's edits to block_fact_sources.py.
- Nine owner decisions gate their own stages and should be answered before that stage starts, not during it. Stage 1: F03 (does a local_path repo update its working tree at all, or does darkmem never write to a checkout it does not own) and F07 (should backup.sh stop emitting --clean --if-exists). Stage 2: F09+F10 (give the app user a real home so add_git_safe_directory can work, and whether local_path repositories are meant to work in the container at all — compose mounts no host source tree, so today they are unreachable regardless) and F16 (keep CORS_ORIGINS as a JSON array or convert it to CSV like MCP_ALLOWED_HOSTS). Stage 3: F05 (stale vs error vs ready for a reconcile that dies before the pipeline writes its own status). Stage 4: F11+F15 (what demo mode should show for the research loop and the providers empty state), F13 (drop the unsendable path field, make it read-only, or extend the update contract), F14 (should the two chat error yields carry conversation_id), F18 (a drag-slop threshold, or exact-zero movement only). Stage 15: whether the drift is fixed in the ORM model or by regenerating the baseline — the second is a database-recreating event, not a code change.
- Two deferred adjacent findings have no home in this programme and will be lost unless they are filed. F17 surfaced that graph-detail-panel.tsx's close button is an icon-only Button with no accessible name (the test has to reach it positionally), and F11+F15 surfaced that purpose-dialog.tsx fires a probe mutation on open — the second is picked up by demo-guard-per-call-site in stage 11, the first is picked up by nothing. Fold the aria-label into stage 12's confirmgate-triggers-keyboard-unreachable package, which is already the accessibility lane.

## 11. What this programme does not cover

The review named its own blind spots, and they are not closed by any stage above. They are
recorded here so the next pass starts from the right place rather than repeating this one.

- **wait_process cancelling a database operation on the caller's request session** — `wait_process.drive` runs `flush_claimed` against the **request's own** `AsyncSession` and, at the deadline, calls `task.cancel()` and awaits the CancelledError — then keeps using that same session for the phase-2 polling `select`, and the route commits it afterwards. SQLAlchemy's asyncio layer throws the cancellation into the greenlet mid-statement; the connection state after that is not something either the pipeline or the memory-buffer reviewer verified, and the module's docstring makes a positive claim about the outcome ("the row(s) it claimed stay `claimed`, exactly the state a crashed worker leaves") that depends on it. If the claim UPDATE is rolled back with the interrupted transaction instead, the documented recovery path (the next scheduled flush's stale-claim sweep) is not the one that runs. *Check:* With the dev Postgres up, drive a `wait_process=true` capture whose pipeline is slowed past `buffer_wait_timeout_seconds`, then assert three things after the 202 returns: the `memory_buffer` row's status, that the request session's later `commit()` does not raise `PendingRollbackError` or `InterfaceError`, and that the connection is not returned poisoned to the pool. `backend/tests/test_wait_process.py` uses an injected fake clock and fake sleep, so the real cancellation path is never exercised against a real connection.
- **Neither test suite was executed by any of the 24 slices** — Every backend finding in this review — including all six of mine — rests on source reading, EXPLAIN probes and two parser executions. No slice ran `python -m pytest -q`, `npm test`, or `./scripts/gate.sh`. A finding that is real in source but already covered by a test, and a test that is currently red for an unrelated reason, are both invisible from here. *Check:* Create `darkmem_test` on 127.0.0.1:5433 if absent, run `./scripts/gate.sh`, and re-check every reported finding against the result — particularly the four benchlib findings (`round5_frame`, `run_step9_independence`, `purge_eval`, `backfill_attempt_pair_hashes`), which claim outright crashes that a green harness suite would contradict.
- **Machine diff of pydantic response models against the frontend's TypeScript interfaces** — Six frontend slices reviewed hooks and components, and two backend slices reviewed routes and schemas; nobody compared the two sides field by field. A field the backend renamed and the frontend still reads renders as `undefined` — blank, not broken — which is the failure mode this codebase's own comments (`config.py:357-360`) say is hardest to notice. *Check:* I ran a crude version (regex over `hooks/api/*.ts` interfaces against every identifier in `backend/app`): 497 properties, 5 unmatched, and all 5 were dead stubs (`KnowledgeTriple.valid_from` / `valid_to` in a hook whose `queryFn` returns `[]`). What that method cannot see is the reverse direction (a field the backend serves that no surface reads) and type-level drift (nullable vs required, string vs number, enum member sets). A real check generates both sides from `/openapi.json` and diffs them structurally.
- **docs/ was reviewed by nobody** — `docs/two-door-parity.md` is named in CLAUDE.md as "the audit of record" for invariant 17, and `docs/api-rest-conventions.md` is the contract new endpoints must match. My finding on `memory_search`'s missing filters is a case where the audit of record states a parity that the code does not have — which means the document is being trusted as evidence while nothing checks it. `docs/runbook-deployment.md` carries the drop-and-recreate procedure that the schema-drift analysis says production already violated once. *Check:* Diff `docs/two-door-parity.md`'s tool column against the actual `@mcp.tool` signatures in `api/mcp/server.py` and the route decorators, parameter by parameter, and check `docs/api-rest-conventions.md`'s "Known deviations" list against the real status codes (e.g. `POST /api/v1/documents` returns 201 for what CLAUDE.md describes as an in-place upsert of an existing `(project, uri)`; that deviation is not on the list).
- **backend/scripts/benchlib/isolation_probe.py lines ~1500-2440** — The benchlib reviewer read 132 files but sampled roughly 900 lines of this one by signature rather than line by line — 30 per-surface drivers, of which ~10 were read. The probe is what asserts project isolation across every read surface, so a driver that silently probes the wrong surface makes the isolation claim weaker than it reads. *Check:* Read the unsampled drivers and confirm each one actually issues the call it names and asserts on the response rather than on a fixture, and that the registry guard at the top enumerates all 30.
- **frontend/src/__tests__, frontend/src/styles/globals.css, and the ~250 frontend production files covered only by ripgrep sweeps** — The fe-crosscutting reviewer covered most of `features/code`, `features/jobs`, `features/usage`, `features/dashboard`, `features/setup`, `features/memory-graph` and the remaining `features/graph/lib` with targeted pattern sweeps rather than full reads. Those sweeps find the patterns they were written for and nothing else — logic errors, wrong units, and inverted conditions do not match a regex. The four files under `frontend/src/__tests__` and `globals.css` appear in no slice's coverage note at all. *Check:* Read `frontend/src/__tests__/no-restricted-imports-count.test.ts` and `vitest-pool-bounded.test.ts` — both are guard tests whose own thresholds can go stale — and give `features/dashboard`, `features/usage/components` and the unread half of `features/graph/lib` a real read rather than a sweep.
- **Frontend XSS and injection** — A stored-XSS in the SPA would run with the session cookie on the same origin as every authenticated route, which is a full takeover with no CORS precondition. *Check:* I grepped `dangerouslySetInnerHTML`, `innerHTML`, `eval(` and `new Function` across `frontend/src` and `extension/src` and found only three hits, all inside `frontend/src/components/darkmem/__tests__/empty-state.test.tsx`. I did not audit third-party markdown/mermaid renderers pulled from `darkraise-ui` for their own sanitisation posture; chat answers and article prose are model-generated text rendered into the UI.
- **Restore/cutover scripts against a live database** — `scripts/restore.sh` and `backend/scripts/cutover/llm_providers_transition.py` are the two paths that can destroy production data in one command, and they run outside the test suite. *Check:* The slice reviewers already flagged `scripts/restore.sh:20` (critical) and `scripts/backup.sh:18` (high). I did not exercise `backend/scripts/cutover/llm_providers_transition.py` against a real old-schema dump, which is the one path CLAUDE.md says a deploy across the provider change must take.
- **MCP request-body bound** — `RequestBodyLimitMiddleware` deliberately excludes `/mcp` (backend/app/main.py:172), so the unauthenticated MCP door accepts an arbitrarily large body while every REST door is capped at 25 MB. `document_put` will then parse up to 1,000,000 characters synchronously before returning. *Check:* Whether the exclusion is still the right trade now that `/mcp` carries `document_put`, `memory_batch_add` and `research_run`. The exclusion is documented as intentional (nginx never fronted `/mcp`), so I did not report it — but the surface it protects has grown since that comment was written.
- **Long-lived websocket authorisation** — `websocket_endpoint` checks the blocklist once at handshake and then loops forever; a socket opened before a logout or password change keeps receiving every broadcast, including memory content previews. *Check:* Whether the broadcast fan-out should re-verify the connection's `jti` periodically, or whether logout should close matching sockets. The slice reviewers covered the missing password-change check *at* handshake (backend/app/api/websocket.py:86); the post-handshake lifetime is a separate question I did not pursue.

---

## Appendix — provenance

- **Review method:** 24 slice reviewers, each given this repository's stated invariants and
  told to read every production file in its slice rather than sample. Every claim then went
  to an independent verifier instructed to default to *refuted* when unsure; every surviving
  critical and high went to a second, separate refuter tracing callers from real input.
  210 raised → 28 refuted → 182 confirmed. Two cross-slice critics found 8 more.
- **Scope:** 712 production files, 178,185 lines — `backend/app`, `backend/migrations`,
  `backend/scripts`, `frontend/src`, `extension/`, `sdks/`, `scripts/`, the Dockerfile and
  both compose files.
- **Independently re-verified by hand:** the four headline claims — the missing `git`
  binary and root-owned repo volume (checked against the running production container), the
  CORS fallback, and the `git reset --hard` on an operator's own checkout.
- **Findings ledger:** https://claude.ai/code/artifact/258fe605-25ea-442c-9a9f-3501bac53924
