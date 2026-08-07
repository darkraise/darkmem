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

**Rejection does not survive a re-derivation, and that is the semantics rather
than a defect** (recorded 2026-08-06 from T2.28's rescope-1, deferred there as
out of scope). A human rejecting a *code-derived* fact leaves the belief closed
on that row — `reject_fact` expires it — and T2.28's restore respects that: the
born-rung statement's WHERE carries the open-belief predicate, so no machine
path puts a label back on the rejected row. But T2.28's **birth** path is keyed
on `triple_key`, not on the rejected row, so while the repository still asserts
the import the next lift tick mints a *new* open row born `corroborated` for the
same triple. That is the round-0-reviewed "re-adding opens a new window"
semantics and it is arguably correct — the code does still depend on the
package, and a person's verdict about one belief window is not a standing veto
over the world changing back. Whoever builds this task's adjudication surface
should state the consequence to the human rather than let them discover it: a
rejection over a fact whose evidence is a live parse is not permanent, and the
durable remedy is removing the dependency, not re-rejecting the fact.

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

**Unblocked for implementation 2026-08-06 (controller).** T2.41 is dropped from
`Depends` because the **code already refuses**: `VerificationJudge.judge()`
raises `JudgeNotQualifiedError` unconditionally without a qualification record,
and that refusal is scan-enforced. So the scan body can be written, tested
against a refusing judge, and shipped inert without any risk that it adjudicates
on an unqualified judge — the guard is structural, not procedural. What stays
gated is the **productive run**, which is what T2.41 was ever protecting.

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

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T0.13` · `Doc: 10 §6` · `Tag: target-new` · `Gate: G-C`

**Unblocked for implementation 2026-08-06 (controller).** G-C's stated
consequence is that "the code-deriver lane stays closed" because *"the deriver
mints facts born `corroborated`"* — but that is **T2.28's** act, not this
task's. This one is imports-only and LLM-free and writes to the inert
`repo_ids[]` arrays; it asserts nothing at the ladder's second rung. The gate
edge belongs on the promotion, and it stays there.

**What.** A narrow deterministic deriver minting Layer-1 assertions from a repo's import
edges only, tagged into the inert `entities.repo_ids[]` / `entity_relations.repo_ids[]`
landed in T0.13 — **this is their first writer.**

**Done when:**
- [ ] Imports only; no LLM call anywhere in the path
- [ ] Existing graph sweeps stay byte-identical in behaviour with `repo_ids[]` populated
- [ ] Re-derivation is idempotent per repo

**Verify.** `cd backend && python -m pytest tests/test_code_deriver.py -q`

#### T2.28 — Lift to facts born `corroborated`

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.27, T2.10, T2.95` · `Doc: 10 §6, 08 §4.1` · `Tag: target-new` · `Gate: G-C`

**HELD 2026-08-06, later the same day: the gate this task's licence rests on
does not hold yet.** The paragraph below is the standing position and it is
still right in principle — but T2.95's Fable review measured the serving gate
leaking on two doors (chat and the review queue read the ungated column), found
suppression invisible on the wire, and demonstrated that the scans do not fail
the build on a *new* bypassing path. T2.28 adds exactly such a path — a second
labelled surface — so building it now would stack a claim on a producer that is
not yet the single producer. **Start this task when T2.95's six repair items
land and are re-verified**, not before; nothing else about the reasoning below
changes.

**Buildable now; the label waits, not the code (amended 2026-08-06 with the M1
split).** This is the task G-C exists for — it mints facts **born
`corroborated`**, an assertion at the ladder's second rung, and serving that
badge over an unproven ladder is the precise harm the gate names. But the harm
is in the *badge*, not in the derivation. With `T2.95`'s serving gate in place
the lift can be built, tested and merged in full: without G-C's
promotion-metrics record every one of these rows leaves the read surface
labelled `candidate`, scan-enforced, and minting the record later lights them up
with no code change. **G-C keeps its teeth on the label and loses them on the
build.**

**What.** Consolidation lifts a corroborated Layer-1 assertion to a fact born
`corroborated` — the parse *is* the verification — with `origin_key = repo_id`. **One
origin per repo regardless of commit count**, matching the one-document-one-origin rule.

**Done when:**
- [ ] A repo indexed 100 times still counts as one origin, proven by test
- [ ] Born-corroborated is the only exception to the ladder, and it is documented as such
- [ ] Withdrawal (repo removed) demotes the derived facts

**Verify.** `cd backend && python -m pytest tests/test_deriver_lift.py -q`

#### T2.96 — Wire the deriver: nothing calls it today

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T2.27` · `Doc: 10 §6, 19 §6` · `Tag: target-new` · `Gate: G-C`

**Minted 2026-08-06 from T2.27's completion report, clause 4.** T2.27 landed
`app/services/code_deriver.py`, both doc 06 §6.1 primitives, and 47 tests — and
`assert_repo_graph` / `derive_assertions` have **no caller anywhere in
`backend/app`**, confirmed by the controller in the tree. So `repo_ids[]` has a
writer that production never reaches.

That is not a defect in T2.27, whose scope was the primitives and the deriver,
but it is the difference between a landed writer and a filled column — and
invariant 23 (scaffolding-not-substrate) is precisely about not conflating
them. The inert label retired on the strength of a writer existing, which is a
fair basis — but the schema inventory must say plainly that nothing schedules
it, or the next reader of that table concludes the bridge is live. **That note
lands when T2.27 merges** (it edits the same rows on its lane, so writing it
here first would only manufacture a conflict).

**What.** Give the deriver its trigger. The natural one is a re-index: a repo
whose imports just changed is a repo whose assertions are stale, and doc 10 §6
already scopes the citation re-verifier (T2.48) to a re-indexed repo's changed
files. Whether it is a `JobRegistry` Tier-C entry with its own cron and
`job:<key>` config row, or a hook on the reindex path, is this task's call —
but it must stay off capture and retrieval (invariant 15).

**Done when:**
- [ ] A production path fills `repo_ids[]`, proven end-to-end rather than by unit test
- [ ] Re-running the trigger is idempotent per repo, inheriting T2.27's strip
- [ ] Removing a repo strips its assertions (the withdrawal half of T2.28's third clause)

**Verify.** `cd backend && python -m pytest tests/test_code_deriver.py -q`

#### T2.97 — Repo-minted entities cannot dedup: no embedding, no ANN

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.27` · `Doc: 10 §6, 06 §5` · `Tag: target-new` · `Gate: G-C`

**Minted 2026-08-06 from T2.27's completion report, clause 3.** Doc 10 §6 sells
the bridge on anchoring: *"a `postgres` entity minted from a repo's imports is
the same deduped node as `postgres` from a memory (the anchoring benefit that
makes the bridge worth building)"*. As shipped, that holds only for an **exact
`(name, entity_type)` match**. A repo-minted entity carries no embedding —
writing one is an embedder call, which T2.27's LLM-free clause forbids — so
Phase-4's ANN probe cannot see it: `postgres` from code and `postgresql` from a
memory stay two nodes where the memory path would have merged them at cosine
0.85 under the `names_distinct` guard.

**This is a narrowing of a stated deliverable, not a bug**, and it is the same
shape as T2.16 shipping two of three signals: the mechanism is right and its
reach is smaller than the doc claims. Logged rather than silently accepted.

**The decision this task owns.** Three candidate shapes, and the choice is the
work:

- **Embed at derive time.** Simplest, and it makes anchoring symmetric — but it
  puts a model call inside a deriver whose whole doctrine is that it has none,
  and couples repo derivation to embedder availability.
- **A Tier-C back-fill** over repo-asserted entities with no embedding, reusing
  the `entity_embedding_cache__<slug>` path. Keeps the deriver clean and pays
  the same fingerprint-partition rules everything else does (invariant 2).
- **A scheduled arm on the back-fill that already exists.** `app/services/
  reembed.py` is a missing-fingerprint back-fill: "obsolete" there means "has
  no row in the active fingerprint's table", which is exactly what a
  repo-minted entity is, and `list_obsolete_entities` / `reembed_entities`
  already find and embed them. What it has no trigger for is a schedule. Least
  new code — but it is a whole-corpus operator action with its own lock set and
  broadcast surface, so turning it into a cron changes behaviour for every
  entity, not only repo-minted ones.

The second is the recommendation; the task may overturn it with a reason.
**Note an embedder call is not an LLM extraction call** — T2.27's clause forbids
the latter, and reading it as forbidding both is what left this gap.

**Shipped 2026-08-07: the second, scoped to repo-asserted rows.** Shape 1 is
not merely doctrinally awkward, it is blocked: T2.27's guard forbids the whole
orchestrator surface, `embed_batch_chunked` included, so taking it means
widening the guard until it permits an extraction too. Shape 3 was rejected on
the behaviour change above. The job is `repo_entity_anchoring`
(`app/services/entity_anchoring.py`), Tier C and not a dreaming-family member,
selecting under a data-resolved fingerprint and writing under the one the
embedder returned. **It closes only the order where the repo is indexed first**
— Phase 4 dedups at write time, so a repo indexed after the memory already
minted the near-named node still leaves two rows. Closing that needs a
retroactive entity-merge pass, which is a different mechanism and is not owned
by any task yet.

**Done when:**
- [ ] A repo-minted entity and a near-named memory-minted one resolve to one node,
      proven by test at the same threshold the memory path uses
- [ ] The deriver's LLM-free guard still passes, whichever shape is chosen
- [ ] No cross-fingerprint comparison (invariant 2)

**Verify.** `cd backend && python -m pytest tests/test_code_deriver.py -q`

#### T2.100 — A declaration that says the wrong thing

`Model: Opus 5` · `Effort: high` · `Size: S` · `Depends: T2.99` · `Doc: 08 §4.3, 12 §4` · `Tag: target-new` · `Gate: standing`

**Minted 2026-08-06 from T2.99's adjacent finding (AF1), with the exposure
itself ruled acceptable** (amendment log, same date). The journal keeps
serving the rung; what must change is the marker that claims otherwise.

`claim_gates.ungated_status` defines wrapping a value as **a claim that the
value reaches no reader**. The ladder's journal sites wrap it — correctly,
in that a journal payload is not a served label — but `list_events` then
hands that payload to an authenticated reader under the same auth as the
facts door. So the declaration is false at exactly the sites where it is
load-bearing, and the enforcement scan reads it as a settled exemption.

**A false declaration is worse than an undeclared site.** An undeclared site
trips the scan and gets looked at; a falsely declared one is trusted by the
scan and by the next person to read it. That is the whole defect here — the
exposure is ruled, the lie is not.

**What.** Split the marker so the audit substrate declares itself as the
audit substrate: one meaning "this value reaches no reader at all", one
meaning "this value reaches a reader as a *record of a computation*, never
as a claim". Both remain scan-visible; neither may be a comment. The
`ungated_status` docstring stops asserting something untrue of its own call
sites.

**Done when:**
- [ ] Every current `ungated_status` site is re-classified deliberately, and
      the report says which meaning each got and why
- [ ] The scan distinguishes the two and still fails the build on an
      undeclared emission
- [ ] No site declares "reaches no reader" while a route serves it — proven
      by driving the door, not by reading the call site

**Verify.** `cd backend && python -m pytest tests/test_claim_serving_gates.py -q`

#### T2.99 — The topics door serves a raw-rung aggregate

`Model: Opus 5` · `Effort: high` · `Size: S` · `Depends: T2.95` · `Doc: 08 §4.3, 09 §3` · `Tag: target-new` · `Gate: standing`

**Minted 2026-08-06 from T2.95's second rescope (DF1).** `GET
/topics/pin-suggestions` is live-mounted and puts `verified_fact_count` on
the wire; `pin_suggestions._FACT_COUNT` computes it over the **raw**
`verification_status IN ('corroborated','confirmed')`. With G-C's record
absent, a reader subtracts the visible `confirmed` facts and recovers the
withheld-rung count.

This is the same class as the facts-list inversion oracle T2.95's round 2
closed, and it is weaker in the same direction — per-subject counting rather
than per-fact membership — but it is a live door and the count also gates
suggestion **membership** through a fact floor, so the leak has two exits.

**The principle that decides the shape, already settled on `tier`:**
*derivation may use the true status; the wire may not reveal it.* Whether
membership keeps computing on the true rung while only the served number is
gated, or both are gated, is this task's call — but a suggestion that appears
with a served count of zero still hints at the membership decision, and the
answer has to say why that residue is acceptable or close it.

**Done when:**
- [ ] With the gate closed, no served number distinguishes a withheld
      `corroborated` from a genuine `candidate` — driven at the door, not asserted
      at the counter
- [ ] Minting the record restores the true counts with no code change
- [ ] A sweep shows no other served aggregate over the raw rung

**Verify.** `cd backend && python -m pytest tests/test_claim_serving_gates.py tests/test_pin_suggestions.py -q`

#### T2.101 — Retroactive entity merge: the anchoring order that never heals

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.97` · `Doc: 10 §6, 06 §5` · `Tag: target-new` · `Gate: G-C`

**Minted 2026-08-07 from T2.97's completion report and confirmed by its adversarial
review.** T2.97 gave repo-minted entities embeddings, so Phase 4's ANN probe can see
them — but it closes **one order only**. Repo indexed → anchoring tick → memory
ingested merges into one node. Memory ingested first, repo indexed later, **never**
merges: `assert_from_repo` is an exact-key `ON CONFLICT (name, entity_type)` upsert
with no ANN probe, and Phase 4 dedups only at memory-write time, so nothing re-runs
the comparison. Re-derivation cannot heal it either — the strip-and-rewrite is keyed
the same way.

That is the order **an existing install produces the first time it indexes a repo**,
which makes it the common case rather than the corner. The limitation is pinned by
`test_a_repo_indexed_after_the_memory_still_leaves_two_nodes`, so this task turns a
red test into a decision rather than discovering the problem fresh.

**What.** A retroactive merge pass over entities that a repo asserted and a
near-named memory-minted node already exists for. The hard part is not finding the
pairs — it is that merging two live entities means rewriting `memory_ids`,
`repo_ids[]`, every relation endpoint, and the `technologies` denorm, atomically,
without breaking the `(name, entity_type)` uniqueness the whole graph rests on.

**Done when:**
- [ ] A memory-first-then-repo pair resolves to one node, at the same 0.85 threshold
      and under the same `names_distinct` guard the write path uses
- [ ] `test_a_repo_indexed_after_the_memory_still_leaves_two_nodes` is replaced by its
      inverse, not deleted
- [ ] Merging is idempotent and never merges across `entity_type`
- [ ] Tier C, off capture and retrieval (invariant 15)

**Verify.** `cd backend && python -m pytest tests/test_repo_entity_anchoring.py -q`

#### T2.102 — One deliberate pass over the frontend event-taxonomy map

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: —` · `Doc: 13 §4` · `Tag: target-new` · `Gate: standing`

**Minted 2026-08-07 from T2.48's rescope, which called the gap systemic rather than
incidental — correctly.** `frontend/src/features/activity/event-taxonomy.ts` maps
`EVENT_TYPES` values onto activity tabs, and a value missing from the map surfaces
only under "all", never on its own tab. Three consecutive rounds have each found one
missing and fixed exactly that one: `contradiction_scanned` (T2.11), `citation_stale`
(T2.48). The rescope then swept the whole vocabulary and found **seven** unmapped
values with live emitters, of which `invalidated`, `human_verdict` and `undone` fit
existing tabs cleanly.

**Three one-line fixes in three rounds is the signal.** Each was correct in isolation
and none was the fix, because the map is maintained reactively — a value lands in the
closed vocabulary, its emitter ships, and nothing fails when the map does not learn
about it. The taxonomy-first rule already governs the vocabulary; it does not reach
this map.

**What.** One pass mapping every emitting `EVENT_TYPES` value deliberately, plus the
guard that makes the next miss impossible: a test that fails when a value with a live
emitter has no entry. A value that genuinely belongs only under "all" is a decision to
record in the map, not an absence to infer.

**Done when:**
- [ ] Every `EVENT_TYPES` value with a live emitter is classified deliberately, and the
      report says which got which tab and why
- [ ] A new vocabulary value with an emitter and no map entry fails the build
- [ ] Values that belong only under "all" say so explicitly rather than by omission

**Verify.** `cd frontend && npm test -- event-taxonomy`

#### T2.98 — The same-endpoint arm has an index for half of itself

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T2.11` · `Doc: 08 §5.3, 04 §8.3` · `Tag: target-new` · `Gate: G-C`

**Minted 2026-08-06 from T2.11's completion report.** Doc 08 §5.3 calls the
same-endpoint arm "an index lookup", and for the subject half it is:
`ix_knowledge_triples_live` is `(subject_name, rel_type, object_name) WHERE
expired_at IS NULL`. **The object half has no leading index**, so a candidate
search keyed on `object_name` scans. It is Tier-C and off both hot paths, so
this is a scale problem rather than a live one — but the doc's own cost
argument for choosing SQL over embeddings rests on both halves being lookups,
and one of them is not.

Out of scope for T2.11 deliberately: that lane's schema mandate was the
`pg_trgm` extension and its GIN index, and widening an unrelated index under a
single-owner shared baseline file is how two lanes collide.

**Done when:**
- [ ] An `object_name`-keyed candidate search uses an index, shown by plan, not by assertion
- [ ] `0001_baseline.py` regenerated in place — still exactly one revision
- [ ] The existing subject-half lookups are not regressed

**Verify.** `cd backend && python -m pytest tests/test_contradiction_scan.py -q`

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

`Model: Fable 5` · `Effort: high` · `Size: M` · `Depends: T2.29, T2.44, T2.84` · `Doc: 07 §3` · `Tag: target-new + activation` · `Gate: standing`

**`T2.84` added to `Depends` 2026-08-05.** `w_heat`'s signal is retrieval heat, and T2.65
established that fact-level heat has **no counter** — the memory-bridged proxy is an
interim position with a stated error bound, and T2.84 replaces it with a real fact-keyed
table. Measuring `w_heat` before that lands would record a ledger number taken against a
substrate scheduled for replacement, and the activation log is precisely the artifact that
must not carry one.

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
the measured `pg_trgm` shortlist miss rate exceeds its stated bar. Groups facts for
counting only; never merges rows, never rewrites `triple_key`.

**The gating measurement is `T2.52`'s, not `T2.11`'s** *(corrected 2026-08-05: this text
said "T2.11's measured miss rate", but T2.11 is `contradiction_scan` and owns no
measurement — T2.52 is the miss-rate runner, and it is already this task's `Depends`. The
wrong reference mattered: T2.11 is **blocked** on an unqualified judge, so a reader would
have concluded T2.33 was blocked behind it when its gate had in fact already cleared.)*

**The gate has cleared.** T2.52 measured **41.7% (5/12)** on the `lexically-disjoint`
slice against a **20%** bar stated beforehand — `docs/eval/2026-08-05-t2.52-contradiction-missrate.md`.
So the "not needed, measured" branch below is **closed**, and this task ships the writer.

**Done when:** miss rate measured and compared to the bar before any code ships; if the
bar is not exceeded, the task closes as "not needed, measured" and the template stays
inert; `names_distinct` is carried into the grouping.
*terminal-by-design — nothing depends on this; it is a backstop, an activation, or a
leaf surface, not infrastructure another task consumes.*

**Verify.** `cd backend && python scripts/benchlib/run_contradiction_missrate.py`

#### T2.34 — `expires_at` self-expiring dated memories

`Model: Opus 5` · `Effort: high` · `Size: S` · `Depends: T1.50, T1.37` · `Doc: 08 §2.3` · `Tag: activation` · `Gate: G-C`

**Split 2026-08-04.** This entry was the memory *and* fact halves of one task; doc 08 §9
and §3.1 contradict each other on the fact half and it is escalated as **T2.85**. The two
were never one mechanism — §2.3 and §9 name them separately — and only the fact half is
blocked, so they are split rather than both held.

**What.** Extraction populates `memories.expires_at` from a memory's own stated expiry
date, so a dated memory self-expires without a caller setting a TTL. The write path is
doc 05's (pipeline Phase 5, savepoint A, with the rest of the memory-row enrichment); the
sweep that spends it is T1.37's, **reused unchanged** including demote-before-delete.

**The derivation is deterministic, and the reason is the F1 bench.** Adding an expiry
field to the extraction schema changes the system prompt, and the bench cache is keyed on
`sha256(content + system_prompt)` — so it would invalidate every cached entry, red the
gate until a live re-warm, and force a re-recorded F1 baseline. A post-extraction parse in
the same idiom as the existing regex date-anchoring rescue adds no entities and no
relations, so entity/relation F1 is untouched and the cache stays valid. *(Owner's ruling,
2026-08-04.)*

**Conservatism is a correctness requirement, not a style preference.** T1.37's sweep
**deletes** the row — embeddings cascade, provenance is withdrawn — so a false-positive
expiry is silent, irreversible data loss. "The licence is valid until 2026-12-31" is a
claim about a licence, not an instruction to forget the note on that date, and a parser
that cannot tell those apart destroys knowledge on a timer. The detector therefore matches
only **self-referential retention instructions** — the memory addressing its own lifetime —
and never a date merely adjacent to an expiry word.

**Done when:**
- [ ] A dated memory expires without a caller setting a TTL, through T1.37's sweep
- [ ] A caller-set `expires_at` is never overwritten by the derivation
- [ ] A derived expiry that is not strictly in the future is refused, so capture can never
      arm a sweep that deletes the memory it just wrote
- [ ] A date about some *other* subject does not become the memory's own TTL, proven by
      test against the phrasings that tempt it
- [ ] The extraction bench is unaffected: `run_bench.py --algo-only` stays green with no
      re-warm

**Verify.** `cd backend && python -m pytest tests/test_self_expiring_memories.py -q`

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

#### T2.91 — Pin suggestions have no durable prior to diff against

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T2.39a, T2.53` · `Doc: 09 §3` · `Tag: rebuild` · `Gate: G-C`

**What.** Minted 2026-08-05 from T2.39a's Fable review (F1), which ruled T2.39a's
clause 3 met at the **mechanism** level and unmet at the **observable** level.

`GET /knowledge/topics/pin-suggestions` calls `diff_topics({}, current)` — an empty
prior — so `prior_member_count` is always null and **every entry reads `new`,
permanently**. `grown` / `stable` / `decayed` can never surface. The review
established this is not merely a pre-T2.53 condition that time will fix: **the only
snapshot that ever exists lives in memory inside the detection job's body, mid-run,
and is discarded.** No durable prior exists anywhere for a read door to diff against.

The consequence names the epic's own recurring failure: **T2.39's Done-when "pin
suggestions show what changed between runs" is unbuildable against live data** —
which is the exact demo-data failure the T2.39/T2.39a split was created to prevent,
reappearing one level up.

**Where it belongs is a real decision, not an obvious one.** The review verified the
direction claim: invariant 15's scans forbid app code from reaching dream-family job
bodies, but **nothing forbids the job body calling `pin_suggestions.py`**. So
persisting a snapshot from `topic_detection`'s body is permitted. Whether the prior
belongs there, in a table the door reads, or in the door itself, is this task's to
settle and to write down.

**Done when:**
- [ ] A durable prior exists that survives across detection runs, and the door diffs
      against it rather than against `{}`
- [ ] `grown`, `stable` and `decayed` are all reachable on the wire, each proven by a
      test spanning **two real detection runs** — a single-run fixture cannot see any
      of them, which is why this was invisible until review
- [ ] The prior keys on the stable dominant-entity label, never the churning
      community id — the same identity rule T2.20 fixed and T2.39a mutation-proved
- [ ] Invariant 15 is not weakened: whatever writes the snapshot, no capture or
      retrieval path reaches a dream-family job body, and the source scan still passes
- [ ] T2.39's clause 3 becomes satisfiable, and T2.39a's amended clause is retired

**Verify.** `cd backend && python -m pytest tests/test_pin_suggestions.py tests/test_topics_read_surface.py -q`

#### T2.92 — An empty LLM completion is written, read as pending, and re-billed forever

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T2.19` · `Doc: 09, invariant 14` · `Tag: rebuild` · `Gate: standing`

**What.** Minted 2026-08-05 from T2.39a's Fable review (F2), and **confirmed in the
tree by the controller**. This is a live defect with a running cost, not a
theoretical one.

`LLMOrchestrator.chat_completion` (`app/services/llm.py:330-343`) returns the
vendor's `content` with **no empty-content guard** — it raises on a malformed
envelope and on truncation, and passes `""` straight through. `generate_report`
(`app/services/memory_community_reports.py:222`) returns that raw, and its own
docstring promises it "never swallows an error into a placeholder string" — which is
true of exceptions and false of an empty success.

So an empty completion writes `report_string = ""`. `report_status()` treats empty
and unset identically **by design**, so the topic reads `pending` forever, and the
next cycle regenerates it — **billing a model call every cycle, indefinitely, for a
topic that will never leave pending.** Nothing surfaces it: `pending` is a legitimate
state and the operator sees a topic that simply never finishes.

This also invalidates a defence T2.39a made in good faith — that `ready` + empty is
"unreachable in production". The *current* producer can write it.

**The fix belongs in T2.19's module, not in the read surface.** A read door cannot
distinguish "never generated" from "generated empty" once the empty string is on
disk; the write path has to refuse it.

**Done when:**
- [ ] An empty or whitespace-only completion for the report purpose fails loudly
      rather than being stored — recorded as `failed`, with the reason, so the state
      is visible instead of silently re-attempted
- [ ] A test drives an empty vendor completion and fails if it lands as `pending`
- [ ] The re-billing loop is closed: a topic whose generation failed is not
      regenerated every cycle without limit; state which policy was chosen
- [ ] `generate_report`'s docstring stops promising something the empty case breaks
- [ ] Whether the guard belongs on `chat_completion` (every purpose) or on the report
      path alone is decided and written down — a global guard is the stronger fix and
      the wider blast radius, so it is a decision, not a default

**Verify.** `cd backend && python -m pytest tests/test_community_reports.py -q`

#### T2.93 — Nothing calls the report pass, so no topic report is ever generated

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T2.53, T2.19` · `Doc: 08 §5, 06 §7` · `Tag: rebuild` · `Gate: G-C`

**What.** Minted 2026-08-05 from T2.92, which went looking for the cycle that
re-bills an empty report and found there is no cycle. `run_topic_detection`
(`memory_community_detection.py:387`) — the body `topic_detection` actually
dispatches — calls `detect_for_project` and nothing else. A repo-wide scan
finds **zero** callers of `generate_reports`, `snapshot_reports` or
`restore_reports` outside `backend/tests`.

Two consequences, and the second is the one that bites. **No topic report is
ever generated in production**, so every topic reads `pending` forever
through T2.39a's read surface — the state is honest, the pipeline behind it
is simply absent. And the carry-forward seam is unexercised: `report_string`
is written against a row id that the *next* detection run deletes, so even
if reports were generated by hand they would not survive one cycle.

T2.19's docstring calls this "the seam T2.53 inherits" and states the
sequence in full. T2.53's Done-when asked only for registration — cron,
floor, per-job lock, 409 on a held trigger — and delivered exactly that.
Neither task was wrong; the wiring simply sits between them and nobody owns
it.

**Done when:**
- [ ] `topic_detection`'s runner sequences the documented order per project:
      `snapshot_reports` (pre-rewrite) -> `detect_for_project` ->
      `restore_reports` -> `generate_reports`
- [ ] A test spanning **two** detection runs proves a generated report
      survives the id churn — the property the seam exists for and that no
      live path has ever exercised
- [ ] The LLM pass is bounded by the job's own config, not unbounded per
      tick, and a report failure never aborts the detection half that
      already committed
- [ ] Invariant 15 holds: the scan still passes, and no capture or
      retrieval path reaches the job body
- [ ] `PlaceholderJobRunner` status is unaffected — this is a live job
      gaining its missing half, not a placeholder being lit

**Verify.** `cd backend && python -m pytest tests/test_dream_jobs.py tests/test_community_reports.py -q`

#### T2.95 — Claim-serving gates: an evidence record gates the label, not the code

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.26` · `Doc: 08 §4.3, 09 §4.3, 17 §11` · `Tag: target-new` · `Gate: standing`

**What.** Minted 2026-08-06 with the M1 split. It is the mechanism that lets
implementation run ahead of evidence without ever putting an unbacked claim in
front of a user, and it generalises a pattern already shipped rather than
inventing one: `VerificationJudge.judge()` has refused unconditionally without a
qualification record since T2.26, scan-enforced, and that refusal never delayed
T2.26's own construction.

Two more truth claims need the same treatment:

- **`corroborated` on a fact.** Without G-C's promotion-metrics record, the
  ladder still computes — the internal bookkeeping is unaffected — but the
  **badge is not served**: rows leave the read surface labelled `candidate`.
- **`grounded` on an article.** Without G-D's judge-qualification record,
  articles synthesise and store, but no serving path may label one grounded.
  Doc 09 §4.3 already withholds never-grounded articles, so this narrows an
  existing rule rather than adding a surface.

**The refusal must be structural, not procedural.** A flag someone can flip, or
a convention someone must remember, is exactly what the M1 split cannot rest
on: the whole safety argument for building years ahead of measurement is that
no code path *can* serve an unbacked label. Both refusals get the AST scan
treatment `verification_judge` already has — a test that fails the build when a
serving module reaches the label without the record.

**Done when:**
- [ ] A fact with no promotion-metrics record serves as `candidate` on every
      door, and a test drives both doors rather than asserting the shape
- [ ] An article with no qualification record cannot be served labelled
      grounded, by any path, proven by a scan and not by inspection
- [ ] Absence of a record is distinguishable in the trace from a genuine
      `candidate` — a suppressed label and an earned one must not read alike,
      or the suppression becomes a silent downgrade
- [ ] Minting a record lights the labels with **no code change**, proven by
      writing a fixture record and re-reading both surfaces
- [ ] The scans fail the build on a new serving path that bypasses either gate

*This is the load-bearing task of the M1 split: if it is wrong, implementation
running ahead of evidence stops being safe.*

**REOPENED 2026-08-06 — it was wrong, and the sentence above is why that
matters.** The Fable review (`reviews/2026-08-06-t2.95-gate-attack.md`) refutes
clauses 1, 3 and 5 with measured drills, and records clause 2 as discharged by
argument rather than by the scan it demands. The design is vindicated —
enforcing at the producer is right — but two consumers dodge the producer,
three schemas drop `label_suppressed`, and the scans enumerate known modules
instead of quantifying over serving paths. The repair is bounded and scoped in
the review's closing section:

1. `chat.py` reads `row.labels["verification_status"]`; `review_queue`'s fact
   arm routes through `row_labels`.
2. Decide `tier`'s semantics under suppression — recompute off the served
   status, or document it as ranking-only and strip it from the wire. Serving
   tier 3 beside `labels: candidate` leaks the withheld rung numerically.
3. `label_suppressed` reaches the wire on `FactListItem`,
   `FactDetailResponse` and `ComposedRowLabels`, with a wire-level test.
4. Both scans walk `app/` structurally — routes and MCP included — and assert
   the absence of any `verification_status` emission not originating in
   `row_labels`. Quantifying is the only shape that fails on the *next* new
   path; enumerating is a snapshot.
5. At least one REST and one MCP door driven with the gate closed and **no
   fixture**.
6. The gate keys on `id_kind`, so the article surface cannot light on the fact
   record. `served_status` does not key on it today, which means G-C's record
   would light `grounded` when T3.02 lands.

**Verify.** `cd backend && python -m pytest tests/test_claim_serving_gates.py -q`

#### T2.94 — The dual-level channel: nothing reads `relation_embeddings`

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.49` · `Doc: 07 §4, §11, 04 §5.3` · `Tag: target-new` · `Gate: G-C`

**What.** Minted 2026-08-06 while executing T2.32/T2.49, which together left
doc 07 §4's three graph signals two-thirds wired and the gap invisible from
the task list. T2.32 shipped PPR's producer and fused it as a ranked list.
T2.49 shipped the `relation_embeddings` **vectors** and the Tier-C job that
keeps them current. **Nothing turns those vectors into candidates**, so
`w_dual` and `dual_level_enabled` exist as flags over a channel that does not
exist, and T2.50 — which is chartered to measure the graph arms — assumes a
reader that was never anyone's deliverable.

This is now enforced rather than remembered: `arm_ablation.resolve_ablatable`
returns `w_dual` as **blocked**, so `--arm w_dual` refuses with the reason
instead of running two identical legs and reporting an exact zero delta that
reads like a measured "no win".

**The global arm is the one channel with no project column of its own** (doc
07 §11, restated in §4 so no implementer re-opens it). `relation_embeddings`
keys on the global `entity_relations`, which carries no project. The channel
must therefore resolve its candidates through the asserting relations'
`memory_ids` and re-apply the project filter to **those memories** — or label
its results cross-project. This is the single exception the SQL pushdown does
not cover with an index, and getting it wrong is a cross-project leak that
returns plausible rows.

**Done when:**
- [ ] A relation-vector arm produces a ranked list of memory ids and joins the
      fusion under `w_dual`, gated by `dual_level_enabled`, both shipping at
      the today-equivalent off
- [ ] Inert means the same rows, not merely the same scores — the arm is
      appended only when it carries weight, the property T2.32's PPR arm is
      pinned on
- [ ] The global arm scopes through asserting memories or labels its rows;
      a test drives a cross-project relation and proves no foreign memory is
      returned unlabelled
- [ ] Both doors derive the weight through one helper, as `ppr_list_weight`
      already does for PPR, so a half-flipped config cannot mean one thing to
      chat and another to search
- [ ] `resolve_ablatable("w_dual")` stops being blocked, and the reason text
      is removed rather than left stale

*Unblocks T2.50's `dual_level` half; T2.50 stays the judge of whether either
graph arm clears a bar (runbook §2).*

**Verify.** `cd backend && python -m pytest tests/test_dual_level_channel.py -q`

#### T2.90 — The knowledge e2e cannot seed its own subject

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T2.86` · `Doc: 17, invariant 14` · `Tag: rebuild` · `Gate: G-C`

**What.** Minted 2026-08-04 from T2.86's re-review, which ruled the demo-only e2e
the **honest maximum for a fix round** and said the remedy is a task, not another
round of that loop.

The Facts surface is GET-only: `app/api/routes/facts.py` has no write door, and
the backend tests seed by direct session insert. So a Playwright spec cannot
create the fact it needs to look at, and every real-mode assertion about the
knowledge surfaces is unreachable. The consequence is precise and worth stating
in full: **wire-shape parity between `FactDetailResponse` and the frontend's
`LiveFactDetailData` is provable only by a vitest suite that mocks `apiFetch`
with hand-built fixtures.** Both sides can agree with each other while disagreeing
with the wire, and nothing in the repo would notice.

That is the same class as F11 on T2.36 — the doubled `/api/v1` prefix that made
the Facts tab 404 on every request while eight good tests stayed green, found
only because a sibling lane happened to read the file. The lesson there was that
mocked-boundary tests cannot see the boundary. This task builds the thing that
can.

**Not a licence to add a write door.** A public `POST /knowledge/facts` would let
a caller assert a fact directly, which the whole verification ladder exists to
prevent — facts are *derived*, never posted. The seeding path must be test-only
and must not become a second producer.

**Done when:**
- [ ] An e2e-visible seeding path exists that a Playwright spec can drive, and it
      is unreachable from a normal deployment — a test-only route guarded by
      environment, a fixture command, or a seeded disposable stack; whichever is
      chosen, a test fails if it is reachable in production configuration
- [ ] `frontend/tests/knowledge.spec.ts` visits the Facts tab and the fact detail
      route against a **real backend**, not the demo fixture
- [ ] A wire-shape drift is caught: renaming a field on `FactDetailResponse`
      without changing the frontend fails the e2e, and a test proves that by
      driving the rename
- [ ] The seeding path cannot mint a fact that bypasses the ladder — whatever it
      inserts is what `fact_lift` would have produced, or the test says plainly
      that it is a fixture and not a derivation

**Verify.** `cd frontend && npm run test:e2e -- knowledge`

#### T2.89 — What an undo restored is unrecoverable after the toast

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T2.13` · `Doc: 08 §7, invariant 14` · `Tag: rebuild` · `Gate: G-C`

**What.** Minted 2026-08-04 from T2.38's fix round, where it was **declined as
out of lane and the decline was verified** by the scoped re-review: this is a
backend schema gap, not a UI shortcut.

`UndoBatchResponse.undone[]` carries per-action `restored` and `not_restored` —
the only place the system ever states **which fields** an undo put back.
`DreamAction`, the read side, carries `undone`, `undone_at`, `undone_by` and
`undo_batch_id` but neither of those two lists
(`app/schemas/dream_digest.py:29-52`). So the digest re-read after an undo can
say *that* an action was undone and by whom, and cannot say *what changed back*.

**The consequence is a one-shot disclosure.** The information exists exactly once,
in an ephemeral toast, and a user who misses it cannot recover it — a second undo
attempt correctly refuses with `already_undone` rather than re-reporting. For a
journal whose whole premise is that the record outlives the moment, a
lifecycle-relevant fact that survives only in a transient notification is the
wrong shape.

**Prefer reconstructing over re-storing.** The `undone` event already carries the
batch id and the journal is append-only, so the restored/not-restored split
should be derivable from `events` at read time rather than denormalised onto a
new column. Check that before adding storage — the retention question over
journal payloads is already an unresolved Tier-3 item and this task must not
quietly enlarge it.

**Done when:**
- [ ] The digest read reports, per undone action, which fields were restored and
      which were not — sourced from the journal rather than re-stored, unless
      that is shown to be impossible and the reason is written down
- [ ] A test drives undo → re-read and asserts the two lists survive the round
      trip, failing if the read side reports only `undone: true`
- [ ] `not_restored` keeps its name; `excluded` is owned by `ResponseEnvelope`
      with a different meaning and `tests/test_envelope.py` fails the build on a
      second declaration
- [ ] The UI stops depending on the toast as the sole carrier

**Verify.** `cd backend && python -m pytest tests/test_dream_digest.py tests/test_dream_undo.py -q`

#### T2.87 — The duplicates response carries what a supersede direction needs

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T2.23` · `Doc: 08 §6` · `Tag: rebuild` · `Gate: G-C`

**What.** Minted 2026-08-04 from T2.37's Fable review, which ruled the lane's
refusal to build "Supersede instead" **correct restraint rather than an
unshipped obligation**: `HygieneDuplicateItem` carries two memory ids and a
similarity score, and nothing else. A frontend cannot honestly decide which of a
pair is the older, superseded one from that, and a direction picker built on it
would be the UI inventing an adjudication.

Doc 08 §6 names four bulk verbs and only three are reachable, so the gap is real
— it is just a **backend** gap, which is why it is its own task.

**The enabling change is small and was measured, not guessed.**
`build_duplicates_query` (`app/services/hygiene_queue.py:186`) already joins both
memory rows — its `WHERE` reads `src.status = 'active'` and
`tgt.status = 'active'` — so both sides are in scope and the SELECT simply does
not project what a decision needs.

**Undoability was never the obstacle**: supersede maps to `ACTION_SUBSUME`
through `deprecate()`, the same invertible action prune already uses, and the
review verified that mapping in `hygiene_queue.py` / `supersede.py` /
`dream_digest.py`.

**Done when:**
- [ ] `HygieneDuplicateItem` carries, for **both** endpoints, at minimum
      `created_at` and a content preview, so a direction is derivable from the
      response alone without a second fetch
- [ ] The preview respects the same project-isolation preview rules the
      isolation probe enforces — a duplicates row must not become a hole through
      which content crosses a project boundary
- [ ] `POST /hygiene-queue/bulk/supersede` is reachable from the Hygiene queue
      with the direction shown before it is applied, confirmed like the other
      bulk actions and undoable through the same cycle door
- [ ] A test fails if the response omits either side's timestamp — the whole
      point is that one side is older

**Verify.** `cd backend && python -m pytest tests/test_hygiene_queue.py -q`

#### T2.88 — `GET /review-queue/counts` cannot be project-scoped

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T2.22` · `Doc: 08 §6, invariant 14` · `Tag: rebuild` · `Gate: G-C`

**What.** Minted 2026-08-04 from T2.37's Fable review. `GET /review-queue/counts`
(`app/api/routes/review_queue.py:70`) takes **no `project` parameter at all**,
while `GET /facts` and `GET /articles` beside it both do. So a filtered queue
renders a count from a different population than the list below it.

T2.37 handled this the only honest way available to it — an inline
`(unscoped — across all projects)` qualifier next to the number — and the review
ruled that **passes invariant 14 narrowly** (the qualifier sits on the number it
qualifies) **but is skimmable, and the note is a workaround for a backend
asymmetry rather than a fix**.

Do not delete the qualifier as part of this task without checking what replaces
it: if the count becomes scopeable, the honest surface is a scoped number with
no qualifier; if some arm genuinely cannot be scoped, the qualifier must survive
and say which arm.

**Done when:**
- [ ] `GET /review-queue/counts` accepts the same `project` parameter its
      sibling reads accept, and applies it
- [ ] The absent parameter still means all projects, so no existing caller changes
      behaviour
- [ ] A test fails if the counts endpoint and the list endpoints disagree about
      the population for the same `project` argument — that disagreement is the
      whole defect
- [ ] The Review queue drops the unscoped qualifier where it no longer applies

**Verify.** `cd backend && python -m pytest tests/test_review_queue.py -q`

#### T2.86 — The fact detail route on live data

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T2.36a, T2.36` · `Doc: 13 §5.1, 12 §2` · `Tag: rebuild` · `Gate: G-C`

**What.** Minted 2026-08-04 from T2.36's fix round, which fixed the dead link by
removing it and said plainly that wiring the page is a task rather than a fix.
`src/routes/_authenticated/knowledge_.facts_.$factId.tsx:64` calls `useDemoFact`
**unconditionally**, so with `DEMO` off — the default since T1.58 — any real fact
id renders "This fact does not exist in the demo store." T2.36a shipped
`GET /knowledge/facts/{id}` and nothing calls it.

The reason this is not a fix: the page renders a verification ladder, a dispute
panel and multiple belief windows, and `FactDetailResponse` does not carry them.
So this task is partly a **backend** question — decide, per field, whether the
detail door grows to serve what the page shows, or the page stops showing what
the door cannot support. Doc 13 §5.1 describes the surface; doc 12 §2 fixes the
route. Neither is free to be quietly narrowed to whatever is cheapest.

**The row's `detail_available` flag is the thing to retire.** T2.36's fix
introduced it as a producer capability — false on the live path — so the row
offers no navigation it cannot honour. That is correct as an interim, and it is
also a surface hiding a capability the system is supposed to have. Removing the
flag is part of done, not a follow-up.

**Done when:**
- [ ] The route reads live data and a real fact id renders that fact
- [ ] Every field the page displays is one the door actually serves; anything it
      cannot serve is removed from the page rather than rendered empty or faked
- [ ] A disputed fact renders **both sides** here, with the backend's two-sided
      claim string verbatim
- [ ] `detail_available` is retired and the Facts tab links to the detail route
      unconditionally
- [ ] **A stale code citation renders as stale** (added 2026-08-07 from T2.48's
      rescope). T2.48 serves `FactSourceGroup.stale` and types it on the
      frontend, and `fact-sources.tsx` reads it nowhere — so a human auditing a
      downgraded badge sees the broken citation looking identical to a live one,
      which is the visible-cause story ending at the API boundary. T2.48 routed
      this here and the routing was correct in principle, but every clause above
      binds only the *removal* direction ("anything it cannot serve is removed"),
      so nothing obliged rendering a field the door already serves. Naming it
      makes the disposition real rather than nominal.
- [ ] A failed read renders as a failed read, distinct from a missing fact
      (invariant 14) — and a 404 for a fact that genuinely does not exist is a
      third, distinguishable state
- [ ] Simple/Advanced honoured, inside `detail-level-invariants.test.tsx`'s
      coverage rather than only in the task's own file

**Verify.** `cd frontend && npm test -- fact-detail && npm run test:e2e -- knowledge`

*(Note the second half is a real obligation: T2.36's fix round established that
`npm run test:e2e -- knowledge` matched zero specs before it added them, so an
e2e Verify clause on this surface is now runnable.)*

#### T2.39a — The topics read surface and the pin-suggestion door

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T2.20, T2.19` · `Doc: 09 §3, 13 §5` · `Tag: target-new` · `Gate: G-C`

**What.** Split from T2.39 on 2026-08-04, for the same reason T2.36a was split from
T2.36 on 2026-08-03: the UI task names a backend it can call and there is no door.
`app/services/topic_browsing.py` (`browse_topics`, `get_topic`, `topics_for_memory`,
`get_injectable_report`) and `app/services/pin_suggestions.py` (`snapshot_topics`,
`diff_topics`, `compute_pin_suggestions`, `journal_pin_suggestions`,
`accept_pin_suggestion`, `dismiss_pin_suggestion`) both shipped with T2.20 and are
well tested — and a repo-wide scan finds **zero** consumers of either module outside
`backend/tests`. No REST route, no MCP tool, no job. Nine public callables and no
caller.

That makes two of T2.39's four Done-when clauses unsatisfiable as written:
"accept/dismiss round-trips" has nothing to round-trip against, and "pin suggestions
show what changed between runs" requires `diff_topics`' output to be reachable from a
browser. A UI lane handed T2.39 unsplit would have satisfied both against
`useDemoStore`, which is the failure T2.36's split existed to prevent.

This task builds the **door**, not new mechanics: T2.20 owns the semantics and is not
to be re-litigated. Note the identity rule T2.20 established — pin suggestions key on
the stable dominant-entity label, never the churning community id — must survive onto
the wire, because a route that keys accept/dismiss on the community id reintroduces the
churn T2.20's Done-when exists to exclude.

**Done when:**
- [ ] A topics list and a topic detail door exist under `/api/v1/knowledge`, matching
      `api-rest-conventions.md`, serving what `browse_topics` / `get_topic` return
      including a **pending** report as pending rather than as absent
- [ ] The injectable report is served through `get_injectable_report`, and a topic whose
      report has not been generated is distinguishable on the wire from one whose report
      is **failed or skipped** *(amended 2026-08-05: the original clause said "empty".
      An empty report and an ungenerated one **do** collapse on the wire — both read
      `pending`/`null` — and the read door cannot separate them, because the write path
      stores `""` on an empty completion. That is **T2.92**, in T2.19's module. This
      clause is reduced to the distinction this door can actually make.)*
- [ ] Pin suggestions are readable with the diff `diff_topics` computes, showing what
      changed between runs *(the 2026-08-05 reduction to "serves that shape faithfully"
      is **retired 2026-08-05** by T2.91, which built the durable prior the original
      clause needed. The door loads it and all four statuses are reachable on the wire,
      each proven across two real detection runs. The clause stands as originally
      written.)*
- [ ] Accept and dismiss are `POST` doors that persist through `accept_pin_suggestion` /
      `dismiss_pin_suggestion`, keyed on the **dominant-entity label**; a test fails if
      the route keys on the community id
- [ ] Every door is project-scoped, and a cross-project read fails a test
- [ ] The doors journal to `events` through `record_event` with an already-vocabulary
      event type — widening `EVENT_TYPES` is taxonomy-first and is not this task's

**Verify.** `cd backend && python -m pytest tests/test_topics_read_surface.py tests/test_pin_suggestions.py -q`

#### T2.39 — Topics tab

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T2.20, T2.39a, T2.91` · `Doc: 13 §5` · `Tag: target-new` · `Gate: G-C`

**What.** Browsing, report injection, pin-suggestion diff.

**Unblocked 2026-08-05.** `T2.91` was added to `Depends` and is done: the second
clause below — the one the T2.39/T2.39a split was created to make buildable, and
which stayed unbuildable one level up — now has a durable prior behind it, and all
four diff statuses are reachable on the wire. Note the **first** clause is honest but
thin until `T2.93`: no live path generates a topic report at all, so "renders as
pending" is currently the only report state a real backend can produce.

**Done when:** a pending report renders as pending; pin suggestions show what changed
between runs; accept/dismiss round-trips; Simple/Advanced honoured.
**Verify.** `cd frontend && npm test -- topics`

---

## Lane K — gates

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

**Verify.** `cd backend && python scripts/benchlib/run_retrieval_eval.py --arm w_ppr && python scripts/benchlib/run_retrieval_eval.py --arm w_dual`

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

**Verify.** `cd backend && python -m pytest tests/test_queue_ranking.py tests/test_access_stats.py -q`
*(Corrected 2026-08-05: the minted field named `tests/test_review_ranking.py`, which does
not exist — the ranking's real coverage is `test_queue_ranking.py`, which this task
extended. Fifth instance of the 2026-08-04 back-fill audit's finding.)*

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

#### T2.71 — Composition serves fact rows with no badge

`Model: Opus 5` · `Effort: high` · `Size: S` · `Depends: T2.36a, T2.55` · `Doc: 12 (the badge is a structured field), 07 §5` · `Tag: rebuild` · `Gate: G-C`

**What.** Found by T2.36a's Fable review, 2026-08-03, and ruled "real and live":
`layer_composition.py` contains **zero** badge references, so every L2 fact the retrieval
path serves today goes out without one. Doc 12 fixes the badge as present on L2/L3 rows
and null on L0; composition satisfies half of that by accident, since it emits no badge at
all.

Not a defect in T2.36a — its brief forbade touching `layer_composition.py`, because T2.55
held that file in the same round. The producer exists and is shaped for this:
`fact_badge.row_labels(...)` already encodes the L0 rule and refuses a badge on a memory
row, `badges_for_facts` batches its queries, and `ComposedRow` already carries `id_kind`
plus a `verification_status` that is `None` for memory. This is the map over composed rows
that nobody's lane could write.

**This blocks G-C.** T2.40's evidence run makes claims about served output; a gate cleared
while every served fact is unlabelled would overstate its coverage. Land this before T2.40
runs.

**Done when:**
- [ ] Every served L2/L3 row carries the badge doc 12 fixes; every L0 row carries
      `badge: null` and `verification_status: null` with `lifecycle` instead
- [ ] The badge is read from the producer, never recomputed at the composition site — a
      second `claim` string anywhere fails a test
- [ ] The per-page query count does not grow with the number of facts returned
- [ ] Removing the badge from a composed fact row fails a test

**Verify.** `cd backend && python -m pytest tests/test_layer_composition.py tests/test_fact_badge.py -q`

#### T2.73 — Four new surfaces took the isolation probe offline

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.23, T2.36a` · `Doc: 17, invariant 14, CLAUDE.md "the harness can break while the floor stays green"` · `Tag: rebuild` · `Gate: G-C`

**What.** T2.23 and T2.36a each registered new `ContentSurface` rows — `hygiene_queue_duplicates`,
`hygiene_queue_memories`, `knowledge_facts_browsing`, `knowledge_fact_detail` — and neither
added the matching driver to `backend/scripts/benchlib/isolation_probe.py`'s `DRIVERS`
table. That table's completeness check is a hard `RuntimeError`, so **the entire
cross-project isolation probe is offline**, not merely one assertion: all eight
`test_isolation_probe.py` tests error or fail on the one cause.

This is the hazard `CLAUDE.md` names in as many words — `pyproject.toml` sets
`testpaths = ["tests"]`, so `pytest -q` does not collect `scripts/benchlib/tests`, and the
harness can break while the floor stays green. Both lanes were green on their Verify and
on the repo floor, both were reviewed, and neither touched benchlib so neither ran it. The
controller merged on a green floor rather than a green `./scripts/gate.sh`, which is where
this should have been caught; that is recorded rather than quietly fixed.

**What is actually at risk.** The probe is the guard that proves memory content does not
cross a project boundary past its declared preview. While the driver table is out of step
it proves nothing at all, and it would stay silent through any number of future merges.

**Done when:**
- [ ] A driver exists for each of the four surfaces, seeded and asserted the way the
      existing `review_queue_*` and `pipeline_failure_triage` drivers are — sightings with
      `true_project`, `true_status` where a lifecycle applies, and `_account_body` for the
      raw wire
- [ ] The four drivers assert against the surfaces' **declared** crossings: the two
      hygiene arms declare `memory_ids` and `content_preview`, the two knowledge arms
      declare `fact_content`
- [ ] `test_driver_table_matches_the_registry` passes without weakening the completeness
      check
- [ ] The full benchlib suite is green **run by path**, and its number is recorded
- [ ] Removing any one of the four drivers fails the build

**Verify.** `cd backend && BENCH_DATABASE_URL=... python -m pytest scripts/benchlib/tests -q`

#### T2.74 — Three surfaces declare a content preview nothing checks

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T2.73` · `Doc: 17, invariant 14` · `Tag: rebuild` · `Gate: standing`

**What.** Found while reviewing T2.73, 2026-08-03, and confirmed by its reviewer as a
**pre-existing** gap rather than anything T2.23 or T2.36a introduced.
`reembed_backfill_queue`, `pipeline_failure_triage` and `capture_buffer_triage` each
declare they cross `content_preview`, and none of their drivers checks the preview
boundary. So each is asserted to truncate and none is proven to.

T2.73 built the generic checker (`_preview_boundary()`) while closing the same hole on
`hygiene_queue_memories`, so the mechanism exists.

**It is not a paste, and the reviewer measured why.** `capture_buffer_triage` declares a
**500-character** preview while its current long fixtures end near 280, so dropping the
helper in unmodified would false-positive rather than pass. Each surface needs its
fixtures checked against its own declared boundary first; the per-surface preview length
is the input, not a constant.

**Done when:**
- [ ] Each of the three drivers checks its own declared preview boundary
- [ ] Each surface's fixtures demonstrably run past that surface's boundary, so the check
      can fail — verified per surface, not assumed from `hygiene_queue_memories`
- [ ] Widening any one surface's preview slice fails the probe, drilled per surface
- [ ] The boundary guarantee does not rest on a fixture comment: a future fixture that
      falls under the boundary fails the build rather than silently disarming the check

**Verify.** `cd backend && python -m pytest scripts/benchlib/tests/test_isolation_probe.py -q`

#### T2.75 — The frontend spells the claim the backend owns

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T2.36a` · `Doc: 12 (the badge field), 13 §5.3, invariant 14` · `Tag: rebuild` · `Gate: standing`

**What.** Doc 13 §5.3 is explicit that the badge string is a contract and **no screen
paraphrases it**. `frontend/src/demo/data/chat-curated.ts` and `memories-curated.ts` carry
badge-shaped claim strings as demo fixtures, and `verification-badge.tsx` documents the
claim in a comment. T2.36a's `assert_no_certainty_words` guard and T2.71's second-producer
scan both walk `backend/app` only, so **no guard in this repo can see any of them**.

Two independent sightings, 2026-08-03. T2.71's implementer reported the fixtures as an
adjacent finding and correctly took no action. T2.71's reviewer reported that **a fixture
at `knowledge-curated.ts:52` is a claim form the shipping producer can never emit** —
`"human-ratified by q.tran on 2026-07-21; previously asserted by 2 distinct origins of
kinds [human, memory]"`, where doc 12's confirmed form is the plain sentence with a
trailing `, human-ratified`. That turns a stylistic worry into a demonstrated divergence.

**Corrected 2026-08-03 by the controller, and the correction matters.** This section
previously cited `chat-curated.ts:52` and recorded the sighting as partial and unverified,
on the belief that the review had terminated on a model-tier limit before writing its
verdict. Both halves were wrong: `review-T2.71/REVIEW.md` is a **complete** review carrying
both verdicts, five findings and a bottom line, and its citation is `knowledge-curated.ts`.
`chat-curated.ts:52` is `"no verification badge on this row — badge: null,
verification_status: null (L0 memories carry lifecycle, not the ladder)"` — a **correct** L0
badge line and not a divergence at all. So the recorded pointer aimed at a healthy row: an
agent re-verifying it as instructed would have found nothing wrong, concluded the sighting
was a false positive, and **discarded a real finding**. The finding is verified, not
pending.

**Why it is not merely cosmetic.** A fixture is what a developer reads when deciding what
the UI should render, and a comment is what they read when deciding what the string means.
Both currently disagree with the one producer, and the disagreement is invisible to CI. The
UI is still on demo data (`useDemoFacts`), so nothing user-visible is wrong today — which
is exactly the window in which to fix it.

**Done when:**
- [ ] Every badge-shaped string in `frontend/` is either produced by the backend payload or
      is provably a fixture that matches a form the producer can emit
- [ ] A guard covers `frontend/` the way `fact_badge`'s covers `backend/app` — a new
      paraphrase fails the build rather than being noticed by a reviewer
- [ ] The `knowledge-curated.ts:52` divergence is corrected — it is verified, not pending,
      so this is a fix rather than a re-check
- [ ] The forbidden words "true" and "verified" are checked on the frontend side too

**Verify.** `cd frontend && npm test -- badge && npm run typecheck`

#### T2.76 — `gate.sh` points the harness at the shared bench database

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: —` · `Doc: runbook §8, CLAUDE.md "Commands"` · `Tag: rebuild` · `Gate: standing`

**What.** Found by T2.21, 2026-08-03, by running the gate in a live four-lane round and
getting a red that was not its own. `scripts/gate.sh` exports `TEST_DATABASE_URL` (line
166) and **not** `BENCH_DATABASE_URL`, so the benchlib arm falls back to the unnumbered
shared `darkmem_bench` regardless of the lane's assignment. In a concurrent round the
harness resets a database another lane is holding:

```
test_arm_ablation … DeadlockDetectedError: DROP SCHEMA IF EXISTS public CASCADE
```

Re-running with the variable pinned is green. **So the repo's own merge gate is the one
command that ignores the per-lane isolation the runbook §8 requires**, and it fails in the
shape the runbook explicitly warns about — "failures that look exactly like a code
regression".

**The fix has a precedent to follow, not to invent.** T2.54 hit the sibling defect and
resolved it by deriving a per-checkout database name from a hash of the checkout path, so
the result stops depending on what a human exported. The same reasoning applies here and
the two should not diverge: a gate that must be configured correctly per invocation is a
gate that will be wrong again next round.

**Do not** resolve this by having `gate.sh` require the caller to export the variable. That
makes a correct gate depend on a human remembering, which is what produced this bug.

**Done when:**
- [ ] `gate.sh` never points the harness at the unnumbered `darkmem_bench`
- [ ] Two gates run concurrently from two worktrees without colliding, demonstrated rather
      than argued
- [ ] An explicitly exported `BENCH_DATABASE_URL` is still honoured, so a deliberate run
      can still target a chosen database
- [ ] The derivation matches T2.54's precedent or states why it must differ

**Verify.** Two concurrent `./scripts/gate.sh` runs from two worktrees, both green.

#### T2.72 — The MCP vault tools, and the door parity doc 12 already assigns

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.36a` · `Doc: 12 §2–§3, invariant 17` · `Tag: target-new` · `Gate: standing`

**What.** Found by T2.36a's Fable review, 2026-08-03. Doc 12 §2's route table assigns
`fact_get` a REST twin at `GET /knowledge/facts/{id}` — the path T2.36a built — and §3 puts
the agent-facing vault reads on MCP's `fact_get` and `knowledge_search`. **Neither MCP tool
exists, and no task owned them**: a scan of every epic file for `fact_get`,
`knowledge_search` or an MCP vault tool returns nothing.

**There is no live invariant-17 breach today**, precisely because no MCP vault tool exists
— parity is not violated by a surface that is absent on both doors' agent side. T2.36a
filed its routes as REST single-door on a trust-posture argument the reviewer judged
**weak**: every two-door surface in this repo already pairs an unauthenticated MCP tool
with an authenticated REST route, so posture is not what decides single-door.

So this task builds the agent's side of the vault and re-files the parity row: the
**detail** route becomes `fact_get`'s twin; the **list** route legitimately stays REST-only,
because doc 12's list-shaped agent twin is `knowledge_search`, not a fact list.

**Done when:**
- [ ] `fact_get` and `knowledge_search` exist on MCP, serving the same rows the REST door
      serves, through the same service layer — not a parallel implementation
- [ ] The badge rides both doors identically, byte for byte
- [ ] `docs/two-door-parity.md`'s row for the detail route is re-filed as two-door, and the
      list route's REST-only classification carries doc 12's reason rather than a posture
      argument
- [ ] A row shape that diverges between the doors fails a test

**Verify.** `cd backend && python -m pytest tests/test_door_parity.py tests/test_mcp_vault_tools.py -q`

#### T2.77 — The claim-scan allowlist is the shortest path to a second producer

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T2.71` · `Doc: 12 (the badge field), invariant 14` · `Tag: rebuild` · `Gate: standing`

**What.** T2.71 hardened `test_no_second_claim_string_exists_under_app` to read bytes
constants and docstrings, closing two demonstrated byte-exact evasions. Docstrings are
scanned behind a **four-file allowlist** — `fact_sources.py`, `knowledge_triples.py`,
`fact_lift.py`, `verification_ladder.py` — for the modules whose prose legitimately carries
the sentence. The allowlist's staleness guard checks only that an entry **still needs its
exemption**, never that its docstrings are *prose*. So a byte-exact docstring-template
producer planted inside allowlisted `fact_sources.py` runs the full 102-test Verify suite
**green**, reproduced end to end by T2.71's re-reviewer.

**Why it is a task and not a ledger sentence.** The implementer proposed recording it and
the re-reviewer escalated, on three grounds worth preserving. First, those four files are
exactly the modules the upcoming truth-core work edits — T2.72's MCP door, `fact_lift`,
T3.02's article claims — so the remaining hole runs through the **highest-traffic files for
this feature**, not through some quiet corner. Second, a cheap non-brittle closure was
verified to exist rather than assumed: none of the four reads `__doc__` or `getdoc` today,
so forbidding `__doc__` access inside allowlisted files costs **zero** false positives, and
a per-file fragment-count pin catches every full template because none of the four carries
`no known contradiction` in prose. Third, R1's charter is that a second producer **fails a
build** — a ledger sentence fails nothing.

The residual the fix *did* close is strictly wider than what remains: before it, a brand-new
file anywhere under `app/` could carry a producer; now it takes an edit to one of four named
files a reviewer is already reading. This task closes the rest.

**Done when:**
- [ ] A byte-exact docstring-template producer planted in any allowlisted file fails the
      build, proved by planting one and watching it fail
- [ ] The closure costs zero false positives, re-measured rather than inherited — the
      four-file list moves as the tree moves
- [ ] The guard's docstring states the residuals it still cannot see (multi-file scatter,
      true paraphrases sharing fewer than two fragments), so the next reader does not
      re-derive them

**Verify.** `cd backend && python -m pytest tests/test_layer_composition.py tests/test_fact_badge.py -q`

#### T2.78 — Delete `HybridSearchService.search_code`

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T2.66` · `Doc: 07 §2, invariant 14` · `Tag: rebuild` · `Gate: standing`

**What.** `HybridSearchService.search_code` carries the one-sided-failure defect T2.66 fixed
in its two live siblings, **and** swallows the exception to return `[]` — invariant 14's
exact forbidden shape, an empty list meaning "everything failed". It also carries a comment
contradicting `CLAUDE.md`'s record that code search does fuse.

It has **no callers**. T2.66's reviewer verified this independently rather than accepting the
lane's claim: both `POST /api/v1/code/search` and MCP `code_search` route through
`CodeQueryService`, and no other live reference exists under `backend/`. The recommended
disposition is deletion rather than repair — fixing dead code preserves a second
implementation that can drift from the real one, which is the condition `code_search` and
`code_blast_radius` were already in before T1.42c consolidated them.

**Why it gets its own review.** Deleting a service method on a no-callers argument is
precisely the claim worth re-checking, and the argument has to hold against dynamic
dispatch and string-keyed lookup, not just a grep for the name.

**Done when:**
- [ ] The no-callers claim is re-verified independently, including non-literal reference
      paths, and the evidence is recorded
- [ ] The method is deleted, or — if a caller is found — the invariant-14 swallow is fixed
      and the finding is re-filed
- [ ] The contradicting comment goes with it

**Verify.** `cd backend && python -m pytest tests/test_hybrid_search.py tests/test_code_query.py -q`

#### T2.79 — The harvest reproducibility test skips wherever its input is gitignored

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T2.54` · `Doc: 17 §9, §11` · `Tag: rebuild` · `Gate: G-D`

**What.** `test_harvest_l2_facts.py`'s reproducibility check skipped on a **gitignored** warm
cache, so it ran in the main checkout and skipped in every lane worktree and every fresh
clone — reporting success either way. The test that silently did not run is T2.54's harvest
reproducibility anchor: the byte-identical manifest that was its reviewer's central
evidence, for a gold set gating G-D and transitively G-C.

**How it surfaced is the point.** Not an audit — **two agents disagreed about a count**. The
controller published 459 from the main checkout; lane `ad` measured 458/1 and disputed
rather than matching.

**Done when:**
- [ ] The input is no longer gitignored, scoped to the entries the harvest actually reads
      rather than the whole shared cache
- [ ] Absence is a **hard failure**, not a skip
- [ ] A fresh clone with zero gitignored state runs it, proven rather than argued
- [ ] No conditional skips remain anywhere in `scripts/benchlib/`

**Verify.** `cd backend && python -m pytest scripts/benchlib/tests -q`

#### T2.80 — `POST /knowledge/search`, the REST twin doc 12 assigns and nobody owns

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.72` · `Doc: 12 §2, §3` · `Tag: target-new` · `Gate: standing`

**What.** Doc 12 §2 assigns the route and §3 pairs it with MCP `knowledge_search`. T2.72
built the agent half and filed the surface MCP-single-door because the alternatives were
worse, logging a Tier-2 amendment. **That filing is honest but weaker than it reads**:
`memory.search` and `code.search` are both two-door, so a cross-layer *ranked* answer is a
capability by this repo's own precedent — leaving `knowledge_search` the only ranked
retrieval in the system with no REST door.

Build the route through the **same** `knowledge_search_response()` serialiser T2.72
deliberately placed outside the tool for exactly this purpose, so the two doors spend one
function rather than reshaping the composition result twice.

**Two Important findings from T2.72's review must be settled here, not deferred again:**

1. `api/mcp/server.py` catches a bare `RuntimeError`, and `derive_rerank_scores` raises the
   same type — so a future reranker defect over a healthy vault is served as "unavailable".
   That is the failed-versus-empty conflation T2.66 spent a whole task eliminating. Needs a
   typed exception on the composition.
2. `envelope.reranked` is permanently false because the reranker is a **door-side
   constructor argument**. The moment this route passes one, the two doors **rank
   differently** while every row-shape parity test stays green — those tests compare shape,
   not order.

**Done when:**
- [ ] The route exists at doc 12 §2's path and both doors spend one serialiser
- [ ] The composition raises a typed exception, and an empty vault is distinguishable from a
      failed rerank at both doors
- [ ] The two doors provably rank the **same**, by a test that compares order and not only
      shape
- [ ] `docs/two-door-parity.md` moves the surface to two-door

**Verify.** `cd backend && python -m pytest tests/test_door_parity.py tests/test_knowledge_search.py -q`

#### T2.81 — The empty-text raise has a live route and an unguarded caller

`Model: Opus 5` · `Effort: high` · `Size: S` · `Depends: T2.69` · `Doc: 07 §4, invariant 14` · `Tag: rebuild` · `Gate: standing`

**What.** T2.69's review ruled the reranker's empty-text raise correct and its disclosure
incomplete. The live half reproduced in three executed links: the wire returned 200 with
`{"content":""}`, the pipeline wrote `payload->>'content' = ''`, and the real
`RerankerService` raise escaped `MemoryService._search_memories_paginated_traced`
uncaught.

**The fix's own prose then turned out to be false and to hide a 500.** `MemoryUpdate`'s
comment claimed `None` means "not being updated", but `model_dump(exclude_unset=True)`
yields `{'content': None}` and a live `PUT` with `{"content": null}` raised uncaught — on
the exact door the task hardened, under prose actively denying it. It was never only
`content`: `importance`, `metadata`, `is_archived`, `project` and `status` are all NOT NULL
columns reachable through the model and all failed identically.

**Done when:**
- [ ] The empty-text path is guarded at its live caller, proven by a wire-level test
- [ ] Every NOT NULL column reachable through `MemoryUpdate` refuses `null` with a **422 at
      validation**, not a service-side drop — `null` is a real instruction for the nullable
      columns (`memory_type`, `expires_at`), so a blanket drop would either break legitimate
      clearing or swallow an incoherent request
- [ ] The prose that denied the failure is corrected in the same change

**Verify.** `cd backend && python -m pytest tests/test_empty_content_update.py tests/test_reranker.py -q`

*(Verify field corrected 2026-08-04, Tier-1 amendment: the minted text named
`tests/test_memory_update_nulls.py`, which does not exist. The task's own commits
(`bac41ea`, `deff41d`) put all 374 added lines of coverage in
`tests/test_empty_content_update.py`.)*

#### T2.82 — `prune-cache` drops every live entity-embedding cache under the sentinel

`Model: Opus 5` · `Effort: high` · `Size: S` · `Depends: T1.50, T2.68` · `Doc: 04 §6, invariant 14` · `Tag: rebuild` · `Gate: standing`

**What.** `POST /reembed/prune-cache` under the `|0` fingerprint sentinel **drops every live
`entity_embedding_cache__*` child table** — the route performs no existence probe.
Pre-existing and **destructive** rather than merely inert, which makes it the most dangerous
member of the sentinel family: the other two sites returned nothing, this one deletes.

T2.68's shipped `llm.py` docstring now describes `ReembedService` as safe to call bare,
which is false for this route, so that claim must be corrected in the same change.

**Done when:**
- [ ] A cache child may only be dropped when its fingerprint is **resolved and registered** —
      treat the deletion path as the invariant-bearing part
- [ ] The sentinel drops nothing, proven by a test that fails if the guard is removed
- [ ] The false safety claim in `llm.py` goes with it

**Verify.** `cd backend && python -m pytest tests/test_reembed_prune_cache_guard.py tests/test_maintenance_journaling.py -q`
*(Corrected 2026-08-05: the minted field named `tests/test_reembed.py`, which has never
existed in this repository — `pytest` exits `ERROR: file or directory not found` rather
than failing, so the box was uncheckable rather than checked. Flagged in the 2026-08-04
Tier-2 audit row and left uncorrected there because the row was claimed by another lane.)*

#### T2.83 — A wrong non-zero `dimensions` reproduces the silent-empty-forever symptom

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T1.50, T2.68` · `Doc: 04 §6` · `Tag: rebuild` · `Gate: standing`

**What.** T2.68 closed the `|0` sentinel, but a **wrong non-zero** `dimensions` — 768
configured while the model emits 1024 — reproduces the original symptom at both read
surfaces, and that fix does not cover it. The plan never owned this case: the task was
written around the sentinel because that is the shape someone noticed. The real class is
**"the configured fingerprint does not match the one an embed would produce"**.

**The asymmetry is what makes it invisible.** Retrieval derives its fingerprint from
`embed()`'s **return value**, so it is structurally immune and keeps working while these
surfaces silently empty. Nothing in a normal session would suggest a misconfiguration.

**Done when:**
- [ ] Both read surfaces refuse, or report honestly, when the configured fingerprint cannot
      be the one an embed would produce — never a silent empty
- [ ] The guard is keyed on the class, not on the `|0` shape, so a third wrong-fingerprint
      form does not need a fourth task
- [ ] A test drives a configured/actual dimension mismatch and fails if the guard is removed

**Verify.** `cd backend && python -m pytest tests/test_vectors_route.py tests/test_api/test_graph.py -q`

*(Verify field corrected 2026-08-04, Tier-1 amendment: the minted text named
`tests/test_reembed.py` and `tests/test_embedder_registry.py`, neither of which
exists anywhere in the repo. The guard lives in
`PostgresVectorRepository.resolve_read_fingerprint` and is exercised through the
two read surfaces, so those are the files that actually cover it.)*

#### T2.84 — The fact-keyed retrieval-heat counter

`Model: Sonnet 5` · `Effort: high` · `Size: M` · `Depends: T2.65` · `Doc: 08 §6` · `Tag: target-new` · `Gate: G-C`

**What.** T2.65 **settled the decision and could not execute it**: a real fact-keyed counter
needs its own table (`fact_id REFERENCES knowledge_triples(id)`), and no lane held
baseline-schema clearance that round, so it held the memory-bridged proxy as an *interim*
position and recorded a ready-to-execute design in the amendment log rather than leaving it
implicit.

**The gap is live, not latent.** `FactsChannel` is unconditional traffic today through
`LayerCompositionService.search`, behind the `knowledge_search` MCP tool T2.72 landed the
same day — no flag gates it, and nothing analogous to `access_stats.spawn_record_access`
sits on the path. Doc 08 §6's consequence ranking is degrading toward its salience arm right
now.

**Needs a schema window.** Schema changes serialise through one owner per epic (CLAUDE.md),
so this cannot share a round with another baseline edit.

**Done when:**
- [ ] Retrieval heat is counted per **fact**, on its own table, not bridged through memories
- [ ] T2.65's pinning test flips: fifty real searches no longer leave the frequency component
      at zero
- [ ] `FACT_KEYED_COUNTER_STATUS` / `RETRIEVAL_HEAT_STATUS` are **retired** — a marker that
      outlives its condition is the stale-premise defect T2.65 was fixing
- [ ] Counting stays off the hot path's critical section, as `access_stats` does

**Verify.** `cd backend && python -m pytest tests/test_facts_channel.py tests/test_access_stats.py -q`

#### T2.85 — Self-expiring dated facts: rule the belief-window contradiction, then build it

`Model: Fable 5` · `Effort: xhigh` · `Size: M` · `Depends: T2.01` · `Doc: 08 §2.3, §3.1, §9` · `Tag: activation` · `Gate: G-C`

**Blocked on a Tier-3 ruling — do not start.** Split out of T2.34 on 2026-08-04. Fable
tier and `xhigh` because the deliverable is a ruling between two design-doc sections
before it is any code, and the wrong ruling is silent.

**What the contradiction is.** Doc 08 §9 says a fact carrying a stated future expiry gets
its belief window **"pre-closed at that date"**, which reads as writing the future date
into `invalid_at` at population. Doc 08 §3.1's state machine says `invalid_at` is set when
**a newer belief arrives** (`open --> window_closed`) and routes a stated expiry down the
other edge entirely (`open --> expired`, i.e. `expired_at`). Both cannot hold.

**Why the literal §9 reading is destructive rather than merely ambiguous.**
`0001_baseline.py` makes **four** indexes partial on `expired_at IS NULL AND invalid_at IS
NULL` — the unique `ux_knowledge_triples_open` plus doc 07 §2's three fact-channel
retrieval indexes. A future `invalid_at` written at population therefore (a) drops the
fact out of the retrieval channel's scope **immediately**, years before its stated expiry,
and (b) frees the unique slot, so a second currently-open belief on the same `triple_key`
can be written beside it. Both are silent. Note `as_of` already implements the correct
half-open window (`valid_at <= t < invalid_at`), so the *model* is right and it is the
shipped "currently open" predicate that assumes `invalid_at` is only ever set in the past.

**The three candidate rulings**, none of which a lane may pick unilaterally:

1. Make "currently open" time-aware. Impossible as a partial index — `now()` is not
   IMMUTABLE — so it means reworking the unique constraint and all three retrieval indexes
   and relaxing invariant 8's temporal analogue: a baseline schema change, serialising
   through one owner per epic.
2. Add a `stated_expiry` column; the recompute arm writes `expired_at` when it passes. A
   schema amendment §9 does not list (its only named amendment is `demotion_pending_since`).
3. No column: the recompute arm re-derives the stated expiry deterministically from the
   fact text each cycle and sets `expired_at` once past. Consistent with both sections and
   with §9's "no LLM, no separate job", at the cost of re-parsing.

**Done when:**
- [ ] The ruling is recorded against doc 08 (both sections made to agree), not just in code
- [ ] A dated fact stops being served **at** its stated expiry and not before, proven by a
      test that fails under the literal §9 reading
- [ ] The row is never deleted — invalidate-not-delete, retained as history
- [ ] No code path deletes from `knowledge_triples`, held by a source scan rather than by
      review (doc 08 §5: the facts table needs no delete job at all, and applying T1.37's
      sweep to it would destroy the history the bi-temporal model exists to keep)

**Verify.** `cd backend && python -m pytest tests/test_self_expiring_facts.py -q`

## Amendment log

| Date | Task | Tier | Change | Why |
|---|---|---|---|---|
| 2026-08-06 | T2.28, T2.04 | 2 | **The veto's admissible-consumer rule widens from "the ladder" to "the modules that decide a verification-axis write", and `fact_lift.py` is admitted as the second and only other.** T2.28's N-1 fix — a controller-ruled `adjudicate_contradiction` consult before restoring a born rung — made `fact_lift` the second module to reach the veto, and T2.04's one-entry allowlist failed the floor over it. The executor did not widen it quietly: it flagged the entry for re-ruling and wrote the warrant into the allowlist, which now states the *rule* rather than an exception. **Accepted** | The consult can only **refuse** a restore — never grant a rung, never open a dispute, never write — and it reads a verdict already journalled by the scan rather than adjudicating afresh, so no judge call and no model call enter the path. Invariant 15 is untouched rather than traded: `fact_lift` is a dream-job body already out of capture's and retrieval's reach. Tier 2 rather than Tier 3 because **no design doc says only the ladder may consult the veto** — doc 08 §4.2 fixes that adjudication happens at the fact layer through the qualified judge, which this consult does not do; it reads that judge's recorded output to decline a write. The generalisation is also the honest one: the property worth protecting was never "one module" but "no module that could dispute inline", and the rewritten comment says so. Drilled three ways, including removing the new entry (fails, so it is load-bearing) and planting the import in a third real app file (fails, naming it). Recorded because a rule's *scope* changed, which reaches past the task that changed it |
| 2026-08-06 | T2.100 | 2 | **Ruling narrowed the same day it was made: a journal payload embedded in a claim surface inherits the claim surface's contract, not the journal's.** T2.100's review measured the `verified` payloads served inside `GET /knowledge/facts/{id}`'s `ladder` array and `GET /review-queue/facts`'s `evidence` array — each body carrying `after.verification_status: "corroborated"` beside a **suppressed label on the same row**. The earlier ruling accepted that exposure on `/events` and named only `/events`, because that is the door AF1 presented. **It does not extend to these two**, and the fix round closes them | The distinction is the whole basis of the original ruling and I stated it there: a journal row records what the ladder computed, a claim surface asserts what is true, and a reader of `/events` is reading a computation log *by construction of which door they opened*. That argument is about the **door**, not about the payload — so it evaporates the moment the same bytes are embedded in a response whose purpose is to state a fact's status. A fact-detail body that suppresses the rung in `verification_status` and hands it back two keys later in `ladder` has not gated anything; it has moved the answer. Worth recording as the shape rather than the instance: **an accepted residue is scoped to the surface it was accepted on**, and every later surface that embeds it re-opens the question rather than inheriting the answer. Also recorded: the ruling's own test is weaker than the ruling on the "authenticated operator" qualifier (auth is unasserted) and narrower than reality on the reader set — it pinned one door of three |
| 2026-08-06 | T2.95, T2.99, T2.100 | 2 | **Ruled: the audit journal keeps serving the rung, and the M1 safety sentence narrows to say so.** `GET /api/v1/events?object_type=fact&event_type=verified` serves `payload` verbatim under the same `require_auth` as the facts door, and every ladder transition journals `before`/`after` `verification_status` — so for any fact that has ever transitioned, the withheld rung is **directly readable, without the subtraction** the two closed oracles needed. Accepted rather than closed. What does not stand is the *declaration*: `claim_gates.ungated_status` defines wrapping as a claim that the value "reaches no reader", and the journal sites hand it to an authenticated one. **T2.100** splits the marker so the audit substrate declares itself as such | Accepted for three reasons, and the first is decisive: **G-C's own false-promotion audit reads this journal.** Narrowing the substrate to protect the gate would degrade the evidence the gate is measured with, which is self-defeating. Second, T2.59 settled the analogous content-residue question the same way six hours earlier — accept and document, never an in-app journal-rewriting path, because "make this never have happened" one bug away from the audit substrate is the worse failure. Third, a journal row and a claim surface are different speech acts: one records what the ladder computed, the other asserts what is true, and a reader of `/events` is reading a computation log by construction. **The correction that matters more than the ruling**: the M1 split's sentence has been stated all day as *no serving path can reach a label whose evidence does not exist*, and that is false as written. The honest form is *no **claim surface** serves an unbacked label; the audit journal records the ladder's own transitions and an authenticated operator can read them.* A false declaration is worse than an undeclared site — the scan trusts it and so does the next reader — which is why the marker is a fix and the exposure is a ruling |
| 2026-08-06 | T2.11 | 2 | **Ruled: a scan-applied dispute is permanent, and that is accepted rather than fixed.** T2.11's review established that once the ladder applies a scan dispute, doc 08 §5.3's own restriction to servable facts *not already disputed* means no later pass can re-adjudicate it — so a judge false positive whose guards keep holding is a permanent manufactured dispute, and the only exits are guard-lapse or human ratification. The exclusion stays; what changes is the detector docstring, which claimed a later clean pass ends the dispute and is false outside the pre-application race window | Accepted because every alternative is worse where it matters. The exclusion is what stops the scan re-paying LLM cost on facts it has already ruled on; a disputed fact is **served labelled with both sides** rather than dropped or hidden (doc 08 §6, invariant 14), so nothing is silently lost; and human ratification is a designed exit, not an accident — `confirmed` is the one rung that never depended on the automatic ladder. The precision-first asymmetry already accepts a bounded false-positive rate behind the 0.95 bar, and re-adjudicating disputes on a schedule would spend model budget re-litigating the judge's own verdicts, which is the tune-against-your-own-output loop this epic has twice been warned off. **The docstring is the real defect here**: a comment describing a recovery path the code does not have is worse than no comment, because the next reader budgets for self-healing that will not arrive. Logged Tier 2 rather than Tier 1 because it is a standing property of the truth layer that a doc-08 reader would want to know, not a task-local correction |
| 2026-08-06 | T2.11, T2.98 | 2 | **T2.98 minted, and `CLAUDE.md`'s dream-job paragraph corrected.** T2.11's report records that `ix_knowledge_triples_live` leads on `subject_name`, so the object half of doc 08 §5.3's "index lookup" scans — T2.98 owns widening it, deliberately not T2.11, whose schema mandate was `pg_trgm` alone. Separately, the baseline's Jobs section said each dream-job body "is a `PlaceholderJobRunner` until its owning task lands", which had been stale through **four** landings and read as a claim the whole family was inert; five of six now have real runners and only `article_synthesis` remains. The frontend event-taxonomy map gained its missing `contradiction_scanned` entry in the same edit | Both surfaced by T2.11's executor and flagged rather than taken unilaterally, which was the right call on a shared file mid-round. The `CLAUDE.md` drift is the more interesting of the two: the sentence was never edited because it was written as a *rule* ("until its owning task lands") rather than a *state*, so every landing left it technically defensible and cumulatively misleading. A reader deciding whether the consolidation family does anything today would have got the wrong answer from the baseline document. Recorded as a shape to watch — a rule-shaped sentence about a changing state ages without ever becoming false enough to trip anyone into fixing it |
| 2026-08-06 | T2.27, T2.96, T2.97 | 2 | **Two tasks minted from T2.27's completion report, both gaps the plan did not have a row for.** **T2.96** — the deriver has no caller: `assert_repo_graph` / `derive_assertions` are reachable from nothing in `backend/app` (controller-confirmed in the tree), so `repo_ids[]` has a writer that production never runs. **T2.97** — a repo-minted entity carries no embedding, so Phase-4's ANN probe cannot see it and anchoring degrades to exact `(name, entity_type)` match: `postgres` from code and `postgresql` from a memory stay two nodes where the memory path merges them. The schema inventory gains a plain statement that no scheduled path fills the arrays yet | T2.27's executor reported both accurately and judged that neither was an amendment. The controller disagrees on both, for the same reason each time: a stated deliverable is narrower than the doc claims it is, and **no row owns the gap**, which is the Tier-2 definition. Doc 10 §6 sells the bridge specifically on anchoring — *"the anchoring benefit that makes the bridge worth building"* — so exact-match-only anchoring is the same shape as T2.16 shipping two of three signals, which was logged Tier 2 on the same reasoning. The wiring gap matters for a second reason: **the inert label on both arrays retired in this task**, and invariant 23 exists to stop scaffolding being claimed as substrate. A writer existing is a fair basis for retiring "inert", but only if the inventory says plainly that nothing schedules it — otherwise the next reader of that table concludes the bridge is live. Worth recording that T2.97's root cause is a **misread of T2.27's own constraint**: "LLM-free" forbids an extraction call, and an embedder call is not one; reading the clause as forbidding both is what left the gap unclosed rather than merely deferred |
| 2026-08-06 | T2.95, T2.28 | 2 | **T2.95 reopened: the Fable review refutes the gate, and T2.28 gains a hard hold on the repair.** Three of five Done-when clauses do not hold, measured rather than argued — `chat.py:401` and `review_queue.py:336` serve the raw promoted status off the ungated column instead of the gated `row.labels`, `label_suppressed` is dropped by `FactListItem` / `FactDetailResponse` / `ComposedRowLabels` so a suppressed label and an earned `candidate` are byte-identical on the wire, and both scans enumerate known modules rather than quantifying over serving paths (a new bypassing module and a new bypassing route each left the suite green). Two further defects were fixed inside the review: `gate_eligible` opened on any truthy JSON value, so the strings `"INTERIM"` and `"false"` both opened it — the module's own named failure mode — and a corrupt record raised `UnicodeDecodeError` through the fact read path rather than failing closed. Status `done` → `wip`; six scoped repair items in `reviews/2026-08-06-t2.95-gate-attack.md` | **This is the task the M1 split rests on, so its being wrong is the one defect in this epic that invalidates a scheduling decision rather than a feature.** The split's safety sentence is *no serving path can reach a label whose evidence does not exist*; it is false today on two doors, so every task merged under the split's licence inherits the doubt until the repair lands. Tier 2 rather than Tier 3 deliberately: **nothing here indicts the design.** Enforcement at the producer is right, and the review says so explicitly — the defects are that two consumers dodge the producer, one attribute duplicates what the labels already carry, three schemas drop a field, and two scans enumerate instead of quantify. No design doc is wrong, no gate bar moves, no honesty tag is reclassified. What it does change beyond one task is the **T2.28 edge**, which is why it is logged rather than merely fixed. Also worth recording as a process finding: T2.95 reached `done` with its mandatory Fable review still owed, and the review is what caught this — the runbook §6 rule earned its cost in a single sitting |
| 2026-08-06 | T2.11, T2.27, T2.28 | 2 | **A gate blocks what it certifies, not what merely precedes it.** Implementation lands **inert**; only the productive or serving path waits for evidence. This is the repo's own standing pattern, applied more consistently — T0.13's inert partitions, T2.08's `PlaceholderJobRunner` family, T2.32/T2.50's build-versus-judge split, and invariant 23's scaffolding-not-substrate. Dependency edges re-pointed off the evidence runs accordingly | Controller decision: the plan had implementation work queued behind **evaluation artifacts it does not depend on** — an SDK scaffold and a browser-extension scaffold waited on a groundedness evidence run, and a document parser waited on a faithfulness metric. That is phase coupling, not artifact coupling, and it stalls build work on datasets that do not exist yet. Evaluation is deferred to an independent measurement phase after the implementation is complete, where it can be run against the whole system rather than against fixtures. **What was deliberately left gated**: T2.28 (mints facts born `corroborated` — the exact harm G-C names), T3.02 (productive article runs — where a grounded claim first reaches a reader), T3.03 (the groundedness consumer). Freeing those would put unverified assertions in front of users, which is a different thing from unblocking a scaffold. |
| 2026-08-06 | T2.31, T2.35 | 2 | **Both activation tasks close as `done` with their arms at 0.0, measurement deferred to whole-system.** Controller decision: neither arm can be honestly measured on the bench today — T2.35 has no context-bearing corpus (so `match_context` returns neutral at every magnitude) and T2.31 has no realistic heat prior (any bench-invented distribution is gold-correlated or gold-blind). Rather than author a corpus and a workload to measure a synthetic world, both are recorded as results under the standing gate and re-measured on the complete system after the implementation phase | The standing gate already provides for exactly this — *"an arm that cannot show its number stays at weight 0, and that outcome is recorded here as a result, not a failure"* — and the T2.50 judge set the precedent hours earlier by closing community injection the same way, naming it *"the same honest floor T2.35's context axis was left at"*. The alternative on the table was ~1.5 days of corpus and workload authoring whose only output would be a number about fixtures. **Neither task had code left to write**: T1.34 shipped the context mechanism and T2.31's signal was wired 2026-08-06, so the corpus was the deliverable rather than its test — which is what made deferral the cheaper *and* more honest option rather than a shortcut. Standing gates apply per activation, so nothing is foreclosed: when real telemetry and real contexts exist, activation is a run plus a ledger row. **What is accepted deliberately**: the `applies_when` boost and the heat/recency priors ship off and stay off until then |
| 2026-08-06 | T2.94, T2.50, T2.49 | 2 | **`T2.94` minted: the dual-level channel has no owner.** Doc 07 §4 names three graph signals. T2.32 shipped PPR's producer; T2.49 shipped the `relation_embeddings` vectors and their refresh job. Nothing reads those vectors, so `w_dual` and `dual_level_enabled` are flags over a channel that does not exist — and **T2.50 depends on it without saying so**, because its Done-when measures `dual_level` as if a reader were already there. T2.94 owns the reader and carries doc 07 §11's global-arm scoping rule, the one channel with no project column of its own | Found by executing the two tasks rather than by reading the graph: T2.49's Done-when says "first writer to one of the two inert partition templates", which is true and complete for a *writer*, and the epic contained no row whose Done-when was the corresponding reader. The same shape as the four `Depends`-vs-prose gaps already logged here — a constraint recorded in one task's prose and absent from the edge the scheduler consults. Now enforced in code as well as prose: `arm_ablation.resolve_ablatable` returns `w_dual` blocked, so an ablation refuses with the reason instead of reporting the exact-zero delta that reads like a measured "no win" |
| 2026-08-05 | T2.16 | 2 | **The empty exclusive-relation-family list is ratified on the Fable review's recommendation, so doc 08 §5.5's three signals are realized as TWO in v1 — overlap and proximity, both to `RELATES_TO`.** The executor could defend no member and declined to invent one; the reviewer then checked **every** `RELATIONSHIP_TYPES` member against `taxonomy.py` and `extraction_clean.py` independently and confirmed it: `DEPLOYED_ON` absorbs `RUNS_ON`/`LOCATED_IN` plus seven rescue connectors including a bare `"on"` at 0.6 confidence, `HAPPENED_ON` absorbs `VISITED`/`LIVES_IN`, and even `EXTENDS` — the closest thing to a missed candidate — is plural under multiple inheritance. **A stored `rel_type` simply does not determine single-valuedness in this taxonomy, because normalisation collapses plural historical names into apparently-singular types.** The contradiction arm is built, wired and tested through an injected family, so ratifying a list later is a one-line edit to `EXCLUSIVE_RELATION_FAMILIES`, not a re-execution. One candidate survived and is **recorded without being adopted**: `REPLACES`-family antisymmetry (A asserts `X REPLACES Y` while B asserts `Y REPLACES X`) — deterministic, no plural-fact escape, and it flags the mutual-flip pathology the supersession ordering guard blocks; it is a different shape from D4 and belongs to its own plan round | This is the **second** scope reduction on one doc sentence in one day — §5.5 said five types from three signals, and v1 ships three types from two signals. Recorded prominently for that reason: a reader auditing §5.5 against the tree will otherwise conclude the pass is half-built, when in fact each reduction was forced by a measured property of the code rather than chosen for convenience. The pattern underneath both is worth naming: §5.5 was written against an idealised taxonomy in which a relation type carries its own arity, and the shipped taxonomy deliberately does not — `LEGACY_RELATION_TYPE_MAP` and the rescue connectors exist precisely to funnel many surface forms into few stored types, which is right for extraction recall and fatal for inferring exclusivity. **The owner may still overturn this**; the cost of doing so is populating one constant, not rebuilding the arm |
| 2026-08-05 | T2.57, T2.52 | 1 | **Doc 17 §5.2's "at least half lexically disjoint" is read as half of the *contradiction* pairs, not half of all pairs — 12 of 22 positives, not 25 of 50.** The argument, recorded in the gold's own `LABELLING.md` where a reader of the data meets it: the disjoint slice exists to power a **recall** measurement, only positives enter recall, and a disjoint *negative* contributes nothing to it — so the whole-set reading would spend half the set on pairs that cannot move the number while crowding out the three negative classes T2.57's Done-when explicitly requires. Note §5.2 calls this a "recommended starting shape", not a bar, so this is a reasoned deviation from a recommendation rather than a missed requirement. **The consequence lands on T2.52**: 12 disjoint positives give the miss rate a granularity of 1/12 ≈ 8.3%, so §5.2's recommended 20% writer-trigger bar is breached at 3 misses | Logged here as well as in `LABELLING.md` because the two readers are different people with different questions. A reader of the gold needs to know how it was labelled; a reader scheduling **T2.52** needs to know the measurement it is about to take is coarse — 3 misses versus 2 is the whole decision on whether T2.33's writer ships, and that granularity is a property of this gold's composition rather than of T2.52's own method. The set is explicitly designed to grow from real adjudicated disputes, so the granularity improves on its own; what must not happen is T2.52 reporting a miss rate as if it were finer than the gold can express |
| 2026-08-05 | T2.31, T2.84 | 2 | **`T2.31` gains `Depends: T2.84`, and the schema window T2.84 has been waiting for is granted to it.** `w_heat`'s input is retrieval heat; T2.65 settled that fact-level heat has no counter and that the memory-bridged proxy stands only as an interim with a stated error bound. Activating `w_heat` against that proxy would put a number in the gate ledger's arm activation log measured on a substrate already scheduled for replacement — and that log is the one artifact whose numbers are supposed to survive being re-read a year later. So the sequencing is now explicit in the graph rather than left to whoever picks the tasks up. Separately, T2.84's own blocker was never technical: it needed a **schema window**, because a fact-keyed counter needs its own table and baseline edits serialise through one owner per epic. No other lane is touching the baseline this round, so the window is granted and T2.84 is dispatched | Filed because the two halves of this row fail differently if left alone. The missing dependency fails **silently and durably**: T2.31 would have run green, produced a real number, and written it into the ledger, where nothing downstream would ever mark it as measured against an interim substrate — the same stale-premise shape T2.65 was itself minted to fix, one layer up. The schema window is the opposite: it fails **loudly and immediately**, because two lanes editing `0001_baseline.py` conflict on every line. Recording the grant is what makes the serialisation auditable — a reader should be able to see which round held the window and why, rather than inferring it from commit order |
| 2026-08-05 | T2.16 | 2 | **T2.16 shipped with D4's exclusive-relation-family list EMPTY, so the pass derives TWO signals (entity overlap, embedding proximity) rather than three; the contradiction arm is built, wired and tested but cannot fire until a list is ratified.** The list was constructed as the plan's D4 describes and no member of `RELATIONSHIP_TYPES` survived: every type that reads single-valued in isolation is also the normalisation target of a plural historical name, so a stored `rel_type` does not determine single-valuedness. `DEPLOYED_ON` absorbs `RUNS_ON` and `LOCATED_IN` through `LEGACY_RELATION_TYPE_MAP` *and* collects seven `_RESCUE_CONNECTORS` phrases including a bare `"on"` at 0.6 confidence, so "postgres DEPLOYED_ON linux" and "postgres DEPLOYED_ON docker" are both true; `HAPPENED_ON` absorbs `VISITED` and `LIVES_IN`; the rest (`USES`, `DEPENDS_ON`, `HAS_PART`, `IMPLEMENTS`, `EXTENDS`, `CAUSES`, `AUTHORED_BY`, `MENTIONS`, `CITES`, `INSPIRED_BY`, `IS_A`, `REPLACES`, `IMPROVES_ON`) are plural by construction, and `RELATED_TO` is the normaliser's own fallback. `EXCLUSIVE_RELATION_FAMILIES` in `app/taxonomy.py` carries the reasoning beside the constant, and the arm is driven through an injected family in `tests/test_memory_relation_derivation.py` so ratifying a list is a one-line edit rather than a re-execution | Tier 2 because it narrows what doc 08 §5.5 delivers a second time — after the three-of-five row above, this is three-of-five signals realised as **two**-of-three. Both the plan's D4 and the dispatch brief make this the controller's call rather than the executor's, and the executor declined to invent a list to avoid it: a derived `CONTRADICTS` suppresses the weaker `RELATES_TO` under D3 *and* feeds the fact-level dispute surface while T2.11's judge is still unqualified, so a loose family manufactures false disputes and erases true edges at the same time. One candidate survived contact and is recorded in the plan's O3 without being adopted — `REPLACES`-family **antisymmetry** (A asserts `X REPLACES Y` while B asserts `Y REPLACES X`), which is deterministic with no plural-fact escape and flags the mutual-flip pathology the supersession ordering amendment blocks — but it is a different shape from D4's "two distinct targets under one family", so adopting it amends the reviewed plan rather than ratifying it |
| 2026-08-05 | T2.16 | 1 | **Nine execution amendments folded into the plan's new §7a**, the two load-bearing ones being: (E1) the pass lives in `memory_dream.py` rather than the new module §5 implies, because `dream_job_implementation_modules()` derives invariant 15's forbidden set from `dream_jobs.py`'s own imports and is deliberately ONE HOP — a new sibling under `app/services/` imported only by `memory_dream` would sit outside the guard and be freely reachable from capture and retrieval, and T2.67's contract forbids widening the derivation to a transitive walk to fix that; and (E4) the strip window is the seed slice bounded above by the last decided pair key, not "the pairs this run re-evaluated" read literally — a pair whose signal has vanished produces no candidate, so the literal reading makes the strip a permanent no-op and the graph grows forever. The remaining seven cover integer-percent thresholds (`FieldDescriptor.default` is typed `int`), the hot-entity cap as a fifth config field, `candidates_truncated` being a lower bound rather than a census, two moved assertions in T2.12's test file, the journal reusing `DETECTOR = "dedup"` so four consumers need no widening, and the strip journalling nothing | Tier 1: each is task-local reality found during execution, and none changes what the task delivers. Logged rather than absorbed silently because the plan passed a Fable review, so an undocumented divergence makes that review describe a tree that no longer exists |
| 2026-08-05 | T2.16, T2.13 | 2 | **Doc 08 §5.5's "derives the five" is realized as three-of-five in v1, ruled by the Fable plan review and logged here as that review required; and T2.16 now carries a change to T2.13's undo module.** (1) `DEPENDS_ON` and `FOLLOWS` are shipped **stored-but-underived**: neither entity overlap, embedding proximity nor contradiction carries the information those two assert, and deriving `FOLLOWS` from `created_at` would assert narrative succession from *typing order*. Cutting them from the vocabulary was considered and rejected — unlike `DERIVED_FROM` they have plausible future writers, and cutting costs taxonomy churn twice while leaving them inert forecloses nothing. **The cut-or-keep question is parked as a standing item, not closed.** (2) The plan's undo integration reaches into `dream_undo`: `_invert_associate` hardcodes `NEAR_DUPLICATE_PASS` in its restore arm, clear arm and currency CAS, so a second pass writing edges would have its undo silently invert **T2.12's** block while reporting success. The journal payload gains a `pass_key` and those three sites generalise to read it, defaulting to the near-duplicate key for existing rows | Tier 2 because it narrows what a design-doc section delivers and because it modifies another task's shipped module. The §5.5 realization is recorded rather than left implicit for the reason this epic keeps re-learning: a doc sentence that says "five" and a tree that derives three is exactly the prose-versus-graph gap that produced T2.36a, T2.39a, T2.91 and T2.93. A reader auditing §5.5 against the code should find this row rather than conclude the pass is incomplete. The undo half is worth its own emphasis: it was invisible from T2.16's own Done-when, which says nothing about undo, and would have surfaced as cross-pass corruption under a green suite — the review caught it from the plan text alone, before any code existed to debug |
| 2026-08-05 | T2.11, T2.54 | 2 | **T2.11's block note was wrong on its central point: no lawful qualification run has ever happened, so the judge did not fail a gate.** The Fable analysis (`analyses/2026-08-05-t2.11-judge-bar.md`) found the 0.8182 was branded INTERIM by its own artifact and measured on an ineligible 41-pair gold on which **the 0.95 bar degenerates to zero-false-positives** — one FP lands at 10/11 = 0.909, so no achievable value exists between 0.909 and 1.0. The blocking artifact is the qualification record, whose eligibility lock now fails on exactly one condition: 2 of 241 pairs still carry `label_source: "author"`. **T2.54's owner sitting therefore holds two gates, not one**, and its marginal cost to T2.11 is zero additional owner work because that sitting is already mandatory for G-D | Filed because it changes the scheduling picture more than any single task here. Read the old way, T2.11 was a failed measurement needing a better judge — open-ended work behind a hard bar. Read correctly, it is one afternoon of adjudication away from being *runnable*, and G-C's critical path runs through the owner's calendar rather than through engineering. The bar itself is right and stands; the analysis explicitly declines to widen it, and records instead that the gold it was measured against could not express it. Worth noting the failure mode: an INTERIM artifact was read as a verdict for a full day and propagated into a `blocked` row, which is how a provisional number becomes a scheduling fact |
| 2026-08-05 | T2.85 | 1 | **Commit-hygiene collision, recorded rather than rewritten: the T2.85 analysis rode into `e68a739e` (a `Task: T2.65` merge) instead of its own commit.** A `git add -A` in the controller's merge swept the analysing agent's then-untracked file while that agent was blocked on the repository's index lock. The file is byte-identical to what its author intended and is fully in history; rewriting a shared merge commit to relabel it would cost more than the mislabelling does | The controller caused it and is recording it, not the agent who reported it. The lesson is narrow and worth keeping: `git add -A` in a worktree where a concurrent agent is writing is not a safe staging command, and the collision is silent — the merge succeeded, the floor stayed green, and only the agent's own final check noticed its file had been committed under someone else's task id. Prefer explicit paths when any other actor is live in the same tree |
| 2026-08-05 | T2.82 | 1 | **Recovered from a stalled lane; `Verify` corrected; an unreverted mutation drill found in that lane's working tree and preserved rather than merged.** Lane `ah` had landed all three Done-when clauses across three commits and then stopped, leaving its worktree carrying an *uncommitted deletion of the registry arm its own commits had just added*. That is the shape of a drill whose revert never ran — the deletion contradicts the surrounding docstring ("a drop that guesses wrong destroys tables"), and the two commits above it are literally "isolate the prune guard's first arm" and "cover the prune guard's second arm". It was stashed in that lane, not merged and not discarded, and the committed state was restored before the merge. Both arms were then re-drilled independently at the epic branch: removing the registry arm reds `test_a_retired_registry_row_refuses_and_spares_the_live_sibling`, removing the table-existence arm reds `test_a_registered_fingerprint_whose_cache_child_is_gone_refuses`, and neither drill reds the other's test — the arms are separately load-bearing, which is why one test could not have covered both. `Verify` also named `tests/test_reembed.py`, which has never existed | Recorded rather than quietly merged because two different failure modes nearly met here. A path-wide `git checkout --` in that worktree would have looked like tidying and would have silently reverted nothing of value — but the *opposite* mistake, merging the dirty tree, would have shipped the destructive defect back in under a commit message claiming to fix it, with a green suite either way except for the one test that catches that exact arm. `CLAUDE.md` already warns that a drill's revert is where work disappears; this is the same hazard from the other side, where a drill's *non*-revert is where a fix disappears. The `Verify` correction is the fourth instance of the 2026-08-04 back-fill audit's finding, and the row that audit wrote predicted this exact file |
| 2026-08-05 | T2.93, T2.19 | 2 | **The invariant-15 report scan admitted no caller at all, which made this task's own wiring unimplementable; it now admits exactly one file and four symbols, and the guarantee is proven in two steps instead of one.** `test_no_app_code_reaches_report_generation` asserted that *nothing* under `app/` reaches `memory_community_reports` beyond five pure projection symbols. But report generation needs a live caller or no topic report is ever written, and every caller is a file under `app/` — so the scan as written forbade the only thing that could close the defect. It was written when no caller existed and encoded "nothing calls this" as if it were the invariant, when the invariant is doc 06 §7's "no *capture or retrieval* path calls this". The exemption is file-scoped **and** symbol-scoped **and** from-imports only: `app/services/memory_community_detection.py`, four names, and a whole-module import in that same file or the identical import in any other file is still an offence — each proven by its own test, plus one asserting the exemption actually covers the shipped import (a scan that passes only because the caller does not exist proves nothing). Invariant 15 now holds by composition: reachable only from the detector, and `test_communities.py`'s sibling scan proves no capture or retrieval path reaches the detector. **Also settled here:** the snapshot/restore half of T2.19's documented four-step sequence moved *into* `detect_for_project` as Phase P/X rather than staying in the runner, matching T2.91's Phase P; the runner keeps only `generate_reports` | Filed Tier 2 rather than Tier 1 because it changes what an invariant-bearing guard asserts, and because it revises the seam T2.19's docstring hands to its successor. **The tier was also escalated Sonnet -> Opus on discovery** (runbook §2): the row was minted as ordinary wiring, and amending a structural guard is not that. Worth recording in full because the shape recurs — a guard whose universal quantifier was correct while a feature was unbuilt and becomes an obstacle the moment it is built. The reason it is safe to narrow here, and would not have been safe to simply delete, is that the composed proof is strictly stronger than a bare allowlist: T2.77's finding was that an allowlist is the shortest path to a second producer, and the answer to that is not "no exemption" — which was unbuildable — but an exemption that cannot be widened without failing a test |
| 2026-08-05 | T2.91, T2.39a, T2.39 | 2 | **The durable prior lands in `projects.properties`, the capture goes inside `detect_for_project` rather than the job runner, T2.39a's amended clause 3 is retired, and T2.39 gains `Depends: T2.91`.** Three choices the task left open, settled here. **(1) Where the prior lives:** one new `projects.properties` key via a narrowly-scoped repository (`topic_priors.py`), the same shape doc 09 §3.4 already assigns to the pinned/dismissed lists — no schema change, and therefore no baseline-clearance serialisation, which is what stalled T2.84's equivalent. A table buys nothing for one small per-project document that is read whole and written whole. **(2) Who writes it:** `detect_for_project` itself, as a new Phase P immediately before the Phase W rewrite, **not** `run_topic_detection`. The task text permitted either. Putting it in the detector makes it impossible to rewrite a project's communities without recording what they were, and — because `detect_for_project` commits internally after Phase R but not again — Phase P and Phase W land in one transaction, so the prior can never be a copy of the rows it is meant to be compared against. In the runner it would have been an ordering convention any future caller could forget. **(3) Replace, never merge:** a prior is a complete census of one run; merging would resurrect labels gone for several runs and report them decaying repeatedly | Filed Tier 2 rather than Tier 1 because it retires an amendment on a `done` task and changes another task's `Depends`. The retirement is the point worth recording: T2.39a's clause 3 was reduced on 2026-08-05 to "serves that shape faithfully" precisely because the observable was unbuildable, and the row that reduced it said the observable belongs to whichever task builds the prior. It has been built, so the clause goes back to what it originally said rather than staying quietly reduced — a reduction that outlives its cause is the stale-premise defect T2.65 was minted to fix. **T2.39 is unblocked by this and its remaining thinness is now T2.93's, not T2.91's**: pin suggestions can show what changed between runs, while "a pending report renders as pending" stays the only report state a real backend can produce until something calls the report pass |
| 2026-08-05 | T2.92, T2.93 | 2 | **T2.92's premise is right about the defect and wrong about the running cost, and the reason it is wrong is its own task: nothing calls the report pass.** The row says an empty completion is "re-billed every cycle, indefinitely". The write defect is real and was fixed as written — an empty completion stored `""`, which `report_status` cannot tell apart from "never generated". But there is no cycle to re-bill it: `run_topic_detection` calls `detect_for_project` and returns, and `generate_reports` / `snapshot_reports` / `restore_reports` have **no caller anywhere outside `backend/tests`**. So the cost today is zero, the topic-report pipeline does not run at all, and the re-billing is what would have happened the moment T2.93 wires the pass in. Both halves of T2.92 shipped anyway, including the bounded-retry policy the third Done-when asks for | Recorded because the two readings schedule differently: "live cost, fix now" versus "latent defect, and the feature behind it is unbuilt". The controller's confirmation in the tree was of the **write path**, which is exactly what it says — the missing caller is one level further out and is invisible unless you follow the job body. Worth noting the fix is not thereby premature: the guard had to land before a caller exists, or the first wiring pass writes empty reports into a surface that has no way to distinguish them afterwards. **This is the seventh instance of the epic's recurring shape** — a sequence recorded in prose (T2.19's docstring states the four-step order in full) with nothing in the graph to run it |
| 2026-08-05 | T2.90 | 1 | **The real-mode e2e went into a sibling file, `knowledge-real-mode.spec.ts`, not into `knowledge.spec.ts` as clause 2 literally names.** Playwright routes by **file**: `knowledge.spec.ts` is pinned to the `demo-fixture` project (port 3637, `VITE_DEMO=1`) by `playwright.config.ts`'s `testMatch`, so a real-mode test added inside it would inherit that binding and run against the demo fixture — **exactly the failure this task exists to close**. The codebase already carries the antidote for the identical problem on the code section (`code-real-mode.spec.ts` beside `code-wiki-empty.spec.ts`); that precedent was followed. `npm run test:e2e -- knowledge` matches both files by substring, so the split is invisible at the Verify boundary and the original three demo specs still pass untouched | Tier 1 under §5's own example — 'a wrong file path' is explicitly task-local. Logged rather than left implicit because the clause's literal wording, followed exactly, would have produced a test that **passes while proving nothing** — the same shape as the demo-only e2e that made this task necessary in the first place. A reader auditing clause 2 against the tree will find the named file unchanged and should find this row rather than conclude the clause was skipped |
| 2026-08-05 | T2.39a, T2.39, T2.91, T2.92 | 2 | **T2.39a's clauses 2 and 3 amended down to what the door can actually deliver, and the two gaps minted as their own tasks.** The Fable review returned spec **FAIL** on both while rating quality Approved, because both are inherited cross-task gaps the lane surfaced loudly instead of papering over. **Clause 3:** the door calls `diff_topics({}, current)` — no durable prior exists **anywhere**, since the only snapshot ever in existence lives in memory inside the detection job's body mid-run — so every entry reads `new` permanently and `grown`/`stable`/`decayed` are unreachable. -> **T2.91**. **Clause 2:** an empty report and an ungenerated one collapse on the wire, and the lane's defence that empty is unreachable is **false** — `chat_completion` has no empty-content guard and `generate_report` returns it raw, so an empty completion stores `""`, reads `pending` forever, and is **re-billed every cycle**. Controller confirmed both in the tree. -> **T2.92** | Amended rather than left failing because the runbook's alternative is worse: leaving two clauses permanently unmet on a `done` task teaches the next reader that Done-when checkboxes are aspirational. The clauses now describe what this door can do; the observables move to the tasks that can build them, and T2.39a's amended text names both so the reduction is auditable rather than quiet. **Note the shape**: T2.39a exists because T2.39's clause was unbuildable against live data, and its own clause 3 turned out unbuildable for the same reason one level up — the split fixed the door and not the absent prior behind it. That is the third time this epic has found a constraint recorded in prose with nothing in the code to satisfy it |
| 2026-08-05 | T2.80 | 3 | **ESCALATED, not decided: doc 12 §3 fixes the MCP degradation shape and is silent on REST's, so T2.80 had to mint one.** `POST /knowledge/search` returns 503 through the app's `ErrorEnvelope` with `error.code = "unavailable"` and the shared unavailability object at **`error.details[0]`** — a *positional* slot in a list the app otherwise fills with validation errors. The route had no alternative: `HTTPException` keeps a string `message` **or** a list of `details`, never both (`main.py:553-555`), so raising one would have left this door naming neither the outage nor its channels while its MCP twin named both. The Fable review verified that constraint is real and called the shape coherent — but ruled it **an unratified contract on a wire surface** | Tier 3 because amending the design corpus is the owner's call, and this is the corpus being *silent* rather than wrong — the same shape as T2.36a's fourth claim form, which was escalated rather than decided in-task. **The cost of deciding late is asymmetric**: doc 15's SDK reads this contract, and a positional slot is the worst thing to bake in — a consumer that learns to read `details[0]` breaks the moment a validation error occupies index 0. The review's own recommendation, offered as input rather than a decision: ratify in doc 12 §3, and key detection on `error.code` plus the object's own `status` field, **never on position**. Cheap to change now, expensive after an SDK ships against it |
| 2026-08-04 | T2.87 | 1 | **T2.87's premise was half wrong: the supersede door already existed.** The task text said doc 08 §6's fourth bulk verb was "backend-blocked", but `POST /hygiene-queue/bulk/supersede` and `bulk_supersede()` were already live at the branch point, covered by existing tests including `TestUndoIntegration::test_bulk_supersede_is_undone_by_dream_undo`. What was actually missing was only the **data to decide a direction** — `HygieneDuplicateItem` carried two ids and a score, so no caller could tell which endpoint was older. The implementer verified rather than rebuilt that half | Corrected here rather than left, because the wrong premise was **load-bearing for a scheduling decision**: T2.37's review ruled the missing verb backend-blocked and the controller minted T2.87 on that basis. The task was still worth doing and its Done-when still describes real work — the previews and timestamps genuinely did not exist — but a reader of the original text would look for a route that was already there. Independently corroborated the same round: T2.37's round-2 re-review ruled `REFUSAL_REASON_LABELS`' `successor_not_newer` entry **not** dead for exactly this reason, noting the door was live and only the UI verb unbuilt |
| 2026-08-04 | T2.38, T2.13, T2.23 | 2 | **The dream digest's whole-cycle undo now sends the named `event_ids` form, not the body-less form — a change to what "undo this cycle" means, logged by the controller because the fix round disclosed it but never filed the row.** The body-less door takes every not-yet-undone action *including* ones blocked by `state_changed` or a missing object, and one blocked action refuses the whole batch — so a dialog listing only the undoable actions and then firing the body-less form promised a set the door would not act on. The named form makes the dialog's promise the request. **Before:** attempt everything, refuse loudly if any member is blocked. **After:** undo exactly the displayed subset; blocked actions are excluded, and the dialog says so in an explicit exclusion sentence. **This leaves the two surfaces disagreeing about what the verb means** — the hygiene queue (`use-hygiene-queue-api.ts:213`) still calls the same door body-less, where "attempt everything, refuse loudly" is the right semantic for a bulk-action batch | Ruled **not** the client-side prefilter the 2026-08-02 amendment forbids, and the distinction is the useful part: that defect was a layer shrinking a set *after* the caller named it, whereas here the set is composed **before** confirmation, displayed, sent exactly as displayed, and then goes through whole — the backend applies no prefilter to named sets and a stale member still 409s. The race is **better**, not worse: a concurrently-undone member now 409s on `already_undone` and the 409-then-refetch flow re-reads, where the body-less form would have silently hidden the other curator's edit. Tier 2 rather than Tier 3 because doc 13 §6.3 asks only for per-action and per-batch undo and the backend contract is untouched. Filed anyway because it changes a user-facing operation's semantics **two days after a logged amendment defined them**, removes the digest's only body-less caller, and leaves the review corpus describing a tree that no longer exists — the shape of drift that is invisible until someone reads the old row and believes it |
| 2026-08-04 | T2.87, T2.88, T2.37 | 2 | **Two backend tasks minted from T2.37's Fable review, both of which the UI lane correctly refused to paper over.** (1) `T2.87` — `HygieneDuplicateItem` carries two memory ids and a score and nothing else, so "Supersede instead" is unbuildable without the frontend inventing an adjudication; the review ruled the refusal **correct restraint, not an unshipped obligation**, and doc 08 §6's fourth bulk verb is therefore backend-blocked. `build_duplicates_query` already joins both memory rows (`src.status`/`tgt.status` in its WHERE), so the enabling change is projection, not a new join — measured, not assumed. (2) `T2.88` — `GET /review-queue/counts` takes no `project` parameter while `/facts` and `/articles` beside it do, so a filtered queue shows a count from a different population than its own list | Both are the same shape as T2.36a and T2.39a: a UI task reaching for a backend capability the corpus assumes and the code does not have. What is different, and worth recording, is that this time **the lane stopped instead of faking it** — it reported the duplicates gap as unbuilt and rendered the counts number with an inline unscoped qualifier rather than showing a figure that disagrees with the list beneath it. The review's ruling on that qualifier is the useful nuance: it passes invariant 14 **narrowly**, because the qualifier sits on the number it qualifies, but it is skimmable and it is a workaround. That is the right standard — an honest workaround is shippable and still generates a task, rather than closing the question |
| 2026-08-04 | T2.86, T2.36 | 2 | **T2.86 minted: the fact detail route is demo-only and nothing calls T2.36a's detail door.** `knowledge_.facts_.$factId.tsx:64` calls `useDemoFact` unconditionally, so with DEMO off any real fact id renders "This fact does not exist in the demo store". T2.36's row linked there for disputed facts, which is how the dead link shipped. The fix round closed the link by **not offering it** — a new `detail_available` producer capability, false on the live path — and said explicitly that wiring the page is a task, not a fix, because the page renders a verification ladder, a dispute panel and multiple belief windows that `FactDetailResponse` does not carry | Filed as its own task rather than widened into T2.36's fix round for a reason worth recording: it is **partly a backend question**. Whether the detail door grows to serve what doc 13 §5.1's page shows, or the page stops showing what the door cannot support, is a per-field decision neither doc settles, and a fix round under time pressure would have settled it by whichever was cheapest. Note `detail_available` is itself scheduled for retirement inside T2.86 — an interim honesty flag that outlives its condition becomes the stale-premise defect T2.65 was minted to fix, so it is part of done rather than a follow-up. The article detail route (`knowledge_.articles_.$articleId.tsx`) has the same shape but is **not** minted here: `article_synthesis` is still a `PlaceholderJobRunner`, so `knowledge_articles` has no production writer and there is nothing live to wire it to |
| 2026-08-04 | T2.79–T2.84 | 2 | **Audited every Verify command on the six back-filled entries; three more name files that do not exist.** After T2.83's field was found wrong, the same check was run across all six. `T2.81` (already **done**) named `tests/test_memory_update_nulls.py` — its own commits put all 374 lines of added coverage in `tests/test_empty_content_update.py`, so the field is corrected here. `T2.82` (currently **wip** in lane ah) names `tests/test_reembed.py`, which does not exist and never has; that lane will hit the same error, and the correct target is one or more of `test_reembed_absent_partition.py` / `test_reembed_code_chunks.py` / `unit/test_reembed_helpers.py` — **left uncorrected deliberately, because the row is owned by another lane and the controller does not edit a claimed task.** `T2.80` names `tests/test_knowledge_search.py`, which is legitimate: that task creates it. T2.79 and T2.84 are clean | The failure mode is what makes this worth a Tier-2 row rather than three Tier-1 fixes. A Verify command naming a missing file does not fail — `pytest` exits with `ERROR: file or directory not found`, which a careless reading scans as 'nothing failed'. Runbook §4 requires the Verify command to be *actually run with its real output recorded*, and a command that cannot run makes that box uncheckable rather than checked. T2.81 passed a Fable review and a scoped re-review with this field wrong in the tree, so the defect survives adversarial reading — it is invisible to everyone who does not try to run the command. The root cause is structural: these six were minted straight into `progress.md` from review findings and back-filled into the epic file on 2026-08-04, so their Verify fields were **reconstructed rather than observed**. Any future back-fill should run every Verify field it writes |
| 2026-08-04 | T2.83 | 1 | **Verify field corrected: it named two test files that do not exist.** The minted text said `tests/test_reembed.py tests/test_embedder_registry.py`; neither is in the repo, and `pytest` exits with `ERROR: file or directory not found` rather than passing vacuously. The real coverage is `tests/test_vectors_route.py tests/test_api/test_graph.py`, because the guard lives in `PostgresVectorRepository.resolve_read_fingerprint` and is observable only through the two read surfaces that call it | Found by the T2.83 implementer, which ran the command as written, reported the error verbatim and did not route around it silently. Worth logging rather than just fixing: T2.83 was one of the six entries minted straight into `progress.md` from a review finding and back-filled into the epic file on 2026-08-04, so its Verify field was reconstructed rather than derived from a real run — the other five back-filled entries carry the same risk and nobody has checked them. A Verify command naming a missing file is the worst shape available: it *errors* rather than fails, so a careless run reads as 'no tests failed' |
| 2026-08-04 | T2.39, T2.39a | 2 | **T2.39 split; `T2.39a` minted to own the topics read surface and the pin-suggestion door, and T2.39 gains `Depends: T2.39a`.** T2.20 shipped `topic_browsing.py` and `pin_suggestions.py` — nine public callables, both modules well tested — and a repo-wide scan finds **zero** consumers of either outside `backend/tests`: no REST route, no MCP tool, no job. Two of T2.39's four Done-when clauses therefore had nothing to satisfy them. "accept/dismiss round-trips" has no door to round-trip against, and "pin suggestions show what changed between runs" needs `diff_topics`' output reachable from a browser. `topics-tab.tsx` is meanwhile a demo-data surface, so nothing fails loudly and a lane would have satisfied both clauses against `useDemoStore` | Caught by the controller at brief-writing time, reading the tree rather than the task text — the same way T2.36a was caught the day before, and the **sixth** instance of this epic's recurring shape: a constraint recorded in prose and absent from the graph. Split rather than widened for the reason the T2.36 split gives: widening in place pushes a Size-M task to L without the reviewed step-level plan runbook §3 requires. Both halves are Sonnet here — the door is plumbing over semantics T2.20 already fixed and tested, not a new honesty contract — which is the one way this differs from the T2.36/T2.36a split. The identity rule is what makes the door non-trivial: T2.20's Done-when pins pin suggestions to the stable dominant-entity label rather than the churning community id, and a route that keys accept/dismiss on the id would silently reintroduce exactly the churn that clause excludes, with a green suite either way |
| 2026-08-03 | T2.78 | 1 | **T2.78's Verify command names `backend/tests/test_code_query.py`, which has never existed in this repository** — `git log --all` for that path returns nothing, and no file of that name exists under any tests directory at the branch point. Ran the actual coverage of `CodeQueryService.search_code` instead — `tests/test_code_search_order.py` plus `tests/test_mcp.py`, `tests/test_mcp_surface_parity.py`, `tests/test_door_parity.py`, `tests/test_pushdown_reason_code.py` (54 passed) — and `tests/test_hybrid_search.py` (10 passed, including the new deletion-proving test) as named | Task-local: a wrong file path in the Verify field, carried into the lane brief unchanged. Recorded rather than silently substituted so the next reader does not re-derive which file the command actually meant, and does not read a clean run of a nonexistent file as having happened |
| 2026-08-03 | T2.76, T2.21 | 2 | **T2.76 minted: `gate.sh` sends the harness to the shared `darkmem_bench` in every round.** It exports `TEST_DATABASE_URL` and not `BENCH_DATABASE_URL`, so the benchlib arm ignores a lane's bench assignment entirely; T2.21 hit it as a `DeadlockDetectedError` on `DROP SCHEMA` while a sibling lane held the database, and green on a re-run with the variable pinned. **The repo's own merge gate is therefore the one command that violates the per-lane isolation runbook §8 mandates** | Recorded rather than patched inline because the fix has a precedent worth matching: T2.54 hit the sibling defect *this same day* — a harness test whose result depended on an ambient environment variable — and resolved it by deriving the database name from a hash of the checkout path so the environment stops deciding. Two components solving the same problem two different ways is how the two RRF constants already drifted. Note also the failure's shape: it is indistinguishable from a code regression, which is precisely what the runbook warns about, and it cost the controller a red gate earlier in this round that was attributed to a killed run — a diagnosis that may have been right for the wrong reason |
| 2026-08-03 | T2.75, T2.71, T2.36a | 2 | **T2.75 minted: the badge guards are backend-only, and the frontend carries claim strings none of them can see.** Doc 13 §5.3 forbids a screen paraphrasing the claim; two demo-fixture files and a component comment do. T2.36a's certainty-word guard and T2.71's second-producer scan both walk `backend/app` exclusively. Two independent sightings the same day: T2.71's implementer flagged the fixtures and took no action, and T2.71's **reviewer reported a fixture at `knowledge-curated.ts:52` in a claim form the producer can never emit** — a demonstrated divergence rather than a stylistic worry | Logged because the interesting property is the **shape of the blind spot**, not the three files. Two separate guards were built this round to stop a second producer of the honesty sentence, both were mutation-proved, and both stop at the language boundary — so the surface doc 13 actually cares about, the one a human reads, is the one surface neither covers. The UI is still on demo data, so nothing user-visible is wrong today; that is the argument for fixing it now rather than after it is wired |
| 2026-08-03 | T2.75 | 1 | **Corrected the sighting's citation and its status.** The row above previously cited `chat-curated.ts:52` and recorded the sighting as partial, on the belief that T2.71's review terminated on a model-tier limit before writing its verdict. Both were wrong: the review is **complete** (both verdicts, five findings, a bottom line), and its citation is `knowledge-curated.ts:52`. `chat-curated.ts:52` is a **correct** L0 badge line | The error was not cosmetic and is worth keeping as a lesson about provenance. The recorded pointer aimed at a **healthy** row, and the Done-when box instructed the next agent to re-verify that line and record a false positive if it found none — which is exactly what it would have found. A mis-cited finding is more dangerous than a lost one, because the re-check manufactures false confidence that the surface is clean. The prior row's own closing sentence — that an unverified sighting is worth more than a lost one "provided nobody later reads it as settled" — was right about the risk and pointed at the wrong line |
| 2026-08-03 | T2.74, T2.73 | 2 | **T2.74 minted: three surfaces declare a `content_preview` crossing that no driver checks** — `reembed_backfill_queue`, `pipeline_failure_triage`, `capture_buffer_triage`. Pre-existing, not introduced by this round: each is *asserted* to truncate and none is *proven* to. T2.73's `_preview_boundary()` is the mechanism, but the reviewer measured that it does **not** drop in unmodified — `capture_buffer_triage` declares a 500-character preview while its long fixtures end near 280, so naive reuse false-positives | Recorded as its own task because the interesting part is the shape: T2.73 was minted for a guard that was *absent*, and reviewing it surfaced three more that are *present and vacuous*. A vacuous guard is the worse of the two — the absent one raised loudly and got fixed within the day, while these three have been reporting clean for as long as they have existed. The per-surface preview length being an input rather than a constant is exactly why 'extend the helper to the other three' is not a paste, and is stated here so the next reader does not size it as one |
| 2026-08-03 | T2.73, T2.23, T2.36a | 2 | **T2.73 minted: the isolation probe is offline on the epic branch, and the controller's merge process is what let it through.** T2.23 and T2.36a each added `ContentSurface` rows without the matching `isolation_probe.DRIVERS` entry. The table's completeness check raises, so **all eight** `test_isolation_probe.py` tests error or fail — the cross-project leak guard is not weakened but entirely absent. Both lanes were green on Verify and on the repo floor, both passed Fable review, and neither touched benchlib so neither ran it | The mechanism is documented in `CLAUDE.md` verbatim — `testpaths = ["tests"]` means `pytest -q` does not collect `scripts/benchlib/tests`, so "the harness can break while the floor stays green", and the stated remedy is to run `./scripts/gate.sh`. **The controller merged three lanes on a green floor rather than a green gate**, which is the process defect; the reviewers were scoped to their lanes and the briefs asked for the floor. Recorded as an amendment rather than fixed silently because the same gap will recur on every future round that adds a surface: the fix is the merge procedure, not just these four drivers. Note what the guard protects — the probe is the only thing proving memory content does not cross a project boundary past its declared preview, and an offline guard is indistinguishable from a passing one in any report that only quotes the floor |
| 2026-08-03 | T2.23, T2.13 | 1 | **T2.23 falsified the 2026-08-02 row's "unreachable from today's producer" premise for the empty-string tombstone key, and the code now guards it.** That row recorded `_invert_subsume` writing a tombstone under an empty-string key if a payload lacked `pair.newer`, and closed it as unreachable and one-line-fixable. T2.23's `prune` bulk action journals `pair.newer=None` by design — deprecation retires a memory without a successor — so undoing a prune reached exactly that path. `dream_undo._invert_subsume` now writes `counterpart or "_none"`; the AST atomicity guard re-runs unchanged and `test_dream_undo.py` is 88 passed. The re-review verified the sentinel on disk after a prune→undo round trip and found it **doubly inert**: the by-id reader never asks for it, and a null-counterpart `content_sha` cannot match. **The older row's text is left standing** — an amendment log is a record of what was believed when, not a document to retro-edit | Worth logging as its own row rather than as a footnote to T2.23, because the interesting content is the *shape*: a defect closed as unreachable became reachable two days later when a new caller supplied the one input the old producer never did. "Unreachable from today's producer" is a claim with an expiry date nobody sets. The disclosure also failed the first time — T2.23's own report did not mention it, and the reviewer found it; the fix round is where it was stated plainly. Five deferred minors from the re-review are recorded in the round's review file: the now-dead caller-supplied `cycle_id` parameter (whose only reachable use would relabel a mixed cycle wholesale, since `MIN` ignores NULLs), the untested `created_at` floor clause, the unpinned `_none` sentinel, the read-path guard's perimeter excluding hybrid search, and a `subject_name`/`subject_id` docstring slip whose surrounding argument the reviewer verified holds anyway |
| 2026-08-03 | T2.36a, T2.71, T2.72 | 2 | **Two tasks minted from T2.36a's review, and one question escalated to the owner.** (1) `T2.71` — `layer_composition.py` contains zero badge references, so every L2 fact retrieval serves today goes out unlabelled; **tagged G-C-blocking**, because T2.40's evidence run makes claims about served output and a gate cleared over unlabelled facts would overstate its coverage. (2) `T2.72` — doc 12 §2 assigns `fact_get` a REST twin at exactly the path T2.36a built, and §3 puts the agent-facing vault reads on MCP's `fact_get`/`knowledge_search`; a scan of every epic file for those names returns **nothing**, so no task owned them. No live invariant-17 breach today, since parity is not violated by a surface absent on both doors' agent side — but T2.36a's REST-only filing rests on a trust-posture argument the reviewer judged weak, every two-door surface in this repo already pairing unauthenticated MCP with authenticated REST. (3) **Escalated, not decided here:** T2.36a emits a fourth `claim` form, `", verification not yet recomputed"`, for a fact with no journalled `verified` event. Doc 12 fixes three forms and is silent on this one, which is the form a cold-start vault renders on *every* fact. The reviewer accepts it and recommends doc 12 gain it; amending the design corpus is the owner's call | Neither task is scope creep: T2.71 is a live honesty gap on the served path, and T2.72 is a contract doc 12 already wrote that nothing was scheduled to satisfy — the sixth instance in this epic of a constraint recorded in the corpus and absent from the graph. T2.71 exists as a separate task only because of round mechanics: T2.36a's brief forbade `layer_composition.py` since T2.55 held it the same round, so the one map over composed rows fell between two lanes. Worth noting the reviewer reached its verdict by extracting doc 12's worked example **by script** and diffing it against a live `build_claim` call, and by inventing two mutation drills the implementer had not run (a quiet `as_of` fallback to `created_at`, and a default `corroborated` list filter) — both of which the suite caught, which is the evidence that the exact-string discipline works |
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
| 2026-08-03 | T2.46 | 1 | **The grace bookkeeping is two columns, not one: `demotion_pending_since` plus `demotion_pending_cycles`.** Doc 08 §4.3/§9 names one "`demotion_pending_since` marker" and fixes the window in *consecutive recompute cycles*; a timestamp cannot count cycles, so a single marker can only implement grace = 1 and would make `verification_demote_grace_cycles` a knob that silently does nothing above its default | Two single-column alternatives were considered and rejected. Deriving the count from the `verified` journal makes a correctness threshold depend on journal retention (an unresolved Tier-3 policy, CLAUDE.md) and on a payload shape `benchlib.promotion_metrics` validates as a closed vocabulary. Expressing the grace in wall time would make the ladder read the recompute job's cadence, which `verification_ladder`'s module docstring explicitly refuses ("never schedules itself"). The marker keeps its documented role untouched: `demotion_pending_since IS NOT NULL` is still the label and still the review-queue predicate `derive_review_state` registers, and the counter is never either |
| 2026-08-03 | T2.46 | 1 | **Lane file list extended by four files the task cannot be built without** (row corrected 2026-08-03 in the fix round: it said three and omitted `app/services/review_queue.py`, which the brief listed as read-only and which the task in fact writes — docstring, `_FACT_COLUMN_NAMES`, `_fact_reason`, `list_open_facts` — under R3's instruction to let the queue name the reason). The brief's may-touch list named `verification_ladder.py`, `app/models/`, the baseline and `tests/`, but the ladder's only write path into the verification axis is `KnowledgeTripleRepository.set_verification_status`, and its only read projection is that module's `_COLUMNS` | The marker must ride the status write (one statement, one lock) for the reason `review_state` does — the T2.62 argument transfers verbatim, since a status moved without the marker leaves a demoted fact still wearing the overlay that promised it had not been demoted — and it must ride `_COLUMNS` or "served labelled" is unprovable against the read path. `app/schemas/review_queue.py` gained one optional response field so the label reaches the queue's wire surface. `app/services/verification_recompute.py` gained the one-recompute-per-fact-per-tick skip (next row) |
| 2026-08-03 | T2.46, T2.09 | 2 | **The recompute job could burn two grace cycles in one tick, collapsing the shipped one-cycle window entirely.** When the slow arm is due it slices over facts the fast arm recomputed moments earlier in the same tick — always, on any vault smaller than the slice size — and both looks run in one session and one transaction, so the second cannot observe anything new. `_reconcile_from_fact_sources` now skips `DrainOutcome.recomputed_ids` and reports `facts_skipped_fresh` | Before hysteresis this was only wasteful (a lock, a read and a no-op write per duplicated fact); with the window counted in recompute cycles it is a correctness bug whose symptom is the hysteresis silently not applying on precisely the ticks the slow arm is due. Surfaced rather than absorbed silently because it changes a T2.09 module's tick semantics: the backstop is unweakened (a fact the fast arm just recomputed is by definition not one it missed, and the cursor still advances over it, so the rotation period is unchanged), but the two arms are now ordered rather than independent |
| 2026-08-03 | T2.46, T2.40 | 2 | **Demotion thrash is now absorbed, and absorbing it leaves no journal trace — so the metric doc 17 §5.1 names has no input.** Entering, holding and cancelling the `under-sourced` state move no rung, so none of them journals a `verified` row; the eventual demotion journals normally. Doc 17 §5.1 tunes the hysteresis parameters "against measured demotion-thrash counts from the same journal", and the flaps the window absorbs are exactly the ones that no longer reach it | Journaling the holds was deliberately not done here. `benchlib.promotion_metrics` raises `UnrecognisedPayloadError` on a `hold` that is neither contradiction- nor supersession-blocked, and its own message states the remediation: the promotion-rate denominator "must be re-derived to account for it before this number can be trusted". That is a gate-metric decision T2.40 owns, not a side effect of landing the column. The row-level record survives — `demotion_pending_since` carries the instant the window opened, on the row and on every read path — so the input exists; what does not exist is a journal stream a G-C query can count flaps from |
| 2026-08-03 | T2.46 | 1 | **"Every fact read path carries the marker" was an overclaim, and two serving surfaces did not carry it.** `verification_ladder`'s module docstring (and commit `4027910`'s body) asserted a universal that `_COLUMNS` cannot deliver, because a surface that hand-enumerates its own projection has to name the marker itself. `facts_read._base_item` — doc 13 §5.1's Facts tab, exactly where §5.3's caution overlay renders — and `facts_channel`'s row payload both omitted it. Fixed by carrying the field on both (plus `FactListItem`, which gates what survives serialisation) and by replacing the universal with the finite list of surfaces that carry it, stated as a list a new surface has to be added to | Found by the Fable task review (F1, Important). Nothing was ever *withheld* — no path filters on the marker — so the honesty clause held, but the live surface could only reach `under-sourced` by elimination (`corroborated` + `review_state='open'`), which is the derivation T2.62 rejected for the queue and which stops being sound as soon as a second opener exists. Proved renderable through `GET /api/v1/knowledge/facts` (list and detail) and mutation-drilled on both halves. Two docstring claims were corrected in the same pass: the applier's "served on every read path", and the cancellation test's narration of a self-healing mutant it does not actually catch |
| 2026-08-03 | T2.72 | 2 | **No task owns `POST /api/v1/knowledge/search`, doc 12 §2's REST twin for `knowledge_search`.** T2.72 shipped the tool and it lands MCP-single-door in `docs/two-door-parity.md` for the agent-shaped-projection reason the six code tools carry — the rows are REST-reachable in their own key spaces, the cross-layer ranked question is not. That reading is honest but it is the *seventh* MCP-ahead-of-REST row, and unlike the code family doc 12 does not claim this twin already exists: §2 lists the route among the ones the reshape adds, and a scan of every epic file returns no owner for it. T2.56 owns the sectioned and fused output *shapes*, not the route. The serialiser both doors need is deliberately outside the tool, in `app/schemas/knowledge.py`, so a route spends the same function rather than reshaping `LayerCompositionService.search`'s result a second time | Recorded rather than built: adding a REST route is outside the lane's file list, and inventing a permanent single-door justification would contradict doc 12 §3's own tool table, which assigns the twin. Filing it as a schedule is what `test_every_single_door_surface_states_a_real_reason` rejects, so the row states the shape-versus-capability distinction and records the discrepancy the way the code rows record theirs. The next scheduling pass should mint the route as its own task |
| 2026-08-04 | T2.34 | 3 | **ESCALATED — doc 08 §9 and §3.1 disagree on which column a fact's stated expiry writes, and the literal §9 reading silently breaks retrieval and a uniqueness invariant. Not implemented; no code written.** §9 says a dated fact "gets its belief window **pre-closed at that date**", which reads as setting `invalid_at` to the future expiry at population. §3.1's state machine says `invalid_at` is set when **a newer belief arrives** (`open --> window_closed`), and routes a stated expiry down the *other* edge entirely (`open --> expired`, i.e. `expired_at`). They cannot both hold. The literal §9 reading is not merely ambiguous, it is destructive: `0001_baseline.py` makes **four** indexes partial on `expired_at IS NULL AND invalid_at IS NULL` — the unique `ux_knowledge_triples_open` plus doc 07 §2's three fact-channel retrieval indexes — so a future `invalid_at` written today (a) drops the fact out of the retrieval channel's scope **immediately**, years before its stated expiry, and (b) frees the unique slot, letting a second currently-open belief on the same `triple_key` exist beside it. Both failures are silent. Note `as_of` already implements the correct half-open window (`valid_at <= t < invalid_at`), so the *model* is right and it is the shipped "currently open" predicate that assumes `invalid_at` is only ever set in the past. **Three ways out, none of which a lane may pick unilaterally:** (1) make "currently open" time-aware — impossible as a partial index, since `now()` is not IMMUTABLE, so it means reworking the unique constraint and all three retrieval indexes and relaxing invariant 8's temporal analogue, i.e. a baseline schema change that serialises through one owner; (2) add a `stated_expiry` column and have the recompute arm write `expired_at` when it passes — a schema amendment §9 does not list (§9's only named amendment is `demotion_pending_since`); (3) no column at all — the recompute arm re-derives the stated expiry deterministically from the fact text each cycle and sets `expired_at` once past, which is consistent with both sections and with §9's "no LLM, no separate job", at the cost of re-parsing | Found while bootstrapping T2.34, before any code. Runbook §5 Tier 3: the corpus doc wins until a human decides, and this would relax an invariant either way. **The memory side is unaffected and remains buildable** — the owner has already settled it as a deterministic post-extraction parse with no prompt change, which keeps the F1 bench cache valid (the cache key is `sha256(content + system_prompt)`, so a schema edit there would red the gate until a live DeepSeek re-warm and force a re-recorded F1 baseline). Recommend splitting T2.34 on that seam once the fact side is ruled |
| 2026-08-04 | T2.34, T2.85 | 2 | **T2.34 split on the escalation seam; the fact half is minted as T2.85 and the memory half proceeds.** The two were never one mechanism — doc 08 names them in separate sections and the task's own text said "two different mechanisms that must not be conflated" — and only the fact half is blocked by the Tier-3 row above, so holding both would have parked a buildable activation behind a doc ruling it does not depend on. T2.34 keeps the memory side, drops to `Size: S`, and loses its `T2.01` dependency (that was the fact half's); T2.85 keeps `T2.01`, carries the contradiction and the three candidate rulings in full, and is **Fable/xhigh** because its first deliverable is a ruling between two design-doc sections rather than code. The `Verify` files split with them (`test_self_expiring_memories.py` / `test_self_expiring_facts.py`) | Runbook §5 Tier 2: a new task the plan missed, so both the epic file and `progress.md` are edited and the split is called out in the completion report |
| 2026-08-04 | T2.34 | 1 | **The stated-expiry detector is narrowed to self-referential retention instructions, because T1.37's sweep deletes.** Doc 08 §2.3's illustrative phrasing is "valid until end of Q3", which reads naturally as any date near an expiry word. But `expired_memory_cleanup` **deletes** the row — embeddings cascade, provenance is withdrawn — so a false positive is silent, irreversible data loss, and "the licence is valid until 2026-12-31" is a claim *about a licence*, not an instruction to forget the note on that date. A deterministic parser cannot tell those apart from phrasing alone, so it matches only a memory addressing **its own** lifetime, and additionally refuses any derived instant not strictly in the future — otherwise capture could arm a sweep that deletes the memory it just wrote | The narrowing costs recall on unusual phrasings, which is the correct direction: a missed expiry leaves a memory alive one cycle longer and is recoverable, while a false positive is not recoverable at all. Recorded so the next reader meets the reasoning rather than widening the patterns to match the doc's illustrative example |
| 2026-08-04 | T2.79, T2.80, T2.81, T2.82, T2.83, T2.84 | 2 | **Six tasks had tracker rows but no epic entry anywhere — minted here.** Every one was minted straight into `progress.md` from a review finding, which is the fast path and also the one that leaves a task undefined: `gen_progress.py` derives ids and titles *from* the epic files, so a row with no entry behind it is a row the generator refuses to regenerate. Three of the six (T2.80, T2.83, T2.84) were `todo` and therefore **unexecutable** — an agent claiming one had the Note cell and nothing else: no `Depends`, no `Doc`, no Done-when, no `Verify`. The entries reconstruct scope from the review findings that minted them, so the two already-`done` rows (T2.79, T2.81) document what shipped and the four open ones can now be picked up | Found at the start of the 2026-08-04 session by running `gen_progress.py`, which had been failing on all six for days and could not be run at all. The lesson is the generator's, not the minter's: minting into the tracker is the natural move after a review, so the epic entry has to be part of that same edit or it never happens |
| 2026-08-04 | T2.65 | 2 | **Decided: the memory-bridged proxy stands as an interim position, not a fact-keyed counter, and the measurement behind that decision found the gap is already live traffic, not a hypothetical one.** `layer_composition.LayerCompositionService.search` — wired unconditionally behind the `knowledge_search` MCP tool, no feature flag gating it — calls `FactsChannel.search_with_trace` for every invocation, and that channel serves `knowledge_triples` rows directly with no call anywhere analogous to `access_stats.spawn_record_access`. So "the facts channel has no consumer wired" does not hold as a defence; a fact served only through `knowledge_search` scores zero retrieval-frequency heat today, on live traffic, not on a hypothetical future one. The proxy is kept anyway because the honest fix — a fact-keyed analogue of `memory_access_stats`, keyed `fact_id REFERENCES knowledge_triples(id)` — needs a new table, and no lane holds baseline-schema clearance this round. `review_ranking.py`'s docstring and `FACT_KEYED_COUNTER_STATUS` now state this as an interim bound rather than the stale "reads exclusively through source memories" premise, and `facts_channel.py` carries a matching `RETRIEVAL_HEAT_STATUS` breadcrumb; `tests/test_queue_ranking.py::test_facts_channel_traffic_never_feeds_retrieval_frequency` pins the gap against fifty real `FactsChannel` searches and was watched to fail when the recording was mutated in | Recorded as a Tier-2 amendment because it is a newly discovered dependency the plan did not carry: the next schema window should mint a task for the `fact_access_stats` table (same shape and coalescing-buffer idiom as `access_stats.py`, fed from `FactsChannel`'s serving path) rather than assume this proxy is permanent. Nothing here builds that table — R6 of the T2.65 brief forbids a schema change this round, and this decision converts the task into exactly the "decision plus a ready-to-execute plan" outcome the brief names as legitimate |
| 2026-08-05 | T2.16 | 1 | **Fix round 1 on the Fable task review: the derivation strip no longer retires edges whose signal no arm measured, and the cap-engaged bound finally has a test that can fail.** (I1) With the proximity arm skipped under an unresolvable fingerprint, `kept` cannot hold a proximity pair, so the strip retired every proximity edge in the seed window without re-measuring a single cosine — silently, because the strip journals nothing, and irreversibly, because the original write's undo CAS-refuses once its block is gone. On a deployment whose embedding purpose carries no `dimensions` the canary never recovers and the whole proximity graph is swept one seed slice at a time. `strip_stale_edges` now takes `unmeasured_signals` and spares any triple whose stored block rests on one, counted as `spared_unmeasured`. (I2) The truncation test named for the bound exercised the *unbounded* branch, so deleting the bound clause outright left all 24 tests green; `test_the_bound_spares_edges_past_the_decided_prefix` drives the engaged bound instead. Three minors fixed with them: the proximity fan-out becomes its own config row `derivation_neighbours` (it used to read the judge's `pair_candidates`, so tuning the judge silently moved which proximity edges could exist), the digest's `action_detail` renders `signal` (this pass has no verdict, so it was the only answer to "why is this edge here"), and §7a gains E10 recording that the cursor advances under a dead canary. Two declined with reasons in the fix report: row locks in `write_derived_edge` (Phase D commits once, so mirroring `apply_associate`'s `FOR UPDATE` would hold locks on up to 2x`derivation_batch` `memories` rows for the whole pass and block the capture path — a worse hazard than the self-healing one it closes) and the expired-memory filter asymmetry (`MemoryFilter` has no expiry predicate at all and is the shared retrieval scope class, so closing it here is a repo-wide retrieval change out of this lane) | Tier 1: both Important findings are task-local and neither reopens the design — the review's own disposition. Recorded rather than absorbed because I1 changes what D9 means (retire only what this run re-evaluated now binds the arms, not just the pairs) and F-M1 adds a row to D6's config list |
| 2026-08-06 | T2.50 | 1 | **The Verify line is corrected to two invocations with the flag spellings the CLI validates.** The stated `--arm w_ppr,dual_level` exits 1 with `unknown --arm 'w_ppr,dual_level'; valid arms are [...]`: `run_retrieval_eval.py` takes one `--arm` per run, and `arm_ablation.resolve_ablatable` deliberately accepts only config-flag spellings (`w_ppr`, `w_dual`), never the short names — the same one-spelling discipline `resolve_arm` documents. Fixed to `--arm w_ppr && ... --arm w_dual` | Found by running the line verbatim during T2.50's execution (the judge's own definition of done requires running the stated Verify); the recorded ablations had already used the correct per-arm invocations, so the defect was in the task text alone |
| 2026-08-07 | T2.97 | 1 | **A third candidate shape existed and the task text named only two: `reembed.py` is already a missing-fingerprint back-fill, and a repo-minted entity is exactly what it calls obsolete.** Added to the task text so the choice is made against the real option set, together with the shipped decision and its boundary. Shape 1 (embed at derive time) turns out to be blocked rather than merely awkward — T2.27's guard forbids the whole orchestrator surface, `embed_batch_chunked` included, and it is reached through the same handle a `chat_completion` is, so permitting the embed means permitting an extraction. Shape 3 was rejected because `reembed_entities` is a whole-corpus operator action with a lock set and a progress broadcast: scheduling it re-embeds every entity missing a vector, which after an embedder rotation is the entire corpus, on a cron nobody asked for. Shipped shape 2 narrowed to `repo_ids <> '{}'`, the one set with no other writer | Runbook §5 Tier 1: task-local, the brief instructed the amendment, and a reader meeting only two options would weigh the recommendation against a false alternative set. The boundary is recorded in the same row because it is the part a future reader is most likely to assume away: the job makes anchoring work when a repo is indexed before the memory arrives, and does nothing for the reverse order |
| 2026-08-07 | T2.97, T2.101 | 2 | **T2.101 minted: the anchoring order that never heals has no owner.** T2.97 gave repo-minted entities embeddings so Phase 4's ANN probe can see them, and its adversarial review confirmed independently that this closes **one order only** — `assert_from_repo` is an exact-key upsert with no probe and Phase 4 dedups at memory-write time, so memory-first-then-repo forks permanently and re-derivation cannot heal it. That is the order an existing install produces the first time it indexes a repo | The executor disclosed it, pinned it with a named failing-direction test, and said plainly that no task owned closing it. Same shape as T2.16 shipping two of three signals and T2.27's two gaps: a stated deliverable is narrower than the doc claims and **no row owns the gap**, which is the Tier-2 definition. Worth recording that the disclosure is what made this cheap — a limitation pinned by a test becomes a decision for the next task rather than a discovery |
| 2026-08-07 | T2.48, T2.86 | 2 | **T2.86 gains a clause naming the `stale` field, and its missing `progress.md` row is restored.** T2.48's rescope judged M-5 NOT ADDRESSED as a self-sufficient disposition: routing "render the stale flag" to T2.86 was right in principle, but every T2.86 clause binds only the *removal* direction, so nothing obliged rendering a field the door already serves — and T2.86 had **zero rows in `progress.md`**, making it invisible to scheduling | The routing was an effective drop, not a handoff, and neither half was visible from inside the lane. The `progress.md` gap is the more alarming of the two: the runbook makes that file canonical for scheduling, so a task absent from it cannot be picked up however complete its text is. Worth a sweep for other task ids present in an epic file and absent from `progress.md` |
| 2026-08-07 | T2.102 | 2 | **T2.102 minted: three consecutive rounds each found one missing entry in the frontend event-taxonomy map and fixed exactly that one.** `contradiction_scanned` (T2.11), then `citation_stale` (T2.48). T2.48's rescope swept the whole vocabulary and found seven unmapped values with live emitters | Each one-line fix was correct in isolation and none was the fix. The map is maintained reactively and nothing fails when it does not learn a new value — the taxonomy-first rule governs the vocabulary but does not reach this map. A defect found three times the same way is a missing guard, not three oversights |
| 2026-08-07 | T2.96, T2.97, T2.48 | 1 | **`CLAUDE.md`'s job count reconciled centrally at merge to nineteen registered / thirteen live.** Three lanes each found the sentence already stale (T2.49's `relation_embedding_refresh` was never counted) and each corrected it for its own addition alone, so all three were locally right and collectively wrong | The keys that escaped the count all register via **constants rather than string literals**, which is exactly how a grep-based check undercounts — now stated in the sentence itself. T2.48's contribution is the durable one: `test_code_deriver.py` derives the roster from `app/main.py`'s AST, so the next job cannot silently desynchronise the baseline. Recorded because the same sentence going stale through four landings, then being independently rediscovered by three concurrent lanes, is a maintenance-shape signal rather than a typo |
