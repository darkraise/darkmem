# Darkmem — Comprehensive Code Audit (2026-06-06)

Full-project audit covering backend, frontend, algorithms, pipelines, business
and logic flows, data integrity, security, engineering standards, and
contract drift against `CLAUDE.md`.

## Method

Seventeen subsystem/lens units were each audited by an independent agent, then
**every finding was re-checked by a separate adversarial verifier** that read
the cited code and either confirmed, refuted, or flagged it uncertain. Only
confirmed findings are listed here. Verification refuted a number of
first-pass claims (e.g. the `next.js` corruption was downgraded from "always
two nodes" to "conditional" after a live trace), so severities below reflect
the verifier's adjusted ratings, not the original auditor's.

Coverage: `backend/app` (~27k LOC, 50 services, 17 routes, 13 models, 5 repos,
3 migrations) and `frontend/src` (~24k LOC, 7 routes, 10 feature areas, 11 API
hook modules, graph renderers). Verified against the running database where
behavior was empirically checkable.

## Results at a glance

| Severity | Count |
| --- | --- |
| Blocker | 0 |
| High | 20 |
| Medium | 34 |
| Low | 86 |
| Nit | 43 |
| **Total confirmed** | **183** |

By category: bug 46, business-logic 25, convention 22, data-integrity 20,
algorithm 18, performance 18, doc-drift 13, security 10, cleanup 9, test-gap 2.

No blocker-class defects (nothing that hard-breaks the primary write/read path
for the common case). The high-severity set is dominated by **frontend/backend
contract drift, data-integrity edge cases around the supersession CHECK
constraint, a hollow code graph for object-oriented/decorated code, and a
reranker that does not actually rerank.**

---

## Cross-cutting themes

These patterns recur across subsystems and are the highest-leverage things to
fix, because one root cause produces many findings.

### T1. Frontend ↔ backend taxonomy drift (4 findings, 3 High)
The frontend hand-maintains enums that have silently diverged from the backend
source of truth. `MemoryStatus` invents `archived`/`deleted` and omits the real
`deprecated`; `createMemorySchema.memory_type` offers `context` (not valid) and
cannot offer `problem`/`architecture`/`milestone`; the graph color map still
keys on legacy `debug`/`session` names that `LEGACY_MEMORY_TYPE_MAP` rewrites.
Users mislabel data at the source and filters silently 422 or no-op. **Fix
once:** expose the taxonomy from one backend endpoint/shared constant so zod
enums and dropdowns cannot drift from `taxonomy.py` again.

### T2. The reranker does not rerank (4 findings, 1 High)
`_rrf_fuse` truncates to `limit` *before* the reranker runs, so the cross-encoder
only reshuffles the page RRF already chose — its entire recall value (rescuing
docs ranked just below the cut) is lost. Compounding it: confidence weighting
rescales `rrf_score` while order is driven by `rerank_score` (no-op on order);
the displayed score no longer matches row order; and the documented
`max_candidates=40` cap is unreachable. **Fix once:** widen the candidate pool
fed to the reranker (`fetch_n`, not `limit`) and make one score field
authoritative per path.

### T3. The `chk_superseded_has_pointer` CHECK is a latent 500 (2 High)
The constraint forbids `status='superseded'` with `superseded_by IS NULL`, but
two paths can produce exactly that: deleting a superseding memory fires
`ON DELETE SET NULL` on its dependents (IntegrityError aborts the delete), and
`PUT /memories/{id}` accepts `status:"superseded"` with no way to set
`superseded_by` (unhandled 500). **Fix:** demote dependents before delete; reject
the `superseded` transition via the public API.

### T4. Supersession under-fires in real scenarios (3 findings)
The trigger is gated on the *new* memory's `technologies` (unrelated to whether
the REPLACES *target* is a tech); same-batch memories share an identical
`created_at` so the strict-older guard never fires within a batch; and the
speculative-marker gate uses bare-substring `would`/`could`, over-suppressing
legitimate replacements. Replacements that should supersede silently leave the
old memory active.

### T5. The code graph is hollow for OO / decorated code (7 findings, 3 High)
This is the residual half of the known "class methods not extracted" issue.
Decorated Python functions/methods (every FastAPI route handler, `@property`,
`@staticmethod`, `@pytest.fixture`) are dropped entirely — no symbol, no chunk,
no call node. Methods of nested classes get no `has_method` edge. Self-calls to
interface-default methods don't resolve. The resolver cache ignores arity
(wrong overload), named-import maps store raw module strings (dead for
non-Python/TS), `BUILTIN_SKIP` suppresses user-defined `map`/`type`/`Set`, and
call-edge `ON CONFLICT DO NOTHING` collapses every call site to one edge. The
result is systematic under-linking that degrades blast-radius, process tracing,
and the wiki.

### T6. WebSocket broadcast is unsafe under load (3 findings, 1 High)
`EventManager.broadcast` has no per-connection lock (concurrent broadcasts from
the pipeline fan-out can interleave ASGI sends on one socket and kill the
connection), no send timeout (one frozen browser tab applies TCP backpressure
and stalls the *indexing/memory pipeline* that awaits the broadcast), and still
sends payloads that failed schema validation. **Fix:** serialize sends behind a
lock and give each connection a bounded queue + writer task.

### T7. Repo manager: clone-URL RCE/SSRF and local-folder deletion (3 findings, 2 High)
`RepoCreate.url` is an unvalidated `str`; it flows into `git clone <url>`, so
`ext::sh -c …` is arbitrary command execution and `file://`/internal hosts are
local-file/SSRF reads. Separately, `pull_repo`'s reclone fallback runs
`shutil.rmtree(cwd)` where `cwd` can be the operator's own `local_path` folder
(force-deleted on any transient git failure). Tokens are also persisted
plaintext into `.git/config` and config rows. **Fix:** scheme allowlist + reject
`-`-leading branches; never rmtree a `local_path` tree; don't persist tokens in
remote URLs.

### T8. React Query invalidation gaps leave stale UI (8+ findings)
Many mutations and WS events under-invalidate: the dashboard `['overview']` is
never refreshed on ingest/delete; bulk-archive touches only
`['memoriesPaginated']`; reprocess-stream skips `['memoriesPaginated']`/`['tags']`;
conversation rename skips the open detail; memory-detail `['memory', id]` is
never invalidated. Several mutations dropped their fallback `onSuccess`
invalidation and rely solely on WS events, so a transient disconnect leaves the
view stale forever (no event replay).

### T9. Symbol enrichment is silently incomplete after reindex (4 findings, 1 High)
The root cause behind "1000/7640 enriched": Phase 13 is capped at
`range(200) × batch_size 5 = 1000`, ignores the operator-configured
`code_enrichment` batch size, and — worse — drains a **global cross-repo**
pending queue with no `repo_id` filter, so reindexing repo A can spend the whole
budget on repo B. Failed symbols are terminal (`status='failed'` is never reset),
so one transient LLM error permanently loses a symbol's summary until a full
reindex. None of this is surfaced to the user.

### T10. Wizard finalize discards vendor reasoning defaults (2 findings)
`setup_finalize` sets every purpose's `params = {}`, wiping the seeded vendor
reasoning controls (`reasoning_effort:none` for Google/gpt-5,
`thinking:{disabled}` for DeepSeek) the orchestrator depends on — so a wizard
user who picks a Google/gpt-5 extraction model can get empty content on the very
first extraction. Separately, `cfg_to_schema` drops `ml_profile_ref` on every
read, hiding the ML classification link from the UI.

### T11. Unbounded inputs / DoS footguns (5+ findings)
`CodeSearchRequest.limit`, `BlastRadiusRequest.max_depth`, `ReasonRequest.limit`,
and `/duplicates` `threshold` have no `Field` bounds — inconsistent with
`MemorySearchRequest` (`ge=1, le=500`). The login rate limiter keys on
`request.client.host`, so behind any proxy all logins share one bucket (trivial
lockout). Password-change and setup-finalize have no brute-force throttle.

### T12. Determinism and reproducibility gaps (2 findings)
Leiden community detection passes no seed (community structure differs between
identical reindexes), and graph layout seeds positions with `Math.random()`
(layout reshuffles on every rebuild/theme switch). The project's
`seed = sha256(...)` reproducibility convention isn't applied here.

### T13. Oversized modules (2 nits, structural)
`extraction.py` (2053 lines, ~50 module-level `_rescue_*`/`_filter_*`/`_gate_*`
helpers + the service class) and `config.py` route module (1050 lines, five
unrelated config domains) should be split for navigability.

---

## Recommended remediation order

**Phase 1 — correctness/security blockers (do first):**
1. T3 — fix `chk_superseded_has_pointer` violations (delete-dependents + reject API transition). Two unhandled 500s on normal operations.
2. T7 — clone-URL scheme allowlist and never-rmtree-local_path. RCE/SSRF + data loss.
3. T5 (decorated symbols) — unwrap `decorated_definition`; this alone restores route handlers and decorated methods to the graph.
4. T1 — align the three frontend enums with backend taxonomy.
5. Code-pipeline error handler: `rollback()` before mutating ORM (otherwise the real exception is masked by `PendingRollbackError`).

**Phase 2 — high-value behavior:**
6. T2 — feed the reranker a wide pool (it's currently a no-op for recall).
7. T9 — scope enrichment to the repo, honor configured batch size, retry failed symbols.
8. T6 — lock + bounded-queue the WebSocket broadcast.
9. T10 — preserve seeded reasoning params in the wizard; surface `ml_profile_ref`.
10. T4 — fix the supersession trigger gate and markers.

**Phase 3 — robustness/consistency:**
11. T8 — close the React Query invalidation gaps (ideally via shared mutation hooks).
12. T11 — add `Field` bounds; make the rate-limiter proxy-aware.
13. T12 — seed Leiden and graph layout.
14. Remaining Medium findings per subsystem below.

**Phase 4 — cleanup:** Low/Nit items, module splits (T13), dead code, doc drift.

---

## Findings by subsystem

Each subsystem lists its High/Medium findings in detail and Low/Nit findings as
compact tables (title — `location`). Full evidence and suggested fixes for every
finding are in the machine-readable workflow outputs referenced in the appendix.

### Memory pipeline & supersession

**[Medium] Within-batch supersession silently fails (same `created_at`).**
`supersession.py:105` requires `candidate.created_at < new` (strict), but
`batch_create_memories` commits all rows in one transaction so
`server_default=func.now()` gives every row the transaction-start timestamp.
A memory plus its replacement ingested in one batch never supersede. Fix:
tie-break equal timestamps by id, or order by an ingest ordinal.

**[Medium] Supersession gated on the wrong condition.** `pipeline.py:400` only
calls `detect_supersessions` when the *new* memory's `technologies` is non-empty,
but the detector keys off the REPLACES *target* overlapping `candidate.technologies`.
A replacement whose new subject is typed `concept`/`artifact` skips supersession
entirely. Fix: gate on the presence of a REPLACES relation, not on
`mem_record.technologies`.

| Sev | Finding | Location |
| --- | --- | --- |
| Low | Speculative gate uses bare-substring `would`/`could` (over-suppresses) | `supersession.py:36-40` + `relations.py:104-113` |
| Low | Confidence weighting rescales `rrf_score` but reranker orders by `rerank_score` (no-op on order) | `pipeline.py:855-864,796-798` |
| Low | `process_batch` has no integration coverage (skipped placeholder test) | `tests/test_pipeline_process_batch.py:53-62` |
| Nit | Bare `= ANY(:ids)` diverges from the defensive `CAST(:ids AS uuid[])` convention | `pipeline.py:850` |
| Nit | Child-table name `entity_embedding_cache` contradicts CLAUDE.md `entity_embeddings_cache` | `embedder_registry.py:67` |
| Nit | Single-flight flag cache re-checks freshness with a pre-lock `now` | `pipeline.py:58-75` |

### Extraction & relations

**[Medium] `next.js` (and any `.js` override) corrupted to a bare stem.**
`_normalize_names` runs `_DOTTED_METHOD` before `_apply_type_overrides`, so
`next.js → next` and the curated `tool` type is lost; the rescue layer re-adds
`next.js` separately. Conditional (self-heals when the name appears cleanly in
the text; produces a bogus `next` node + dropped edge otherwise). Fix: skip the
dotted-strip when the lowercased name is a curated entity. `extraction.py:146,311-313,235`.

**[Medium] `instead of` treated as negation drops the rejected alternative.**
For "chose pgvector instead of qdrant", `_filter_negation_only` drops `qdrant`,
so the `pgvector IMPROVES_ON qdrant` edge the prompt explicitly wants is removed
— `_filter_negation_only` runs before the selection gate that would keep it.
Fix: remove `instead of` from `_NEGATION_WINDOW`, or protect relation endpoints.
`extraction.py:258-274,1250-1285`.

| Sev | Finding | Location |
| --- | --- | --- |
| Low | `_suppress_temporal_edges` uses first-occurrence `find()` (wrong span pair on repeated names) | `extraction.py:1759-1762` |
| Low | `_drop_uses_when_replaces_exists` drops a legitimately distinct USES (unordered match) | `extraction.py:1503-1538` |
| Low | `_validate_directions` substring containment can mis-swap on shared substrings | `extraction.py:1393-1394,1570-1581` |
| Low | `_fan_out_coordinated` runs after `_filter_event_edges`; can mint illegal event edges | `extraction.py:1812-1853` |
| Low | `_filter_literals` dotted-stem guard can drop a real standalone entity | `extraction.py:1599-1618` |
| Nit | Docstring says `tail_gap <= 5` but code uses 15 | `extraction.py:781-782,828` |
| Nit | Dead `hardware_only` field in `_RESCUE_CONNECTORS` | `extraction.py:580-600,864` |
| Nit | `_RESCUE_SKIP_SHORT` / `_SHORT_TOOL_ALLOWLIST` disagree, no invariant | `extraction.py:191-205` |
| Nit | `_split_clauses` recomputed 3× per memory | `extraction.py:830,996,1165` |

### Entity graph & dedup

| Sev | Finding | Location |
| --- | --- | --- |
| Low | `get_neighbors_by_name`/`get_relations_between` resolve by name only, ignoring the `(name, entity_type)` key | `graph.py:305-310,484-507` |
| Low | `create_relationship` silently drops the edge when an endpoint is missing (no log) | `graph.py:177-188` |
| Nit | `insert_entity_stub`/`upsert_entity_simple` create entities with no `memory_ids` (instant orphans) | `graph.py:520-541` |
| Nit | `find_similar_entity` ANN probe unordered tie + strict `>` drops exact-equality matches | `graph.py:33-35` |
| Nit | `names_distinct` doesn't guard month abbreviation vs full-name aliases | `relations.py:92-96` |

> Note: a Phase-4/Phase-5 ordering hole (dedup can canonicalize onto a ghost the
> same memory is about to delete) and a name-only endpoint resolution gap were
> raised by the entity-graph unit; treat the two `graph.py` lookups above as the
> actionable core.

### Code indexing pipeline

**[High] Decorated Python functions/methods are silently dropped.**
Tree-sitter wraps decorated defs in a `decorated_definition` node, which is in
neither `SYMBOL_NODE_TYPES` nor `BODY_CONTAINER_TYPES`, so `_walk_tree` /
`_collect_nested_symbols` never visit it. Every FastAPI route handler,
`@property`/`@staticmethod`/`@classmethod` method, and `@pytest.fixture` gets no
`CodeSymbol`, no chunk/embedding, and cannot be a call source/target. Fix:
unwrap `decorated_definition`. `code_parser.py:355-390,165,171`.

**[High] Pipeline error handler commits without rolling back a failed tx.**
The `except` branch mutates `repo.status` and commits with no prior
`session.rollback()`; if the original exception was a DB error, the session is in
a need-rollback state and the commit raises `PendingRollbackError`, masking the
real error and leaving status stuck. The project's own memory note records the
rule "rollback before mutating ORM in error handlers". `code_pipeline.py:302-328`.

**[Medium] Phase 13 enrichment cap drains a global cross-repo queue.**
`process_batch`'s SELECT has no `repo_id` filter, so reindexing repo A can spend
the entire 1000-symbol budget on repo B's backlog while reporting success for A.
`code_pipeline.py:1180-1185`, `enrichment_worker.py:35-42`.

**[Medium] Tree-sitter re-parses every file twice more (phases 6 & 7).**
Phase 2 discards the parsed tree, so phases 6/7 each re-encode and re-parse every
file inline in the event loop — 3× parsing per full reindex. Fix: cache the tree
on `self._parsed`. `code_pipeline.py:747-754,888-895`.

| Sev | Finding | Location |
| --- | --- | --- |
| Low | `has_method` edges & chunking cover only top-level classes (nested classes missing) | `code_pipeline.py:1587-1600`, `code_parser.py:644-678` |
| Low | Inner `prompt` local shadows the imported `prompt` module | `enrichment_worker.py:8,52,58` |
| Low | Phase 14 wiki generation swallows exceptions (not in `_stats['errors']`) | `code_pipeline.py:1190-1202` |

### Call / import / heritage resolution

**[High] Resolver cache key omits `arg_count`/`call_form` → wrong overload.**
`cache_key = (from_file, called_name, receiver_name)` but `_filter` disambiguates
by arity and call form; the first call's full result is cached and returned for a
later same-name call of different arity. `call_resolver.py:58-60,156-167`.

**[High] Named-import map stores raw module strings as `source_file`.**
`build_named_imports` stores `imp.source` (e.g. `app.services.foo`) where the
resolver expects a repo-relative file path, so the 0.90 import-scoped resolution
branch is dead for any entry `propagate()` doesn't overwrite (i.e. all of
Go/Rust/Java/Kotlin). `call_resolver.py:270-282,94-104`.

**[Medium] Call-edge `ON CONFLICT DO NOTHING` collapses every call site to one edge.**
Line lives only in `properties`, not the key, so a caller calling the same target
on multiple lines yields one edge; call-frequency/line attribution (blast-radius,
process tracing) is wrong. `code_pipeline.py:840-854,1007-1024`.

**[Medium] Self-call inheritance ignores interface-default (`implements`) methods.**
`find_inherited_method` walks only `extends`, so Java/Kotlin/C# default-interface
and Python-ABC self-calls don't resolve. `heritage_resolver.py:233-245`.

**[Medium] `BUILTIN_SKIP` suppresses user-definable names.** `resolve()` returns
`None` for `map`/`filter`/`type`/`set`/`open`/`Object`/`Array`/`Set`/… with no
check for a same-named user symbol, and the set is language-agnostic. Systematic
under-linking. `call_resolver.py:18-31,55-56`.

| Sev | Finding | Location |
| --- | --- | --- |
| Low | Phase 08 rebuilds `import_map` from `_all_imports`, contradicting phase 04's refined map | `code_pipeline.py:900-902,960-966` |
| Low | `_try_interface_dispatch` assumes interface methods have `owner_id is None` | `call_resolver.py:136-146` |
| Low | JVM member-import detection misclassifies lowercase-first class names | `jvm_resolver.py:78-84` |
| Low | `build_import_map` bare-import matching is loose suffix/stem matching | `call_resolver.py:206-250` |
| Low | `build_*_imports` ignore relative-import dots for non-Python (hardcodes `.py`) | `call_resolver.py:288-305` |
| Low | `resolve_chain` re-derives `current_type` via `lookup_global`, can mismatch | `call_resolver.py:187-197` |
| Nit | C++ leftmost-base MRO keeps last occurrence | `heritage_resolver.py:75-96` |

### Community / process / query analytics

**[High] Community label collisions overwrite distinct communities.** `comm_key`
is just the most-common directory name; two Leiden communities in the same
directory produce identical keys, and `ON CONFLICT DO UPDATE` silently merges
them (and their `member_of` edges). Fix: append `comm_id`/hash to the key.
`community_detector.py:155-203`.

**[Medium] Leiden detection is non-deterministic (no seed).** Community
membership and labels differ between identical reindexes. `community_detector.py:122-128`.

**[Medium] `search_code` text branch ignores the language filter.** The vector
branch filters by language but the keyword branch doesn't, so RRF fuses a
filtered semantic list with an unfiltered keyword list. `code_query.py:56-96`.

**[Medium] Process tracer emits `entry_point_of` edges with a non-symbol source.**
Route/tool entries insert `source_kind='symbol'` with a route key, producing a
dangling/mis-kinded reference. `process_tracer.py:156-245`.

| Sev | Finding | Location |
| --- | --- | --- |
| Low | Process step edges silently truncated by `dynamic_cap` (later steps dropped) | `process_tracer.py:247-267` |
| Low | AAAK dialect can't detect all-lowercase entity names | `dialect.py:253-262` |
| Low | Suffix index case-insensitive map omits no-extension/dotted forms | `suffix_index.py:36-94` |
| Nit | Unused `uuid4` imports | `community_detector.py:7`, `process_tracer.py:7` |
| Nit | Blast-radius CTE: redundant `DISTINCT` with `GROUP BY/MIN` | `code_query.py:319-322` |

### Classification & enrichment

**[High] Failed code-symbol enrichment is terminal.** On any transient LLM error
the worker sets `enrichment_status='failed'`, and nothing ever resets it to
`pending`; the symbol loses its summary until a full reindex. Both the inline
drain and the scheduled job share the `pending`-only query. Fix: keep transient
failures as `pending` with a retry counter, or add a periodic reset sweep.
`enrichment_worker.py:82-85,37`.

**[Medium] Inline Phase-13 drain ignores the configured `batch_size` and caps at 1000.**
Uses the default `batch_size=5` (not the operator's Jobs-UI value) and loops at
most 200×; repos with >1000 symbols are silently truncated. `code_pipeline.py:1180-1184`.

| Sev | Finding | Location |
| --- | --- | --- |
| Low | `_disambiguate` emotional branches are dead in the default `simple` mode | `memory_classifier.py:413-427`, `classification_areas.py:531-564` |
| Low | `convo_miner` general path ignores configured areas/mode | `convo_miner.py:203-220` |
| Low | `convo_miner` general mode conflates room slug with `memory_type` | `convo_miner.py:209-218` |
| Low | ML classifier nulls `llm_summary`/empties emotions/flags while enrichment is on | `classification_ml.py:65`, `pipeline.py:325-329` |
| Low | `process_batch` classification/`llm_*` write parity untested (skipped) | `tests/test_pipeline_process_batch.py:54-61` |

### LLM orchestration & config

**[High] `cfg_to_schema` drops `ml_profile_ref`.** Resolved and persisted
correctly, but never serialized back, so GET reports `ml_profile_ref=None` and
the UI dropdown loses the selection on refresh. One-line fix. `config.py:33-42`.

**[Medium] Wizard finalize wipes per-purpose `params` to `{}`.** Discards the
seeded vendor reasoning controls the orchestrator relies on; Google/gpt-5
extraction can return empty content on the first call (only zai/deepseek have a
runtime auto-injection fallback). `setup.py:498-527`.

| Sev | Finding | Location |
| --- | --- | --- |
| Low | `chat_completion_stream` omits the zai/deepseek thinking-disable injection + response_format handling | `llm.py:471-498` |
| Low | Embedding dispatch only special-cases ollama; no per-vendor request shaping or capability assertion | `llm.py:64-139` |
| Low | No retry/backoff and a single 300s timeout; one transient 5xx fails the whole step | `llm.py:29` |
| Low | Provider overlay doesn't carry `supports_embedding` into resolved config | `config.py:84-91` |
| Low | Embedding purpose params also blanked by wizard | `setup.py:521-527` |

### Repositories, models, migrations

**[High] Deleting a superseding memory violates `chk_superseded_has_pointer`.**
`superseded_by` is `ON DELETE SET NULL`; deleting memory N nulls dependents'
pointer while `status` stays `superseded`, so the delete aborts with
IntegrityError. Fix: demote dependents (`status='deprecated', superseded_by=NULL`)
in the same transaction before deleting. `models/memory.py:64-79`, `memory.py:141`.

| Sev | Finding | Location |
| --- | --- | --- |
| Low | HNSW index name can exceed 63-char `NAMEDATALEN`, silently truncate/collide → partition with no vector index | `embedder_registry.py:176-182` |
| Low | `knowledge_triples.source_memory_id` SET NULL but orphans never pruned | `models/graph.py:57-59`, migration `0001:281` |
| Low | `create_relationship` no-ops silently on missing endpoint | `graph.py:177-188` |
| Low | `code_chunk` child table has no unique key; correctness relies on delete-before-insert | `embedder_registry.py:52-66`, `vector.py:363-410` |
| Nit | `set_tags` re-selects after `on_conflict_do_nothing` without locking | `relational.py:156-175` |
| Nit | `Memory.update` issues two full refreshes (extra round-trip) | `relational.py:59-62` |
| Nit | Migration docstring uses `entity_embedding_cache` vs contract name | `0001_initial_schema.py:17,292,513` |
| Nit | `find_similar_entity` non-sargable recomputed cosine predicate in WHERE defeats HNSW | `graph.py:27-38` |

### Core API routes

**[High] `PUT /memories/{id}` `status="superseded"` → unhandled 500.**
`MemoryUpdate` allows the transition with no `superseded_by`, and `update` just
setattrs and flushes, violating the CHECK. Fix: drop `superseded` from the public
`MemoryUpdate.status` and wrap the repo update to return 4xx, not 500.
`memories.py:78`, `memory.py:103`, `relational.py:50`.

**[Medium] `CodeSearchRequest.limit` / `BlastRadiusRequest.max_depth` / `ReasonRequest.limit` unbounded.**
Plain ints, no `Field(ge/le)`, unlike `MemorySearchRequest`. DoS footgun on graph
BFS. `schemas/code.py:75,91`, `reason.py:6`.

**[Medium] `search_code` maps null `repo_id` to a zero-UUID.** Fabricates an
all-zeros repo id (schema is non-optional), breaking result→repo linking. Fix:
make `CodeSearchResult.repo_id` optional. `code.py:41`.

**[Medium] Chat stream loses the persisted turn on client disconnect.**
`send_message` only flushes; the commit is deferred to request end, which a
mid-stream disconnect rolls back, discarding both the user message and streamed
assistant content. Fix: commit the user turn before the LLM stream. `chat.py:126-148`, services `chat.py:104`.

| Sev | Finding | Location |
| --- | --- | --- |
| Low | `/duplicates` `threshold` query param unbounded | `memories.py:162-170` |
| Low | reindex flips status to `indexing` and commits before the task is registered | `repos.py:165-211` |
| Low | LLM-dependent deps inconsistently 503 vs silently pass `llm=None` | `deps.py:21-28,37-48`, `code.py:24` |
| Nit | `bulk_delete` partial failure commits some then can 500 with no rollback signal | `memories.py:101-111`, `memory.py:160-178` |
| Nit | `create_conversation` response omits `message_count` | `chat.py:49-62` |
| Nit | `request: Request = None` default masks missing-Request errors | `code.py`, `graph.py`, `vectors.py` |

### Admin / config API routes

**[Medium] Pre-setup filesystem browse is unauthenticated with no `SETUP_SECRET` (non-prod).**
`fs/roots` and `fs/list` let any reachable client enumerate host drives before a
password exists. Acceptable per the local-install design but undocumented; bind
to loopback or require the secret off-localhost. `setup.py:267-295,50-67`.

| Sev | Finding | Location |
| --- | --- | --- |
| Low | `POST /config/llm` should be `PUT` per the conventions doc (known deviation) | `config.py:110` |
| Low | Bulk-retry error count can be wrong when `process_batch` raises mid-way | `pipeline_failures.py:205-220` |
| Low | Graph-stats failure swallowed; can leave the session in a failed state | `analytics.py:36-42` |
| Low | reembed `_dispatch_single_category` may reference `batch_id` before assignment | `reembed.py:104-154` |
| Low | Setup finalize issues an auth cookie even when LLM/repo blocks failed (200 + per-section status) | `setup.py:612-621` |
| Low | Job trigger doesn't surface 409 when a run is already in progress | `jobs.py:120-135` |
| Nit | Unused `request: Request = None` param | `analytics.py:27` |
| Nit | `update_llm_config` rebuilds the fingerprint by hand vs the canonical helper | `config.py:229` |
| Nit | `_validate_name` whitespace check is order-dependent/confusing | `config.py:254-265` |

### MCP server & websocket

**[High] `EventManager.broadcast` has no per-connection lock.** Concurrent
broadcasts from the pipeline fan-out, indexing, jobs, and reembed can interleave
ASGI sends on one socket and raise "Unexpected ASGI message", killing the client.
`websocket.py:26-41`.

**[Medium] Broadcast has no send timeout (head-of-line blocking).** A backgrounded
tab applies TCP backpressure; because producers `await` the broadcast, the
indexing/memory pipeline stalls behind the slowest viewer. `websocket.py:35-39`.

**[Medium] MCP write tools can't set `project`.** `memory_add`/`memory_batch_add`
never pass `project`, so all MCP memories land in `default` — supersession (which
requires same project) can't fire across the intended project. `server.py:63-81,181-196`.

| Sev | Finding | Location |
| --- | --- | --- |
| Low | `broadcast` logs schema-validation failures but still sends the payload | `websocket.py:26-33` |
| Low | Receive loop only catches `WebSocketDisconnect`; other errors leak the connection | `websocket.py:69-74` |
| Nit | `code_search` raises a tool error instead of a typed unavailable result when LLM unconfigured | `server.py:313-314` |

### Jobs, tasks, repo manager

**[High] `pull_repo` reclone fallback can delete a user's `local_path` folder.**
On any transient git failure `needs_clone=True` triggers `shutil.rmtree(cwd)` where
`cwd` is the operator's own checkout (a `local_path` repo that also has a `url`).
Fix: branch early for `local_path` repos and never rmtree outside `REPOS_BASE_DIR`.
`repo_manager.py:322-356`.

**[Medium] Repo URL has no scheme/host validation (SSRF / local-file).** See T7.
`schemas/code.py:9`, `repo_manager.py:366-383`.

**[Medium] Git token persisted into on-disk `.git/config` via `remote set-url`.**
Plaintext token lingers, including in the operator's own `local_path/.git/config`.
Fix: per-invocation auth (`http.extraHeader`/`GIT_ASKPASS`), reset remote after.
`repo_manager.py:332-337`.

**[Medium] `TaskRegistry` leaks completed/cancelled entries.** Cleanup only runs
on `register()` when `len > 100`; smaller deployments never prune. `task_registry.py:24-39,89-103`.

**[Medium] Manual `trigger()` runs the full job synchronously in the request.**
Holds the per-job lock for minutes (repo_sync clones every repo), blocking
scheduled ticks; no timeout. Fix: fire-and-return via `create_task`/`wakeup`.
`jobs.py:120-135`, `job_registry.py:323-336`.

| Sev | Finding | Location |
| --- | --- | --- |
| Low | `GIT_ASKPASS='echo'` does nothing useful; use `GIT_TERMINAL_PROMPT=0` | `repo_manager.py:333` |
| Low | `load_config` default `enabled=True` diverges from `from_dict` default `False` | `job_registry.py:109-120,172-218` |
| Low | `validate_local_path` home-subpath check has a Windows gap | `repo_manager.py:39-71` |
| Low | pynvml handle captured once at import; survives driver reload as stale | `system_metrics.py:23-30,56-64` |
| Low | Deprecated `asyncio.get_event_loop()` inside coroutines | `repo_manager.py:112-115,399-405` |
| Low | `except (CancelledError, Exception): pass` swallows teardown bugs | `job_registry.py:245-263` |

### Security (cross-cutting)

**[High] `git clone` against an unvalidated, scheme-unchecked URL.** `ext::sh -c`
= arbitrary command execution; `file://`/internal hosts = local-file read / SSRF.
`default_branch` is also interpolated unvalidated (`--upload-pack=` injection).
Fix: scheme allowlist + reject `-`-leading branches + `--` separator.
`repo_manager.py:366-383`, `schemas/code.py:9`.

| Sev | Finding | Location |
| --- | --- | --- |
| Medium | Login rate limiter keys on `request.client.host` — shared bucket / lockout behind a proxy | `auth.py:52-53`, `login_rate_limit.py:42-49` |
| Low | Password-change & setup-finalize have no brute-force throttle | `auth.py:109-151`, `setup.py:369-407` |
| Low | Production detection diverges (startup validator vs `/.dockerenv` gate) → self-lockout | `setup.py:349-351`, `config.py:136-153` |
| Low | SSRF via admin-controlled LLM `base_url` in probe/test/models endpoints | `setup.py:124-162`, `config.py:423-620` |
| Low | Git auth token & provider api_keys stored plaintext at rest | `repo_manager.py:159-162` |
| Nit | Setup section errors return `str(exc)` to the client (internal detail) | `setup.py:531-588` |

### Frontend — routes & data flow

**[Medium] Dashboard `['overview']` is never invalidated by pipeline/memory WS events.**
The handler refreshes `['stats']` etc. but not `['overview']`, the landing-page
query; with `staleTime 60s` + `refetchOnWindowFocus:false`, the dashboard shows
stale counts/recent-memories after every ingest/delete. `websocket.ts:55-71`,
`use-pipeline-api.ts:188-193`.

| Sev | Finding | Location |
| --- | --- | --- |
| Low | Memory-detail `['memory', id]` never invalidated on delete/pipeline completion | `use-memory-api.ts:50-113`, `websocket.ts:66-71` |
| Low | Memories focus-scroll effect cleanup unreachable; re-runs on array identity change | `memories.tsx:148-163` |
| Low | `unfilteredTotal` falls back to filtered total, mislabeling header count | `memories.tsx:130-141,458-465` |
| Low | WebSocket `onmessage` `JSON.parse` unguarded (malformed frame silently drops handling) | `websocket.ts:45-53` |
| Low | 401 does a full-page `window.location` redirect, dropping SPA state | `lib/api.ts:19-23` |
| Nit | `confirmDelete` carries a stale unused `qc` dependency | `memories.tsx:231-246` |
| Nit | Repo "last indexed"/counts can lag (stats/tasks skipped per tick, no final flush) | `websocket.ts:116-134` |

### Frontend — API hooks & types

**[High] `MemoryStatus` enum drifts from backend** (`archived`/`deleted` phantom,
`deprecated` missing) — invalid values sent to the server. `use-memory-api.ts:4,143`.
*(Also flagged independently by the cleanup unit.)*

**[High] `createMemorySchema.memory_type` diverges from `MEMORY_TYPES`** — offers
`context` (lost to default), can't offer `problem`/`architecture`/`milestone`.
`features/memories/schemas.ts:9-15`.

| Sev | Finding | Location |
| --- | --- | --- |
| Medium | Bulk-archive invalidates only `memoriesPaginated`, leaving stats/tags/memories stale | `memories.tsx:271-289` |
| Medium | `useReprocessStream` doesn't invalidate `memoriesPaginated`/`tags` | `use-pipeline-api.ts:152-153` |
| Medium | `useUpdateConversation` invalidates the list but not the open detail | `use-chat-api.ts:66-85` |
| Low | `MemoryContextData.entities.properties` typed `string` but backend returns JSONB object | `use-graph-api.ts:38-45` |
| Low | `apiFetch` treats every 401 as logout + hard redirect, even on background queries | `lib/api.ts:19-23` |
| Low | `useReembed*` mutations have no `onSuccess` invalidation; rely entirely on WS | `use-pipeline-api.ts:294-340` |
| Nit | `PipelineFailure.metadata` type collides with backend `metadata_` | `use-pipeline-api.ts:46` |
| Nit | `useFeatureFlags` interface includes `classification_mode/areas` not in the flag set | `use-config-api.ts:228-240` |

### Frontend — LLM config UI

**[High] ML profile TTL accepts `NaN` when the number field is cleared.** Stored
raw, marks the row dirty, and writes `ttl_seconds: NaN` into the PUT body; other
call sites guard this exact case. `MLProfilesPanel.tsx:253,347`.

**[Medium] Resolved summary shows a stale connection when a linked profile's provider is missing.**
`applyLlmProfile` keeps previous connection fields when `provider_ref` dangles,
then captions them "Resolved from Profile X". `LLMPurposeCard.tsx:206-232`.

**[Medium] `purpose=reasoning` on an embedding profile leaves `is_embedding` set.**
The non-embedding branches of `purposePatch` never clear `is_embedding`, creating
an inconsistent row. `LLMProfilesPanel.tsx:556-563`.

| Sev | Finding | Location |
| --- | --- | --- |
| Low | Embedding-capability mismatch is only a warning, not a save block | `LLMProfilesPanel.tsx:260-309` |
| Low | Editing params JSON marks dirty but save can be a no-op clear of `profile_ref` | `LLMPurposeCard.tsx:582-595` |
| Low | Draft resets on any stored-map reference change without a dirty guard | `LLMProfilesPanel.tsx:112-114`, `LLMProvidersPanel.tsx:79-81` |
| Nit | Provider "Reset" discards unsaved edits with no confirmation | `LLMProvidersPanel.tsx:186` |
| Nit | Provider "Display label" edits silently change resolved summary text | `LLMProvidersPanel.tsx:541-549` |
| Nit | Raw glyph triangles (▾/▸) instead of icon components | `LLMPurposeCard.tsx:282,463` etc. |
| Nit | Service status dots are color-only (no text/aria alternative) | `MaintenancePanel.tsx:43-49` |
| Nit | Combobox free-text model committed without trimming | `LLMProfilesPanel.tsx:696-699` |

### Frontend — graph rendering

**[High] `Graph2DRenderer` ignores `spacing`/`clusterTightness` props** — two
toolbar sliders rebuild the graph but never change the layout (FA2 settings are
hardcoded). Fix: consume the props or hide the sliders in 2D. `graph-2d-renderer.tsx:42-65,359-368`.

**[Medium] `KnowledgeGraphRenderer` FA2 stop timer never cleared on unmount.**
Leaks a queued timer per mount (siblings use a ref). `knowledge-graph-renderer.tsx:217-236`.

**[Medium] Stale memory-type color map keyed on legacy `debug`/`session` names.**
`LEGACY_MEMORY_TYPE_MAP` rewrites `debug → problem`, absent from the map, so the
curated colors regress to hash-derived. `graph-colors.ts:78-110`.

| Sev | Finding | Location |
| --- | --- | --- |
| Low | `Graph2DRenderer` accepts an unused `data` prop | `graph-2d-renderer.tsx:35,52-65` |
| Low | `Graph3DRenderer` sets `document.body` cursor on hover, never resets on unmount | `graph-3d-renderer.tsx:57-71` |
| Low | Hardcoded chrome colors in 2D/3D/knowledge renderers bypass theme tokens | `graph-2d-renderer.tsx` etc. |
| Low | `CodeGraphRenderer` animates the camera on every selection change incl. deselect | `code-graph-renderer.tsx:949-971` |
| Low | Force-layout seeds positions with `Math.random()` (non-deterministic rebuilds) | `code-graph-renderer.tsx:501-598` etc. |
| Low | `filteredNodes` default-kind `'function'` fallback can mis-bucket kind-less nodes | `code-graph.tsx:190-224` |
| Low | `deriveProcesses` re-scans all edges per process node (O(P·E)) | `code-processes.ts:64-96` |
| Low | `Graph3DRenderer` build effect has no THREE dispose-on-unmount for ring/hull meshes | `graph-3d-renderer.tsx:36-231` |
| Nit | Process flow step swatch can resolve to undefined background | `process-flow-modal.tsx:82-86` |

### Frontend — misc features

**[High] `EditRepoDialog` `enrich_symbols`/`generate_wiki` toggles are silently dropped.**
The switches write to `PUT /repos/{id}`, but `RepoUpdate` has only
name/auto_sync/auth_token/default_branch — Pydantic drops the extras, so the
toggles are dead controls. Fix: remove them (they're reindex-time options) or add
them to the model. `edit-repo-dialog.tsx:132-154`, `repos.tsx:544-545`.

**[High] `EditRepoDialog` keeps stale values when reopened for a different repo.**
Always-mounted; react-form captures `defaultValues` once, so editing repo A then
opening repo B shows A's values and can overwrite B. Fix: `key={editingRepo?.id}`.
`edit-repo-dialog.tsx:32-47`.

**[Medium] retry-all / retry-single drop the stale-table safety net on WS disconnect.**
Both removed their `onSuccess` invalidation and rely solely on WS events; a resolve
during a transient disconnect is lost with no replay. `use-pipeline-api.ts:217-265`.

| Sev | Finding | Location |
| --- | --- | --- |
| Low | Chat sidebar timestamp/message-count stale after sending in an existing conversation | `use-chat-stream.ts:63-69` |
| Low | Bulk delete fans out N `memory.deleted` broadcasts → N redundant invalidations | `websocket.ts:66-71`, `memory.py:160-178` |
| Low | Setup wizard repo rename inputs/checkboxes lack accessible labels | `StepFinish.tsx:91-99` |
| Low | `ReindexDialog` retains previous checkbox selections across reopens | `reindex-dialog.tsx:23-37` |
| Nit | Single-memory delete double-invalidates (mutation `onSuccess` + WS event) | `use-memory-api.ts:83-86` |

### Backend cleanup & contract drift

| Sev | Finding | Location |
| --- | --- | --- |
| Low | `bulk_delete_memories` is not atomic — partial failure leaves mixed committed state | `memory.py:160-176` |
| Low | `WikiGenerator(session, None)` on the read path — silent footgun if `read()` ever calls `generate()` | `code.py:135`, `wiki_generator.py:24-29` |
| Nit | `extraction.py` is a 2053-line module mixing ~50 helpers with the service | `extraction.py:1-2053` |
| Nit | `config.py` route module (1050 lines) bundles five config domains | `config.py:101-1050` |
| Nit | Deadlock-avoidance rationale comment triplicated across three layers | `memory.py`, `memories.py`, `use-memory-api.ts` |
| Nit | New docstrings narrate WHAT (against the comment policy) | `wiki_generator.py:20-25`, `code.py:131-135` |
| Nit | `get_wiki` returns `dict|None` with no `response_model` | `code.py:123-135` |

> The cleanup unit also re-flagged the `MemoryStatus` frontend drift (counted
> once under Frontend — API hooks).

---

## Appendix

### What was refuted / not a problem
Verification refuted several first-pass claims and downgraded others, so the
list above is the survivors. Notably confirmed-clean: the closed taxonomy
normalization, fingerprint registration ordering, idempotent re-extraction via
`delete_by_memory_id`, the `technologies` lowercase/GIN denorm, per-fingerprint
partition isolation (no cross-fingerprint joins), `memory_id` str/UUID
normalization at the boundaries checked, the slug-collision guard, vendor auth
headers (x-api-key vs Bearer), seed forwarding, the `llm_config_lock` swap path,
and backend↔frontend WS event-map parity. One finding remained **uncertain**: a
`_clone_repo` `cwd=dest.parent` concern that is safe for the id-based path but
interacts with the unvalidated-URL issue (T7) — fixing T7 resolves it.

### Two known issues confirmed
- The "class methods not extracted → hollow OO graph" item from the prior core-systems review is **partly fixed** (undecorated body-nested methods) but **decorated** functions/methods remain dropped (T5, High).
- The user-reported "1000/7640 enrichment" is root-caused beyond the inline cap: it also ignores configured batch size and drains a **global cross-repo** queue (T9).

### Reproducing / drilling in
Per-finding evidence, adversarial verifier notes, and suggested fixes for all 183
findings are in the workflow result JSON under the session task outputs
(`darkmem-comprehensive-audit` + `darkmem-audit-recovery`). The audit ran 17
subsystem units; 14 were re-run in a second pass after the first emit attempt
failed to return structured output for the broad units.

### Suggested next step
This document is review-only — no code was changed. Recommend tackling **Phase 1**
(the two CHECK-constraint 500s, clone-URL validation, decorated-symbol
extraction, the three enum mismatches, and the error-handler rollback) as a first
remediation branch; most are small, localized fixes with outsized impact.
