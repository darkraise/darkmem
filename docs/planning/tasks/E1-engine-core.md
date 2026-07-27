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
| 2026-07-27 | T1.10 | 1 | **UUIDv7 source decided: the `uuid6` package, not a Python-floor raise.** Added to `pyproject.toml`, lock regenerated with the documented universal command; `app/utils/ids.py::new_id()` is the single call site. | The task required a decision rather than an assumption. `uuid.uuid7` is 3.14+; `requires-python` is >=3.12, this venv runs 3.13.5 and `backend/Dockerfile` builds on `python:3.12-slim`. Raising the floor is a toolchain migration — image, universal lock, and a 3.14 wheel for every dependency including twenty-odd tree-sitter grammars — and would break this environment immediately, for one function. One call site keeps the later swap to one import. Lock diff was exactly the two expected lines: no pywin32 leak, no uvloop drop. |
| 2026-07-27 | T1.10 | 1 | `origin_key` rides `memory_buffer.metadata`, not a new column. | Doc 04 §8.6 enumerates the table's columns and states the rule for everything else: caller-supplied fields beyond those columns ride the `metadata` jsonb and replay verbatim, and the buffer may never silently drop a captured field. Adding a column would diverge from the schema owner's table for a value nothing filters the buffer by. Tested by asserting every replayed field round-trips, including unknown future ones. |
| 2026-07-27 | T1.06 | 2 | Doc 04 §8.1's `BEFORE UPDATE OR DELETE OR TRUNCATE` forbid-trigger is **three** triggers, not one, and the doc is amended to say so. TRUNCATE fires only statement-level so it cannot share a trigger with the per-row UPDATE/DELETE guard; and a statement-level TRUNCATE trigger on a partitioned parent does not cascade to children (row triggers do), so every monthly child needs its own. | Measured on PG 17, not inferred: with only the parent's triggers, `TRUNCATE events_202607` succeeds and erases a month of the audit trail — the append-only invariant would have read as enforced while having a one-statement hole. The decision doc 04 makes (structural, role-agnostic, no `REVOKE` split) is unchanged; only its mechanism description was wrong. |
| 2026-07-27 | T1.06 | 1 | Every partition-creating path goes through one SQL function, `events_ensure_partition`, rather than each site writing its own `CREATE TABLE … PARTITION OF`. Boot reconciliation added, plus a maintenance arm on `pipeline_failure_cleanup` (doc 04 §8.1 names that job). | The per-child TRUNCATE guard is easy to forget at one of three call sites, and forgetting it is silent. Boot-only reconciliation is also insufficient: a process that boots in January and runs into March outlives its partitions, and a RANGE parent rejects every insert with no child to land in — so journaling would stop rather than degrade. |
| 2026-07-27 | T1.06 | 1 | Three existing tests cleaned up committed `events` rows with `DELETE FROM events`, which the forbid-trigger now refuses. Removed both cleanups and relaxed one exact-list assertion in `test_audit_endpoint.py` to a set assertion. | The tests were asserting "no earlier test left a row behind"; what the endpoint actually guarantees is that its action filter returns no *other* action. Rows genuinely accumulate for the life of the database now, so the set form is both correct and what production looks like. |
| 2026-07-27 | T1.23 | 1 | Fixed `scripts/gen_progress.py`, which rewrote the rollup's hand-edited Gate cell back to its literal — regenerating turned `G-A CLEARED 2026-07-27` into `G-A open`. It now carries that cell forward the way it already carries the five per-task state columns. | Every agent is told to regenerate after logging an amendment (runbook §5), so the next regeneration would have silently un-cleared a gate that was actually met — the tracker reading as if the evidence run never happened. |
| 2026-07-27 | T0.11 / T1.23 | 1 | Discharged the trigger-enumeration obligation E0 left open: doc 04 §12 and doc 19 §2 now name three trigger kinds. Also corrected `baseline-schema-inventory.md` §4.3/§9.2, which named three `touch_updated_at` triggers where the baseline authors **four** (it omitted `documents`). | The inventory is the schema work order; a divergence between it and the migration is a defect in one of them. Here the baseline was right — the rule is per-table and `documents` carries `updated_at`. |
