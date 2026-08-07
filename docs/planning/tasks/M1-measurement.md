# M1 — Measurement phase (evidence, gold, and gate verdicts)

**Goal:** Run every measurement the system's truth claims owe, against the finished
implementation rather than against fixtures. This epic holds the evidence runs and the
gold they consume — nothing else — so that no implementation task ever waits on a dataset.

**Entry gate:** none. M1 opens when the implementation epics it measures are complete
enough to measure; it is **not** on any implementation critical path by construction.

**Done when:** G-C, G-D, G-E and G-F each carry a verdict — cleared *or* recorded as a
measured miss. A miss is an outcome, not a failure to finish.

**Epic branch:** `feat/m1-measurement`

**Contract:** [`../agent-runbook.md`](../agent-runbook.md). Amendments log at the bottom.

## Why this epic exists

Created 2026-08-06 by controller decision. The plan had evidence runs and gold authoring
sitting *inside* the implementation epics, so a single unlabelled gold set held six E2
tasks and, through the entry gates, most of E3 and EH1. That is backwards: measurement is
a consumer of implementation, not a prerequisite for it.

**The mechanism that makes the separation safe is `T2.95`'s serving gate: an evidence
record gates the *label*, never the *code*.** Every truth claim darkmem makes —
`corroborated`, `grounded`, span-supported — is refused at the serving boundary until the
corresponding record exists, and that refusal is scan-enforced rather than remembered.
So implementation can run arbitrarily far ahead of evidence without ever putting an
unbacked claim in front of a user; what ships before M1 simply ships **unlabelled**.

The precedent is already in the tree: `VerificationJudge.judge()` has refused
unconditionally without a qualification record since T2.26, and that never slowed T2.26's
own construction by a day.

## What is deliberately NOT here

Anything that shapes an implementation. If a measurement would change how a feature is
*built* rather than whether its label is *served*, it belongs in the implementation epic
with the feature — this epic is the consumer, and a consumer that feeds back into its
producer's design is not a separate phase at all.

---

## Tasks

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

#### T2.108 — A measurement corpus that can actually promote

`Model: Opus 5` · `Effort: high` · `Size: M` · `Depends: T2.10` · `Doc: 20 §4, 17 §11` · `Tag: target-new` · `Gate: G-C`

**Minted 2026-08-07 from the gate-ordering analysis, which found this is the long pole
under every option considered — and that no task owned it.**

T2.40's G-C run returned *not evaluable* on all four probes. The judge dependency gets the
attention, but it blocks **one arm of one probe**. The corpus starves **all four**: the
production `darkmem` journal holds 0 events, and the only existing corpus is structurally
incapable of promoting — all 62 facts are anonymous-origin, folding into the bucket that
counts once and can never fire a gate.

**And the production route is circular before the cutover.** Doc 17 §11's own sequencing
puts the homelab cutover *after* G-C and G-D, so "wait for real traffic" is not available
to a gate that must clear first. A purpose-built measurement corpus is the only
pre-cutover route to any G-C verdict at all.

**What.** A corpus that exercises the promotion ladder for real: facts reaching the
eligible population with **distinct `origin_key`s**, so `COUNT(DISTINCT origin_key)`
crosses the required N and promotions actually journal. Enough of them that G-C's
decidability thresholds are met — `promotion_rate_min_eligible` (5 per bucket) and
`false_promotion_min_corroborated` (20 in-window), both already committed in
`promotion_bars.py`.

**The trap this task exists inside.** A corpus built to make a gate clear is not evidence,
it is a fixture wearing evidence's clothes. What makes this admissible is that it must
exercise the *shipped* lift and the *shipped* recompute — T2.40's own run is the
precedent: 62 facts flowed end to end through the production path with 0 live model calls.
Hand-writing journal rows, or seeding `verification_status` directly, measures the
fixture. State plainly in the report which parts of the path the corpus drives and which
it stubs, because the gate's credibility rests entirely on that boundary.

**Done when:**
- [ ] Facts flow through the shipped lift and recompute — no hand-written `verified`
      events, no directly-seeded statuses
- [ ] Distinct `origin_key`s produce real promotions that journal, proven by a non-zero
      promotion count read back from `events` by SQL
- [ ] Both decidability thresholds in `promotion_bars.py` are met, so every probe that
      does not need the judge becomes decidable
- [ ] The corpus is reproducible from a committed definition, not a one-off database state
- [ ] The report states exactly what is driven and what is stubbed

**Verify.** `cd backend && python scripts/benchlib/run_promotion_metrics.py`

#### T2.107 — The resample sitting's instrument

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T2.54 (partial)` · `Doc: 17 §6, §11` · `Tag: target-new` · `Gate: G-D`

**Minted 2026-08-07 at the owner's request, to shorten the one step no agent may
perform.** T2.54's Layer-3 blind resample is the last outstanding clause on the gold set,
and it blocks G-D (T2.41) and — as T2.40's run established — G-C's false-promotion audit
as well.

**Most of the instrument already exists and is well built.** `resample_draw.py` has drawn
the sample (n = 93; full census of `contradicted` at 55, proportional `unsupported` 17 and
`entailed` 21), pinned its seed to the gold's own SHA-256 so it can be neither re-rolled
nor chosen, deliberately recorded no ids, and emitted a shuffled blind export at
`entailment/resample_blind.json` carrying only `id`, `premise`, `hypothesis`.

**What is missing is the return path.** `judge_qualification.py`'s lock requires
`gold_doc["resample"]` to carry `n`, `disagreements`, `seed`, `performed_by` and `date`,
and nothing computes or writes that block. So the owner can sit and label, and there is
no supported way to score the result.

**What.** Two pieces, and the discipline around them is most of the work:

1. **A readable sheet** generated from the existing blind export — 93 items, each with its
   premise, hypothesis and the `LABELLING.md` rule references a labeller needs, in the
   export's shuffled order, with a slot for one verdict per item. It must leak nothing the
   export does not already leak: no stratum, no neighbouring-item hint, no ordering signal.
2. **A scorer** that takes the completed verdicts, compares them against the stored gold,
   counts disagreements, and writes the `resample` block.

**Done when:**
- [ ] The sheet is generated from `resample_blind.json`, never from `gold.json` — proven
      structurally, so a future edit cannot reach the labels
- [ ] The scorer refuses when `gold.json`'s SHA-256 no longer matches the manifest's
      `gold_sha256`: the draw is pinned to one gold version, and scoring a stale draw
      certifies nothing
- [ ] The scorer writes `n`, `disagreements`, `seed` (from the manifest, never recomputed
      from a changed gold), `performed_by` and `date`, and `judge_qualification`'s lock
      accepts the block it writes — tested against the real lock, not a mock
- [ ] **A re-run cannot improve the number**: scoring is recorded once per draw, and a
      second sitting requires a new draw against a new gold SHA. State how this is enforced
- [ ] The disagreeing items are reported by id with both verdicts, since a miss is the
      instrument's most useful output — it localises where the rulebook is underspecified

**No agent labels any pair, in the sheet, the scorer, or the tests.** The resample is the
first accuracy measurement made from outside the family that labelled the set; an agent
supplying either side of the comparison destroys the only thing it measures. Test fixtures
use synthetic pairs, never the real gold's verdicts.

**Verify.** `cd backend && python -m pytest scripts/benchlib/tests/test_resample_draw.py scripts/benchlib/tests/test_judge_qualification.py -q`

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

#### T2.40 — G-C evidence run

`Model: Fable 5` · `Effort: xhigh` · `Size: M` · `Depends: T2.06, T2.09, T2.10, T2.11, T2.24, T2.51` · `Doc: 20 §4` · `Tag: target-new` · `Gate: G-C`

**Born-corroborated facts are invisible to this run, and that is by construction —
inherit it knowingly (recorded 2026-08-06 from T2.28's review).** T2.28's lift mints
code-originated facts already at `corroborated`, and its ladder branch **journals
nothing**, so those rows enter neither the numerator nor the denominator of the
promotion rate and never appear in the false-promotion audit. That was verified, not
assumed: the reviewer counted zero `verified` rows after a birth plus two recomputes,
and both metrics are journal-anchored in `benchlib/promotion_metrics.py`.

The consequence to state in the ledger rather than discover later: **once this run mints
the promotion record, born rows light `corroborated` on doc 10 §6's argument alone** —
*the parse is the verification* — and not on anything this gate measured. That is
exactly what the doc claims, and it may well be the right claim, since a parsed import
is not an inference. But G-C's number will be a statement about the *counting* ladder,
and the badge it unlocks will also appear on rows that ladder never counted. Say so
where the number is recorded.

**What.** Promotion rate `(promoted / eligible)` sliced by source-kind diversity and by
which N fired; false-promotion audit (corroborated facts later disputed or human-rejected)
under the stated bar; every ladder transition journaled.

**Done when:** all three measured from the `events` journal by SQL; bars stated as
`config` before measuring, not after; **facts have actually flowed through the ladder**
(a 0/0 promotion rate is under-powered, not a pass); verdict in `gate-ledger.md`;
`CLAUDE.md` refreshed to the shipped L2 shape; a miss leaves G-C open and the deriver
lane (T2.27–T2.28) closed.
**Verify.** `cd backend && python scripts/benchlib/run_promotion_metrics.py`

#### T3.24 — Coverage-distribution runner

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T3.03` · `Doc: 20 §4` · `Tag: target-new` · `Gate: G-E`

**What.** The plumbing behind T3.22's verify. Reports the **distribution** of per-article
claim-support coverage, not a mean — one well-covered article is not evidence.

**Done when:**
- [ ] Distribution reported with percentiles, not a summary statistic
- [ ] The production read is **read-only** (the sanctioned exception in runbook §8)
- [ ] Runs against a named snapshot so the number is reproducible

**Verify.** `cd backend && python scripts/benchlib/run_coverage_distribution.py`

#### T3.22 — G-E evidence run

`Model: Fable 5` · `Effort: xhigh` · `Size: M` · `Depends: T3.05, T3.06, T3.08, T3.23, T3.24` · `Doc: 20 §4` · `Tag: target-new` · `Gate: G-E`

**What.** L3 shipped **and** the per-article coverage distribution holding above the
runtime threshold in production — a distribution, not a single flattering article.

**Done when:** the coverage distribution is reported (not just a mean); the threshold
was stated before measuring; F7 shipped; verdict in `gate-ledger.md`; `CLAUDE.md`
refreshed to the shipped L3 shape. The production read is the one sanctioned exception
to "nothing automated touches `darkmem`" — it is **read-only** and may never write.
**Verify.** `cd backend && python scripts/benchlib/run_coverage_distribution.py`

---

## Lane H — added by review

#### TH1.17 — Faithfulness-gate runner

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: TH1.01, T2.26` · `Doc: 17 §6` · `Tag: horizon` · `Gate: G-F`

**What.** The plumbing behind TH1.10's verify, built by Sonnet so the Fable gate task only
designs the bar and reads the number (runbook §2).

**Done when:** scores span-support coverage against block-span entailment gold; reports
per-slice; emits its cost twin.
**Verify.** `cd backend && python scripts/benchlib/run_faithfulness_gate.py`

---

#### TH1.10 — Faithfulness ship gate (G-F evidence)

`Model: Fable 5` · `Effort: xhigh` · `Size: M` · `Depends: TH1.09, TH1.17` · `Doc: 20 §4, 17 §6` · `Tag: horizon` · `Gate: G-F`

**What.** Double duty: TH1.09 is the per-answer runtime gate; this is the **ship** gate.
The metric defined in TH1.01 must clear its bar on a labelled gold set before H1 ships.

**Done when:** measured on block-span entailment gold; the bar was set in TH1.01, before
the build; verdict in `gate-ledger.md`; `CLAUDE.md` refreshed for the documents/blocks
tables and the new jobs H1 ships; a miss leaves H1 unshipped.
**Verify.** `cd backend && python scripts/benchlib/run_faithfulness_gate.py`

---

## Lane D — proposition lifting (the vault bridge)

## Amendment log

| Date | Task | Tier | Change | Why |
|---|---|---|---|---|
| 2026-08-06 | T2.40, T2.41, T2.54, T3.22, T3.24, TH1.10, TH1.17 | 2 | **Epic created; all seven evidence-and-gold tasks moved here from E2, E3 and EH1, ids unchanged.** Ids keep their original epic prefix deliberately — every gate-ledger row, analysis and commit message in the tree already cites them, and renumbering would break that trail to buy nothing | Controller decision: implementation must not queue behind datasets. One unlabelled gold (T2.54) was holding six E2 tasks and, through the epic entry gates, most of E3 and EH1 — while 89 of 96 E2 tasks had already closed without any gold at all, which is the measurement that the coupling was accidental. Moving them out makes the dependency explicit rather than structural: M1 consumes implementation, never gates it. Safety is preserved by `T2.95`'s serving gate, not by ordering |
