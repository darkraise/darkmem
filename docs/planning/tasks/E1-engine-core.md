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
- [ ] Greenfield is the default: drop/recreate and **re-run the setup wizard**
      (doc 11 §9.4). A one-time transform is a convenience taken only if the mapping
      proves trivial — doc 20 §10 exists precisely to stop a plan assuming a migration
      nobody committed to. Memory data is a separate question, owned by T1.51
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
- [ ] The runtime `api_kind`-keyed assertion is the surviving embed guard, and the
      settings picker re-derives its cannot-embed hint from `api_kind` directly —
      `supports_embedding` lived on the provider table T1.01 deletes (doc 11 §4)
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
- [ ] UUIDv7 minted at accept and carried through to the `memories` row unchanged.
      Name the source: stdlib `uuid.uuid7` is 3.14+, while `pyproject` pins
      `requires-python >=3.12` — either raise the floor or take the `uuid6` package,
      but decide rather than assume
- [ ] Buffer survives a process restart (this is the durability the tier depends on)

**Verify.** `cd backend && python -m pytest tests/test_memory_buffer.py -q`

#### T1.11 — `origin_key` resolution — born at capture

`Model: Opus 5` · `Depends: T1.10` · `Doc: 05 §2.1` · `Tag: target-new` · `Gate: G-B`

**What.** `origin_key` is the capture-session / per-boot agent-run identity, and every
later corroboration count in E2 is `COUNT(DISTINCT origin_key)` over it. Getting this
wrong in Phase 1 silently inflates every verification number in Phase 2.

**This is not the `source` resolution chain.** `source` resolves explicit arg > the
`X-Darkmem-Client` header > a User-Agent product map > `mcp`, and that chain belongs to
T1.42. `origin_key` has its own, shorter chain (doc 05 §2.1): a declared
`X-Darkmem-Origin` header carrying the caller's capture-session id, composed as
`source ‖ ':' ‖ origin_id`; failing that, the merge-to-one fallback
`'unknown:' ‖ source ‖ ':' ‖ project`. **When identity is genuinely unknown it merges to
ONE origin** — undercount, never manufacture agreement.

**Done when:**
- [ ] Resolution implements doc 05 §2.1's chain exactly: declared origin id →
      `source:origin_id`, else `unknown:source:project`
- [ ] Unknown identity provably collapses to one origin per `(source, project)`
- [ ] A test asserts two unknown-identity captures from one source do **not** count as
      two origins
- [ ] **A per-request random is forbidden** (doc 05 §12) — it counterfeits independence
      and would make every corroboration count a fiction. A test asserts two captures with
      no declared origin produce the *same* key, not two fresh ones

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
- [ ] Claim batch is `buffer_claim_batch` (a `config` row, default 32, sized near the
      embed chunk) — **not** the capture door's 1–100 cap, which governs a different
      boundary (doc 05 §3)
- [ ] Doc 05 §3.1's buffer contract holds: poison rows bounded by `buffer_max_attempts`
      then moved to `error` for triage, stale claims visible, `done` rows retained
- [ ] Registered under `JobRegistry` with a cron, a `min_interval_seconds` floor, and a
      per-job lock like every other job

**Verify.** `cd backend && python -m pytest tests/test_buffer_flush.py -q`

#### T1.14 — `wait_process` interactive bypass

`Model: Sonnet 5` · `Depends: T1.13` · `Doc: 05 §3` · `Tag: target-new` · `Gate: G-B`

**What.** An interactive caller that needs the result now bypasses the buffer and runs
the pipeline inline.

**Done when:**
- [ ] `wait_process` writes the buffer row and then drives **that row's flush**
      synchronously — it bypasses the scheduled flush, not the buffer write
- [ ] Bounded by `buffer_wait_timeout_seconds` (config row, recommended default 10s);
      **on timeout it degrades to the plain 202 accept**, telling the caller it is
      still processing rather than hanging (doc 05 §2.2, invariant 14)
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

`Model: Opus 5` · `Depends: T1.03` · `Doc: 05 §5` · `Tag: rebuild` · `Gate: G-B`

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
- [ ] `run_bench.py` updated to exercise the **merged shipping path** with its gate
      state pinned, and the cache re-recorded. The bench assembles its own call from
      `prompt_constants` rather than going through the pipeline, so without this it
      would measure a non-shipping configuration — exactly what T0.03 forbids
- [ ] F1 bench shows no regression against the T0.05 baseline (whose tolerance must
      already anticipate this prompt change)

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

`Model: Opus 5` · `Depends: T1.16` · `Doc: 05 §5` · `Tag: rebuild` · `Gate: G-B`

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

**What.** Entity, relationship, tech, and memory types. Pure normalisers; unknown entity
types fall back to `concept`, unknown relations to `RELATED_TO`; `LEGACY_*` maps rewrite
historical names at runtime. The memory-relation vocabulary is **reserved** here and
owned by T2.15 — one vocabulary, one owner, landed taxonomy-first before doc 08's
consolidation passes emit any edge (doc 06 §10).

**Done when:**
- [ ] Only tabled values are ever stored (invariant 5)
- [ ] `LEGACY_*` rewrites keep old rows matching new code (e.g. `framework`→`tool`,
      `RUNS_ON`→`DEPLOYED_ON`, `debug`→`problem`)
- [ ] Normalisers are pure functions with no DB access
- [ ] `MEMORY_TYPES` widens 7 -> 9 with **episodic** and **procedural** (doc 06 §3);
      `insight` and `profile` do **not** join. This changes the extraction prompt, so
      it lands taxonomy-first and is measured on the F1 bench like any prompt change

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

`Model: Opus 5` · `Depends: T1.26` · `Doc: 06 §6` · `Tag: rebuild` · `Gate: G-B`

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
- [ ] Query plans confirm index use on the **keyword and direct-scan** channels. The
      semantic channel cannot: an HNSW scan applies the pushed-down predicate as a
      post-scan filter over its candidate stream, so its win is correctness and
      reduced over-fetch, not an index-scan plan — and the `limit x 3` fetch
      multiplier stays (doc 04 §10, doc 07 §7)
- [ ] String/`UUID` id normalisation happens at the boundary so matches cannot silently drop

**Verify.** `cd backend && python -m pytest tests/test_retrieval_pushdown.py -q`

#### T1.30 — RRF fusion + the unified `rank_fusion_factor`

`Model: Opus 5` · `Depends: T1.29` · `Doc: 07 §3` · `Tag: rebuild` · `Gate: G-B`

**What.** Two classes of signal, kept separate (doc 07 §3). Every signal producing a
**ranked list** joins one Reciprocal Rank Fusion at k=60 as a weighted input —
`semantic_weight` (default 0.7) is a list weight there. Every signal producing a
**per-row scalar** is a deterministic post-fusion multiplier, and `rank_fusion_factor`
is that multiplier, composing the `w_conf`/`w_importance`/`w_heat`/`w_recency` arms.
Nothing collapses the fusion into the factor. Consumers order by `rrf_score`; the
per-modality `score` key survives on the row and is the first-seen side's raw score —
never the ordering signal.

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

`Model: Opus 5` · `Depends: T1.12, T1.14, T1.33` · `Doc: 12 §2–§6` · `Tag: rebuild` · `Gate: G-B`

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

**Verify.** `cd backend && python -m pytest tests/test_api tests/test_mcp.py tests/test_mcp_batch.py tests/test_mcp_transport_security.py -q` — MCP tests are flat
files, not a `tests/test_mcp/` package.

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

`Model: Fable 5` · `Depends: T0.16, T1.24, T1.35, T1.44` · `Doc: 20 §4` · `Tag: target-new` · `Gate: G-B`

**What.** Clear G-B, adversarially. Three numbers, all of which must hold.

**Done when:**
- [ ] Extraction F1 parity with the T0.05 baseline within its stated tolerance
- [ ] Retrieval eval vs the full-context baseline, reported **with** its latency/cost twin
- [ ] Isolation probe returns zero on every channel
- [ ] All three, their artifacts, and the verdict written to `gate-ledger.md`
- [ ] Any shortfall recorded and G-B left open — never widen a bar to fit a result
- [ ] `CLAUDE.md` refreshed to the shipped shape: LLM configuration, `events` replacing
      `audit_log`, capture tiers and `memory_buffer`, the collapsed migration chain,
      and the job list. Runbook §1 makes it every agent's bootstrap contract, so a
      stale one poisons every later task

**Verify.** `./scripts/gate.sh --full` plus `python scripts/benchlib/run_isolation_probe.py`

---

## Lane I — the homelab cutover (added by review, finding B-F1)

**This lane is the only place in the plan where irrecoverable user data is at stake.**
It was missing entirely from the first draft. It runs at the tail of E1, **after G-B** —
real data moves onto the rebuilt engine only once that engine has proven itself, never
before.

#### T1.51 — Cutover transform + carried-set column map

`Model: Opus 5` · `Depends: T0.12, T1.01, T1.23` · `Doc: 19 §4` · `Tag: target-new` · `Gate: G-B`

**What.** The one-time transform from today's schema to the baseline: the `llm_` renames,
`origin_key` landing NULL on carried rows, lineage carried verbatim, and the carried set
itself — memories, tags, conversations. Everything outside that set is rebuilt, not
carried.

**Done when:**
- [ ] The carried set is enumerated explicitly, and everything outside it is named as
      rebuilt so nothing is carried by accident
- [ ] `origin_key` is NULL on carried rows and the corroboration arithmetic treats NULL as
      "no origin", never as a shared one (this is the T1.11 rule applied to history)
- [ ] Supersession lineage (`status`, `superseded_by`) carries verbatim — a transform that
      breaks `chk_superseded_has_pointer` fails loudly rather than dropping the pointer
- [ ] The transform is re-runnable against a fresh restore, because the rehearsal in T1.53
      will run it more than once

**Verify.** `cd backend && python -m pytest tests/test_cutover_transform.py -q`

#### T1.52 — Tier-C re-extraction backfill + verification counts

`Model: Opus 5` · `Depends: T1.51, T1.13, T1.26` · `Doc: 19 §4` · `Tag: target-new` · `Gate: G-B`

**What.** Carried memories have no graph under the rebuilt extractor. Re-extract them as
Tier-C work through the ordinary pipeline, then verify by counts — not by spot-checking.

**Done when:**
- [ ] Backfill runs off the hot path and is resumable after interruption
- [ ] Failures land in `pipeline_failures` for triage rather than being skipped
- [ ] Verification is by count: memories in = memories out, and the F1 gate run against
      the carried corpus matches the T0.05 baseline within tolerance
- [ ] A partial backfill is visibly partial — never reported as complete

**Verify.** `cd backend && python -m pytest tests/test_cutover_backfill.py -q`

#### T1.53 — Cutover rehearsal on a dump copy + restore drill

`Model: Sonnet 5` · `Depends: T1.52` · `Doc: 19 §4, §9` · `Tag: target-new` · `Gate: G-B`

**What.** Rehearse the whole cutover against a `pg_dump` copy of the real database. Doc 19
notes this doubles as the first restore drill — which is also the rollback story if the
frozen baseline turns out wrong.

**Done when:**
- [ ] Full rehearsal on a restored copy, end to end, with the verification counts green
- [ ] The restore path is proven, timed, and written down — this is the rollback
- [ ] A nightly `pg_dump` cadence is documented (doc 19 §9.2)
- [ ] The rehearsal never touches the real database

**Verify.** Rehearsal transcript archived under `docs/e2e/`, with the restore timing.

#### T1.54 — Execute the cutover, verify, apply the freeze tag

`Model: Fable 5` · `Depends: T1.53, T1.50, T0.15` · `Doc: 19 §2, §4` · `Tag: target-new` · `Gate: G-B`

**What.** The real thing, once and only once, after G-B has cleared. Then apply the freeze
tag that ends the regenerate-freely window.

**Done when:**
- [ ] A fresh `pg_dump` is taken immediately before, and its restore path verified
- [ ] Verification counts and the F1 gate run green **on the real data** post-cutover
- [ ] The freeze tag is applied and T0.15's CI assertion flips to enforcing additive
      revisions
- [ ] `CLAUDE.md` and the schema inventory record the freeze date — the real one
- [ ] If verification fails, the documented restore runs and the freeze is **not** applied

**Verify.** Post-cutover counts + `./scripts/gate.sh --full` on the live instance,
archived to `gate-ledger.md` alongside the G-B entry.

---

## Lane J — the surfaces the rebuild orphans (added by review, findings B-F3, B-F4, B-F10)

**Principle 10 is not optional here.** T1.01 deletes the tables today's Settings screens
edit, and demo mode currently defaults *on* with 64 files importing `src/demo/`. Without
this lane, E1 ships a backend nobody can configure behind a UI that renders fixtures.

#### T1.55 — Settings → LLM: six inline purpose cards

`Model: Sonnet 5` · `Depends: T1.01, T1.04` · `Doc: 13 §7` · `Tag: rebuild` · `Gate: G-B`

**What.** Rebuild the tab against the flattened config: six inline purpose cards plus the
`classifier_kind` toggle. **Delete the provider and profile pickers** — doc 13 §7 names
leaving a profile picker over a schema with no profiles table as an invariant-23
violation, not merely dead UI.

**Done when:**
- [ ] Six purpose cards edit inline connection details; no `*_ref` indirection remains
- [ ] Provider/profile/ml-profile UIs are deleted, not hidden
- [ ] The cannot-embed hint derives from `api_kind` (see T1.03)

**Verify.** `cd frontend && npm test -- settings-llm`

#### T1.56 — Setup wizard finalize against the flattened config

`Model: Sonnet 5` · `Depends: T1.01` · `Doc: 11 §9.4` · `Tag: rebuild` · `Gate: G-B`

**What.** The wizard writes seed-plus-overlay into the flattened `llm_purpose_configs`.
This is also the supported path for an existing install, since T1.01 makes wizard re-run
the default rather than a config transform.

**Done when:**
- [ ] Finalize writes flattened rows; no reference to the dropped tables survives
- [ ] A re-run against an initialised instance is safe and idempotent
- [ ] Trust-on-first-use gating is unchanged (doc 18)

**Verify.** `cd frontend && npm test -- setup-wizard` and `cd backend && python -m pytest tests/test_setup.py -q`

#### T1.57 — Settings → Flags, bound to `config`

`Model: Sonnet 5` · `Depends: T1.31` · `Doc: 13 §7` · `Tag: rebuild` · `Gate: G-B`

**What.** The arms rendered honestly. Every `w_*` at zero shows as **inactive** with its
activation bar named — that labelling is the UI half of the arms-at-zero honesty T1.31
lands in the backend.

**Done when:**
- [ ] Dormant arms render as inactive, never omitted (a hidden zero reads as absent)
- [ ] Corroboration N and job cadences editable as `config` rows
- [ ] Flipping a flag with no measured win is possible but visibly unmeasured

**Verify.** `cd frontend && npm test -- settings-flags`

#### T1.58 — Retire demo mode as the default

`Model: Sonnet 5` · `Depends: T1.42` · `Doc: 13 §2` · `Tag: rebuild` · `Gate: G-B`

**What.** `DEMO` currently defaults on (`VITE_DEMO !== "0"`). Flip it: real API and auth
are the default, and `src/demo/` becomes test-fixture-only.

**Done when:**
- [ ] Real mode is the default; demo is explicitly opted into
- [ ] No production route imports from `src/demo/` — asserted by a lint rule, not review
      (the existing `no-restricted-imports` rule already encodes the intent)
- [ ] The login/auth path works against the real backend end to end

**Verify.** `cd frontend && npm run lint && npm run test:e2e -- auth`

#### T1.59 — Bind the Code section to live data

`Model: Sonnet 5` · `Depends: T1.42, T1.58` · `Doc: 13 §4.2` · `Tag: rebuild` · `Gate: G-B`

**What.** Repositories (live indexing status, reindex dialog), Code Graph, and Wiki
against the real backend. T1.46 binds only the two new signals; these are the surfaces
around them.

**Done when:**
- [ ] Repo status, phase ticker, and reindex all drive real runs
- [ ] Code Graph reads the real graph; the Explorer's file tree comes from the index
- [ ] Wiki is read-only and never triggers generation on browse

**Verify.** `cd frontend && npm run test:e2e -- code`

#### T1.60 — Bind Chat and the Memory Graph explorer

`Model: Sonnet 5` · `Depends: T1.44, T1.58` · `Doc: 13 §4.1` · `Tag: rebuild` · `Gate: G-B`

**What.** Both are doc-13 committed surfaces with no task in the first draft. Chat renders
retrieved context **with its labels and trace** — an unlabelled citation in a chat answer
is the silent-authority failure invariant 14 forbids.

**Done when:**
- [ ] Chat shows layer, verification, and superseded/stale labels on every cited row
- [ ] Memory Graph reads the real graph with project scope applied in SQL
- [ ] Neither surface reads `src/demo/`

**Verify.** `cd frontend && npm test -- chat memory-graph`

#### T1.61 — Activity: feed, day view, and the buffer monitor

`Model: Sonnet 5` · `Depends: T1.08, T1.10` · `Doc: 13 §6.1` · `Tag: rebuild` · `Gate: G-B`

**What.** The Activity shell's remaining modules over `events` and `memory_buffer`. The
buffer monitor is doc 13 §6.1's named surface for poison rows — the visible half of
T1.13's `buffer_max_attempts` bounding.

**Done when:**
- [ ] Feed and day views read `/events`; no client-side aggregation
- [ ] Buffer monitor shows claimed, stale, and poison rows with their attempt counts
- [ ] A poison row is actionable from the UI, not just visible

**Verify.** `cd frontend && npm test -- activity`

#### T1.62 — App-as-edge deployment artifact

`Model: Opus 5` · `Depends: T1.42, T1.58` · `Doc: 19 §5, 18 §4` · `Tag: target-new` · `Gate: G-B`

**What.** One image containing FastAPI **and** the built SPA, with the app as the network
edge. nginx goes away, `trust_proxy_headers` flips **off**, and the login rate limiter
reads the transport peer. Both IP-source strategies stay live and tested, because the
nginx fallback and the exposed-deployment horizon each restore the header path.

**Done when:**
- [ ] One image serves API and SPA; compose surface is the two secrets, host networking,
      `repo_data` volume, Postgres `shm_size`
- [ ] `trust_proxy_headers` defaults **off**; the limiter reads `request.client.host`
- [ ] The leftmost `X-Forwarded-For` is read in **no** posture, proven by test
- [ ] Both strategies are tested, so a posture change is a config flip, not a rewrite
- [ ] Exactly one uvicorn worker (invariant 13)

**Verify.** `cd backend && python -m pytest tests/test_client_ip_attribution.py -q` plus a
clean `docker compose up -d` boot with `/health` 200.

#### T1.63 — Bind Settings: Security, Maintenance, Jobs

`Model: Sonnet 5` · `Depends: T1.58` · `Doc: 13 §7` · `Tag: rebuild` · `Gate: G-B`

**What.** The remaining Settings tabs against real endpoints, including the job board's
409-on-held-lock behaviour.

**Done when:**
- [ ] Jobs tab drives real triggers and shows a held lock as busy, never as queued
- [ ] Maintenance operations confirm before running and journal to `events`
- [ ] Security tab reflects the real posture, including which IP strategy is active

**Verify.** `cd frontend && npm test -- settings`

#### T1.64 — API e2e suite + the honesty specs

`Model: Sonnet 5` · `Depends: T0.16, T1.42` · `Doc: 17 §9` · `Tag: target-new` · `Gate: G-B`

**What.** The e2e plan's ring 3 names an "API e2e suite" that does not exist. Build it,
with a stated location and database posture, and land the eight honesty specs it owns.
Today's `docs/e2e/scripts/` run against a live server without the drop-and-migrate
discipline — decide whether to port or replace them, and say which.

**Done when:**
- [ ] The suite has one documented entry point and runs against `darkmem_test`
- [ ] The eight honesty specs from the e2e plan exist and each fails if its rule is removed
- [ ] `scripts/gate.sh --full` invokes it
- [ ] The disposition of `docs/e2e/scripts/` is recorded — ported, replaced, or retired

**Verify.** `./scripts/gate.sh --full`

#### T1.65 — `projectStore`, `contextStore`, and the project switcher

`Model: Sonnet 5` · `Depends: T1.29, T1.34` · `Doc: 13 §2` · `Tag: target-new` · `Gate: G-B`

**What.** The UI face of the isolation work: a global project scope feeding every query
key, and the session `applies_when` declaration that T1.34 boosts and T3.14's
`declareContext` verb will set.

**Done when:**
- [ ] Project scope is in every query key, so switching projects cannot serve stale rows
- [ ] Context declaration is visible and clearly distinct from project scope — conflating
      the isolation boundary with the context hint is the confusion the Memories surface
      already guards against
- [ ] An undeclared context renders as undeclared, never as a default

**Verify.** `cd frontend && npm test -- stores`

---

## Amendment log

| Date | Task | Tier | Change | Why |
|---|---|---|---|---|
| — | — | — | (none yet) | — |
