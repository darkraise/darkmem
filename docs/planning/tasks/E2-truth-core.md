# E2 — Phase 2: The truth core (L2)

**Goal:** Ship the truth core — verified facts + `fact_sources` + the verification
ladder, review/hygiene queues, the `projects` registry, the consolidation ("dreaming")
job family, memory relations, topics, then the code deriver once L2 is proven live.

**Advance gates:** **G-C** (deriver + Phase-2 exit) — promotion rate and false-promotion
audit under the stated bar, every ladder transition journaled to `events`. **G-D**
(→ Phase 3) — the groundedness judge's precision/recall clears the bar on labelled gold.

**Epic branch:** `feat/e2-truth-core`

**Contract:** [`../agent-runbook.md`](../agent-runbook.md). Amendments log at the bottom.

**The under-claiming rule governs this whole epic.** The machine's ceiling is
`corroborated`; only a human reaches `confirmed`. A delayed promotion costs a label,
never availability — candidates are served labelled, never withheld (invariant 14).

---

## Lane A — verified facts and the ladder

#### T2.01 — `knowledge_triples` rebuild: the bi-temporal belief axis

`Model: Opus 5` · `Depends: T1.06` · `Doc: 08 §3–§4` · `Tag: rebuild + target-new` · `Gate: G-C`

**What.** Two orthogonal axes: belief (open → window-closed → expired) and verification
(candidate → corroborated → confirmed, plus disputed). Conflating them is the modelling
error this rebuild exists to fix — a fact can be well-verified and no longer current.

**Done when:**
- [ ] The two axes are independently queryable and independently transitioned
- [ ] A confirmed-but-expired fact is representable and renders as such
- [ ] `triple_key` identity is stable across re-derivation

**Verify.** `cd backend && python -m pytest tests/test_knowledge_triples.py -q`

#### T2.02 — `fact_sources` and origin-diversity counting

`Model: Opus 5` · `Depends: T2.01, T1.11` · `Doc: 08 §4.1` · `Tag: target-new` · `Gate: G-C`

**What.** Promotion counts `COUNT(DISTINCT origin_key)` over `fact_sources` — **never
rows**. Row-counting manufactures agreement out of one chatty source; this is the single
most important arithmetic in the epic.

**Done when:**
- [ ] Distinct-origin counting proven by a test that fails under row-counting
- [ ] The same source asserting a fact ten times counts as one origin
- [ ] Source kinds recorded (`memory`, `code`, `human`, later `block`)

**Verify.** `cd backend && python -m pytest tests/test_fact_sources.py -q`

#### T2.03 — The verification ladder

`Model: Opus 5` · `Depends: T2.02` · `Doc: 08 §4` · `Tag: target-new` · `Gate: G-C`

**What.** Promotion from candidate → corroborated on distinct-origin diversity, with N
and the diversity rule as `config` rows.

**Done when:**
- [ ] Promotion is a pure function of the ladder inputs — reproducible on replay
- [ ] N and the diversity rule read from `config`, defaults stated
- [ ] Loosening either requires a G-C measurement (T2.40), not an edit

**Verify.** `cd backend && python -m pytest tests/test_verification_ladder.py -q`

#### T2.04 — The contradiction veto is absolute

`Model: Opus 5` · `Depends: T2.03` · `Doc: 08 §4.2` · `Tag: target-new` · `Gate: G-C`

**What.** A single non-echo contradiction over an overlapping validity window vetoes to
`disputed`. Absolute — not a weight, not a score, not tunable.

**Done when:**
- [ ] One contradiction beats any number of corroborations, proven by test
- [ ] Echoes (the same origin restating itself) do not count as contradiction
- [ ] Validity-window overlap is required — non-overlapping claims are not contradictions
- [ ] No `config` knob can soften the veto

**Verify.** `cd backend && python -m pytest tests/test_contradiction_veto.py -q`

#### T2.05 — Human ratification is the only path to `confirmed`

`Model: Sonnet 5` · `Depends: T2.03` · `Doc: 08 §4.4` · `Tag: target-new` · `Gate: G-C`

**What.** Only a human ratifying, writing a `human`-kind `fact_sources` row, reaches
`confirmed`. No machine path exists.

**Done when:**
- [ ] No code path sets `confirmed` without a `human` source row
- [ ] Ratification is single-door by design (doc 18) and never an API-key scope
- [ ] The ratifier and timestamp are recorded

**Verify.** `cd backend && python -m pytest tests/test_ratification.py -q`

#### T2.06 — Every ladder transition journaled

`Model: Sonnet 5` · `Depends: T2.03, T1.07` · `Doc: 08 §4` · `Tag: target-new` · `Gate: G-C`

**What.** G-C is computed *from* the journal, so an unjournaled transition is an
unmeasurable one.

**Done when:**
- [ ] Every transition writes an event with before/after and the triggering evidence
- [ ] The G-C metrics are derivable by SQL over `events` alone

**Verify.** `cd backend && python -m pytest tests/test_ladder_journaling.py -q`

---

## Lane B — the `projects` registry

#### T2.07 — `projects` table + lazy registration

`Model: Sonnet 5` · `Depends: T1.12` · `Doc: 04 §7, 09 §5` · `Tag: target-new` · `Gate: G-C`

**What.** `projects(name PK, display_name, properties, created_at)` anchors per-project
`applies_when` defaults, review-queue scoping, and the one-live-article-per-subject rule.
Capture registers lazily via `INSERT … ON CONFLICT DO NOTHING`, closing the typo'd-project
fact-identity split.

**Done when:**
- [ ] Capture registers unseen projects without a round trip or a failure mode
- [ ] A typo creates a visible project rather than a silent parallel universe
- [ ] Existing project strings backfill into the registry

**Verify.** `cd backend && python -m pytest tests/test_projects_registry.py -q`

---

## Lane C — consolidation ("dreaming")

#### T2.08 — Job-family umbrella under JobRegistry

`Model: Sonnet 5` · `Depends: T2.01` · `Doc: 08 §5` · `Tag: target-new` · `Gate: G-C`

**What.** Several cooperating Tier-C jobs under one schedule umbrella, each with its own
cron, floor, ceiling, and per-job lock. Reconciliation stays off the hot path
(invariant 15) — no job here may be called from capture or retrieval to "accelerate" a gate.

**Done when:**
- [ ] Each job independently scheduled, locked, and configurable
- [ ] A manual trigger while the lock is held returns 409, never queues
- [ ] No Tier-A/B caller can invoke any of them

**Verify.** `cd backend && python -m pytest tests/test_dream_jobs.py -q`

#### T2.09 — `verification_recompute`

`Model: Sonnet 5` · `Depends: T2.08, T2.03` · `Doc: 08 §5` · `Tag: target-new` · `Gate: G-C`

**What.** Recompute ladder state as sources accumulate or withdraw.

**Done when:** recompute is idempotent; a withdrawn source demotes correctly; each change
journals.
**Verify.** `cd backend && python -m pytest tests/test_verification_recompute.py -q`

#### T2.10 — `fact_lift`

`Model: Opus 5` · `Depends: T2.08, T2.02` · `Doc: 08 §5` · `Tag: target-new` · `Gate: G-C`

**What.** Lift corroborated L1 relations into L2 facts, writing the `fact_sources` rows
that justify them.

**Done when:** lifting is idempotent on re-run; every lifted fact traces to its source
rows; no fact is born above `corroborated` except via T2.28's parse-is-verification rule.
**Verify.** `cd backend && python -m pytest tests/test_fact_lift.py -q`

#### T2.11 — `contradiction_scan`

`Model: Opus 5` · `Depends: T2.04` · `Doc: 08 §5` · `Tag: target-new` · `Gate: G-C`

**What.** Find contradiction candidates via the `pg_trgm` shortlist and adjudicate with
the `verification` judge. The shortlist's measured miss rate is what gates T2.33.

**Done when:** shortlist recall is measured and recorded; adjudication uses the judge, not
a heuristic; misses are counted, not hidden.
**Verify.** `cd backend && python -m pytest tests/test_contradiction_scan.py -q`

#### T2.12 — `memory_dream` — never hard-merges, never deletes

`Model: Opus 5` · `Depends: T2.08` · `Doc: 08 §5.4` · `Tag: target-new` · `Gate: G-C`

**What.** Subsumption routes through the `supersede()` primitive; near-duplicates get an
associative edge plus a hygiene item; `refine` rewrites only derived fields, **never
`content`**. Invalidate-not-delete is what makes T2.13's undo tractable.

**Done when:**
- [ ] No path deletes or hard-merges a memory, proven by test
- [ ] `refine` cannot touch `content`
- [ ] Every action writes a before/after event payload

**Verify.** `cd backend && python -m pytest tests/test_memory_dream.py -q`

#### T2.13 — Dream digest + per-action and per-batch undo

`Model: Opus 5` · `Depends: T2.12` · `Doc: 08 §7` · `Tag: target-new` · `Gate: G-C`

**What.** Group a cycle's actions into a digest and offer undo at both granularities.
Tractable precisely because every inverse is a status, pointer, or timestamp restore.

**Done when:**
- [ ] Undo restores exact prior state for every action type
- [ ] Batch undo is atomic — partial undo is not representable
- [ ] Undo itself journals (an undo is an action, not an erasure)

**Verify.** `cd backend && python -m pytest tests/test_dream_undo.py -q`

#### T2.14 — Register `article_synthesis` inert

`Model: Haiku 4.5` · `Depends: T2.08` · `Doc: 08 §5.6` · `Tag: target-new, inert` · `Gate: G-C`

**What.** Registered under the umbrella now; productive runs are Phase 3 behind G-D.

**Done when:** job exists, scheduled off; labelled inert naming T3.02 as its first
productive run.
**Verify.** `cd backend && python -m pytest tests/test_inert_objects.py -q`

---

## Lane D — memory relations (the associative layer)

#### T2.15 — Five associative types + normaliser

`Model: Sonnet 5` · `Depends: T1.23` · `Doc: 06 §3.1, 08 §5.5` · `Tag: target-new` · `Gate: G-C`

**What.** `CONTRADICTS`, `ELABORATES`, `DEPENDS_ON`, `FOLLOWS`, `RELATES_TO` through
`normalize_memory_relation_type`. **`SUPERSEDES` is never written here** — it stays the
projected `superseded_by` pointer.

**Done when:** only the five are storable; `SUPERSEDES` is rejected; unknown types fall
back within the closed set.
**Verify.** `cd backend && python -m pytest tests/test_memory_relation_types.py -q`

#### T2.16 — Derivation from overlap, proximity, and contradiction

`Model: Opus 5` · `Depends: T2.15, T2.12` · `Doc: 08 §5.5` · `Tag: target-new` · `Gate: G-C`

**What.** `memory_dream` derives the edges from entity overlap, embedding proximity, and
contradiction checks.

**Done when:** thresholds are `config` rows; proximity never compares across fingerprints
(invariant 2); derivation is reproducible on replay.
**Verify.** `cd backend && python -m pytest tests/test_memory_relation_derivation.py -q`

#### T2.17 — Strip-before-rewrite and endpoint self-healing

`Model: Sonnet 5` · `Depends: T2.16` · `Doc: 08 §5.5` · `Tag: target-new` · `Gate: G-C`

**What.** Same idempotence discipline as the entity graph, and self-healing when either
endpoint is deleted.

**Done when:** re-derivation is idempotent; a deleted endpoint leaves no dangling edge.
**Verify.** `cd backend && python -m pytest tests/test_memory_relation_healing.py -q`

---

## Lane E — topics

#### T2.18 — `memory_communities` + members, Leiden per project

`Model: Opus 5` · `Depends: T2.07` · `Doc: 06 §7` · `Tag: target-new` · `Gate: G-C`

**What.** Materialised Leiden communities over a project-scoped projection,
delete-and-rewritten per project.

**Done when:**
- [ ] Detection is project-scoped; no cross-project community is representable
- [ ] Rewrite is atomic per project
- [ ] **No test pins exact community membership** — Leiden is not deterministic across
      implementations and a pinned test is a permanent flake (doc 17 §7)

**Verify.** `cd backend && python -m pytest tests/test_communities.py -q`

#### T2.19 — Labelling + `report_string` off the hot path

`Model: Sonnet 5` · `Depends: T2.18` · `Doc: 06 §7` · `Tag: target-new` · `Gate: G-C`

**What.** Label from dominant entities; generate the LLM report as Tier-C work.

**Done when:** labels derive deterministically; report generation never blocks a read;
a missing report renders as pending, not as absent.
**Verify.** `cd backend && python -m pytest tests/test_community_reports.py -q`

#### T2.20 — Browsing, report injection, pin-suggestion diff

`Model: Sonnet 5` · `Depends: T2.19` · `Doc: 09 §3` · `Tag: target-new` · `Gate: G-C`

**What.** The three read/derive operations doc 09 owns over doc 06's durable rows,
including diffing across runs into pin suggestions a human accepts or dismisses.

**Done when:** pin suggestions key on the stable dominant-entity label, not the churning
community id; accept/dismiss persists.
**Verify.** `cd backend && python -m pytest tests/test_pin_suggestions.py -q`

#### T2.21 — `memory_overview` map-reduce tool

`Model: Opus 5` · `Depends: T2.19` · `Doc: 09 §3.3` · `Tag: target-new` · `Gate: G-C`

**What.** Map over precomputed reports, one bounded `summarization` reduce. A separate
MCP tool — **never** per-memory RRF.

**Done when:** cost is bounded by community count, not memory count; the reduce is one
call; both front doors expose it.
**Verify.** `cd backend && python -m pytest tests/test_memory_overview.py -q`

---

## Lane F — review and hygiene queues

#### T2.22 — Review queue (adjudicates truth)

`Model: Sonnet 5` · `Depends: T2.04` · `Doc: 08 §6` · `Tag: target-new` · `Gate: G-C`

**What.** Disputed and under-sourced facts, ungrounded articles. A `status + partial
index` surface — **never a gate on the read path**; disputed items still serve, labelled
with both sides.

**Done when:** queue membership is a partial index, not a scan; a queued item is still
retrievable and still labelled.
**Verify.** `cd backend && python -m pytest tests/test_review_queue.py -q`

#### T2.23 — Hygiene queue (curates housekeeping) + bulk actions

`Model: Sonnet 5` · `Depends: T2.22` · `Doc: 08 §6` · `Tag: target-new` · `Gate: G-C`

**What.** A distinct surface: duplicates, low-confidence, expiring-soon, superseded
lineage, with bulk actions. Distinct from review because conflating adjudication with
housekeeping is how truth work gets buried under chores.

**Done when:** the two queues share no rows; bulk actions journal per-item, not per-batch;
bulk actions are undoable through the T2.13 primitive.
**Verify.** `cd backend && python -m pytest tests/test_hygiene_queue.py -q`

#### T2.24 — Consequence ranking + dispute-staleness decay

`Model: Opus 5` · `Depends: T2.22` · `Doc: 08 §6` · `Tag: target-new` · `Gate: G-C`

**What.** Ranked by retrieval frequency + subject salience, **never FIFO**. Stale disputes
auto-expire off the *active* queue past `dispute_stale_days` but stay `disputed` and
served labelled — decay changes priority, never verification status.

**Done when:**
- [ ] Ranking is consequence-based and explainable per item
- [ ] A decayed dispute is still `disputed` and still labelled, proven by test
- [ ] `dispute_stale_days` is a `config` row

**Verify.** `cd backend && python -m pytest tests/test_queue_ranking.py -q`

---

## Lane G — the groundedness judge (clears G-D)

#### T2.25 — Labelled entailment gold set

`Model: Fable 5` · `Depends: T2.03` · `Doc: 17 §6` · `Tag: target-new` · `Gate: G-D`

**What.** Claim/fact entailment gold, seeded from real synthesis drafts once L2 is live.
This gold set is what G-D measures against; build it before the judge so the judge cannot
be tuned to its own test.

**Done when:** grounded and ungrounded sentences both represented, including hard
near-misses; labelling rationale recorded; gold is JSON on disk.
**Verify.** `cd backend && python -m pytest scripts/benchlib/tests/test_entailment_gold.py -q`

#### T2.26 — `verification`-purpose judge + precision/recall bars

`Model: Fable 5` · `Depends: T2.25` · `Doc: 17 §6, 11 §6` · `Tag: target-new` · `Gate: G-D`

**What.** One judge, three consumers: the Phase-2 contradiction veto, Phase-3 synthesis,
and the F8 horizon. Qualify it **before** any consumer's layer ships.

**Done when:**
- [ ] Precision and recall measured on the gold set and recorded
- [ ] Bars live as `config` rows with stated defaults
- [ ] Below the bar, no L3 article may ship as grounded — enforced in code, not by policy
- [ ] Result written to `gate-ledger.md` under G-D

**Verify.** `cd backend && python scripts/benchlib/run_judge_qualification.py`

---

## Lane H — the code deriver (after G-C)

**Entry condition: G-C cleared.** This lane ships only once L2 is proven live.

#### T2.27 — `assert_from_repo` — imports-only, LLM-free

`Model: Opus 5` · `Depends: T2.40, T0.13` · `Doc: 10 §6` · `Tag: target-new` · `Gate: G-C`

**What.** A narrow deterministic deriver minting Layer-1 assertions from a repo's import
edges only, tagged into the inert `entities.repo_ids[]` / `entity_relations.repo_ids[]`
landed in T0.13 — **this is their first writer.**

**Done when:**
- [ ] Imports only; no LLM call anywhere in the path
- [ ] Existing graph sweeps stay byte-identical in behaviour with `repo_ids[]` populated
- [ ] Re-derivation is idempotent per repo

**Verify.** `cd backend && python -m pytest tests/test_code_deriver.py -q`

#### T2.28 — Lift to facts born `corroborated`

`Model: Opus 5` · `Depends: T2.27, T2.10` · `Doc: 10 §6, 08 §4.1` · `Tag: target-new` · `Gate: G-C`

**What.** Consolidation lifts a corroborated Layer-1 assertion to a fact born
`corroborated` — the parse *is* the verification — with `origin_key = repo_id`. **One
origin per repo regardless of commit count**, matching the one-document-one-origin rule.

**Done when:**
- [ ] A repo indexed 100 times still counts as one origin, proven by test
- [ ] Born-corroborated is the only exception to the ladder, and it is documented as such
- [ ] Withdrawal (repo removed) demotes the derived facts

**Verify.** `cd backend && python -m pytest tests/test_deriver_lift.py -q`

---

## Lane I — retrieval-arm activations (doc 20 §5 matrix)

Every task here needs a **measured retrieval-eval win with its latency/cost twin** before
the arm leaves zero. An arm that cannot show its number stays at zero — that is the
deliverable, not a failure.

#### T2.29 — `memory_access_stats` feeder

`Model: Sonnet 5` · `Depends: T1.30` · `Doc: 07 §3` · `Tag: target-new` · `Gate: G-C`

**What.** The substrate `w_heat` and `w_recency` read. Landing the feeder is the
deliverable; the arms stay at zero until T2.31 measures them.

**Done when:** access recorded off the hot path; no read-path latency regression measured.
**Verify.** `cd backend && python -m pytest tests/test_access_stats.py -q`

#### T2.30 — `w_importance` activation

`Model: Fable 5` · `Depends: T1.31` · `Doc: 07 §3` · `Tag: activation` · `Gate: G-C`

**What.** The column is populated but unread today. Measure, then activate or leave at zero.
**Activation bar:** a positive retrieval-eval delta with its twin.

**Done when:** delta measured per slice with p95 latency and token cost; the decision and
its number are in the ledger — including a decision to leave it at zero.
**Verify.** `cd backend && python scripts/benchlib/run_retrieval_eval.py --arm w_importance`

#### T2.31 — `w_heat` / `w_recency` activation

`Model: Fable 5` · `Depends: T2.29` · `Doc: 07 §3` · `Tag: activation` · `Gate: G-C`

**What.** Same protocol, over the T2.29 feeder. **Activation bar:** retrieval-eval win
with twin.

**Done when:** per-slice deltas recorded; recency's interaction with the belief axis
checked (a fresh wrong fact must not outrank an older verified one).
**Verify.** `cd backend && python scripts/benchlib/run_retrieval_eval.py --arm w_heat,w_recency`

#### T2.32 — PPR snapshot job + graph arms

`Model: Opus 5` · `Depends: T2.18` · `Doc: 07 §3, 02 §11` · `Tag: target-new` · `Gate: G-C`

**What.** Graph arms (`w_ppr`, dual-level, community injection) need the snapshot job live
first. The cached igraph snapshot is one of the in-process assumptions that binds
invariant 13 — note it for the Phase-4 multi-replica decision.

**Done when:** snapshot job scheduled with lock and floor; arms default 0; community
injection is measured on **answer-quality/groundedness**, not MRR — it augments context,
it is not a ranking signal (doc 17 §2).
**Verify.** `cd backend && python -m pytest tests/test_ppr_snapshot.py -q`

#### T2.33 — `triple_embeddings` writer, miss-rate gated

`Model: Opus 5` · `Depends: T2.11, T0.13` · `Doc: 08 §5.3` · `Tag: target-new` · `Gate: G-C`

**What.** First writer to the template landed inert in T0.13 — and it ships **only** if
T2.11's measured `pg_trgm` shortlist miss rate exceeds its stated bar. Groups facts for
counting only; never merges rows, never rewrites `triple_key`.

**Done when:** miss rate measured and compared to the bar before any code ships; if the
bar is not exceeded, the task closes as "not needed, measured" and the template stays
inert; `names_distinct` is carried into the grouping.
**Verify.** `cd backend && python scripts/benchlib/run_contradiction_missrate.py`

#### T2.34 — `expires_at` self-expiring dated facts

`Model: Sonnet 5` · `Depends: T2.01, T1.37` · `Doc: 08 §2.3` · `Tag: activation` · `Gate: G-C`

**What.** The activation half of Phase-1's caller-set TTL: facts carrying a date expire
themselves. Deterministic — no measured bar, it follows with the temporal passes.

**Done when:** a dated fact expires without a caller setting TTL; the demote-before-delete
ordering from T1.37 is reused, not reimplemented.
**Verify.** `cd backend && python -m pytest tests/test_self_expiring_facts.py -q`

#### T2.35 — `applies_when` magnitude tuning

`Model: Sonnet 5` · `Depends: T1.34` · `Doc: 07, 09 §5` · `Tag: target-new` · `Gate: G-C`

**What.** Tune the `config` magnitude wired in T1.34. The boost-plus-label and
conflict-count rules stay hard rules — only the magnitude is tuned.

**Done when:** magnitude tuned against the retrieval eval; the hard-rule tests still pass
unchanged at every magnitude tried.
**Verify.** `cd backend && python scripts/benchlib/run_retrieval_eval.py --arm applies_when`

---

## Lane J — UI (F9: signal ships with surface)

#### T2.36 — Facts tab — bi-temporal, multi-origin browsing

`Model: Sonnet 5` · `Depends: T2.03` · `Doc: 13 §5.1, §5.3` · `Tag: target-new` · `Gate: G-C`

**What.** Verification badges rendered **verbatim** — the badge string is the claim, never
softened or recomputed client-side. Both axes visible; disputed shows both sides.

**Done when:** badges verbatim from the backend; belief and verification axes distinct in
the UI; disputed items render both sides, never one; virtualized and paged.
**Verify.** `cd frontend && npm test -- facts && npm run test:e2e -- knowledge`

#### T2.37 — Review / Hygiene triage shell

`Model: Sonnet 5` · `Depends: T2.24` · `Doc: 13 §6.2` · `Tag: target-new` · `Gate: G-C`

**What.** Two distinct surfaces, consequence-ranked, with the queue's reasoning visible.

**Done when:** the two queues are visibly distinct; ranking rationale shown per item;
bulk actions confirm before applying and are undoable.
**Verify.** `cd frontend && npm test -- review`

#### T2.38 — Dream digest UI with undo

`Model: Sonnet 5` · `Depends: T2.13` · `Doc: 13 §6.3` · `Tag: target-new` · `Gate: G-C`

**What.** A cycle's actions grouped, each with before/after and per-action or per-batch
undo.

**Done when:** every action shows what changed; undo is reachable at both granularities;
an undone action still appears, marked undone.
**Verify.** `cd frontend && npm test -- dream-digest`

#### T2.39 — Topics tab

`Model: Sonnet 5` · `Depends: T2.20` · `Doc: 13 §5` · `Tag: target-new` · `Gate: G-C`

**What.** Browsing, report injection, pin-suggestion diff.

**Done when:** a pending report renders as pending; pin suggestions show what changed
between runs; accept/dismiss round-trips.
**Verify.** `cd frontend && npm test -- topics`

---

## Lane K — gates

#### T2.40 — G-C evidence run

`Model: Fable 5` · `Depends: T2.06, T2.24` · `Doc: 20 §4` · `Tag: target-new` · `Gate: G-C`

**What.** Promotion rate `(promoted / eligible)` sliced by source-kind diversity and by
which N fired; false-promotion audit (corroborated facts later disputed or human-rejected)
under the stated bar; every ladder transition journaled.

**Done when:** all three measured from the `events` journal by SQL; bars stated as
`config` before measuring, not after; verdict in `gate-ledger.md`; a miss leaves G-C open
and the deriver lane (T2.27–T2.28) closed.
**Verify.** `cd backend && python scripts/benchlib/run_promotion_metrics.py`

#### T2.41 — G-D evidence run

`Model: Fable 5` · `Depends: T2.26` · `Doc: 20 §4` · `Tag: target-new` · `Gate: G-D`

**What.** The judge's precision/recall on the labelled gold clears its bar — the single
gate that opens Phase 3.

**Done when:** precision and recall recorded per class; the bar was stated before the run;
verdict in `gate-ledger.md`; E3 stays closed on a miss.
**Verify.** `cd backend && python scripts/benchlib/run_judge_qualification.py --gate`

---

## Amendment log

| Date | Task | Tier | Change | Why |
|---|---|---|---|---|
| — | — | — | (none yet) | — |
