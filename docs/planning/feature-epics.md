# darkmem — Feature Epics (planning bridge)

**Status:** planning bridge, dated 2026-07-24. Spec:
`docs/superpowers/specs/2026-07-24-feature-epics-and-mockups-design.md` §3.

## Purpose

This document elaborates `docs/design/20-roadmap-and-sequencing.md` into a nested
epic → feature tree that the implementation-planning phase consumes directly: one epic
per roadmap lane, each stating its goal and its advance gate as the definition of done,
with a features table under it whose rows a plan writer turns into TDD tasks. It is a
planning bridge, not a 22nd design document — the design corpus (docs 00–20) stays
closed, and every row here traces to an owning doc. It introduces no new mechanism and
no new decision: it organizes doc 20, and never re-litigates phase order, gates, or the
F1–F11 dispositions.

## Divergence rule

On any conflict between this doc and docs 13/14/20, the corpus doc wins; this doc is an organizational view, never an override.

## Legend

### Row schema (6 fields)

Every feature row under an epic carries these six fields:

| # | Field | Definition |
|---|---|---|
| 1 | Feature name + story bullets | What it delivers, at the altitude a plan writer turns into TDD tasks — not the tasks themselves. |
| 2 | Tag (honesty tag) | One of `exists-today` / `target-new` / `rebuild` / `activation` / `horizon` (doc 04 §1) — or a compound (e.g. `rebuild + target-new`) when a row both rebuilds one object and adds another — so the plan never claims scaffolding as shipped (invariant 23). |
| 3 | Owning doc | The owning design doc — usually 05–19, but 02/04/03a also appear where an epic's mechanism is owned there — that owns the mechanism; this document follows the pointer for detail and never re-designs it. |
| 4 | F-flow | The business flow F1–F11 (doc 01 §7 / doc 20 §5) the feature serves. Substrate/infrastructure rows serving no single business flow carry `F-none`. |
| 5 | Gate | The doc-20 §4 gate (G-A…G-G) this feature must clear, helps clear, or ships behind as an entry gate; a compound value (e.g. `G-D (entry) / G-E (proof)`) names both. |
| 6 | Activation bar | `activation`-tagged rows only — the measured number that flips the arm/flag on (doc 20 §5/§10); such a feature is never "done" without it, only its landing-wired-at-zero is a phase deliverable. |

### Honesty tags

| Tag | Meaning |
|---|---|
| `exists-today` | Ships in the current baseline and the target keeps it as-is (e.g. `w_conf`, already read today via the confidence weighting). |
| `target-new` | A net-new table, column, service, or capability with no equivalent in the current baseline. |
| `rebuild` | The name and/or table survives, but the mechanism is a fresh build with a different semantic. |
| `activation` | The column, model, or arm already exists today, is populated but unread (or wired at zero), and the target begins to spend it once its measured bar clears. |
| `horizon` | Designed now, scoped to a horizon lane (H1/H2) or a lane-adjacent deferral (e.g. the MCP-resource inject transport, doc 20 §6's H1+), and shipped only on appetite behind its gate — never a Phase 0–4 dependency. |

---

## E0 — Phase 0: Baseline & harness

**Goal:** Land the single baseline migration with its dormant objects landed inert, and
stand up the eval harness as a first-class, CI-gated deliverable.

**Advance gate:** G-A — extraction F1 bench green reproducing the recorded baseline;
retrieval eval running with accuracy + p95 latency + token cost; baseline migration
boots clean and boot-time reconciliation is idempotent (doc 20 §4).

### Features

| Feature | Story bullets | Tag | Owning doc | F-flow | Gate | Activation bar |
|---|---|---|---|---|---|---|
| Single baseline migration + dormant objects landed inert | • Greenfield schema ships as one Alembic baseline revision, regenerated freely until the homelab-cutover freeze event (doc 19 §2).<br>• `repo_ids[]` (entities/entity_relations), `documents`/`blocks`, and the four per-fingerprint partition templates (block/relation/article/triple embeddings) land reviewed-and-frozen with no writer yet (doc 19 §3).<br>• Boot-time partition reconciliation runs idempotently at every startup, register-before-insert (doc 19 §2).<br>• SQL-first is a standing constraint on Phases 0–4: no ORM-only construct may be load-bearing, so the baseline stays plain-SQL (doc 20 §7, doc 19). | target-new | 19 | F-none | G-A | — |
| Extraction F1 bench — regression owner | • 26-memory `gold.json` + held-out split at `backend/scripts/extraction_bench/`; the LLM-output cache makes cleanup-pass iteration free (doc 17 §3).<br>• Scores four dimensions — entity name-only, entity name+type, relation pair-only, relation full-triple — as precision/recall/F1.<br>• Must reproduce the recorded as-is baseline before G-A clears (doc 20 §4). | exists-today | 17 | F-none | G-A | — |
| Retrieval eval + CI gate posture | • Accuracy sliced by query type, always paired with p95 latency and token cost against a full-context baseline (doc 17 §4).<br>• Both the F1 bench and the retrieval eval run behind a CI gate so no layer advances on intuition (doc 20 §2/§4); today that gate is a scripted local discipline, not hosted CI (doc 17 §9). | target-new | 17 | F-none | G-A | — |

### F9 — signal-ships-with-UI (this phase)

None — Phase 0 ships the eval harness and the baseline migration only; there is no UI
surface this phase (doc 13 §4 lists no Phase-0 screen; the harness and CI gate are
developer-facing, not product UI).

---

## E1 — Phase 1: Engine core at target shape

**Goal:** Rebuild the engine at target shape — capture + `memory_buffer`, the
five-phase pipeline, L1 graph & taxonomy, retrieval with SQL pushdown + labels + trace,
code truth T1–T4, the flattened LLM orchestrator, `events`, and the contract + core UI.

**Advance gate:** G-B — extraction F1 parity with the recorded baseline within a stated
tolerance; retrieval eval vs. the full-context baseline reported with its latency/cost
twin; isolation probes count zero unlabelled cross-project or superseded rows on every
channel (doc 20 §4).

### Features

| Feature | Story bullets | Tag | Owning doc | F-flow | Gate | Activation bar |
|---|---|---|---|---|---|---|
| Capture + `memory_buffer`, `origin_key` born at capture | • Tier-A synchronous accept resolves `source`/`origin_key`/`project`, validates against `MemoryCreate`, writes a durable buffer row, and returns a 202-style ack with a pre-minted UUIDv7 id (doc 05 §2).<br>• `origin_key` is the capture-session/agent-run identity; when identity is genuinely unknown it merges to ONE origin per `(source, project)` — undercount, never manufacture agreement (doc 05 §2.1).<br>• `memory_buffer` is claimed via `FOR UPDATE SKIP LOCKED` and flushed by a `buffer_flush` JobRegistry job; `wait_process` bypasses the buffer for an interactive caller (doc 05 §3).<br>• Repo-hint auto-provision handoff: capture validates the hint against doc 18's SSRF allowlist gate, then queues F11 in Tier C — never clones on the capture path (doc 05 §2.4). | target-new | 05 | F1 | G-B | — |
| Five-phase pipeline — merged extraction+classification call | • Content embed → merged extract+classify → cached entity embed → type-constrained dedup probe → two-savepoint write; each phase a hard checkpoint (doc 05 §5).<br>• One LLM touch per memory by default; `classifier_kind=local` narrows to extraction-only, and a non-simple classification mode keeps the two-concurrent-call path (doc 05 §6).<br>• Fingerprint registered before any partition write, and re-registered on mid-batch embedder rotation (doc 05 §5). | rebuild | 05 | F2 | G-B | — |
| L1 candidate graph & taxonomy | • Five closed vocabularies (entity/relationship/tech/memory types, plus the target memory-relation set) with pure normalisers and `LEGACY_*` runtime rewrites (doc 06 §3).<br>• The ~40-pass deterministic post-processor plus the relation-rescue layer stay out of the prompt — the extraction moat (doc 06 §4).<br>• Type-constrained ANN dedup at 0.85 with the `names_distinct` discriminator hands Phase 5 a `canonical_map`; strip-before-rewrite self-heals on re-extraction (doc 06 §5–§6). | rebuild | 06 | F2 | G-B | — |
| Retrieve — SQL pushdown + labels + trace | • Project/status/archived predicates pushed into SQL on every channel, closing the `memory_reason` cross-project/superseded leak — the named G-B isolation prerequisite (doc 07 §7).<br>• RRF fusion (k=60) over semantic + keyword, the unified `rank_fusion_factor` (confidence spent today, importance/heat/recency wired at zero), and an optional flag-gated reranker (doc 07 §3).<br>• The retrieval trace (envelope + per-row) attaches on request, transient, no table for v1 (doc 07 §8).<br>• The `applies_when` context-boost slot wires in this phase (magnitude a `config` row, tuned in Phase 2); the boost-plus-label and conflict-count rules are hard rules, never tuned (doc 07, doc 09 §5). | rebuild | 07 | F3 | G-B | — |
| Supersede — write-time detector, rules 1–6 verbatim | • Fires synchronously in Phase 5 savepoint B when a new memory carries a REPLACES-family relation (doc 08 §2.1).<br>• Six-rule gate: same project, candidate active, lowercased `technologies` overlap on the GIN, 90-day window, strictly-older `(created_at, id)` tie-break, and the per-target speculative-marker gate (doc 08 §2.1).<br>• Flips `status` + `superseded_by` atomically under `chk_superseded_has_pointer` (doc 08 §2.1). | exists-today | 08 | F4 | G-B | — |
| Expire — TTL sweep, demote-before-delete | • `expired_memory_cleanup` deletes rows past `expires_at`, first demoting every dependent that points at an expiring row via `superseded_by` to `deprecated` — the `SET NULL` FK forces this order (doc 08 §2.3).<br>• The interactive delete path (`MemoryService.delete_memory`) runs the identical demotion.<br>• `expires_at` stays a caller-set TTL in Phase 1; the self-expiring-dated-fact activation half follows in Phase 2 (doc 08 §2.3). | exists-today | 08 | F5 | G-B | — |
| Code truth hardening T1–T4 | • T1 fail-stale: a pipeline exception keeps the last-good graph labelled `stale`, never wipes; a diff failure falls back to a full index, not a bare wipe (doc 10 §3).<br>• T2 index-debt drain: dependent-caller re-trace overflow past the retrace cap persists to `repositories.index_debt` and drains in continuation batches, never dropped (doc 10 §3).<br>• T3 `code_reconcile` periodically hashes each tracked repo's working tree and feeds mismatches through the incremental path (doc 10 §3).<br>• T4 summary carry-over: a symbol whose body is unchanged keeps its LLM summary and enriched status across a file re-index, never re-billed (doc 10 §3). | target-new | 10 | F11 | G-B | — |
| Flattened LLM orchestrator | • Six-to-eight inline `llm_purpose_configs` rows — the six live purposes plus `synthesis` and `verification` seeded inert behind their unshipped layers (doc 11 §2/§6) — replace the provider/profile/ml-profile indirection; `classifier_kind` (`llm`\|`local`) rides inline on the classification purpose (doc 11 §2).<br>• One shared `httpx.AsyncClient`, constructed at boot and live-reloaded atomically on an admin save under the single-worker assumption (doc 11 §3).<br>• `api_kind` is the sole vendor-quirk home — auth, reasoning-disable knobs, structured-output caveats — across `openai`/`ollama`/`anthropic`/`google`/`deepseek`/`zai` (doc 11 §4). | rebuild | 11 | F-none | G-B | — |
| `events` substrate | • Every capture, extraction, supersession, and pipeline outcome writes an `events` row, replacing the coarse `audit_log`/`AuditLog` reads (doc 04 §8.1, doc 05 §2.3).<br>• Monthly `RANGE(created_at)` partitioning with a forbid-trigger blocking UPDATE/DELETE/TRUNCATE keeps the journal append-only.<br>• Feeds the target `GET /events`, `/events/calendar`, `/events/timeline` read surface (doc 12 §7). | target-new | 04 | F-none | G-B | — |
| Contract + core UI surfaces | • REST/MCP payload envelope, source/context resolution, and the auth-and-trust posture ship as the callable contract over the Phase-1 retrieval/pipeline signals (doc 12 §2–§6).<br>• TanStack Router IA, the Query/Zustand state split, and the WebSocket-to-invalidation mapping ride the same phase as their backend signal — there is no separate UI phase (doc 13 §2–§4).<br>• The pipeline stepper, failure triage, and job board ship as the Activity shell's v1 modules (doc 13 §6.1). | rebuild | 12 | F-none | G-B | — |
| Detail-level preference (Simple / Advanced view) | • Per-viewer display preference (`advanced` default, `simple` opt-in) persisted client-side in localStorage — changes only what the UI renders, never what the backend computes or returns (spec §Feature-1).<br>• `simple` hides technical/numeric detail — per-modality + fused `rrf_score` + rerank scores, the `rank_fusion_factor` arm breakdown, fingerprints, raw `config` keys, doc refs — collapsing the score breakdown to one plain "why it ranked" line.<br>• `simple` NEVER hides an honesty signal: verification badges, layer + superseded/stale labels, and the exclusion counts always render (invariant 14, doc 13 §5.4/§8). Ships with the first advanced surface (the why-retrieved trace); every later surface honours the same flag. | target-new | 13 | F9 | G-B | — |

### F9 — signal-ships-with-UI (this phase)

The five-phase pipeline stepper, failure triage, and job board (Activity shell v1
modules, doc 13 §6.1) + the Dashboard, including the contribution calendar — the
Dashboard is E1's core UI surface, and the calendar reads the Phase-1 `events`
date-bucket substrate (doc 13 §4, doc 04 §8.1) — + the Memories search surface with its
why-retrieved trace (doc 13 §4/§5.4) + the Code section's fail-stale banner (T1) and
index-debt indicator (T2), the two target-new signals the code-truth hardening produces
(doc 13 §4.2) + the Memory-detail supersession-lineage surface (amber badge + successor
link, doc 13 §4) + the global-chrome detail-level toggle (Simple / Advanced),
whose Simple view hides technical detail while keeping every honesty label
(spec §Feature-1).

---

## E2 — Phase 2: The truth core (L2)

**Goal:** Ship the truth core (L2) — verified facts + `fact_sources` + the verification
ladder, review/hygiene queues, the `projects` registry, the consolidation ("dreaming")
job family, memory relations, topics, then the code deriver once L2 is proven live.

**Advance gate:** G-C (deriver, Phase-2 exit) — promotion rate and false-promotion audit
under the stated bar, every ladder transition journaled to `events`; G-D (→ Phase 3) —
the groundedness judge's precision/recall clears the bar on a labelled gold set
(doc 20 §4).

### Features

| Feature | Story bullets | Tag | Owning doc | F-flow | Gate | Activation bar |
|---|---|---|---|---|---|---|
| Verified facts + `fact_sources` + the verification ladder | • `knowledge_triples` rebuild: a bi-temporal belief axis (open → window-closed → expired) orthogonal to the verification axis (candidate → corroborated → confirmed, + disputed) (doc 08 §3–§4).<br>• Promotion counts `COUNT(DISTINCT origin_key)` over `fact_sources`, never rows — origin diversity measured over the Phase-1 `origin_key` (doc 08 §4.1).<br>• A single non-echo contradiction over an overlapping validity window is an absolute veto to `disputed` (doc 08 §4.2).<br>• Only a human ratifying writes a `human`-kind `fact_sources` row reaches `confirmed` — the machine's ceiling is `corroborated` (doc 08 §4.4). | rebuild + target-new | 08 | F6 | G-C | — |
| Review & hygiene queues | • Two distinct `status + partial index` surfaces — review adjudicates truth (disputed/under-sourced facts, ungrounded articles), hygiene curates housekeeping (duplicates, low-confidence, expiring-soon, superseded lineage) with bulk actions (doc 08 §6).<br>• Consequence-ranked (retrieval frequency + subject salience), never FIFO, and never a gate on the read path — disputed items serve labelled with both sides (doc 08 §6).<br>• Stale disputes auto-expire off the *active* queue past `dispute_stale_days`, but stay `disputed` and served labelled — the decay changes priority, never verification status (doc 08 §6). | target-new | 08 | F6 | G-C | — |
| `projects` registry | • Minimal `projects(name PK, display_name, properties, created_at)` table anchors per-project `applies_when` defaults, review-queue scoping, and the one-live-article-per-subject rule (doc 04 §7, doc 09 §5).<br>• Capture lazily registers the resolved project via `INSERT … ON CONFLICT (name) DO NOTHING`, closing the typo'd-project fact-identity split (doc 05 §2). | target-new | 04 | F-none | G-C | — |
| Consolidate / dream — job family + digest + undo | • Several cooperating Tier-C `JobRegistry` jobs under one schedule umbrella — `verification_recompute`, `fact_lift`, `contradiction_scan`, `memory_dream`, plus the scheduled `topic_detection`/`article_synthesis` — each with its own cron/floor/ceiling and per-job lock (doc 08 §5); `article_synthesis` is registered under this umbrella but its productive runs are Phase-3, behind G-D (doc 08 §5.6, doc 20 §3).<br>• `memory_dream` never hard-merges or deletes a memory: subsumption routes through the `supersede()` primitive, near-duplicates get an associative edge plus a hygiene-queue item; `refine` rewrites only derived fields, never `content` (doc 08 §5.4).<br>• Every action journals a before/after `events` payload; the dream digest groups a cycle's actions and offers per-action/per-batch undo, tractable because invalidate-not-delete means every inverse is a status/pointer/timestamp restore (doc 08 §7). | target-new | 08 | F6 | G-C | — |
| Memory relations — the associative layer | • `memory_dream` derives the five stored associative types (`CONTRADICTS`, `ELABORATES`, `DEPENDS_ON`, `FOLLOWS`, `RELATES_TO`) from entity overlap, embedding proximity, and contradiction checks, writing through `normalize_memory_relation_type` (doc 08 §5.5, doc 06 §3.1).<br>• Strip-before-rewrite and self-healing on either endpoint's deletion; `SUPERSEDES` is never written here — it stays the projected `superseded_by` pointer (doc 08 §5.5). | target-new | 08 | F6 | G-C | — |
| Topics as an organizing surface | • Materialised Leiden communities over a project-scoped projection (`memory_communities` + `memory_community_members`), delete-and-rewritten per project, labelled from dominant entities, with an LLM `report_string` off the hot path (doc 06 §7).<br>• This doc consumes the durable rows as three read/derive operations — browsing, local report injection, and diffing across runs into pin suggestions the human accepts or dismisses — and owns none of the detection mechanics (doc 09 §3).<br>• The global `memory_overview` map-reduce (map over precomputed reports, one bounded `summarization` reduce) is a separate MCP tool, never per-memory RRF (doc 09 §3.3). | target-new | 09 | F9 | G-C | — |
| Code deriver — imports-only, facts born `corroborated` | • A narrow, deterministic, LLM-free deriver mints Layer-1 assertions from a repo's import edges only, tagged via `assert_from_repo` into `entities.repo_ids[]`/`entity_relations.repo_ids[]` (doc 10 §6).<br>• Ships only after Layer 2 is proven live — the inert `repo_ids[]` amendment lands in the Phase-0 baseline (the amended sweeps byte-identical to today's) and this is its first writer (doc 10 §6, doc 06 §6.1).<br>• Consolidation lifts a corroborated Layer-1 assertion to a fact born `corroborated` — the parse is the verification — with `origin_key = repo_id`, one origin per repo regardless of commit count (doc 10 §6, doc 08 §4.1). | target-new | 10 | F11 | G-C | — |
| Groundedness judge — qualified on labelled entailment gold | • The single `verification`-purpose judge is qualified on a labelled entailment gold set before any consumer's layer ships — the deliverable that clears G-D (doc 17 §6, doc 11 §6).<br>• `config` precision/recall bars on claim/fact entailment gold, seeded from real synthesis drafts once Layer 2 is live; below the bar, no L3 article ships as grounded (doc 17 §6).<br>• Built once in Phase 2 for the contradiction veto, then reused by L3 synthesis and the F8 horizon — one judge, three consumers (doc 17 §6, doc 20 §3). | target-new | 17 | F-none | G-D | — |

> The Phase-2 retrieval-arm landings — `w_importance` activation, the `memory_access_stats`
> feeder for `w_heat`/`w_recency`, the PPR snapshot job, and the `triple_embeddings` writer —
> are enumerated in the closing Phase × subsystem matrix rather than as feature rows here (doc 20 §5).

### F9 — signal-ships-with-UI (this phase)

The Facts tab — the bi-temporal, multi-origin browsing surface (doc 13 §5.1) — with
verification badges rendered verbatim (doc 13 §5.3) + the Review/Hygiene triage shell
(doc 13 §6.2) + the dream digest with per-action/per-batch undo (doc 13 §6.3) + the
Topics tab of the Knowledge shell — browsing, report injection, pin-suggestion diff
(doc 13 §5).

---

## E3 — Phase 3: Synthesis & reach (L3)

**Goal:** Ship synthesis & reach (L3) — subject articles behind the groundedness gate,
F7 auto-research as a committed fast-follow, and distribution (inject v1, onboarding,
SDKs, browser capture).

**Advance gate:** done = G-E cleared (L3 shipped, per-article coverage holding above the
runtime threshold in production) + F7 shipped; Phase 3 → 4 is appetite/demand, not a
metric (doc 20 §4).

### Features

| Feature | Story bullets | Tag | Owning doc | F-flow | Gate | Activation bar |
|---|---|---|---|---|---|---|
| Subject articles + citations, behind the groundedness gate | • One live grounded article per `(project, subject_key)`, synthesised only from non-disputed corroborated/confirmed facts; subjects clear a hard verified-fact eligibility gate, then a weighted priority score orders them under a per-run synthesis budget (doc 09 §4.1–§4.2).<br>• A claim-level entailment pass (doc 11's `verification` purpose) forces every sentence to cite a fact; coverage below threshold routes to review, never ships as corroborated (doc 09 §4.3).<br>• `article_citations` is the one hard FK to `knowledge_triples` — safe because facts are invalidate-not-delete (doc 09 §4.3).<br>• The staleness gate is a hash of the *verified* fact set only; re-synthesis is debounced, strip-before-rewrite, and supersedes the prior article (doc 09 §4.4). | target-new | 09 | F6 | G-D (entry) / G-E (proof) | — |
| F7 Auto-research — committed fast-follow | • A thin orchestration over already-shipped capture, consolidation, and synthesis: a research-agent loop files evidence through the ordinary capture front door, each genuinely independent source stamped a distinct `origin_key` (doc 09 §6).<br>• Corroboration counts distinct origins — the same source fetched twice, or unknown identity, merges to ONE origin, never manufactured (doc 09 §6, reshape spec §2.1).<br>• Sequenced at the tail of Phase 3, after both L2 and L3 prove live; committed on the roadmap, never a v1 blocker on the core agent engine (doc 20 §5, doc 01 §9). | target-new | 09 | F7 | G-E | — |
| Inject v1 — push managed block | • Client-side pull-then-write: the writer pulls the F3 fused, labelled selection and rewrites a marker-bounded managed block in the tool's native context file — the server never writes the client's filesystem (doc 15 §3.1–§3.2).<br>• Truth-first content fill (L2 facts, then L3 articles, then L0 memory summaries) under a `config` token budget; every item carries its layer/verification/badge labels (doc 15 §3.4).<br>• v1 transport is a managed file block per target tool (Claude Code `CLAUDE.md`, Cursor, Codex `AGENTS.md`, Cline); session-start refresh cadence, `watch` mode deferred to Phase 4 (doc 15 §3.3/§3.5). | target-new | 15 | F10 | G-D | — |
| One-command onboarding + client SDKs | • `darkmem connect <tool>` writes the tool's MCP config from a maintained adapter registry and verifies via the stateless `initialize → tools/list` handshake; a foreign-Host `421` is reported as "extend the allowlist," never worked around (doc 15 §5).<br>• A minimal generated SDK (TypeScript + Python) exposes three verbs — `capture` / `search` / `declareContext` — over the doc 12 contract; ratify/review/vault-admin stay out (doc 15 §6). | target-new | 15 | F-none | G-D | — |
| Browser capture — new ingestion front door | • A browser extension packages a human-selected AI-chat exchange and posts it through the ordinary REST/MCP capture front door into `memory_buffer` — no new pipeline (doc 15 §4).<br>• v1 is human-triggered only, never auto-scraped; a small maintained adapter set covers ChatGPT/Claude.ai/Gemini web with a plain-selection fallback, deduped by content fingerprint and a per-install `origin_key` (doc 15 §4). | target-new | 15 | F1 | G-D | — |
| Session progress checkpoints + resume | • Server-side checkpoint store keyed on `origin_key` (the agent-run identity, doc 05 §2.1): a new `session_checkpoints` table, `POST`/`GET /checkpoints`, and MCP `checkpoint_save`/`checkpoint_latest`, holding a compact `summary` + structured `next_steps` (spec §Feature-2, extends doc 04/12).<br>• Resume is a specialised inject — at session start the latest checkpoint writes into the `CLAUDE.md` managed block under the token budget, so a fresh session loads a ~budgeted digest instead of reloading full context (doc 15 §3.2, invariant 17).<br>• Operational, not vault knowledge (no verification badge); surfaced in the Activity shell with copy-resume, `checkpoint_saved`/`resumed` journaled to `events` (doc 13 §6, doc 04 §8.1). Store + a manual `/resume` needs only `origin_key`, so that half is Phase-1-capable; the Claude Code plugin carrier is planned separately (spec §Feature-2). | target-new | 15 | F10 | G-D | — |

### F9 — signal-ships-with-UI (this phase)

The Articles tab of the Knowledge shell — grounded prose, inline claim citations, the
claim-support-coverage readout, and the stale label (doc 13 §5.2) + the distribution
surfaces: the Settings → Distribution tab (per-target managed-block config, inject
content policy, curb control) and inject records surfaced as journaled events in the
timeline/calendar (doc 13 §6.5) + the Session-checkpoints / resume view in the
Activity shell (per-run digest, next-steps, copy-resume; `checkpoint_saved`/`resumed`
events, spec §Feature-2, doc 13 §6).

---

## E4 — Phase 4: Hardening & scale

**Goal:** Harden and scale — `ApiKey` activation + exposed-deployment posture, the repo
push webhook, inject `watch` mode, auto-scrape opt-in, and the multi-replica decision if
ever taken.

**Advance gate:** demand-gated — an actual exposed deployment (or a concrete second
consumer) opens this phase; nothing in Phases 0–3 depends on it (doc 20 §10).

### Features

| Feature | Story bullets | Tag | Owning doc | F-flow | Gate | Activation bar |
|---|---|---|---|---|---|---|
| `ApiKey` activation + exposed-deployment posture | • The dormant `api_keys` table (exists today, unwired — every write passes `api_key_id=None`) is wired to a bearer credential shape (`dmk_<key_id>_<secret>`) with a closed scope set (`capture`/`read`/`admin`) + optional MCP bearer; `ratify` is deliberately never a scope (doc 18 §5).<br>• Under exposure, `trust_proxy_headers` returns on, `cookie_secure` is enforced, and an operator TLS proxy sits in front — every LAN rule (Host allowlist, TOFU-then-403, single-door ratification) stays unchanged underneath (doc 18 §4/§9).<br>• Every keyed call stamps `events.api_key_id`/`events.actor` — the first time those dormant columns carry a value (doc 18 §5). | activation | 18 | F-none | demand-gated | First exposed deployment or push-webhook receiver needing a non-LAN credential — an event trigger, not a scored metric (doc 18 §5/§11) |
| Repo push webhook | • Replaces, for the pushed repo, periodic change-gated `repo_sync` polling with index-on-push, reusing the identical change-gated `CodePipeline.run` — never a second indexing path (doc 10 §5, doc 15 §9).<br>• Gated on the `ApiKey` exposed-endpoint auth activation, since it needs an externally-reachable authenticated receiver (doc 10 §5). | target-new | 10 | F11 | demand-gated | — |
| Inject `watch` mode + auto-scrape opt-in | • `watch` mode re-injects the managed block as the project, open file, or declared context shifts, instead of only at session start; config-gated, deferred behind a measured need (doc 15 §3.5).<br>• Automatic full-conversation browser capture becomes an opt-in, widening v1's human-triggered-selection-only scope (doc 15 §4). | target-new | 15 | F10 / F1 | demand-gated | — |
| Multi-replica decision (if taken) | • Any move beyond one uvicorn worker breaks the in-process assumptions load-bearing across the corpus — the cached PPR/igraph snapshot, the feature-flag TTL cache, the entity-embedding LRU, and every per-job `asyncio.Lock` — and needs sticky routing or a serialised snapshot table (doc 02 §11, invariant 13).<br>• Stays a flagged Phase-4 decision, never a side effect of any earlier phase's deployment work (doc 20 §9). | target-new | 02 | F-none | demand-gated | — |

### F9 — signal-ships-with-UI (this phase)

`ApiKey`-use journaled to `events` and surfaced in the per-object timeline (doc 13
§6.4, doc 18 §5) + the inject `watch`-mode and curb surfaces on the Distribution tab —
the human can see and curb push, never a silent context swap (doc 13 §6.5, doc 15
§3.5).

---

## EH1 — H1: Documents / PKM (horizon)

**Goal:** Ship the horizon documents/PKM lane — the block pipeline, block retrieval, the
faithfulness gate, proposition lifting, and the analysis surface.

**Advance gate:** G-F — the core eval gate (doc 16 §1): retrieval eval and promotion
metrics stable, plus maintainer appetite; the faithfulness metric (span-support
coverage) is defined before build starts and gates before ship (doc 20 §4).

### Features

| Feature | Story bullets | Tag | Owning doc | F-flow | Gate | Activation bar |
|---|---|---|---|---|---|---|
| Block pipeline — document ingest, parse, chunk, embed | • Firewall, both directions: article synthesis never reads a block (the vault does not depend on this unshipped horizon), and the whole PKM surface ships only after the core's eval gate clears (doc 16 §1, doc 01 §3.4).<br>• Tier-B pipeline variant — not the five-phase memory pipeline: parse a filed document into a block tree, strip-before-rewrite by `document_id`, embed each block into `block_embeddings__<slug>` (doc 16 §2–§3).<br>• Document identity is the partial `UNIQUE (project, uri)` with `content_hash` as the re-ingest change gate — an unchanged hash short-circuits the whole pipeline (doc 16 §2–§3).<br>• Parser stack ADR: `pdfplumber` for PDF, `markdown-it-py`/`mistune` for markdown, native segmentation for notes — rejects `PyMuPDF` (AGPL) and ML-layout parsers (violates doc 03 §3.3's no-heavy-ML floor) (doc 16 §3). | horizon | 16 | F8 | G-F | — |
| Block retrieval — separate channel, trace addendum | • Semantic-only channel over `block_embeddings__<slug>`, never fused into the four-layer memory/vault composition — the document-RAG twin of code search (doc 16 §4, doc 07 §2).<br>• Emits the doc 07 §8 trace with a `block` id-kind and a `document` layer — additive to the core trace schema, never assumed by a consumer until H1 ships (doc 16 §4). | horizon | 16 | F8 | G-F | — |
| Faithfulness gate — grounded Q&A, span-support coverage | • Interactive `reasoning`-purpose flow: retrieve blocks, generate a per-sentence cited answer, then a `verification`-purpose faithfulness check on span-support coverage (entailed claims / total claims) before serving (doc 16 §4).<br>• A below-threshold answer is labelled could-not-fully-ground or withheld, never served as grounded (invariant 14, doc 16 §4).<br>• Double duty: a per-answer runtime gate AND the doc-17 ship gate — the faithfulness metric must be *defined* before H1 build starts and *clears* a labelled gold-set bar before H1 ships (doc 20 §4). | horizon | 16 | F8 | G-F | — |
| Proposition lifting — block-sourced facts, the vault bridge | • On-demand, Tier-C lift only — never automatic on ingest; mints proposition memory rows carrying `(document_id, block_id, char_span)` provenance on the derived row, then flows through the ordinary F2 pipeline (doc 16 §5).<br>• Corroborated relations lift to an L2 fact via `fact_sources(kind='block', origin_key=document_id)` — one document is one origin regardless of block count, matching the "a repo is one origin" rule (doc 16 §5, doc 08 §4.1).<br>• Idempotent, keyed on `document_id` — strip-before-rewrite on re-ingest, self-healing through the ordinary source-withdrawal sweep (doc 16 §5). | horizon | 16 | F8 | G-F | — |
| Analysis surface — grounded Q&A, summary, emergent connections | • v1 scope is thin and reuses shipped machinery: grounded Q&A (F8) is committed to the horizon; single-document summary reuses doc 11's `summarization` purpose as an unbadged report, never a verified claim (doc 16 §6).<br>• Cross-document connections are emergent from the shared graph after lifting — entity overlap, topic communities (doc 06), associative relations (doc 08) — no new analysis engine (doc 16 §6).<br>• Corpus trend dashboards and multi-document synthesis write-ups are deferred/demand-gated; a verified multi-source write-up is an article (doc 09), never an analysis feature reading blocks (doc 16 §6). | horizon | 16 | F8 | G-F | — |

### F9 — signal-ships-with-UI (this phase)

The analysis surface — grounded Q&A over blocks, single-document summary, and
emergent cross-document connections (doc 16 §6) — is the horizon lane's one UI
surface; doc 13's inventory defines no documents screen today, and doc 16 expects a horizon-labelled documents view to land with the lane.

---

## EH2 — H2: .NET migration (horizon)

**Goal:** Replay the target shape onto .NET — the SQL-first baseline replay and a
harness-paritied port, entered on appetite.

**Advance gate:** G-G — the Python target shipped; the harness exists in the new stack
before any parity claim: byte-identical LLM-cache reuse and exact F1-scorer parity
(doc 20 §4).

### Features

| Feature | Story bullets | Tag | Owning doc | F-flow | Gate | Activation bar |
|---|---|---|---|---|---|---|
| Harness ports first — byte-identical cache + exact F1-scorer parity | • The harness must exist in the new stack **before** any parity claim (doc 00 §7.2, doc 19 §7) — proven by `spikes/dotnet-benchlib/`: 26/26 LLM-cache reuse via byte-identical sha256 keys, and an F1 scorer exactly identical to `run_bench.py` on real cached outputs (1e-12).<br>• `gold.json` is stack-neutral JSON and carries verbatim; a ported cleanup pass's F1 delta is attributable purely to the pass, never to model drift or metric skew (doc 19 §7, doc 03a §5.3). | horizon | 19, 03a | F-none | G-G | — |
| SQL-first baseline replay via DbUp | • The single Alembic baseline (kept plain-SQL by rule — no ORM-only construct load-bearing) becomes the first script of a DbUp chain baselined from a schema snapshot; `alembic_version` is dropped (doc 19 §7).<br>• Homelab data carries via `pg_dump`/restore; the asyncpg `CAST` wrappers are dropped, not copied — Npgsql resolves types client-side, so the bug class disappears (doc 19 §7, doc 03a §3). | horizon | 19, 03a | F-none | G-G | — |
| Registry DDL in C# — boot-time partition reconciliation | • The boot-time reconciliation (a loop over `embedders` rows running parameterised SQL DDL) moves into the registry's C# equivalent — spike-proven live: runtime child-table DDL, sanitised slug, no-CAST vector insert, `<=>` round-trip (`spikes/dotnet-data/`, doc 19 §7).<br>• Register-before-insert, `child_table`-only naming, and no cross-fingerprint joins (invariant 2) carry forward as invariants, not as Python code (doc 19 §7). | horizon | 19, 03a | F-none | G-G | — |
| Pipeline + code-indexing port — measured, not faith-based | • Pipeline + ~40 cleanup passes port with every pass gated on a measured F1 delta against the ported harness (doc 19 §7).<br>• Code indexing: the stock tree-sitter binding plus a `zig cc` grammar-pack CI (all 12 grammars, single-DLL pack, cross-compiles to all 5 RIDs) — a wiring/packaging task, not a feasibility red (doc 19 §7, doc 03a §5.1.1).<br>• Pure-managed full Leiden matches leidenalg at −0.4% modularity / 98.4% partition agreement and is never bit-identical — any test pinning exact community membership must tolerate this permanent, measured residual (doc 19 §7). | horizon | 19, 03a | F-none | G-G | — |
| Named residuals + the magnitude anchor | • Two named mechanical residuals with no matrix red: full-harness assembly around the proven benchlib core, and the psutil/pynvml system/GPU telemetry gap — the port needs `System.Diagnostics` plus a GPU-vendor library, or a graceful degrade (doc 19 §7/§9.6, doc 03a).<br>• The magnitude anchor stands as recorded: ~19–38 weeks (≈5–9 months) single-engineer sequential (doc 03a §9) — carried by doc 20 §10 as an anchor for phase sizing, never a commitment or a plan. | horizon | 19, 03a | F-none | G-G | — |

### F9 — signal-ships-with-UI (this phase)

None — Phase H2 is a backend stack replay (harness parity, the DbUp baseline, registry
DDL, the pipeline/code-indexing port); no new UI ships (doc 19 §7).

---

## Phase × subsystem matrix

Non-exhaustive by intent: it enumerates every doc-20 §5 split (every arm, flag, and
subsystem whose ship point and activation point differ), and doc 20 is the authority.

**Docs 13/14 disposition.** Docs 13 (frontend architecture/IA) and 14 (UI/UX design
language) own no epic of their own — mirroring doc 20 §5's framing of F9 (Observe &
curate: committed, every phase, "it is not a phase," principle 10). Every UI surface
docs 13/14 specify binds to the epic whose phase its backing signal ships in, through
that epic's F9 callout above; there is no separate UI phase or UI epic.

| Item | P0 | P1 | P2 | P3 | P4 | Horizon | Activation bar |
|---|---|---|---|---|---|---|---|
| F11 Index code | — | T1–T4 hardening: fail-stale, index-debt drain, `code_reconcile`, summary carry-over (doc 10 §3) | Deriver — imports-only Layer-1 assertions via `assert_from_repo`, after G-C (doc 10 §6) | — | Push webhook, replacing polling for the pushed repo (doc 10 §5) | — | Deriver: G-C (Phase-2 exit); push webhook: gated on the `ApiKey` exposed-deployment activation, demand-gated (doc 10 §5) |
| Retrieval — ranking arms (general) | — | Core retrieve ships: SQL pushdown + labels + trace + RRF fusion; the `rank_fusion_factor` formula slots for importance/heat/recency wire at zero (doc 07 §3) | Per-arm activation on a measured retrieval-eval win (P2-activate) | — | — | — | See the individual arm/flag rows below |
| Topics & articles (doc 09) | — | — | Topics — Leiden communities, browsing/injection/pin-diff, G-C (doc 09 §3) | Subject articles + citations behind the groundedness gate, G-D/G-E (doc 09 §4) | — | — | Topics: G-C; articles: per-article coverage above the runtime threshold in production |
| Inject / distribution (doc 15) | — | — | — | Inject v1 — managed file block, session-start refresh, G-D (doc 15 §3) | `watch` mode + auto-scrape opt-in, demand-gated (doc 15 §3.5/§4) | MCP-resource inject transport (doc 15 §3.3) | Phase 3 → 4 is appetite/demand, not a metric |
| Migration substrate (doc 19) | Dormant objects land inert: `repo_ids[]`, `documents`/`blocks`, per-fingerprint embedding templates, G-A (doc 19 §2–§3) | — | — | — | — | H2 — SQL-first baseline replay via DbUp + registry-DDL port, G-G (doc 19 §7) | P0: G-A, boot-time reconciliation idempotent; H2: G-G, harness ports first — byte-identical LLM-cache reuse + exact F1-scorer parity |
| `expires_at` | — | exists-today — caller-set TTL, demote-before-delete sweep (doc 08 §2.3) | activation — self-expiring dated facts, follows with the temporal passes (doc 08 §2.3) | — | — | — | Follows in Phase 2 with the temporal passes — deterministic, no measured bar (doc 20 §5, doc 08 §9) |
| `w_conf` (confidence arm) | — | exists-today, read now | — | — | — | — | Harness-tuned magnitude |
| `relation_rescue` | — | exists-today, on | — | — | — | — | Guarded by the F1 bench — reorder/remove only against a measured delta |
| `w_importance` | — | formula slot wired at zero (doc 07 §3) | activation — populated, unread today | — | — | — | Retrieval-eval win with twin |
| `w_heat`, `w_recency` | — | formula slot wired at zero (doc 07 §3) | target-new — `memory_access_stats` feeder + activation | — | — | — | Retrieval-eval win with twin |
| `w_ppr`, dual-level, community injection | — | — | target-new, flags default 0; graph arms need the snapshot job live first | — | — | — | Retrieval-eval win with twin; graph arms need the snapshot job live first |
| `reranker_enabled` | — | exists-today, dormant — ships wired-dormant with the P1 retrieve rebuild (doc 07 §3) | — | — | — | — | measured win incl. p95 cost, any phase clears the bar first |
| `applies_when` boost magnitude | — | wire (target-new) | tune | — | — | — | Magnitude is `config`; the boost-plus-label and conflict-count rules are hard rules, never tuned |
| `triple_embeddings` writer | template lands inert (doc 04 §5.3) | — | writer activates, P2+ | — | — | — | Trigram miss-rate above its stated bar; counting only, `names_distinct` carried |
| Detail-level preference (spec) | — | Simple / Advanced view ships with the why-retrieved trace; localStorage, honesty labels always shown (G-B) | honoured by vault surfaces | honoured by article/distribution surfaces | — | — | Per-viewer display preference — no measured bar |
| Session checkpoints + resume (spec) | — | Store + manual `/resume` Phase-1-capable (`origin_key` only) | — | Checkpoint store + auto-inject resume at session start, G-D (doc 15) | — | — | Committed Phase 3; store half pullable to Phase 1 |
