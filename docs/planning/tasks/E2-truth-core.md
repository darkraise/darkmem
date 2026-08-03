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

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.04, T2.26, T2.41` · `Doc: 08 §5` · `Tag: target-new` · `Gate: G-C`

**BLOCKED as of 2026-07-31 — the judge is not qualified, and this is enforced in code.**
T2.26 shipped the judge and its bars but measured contradiction precision **0.8182
against a 0.95 bar**, so no qualification record was minted.
`VerificationJudge.judge()` — the only lawful consumer door — raises
`JudgeNotQualifiedError` unconditionally while that record is absent, so the Done-when
clause below is unsatisfiable in code rather than merely unproven. `Depends` gains
**T2.41**, the run that can actually mint the record, which is itself behind T2.54.

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

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T2.22, T2.13, T2.12` · `Doc: 08 §6` · `Tag: target-new` · `Gate: G-C`

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

**Where the material comes from, since Phase-3 drafts do not exist yet.** *(Amended
2026-07-31 — the two sources this paragraph originally named were verified
unavailable: `article_synthesis` is a `PlaceholderJobRunner` until T3.02, so there is
no manual non-shipping mode to run, and `knowledge_triples` has no producer until
`fact_lift` (T2.10), so no live L2 facts exist.)* The harvest is hand-authored:
claim/fact pairs over synthetic-but-realistic fact texts, and over
`benchlib/retrieval/corpus.json` entries used verbatim as premises with a
machine-checked anchor. Every pair records its actual provenance in a closed
vocabulary with declared counts; `synthesis-draft` and `l2-fact` are reserved
values pinned to zero until their producers land. Nothing produced this way ships
as an article — it exists to be labelled. Waiting for real drafts would deadlock
the gate, since drafts come from T3.02, which is behind the gate this task feeds.

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

#### T2.36a — The `badge` object and the facts read surface

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.03, T2.02` · `Doc: 12 §"the badge is a structured field", 13 §5.1` · `Tag: target-new` · `Gate: G-C`

**What.** Split from T2.36 on 2026-08-03, because T2.36's first Done-when — "badges
verbatim from the backend" — names a backend producer that does not exist. Nothing in
`backend/app` emits the string `"asserted by K distinct origins of kinds [X, Y], no known
contradiction, as of T"`; it appears only inside a docstring in
`verification_ladder.py`. Nor is there any read surface over `knowledge_triples` beyond
T2.22's review-queue list — `review_queue.py`'s own docstring says so. So the frontend
task was told to render verbatim a string with no producer, which is the fifth instance
of this epic's recurring shape: a constraint stated in prose and unsatisfiable in code.

This task builds the **producer** and the **door**: doc 12's `badge` object exactly as
that doc fixes it (including the `disputed` two-sided form and the `confirmed`
human-ratified suffix), and the fact list + fact detail read surface doc 13 §5.1
describes, with `fact_sources` grouped by `origin_key` so the count the badge claims is
auditable.

**Done when:**
- [ ] `badge` is emitted with every field doc 12 fixes, and `claim` is byte-exact against
      that doc's three forms — plain, `disputed`, `confirmed` — pinned by exact-string tests
- [ ] `origin_count` is `COUNT(DISTINCT origin_key)` and a row-count implementation fails a test
- [ ] The string never contains the words "true" or "verified"; a guard fails the build if it does
- [ ] Memory rows carry `badge: null` and `verification_status: null`, and `lifecycle` instead
- [ ] A fact list and a fact detail door exist, matching `api-rest-conventions.md`, serving
      the belief window (`valid_at` / `invalid_at` / `expired_at`), `applies_when`, and the
      sources grouped by `origin_key` with each source's kind

**Verify.** `cd backend && python -m pytest tests/test_fact_badge.py tests/test_facts_read_surface.py -q`

#### T2.36 — Facts tab — bi-temporal, multi-origin browsing

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T2.03, T2.36a` · `Doc: 13 §5.1, §5.3` · `Tag: target-new` · `Gate: G-C`

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

`Model: Fable 5` · `Effort: xhigh` · `Size: M` · `Depends: T2.26, T2.54` · `Doc: 20 §4, 17 §11` · `Tag: target-new` · `Gate: G-D`

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
- [ ] Disputed facts are **returned, never filtered out**, labelled with everything the
      fact row itself carries — the non-negotiable half, proven by a test that fails if a
      filter is added
- [ ] The **counterpart** half of "both sides" is not re-derived at this surface; it lands
      with T2.64 and is served by T2.43 (2026-08-02 amendment)

**Verify.** `cd backend && python -m pytest tests/test_facts_channel.py -q`

#### T2.43 — Four-layer composition, labelling, and grouping

`Model: Opus 5` · `Effort: high` · `Size: L` · `Depends: T2.42, T2.64` · `Doc: 07 §5` · `Tag: target-new` · `Gate: G-C`

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

`Model: Fable 5` · `Effort: high` · `Size: L` · `Depends: T2.25, T2.10` · `Doc: 17 §6, §11` · `Tag: target-new` · `Gate: G-D`

**What.** Split from T2.25 so the compute half cannot stall on the human half. T2.25
harvests candidate claim/fact pairs; this task is the labelling itself, which is bounded by
your afternoon rather than by a machine.

**Composition is gate-binding, not just volume** (added 2026-07-31 from T2.25's review).
Doc 17 §11's stance is explicit: the qualification gold is *"seeded from real synthesis
drafts and real block answers once Layer 2 is live — **synthetic-only entailment gold is
rejected as unrepresentative**; ≥ 200 pairs per task variant before the corresponding gate
can open"*. T2.25's 41 pairs are 100% hand-authored, correctly and honestly so — neither
named source existed at its branch point — and its two reserved provenances
(`synthesis-draft`, `l2-fact`) sit test-pinned at zero waiting for this task. **So G-D
cannot open on T2.25's composition however far it is grown.** Volume is necessary and not
sufficient.

**This is not the deadlock T2.25's text feared, for the claim/fact variant.** §11 says
"once **Layer 2** is live", and Layer 2 is verified facts — `knowledge_triples`, whose
producer is `fact_lift` (**T2.10**, this epic), not the Phase-3 article synthesiser. So
real premises for the `claim-fact` variant become available inside E2, which is why T2.10
is now a dependency. The `synthesis-draft` provenance and the block-answer variant stay
behind T3.02 and doc 16's horizon respectively; they gate those variants' own bars, not
this one.

**Done when:**
- [ ] Grounded and ungrounded sentences both represented, including hard near-misses
- [ ] Labelling rationale recorded, so a later contributor labels consistently
- [ ] Inter-label consistency spot-checked on a resample
- [ ] Gold committed as JSON on disk (invariant 1)
- [ ] The `claim-fact` variant reaches ≥ 200 pairs **and** carries real `l2-fact` premises
      rather than hand-authored ones — the §11 composition rule, not volume alone

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

#### T2.60 — The supersession-signal promotion blocker

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.03, T2.02, T1.36` · `Doc: 08 §4.1 (as amended), spec §2.1` · `Tag: target-new` · `Gate: G-C`

**What.** Spec §2.1's promotion condition 4 has two halves. The contradiction half is
T2.04's. This task owns the other: **a fact does not promote while a newer
REPLACES-family / supersession signal stands over its live memory sources.** It is a
deterministic **hold** — no LLM, no model call. It never writes `disputed`, and it never
demotes an already-`corroborated` fact; it only withholds a promotion that would otherwise
fire. Opened by the Tier-3 ruling at
`.superpowers/sdd/rulings/2026-07-29-t2.03-supersession-blocker.md`, which found doc 08
§4.1 had dropped the condition by drift rather than decision.

**Done when:**
- [ ] The predicate is deterministic — no LLM, no model call on the promotion path
- [ ] A fact that meets its N-origin bar but carries a superseded live source does **not**
      promote, proven by test
- [ ] The signal writes no `disputed` status and causes no demotion — it holds only
- [ ] The signal is journaled in the decision evidence so G-C can count blocked promotions

**Verify.** `cd backend && python -m pytest tests/test_supersession_blocker.py -q`

#### T2.61 — The TTL sweep must withdraw provenance too

`Model: Opus 5` · `Effort: high` · `Size: S` · `Depends: T2.47` · `Doc: 05 §8.4, 08 §3.3` · `Tag: target-new` · `Gate: G-C`

**What.** T2.47 landed the provenance-withdrawal hook on `delete_by_memory_id`, which
covers re-extraction and both interactive delete doors (`delete_memory` and
`bulk_delete_memories` route through `pipeline.delete_memory`). It does **not** cover the
`expired_memory_cleanup` job, which deletes TTL-expired memories with a raw
`DELETE FROM memories WHERE id = ANY(...)` and never routes through the repository method
the hook hangs off. `fact_sources.source_ref` is a **soft** reference with no FK, so
nothing cascades: a TTL-expired memory strands its `fact_sources` rows, and a fact whose
only source was that memory keeps serving as `corroborated` forever with `expired_at`
NULL — the exact "lingering as corroborated" failure doc 08 §3.3's inline expiry exists to
prevent, reached by the one delete path that skips it.

**A second stranding path, found by T2.47's review.** `ProcessingPipeline.delete_memory`
swallows every exception with a log line, so a withdrawal that *fails* on the interactive
path strands its rows just as silently as the TTL sweep's bypass does. Both directions
produce the same end state — a fact solely sourced by a vanished memory keeps serving as
`corroborated` forever, with no `sources_changed` ever revisiting it — which is the
**overcounting** direction the truth core categorically forbids. A backstop that heals
orphaned provenance covers both; routing the TTL sweep alone covers only one.

**Latent today, live the moment T2.10 lands.** `fact_sources` has no producer until
`fact_lift`, so the gap writes no bad data yet. That is why it is a task rather than a
bug: it must close before the first producer ships. **G-C may not claim the withdraw path
is closed until this lands** — T2.47 closes the removal half on the paths that reach it,
not the paths that skip it.

**T2.34 does not own this.** Its text explicitly reuses T1.37's sweep *unchanged*, and it
governs the fact side's pre-closed belief window, not memory-deletion provenance.

**Done when:**
- [ ] The TTL sweep withdraws provenance and expires sole-sourced facts on the same terms
      as every other delete path, proven by a test that fails if the sweep regresses to a
      bare SQL delete
- [ ] Orphaned `fact_sources` rows are reaped whatever stranded them, so a swallowed
      failure on the interactive path heals too — not only the TTL bypass
- [ ] The demote-before-delete ordering T1.37 owns is preserved — the sweep must still
      demote `superseded_by` dependents before deleting, or `chk_superseded_has_pointer`
      aborts the batch
- [ ] One shared withdrawal path, not a second copy of T2.47's logic

**Verify.** `cd backend && python -m pytest tests/test_expired_memory_cleanup.py tests/test_sources_changed_emit.py -q`

#### T2.62 — `review_state` must open on the veto and clear on recovery

`Model: Opus 5` · `Effort: high` · `Size: S` · `Depends: T2.04` · `Doc: 08 §4.3, §6` · `Tag: target-new` · `Gate: G-C`

**What.** Doc 08 §4.3's flowchart node reads "set `disputed`, `review_state` open", and §6
defines the review queue as `WHERE review_state='open'`. `ix_knowledge_triples_review` has
been in the baseline since T0.12b waiting for a writer. **There is none.** The only
mention of `review_state` in `backend/app` outside the model is an insert parameter
defaulting to `None` that no caller passes. So a fact the veto disputes never reaches the
review queue, and nothing clears the flag when the contradiction resolves.

**Why its own task and not T2.22's.** The open and clear writes belong beside the sole
journaller, inside `recompute_fact`'s `FOR UPDATE` window — ladder-side code. T2.22 is a
queue-*surface* task, and a surface-layer writer would open a window in which a fact is
`disputed` but unqueued. `review_state` is also shared with T2.46's `under-sourced` label
and §6's human-clear, so the clear semantics span three tasks' outputs — the same
cross-cutting shape that got T2.60 minted.

**Done when:**
- [ ] The veto opens `review_state` in the same transaction and under the same lock as the
      status write, so `disputed`-but-unqueued is not a reachable state
- [ ] Recovery clears it, proven by test
- [ ] The clear does not stomp a value T2.46's `under-sourced` label or a human owns — the
      three writers' precedence is stated and tested, not left to write order
- [ ] `chk_superseded_has_pointer` and the sole-journaller property both still hold

**Verify.** `cd backend && python -m pytest tests/test_review_state_transitions.py -q`

#### T2.63 — Human adjudication verdicts must reach the journal

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.22, T2.62` · `Doc: 08 §6, 17 §5.1` · `Tag: target-new` · `Gate: G-C`

**What.** Doc 17 §5.1 defines the false-promotion audit as "the count of corroborated
facts later disputed **or human-rejected**". The disputed half is computable — it is a
self-join over `verified` events. **The human-rejected half has no source at all**, and
after T2.62 it cannot acquire one by accident.

T2.62 settled `review_state` as a pure queue-membership marker: the only writable value
is `'open'`, the repository refuses any other literal, and human resolution *clears* the
column to NULL. Doc 08 §6 names no "rejected" value and should not gain one — the column
is derived, and a human verdict is an event, not a state. So the audit's second half is
**structurally unreachable** from anything the system currently records: T2.51's runner
reads 0 forever, and reads it silently, because its `KNOWN_REVIEW_STATES` tripwire can
never fire against a vocabulary that is correct.

The fix is journalling, not a column. When a human ratifies, re-grounds, edits or rejects
a queued fact, that verdict must land in `events` with enough payload for the audit to
count it — the same discipline T2.06 applied to machine transitions, which is exactly why
G-C's other metrics are computable by SQL over one table.

**Why its own task.** The verdict is written by T2.22's queue surface and by T2.05's
ratification path, and read by T2.51's runner — three owners, none of whom can define the
vocabulary alone. `EVENT_TYPES` is a closed vocabulary and widening it is taxonomy-first
(land the value before its emitter ships), so one task must own the value, the payload
shape, and both emitters.

**Done when:**
- [ ] A human verdict on a queued fact journals to `events` under a value landed in
      `EVENT_TYPES` **before** any emitter references it
- [ ] The payload carries what doc 17 §5.1's audit needs — which fact, which verdict,
      and the `verification_status` it held — without a join back to `knowledge_triples`
- [ ] `review_state` gains no new value; T2.62's derivation and its refusal guard are
      untouched, proven by test
- [ ] T2.51's human-rejected arm reads the journal and its tripwire can actually fire,
      proven by a seeded rejection
- [ ] The sole-journaller property for *verification transitions* still holds — a human
      verdict is a distinct event type, not a second writer of `verified`

**Verify.** `cd backend && python -m pytest tests/test_human_adjudication_events.py -q`

#### T2.64 — The contradiction's counterpart must ride the journal payload

`Model: Opus 5` · `Effort: high` · `Size: S` · `Depends: T2.04, T2.06` · `Doc: 08 §6, §4.2` · `Tag: target-new` · `Gate: G-C`

**What.** Doc 08 §6 requires disputed knowledge be "served **labelled with both sides**",
and §4.2's veto is what knows both sides. It does not record them: `ContradictionFinding`
is computed on the fly inside the adjudication and discarded once the verdict is taken.
So the review queue (T2.22) can say *this fact is disputed, with N origins of these
kinds* but cannot say *disputed by fact X asserting Y* — the half a human actually needs
to adjudicate.

T2.22 could not close this and correctly declined to: the deterministic scan is guarded by
a tree-wide source scan that fails the build on any caller outside the ladder, so a
surface-layer re-derivation is forbidden by construction, and rightly.

**The closure is cheap and needs no schema change.** The ladder already journals T2.06's
enriched `verified` payload at the exact point where the finding is still in scope. Adding
the counterpart fact id (and the asserted object) to that jsonb payload costs one field;
T2.22's evidence attach then surfaces it with no query change at all.

**Done when:**
- [ ] A `disputed` transition's `verified` payload names the counterpart fact(s)
- [ ] The `verified` **event population is unchanged** — no new rows, no rows lost; only
      the payload of rows that already existed gains a field
- [ ] T2.51's payload-vocabulary guard is widened in the same commit, or the new key
      makes every promotion-metrics run raise `UnrecognisedPayloadError`
- [ ] `recompute_fact` remains the sole journaller; the scan gains no second caller
- [ ] A queued fact's counterpart is readable from the journal alone, proven by test

**Verify.** `cd backend && python -m pytest tests/test_ladder_journaling.py tests/test_contradiction_veto.py -q

#### T2.65 — Fact-level retrieval heat has no counter

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T2.42, T2.29` · `Doc: 08 §6, 07 §3` · `Tag: target-new` · `Gate: G-C`

**What.** Doc 08 §6 ranks the review queue by retrieval frequency, but the only counter in
the tree is `memory_access_stats` (T2.29), keyed by `memory_id` and fed from the memory
hybrid. T2.24's landed consequence ranking reaches it through `fact_sources.source_ref`
cast to a memory id — an explicit, documented **proxy**, correct only while facts are read
exclusively through the memories that source them.

T2.42 broke that premise: the facts channel serves `knowledge_triples` rows directly and
records nothing. So a frequently-served fact accrues no heat anywhere, and §6's
consequence ranking quietly degrades toward its salience arm as the facts channel takes
traffic. The degradation is silent — no error, no empty result, just a ranking that
weights the wrong thing.

**This task is a decision before it is an implementation.** Either a fact-keyed analogue of
T2.29's substrate is fed from the serving path, or the proxy is declared permanent with
its error bound stated. Do not build the counter before settling which, and record the
answer where §6's reader sees it rather than only in a report.

**Done when:**
- [ ] The decision is made and argued: fact-keyed counter, or the proxy made permanent
- [ ] If a counter: the serving path feeds it, and the recording is off the ranking's hot
      path in the way `_record_access` already is
- [ ] If the proxy stands: its error bound is stated where a ranking reader sees it, and a
      test pins the proxy's behaviour so it cannot silently drift
- [ ] Either way, `review_ranking`'s comment stops describing a premise that no longer holds

**Verify.** `cd backend && python -m pytest tests/test_review_ranking.py tests/test_access_stats.py -q`

#### T2.66 — A one-sided database failure must degrade, not take the channel down

`Model: Opus 5` · `Effort: high` · `Size: S` · `Depends: T2.42` · `Doc: 07 §2, invariant 14` · `Tag: rebuild` · `Gate: standing`

**What.** Doc 07 §2's channel contract is that a one-sided failure degrades to the other
modality while a both-sided failure raises, so an empty list is never confused with a
genuine no-match. Both the memory hybrid (`hybrid_search.py`) and the facts channel
(`facts_channel.py`) run their two arms on **one shared session**, so a database-level
error in the first arm aborts the transaction and the second arm's *valid* SQL then fails
on the aborted transaction. The channel raises where the contract promises degraded
service, naming an arm that never independently failed.

**Both channels' contract tests pass anyway**, because they simulate failure by
monkeypatching the query *builder* — a pre-SQL failure, which leaves the transaction
usable. That is a guard reading stronger than it is, and it is the template's defect
rather than either channel's invention, which is why this is one task over both rather
than a fix in one.

**Fix shape:** a SAVEPOINT per arm (`begin_nested()`), so an arm's failure rolls back only
that arm. Land it in both channels together — diverging the idiom is how the two ranking
paths already drifted.

**Done when:**
- [ ] A genuine database-level failure in one arm degrades to the other, in **both**
      channels, proven by a test that breaks the SQL rather than the builder
- [ ] A both-sided failure still raises rather than returning an empty list
- [ ] The existing builder-level tests are kept, not replaced — they pin a different path
- [ ] Removing either savepoint fails a test

**Verify.** `cd backend && python -m pytest tests/test_facts_channel.py tests/test_hybrid_search.py -q`

#### T2.67 — Invariant 15's scan is bypassed by ordinary import formatting

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T2.18` · `Doc: 08 §5, invariant 15` · `Tag: rebuild` · `Gate: G-C`

**What.** Invariant 15 says none of the six Tier-C dream jobs may be reached from capture
or retrieval, and a source scan over `backend/app` is what enforces it. That scan is
line-based, so **a parenthesised multi-line import defeats it** — the exact form a
formatter produces. Measured, not reasoned: appending

```python
from app.services import (
    fact_lift,
)
```

to the real `app/services/pipeline.py` leaves `test_no_app_code_reaches_a_family_job`
**passing**, while the single-line form fails it. A Tier-A module reaching a shipped
family job's body, undetected.

**The second net does not cover it, and the reason is structural.** The family scan has two
arms: a module-import arm and a quoted-job-key arm. Quoting a key is how you ask the
*registry* for a job; reaching a job's *body* goes through its module and needs no key at
all. So the two arms double-cover the registry route and leave the module route open.

Exposure is live and growing: `fact_lift` and `verification_recompute` have shipped bodies
today, and four more family members land in this epic.

T2.18 rebuilt **its own** detector scan on an AST walk and proved the rebuild a strict
superset of the regex — every case the regex caught plus eight it missed, including
wrapped imports, split-string `import_module`, name-bound `importlib`, `__import__`,
`sys.modules`, `getattr` with a literal, a full-literal f-string, and a depth-2 relative
import. It deliberately did **not** widen the family scan from a topics commit: a
cross-cutting invariant change buried in a feature commit is not reviewable as one.

**Design notes from the re-review, which reproduced the measurement independently:**

- Lift T2.18's AST helper into a shared test utility, **parameterised on the forbidden
  module set** — the family scan derives its set from the umbrella's imports, so the set
  cannot be hard-coded.
- Rework `_ALLOWED_DREAM_JOB_LINES` from line-text allowlists into **node-addressable
  exemptions**; a line-text allowlist re-introduces the bug it is meant to except.
- Close T2.18's own two residuals in the same stroke: an `ast.Attribute` net for reach
  through a parent-package import (`from app import services` then
  `services.<module>.<fn>()` — inert today only because nothing imports the module, and
  live the moment T2.53's umbrella does), and a docstring sentence bounding the
  computed-string forms (`"a" + "b"`, f-string interpolation) that no literal-level static
  scan can close in general.

**Done when:**
- [ ] One scanner serves both vocabularies; neither scan is line-based
- [ ] The wrapped-import and split-string bypasses **fail the build**, proven by injecting
      each into real code under `app/` rather than into a fixture string
- [ ] The attribute-reach route is caught
- [ ] The allowlist is node-addressable, and a test proves an exempted node's *neighbour*
      is still flagged
- [ ] The computed-string bound is documented where the scan's reader sees it, not only in
      a report
- [ ] The rebuilt family scan is a strict superset of today's: every case the current scan
      catches still fails the build

**Verify.** `cd backend && python -m pytest tests/test_dream_jobs.py tests/test_communities.py -q`

#### T2.68 — Two read paths key on a fingerprint that can be a sentinel

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: —` · `Doc: 04 §5, invariant 2` · `Tag: rebuild` · `Gate: standing`

**What.** `LLMOrchestrator.llm_fingerprint()` returns `f"{model}|{cfg.dimensions or 0}"`.
When the embedding purpose's `dimensions` is unset — **a legal, documented
configuration**, and the function's own docstring says so — it yields a `|0`
sentinel, and the true-dimension fingerprint is only registered on demand by a real
embed call.

Two read paths call it and then read an embedding partition **with no embed anywhere
on the path**:

| Site | Reads |
|---|---|
| `app/api/routes/vectors.py:42` | `get_all_vectors` → `memory_embeddings__<slug>` |
| `app/services/graph.py:52` | `get_louvain_clustered_vectors` → the same, via `vector.py` |

Boot registers the sentinel partition (`main.py:120`), so under that configuration both
surfaces **succeed and return empty, forever, with no error and no symptom**. Retrieval
is unaffected: `hybrid_search` takes its fingerprint from `embed()`'s return value,
measured as `f"{model}|{len(vec)}"` from an actual vector, so it structurally cannot hit
the sentinel.

**This is the silent-inert failure class, live in the tree.** The same trap was caught in
T2.12's plan review before it could ship into the dream job; these two are the instances
that already exist and that no task owns.

**Done when:**
- [ ] Neither surface can read the sentinel partition and report success — either the
      fingerprint is resolved the way retrieval resolves it, or a `|0` result is a loud
      refusal naming the unset `dimensions` config
- [ ] The failure is distinguishable from a genuine empty result at the surface, not only
      in a log
- [ ] A test fails if either site reverts to the bare `llm_fingerprint()` read
- [ ] The docstring on `llm_fingerprint()` records which callers may use it and which may
      not, since its current text explains the sentinel without saying who is entitled to
      receive one

**Verify.** `cd backend && python -m pytest tests/test_vectors_route.py tests/test_graph.py -q`

#### T2.69 — The reranker cannot say "asked and failed", and does not say what text it needs

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T2.43` · `Doc: 07 §3, invariant 14` · `Gate: standing`

**What.** Two defects in `RerankerService`, found from opposite directions and sharing one
cause: the service takes documents on trust and returns numbers that cannot be
distinguished from each other.

**It returns `0.0` for a per-document failure.** Inside one window, *asked and failed* is
therefore indistinguishable from *rated worst*. T2.43's all-zero guard catches a **total**
outage — every document zero means no usable signal, fall back to the deterministic order
and report `reranked=False` — but a single failed document inside an otherwise healthy
window silently becomes the lowest-ranked row.

**And it never declares what field carries a document's text.** It resolves via a
fall-through chain — `content` → `payload.content` → `chunk_content`. A `knowledge_triples`
row's text lives under `fact`, so **every L2 fact reaching the reranker was scored against
an empty string**, and because the model returns a real number for an empty document,
neither the all-zero guard nor the terminal band could see it. T2.43 fixed this at its own
construction site with a closed dispatch that raises on an undeclared layer; the producer
still has no contract, so the next consumer inherits the same trap.

**The shared cause is worth naming**: a `0.0` that means three things, and a text lookup
that guesses. Both are honest-output defects (invariant 14) rather than ranking defects.

**Done when:**
- [ ] A per-document failure is distinguishable from a genuine low score at the consumer —
      a sentinel, not `0.0` — and a consumer can tell how many documents in a window were
      not really scored
- [ ] The service declares the text contract it requires, rather than guessing through a
      fall-through chain; a document it cannot resolve text for is a loud failure, never a
      scored row
- [ ] T2.43's construction-site dispatch still passes unchanged, so the fix is at the
      producer rather than a second copy
- [ ] Removing the sentinel fails a test; feeding a document with no resolvable text fails
      a test

**Verify.** `cd backend && python -m pytest tests/test_reranker.py tests/test_layer_composition.py -q`

#### T2.70 — Grouping and the result cap drop a row nobody counts

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.55` · `Doc: 07 §5, §8, invariant 14` · `Tag: rebuild` · `Gate: G-C`

**What.** Found by T2.55's Fable review, 2026-08-03, on a driver over the real `search()`
path rather than by reading. Grouping is composition's last pass and the result cap slices
**after** it, so a memory nested under a fact that falls past the cut disappears with the
fact. Measured at `limit=4`: ungrouped serves `[F1, M1, F2, M2]`, grouped serves
`[F1, M1, F2, F3]` — `M2` and `F4` vanish together, uncounted, and `F3` is promoted into
the space they left.

**This is not T2.55's defect and T2.55 is not reopened.** The behaviour is the correct
reading of the ruling T2.55 was given (a group ranks as its fact), and the reviewer
confirmed it is not an invariant-14 violation as the contract *operationalises* that
invariant: doc 07 §8's `excluded` vocabulary counts context conflicts and project scope,
and has never counted the limit tail. The gap is the **plan's**. Doc 07 §5's own predicate
is "a memory covered by a **returned** cited fact", and in this corner the fact is not
returned — which is also exactly the rationale for T2.55's R4 (a memory whose fact is
absent from the result set stays a top-level row, because nesting it under an absent fact
would remove it from view entirely). The cut makes a fact absent *after* nesting decided
it was present.

**The resolution, ruled by the controller 2026-08-03:** scope nesting to the facts that
survive the cut. That is the reading consistent with doc 07 §5, §8, R2 and R4 together.
It is a separate task rather than a reviewer's patch because it needs a **window fixpoint
decision**: un-nesting a memory returns it to the top-level ordering, which can change
which rows survive the cut, which can change what nests. Choose and argue the fixpoint —
iterate to stability, over-fetch a bounded window before grouping, or nest only within a
prefix known to survive — rather than picking one silently.

**Done when:**
- [ ] A memory that would rank above the cut on its own is never removed by the cut solely
      because the fact it nested under fell below it
- [ ] The fixpoint rule is stated in the module and pinned by a test whose failure names it
- [ ] The chosen rule terminates on an adversarial input, proven rather than assumed
- [ ] T2.55's three Done-when clauses still hold, its tests unchanged
- [ ] If any row is still dropped by design, it is **counted** and surfaced, per invariant 14

**Verify.** `cd backend && python -m pytest tests/test_result_grouping.py tests/test_grouping_cut.py -q`

## Amendment log

| Date | Task | Tier | Change | Why |
|---|---|---|---|---|
| 2026-08-03 | T2.55, T2.70 | 2 | **T2.70 minted: grouping and the result cap drop a row nobody counts, and the controller rules the resolution is to scope nesting to the facts that survive the cut.** T2.55's reviewer built a driver on the real `search()` path and measured it: at `limit=4`, ungrouped serves `[F1, M1, F2, M2]` and grouped serves `[F1, M1, F2, F3]` — the nested memory leaves with its fact, uncounted, and an unrelated row is promoted. Ratified by ruling rather than patched in-lane: the behaviour is the correct reading of T2.55's R2, and it is **not** an invariant-14 violation as doc 07 §8 operationalises that invariant, whose `excluded` vocabulary has never counted the limit tail. But it sits outside doc 07 §5's own warrant — §5 says "a memory covered by a **returned** cited fact" — and the cut makes the fact un-returned *after* nesting decided it was returned | The gap is the plan's, not the implementer's: R2 and R4 were both written by the controller and they meet in a corner neither anticipated, since R4 already says a memory whose fact is absent stays top-level and the cut is a second way for a fact to be absent. Routed to its own task because the fix needs a **window fixpoint** decision — un-nesting returns a memory to the ordering, which changes what survives the cut, which changes what nests — and a reviewer patching that inside a scoped fix round would be choosing a fixpoint silently. Recorded before G-C at the reviewer's recommendation, since G-C's claims are about served output. Note the shape: the review found this by *running the real path*, not by reading the diff, which is the second time this round that an executable check beat an inspection |
| 2026-08-03 | T2.36, T2.36a | 2 | **T2.36 split; `T2.36a` minted to own doc 12's `badge` object and the facts read surface, and T2.36 gains `Depends: T2.36a`.** T2.36's first Done-when is "badges verbatim from the backend", and there is no backend producer: `rg "no known contradiction" backend/app` returns nothing, and the canonical sentence exists only inside `verification_ladder.py`'s `compute_confidence` docstring. There is also no read surface over `knowledge_triples` for a browsing tab to call — `review_queue.py`'s docstring states it in as many words ("no REST GET beyond this module's own queue list"). The Facts tab is meanwhile a demo-data surface (`useDemoFacts`), so nothing would have failed loudly; a lane could have satisfied "verbatim" by formatting the string client-side, which is precisely what invariant 14 forbids and what the Done-when's word *verbatim* exists to prevent | Caught by the controller at brief-writing time, reading the tree rather than the task text. This is the **fifth** instance of this epic's recurring shape — a constraint recorded in prose and absent from the code and the graph — and the second in which the missing producer would have been silently substituted by the consumer. Split rather than widened because the two halves are different tiers and different failure modes: the badge is an honesty contract whose string doc 12 fixes byte-exactly and whose `origin_count` must be `COUNT(DISTINCT origin_key)` (Opus, silent-correctness-drift), while the tab is a UI surface on an existing component (Sonnet). Widening T2.36 in place would have run it at the lower tier and pushed a Size-M task to L without the reviewed step-level plan runbook §3 requires. Note the 2026-07-29 amendment already treats the badge as T2.36's — "three later tasks read this number: T2.06's journal evidence, **T2.36's badge**, and the review queue's consequence ranking" — so the ownership is not new, only its unbuilt state |
| 2026-08-03 | T2.43, T2.13, T2.58, T2.55 | 1 | **Five deferred minors recorded from the two final re-reviews, each found after the named findings were closed — the point at which a suite is most trusted and least probed.** From T2.43: (a) the F3 guard pinning that channel weights are order-inert **has a blind spot** — inserting `-weighted_score` as a tie-break *after* band and tier passes all 46 tests, because no fixture holds an equal-tier cross-channel pair, so the guard catches the realistic mutation and not the subtle one; (b) the empty-text rerank warning is reachable but unasserted, and a row whose declared text field is empty is still scored against an empty document, warned only; (c) the article title-fallback in `RERANK_TEXT_FIELDS` is untested, its producer being T3.02's; (d) **plan §2.3 still names `with_trace` in the seam signature** though the parameter was deliberately not built, so **T2.58's brief must state the flagless seam** or §2.3 be amended by the corpus owner; (e) the `limit` test pins the length of the cut, not that the cut keeps the head of the total order. From T2.13: (f) in the combined `action` + `event_ids` form the stray-id check computes membership *after* the action filter, so an in-cycle id of another kind is refused with a message saying it is not in the cycle — the refusal is right, only the message misleads; (g) the new `unsupported_action` reason's **ladder position is untested** — hoisting the comparator check above all three older reasons survives all 88 tests, so the tuple order is pinned but no test proves an older reason wins at runtime | All seven were found by re-reviewers running mutations after the Important findings were closed. None is a defect in shipped behaviour: (a), (e) and (g) are guards narrower than they read, (b) and (c) are unasserted paths, (d) is a plan/code divergence with a named owner, and (f) is a message. Recorded rather than looped because each is either another task's input (d), a fixture gap whose producer does not exist yet (c), or a one-line hardening better bundled with the next change to its file — and because the alternative is that T2.55, T2.56 and T2.58 each pay to rediscover them. **Note (a) and (g) are the same shape**: a guard proven against the mutation its author imagined, blind to one they did not |
| 2026-08-02 | T2.69, T2.43 | 2 | **T2.69 minted: `RerankerService` returns `0.0` for a per-document failure, and never declares what field carries a document's text.** The first makes *asked and failed* indistinguishable from *rated worst* inside a window — T2.43's all-zero guard catches only a total outage. The second is worse and was found by T2.43's review: the service resolves text through a fall-through chain (`content` → `payload.content` → `chunk_content`), and a fact's text lives under `fact`, so **every L2 fact reaching the reranker was scored against an empty string** — silently, because the model returns a real number for an empty document, so neither the all-zero guard nor the terminal band could see it | Found from two directions in one round: the per-document conflation was reported by T2.43's implementer as O9 and confirmed unowned, and the empty-document defect by its reviewer, which probed the real service and captured `document_text=''` for the fact row beside the memory row's real content. T2.43 fixed its own construction site with a **closed dispatch that raises** on an undeclared layer rather than another fall-through — deliberately, since a fall-through is what produced the bug — but the producer still has no contract, so the next consumer inherits the same trap. Minted rather than folded into T2.43 because both halves live in `reranker.py`, which is not that task's file and which no task owned; scoped S because each half is small, and paired because they share one cause — a service that takes documents on trust and returns numbers that cannot be told apart |
| 2026-08-02 | T2.23, T2.13, T2.12 | 2 | **`T2.23` gains `Depends: T2.13, T2.12`.** Its third Done-when clause reads "bulk actions are undoable **through the T2.13 primitive**" — naming a task that has not started — while its `Depends` field read `T2.22` alone. So the task graph permitted claiming a task whose acceptance criterion is unsatisfiable in code, exactly as it did for T2.41 before T2.54 and for T2.11 before T2.26's qualification record. `T2.12` is added in the same edit because T2.12 is what actually produces the queue's rows: it writes `memory_relations.properties.dream.near_duplicate.hygiene_state`, and T2.12's re-review established that the marker survives re-derivation through **two** mechanisms — the pass-keyed `jsonb_set` and a Python-side carry-forward — **neither of which may be dropped alone**. A T2.23 built without reading that would re-open triaged items nightly | Caught by the controller at claim time, running runbook §1.5's entry check rather than trusting the `Depends` field, which is what that check exists for. This is the **fourth** instance of the same shape in this epic: a constraint recorded in a task's prose and absent from the edge the scheduler actually consults. Worth noting the pattern rather than only the instance — prose is where these constraints get written because that is where they are discovered, and nothing yet forces the edge to follow. Also note T2.23 is tagged *terminal-by-design*, which is now wrong in one direction: T2.12's re-review routed it a within-cycle ordering item (a duplicate pair outranking a subsume pair writes an edge against a memory retired later in the same cycle), so T2.23 has inherited work rather than being a pure leaf |
| 2026-08-02 | T2.12, T2.23, T2.13 | 1 | **Five deferred minors recorded from T2.12's scoped re-review, none a defect, each one a thing the next reader would otherwise rediscover.** (1) **The score-ordering mirror of I1**: when a duplicate pair outranks a subsume pair, Phase W applies the associate first, so an edge is written while both halves are active and the subsume retires its target later in the same cycle — reproduced. The write and journal are truthful at their own moment and the same end-state arises across cycles regardless, so no per-action guard can see it; ordering subsume actions before associate actions in Phase W would close the within-cycle instance in one line. **T2.23's domain.** (2) `memory_crossrefs.related_memory_id` is neither seeded nor counted by `_reference_counts`, so a repoint of that column alone passes 90/90 — narrow, since any realistic merge touches the covered primary endpoint, but a two-line extension closes it. (3) I3's after-side fallback has no teeth: with `verdict.tags is None`, journalling `memory.tags` instead of `locked_tags` passes — the code is correct but only the explicit-tags path is guarded. (4) The journal's `project` is still a Phase-R read in all three arms, and `MemoryUpdate.project` is wire-editable, so a project edit during Phase C files the event under the stale project — a mislabel, not a loss, and undo keys on `memory_id`. (5) `pair_arm_skipped_reason` is asserted by no test, as its predecessor was not — untested observability only | All five were found by the re-reviewer running mutations after the three Important findings were closed, which is when a suite is most likely to be trusted and least likely to be probed. Recorded rather than fixed because each is either another task's domain (1), narrower than any realistic failure (2), a correct-but-unguarded fallback (3, 5), or a labelling imprecision with no data loss (4). Logged at Tier 1 because none changes a task's scope or a dependency edge — but logged, because the alternative is that T2.13 and T2.23 each pay to rediscover them |
| 2026-08-02 | T2.68, T2.12, T2.16 | 2 | **T2.68 minted: two shipped read paths key an embedding-partition read on `llm_fingerprint()`, which returns a `|0` sentinel whenever the embedding purpose's `dimensions` is unset — a legal configuration.** `app/api/routes/vectors.py:42` and `app/services/graph.py:52` both call it and read `memory_embeddings__<slug>` with no embed anywhere on the path, and boot registers the sentinel partition, so under that config both surfaces succeed and return **empty forever, with no error and no symptom**. Retrieval is unaffected — `hybrid_search` takes its fingerprint from `embed()`'s return value, measured from an actual vector, so it cannot hit the sentinel | Found by T2.12's plan review as a hazard the *plan* had normalised (every seed skipping was classified 'not an error', which would have left the dream job permanently inert while reporting a green run), then sharpened by the implementer into the observation that no read path under `app/` calls `llm_fingerprint()` safely, then corrected again by the scoped re-reviewer: the implementer's claim that every existing caller 'either follows with a real embed or reads no partition' is **false for these two**, which read partitions directly. So the plan-level trap was caught before shipping and these two are the instances already in the tree. Minted rather than folded into T2.12 because neither site is the dream job's and fixing another surface from a consolidation task is the cross-cutting-change-in-a-feature-commit pattern this epic has now declined three times |
| 2026-08-02 | T2.67, T2.08, T2.53 | 2 | **T2.67 minted: invariant 15's source scan is bypassed by a parenthesised multi-line import — the form a formatter produces.** Measured, not reasoned: appending `from app.services import (\n    fact_lift,\n)` to the real `app/services/pipeline.py` leaves `test_no_app_code_reaches_a_family_job` passing, while the single-line form fails it. The scan's second arm does not help, and the reason is structural rather than incidental: quoting a job key is how you ask the *registry* for a job, whereas reaching a job's *body* goes through its module and needs no key, so the two arms double-cover the registry route and leave the module route open. Exposure is live and growing — `fact_lift` and `verification_recompute` have shipped bodies today and four more family members land in this epic | Found by T2.18 while closing the identical hole in its **own** detector scan, and reproduced independently by the scoped re-reviewer. T2.18 deliberately declined to widen the family scan from a topics commit, on the grounds that a cross-cutting invariant change buried in a feature commit is not reviewable as one — the same judgement T2.22 and T2.42 made about clause scope, and the right one. Its AST rebuild is the proven template: a strict superset of the regex, catching eight shapes the regex missed. Routed as its own task because the shared utility must be parameterised on a forbidden-module set the family scan derives from the umbrella's imports, and because `_ALLOWED_DREAM_JOB_LINES` must become node-addressable — a line-text allowlist re-introduces the very bug it excepts |
| 2026-08-02 | T2.65, T2.42, T2.29, T2.24 | 2 | **T2.65 minted: fact-level retrieval heat has no counter, and T2.42 broke the premise the existing proxy rests on.** Doc 08 §6 ranks the review queue by retrieval frequency; the only counter is `memory_access_stats` (T2.29), keyed by `memory_id` and fed from the memory hybrid, and T2.24's landed ranking reaches it through `fact_sources.source_ref` cast to a memory id — a documented proxy that is correct only while facts are read through the memories sourcing them. The facts channel now serves `knowledge_triples` rows directly and records nothing, so a frequently-served fact accrues heat nowhere and §6's consequence ranking degrades toward its salience arm as that channel takes traffic. Minted as a **decision before an implementation**: either a fact-keyed counter fed from the serving path, or the proxy declared permanent with its error bound stated where a ranking reader sees it | Flagged by T2.42's implementer as a controller-facing gap and independently confirmed by its Fable review, which swept T2.29, T2.31, T2.55, T2.56 and this log and found no task owning a fact-keyed counter. Minted rather than folded into T2.43 because the question is which substrate is correct, not where to call it from — and the degradation is silent, with no error and no empty result, only a ranking that weights the wrong thing, which is the failure mode this corpus is least able to notice after the fact |
| 2026-08-02 | T2.66, T2.42 | 2 | **T2.66 minted: the one-arm-degrade contract does not survive a database-level failure, in both channels.** Doc 07 §2 promises that a one-sided failure degrades to the other modality while a both-sided failure raises. Both the memory hybrid and the new facts channel run their arms on **one shared session**, so a database-level error in the first arm aborts the transaction and the second arm's valid SQL then fails on the aborted transaction — the channel raises where the contract promises degraded service, naming an arm that never independently failed. Both channels' contract tests pass regardless, because they simulate failure by monkeypatching the query *builder*, a pre-SQL failure that leaves the transaction usable. Fix shape is a SAVEPOINT per arm via `begin_nested()`, landed in both channels together | Proved empirically by T2.42's Fable reviewer, which broke only the keyword arm's SQL and watched the name arm's own statement error, rather than reading the contract test and believing it. Non-blocking for T2.42's merge on two grounds the reviewer named: the failure direction is loud rather than a silent empty list, and the shape is copied verbatim from `hybrid_search.py`, which the brief mandated as the template — so the defect is the template's and predates this task. Scoped over both channels deliberately: fixing one would diverge the idiom, which is exactly how the two ranking implementations already drifted |
| 2026-08-02 | T2.45, T2.12 | 2 | **The `supersede()` primitive refuses a successor that is not strictly newer than the candidate — `created_at >`, with an `id` tie-break for equal timestamps — mirroring `detect_supersessions`' rule 5, and the refusal short-circuits to no-change rather than falling through to guard 1's `deprecated` arm.** Doc 08 §3.4 states **no** ordering rule for the status bridge, so two spent memories can each be the sole live source of the triple that invalidated the other's fact, supersede each other, and both leave the active view — the mutual flip that rule 5 exists to block on the fast path, which the slow path inherited nothing from. `WHERE status='active'` does not help: it guards the candidate, and the second adjudication's candidate is still active. **This narrows the bridge beyond §3.4's letter without contradicting it**, since §3.4 states no ordering rule to override. It changes what T2.12 may hand the primitive, hence both tasks. Accepted cost, stated rather than smoothed away: a backfilled successor genuinely older than the candidate is declined and the candidate lingers as `active` until a later pass — the owner's own accepted failure mode for the neighbouring ruling | **The reason of record is blocker visibility, not symmetry.** `supersession_hold.py:179-194` recognises a supersession signal **only** when `sup.created_at > m.created_at OR (sup.created_at = m.created_at AND sup.id > m.id)`, and `:48-55` states that it checks rather than assumes this precisely *because* `memories.status` has a second future writer — this bridge — "whose guards are about *fact invalidation* and say nothing about timestamps". So a bridge-written pointer with an older superseder is **invisible to T2.60's blocker**, and a fact sourced by that superseded memory promotes to `corroborated` on evidence the store already knows was replaced: a correctness leak with no error and no symptom. T2.60 therefore already depends on this property and documents the dependency; the amendment makes the dependency true. Raised by T2.45's step-level plan (§3 D7), which declined to apply a doc-narrowing constraint unilaterally, and approved after the controller verified the `supersession_hold.py` claim against the tree independently. A strict total order was chosen over a 2-cycle refusal because it forbids cycles of every length, where `S.superseded_by == M` needs a recursive CTE to generalise and leaves 3-cycles reachable |
| 2026-08-02 | T2.45, T2.12, T2.13 | 3 | **RULED by the owner: doc 08 §3.4's guard 2 is absolute and is evaluated first — a memory still asserting any live fact never changes status, whatever guard 1 says.** §3.4 described the bridge twice and the two descriptions disagreed: the prose said a guard-2 failure means "the bridge does not apply at all ... deprecating it would drop a memory that still carries live knowledge out of the active view, which is exactly what guard 2 exists to prevent", while the flowchart directly below checked guard 1 first and routed its failure straight to `deprecated` without consulting guard 2. Where both fail, the flowchart produced precisely the outcome the prose forbids. **Doc 08 §3.4 amended in place** — prose and flowchart both — and the evaluation order is now stated explicitly: guard 2 answers *may the status change at all*, guard 1 answers *which change*. Full adjudication and the rejected alternative at `.superpowers/sdd/rulings/2026-08-02-t2.45-status-bridge-guard-order.md`. T2.45's Done-when is unchanged: the two guards still fail differently | Escalated by T2.45's step-level plan (§8 O1, `b4611ef`), which correctly refused to resolve a doc-internal contradiction from an implementation task and gated its own Step 3 on the ruling. The cell is ordinary rather than a corner case — any memory carrying more than one fact reaches it — so the flowchart's reading would have fired routinely. Ruled for guard 2 on reversibility: the ruled reading can only ever decline to act, and a later pass corrects it at no cost, whereas the rejected reading deprecates live knowledge out of the active view with nothing in a monotonic bridge to put it back. The both-fail cell now owes its own test; leaving it to fall out of the two single-guard cases is what let the contradiction survive review this long |
| 2026-08-02 | T2.42, T2.43, T2.64 | 2 | **"Labelled with both sides" is satisfied in two parts, not one: T2.42's Done-when splits, and `T2.43` gains `Depends: T2.64`.** T2.42 built the facts channel and confirmed against the tree that the counterpart half has no data source a retrieval query can read — the same finding T2.22 reported for the review queue, re-confirmed independently: `knowledge_triples` carries no counterpart column, `fact_sources` carries provenance rather than opposition, and the `verified` journal payload T2.06 enriched stops at `outcome`/`origin_count`/`required_n`/`gate_fired`/`source_kinds`/`contradiction_blocked`/`supersession_blocked`. So T2.42 ships the non-negotiable half — a disputed fact is returned, never filtered, labelled with what its own row carries and with `counterpart: None` naming T2.64 as owner rather than silently omitted — and T2.43, which is where a served row actually has to show both sides, now depends on T2.64 | The clause was a single Done-when checkbox on a task that provably cannot satisfy it, which makes the box either a lie or a licence to invent a re-derivation. T2.42 declined to invent one for the same structural reason T2.22 did: the deterministic scan's sole legitimate caller is the verification ladder, enforced by a tree-wide reference scan that fails the build on a second entry point, so a retrieval-surface re-derivation is forbidden by construction. Routed as a dependency edge on T2.43 rather than on T2.42 because T2.42 is a candidate *producer* — it has no served row to label — while T2.43 is the composition that serves one, so that is where the missing data is actually consumed. Note T2.64's own coupling to T2.51's payload-vocabulary guard still applies |
| 2026-07-31 | T2.41, T2.54 | 2 | **`T2.41` gains `Depends: T2.54`.** The composition amendment logged earlier today put doc 17 §11's "synthetic-only gold is rejected as unrepresentative; >= 200 pairs per variant before the gate can open" onto T2.54's Done-when, but never added the dependency **edge** to the evidence run that consumes it. So the task graph still permitted starting G-D's evidence run with T2.54 incomplete — the exact claim the amendment exists to block | Caught by T2.26's plan, which had to reason about when G-D may open and found the constraint stated in one place and unenforced in the graph. A constraint recorded on the producer but absent from the consumer's `Depends` is enforced only by whoever remembers to read it; the graph is what the runbook's entry-gate check actually consults |
| 2026-08-01 | T2.63, T2.62, T2.24, T2.05 | 2 | **A rejected fact never leaves the review queue while its contradiction stands, and no human verb in doc 08 §6 is reachable except rejection.** T2.63's rejection withdraws belief through `expire`, but expiry is **not** an opener input to T2.62's `REVIEW_OPENERS`, so `recompute_fact` re-derives `review_state='open'` forever on a disputed fact the human has already rejected. The one reachable human verb does not resolve the queue item it will most often be invoked from. Separately, §6 names ratify / re-ground / edit, and **none has a door**: ratify is T2.05's (unstarted, and the seam is `record_human_verdict`), while re-ground and edit have no named owner at all | Derived by T2.63's Fable reviewer, going beyond what the implementer reported. Not a T2.63 defect — the ladder's derivation was outside its bounds and it correctly declined to widen `REVIEW_OPENERS` from a queue-surface task, exactly as T2.22 declined the `review_state` writer. Needs a controller decision between two shapes: add an expiry (or verdict) predicate to the derivation so a rejected fact drops out, or handle it T2.24-side as a rank tier the way dispute-staleness decay already works. The withdrawal is at least **visible** meanwhile — the queue view selects `expired_at`. Recording the §6 door gap in the same row because both halves say the same thing: the human-facing surface is narrower than §6 describes |
| 2026-08-01 | T2.51 | 1 | **Deferred minor recorded: a query parameter, not an encoding, can still reach a forbidden database.** `postgresql+asyncpg://…/darkmem?database=darkmem_test` passes `_assert_not_forbidden` — which reads only the path-derived name — while SQLAlchemy's asyncpg dialect passes the query param through as the `database` connect kwarg; confirmed by `SELECT current_database()` returning `darkmem_test` | Found by T2.51's scoped re-reviewer while verifying the percent-encoding fix, which is itself sound (every encoding shape probed is refused before a connection opens). **Not a fix-round regression** — the pre-fix `urlsplit` check had the identical hole. The read-only GUC still prevents writes, so the exposure is the narrower hazard the original finding named: a runner measuring a database mid-`DROP SCHEMA` and emitting garbage into a gate report. Reachable only by deliberate construction, so recorded for a future pass rather than looped on |
| 2026-08-01 | T2.22, T2.51, harness | 2 | **`darkmem_bench` has no per-lane isolation, and concurrent lanes produce convincing false failures on it.** The runbook assigns `darkmem_test_N` per lane precisely so `conftest`'s `DROP SCHEMA` cannot cross lanes, but the bench database has one name and no numbered siblings. Observed twice in one round: T2.51's reviewer saw three retrieval-eval tests fail in a full run and pass in isolation, and T2.22's harness suite failed in a cluster across repeated runs — then passed **376/376 with zero failures** when re-run alone with no sibling active. Both were contention, neither was a code defect | Costly because the failure is indistinguishable from a regression: it lands in unrelated tests, it moves between runs, and it appears in exactly the suite `pytest -q` does not collect, so it surfaces only when someone runs the gate. It cost one lane several retry cycles and briefly read as a T2.22 regression before being isolated. **The mechanism already exists and is simply undocumented in the runbook: set `BENCH_DATABASE_URL` to a per-lane database** (T2.09's reviewer used `darkmem_bench_c3` and got exactly 376 after two red runs of 36 and 27 failures on the shared default). Runbook §8 should name it beside the `darkmem_test_N` rule, since an agent following §8 as written lands on the shared database every time | Costly because the failure is indistinguishable from a regression: it lands in unrelated tests, it moves between runs, and it appears in exactly the suite `pytest -q` does not collect, so it surfaces only when someone runs the gate. Hit three independent agents in one round — T2.51's reviewer, T2.22's implementer (which lost several retry cycles and briefly read as a T2.22 regression), and T2.09's reviewer, which was the one to identify the existing env-var fix |
| 2026-07-31 | T2.61, T2.02 | 1 | **Deferred minor recorded, not built: `FactSourceRepository.add_source` could reject or normalise a `memory`-kind `source_ref` failing `_CANONICAL_REF`.** T2.61's backstop spares any ref it cannot interpret, which makes its coverage explicitly conditional on producers minting through `memory_source_ref` — a future producer writing refs directly gets orphans that are never reaped, silently and by design. Guarding at the write door would convert that silent stranding into a loud write-time failure at the one door every current writer uses | Named by T2.61's scoped re-reviewer as a cheaper, stronger guard than anything the backstop can do from the read side, and explicitly scoped out of that round. The residual exposure predates the backstop and is now documented at the minting site, in the module docstring, and pinned executably by `test_the_minted_ref_matches_the_shape_the_backstop_trusts` — so this is a hardening opportunity rather than an open defect. Recorded here so it is not rediscovered from scratch |
| 2026-07-31 | T2.63, T2.51, T2.22, T2.62, T2.05 | 2 | **T2.63 minted: doc 17 §5.1's false-promotion audit has a second half — "or human-rejected" — with no possible source, and T2.62 closed the accidental route.** T2.62 settled `review_state` as a pure queue-membership marker: only `'open'` is writable, the repository refuses any other literal, and human resolution clears it to NULL. Doc 08 §6 names no "rejected" value and should not gain one. So T2.51's `human_rejected` arm reads 0 **silently and forever**, and its `KNOWN_REVIEW_STATES` tripwire can never fire, because the vocabulary it guards is correct. The fix is journalling a human verdict as an event, not adding a column | Found by T2.51's Fable review, which checked the arm against T2.62's *landed* design on the sibling branch rather than against the branch point. T2.51's own report had called the arm "a forward-compatible guard that fails loudly when a writer lands"; against T2.62 it does not. Minted rather than folded into T2.22 or T2.05 because the verdict is written by both of those and read by T2.51 — three owners, none of whom can define the vocabulary alone — and `EVENT_TYPES` is closed, so widening is taxonomy-first and needs one owner for the value, the payload and both emitters. T2.51 was directed to state the blindness in its rendered report meanwhile: a 0 nobody can see the reason for is worse than an absent number |
| 2026-07-31 | T2.64, T2.22, T2.04, T2.06 | 2 | **T2.64 minted: doc 08 §6's "served labelled with both sides" has no data source, and the closure needs no schema change.** `ContradictionFinding` is computed inside adjudication and discarded once the verdict is taken, so the review queue can say *disputed, N origins of these kinds* but not *disputed by fact X asserting Y* — the half a human needs to adjudicate. The ladder journals T2.06's enriched `verified` payload at the exact point the finding is still in scope, so adding the counterpart fact id costs one jsonb field and T2.22's evidence attach surfaces it with no query change | Raised by T2.22's implementer as a coordination item and sharpened by its Fable review, which identified the cheap closure the implementer had not named. T2.22 correctly declined to work around it: a tree-wide source scan fails the build on any caller of the deterministic scan outside the ladder, so a surface-layer re-derivation is forbidden by construction. Routed to a new task rather than left as a coordination note because notes decay and this one is a Done-when clause of a doc, not a nicety. Note the coupling to T2.51's payload-vocabulary guard — a new key raises `UnrecognisedPayloadError` unless widened in the same commit |
| 2026-07-31 | T2.40, T2.51, T2.06 | 2 | **T2.40 must be told two things about the number it reads: the promotion rate is per-transition where doc 17 §5.1 says per-fact, and the "diverse" slice is not the gate's diversity rule.** A fact exiting `candidate` more than once in a window contributes multiple rows to both sides of the rate; T2.06 converted the *audit* to DISTINCT-facts to match §5.1's wording and left the rate per-event, and T2.51 inherited the asymmetry verbatim. Separately, the gate's diversity rule needs two *attributable* origins of differing kinds while the payload's `source_kinds` is the union over all origins, so a lone origin asserting under two kinds slices as "diverse" without ever having lowered the bar | Both surfaced by T2.51's Fable review; the units divergence was plan-mandated (the brief instructed inheriting T2.06's derivation verbatim) so it is a disclosure rather than a defect, and the diversity divergence is wider than T2.51's own report stated. Neither is fixable in the runner without contradicting its brief, and both change how a gate verdict should be read — so they are labelled in the rendered report and recorded here rather than silently carried into G-C |
| 2026-07-31 | T2.54, T2.41, T2.26 | 3 | **RULED by the owner: doc 17 §11's "real" governs the premise *distribution*, not authorship or database of origin.** A `claim-fact` premise is real when minted by the production code path (extraction → `fact_lift` → `fact_sentence`) and byte-anchored to the `knowledge_triples` row that produced it, whatever corpus was ingested. Bench-lifted facts therefore qualify; hand-authored premises do not. Doc 17 §11 amended in place to carry the ruling — the corpus doc is where it lands, not a satellite document | Escalated to Tier 3 by T2.54's plan review, which judged the plan's Tier-2 self-resolution insufficient: lodging the definition in `LABELLING.md` leaves the next reader of §11 with the ambiguity intact. The rejected reading ("rows from the production vault") is near-circular — doc 20 sequences the homelab cutover *after* G-C and G-D — and the one route satisfying it today, snapshotting the live LAN instance's 415 memories into the bench database, would commit the owner's private memory content into a committed `gold.json` permanently, in a repo contemplating publication. The owner weighed that route explicitly and declined it. **The plan's original justification was factually wrong and was corrected first**: it claimed no production deployment existed anywhere, having measured only the dev-compose Postgres; a live instance serves this repo's own MCP tools |
| 2026-07-31 | T2.54, T2.41 | 2 | **RATIFIED by the owner: a 50% `l2-fact` proportion floor per task variant, enforced in `gate_eligibility`, with the `temporal` slice exempt and the exemption sunsetting when `fact_lift` renders validity windows.** Closes the hole where a 199-synthetic/1-real gold passes mechanically, since the eligibility lock previously checked only for *zero* `l2-fact` premises | Tightening-only and elaborating §11's stated intent rather than changing a gate's bar, so Tier 2 rather than Tier 3 — the plan reviewer concurred with that tiering while escalating the sibling ruling above. Paired with the machine-checkable anchor (premise byte-equal to a committed harvest manifest row, manifest as source of truth) so the floor counts real premises rather than self-declared provenance strings |
| 2026-07-31 | T2.54 | 1 | **RATIFIED by the owner: the label-consistency resample is n = 93 at ≤ 1 disagreement**, not the originally planned 37 | The plan review computed the power: at n = 37 a gold with exactly 5% label error passes 44% of the time and a pass certifies only < 12.2% error at 95% confidence — while 5% gold noise consumes the entire precision budget of the judge's 0.95 bar the resample exists to protect. At n = 93 the pass probability under 5% true error is 0.0500, so a pass genuinely certifies < 5%. Costs the owner roughly 1–1.5 h more, accepted deliberately |
| 2026-07-31 | T2.11, T2.40, T2.41, T2.54 | 2 | **T2.11 moved to `blocked` and gains `Depends: T2.41`; G-C is now transitively behind T2.54.** T2.11's Done-when requires adjudication by the *qualified* judge. T2.26 shipped the judge but measured contradiction precision **0.8182 against a 0.95 bar** stated in writing beforehand, so it minted no qualification record — and `VerificationJudge.judge()`, the only lawful consumer door, raises `JudgeNotQualifiedError` unconditionally while that record is absent (`app/services/verification_qualification.json` confirmed not present on disk). The record is mintable only by `run_judge_qualification.py --gate`, whose eligibility lock refuses a gold with < 200 live pairs or zero `l2-fact` premises — which is T2.54's output, consumed by T2.41. Since T2.40 (G-C evidence) depends on T2.11, **G-C now sits behind T2.54 exactly as G-D already did** | The dependency edge was missing, not the constraint: T2.26's own completion note says "T2.11 cannot ship on this judge", but T2.11's `Depends` field still read `T2.04, T2.26` — and `Depends` is what the runbook §1.5 entry check actually consults, so the graph permitted claiming a task that cannot compile a passing test. Same failure shape as the T2.41/T2.54 amendment logged earlier today: a constraint recorded on the producer and absent from the consumer's `Depends` is enforced only by whoever remembers to read it. **Not** resolved by fixing the judge's reversal-exclusivity errors: the 41-pair gold that measured 0.8182 has already been contacted, so tuning against those three errors is precisely the tune-against-gold loop T2.26's plan review flagged as its one Critical finding. A prompt edit also moves `prompt_sha`, hence the judge identity, hence de-qualifies mechanically — so any fix must be measured on T2.54's fresh gold regardless |
| 2026-07-31 | T2.62, T2.04, T2.22 | 2 | **T2.62 minted: nothing writes `review_state`, so a veto-disputed fact never reaches the review queue.** Doc 08 §4.3 pairs the status flip with opening `review_state` and §6 defines the queue as `WHERE review_state='open'`, but T2.04's five Done-when clauses never name the write and T2.22's cover only the queue's surface and index shape. `ix_knowledge_triples_review` has sat in the baseline since T0.12b with no writer | Surfaced by T2.04's implementer, which deliberately declined to absorb it, and independently confirmed by the Fable review (the only `review_state` mention in `backend/app` outside the model is an insert parameter defaulting to None that nothing passes). Minted rather than folded into T2.22 on the reviewer's recommendation: the writes belong inside `recompute_fact`'s `FOR UPDATE` window beside the sole journaller, and a queue-surface writer would leave a window where a fact is `disputed` but unqueued. The clear semantics additionally span T2.46's `under-sourced` label and §6's human-clear, so precedence needs one owner |
| 2026-07-31 | T2.54, T2.41, T2.26, T2.25 | 2 | **Doc 17 §11 makes the entailment gold's *composition* gate-binding, not only its size, and no task carried that.** §11: gold is "seeded from real synthesis drafts and real block answers once Layer 2 is live — **synthetic-only entailment gold is rejected as unrepresentative**; >= 200 pairs per task variant before the corresponding gate can open". T2.54's Done-when named only the resample and JSON-on-disk; its handoff from T2.25 named only volume. T2.54 now carries the composition clause and **depends on T2.10** | Raised as a Minor by the Fable review of T2.25, 2026-07-31, and confirmed against §11 verbatim. T2.25 is unaffected and stays `done` — its 41 pairs are 100% hand-authored for the honest reason that neither named source existed at its branch point, and it reserved `synthesis-draft` / `l2-fact` at test-pinned zero precisely so the first real harvest is a visible diff. The trap this closes is that G-D could otherwise be claimed on a grown-but-still-synthetic set. **Not the deadlock T2.25 feared**: §11 says "once *Layer 2* is live", and Layer 2 is `knowledge_triples`, whose producer is T2.10 in this epic — not T3.02 behind the gate. The `synthesis-draft` provenance and the block-answer variant remain behind T3.02 and doc 16, gating those variants only |
| 2026-07-31 | T2.47, T2.61, T2.34 | 2 | **T2.61 minted: the `expired_memory_cleanup` job bypasses T2.47's provenance-withdrawal hook.** T2.47 hangs the hook off `delete_by_memory_id`, which covers re-extraction and both interactive delete doors. The TTL sweep deletes by raw SQL (`app/services/job_runners.py`) and never reaches it; `fact_sources.source_ref` is a soft ref with no FK, so a TTL-expired memory strands its provenance and its sole-sourced facts never expire. Latent today (no `fact_sources` producer until T2.10) and live the moment `fact_lift` ships | Found by T2.47's implementer and confirmed by the controller against every delete path. Raised to Tier 2 because it is a **new task the plan missed**, not a T2.47-local correction: T2.47's own Done-when list is satisfied without it, and T2.34 — the only other task touching this sweep — explicitly reuses T1.37's sweep *unchanged*, so no existing task owns the fix. Sized S and made to depend on T2.47 so it lands on the shared withdrawal path rather than duplicating it |
| 2026-07-27 | T2.50 | 2 | Added a precondition: the arm's entity-linking semantics must be stated before any multi-hop activation verdict is read off the retrieval slice | T0.06a's adversarial review measured the ingested graph pair by pair and found the multi-hop bridges are not uniform. Six of the fourteen live pairs bridge through one shared entity row; eight bridge through same-name nodes of *different* `entity_type`, which are disjoint under the domain model's `(name, entity_type)` identity because Phase-4 dedup is type-constrained. The slice's achievable ceiling is therefore 6/14 under strict node-identity traversal and 14/14 under name or name-embedding linking. That is a property of the arm, not of the gold, so the gold records both ceilings and defers rather than guessing; without the semantics stated, an activation number measures the gold's undocumented shape rather than the arm |
| 2026-07-28 | T2.58 | 3 | **New task, opened from a Tier-3 doc/code conflict found by T1.60's planning pass and confirmed in code by the controller: Chat runs a THIRD retrieval implementation.** Doc 13 §4.1 asserted "Chat's reads ride the same one ranking path as Memories (doc 07 §9, invariant 17)". `ChatService._search_memories` calls `vector_repo.search` directly — semantic-only, no keyword arm, no RRF, no rank-fusion factor, no trace. Doc 13 §4.1 amended to describe the tree; the convergence is T2.58, placed in E2 beside T2.43. | Routed to E2 rather than E1 deliberately: converging Chat onto today's fusion only to re-converge it after the four-layer composition lands would be two rewrites of an invariant-bearing path. The escalation itself is the part worth recording — a Sonnet-tier planning lane hit retrieval-fusion surgery, recognised it as above its tier, and stopped instead of building it silently, which is runbook §2's escalate-on-discovery rule working in the direction it is hardest to follow. The count is also the finding: three ranking implementations now exist (`rank_fusion.py`, `code_query.py`'s own `RRF_K`, and Chat's none), so a task that fixes only one has closed one of two doors. |
| 2026-07-29 | T2.01 | 2 | **Done-when 2's "renders as such" is satisfied at the read-model level; the visual render transfers to T2.36.** T2.01's obligation is that a confirmed-but-expired fact is representable and that both axes are independently distinguishable on the read model | T2.36 (Facts tab) depends on T2.03, so no render surface can exist at T2.01 time — read literally, the box could not be checked by its own task. Recorded rather than left as a private interpretation: an unrecorded reinterpretation means the next agent auditing G-C evidence finds a box satisfied only under a reading nowhere in the plan. Raised as finding I4 by the Fable-tier plan review, 2026-07-29 |
| 2026-07-29 | T2.01, T2.07, T2.10 | 2 | **`compute_triple_key` embeds `project` VERBATIM — it is not canonicalised, while `subject_name` / `rel_type` / `object_name` are.** Decided while the table holds zero rows | `project` is case-sensitive exact-match text everywhere else: `memories.project` matches exactly in supersession gate 1, and T2.07's registry is a case-sensitive `name` PK. Doc 04 §8.3 says uuid5 over "canonicalised lowercase **names**" with project merely "embedded" — it never says the project is canonicalised. Canonicalising it would give projects `Foo` and `foo` — distinct registry rows with distinct memory scopes — one shared fact identity, so `ux_knowledge_triples_open` would reject `foo`'s insert while `Foo` holds the open belief: cross-project interference through a unique index, and corroboration merged across scopes. Changing this after T2.10 writes rows re-keys the table, so it had to be settled now. Raised as I3 by the whole-branch review |
| 2026-07-29 | T2.01, T2.10 | 1 | **`get_live` and `as_of` require `project`; `insert_open` still defaults it to `'default'`.** T2.10 must pass `project` explicitly when wiring the producer, or drop that default | E1's standing warning F7 (`E1-engine-core.md`) told whoever wired this layer to render the scope in the repository, not at the front door, so the reads were made scope-required (I2). The producer default was left because it mirrors `memories.project` and the column's own `server_default`. The sharp edge is key/column divergence: computing a key with project X while inserting without `project=X` mints a row findable only under the wrong scope, silently |
| 2026-07-29 | T2.02 | 1 | **`document` is not a fifth `source_kind`.** Doc 08 §4.1 names a `document` origin ("document → `document_id`", and the diversity example "memory + document + code") that doc 04 §8.3's column vocabulary `{memory, block, code, human}` does not carry. Resolution: `document` is the origin-key rule for content arriving under the **`block`** kind, not a separate value. `block` ships reserved-and-refused until its producer exists | Surfaced by T2.02's implementer and independently confirmed by its reviewer against both docs. Recorded because the next reader of doc 08 §4.1 hits the same apparent contradiction, and adding a fifth value to satisfy the prose would break the CHECK-adjacent vocabulary doc 04 fixes. Nothing produces either kind yet, so the resolution costs nothing today |
| 2026-07-29 | T2.03, T2.06, T2.36 | 2 | **The `confidence` formula is fixed here, because the corpus fixes only its properties.** Doc 04 §8.3 and doc 08 §4.1 bind `confidence` as an *aggregated* support estimate "recomputed with `verification_status`, never a single-source guess", and state no formula. T2.03 adopts `support = min(K, N) / N` and `confidence = min(0.90, 0.40 + 0.40·support + 0.10·(gate fired))`, pinned by **exact-value vectors** rather than by properties alone, and capped at 0.90 because the machine never claims certainty. **Contradiction deliberately does not enter it**: confidence is support, while a dispute is adjudication and lives on the verification/`review_state` surfaces T2.04 owns — so a contradiction-blocked hold can legitimately carry 0.90 | Raised to Tier 2 because three later tasks read this number: T2.06's journal evidence, T2.36's badge, and the review queue's consequence ranking. A formula chosen silently at code time would be an unreviewable decision propagating into all three. Revision is cheap **now** and expensive later — `knowledge_triples` has no producer until T2.10, so the table holds zero production rows. The exact-value pinning came from the Fable plan review (M1), which showed all four stated properties are survived by a coefficient typo: `0.04·support` is monotone, capped, row-invariant and deterministic while every confidence in the system is wrong |
| 2026-07-29 | T2.04 | 2 | **Recovery out of `disputed` is T2.04's, and is recorded here because T2.04's Done-when list does not name it.** Doc 08 §4's state diagram carries `disputed → corroborated : contradiction resolved`, but T2.04's five checkboxes cover only the veto's entry (one contradiction beats any number of corroborations, echo semantics, window overlap, no config knob, the e2e spec). T2.03 holds `disputed` unconditionally on the stated grounds that both the entry and the exit are T2.04's; that reading is now recorded rather than private | Raised as finding I5 by the Fable-tier review of T2.03's plan, 2026-07-29. Read literally, T2.04's checkboxes leave `disputed` a **one-way state with no owner for the exit** — the same unowned-transition shape §7's Tier-3 escalation surfaced, and the same read-literally trap the T2.01 amendment row (I4) exists to prevent. Cheap to record now, expensive as a surprise during T2.04's review. T2.03's own scope is unchanged: it never writes `disputed` and never resolves one |
| 2026-07-29 | T2.03, T2.60 | 3 | **Spec §2.1 promotion condition 4's supersession-signal half stands.** Doc 08 §4.1 and doc 04 §8.3 omitted it by drift, not by decision; **T2.60** is minted to own it as a deterministic promotion blocker (hold, never `disputed`, never demote). Doc 08 §4.1 and doc 04 §8.3 amended to carry the condition; the spec is unchanged because it was right. T2.03, T2.04 and T2.45 are unchanged in scope, and T2.03 is unblocked | Escalated by T2.03's plan (§7): a promotion-blocking input the spec requires had no owner in the task corpus, so facts could promote while a newer memory had already replaced the claim. Adjudicated at Fable tier under owner delegation; full ruling and its rejected alternatives at `.superpowers/sdd/rulings/2026-07-29-t2.03-supersession-blocker.md` |
| 2026-07-31 | T2.25 | 1 | **The task's two stated material sources were verified unavailable, and the material paragraph was corrected in place.** `article_synthesis` has no runnable body — it is a `PlaceholderJobRunner` until T3.02, which is behind G-D, so "run it manually in non-shipping mode" is not an available operation; and `knowledge_triples` holds zero rows because its producer is `fact_lift` (T2.10), so "live L2 facts" do not exist. The harvest was realised as hand-authored pairs: 25 over synthetic fact texts and 16 over verbatim `benchlib/retrieval/corpus.json` premises with a machine-checked corpus anchor, provenance declared per pair in a closed vocabulary with counted, test-pinned totals; `synthesis-draft` and `l2-fact` are reserved provenances pinned to zero until their producers land | The task text anticipated the deadlock but named concrete mechanisms that do not exist at this branch point; left uncorrected, T2.54's labeller would look for drafts that were never produced. Recording the realised provenance here keeps G-D's eventual precision/recall numbers traceable to what the gold actually contains — a gold set whose provenance is overstated is worse than a small one |
| 2026-07-31 | T2.04 | 1 | **`NO_DETECTOR` is retyped from `False` to `None`, and the contradiction input becomes three-valued (`bool \| None`).** `False` now means "every wired detector adjudicated this fact and found nothing" — the affirmative verdict that permits recovery out of `disputed` — and `None` means "no detector reported", which still holds a dispute unconditionally | T2.03 shipped `NO_DETECTOR = False` as a placeholder whose whole job was to be indistinguishable from a clean adjudication, because nothing could yet adjudicate. Recovery needs those two claims separated: with one boolean, any caller leaving the keyword at its default would resolve a real dispute by silence, which is the detector-less machine T2.03's unconditional hold existed to stop. The third value is the replacement guard and is strictly stronger — resolving a dispute now requires an affirmative verdict, not merely the absence of one |
| 2026-07-31 | T2.04 | 1 | **Recovery out of `disputed` re-enters the ordinary threshold rule rather than landing unconditionally on `corroborated`.** A resolved dispute targets `corroborated` when K ≥ N and `candidate` otherwise, under a new `recover` outcome | Doc 08 §4's state diagram draws only `disputed → corroborated : contradiction resolved`, but §4.1's N rule is unconditional and a fact can lose origins while disputed. Read literally the diagram would promote an unsupported fact past its own bar, so the two clauses can only both hold if recovery re-runs the count. Recorded because the extra `disputed → candidate` edge is not on the diagram and would otherwise read as an invention |
| 2026-07-31 | T2.04, T2.22 | 2 | **Nobody owns writing `review_state='open'` when the veto fires, or clearing it on recovery.** T2.04 deliberately does not write it | Doc 08 §4.3's recompute flowchart pairs the two ("set disputed, review_state open") and §6 defines the review queue as `WHERE review_state='open'`, with `ix_knowledge_triples_review` already in the baseline — but T2.04's Done-when list never names it and T2.22's Done-when covers only the queue's surface and index shape. `review_state` is a single shared text column that T2.46's `under-sourced` label also claims, so a veto that set it without owning the clear semantics would drift against the hysteresis label. Surfaced rather than absorbed: as it stands a disputed fact never reaches the review queue, so T2.22 must either own both writes or the gap needs its own task |
| 2026-07-31 | T2.04, T2.10, T2.11 | 2 | **`SINGLE_VALUED_RELATIONS` ships EMPTY; `HAPPENED_ON` was admitted in the first round and withdrawn.** The deterministic scan's whole reach is now the inverse-replacement rule. Constraint for **T2.10** (fact lifting), which is where these shapes actually enter the layer: a `HAPPENED_ON` row may carry a point date, a span day, or a *place*, and nothing downstream can tell them apart | `normalize_relation_type` folds three unrelated senses into one stored `rel_type` with no discriminator: a point occurrence, a span occurrence (a multi-day event asserted per day), and — through `LEGACY_RELATION_TYPE_MAP`'s `VISITED → HAPPENED_ON` and `LIVES_IN → HAPPENED_ON` (`app/taxonomy.py:128-129`) — a location. So "alice HAPPENED_ON paris" and "alice HAPPENED_ON tokyo" adjudicated as a contradiction while both are true, which is the manufactured dispute doc 08 §5.3's precision-first asymmetry forbids. A relation is single-valued only when *every* sense it stores is, and no deterministic predicate over `(subject_name, rel_type, object_name)` recovers the point sense: senses 1 and 2 are both date-shaped, so neither a date parse nor an ISO-shape gate separates them, and a fuzzy parser would put judgment inside a scan whose doctrine is that it has none. Re-admission needs the taxonomy to separate the senses first (taxonomy-first, doc 06 §3.1). Guarded in code by the empty set and in tests by a general rule — no member of `SINGLE_VALUED_RELATIONS` may be a target of `LEGACY_RELATION_TYPE_MAP`, re-read live — plus three regression shapes. Raised by the T2.04 reviewer; the coordinator overrode the reviewer's "a recorded constraint suffices" and required the code fix |
| 2026-07-31 | T2.54, T2.41 | 2 | **T2.26's eligibility lock encodes doc 17 §11's composition rule at its minimum decodable floor, and two of its inputs need T2.54's attention before the gate run.** `run_judge_qualification.py --gate` refuses a gold with < 200 live pairs, zero `l2-fact` premises, or any live `label_source: "author"` pair — but (a) `l2-fact` is today a *self-declared* provenance with no machine-checkable anchor tying an `l2-fact` premise to the `knowledge_triples` row it came from (the corpus pairs have exactly such an anchor via `corpus_key` verbatim equality; T2.54 owes the analogue when it harvests real premises), and (b) the `>= 1` real-pair floor means a 199-synthetic/1-real set passes mechanically — whether §11 needs a real *proportion* floor is an open question T2.54/T2.41 must settle before the gate run. Both are visible, not silent: the eligibility output always surfaces the counts (`l2-fact: 1/200`) | The lock blocks the named vector (a grown-but-still-synthetic set) in code, and refusing to invent a proportion threshold no doc states keeps the bar-before-number discipline; the residual softness is routed to the tasks that own the gold's composition and the gate verdict |
| 2026-07-31 | T2.26 | 1 | **Executed under the reviewed plan's interim/gate split: the judge, its bars and the enforcement mechanism landed; the qualification VERDICT stays T2.41's behind T2.54.** The judge lives in `app/services/verification_judge.py` (one door: the qualification-gated `judge()`, with the ungated `qualification_probe` scan-pinned to the harness); bars are `config` rows over stated defaults (0.95 entailed-precision, 0.90 entailed-recall, 0.95 contradiction-precision — stated in the plan before any number existed and not retuned); qualification is computed at read time from a committed record only a canonical-gold `--gate` run can mint (absence test-pinned), keyed to a judge identity that hashes model+params+prompt text, so a model swap or prompt edit de-qualifies mechanically. The prompt froze at fixture-pass before first gold contact (zero shakeout iterations, zero gold-contaminating edits, `gold_touching_attempts` published). Interim numbers on the 41-pair gold, reported straight: entailed P/R 1.000/1.000, contradiction precision **0.818 — below its bar** (two manufactured disputes on `direction` pairs), recorded in `docs/eval/2026-07-31-judge-qualification.md` and under G-D as interim | `Size: L` — runbook §3 required the plan-first path; three review rounds (1 Critical, 5 Important, 11 minor) reshaped the freeze discipline, the record minting lock and the attempt accounting before any code |
| 2026-07-31 | T2.26 | 1 | **T1.05's inert-purpose dispatch pin fired on the floor and was retired for `verification`, per its own handoff message.** The plan's file list missed `tests/test_inert_objects.py`: landing the judge makes T2.26 the purpose's first dispatcher, which is exactly what that guard exists to catch. The pin now covers `synthesis` alone (until T3.02); `verification`'s single-door discipline moved to the judge suite's stricter scan. Found by the floor, not by the plan — the first honest full-floor run failed on precisely this test | The guard's failure message names the procedure ("if this is the intended first writer, remove the purpose from this test"), so the edit is the designed handoff, not a workaround; recorded here because the reviewed plan did not foresee it |
| 2026-08-02 | T2.18 | 1 | **M3's shortfall journal follows the test plan, not §4.1's prose, because the plan contradicts itself — and the resulting label is deliberately pessimistic.** Plan §4.1 assigns "absent **or now in another project**" to `stale_snapshot`; test T3 requires a hand-supplied foreign-project candidate to journal `cross_project_violation`. Those cannot both hold: at the database the two cases are one state (a row exists under a different project) and nothing distinguishes a memory that *moved* between Phase R and Phase W from one that was never in scope. Implemented per T3 — absent → `stale_snapshot`, exists-elsewhere → `cross_project_violation`. **Consequence to record: a benign project-move race between R and W now journals under a defect label.** The rewrite aborts either way and the previous run survives, so only the label is affected | Chosen because the two error directions are not symmetric. Labelling a real cross-project violation as a benign race hides the one defect M1–M4 exist to surface; labelling a rare race as a violation costs an operator one investigation that the payload's candidate ids resolve immediately. Judged the right call by the Fable review, which asked for this ride-along rather than a code change |
| 2026-08-02 | T2.18 | 1 | **`build_projection` reads its node set and its edges in separate statements, so under READ COMMITTED a memory that becomes eligible in between raises `KeyError` and the project is skipped for that run.** Self-healing: the next run re-reads both and succeeds, and nothing is written in the meantime, so no partial or torn state is reachable | Recorded rather than fixed. Closing it means either one statement returning both shapes or a REPEATABLE READ snapshot, and both are larger changes than the failure justifies for a nightly job whose worst case is one project one run late. Named so the next reader meets it as a known bound rather than a mystery traceback |
| 2026-08-02 | T2.18, T2.53 | 1 | **`resolution` ships as a code-level keyword argument, not a `config` row, because `FieldDescriptor` cannot express a float.** Its `default` field is typed `int`, so a 1.0/2.0 knob is not representable in a job `config_schema`; the other four new knobs (`hub_cap`, `min_community_size`, `leiden_timeout_seconds`, `max_projection_edges`) are int-typed and do ship as config fields alongside the placeholder's `batch_size` | Widening `FieldDescriptor` to carry floats touches `job_registry`'s validation and every job's schema rendering — outside T2.18's lane, and not worth doing blind when O-3 records that none of these thresholds has an owning metric yet. Whoever gives topic quality a metric should decide whether `resolution` needs to be operator-tunable at all |
| 2026-08-02 | T2.18 | 1 | **Plan §5.2's "Phase R — own session, released" is implemented as a commit on the single session `detect_for_project` is handed, not as a second session.** §7.2 fixes the signature as `detect_for_project(session, project)` so the function has no factory to open a second session with; committing after the read achieves the property the phase split is for — no transaction open across Phase C — and Phase R writes nothing, so the commit is a release | The measurable property (`session.in_transaction()` is False during clustering, connection back in the pool rather than `idle in transaction`) is now test-pinned. Found by the Fable review, which measured `pg_stat_activity` and caught the module comments asserting the planned behaviour while the code held the transaction for the whole compute |
| 2026-08-02 | T2.18, invariant 15 | 2 | **`tests/test_dream_jobs.py`'s family scan is line-based and misses ordinary wrapped imports; measured, not inferred.** `from app.services import (\n    fact_lift,\n)` in `pipeline.py` — a Tier-A module reaching a *shipped* family job's body — leaves `test_no_app_code_reaches_a_family_job` **passing**, verified by running it. The quoted-job-key second net does not cover it: reaching the body through the module needs no job key. T2.18's own detector scan was rebuilt on an AST walk and does catch it, plus split-string dynamic reach; the precedent scan is deliberately left alone as not this task's to widen | Surfaced by the Fable review of T2.18 and confirmed empirically here. Recommended as its own small task: lift T2.18's AST helper into a shared test utility and give the family scan both nets, since one scanner serving two vocabularies is the fix, not two parallel line-based greps |
| 2026-08-02 | T2.12, T2.45, T2.34 | 2 | **The status bridge has no producer, so T2.12 ships dedup-driven subsumption only and the bridge-driven arm is deferred to a follow-up task.** Measured, not inferred: `grep -rn "close_window" backend/app/` returns three hits — a docstring line (`knowledge_triples.py:17`), the definition (`:188`) and its own debug log (`:220`) — and **no caller**; `grep -rn "apply_status_bridge" backend/app/` returns **one** hit, the definition (`supersede.py:643`), and **no caller**. So `apply_status_bridge`'s input — an `(invalidated fact, invalidating fact)` pair — cannot be produced today: `fact_lift`'s own docstring (`fact_lift.py:24-37`) documents stale-on-arrival as *unreachable* because Layer 1 carries no temporal qualifier, and the two `expire` callers (`fact_provenance.py:253` source withdrawal, `human_adjudication.py:171`) withdraw belief for want of evidence with **no invalidating triple in existence**. **T2.45's bridge is therefore built-but-unspent, not defective** — its primitive, guards, ruled evaluation order and decision record are all correct; what is missing is upstream of it. **T2.34 is named but does not unblock it**: pre-closing a fact's window when its own stated expiry passes makes `close_window` reachable and `invalidated` events real, but a window closed by its own expiry has no replacing triple and still supplies no `invalidating_fact_id`. The arm needs a producer of a *replacement* — a stale-on-arrival pass over a temporally-qualified Layer 1, or a contradiction-driven invalidation naming the winning fact. The follow-up task is minted from this row | Raised by T2.12's step-level plan (§8 O1), which escalated rather than resolving it, and **verified independently by the controller** with the greps above rather than taken on the plan's word. Ruled for deferral on scope and honesty: doc 08 §2.2 names **two** callers for the primitive — "dedup finds a near-identical newer memory that strictly subsumes an older one, **or** the status bridge decides a memory's every live fact is now invalidated" — and only the first is T2.12's, whose own task text describes subsumption from dreaming and never mentions the bridge. Wiring an arm that cannot fire on real data would add code whose only exercise is a hand-built fixture, plus a false sense of coverage on a path nothing reaches (invariant 23). The plan's refusal to fabricate a pairing is upheld as a standing rule the follow-up inherits: substituting the invalidated fact's own id for the invalidating one would let guard 1 nominate, as the memory that replaced the candidate, another memory asserting that very same discredited fact — a wrong write, not a conservative one. The four bridge tests the plan had drafted (T-BR1–T-BR4) are recorded in it as work the follow-up inherits, so the deferral loses nothing |
| 2026-08-02 | T2.12, T2.45 | 1 | **`supersede()` and `deprecate()` gain a keyword-only `reason: str = "status_bridge"`, threaded into `_journal` in place of the hardcoded literal at `supersede.py:302`.** Both writers journalled every transition as `"reason": "status_bridge"`, so a dedup-driven subsumption — the path doc 08 §5.4 assigns to `memory_dream`, and the one T2.12 actually ships — was recorded in an append-only journal under the name of a bridge that did not produce it. T2.12's dedup arm passes `reason="dream_dedup"`; `apply_status_bridge`'s two call sites pass nothing and keep the default, so **T2.45's behaviour is unchanged and its suite passes with zero edits**, which is the acceptance criterion for the change rather than a hope. This does **not** make `payload.reason` a key T2.13 may build on: the write-time fast path (`supersession.py`) writes its own `superseded` rows with a different payload shape and no `reason` at all, so the key is present on some `superseded` events and absent on others — T2.12's uniform `consolidated` stream stays the digest's source of truth | Found by T2.12's implementer as the first non-bridge caller of the primitive, and **scope explicitly widened by the controller** to fix it in T2.12's execution round rather than leaving a known-false label in an append-only substrate. A default rather than a required parameter because a required one would break every existing call site and turn a label fix into a cross-task diff; only a caller that knows better says so. Landed as its own commit, separate from T2.12's job wiring, so a change to another task's module is reviewable and revertible on its own |
| 2026-08-02 | T2.12, T2.08, T2.11, T2.53, T2.67 | 1 | **`register_dream_jobs` gains an `llm_provider` parameter, and `_ALLOWED_DREAM_JOB_LINES` gains one entry in the same commit.** The dreaming pass is the family's first member that needs a model handle, and `app.state.llm` is replaced whole on a config save (`app/api/routes/config.py:100`), so a closed-over orchestrator goes stale and keeps dispatching at the previous configuration. `main.py` passes `lambda: getattr(app.state, "llm", None)` — a provider callable rather than the FastAPI app, so the umbrella stays framework-free and a test passes a stub in one line. The parameter defaults to `None`, so every existing `register_dream_jobs(registry)` call site (including `tests/test_communities.py`'s) is unchanged. **T2.11 and T2.53 need the same handle**, so the shared-file edit is paid once here rather than worked around three times | Recommended by T2.12's step-level plan (§3 D1 option (a)) and ruled by the controller (§8 O3). The accepted cost is one entry in `tests/test_dream_jobs.py`'s exact-line allowlist, which is what that constant exists for. **Recorded for T2.67's executor:** that allowlist matches on stripped line *text* and is itself the defect T2.67 was minted for — a parenthesised multi-line import defeats the scan the set belongs to. T2.12 did not fix it; it added its entry in the existing style with a note naming T2.67 beside it, so the rework into node-addressable exemptions does not silently drop this entry |
| 2026-08-02 | T2.12 | 1 | **D6's Phase-W re-validation splits: the `status = 'active'` arm is dropped from the subsume arm and kept on the associate and refine arms.** `supersede()` re-reads the candidate under its own `FOR UPDATE` in the same transaction the caller already holds that row's lock in, so a local pre-check there could never disagree with it — it could only convert `already_superseded` and `terminal` into one anonymous `stale_skipped` and leave D4's refusal table with **no reachable path**. Two named tests are rebuilt around this: the plan's T-REF1 fixture genuinely cannot produce its refusal, because a pre-superseded candidate is excluded both by the seed predicate and by the probe's `statuses=("active",)` filter, so T-REF1 now drives the reachable path D4 itself names — two pairs sharing the older memory in one cycle — and T-STALE is re-keyed onto `content`, the half only the local check can catch. **The rationale does not transfer to `apply_associate`, which calls no primitive**: dropping the arm there left that path with no status guard at all, and it needed no concurrency to fire — pairs (A,B)→`subsumes` and (A,C)→`duplicate` in one cycle retire A and then write an `open` hygiene edge against it, which never self-corrects because a retired memory leaves the active probe, and permanently records an associate action on a non-active memory in an append-only journal | Deviation raised by T2.12's implementer with the reasoning above; **the subsume half ratified and the associate half rejected** by the scoped reviewer, who reproduced the wrong write in a single cycle (`subsumed=1 associated=1 stale=0`) and confirmed independently that the plan's T-REF1 fixture is unreachable. The associate arm's guard is restored and carries its own test, which fails when the guard is removed. Recorded because the plan's D6 text still reads as a single uniform rule, and a later reader restoring it uniformly would silently disarm the refusal table again |
| 2026-08-02 | T2.13, T2.12 | 2 | **RULED and RATIFIED: an undone subsumption is suppressed, not re-applied.** T2.12 left this open (§9.2 item 6b). T2.13 rules for suppression scoped as a **nomination filter inside `memory_dream.generate_pairs`**, not a lifecycle mechanism: `detect_supersessions`, `supersede()`, `deprecate()`, `apply_status_bridge`, the status lifecycle and `chk_superseded_has_pointer` are unchanged and none consults the tombstone — the primitive still supersedes that exact pair for any caller that asks (`test_the_tombstone_never_reaches_the_lifecycle` makes crossing the line audible). Mechanism: `memories.metadata.dream.undone_subsume.<counterpart_id>`, written in the same statement as the status restore, keyed on **both** memories' `content_sha` so it lapses when either text changes. **Tier 2, not Tier 3**: the category already exists one function away — `needs_refine` filters the refine work set — so the tombstone joins an existing category rather than inventing one | Ratified by the controller before execution, verified against the tree. Re-application here is **deterministic**, not probabilistic: the judge is seeded on unchanged content in fixed order, so this is not "the system may reconsider" but "the system will reverse you tonight, and every night". The drill confirms it — with the read removed, the second cycle logs `1 subsumed` over the same pair |
| 2026-08-02 | T2.13, T2.08 | 2 | **Doc 08 §7's undo-currency check is implemented as a compare-and-swap against the live row, not as an `events` watermark, and widened from "a newer consolidation change" to "any change".** §7's own parenthetical states the property; the watermark and "a newer consolidation change" are narrower proxies for it in the same sentence, so the CAS is **doc-faithful rather than a departure**. Load-bearing, not stylistic: `hygiene_state` is written only inside the dreaming pass today, so a watermark over `consolidated` events cannot see a human triage from T2.23, and the `created = True` associate inverse would then delete a triaged row | Ratified by the controller before execution. Guarded by `test_a_human_triage_refuses_the_undo`, drilled: with the CAS blinded the undo proceeds and takes the triage with it. Widening a safety guard this way can only ever decline to act |
| 2026-08-02 | T2.13, T2.45 | 2 | **`app/services/dream_undo.py` joins `_ALLOWED_POINTER_WRITERS` in `tests/test_supersede_primitive.py`, with a narrowing guard.** T2.45's scan allowed exactly two modules to write `memories.superseded_by`; the subsume inverse must write it, because restoring `status` and the pointer in **one** statement is what `chk_superseded_has_pointer` requires. This is **not a third supersede door**: doc 08 §2.1 already names "undo (§7)" alongside demote-first as a pointer-affecting path, and §7 requires the write — the two-module allowlist predates the path rather than forbidding it. The entry is not a blank cheque: `test_the_undo_door_never_writes_a_supersession` fails if the module ever names the superseded status outside its enum validator or writes a literal status, and it was drilled | The plan did not anticipate this scan; found by running the floor. Recorded at Tier 2 rather than escalated because the corpus does not have to change — doc 08 §2.1 contemplates the path and §7 mandates it, so what changed is a test allowlist written before the path existed. The invariant the scan protects (atomic set of status and pointer under one CHECK) is untouched |
| 2026-08-02 | T2.13, T2.23 | 2 | **`dream_undo.undo()` has THREE outcomes, and only `UndoRefused` guarantees nothing was written.** Returning means every named action is restored and uncommitted; `UndoRefused` means validation refused before any write, so the session is clean and needs no rollback; **any other raise — the journal readback's shortfall, a failing inverse, `lock_timeout`, deadlock — leaves restores already in the session and the caller must roll back.** The module owns no savepoint by construction (the atomicity scan forbids it), so it cannot self-heal: "partial undo is not representable" holds **under caller rollback**. The HTTP door inherits this from the request-scoped session dependency; **an in-process caller inherits nothing**, and a T2.23 bulk loop catching broadly per item and continuing on one session would commit a partial, unjournalled undo | Found by the Fable plan review, which caught that a two-outcome dichotomy the first consumer would have built on is contradicted by the plan's own D6. Pinned by `test_the_caller_rollback_seam_is_real`, which asserts the held restore **before** any rollback so the seam is a test rather than folklore, and drilled |
| 2026-08-02 | T2.13, T2.12 | 1 | **Five corrections to T2.12 §9.2's interface contract, confirmed against what shipped.** (a) The refine payload key is `metadata_dream_refine` holding the marker itself, not `metadata_dream`. (b) The associate payload's `after.edge.properties` is the **pass-relative** view, without the `dream` wrapper the database path carries. (c) `before.edge` is already the pass block, not the edge row. (d) **§9.2 item 7's two-way inverse has no arm for `created = False` with `before.edge = None`**, reachable the moment T2.16 owns the row first; restoring `None` through `jsonb_set` leaves the key present holding JSON `null`, which `pass_block_of` reads as absent while the row carries a value the prior state never had — so the inverse is three-way and the removal arm uses `#-`. (e) `created = True` does not license an unconditional row delete: a sibling pass may have claimed the row since | None is a defect in T2.12; each is a place where building from the prose alone produces wrong code. (d) was drilled: the `jsonb_set`-to-null form yields `'near_duplicate': None` exactly as predicted |
| 2026-08-02 | T2.13 | 1 | **T2.13's subsume inverse cannot be split into two statements — but only one of the two split orders raises, and the plan assumed the wrong one.** `chk_superseded_has_pointer` is `status != 'superseded' OR superseded_by IS NOT NULL`, so on the *restore* path clearing the pointer first raises while setting `status='active'` first **does not**: it leaves an active memory still pointing at its successor, which no constraint objects to. The forward flip is the mirror image, so carrying the forward direction's reasoning into the inverse gets the failure mode exactly backwards. The one-statement restore is required because the alternative fails **silently**, which is a stronger argument than the loud one the plan made. Both halves are now pinned | Found by running the plan's own T-SUB2, which asserted an `IntegrityError` that did not arrive |
| 2026-08-02 | T2.13, T2.38, T2.23 | 1 | **Three wire-surface corrections found by the repo-wide conformance scans.** (1) The reported field is `not_restored`, not the plan's `excluded`: `excluded` is owned by `ResponseEnvelope` with a different meaning (rows dropped from a result set, keyed by reason) and `tests/test_envelope.py` fails the build on a second declaration. (2) The 409 body carries its per-action reasons as `error.details`, a **list**, because `app/main.py`'s handler flattens a dict `detail` to a generic message; widening that handler would touch every route's error path. (3) The suppression tombstone records `undo_batch_id`, not the plan's `undo_event_id`: it rides the restore statement, which precedes the journal, so the event id cannot exist yet — the batch id is minted before the apply loop and every journal row of the batch carries it | All three found by running the floor rather than by reading. T2.38 and T2.23 read `not_restored` and `error.details` |
| 2026-08-02 | T2.13 | 1 | **`events.id` gains its first by-id consumer, so `0001_baseline.py`'s "nothing joins events by id" is now stale.** The composite `PRIMARY KEY (id, created_at)` means a bare `WHERE id = :id` scans every monthly child, so every lookup is bounded by the retention window and prunes to one or two children at the default 14 days. Ids that window misses are chased once over a wider bound, so an action just past its window reports the honest `retention_elapsed` rather than vanishing into "no such action". No index is added — that is a baseline edit and the baseline serialises through one owner per epic | Recorded so the schema owner meets the consequence rather than the comment |
| 2026-08-02 | T2.13, T2.12, T2.16 | 1 | **`MemoryUpdate.metadata` is wire-editable and `PostgresMemoryRepository.update` replaces `metadata_` wholesale, so one `PUT /api/v1/memories/{id}` destroys every subsystem's marker beneath `dream` at once** — today T2.12's refine marker and T2.13's subsume tombstone, tomorrow whatever T2.16 keys there. Both fail open, so this is a bound rather than a defect, and **no task owns the replace-not-merge question**. Note the door is a PUT; the plan called it a PATCH, which does not exist | Guarded by a test that **asserts the loss** rather than defending against it, so the third marker's author meets it as a test. Not fixed from this lane: changing the door to merge is a wire-contract change touching every `metadata` writer |
| 2026-08-02 | T2.13, T2.12, T1.29e | 1 | **`event_journal` gains `summary` to its declared crossings, and its probe driver gains two arms that model it.** The consolidation stream's refine action journals the summary it replaced and the one it wrote — which is what makes the action undoable at all — and `GET /api/v1/events` plus `/events/timeline` serve those payloads. **The crossing predates T2.13**: T2.12 shipped the writer, but no isolation-probe fixture produced a `consolidated` refine event until T2.13's `dream_cycle_digest` driver did, so the raw-body net had nothing to catch and the declaration stayed silent. Both arms now enumerate a payload sentinel against the event's own project label instead of letting it land as an unmodelled crossing; the `/events/timeline` arm previously enumerated **nothing at all** and passed only because no fixture reached it. It falls under the same escalated retention question and widens it by no new principle | Found by running the benchlib harness, which `testpaths = ["tests"]` excludes from the repo floor — the floor was green for all of it. Worth noting the shape: the probe's raw-body net is explicitly documented as firing for *either* a real leak *or* a driver that failed to model a field, and this was the second kind |
| 2026-08-02 | T2.13, T2.38 | 1 | **`POST /cycles/{id}/undo` silently shrank an explicitly named set; the already-undone prefilter is now scoped to the body-less whole-cycle form.** The door filtered `not view.undone` **before** intersecting with `body.event_ids`, so a request naming an action another curator had already undone returned **200 carrying only the rest** — no 409, no mention of the dropped action — defeating the primitive, which would have refused on `already_undone`, the first reason in the tested precedence. The failure is a two-curator race and it broke the 409-then-refetch flow T2.38 is built around. A named set (`event_ids` **or** `action`) now goes through whole and the primitive decides; the body-less form keeps the prefilter, where *undo what is left of this cycle* is what the request means. An `event_ids` entry outside the cycle is now 404'd rather than dropped, the same defect in its other shape | Found by the Fable task review, reproduced with a driver. The primitive was never wrong — this was the door only, which is why T2.23 (which consumes `undo()` directly) was judged unaffected. Guarded by four tests and drilled: restoring the prefilter turns the 409 back into a 404/200 |
| 2026-08-02 | T2.13 | 1 | **Two accepted review minors.** (1) An action kind with no registered inverse now reports a distinct `unsupported_action` rather than `state_changed`: the state may be pristine, and saying it changed sends an operator looking for a write that never happened. This is the reason a fourth reversible action kind (§8 O4) will meet before its inverse exists. (2) `undo()` issues `SET LOCAL lock_timeout`, which is scoped to the **transaction**, not the call, so an in-process caller that keeps working on the same session inherits a 5s timeout it did not choose — now stated in the three-outcome contract on the module docstring. Harmless for the HTTP door, whose transaction ends with the request | Both from the Fable task review. Two further minors were recorded rather than fixed: the pointer-guard docstring was softened to claim only the two syntactic properties its AST actually enforces (it cannot see that the bound status is a *journalled* value, which lives in the behavioural tests), and `_invert_subsume` would write a tombstone under an empty-string key if a payload lacked `pair.newer` — unreachable from today's producer, closable in one line |
| 2026-08-02 | T2.13, T1.29e | 1 | **Audit of every `_account_body(..., set())` arm in `isolation_probe.py`: one latent instance found and fixed, none remaining.** Nine arms enumerate nothing. Four are 202 capture acks carrying only a pre-minted id; three (the entity listing, its neighbours, and the content-free sweep) are *correctly* strict, because their surfaces declare no content crossing at all, so any sentinel is a real leak rather than an unmodelled field; one is the duplicates probe's absent-partition case, where every row is already forced-V1 and `set()` is maximal rather than lax. The ninth, `GET /api/v1/analytics/pipeline-logs`, is the closest analogue of the `/events/timeline` arm this task fixed and is **safe by payload shape rather than by accident**: the door returns `events.payload` verbatim for `extracted` rows, and `pipeline.py` writes `{**status, "outcome": ...}` — a closed status dict with no memory-derived text. Widening that payload would make the arm fire loud, which is the correct behaviour | Chartered by the controller as the cheapest moment to look, after this task found the `/events/timeline` arm enumerating nothing and passing only because no fixture reached it. Recorded so the next person to widen an `extracted` payload knows the arm is load-bearing |
