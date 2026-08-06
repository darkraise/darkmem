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
