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

`Model: Opus 5` · `Effort: high` · `Size: L` · `Depends: T1.50, T1.06` · `Doc: 08 §3–§4` · `Tag: rebuild + target-new` · `Gate: G-C`

**What.** Two orthogonal axes: belief (open → window-closed → expired) and verification
(candidate → corroborated → confirmed, plus disputed). Conflating them is the modelling
error this rebuild exists to fix — a fact can be well-verified and no longer current.

**Done when:**
- [ ] The two axes are independently queryable and independently transitioned
- [ ] A confirmed-but-expired fact is representable and renders as such
- [ ] `triple_key` identity is stable across re-derivation

**Verify.** `cd backend && python -m pytest tests/test_knowledge_triples.py -q`

#### T2.02 — `fact_sources` and origin-diversity counting

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.01, T1.11` · `Doc: 08 §4.1` · `Tag: target-new` · `Gate: G-C`

**What.** Promotion counts `COUNT(DISTINCT origin_key)` over `fact_sources` — **never
rows**. Row-counting manufactures agreement out of one chatty source; this is the single
most important arithmetic in the epic.

**Done when:**
- [ ] Distinct-origin counting proven by a test that fails under row-counting
- [ ] The same source asserting a fact ten times counts as one origin
- [ ] Source kinds recorded (`memory`, `code`, `human`, later `block`)

**Verify.** `cd backend && python -m pytest tests/test_fact_sources.py -q`

#### T2.03 — The verification ladder

`Model: Opus 5` · `Effort: high` · `Size: L` · `Depends: T2.02` · `Doc: 08 §4` · `Tag: target-new` · `Gate: G-C`

**What.** Promotion from candidate → corroborated on distinct-origin diversity, with N
and the diversity rule as `config` rows.

**Done when:**
- [ ] Promotion is a pure function of the ladder inputs — reproducible on replay
- [ ] N and the diversity rule read from `config`, defaults stated
- [ ] Loosening either requires a G-C measurement (T2.40), not an edit

**Verify.** `cd backend && python -m pytest tests/test_verification_ladder.py -q`

#### T2.04 — The contradiction veto is absolute

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.03` · `Doc: 08 §4.2` · `Tag: target-new` · `Gate: G-C`

**What.** A single non-echo contradiction over an overlapping validity window vetoes to
`disputed`. Absolute — not a weight, not a score, not tunable.

**Done when:**
- [ ] One contradiction beats any number of corroborations, proven by test
- [ ] Echoes (the same origin restating itself) do not count as contradiction
- [ ] Validity-window overlap is required — non-overlapping claims are not contradictions
- [ ] No `config` knob can soften the veto
- [ ] Ships the `honesty/veto-absolute` e2e spec: one contradiction beats any number of
      corroborations

**Verify.** `cd backend && python -m pytest tests/test_contradiction_veto.py -q`

#### T2.05 — Human ratification is the only path to `confirmed`

`Model: Opus 5` · `Effort: high` · `Size: S` · `Depends: T2.03` · `Doc: 08 §4.4` · `Tag: target-new` · `Gate: G-C`

**What.** Only a human ratifying, writing a `human`-kind `fact_sources` row, reaches
`confirmed`. No machine path exists.

**Done when:**
- [ ] No code path sets `confirmed` without a `human` source row
- [ ] Ratification is single-door by design (doc 18) and never an API-key scope
- [ ] The ratifier and timestamp are recorded
- [ ] Ships the `honesty/human-only-confirmed` e2e spec: no machine path reaches
      `confirmed`

**Verify.** `cd backend && python -m pytest tests/test_ratification.py -q`

#### T2.06 — Every ladder transition journaled

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T2.03, T1.07` · `Doc: 08 §4` · `Tag: target-new` · `Gate: G-C`

**What.** G-C is computed *from* the journal, so an unjournaled transition is an
unmeasurable one.

**Done when:**
- [ ] Every transition writes an event with before/after and the triggering evidence
- [ ] The G-C metrics are derivable by SQL over `events` alone

**Verify.** `cd backend && python -m pytest tests/test_ladder_journaling.py -q`

---

## Lane B — the `projects` registry

#### T2.07 — `projects` table + lazy registration

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.50, T1.12` · `Doc: 04 §7, 09 §5` · `Tag: target-new` · `Gate: G-C`

**What.** The table itself lands in the baseline (T0.12b); this task wires its use.
Capture registers lazily via `INSERT … ON CONFLICT (name) DO NOTHING`, closing the
typo'd-project fact-identity split, and existing project strings backfill. The registry
anchors per-project `applies_when` defaults, review-queue scoping, and the
one-live-article-per-subject rule.

**Done when:**
- [ ] Capture registers unseen projects without a round trip or a failure mode
- [ ] A typo creates a visible project rather than a silent parallel universe
- [ ] Existing project strings backfill into the registry

**Verify.** `cd backend && python -m pytest tests/test_projects_registry.py -q`

---

## Lane C — consolidation ("dreaming")

#### T2.08 — Job-family umbrella under JobRegistry

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T2.01` · `Doc: 08 §5` · `Tag: target-new` · `Gate: G-C`

**What.** Several cooperating Tier-C jobs under one schedule umbrella, each with its own
cron, floor, ceiling, and per-job lock. Reconciliation stays off the hot path
(invariant 15) — no job here may be called from capture or retrieval to "accelerate" a gate.

**Done when:**
- [ ] Each job independently scheduled, locked, and configurable
- [ ] A manual trigger while the lock is held returns 409, never queues
- [ ] No Tier-A/B caller can invoke any of them

**Verify.** `cd backend && python -m pytest tests/test_dream_jobs.py -q`

#### T2.09 — `verification_recompute`

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T2.08, T2.03, T2.47` · `Doc: 08 §5` · `Tag: target-new` · `Gate: G-C`

**What.** Recompute ladder state as sources accumulate or withdraw.

**Done when:** recompute is idempotent; a withdrawn source demotes correctly; each change
journals.
**Verify.** `cd backend && python -m pytest tests/test_verification_recompute.py -q`

#### T2.10 — `fact_lift`

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.08, T2.02` · `Doc: 08 §5` · `Tag: target-new` · `Gate: G-C`

**What.** Lift corroborated L1 relations into L2 facts, writing the `fact_sources` rows
that justify them.

**Done when:** lifting is idempotent on re-run; every lifted fact traces to its source
rows; no fact is born above `corroborated` except via T2.28's parse-is-verification
rule; and **`fact_lift` emits a `sources_changed` event per touched fact** (doc 08 §5.2)
under T2.47's provenance no-op guard. This is the emitter that matters: doc 05 §8.4 makes
the Phase-5 hook a no-op on first ingest, because a brand-new memory has no `fact_sources`
rows yet — without this emit, newly lifted facts are never enqueued for promotion.
**Verify.** `cd backend && python -m pytest tests/test_fact_lift.py -q`

#### T2.11 — `contradiction_scan`

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.04, T2.26` · `Doc: 08 §5` · `Tag: target-new` · `Gate: G-C`

**What.** Generate contradiction candidates from **same-endpoint facts plus a
`pg_trgm`-on-`fact` shortlist** (doc 08 §5.3 — the combined generator, not the trigram
half alone), then adjudicate with the `verification` judge. The judge must already be
qualified: the Phase-2 veto is its first consumer, and T2.26's rule is that no
consumer ships on an unqualified judge. The generator's measured miss rate (T2.52) is
what gates T2.33.

**Done when:** the combined generator emits candidates; adjudication uses the qualified
judge, not a heuristic; misses are counted, not hidden. **Recall measurement is T2.52's**,
not this task's — measuring it here would require a runner that depends on this task.
**Verify.** `cd backend && python -m pytest tests/test_contradiction_scan.py -q`

#### T2.12 — `memory_dream` — never hard-merges, never deletes

`Model: Opus 5` · `Effort: high` · `Size: L` · `Depends: T2.08, T2.45` · `Doc: 08 §5.4` · `Tag: target-new` · `Gate: G-C`

**What.** Subsumption routes through the `supersede()` primitive; near-duplicates get an
associative edge plus a hygiene item; `refine` rewrites only derived fields, **never
`content`**. Invalidate-not-delete is what makes T2.13's undo tractable.

**Done when:**
- [ ] No path deletes or hard-merges a memory, proven by test
- [ ] `refine` cannot touch `content`
- [ ] Every action writes a before/after event payload

**Verify.** `cd backend && python -m pytest tests/test_memory_dream.py -q`

#### T2.13 — Dream digest + per-action and per-batch undo

`Model: Opus 5` · `Effort: high` · `Size: L` · `Depends: T2.12` · `Doc: 08 §7` · `Tag: target-new` · `Gate: G-C`

**What.** Group a cycle's actions into a digest and offer undo at both granularities.
Tractable precisely because every inverse is a status, pointer, or timestamp restore.

**Done when:**
- [ ] Undo restores exact prior state for every action type
- [ ] Batch undo is atomic — partial undo is not representable
- [ ] Undo itself journals (an undo is an action, not an erasure)

**Verify.** `cd backend && python -m pytest tests/test_dream_undo.py -q`

#### T2.14 — Register `article_synthesis` inert

`Model: Haiku 4.5` · `Effort: high` · `Size: S` · `Depends: T2.08` · `Doc: 08 §5.6` · `Tag: target-new, inert` · `Gate: G-C`

**What.** Registered under the umbrella now; productive runs are Phase 3 behind G-D.

**Done when:** job exists, scheduled off; labelled inert naming T3.02 as its first
productive run.
**Verify.** `cd backend && python -m pytest tests/test_inert_objects.py -q`

---

## Lane D — memory relations (the associative layer)

#### T2.15 — Five associative types + normaliser

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T1.50, T1.23` · `Doc: 06 §3.1, 08 §5.5` · `Tag: target-new` · `Gate: G-C`

**What.** `CONTRADICTS`, `ELABORATES`, `DEPENDS_ON`, `FOLLOWS`, `RELATES_TO` through
`normalize_memory_relation_type`. **`SUPERSEDES` is never written here** — it stays the
projected `superseded_by` pointer.

**Done when:** only the five are storable; `SUPERSEDES` is rejected; unknown types fall
back within the closed set.
**Verify.** `cd backend && python -m pytest tests/test_memory_relation_types.py -q`

#### T2.16 — Derivation from overlap, proximity, and contradiction

`Model: Opus 5` · `Effort: high` · `Size: L` · `Depends: T2.15, T2.12` · `Doc: 08 §5.5` · `Tag: target-new` · `Gate: G-C`

**What.** `memory_dream` derives the edges from entity overlap, embedding proximity, and
contradiction checks.

**Done when:** thresholds are `config` rows; proximity never compares across fingerprints
(invariant 2); derivation is reproducible on replay.
**Verify.** `cd backend && python -m pytest tests/test_memory_relation_derivation.py -q`

#### T2.17 — Strip-before-rewrite and endpoint self-healing

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T2.16` · `Doc: 08 §5.5` · `Tag: target-new` · `Gate: G-C`

**What.** Same idempotence discipline as the entity graph, and self-healing when either
endpoint is deleted.

**Done when:** re-derivation is idempotent; a deleted endpoint leaves no dangling edge.
**Verify.** `cd backend && python -m pytest tests/test_memory_relation_healing.py -q`

---

## Lane E — topics

#### T2.18 — `memory_communities` + members, Leiden per project

`Model: Opus 5` · `Effort: high` · `Size: L` · `Depends: T2.07` · `Doc: 06 §7` · `Tag: target-new` · `Gate: G-C`

**What.** Materialised Leiden communities over a project-scoped projection,
delete-and-rewritten per project.

**Done when:**
- [ ] Detection is project-scoped; no cross-project community is representable
- [ ] Rewrite is atomic per project
- [ ] **No test pins exact community membership** — Leiden is not deterministic across
      implementations and a pinned test is a permanent flake (doc 17 §7)

**Verify.** `cd backend && python -m pytest tests/test_communities.py -q`

#### T2.19 — Labelling + `report_string` off the hot path

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T2.18` · `Doc: 06 §7` · `Tag: target-new` · `Gate: G-C`

**What.** Label from dominant entities; generate the LLM report as Tier-C work.

**Done when:** labels derive deterministically; report generation never blocks a read;
a missing report renders as pending, not as absent.
**Verify.** `cd backend && python -m pytest tests/test_community_reports.py -q`

#### T2.20 — Browsing, report injection, pin-suggestion diff

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T2.19` · `Doc: 09 §3` · `Tag: target-new` · `Gate: G-C`

**What.** The three read/derive operations doc 09 owns over doc 06's durable rows,
including diffing across runs into pin suggestions a human accepts or dismisses.

**Done when:** pin suggestions key on the stable dominant-entity label, not the churning
community id; accept/dismiss persists.
**Verify.** `cd backend && python -m pytest tests/test_pin_suggestions.py -q`

#### T2.21 — `memory_overview` map-reduce tool

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.19` · `Doc: 09 §3.3` · `Tag: target-new` · `Gate: G-C`

**What.** Map over precomputed reports, one bounded `summarization` reduce. A separate
MCP tool — **never** per-memory RRF.

**Done when:** cost is bounded by community count, not memory count; the reduce is one
call; both front doors expose it.
**Verify.** `cd backend && python -m pytest tests/test_memory_overview.py -q`

---

## Lane F — review and hygiene queues

#### T2.22 — Review queue (adjudicates truth)

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T2.04` · `Doc: 08 §6` · `Tag: target-new` · `Gate: G-C`

**What.** Disputed and under-sourced facts, ungrounded articles. A `status + partial
index` surface — **never a gate on the read path**; disputed items still serve, labelled
with both sides.

**Done when:** queue membership is a partial index, not a scan; a queued item is still
retrievable and still labelled.
**Verify.** `cd backend && python -m pytest tests/test_review_queue.py -q`

#### T2.23 — Hygiene queue (curates housekeeping) + bulk actions

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T2.22` · `Doc: 08 §6` · `Tag: target-new` · `Gate: G-C`

**What.** A distinct surface: duplicates, low-confidence, expiring-soon, superseded
lineage, with bulk actions. Distinct from review because conflating adjudication with
housekeeping is how truth work gets buried under chores.

**Done when:** the two queues share no rows; bulk actions journal per-item, not per-batch;
bulk actions are undoable through the T2.13 primitive.
*terminal-by-design — nothing depends on this; it is a backstop, an activation, or a
leaf surface, not infrastructure another task consumes.*

**Verify.** `cd backend && python -m pytest tests/test_hygiene_queue.py -q`

#### T2.24 — Consequence ranking + dispute-staleness decay

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.22` · `Doc: 08 §6` · `Tag: target-new` · `Gate: G-C`

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

`Model: Fable 5` · `Effort: high` · `Size: M` · `Depends: T2.01` · `Doc: 17 §6` · `Tag: target-new` · `Gate: G-D`

**What.** Claim/fact entailment gold. This is what G-D measures against, so build it
before the judge — otherwise the judge is tuned to its own test.

**Where the material comes from, since Phase-3 drafts do not exist yet.** Running
`article_synthesis` manually in a **labelled non-shipping mode against
`darkmem_bench`** produces raw drafts to label; supplement with hand-authored
claim/fact pairs over live L2 facts. Nothing produced this way ships as an article —
it exists to be labelled. Waiting for real drafts would deadlock the gate, since
drafts come from T3.02, which is behind the gate this task feeds.

**Done when:** grounded and ungrounded sentences both represented, including hard
near-misses; labelling rationale recorded; gold is JSON on disk.
**Verify.** `cd backend && python -m pytest scripts/benchlib/tests/test_entailment_gold.py -q`

#### T2.26 — `verification`-purpose judge + precision/recall bars

`Model: Fable 5` · `Effort: high` · `Size: L` · `Depends: T2.25` · `Doc: 17 §6, 11 §6` · `Tag: target-new` · `Gate: G-D`

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

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.40, T0.13` · `Doc: 10 §6` · `Tag: target-new` · `Gate: G-C`

**What.** A narrow deterministic deriver minting Layer-1 assertions from a repo's import
edges only, tagged into the inert `entities.repo_ids[]` / `entity_relations.repo_ids[]`
landed in T0.13 — **this is their first writer.**

**Done when:**
- [ ] Imports only; no LLM call anywhere in the path
- [ ] Existing graph sweeps stay byte-identical in behaviour with `repo_ids[]` populated
- [ ] Re-derivation is idempotent per repo

**Verify.** `cd backend && python -m pytest tests/test_code_deriver.py -q`

#### T2.28 — Lift to facts born `corroborated`

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.27, T2.10` · `Doc: 10 §6, 08 §4.1` · `Tag: target-new` · `Gate: G-C`

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

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.50, T1.30` · `Doc: 07 §3` · `Tag: target-new` · `Gate: G-C`

**What.** The substrate `w_heat` and `w_recency` read. Landing the feeder is the
deliverable; the arms stay at zero until T2.31 measures them.

**Done when:** access recorded off the hot path; no read-path latency regression measured.
**Verify.** `cd backend && python -m pytest tests/test_access_stats.py -q`

#### T2.30 — `w_importance` activation

`Model: Fable 5` · `Effort: high` · `Size: M` · `Depends: T1.31, T2.44` · `Doc: 07 §3` · `Tag: activation` · `Gate: standing`

**What.** The column is populated but unread today. Measure, then activate or leave at zero.
**Activation bar:** a positive retrieval-eval delta with its twin.

**Done when:** delta measured per slice with p95 latency and token cost; the decision and
its number are in the ledger — including a decision to leave it at zero.
**Verify.** `cd backend && python scripts/benchlib/run_retrieval_eval.py --arm w_importance`

#### T2.31 — `w_heat` / `w_recency` activation

`Model: Fable 5` · `Effort: high` · `Size: M` · `Depends: T2.29, T2.44` · `Doc: 07 §3` · `Tag: target-new + activation` · `Gate: standing`

**What.** Same protocol, over the T2.29 feeder. **Activation bar:** retrieval-eval win
with twin.

**Done when:** per-slice deltas recorded; recency's interaction with the belief axis
checked (a fresh wrong fact must not outrank an older verified one).
**Verify.** `cd backend && python scripts/benchlib/run_retrieval_eval.py --arm w_heat,w_recency`

#### T2.32 — PPR snapshot job + graph arms

`Model: Opus 5` · `Effort: high` · `Size: L` · `Depends: T2.18` · `Doc: 07 §3, 02 §11` · `Tag: target-new` · `Gate: G-C`

**What.** Graph arms (`w_ppr`, dual-level, community injection) need the snapshot job live
first. The cached igraph snapshot is one of the in-process assumptions that binds
invariant 13 — note it for the Phase-4 multi-replica decision.

**Done when:** snapshot job scheduled with lock and floor; arms default 0; community
injection is measured on **answer-quality/groundedness**, not MRR — it augments context,
it is not a ranking signal (doc 17 §2).
**Verify.** `cd backend && python -m pytest tests/test_ppr_snapshot.py -q`

#### T2.33 — `triple_embeddings` writer, miss-rate gated

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.52, T0.13` · `Doc: 08 §5.3` · `Tag: target-new` · `Gate: standing`

**What.** First writer to the template landed inert in T0.13 — and it ships **only** if
T2.11's measured `pg_trgm` shortlist miss rate exceeds its stated bar. Groups facts for
counting only; never merges rows, never rewrites `triple_key`.

**Done when:** miss rate measured and compared to the bar before any code ships; if the
bar is not exceeded, the task closes as "not needed, measured" and the template stays
inert; `names_distinct` is carried into the grouping.
*terminal-by-design — nothing depends on this; it is a backstop, an activation, or a
leaf surface, not infrastructure another task consumes.*

**Verify.** `cd backend && python scripts/benchlib/run_contradiction_missrate.py`

#### T2.34 — `expires_at` self-expiring dated facts

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.01, T1.37` · `Doc: 08 §2.3` · `Tag: activation` · `Gate: G-C`

**What.** Two different mechanisms that must not be conflated (doc 08 §2.3 vs §9).

**Memory side:** extraction populates `memories.expires_at` from a memory's own stated
expiry date (the write path is doc 05's; the sweep that spends it is T1.37's, reused
unchanged including demote-before-delete).

**Fact side:** a fact carrying a stated future expiry gets its belief window
**pre-closed** at that date by a lightweight arm of `verification_recompute` —
**invalidate-not-delete**, so the row survives as history. The facts table needs no
delete job at all (doc 08 §5); applying T1.37's delete sweep to `knowledge_triples`
would destroy the history the whole bi-temporal model exists to keep.

**Done when:**
- [ ] A dated memory expires without a caller setting TTL, through T1.37's sweep
- [ ] A dated fact's window pre-closes; the row is never deleted, proven by test
- [ ] No code path deletes from `knowledge_triples`

**Verify.** `cd backend && python -m pytest tests/test_self_expiring_facts.py -q`

#### T2.35 — `applies_when` magnitude tuning

`Model: Fable 5` · `Effort: high` · `Size: M` · `Depends: T1.34, T2.44` · `Doc: 07, 09 §5` · `Tag: target-new` · `Gate: standing`

**What.** Tune the `config` magnitude wired in T1.34. The boost-plus-label and
conflict-count rules stay hard rules — only the magnitude is tuned.

**Done when:** magnitude tuned against the retrieval eval; the hard-rule tests still pass
unchanged at every magnitude tried.
**Verify.** `cd backend && python scripts/benchlib/run_retrieval_eval.py --arm applies_when`

---

## Lane J — UI (F9: signal ships with surface)

#### T2.36 — Facts tab — bi-temporal, multi-origin browsing

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T2.03` · `Doc: 13 §5.1, §5.3` · `Tag: target-new` · `Gate: G-C`

**What.** Verification badges rendered **verbatim** — the badge string is the claim, never
softened or recomputed client-side. Both axes visible; disputed shows both sides.

**Done when:** badges verbatim from the backend; belief and verification axes distinct in
the UI; disputed items render both sides, never one; virtualized and paged; and the
**Simple/Advanced flag is honoured** — Simple hides the technical detail and still renders
every honesty label (T1.48's rule, invariant 14).
**Verify.** `cd frontend && npm test -- facts && npm run test:e2e -- knowledge`

#### T2.37 — Review / Hygiene triage shell

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T2.24` · `Doc: 13 §6.2` · `Tag: target-new` · `Gate: G-C`

**What.** Two distinct surfaces, consequence-ranked, with the queue's reasoning visible.

**Done when:** the two queues are visibly distinct; ranking rationale shown per item;
bulk actions confirm before applying and are undoable; Simple/Advanced honoured.
**Verify.** `cd frontend && npm test -- review`

#### T2.38 — Dream digest UI with undo

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T2.13` · `Doc: 13 §6.3` · `Tag: target-new` · `Gate: G-C`

**What.** A cycle's actions grouped, each with before/after and per-action or per-batch
undo.

**Done when:** every action shows what changed; undo is reachable at both granularities;
an undone action still appears, marked undone; Simple/Advanced honoured.
**Verify.** `cd frontend && npm test -- dream-digest`

#### T2.39 — Topics tab

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T2.20` · `Doc: 13 §5` · `Tag: target-new` · `Gate: G-C`

**What.** Browsing, report injection, pin-suggestion diff.

**Done when:** a pending report renders as pending; pin suggestions show what changed
between runs; accept/dismiss round-trips; Simple/Advanced honoured.
**Verify.** `cd frontend && npm test -- topics`

---

## Lane K — gates

#### T2.40 — G-C evidence run

`Model: Fable 5` · `Effort: xhigh` · `Size: M` · `Depends: T2.06, T2.09, T2.10, T2.11, T2.24, T2.51` · `Doc: 20 §4` · `Tag: target-new` · `Gate: G-C`

**What.** Promotion rate `(promoted / eligible)` sliced by source-kind diversity and by
which N fired; false-promotion audit (corroborated facts later disputed or human-rejected)
under the stated bar; every ladder transition journaled.

**Done when:** all three measured from the `events` journal by SQL; bars stated as
`config` before measuring, not after; **facts have actually flowed through the ladder**
(a 0/0 promotion rate is under-powered, not a pass); verdict in `gate-ledger.md`;
`CLAUDE.md` refreshed to the shipped L2 shape; a miss leaves G-C open and the deriver
lane (T2.27–T2.28) closed.
**Verify.** `cd backend && python scripts/benchlib/run_promotion_metrics.py`

#### T2.41 — G-D evidence run

`Model: Fable 5` · `Effort: xhigh` · `Size: M` · `Depends: T2.26` · `Doc: 20 §4` · `Tag: target-new` · `Gate: G-D`

**What.** The judge's precision/recall on the labelled gold clears its bar — the single
gate that opens Phase 3.

**Done when:** precision and recall recorded per class; the bar was stated before the run;
verdict in `gate-ledger.md`; `CLAUDE.md` refreshed for the judge and its config rows;
E3 stays closed on a miss.
**Verify.** `cd backend && python scripts/benchlib/run_judge_qualification.py --gate`

---

## Lane L — mechanisms the first draft missed (added by review)

Findings A-4, A-5, A-13, B-F7, B-F9. Each traces to a design-doc mechanism with no owning
task; without them E2 ships facts nobody can retrieve and G-C measures machinery that was
never built.

#### T2.42 — Facts retrieval channel, born with pushdown

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.03, T1.29c` · `Doc: 07 §2` · `Tag: target-new` · `Gate: G-C`

**What.** Doc 07 §2 makes the facts channel target-new and **born with SQL project/status
pushdown** — it never has a pre-pushdown generation to regress from. Without it, E2's
whole truth core is unreachable by search.

**Done when:**
- [ ] Channel queries `knowledge_triples` with scope predicates in SQL from the first commit
- [ ] Verification state and belief window ride every returned row as labels
- [ ] Disputed facts are returned **labelled with both sides**, never filtered out

**Verify.** `cd backend && python -m pytest tests/test_facts_channel.py -q`

#### T2.43 — Four-layer composition, labelling, and grouping

`Model: Opus 5` · `Effort: high` · `Size: L` · `Depends: T2.42` · `Doc: 07 §5` · `Tag: target-new` · `Gate: G-C`

**What.** Doc 07 §5's composition rules over the four layers — L0 memory, L1 candidate
graph (not directly served), L2 verified facts, L3 subject articles: the
verified-above-labelled-candidate ordering, and disputed served with both sides.

**Code search is not one of the layers.** It is a repository-gated, semantic-only sibling
that **never fuses** with the memory/vault composition (doc 07 §2). Grouping and
cold-start are T2.55; the output shapes are T2.56.

**Done when:**
- [ ] The ordering rule has a test that fails if the rule is removed
- [ ] Disputed facts are served with both sides, never one
- [ ] A test asserts code search cannot enter the composition

**Verify.** `cd backend && python -m pytest tests/test_layer_composition.py -q`

#### T2.44 — Arm-ablation interface for the retrieval eval

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T1.50, T0.10, T1.31` · `Doc: 17 §4` · `Tag: target-new` · `Gate: standing`

**What.** The plumbing behind `run_retrieval_eval.py --arm <name>`, which T2.30, T2.31,
T2.35 and T2.50 all invoke and which T0.10 never scoped. Sonnet builds it; the Fable
activation tasks only design the bar and read the result (runbook §2).

**Done when:**
- [ ] `--arm` runs the eval with a named arm on and off, reporting per-slice deltas
- [ ] Every run emits its latency/cost twin, since an accuracy number without one is
      inadmissible
- [ ] Ablation pins the fingerprint — no cross-fingerprint comparison (invariant 2)

**Verify.** `cd backend && python scripts/benchlib/run_retrieval_eval.py --arm w_importance`

#### T2.45 — The Tier-C `supersede()` primitive + status bridge

`Model: Opus 5` · `Effort: high` · `Size: L` · `Depends: T2.01, T1.36` · `Doc: 08 §2.2, §3.4` · `Tag: target-new` · `Gate: G-C`

**What.** T2.12 calls `supersede()` but nothing builds it. Doc 08 §2.2 makes it a Tier-C
primitive distinct from T1.36's write-time detector, and §3.4's status bridge decides what
happens to an asserting memory when its fact is invalidated: `superseded` only under two
guards, otherwise `deprecated`.

**Done when:**
- [ ] The primitive is the single path by which consolidation supersedes anything
- [ ] The status bridge's two guards are tested independently, and **they fail
      differently** (doc 08 §3.4, corrected 2026-07-25): guard 1 failing means the successor
      is not well-defined, so the memory goes to `deprecated` with `superseded_by=NULL`;
      guard 2 failing means the bridge does not apply at all, so the memory's status is
      **unchanged**. A test asserts that a memory still asserting live facts is left alone —
      deprecating it would drop live knowledge out of the active view, which is what guard 2
      exists to prevent
- [ ] `chk_superseded_has_pointer` holds through every transition

**Verify.** `cd backend && python -m pytest tests/test_supersede_primitive.py -q`

#### T2.46 — Demotion hysteresis and the `under-sourced` label

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.09` · `Doc: 08 §4.3, §9` · `Tag: target-new` · `Gate: G-C`

**What.** A fact that loses a source does not drop rung immediately: it enters a labelled
`under-sourced` state for `verification_demote_grace_cycles`, tracked by a
`demotion_pending_since` column. Without hysteresis a flapping source flaps the ladder,
and every flap is a visible badge change.

**Done when:**
- [ ] `demotion_pending_since` lands on the schema; grace cycles are a `config` row
- [ ] An under-sourced fact is **served labelled**, not withheld
- [ ] Regaining a source inside the grace window cancels the demotion cleanly

**Verify.** `cd backend && python -m pytest tests/test_demotion_hysteresis.py -q`

#### T2.47 — The enqueue-for-verification emit hook

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T1.21, T2.02` · `Doc: 05 §8.4, 08 §3.3` · `Tag: target-new` · `Gate: G-C`

**What.** The emit side of the hook that tells verification a fact's evidence moved: the
`sources_changed` `events` value landed taxonomy-first, emitted from Phase 5 and from the
withdrawal sweep, with the inline expire-on-last-source-withdrawal path — and a
**provenance no-op guard** so a re-extraction that changes nothing emits nothing.

**The third emitter is `fact_lift`'s (doc 08 §5.2) and it belongs to T2.10.** It is the
one that fires on fresh data, since the Phase-5 hook is usually a no-op on first ingest.

**Done when:**
- [ ] `sources_changed` is in the closed events vocabulary before any emitter uses it
- [ ] A no-op re-extraction emits no event, proven by test (otherwise every reprocess
      would look like evidence churn)
- [ ] Losing the last source expires inline rather than waiting for a sweep

**Verify.** `cd backend && python -m pytest tests/test_sources_changed_emit.py -q`

#### T2.48 — Citation re-verifier + code-fact lifecycle

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.28` · `Doc: 10 §6` · `Tag: target-new` · `Gate: G-C`

**What.** Doc 10 §6's second sanctioned crossing: a Tier-C re-verifier walks
`fact_sources(kind='code')` rows whose `detail.symbol_key` falls in a run's changed or
deleted file set, marks the row stale and **downgrades the citing fact's badge — never
auto-expires it**. A dependency removed leaves the fact invalidate-not-deleted when code
was its sole source.

**Done when:**
- [ ] A changed symbol downgrades rather than expiring — the human decides, not the parser
- [ ] Sole-source removal invalidates without deleting
- [ ] Re-verification is idempotent per repo run

**Verify.** `cd backend && python -m pytest tests/test_citation_reverifier.py -q`

#### T2.49 — `relation_embeddings` refresh job + writer

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T2.32, T0.13` · `Doc: 04 §5.3, 07 §4, 19 §6` · `Tag: target-new` · `Gate: G-C`

**What.** First writer to one of the two inert partition templates that had no named owner,
and the JobRegistry refresh arm doc 19 §6 lists.

**Done when:**
- [ ] The template loses its inert label and the schema inventory records this task as its
      first writer
- [ ] Refresh is Tier-C with its own cron, floor, and lock
- [ ] No cross-fingerprint comparison (invariant 2)

*terminal-by-design — nothing depends on this; it is a backstop, an activation, or a
leaf surface, not infrastructure another task consumes.*

**Verify.** `cd backend && python -m pytest tests/test_relation_embeddings.py -q`

#### T2.50 — Graph-arm activation measurement

`Model: Fable 5` · `Effort: high` · `Size: M` · `Depends: T2.32, T2.44` · `Doc: 07 §3, 17 §2` · `Tag: activation` · `Gate: standing`

**What.** Split out of T2.32 so the model that builds the snapshot does not also judge its
number (runbook §2). Measures `w_ppr`, dual-level, and community injection.
**Activation bar:** a retrieval-eval win with its twin — except community injection, which
is measured on **answer-quality/groundedness, not MRR**, because it augments context rather
than ranking (doc 17 §2).

**Done when:**
- [ ] Each arm measured separately, per slice, with the twin
- [ ] Community injection scored on the reasoning gold set, never on MRR
- [ ] Arms that do not clear stay at zero, and that outcome is recorded as a result

**Amendment (Tier-2, 2026-07-27, from the T0.06a adversarial review):**
- [ ] **State this arm's entity-linking semantics before reading any multi-hop verdict off
      the slice.** The retrieval gold's multi-hop bridges are not uniform: 6 of 14 live pairs
      bridge through one shared entity row (same `name` *and* `entity_type`), while 8 bridge
      through same-name nodes of **different** `entity_type` — disjoint under the domain
      model's `(name, entity_type)` identity, with no connecting relation, because Phase-4
      dedup is deliberately type-constrained. So this slice's achievable ceiling is **6/14
      under strict node-identity traversal and 14/14 if the arm links entities by name or
      name-embedding**. Which one applies is a property of the arm, not of the gold, and it
      is undecided: `backend/scripts/benchlib/retrieval/SLICES.md` records both ceilings and
      the per-pair `bridge_status` deliberately rather than resolving it. Reading an
      activation verdict off this slice without stating the semantics measures the gold's
      undocumented shape instead of the arm.

**Verify.** `cd backend && python scripts/benchlib/run_retrieval_eval.py --arm w_ppr,dual_level`

#### T2.51 — Promotion-metrics runner

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T2.06` · `Doc: 17 §5.1` · `Tag: target-new` · `Gate: G-C`

**What.** The SQL-over-`events` runner T2.40 invokes: promotion rate sliced by source-kind
diversity and by which N fired, plus the false-promotion audit. Built by Sonnet so the
Fable gate task only designs the bar and reads the number.

**Done when:**
- [ ] Every metric derives from the journal alone — no instrumentation side-tables
- [ ] Slices are reported separately; no aggregate replaces them
- [ ] A vacuous 0/0 is reported as under-powered, not as a pass

**Verify.** `cd backend && python scripts/benchlib/run_promotion_metrics.py`

#### T2.52 — Contradiction-shortlist miss-rate runner

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T2.57` · `Doc: 17 §5.2` · `Tag: target-new` · `Gate: standing`

**What.** Measures the recall of the **combined** candidate generator — same-endpoint
facts plus the `pg_trgm` shortlist — against contradiction-pair gold. Its number is the
bar T2.33 must exceed before the `triple_embeddings` writer ships at all.

**Done when:**
- [ ] Measures the combined generator, not the trigram half alone
- [ ] Miss rate reported against gold with the bar stated beforehand
- [ ] Result recorded whether or not it justifies T2.33

**Verify.** `cd backend && python scripts/benchlib/run_contradiction_missrate.py`

#### T2.53 — Register `topic_detection` on the schedule

`Model: Haiku 4.5` · `Effort: high` · `Size: S` · `Depends: T2.18, T2.08` · `Doc: 08 §5` · `Tag: target-new` · `Gate: G-C`

**What.** The feature row says each dream-family job has its own cron, floor, and ceiling;
`topic_detection` was built (T2.18) but never scheduled.

**Done when:** registered under the umbrella with cron, floor, and per-job lock; a manual
trigger while held returns 409.
**Verify.** `cd backend && python -m pytest tests/test_dream_jobs.py -q`

#### T2.54 — Label the entailment gold set

`Model: Fable 5` · `Effort: high` · `Size: L` · `Depends: T2.25` · `Doc: 17 §6` · `Tag: target-new` · `Gate: G-D`

**What.** Split from T2.25 so the compute half cannot stall on the human half. T2.25
harvests candidate claim/fact pairs; this task is the labelling itself, which is bounded by
your afternoon rather than by a machine.

**Done when:**
- [ ] Grounded and ungrounded sentences both represented, including hard near-misses
- [ ] Labelling rationale recorded, so a later contributor labels consistently
- [ ] Inter-label consistency spot-checked on a resample
- [ ] Gold committed as JSON on disk (invariant 1)

**Verify.** `cd backend && python -m pytest scripts/benchlib/tests/test_entailment_gold.py -q`

#### T2.55 — Grouping under the fact, and the no-triple-count rule

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.43` · `Doc: 07 §5` · `Tag: target-new` · `Gate: G-C`

**What.** Split from T2.43. Results group under the fact they support, so three memories
backing one fact render as **one** grouped result rather than three hits. Without this the
vault inflates its own apparent evidence — the reader sees three confirmations where the
system has one.

**Done when:**
- [ ] Three memories supporting one fact render as one grouped result, proven by test
- [ ] The group names its constituent evidence without counting it again
- [ ] Grouping survives fusion — it is not a presentation-layer patch

**Verify.** `cd backend && python -m pytest tests/test_result_grouping.py -q`

#### T2.56 — Cold-start behaviour and the output shapes

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T2.55` · `Doc: 07 §5` · `Tag: target-new` · `Gate: G-C`

**What.** Split from T2.43. Cold start returns **labelled candidates** rather than nothing —
an empty vault is not an empty answer — plus doc 07 §5's sectioned and fused output shapes.

**Done when:**
- [ ] A query against an empty vault returns labelled candidates, not zero rows
- [ ] Both output shapes implemented and selectable
- [ ] The label on a cold-start result states plainly that it is unverified

**Verify.** `cd backend && python -m pytest tests/test_cold_start.py -q`

#### T2.57 — Contradiction-pair gold set

`Model: Fable 5` · `Effort: high` · `Size: M` · `Depends: T2.04` · `Doc: 17 §5.2` · `Tag: target-new` · `Gate: standing`

**What.** T2.52 measures the candidate generator's recall "against contradiction-pair gold"
— which nothing built. This is that gold: labelled pairs that do and do not contradict, over
overlapping and non-overlapping validity windows.

**Done when:**
- [ ] Pairs cover same-endpoint and lexically-similar-but-unrelated cases
- [ ] Non-overlapping validity windows are represented as **non**-contradictions
- [ ] Echoes (one origin restating itself) are labelled as not-contradiction
- [ ] Gold is JSON on disk

**Verify.** `cd backend && python -m pytest scripts/benchlib/tests/test_contradiction_gold.py -q`

#### T2.58 — Converge Chat onto the one ranking path

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.43` · `Doc: 07 §9, 13 §4.1, invariant 17` · `Tag: rebuild` · `Gate: G-D`

**What.** `ChatService._search_memories` calls `vector_repo.search` **directly** —
semantic-only, no keyword arm, no RRF, no rank-fusion factor, no trace. Memories goes through
`HybridSearchService`. So a chat answer and the search surface can rank the same corpus
differently, and Chat's context panel has no trace or exclusion counts to render because
nothing computes them on that path. Found by T1.60's planning pass (2026-07-28) and confirmed
in code by the controller; doc 13 §4.1 was amended to describe the tree rather than the intent.

**Why it is here and not in E1.** Rewiring Chat's retrieval is fusion surgery on an
invariant-bearing path, and it belongs beside the four-layer composition (T2.43) that decides
what a composed result *is* — converging Chat onto today's fusion only to re-converge it after
T2.43 would be two rewrites. T1.60 correctly satisfied its own Done-when (per-row honesty
labels, which come from the row rather than from ranking) and escalated rather than building
this silently.

**This is the third ranking implementation, and the count is the point.** `rank_fusion.py` is
canonical; `code_query.py` declares its own `RRF_K = 60` beside it; `ChatService` has none.
A task that converges Chat and leaves `code_query`'s constant free to drift has closed one of
two doors.

**Done when:**
- [ ] Chat retrieval runs through the same service and the same fusion as Memories
- [ ] Chat's context panel renders the trace and exclusion counts it can now actually receive
- [ ] A test fails if a second RRF constant is declared outside `rank_fusion.py`
- [ ] The ranking a chat turn used and the ranking the search surface would give are
      **demonstrably the same** for one fixed query — asserted, not assumed

**Verify.** `cd backend && python -m pytest tests/test_chat_retrieval_parity.py -q`

#### T2.59 — Content retention on delete: decide the policy, then implement it

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.07` · `Doc: 04 §8.1, 08 §2.3, invariant 14` · `Tag: target-new` · `Gate: G-C`

**What.** **"Delete my memory" does not today remove that memory's content from the system.**
It survives in **two** stores, not one: `events` rows carry a 500-char
`payload.content_preview` (a `buffer_discarded` row outlives the memory it came from), and
`messages.context` persists a ~150-char snippet of every cited memory that nothing prunes on
delete. `events` is **append-only by design** — T1.06's three forbid-triggers — so this is not
a missing `DELETE`; it is a collision between two deliberate properties.

**The policy is the owner's call, not this task's.** Raised as a Tier-3 escalation by T1.29e
on 2026-07-27 and carried unowned through G-B; the G-B evidence run (T1.50, 2026-07-28)
cleared on the three measured probes and named this as a condition for the controller to
discharge, which is what opening this task does. **This task implements whichever policy the
owner states; it does not choose one.** The plausible answers are genuinely different systems:
redact the preview in place (breaks append-only), stop writing content into events at all
(loses triage value for poison rows), tombstone-and-exclude at read time (content still on
disk), or accept and document the retention (honest, and possibly correct for a
single-operator homelab).

**Done when:**
- [ ] The owner's stated policy is recorded verbatim in the task before any code is written
- [ ] Both stores are covered — a policy applied to `events` alone is a half-measure by the
      escalation's own finding
- [ ] Whatever the policy, the **user-visible claim matches the behaviour**: if content is
      retained after delete, the UI and the docs say so rather than implying erasure
- [ ] If append-only is preserved, the mechanism that satisfies the policy without violating
      it is stated and tested

**Verify.** `cd backend && python -m pytest tests/test_content_retention.py -q`

---

## Amendment log

| Date | Task | Tier | Change | Why |
|---|---|---|---|---|
| 2026-07-27 | T2.50 | 2 | Added a precondition: the arm's entity-linking semantics must be stated before any multi-hop activation verdict is read off the retrieval slice | T0.06a's adversarial review measured the ingested graph pair by pair and found the multi-hop bridges are not uniform. Six of the fourteen live pairs bridge through one shared entity row; eight bridge through same-name nodes of *different* `entity_type`, which are disjoint under the domain model's `(name, entity_type)` identity because Phase-4 dedup is type-constrained. The slice's achievable ceiling is therefore 6/14 under strict node-identity traversal and 14/14 under name or name-embedding linking. That is a property of the arm, not of the gold, so the gold records both ceilings and defers rather than guessing; without the semantics stated, an activation number measures the gold's undocumented shape rather than the arm |
| 2026-07-28 | T2.58 | 3 | **New task, opened from a Tier-3 doc/code conflict found by T1.60's planning pass and confirmed in code by the controller: Chat runs a THIRD retrieval implementation.** Doc 13 §4.1 asserted "Chat's reads ride the same one ranking path as Memories (doc 07 §9, invariant 17)". `ChatService._search_memories` calls `vector_repo.search` directly — semantic-only, no keyword arm, no RRF, no rank-fusion factor, no trace. Doc 13 §4.1 amended to describe the tree; the convergence is T2.58, placed in E2 beside T2.43. | Routed to E2 rather than E1 deliberately: converging Chat onto today's fusion only to re-converge it after the four-layer composition lands would be two rewrites of an invariant-bearing path. The escalation itself is the part worth recording — a Sonnet-tier planning lane hit retrieval-fusion surgery, recognised it as above its tier, and stopped instead of building it silently, which is runbook §2's escalate-on-discovery rule working in the direction it is hardest to follow. The count is also the finding: three ranking implementations now exist (`rank_fusion.py`, `code_query.py`'s own `RRF_K`, and Chat's none), so a task that fixes only one has closed one of two doors. |
| 2026-07-29 | T2.01 | 2 | **Done-when 2's "renders as such" is satisfied at the read-model level; the visual render transfers to T2.36.** T2.01's obligation is that a confirmed-but-expired fact is representable and that both axes are independently distinguishable on the read model | T2.36 (Facts tab) depends on T2.03, so no render surface can exist at T2.01 time — read literally, the box could not be checked by its own task. Recorded rather than left as a private interpretation: an unrecorded reinterpretation means the next agent auditing G-C evidence finds a box satisfied only under a reading nowhere in the plan. Raised as finding I4 by the Fable-tier plan review, 2026-07-29 |
| 2026-07-29 | T2.01, T2.07, T2.10 | 2 | **`compute_triple_key` embeds `project` VERBATIM — it is not canonicalised, while `subject_name` / `rel_type` / `object_name` are.** Decided while the table holds zero rows | `project` is case-sensitive exact-match text everywhere else: `memories.project` matches exactly in supersession gate 1, and T2.07's registry is a case-sensitive `name` PK. Doc 04 §8.3 says uuid5 over "canonicalised lowercase **names**" with project merely "embedded" — it never says the project is canonicalised. Canonicalising it would give projects `Foo` and `foo` — distinct registry rows with distinct memory scopes — one shared fact identity, so `ux_knowledge_triples_open` would reject `foo`'s insert while `Foo` holds the open belief: cross-project interference through a unique index, and corroboration merged across scopes. Changing this after T2.10 writes rows re-keys the table, so it had to be settled now. Raised as I3 by the whole-branch review |
| 2026-07-29 | T2.01, T2.10 | 1 | **`get_live` and `as_of` require `project`; `insert_open` still defaults it to `'default'`.** T2.10 must pass `project` explicitly when wiring the producer, or drop that default | E1's standing warning F7 (`E1-engine-core.md`) told whoever wired this layer to render the scope in the repository, not at the front door, so the reads were made scope-required (I2). The producer default was left because it mirrors `memories.project` and the column's own `server_default`. The sharp edge is key/column divergence: computing a key with project X while inserting without `project=X` mints a row findable only under the wrong scope, silently |
