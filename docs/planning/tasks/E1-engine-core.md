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
