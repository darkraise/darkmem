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

`Model: Opus 5` · `Effort: high` · `Size: L` · `Depends: T0.17, T0.12c` · `Doc: 11 §2` · `Tag: rebuild` · `Gate: G-B`

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

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.01` · `Doc: 11 §3` · `Tag: rebuild` · `Gate: G-B`

**What.** Construct the client once at boot; an admin save swaps configuration
atomically under the single-worker assumption (invariant 13).

**Done when:**
- [ ] One client instance for the process lifetime; no per-call construction
- [ ] A save mid-flight never leaves a half-applied config visible to a caller
- [ ] Reload failure surfaces the error and keeps the prior working config

**Verify.** `cd backend && python -m pytest tests/test_llm_orchestrator_reload.py -q`

#### T1.03 — `api_kind` as the sole vendor-quirk home

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.01` · `Doc: 11 §4` · `Tag: rebuild` · `Gate: G-B`

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

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.01` · `Doc: 11 §2` · `Tag: rebuild` · `Gate: G-B`

**What.** `classifier_kind` (`llm` | `local`) rides inline on the classification purpose
and is the only switch selecting the classifier. Do not reintroduce a generic ML on/off
flag — that was deliberately removed in the 2026-05-01 consolidation.

**Done when:**
- [ ] `llm` and `local` both dispatch; the value lives on the purpose row
- [ ] No new feature flag is added for this

**Verify.** `cd backend && python -m pytest tests/test_classifier_kind.py -q`

#### T1.05 — Seed `synthesis` and `verification` purposes inert

`Model: Haiku 4.5` · `Effort: high` · `Size: S` · `Depends: T1.01` · `Doc: 11 §6` · `Tag: target-new, inert` · `Gate: G-B`

**What.** Both purposes seed now behind their unshipped layers (E2/E3), landed inert
with no caller.

**Done when:**
- [ ] Rows exist with sane defaults; nothing calls them
- [ ] Labelled inert in the schema inventory naming their first-writer tasks (T2.26 for
      `verification`, T3.02 for `synthesis`)

**Verify.** `cd backend && python -m pytest tests/test_inert_objects.py -q`

#### T1.06 — `events` table, monthly partitioning, append-only trigger

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T0.17, T0.12c` · `Doc: 04 §8.1` · `Tag: target-new` · `Gate: G-B`

**What.** The journal that makes measurement a query instead of an instrument.
`RANGE(created_at)` monthly partitions plus a forbid-trigger blocking UPDATE, DELETE and
TRUNCATE. Convention 8 depends on this being genuinely append-only.

**Done when:**
- [ ] Monthly partitions created ahead of need, reconciled at boot
- [ ] UPDATE / DELETE / TRUNCATE on `events` raise, proven by test
- [ ] `api_key_id` and `actor` columns land **inert** (their writer is T4.02)

**Verify.** `cd backend && python -m pytest tests/test_events_append_only.py -q`

#### T1.07 — `events` writer and the journaling convention

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.06` · `Doc: 05 §2.3` · `Tag: target-new` · `Gate: G-B`

**What.** One helper every subsystem journals through, so payload shape stays uniform
across capture, extraction, supersession, and pipeline outcomes.

**Done when:**
- [ ] Capture, extraction, supersession, and each pipeline outcome write an event
- [ ] Payload carries before/after state where the action mutates
- [ ] Journaling never blocks the hot path on failure — a journal error degrades loudly
      but does not fail the capture

**Verify.** `cd backend && python -m pytest tests/test_events_writer.py -q`

#### T1.08 — `GET /events`, `/events/calendar`, `/events/timeline`

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.07` · `Doc: 12 §7` · `Tag: target-new` · `Gate: G-B`

**What.** The read surface the Dashboard calendar and per-object timeline consume.

**Done when:**
- [ ] Three endpoints matching `api-rest-conventions.md`
- [ ] Calendar returns date-bucketed counts, not rows
- [ ] Timeline is per-object and paginated
- [ ] Project scoping is pushed into SQL, not filtered after (see T1.29a–c)

**Verify.** `cd backend && python -m pytest tests/test_api/test_events.py -q`

#### T1.09 — Retire `audit_log` reads

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T1.08` · `Doc: 04 §8.1` · `Tag: rebuild` · `Gate: G-B`

**What.** `events` replaces the coarse `audit_log`/`AuditLog` read paths. Retire the
readers; keep the auth-audit writes that doc 18 still owns.

**Done when:**
- [ ] No product read path queries `audit_log`
- [ ] Auth audit trail still functions (doc 18 posture unchanged)

**Verify.** `rg -n "audit_log|AuditLog" backend/app` reviewed — only doc-18 writes remain.

---

## Lane B — capture and the buffer (F1)

#### T1.10 — `memory_buffer` table + pre-minted UUIDv7 ids

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T0.17, T0.12c` · `Doc: 05 §2` · `Tag: target-new` · `Gate: G-B`

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

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.10` · `Doc: 05 §2.1` · `Tag: target-new` · `Gate: G-B`

**What.** `origin_key` is the capture-session / per-boot agent-run identity, and every
later corroboration count in E2 is `COUNT(DISTINCT origin_key)` over it. Getting this
wrong in Phase 1 silently inflates every verification number in Phase 2.

**This is not the `source` resolution chain.** `source` resolves explicit arg > the
`X-Darkmem-Client` header > a User-Agent product map > `mcp`, and that chain belongs to
T1.42a. `origin_key` has its own, shorter chain (doc 05 §2.1): a declared
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

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.11` · `Doc: 05 §2` · `Tag: target-new` · `Gate: G-B`

**What.** Accept validates against `MemoryCreate`, writes the buffer row, journals, and
returns a 202-style ack with the pre-minted id. No LLM call, no graph write, no waiting.

**Done when:**
- [ ] Accept latency is dominated by one insert — no model call on this path
- [ ] Validation failures return 4xx before anything is written
- [ ] Both front doors (REST + MCP) accept identically (invariant 17)

**Verify.** `cd backend && python -m pytest tests/test_api/test_capture.py -q`

#### T1.13 — `buffer_flush` job with `FOR UPDATE SKIP LOCKED`

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.12` · `Doc: 05 §3` · `Tag: target-new` · `Gate: G-B`

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

#### T1.13b — `memory_buffer` read surface and poison-row action

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.13` · `Doc: 05 §3.1, 13 §6.1, 12 §2` · `Tag: target-new` · `Gate: G-B`

**What.** The REST surface carrying `memory_buffer` state to the operator. **Added by
amendment 2026-07-27** — the plan had T1.13 producing poison rows and T1.61 rendering
them, with nothing between: no route anywhere exposes `memory_buffer`, so T1.61's buffer
monitor can only bind demo data. That is Principle 10 inverted — a Phase-1 surface with no
Phase-1 signal to read.

**Done when:**
- [ ] A read endpoint lists buffer rows with status, attempt count, claim timestamp, and
      `last_error`, filterable to claimed / stale / poison (`error`), matching
      `api-rest-conventions.md`
- [ ] Stale is derived from T1.13's lease (`buffer_claim_visibility_seconds`), reusing the
      existing `stale_claims()` helper rather than reimplementing the predicate — T1.13
      shipped it tested and without a production caller, and two definitions of stale will
      drift
- [ ] A poison row is **actionable**: a route that requeues it (resetting attempts) or
      discards it, journalling the action to `events`. T1.61's "actionable, not just
      visible" box depends on this
- [ ] Project scoping is pushed into SQL, not filtered after (T1.29a–c)
- [ ] Retention is unchanged: `done` rows are retained and `error` rows are **never** swept,
      per T1.13's contract — this surface reads and acts, it does not clean up
- [ ] REST-single-door is acceptable **with a stated reason** recorded for T1.42d's parity
      audit, as the `events` read surface already is; if it ships MCP tools instead, they go
      through the same service layer

**Verify.** `cd backend && python -m pytest tests/test_api/test_buffer.py -q`

#### T1.14 — `wait_process` interactive bypass

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.13` · `Doc: 05 §3` · `Tag: target-new` · `Gate: G-B`

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

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.12` · `Doc: 05 §2.4, 18` · `Tag: target-new` · `Gate: G-B`

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

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.03` · `Doc: 05 §5` · `Tag: rebuild` · `Gate: G-B`

**What.** One chunked embed call for the batch, returning vectors + fingerprint. The
fingerprint is registered exactly once before any partition write.

**Done when:**
- [ ] Embed failure marks every memory `embed=error` and skips all writes
- [ ] Fingerprint registered before the first partition insert, always
- [ ] No cross-fingerprint comparison anywhere (invariant 2)

**Verify.** `cd backend && python -m pytest tests/test_pipeline_phase1.py -q`

#### T1.17 — Phase 2: merged extract + classify in one call

`Model: Opus 5` · `Effort: high` · `Size: L` · `Depends: T1.16, T1.04` · `Doc: 05 §5–§6` · `Tag: rebuild` · `Gate: G-B`

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

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T1.17` · `Doc: 05 §6` · `Tag: rebuild` · `Gate: G-B`

**What.** With a local classifier the extraction call narrows to extraction-only and
classification runs in-process.

**Done when:**
- [ ] Local path produces the same `{hall, summary, emotions, flags}` surface
- [ ] Extraction prompt narrows accordingly (no dead classification fields requested)

**Verify.** `cd backend && python -m pytest tests/test_classifier_local.py -q`

#### T1.19 — Phase 3: entity embed with the two-level cache

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.16` · `Doc: 05 §5` · `Tag: rebuild` · `Gate: G-B`

**What.** Memory cache → DB cache → embed the misses, writing new vectors back to both,
keyed `(name_lower, fingerprint)`.

**Done when:**
- [ ] Cache hit rate is observable on a run (this is the phase's whole value)
- [ ] Cache writes are batched, not per-entity
- [ ] A fingerprint rotation between Phase 1 and 3 registers and switches correctly

**Verify.** `cd backend && python -m pytest tests/test_pipeline_phase3.py -q`

#### T1.20 — Phase 4: type-constrained dedup + `names_distinct`

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.19` · `Doc: 06 §5` · `Tag: rebuild` · `Gate: G-B`

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

#### T1.20a — A canonicalized entity's embedding overwrites the survivor's

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T1.20, T1.21` · `Doc: 06 §5` · `Tag: rebuild` · `Gate: G-B`

**What.** **Added by amendment 2026-07-28.** Raised first by T1.21's planning pass and again
by its execution, both of which correctly declined to fix it in lane.

When Phase 4 canonicalizes a variant onto a survivor — `postgresql` → `postgres` —
`pipeline.py` looks the embedding up under the **variant's** name and writes it against the
**survivor's** row. So the canonical entity's stored vector is whichever variant was written
last, not its own.

**Why it is small but real.** Dedup only merges at ≥0.85 cosine, so the wrong vector is by
construction a near neighbour and no single write is visibly harmful. But it is wrong in a
way that **compounds**: every re-extraction that merges a different variant rewrites the
canonical vector again, so the survivor's embedding random-walks among its variants instead
of being stable. That undermines the two things the entity partition exists for — the
`(name_lower, fingerprint)` cache, which now caches a value keyed to a name it was not
computed from, and Phase 4's own ANN probe, which compares future candidates against a drifting
target.

**Done when:**
- [ ] The survivor's row stores the embedding computed for the **survivor's** name
- [ ] A test merges two variants and asserts the stored vector is the survivor's, not the
      last-written variant's — and fails if the lookup key reverts
- [ ] Re-running the same batch twice leaves the survivor's vector **unchanged** (the
      compounding half; a single-pass test cannot see it)
- [ ] The two-level cache is keyed consistently with whatever the fix decides, so a cache hit
      cannot reintroduce the variant's vector

**Verify.** `cd backend && python -m pytest tests/test_dedup_discriminator.py tests/test_pipeline_phase3.py -q`

#### T1.21 — Phase 5: the two-savepoint write

`Model: Opus 5` · `Effort: high` · `Size: L` · `Depends: T1.20` · `Doc: 05 §5` · `Tag: rebuild` · `Gate: G-B`

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

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.19` · `Doc: 05 §5` · `Tag: rebuild` · `Gate: G-B`

**What.** If the active embedder rotates between Phase 1 and Phase 3, Phase 3 registers
and switches to the new fingerprint rather than writing into the old partition.

**Done when:**
- [ ] Rotation mid-batch is handled without a cross-fingerprint write
- [ ] Test forces a rotation and asserts partition correctness

**Verify.** `cd backend && python -m pytest tests/test_embedder_rotation.py -q`

#### T1.23 — Five closed vocabularies + normalisers + `LEGACY_*` maps

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T0.17, T0.12c` · `Doc: 06 §3` · `Tag: rebuild` · `Gate: G-B`

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

**The extraction system prompt is out of scope here — T1.17 owns it** (amended
2026-07-27). The widened vocabulary reaches the model through the schema string
`_build_extraction_schema` builds; the system prompt's own seven-type enumeration is
left byte-identical and pinned by a test, because that text is half the F1 bench's
cache key and editing it invalidates all 36 cached raw outputs, turning the merge
gate red until a live re-measurement against the same model re-warms it. T1.17
already rewrites that prompt to schema + content + seed + minimal rules, and G-B's
tolerance already budgets the re-sample. Until then nothing *emits* the two new
kinds from extraction — which is the taxonomy-first ordering, not a gap: the value
lands in the vocabulary, and every hard-coded copy is swept, before any feature
emits it.

**Verify.** `cd backend && python -m pytest tests/test_taxonomy.py -q`

#### T1.24a — Pass registry, the ordering contract, and the per-pass harness

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.23` · `Doc: 06 §4` · `Tag: rebuild` · `Gate: G-B`

**What.** The scaffold the ~40 passes hang off: an ordered registry where each pass is a
pure `list[dict] -> list[dict]`, individually testable and individually reversible, with no
hidden state.

**Three ordering constraints are load-bearing and must be encoded here, not left to
convention** (doc 06 §4): entity rescue runs **after** entity dedup, so canonical short
names are not dropped as substrings; `_fan_out_coordinated` runs **last**, after
`_dedup_by_target_predicate`, because fan-out deliberately mints a multi-source set that
the dedup would otherwise collapse; and `_filter_event_edges` runs **twice**, because
fan-out can mint an event-typed edge the first pass never saw.

**Done when:**
- [ ] Registry is an explicit ordered sequence; reordering is a one-line, measurable change
- [ ] Each pass is a pure function with its own test fixture
- [ ] The three ordering constraints are asserted by tests that fail if the order changes
- [ ] Zero model calls in the whole chain (this is what makes the F1 bench free to iterate)

**Verify.** `cd backend && python -m pytest tests/test_pass_registry.py -q`

#### T1.24b — Stage 1: entity shaping

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.24a` · `Doc: 06 §4 S1` · `Tag: rebuild` · `Gate: G-B`

**What.** The non-mutating entity filters, in doc 06 §4's order: `_normalize_names`,
`_filter_noise` / `_filter_literals`, `_snap_hardware_types` / `_apply_type_overrides`,
`_filter_hallucinated_names`, `_filter_negation_only`, `_dedup_entities`.

**`_apply_type_overrides` is the curated map, and it is where nuanced typing is actually
fixed** — six rounds of prompt patches historically failed to move this model on entity
type. Fix in the map, not the prompt.

**Done when:**
- [ ] Each pass lands with its own tests before the next is added
- [ ] Value-literals, generic nouns, filenames, URLs, env vars, IP/port and dotted config
      stems are dropped as entities
- [ ] Multi-word names not grounded in the source are dropped
- [ ] Entity F1 (name+type) does not regress at any point in the chain

**Verify.** `cd backend && python scripts/extraction_bench/run_bench.py --algo-only`

#### T1.24c — Stage 2: entity rescue

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.24b` · `Doc: 06 §4 S2` · `Tag: rebuild` · `Gate: G-B`

**What.** Add back what the LLM dropped: `_rescue_known_entities` (curated short and
hardware names, negation-aware, **span-guarded**), `_rescue_file_path_entities`,
`_rescue_happened_on`.

**Done when:**
- [ ] Runs **after** dedup, per T1.24a's ordering contract
- [ ] Span guard holds: `darkraise` is not re-added inside `darkraise-ui`, nor `github`
      inside `GitHub Actions` — both are recorded regressions
- [ ] Negated mentions are not rescued
- [ ] ISO dates survive for `HAPPENED_ON`

**Verify.** `cd backend && python -m pytest tests/test_entity_rescue.py -q`

#### T1.24d — Stage 4: relation gating and direction

`Model: Opus 5` · `Effort: high` · `Size: L` · `Depends: T1.24c, T1.25` · `Doc: 06 §4 S4` · `Tag: rebuild` · `Gate: G-B`

**What.** Remap to valid names and strip edges to negated entities; the two REPLACES gates
(`_gate_replaces_selection`, `_gate_replaces_requires_verb`) that reserve REPLACES for real
migrations; temporal handling (`_suppress_temporal_edges`, `_downgrade_future_to_mentions`,
`_drop_date_misuse`); direction validation (`_validate_directions`,
`_validate_hosting_direction`); and `_filter_event_edges`, which allows an event only
`HAPPENED_ON` / `CAUSES` / `AUTHORED_BY` / `MENTIONS`.

**Done when:**
- [ ] Each gate individually tested; a negation does not mint a spurious REPLACES
- [ ] Unambiguously wrong directions swap; ambiguous ones are left alone
- [ ] Relation F1 does not regress
- [ ] This is stage 4 — stage 3 (the rescue layer) is T1.25 and runs before it

**Verify.** `cd backend && python -m pytest tests/test_relation_gating.py -q`

#### T1.24e — Stage 5: collapse, dedup, fan-out

`Model: Opus 5` · `Effort: high` · `Size: L` · `Depends: T1.24d` · `Doc: 06 §4 S5` · `Tag: rebuild` · `Gate: G-B`

**What.** Drop redundant `USES` when a REPLACES or DEPLOYED_ON exists;
`_dedup_by_target_predicate` with its tie-break (**rescue-tagged beats LLM, then weight** —
this is the wrong-direction-REPLACES fix); `_fan_out_coordinated`; then the second
`_filter_event_edges` and `_drop_unlinked_dates`.

**Done when:**
- [ ] The rescue-first tie-break is tested against a known wrong-direction case
- [ ] Fan-out runs last and its output survives dedup, per the ordering contract
- [ ] `_filter_event_edges` demonstrably runs twice, and the second run catches an edge the
      first could not have seen

**Verify.** `cd backend && python -m pytest tests/test_collapse_fanout.py -q`

#### T1.24f — Whole-chain F1 parity against the recorded baseline

`Model: Fable 5` · `Effort: high` · `Size: M` · `Depends: T1.24e, T1.17` · `Doc: 06 §4, 17 §3` · `Tag: rebuild` · `Gate: G-B`

**What.** The chain is only as good as its measured number. Run the full bench against
T0.05's recorded baseline on both gold and held-out, and confirm the moat survived the
rebuild.

**Done when:**
- [ ] All four dimensions at or above the T0.05 baseline within its tolerance
- [ ] No pass is a prompt instruction in disguise — the prompt stays minimal (doc 06 §4)
- [ ] Per-pass contribution recorded, so a later reorder can be judged against evidence

**Verify.** `cd backend && python scripts/extraction_bench/run_bench.py --algo-only` and
`--gold gold_heldout.json`; numbers appended to `gate-ledger.md` under G-B.

#### T1.25 — `relation_rescue` layer

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.24a` · `Doc: 06 §4` · `Tag: exists-today` · `Gate: G-B`

**What.** Doc 06 §4's **Stage 3** — the only surviving ingestion-side behavioural flag.
Three passes: `_rescue_relations` (adjacency connectors under tight gap constraints),
subject-tracking (via/with/using/to keyed on the clause subject), and
`_rescue_relations_replaces` (Patterns A–D: from-X-to-Y, verb-X-prep-Y, Y-supersedes-X,
out-of-A-into-B). The substring over-extraction guard belongs to `_rescue_known_entities`
in Stage 2 — that is T1.24c's, not this task's.

**Done when:**
- [ ] Rescue-tagged wins the `_dedup_by_target_predicate` tie-break, then weight
- [ ] Every rescue-emitted triple carries `properties.rescue = True`
- [ ] `REPLACES` / `IMPROVES_ON` / legacy `BUILDS_ON` collapse via `family_key`
- [ ] Guarded by the F1 bench — reorder or remove only against a measured delta

**Verify.** `cd backend && python -m pytest tests/test_relation_rescue.py -q`

#### T1.26 — Strip-before-rewrite: idempotent re-extraction

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.21` · `Doc: 06 §6` · `Tag: rebuild` · `Gate: G-B`

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

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.26` · `Doc: 06 §6` · `Tag: rebuild` · `Gate: G-B`

**What.** Recompute `memories.technologies` from entities whose type is in `TECH_TYPES`,
lowercase, GIN-indexed. Supersession and the retrieval filter both read this column
instead of joining — keep all three properties (lowercase, denormalised, indexed).

**Done when:**
- [ ] Recomputed on every graph write, never partially updated
- [ ] Always lowercase; GIN index present and used by the supersession query plan
- [ ] Curated `_TYPE_OVERRIDES` applied (this map, not the prompt, is what fixes typing)

**Verify.** `cd backend && python -m pytest tests/test_technologies_denorm.py -q`

#### T1.28 — `graph_orphan_cleanup` backstop

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T1.26` · `Doc: 06 §6` · `Tag: exists-today` · `Gate: G-B`

**What.** The hourly unscoped sweep (`prune_orphan_entities`) so Phase-4 dedup never
merges fresh entities onto stale ghosts.

**Done when:**
- [ ] Runs hourly under JobRegistry with its own lock and floor
- [ ] Removes only entities with no live memory and no surviving relation
- [ ] A dedup run after the sweep cannot match a pruned ghost

*terminal-by-design — nothing depends on this; it is a backstop, an activation, or a
leaf surface, not infrastructure another task consumes.*

**Verify.** `cd backend && python -m pytest tests/test_graph_orphan_cleanup.py -q`

---

## Lane D — retrieval (F3)

#### T1.29a — Pushdown on the semantic channel

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.16` · `Doc: 07 §7, 04 §10` · `Tag: rebuild` · `Gate: G-B`

**What.** Project, status, and archived predicates into the SQL for the semantic channel.

**Set the expectation correctly.** An HNSW scan applies the predicate as a **post-scan
filter** over its candidate stream — the win here is correctness and reduced over-fetch,
**not** an index-scan plan, and the `limit x 3` fetch multiplier stays. A task that chases
an index plan on this channel is chasing something the index cannot give.

**Done when:**
- [ ] Predicates are in the SQL, never applied in Python afterwards
- [ ] The fetch multiplier still compensates for post-scan filtering
- [ ] String/`UUID` id normalisation happens at the boundary — hybrid search returns
      strings, the vector repo returns `UUID`, and a mismatch drops matches silently

**Verify.** `cd backend && python -m pytest tests/test_pushdown_semantic.py -q`

#### T1.29b — Pushdown on the keyword and graph channels

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.29a` · `Doc: 07 §7` · `Tag: rebuild` · `Gate: G-B`

**What.** The same predicates on `ts_rank` keyword search and the graph traversal. Unlike
the semantic channel, these **can** show an index-scan plan, and should.

**Done when:**
- [ ] Query plans confirm index use on both
- [ ] Graph traversal cannot cross a project boundary mid-walk

**Verify.** `cd backend && python -m pytest tests/test_pushdown_keyword_graph.py -q`

#### T1.29c — Pushdown on `memory_reason` and code search

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.29b` · `Doc: 07 §7` · `Tag: rebuild` · `Gate: G-B`

**What.** The two channels with the recorded leak. `memory_reason` is named in doc 07 §7 as
the specific cross-project and superseded escape; closing it is the **G-B blocking
prerequisite**, and no phase after 1 may describe isolation as holding without it.

**Done when:**
- [ ] `memory_reason` is proven leak-free against deliberately hostile fixtures
- [ ] Code search is scoped by repository, and repository scope is not project scope
- [ ] Every channel now filters in SQL — T1.35's probe is what proves it

**Verify.** `cd backend && python -m pytest tests/test_pushdown_reason_code.py -q`

#### T1.29d — Close the channels the pushdown enumeration missed

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.29c` · `Doc: 07 §7, §9, 20 §4` · `Tag: rebuild` · `Gate: G-B`

**What.** Three confirmed live isolation leaks on channels **no task enumerated**, found by
T1.29c's code-derived channel inventory. **Added by amendment 2026-07-27.** T1.29a–c were
scoped from doc 07 §7/§9's consumer list, and that list is now demonstrably incomplete —
it had already missed `ChatService`, and the inventory found three more.

**The leaks, each verified in the tree:**

1. **`GET /api/v1/vectors/projection`** — authenticated, `limit` up to **5000**, calls
   `get_all_vectors(fingerprint, limit)` with **no project, status or archived predicate**,
   and its points carry memory content snippets. This is the one most likely to make
   T1.35's zero a false pass.
2. **`memory_find_duplicates`** — calls `find_similar` with no filters, and its rows carry
   the payload content.
3. **`GraphService._fetch_neighbor_memories`** — applies project and archived but **never
   status**, so a superseded neighbour still reaches `get_memory_context`. T1.29c reported
   rather than fixed this, because changing it also changes the shape T1.29b deliberately
   chose for the entity and relation arms; resolve that interaction explicitly.

**Done when:**
- [ ] All three filter in SQL, with the same predicates the other channels use
- [ ] The projection endpoint keeps its single-fingerprint constraint — inactive
      fingerprints live in other partitions and mixing spaces yields meaningless
      coordinates (invariant 2)
- [ ] T1.29c's channel inventory is re-derived from the code and reported **empty of
      unscoped channels**, not merely updated by hand
- [ ] Each fix has a hostile-fixture test that fails if the predicate is removed

**Verify.** `cd backend && python -m pytest tests/test_pushdown_remaining_channels.py -q`

#### T1.29e — Adjudicate the operational surfaces that return memory content

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.29d` · `Doc: 07 §7, 18, 20 §4` · `Tag: rebuild` · `Gate: G-B`

**What.** T1.29d's inventory came back **empty of unscoped retrieval channels but not empty
of unscoped memory-content channels**. Five live authenticated surfaces still return memory
content with predicates missing, none owned by any task. **Added by amendment 2026-07-27,
the third round of this discovery.**

**This task is an adjudication, not a blanket fix.** Some of these are operator/triage
surfaces where cross-project visibility may be *correct* — a pipeline-failure triage screen
that hid failures from other projects would be a worse tool. The deliverable is a decision
per surface, with its reason recorded, exactly as T1.42d does for two-door parity. What is
**not** acceptable is a surface whose scoping nobody has decided.

**The five, from T1.29d's report:**

1. **`GET /reembed/obsolete/memories`** — 120-char previews, and **its anti-join degrades to
   a literal `TRUE` when the active partition is absent**, at which point it previews every
   row in the database. That degradation is a defect in its own right regardless of the
   scoping decision, and makes it a larger surface than `/vectors/projection` was.
2. **`GET /pipeline-failures`** — 80-char preview over an unscoped `LEFT JOIN memories`.
3. **The analytics recents list.**
4. **`GET /memory-buffer`** (T1.13b's) — *scopeable*: it takes a `project` parameter and
   passes it through, but defaults to all projects. Consistent with the ratified `reason`
   default, so this may well be correct; decide and record it.
5. **`GET /events`** — a 500-char content preview that **survives deletion of the memory it
   came from**. `events` is append-only by design (T1.06's three forbid-triggers), so this
   is a retention property, not a bug: deleting a memory does not remove its content from
   the journal. **Escalate this one rather than deciding it** — it is a data-retention and
   privacy question, not an isolation question.

**Done when:**
- [ ] Each of the five carries a recorded decision: scoped, or deliberately operator-wide
      **with its reason stated in the doc**
- [ ] The `/reembed/obsolete/memories` anti-join degradation is fixed regardless of the
      scoping decision — a filter that silently becomes `TRUE` is a defect on any reading
- [ ] `GET /events`' content-retention question is escalated, not resolved unilaterally
- [ ] **T1.35's probe covers memory-content surfaces, not only retrieval channels** — this
      is the distinction that made three rounds of discovery necessary, and the probe must
      encode it or its zero is false
- [ ] Every surface decided "operator-wide" is enumerated somewhere T1.42d's audit can read

**Verify.** `cd backend && python -m pytest tests/test_content_surface_scoping.py -q`

#### T1.30 — RRF fusion + the unified `rank_fusion_factor`

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.29b` · `Doc: 07 §3` · `Tag: rebuild` · `Gate: G-B`

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

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T1.30` · `Doc: 07 §3` · `Tag: target-new, inert` · `Gate: G-B`

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

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T1.30` · `Doc: 07 §3` · `Tag: exists-today` · `Gate: G-B`

**What.** `reranker_enabled` ships wired and off. When on, LLM-scores the top 40
RRF-ranked rows 0–10 and appends the unscored tail in original order.

**Done when:**
- [ ] Flag defaults off; on-path tested
- [ ] The unscored tail past rank 40 keeps its RRF order, never re-ranked
- [ ] Turning it on requires a measured win including p95 cost (recorded in the ledger)

**Verify.** `cd backend && python -m pytest tests/test_reranker.py -q`

#### T1.33 — The retrieval trace

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.30` · `Doc: 07 §8` · `Tag: target-new` · `Gate: G-B`

**What.** Envelope + per-row trace attached on request. Transient — **no table in v1**.
This is the signal the why-retrieved UI (T1.44) renders, and it is where the RRF and
rerank scores stop being dropped at the API boundary.

**Done when:**
- [ ] Trace carries per-channel contribution, fused `rrf_score`, and rerank score
- [ ] Attached only when requested; zero cost when not
- [ ] Scores survive to the API response — the known drop-at-the-boundary defect is
      closed and has a regression test
- [ ] Exclusion counts are in the envelope (a silent drop is the failure mode)
- [ ] Ships the `honesty/no-silent-drop` e2e spec: a filtered channel reports its count
      and no row disappears uncounted. The spec fails if the rule is removed

**Verify.** `cd backend && python -m pytest tests/test_retrieval_trace.py -q`

#### T1.34 — `applies_when` context-boost slot

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.30` · `Doc: 07, 09 §5` · `Tag: target-new` · `Gate: G-B`

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

`Model: Fable 5` · `Effort: high` · `Size: M` · `Depends: T1.29c, T0.10` · `Doc: 20 §4` · `Tag: target-new` · `Gate: G-B`

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

#### T1.35a — Label the escapes the isolation probe counted

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.35` · `Doc: 20 §4` · `Tag: rebuild` · `Gate: G-B`

**What.** T1.35's probe returned **10**, against a bar of 0, so G-B's isolation row is a
recorded FAIL. **Added by amendment 2026-07-28.** Close them.

**All ten are the same failure mode, and it is not the one the earlier five rounds fixed.**
Every one is `[V2]` — *a row returned without its label*, not a row wrongly returned. These
surfaces legitimately default to every project (the `reason` default was ratified), but the
rows arrive carrying no `project` and no `status`, so a consumer cannot tell a cross-project
or superseded row from a local live one. That is the honesty half of invariant 14, and it is
exactly what the bar's word "unlabelled" was there to catch.

| Surface | Door | Count |
|---|---|---|
| `memory_reason` | `POST /api/v1/memories/reason` **and** `mcp:memory_reason` | 4 |
| `chat_retrieval` | `POST /api/v1/chat/completions` | 2 |
| `chat_history_citations` | `GET /api/v1/chat/conversations/{id}` | 2 |
| `reembed_backfill_queue` | `GET /api/v1/reembed/obsolete/memories` | 2 |

**Done when:**
- [ ] All four surfaces emit `project` and `status` on every memory row they return
- [ ] `python scripts/benchlib/run_isolation_probe.py` returns **0**, recorded in
      `gate-ledger.md` under G-B alongside the failing 10
- [ ] The registry's own claims are made true: `memory_reason` and `chat_retrieval` are
      classified as label-emitting in `app/services/content_surfaces.py` while their
      responses do not emit — fix the responses, **not** the classification
- [ ] Follow the precedent T1.29d set: `get_all_vectors` labels every row **unconditionally**,
      including for `filters=None` callers, so a row escaping an unenumerated caller arrives
      self-describing. Prefer that shape over per-call-site labelling

**Verify.** `cd backend && python scripts/benchlib/run_isolation_probe.py` — expect `0`.

#### T1.36 — Supersession detector, rules 1–6 verbatim

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.21, T1.27` · `Doc: 08 §2.1` · `Tag: exists-today` · `Gate: G-B`

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
- [ ] Ships the `honesty/superseded-pointer` e2e spec: `status='superseded'` without
      `superseded_by` is impossible

**Verify.** `cd backend && python -m pytest tests/test_supersession.py -q`

#### T1.37 — TTL sweep, demote before delete

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.36` · `Doc: 08 §2.3` · `Tag: exists-today` · `Gate: G-B`

**What.** `expired_memory_cleanup` deletes rows past `expires_at`, **first** demoting
every dependent pointing at an expiring row via `superseded_by` to `deprecated` with
`superseded_by=NULL`. The FK is `ON DELETE SET NULL`, so skipping the demotion violates
`chk_superseded_has_pointer` and aborts the whole batch.

**Done when:**
- [ ] Demotion precedes deletion, proven by a test that fails if reordered
- [ ] The interactive delete path runs the identical demotion
- [ ] `expires_at` stays caller-set this phase (the self-expiring-fact half is T2.34)
- [ ] Ships the `honesty/demote-before-delete` e2e spec: reordering the sweep's
      demote/delete breaks the constraint

**Verify.** `cd backend && python -m pytest tests/test_expiry_sweep.py -q`

---

## Lane F — code truth hardening T1–T4 (F11)

#### T1.38 — T1 fail-stale

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.07` · `Doc: 10 §3` · `Tag: target-new` · `Gate: G-B`

**What.** A pipeline exception keeps the last-good graph, labelled `stale` — never wipes.
A diff failure falls back to a full index, not a bare wipe.

**Done when:**
- [ ] Forced mid-index failure leaves the prior graph queryable and marked stale
- [ ] The stale label names the last-good sha and the cause
- [ ] No path deletes a graph without a successful replacement

**Verify.** `cd backend && python -m pytest tests/test_code_fail_stale.py -q`

#### T1.39 — T2 index-debt drain

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.38` · `Doc: 10 §3` · `Tag: target-new` · `Gate: G-B`

**What.** Dependent-caller re-trace overflow past the retrace cap persists to
`repositories.index_debt` and drains in continuation batches. **Never dropped** — silent
truncation here is a graph that is quietly wrong.

**Done when:**
- [ ] Overflow persists rather than truncating
- [ ] Continuation batches drain it to zero across runs
- [ ] Debt count is observable (it is the UI signal in T1.46)

**Verify.** `cd backend && python -m pytest tests/test_index_debt.py -q`

#### T1.40 — T3 `code_reconcile` job

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.39` · `Doc: 10 §3` · `Tag: target-new` · `Gate: G-B`

**What.** Periodically hash each tracked repo's working tree and feed mismatches through
the incremental path.

**Done when:**
- [ ] Registered under JobRegistry with cron, floor, and lock
- [ ] A drifted working tree is detected and reconciled incrementally
- [ ] An unchanged tree short-circuits with no work

**Verify.** `cd backend && python -m pytest tests/test_code_reconcile.py -q`

#### T1.41 — T4 summary carry-over

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T1.40` · `Doc: 10 §3` · `Tag: target-new` · `Gate: G-B`

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

#### T1.42a — Payload envelope + source and context resolution

`Model: Opus 5` · `Effort: high` · `Size: L` · `Depends: T1.12, T1.14, T1.33` · `Doc: 12 §4–§5` · `Tag: rebuild` · `Gate: G-B`

**What.** The response envelope every surface returns, and the `source` resolution chain:
explicit arg > the `X-Darkmem-Client` header > a User-Agent product map > `mcp`.
`memory_batch_add` resolves on the **raw entry dicts before validation**, because
`MemoryCreate` would stamp its default and erase the absent-vs-explicit distinction.

**This is the `source` chain, not `origin_key`'s** — those are different mechanisms with
different fallbacks (T1.11 owns the other one).

**It also lands the context chain** (doc 12 §5, contract 3): per-call `context` arg >
`X-Darkmem-Context` header > project default > nothing, carrying the
`provenance: human|llm_guessed` marker. T1.34 boosts against a declared context and
T1.65 renders it, so without this wire format both are building on nothing.

**Done when:**
- [ ] One envelope shape across every surface, including error shapes
- [ ] Source resolution order tested end to end on both doors
- [ ] Batch resolution happens pre-validation, proven by a test that would fail post-hoc
- [ ] The context chain and its `provenance` marker land with the same test rigour

**Verify.** `cd backend && python -m pytest tests/test_envelope.py tests/test_client_identity.py -q`

#### T1.42b — REST surface conformance

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.42a` · `Doc: 12 §2` · `Tag: rebuild` · `Gate: G-B`

**What.** Every Phase-1 REST route against `api-rest-conventions.md`: 201 on create, 204 on
delete, 202 for async-accepted, POST `.../search` for complex queries.

**Done when:**
- [ ] Every route's status codes match the convention, asserted per route
- [ ] Pagination and error shapes are uniform

**Verify.** `cd backend && python -m pytest tests/test_api -q`

#### T1.42c — MCP surface parity and transport hardening

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.42a` · `Doc: 12 §6, 18` · `Tag: rebuild` · `Gate: G-B`

**What.** The MCP tool family over the same service layer, with the transport defences
intact: DNS-rebinding protection via the Host allowlist, `MCP_ALLOWED_HOSTS` for LAN
agents, browser Origins allowlisted to the same hosts, and the 1–100 batch cap mirroring
HTTP.

**Done when:**
- [ ] Tools call the same service layer as REST — no parallel implementation
- [ ] A foreign Host gets 421, and the **default** (empty allowlist) enforces the check.
      `*` remains the documented explicit opt-out for a fully-trusted isolated network
      (doc 12 §6) — the rule that a 421 is fixed by extending the allowlist rather than
      by reaching for `*` is operator discipline, not something to make technically
      impossible
- [ ] `source_agent` defaults to the caller's raw User-Agent

**Verify.** `cd backend && python -m pytest tests/test_mcp.py tests/test_mcp_batch.py tests/test_mcp_transport_security.py -q`

#### T1.42d — Two-door parity audit

`Model: Opus 5` · `Effort: high` · `Size: S` · `Depends: T1.42b, T1.42c` · `Doc: 12, invariant 17` · `Tag: rebuild` · `Gate: G-B`

**What.** The audit that makes invariant 17 true rather than aspirational: enumerate every
Phase-1 surface and show it exists on **both** doors, or is single-door **with a stated
reason** in the doc. Sequencing MCP behind REST as a shortcut is exactly what the invariant
forbids.

**Done when:**
- [ ] A table of every Phase-1 surface with its REST and MCP status, committed
- [ ] Each single-door surface carries its reason (the `events` read surface is
      REST-single-door by design)
- [ ] A test enumerates the tool list and fails when a new REST surface has no MCP twin or
      no recorded exemption

**Verify.** `cd backend && python -m pytest tests/test_door_parity.py -q`

#### T1.43 — Dashboard + contribution calendar

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.08` · `Doc: 13 §4` · `Tag: rebuild` · `Gate: G-B`

**What.** E1's core UI surface. The calendar reads the `events` date-bucket substrate —
its click-to-date contract lands on `/memories?date=YYYY-MM-DD`.

**Done when:**
- [ ] Calendar renders from `/events/calendar`, not a client-side aggregation
- [ ] Cell click navigates to the memories surface positioned on that day
- [ ] Empty state is honest (no data ≠ broken)

**Verify.** `cd frontend && npm test && npm run test:e2e -- dashboard`

#### T1.44 — Memories search + the why-retrieved trace

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.33, T1.43` · `Doc: 13 §4, §5.4` · `Tag: rebuild` · `Gate: G-B`

**What.** The search surface with the per-row trace expanded on demand, plus the
exclusion strip that renders even when the result list is empty — a silent drop is the
failure this design fears most.

**Done when:**
- [ ] Trace shows per-channel contribution and the fused score
- [ ] Exclusion counts always render, including on zero results
- [ ] The list virtualizes (the skeleton's `useMainVirtualizer` pattern) and pages
- [ ] Honesty labels — layer, verification, superseded/stale — always render
- [ ] Ships the `honesty/exclusions-on-empty` e2e spec: exclusion counts render even
      when the result list is empty

**Verify.** `cd frontend && npm test && npm run test:e2e -- memories`

#### T1.45 — Pipeline stepper, failure triage, job board

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.21, T1.13` · `Doc: 13 §6.1` · `Tag: rebuild` · `Gate: G-B`

**What.** The Activity shell v1 modules over the five-phase signal, `pipeline_failures`,
and JobRegistry.

**Done when:**
- [ ] Stepper reflects real per-phase status including `partial`
- [ ] Failure triage surfaces the failed step and offers retry
- [ ] Job board shows cron, last run, and a manual trigger that returns 409 when the
      job's lock is held (never queues)

**Verify.** `cd frontend && npm test` + manual walkthrough against a live pipeline run.

#### T1.46 — Code fail-stale banner + index-debt indicator

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.39` · `Doc: 13 §4.2` · `Tag: target-new` · `Gate: G-B`

**What.** The two signals the code-truth hardening produces, surfaced. Both already exist
in the frontend skeleton's demo data — this task binds them to the real backend.

**Done when:**
- [ ] Stale banner names the last-good sha and the cause
- [ ] Debt indicator shows queued file count and that it is draining, not lost
- [ ] Both read live backend state, not demo fixtures

**Verify.** `cd frontend && npm run test:e2e -- code`

#### T1.47 — Memory-detail supersession lineage

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.36` · `Doc: 13 §4` · `Tag: rebuild` · `Gate: G-B`

**What.** Amber badge plus successor link. Superseded rows show by default with the badge
— hiding them is what once made two memories silently vanish.

**Done when:**
- [ ] Badge renders on superseded rows; successor link navigates
- [ ] Superseded rows are visible by default, labelled, not filtered out
- [ ] Lineage renders both directions (what this replaced, what replaced it)

**Verify.** `cd frontend && npm test -- memory-detail`

#### T1.48 — Detail-level preference honoured across advanced surfaces

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.44` · `Doc: 13 §5.4, §8` · `Tag: target-new` · `Gate: G-B`

**What.** Simple/Advanced ships with the first advanced surface. `simple` hides technical
detail — per-modality and fused scores, the arm breakdown, fingerprints, raw `config`
keys, doc refs — collapsing the breakdown to one plain "why it ranked" line. **`simple`
never hides an honesty signal** (invariant 14).

**Done when:**
- [ ] Verification badges, layer labels, superseded/stale labels, and exclusion counts
      render in **both** modes — asserted by test
- [ ] Preference persists in localStorage; it changes rendering only, never the request
- [ ] Every later advanced surface honours the same flag
- [ ] Ships the `honesty/labels-always-render` e2e spec: badges, layer labels and
      superseded/stale labels render in **both** modes

**Verify.** `cd frontend && npm test -- detail-level`

#### T1.49 — WebSocket → query-invalidation mapping

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.45` · `Doc: 13 §2–§3` · `Tag: rebuild` · `Gate: G-B`

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

`Model: Fable 5` · `Effort: xhigh` · `Size: M` · `Depends: T0.16, T1.24f, T1.35, T1.44` · `Doc: 20 §4` · `Tag: target-new` · `Gate: G-B`

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

`Model: Opus 5` · `Effort: high` · `Size: L` · `Depends: T0.12c, T1.01, T1.23` · `Doc: 19 §4` · `Tag: target-new` · `Gate: G-B`

**What.** The one-time transform from today's schema to the baseline: the `llm_` renames,
`origin_key` landing NULL on carried rows, lineage carried verbatim, and the carried set
itself — memories, tags, conversations.

**Three buckets, not two.** Carried (the set above); rebuilt (the graph, via T1.52's
re-extraction); and **dropped** — `pipeline_failures`, `token_blocklist` and job-state
rows are operational residue with no post-cutover meaning (doc 19 §9.1), and are neither
carried nor rebuilt.

**Done when:**
- [ ] All three buckets enumerated explicitly — carried, rebuilt, dropped — so nothing
      is carried by accident and nothing is resurrected that should die with the old
      schema
- [ ] `origin_key` is NULL on carried rows and the corroboration arithmetic treats NULL as
      "no origin", never as a shared one (this is the T1.11 rule applied to history)
- [ ] Supersession lineage (`status`, `superseded_by`) carries verbatim — a transform that
      breaks `chk_superseded_has_pointer` fails loudly rather than dropping the pointer
- [ ] The transform is re-runnable against a fresh restore, because the rehearsal in T1.53
      will run it more than once

**Verify.** `cd backend && python -m pytest tests/test_cutover_transform.py -q`

#### T1.52 — Tier-C re-extraction backfill + verification counts

`Model: Opus 5` · `Effort: high` · `Size: L` · `Depends: T1.51, T1.13, T1.26` · `Doc: 19 §4` · `Tag: target-new` · `Gate: G-B`

**What.** Carried memories have no graph under the rebuilt extractor. Re-extract them as
Tier-C work through the ordinary pipeline, then verify by counts — not by spot-checking.

**Done when:**
- [ ] Backfill runs off the hot path and is resumable after interruption
- [ ] Failures land in `pipeline_failures` for triage rather than being skipped
- [ ] Verification is by count: carried-row counts match the dump, and the
      `pipeline_failures` residue is bounded and **triaged, not ignored**
- [ ] The F1 evidence is an **extraction-bench run on the target configuration** against
      the gold set, holding the T0.05 tolerance. There is no F1 number "against the
      carried corpus" — the homelab data carries no gold annotations, so that figure is
      not computable (doc 19 §4)
- [ ] A partial backfill is visibly partial — never reported as complete

**Verify.** `cd backend && python -m pytest tests/test_cutover_backfill.py -q`

#### T1.53 — Cutover rehearsal on a dump copy + restore drill

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.52` · `Doc: 19 §4, §9` · `Tag: target-new` · `Gate: G-B`

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

`Model: Fable 5` · `Effort: high` · `Size: M` · `Depends: T1.53, T1.50, T0.15` · `Doc: 19 §2, §4` · `Tag: target-new` · `Gate: G-B`

**What.** The real thing, once and only once, after G-B has cleared. Then apply the freeze
tag that ends the regenerate-freely window.

**Done when:**
- [ ] A fresh `pg_dump` is taken immediately before, and its restore path verified
- [ ] Post-cutover verification is green: carried-row counts match, `pipeline_failures`
      is triaged, and the extraction bench on the target configuration holds tolerance
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

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.01, T1.04` · `Doc: 13 §7` · `Tag: rebuild` · `Gate: G-B`

**What.** Rebuild the tab against the flattened config: six inline purpose cards plus the
`classifier_kind` toggle. **Delete the provider and profile pickers** — doc 13 §7 names
leaving a profile picker over a schema with no profiles table as an invariant-23
violation, not merely dead UI.

**Done when:**
- [ ] Six purpose cards edit inline connection details; no `*_ref` indirection remains
- [ ] Provider/profile/ml-profile UIs are deleted, not hidden
- [ ] The cannot-embed hint derives from `api_kind` (see T1.03)
- [ ] The three code-summarization sub-buckets (symbol / module / overview) render as
      their own cards — doc 13 §7 places them on this tab and nothing else owns them

**Verify.** `cd frontend && npm test -- settings-llm`

#### T1.56 — Setup wizard finalize against the flattened config

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.01` · `Doc: 11 §9.4` · `Tag: rebuild` · `Gate: G-B`

**What.** The wizard writes seed-plus-overlay into the flattened `llm_purpose_configs`.
This is also the supported path for an existing install, since T1.01 makes wizard re-run
the default rather than a config transform.

**Done when:**
- [ ] Finalize writes flattened rows; no reference to the dropped tables survives
- [ ] A re-run against an initialised instance is safe and idempotent
- [ ] Trust-on-first-use gating is unchanged (doc 18)

**Verify.** `cd frontend && npm test -- setup-wizard` and `cd backend && python -m pytest tests/test_setup.py -q`

#### T1.57 — Settings → Flags, bound to `config`

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.31` · `Doc: 13 §7` · `Tag: rebuild` · `Gate: G-B`

**What.** The arms rendered honestly. Every `w_*` at zero shows as **inactive** with its
activation bar named — that labelling is the UI half of the arms-at-zero honesty T1.31
lands in the backend.

**Done when:**
- [ ] Dormant arms render as inactive, never omitted (a hidden zero reads as absent)
- [ ] Corroboration N and job cadences editable as `config` rows
- [ ] Flipping a flag with no measured win is possible but visibly unmeasured

**Verify.** `cd frontend && npm test -- settings-flags`

#### T1.58 — Retire demo mode as the default

`Model: Sonnet 5` · `Effort: high` · `Size: L` · `Depends: T1.42a` · `Doc: 13 §2` · `Tag: rebuild` · `Gate: G-B`

**What.** `DEMO` currently defaults on (`VITE_DEMO !== "0"`). Flip it: real API and auth
are the default.

**This task does not strip the imports.** 66 files import `src/demo/`, and the surfaces
that bind to live data do so in T1.43–T1.49 and T1.59–T1.63 — stripping their fixtures
here would leave them broken until their binding task lands. Each binding task removes
its **own** surface's demo imports; this task lands the default flip, the real auth
path, and the lint rule **in warn mode**. T1.64 flips that rule to error once the last
binding task is done.

**Done when:**
- [ ] Real mode is the default; demo is explicitly opted into
- [ ] The `no-restricted-imports` rule covering `src/demo/*` is active in **warn** mode
      and its current violation count is recorded, so the sweep's progress is visible
- [ ] The login/auth path works against the real backend end to end

**Verify.** `cd frontend && npm run lint && npm run test:e2e -- auth`

#### T1.59 — Bind the Code section to live data

`Model: Sonnet 5` · `Effort: high` · `Size: L` · `Depends: T1.42d, T1.58` · `Doc: 13 §4.2` · `Tag: rebuild` · `Gate: G-B`

**What.** Repositories (live indexing status, reindex dialog), Code Graph, and Wiki
against the real backend. T1.46 binds only the two new signals; these are the surfaces
around them.

**Done when:**
- [ ] Repo status, phase ticker, and reindex all drive real runs
- [ ] Code Graph reads the real graph; the Explorer's file tree comes from the index
- [ ] Wiki is read-only and never triggers generation on browse

**Verify.** `cd frontend && npm run test:e2e -- code`

#### T1.60 — Bind Chat and the Memory Graph explorer

`Model: Sonnet 5` · `Effort: high` · `Size: L` · `Depends: T1.44, T1.58` · `Doc: 13 §4.1` · `Tag: rebuild` · `Gate: G-B`

**What.** Both are doc-13 committed surfaces with no task in the first draft. Chat renders
retrieved context **with its labels and trace** — an unlabelled citation in a chat answer
is the silent-authority failure invariant 14 forbids.

**Done when:**
- [ ] Chat shows layer, verification, and superseded/stale labels on every cited row
- [ ] Memory Graph reads the real graph with project scope applied in SQL
- [ ] Neither surface reads `src/demo/`

**Verify.** `cd frontend && npm test -- chat memory-graph`

#### T1.61 — Activity: feed, day view, and the buffer monitor

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.08, T1.10` · `Doc: 13 §6.1` · `Tag: rebuild` · `Gate: G-B`

**What.** The Activity shell's remaining modules over `events` and `memory_buffer`. The
buffer monitor is doc 13 §6.1's named surface for poison rows — the visible half of
T1.13's `buffer_max_attempts` bounding.

**Done when:**
- [ ] Feed and day views read `/events`; no client-side aggregation
- [ ] Buffer monitor shows claimed, stale, and poison rows with their attempt counts
- [ ] A poison row is actionable from the UI, not just visible

**Verify.** `cd frontend && npm test -- activity`

#### T1.62 — App-as-edge deployment artifact

`Model: Opus 5` · `Effort: high` · `Size: L` · `Depends: T1.42d, T1.58` · `Doc: 19 §5, 18 §4` · `Tag: target-new` · `Gate: G-B`

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

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.58` · `Doc: 13 §7` · `Tag: rebuild` · `Gate: G-B`

**What.** The remaining Settings tabs against real endpoints, including the job board's
409-on-held-lock behaviour.

**Done when:**
- [ ] Jobs tab drives real triggers and shows a held lock as busy, never as queued
- [ ] Maintenance operations confirm before running and journal to `events`
- [ ] Security tab reflects the real posture, including which IP strategy is active

**Verify.** `cd frontend && npm test -- settings`

#### T1.64 — API e2e suite + the honesty specs

`Model: Sonnet 5` · `Effort: high` · `Size: L` · `Depends: T0.16, T1.42d` · `Doc: 17 §9` · `Tag: target-new` · `Gate: G-B`

**What.** The e2e plan's ring 3 names an "API e2e suite" that does not exist. Build it,
with a stated location and database posture, and land the eight honesty specs it owns.
Today's `docs/e2e/scripts/` run against a live server without the drop-and-migrate
discipline — decide whether to port or replace them, and say which.

**Done when:**
- [ ] The suite has one documented entry point and runs against `darkmem_test`
- [ ] The **five E1-satisfiable** honesty specs are wired into the suite:
      `labels-always-render`, `exclusions-on-empty`, `no-silent-drop`,
      `demote-before-delete`, `superseded-pointer`. The other three
      (`veto-absolute`, `human-only-confirmed`, `withheld-not-grounded`) need the
      contradiction veto, ratification and grounded answering, which do not exist until
      E2/EH1 — their owning tasks ship them
- [ ] The `no-restricted-imports` demo rule flips from warn to **error** (T1.58 left it
      in warn while the binding sweep ran)
- [ ] `scripts/gate.sh --full` invokes it
- [ ] The disposition of `docs/e2e/scripts/` is recorded — ported, replaced, or retired

**Verify.** `./scripts/gate.sh --full`

#### T1.65 — `projectStore`, `contextStore`, and the project switcher

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.29c, T1.34` · `Doc: 13 §2` · `Tag: target-new` · `Gate: G-B`

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
| 2026-07-27 | T1.23 | 2 | The extraction **system prompt** is explicitly **not** swept by T1.23; the widened vocabulary reaches the model through the schema string only, and T1.17 owns the prompt-side edit. Added to T1.23's text and pinned by a test. | The prompt text is half the F1 bench's cache key (`sha256(content + "\0" + prompt)`), so any edit invalidates all 36 cached raw outputs and turns `gate.sh`'s `--algo-only` step red. Re-greening needs a live re-measurement against the same model (`deepseek-v4-flash`, `DEEPSEEK_API_KEY`), which this environment cannot reach. T1.17 already rewrites that prompt and G-B's tolerance already budgets 2 F1 flips for the re-sample, so folding the edit there costs nothing and duplicating it here would spend the budget twice. Nothing emits `episodic`/`procedural` in the meantime — which is the taxonomy-first ordering working as designed, not a gap. |
| 2026-07-27 | T1.23 | 1 | Swept two hard-coded vocabularies doc 06 §3 and doc 04 §12 do not name: the classification label space (`SIMPLE_TYPES` and the always-on `general` area in `classification_areas.py`) and the MCP tool descriptions. | The named list ( `reason()`, `_build_extraction_schema`, UI filters) is "the known hard-coded vocabularies", not an exhaustive one. Left unswept, classification could never produce the two new kinds in either mode, and the MCP surface would advertise a stale seven to every agent — both silent, both exactly the failure the sweep rule exists to prevent. |
| 2026-07-27 | T1.23 | 1 | Found and fixed a fourth frontend copy of the vocabulary (`demo/data/generate.ts`, which also emitted a non-existent `context` type) and a fifth in `memory-editor-dialog.tsx`. Doc 13's "single shared vocabulary source" is now `frontend/src/lib/taxonomy.ts`, enforced by a backend drift test. | Grep found three sites; the drift test found the fourth. A per-component list that misses a widening hides every row of the new type instead of failing, so the enforcement matters more than the sweep. |
| 2026-07-27 | T1.01 | 1 | Re-sized **L → M**. Phase 0's T0.12c already landed the mechanical read-path work — indirection tables, models and `config_llm_registry.py` deleted, resolution already one un-joined query — leaving the query-counting assertion and the F-10 decision. | Runbook §3 forbids executing an `L` directly; the honest fix is the size field, not a plan for work that no longer exists. Recording it because a size that was right when written and wrong when executed is the planning signal §3 asks for, in reverse. |
| 2026-07-27 | T1.01 | 2 | **F-10 resolved: `llm_purpose_configs.provider` is DROPPED**, end to end — column, ORM field, `LLMPurposeConfig`, both wire schemas, and the frontend `LlmPurposeConfig` interface. Inventory §4.4 updated from "unresolved" to the decision and its evidence. | Decided on evidence rather than preference: no runtime path dispatched on it. The wizard wrote `pcfg.provider = body.llm.api_kind` — a verbatim copy — and every read carried the value along unused, so the column's only possible future was drifting away from the field that actually decides behaviour. Doc 04 §7 omits it from the inline field list and doc 11 §4 fixes `api_kind` as the sole vendor-quirk home. Tier 2 because it changes a wire contract the frontend types, though no component read the key. |
| 2026-07-27 | T1.10 | 2 | **Correction, post-review.** The buffer row's id and the pre-minted memory id are now **two distinct ids**, per doc 05 §2.2 — the memory id rides `metadata_` and is read with `buffered_memory_id()`; `row.id` is the buffer tracking handle. The original implementation stored the caller's memory id AS the buffer PK. | Doc 05 §2.2 is explicit ("The buffer row's own id is the buffer tracking handle; the pre-minted memory id is the caller's durable reference") and it is T1.10's own owning doc section — I worked from doc 04 §8.6 and the brief and did not read it. The conflation was workable but deviated from the doc on the exact seam T1.12 and T1.13 consume, and a T1.13 implementer following §3.1 literally would have looked in `metadata` and found nothing. |
| 2026-07-27 | T1.10 | 1 | `REPLAYED_METADATA_FIELDS` gained `metadata` — the caller's own `MemoryCreate.metadata` dict, which doc 05 §3.1 lists among the replayed fields and the tuple omitted. It nests under its own key rather than merging. | The tuple's stated purpose is to make an unreplayed capture field a visible omission; it shipped with one invisible. A T1.12 built against the tuple would have dropped caller metadata silently — the §8.6-forbidden failure. |
| 2026-07-27 | T1.23 | 1 | **Correction, post-review.** Deleted the `PRECEDES → FOLLOWS` alias from `LEGACY_MEMORY_RELATION_TYPE_MAP`. | "A PRECEDES B" asserts A is earlier; a pure type-string normaliser cannot swap endpoints, so rewriting the type alone stored "A FOLLOWS B" and silently inverted temporal order. Unknowns now fall to `RELATES_TO`, which loses the direction claim instead of reversing it. No writer exists yet, which is precisely why it mattered — it was baked into the contract T2.15 builds on. |
| 2026-07-27 | T1.23 | 1 | **Correction, post-review.** Regenerated `frontend/src/demo/data/memories.json` and retyped one `memories-curated.ts` row. The sweep had fixed the generator but not its committed output, which still carried 1000 rows of a non-existent `context` memory type. | The drift test cannot see it — it skips `.json`, and `context` is not a vocabulary member so the hit-count heuristic cannot count it. Demo mode rendered a type absent from the shared vocabulary source: unfilterable, label falling through raw. The regenerated fixture also now exercises all nine types instead of five. |
| 2026-07-27 | T1.23 | 2 | Closed a pre-existing invariant-5 hole the review surfaced: `MemoryService.update_memory` now normalises `memory_type`, so the REST update route and MCP `memory_update` can no longer persist an untabled value. | Create normalises via the pipeline; update did not, and an unchanged content triggers no reprocess — so `memory_update(memory_type="bogus")` stored `bogus` permanently, invisible to every type filter that reads the closed set. Tier 2 because it changes behaviour on a shipped write path beyond T1.23's stated scope. |
| 2026-07-27 | T1.06 | 1 | **Correction, post-review.** `events_ensure_partition` now pins its bounds to explicit UTC offsets, normalises a mid-month argument to the month, matches the guard by the child's OID rather than a bare `relname`, and treats a concurrent `duplicate_table` as success. The partition arm also runs before the prunes in its own session. | Measured: `created_at` is `timestamptz`, so a bare date bound resolves against the session `TimeZone` at DDL time — create one month under UTC and the next under +07 and the pair silently leaves a 7-hour hole, after which an insert in the gap raises "no partition found" out through `record_event` and fails the request being journaled. JDBC clients set the session zone by default and this operator is UTC+7. The other three are the same function's remaining sharp edges. |
| 2026-07-27 | T1.07 | 2 | **Merge-time defect, found by benchlib and by nothing else.** The journaling wiring referenced `mem_record` from the per-memory `record_event` call, but `mem_record` was bound inside savepoint A — which a failed Phase 1 skips entirely. Every memory in that batch then took an `UnboundLocalError` instead of an outcome, surfacing as `embed='unknown'`, `vector/graph='error'`. The binding is hoisted to the loop body and outcome derivation is now one shared `_derive_outcome` used by both the durable event and the `pipeline.*` broadcast. | The backend suite was **909 passed** with this defect present; `scripts/benchlib/tests` caught it, because `pyproject.toml` sets `testpaths = ["tests"]` and excludes benchlib. This is the second time this session that the benchlib blind spot caught something the floor could not (T1.01 was the first). Note also that `tests/test_pipeline_process_batch.py` is a documented placeholder — a real `process_batch` integration test is exactly what would have caught this at the floor, and its absence has now cost twice. Worth a task. |
| 2026-07-27 | T1.24a | 2 | **Doc 06 §4's stated reason for ordering constraint 1 is corrected.** It said rescue-after-dedup keeps short names from being dropped "as substrings"; `_dedup_entities` has no substring rule. The constraint stands — it bites via whitespace-collapse equality — but the mechanism description was wrong, so the doc now says so. | Verified in code: dedup keys on `name.upper().replace(" ", "")` plus acronym containment, and `_is_acronym_of` requires an uppercase short side while the rescue only inserts lowercase curated names, so the acronym path can never drop a rescued name. Same class as T1.06's doc 04 §8.1 correction: the decision is untouched, only its explanation. A future reader reasoning from the substring claim would look for a rule that does not exist. |
| 2026-07-27 | T1.24a | 1 | The registry lands **28 top-level entries, not the ~40** doc 06 §4 implies, and `test_registry_is_an_explicit_ordered_sequence` pins that count. | The doc's count includes sub-passes nested inside `_rescue_relations` and helper predicates that are not themselves passes. T1.24a is scaffold-only, so the top-level body was registered as it actually runs; flattening the three synthesis sub-passes is a T1.24b–e decision. The pinned count means a later stage adding passes must update it deliberately rather than drifting. |
| 2026-07-27 | T1.05 | 1 | The two inert purposes ARE added to `PURPOSES` (and to the `Settings` defaults map), not held out of it. A first attempt held them out on the reasoning that "inert" meant undispatchable; doc 11 §6 settles it the other way. | Doc 11 §6: "the new purpose rows, their seeds, **and the wizard/`PURPOSES`-list sweep** land **before** any consumer dispatches on them; a consumer dispatching on an unseeded purpose is the same class of bug as a feature emitting an untabled entity type." Inert means *nothing dispatches*, not *not configured* — the purposes-analog of taxonomy-first. Holding them out also breaks on a fresh install: `get_llm_config` indexes its defaults map by every `PURPOSES` entry, so a purpose in the list with no `Settings` default is a `KeyError` at the first call, and that first call would be a Tier-C consumer in E2/E3. Both halves land together, each mutation-checked. |
| 2026-07-27 | T1.01 | 1 | **Correction, post-review.** The F-10 evidence sentence "nothing dispatched on it" was overstated: `scripts/ensure_ollama_models.py` (repo-root `scripts/`, never swept — only `backend/scripts/` was) filtered on `provider` in both paths, one breaking loudly and one silently returning an empty set and exiting 0. Re-keyed on `api_kind` + the base URL port; both records corrected. | The decision survives the correction — that filter was already broken, since `provider` mirrored `api_kind` and wizard-written Ollama-compat rows carry `openai`, so it already missed the purposes it existed to find. But an overclaimed evidence sentence had reached a gate-feeding record, and the silent path would have let a deploy pre-pull no models and fail later at pipeline runtime. |
| 2026-07-27 | T1.10 | 1 | **UUIDv7 source decided: the `uuid6` package, not a Python-floor raise.** Added to `pyproject.toml`, lock regenerated with the documented universal command; `app/utils/ids.py::new_id()` is the single call site. | The task required a decision rather than an assumption. `uuid.uuid7` is 3.14+; `requires-python` is >=3.12, this venv runs 3.13.5 and `backend/Dockerfile` builds on `python:3.12-slim`. Raising the floor is a toolchain migration — image, universal lock, and a 3.14 wheel for every dependency including twenty-odd tree-sitter grammars — and would break this environment immediately, for one function. One call site keeps the later swap to one import. Lock diff was exactly the two expected lines: no pywin32 leak, no uvloop drop. |
| 2026-07-27 | T1.10 | 1 | `origin_key` rides `memory_buffer.metadata`, not a new column. | Doc 04 §8.6 enumerates the table's columns and states the rule for everything else: caller-supplied fields beyond those columns ride the `metadata` jsonb and replay verbatim, and the buffer may never silently drop a captured field. Adding a column would diverge from the schema owner's table for a value nothing filters the buffer by. Tested by asserting every replayed field round-trips, including unknown future ones. |
| 2026-07-27 | T1.06 | 2 | Doc 04 §8.1's `BEFORE UPDATE OR DELETE OR TRUNCATE` forbid-trigger is **three** triggers, not one, and the doc is amended to say so. TRUNCATE fires only statement-level so it cannot share a trigger with the per-row UPDATE/DELETE guard; and a statement-level TRUNCATE trigger on a partitioned parent does not cascade to children (row triggers do), so every monthly child needs its own. | Measured on PG 17, not inferred: with only the parent's triggers, `TRUNCATE events_202607` succeeds and erases a month of the audit trail — the append-only invariant would have read as enforced while having a one-statement hole. The decision doc 04 makes (structural, role-agnostic, no `REVOKE` split) is unchanged; only its mechanism description was wrong. |
| 2026-07-27 | T1.06 | 1 | Every partition-creating path goes through one SQL function, `events_ensure_partition`, rather than each site writing its own `CREATE TABLE … PARTITION OF`. Boot reconciliation added, plus a maintenance arm on `pipeline_failure_cleanup` (doc 04 §8.1 names that job). | The per-child TRUNCATE guard is easy to forget at one of three call sites, and forgetting it is silent. Boot-only reconciliation is also insufficient: a process that boots in January and runs into March outlives its partitions, and a RANGE parent rejects every insert with no child to land in — so journaling would stop rather than degrade. |
| 2026-07-27 | T1.06 | 1 | Three existing tests cleaned up committed `events` rows with `DELETE FROM events`, which the forbid-trigger now refuses. Removed both cleanups and relaxed one exact-list assertion in `test_audit_endpoint.py` to a set assertion. | The tests were asserting "no earlier test left a row behind"; what the endpoint actually guarantees is that its action filter returns no *other* action. Rows genuinely accumulate for the life of the database now, so the set form is both correct and what production looks like. |
| 2026-07-27 | T1.23 | 1 | Fixed `scripts/gen_progress.py`, which rewrote the rollup's hand-edited Gate cell back to its literal — regenerating turned `G-A CLEARED 2026-07-27` into `G-A open`. It now carries that cell forward the way it already carries the five per-task state columns. | Every agent is told to regenerate after logging an amendment (runbook §5), so the next regeneration would have silently un-cleared a gate that was actually met — the tracker reading as if the evidence run never happened. |
| 2026-07-27 | T0.11 / T1.23 | 1 | Discharged the trigger-enumeration obligation E0 left open: doc 04 §12 and doc 19 §2 now name three trigger kinds. Also corrected `baseline-schema-inventory.md` §4.3/§9.2, which named three `touch_updated_at` triggers where the baseline authors **four** (it omitted `documents`). | The inventory is the schema work order; a divergence between it and the migration is a defect in one of them. Here the baseline was right — the rule is per-table and `documents` carries `updated_at`. |
| 2026-07-27 | T1.07 | 1 | Doc 05 §2.3 says the flush writes "the extraction outcome (`extracted` / `consolidated` per the per-step status)", which reads as a per-outcome choice between the two. Doc 06 §379 fixes `consolidated` to a different subsystem entirely (`object_type='topic'`, emitted once per Tier-C topic-detection run, doc 08/F6 — not shipped yet). Resolved as: the per-memory pipeline-outcome event T1.07 owns always emits `event_type='extracted'`; the per-step status (completed/partial/failed) rides `payload.outcome` instead of selecting the event type. `consolidated` is left declared in `EVENT_TYPES` but unemitted, for whichever F6 task wires topic-detection journaling. | Doc 05's own sentence is the only place `extracted`/`consolidated` are posed as alternatives for the *same* event; every other doc reference to `consolidated` (doc 06 §379, doc 13's timeline vocabulary listing) ties it to topic/community detection, a Tier-C pass with no ingest-time trigger. Reading doc 05 literally would require the ingest flush to sometimes emit a topic-shaped event with no topic, which doesn't type-check against doc 04 §8.1's `object_type` closed set (`memory` vs `topic`). Recording this because a future emitter for `consolidated` should tie it to topic detection, not treat doc 05 §2.3 as evidence the pipeline flush ever emits it. |
| 2026-07-27 | T1.07 | 1 | `EVENT_TYPES` / `OBJECT_TYPES` (doc 04 §8.1's closed vocabularies) land in `app/services/events.py`, not `app/taxonomy.py`, and an unrecognised value logs a warning rather than being rewritten to a safe fallback. | `app.taxonomy`'s four vocabularies (doc 06 §3) normalise strings the LLM emits, where an unknown value must be rewritten (to `concept`, `RELATED_TO`, ...) because the input is untrusted and a hallucinated type cannot reach disk. `event_type`/`object_type` are never LLM output — every call site is a literal string this codebase writes — so an unrecognised value is a programming error, not untrusted input; rewriting it would silently misfile the row instead of surfacing the bug. Colocating with the one writer mirrors the precedent `TECH_TYPES` already sets by living in `app.services.relations` rather than `app.taxonomy`. Pre-existing `auth_*`/`setup_*` event types from T0.12c (e.g. `auth_login_success`, `setup_complete`) sit outside doc 04's example list; the warn-not-rewrite design leaves them working unchanged rather than retroactively enforcing a vocabulary those call sites shipped ahead of. |
| 2026-07-27 | T1.24b | 1 | **The one entity-type error left on gold.json is deliberately NOT fixed in the curated map.** `phoenix v2` is typed `service` by both gold memories that carry it; the model emits `tool` in one and `project` in the other, which is exactly the flip `_TYPE_OVERRIDES` exists to settle. Adding the entry was measured at ent_nt 0.932 -> 0.962 and left untaken. | The name appears in `gold.json` twice and nowhere else — not in `gold_heldout.json`, not in the repo. A curated entry justified only by the set it is measured on is unfalsifiable: the +0.030 would reach G-B as generalising quality when it is a fitted constant. The map's own docstring scopes it to names "whose canonical type is unambiguous in the darkmem corpus", and one tuning file is not that. Reversible in one line if the held-out set or a real corpus later carries the name. |
| 2026-07-27 | T1.24b | 1 | **Stage 1 cannot close the remaining entity recall gap, and no pass was added to try.** All five name-only misses on `gold.json` (`isort`, `gateway`, `design doc`, `savepoints`, `cli`) are absent from the raw cached model output — the LLM never emitted them. | Stage 1 is filters only: every pass is `list[dict] -> list[dict]` that can drop or retype, never add. Recall is stage 2's (`_rescue_known_entities`, T1.24c). Recording it so T1.24c's reviewer knows the gap is already scoped and the registry count stayed at 28 for a reason. |
| 2026-07-27 | T1.03 | 1 | The vendor quirks land as a **data table** (`VendorQuirks` rows in the new `app/services/llm_quirks.py`) rather than as branches in `_headers` / `_build_openai_chat_body` / the dispatch methods. Doc 11 §4's maintenance rule and its "two mirrors" sentence are amended to match, and a test parses every module under `app/` and fails on any comparison against a vendor literal outside that table. | Doc 11 §4's own Done-when is "no vendor conditional survives at any call site", and two call sites outside the orchestrator already had one: the `/health` reachability probe and the wizard's `POST /setup/probe-models` each carried their own Ollama-vs-compat endpoint choice and their own Anthropic `x-api-key` branch, with a third copy of the `/v1`-stripping helper. Branches inside three orchestrator methods cannot be shared with a route that has no orchestrator instance, so the rule was unenforceable as written; a table both can query makes it enforceable, and the AST test makes it stay true. Also deleted `LLMProviderProfile` and `LLMProfile` from `app/config.py` — dead since T0.12c, and the former is where `supports_embedding` lived. |
| 2026-07-27 | T1.03 | 2 | The orchestrator now **injects `reasoning_effort: "none"` for `google` on every non-reasoning purpose** (when the params do not already set one), and **raises on a `reasoning_effort` the vendor does not accept** — `minimal` on `openai`, any value on `anthropic`. | Both are doc 11 §4 table rows that no code implemented: the Gemini knob only ever arrived as a literal in the `google-*` profile seeds, and T1.01 deleted the profile layer those seeds fed, so a wizard-written Gemini row would have reasoned by default, pegged `max_tokens` on a hidden trace and returned empty content — the exact failure the zai/deepseek `thinking` injection exists to prevent. The validation is the same fail-loud posture as `_assert_can_embed`: the request 400s at the vendor either way, so failing locally with the recorded effort set costs nothing and names the fix. Tier 2 because it changes what goes on the wire for two api_kinds. |
| 2026-07-27 | T1.16 | 2 | **The `tests/test_pipeline_process_batch.py` placeholder is replaced with a real integration test**, and the obligation was added to T1.16 rather than left unowned. Two cases land end to end against the real database with only the embed and extraction calls mocked: the happy path (partition row, entity/relation graph, `technologies` denorm, enrichment columns, resolved `pipeline_failures`, `extracted` journal row with `outcome=completed`) and the Phase-1-failure path (every memory `embed=error`, no partition, no registry row, no graph row, no crossref, one open failure row and one `extracted` journal row per memory). | The T1.07 row above says the placeholder's absence "has now cost twice" and ends "Worth a task" — this is that task, assigned to the owner of the failure path it kept missing. Both escapes were Phase-1-failure-path defects, which is T1.16's own first Done-when box, so the test is not a bolt-on. The three deferral reasons are solved rather than re-argued: a committing `async_sessionmaker` bound to `test_engine` with hand-written teardown, a per-test unique fingerprint plus `embedder_registry.forget`, and mocked embed/extract surfaces. Asserting `embed == "error"` specifically (not the `"unknown"` the exception-normalisation path stamps) is what makes it a regression test for T1.07's class rather than a smoke test. |
| 2026-07-27 | T1.16 | 1 | Phase 1 gained two failure classes the task text does not enumerate, both degrading to the defined Phase-1-failure state: an embed return whose vector count does not match the batch, and a failure of `_register_fingerprint` itself. | Neither was covered and both are silent. Phase 5 pairs vectors to entries by `zip`, so a short return drops the tail of the batch with no status, no `pipeline_failures` row and no broadcast, and hands the caller fewer results than entries; a long or misaligned return would store one memory's embedding under another's id. A registration failure previously escaped `process_batch` as an exception, which is the same shape as T1.07's defect — no memory gets an outcome — and leaves nothing to write into, so the batch has to take the failure path rather than proceed against a partition that does not exist. |
| 2026-07-27 | T1.19 | 2 | **Finding, not fixed — out of T1.16's lane, flagged for T1.19 (Phase 3).** On a mid-batch embedder rotation, Phase 3 keeps the cache hits it fetched under the OLD fingerprint in `name_to_embedding` and then probes and writes the whole map under the NEW one, so old-embedder vectors land in the new fingerprint's `entity_embeddings` partition and are compared against it in Phase 4. | This is the cross-fingerprint violation invariant 2 forbids, and it is silent whenever the two embedders share a dimension count (a differing one fails loud on the `vector(N)` insert instead). It is reachable only through the rotation branch Phase 3 already handles deliberately, so the branch is right and only its handling of the pre-rotation hits is wrong: they must be dropped and re-embedded, or kept keyed to their own fingerprint. T1.16 owns Phase 1 and left Phase 3 untouched per its lane boundary; T1.16's own rotation test covers the Phase-1-to-Phase-5 seam (content vector stays in the producing fingerprint's partition, entity vectors in the rotated one) and deliberately exercises the all-miss path, so it does not mask this. |
| 2026-07-27 | T1.43 | 2 | Dashboard's contribution calendar previously called `useDemoContributions()` **unconditionally, with no `DEMO` check at all** — it rendered demo data even with `VITE_DEMO=0`. There was no existing per-surface `DEMO ? demo : real` switching idiom anywhere else in the codebase to copy (only `_authenticated.tsx`/`login-form.tsx`/`theme-persistence.ts` branch on `DEMO`, none of them for a data-bound surface). T1.43 establishes that idiom for this one surface (`useContributionCalendar`: both hooks called unconditionally, the demo store hook and a real `useEventsCalendar` query gated by `enabled: !DEMO`) rather than deleting the demo fixture outright, because deleting it would make demo mode (still the default) call the live backend, contradicting `flag.ts`'s "no backend required" contract. | Ruling 1 asked to remove "the Dashboard's own demo fixture path where `/events/calendar` now covers it" and offered an explicit escape hatch — report a concern rather than pre-empt T1.58 — if the existing switching pattern made a clean removal impossible. No such pattern existed to reuse, so one was built rather than blocked on. `buildContributions`/`useDemoContributions` still exist and now serve demo mode only; the real (non-demo) path renders from `/events/calendar` exclusively, per the task's Done-when. Flagging this so T1.58 (which flips the global default) and any reviewer auditing Ruling 1 can confirm the interpretation rather than discover it. |
| 2026-07-27 | T1.12 | 2 | **`POST /memories`, `POST /memories/batch`, `memory_add`, and `memory_batch_add` are deliberately NOT cut over to the buffered 202 contract by this task**, even though doc 05 §2's table names them as the target-new front doors. T1.12 instead lands the Tier-A accept mechanics (`MemoryService.accept_capture`/`accept_capture_batch`, both proven to make zero pipeline calls) behind two new, additive doors: REST `POST /memories/capture` + `POST /memories/capture/batch`, and MCP `memory_capture` + `memory_capture_batch`. The existing doors keep running the inline pipeline exactly as before. | Verified by running the affected suites against the naive cutover: switching the existing doors to buffer-and-return breaks `tests/test_api/test_memories.py` (creates/gets/updates/deletes/searches a memory synchronously right after POST), `tests/test_mcp.py` (`_get_memory` queries the `memories` table by content immediately after `memory_add`), and every other test that calls `MemoryService.create_memory`/`batch_create_memories` expecting a `Memory` row back, not a buffered ack — dozens of tests across the floor, none of them capture-specific. The reason is sequencing, not a coding choice: nothing drains `memory_buffer` until T1.13's flush job exists, and the only way to get a synchronous result back from a buffered door is T1.14's `wait_process` bypass, which also doesn't exist yet. Doc 05 §2.2 already says this in so many words — "today every capture is effectively `wait_process=true`" — so cutting the default over now would silently strand every real capture with no drain and no opt-out, while also being impossible to land without breaking the floor this task must keep green. The production cutover belongs with or after T1.14, once the bypass exists to preserve "get it now" callers; until then this is a Tier-2 amendment because it changes what a later task (whichever lands the cutover) still has to do, and it should not be re-discovered from scratch. |
| 2026-07-27 | T1.24c | 2 | **Stage 2 gains a fourth pass, `_rescue_relation_endpoints`, and doc 06 §4's S2 diagram (B1 -> B2 -> B3) needs a B0 box ahead of it.** The pass reinstates a name the model asserted as an endpoint of one of its own edges but omitted from its own `entities` array; without it `_remap_to_valid_entities` deletes every edge anchored to that name. Two new `RunsBefore` constraints are declared and validated at import: dedup before it (same whitespace-collapse reason as constraint 1), and it before the remap it exists to survive. The doc edit is **not made here** — `docs/design/` is outside this lane's file list — so the controller owns landing the B0 box. | Measured, not inferred: across both gold sets there are exactly five endpoints the model asserted but did not list, and all five are gold entities — zero false positives. The failure is the model's proper-noun bias: it lists `Auth0`, `RFC 7519` and `Datadog` while dropping the common-noun subject the sentence is about (`the design doc`, `the web app`, `the CLI`), and it emits the edges anyway. Doc 06 §4 already scopes its stage boxes as "representative passes; the full inventory is the ordered `clean_extraction` body", so a fourth pass inside S2's declared purpose ("add back what the LLM dropped") extends the inventory rather than contradicting it. Registry count pinned 28 -> 29 in the same commit per T1.24a's deliberate-update rule. Also corrected a stale comment in `_rescue_known_entities` that claimed `_` is a word-boundary separator; the regex has always kept `_` inside the class, so `CPU_count` never yielded `cpu`, and the behaviour is now pinned rather than the claim. |
| 2026-07-27 | T1.24c | 1 | **No curated name list was added, and three recall wins were measured and declined.** The one new vocabulary, `_ARTIFACT_HEAD_NOUNS`, is a verbatim transcription of the frozen extraction system prompt's own rules 7b and 9j; a test asserts every entry already appears in that prompt, so it cannot drift into a fitted list. Declines: (a) rescuing negated endpoints would have taken `savepoints` on `gold.json` for ent_nt +0.008 / ent_n +0.008, and is refused because the task's own Done-when forbids it and it would make `_filter_negation_only` bypassable — it also *cost* rel -0.012, so the decline is not even a net loss; (b) `isort` and `gateway` are still missed and would need a genuine curated entry, untaken; (c) `phoenix v2` stays out per the ratified T1.24b decline. | Ruling 1's standard is that a curated name must be justifiable independently of the set it is measured on. The head-noun sets clear it by construction: they come from a file this lane is forbidden to edit, written before either gold set, and the model's under-compliance with those two rules is exactly the case doc 06 §4 says to fix in the pass chain rather than the prompt. The generalisation evidence is that **held-out moved further than gold on every dimension** (ent_nt +0.056 vs +0.008, ent_n +0.054 vs +0.008, rel +0.205 vs +0.030) — the opposite of the fitting signature, which is gold movement with a flat held-out. The alternative typing (blanket `concept`, the taxonomy's unknown default) was measured and rejected: it regresses ent_nt *below baseline* on both sets (gold 0.925 vs 0.932, held-out 0.847 vs 0.893). |
| 2026-07-27 | T1.24b | 1 | **Controller ruling: the declined `phoenix v2` curated type-map entry stays declined.** T1.24b measured it at +0.030 entity F1 and escalated rather than taking it; the decline is ratified and the same standard was written into T1.24c's brief as a binding constraint on every curated name that task adds. | The name occurs twice in `gold.json` and nowhere else — not in `gold_heldout.json`, not in the repository. A constant justified only by the set it is measured on is unfalsifiable, and G-B's claim is F1 as *evidence* of extraction quality; a gain fitted to the answer key inflates the gate number using the gate's own answer key. T1.24c then supplied the counter-example that shows the standard is not merely conservative: a general rule grounded in the model's own output moved held-out roughly seven times further than gold. |
| 2026-07-27 | T1.22 | 2 | **Re-routed, controller.** T1.16's Phase-3 cross-fingerprint finding was logged against T1.19; its owner is **T1.22**, whose Done-when already names the exact property ("rotation mid-batch is handled without a cross-fingerprint write"). T1.19 rebuilds the cache that feeds the hole and must not reintroduce it. | On a mid-batch embedder rotation Phase 3 keeps the cache hits it fetched under the pre-rotation fingerprint, then switches `entity_fingerprint` and probes and writes the whole map — old hits included — into the new partition. That is invariant 2, and it is silent precisely when the two embedders share a dimension count; a differing count fails loud on the `vector(N)` insert, which is why it has never been hit. Pre-existing, not introduced by T1.16, and correctly left unfixed as out-of-lane. |
| 2026-07-27 | T1.14 | 2 | **T1.14 owns the front-door cutover, and G-B may not claim doc 05 §2 until it lands.** T1.12 landed Tier-A additively — new `POST /memories/capture(/batch)` and MCP `memory_capture`/`memory_capture_batch` — leaving `POST /memories`, `POST /memories/batch`, `memory_add` and `memory_batch_add` synchronous. Those additive doors are scaffolding, not the destination; T1.14 collapses them back. | Verified by running it, not predicted: cutting the named doors over now breaks dozens of unrelated tests across the floor, because nothing drains `memory_buffer` until T1.13 and no caller can get a synchronous result back until T1.14's `wait_process` bypass exists. Doc 05 §2.2 concedes the same state ("today every capture is effectively `wait_process=true`"), and T1.14's own text ("default remains buffered; the bypass is opt-in per call") is only true once the flip happens. Recorded against T1.50 as well: the mechanism exists but doc 05 §2's named front doors do not yet carry it. |
| 2026-07-27 | T1.24c | 1 | **Doc 06 §4's Stage 2 diagram corrected by the controller** (`docs/design/06-knowledge-graph-and-taxonomy.md`): S2 now carries four passes, with `_rescue_relation_endpoints` **first**, matching `PASS_REGISTRY`'s actual order rather than being appended at the end. | T1.24c flagged the diagram as one box short and correctly declined to edit `docs/design/`, which was outside its lane. Placement matters as much as presence: the pass runs before `_rescue_known_entities`, and a diagram implying it runs last would misdescribe the ordering contract T1.24a validates at import. |
| 2026-07-27 | T1.24f | 1 | **Unadjudicated gold/prompt disagreement recorded for the whole-chain F1 task.** `gold.json` types `gateway` as `service`, while the frozen extraction system prompt lists it among the `artifact` surfaces. No number moves on it today. | Surfaced by T1.24c while justifying a declined curated entry. It changes no measurement now, but it is a latent disagreement between the answer key and the instruction the model is given, and T1.24f is the task that judges the whole chain against that answer key. Resolving it belongs with whoever can re-adjudicate the gold set, not with a stage task. |
| 2026-07-27 | T1.04 | 1 | `backend/app/services/ml_seed.py` (`DEFAULT_ML_PROFILES`) is **orphaned**: no importer, and no `ml_profiles` table left to seed. Flagged, deliberately not deleted. | Already dead before T1.04 — the baseline dropped the table and T0.12c/T1.01 removed the models. T1.04 removed the last dead *reader* (`pipeline.py`'s `MLProfile` block), which makes the orphan visible but does not make deleting it T1.04's call. Note that `classification_ml.py` and `ml_runtime.py` are **not** orphaned: T1.04 made them genuinely reachable for the first time, since `classifier_kind='local'` had no selecting code path before it. |
| 2026-07-27 | T1.64 | 2 | **`gate.sh --full`'s Playwright step is vacuous today and must not be read as e2e evidence.** Measured by the controller after installing the missing browser: all **7** specs run and all **7** skip, and the step still exits 0. Two independent causes, both recorded here for T1.64. | First, the Playwright chromium binary was simply not installed on this machine, so every spec failed at `browserType.launch` — the `--full` gate had never actually executed a browser test. Installing it (`npx playwright install chromium`) turns 7 failures into 7 skips, not 7 passes. Second, every spec — the five that predate this wave and T1.43's two new ones — carries the same soft-skip (`test.skip(..., "not reachable without login")`), so with demo mode still the default and no authenticated session the whole suite asserts nothing while reporting green. This is exactly the silent-green failure mode invariant 14 exists to prevent, sitting inside the gate itself. T1.64 owns the suite and its database posture, and T1.58 owns the real auth path the specs need; until both land, a green `--full` is not e2e evidence and T1.50 must not cite it as such. |
| 2026-07-27 | T1.29a | 1 | **`app/services/pipeline.py` was edited despite the lane list excluding it** — one `filters: MemoryFilter \| None = None` keyword on `ProcessingPipeline.semantic_search`, forwarded to `HybridSearchService.search` and `PostgresVectorRepository.search`. No other line of that file changed. | `semantic_search` is the only route from `MemoryService` to either semantic implementation, so without the pass-through the pushdown is unreachable from any front door and the task lands inert. The brief's exclusion states its own rationale — "a sibling lane owns Phase 3 this wave" — and `semantic_search` is not Phase 3; it sits ~400 lines from `process_batch`, so the merge surface with T1.22 is disjoint. Recorded rather than silently taken, because the controller merges both lanes. |
| 2026-07-27 | T1.29a | 2 | **The Python project/status/archived drop in `MemoryService._matches_schema_v2_filters` deliberately stays, and removing it is T1.29b's job, not a leftover.** T1.29a's own Done-when says the predicates are "never applied in Python afterwards"; that is true of the semantic channel's rows and false of the result list as a whole. | `HybridSearchService.search` fuses the now-scoped semantic side with an **unscoped** keyword side, and T1.29b explicitly owns "the same predicates on `ts_rank` keyword search". Deleting the service-level drop before that lands would let a cross-project or superseded row enter through the keyword arm of RRF and reach `POST /memories/search` and `memory_search` — turning a pushdown task into a new leak. So the check survives as the keyword arm's filter only, with a comment saying so, and T1.29b removes it in the same commit that scopes that arm. |
| 2026-07-27 | T1.29a | 2 | **`ChatService._search_memories` is a fourth unfiltered consumer of the semantic channel, and no task owns it.** It calls `PostgresVectorRepository.search` with no project, status or archived scope and feeds the rows straight into the chat LLM's context, with no Python re-filter anywhere downstream — the same shape as the `memory_reason` leak doc 07 §7 names, on a surface that doc does not list. | Doc 07 §9 enumerates the read consumers as `memory_reason`, inject (F10), and the MCP/REST read surface; chat is none of those and was missed. Verified by reading the path, not inferred: `_search_memories` -> `_retrieve` -> `formatted_memories` -> prompt, with `is_archived`, `project` and `status` untouched at every hop. Left unfixed because `app/services/chat.py` is outside T1.29a's lane list and outside T1.29c's stated scope (`memory_reason` and code search). One line of wiring once an owner exists — the `filters` keyword it needs already lands with this task. |
| 2026-07-27 | T1.25 | 1 | **Stage 3 becomes three registry passes instead of one.** Doc 06 §4's S3 names `_rescue_relations`, subject-tracking and `_rescue_relations_replaces` as siblings, but only the first was a `PASS_REGISTRY` entry — the other two were nested calls at the bottom of the first. All three are now registry passes in the doc's order, each `(entities, relationships, content) -> relationships` and each gated on `relation_rescue`. The state the three used to thread between them (occurrence index, clause spans, dedup key set) is rebuilt per pass by `_rescue_context`; the recomputed `existing` set provably equals the threaded one, because every emitted triple is appended under exactly the key that was added. Registry count pinned 29 -> 31 in the same commit. | Two properties the doc asserts were not true of the nested form. `without(PASS_REGISTRY, name)` — the harness primitive that makes "a pass may be reordered or removed only against a measured F1 delta" actionable — can only drop a pass the registry names, so two thirds of Stage 3 could not be ablated or measured at all. And `ORDERING_CONSTRAINTS` cannot reference a pass that is not in the sequence, so the stage's internal order was convention rather than contract. Behaviour is unchanged and was proven so rather than argued: `clean_extraction` output was captured for all 36 corpus memories x both flag states before and after, and every entity, relationship, weight and properties dict is identical. |
| 2026-07-27 | T1.25 | 2 | **The F1 bench does not currently guard the `relation_rescue` layer — its measured delta is 0.000 on every dimension of both gold sets.** Ablated four ways on the 36-memory corpus: flag off, and each of the three passes dropped individually via `without`. All four give gold 0.940/0.970/0.895/0.921 and held-out 0.949/0.983/0.872/0.872 — bit-identical output, not merely equal scores. The layer emits 6 triples corpus-wide; 5 are killed downstream by the date/event gates and the 6th (`darkmem MENTIONS kafka`, e24) is a triple the LLM also emits, where the rescue only changes the surviving weight and provenance. **This is not a recommendation to remove it.** | The task's own Done-when reads "guarded by the F1 bench — reorder or remove only against a measured delta", and on this corpus that rule returns "no measured harm" for deleting the whole stage. That conclusion would be wrong: the layer's documented reasons for existing are cases the gold sets do not contain — Pattern D's file-relocation edges (six rounds of prompt patches failed to elicit them, doc 06 §4), and the wrong-direction-REPLACES fix doc 06 §4 spells out by name. Recorded so the next reader of that Done-when knows the number is zero for lack of corpus coverage, not for lack of value, and so G-B does not cite F1 as evidence for this stage. The real guard is now `tests/test_relation_rescue.py`, whose three invariant pins were each proven by breaking them on purpose. |
| 2026-07-27 | T1.25 | 2 | **Finding, not fixed — `_fan_out_coordinated` makes `clean_extraction` non-reproducible across processes.** It builds coordinated-subject groups as `list[set[str]]` and emits with `for member in g`, so Python's per-process string hash randomisation decides the order of the fan-out edges. Two runs of the same input in two processes produce the same triples in a different list order (observed on gold `e10` and held-out `h3`). Set contents, and therefore every F1 number, are unaffected. | Doc 06 §4 calls the post-processor deterministic and each pass a pure function, and doc 11's reproducibility contract seeds the LLM call so the same input yields the same JSON; a downstream pass reintroducing order nondeterminism undercuts both, and it defeats byte-level diffing as a regression technique — it is what made T1.25's own before/after equivalence check need an order-insensitive comparison. The fix is one word (`sorted(g)`), but `_fan_out_coordinated` is Stage 5 and Ruling 8 scoped T1.25 to Stage 3, so it is left for T1.24e. |
| 2026-07-27 | T1.13 | 1 | The four buffer thresholds (`buffer_claim_batch`, `buffer_max_attempts`, `buffer_claim_visibility_seconds`, `buffer_done_retention_hours`) land as the `buffer_flush` job's **`config_schema` fields**, which the JobRegistry persists in the `config` row `job:buffer_flush` under its `config` key — not as four standalone `config` rows and not in `FEATURE_FLAGS_DEFAULTS`. `buffer_settings()` in `app/services/buffer_flush.py` is the reader, merging DB values over the defaults the same way `get_feature_flags_dict` does. | Doc 05 §3/§3.1 requires them to be `config` rows and this is literally one, but it also inherits the machinery already built for per-job knobs: `set_config`'s type/min/max validation, the `PUT /api/v1/jobs/{key}/config` route, the generic settings UI, and the same per-job `asyncio.Lock` that guards a scheduled run. Four loose rows would have needed a second validation path and a second UI surface for the same four integers. `buffer_wait_timeout_seconds` (T1.14) is the odd one out — it is read on the request path rather than by the job — so T1.14 should decide its home on its own merits rather than assume this one. |
| 2026-07-27 | T1.13 | 2 | **`memory_buffer` rows that reach `error` have no triage surface yet.** T1.13 lands the producer (poison bounding, stale-claim reclaim, `last_error`) and a read helper (`stale_claims`), but nothing renders either. Doc 13 §6.1's buffer monitor is T1.61's, and doc 05 §3.1's "error rows are retained until resolved or explicitly forgotten from triage" has no resolve path anywhere. | Recording it because the retention rule makes `error` rows permanent by design: the sweep deletes only `done`. Without T1.61 (or some triage route) a poisoned capture accumulates silently and forever — bounded per row, unbounded in aggregate — which is the same shape of silent failure the bounding exists to prevent. T1.61 should treat `stale_claims` and the `error` status as its two required views, and whoever owns triage needs a resolve/re-buffer action, not just a list. |
| 2026-07-27 | T1.55 | 1 | **Ruling 3 resolved as the controller's steer: all eight `PURPOSES` render, the two Tier-C purposes (`synthesis`, `verification`) clearly labelled `inert` and naming their activation task (T3.02 / T2.26).** Not overturned — the codebase already had the identical honesty pattern in hand (`armStatus`/dormant w_* arms on the Flags tab, doc invariant 23), and hiding a seeded-but-undispatched purpose would read as "not configured", the same misreading a hidden zero-value arm would cause. The two inert cards are static (model/api_kind only, no Save button): neither the wire (`LLMConfigResponse` still declares six keys) nor any backend table carries them yet, so there is nothing live to bind in either mode. | Extending the wire schema to eight purposes would touch `backend/app/schemas/config.py` / `app/api/routes/config.py`, both outside this lane's file list and explicitly reserved ("retiring them is the contract task's call" per that schema's own comment). Rendering the two as static, clearly-inert cards satisfies the Done-when without that out-of-lane edit. |
| 2026-07-27 | T1.55 | 1 | **Found and deleted a genuine invariant-23 violation the brief's file list did not name: the entire pre-rebuild `frontend/src/features/pipeline/` directory** (`LLMProvidersPanel`, `LLMProfilesPanel`, `MLProfilesPanel`, `LLMPurposeCard`, `LLMProviderTestDialog`, `LLMPurposePromptEditor`, `AssistantServicesPanel`, `MaintenancePanel`, `PipelineSettingsPanel`, plus their six test files) — orphaned, unrouted (no route or component outside the directory imported any of them except `api-kinds.ts`, relocated to `features/setup/`), and wired to `/config/llm-providers`, `/config/llm-profiles`, `/config/ml-profiles` REST endpoints that no longer exist on the backend (T1.01 dropped them). Also removed the frontend hooks calling those dead endpoints (`use-config-api.ts`'s `useLlmProviders`/`useLlmProfiles`/`useMlProfiles` families and their types), the now-orphaned `use-pipeline-config.ts` (`usePipeline`, only consumer was the deleted `PipelineSettingsPanel`), and the demo `llmProfiles` fixture slice (`demo/data/llm-profiles.json`, `DemoStoreState.llmProfiles`, `useDemoLLMProfiles`) that fed only the deleted panels. | This is exactly what doc 13 §7 calls an invariant-23 violation, not merely dead UI: a provider/profile/ml-profile picker left in the source tree over a schema with no such tables, one HTTP call away from a 404 if anyone had wired a route back to it. T1.55's own Done-when ("Provider/profile/ml-profile UIs are deleted, not hidden") requires exactly this; the brief's file list evidently predates discovering this leftover directory (it was last touched only by repo-wide cosmetic sweeps, never by feature work), so deleting it is in scope rather than a lane violation. `frontend/src/hooks/api/use-config-api.ts` is touched as a direct, necessary consequence — it is the file whose exports made the dead panels reachable at all. |
| 2026-07-27 | T1.55 | 1 | **Consolidated three independent hard-coded copies of "which api_kind lacks an embeddings endpoint" into one canonical source, `frontend/src/features/setup/api-kinds.ts`'s `apiKindSupportsEmbedding`/`embeddingKindWarning`** (mirroring `backend/app/services/llm_quirks.py`'s `supports_embedding` table, T1.03). The duplicates removed: the demo LLM tab's own `embeddingKindWarning` (now delegates), the setup wizard's `StepLLM.tsx` `KIND_SUPPORTS_EMBEDDING` record, and the (now-deleted) `features/pipeline/api-kinds.ts` original. | Ruling 2 explicitly warns against a vendor-name comparison scattered in a frontend component; three separately-maintained copies of the same two-vendor fact is precisely that risk (a fourth vendor losing embeddings would need three coordinated edits to stay correct). No REST endpoint exposes vendor capability data to an authenticated (post-setup) caller — confirmed by inspecting every route under `app/api/routes/` — and adding one would touch `app/schemas/config.py`/`app/api/routes/config.py`, outside this lane. A single frontend-side mirror table, named and commented as tracking `llm_quirks.py`, is the same posture `api-kinds.ts`'s pre-existing `LlmApiKind` type already used for the vendor enum itself ("keep in sync"). |
| 2026-07-27 | T1.56 | 1 | **`backend/tests/test_setup.py` did not exist** (the setup wizard's existing coverage lives in `test_setup_route.py` / `test_setup_security.py`); created it fresh with the two re-run/idempotency tests T1.56's Done-when requires, rather than folding them into the differently-named existing file. | The brief's Verify command (`pytest tests/test_setup.py`) names a file that does not exist on this branch; creating it satisfies the command literally without touching or restructuring the two pre-existing, unrelated-named setup test files. |
| 2026-07-27 | T1.56 | 1 | **Fixed a real duplicate-primary-key bug in `setup_finalize`'s LLM block**: the purpose-row seed loop unconditionally `session.add()`-ed a fresh `LLMPurposeConfigRow` per `DEFAULT_PURPOSE_CONFIGS` entry, so any re-run against an instance whose `llm_purpose_configs` rows already existed (re-opened via clearing `admin_password_hash`, the only sanctioned re-open path per doc 18) raised a SQLAlchemy identity-key conflict rather than 500ing cleanly or overlaying. Changed to fetch existing rows first and update in place, inserting only for a purpose with no row yet — upsert, not insert. Verified as load-bearing: reverting the fix reproduces the exact failure (`test_setup_finalize_llm_reopen_is_idempotent` fails with the identity-key conflict) on the unmodified test; restoring the fix passes it again. | Doc 20 §10 / T1.01 make wizard re-run the supported upgrade path for an existing install, and Ruling 4 requires proving finalize-twice is safe rather than assuming it. The bug was latent (untested) rather than newly introduced — `test_setup_route.py::test_setup_finalize_with_llm` only ever calls finalize once. Also corrected a stale comment claiming the block "inserts the full default seed (DEFAULT_PROVIDERS + DEFAULT_PROFILES + DEFAULT_PURPOSE_CONFIGS)"; only `DEFAULT_PURPOSE_CONFIGS` was ever written to the database — the other two are pure-Python lookups for a default base_url and a matching params preset, never rows. |
| 2026-07-27 | T1.29c | 2 | **A live isolation leak with no owner, found by T1.29a and confirmed by the controller in the working tree.** `ChatService._search_memories` (`app/services/chat.py:254`) calls `vector_repo.search()` with **no project, status or archived predicate**, and line 218 feeds the result straight into the chat LLM's context. Archived, superseded and cross-project rows reach a user-visible answer today. Assigned to **T1.29c**, whose third Done-when is already "every channel now filters in SQL". | Doc 07 §9's enumeration of retrieval consumers omits this path entirely, which is why no task covered it. The more important half: **T1.35's probe must cover the chat path explicitly**. Its bar is zero unlabelled cross-project or superseded rows on *every* channel, and a probe built from doc 07 §9's list would have returned a clean zero while this leak was live — the gate passing for the wrong reason, which is worse than the gate failing. Distinct from T1.60, which labels cited rows; labelling a row that should never have been retrieved does not fix it. |
| 2026-07-27 | T1.29b | 2 | **T1.29a's service-layer Python filter drop deliberately survives, and T1.29b must delete it in the same commit that scopes the keyword arm.** Until then T1.29a's "predicates are never applied in Python afterwards" box is *qualified*, not met, and its report says so rather than claiming it. | Hybrid fusion still mixes in an unscoped keyword side, which is T1.29b's. Removing the Python filter before that arm is scoped would open a leak rather than close one — the pushdown would be real on the semantic channel while the keyword channel fed unscoped rows into the same fused result. Sequencing, not an oversight. |
| 2026-07-27 | T1.29a | 1 | T1.29a edited `app/services/pipeline.py` despite the brief's lane list excluding it — one `filters` keyword on `semantic_search`, forwarded to both branches. **Accepted by the controller.** | `semantic_search` is the only route from `MemoryService` to either semantic implementation, so without the forward the pushdown is unreachable and the task lands inert. The exclusion existed to keep Phase 3 single-owner during a concurrent wave, and this hunk is ~400 lines away from Phase 3. Recorded because the lane flagged it and offered the revert rather than assuming, which is the behaviour the lane rule wants. |
| 2026-07-27 | T1.21 | 2 | **Assigned: a DB failure in the Phase 3 entity-cache *lookup* still escapes `process_batch` as a raw exception** instead of degrading to per-memory statuses. Found by T1.19/T1.22's lane and correctly left unfixed as out of scope. | Same defect class T1.16 hardened for Phase 1, and the same class as T1.07's `UnboundLocalError` — the one a 909-green backend floor missed and only benchlib caught. Owner is T1.21 because it owns `derive_memory_failed_step` and the per-memory `pipeline_failures` row: an escaping exception means **no** per-memory row is recorded, so the failure is invisible to the triage surface rather than merely mislabelled. Symmetry would argue Phase 3's hardening belonged to T1.19, but reopening a done task to chase a pre-existing hole is worse than assigning it to the task owning the failure-state machinery. |
| 2026-07-27 | T1.19 | 1 | Phase 3 cache hit/miss counters **double-count across a rotation retry** — after drop-and-re-resolve they report *work performed*, not *names resolved*. Left as-is deliberately. | T1.19's Done-when asks for an observable hit rate, and the counter is honest about the work the phase actually did. Recorded so a later reader of a rotated batch's hit rate knows the denominator, and so nobody "fixes" it into under-reporting real embedding cost. |
| 2026-07-27 | T1.25 | 2 | **T1.25's "guarded by the F1 bench" Done-when is not satisfiable on the current corpus, and is recorded as qualified rather than met.** Measured by the lane and **independently re-measured by the controller** via direct `relation_rescue=True/False` ablation over both cached gold sets: on `gold.json` 25 of 26 memories are bit-identical and exactly **one** rescue-tagged triple survives (duplicating an LLM triple); on `gold_heldout.json` all 10 are identical and **zero** survive. Each of the three passes ablated individually gives the same result. | The guard the criterion names is structurally incapable of detecting the thing it guards, so a flat F1 across an ablation is evidence of *nothing measured*, not of *no regression*. Three consequences: **G-B must not cite F1 as evidence for Stage 3** (added to T1.50); **T1.24f owns closing it** and its "per-pass contribution recorded" box must record Stage 3 as **unmeasurable on this corpus**, not as *zero contribution* — different claims, only one true; and the layer was correctly **not** removed, since its documented reasons for existing (Pattern D relocation edges, the wrong-direction REPLACES fix) are cases neither gold set contains. No new gold-authoring task was created: T1.24f is Fable-tier and already owns per-pass evidence. |
| 2026-07-27 | T1.24e | 2 | **`_fan_out_coordinated` (Stage 5) iterates a `set` of strings, so `clean_extraction`'s output *order* varies between processes under hash randomisation.** Reproduced on gold `e10` and held-out `h3`. Resulting sets, and every F1 number, are unaffected. One-word fix (`sorted(g)`), routed to T1.24e as Stage 5's owner. | Larger than its size suggests: doc 17 §7 and `CLAUDE.md`'s Reproducibility contract exist so identical input reproduces identical output, and the seed forwarding is built to protect exactly that. A nondeterministic ordering downstream undermines the same property by a different route, and order-sensitive consumers — dedup tie-breaks, `canonical_map` construction — would surface it as a rare flake rather than a clean failure. Found by T1.25's lane, which correctly did not reach into another stage. |
| 2026-07-27 | T1.55 | 1 | The orphaned `frontend/src/features/pipeline/` directory is **deleted** — dead provider/profile/ml-profile UI wired to endpoints T1.01 removed. Its one live file (`api-kinds.ts`) was **moved** to `features/setup` and its single importer updated. Frontend test count drops **354 → 338**; the 16 removed tests covered the deleted dead code. | Verified by the controller before merge: `StepLLM.tsx`'s `api-kinds` import was the *only* reference into the directory from outside it, so the remainder was unreachable. Doc 13 §7 names a surviving profile picker over a schema with no profiles table as an invariant-23 violation rather than merely dead UI, which puts the deletion inside T1.55's remit even though the file list did not name the directory. Recording the test-count drop explicitly so a later reader does not read it as a regression. |
| 2026-07-27 | T1.61 | 2 | **No task in the graph exposes `memory_buffer` over REST, and T1.61's Done-when ("buffer monitor shows claimed, stale, and poison rows"; "a poison row is actionable") cannot be met with real data as a result.** T1.10 lands the table and T1.13 lands the flush job plus the read-only `stale_claims()` helper, but neither adds a route, and none of T1.08's three `/events` endpoints touch `memory_buffer` either. T1.61's own file list (frontend-only, `Not backend/`) and ruling 4 ("do not add a backend endpoint yourself") forbid this lane from closing the gap itself. Delivered instead: feed and day views are fully bound to real `/events`/`/events/calendar` (Done-when #1, met); the buffer monitor's demo-mode target design was corrected to the shipped semantics (`attempts` relabelled "claimed N× ", a distinct stale-claims list separate from poison, and working retry/forget actions on poison rows via the demo store) so Done-when #2/#3 are met **in demo mode only**; the real-mode branch (unreachable until T1.58 flips `DEMO`) renders an honest "no REST surface yet" staged state rather than fetching against a guessed contract. A follow-up backend task — a read route over `memory_buffer` (counts + `stale_claims()` + poison rows) plus retry/forget actions on a poison row — is needed before the monitor can go fully live. | T1.13's own amendment row (above, 2026-07-27, tier 2) already flagged that error rows have no triage surface and named T1.61 as the owner, but neither that row nor T1.61's brief anticipated that closing it needs a backend change, which this lane's scope explicitly excludes. Recording as tier 2 because it changes what a future task must still do — add the missing route — not as a tier 3, since no design doc is contradicted: doc 13 §6.1's own invariant-23 language ("a monitor for a table that does not yet write would render an empty panel that reads as either broken or as claiming a shipped capability") is exactly the reasoning applied here to keep the real branch honestly staged rather than fabricating a fetch. |
| 2026-07-27 | T1.13b | 2 | **New task added — the plan had a signal with no wire.** T1.13 produces buffer state (claimed, stale, poison/`error` with attempt counts) and T1.61 renders it, but **no route anywhere exposes `memory_buffer`** — confirmed by the controller: `backend/app/api/routes/` contains only the capture write path, and the sole `buffer` mentions are two docstrings. T1.61's buffer monitor therefore binds demo data only, and its "poison row is actionable" box cannot be met with live state. Added T1.13b (Sonnet, M) between T1.13 and T1.61's live binding. | Principle 10 inverted: doc 20 forbids a Phase-1 signal with no Phase-1 surface, and this is the mirror case — a committed surface (doc 13 §6.1 names the buffer monitor as *the* place poison rows appear) with no signal to read. Found by T1.61's lane, which correctly reported it rather than adding a backend route from a frontend-scoped lane while four backend lanes were running. The task explicitly requires reusing T1.13's tested-but-uncalled `stale_claims()` helper rather than reimplementing the staleness predicate, because two definitions of stale will drift and the UI's would be the one users believe. |
| 2026-07-27 | T1.61 | 1 | T1.61's buffer-monitor Done-when boxes are recorded **met in demo mode only**, pending T1.13b. Feed and day-view live binding are fully delivered and unaffected. | Honest scoping rather than a claimed box: the surface, its states and its actions are built and tested, and the moment T1.13b lands they bind to real rows. Recording it so the row does not read as fully live when half of it is waiting on a route that did not exist when the task was written. |
| 2026-07-27 | T1.29b | 1 | **Touched `backend/app/services/graph.py`, which the lane's file list does not name**, to wire `GraphService.get_memory_context` to the newly scoped traversal (it derives the scope from the seed memory's own project). Repository-layer change alone would have been correct and inert. | `get_memory_context` is the only live graph read path with a derivable project, and it leaked: an entity asserted by memories in two projects hands back the foreign project's memories through `entity.memory_ids`, and `get_relations_between` returned edges no in-project memory asserts. Leaving the traversal scope-capable but uncalled would have reproduced exactly the "qualified, not met" outcome Ruling 1 exists to prevent. No sibling lane in this wave touches the file (T1.20 is `pipeline.py`, T1.14 `wait_process`, T1.61 frontend). |
| 2026-07-27 | T1.29b | 2 | **`ix_memories_project_live` — the one index doc 04 §10 says the pushdown "strictly requires" — is not reachable from the pushdown's own SQL, and no plan uses it.** It is partial on `WHERE status = 'active' AND is_archived = false`; `MemoryFilter.where_sql` renders status as `status::text = ANY(CAST(:flt_statuses AS text[]))` with the array as a bound parameter, so the planner cannot prove the query predicate implies the index predicate and never considers it. Measured, not inferred: the keyword channel plans to `ix_memories_fts`, the scope alone to `ix_memories_project` / `ix_memories_is_archived`, and the graph scope to `memories_id_project_key`. | Recorded so nobody cites that index as evidence the pushdown is indexed — it is indexed, but by three other indexes. Not fixed here: making it reachable means either inlining a literal `status = 'active'` into the SQL string or comparing against the enum type, and the text comparison is deliberate (T1.29a chose it so an unrecognised status is a no-match instead of a query-aborting `InvalidTextRepresentation`, pinned by `test_unknown_status_matches_nothing`). Whoever revisits doc 04 §10 should decide whether the index earns a shape change or should be dropped. |
| 2026-07-27 | T1.29b | 1 | A GIN index buffers fresh entries in a pending list, and the planner charges a scan of the whole list — so after a bulk insert inside a test transaction `ix_memories_fts` looks arbitrarily expensive and is never chosen, whatever the row count. Any future `EXPLAIN` test over `search_vector` must call `gin_clean_pending_list('ix_memories_fts')` before `ANALYZE`, or it is measuring the fixture. | Cost two wrong diagnoses before it was found: at 400 and at 5000 seeded rows the plan picked `ix_memories_is_archived` and `ix_memories_project` respectively, which reads as "the FTS index is not eligible" rather than "the statistics are not settled". Recorded because the same trap sits in front of every later index-plan claim on this table, including T1.35's probe. |
| 2026-07-27 | T1.14 | 2 | **The front-door cutover (Ruling 1) landed as directed**: `POST /memories`, `POST /memories/batch`, MCP `memory_add`, `memory_batch_add` are now buffered by default (202 accept, `CaptureAck`), with `wait_process=true` as the opt-in synchronous escape returning the full processed body (201) once it settles in time. `POST /memories/capture(/batch)` and MCP `memory_capture`/`memory_capture_batch` (T1.12's additive doors) are **removed** — folded back into the four canonical doors, closing the two-door capture surface T1.42d's parity audit would otherwise have flagged. `MemoryService.accept_capture`/`accept_capture_batch` are gone too, merged into `create_memory`/`batch_create_memories`. | Doc 05 §2.2 concedes "today every capture is effectively `wait_process=true`" only until this lands; T1.13 (the flush) and this task (the sync escape) are exactly the two preconditions the T1.12 amendment log named. `MemoryService`'s prior direct-`process_batch` dispatch is retired in favour of always writing the buffer row first and, only on `wait_process`, driving that row's own flush through `buffer_flush.flush_claimed`/`claim_specific` — the identical `FOR UPDATE SKIP LOCKED` claim T1.13's scheduled job uses (proven by a mutation test: removing the clause turns an immediate skip into a 12s block). |
| 2026-07-27 | T1.14 | 1 | **Two SQLAlchemy identity-map staleness bugs found and fixed while building `wait_process`'s single-session drive.** (1) The claim's raw-SQL `UPDATE` and `materialize()`'s enrichment write bypass the ORM unit of work, so a plain re-`select` on the same session serves the caller's own stale, pre-flush copy of the row (`expire_on_commit=False`); fixed with `execution_options(populate_existing=True)` on the final read in `MemoryService._capture_batch`, scoped to only the ids this call just settled — a blanket `session.expire_all()` was tried first and rejected, since it also invalidates any unrelated object the *caller* is still holding a plain (non-awaited) reference to, raising `MissingGreenlet` on next access. (2) `wait_process.drive()`'s own claim/replay must run through the *same* session the caller's buffer write used (never a second connection), via a `_ReuseSessionFactory` adapter (`buffer_flush.as_session_factory`) that lets the identical `_claim_and_prepare`/`_replay` code the scheduled job uses operate over one caller-owned session instead of a session_factory. | Neither bug is hypothetical: (1) reproduced directly (a `RecordingPipeline` capture's `CaptureResult.memory` silently missing its own committed enrichment) and (2) is what makes `wait_process` usable from a single HTTP/MCP request session at all rather than needing its own dedicated session_factory wiring at every call site. Recorded because both are the kind of silent-drift failure this corpus exists to catch, and neither is named in doc 05 §2.2's text. |
| 2026-07-27 | T1.14 | 2 | **Found, not fixed: `frontend/src/hooks/api/use-memory-api.ts`'s `useCreateMemory` (consumed by `CreateMemoryDialog`) calls `POST /memories` and types the response as the full `Memory`, with no `wait_process` param.** After this cutover that call now gets the buffered `CaptureAck` (202, `{id, status}`) by default, not the created memory. The dialog itself only reads the mutation's `isPending`/`isError` state (never the resolved body) and relies on `invalidateQueries(["memories"])` to refresh the list, so nothing crashes — but the immediate post-create refetch races the buffer flush (default every ~5s), so the just-created memory can be briefly absent from the list the toast just said was created. Left unfixed: `frontend/**` is outside this lane's file list (backend-only lane, T1.14 brief). | A real, silent UX regression this cutover causes, not merely a hypothetical one — verified by reading `create-memory-dialog.tsx` and `use-memory-api.ts` directly, not inferred. The fix is small (add `?wait_process=true` to `useCreateMemory`'s `apiFetch` call, or accept the async gap and shorten `buffer_claim_batch`'s cadence) but is a frontend-lane change with its own gate (`npm run typecheck && npm test && npm run build`), which this backend-only lane does not run. Needs an owner before G-B, since doc 05 §2's "genuinely 202" contract is exactly what this dialog was built assuming synchronous creation instead. |
| 2026-07-27 | T1.58 | 2 | **Blocking precondition recorded: the frontend create path is now type-wrong against the real backend.** T1.14 flipped `POST /memories` to a buffered 202 ack, but `frontend/src/hooks/api/use-memory-api.ts` still calls `apiFetch<Memory>("/memories", ...)` — typed to receive a `Memory`, with no `wait_process` parameter. Confirmed by the controller. **T1.58 may not claim "real mode is the default" while creating a memory through the UI is broken.** | Masked today only because demo mode still defaults on, so the real endpoint is never called — and T1.58 is precisely the task that removes that mask. Flagged by T1.14's lane, which correctly did not reach into the frontend from a backend-only lane. The ack's wire shape is T1.42a's envelope work; the binding fix is T1.58's. Recording it against T1.58 because that is where it becomes user-visible rather than theoretical. |
| 2026-07-27 | T1.29b | 2 | **`ix_memories_project_live` is dead weight as currently shaped.** Doc 04 §10 calls it "the one index change the SQL needs", but it appears in **no** query plan: the parameterised `status::text = ANY(...)` form prevents the planner proving the partial-index predicate. Logged, not fixed — the text comparison is deliberate and pinned by a test. | Box 1 ("query plans confirm index use on both") is still genuinely met, by real `EXPLAIN` output — a Bitmap Index Scan on `ix_memories_fts` for the keyword channel and index scans throughout the graph traversal. The finding is narrower and worth resolving deliberately: either reshape the SQL so the partial predicate is provable, or admit the index is not earning its keep and drop it. Carrying an index the plan never uses while a doc calls it a strict requirement is the kind of divergence that reads as covered when it is not. |
| 2026-07-27 | T1.35 | 1 | **Environment fact for the isolation probe, measured by T1.29b's lane:** a GIN pending list makes `ix_memories_fts` look arbitrarily expensive immediately after a bulk insert, so the planner picks `ix_memories_is_archived` at one fixture size and `ix_memories_project` at another. `gin_clean_pending_list('ix_memories_fts')` before `ANALYZE` is what makes a plan assertion real. | Recorded because T1.35 is a measurement task whose result is a gate number. An index-plan assertion written without this measures its own fixture rather than the query, and would flip between fixture sizes for reasons that look like real plan instability. |
| 2026-07-27 | T1.29b | 1 | T1.29b edited `app/services/graph.py`, outside its brief's file list, so `get_memory_context` derives its scope from the seed memory's project. **Accepted by the controller.** It was leaking foreign-project neighbour memories through a shared entity's `memory_ids`. | Squarely inside the task's own second Done-when box ("graph traversal cannot cross a project boundary mid-walk"), and the exact mechanism the brief's Ruling 3 warned about: entities are **not** memory-scoped, so project scope on the graph side is a property of the memories asserting an entity rather than of the entity row. The file list was incomplete, not the edit wrong. Lane flagged it as revertable rather than assuming. |
| 2026-07-27 | T1.30 | 1 | The two-class model landed in a **new module `backend/app/services/rank_fusion.py`** rather than inside `hybrid_search.py`, and `rank_fusion_factor` **moved out of `app/services/confidence.py`** (its four tests moved with it, out of `tests/test_schema_v2_metadata.py` and into the new `tests/test_rrf_fusion.py`). Both files sit outside the brief's file list. | Doc 07 §3's separation is a property of *where the two classes live*, not only of what they compute. `hybrid_search.py` is one ranked-list producer; PPR, dual-level, facts and articles are named as future producers of the same fusion, so the fusion cannot be owned by one channel. And `rank_fusion_factor` stopped being a confidence helper the moment it composed importance/heat/recency — leaving it in `confidence.py` would have made three of its four arms look like confidence concerns. `confidence.py` keeps `estimate_confidence` and the constants and now imports nothing new. |
| 2026-07-27 | T1.30 | 1 | **`ProcessingPipeline._apply_confidence_weighting` keeps its now-inaccurate name, deliberately.** It applies the composed multiplier, not confidence alone. **T1.31 should rename it** (`_apply_rank_fusion_factor`) in the same commit that wires the arms. | The name is quoted in the repo-root `CLAUDE.md` ("used by `_apply_confidence_weighting` when `confidence_rank_gamma > 0`"), which is outside this lane's file list and outside any lane's this wave. Renaming the method without that line would leave the business-logic baseline pointing at a symbol that no longer exists — worse than a stale name. The rename is a two-line change once an owner can touch both. |
| 2026-07-27 | T1.31 | 1 | **How to assert "ranking is bit-identical with the arms at zero vs absent", concretely.** An arm at weight 0 returns exactly `1.0` from `arm_factor`, and `x * 1.0` is exact in IEEE-754, so the composed factor is bit-identical — assert with `.hex()`, not `pytest.approx`. `tests/test_rrf_fusion.py::test_arms_at_zero_are_bit_identical_to_arms_absent` already pins it at the factor level; T1.31 owes the same at the **ranking** level (same row order and same score bits through `semantic_search`) once the three flags exist in `FEATURE_FLAGS_DEFAULTS`. | Recorded because an approx-based version of this test passes even when an arm is quietly non-inert, which is the exact failure T1.31's box exists to catch. `test_future_arms_are_zero_weighted_by_default` reads `FEATURE_FLAGS_DEFAULTS` through `.get(flag, 0.0)`, so it holds both before T1.31 adds the flags and after — it does not need editing, only the ranking-level twin added. |
| 2026-07-27 | T1.29c | 1 | Touched five files the lane list does not name: `app/schemas/reason.py`, `app/api/routes/memories.py` and `app/api/mcp/server.py` (a `project` argument on both `reason` front doors), `app/repositories/graph.py` (a `scope` argument on `get_entities`, matching its neighbour-walk siblings), and `tests/test_services_reason.py` (a stale `semantic_search` stub signature). | A scope the service accepts and no front door can set is a leak that is merely harder to reach, and invariant 17 forbids a behaviour existing on one door and not the other. `get_entities` is how chat resolves an `@mention`; leaving it unscoped would have closed chat's memory arm while its entity arm still handed the model a foreign project's graph. The stub predates the `filters` keyword T1.29a added and broke the floor on signature alone, not behaviour. |
| 2026-07-27 | T1.29c | 2 | **Doc 07 §9's consumer enumeration is incomplete, and a T1.35 probe built from it would return a clean zero over live leaks.** Code-derived inventory in the T1.29c report. Three memory-content channels the doc omits: `ChatService._retrieve` (fixed here), `GET /api/v1/vectors/projection` (`get_all_vectors` — up to 5000 rows with content snippets, **no project, status or archived predicate**), and `memory_find_duplicates` / `GET /memories/{id}/duplicates` (`find_similar` is called with no `filters`, and its rows carry the payload content). | The projection route and the duplicates probe are the two that matter for the gate: both are unscoped by construction and both return memory content to a caller. The duplicates probe may be deliberately unscoped — the `MemoryFilter` docstring says the dedup and crossref probes want every candidate regardless of lifecycle — but the same function now serves a user-facing tool, so the choice needs an owner rather than an inherited default. T1.35's probe must be built from the code, never from the doc's list. |
| 2026-07-27 | T1.29c | 2 | **Found, not fixed: `GraphService._fetch_neighbor_memories` applies `project` and `is_archived` but never `scope.statuses`, so a superseded neighbour still reaches `get_memory_context`.** `_project_scope` builds `MemoryFilter(project=project)` with `statuses=None`, so no graph arm — neighbours, relations or the traversal — carries a status predicate. | Left to its owner deliberately. T1.29b chose project+archived for the graph channel and reversing that shape from a sibling lane would change the entity and relation arms too, where "an entity asserted only by a superseded memory" is a genuine design question rather than an oversight. Doc 07 §7's "the pushdown's default excludes non-active rows from the default view" argues it should be closed; recording it so the graph channel is not counted as fully scoped in a gate claim. |
| 2026-07-27 | T1.29d | 2 | **New task — doc 07 §7/§9's channel enumeration is demonstrably incomplete, and three more live leaks were found.** T1.29c's code-derived inventory (required by its brief precisely because the doc's list had already missed `ChatService`) surfaced: `GET /api/v1/vectors/projection`, authenticated, up to **5000** rows carrying content snippets, with **no** project/status/archived predicate; `memory_find_duplicates`, calling `find_similar` unfiltered with payload content on its rows; and `GraphService._fetch_neighbor_memories`, which scopes project and archived but **never status**, so superseded neighbours still reach `get_memory_context`. Controller verified the projection endpoint in the tree. | This is the second time the doc's consumer list has proven wrong, and it is the reason T1.29c's brief demanded an inventory derived from code rather than from the doc. **T1.35's bar is zero leaked rows on every channel, so a probe built from the doc's list would return a clean zero over three live leaks** — the gate passing for the wrong reason. Made a task rather than folded into T1.35 because runbook §2 keeps measurement design and measurement plumbing separate: the probe must not be written by the same pass that fixes what it measures. |
| 2026-07-27 | T1.29c | 1 | **Controller ruling on `reason`'s default scope: `project=None` meaning "every project" is correct and stands.** T1.29c asked whether doc 07 §7 requires a default project scope rather than merely the ability to scope. | It matches the search surface, which is the consistency that matters: a channel that silently defaulted to a narrower scope than its sibling would surprise every caller and would be discovered as missing results rather than as a policy. Doc 07 §7's actual complaint about `memory_reason` was that it could not scope **at all** and leaked superseded and archived rows unconditionally; both are now unconditionally scoped and project is scopeable. The leak is closed; the default is a separate question and the consistent answer is the right one. |
| 2026-07-27 | T1.29c | 1 | Fixed a floor failure not of this task's making: `tests/test_services_reason.py`'s pipeline stub predated the `filters` keyword T1.29a added and raised `TypeError` on signature alone. | Recording it because it was latent across a merge — the stub was signature-incompatible from the moment T1.29a landed, and it surfaced only when this lane exercised that path. A stub that mirrors a production signature without being pinned to it will drift again; worth remembering when the next keyword is added. |
| 2026-07-27 | T1.13 | 2 | **Finding I-1 fixed on both halves, as directed.** `_replay` kept one try/except around `materialize` + `process_batch`, so a capture that could not be written at all settled every row claimed with it — reproduced first as a failing test (1 poison + 2 innocent → 3 `error` rows sharing one untriageable `DBAPIError`) before any fix. Now `_materialize_isolated` keeps the batch call for throughput and falls back to one row at a time when it raises, so the offender settles alone with a `last_error` naming the real failure; and `MemoryCreate`/`MemoryUpdate` validate tag length against the `tags` columns at the door, so the poison never enters. `tag_category` moves to `app/models/memory.py` as the one derivation the door and both tag writers share. The batch handler is kept for `process_batch` itself, which is batch-wide by construction: the pipeline swallows per-memory failures into `statuses`, so an exception escaping it is the embedder, not one capture's data. | The reviewer's driver, reproduced. Door-side validation alone would leave the flush undefended against rows from any other writer (the premise of the `detach` rejection path); per-row isolation alone would keep 202-acking captures that can never be materialised. Five mutations were made and each failed the intended test: removing the row-at-a-time fallback, removing the attempt refund, removing the claim shrink, treating a lone-row deadline as batch-wide, and deleting the tag validator. |
| 2026-07-27 | T1.13 | 2 | **Finding I-3: mechanism chosen is a flush-owned deadline plus a refund bounded by an adaptive claim shrink — not a raised ceiling and not a capped batch max.** `flush_once` now runs `process_batch` under `BUFFER_FLUSH_DEADLINE_SECONDS` (the registry ceiling less a 10s settle margin), so the flush settles its own rows instead of being cancelled with them left `claimed` for a whole visibility window. A deadline is treated as nobody's failure: the batch returns to `pending` with its claim-time attempt refunded and a per-row `flush_timeouts` counter incremented in the buffer's own bookkeeping metadata, and the next claim is `buffer_claim_batch >> head.flush_timeouts`. **The refund cannot livelock**, because once the shrink puts a row in a batch of one the whole deadline was its to use and a timeout there settles through the ordinary attempts ladder into `error`. | The two options the brief offered are each insufficient alone. Refunding timeouts unconditionally reintroduces exactly the infinite retry the claim-time increment exists to prevent (a row that hangs forever also head-of-line-blocks the tier). Capping `buffer_claim_batch`'s schema max against the ceiling needs an invented per-row latency constant and still only moves the cliff — a slow enough model overruns any fixed batch. The shrink is adaptive, needs no new constant and no schema change, and converges on a batch the deployment can actually carry; it also composes with I-1, since both reduce to "settle the smallest unit that can be blamed". Cost recorded honestly: under a uniformly too-slow deployment rows still reach `error`, but only one at a time and only after each has had the entire deadline alone, never as a co-claimed batch. |
| 2026-07-27 | T1.13b | 1 | **Route named `/api/v1/memory-buffer`**, table-name-kebab-cased after the `pipeline_failures` → `pipeline-failures` precedent, rather than a plural collection noun. **REST single door, no MCP twin**, with the reason recorded for T1.42d's parity audit in the router docstring: this is an operator's view of the ingest tier's own plumbing (claim leases, worker identities, attempt counts), not an agent capability, and a delete over buffered captures does not belong on the unauthenticated local MCP door. Two new `EVENT_TYPES` values, `buffer_requeued` and `buffer_discarded`, journal under `object_type='memory'` keyed on the pre-minted memory id. | Taxonomy-first, per `app/services/events.py`'s own convention: the values land in the closed vocabulary before an emitter ships them. Keying the journal on the pre-minted memory id rather than inventing a `buffer` object type keeps a discarded capture's record on the timeline of the id its caller was already handed by the 202. |
| 2026-07-27 | T1.13b | 1 | **Found, not fixed (frontend is out of lane): T1.61's demo contract disagrees with this route on two points.** `frontend/src/demo/types.ts`'s `DemoBufferRow` uses camelCase keys (`maxAttempts`, `lastError`, `claimedAt`) while the route returns the codebase-standard snake_case, so the live adapter needs a mapping layer; and its `retryBufferRow` comment says a retry leaves attempts untouched, whereas T1.13b's Done-when says a requeue resets them — the route implements the task text. | Reported rather than edited: T1.61 is landed and `frontend/` belongs to no lane this wave. Both are adapter-level, not shape-level: every field the demo monitor renders (`staleClaims`, `poisonRows`, the four counts, the two actions) has a live source now. |
| 2026-07-27 | T1.61 | 2 | **T1.61's buffer-monitor adapter disagrees with T1.13b's actual route on two points and must be reconciled before its boxes can be called live.** (a) The demo contract uses **camelCase** keys where the route returns **snake_case** — and snake_case is the house style, since `CLAUDE.md` records the REST and websocket payloads still reading `llm_*`. (b) A demo comment says a retry leaves `attempts` untouched, where T1.13b's task text says a requeue **resets** them; T1.13b implemented the task text. | Found by T1.13b's lane, which implemented the specified contract and correctly left the frontend alone rather than bending the backend to a fixture. This is the failure mode a demo default hides: both sides pass their own tests while disagreeing, and the mismatch surfaces only when T1.58 flips demo off — as an empty or wrongly-rendered monitor rather than as an error. T1.61's boxes stay recorded as demo-only until the adapter is reconciled. |
| 2026-07-27 | T1.13 | 1 | I-3 resolved with a **flush-owned deadline plus an attempt refund bounded by an adaptive claim shrink**, rather than either option the brief listed alone. Residual, stated rather than hidden: a uniformly too-slow deployment still errors rows — but one at a time, and only after each has had the whole deadline to itself. | The brief offered two mechanisms and the lane took neither in isolation, which is the right instinct: refunding attempts alone lets a genuinely poisonous slow row retry forever, and shrinking the batch alone still burns attempts on the survivors. Recording the residual because a bounded, visible degradation is an acceptable answer and an unstated one is not. |
| 2026-07-27 | T1.13b | 1 | Two files touched outside the brief's list, both accepted: two entries added to `EVENT_TYPES` in `app/services/events.py`, and two call sites in `app/repositories/relational.py` redirected through a shared `tag_category()`. | The first is forced by design — `EVENT_TYPES` is a **closed** vocabulary (doc 04 §8.1) that warns rather than rewrites on an unknown value, so journaling a new action without adding it would log a warning on every requeue. The second stops the door's new tag validation and the tag writers keeping two independent notions of category, which is the same drift argument that put `stale_claims()` reuse in the task text. |
| 2026-07-27 | T1.15 | 1 | **The repository hint is extracted and gated at accept, not at flush** (Ruling 4's explicit choice). `MemoryService._capture_batch` calls `repo_provision.handoff_capture_hint` after the buffer rows are enqueued and before the capture's commit; `backend/app/services/buffer_flush.py` is **untouched** and the sibling lane fixing `flush_once` needs no hook for this. | Three reasons, in order. (1) Doc 18 §6's own sequence diagram puts the gate at *Capture*, before the memory exists, and doc 05 §2.4 says capture "owns only the validate-and-enqueue hook". (2) Accept is the one place every front door already funnels through (REST `POST /memories` + `/batch`, MCP `memory_add` + `memory_batch_add`), so REST and MCP get one gate rather than two, and a `wait_process` caller cannot get a different provisioning outcome from a buffered one. (3) The handoff writes then commit in the **same transaction as the buffer row the caller is acked for** — the registry row and the refusal event become durable exactly when the capture does, instead of up to a flush cadence later. The cost is one config-row read and pure string parsing per batch: no network call, no subprocess, nothing that would make accept slower in the way Ruling 3 exists to forbid. |
| 2026-07-27 | T1.15 | 1 | The gate refuses two shapes doc 18 §6 does not enumerate: a hint carrying an **explicit port** (`https://github.com:8443/org/repo`) and a **schemeless** hint (`github.com/org/repo`). Both return their own rejection reason rather than falling through to `not_allowlisted`. | Fail-closed reading of the pattern language doc 18 §9 fixes ("hosts with optional `*.` subdomain wildcard and optional path prefix, nothing more"). A pattern cannot name a port, so a port cannot be allowlisted — and a port swap on an allowlisted host reaches a service the operator never named, which is the SSRF the gate exists to stop. A schemeless hint's transport would have to be *guessed*, and guessing a transport for attacker-supplied text is the wrong direction to guess in; the scp-like `git@host:path` form is the one schemeless shape doc 18 explicitly normalises, and it is accepted. |
| 2026-07-27 | T1.15 | 2 | **The Tier-C executor for auto-provision is the existing `repo_sync` job, not a new one.** Capture's queue entry is the `repositories` row itself: `url` = the gate's *rebuilt* remote, `auto_sync=true`, `status='queued'`, plus the `project_repositories` association with `added_from='memory_hint'`. `repo_sync` filters on `auto_sync` and `CodePipeline.run` → `RepoManager.pull_repo` clones a working dir that does not exist yet, so the row drains without new machinery. | Doc 10 §5 already fixes the default-options set for an auto-registered repo as `auto_sync=true`, `enrich_symbols=false`, `generate_wiki=false`, **"at the standard `repo_sync` cadence"** — so a second job would have duplicated a Tier-C loop the plan already named. Recorded as Tier 2 because whichever task owns doc 10's F11 *execution* needs to know the queue shape is a `repositories` row and not a separate work table, and must not re-register a `repo_autoprovision` job beside it. Note the capture path deliberately does **not** call `RepoManager.create`: that method spawns `_clone_in_background` as an asyncio task, which would clone off a capture. |
| 2026-07-27 | T1.15 | 2 | **Found, not fixed: the `repo_allowlist` config row has no editing surface.** `app/api/routes/config.py` exposes per-concern routes (`/llm`, `/feature-flags`, `/system-prompts`, `/repos-path`, `/theme`) and no generic key/value PUT, so an operator can only opt into auto-provision by writing the `config` row directly against Postgres. | Doc 18 §6 makes clearing the allowlist "the global kill" and §11 requires the repo allowlist to be a `config` row **"changeable from the UI without redeploy — never env-var security policy"**. The gate itself is correct and inert-by-default either way, so this is not a security hole; it is a shipped feature the operator cannot reach. Needs an owner (a `GET`/`PUT /config/repo-allowlist` pair plus its settings surface) before G-B can claim doc 18 §6 end to end. Left unfixed here because the route plus its frontend surface is a separate lane with its own gate. |
| 2026-07-27 | T1.07 | 2 | **Found, not fixed: `backend/tests/conftest.py`'s `restart_savepoint` listener makes every `record_event` call log `events: failed to journal` in the test suite** (6 occurrences in `test_events_writer.py`, 14 in `test_api/test_capture.py`) even though every row lands and every assertion passes. The listener calls `session.begin_nested()` from `after_transaction_end`, which SQLAlchemy refuses while the ending `begin_nested()` context manager is still unwinding (`InvalidRequestError: Can't operate on closed transaction inside context manager`); `record_event`'s own `except Exception` then swallows it. | A journaling failure and a harness artifact are currently **indistinguishable in test logs**, which is the exact observability the T1.07 writer's never-raise design depends on to "degrade loudly". Any future test asserting "nothing failed to journal" would be unwritable, and a real partition or constraint failure would read as more of the same noise. Found while building T1.15's handoff, whose own savepoint hits the identical listener; the handoff was restructured so its return value survives the artifact, but the underlying listener is T1.07's writer and the shared conftest, neither of which is this lane's file. |
| 2026-07-27 | T1.13 | 2 | **Found, not fixed: `_CLAIM_SQL` does not enforce `buffer_claim_batch`.** The claim renders its `LIMIT ... FOR UPDATE SKIP LOCKED` sub-select as a plain `UPDATE ... FROM (subquery)`. When the planner puts that sub-select on the **inner** side of a nested loop with no `Materialize` above it, the sub-select is re-executed once per outer row; each re-execution skips the rows this same command already updated (`TM_SelfModified`) and returns the next pending row, so the statement claims **every** pending row regardless of `LIMIT`. Reproduced deterministically in psql on PG 17.10 — `ANALYZE` an empty `memory_buffer`, insert 3 rows, run the claim with `:limit=1`, get `UPDATE 3`. The trigger is a `memory_buffer` whose heap has pages but whose `reltuples` is 0, which is exactly what autovacuum records after the buffer drains — its normal steady state. Verified fix (applied, measured, reverted, **not** committed): wrap the sub-select in `WITH c AS MATERIALIZED (...)` so it is evaluated once; the same hostile plan then yields `UPDATE 1`. | Not a test artifact and not this lane's file. `buffer_claim_batch` is silently unenforced, and `claim_limit`'s deadline-halving valve — the fix for the Fable review's finding I-3 — is defeated with it: it computes a smaller limit that the SQL ignores, so one `process_batch` call receives the entire backlog and the batch that cannot finish inside the ceiling marches the whole healthy backlog into `error`, which is the exact failure I-3 exists to prevent. This is also the cause of the floor's intermittent `test_buffer_flush.py` (5 tests) and `test_wait_process.py::test_claim_specific_skips_a_locked_row_rather_than_waiting_on_it` failures — measured at 5 failing runs in 18 loaded floor runs, and reproducible on demand by simulating an autovacuum ANALYZE of a drained `memory_buffer`. `claim_specific`, `_RECLAIM_SQL` and `_SWEEP_DONE_SQL` share the shape but carry no `LIMIT`, so they are correct today; they would acquire the same defect the moment one gains a bound. |
| 2026-07-27 | T1.29b | 1 | `test_graph_walk_can_use_indexes_on_every_join` now sizes its fixture so `project = 'alpha'` is genuinely selective and `ANALYZE`s the three tables the walk touches, before asserting the plan. Assertions unchanged. | On three memories the scope matched nearly the whole table, leaving `memories_id_project_key` and `ix_memories_project` costing the same; the planner broke the tie on `memories`' physical page count, which an earlier bulk-inserting test in the same session sets and this test cannot control. Measured over the cross-product of four statistics states each for `memories` and `entities`: 4 of 16 failed before, 16 of 16 pass after. Making the plan deterministic was preferred over weakening the assertion so the task's "query plans confirm index use" box keeps meaning what it says. |
| 2026-07-27 | T1.07 | 1 | **Resolves T1.07's own "found, not fixed" row above.** `backend/tests/conftest.py`'s `restart_savepoint` listener and its manual `connection.begin_nested()` are removed; `tests/test_harness_savepoint.py` pins the behaviour. | The listener is SQLAlchemy 1.x's recipe and is redundant on 2.0.51, where the default `join_transaction_mode="conditional_savepoint"` already runs a session bound to an in-transaction connection inside its own SAVEPOINT — verified by deleting the listener and observing isolation hold. It was not merely redundant: it fired while an application `session.begin_nested()` was unwinding and the `InvalidRequestError` it raised was reported by `record_event` as a journal failure on every call, so `test_record_event_swallows_a_real_db_failure` was passing on harness noise rather than on the failure it induces. Both halves proven by mutation. |
| 2026-07-27 | T1.13 | 1 | **`_CLAIM_SQL` did not enforce `buffer_claim_batch` at all**, and the claim's row set is now `WITH c AS MATERIALIZED (...)` rather than a plain sub-select. As a sub-select the planner may place the `LIMIT ... FOR UPDATE SKIP LOCKED` scan on the inner side of a nested loop and re-execute it per outer row; each re-execution steps past the rows the same command already updated (`LockRows` treats them as `TM_SelfModified`) and returns the next pending one, so the statement claimed **every** pending row. Reproduced deterministically in psql (`LIMIT 1` -> `UPDATE 3`) and in-suite by inducing the planner statistics rather than a race. `_CLAIM_IDS_SQL` is materialized too: bounded by `id = ANY(:ids)` it could not overrun a limit it does not have, so it was not defective, but it took the same rescan and its lock decisions were quadratic in the caller's id set. `_RECLAIM_SQL` and `_SWEEP_DONE_SQL` are unbounded by design and were left alone. | The trigger is `memory_buffer`'s normal production steady state — a drained table autovacuum has just analysed (`relpages > 0`, `reltuples = 0`) — so this was live, not a test artifact, and since T1.14 every capture flows through this path. It also defeated the `claim_limit` deadline valve (Fable review I-3): the batch that valve halves was not the batch actually claimed, so a batch too slow for the ceiling marched the whole healthy backlog into `error`, which is the exact failure I-3 exists to prevent. Found by lane G while diagnosing a floor flake and escalated because `buffer_flush.py` was outside that lane. Guarded by two statistics-driven regression tests (never timing-driven, which would reintroduce the flake); mutation-verified by restoring the sub-select form, which fails six tests including `test_a_slow_batch_does_not_march_the_backlog_into_error`. |
| 2026-07-27 | T1.34 | 1 | **Only the closed-vocabulary axes (`env`, `situation`) can produce a `conflict`; a `version` difference is `neutral`, never an exclusion.** Doc 07 §6's outcome table gives one example (`env=prod` vs `dev-only`) and does not say which axes may exclude, so the rule was fixed narrowly and pinned by a test. | Doc 07 §6 and doc 12 §5 both call `version` "a free string compared app-side". Equality on a free string can establish "not the same version" but never "explicitly incompatible" — `15` vs `15.3` is the common case, and treating it as a conflict would silently delete the correct answer. `env`/`situation` are closed vocabularies under doc 06's discipline, so a stated mismatch there really is explicit. Exclusion is the one direction where being wrong removes a row instead of merely misranking it, so the ambiguity was resolved toward not excluding. |
| 2026-07-27 | T1.34 | 2 | **The `applies_when` slot fixes the interface T1.42a's context chain must terminate in**, so the chain can be planned against a real seam: `declared_context_from_wire(raw: Mapping | None, provenance) -> DeclaredContext | None` (the chain resolves *precedence*, this resolves *meaning*), and `row_context_from_applies_when(applies_when, provenance) -> RowContext | None` per row. `None` is the single representation of "undeclared" — a `DeclaredContext` with no stated axis raises — and `ContextComposition.declared` carries the declaration alongside the rows so "nothing declared" stays distinct from "declared and matched nothing". | Ruling 4: T1.42a is Size L with no step-level plan and cannot be built here, but a slot wired against an imagined input is a slot that will not fit the real one. Declaring the seam now costs T1.42a nothing and makes the join checkable. The `None`-only-undeclared rule is T1.65's distinction made structural: a vacuous declared context would be indistinguishable from no declaration while still being a live object, which is exactly how an undeclared context starts rendering as a default. |
| 2026-07-27 | T1.33 | 2 | **The trace envelope's `excluded` keys are the concrete schema-v2 filter names (`memory_type`, `source`, `technologies`, `tags`, `not_found`), not doc 07 §8's forward-looking `{by_project, by_status, by_context_conflict}`.** `with_trace=True` is wired only on `POST /memories/search/paginated` (which already returns a wrapper object with room for an `envelope`), not on `POST /memories/search` (a bare `list[MemoryResponse]` with no slot for request-level data). The trace-assembly path (`MemoryService._search_memories_paginated_traced`) is a parallel method built directly on `HybridSearchService`/`RerankerService`/`rank_fusion.py`, never a branch inside `pipeline.py` — that file is outside this lane, and the reimplementation is narrow enough (embed, two channels, RRF, optional rerank, optional confidence weighting) that duplicating it beat threading a flag through a file the lane may not touch. | `by_project`/`by_status` cannot fire on this path today: the sibling pushdown lane (T1.29-series) already scopes project/status/archived in the channels' own SQL, so a foreign row is never fetched to be counted here — reporting them as permanently-zero reserved keys would be decorative, not honest. `by_context_conflict` has no implementation yet (context/`applies_when` matching and the L0/L2/L3 layers are E2/E3 concepts); this task only proves the honesty rule (every excluded row is counted by reason, rendered even at zero survivors) against the filters E1 actually has. T1.42a/T1.44, which render this envelope, need to know the real key set is filter-name-shaped, not the doc's three-key table, until a later task adds project/status/context-conflict exclusion counting for real. |
| 2026-07-27 | T1.44 | 2 | **The exclusion envelope is honest about what it can see, and structurally blind to SQL-filtered rows — T1.44's UI must not render that blindness as "nothing was excluded".** T1.33 reports the *real* post-hoc exclusion reasons rather than doc 07 §8's forward-looking `{by_project, by_status, by_context_conflict}`, because the first two are now closed by SQL pushdown (T1.29a–d) and would therefore always report **zero**. | Emitting an always-zero `by_project` would be worse than omitting it: it reads as an affirmative "no rows were removed by project scope" when in fact the filter ran in SQL and removed an uncounted number. So the lane's choice is the more honest one. But the gap it leaves is real — a caller still cannot learn how many rows project or status scoping removed, and counting them would cost a second query. **T1.44 must therefore not present an empty exclusion strip as proof nothing was filtered**, and T1.50 must not cite the envelope as evidence that isolation removed nothing. Whether to buy the second query is a design decision, not an implementation detail. |
| 2026-07-27 | T1.44 | 1 | `with_trace` is wired on `/search/paginated` only, **not** on the bare `/search`. | T1.44 renders the why-retrieved trace and will hit this directly: if the Memories surface calls `/search`, no trace is available and the feature silently renders nothing. Either T1.44 uses the paginated route (which it needs anyway, since its own Done-when requires the list to virtualize and page) or the flag must be extended. Recording it so it is a decision rather than a surprise. |
| 2026-07-27 | T1.34 | 1 | **Ruling accepted: only the closed-vocabulary axes `env` and `situation` can produce a context conflict; a `version` difference is neutral.** | T1.34's reasoning holds and both docs support it — doc 07 §6 and doc 12 §5 each treat version as a free string compared app-side. A strict version comparison would let `15` versus `15.3` silently delete the right answer, which is the failure the conflict-count rule exists to expose rather than cause. Flagged for a reviewer's eye because it is an interpretation, not a quotation. |
| 2026-07-27 | T1.29d | 1 | Touched two files the lane list does not name: `app/api/routes/graph.py` (one `project` Query parameter forwarded to `get_unified_graph`) and `app/services/pipeline.py` (`find_duplicates` only — it derives the scope and forwards `filters`). | `find_duplicates` in `pipeline.py` **is** the "`memory_find_duplicates` implementation" the file list names; the tool and route are both thin delegations to it, so there is nowhere else the fix could live. The graph route parameter exists because `get_unified_graph` turned out to be a **fourth** consumer of the same unscoped `get_all_vectors` read, and a scope the service accepts that no front door can set is a leak that is merely harder to reach (the rule invariant 17 and T1.29c's Tier-1 row both state). Both hunks are one-liners; no other line of either file changed. |
| 2026-07-27 | T1.29d | 2 | **`GET /api/v1/graph/unified` was a fourth unscoped consumer of `get_all_vectors`, which no enumeration — including T1.29c's — had listed.** It reaches the same bulk partition read through `get_louvain_clustered_vectors` and returns full memory content per node. Fixed here alongside `/vectors/projection`, and `get_all_vectors` now also emits `project` and `status` on **every** row it returns, including for `filters=None` callers. | This is the third consecutive enumeration of this subsystem to come back incomplete, and it is why the labels are unconditional rather than a by-product of scoping: T1.35's bar counts *unlabelled* cross-project and superseded rows, so a row that escapes through a caller nobody enumerated still arrives self-describing. Scoping one route while its sibling read the same rows unscoped is precisely the shape that made the previous two enumerations wrong. |
| 2026-07-27 | T1.29d | 2 | **The re-derived inventory is empty of unscoped *retrieval* channels but NOT empty of unscoped memory-content channels, and the residue has no owner.** Five live, authenticated surfaces return memory content with predicates missing, none of them named by any task: `GET /reembed/obsolete/memories` (`LEFT(content,120)`, and its anti-join degrades to literal `TRUE` when the active partition is absent, so it previews *every* row); `GET /pipeline-failures` (`LEFT(m.content,80)` over an unscoped `LEFT JOIN memories`); `GET /analytics/overview` recent-memories (full content, `is_archived` only — T1.29c's F4); `GET /memory-buffer` and its requeue (500-char `content_preview`, project optional); `GET /events` and `/events/timeline` (`buffer_discarded` rows carry a 500-char `content_preview`, project optional). | **T1.35's probe must cover these or its zero is false**, which is the entire reason this task exists. Not fixed here: every one sits outside this lane's file list, and `memory-buffer` is adjacent to `buffer_flush.py`, which the brief excludes by name. They are operator and diagnostic surfaces rather than retrieval channels, so the honest claim is the narrow one — the retrieval channel inventory is closed, the memory-content inventory is not. Recording the distinction rather than letting "every channel filters in SQL" be read as the wider statement. |
| 2026-07-27 | T1.29d | 1 | **The three arms of `get_memory_context` are now deliberately asymmetric, and the asymmetry is pinned by test rather than by comment alone.** The neighbour-memory arm renders `project + status IN ('active') + is_archived = FALSE`; the relation arm keeps `project + is_archived` with **no** status; the entity arm stays seed-addressed. `MemoryFilter.orm_criteria` was added so the ORM arm and the SQL-text arms render one definition of the scope. | Resolves the interaction T1.29c logged and left open. Collapsing the arms onto one scope object is the obvious "fix" and it is wrong in both directions: adding status to the shared filter empties the context view of a superseded memory of its own edges — the view a reader opens precisely to understand what replaced it — while leaving it off the neighbour arm presents retired content as a live peer, which is what doc 07 §7 counts. `test_memory_context_keeps_an_edge_its_only_asserter_superseded` makes the *same* superseded memory both the excluded neighbour and the sole asserter of a required edge, so one scope object cannot pass both tests. |
| 2026-07-27 | T1.29d | 2 | **`KnowledgeGraphService` and the `knowledge_triples` read path carry no project predicate and have no front door yet.** `get_triples_by_subject/object/predicate`, `get_triples_for_entity_timeline` and `get_recent_triples` filter on subject/object/predicate and the temporal window only, while `knowledge_triples` carries both a `project` column and a `fact TEXT` payload. `KnowledgeGraphService` has no caller anywhere in `app/`. | Recorded now, while it is still inert and therefore free to fix. The Layer-2 fact store is a memory-content channel by construction, and the first task that wires a route or MCP tool to it will otherwise inherit exactly the unscoped default this whole T1.29 series has been unwinding. Whoever owns that wiring should render the scope in the repository, not at the front door. |
| 2026-07-27 | T1.29e | 2 | **New task, and the third round of this discovery.** T1.29d's code-derived inventory is **empty of unscoped retrieval channels but not of unscoped memory-content channels** — five live authenticated surfaces still return content with predicates missing, none owned by any task. Framed as an **adjudication**, not a blanket fix: several are operator/triage surfaces where cross-project visibility may be correct, and a pipeline-failure screen that hid other projects' failures would be a worse tool. | The distinction between a *retrieval channel* and a *memory-content surface* is what made three rounds necessary: each earlier sweep enumerated the former and stopped. **T1.35's probe must encode that distinction or its zero is false** — that is the load-bearing item, above any individual fix. Two of the five are not scoping questions at all: `/reembed/obsolete/memories`'s anti-join **degrades to a literal `TRUE`** when the active partition is absent, previewing every row (a defect on any reading), and `/events`' 500-char preview **survives deletion of its source memory**, which is a retention and privacy question escalated rather than decided, since `events` is append-only by design. |
| 2026-07-27 | T1.29d | 1 | **Found and fixed a fourth leak the brief did not name:** `GET /graph/unified` reads the same `get_all_vectors` through the Louvain wrapper and returned full content per node. `get_all_vectors` now labels every row with `project` and `status` **unconditionally**, including for `filters=None` callers. | Defence in depth rather than another enumeration: a row escaping through a caller nobody has enumerated now arrives **self-describing**, so the next missed channel leaks a labelled row instead of an anonymous one. Given that the consumer list has now been wrong three times, a mechanism that degrades safely is worth more than another sweep. |
| 2026-07-27 | T1.29d | 1 | **The three graph arms are deliberately asymmetric and must stay so:** neighbour memories get project + status + archived; relations keep project + archived with **no** status; entities stay seed-addressed. | Collapsing them onto one scope is wrong in both directions, and the lane pinned it with a test that makes this impossible to "simplify" by accident: `test_memory_context_keeps_an_edge_its_only_asserter_superseded` makes the same superseded memory both the excluded neighbour **and** the sole asserter of a required edge, so no single scope object can pass both assertions. Also corrects the controller's brief on one fact — `get_memory_context` feeds the frontend graph explorer, not an LLM context, so the exclusion rests on the honesty bar rather than on prompt hygiene. |
| 2026-07-27 | T1.09 | 1 | **No code change: verified the task's premise no longer holds.** `rg -n "audit_log\|AuditLog" backend/app` returns exactly three hits, all comments (`app/api/routes/auth.py:219`, `app/api/routes/analytics.py:88`, `app/services/analytics.py:247`) documenting that `audit_log` was dropped at the baseline's genesis (doc 04 §7/§8.1, doc 18 §-legacy-transform) — there is no literal `audit_log` table, model, or query anywhere, and none ever existed in this repo's history to retire. `GET /api/v1/auth/audit` already reads `events` directly (`event_type LIKE 'auth\_%' OR 'setup\_%'`), and every doc-18 write (`auth_login_failed/success`, `auth_logout`, `auth_password_change`) already goes through `record_event` per T1.07's row above. Both were already true on this branch before this task ran. | T1.07's own amendment row states it generalised the writer *and* T0.12c's pre-existing `auth_*`/`setup_*` types kept working unchanged; between that and T1.08's read API, the reader migration T1.09 was written to perform had already happened. `progress.md` still lists T1.07-T1.09 as `todo` because lane merges land on the epic branch ahead of the controller's separate progress update — the code, not the tracker, is ground truth here. Both Done-when boxes hold (`test_audit_endpoint.py` passes in the green floor), so the task closes by verification, not by a diff. |
| 2026-07-27 | T1.45 | 2 | **`GET /pipeline-logs` queries an `events` `event_type` that nothing ever writes**, so it returns empty forever. Found by T1.38's lane, correctly left unfixed as out of scope. Assigned to **T1.45**, which owns the pipeline stepper and failure-triage surface. | This is the honesty failure the corpus fears in its quietest form: an operator opening a pipeline-log view sees an empty list and concludes nothing went wrong, when in fact nothing is being recorded. It is indistinguishable from a healthy system. T1.45's Done-when already covers failure triage surfacing the failed step, so either that view must read an event type something emits, or the emitter must be added — but a surface that structurally cannot show data must not ship looking like one that can. Note T1.07 made `EVENT_TYPES` a closed vocabulary that warns rather than rewrites, so adding an emitter means adding the type there too. |
| 2026-07-27 | T1.09 | 1 | **Closed by verification with no code change — the task's premise was already satisfied.** `audit_log` was dropped by the baseline outright, and the controller confirmed only **three** references remain in `backend/app`, all of them **comments** (`analytics.py:88`, `auth.py:219`, `services/analytics.py:247`). There is no product read path to retire and no `AuditLog` model to delete. | The task was written against a pre-baseline state where the table still existed; T0.12c's baseline and T1.07/T1.08's `events` work between them removed the substrate before this task was reached. Recording it as an amendment rather than silently ticking the boxes, because a task that turns out unnecessary is a planning signal worth keeping — and because the Done-when's second clause ("auth audit trail still functions") now reads oddly: those writes go to `events`, not to a table that no longer exists. |
| 2026-07-27 | T1.44 | 1 | The real (`!DEMO`) project-scope control is a free-text `Input`, not the demo page's project `Select`. No backend endpoint enumerates distinct `project` values, and `projectStore` (doc 13 §2) is target-new — a dropdown would have to fabricate its own option list from whatever page of results happened to be loaded, which is exactly the kind of decorative completeness invariant 14 forbids. | A future task that lands a projects-list endpoint or `projectStore` should upgrade this control to a `Select`; until then, free text over the exact `project` string is the honest interface to a filter with no enumeration source. |
| 2026-07-27 | T1.44 | 1 | The DEMO/real split is done at the **component** level (`DEMO ? <DemoMemoriesPage/> : <RealMemoriesView/>` in the route's `component`), not inside one hook the way T1.43's `useContributionCalendar` does. | The existing Memories page carries several demo-only affordances with no real-backend equivalent in this epic — the timeline scrubber, the heatmap seek-to-date effect, and the `applies_when` session context chip (doc 13 §3's `contextStore` is target-new; the real `Memory` schema has no `applies_when` column at all). Threading `DEMO` through each of those individually would scatter conditionals across one already-large component. `DEMO` is fixed for the process lifetime (`import.meta.env`, not runtime state), so branching whole components on it never risks violating the rules of hooks. |
| 2026-07-27 | T1.44 | 1 | `RealMemoriesView` does not render a create/edit-memory dialog; `MemoryEditorDialog` (unconditionally bound to the demo store's `addMemory`/`updateMemory`) stays demo-only. | Wiring memory creation to the real backend is not in this task's Done-when and would need a new `useUpdateMemory` hook plus dropping the demo-only `applies_when` field the dialog currently collects — real scope creep beyond "the search surface with the per-row trace," not a one-line reuse. Left for whichever task owns real memory authoring. |
| 2026-07-27 | T1.58 | 1 | **T1.44's create/edit dialog stays demo-only, and that is consistent with an already-recorded gap rather than a new one.** T1.14 flipped `POST /memories` to a buffered 202 ack while `frontend/src/hooks/api/use-memory-api.ts` still types the call as returning a `Memory`; the dialog cannot bind to a shape nobody has defined yet. | Grouping the two so T1.58 sees one problem rather than two symptoms: the create path's wire shape is T1.42a's envelope work (its plan names the 202 ack's shape as an open question deciding the type T1.58 will write), and the binding is T1.58's. Neither is a defect in T1.44 — a lane that bound the dialog to a guessed shape would have had to unbind it. |
| 2026-07-27 | T1.44 | 1 | Project filter shipped as **free text rather than a `Select`**, because no distinct-projects endpoint exists. | Worth recording because it is the third symptom of the same absence: T1.42a's plan found the `projects` table has **no reader, writer or model**, which also leaves tier 3 of the context chain (project default) permanently empty. One missing substrate, three surfaces improvising around it — whoever lands the projects reader should sweep all three rather than fixing whichever is reported first. |
| 2026-07-27 | T1.42a | 2 | **Step 15's row-shape half is already landed**, out of band and ahead of the rest of T1.42a. `memory_to_dict` now derives its field list from `MemoryResponse.model_fields` instead of restating it, so the MCP row carries `project`, `status`, `superseded_by`, `technologies`, `confidence`, `related_memories` and `trace`. Two guards ship with it: a declaration-only drift test that fails naming any `MemoryResponse` field the serializer cannot resolve, and a door-level test that a superseded memory read through `memory_get` reports `status='superseded'` plus its `superseded_by` pointer. T1.42a's Step 15 keeps its `CaptureAck.schema_version` change and its four-surface key-set audit; its "add the five fields" sentence is done. The envelope itself is untouched. | The omission was a live invariant-14 hole on the unauthenticated door: an MCP agent read a retired memory as current, with no lifecycle label anywhere on the wire and no human reading a badge. T1.42a is Size L, unexecuted, and its Step 7 has an unresolved downstream consequence; a known silent-authority defect on the product's primary interface should not wait behind that. `related_memories` and `trace` are emitted as `null`, which is exactly what an ordinary REST read carries — key-set parity at zero cost, no crossref query and no trace assembly on the MCP path. |
| 2026-07-27 | T1.42d | 1 | **Value parity gap recorded for the two-door audit:** after the MCP serialization fix, key parity between the doors holds, but `related_memories` is `null` on MCP where REST's single-memory GET populates it. | T1.42d's job is making invariant 17 true rather than aspirational, and this is precisely the shape it should catch — a field present on both doors with the same name and a different meaning is more misleading than one that is absent, because a client cannot tell an empty relationship set from an unpopulated one. Recording it now so the audit inherits it rather than rediscovering it. |
| 2026-07-27 | T1.42a | 2 | **The MCP serialization defect was fixed out of band rather than waiting for T1.42a**, whose plan covers it. `memory_to_dict` omitted seven `MemoryResponse` fields including **`status` and `superseded_by`**, so an MCP agent could not distinguish an active memory from a superseded one, and `project` was absent from the one door where an agent would use it. Fixed by deriving the serializer from `MemoryResponse.model_fields` with a drift guard, commit `c341e7a`. | Justified by severity and by the caller audit: `memory_to_dict` has exactly **one** importing module (`api/mcp/server.py`, five call sites) and no REST, websocket, service, harness or test consumer, so the change lands only on MCP and could not disturb T1.42a's envelope work. Leaving a silent-authority failure on the primary agent interface — while REST honoured the shown-with-a-badge rule and MCP did not — for the duration of a blocked Size-L task was the worse option. **T1.42a's plan should be updated to note this is already done.** |
| 2026-07-27 | T1.29e | 2 | **All five operational surfaces are now decided, and three of them are decided *operator-wide* on purpose.** `GET /reembed/obsolete/memories` (re-embedding is a partition backfill: every project and every lifecycle state needs a vector under the active embedder, and the write path is unscoped for the same reason, so a scoped preview over an unscoped backfill would let an operator read the queue as empty while whole projects stayed unembedded); `GET /pipeline-failures` (the join is addressed by `pf.entity_id`, so it returns only the memory the operator is already being shown a failure for, and a lifecycle predicate would blank the preview for exactly the rows most in need of triage); `GET /analytics/overview` recents (every other number on that dashboard is deployment-wide and supersession is itself recent activity). `GET /memory-buffer` keeps its scopeable, defaults-wide shape unchanged — pre-flush rows have no status or `is_archived` yet, and the `project` parameter already rides the SQL. | Scoping something that should stay operator-wide is as much a defect as the reverse, so the three wide decisions bought their width with the other half of T1.29d's mechanism: the failure list now emits `entity_project` / `entity_status` and the recents list now emits `project` / `status`, so every row they return is self-describing and the honesty bar's *unlabelled* qualifier is satisfied without narrowing a triage tool into uselessness. All four decisions are pinned from both directions in `tests/test_content_surface_scoping.py` — a test fails if they are narrowed and a test fails if the labels are dropped. |
| 2026-07-27 | T1.29e | 2 | **The `/reembed/obsolete/memories` anti-join no longer degrades to a predicate that matches every row.** `_missing_filter` substituted a literal `TRUE` when the active partition was absent; that state is real after any embedder rotation, and in it the endpoint paged 120-char content previews of the entire `memories` table. The helper is now `_anti_join`, returning `None` rather than a matching-everything string, and the callers branch: counts stay exact, the memories and entities listings withhold the enumeration, and all three listings report a new `partition_missing` flag so the whole-corpus answer is self-describing rather than silent. `tests/test_reembed_absent_partition.py` previously asserted the old behaviour (`len(items) >= 1`) and was updated to the new contract. | Fixed regardless of the scoping decision, per the controller's ruling: the row set the substitution produced was arithmetically right, but a filter whose degraded form discriminates nothing has no business driving a content listing — the count already carries every bit of information the enumeration does in that state. The response-shape change is additive and no frontend consumer reads these three listings (the maintenance tab reads `/reembed/obsolete-counts` and the POST actions only). |
| 2026-07-27 | T1.29e | 3 | **ESCALATED, not decided — memory content survives deletion of its memory, in two stores rather than one.** `events` is append-only by design (T1.06's three forbid-triggers), so a `buffer_discarded` row's 500-char `payload.content_preview` outlives the memory it came from: "delete my memory" does not remove its content from the journal. Adjudicating that surface surfaced a **second** store with the same property, which no sweep had named: every assistant message persists a 150-char snippet of each cited memory in `messages.context`, served by `GET /api/v1/chat/conversations/{id}`, and nothing prunes it on delete. Retrieval was correctly scoped when the snapshot was taken; the issue is retention, not isolation. Behaviour is pinned by test in both stores so the decision has something concrete to flip; **no redaction scheme was implemented.** The options, for the human: (a) accept it and say so in the privacy posture — the journal is the audit substrate and a redactable audit log is a weaker one; (b) redact on delete via a compensating **append** (an `event_redacted` row the read surface honours) rather than an UPDATE, which the forbid-triggers rule out; (c) stop writing content into the journal at all and key the preview to the buffer row, accepting that a discarded capture becomes unreconstructable; (d) age the payload out on a retention clock, which needs a stated retention period and does not help a delete-now request. | Raised to Tier 3 because every option is a policy choice about what the product promises when a user deletes a memory, and (b) and (c) both change the meaning of the audit substrate. The scoping half of these two surfaces is not the question and was not changed: `project` already rides the SQL on both event reads and defaults to every project, consistent with the buffer and the ratified `reason` default. |
| 2026-07-27 | T1.29e | 2 | **The retrieval-channel versus memory-content-surface distinction is now code, not prose: `app/services/content_surfaces.py`.** A retrieval channel *chooses* rows in answer to a question, so isolation is a correctness property of the choice; a memory-content surface returns memory-derived data as a side effect of an operational job, so its scoping is a policy decision that may legitimately be deployment-wide. The registry names every front door that returns memory-derived data — REST and MCP — with its kind, what crosses it, its `Scoping` (`SCOPED` / `ID_ADDRESSED` / `OPERATOR_WIDE` / `ESCALATED`), the per-row labels it emits, and the recorded reason. **T1.35 must drive `memory_content_surfaces()` as well as `retrieval_channels()`**, and T1.42d reads `front_doors` for the two-door split and `operator_wide_surfaces()` for the scoping exemptions. | The load-bearing deliverable, above any individual fix: three rounds of discovery happened because each sweep enumerated the former and stopped, and a probe built the same way returns a clean zero over the whole operational half. The registry also carries the mechanism that stops a fourth round — `ROUTES_WITHOUT_MEMORY_CONTENT` and `MCP_TOOLS_WITHOUT_MEMORY_CONTENT` must together account for every route the app registers and every tool it exposes, so adding a front door without classifying it fails the build. Two surfaces no sweep had listed were found by writing that guard: the chat-history citation snapshots (above) and the `memory_ids` arrays on the graph entity browser (recorded operator-wide — entities are deliberately not memory-scoped, and trimming the array would break the neighbour derivation that consumes it). |
| 2026-07-27 | ESCALATION | 3 | **The content-retention question spans TWO stores, not one, and any policy covering only `events` is a half-measure.** Alongside `events`' 500-char preview, **`messages.context` persists a 150-char snippet of every cited memory and nothing prunes it on delete** — found by T1.29e's registry completeness guard. So "delete my memory" leaves that memory's content in the append-only journal **and** in chat history. Four options are written up in T1.29e's report. **Needs an owner before G-B.** | Escalated rather than decided, per runbook §5 Tier 3: this is a data-retention and privacy property, not an isolation bug, and `events` is append-only *by design* (T1.06's three forbid-triggers). The controller had already raised the `events` half with the human; recording the second store because a ruling made on the first alone would be quietly incomplete, and the incompleteness would only surface the first time someone tested a deletion end to end. |
| 2026-07-27 | T1.21 | 1 | **Assigned F6:** the crossref probe (`find_similar_memories`) calls `search(filters=None)`, and its output is stored in `memory_crossrefs` and served as ids and scores by `GET /memories/{id}`. No content crosses, but the *existence* of a similar memory in another project does. | T1.29d left it deliberately and correctly: the fix belongs at the Phase-5 crossref call site in `pipeline.py`, which no pushdown brief named, and narrowing crossrefs is a **behaviour change to a stored artifact** rather than a filter on a read. T1.21 owns Phase 5, including the separate-session crossref computation, so it is the right home — and it must decide deliberately, since existing stored crossrefs would not be retroactively narrowed. |
| 2026-07-27 | T1.42c | 1 | **Assigned F9:** MCP `memory_search` exposes no `project` parameter although `MemorySearchRequest.project` exists, so the project pushdown is reachable from REST and **not** from MCP. | A clean invariant-17 asymmetry — the same capability on two doors with only one able to use it — which makes it T1.42c's (MCP surface parity) with T1.42d auditing it. Worth noting the direction: this is the *safe* asymmetry (MCP callers cannot narrow rather than cannot isolate), but an agent that cannot scope its own search is exactly the caller most likely to need to. |
| 2026-07-27 | T1.60 | 2 | **Assigned F8 and F10, both graph-explorer surfaces, as one decision.** F8: `GET /graph/full`, `/graph/entities`, `/graph/entities/{id}/neighbors` and the `include_entities` overlay return `memory_ids` arrays spanning every project and status — no content crosses, but memory *identity* does. F10: `_fetch_entity_overlay` calls `get_full_graph(limit=500)` unscoped then filters in Python, which is not a leak but **can silently under-return**. | Grouped because they are the same surface and the same product question, and because F8 is genuinely not a leak fix: `CLAUDE.md` states entities are **not** memory-scoped, so scoping the global entity browser is a design decision, and trimming `memory_ids` would break the neighbour derivation that consumes it. T1.60 binds the Memory Graph explorer and is where that decision becomes visible. F10's silent under-return is the more insidious half — a user sees fewer nodes and no indication why. |
| 2026-07-27 | T2.xx | 1 | **Standing warning, F7:** `knowledge_triples` carries both `project` and `fact`, and every `KnowledgeGraphService` read filters on subject/object/predicate and the temporal window **only**. `KnowledgeGraphService` has **no caller anywhere in `app/`**, so nothing leaks today. | Recorded while it is still inert and free to fix. The first E2 task that wires a route or MCP tool to the Layer-2 fact store would otherwise inherit exactly the unscoped default this five-round series has spent the session unwinding — and it would inherit it on the *truth* layer, where a cross-project fact count is worse than a cross-project search hit. |
| 2026-07-27 | T1.57 | 1 | **Closes T1.15's found-not-fixed row above: `GET`/`PUT /api/v1/config/repo-allowlist` now exists**, validated with T1.15's own `validate_pattern` (new, wraps the existing private `_split_pattern` — the exact parse `evaluate_hint` runs a stored pattern through), never a second hand-rolled check. Settings → Flags is the editing surface (textarea, one pattern per line). | Ruling 2 required reusing T1.15's validator rather than writing a second one; proven by a mutation test (`test_repo_allowlist_route.py`) that swaps the route's validation call for a permissive stub and watches six tests fail, then restores it. |
| 2026-07-27 | T1.57 | 1 | **Ruling 1's shape: `FeatureFlagsResponse` gained flat `w_importance`/`w_heat`/`w_recency`/`w_context_boost` fields plus a `rank_arms: [{name, flag, value, activation}]` list read straight from `app.services.rank_fusion.RANK_ARMS`.** The frontend never re-declares which arm activates at which task id — it reads `rank_arms[].activation` (T2.30 for `w_importance`, T2.31 for `w_heat`/`w_recency`, `null` for the already-live `confidence` arm), so T1.31's backend labelling and this task's UI labelling cannot drift apart. | Recorded so a later task extending `RANK_ARMS` (e.g. adding `w_ppr`) gets the wire field for free with no route edit, and so nobody re-adds a second, hand-copied activation-id map in the frontend. |
| 2026-07-27 | T1.57 | 1 | **Ruling 3's "visibly unmeasured" reads from a new `flag_measurements` config row (key absent = nothing measured), not a hardcoded frontend list.** `MEASURABLE_FLAGS = (w_importance, w_heat, w_recency, w_context_boost, reranker_enabled)` in `app/services/feature_flags.py` names which flags are subject to the gate-ledger's "flip only on a measured win" rule; `measured_flags` (also wired on the response) names which of those have actually cleared one — empty today, matching `gate-ledger.md`'s never-populated "Arm activation log". No write path is exposed for `measured_flags`: only a future gate-clearing process is meant to populate it, never an operator toggle, or the honesty bar would be gameable from the same surface it is meant to protect. | Chose a `config` row over parsing `gate-ledger.md` at request time (fragile, and a doc is not meant to be a runtime dependency) or a static array (exactly what ruling 3 asked not to build). Mutation-tested: hardcoding `unmeasured` to ignore `measured_flags` fails `settings-flags.real.test.tsx`'s "clears the unmeasured badge once measured" case. |
| 2026-07-27 | T1.57 | 2 | **Two Done-when items — graph-augmentation flags (`ppr_enabled`/`dual_level_enabled`/`community_injection_enabled`, plus their `w_ppr`/`w_dual` weights) and the corroboration `N`/diversity gate — are rendered demo-only; real mode shows an honest "not yet exposed via the API" panel rather than a fetch.** Neither exists as a `config` key anywhere in the backend today: the graph-augmentation flags are doc 07 §4/§11's Phase-2 scope, and corroboration `N` is `T2.03`'s ("the verification ladder", Opus tier, E2/Truth-core epic, `Tag: target-new`) to define — doc 08 §4.1 states a candidate default (N=2 diverse/≥7-day else 3) but explicitly frames it as tuned by that task, not pre-committed here. Building either now would mean inventing an Opus-tier design decision from a Sonnet-tier lane, or reaching into retrieval fusion, both outside this task's lane per the runbook's escalation rule. | Flagging as tier 2 because the task text's own Done-when ("Corroboration N ... editable as `config` rows") reads as if this lane should build it; ruling 1 named only `w_importance`/`w_heat`/`w_recency` as needing backend exposure and said nothing about corroboration or `w_ppr`/`w_dual`, which this lane reads as the controller's implicit scope line. Followed the T1.61 buffer-monitor precedent (same file, "the real branch... renders an honest 'no REST surface yet' staged state rather than fetching against a guessed contract") rather than inventing a config row or a UI lie. A reviewer should confirm this reading before G-B closes doc 13 §7 end to end. |
| 2026-07-27 | T1.57 | 1 | **"Job cadences editable as `config` rows" is satisfied by the pre-existing `PUT /jobs/{key}` surface, reachable from Settings → Jobs — this task binds only the read-only summary inside Flags to real `/jobs` data** (via `useJobs`, mapped through `cronInfo` for the label) and leaves the summary's pointer to the dedicated tab unchanged. | `jobs-settings-tab.tsx` itself is still demo-bound; `T1.63` ("Bind Settings: Security, Maintenance, Jobs") owns making it real, with its own Done-when ("Jobs tab drives real triggers and shows a held lock as busy"). Binding it here would duplicate that task's work ahead of its own dependency (`T1.58`) landing. |
| 2026-07-28 | T1.39 | 1 | **`_find_dependent_caller_files` now returns `(kept, overflow)` rather than `(kept, total)`.** The work past the re-trace cap had to be *named* to be persisted; a count can only be logged. `tests/test_incremental_dependents.py`'s two assertions were updated to the new shape. | The old signature encoded the defect: it gave the caller exactly enough to write a log line about truncation and not enough to do anything about it. Recording it because the return shape is the seam any later re-trace work will touch. |
| 2026-07-28 | T1.39 | 1 | **`repositories.index_debt` is no longer inert**, so it left `INERT_COLUMNS` in `tests/test_inert_objects.py` along with its two guard clauses (the `IS NOT NULL` count and the `index_debt` arm of the no-writer source scan). `baseline-schema-inventory.md` §7 already named T1.39 as its first writer and needed no edit. | Exactly the handover that module documents in its own failure message. The column's DDL was untouched — the writer landed against the shape the baseline already carried, so no baseline regeneration and no schema-owner serialisation was needed. |
| 2026-07-28 | T1.39 | 2 | **An unchanged HEAD no longer short-circuits a reindex when the repo carries debt** — `CLAUDE.md`'s Code-indexing section is updated to say so, and `POST /repos/{id}/reindex` is therefore the human-facing force-drain doc 13 asks for, with no new endpoint. Without this the queue would drain only when someone happened to push, which is the same unbounded staleness the debt exists to end (`code_reconcile`'s drain arm, T3, does not exist yet). | Tier 2 because it changes a documented behaviour other tasks reason about, and because `repo_sync` now performs a bounded continuation run per polled repo until its debt reaches zero, then returns to the no-op it was. Convergence is asserted, not assumed: `test_continuation_batches_drain_to_zero` drives the queue to zero across runs and fails if a batch stalls. |
| 2026-07-28 | T1.46 | 2 | **The debt observable is a shape, not a count, and T1.46 should quote it.** `GET /api/v1/repos/{id}` (and the list) carries `index_debt: {queued, deferred_total, drained_total, last_defer, last_drain}`, where each last-* record is `{at, count, commit, vanished}`; the same numbers ride `repo.indexing_completed` as `index_debt_queued` / `index_debt_drained`, and every defer and drain journals a `repo_indexed` `events` row. | T1.46's box is "shows queued file count **and that it is draining, not lost**", and `queued` alone cannot carry the second half — a stuck queue and a draining one are the same integer at a single instant. `drained_total` with `last_drain.at` is what makes the difference readable from one response. The event type is an existing `EVENT_TYPES` value with a live reader (`GET /api/v1/events`), deliberately not the write-nothing path T1.45 inherited. |
| 2026-07-28 | T1.35 | 2 | **The isolation probe is built and the measured number is 10, not 0 — G-B's isolation row is recorded FAIL and the gate stays open.** Probe: `backend/scripts/benchlib/run_isolation_probe.py`, driven from the `content_surfaces` registry (aborts on any surface without a driver), deterministic (two byte-identical runs), zero model calls, sensitivity proven by mutation (removing the `MemoryFilter.where_sql` status clause drives 10 → 58 with named rows). The ten leaks, all V2 unlabelled escapes on four surfaces: `memory_reason` REST+MCP default scope returns cross-project 200-char previews with no project/status keys on `sources` rows (4); chat `sources` SSE rows carry full content unlabelled under the default context (2); the re-embed backfill queue previews cross-project and superseded rows as `{memory_id, content_preview}` only (2); chat history re-serves the unlabelled cross-project citation snippets on every conversation read (2). Registry honesty: `memory_reason` and `chat_retrieval` declare `labels=("project","status")` that their response shapes do not emit. | The fixes have **no owner**: T1.29e ratified the reembed queue wide with `labels=()`, and nothing owns labelling `reason`/chat `sources` rows or citation snippets. Per the probe brief the probe must not fix what it measures, so the leaks are reported here for the controller to assign; the probe is re-runnable as-is once owned fixes land. Id-only exposure (15 sightings) and retention snapshots (3) are reported-not-counted with the decision stated in `benchlib/isolation_rules.py` and the G-B ledger entry. |
| 2026-07-28 | T1.35a | 2 | **The isolation probe now measures 0 and G-B's isolation row clears; the failing 10 stays recorded beside it.** All ten were closed by *labelling*, never by narrowing — the per-surface row counts are byte-identical to the failing run and only the V2 column moved. The labels are stamped where rows are produced, following T1.29d's `get_all_vectors` precedent: `PostgresVectorRepository.search` and both `HybridSearchService` arms join `memories` unconditionally and emit `project`/`status` even for `filters=None` callers; `MemoryService.reason` builds one citation shape for both its passes and therefore for both doors; `ChatService` labels the `sources` event and the persisted citation snapshot; `list_obsolete_memories` labels its previews. New shared vocabulary: `app/utils/scope_labels.py`. Guards: `backend/tests/test_scope_labels.py` (18), each labelling point mutated in turn and observed failing before restoration. | The registry-honesty finding is closed in the direction the bar required: `memory_reason` and `chat_retrieval` declared `labels=("project","status")` while their responses emitted neither, and the **responses** were the false statement — reclassifying them would have made the probe pass by converting a real finding into a documented non-problem. `reembed_backfill_queue` and `chat_history_citations` moved from `labels=()` to the two labels because they now emit them. The probe, its fixtures and its predicates were untouched, and its informational I1/I2 lists are unchanged and still owned elsewhere (T1.60, the escalated retention question). |
| 2026-07-28 | T1.21 | 3 | **D1 RESOLVED as Reading 2 — the graph strip moves INSIDE savepoint B, and doc 05 §8's flowchart is the erroneous artifact.** Decided under delegated authority; T1.21 Step 3 is unblocked. Verified in code first: `delete_by_memory_id` runs at `pipeline.py:533`, outside **both** savepoints (A opens at 553, B at 604), and savepoint B is gated on `status['extract'] in ('ok','partial')`. | Reading 2 is strictly safer on **both** reachable failure paths, and it is what the section's own prose already promises ("a failure in B rolls back only B"). With the strip inside B: a **savepoint-B failure** rolls the strip back with it, so the prior graph survives instead of the memory being left with none; and an **ordinary extraction failure** — the routine path the plan's original D1 write-up omitted, where B is never entered — never runs the strip at all, so the graph and its `technologies` denorm stay intact rather than being silently emptied. Under Reading 1 both paths destroy the prior graph with no error. The idempotency the strip exists for is not weakened but strengthened: strip-and-write inside one savepoint is an **atomic replace**. The costs are real but small — a marginally longer lock hold, and the loss of the strip's incidental self-healing of dangling `memory_ids` on rollback, which `graph_orphan_cleanup` is already the designated backstop for (doc 06 §6). |
| 2026-07-28 | T1.21 | 2 | **Found while resolving D1, and it is a second defect on the same lines: the strip's failure is swallowed.** `pipeline.py:532-538` wraps `delete_by_memory_id` in `try/except Exception` that logs a warning and then **continues to write the new graph on top of the un-stripped old one**. | This defeats the invariant the strip exists to enforce. `CLAUDE.md`: "Always strip prior `memory_id` graph contributions before writing a new set" — a swallowed strip failure produces exactly the duplicate-by-type accumulation doc 06 §6 says re-extraction must not cause, with a log line as the only symptom. It is the same silent-degradation class as the Phase-3 cache-lookup escape already assigned to T1.21, so it belongs in the same task. Moving the strip inside savepoint B makes the fix natural: a failed strip should fail savepoint B, marking `graph=error` and leaving the prior graph intact, rather than proceeding to corrupt it. |
| 2026-07-28 | T1.40 | 2 | **`code_reconcile` reconciles the graph but not the embeddings, so code *search* stays stale for reconciled content until a real commit.** The runner intentionally runs with `llm=None`, so drifted files are re-parsed into the graph and never re-embedded. Reported by the lane, not hidden. | Worth recording as a scope limit rather than a bug: the task's Done-when is "a drifted working tree is detected and reconciled incrementally", and the graph half genuinely is. But a user's symptom is that code search still returns pre-drift results after a reconcile ran and reported success, which is the quiet mismatch between a green operation and a stale answer this corpus keeps finding. Embedding on reconcile would put live model calls on a periodic job, which is a cost decision nobody has made — hence flagged, not fixed. |
| 2026-07-28 | T1.40 | 1 | **Reconcile is effectively scoped to `local_path` repos with no reachable remote.** `CodePipeline.run()`'s own `pull_repo()` fetch can reset away uncommitted drift before reconcile's forced files are processed, for any repo with a working remote. | Narrower than the task text's "each tracked repo" implies, though it does match the scenario the brief described. Recording the real reach so a later reader does not assume drift detection covers remote-backed repos, and so whoever owns the fetch ordering can decide whether reconcile should run before the pull rather than after. |
| 2026-07-28 | T1.13 / T1.40 | 1 | **`CLAUDE.md`'s job list was stale at seven; corrected to nine.** `buffer_flush` (T1.13) and `code_reconcile` (T1.40) were both missing. | Found because T1.40's lane correctly declined to edit the shared baseline from a lane. Both register via the constants `BUFFER_FLUSH_JOB_KEY` and `CODE_RECONCILE_JOB_KEY` rather than string literals, which is *why* the list drifted — a grep for quoted keys undercounts, and that is now noted in the doc so the next reader does not repeat the miscount. Runbook §1 makes `CLAUDE.md` every agent's bootstrap contract, so a stale list there misleads every later task. |
| 2026-07-28 | T1.21 | 3 | **Ruling 1 discharged: doc 05 §8's flowchart amended.** `W --> STRIP --> SA --> SB` becomes `W --> SA --> SB`, with the strip named as savepoint B's first statement; §8's prose gains a paragraph stating why the strip cannot sit in the outer transaction, §8.2 records that B strips before it writes, and §9's "Before writing" becomes "As savepoint B's first statement". | The flowchart was the only artifact placing the strip outside the savepoints, and the section's own prose ("a failure in B rolls back only B") already implied Reading 2. Leaving it would have left the corpus contradicting the code the same ruling just mandated. Pinned by `test_savepoint_b_failure_leaves_the_prior_graph_standing` and `test_extraction_failure_never_strips_the_prior_graph`, which fail if the strip is hoisted back out. |
| 2026-07-28 | T1.21 | 2 | **D2 resolved as option (a): a strip failure fails savepoint B.** The `try/except` that logged a warning and wrote on regardless is gone; `delete_by_memory_id` now raises into savepoint B's handler, which marks `graph=error`, populates `status["error"]` and rolls the strip back. No new `failed_step` value was added. | Option (a) is the only one under which the graph on disk is always exactly one extraction's output; it costs a graph write that might have succeeded, which is the cheap direction of the trade. Option (c)'s `graph_strip` value was deliberately not taken: it adds a `pipeline_failures` vocabulary entry the T1.45 triage UI would have to render, which is a Tier-2 change with no benefit to correctness. Triage sees `graph_write`, which is accurate — the graph step failed. |
| 2026-07-28 | T1.21 | 2 | **D3 resolved as option (a): the `pipeline.{completed,partial,failed}` broadcast moves from `_write_memory` to `process_batch`, emitted after the `pipeline_failures` rows commit.** `_write_memory` no longer broadcasts. **T1.45 inherits this**: the emission order changed, and the wire event now always follows its triage row. | The broadcast could not fire for a memory whose own `_write_memory` raised — that memory got a normalised status dict and a failure row but no wire event at all, so "exactly one broadcast per memory per batch" was false on precisely the path a stepper UI most needs. Centralising it makes the property checkable in one place and orders the event after the row, so a UI reacting to `pipeline.failed` by fetching the failure list cannot race an unwritten row. T1.45 is not built yet, which made this the only cheap moment to change it. |
| 2026-07-28 | T1.21 | 2 | **Carried forward, not fixed here: a canonicalized entity's embedding overwrites the surviving entity's.** `_write_memory` looks the embedding up under `entity["_orig_lower"]` — the *variant's* name — and upserts it onto the *canonical* entity's row, so ingesting `postgresql` (canonicalized onto `postgres`) replaces `postgres`'s stored vector and the ANN centroid drifts to whichever variant was written last. | It sits inside savepoint B, so T1.21 *could* have absorbed it, but the semantics belong to the Phase-3 cache and Phase-4 dedup design (T1.19/T1.20, both merged) rather than to the transactional structure this task owns. It is arguably deliberate (the variant is fresh signal) and arguably a defect (the canonical entity's identity is decided by write order) — which makes it a design question, not a bug fix. Recorded so T1.26 and T1.27 do not each assume the other handled it; it wants its own task. |
| 2026-07-28 | T1.21 | 2 | **Boundary restated for T1.26, T1.27 and T1.36.** T1.21 delivered only the *transactional position* of the strip (inside savepoint B) and that its failure is visible in the per-memory status — **T1.26 still owns what `delete_by_memory_id` deletes**: relation only when no live memory asserts it, entity only when no live memory asserts it and no surviving relation references it, dangling `memory_ids` self-heal, re-extraction idempotence. T1.21 delivered that the `technologies` recompute happens inside savepoint B as one whole-column assignment; **T1.27 owns** lowercase, the GIN index and `_TYPE_OVERRIDES`. T1.21 delivered that `detect_supersessions` is called inside savepoint B after `flush([mem_record])` and that its failure attributes to `graph`; **T1.36 owns** rules 1-6, the `(created_at, id)` tie-break, the per-target speculative gate, the atomic flip, and **widening the trigger predicate from `REPLACES` to `REPLACES_FAMILY`** — still narrow in both `pipeline.py` and `supersession.py`, deliberately left as one behaviour in two files that must change together. T1.21 emitted no `sources_changed` event and added no provenance-no-op guard; that stays **T2.47's**. | Three tasks cover mechanisms that physically live inside savepoint B, and without the split stated in one place each would assume another delivered it. Moving the strip touches T1.26's subject, so the split is stated explicitly: T1.21 changed **where** the strip runs, T1.26 owns **what** it deletes and the self-healing semantics. |
| 2026-07-28 | T1.20a | 2 | **New task: a canonicalized entity's embedding overwrites the survivor's.** Raised by T1.21's planning pass and again by its execution; both correctly declined to fix it in lane. `pipeline.py` looks the embedding up under the **variant's** name and writes it against the **survivor's** row. | Small per write and compounding over time, which is why it earns a task rather than a note. Dedup merges only at ≥0.85 cosine, so any single wrong vector is a near neighbour — but every re-extraction that merges a different variant rewrites the canonical vector again, so the survivor's embedding random-walks among its variants. That degrades exactly the two mechanisms the entity partition exists for: the `(name_lower, fingerprint)` cache ends up caching a value keyed to a name it was not computed from, and Phase 4's ANN probe compares future candidates against a drifting target. The acceptance deliberately includes a **two-pass** test, because a single-pass one cannot see the compounding half. |
| 2026-07-28 | T1.21 | 2 | **D1's resolution is now reflected in `CLAUDE.md`'s Phase-5 description**, which still described the strip as running before the savepoints. The baseline now states that the strip runs **inside savepoint B**, that strip-and-write is one atomic replace, and that a failed strip fails B rather than being swallowed and written over. | T1.21's lane flagged the imprecision and correctly left the shared baseline alone, since it was outside the lane's file list. Runbook §1 makes `CLAUDE.md` every agent's bootstrap contract, so leaving it describing the arrangement that silently emptied a memory's graph on two failure paths would have taught the wrong invariant to every later task. |
| 2026-07-28 | T1.45 | 1 | **T1.45 inherits a changed emission order:** T1.21 resolved its D3 as (a), moving the `pipeline.*` broadcast to `process_batch`. | Recorded because T1.45 builds the pipeline stepper over that broadcast, and its Done-when requires the stepper to reflect real per-phase status **including `partial`**. A stepper written against the old emission point would mis-sequence. Pairs with the already-recorded finding that `GET /pipeline-logs` queries an event type nothing emits — T1.45 should treat both as one piece of work on its signal source. |
| 2026-07-28 | T1.48 | 1 | **Closed a real honesty gap the task text did not name:** the Articles detail page emitted a raw `fact_set_hash` fingerprint **unconditionally**, and it is now advanced-only — while the stale label beside it stays in **both** modes. | The distinction is exactly the one invariant 14 draws and the reason this counts as in-scope rather than scope creep: a **fingerprint is technical detail** that `simple` exists to collapse, and a **stale label is an honesty signal** that `simple` may never hide. Getting it backwards in either direction is a defect — hiding the label would conceal that the data is stale, and showing the hash makes `simple` mode not simple. The lane also found the simple/advanced infrastructure already correctly wired by earlier work, so the task's real deliverable became the 8-test suite proving the invariant holds *and breaks when violated*. |
| 2026-07-28 | T1.46 | 1 | T1.46 binds the in-nav `/code/repositories` route rather than the orphaned legacy `/repos` page. | Recorded so the legacy page's status is a known question rather than a surprise for T1.59, which owns binding the rest of the Code section. An orphaned page that still renders demo fixtures is precisely what T1.58's lint sweep is meant to surface; if `/repos` is dead it should be deleted, and if it is reachable it needs binding — but that is T1.59's call, not this task's. |
| 2026-07-28 | T1.24d | 2 | **G-B must not cite relation F1 as evidence for Stage 4, and T1.24f must record Stage 4 as _unmeasurable on this corpus_ rather than _zero contribution_.** Re-measured with the final code: dropping any one Stage-4 pass moves `rel_full` by `remap_to_valid_entities` −0.045 gold / −0.022 held-out, `downgrade_future_to_mentions` and `drop_date_misuse` −0.012 gold / 0.000 held-out, and **0.000 with 0/26 and 0/10 memories changed for the other seven** — `drop_edges_to_negated`, both REPLACES gates, `suppress_temporal_edges`, both direction validators and the Stage-4 `filter_event_edges`. The substitute guard is `tests/test_relation_gating.py`: per-gate behavioural tests authored from each pass's docstring and its doc 06 §4 S4 box, nine mutation proofs, and an order-insensitive whole-chain diff over all 36 memories. | The task's third Done-when box, "relation F1 does not regress", is satisfiable by deleting 70% of the stage — it is a necessary condition and nothing more. The seven passes it cannot see are exactly the ones whose failure mode is a false `REPLACES` reaching `detect_supersessions`, which flips a live memory out of the default `active` view: a silent data-visibility loss, not a crash. This mirrors the ruling already standing for Stage 3 (2026-07-27, T1.25) and already routed to T1.50. "Unmeasurable" and "zero contribution" are different claims and only one of them is true. |
| 2026-07-28 | T1.24d | 1 | **`drop_edges_to_negated` is REACHABLE; the planning pass's unreachability finding is withdrawn and doc 06 §4's S4 box D1 needs no correction.** Falsifying input: `"The dashboard was rebuilt without ui/theme.css in the bundle."` with the model listing `ui/theme.css` as an entity. Two file-path vocabularies disagree — `_filter_noise`'s `_FILENAME_PATTERN` lists ~24 extensions while the rescue's `_FILE_PATH_RE` lists ~60, so `css`/`scss`/`lua`/`html`/`svg`/`proto` paths are **not** dropped as noise and reach `_filter_negation_only`, which records the name in `negated_names`. A two-character leading directory keeps `_filter_hallucinated_names` under its two-significant-token threshold. `_rescue_file_path_entities` — the one rescue that is not negation-aware — then re-adds it, so the endpoint is valid again when the remap runs and only this pass removes the edge. Pinned by `test_the_negated_entity_reaches_the_pass_with_a_live_edge`, `test_only_this_pass_removes_the_edge_to_the_negated_path` and `test_a_negation_does_not_mint_a_replaces_against_the_denied_entity`. | The plan's Step 5 required a genuine falsification attempt before concluding, and the attempt succeeded: the structural argument's premise that "`_filter_noise` drops file paths first" holds only for the extensions `_FILENAME_PATTERN` happens to list. No pass is deleted, no pass is reordered, and the resolution the controller was asked to choose is moot. The same construction with a `REPLACES` edge shows the consequence the pass prevents: without it, `ui/tokens.css REPLACES ui/theme.css` survives to supersession on the strength of a denial. |
| 2026-07-28 | T1.24d | 1 | **Two of the plan's three candidate ordering constraints were declared, a third was replaced, and the plan's stated mechanism for it does not hold.** Declared: `remap_to_valid_entities` before `drop_edges_to_negated`; `remap_to_valid_entities` before `suppress_temporal_edges`; `gate_replaces_selection` before `gate_replaces_requires_verb`. **Not** declared: `gate_replaces_selection` before `validate_directions`. Its stated mechanism — the two pattern families assigning source/target in opposite order, so a reversal can invert a correct edge — cannot fire, because `_MIGRATION_RE` suppression means a firing selection gate excludes exactly the reversed-role `from X to Y` patterns; the only surviving `_REPLACES_PATTERNS` in that state (`chose`/`picked`/`went with`/`decided to use`) carry the **same** `("source","target")` roles as `_IMPROVES_PATTERNS`. Isolating that single move yields a *better*-oriented edge, not a worse one. The real load-bearing order is against the **verb** gate: run it first and it reads the unsupported `REPLACES` as bare, collapsing a genuine improvement claim to `RELATED_TO` before the selection gate can reclassify it. | The plan's own rule: "a constraint that cannot be broken into a failure is a comment, not a contract." Declaring the candidate as written would have encoded a mechanism that does not exist in a `why` string that future readers would trust. Constraints only, so the pinned registry length stays 31. |
| 2026-07-28 | T1.24d | 2 | **The plan's claim that `drop_edges_to_negated` is unreachable is FALSIFIED, and doc 06 §4's D1 box is correct after all.** T1.24d's lane produced the falsifying input: `_filter_noise`'s filename pattern lists ~24 extensions while the rescue's file-path pattern lists ~60, so a `.css` / `.scss` / `.lua` / `.svg` path is **not** dropped as noise, reaches the negation filter, and is then re-added by `_rescue_file_path_entities`, the one rescue that is not negation-aware. No controller decision is owed. | This is the brief's Ruling 1 working as intended: the lane executed without a separate plan review on the explicit understanding that **it** was the adversarial pass, and it overturned the plan's own conclusion rather than implementing it on trust. The same construction demonstrates the consequence — without the pass, a `REPLACES` minted from a **denial** reaches supersession, which flips a live memory out of the default view. A pass the corpus cannot measure turned out to be load-bearing, which is precisely the case the ledger's F1-blindness entry warns about. |
| 2026-07-28 | T1.24b | 1 | **Out-of-lane finding, routed:** `_filter_noise`'s filename extension list (~24) and `_rescue_file_path_entities`'s path extension list (~60) diverge, so the two passes disagree about what counts as a file path. | It is the mechanism that makes `drop_edges_to_negated` reachable, so it is not simply a tidy-up — closing the divergence without understanding that would silently remove the negation guard's only live path. Belongs to T1.24b as Stage 1's owner. Whoever takes it must decide deliberately whether the lists should converge at all, and must not do so by narrowing the rescue. |
| 2026-07-28 | T1.24d | 1 | The lane **declined one of the plan's ordering constraints with a measurement** — its stated mechanism cannot fire, because migration-verb suppression excludes exactly the opposite-role patterns it depends on, and the isolated reversal produces a better-oriented edge rather than an inverted one. It declared three constraints it could each break into a wrong answer instead. | Recording it because declining a plan's constraint is the harder call than adding one, and the substitution is what makes it defensible: three constraints demonstrably breakable into wrong answers are worth more than one whose stated mechanism is unreachable. Step 9 was skipped per Ruling 4 with its reason recorded — the per-target scoping rule does not transfer to the two-endpoint gates without a design decision no doc settles, and the only measurable gate has a single supporting gold memory, which the anti-fitting standard forbids tuning against. |
| 2026-07-28 | ENVIRONMENT | 1 | **Postgres `max_connections` raised 100 → 400.** T1.24d's lane hit a red floor (154 failed, 44 errors) whose every named test passed in isolation immediately after, with two subsequent full runs clean — connection exhaustion from concurrent lanes, not a defect. | Five concurrent lanes each holding a SQLAlchemy pool (default 5 plus up to 10 overflow per engine) can reach 75 connections before the app, benchlib and the controller's own runs are counted. The failure mode is the expensive kind: a red floor that looks exactly like a real regression, costing a lane a full re-run and risking a misdiagnosis in the other direction. Raising the ceiling removes the class rather than the symptom. |
| 2026-07-28 | T1.26 | 2 | **The strip now reconsiders the endpoints of the relations it just deleted, not only the entities the memory asserted.** `delete_by_memory_id`'s entity-orphan candidate set was `ent_ids` (the entities carrying this `memory_id`); it is now `ent_ids` ∪ the `source_entity_id`/`target_entity_id` of every relation the same call deleted. Both guards are unchanged — an entity still goes only when no live memory asserts it AND no surviving relation references it — so this widens what is *considered*, never what is *permitted*. **Affects T1.28:** `prune_orphan_entities` is now a backstop for ghosts arriving by other routes only; it is no longer compensating for a ghost the strip itself created. | A memory may assert a relation whose endpoint entity it does not itself assert (`create_relationship` resolves endpoints against all entities, so an endpoint another memory created is reachable). When that other memory is stripped first, the endpoint survives solely because the relation references it. Re-extracting the asserting memory then deletes the relation — and the old candidate set never looked at the endpoint, leaving an entity with no live asserter and no relation: exactly the stale ghost Phase-4 ANN dedup collapses fresh entities onto. Ruling 4 requires the strip to be correct on its own rather than correct-once-the-sweep-runs, so this belongs in the strip. Proven by `test_the_strip_leaves_behind_no_entity_it_orphaned_itself`, which fails against the narrow candidate set. |
| 2026-07-28 | T1.17 | 2 | The prompt strip landed **small and deliberately**: 4 rules stripped, 1 stale statement corrected, ~44 kept (35,665 → 35,188 chars; `775ca7c45ed9a06a` → `f59a62d1be7273a8`). Doc 05 §6's "strip every rule the passes already enforce" assumes deterministic twins that mostly do not exist yet. | Policy applied: strip only on demonstrated full subsumption by an existing pass or by the schema string. Measured: `_NOISE_NAMES` carries 10 of rule 2a's 28 builtins; nothing covers rule 2b or rule 9h-dir; `weight` (rule 14) has no downstream enforcement. Per-rule evidence in `docs/eval/2026-07-28-T1.17-prompt-rule-audit.md`. |
| 2026-07-28 | T1.24b–e | 2 | **Six pass gaps handed over**, each a prompt rule carrying work its named pass does not do: rule 2a's 18 missing builtins in `_NOISE_NAMES`; no config-value/CSS-token filter (2b); no `CAUSES` synthesis or re-orientation (9h-dir); no soft-dependency `DEPENDS_ON`→`USES` downgrade (9c-soft); `_filter_noise`'s article guard deletes `the web app` rather than rewriting it to `web app`, so rules 4 and 7b work against each other; `_DATE_ISO_RE` cannot match the non-ISO date forms rule 9f names. | Closing any one makes the corresponding rule strippable under the same policy. Until then the rule stays in the prompt and the F1 gate depends on it. |
| 2026-07-28 | T1.17 | 2 | The extraction **memory-type paragraph contradicted the taxonomy** and was corrected, not stripped: it said "choose exactly one of these seven" while `MEMORY_TYPES` has been nine since T1.23 and the schema string has been offering all nine on every call, and it forbade `debug`/`workflow`/`session` although `normalize_memory_type` maps `workflow → procedural` and `session → episodic`. | T1.23's 2026-07-27 amendment explicitly deferred the prompt-side edit for the widening to T1.17. `memory_type` is not scored by the F1 bench, so the correction carries no measured F1 risk; leaving the prompt and the schema disagreeing about the vocabulary was the real defect. |
| 2026-07-28 | T1.17 | 2 | The F1 bench's **absolute number was measuring a request the code no longer sent**, and now is not. The cache key covered the system message only, so the 9-type schema riding the user message never keyed; the key now covers the whole assembled request and `.cache/manifest.json` makes `--algo-only` exit non-zero naming the mismatching field. The bench also assembles through `ExtractionService.build_extraction_request` — the pipeline's own function — rather than a hand-rolled copy. | T0.03: the harness measures the shipping path or it measures nothing. Recorded in the gate ledger's G-B section with the five-arm decomposition. |
| 2026-07-28 | T1.50 | 2 | Confirmed, not new: T1.17's prompt change invalidates `benchlib`'s retrieval cache (~94 cached extraction calls) **and the ingested graph the retrieval accuracy numbers were computed over**. T1.17 did not pay it and did not re-run the retrieval eval. | Already recorded by the controller in the gate ledger; restated here so the amendment log carries the scheduling consequence next to the task that caused it. |
| 2026-07-28 | T1.17 | 2 | **Done-when boxes 1–3 were already satisfied by shipped code** before the task ran (`can_merge`, the two-call fallback, the merged schema toggle, seed forwarding). The task's real deliverables were the bench's shipping-path rework, the prompt strip, and the live re-record. Box 3 is now pinned by a real test rather than by the seed being forwarded. | Recorded so a reviewer checking the boxes against the diff does not read the pre-existing mechanisms as this task's work. |
| 2026-07-28 | T1.45 | 1 | **Ruling 1 discharged by repointing, not by adding an emitter.** `GET /pipeline-logs` now reads `event_type = 'extracted'` instead of `'pipeline'` (a value outside `EVENT_TYPES` that nothing ever wrote). `extracted` already carries one row per memory per batch, journalled by `process_batch` with the same status dict the `pipeline.*` broadcast carries plus `outcome` — no `events.py` vocabulary change was needed. Guarded by `test_pipeline_logs_reads_extracted_events` / `test_pipeline_logs_ignores_other_event_types`, both mutation-proven (reverting the filter to `'pipeline'` fails the first test). | T1.39's `repo_indexed` precedent showed the emitter side; here the emitter already existed and only the reader was wrong, so the cheaper of the ruling's two options applied. Recorded so a later reader does not assume a new `EVENT_TYPES` entry was added for this task. |
| 2026-07-28 | T1.45 | 2 | **The real stepper mirrors Phase 3/4 (entity embed, dedup) from `extract`'s outcome rather than inventing a signal for them.** `pipeline.py`'s status dict carries exactly `embed`/`extract`/`vector`/`graph` — no per-memory field for entity embed or dedup exists, because both are batch-level checkpoints whose failure already escapes as the `process_batch` backstop (`embed`/`extract` = `"unknown"`, `vector`/`graph` = `"error"`). `use-pipeline-runs.ts`'s `impliedStep` renders those two steps `"ok"` whenever `extract` is `"ok"`/`"partial"` and `"skipped"` otherwise, since reaching that outcome is only possible if they already ran without escaping. | Considered and rejected: rendering them as a fixed `"ok"` regardless of `extract`, which would lie on the batch-backstop path; and adding a demo-only 5th column, which would make the demo and real code paths diverge in shape rather than in data source. Guarded by `use-pipeline-runs.real.test.tsx`'s batch-backstop case. |
| 2026-07-28 | T1.45 | 2 | **Two fields the demo fixture shows have no real-mode source and are rendered as `null`, never fabricated:** `DemoJob.max_run_seconds` (the registry's ceiling is not in `JobItem`'s response shape) and `DemoJob.next_run_label` (no cron-next calculator exists client-side and the API returns none). Both widened from non-nullable to `T | null` in `demo/types.ts`; `JobConfigDialog` skips the `max_run_seconds` row entirely when null instead of printing `null`, and the header's `next_run_label` span renders empty. `JobTriggerResult`'s `lock_held_since` was widened the same way — the real 409 has no lock-acquisition timestamp in its response body. | The alternative (approximating either value client-side) would have created a number that looks authoritative but is not derived from anything the server asserts — exactly the class of surface this corpus keeps finding. `frontend/src/demo/data/jobs.json` still lists seven jobs, not nine (`buffer_flush`/`code_reconcile` missing) — left alone as out-of-lane (`src/demo/data/**` is not in this task's file list); real mode is unaffected since `useJobBoard` reads whatever `GET /jobs` returns, with no hardcoded count. |
| 2026-07-28 | T1.45 | 2 | **`lib/api.ts`'s `apiFetch` now throws a typed `ApiError` (message + `status`) instead of a bare `Error`.** Additive and backward-compatible (`ApiError extends Error`) — needed because ruling 4's 409-must-render-as-busy contract has no other reliable signal: the job-trigger route's `HTTPException(409, ...)` body has a `detail` key but no structured `{accepted:false}` shape to branch on, so message-sniffing was the only alternative. `use-job-board.ts`'s `trigger()` catches `ApiError` with `status === 409` and resolves `{ok:false, status:409, lock_held_since:null}`; any other status rethrows. Mutation-proven: changing the checked status to 410 makes a 409 escape as an unhandled rejection instead of resolving busy. | `frontend/src/lib/api.ts` sits outside `frontend/src/features/activity/**` but is what the brief calls "the shared query layer" — every `hooks/api/*` call site funnels through it, and the change is additive so no existing caller's behavior changes. Flagging the boundary call explicitly rather than silently treating "shared query layer" as license for unbounded lib edits. |
| 2026-07-28 | T1.27 | 1 | **The Phase-5 recompute now reads the graph instead of accumulating from the extraction dict.** `_write_memory` built a `tech_names` set while looping the entities it was about to write; it now assigns `mem_record.technologies = await graph_repo.technologies_for_memory(memory_id)`, a new repo method reading `SELECT DISTINCT lower(name) FROM entities WHERE :mid = ANY(memory_ids) AND entity_type = ANY(TECH_TYPES)` inside savepoint B, after the strip and after every `create_entity`. Value is unchanged today; the property gained is that the column is a *projection* of the post-strip, post-write graph rather than a set built from what the writer intended to store, and `lower()` now guards the denorm boundary rather than being assumed of the write path. | Ruling 3 assigns T1.27 "the recompute, including that it reflects the post-strip, post-write entity set rather than a stale read". An accumulator is only equal to the graph while every step between intent and row stays lossless; a projection is equal by construction. `lower()` at the denorm is the cheap half of the invariant that costs the most when it drifts — `test_a_denorm_that_kept_original_casing_stops_supersession` shows the failure is a supersession that silently never fires. |
| 2026-07-28 | T1.27 | 2 | **`supersession.py` gained `candidate_stmt(...)`, the candidate SELECT extracted from `detect_supersessions` verbatim. Affects T1.36**, which owns that file's rules and will edit the same lines. No rule changed: same predicates, same order, same tie-break; `detect_supersessions` now calls it. | Ruling 1 requires proving the GIN index is *used by the supersession query plan*, not merely present. An EXPLAIN over a hand-rewritten copy of the query proves nothing about the query that runs, so the executed statement had to become addressable from a test. Flagged Tier 2 rather than Tier 1 because the edit lands in T1.36's file. |
| 2026-07-28 | T1.28 | 1 | **No production code changed; the deliverable is `tests/test_graph_orphan_cleanup.py`.** All three Done-when properties already held — `prune_orphan_entities` guards on no-live-memory AND no-surviving-relation, and `app/main.py` registers the job at `0 * * * *` with `min_interval_seconds=60` under the registry's shared per-job lock — so the missing artefact was the proof, not the mechanism. Each property is now mutation-proven: dropping the surviving-relation guard, replacing the no-live-asserter predicate with a live-asserter one (a "scoped" sweep), and re-registering the job daily each turn a distinct test red. The registration values are read out of `app/main.py` by `ast` rather than from a live registry, because the `Job(...)` literals live inside `lifespan` and no test enters it. | The task carries `Tag: exists-today`, and its real risk is the sweep quietly degrading later — a scoped or relation-blind sweep still passes a smoke test and only shows up as Phase-4 dedup collapsing a fresh entity onto a ghost, months on. Recorded so the next reader does not go looking for the code change this task "should" have made. |
| 2026-07-28 | T1.28 | 2 | **Ruling 5 written into the test module's docstring rather than left as brief-only context.** `prune_orphan_entities` is unscoped *because* a ghost's last asserting memory is already gone, so there is nothing to scope by and a scoped pass cannot reach it at all — it is a maintenance sweep over the graph, not a surface returning rows to a caller, and the read-path isolation rules do not bind it. **Relevant to any later isolation work**: this sweep is a standing, deliberate exception and must not be "fixed" by adding a project or status filter. | The isolation probe classifies front doors; a job is not one. Without the exception stated at the code, a future isolation pass reads an unfiltered full-table DELETE as an oversight and scopes it, which silently restores exactly the stale-ghost dedup failure the job exists to prevent. |
| 2026-07-28 | T1.42a | 2 | **Done-when box 3 is recorded as *satisfied by construction*, not met by a discriminating test.** The box asks for a test that fails if `source` resolution ran post-validation. That failure mode existed only because `MemoryCreate.source` stamped `"api"` during validation; deleting the default (`str \| None = None`, the task's own root fix) removes the erasure, after which pre- and post-validation resolution are **observationally equivalent** for every input class and the mandated mutation passes instead of failing. Pinned instead by `test_memory_create_source_has_no_default`, which fails by name if a default returns. | Meeting the box as literally written had two exits and both were worse than recording the truth: the plan's discriminator table claims an explicit `"api"` should *win* over `X-Darkmem-Client`, which inverts the shipped sentinel (`tests/test_client_identity.py:38`, doc 12 §5, `CLAUDE.md`) — so an agent could satisfy the table only by breaking the sentinel the task exists to harden — or, on finding the mutation refused to fail, by quietly weakening the criterion. The raw-dict discipline in `resolve_entry_identity` is kept regardless, for reasons independent of the default: the MCP tool signature is `entries: list[dict]` so there is no model to interrogate, and a later `default_factory` or model validator would silently reintroduce the erasure behind a post-hoc reader. |
| 2026-07-28 | T1.42a | 2 | **REST-door `origin_key` values change, and the change is a historical discontinuity to record.** `resolve_origin_key` is untouched — signature, body and docstring — but its `source` input is now the *resolved* label instead of `MemoryCreate.source`'s stamped `"api"`. A REST caller sending `X-Darkmem-Client: dashboard` moves from `unknown:api:<project>` to `unknown:dashboard:<project>`. | This is the intended fix of a wrong input, not a change to T1.11's logic, and it is guarded three ways (`tests/test_origin_key.py` unmodified, a signature assertion, and a two-call determinism assertion re-proving the per-request-random prohibition of doc 05 §12). The **discontinuity** is the part worth recording: one physical origin now reads under two keys across the boundary, so when E2's `COUNT(DISTINCT origin_key)` lands, a tool spanning the change reads as two origins — and overcounting is the direction doc 05 §12 forbids. No live consumer exists today (nothing in `backend/app` counts distinct origins), which is why it is recorded rather than migrated. |
| 2026-07-28 | T1.42a | 3 | **ESCALATED, not resolved — doc 12 §4's `excluded` key table still contradicts the tree, and T1.42a is the task that puts the envelope on every surface.** §4 and §459 fix `excluded` as `{by_project, by_status, by_context_conflict}`; the tree ships reason-named keys (`memory_type`, `source`, `technologies`, `tags`, `not_found`) because the T1.29-series pushdown scopes project and status in SQL and `by_context_conflict` has no implementation. `ResponseEnvelope.excluded` is an open `dict[str, int]`, inheriting T1.33's ruling. | Either doc 12 §4 is amended to describe reason-named keys, or a task is named that makes the doc's three keys real. A corpus-level decision, and the moment it stops being a forward-looking sketch is exactly now — an SDK built against the doc's table would find keys that never appear. Decorative always-zero keys were deliberately not reserved: an always-zero honesty counter reads as evidence that a check ran. |
| 2026-07-28 | T1.42a | 3 | **ESCALATED, not resolved — doc 12 §5 describes `source` resolution as a one-door mechanism the task requires on two.** Implemented as the plan's reading 1: per-door fallback **and** per-door sentinel (`REST_FALLBACK_SOURCE = "api"` with an explicit `"api"` counting as unspecified; MCP unchanged on `"mcp"`). Doc 12 §5's verbatim chain terminates in `mcp` for every door and its §5 prose still says `MemoryCreate` "stamps its `api` default during validation" — no longer true after this task. | Reading 2 (one `"mcp"` fallback everywhere) would label every unattributed HTTP capture as MCP-sourced, a false attribution on the column the UI filters and colours by; reading 3 (`"api"` as a non-sentinel default) recreates the exact masking hole the sentinel closes. Reading 1 is the only defensible one, but **it is not what the doc says**, so the doc needs amending by whoever owns it. `docs/design/` is outside this lane's file list, so no edit was made. `CLAUDE.md`'s MCP section carries the same now-stale sentence about the `api` default and needs the same correction. |
| 2026-07-28 | T1.42a | 2 | **The `projects` table now has a reader and still has no writer.** `app/repositories/project_registry.get_applies_when_default` lands tier 3 of the context chain (`properties->'applies_when_default'`), returning `None` for an absent row, an absent key, and an empty object. No ORM model and no writer were added. | Tier 3 is therefore structurally present and permanently empty until some task owns project-registry writes; T1.65's project switcher is the natural home for the UI half, and nothing in the current graph owns the backend half. Recorded so the chain's fourth tier is a known gap rather than a mystery — and so nobody reads "the project default never wins" as a resolution bug. |
| 2026-07-28 | T1.42a | 2 | **The non-traced paginated route deliberately keeps `envelope: null` rather than gaining a `page`-only envelope.** That path drops rows through `_matches_schema_v2_filters` without counting them, so an envelope there would report `excluded: {}` — "nothing was dropped" — about a path that never measured. | An absent envelope says "not measured"; an empty one reads as evidence (invariant 14). T1.33 deliberately structured the exclusion bookkeeping into the `with_trace` path alone so a caller who never asks for a trace never pays for it, and re-deriving it here to fill an envelope would undo that. **T1.42b inherits this**: conforming the route means either counting on that path or keeping the null, not defaulting an empty envelope in. |
| 2026-07-28 | T1.42a | 2 | **`POST /memories/search` and MCP `memory_search` stay bare lists; only the paginated route echoes the context.** Both accept the resolved wire format (`MemorySearchRequest.context`), neither has a slot for an envelope. The REST case was the plan's Open Question 4; **the MCP case was not raised and is raised here** — giving MCP `memory_search` a `ContextEcho` is a breaking shape change for every MCP consumer, and the plan's own boundary table assigns MCP surface conformance to **T1.42c**. | Also recorded: `search_memories` deliberately does **not** run the chain, because resolving a value the response cannot carry would spend a project-registry read per search for nothing. The asymmetry is between routes that can report the resolution and routes that cannot — not between doors. |
| 2026-07-28 | T1.24e | 2 | **Stage 5's per-pass ablation: half the stage is invisible to this corpus.** Measured over both gold sets against the T1.17 re-record (gold `0.912/0.971/0.857/0.857`, held-out `0.967/0.967/0.950/0.950`), dropping one pass at a time from `PASS_REGISTRY`. `drop_uses_when_deployed_on_exists`, the **Stage-5** `filter_event_edges` and `drop_unlinked_dates` produce **bit-identical output on all 36 memories when deleted entirely** (0/26 and 0/10 memories changed). `drop_uses_when_replaces_exists` moves one gold memory (`e25`, −0.011 on removal) and nothing held-out; `dedup_by_target_predicate` moves one gold memory (`e14`) and nothing held-out; only `fan_out_coordinated` is substantially visible (−0.097 gold, −0.117 held-out, 3/26 and 1/10). **G-B must not cite F1 as evidence for the three invisible passes**, and T1.24f's "per-pass contribution recorded" box must record them as **unmeasurable on this corpus**, not as *zero contribution*. | Third independent confirmation of the same corpus limit already recorded for Stage 3 (T1.25, all three passes) and Stage 4 (T1.24d, seven of ten): "relation F1 does not regress" is a necessary condition and nothing more. The substitute guard landed with the task — `tests/test_collapse_fanout.py`, 49 tests, with six named mutation proofs (§ report). The most valuable is `_drop_unlinked_dates`'s `fullmatch` → `search`: a one-word change the bench rates at exactly 0.000 on both sets that would delete every dated event entity in production. |
| 2026-07-28 | T1.24e | 2 | **The rescue-first tie-break in `_prefer_relation` was over-scoped, and on this corpus it fired exactly once and fired wrong. Narrowed to direction-grounded rescue triples.** The rule was "any `properties.rescue` beats the LLM, then weight". Its own docstring justified that with "regex-grounded against the source text, so its directional claim is more reliable" — but only `_rescue_relations_replaces` matches a *directional* pattern (from-X-to-Y, Y-supersedes-X) and stamps `properties.pattern`; `_rescue_relations` and `_rescue_relations_subject_tracking` ground *adjacency* and infer the subject from position. On gold `e14` ("The gateway's JWT auth follows RFC 7519 and signs tokens with RS256") the subject-tracking rescue took the possessive modifier `gateway` for the subject head `JWT auth` and displaced the correct `JWT USES RS256` — failure mode 1 in the dedup's own docstring, re-introduced by the rule meant to improve it. New predicate `_is_direction_grounded`; weight decides otherwise. **Gold relation F1 0.857 → 0.883 on both relation dimensions; held-out unmoved at 0.950; entity dimensions unmoved; `e14` is the only memory whose output changes across all 36.** | Recorded as tier 2 because it moves a number G-B will cite and changes a **recorded bug fix**. The justification is structural and independent of `gold.json` — the docstring's premise is false for two of the three emitters, readable from the code alone — and the +0.026 is corroboration, not the argument; that distinction is the anti-fitting standard ratified 2026-07-27, under which a +0.030 was declined. **The corpus cannot distinguish this narrowing from a full revert of the recorded fix**: V2 (narrowed), V3 (family-scoped) and V4 (weight-only) all score gold `0.883` / held-out `0.950`. The separating experiment is a test, not a bench run — `test_weight_alone_would_have_kept_the_backwards_edge` shows the rescue triple carries the *lower* weight (0.85 against 0.9), so V4 keeps the backwards `REPLACES` that `detect_supersessions` would then act on, while V2 keeps the correct one because the winning triple carries `pattern="from-to"`. Mutation M3 (delete the grounding branch) fails four tests across two files. |
| 2026-07-28 | T1.24e | 1 | **`_fan_out_coordinated`'s cross-process ordering defect is fixed** (`sorted(g)`), closing the tier-2 row opened for T1.24e on 2026-07-27. Reproduced first, exactly as recorded: four `PYTHONHASHSEED` values over gold `e10` and held-out `h3` gave two distinct output orderings each, with identical sets. | The guard needed strengthening twice, which is the part worth recording. A three-member coordinated group has only six possible orderings and the first two seeds chosen **agreed even with the defect restored** — the mutation proof caught a guard that was green against the bug it existed to catch. The shipped test uses a five-member group (120 orderings) and six fixed seeds, and was re-verified to produce six distinct outputs with the defect restored. Sets and every F1 number are unaffected either way, so the F1 bench could never have seen this; the cross-process comparison of the output **list** is the only instrument that can. |
