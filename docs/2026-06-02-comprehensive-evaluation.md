# Darkmem — Comprehensive System Evaluation

**Date:** 2026-06-02 · **Branch:** feat/ui-v3-refactor · **Focus:** reliability, accuracy, usability

**Method.** Every subsystem was read and evaluated against the `CLAUDE.md` behavioral
contract, then each finding was adversarially re-verified against the actual code (misreads
and already-implemented suggestions were dropped). The reliability/accuracy core (ingestion
pipeline, retrieval + reranker, supersession, entity graph, MCP surface, vector repo) was
verified by hand; the remaining ten subsystems via a two-stage analyze→verify agent pipeline.
Severities reflect user-facing impact × likelihood, not fix difficulty.

**Overall.** Darkmem is a well-architected system with genuinely strong bones: the phased
pipeline with per-memory savepoints, fingerprint-partitioned embeddings, the closed taxonomy,
the cron-unified job registry, the three-table LLM config with credential-rotation overlay,
and the token-lifecycle auth are all thoughtfully designed and largely correct. The issues
below are concentrated, not pervasive — but they cluster around one dangerous pattern for a
memory system: **silent degradation**, where the system keeps reporting success while quietly
losing data or returning worse results.

---

## Cross-cutting themes

These patterns recur across subsystems; fixing the pattern is higher-leverage than fixing each instance.

### 1. Silent failure is the dominant risk
A memory system's worst failure is one that *looks* like it worked. This recurs everywhere:
extraction parse errors empty the graph with no signal; the reranker (when enabled) scores
empty strings; hybrid search swallows embedder outages into "no matches"; code-chunk reembed
is a no-op that reports success; an unreachable ML classifier silently labels everything
`fact`; an ML profile silently blanks three of four enrichment columns; `search_memories`
silently under-returns filtered queries. **Pattern fix:** validate-and-surface at boundaries,
fail loud, and add per-memory pipeline-status visibility so degraded rows are findable.

### 2. Determinism makes failures permanent
The `sha256(content)` seed buys reproducibility, but it also guarantees that any *deterministic*
failure (a parse error, a dedup collapse, a vendor that prepends reasoning prose) recurs
identically on reprocess. The system has no notion of transient vs permanent failure, so the
one remedy an operator reaches for — reprocessing — cannot close a deterministic gap.
**Pattern fix:** salvage/validate at ingest; classify failures so retry targets the recoverable ones.

### 3. Core invariants are enforced only by convention
`memory_id` str-vs-UUID, lowercase entity names, no cross-fingerprint joins, and the partition
slug are all upheld by call-site discipline rather than types. One forgetful consumer silently
drops matches or, worse, the slug's character-folding collapse can map two distinct models into
one `vector(N)` column and corrupt every cosine result. **Pattern fix:** centralize coercion,
add a guard at `child_table()` access, and hash-qualify the slug.

### 4. Whole-program work computed on a subset
Incremental code reindex resolves the cross-file call/heritage graph from only the changed
files, so stale and missed edges accumulate silently across pushes. Clustering and analytics
run over an arbitrary `LIMIT N` sample with no `ORDER BY`. Searches fetch a fixed slice then
post-filter. **Pattern fix:** dependency-closure working sets, deterministic sampling, over-fetch-before-filter.

### 5. The pre-setup window is a real attack surface
Filesystem-browse (`fs/roots`, `fs/list`) and `probe-models` are reachable by any LAN peer
before the admin password exists, and `_enforce_setup_secret` never guards them. `probe-models`
is an SSRF/credential-relay primitive. There is no login rate limiting, and the rich audit
trail has no read surface. **Pattern fix:** gate those endpoints behind the setup secret /
loopback, throttle login, and expose the audit log.

### 6. Half-built features that mislead
The `api_keys` model is fully dead (no `X-API-Key` path; every `api_key_id` is `None`);
`convo_miner.py` has no callers; `retired_at` is honored by one reader and ignored by four
writers; the jobs `min_interval_seconds` schema field is never wired; the Edit-Repository cron
field is validated then silently dropped; the knowledge-timeline tab renders inert controls.
**Pattern fix:** wire or delete — a half-built primitive implies a capability that does not exist.

---

## Prioritized roadmap

### P0 — correctness / data-loss (do first)

| # | Fix | Subsystem | Effort |
|---|-----|-----------|--------|
| 1 | Reranker scores empty documents (reads `doc["content"]`; content is under `payload`) | Retrieval | small |
| 2 | `memory_batch_add` drops `project`, landing every MCP batch in `default` | MCP | small |
| 3 | `delete_by_memory_id` + FK CASCADE deletes relations other memories still assert | Entity graph | medium |
| 4 | Extraction: brace-balanced JSON salvage + fence-anywhere + log raw prefix | Extraction | medium |
| 5 | `create_entity` overwrites shared-entity `properties` (loses `display_name`) — merge instead | Entity graph | small |

**Why these first.** Each silently corrupts or discards data on the happy path. (1) makes the
reranker actively harmful when enabled; (2) breaks supersession scoping for the primary agent
ingestion route; (3) violates the idempotent-re-extraction invariant and loses shared edges;
(4) is the most common reasoning-vendor failure and never self-heals; (5) quietly degrades
entity metadata every time a shared entity is re-asserted.

### P1 — accuracy / reliability

| # | Fix | Subsystem | Effort |
|---|-----|-----------|--------|
| 6 | Surface search-backend failures instead of degrading to empty / keyword-only silently | Retrieval | small |
| 7 | Over-fetch before post-filter in `search_memories`; honor MCP `offset` | Retrieval/MCP | small |
| 8 | Scope the supersession speculative-marker gate to the REPLACES clause, not the whole memory | Supersession | small |
| 9 | Guard read/count paths against a not-yet-created active partition (500 on fresh install/rotation) | Embedders | small |
| 10 | Hash-qualify the partition slug to kill character-folding/truncation collisions | Embedders | small |
| 11 | Code-chunk reembed: implement the backfill or surface that code search is degraded | Embedders | medium |
| 12 | Incremental code reindex: rehydrate cross-file resolution state (dependency closure) | Code pipeline | large |
| 13 | Wrap embed errors + reconcile a wrong explicit `dimensions` against the probed length | LLM orch | small |
| 14 | Add `job.lock` to `update_config` (lost-update race vs `_run_once`/`set_config`) | Jobs | small |
| 15 | ML classifier: warn on dangling `ml_profile_ref`; document/merge the blanked enrichment columns | Classification | medium |

### P1 — security

| # | Fix | Subsystem | Effort |
|---|-----|-----------|--------|
| 16 | Gate `fs/*` and `probe-models` behind `_enforce_setup_secret` / loopback (FS disclosure + SSRF) | Auth/Setup | medium |
| 17 | Login rate-limit / lockout, and an admin read surface for the `auth_*` audit rows | Auth/Setup | medium |

### P2 — usability / polish
Reranker latency cliff (1 LLM call/result); `get_full_graph` arbitrary 200-row slice (no `ORDER BY`);
stuck "re-embedding" state on a missed websocket event; provider/profile save blocked by unrelated
invalid rows; multi-select filters that narrow only the current page with misleading counts; setup
returns 200 + cookie on partial failure; Edit-Repo cron field dropped on save; reindex dialog opens
all-off; knowledge-timeline stub controls; inherited-method calls produce no call edge.

---

## Findings by subsystem

Axis legend: **R**=reliability, **A**=accuracy, **U**=usability, **D**=design.

### Ingestion pipeline (`services/pipeline.py`) — verified by hand
Strong: phased checkpoints, per-memory savepoint isolation, idempotent strip-before-write,
single-flight flag cache, fingerprint-rotation handling across phases.

| Finding | Axis | Sev |
|---|---|---|
| Phase-1 embed failure gates *all* graph writes (`if embed=="ok"`), so a transient embedder outage discards successful Phase-2 extraction; the memory becomes a zombie row recoverable only via reprocess | R | med |
| Status derivation reports `pipeline.partial` when embed=error+extract=ok even though nothing was persisted (graph skipped) | A | low |
| Per-batch supersession runs inside each concurrent write's savepoint; two writes superseding the same candidate can race on the UPDATE | R | low |

*Improvement:* decouple graph extraction from embedding success (persist the graph even when the
vector write fails, marking only `vector=error`), so an embedder blip doesn't throw away LLM
extraction work. *Reason:* extraction and embedding are independent costs; coupling them wastes
the more expensive one and creates silently incomplete rows.

### Retrieval — hybrid search / reranker / memory service — verified by hand
Strong: RRF fusion is correct, confidence weighting is a clean no-op at γ=0, `get_many` preserves
rank order, `reason()` normalizes id types and prefers `rrf_score`.

| Finding | Axis | Sev |
|---|---|---|
| **Reranker scores empty documents** — `rerank` reads `doc.get("content")`, but fused hybrid rows carry content under `payload`; every document is scored as `""`, so enabling the reranker randomizes ranking | A | high |
| Both search sides swallow exceptions — an embedder outage silently degrades to keyword-only or an empty result indistinguishable from "no matches" | R/U | med |
| `plainto_tsquery` ANDs all terms, so multi-word keyword queries require *every* term to match — recall loss; `websearch_to_tsquery` is the drop-in fix | A | med |
| `search_memories` (used by MCP) fetches exactly `limit` semantic hits then post-filters archived/status/type/project/tags in memory and returns `[:limit]`; any active filter (incl. the default that drops superseded) shrinks results below `limit` | A | med |
| Fused rows retain a stale single-modality `score` next to `rrf_score` (contract says score is "replaced"); consumers reading `.score` get cosine for some rows, `ts_rank` for others | A | low |
| Reranker fires one LLM call per result (default limit 20) at concurrency 3 — a multi-second latency cliff when enabled | U | low |

*Improvement (reranker):* pass `content_key` that reads `payload.content`/`chunk_content`, or
promote content to the top level during fusion; add a regression test asserting non-empty
documents reach the scorer. *Reason:* the feature is currently a silent accuracy regression for
anyone who turns it on.

### Supersession (`services/supersession.py`) — verified by hand
Strong: all six gates present, strictly-older guard correctly prevents the bidirectional-flip
bug, REPLACES targets lowercased to match the `technologies` denorm.

| Finding | Axis | Sev |
|---|---|---|
| The speculative-marker gate is whole-memory: one "might"/"considering" anywhere suppresses *all* REPLACES supersessions for that memory, despite the comment calling it a "per-relation" gate | A | med |
| The strict `created_at <` guard also excludes equal timestamps, so same-second siblings in a batch never supersede each other (minor; timestamps are usually distinct) | A | low |

*Improvement:* run `is_speculative` against the clause around each REPLACES relation rather than
the full memory text. *Reason:* a memory can definitively replace X while speculating about Y;
the coarse gate loses the definitive supersession.

### Entity / relation graph (`repositories/graph.py`, `models/graph.py`) — verified by hand
Strong: `(name,type)` uniqueness, `memory_ids[]` append-not-duplicate, ANN dedup, type-scoped
relationship endpoint resolution.

| Finding | Axis | Sev |
|---|---|---|
| `delete_by_memory_id` deletes an entity once its `memory_ids` empties; the FK `ondelete=CASCADE` then deletes every relation touching it — including relations whose own `memory_ids` are non-empty (other memories assert them). Violates the contract's "shared survive" for relations | R/A | med |
| `create_entity` `ON CONFLICT SET properties = EXCLUDED.properties` is a full overwrite; re-asserting a shared entity from a second memory clobbers the first's `properties` (incl. `display_name`). `upsert_entity_simple` merges with `||` — inconsistent | A | med |
| `create_relationship` silently `return`s if endpoints aren't found, dropping rescue-emitted relations whose endpoint wasn't extracted as an entity | A | low |
| `get_full_graph` does `LIMIT 200` with no `ORDER BY` → a nondeterministic 200-entity slice in the UI | U | low |

*Improvement (relations):* before deleting an orphaned entity, reassign or guard relations that
other memories still assert, or make relation cleanup `memory_ids`-aware the way entity cleanup
is. *Reason:* re-extracting one memory should never delete another memory's edges.

### MCP server (`api/mcp/server.py`) — verified by hand
Strong: clear agent-facing tool descriptions, input caps mirror the HTTP bounds, UUID validation,
a rich code-intelligence tool surface.

| Finding | Axis | Sev |
|---|---|---|
| `memory_batch_add` re-implements creation and omits `project=data.project`, so every batch-added memory lands in `default` — breaking supersession scope for the primary agent path | A | high |
| `memory_search` builds an `offset` but calls `search_memories`, which never reads it — MCP semantic pagination is a silent no-op | U | med |
| `memory_stats` counts all memories incl. archived/superseded (no filter) | A | low |
| `code_communities` description says "Leiden" but the implementation is Louvain (`community_multilevel`) | D | low |
| `memory_batch_add` duplicates `batch_create_memories` rather than calling it (the divergence source of the project bug) | D | low |

### Vector repo & clustering (`repositories/vector.py`) — verified by hand
| Finding | Axis | Sev |
|---|---|---|
| `find_similar_memories` (runs on every ingest for crossrefs) self-joins with a non-constant operand, so the ANN index can't be used → full scan per ingest; `find_similar` does it right (fetch vector first) | R/perf | med |
| Clustering reads `get_all_vectors` with `LIMIT 500` (300 for DBSCAN) and no `ORDER BY` → analytics computed on an arbitrary sample | A/U | low |

### Extraction, prompts, rescue (`services/extraction.py`) — agent-verified
| Finding | Axis | Sev |
|---|---|---|
| Malformed LLM response empties the graph: one `json.loads`, `_strip_json_fences` only fires when the response *starts* with a fence, no salvage/retry. Reasoning vendors that prepend prose or double-fence yield zero entities/relations; the deterministic seed makes reprocess fail identically. (Content/embedding/FTS still written, so retrieval finds the row — only the graph is empty) | R | med |
| `_dedup_by_target_predicate` keys on `(target, predicate)` only, dropping a legitimately distinct source when two subjects share a predicate+target *within one memory* (intended for REPLACES subject-anchoring, but applied universally) | A | med |

*Improvement:* depth-scan from the first `{` (tracking string/escape state) to recover a balanced
object; broaden the fence stripper to find a fenced block anywhere; log the raw 200-char prefix.
Restrict the source-dropping collapse to the REPLACES family. *Reason:* recovers the common
vendor-envelope cases with near-zero false positives, and stops collateral loss of distinct edges.

### Classification / enrichment — agent-verified
| Finding | Axis | Sev |
|---|---|---|
| `MLModelManager.shutdown_all` is never wired into the app lifespan; the `app.state.ml_model_manager` docstring is false → leaked torch models + dangling eviction tasks on restart | R | high |
| Seeded default ML repo is unverified and enabling ML classification fails opaquely (every memory → `fact`) with no save-time probe or `/health/ml` | U | med |
| Label-vocabulary mismatch between an ML model and the area type set collapses every prediction to `fact`, unguarded and invisible | A | med |
| Switching to an ML profile silently blanks `llm_summary`/`llm_emotions`/`llm_flags` (ML returns only a type; Phase 5 overwrites unconditionally) | A | med |
| Enrichment worker permanently marks a symbol `failed` on the first transient error (pending-only re-select, no attempt counter) | R | low |
| Per-batch ML/LLM dispatch uses an uncached DB round-trip and a bare `except` that silently falls back to LLM on a dangling ref | D | low |
| Idle-eviction watchdog `pop`s without the per-repo lock (TOCTOU; latent at default ttl=0) | R | low |
| Regex `emotional` type collapses to `preference` in simple mode while emotions are still detected — internally inconsistent rows | A | low |

### Embedders / partitioning / reembed — agent-verified
| Finding | Axis | Sev |
|---|---|---|
| Read/count paths (`count_missing`, `list_obsolete_*`, semantic search) query the active partition with no existence guard → 500 on `GET /reembed/obsolete-counts` on fresh install / right after a model rotation; search silently degrades to keyword-only | R | high |
| Code-chunk reembed is a no-op that reports success (`_chunk_source_view_exists` hard-coded `False`); after a rotation code search silently returns nothing and the UI shows "0 obsolete" | U | med |
| Partition slug folds all non-alphanumerics to `_`, so `model-a\|512` and `model.a\|512` collide into one `vector(512)` table — cross-embedder vectors share a column | A | med |
| Reembed is fire-and-forget with in-memory state: a restart mid-backfill leaves a partial partition and a hung progress bar, with no resume | R | med |
| `register` commits a caller-supplied session (reembed path) and builds four tables + HNSW in one un-saved transaction | R | med |
| `warm_cache_from_db` filters `retired_at IS NULL` but all fan-out queries ignore it, and nothing ever sets `retired_at` (half-built retirement) | R | low |
| `/reembed` pins a snapshot fingerprint never re-checked against a mid-dispatch rotation → backfills a no-longer-active partition while reporting success | A | low |

### Code parsing / symbols — agent-verified
| Finding | Axis | Sev |
|---|---|---|
| `propagate_types` cyclic-import fallback merges by dict-insertion order (first-writer-wins) → non-deterministic type bindings → flaky call edges, undermining the reproducibility the project values | A | med |
| Constructor-typed assignment is detected only for bare capitalized callees, missing `x = module.Service()` and lowercase constructors → lost member-call edges | A | med |
| ~30 grammars are declared but only ~8 have node-type coverage; the rest parse then extract zero symbols (silent), and `.h`→`cpp` can misparse C | A | low |
| Suffix-index basename collisions (`utils`, `index.ts`) force common imports onto the slow fallback (degrades coverage, not correctness) | A | low |
| `self`/`this` typing depends on a stringly-encoded scope key parsed by index — fragile to any new class/method node type | A | low |
| `_extract_string_arg` returns the first string anywhere in the subtree; JS route match is a substring scan — can record a wrong route path | A | low |
| `dialect.compression_stats` reports a 0× ratio for sub-3-char inputs | R | low |

### Code pipeline / call & heritage resolution / wiki — agent-verified
| Finding | Axis | Sev |
|---|---|---|
| Incremental reindex builds cross-file resolution state (imports, topo order, bindings, call sites to re-trace) from only the diff, while the symbol table loads whole → stale + missed cross-file edges accumulate across pushes; communities/processes then mix fresh and stale edges | A | high |
| `GET /code/wiki` runs N+1 LLM calls and writes a cache row on a stale/uncached read despite a documented read-only contract; `force=true` is exposed | R | med |
| Symbol key `name::file_path` collides for overloads / same-name nested symbols → merged nodes, last-writer-wins properties | A | med |
| Route/tool process traces seed from the first three symbols by line, not the actual handler → wrong call chain per endpoint | A | med |
| Member calls on inherited methods produce no call edge — the resolver never consults the MRO it already computes (`find_inherited_method` is unused) | A | med |
| Phase-08 skip heuristic divides resolved calls by *all* call sites (incl. builtins), so it almost never skips even when fully resolved; `unresolved_count` is dead code | A | med |
| `_delete_file_data` orphans route/tool graph nodes on re-index (no `file_path` property/key suffix) and uses an unescaped `LIKE` on the path | A | low |
| `search_code` fuses the semantic ranking with an unordered `ILIKE` scan and labels it RRF — the keyword `rank` is iteration order, not relevance | A | low |

### LLM orchestration / providers / config — agent-verified
| Finding | Axis | Sev |
|---|---|---|
| A wrong explicit `dimensions` value mislabels partitions: real embeds emit `model\|true_dims` while `llm_fingerprint()` returns `model\|stored_dims`; the two disagree and search queries an unwritten partition | A | high |
| Embed methods leak raw transport errors *and* malformed-200 `KeyError`/`IndexError` to search/chat callers (unlike `chat_completion`, which wraps both) | R | med |
| The main `POST /config/llm` never checks that the embedding purpose's provider `supports_embedding` (the gate exists on every other path), so the embedding purpose can be pointed at Anthropic/DeepSeek → 404 on every embed | U | med |
| Provider-key rotation does not refresh purposes that inline-copied the key; an inline-key purpose stays on the revoked key with no UI signal | D | med |
| `/test` and model-list probes hardcode their own timeout and skip the reasoning-disable injection the live path uses → can pass when prod fails or vice-versa | U | low |
| Streaming path reimplements body construction and drops Ollama `extra_body` + the zai/deepseek `thinking` injection | D | low |
| Phase-1 embed has no retry/backoff and no `return_exceptions`; one chunk's 429/503 fails the whole batch and discards successful chunks | R | low |
| Per-call seed silently overrides a `params.seed` with inconsistent precedence across purposes | A | low |
| Providers PUT persists a free-form `api_kind` and goes live with no enum check → a typo silently dispatches via OpenAI-compat with the wrong auth header | R | low |

### Jobs / scheduling / repo sync — agent-verified
Strong: cron validation centralized, the loop survives malformed config and bad cron, "no
immediate fire on cron-only edit" is correct, the shared per-job lock prevents trigger/loop overlap.

| Finding | Axis | Sev |
|---|---|---|
| `update_config` does a read-modify-write *without* `job.lock` (which `set_config` and `_run_once` both take) → lost update: a concurrent scheduled run's `last_run_at`/status is clobbered by a stale snapshot | R | med |
| `min_interval_seconds` floor falls back to a hardcoded `1` when a row omits the field (rather than the registered default) | R | low |
| `TaskRegistry.cancel` is fire-and-forget (never awaits); an executor-bound `git clone` keeps running after "cancelled", racing a re-create's `rmtree` | R | low |
| `_restart_loop`/`stop_all` catch `(CancelledError, Exception)` and `pass`, hiding a loop that died from a real bug | R | low |
| `repo_sync` snapshots the auto-sync list once, so a mid-run disable isn't honored this pass | R | low |
| `convo_miner.py` ships with zero `app/` callers (dead code) | D | low |
| The protective floor is not operator-tunable (design tension, not a defect) | U | low |

### Auth / setup / API keys / audit — agent-verified
Strong: httponly-cookie JWT with Bearer fallback, logout blocklisting + GC job, the
`iat < changed_at` epoch revocation, and an independently-committed audit trail are all correct and tested.

| Finding | Axis | Sev |
|---|---|---|
| Pre-setup `fs/roots` / `fs/list` are unauthenticated (only `require_uninitialized`); `_enforce_setup_secret` is never applied → any LAN peer can walk most of the host filesystem before setup completes | R | high |
| `probe-models` (also pre-setup, unauthenticated) makes server-side GETs to a caller-controlled `base_url` and reflects status + truncated body → SSRF / credential-relay primitive | R | med |
| No login rate-limit / lockout on the single shared admin password | R | med |
| The rich `auth_*`/`setup_*` audit trail has no read surface in the API or UI (only `pipeline` rows are read back) | U | med |
| `/refresh` and `/change-password` don't blocklist the presented JTI → non-rotating refresh; an old token stays valid up to 24h | R | med |
| The `api_keys` model + `api_key_id` plumbing is fully dead (no `X-API-Key` path; audit column always null) — wire it or delete it | D | med |
| `setup_finalize` returns 200 + admin cookie even when the LLM/repo block failed (only a nested `ok:false`) | U | low |
| Same-second epoch boundary lets an `iat == changed_at` token survive a password change (needs an already-authenticated attacker) | A | low |
| `jwt.decode` doesn't pin `require`/`verify_exp` (expiry enforced incidentally by the Pydantic model) | R | low |

### Observability — analytics / metrics / websocket / failures — agent-verified
Strong: the failure-tracking upsert (partial-unique on unresolved), the retry-handler registry,
and `derive_memory_failed_step` mirroring the Phase 1-5 contract are the best part.

| Finding | Axis | Sev |
|---|---|---|
| `EventManager.broadcast` `await`s each `send_text` sequentially with no timeout, inline in the pipeline write path → one slow client head-of-line-blocks every other admin *and* stalls `process_batch` | R | high |
| `onopen` invalidates nothing, so events lost during a reconnect leave the UI stale (a finished retry-batch can appear to hang) until a manual refresh | R | med |
| `recent_errors` has no time-window filter — it counts errors over all time | A | med |
| `retry_all` batch-level exception sets both `processed` and `errors` to `len(entries)` and doesn't per-item re-record | A | med |
| `system_metrics` `cpu_percent` uses a process-global delta that concurrent callers corrupt | R | low |
| `process_batch` has no batch cap; `reprocess_all` materializes all extraction tasks at once | R | low |

### Frontend — core feature UX (memories, graph, chat, code) — agent-verified
| Finding | Axis | Sev |
|---|---|---|
| Knowledge-timeline tab: hooks are stubs (`queryFn: () => []`) and the entity-select never populates → working-looking controls that can't produce data; constant query key `["knowledgeTimeline"]` would collide entities once implemented | U/A | med |
| Multi-select source/type filters narrow only the current 50-row page client-side while the server ignores them → arbitrary subset, and the "of N" count reflects the unfiltered query | A | med |
| Chat entity-badge injection does substring `indexOf` with no word boundary; 3-letter entities (`api`, `cat`) get badged mid-word, corrupting prose | A | med |
| Code-search result clicks resolve only against currently-visible/filtered nodes (and by label equality) → off-screen matches are silent no-ops; same-name symbols select the wrong one | U | med |
| Bulk delete funnels through one shared `useDeleteMemory` mutation (latent if any spinner reads its `isPending`); first-error-only toast | R | low |
| Memories `columns` memo depends on `selected`, rebuilding on every checkbox toggle; Code Wiki renders all symbols unvirtualized | D | low |
| Unified-graph cluster-edge generation is O(cluster²) and runs even in the default 2D view (output only feeds 3D) | R | low |

### Frontend — config / admin UX (LLM, settings, jobs, repos, setup) — agent-verified
| Finding | Axis | Sev |
|---|---|---|
| Re-embed "running" state never clears on a missed websocket `done` event → all re-embed buttons permanently disabled until reload (no done-to-clear effect, no server-state recovery) | R | high |
| Provider/Profile save loops over *all* rows, so one invalid untouched row blocks saving an unrelated edit (and re-submits unchanged rows) | U | med |
| Edit-Repository dialog shows an editable, validated "Sync schedule (cron)" field that is hardcoded on open and silently dropped on save (no cron field in `RepoUpdateParams`) | A | med |
| Setup wizard's "Next" gate gives no per-row feedback about which required model is missing | A | med |
| Jobs UI exposes `min_interval_seconds` as a column + schema field but never lets the user edit it | U | low |
| Reindex dialog opens all-off with a disabled primary button (extra click for the common action) | U | low |
| Cron preset `Select` is hard-bound to `value=""` so it never reflects the chosen preset; `Reprocess All` has an unused `cancel()` with no UI control | U | low |

---

## What's well-designed (keep)
The phased pipeline with per-memory savepoints and idempotent strip-before-write; fingerprint
partitioning with `child_table()` indirection; the closed taxonomy with legacy remaps; the
strictly-older supersession guard; the three-table LLM config with credential-rotation overlay
and background orchestrator swap; the cron-unified `JobRegistry` with shared per-job locks; the
failure-tracking partial-unique upsert; the token-lifecycle auth (logout blocklist + epoch
revocation + independent audit session); and the careful draft/merge pattern in the LLM admin panels.

## Method notes & limits
This evaluation reads code and the `CLAUDE.md` contract; it did not execute the system. Findings
are grounded in `file:line` and were adversarially re-verified, but runtime-only issues
(actual latency, real vendor-envelope rates, index plans under load) would need a live profile.
The two agent passes that returned structured output failed on a tool-protocol issue and were
re-run in prose mode; the prose reports are the basis here. Per-subsystem full prose lives in
`scripts/eval_reports.md`.
