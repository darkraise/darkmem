# E1 — Phase 1: Engine core at target shape

**Goal:** Rebuild the engine at target shape — capture + `memory_buffer`, the five-phase
pipeline, L1 graph & taxonomy, retrieval with SQL pushdown + labels + trace, code truth
T1–T4, the flattened LLM orchestrator, `events`, and the contract + core UI.

**Advance gate:** **G-B** — extraction F1 parity with the recorded baseline within the
tolerance stated in T0.05; retrieval eval vs the full-context baseline reported with its
latency/cost twin; isolation probes count **zero** unlabelled cross-project or superseded
rows on every channel (doc 20 §4).

**Epic branch:** `feat/e1-engine-core`

**Contract:** [`../agent-runbook.md`](../agent-runbook.md). Amendments log at the bottom.

**This epic rebuilds a working engine.** The risk is silent behaviour drift, not
breakage — which is why G-B is F1 parity plus a zero-count isolation probe rather than a
review. Treat `CLAUDE.md`'s invariant list as the behaviour contract throughout.

---

## Lane A — foundations (LLM orchestrator + `events`)

Start here: most other lanes journal to `events` or call the orchestrator.

#### T1.01 — Flatten `llm_purpose_configs` to inline rows

`Model: Opus 5` · `Depends: T0.12` · `Doc: 11 §2` · `Tag: rebuild` · `Gate: G-B`

**What.** Replace the `provider_ref` / `profile_ref` / `ml_profile_ref` indirection with
six-to-eight inline purpose rows. The indirection bought rotation-in-one-place and cost
three levels of resolution on every call; the target keeps the config flat.

**Done when:**
- [ ] Six live purposes carry their connection details inline
- [ ] The three `*_ref` columns and their tables are gone from the read path
- [ ] Existing homelab config migrates without a manual re-entry step
- [ ] Purpose resolution is one query, asserted by a test that counts queries

**Verify.** `cd backend && python -m pytest tests/test_llm_config.py -q`

#### T1.02 — One shared `httpx.AsyncClient` with atomic live reload

`Model: Sonnet 5` · `Depends: T1.01` · `Doc: 11 §3` · `Tag: rebuild` · `Gate: G-B`

**What.** Construct the client once at boot; an admin save swaps configuration
atomically under the single-worker assumption (invariant 13).

**Done when:**
- [ ] One client instance for the process lifetime; no per-call construction
- [ ] A save mid-flight never leaves a half-applied config visible to a caller
- [ ] Reload failure surfaces the error and keeps the prior working config

**Verify.** `cd backend && python -m pytest tests/test_llm_orchestrator_reload.py -q`

#### T1.03 — `api_kind` as the sole vendor-quirk home

`Model: Opus 5` · `Depends: T1.02` · `Doc: 11 §4` · `Tag: rebuild` · `Gate: G-B`

**What.** Every vendor quirk — auth scheme, reasoning-disable knob, structured-output
caveat — lives behind `api_kind` and nowhere else. The known ones are recorded and must
survive the rebuild: Anthropic needs `x-api-key` + `anthropic-version`, not Bearer;
DeepSeek needs `thinking:{type:disabled}`; Gemini's OpenAI shim honours only
`reasoning_effort=none`; OpenAI dropped `minimal` from the effort set.

**Done when:**
- [ ] `openai` / `ollama` / `anthropic` / `google` / `deepseek` / `zai` each dispatch
      correctly, with quirks isolated to the dispatch layer
- [ ] No vendor conditional survives at any call site
- [ ] `supports_embedding` still gates the embedding-purpose picker
- [ ] Each recorded quirk above has a regression test

**Verify.** `cd backend && python -m pytest tests/test_api_kind_dispatch.py -q`

#### T1.04 — `classifier_kind` inline on the classification purpose

`Model: Sonnet 5` · `Depends: T1.01` · `Doc: 11 §2` · `Tag: rebuild` · `Gate: G-B`

**What.** `classifier_kind` (`llm` | `local`) rides inline on the classification purpose
and is the only switch selecting the classifier. Do not reintroduce a generic ML on/off
flag — that was deliberately removed in the 2026-05-01 consolidation.

**Done when:**
- [ ] `llm` and `local` both dispatch; the value lives on the purpose row
- [ ] No new feature flag is added for this

**Verify.** `cd backend && python -m pytest tests/test_classifier_kind.py -q`

#### T1.05 — Seed `synthesis` and `verification` purposes inert

`Model: Haiku 4.5` · `Depends: T1.01` · `Doc: 11 §6` · `Tag: target-new, inert` · `Gate: G-B`

**What.** Both purposes seed now behind their unshipped layers (E2/E3), landed inert
with no caller.

**Done when:**
- [ ] Rows exist with sane defaults; nothing calls them
- [ ] Labelled inert in the schema inventory naming their first-writer tasks (T2.26 for
      `verification`, T3.02 for `synthesis`)

**Verify.** `cd backend && python -m pytest tests/test_inert_objects.py -q`

#### T1.06 — `events` table, monthly partitioning, append-only trigger

`Model: Opus 5` · `Depends: T0.12` · `Doc: 04 §8.1` · `Tag: target-new` · `Gate: G-B`

**What.** The journal that makes measurement a query instead of an instrument.
`RANGE(created_at)` monthly partitions plus a forbid-trigger blocking UPDATE, DELETE and
TRUNCATE. Convention 8 depends on this being genuinely append-only.

**Done when:**
- [ ] Monthly partitions created ahead of need, reconciled at boot
- [ ] UPDATE / DELETE / TRUNCATE on `events` raise, proven by test
- [ ] `api_key_id` and `actor` columns land **inert** (their writer is T4.02)

**Verify.** `cd backend && python -m pytest tests/test_events_append_only.py -q`

#### T1.07 — `events` writer and the journaling convention

`Model: Sonnet 5` · `Depends: T1.06` · `Doc: 05 §2.3` · `Tag: target-new` · `Gate: G-B`

**What.** One helper every subsystem journals through, so payload shape stays uniform
across capture, extraction, supersession, and pipeline outcomes.

**Done when:**
- [ ] Capture, extraction, supersession, and each pipeline outcome write an event
- [ ] Payload carries before/after state where the action mutates
- [ ] Journaling never blocks the hot path on failure — a journal error degrades loudly
      but does not fail the capture

**Verify.** `cd backend && python -m pytest tests/test_events_writer.py -q`

#### T1.08 — `GET /events`, `/events/calendar`, `/events/timeline`

`Model: Sonnet 5` · `Depends: T1.07` · `Doc: 12 §7` · `Tag: target-new` · `Gate: G-B`

**What.** The read surface the Dashboard calendar and per-object timeline consume.

**Done when:**
- [ ] Three endpoints matching `api-rest-conventions.md`
- [ ] Calendar returns date-bucketed counts, not rows
- [ ] Timeline is per-object and paginated
- [ ] Project scoping is pushed into SQL, not filtered after (see T1.29)

**Verify.** `cd backend && python -m pytest tests/test_api/test_events.py -q`

#### T1.09 — Retire `audit_log` reads

`Model: Sonnet 5` · `Depends: T1.08` · `Doc: 04 §8.1` · `Tag: rebuild` · `Gate: G-B`

**What.** `events` replaces the coarse `audit_log`/`AuditLog` read paths. Retire the
readers; keep the auth-audit writes that doc 18 still owns.

**Done when:**
- [ ] No product read path queries `audit_log`
- [ ] Auth audit trail still functions (doc 18 posture unchanged)

**Verify.** `rg -n "audit_log|AuditLog" backend/app` reviewed — only doc-18 writes remain.

---

## Lane B — capture and the buffer (F1)

#### T1.10 — `memory_buffer` table + pre-minted UUIDv7 ids

`Model: Sonnet 5` · `Depends: T0.12` · `Doc: 05 §2` · `Tag: target-new` · `Gate: G-B`

**What.** The durable landing zone for accepted-but-unprocessed captures. The id is
minted at accept so the caller gets a real handle back from a 202.

**Done when:**
- [ ] Buffer row persists content, resolved `source`/`origin_key`/`project`, and status
- [ ] UUIDv7 minted at accept and carried through to the `memories` row unchanged
- [ ] Buffer survives a process restart (this is the durability the tier depends on)

**Verify.** `cd backend && python -m pytest tests/test_memory_buffer.py -q`

#### T1.11 — `origin_key` resolution — born at capture

`Model: Opus 5` · `Depends: T1.10` · `Doc: 05 §2.1` · `Tag: target-new` · `Gate: G-B`

**What.** `origin_key` is the capture-session/agent-run identity, and every later
corroboration count in E2 is `COUNT(DISTINCT origin_key)` over it. **When identity is
genuinely unknown it merges to ONE origin per `(source, project)`** — undercount, never
manufacture agreement. Getting this wrong in Phase 1 silently inflates every verification
number in Phase 2.

**Done when:**
- [ ] Resolution order documented and tested: explicit arg > client header > user-agent
      map > the merge-to-one fallback
- [ ] Unknown identity provably collapses to one origin per `(source, project)`
- [ ] A test asserts two unknown-identity captures from one source do **not** count as
      two origins
- [ ] `memory_batch_add` resolves on the raw entry dicts before validation, so an absent
      value is distinguishable from an explicit default

**Verify.** `cd backend && python -m pytest tests/test_origin_key.py -q`

#### T1.12 — Tier-A synchronous accept + 202 ack

`Model: Sonnet 5` · `Depends: T1.11` · `Doc: 05 §2` · `Tag: target-new` · `Gate: G-B`

**What.** Accept validates against `MemoryCreate`, writes the buffer row, journals, and
returns a 202-style ack with the pre-minted id. No LLM call, no graph write, no waiting.

**Done when:**
- [ ] Accept latency is dominated by one insert — no model call on this path
- [ ] Validation failures return 4xx before anything is written
- [ ] Both front doors (REST + MCP) accept identically (invariant 17)

**Verify.** `cd backend && python -m pytest tests/test_api/test_capture.py -q`

#### T1.13 — `buffer_flush` job with `FOR UPDATE SKIP LOCKED`

`Model: Opus 5` · `Depends: T1.12` · `Doc: 05 §3` · `Tag: target-new` · `Gate: G-B`

**What.** A JobRegistry job claims buffered rows with `FOR UPDATE SKIP LOCKED` and feeds
them to `process_batch`. Claiming is the correctness-critical part: a row must never be
processed twice or stranded.

**Done when:**
- [ ] Concurrent claimers never double-process a row
- [ ] A crashed claim is reclaimable (no permanent lease leak)
- [ ] Batch size respects the 1–100 cap both doors already enforce
- [ ] Registered under `JobRegistry` with a cron, a `min_interval_seconds` floor, and a
      per-job lock like every other job

**Verify.** `cd backend && python -m pytest tests/test_buffer_flush.py -q`

#### T1.14 — `wait_process` interactive bypass

`Model: Sonnet 5` · `Depends: T1.13` · `Doc: 05 §3` · `Tag: target-new` · `Gate: G-B`

**What.** An interactive caller that needs the result now bypasses the buffer and runs
the pipeline inline.

**Done when:**
- [ ] `wait_process` returns the processed memory, not an ack
- [ ] The bypass runs the identical pipeline — never a second code path
- [ ] Default remains buffered; the bypass is opt-in per call

**Verify.** `cd backend && python -m pytest tests/test_wait_process.py -q`

#### T1.15 — Repo-hint auto-provision handoff + SSRF allowlist gate

`Model: Opus 5` · `Depends: T1.12` · `Doc: 05 §2.4, 18` · `Tag: target-new` · `Gate: G-B`

**What.** A capture mentioning a repo queues F11 provisioning in Tier C. **Capture never
clones.** The hint is validated against doc 18's SSRF allowlist before anything is queued.

**Done when:**
- [ ] Hint validated against the allowlist at capture time; rejection is logged and the
      capture still succeeds
- [ ] Provisioning happens in Tier C, off the capture path — asserted by timing test
- [ ] A hostile hint (internal IP, redirect chain, credential-bearing URL) is refused
- [ ] `git config --global --add safe.directory` still applied on local registration

**Verify.** `cd backend && python -m pytest tests/test_repo_hint_ssrf.py -q`

---

## Lane C — the five-phase pipeline and L1 graph (F2)

#### T1.16 — Phase 1: content embed + register-before-insert

`Model: Sonnet 5` · `Depends: T1.03` · `Doc: 05 §5` · `Tag: rebuild` · `Gate: G-B`

**What.** One chunked embed call for the batch, returning vectors + fingerprint. The
fingerprint is registered exactly once before any partition write.

**Done when:**
- [ ] Embed failure marks every memory `embed=error` and skips all writes
- [ ] Fingerprint registered before the first partition insert, always
- [ ] No cross-fingerprint comparison anywhere (invariant 2)

**Verify.** `cd backend && python -m pytest tests/test_pipeline_phase1.py -q`

#### T1.17 — Phase 2: merged extract + classify in one call

`Model: Opus 5` · `Depends: T1.16, T1.04` · `Doc: 05 §5–§6` · `Tag: rebuild` · `Gate: G-B`

**What.** One LLM touch per memory by default: the merged schema adds
`summary`/`emotions`/`flags` to extraction, and extraction's `memory_type` doubles as the
classification label. The gate changes the prompt, so re-extracting the same content
under a different gate state is **not** bit-identical — record that caveat in the test.

**Done when:**
- [ ] Merged path fires when classifier is LLM-backed and mode is `simple`
- [ ] Any other config keeps the two-concurrent-call path
- [ ] Seed `sha256(content)[:8]` forwarded, so identical input reproduces (doc 17 §7)
- [ ] F1 bench shows no regression against the T0.05 baseline

**Verify.** `cd backend && python scripts/extraction_bench/run_bench.py` — compare to T0.05.

#### T1.18 — `classifier_kind=local` narrowing path

`Model: Sonnet 5` · `Depends: T1.17` · `Doc: 05 §6` · `Tag: rebuild` · `Gate: G-B`

**What.** With a local classifier the extraction call narrows to extraction-only and
classification runs in-process.

**Done when:**
- [ ] Local path produces the same `{hall, summary, emotions, flags}` surface
- [ ] Extraction prompt narrows accordingly (no dead classification fields requested)

**Verify.** `cd backend && python -m pytest tests/test_classifier_local.py -q`

#### T1.19 — Phase 3: entity embed with the two-level cache

`Model: Sonnet 5` · `Depends: T1.16` · `Doc: 05 §5` · `Tag: rebuild` · `Gate: G-B`

**What.** Memory cache → DB cache → embed the misses, writing new vectors back to both,
keyed `(name_lower, fingerprint)`.

**Done when:**
- [ ] Cache hit rate is observable on a run (this is the phase's whole value)
- [ ] Cache writes are batched, not per-entity
- [ ] A fingerprint rotation between Phase 1 and 3 registers and switches correctly

**Verify.** `cd backend && python -m pytest tests/test_pipeline_phase3.py -q`

#### T1.20 — Phase 4: type-constrained dedup + `names_distinct`

`Model: Opus 5` · `Depends: T1.19` · `Doc: 06 §5` · `Tag: rebuild` · `Gate: G-B`

**What.** One ANN probe per unique `(name, entity_type)` at threshold 0.85. The
`names_distinct` discriminator is what keeps "february outage" and "march outage" apart
at 0.885 cosine while still merging postgres/postgresql at 0.974 — it must survive the
rebuild intact.

**Done when:**
- [ ] Probes are type-constrained; same-named entities of different types dedup separately
- [ ] Discriminating tokens (numbers, dates, versions, month names) block a merge
- [ ] `canonical_map` keyed `(name_lower, entity_type)`; Phase 5 resolves endpoints by
      the same key
- [ ] Probes fan out bounded by `pipeline_concurrency`

**Verify.** `cd backend && python -m pytest tests/test_dedup_discriminator.py -q`

#### T1.21 — Phase 5: the two-savepoint write

`Model: Opus 5` · `Depends: T1.20` · `Doc: 05 §5` · `Tag: rebuild` · `Gate: G-B`

**What.** Savepoint A: vector upsert + memory-row enrichment. Savepoint B:
entity/relationship graph + technologies + supersession. Split so a graph failure never
rolls back the vector write.

**Done when:**
- [ ] A forced graph failure leaves the vector write committed
- [ ] Crossrefs computed in a separate session after the main commit
- [ ] `derive_memory_failed_step` records or resolves a `pipeline_failures` row per memory
- [ ] The websocket broadcasts `pipeline.completed | partial | failed` per per-step status

**Verify.** `cd backend && python -m pytest tests/test_pipeline_savepoints.py -q`

#### T1.22 — Mid-batch embedder rotation

`Model: Opus 5` · `Depends: T1.19` · `Doc: 05 §5` · `Tag: rebuild` · `Gate: G-B`

**What.** If the active embedder rotates between Phase 1 and Phase 3, Phase 3 registers
and switches to the new fingerprint rather than writing into the old partition.

**Done when:**
- [ ] Rotation mid-batch is handled without a cross-fingerprint write
- [ ] Test forces a rotation and asserts partition correctness

**Verify.** `cd backend && python -m pytest tests/test_embedder_rotation.py -q`

#### T1.23 — Five closed vocabularies + normalisers + `LEGACY_*` maps

`Model: Sonnet 5` · `Depends: T1.17` · `Doc: 06 §3` · `Tag: rebuild` · `Gate: G-B`

**What.** Entity, relationship, tech, memory types, plus the target memory-relation set.
Pure normalisers; unknown entity types fall back to `concept`, unknown relations to
`RELATED_TO`; `LEGACY_*` maps rewrite historical names at runtime.

**Done when:**
- [ ] Only tabled values are ever stored (invariant 5)
- [ ] `LEGACY_*` rewrites keep old rows matching new code (e.g. `framework`→`tool`,
      `RUNS_ON`→`DEPLOYED_ON`, `debug`→`problem`)
- [ ] Normalisers are pure functions with no DB access

**Verify.** `cd backend && python -m pytest tests/test_taxonomy.py -q`

#### T1.24 — The deterministic post-processor (~40 passes)

`Model: Opus 5` · `Depends: T1.23` · `Doc: 06 §4` · `Tag: rebuild` · `Gate: G-B`

**What.** The extraction moat: ~40 deterministic cleanup passes that stay **out of the
prompt**. Prior campaigns moved relations F1 0.64→0.96 and entity name+type 0.68→0.93
through these passes, plus the curated `_TYPE_OVERRIDES` map. Prompt changes do not move
this model on nuanced typing — fix in the passes and the curated maps.

**Done when:**
- [ ] Every pass is individually testable and individually reversible
- [ ] Pass order is explicit and documented — reordering is a measured change
- [ ] F1 bench matches or beats the T0.05 baseline on all four dimensions
- [ ] No pass is a prompt instruction in disguise

**Verify.** `cd backend && python scripts/extraction_bench/run_bench.py --algo-only`

#### T1.25 — `relation_rescue` layer

`Model: Sonnet 5` · `Depends: T1.24` · `Doc: 06 §4` · `Tag: exists-today` · `Gate: G-B`

**What.** The only surviving ingestion-side behavioural flag. Pattern-based rescue for
relations the LLM misses, including the generic REPLACES extractor (from X to Y, replaced
X with Y, swapped X for Y, Y supersedes X) and the substring over-extraction guard.

**Done when:**
- [ ] Rescue-tagged wins the `_dedup_by_target_predicate` tie-break, then weight
- [ ] Rescue hits inside a longer existing entity span are skipped
- [ ] `REPLACES` / `IMPROVES_ON` / legacy `BUILDS_ON` collapse via `family_key`
- [ ] Guarded by the F1 bench — reorder or remove only against a measured delta

**Verify.** `cd backend && python -m pytest tests/test_relation_rescue.py -q`

#### T1.26 — Strip-before-rewrite: idempotent re-extraction

`Model: Opus 5` · `Depends: T1.21` · `Doc: 06 §6` · `Tag: rebuild` · `Gate: G-B`

**What.** Delete this `memory_id`'s prior graph contributions before writing the new set.
`delete_by_memory_id` deletes a relation only when no live memory still asserts it, and
an entity only when no live memory asserts it and no surviving relation references it —
the FK cascades, so deleting a referenced entity destroys another memory's edge.

**Done when:**
- [ ] Re-extracting the same memory twice yields an identical graph
- [ ] Entities shared with other live memories survive the strip
- [ ] Dangling `memory_ids` self-heal on the sweep
- [ ] Deleting a referenced entity is impossible, proven by test

**Verify.** `cd backend && python -m pytest tests/test_idempotent_reextraction.py -q`

#### T1.27 — `technologies` denorm recompute

`Model: Sonnet 5` · `Depends: T1.26` · `Doc: 06 §6` · `Tag: rebuild` · `Gate: G-B`

**What.** Recompute `memories.technologies` from entities whose type is in `TECH_TYPES`,
lowercase, GIN-indexed. Supersession and the retrieval filter both read this column
instead of joining — keep all three properties (lowercase, denormalised, indexed).

**Done when:**
- [ ] Recomputed on every graph write, never partially updated
- [ ] Always lowercase; GIN index present and used by the supersession query plan
- [ ] Curated `_TYPE_OVERRIDES` applied (this map, not the prompt, is what fixes typing)

**Verify.** `cd backend && python -m pytest tests/test_technologies_denorm.py -q`

#### T1.28 — `graph_orphan_cleanup` backstop

`Model: Sonnet 5` · `Depends: T1.26` · `Doc: 06 §6` · `Tag: exists-today` · `Gate: G-B`

**What.** The hourly unscoped sweep (`prune_orphan_entities`) so Phase-4 dedup never
merges fresh entities onto stale ghosts.

**Done when:**
- [ ] Runs hourly under JobRegistry with its own lock and floor
- [ ] Removes only entities with no live memory and no surviving relation
- [ ] A dedup run after the sweep cannot match a pruned ghost

**Verify.** `cd backend && python -m pytest tests/test_graph_orphan_cleanup.py -q`

---

## Lane D — retrieval (F3)

#### T1.29 — SQL pushdown of project / status / archived on every channel

`Model: Opus 5` · `Depends: T1.16` · `Doc: 07 §7` · `Tag: rebuild` · `Gate: G-B`

**What.** **The named G-B blocking prerequisite.** Push the scope predicates into SQL on
*every* channel — semantic, keyword, graph, code — closing the `memory_reason`
cross-project and superseded leak. No phase after 1 may describe isolation as holding
without this (invariant 14).

**Done when:**
- [ ] Every channel filters in SQL; no post-filtering in Python anywhere
- [ ] `memory_reason` specifically is proven leak-free
- [ ] Query plans confirm the predicates are used, not evaluated after a full scan
- [ ] String/`UUID` id normalisation happens at the boundary so matches cannot silently drop

**Verify.** `cd backend && python -m pytest tests/test_retrieval_pushdown.py -q`

#### T1.30 — RRF fusion + the unified `rank_fusion_factor`

`Model: Opus 5` · `Depends: T1.29` · `Doc: 07 §3` · `Tag: rebuild` · `Gate: G-B`

**What.** Reciprocal Rank Fusion at k=60 over semantic + keyword, weighted by
`semantic_weight` (default 0.7), collapsed into one `rank_fusion_factor` formula.
Consumers order by `rrf_score`; the per-modality `score` key survives on the row and is
the first-seen side's raw score — never the ordering signal.

**Done when:**
- [ ] `rrf_score` is the only ordering signal, asserted by test
- [ ] `w_conf` (confidence) is spent today, as it is now
- [ ] Formula slots for importance / heat / recency exist and are **wired at zero**
- [ ] Confidence weighting after a rerank runs with `preserve_order=True`

**Verify.** `cd backend && python -m pytest tests/test_rrf_fusion.py -q`

#### T1.31 — Ranking arms wired at zero

`Model: Sonnet 5` · `Depends: T1.30` · `Doc: 07 §3` · `Tag: target-new, inert` · `Gate: G-B`

**What.** `w_importance`, `w_heat`, `w_recency` land as formula slots at weight 0. Landing
them wired-at-zero is the Phase-1 deliverable; activation is Phase 2 behind a measured
retrieval-eval win with its twin.

**Done when:**
- [ ] Each arm reads from `config` with default 0
- [ ] A test asserts ranking is bit-identical with the arms at zero vs absent
- [ ] Each is labelled inert with its activation task id (T2.30 for `w_importance`,
      T2.31 for `w_heat`/`w_recency`)

**Verify.** `cd backend && python -m pytest tests/test_ranking_arms_zero.py -q`

#### T1.32 — Reranker wired dormant

`Model: Sonnet 5` · `Depends: T1.30` · `Doc: 07 §3` · `Tag: exists-today` · `Gate: G-B`

**What.** `reranker_enabled` ships wired and off. When on, LLM-scores the top 40
RRF-ranked rows 0–10 and appends the unscored tail in original order.

**Done when:**
- [ ] Flag defaults off; on-path tested
- [ ] The unscored tail past rank 40 keeps its RRF order, never re-ranked
- [ ] Turning it on requires a measured win including p95 cost (recorded in the ledger)

**Verify.** `cd backend && python -m pytest tests/test_reranker.py -q`

#### T1.33 — The retrieval trace

`Model: Sonnet 5` · `Depends: T1.30` · `Doc: 07 §8` · `Tag: target-new` · `Gate: G-B`

**What.** Envelope + per-row trace attached on request. Transient — **no table in v1**.
This is the signal the why-retrieved UI (T1.44) renders, and it is where the RRF and
rerank scores stop being dropped at the API boundary.

**Done when:**
- [ ] Trace carries per-channel contribution, fused `rrf_score`, and rerank score
- [ ] Attached only when requested; zero cost when not
- [ ] Scores survive to the API response — the known drop-at-the-boundary defect is
      closed and has a regression test
- [ ] Exclusion counts are in the envelope (a silent drop is the failure mode)

**Verify.** `cd backend && python -m pytest tests/test_retrieval_trace.py -q`

#### T1.34 — `applies_when` context-boost slot

`Model: Opus 5` · `Depends: T1.30` · `Doc: 07, 09 §5` · `Tag: target-new` · `Gate: G-B`

**What.** Wire the slot this phase; magnitude is a `config` row tuned in Phase 2. The
**boost-plus-label rule and the conflict-count rule are hard rules, never tuned** — a
boosted row is always labelled, and conflicts are always counted.

**Done when:**
- [ ] Magnitude reads from `config`; default stated
- [ ] Every boosted row carries its label — no unlabelled boost is representable
- [ ] Conflict counting is not behind a flag
- [ ] Tests pin the hard rules independently of the magnitude

**Verify.** `cd backend && python -m pytest tests/test_applies_when_boost.py -q`

#### T1.35 — The isolation probe (G-B's zero-count)

`Model: Fable 5` · `Depends: T1.29, T0.10` · `Doc: 20 §4` · `Tag: target-new` · `Gate: G-B`

**What.** The probe that clears G-B: count unlabelled cross-project and superseded rows
returned on **every** channel. The bar is zero. Design it adversarially — construct the
cases most likely to leak, not the ones most likely to pass.

**Done when:**
- [ ] Probe covers every channel including `memory_reason`, code search, and graph
- [ ] Deliberately hostile fixtures: same-name entities across projects, superseded rows
      with live successors, archived rows, cross-fingerprint attempts
- [ ] A single leaked row fails the probe loudly
- [ ] Result recorded in `gate-ledger.md` under G-B

**Verify.** `cd backend && python scripts/benchlib/run_isolation_probe.py` — expect `0`.

---

## Lane E — lifecycle (F4, F5)

#### T1.36 — Supersession detector, rules 1–6 verbatim

`Model: Opus 5` · `Depends: T1.21, T1.27` · `Doc: 08 §2.1` · `Tag: exists-today` · `Gate: G-B`

**What.** Fires synchronously in Phase 5 savepoint B on a REPLACES-family relation. All
six rules carry verbatim: same project; candidate active; lowercased `technologies`
overlap on the GIN; 90-day window; strictly-older with the `(created_at, id)` tie-break;
and the per-target speculative-marker gate. The tie-break is what prevents the mutual
supersession that once made two memories vanish from the default view.

**Done when:**
- [ ] All six rules tested independently
- [ ] Same-batch rows share one `created_at`; the id tie-break lets within-batch
      supersession fire while blocking the mutual flip
- [ ] The speculative gate is scoped per target — an unrelated speculative aside
      elsewhere in the memory does not suppress a definitive replacement
- [ ] `status` + `superseded_by` flip atomically under `chk_superseded_has_pointer`
- [ ] REPLACES targets lowercased to match `technologies` — both sides change together

**Verify.** `cd backend && python -m pytest tests/test_supersession.py -q`

#### T1.37 — TTL sweep, demote before delete

`Model: Opus 5` · `Depends: T1.36` · `Doc: 08 §2.3` · `Tag: exists-today` · `Gate: G-B`

**What.** `expired_memory_cleanup` deletes rows past `expires_at`, **first** demoting
every dependent pointing at an expiring row via `superseded_by` to `deprecated` with
`superseded_by=NULL`. The FK is `ON DELETE SET NULL`, so skipping the demotion violates
`chk_superseded_has_pointer` and aborts the whole batch.

**Done when:**
- [ ] Demotion precedes deletion, proven by a test that fails if reordered
- [ ] The interactive delete path runs the identical demotion
- [ ] `expires_at` stays caller-set this phase (the self-expiring-fact half is T2.34)

**Verify.** `cd backend && python -m pytest tests/test_expiry_sweep.py -q`

---

## Lane F — code truth hardening T1–T4 (F11)

#### T1.38 — T1 fail-stale

`Model: Sonnet 5` · `Depends: T1.07` · `Doc: 10 §3` · `Tag: target-new` · `Gate: G-B`

**What.** A pipeline exception keeps the last-good graph, labelled `stale` — never wipes.
A diff failure falls back to a full index, not a bare wipe.

**Done when:**
- [ ] Forced mid-index failure leaves the prior graph queryable and marked stale
- [ ] The stale label names the last-good sha and the cause
- [ ] No path deletes a graph without a successful replacement

**Verify.** `cd backend && python -m pytest tests/test_code_fail_stale.py -q`

#### T1.39 — T2 index-debt drain

`Model: Opus 5` · `Depends: T1.38` · `Doc: 10 §3` · `Tag: target-new` · `Gate: G-B`

**What.** Dependent-caller re-trace overflow past the retrace cap persists to
`repositories.index_debt` and drains in continuation batches. **Never dropped** — silent
truncation here is a graph that is quietly wrong.

**Done when:**
- [ ] Overflow persists rather than truncating
- [ ] Continuation batches drain it to zero across runs
- [ ] Debt count is observable (it is the UI signal in T1.46)

**Verify.** `cd backend && python -m pytest tests/test_index_debt.py -q`

#### T1.40 — T3 `code_reconcile` job

`Model: Sonnet 5` · `Depends: T1.39` · `Doc: 10 §3` · `Tag: target-new` · `Gate: G-B`

**What.** Periodically hash each tracked repo's working tree and feed mismatches through
the incremental path.

**Done when:**
- [ ] Registered under JobRegistry with cron, floor, and lock
- [ ] A drifted working tree is detected and reconciled incrementally
- [ ] An unchanged tree short-circuits with no work

**Verify.** `cd backend && python -m pytest tests/test_code_reconcile.py -q`

#### T1.41 — T4 summary carry-over

`Model: Sonnet 5` · `Depends: T1.40` · `Doc: 10 §3` · `Tag: target-new` · `Gate: G-B`

**What.** A symbol whose body is unchanged keeps its LLM summary and enriched status
across a file re-index — never re-billed.

**Done when:**
- [ ] Unchanged symbol bodies retain summaries across a re-index
- [ ] Changed bodies drop the stale summary rather than keeping a wrong one
- [ ] A re-index of an unchanged file makes zero enrichment LLM calls

**Verify.** `cd backend && python -m pytest tests/test_summary_carryover.py -q`

---

## Lane G — the contract and core UI (F9)

**Principle 10: the signal ships with its surface.** Nothing in this lane is optional
polish — a Phase-1 backend signal with no Phase-1 surface is the unshipped-signal debt
doc 20 forbids.

#### T1.42 — REST/MCP payload envelope and two-door parity

`Model: Opus 5` · `Depends: T1.33` · `Doc: 12 §2–§6` · `Tag: rebuild` · `Gate: G-B`

**What.** One service layer, two front doors (invariant 17). Envelope, source/context
resolution, and the auth-and-trust posture ship as the callable contract over the Phase-1
signals.

**Done when:**
- [ ] Every Phase-1 surface exists on both doors, or is single-door with a stated reason
- [ ] `api-rest-conventions.md` honoured: 201 create, 204 delete, 202 async, POST
      `.../search` for complex queries
- [ ] MCP source resolution order preserved (explicit > header > user-agent > `mcp`)
- [ ] MCP Host allowlist / DNS-rebinding protection unchanged; a LAN 421 is fixed by
      extending the allowlist, never by disabling the check

**Verify.** `cd backend && python -m pytest tests/test_api tests/test_mcp -q`

#### T1.43 — Dashboard + contribution calendar

`Model: Sonnet 5` · `Depends: T1.08` · `Doc: 13 §4` · `Tag: rebuild` · `Gate: G-B`

**What.** E1's core UI surface. The calendar reads the `events` date-bucket substrate —
its click-to-date contract lands on `/memories?date=YYYY-MM-DD`.

**Done when:**
- [ ] Calendar renders from `/events/calendar`, not a client-side aggregation
- [ ] Cell click navigates to the memories surface positioned on that day
- [ ] Empty state is honest (no data ≠ broken)

**Verify.** `cd frontend && npm test && npm run test:e2e -- dashboard`

#### T1.44 — Memories search + the why-retrieved trace

`Model: Sonnet 5` · `Depends: T1.33, T1.43` · `Doc: 13 §4, §5.4` · `Tag: rebuild` · `Gate: G-B`

**What.** The search surface with the per-row trace expanded on demand, plus the
exclusion strip that renders even when the result list is empty — a silent drop is the
failure this design fears most.

**Done when:**
- [ ] Trace shows per-channel contribution and the fused score
- [ ] Exclusion counts always render, including on zero results
- [ ] The list virtualizes (the skeleton's `useMainVirtualizer` pattern) and pages
- [ ] Honesty labels — layer, verification, superseded/stale — always render

**Verify.** `cd frontend && npm test && npm run test:e2e -- memories`

#### T1.45 — Pipeline stepper, failure triage, job board

`Model: Sonnet 5` · `Depends: T1.21, T1.13` · `Doc: 13 §6.1` · `Tag: rebuild` · `Gate: G-B`

**What.** The Activity shell v1 modules over the five-phase signal, `pipeline_failures`,
and JobRegistry.

**Done when:**
- [ ] Stepper reflects real per-phase status including `partial`
- [ ] Failure triage surfaces the failed step and offers retry
- [ ] Job board shows cron, last run, and a manual trigger that returns 409 when the
      job's lock is held (never queues)

**Verify.** `cd frontend && npm test` + manual walkthrough against a live pipeline run.

#### T1.46 — Code fail-stale banner + index-debt indicator

`Model: Sonnet 5` · `Depends: T1.39` · `Doc: 13 §4.2` · `Tag: target-new` · `Gate: G-B`

**What.** The two signals the code-truth hardening produces, surfaced. Both already exist
in the frontend skeleton's demo data — this task binds them to the real backend.

**Done when:**
- [ ] Stale banner names the last-good sha and the cause
- [ ] Debt indicator shows queued file count and that it is draining, not lost
- [ ] Both read live backend state, not demo fixtures

**Verify.** `cd frontend && npm run test:e2e -- code`

#### T1.47 — Memory-detail supersession lineage

`Model: Sonnet 5` · `Depends: T1.36` · `Doc: 13 §4` · `Tag: rebuild` · `Gate: G-B`

**What.** Amber badge plus successor link. Superseded rows show by default with the badge
— hiding them is what once made two memories silently vanish.

**Done when:**
- [ ] Badge renders on superseded rows; successor link navigates
- [ ] Superseded rows are visible by default, labelled, not filtered out
- [ ] Lineage renders both directions (what this replaced, what replaced it)

**Verify.** `cd frontend && npm test -- memory-detail`

#### T1.48 — Detail-level preference honoured across advanced surfaces

`Model: Sonnet 5` · `Depends: T1.44` · `Doc: 13 §5.4, §8` · `Tag: target-new` · `Gate: G-B`

**What.** Simple/Advanced ships with the first advanced surface. `simple` hides technical
detail — per-modality and fused scores, the arm breakdown, fingerprints, raw `config`
keys, doc refs — collapsing the breakdown to one plain "why it ranked" line. **`simple`
never hides an honesty signal** (invariant 14).

**Done when:**
- [ ] Verification badges, layer labels, superseded/stale labels, and exclusion counts
      render in **both** modes — asserted by test
- [ ] Preference persists in localStorage; it changes rendering only, never the request
- [ ] Every later advanced surface honours the same flag

**Verify.** `cd frontend && npm test -- detail-level`

#### T1.49 — WebSocket → query-invalidation mapping

`Model: Sonnet 5` · `Depends: T1.45` · `Doc: 13 §2–§3` · `Tag: rebuild` · `Gate: G-B`

**What.** Map each broadcast event to the queries it invalidates, so the UI refreshes on
real state rather than on a poll.

**Done when:**
- [ ] `pipeline.completed | partial | failed` invalidate the right query keys
- [ ] A dropped socket reconnects and reconciles rather than showing stale data forever
- [ ] No `refetchInterval` remains where an event now covers it

**Verify.** `cd frontend && npm test -- websocket`

---

## Lane H — gate

#### T1.50 — G-B evidence run and ledger entry

`Model: Fable 5` · `Depends: all E1 lanes` · `Doc: 20 §4` · `Tag: target-new` · `Gate: G-B`

**What.** Clear G-B, adversarially. Three numbers, all of which must hold.

**Done when:**
- [ ] Extraction F1 parity with the T0.05 baseline within its stated tolerance
- [ ] Retrieval eval vs the full-context baseline, reported **with** its latency/cost twin
- [ ] Isolation probe returns zero on every channel
- [ ] All three, their artifacts, and the verdict written to `gate-ledger.md`
- [ ] Any shortfall recorded and G-B left open — never widen a bar to fit a result

**Verify.** `./scripts/gate.sh --full` plus `python scripts/benchlib/run_isolation_probe.py`

---

## Amendment log

| Date | Task | Tier | Change | Why |
|---|---|---|---|---|
| — | — | — | (none yet) | — |
