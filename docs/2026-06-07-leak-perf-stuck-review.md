# Darkmem review — memory leaks, performance bottlenecks, stuck jobs/tasks

Date: 2026-06-07
Scope: backend async runtime (FastAPI + asyncio + asyncpg/SQLAlchemy + pgvector,
plus tree-sitter parsing, HF/ML dispatch, git repo sync, LLM HTTP calls).
Method: three parallel sweeps (one per concern) + line-level verification of every
HIGH finding against the actual source. Findings marked **[verified]** were read
and confirmed at the cited lines.

---

## Executive summary

The single most important issue is not one bug but a **compounding chain** that
lets a slow or hung upstream stall a background job indefinitely while holding its
lock, and a **second, independent** path that lets a job loop die silently and
never fire again. Memory growth and query patterns are real but secondary.

Three things to fix first, in order:

1. **Cap runner duration.** A job lock is held across an unbounded runner, the LLM
   client has a 5-minute blanket timeout, and executor parse/inference work has no
   timeout at all. Together a single flapping LLM endpoint or one pathological
   source file wedges `repo_sync` / `code_enrichment` for many minutes to hours.
   (Findings **L1 + L2 + L3**.)
2. **Stop the loop from dying.** `load_config`/`save_config` inside `_run_once`
   sit outside the try/except, and `_loop` only catches `CancelledError`. A
   transient DB error around a run kills the job loop permanently. (Finding **L4**.)
3. **Bound the entity cache.** A process-lifetime dict on the pipeline singleton
   grows once per distinct entity name with no cap and only lazy expiry — a slow
   monotonic heap leak over a long-running ingest. (Finding **M1**.)

Reassurance: the recently-added strong-ref background-task pattern
(`utils/background.spawn`), the websocket registry, DB session lifetimes, the MCP
server (stateless), off-thread ML/git/Leiden work, and the cron floor math are all
**correct** — see "Verified clean" at the end. The problems are concentrated, not
pervasive.

---

## Stuck jobs / tasks

### L1 — Job lock held across an unbounded runner (HIGH) **[verified]**
`backend/app/services/job_registry.py:337-350`
```python
async def _run_once(self, key: str) -> None:
    job = self._jobs[key]
    async with job.lock:                 # held for the WHOLE runner
        cfg = await self.load_config(key)
        ...
        try:
            await job.runner()           # repo_sync → CodePipeline.run(); no overall ceiling
        ...
        await self.save_config(key, cfg)
```
The per-job `asyncio.Lock` wraps the entire `runner()`. `repo_sync` fans out LLM
calls and executor parse work with no aggregate time bound. While the lock is held
every scheduled tick re-enters `_run_once` and blocks on `job.lock`; the job stops
making progress and back-pressures. With thousands of symbols serializing at the
per-call timeout, a single slow upstream turns a 10-second cron into an hours-long
stall.
**Fix:** wrap the runner in `asyncio.wait_for(job.runner(), timeout=job.max_run_seconds)`
with a per-job ceiling (e.g. repo_sync 1800s, enrichment 300s). Never hold the lock
across an operation with no upper bound.

### L2 — Single 300s blanket LLM timeout × transport retries (HIGH) **[verified]**
`backend/app/services/llm.py:32-39`
```python
_TRANSPORT_RETRIES = 2
self._client = httpx.AsyncClient(
    timeout=300.0,
    transport=httpx.AsyncHTTPTransport(retries=self._TRANSPORT_RETRIES),
)
```
A scalar `timeout=300.0` sets connect, read, write, **and pool-acquire** all to
300s. Combined with `retries=2`, a connection-level flap can burn up to ~3×300s ≈
15 minutes on a single `embed`/`chat_completion`. Every caller is either in a
request or under a job lock (L1), so this is the multiplier behind every stall.
**Fix:** `httpx.Timeout(connect=10, read=120, write=30, pool=10)` (or per-purpose).
Connect/pool hangs should fail fast; only the read budget needs to be generous.

### L3 — Executor parse / ML inference have no timeout and can't be cancelled (MED) **[verified]**
`backend/app/services/code_pipeline.py:472` (`run_in_executor(None, parse_file, …)`),
`backend/app/services/ml_runtime.py` (`asyncio.to_thread(_load_model_sync / _classify_sync)`).
`run_in_executor`/`to_thread` results can be awaited but the underlying thread
**cannot be cancelled**. A hung tree-sitter parse on a hostile file, or a stalled
model download, occupies a default-pool thread forever; the awaiting coroutine —
under the L1 job lock — never returns. Leiden (`community_detector.py:118`, 60s)
and git (`repo_manager.py:419`, 300/10s) are correctly bounded; parse and model
load are not.
**Fix:** wrap these in `asyncio.wait_for` (frees the coroutine/lock even though the
thread leaks), and use a dedicated bounded executor for parse work so one hang
can't starve the global pool.

### L4 — Job loop dies permanently on a transient DB error (HIGH) **[verified]**
`backend/app/services/job_registry.py:332` and `337-350`
The inner try/except in `_run_once` wraps only `await job.runner()`. The
surrounding `await self.load_config(key)` (line 340) and `await self.save_config(key, cfg)`
(line 350) are **outside** it. In `_loop`, `await self._run_once(key)` (line 332)
is not wrapped either, and the loop's only handler is `except asyncio.CancelledError`
(line 333). So a transient DB blip (pool exhaustion, serialization failure) during
the post-run `save_config` raises straight out of `_loop`, the loop task dies, and
the job **never fires again** until full app restart — while `list_with_config`
still reports it. Note the loop *does* protect its own top-of-iteration
`load_config` (293-309); the unprotected copies are the ones inside `_run_once`.
**Fix:** move `load_config`/`save_config` inside `_run_once`'s try/finally, and/or
wrap `await self._run_once(key)` in `_loop` with a catch-log-continue. Consider a
supervisor that restarts a dead loop.

### L5 — Reindex/clone task exceptions silently swallowed (MED) **[verified]**
`backend/app/services/task_registry.py:42-47`
```python
@classmethod
def _on_done(cls, task_id: str) -> None:
    cls._tasks.pop(task_id, None)        # never calls t.exception()
```
`_run_index`/`_clone_in_background` wrap their bodies, but an exception raised
*outside* that try (e.g. the except-block's own `broadcast` failing) is never
retrieved: asyncio logs "Task exception was never retrieved" at GC and the failure
is otherwise invisible, leaving the repo stuck in `indexing`/`cloning`. Contrast
`utils/background.spawn`, which retrieves and logs the exception.
**Fix:** in `_on_done`, `if not t.cancelled() and t.exception(): logger.error(...)`,
or route reindex/clone through `spawn`.

### L6 — Streaming analytics consumer can block forever (MED)
`backend/app/services/analytics.py:99-147`. The consumer loops
`while completed_count < total: await results_queue.get()`; each producer `put`s
once in `finally`. A task cancelled *before its body runs* (client disconnects the
SSE stream while the task is still queued on the semaphore) never `put`s, so `get()`
blocks forever and the generator hangs.
**Fix:** `asyncio.wait_for` the `get()`, or count via `asyncio.as_completed` /
detect `task.done()`.

### L7 — `trigger()` blocks instead of 409 on a lost race (LOW)
`backend/app/services/job_registry.py:415-419`. The route pre-checks
`job.lock.locked()` (jobs.py:133) and returns 409, but `trigger()` itself just
`async with`es the lock, so two concurrent triggers (or a scheduled run slipping in
after the check) make the HTTP request **hang** for the full runner duration (L1)
rather than failing fast. No deadlock (lock always released), but a hung request.
**Fix:** make `trigger()` itself non-blocking — raise if `job.lock.locked()` or
acquire with a timeout.

---

## Memory leaks / unbounded growth

### M1 — Pipeline entity-embedding cache is unbounded (HIGH) **[verified]**
`backend/app/services/pipeline.py:96` (decl), `:141` (only deletion), `:154/:183` (writes).
`ProcessingPipeline` is a process-lifetime singleton on `app.state.pipeline`. Every
entity name embedded during ingest is stored as `(name_lower, fingerprint) →
(vector, ts)`. The **only** removal is lazy — a key is dropped solely if it's
re-looked-up after its TTL expired. An entity embedded once and never queried again
stays resident forever; each value is a full float vector (≈8 KB at 1024 dims).
No size cap, no sweep, no eviction on the write paths; embedder rotation compounds
it (old-fingerprint keys never purged).
**Fix:** bound it — an `OrderedDict` LRU with `move_to_end` + pop-oldest past a few
thousand entries, or a proactive sweep of TTL-expired keys at the top of
`process_batch`. The DB cache backstops misses, so a small cap is safe.

### M2 — Login rate-limiter never evicts idle IPs (MED)
`backend/app/services/login_rate_limit.py:35,64`. `record_failure` does
`_state.setdefault(ip, …)`; entries are removed only on `record_success`. An IP
that fails once (or whose lockout later expires) but never succeeds leaves a
permanent key. The key space is exactly the hostile one (every spoofable
`X-Forwarded-For`), so it is strictly monotonic with no GC path. Small on a LAN,
unbounded under exposure.
**Fix:** lazy-sweep entries whose `locked_until` has passed and whose `failures`
list is empty, or cap and evict oldest.

### M3 — ML load-locks orphaned on model eviction (LOW)
`backend/app/services/ml_runtime.py:61`. `_load_locks.setdefault(model_repo, Lock())`
is never pruned; `_evict_on_idle` (line 188) pops `_models` but not `_load_locks`.
Bounded by the handful of configured model repos, but a genuine asymmetry.
**Fix:** also `_load_locks.pop(model_repo, None)` under `self._lock` after eviction.

---

## Performance bottlenecks

### P1 — Code-graph write is per-symbol/edge N+1 INSERTs (HIGH)
`backend/app/services/code_pipeline.py:1609-1734` (`_store_graph`). One
`INSERT code_graph_nodes` plus one or two `INSERT code_edges` per symbol, recursing
over every symbol; imports/heritage/properties/routes each loop with their own
per-item awaits. A 300-symbol file ⇒ ~1000+ serialized round-trips, called per
changed file — a 200-file reindex is hundreds of thousands of sequential
statements. This dominates code-indexing cost.
**Fix:** batch each category into one multi-row INSERT per file via
`jsonb_to_recordset` — the exact pattern already used for `code_edges` in Phase
6/10. 2-4 bulk INSERTs per file instead of thousands.

### P2 — Memory-graph write (Phase 5) is per-entity/per-relation sequential (HIGH)
`backend/app/repositories/graph.py:130-221` + `backend/app/services/pipeline.py:368-396`.
`_write_memory` loops `await create_entity(...)` + `await upsert_entity_embedding(...)`
per entity, then `await create_relationship(...)` per relation — and each
`create_relationship` does a SELECT to resolve endpoints then an INSERT (2 round
trips). A memory with 15 entities + 15 relations ⇒ ~45+ serialized round-trips, per
memory, under the write semaphore.
**Fix:** bulk-upsert entities via `INSERT … SELECT FROM jsonb_to_recordset … ON
CONFLICT … RETURNING`; resolve all relation endpoints in one keyed query; bulk-insert
relations; one multi-row embedding upsert.

### P3 — No httpx connection-pool limits on the shared LLM client (HIGH)
`backend/app/services/llm.py`. One shared `AsyncClient` with default pool limits and
the 300s blanket (L2). Nothing caps total in-flight LLM connections, so a large
`pipeline_concurrency` can fan out hundreds of concurrent 300s requests at a
rate-limited vendor.
**Fix:** explicit `httpx.Limits(max_connections=…, max_keepalive_connections=…)`,
document `pipeline_concurrency` as the LLM concurrency knob, and apply the split
timeout from L2.

### P4 — Connection pool thin vs the session-per-operation pattern (MED)
`backend/app/database.py` (`pool_size=20, max_overflow=10` ⇒ 30 max). Pipeline
phases open fresh sessions per unit of fan-out: Phase 4 `_probe` one session per
(name,type) under `Semaphore(pipeline_concurrency)`; Phase 5 one per memory plus a
separate crossref session; `_register_fingerprint`/`_lookup`/`_store` each their own.
A single default-concurrency batch stays under 30, but raising `pipeline_concurrency`
or running code-indexing alongside ingest exhausts the pool and serializes on
checkout.
**Fix:** reuse one session across a phase's fan-out, or size the pool to comfortably
exceed `pipeline_concurrency × sessions_per_unit`.

### P5 — Enrichment drain query has no supporting index (MED) **[verified]**
`backend/app/services/enrichment_worker.py:47-58`. `WHERE enrichment_status='pending'
ORDER BY enrichment_attempts ASC, enrichment_priority DESC LIMIT size` with no index
on `enrichment_status` or the sort keys (migration 0001 only indexes
`ix_code_symbols_file_id`). Phase 13 loops this up to 200×/reindex ⇒ up to 200 full
scans + sorts of a table that grows to tens of thousands of rows.
**Fix:** `CREATE INDEX … ON code_symbols (enrichment_attempts, enrichment_priority DESC)
WHERE enrichment_status='pending'`; reconsider the 200-iteration inline drain.

### P6 — `find_similar_entity` type filter unindexed + per-name session churn (MED)
`backend/app/repositories/graph.py:18-49`, driven by `pipeline.py:652-683`. Phase 4
calls it once per (name,type), each opening its own session; the `entity_type`
post-filter has no standalone btree index (only the composite unique `(name,
entity_type)`, unusable for a type-only predicate).
**Fix:** add `entities(entity_type)` btree; reuse one session for the Phase 4 fan-out.

### P7 — Per-batch classifier-resolution DB round-trip even when unused (MED)
`backend/app/services/pipeline.py:546-568`. Every `process_batch` opens a session and
runs `get_llm_config()` + an `MLProfile` SELECT to decide whether to swap the
classifier, regardless of whether `ml_profile_ref` is ever set.
**Fix:** fold the resolution into the existing 5s feature-flags TTL cache.

### P8 — Tree-sitter re-parses every file 2-3× (MED)
`backend/app/services/code_pipeline.py:735-765, 871-905`. Phase 6 and Phase 7 each
re-`Parser(...).parse(...)` all files to build type envs, even though Phase 2 already
produced a full AST that is then discarded.
**Fix:** cache the Phase 2 `Tree` / built `TypeEnvironment` and reuse it.

### P9–P11 (LOW)
- **P9** `relational.py:153-154` — paginated count wraps the full filtered/joined
  query in a subquery; re-runs the whole filter to count. Fine now, scales poorly.
- **P10** `vector.py:79-87, 266-284, 467-489` — per-fingerprint loops issue one
  statement per registered embedder; bounded today (1-2 fingerprints), N if many accrue.
- **P11** `entity_registry.py:39-74, 381-407` — context-disambiguation regexes and
  `learn_from_text` per-candidate `\b…\b` patterns recompiled per call; pre-compile at import.

---

## Verified clean (checked, not findings)

- **Strong-ref background tasks** (`utils/background.spawn`) — adds to a set, done
  callback `discard`s **and** retrieves the exception. Correct. The two ad-hoc
  `create_task` callers (`repo_manager.py:169`, `repos.py:210`) register into
  `TaskRegistry` (strong ref) — but see L5 re: exception retrieval there.
- **Websocket registry** (`api/websocket.py`) — removes on disconnect in `finally`,
  prunes dead sockets in `broadcast`, holds `_send_lock` across a 5s-bounded send.
  No add-without-remove, no deadlock. (Slow consumers add bounded latency to
  broadcasts, which couples into job-lock hold time — minor, noted.)
- **DB sessions / pool** — every `async_session_factory()` is `async with`;
  `get_session` commits/rolls-back/closes; `expire_on_commit=False` is safe for
  short-lived sessions; no long-lived identity-map growth.
- **MCP server** — `stateless_http=True`; no per-session registry to leak.
- **ML inference & model load** — `asyncio.to_thread`, off the event loop (timeout
  is L3, not a blocking-loop issue). **git** — `run_in_executor` with subprocess
  timeouts. **Leiden** — executor + 60s `wait_for`.
- **gather discipline** — `embed_batch_chunked` omits `return_exceptions` on purpose
  (a chunk failure should fail the batch); Phase 5 write and enrichment use
  `return_exceptions=True` correctly.
- **Cron math** — `next_fire_delta_seconds` uses `max(floor, delta)`; no negative
  sleep; `min_interval_seconds` floor honored.
- **Lifespan teardown** — `TaskRegistry.cancel_all()` and
  `ml_model_manager.shutdown_all()` called; loop cancellation re-raises
  `CancelledError` properly.
- **Feature flags** — fetched per-batch through a 5s single-flight TTL cache, not
  per-row.

---

## Suggested fix order

1. L2 (split httpx timeout) — smallest change, removes the multiplier under every stall.
2. L1 (`wait_for` around the runner) — caps the worst case.
3. L4 (load/save_config inside try) — stops permanent loop death.
4. M1 (bound entity cache) — stops the one real heap leak.
5. L5 (retrieve task exceptions) — makes reindex/clone failures visible.
6. P1 + P2 (bulk graph writes) — the dominant throughput wins, fix pattern already in-repo.
7. P3/P4 (httpx limits + pool sizing), then the remaining MEDs.

---

## Remediation status (2026-06-07)

Implemented and verified (backend suite **571 passed, 2 skipped**, incl. 3 new
job tests). Each fix was then put through a parallel adversarial-review workflow
(5 reviewers + per-finding skeptical verification); the two issues it confirmed
as real were corrected before this was written.

| ID | Status | Notes |
|----|--------|-------|
| L1 | done | `wait_for(job.runner(), max_run_seconds)` in `_run_once`; per-job ceilings in `main.py` (repo_sync 1800s, enrichment 600s, cleanups 300s). |
| L2/P3 | done | Split `httpx.Timeout` (connect 10 / read 300 / write 30 / pool 10) + `httpx.Limits(64/16)`. Read kept at 300s deliberately to avoid cutting legit long generations. |
| L3 | done (residual noted) | `wait_for` around tree-sitter parse (60s) and ML load/classify (300s/30s). **Residual:** the orphaned thread keeps a slot in the *shared* default executor; a systematic stall could cumulatively starve app-wide blocking work. A dedicated bounded executor would contain the blast radius — deferred as hardening (net improvement over the prior unbounded hang). |
| L4 | done | `load_config`/`save_config` moved inside `_run_once` try/except; loop can no longer die on a transient DB error. |
| L5 | done | `TaskRegistry._on_done` retrieves + logs `task.exception()`. |
| L6 | done | Analytics consumer: 30s liveness poll + `finally` cancels stragglers. |
| L7 | done | `trigger()` raises `JobBusyError` (→ 409) instead of blocking. Tests added. |
| M1 | done | Entity cache is a bounded LRU (`OrderedDict`, 10k). |
| M2 | done | Login rate-limiter sweeps stale IPs past a 10k cap. |
| M3 | **reverted** | The load-lock eviction introduced a HIGH double-load race (review-caught): popping `_load_locks` destabilizes the per-repo lock `get()` caches outside `self._lock`. Reverted to popping only `_models`; the negligible idle-lock retention is the intended trade. |
| P4 | done | Pool 30+20, `pool_pre_ping=True`. |
| P5 | done | Migration 0005: partial index on `code_symbols (enrichment_attempts, enrichment_priority DESC) WHERE pending`. |
| P6 | **dropped** | The `entities(entity_type)` index doesn't serve `find_similar_entity` — that query is HNSW-driven and filters `entity_type` post-join on a PK-fetched row, so a standalone btree is not an access path (review-caught). Removed rather than ship a write-cost index with no read path. |
| P7 | done + hardened | Classifier resolution cached (30s TTL); review caught that an `ml_profile_ref` flip wasn't invalidated, so `_swap_pipeline_llm` now resets the cache on every LLM-config swap. |
| P1, P2 | **deferred** | The N+1 graph-write rewrites (`code_pipeline._store_graph`, Phase-5 `graph.py`) are hot-path changes that warrant their own separately-tested change, not a ride-along with stability fixes. |
| P8–P11 | not done | Lower-value perf items; left for a focused perf pass. |
