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

#### T2.116 — Bind the resample certification to the pairs it certified

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T2.107` · `Doc: 17 §6` · `Tag: target-new` · `Gate: G-D (produces)`

**Minted 2026-08-10 from the E3 branch review's triage, which ruled D-7 and D-8
"may stand" and then noted T2.115 had just paid their manual tax a third
time.** Both were parked twice as hardening on a lock whose current answer is
correct. That reasoning still holds and is not what mints this: the cost is now
measured at three rounds of the same manual step, and a procedure re-executed
correctly three times is a procedure waiting to be executed incorrectly once.

**D-7 — the eligibility lock does not bind the certification to pair content.**
`gate_eligibility` validates that the embedded `resample` block *says* n ≥ 93
with ≤ 1 disagreement and carries its citation fields. Nothing ties that
certification to the pairs it certified, so a post-certification label flip
keeps eligibility green on a certification of a different file. T2.110 and
T2.115 both handled it correctly **by procedure** — stripping the carried-over
block because the file had moved — which is the tell: the protocol already
understands what the code does not enforce. The slice-count pin catches
appends, not flips. `--from-raw`'s sha refusal covers the *raw* record and not
the embedded block.

**D-8 — the certification is written into `gold.json`, so the certified sha is
not the measured sha.** Reproduced again this round: certified `58ac1a90`
against an on-disk `98fc4b49`. Verified annotation-only each time, and the
attempt counter treats the new sha as uncontacted, which is the behaviour the
ledger's lineage note already describes. It is the same root as D-7 — a record
about a file, stored inside it.

**What.** Record a pairs-only content hash in the `resample` block and
re-derive it at eligibility time, so a certification names the pair set it saw.
That closes D-7 directly and makes D-8 a stated property rather than a footnote:
the certified sha may differ from the file sha, and the content hash is what
actually has to match.

**Done when:**
- [x] The block carries a hash over the pairs alone, excluding the block itself
- [x] `gate_eligibility` re-derives it and refuses a mismatch, with the refusal
      naming which pairs moved rather than only that something did
- [x] A label flipped after certification turns eligibility red — asserted by
      mutation, since this is the exact case the current lock passes
- [x] The existing certified gold re-certifies without a manual strip

**Landed 2026-08-12.** The basis is `entailment_gold.CERTIFIED_PAIR_FIELDS`
(`id`, `premise`, `hypothesis`, `verdict`) over the **live** population, folded
into one `pairs_sha256` through a per-pair digest map the refusal reads to name
what moved. Two design choices are pinned by mutation because both are
narrowings a later reader would be tempted to widen: hashing the whole pair
makes ordinary annotation churn indistinguishable from a label flip, and
hashing retired pairs turns an append to the archive red for a change that
moves no number the gate reads.

**The re-stamp was proved rather than asserted.** The existing certification
could only be carried forward honestly if the pairs had not moved since the
sitting, and that is checkable: the gold *minus its own resample block*
reproduces `58ac1a90`, the sha the draw manifest pinned, and the manifest's
seed is `int("58ac1a90", 16)`. So the draw, the sitting and the stamped basis
name one file state — and **D-8 is fully explained**: the certified sha differs
from the file sha because writing the certification into the file is what
changed it, not because anything was annotated.

**Verify.** `cd backend && python -m pytest scripts/benchlib/tests/test_judge_qualification.py scripts/benchlib/tests/test_entailment_gold.py -q`

**Not a G-D blocker.** The gold *is* eligible today, by a resample that did
happen, on the file as it stands. This is hardening the next round should not
have to do by hand.

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

#### T2.109 — The veto's two arms: ratify and rewire (G-D redesign)

`Model: Opus 5` · `Effort: xhigh` · `Size: L` · `Depends: T2.41` · `Doc: 08 §4.2, 17 §6, 20 §4` · `Tag: target-new` · `Gate: G-D` · `OWNER-GATED`

**What.** G-D was measured three times and does not clear; the resolution spike
(2026-08-08, recorded under G-D in `gate-ledger.md`) found the defect is not the model
and not the bar but **the veto's architecture** — the LLM judge is wired directly into
the absolute dispute veto and gated on precision alone.

**The coherence result that decides it, reproduced against the shipped scorer:** a judge
that says `contradicted` on exactly one correct pair — missing 54 of 55 — **passes all
three gated bars** (precision 1.0, recall 0.0182). Only total silence fails, and only via
the precision-is-None rule. The gate as specified qualifies a near-mute judge to hold an
absolute veto while failing the measured 0.88-precision / 0.95-recall one.

**Why not the other resolutions.** Not clearable: the two vendors' false positives
intersect on 3 pairs, so even a conjunctive two-vendor veto — the most precision-favouring
composition of every judge measured, fitted post-hoc — ceilings at 55/58 = 0.9483 at any
recall. Not the bar: 0.95 was *inherited* from the entailed bar (doc 17 §6's own words),
never derived from the veto's cost function, which argues the disputing consumer's bar
should be **higher**, since a scanned false dispute is near-permanent.

**Proposed shape (the owner ratifies; this task does not decide it).**
- The absolute veto stays on the **deterministic arm** — precise by construction, and no
  migration burden since the LLM arm has never fired.
- The LLM scan's finding **opens review instead of disputing**, which doc 08 §5.3's
  delay-not-manufacture asymmetry already licenses.
- The qualification metric pair **inverts**: recall becomes truth-critical, precision
  becomes a review-load floor.

**Done when:**
- [ ] The owner has ratified the design as a Tier-3 amendment to doc 08 §4.2 and doc 17 §6
- [ ] **New bars are stated by the owner before any measurement.** Both gpt-5.5 numbers
      are already public, so a bar chosen now by anyone who has seen them is fitted —
      this is why the spike deliberately proposed none
- [ ] Measured on **T2.54-grown gold**, not this one: it carries 3 contacts and its
      false-positive census is public
- [ ] The `disputed` rung, the demotion hysteresis and doc 08 §4.2's veto semantics are
      each shown to survive the rewire, or amended with it
- [ ] The G-C→G-D cross-edge is re-read under the audit's new shape — the machine-dispute
      arm's reachability changes if the LLM arm stops disputing

**Verify.** `cd backend && python scripts/benchlib/run_judge_qualification.py --gate`
after the rewire, against the grown gold.

---

#### T2.112 — Show the reviewer what was suspected

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T2.109` · `Doc: 08 §4.2, §6` · `Tag: target-new` · `Gate: standing`

**Minted 2026-08-08 from T2.109's own review.** The redesign moved the LLM contradiction
scan from disputing to opening review — but `review_queue._fact_reason` derives the
queue's reason from the fact's own columns (`verification_status`,
`demotion_pending_since`), and the suspicion is computed at recompute time from the scan's
journal and persisted nowhere. So a contradiction-suspected fact arrives in the queue
rendering `unspecified`: a healthy-looking row, no counterpart, nothing to adjudicate
against.

**Why this is not cosmetic.** The whole argument for the redesign is that a flag awaiting
human confirmation is a *delayed* dispute rather than a manufactured one — doc 08 §5.3's
sanctioned direction of error. That argument holds only if a human can actually confirm
it. A reviewer who cannot see which fact contradicts, or why, cannot confirm or dismiss,
so the flag is neither a dispute nor a delay — it is a fact stuck in a queue. The
half-shipped state is worse than either end: it consumes review attention and resolves
nothing.

**The evidence already exists**; only the path to the reader is missing. The scan writes
its counterpart and reason on its own journal row. Surfacing it costs either a journal
read on the queue query or a column on the fact row — a real trade (query cost against
schema, and the schema is still pre-freeze so a column is cheap *now* and not later).
T2.109 deliberately did not guess; it documented the gap at both sites.

**Done when:**
- [ ] A contradiction-suspected fact renders a reason naming the suspicion, not `unspecified`
- [ ] The counterpart fact is reachable from the queue entry, so the reviewer can compare
- [ ] The chosen path (journal read vs persisted column) is argued in the commit, including
      the pre-freeze schema consideration
- [ ] Confirming from the queue disputes through the existing `human_adjudication.reject_fact`
      door — no second write path
- [ ] Dismissing clears only this opener; `derive_review_state` stays total and the clear
      remains the absence of every opener

**Verify.** `cd backend && python -m pytest tests/test_review_queue.py tests/test_verification_ladder.py -q`

#### T2.113 — Make an unjournalled ladder transition impossible

`Model: Opus 5` · `Effort: high` · `Size: S` · `Depends: T2.111` · `Doc: 17 §5.1, 08 §6` · `Tag: target-new` · `Gate: G-C`

**Minted 2026-08-09 from T2.111's third vacuity clause, which it ruled OPERABLE AND
UNRESOLVED and which had no owner.** T2.40 stated the clause; T2.111 verified it in code and
found the remedy pattern already in the tree. Nothing owned closing it.

**The defect, verified rather than suspected.** `KnowledgeTripleRepository.set_verification_status`
ends with a bare `await record_event(...)` — return value not inspected, rows not counted
back — and `record_event` degrades loudly but **never raises into its caller**, by design, so
that a journal failure cannot take down a capture. The consequence here is different from the
one that design serves: the status UPDATE commits while the journal row silently does not, and
**every G-C metric reads `events` alone**. `ratify` has the same shape on the human-only rung.

**Why it is the one clause that matters.** An unjournalled transition does not show up as a
gap. It lands in the **denominator** — the completeness probe compares column state against
journal rows and would score a fact that never journalled as consistent, and the promotion rate
would divide by an eligible count that silently shrank. Under-power announces itself; this does
not. A future G-C run that *is* powered would therefore be untrustworthy for a reason no probe
in the suite can surface, which is why this blocks trusting the gate rather than merely
annoying it.

**The remedy already exists in this tree and should be copied, not invented.** `dream_undo`
counts its own `undone` rows back and raises when short, on the stated principle that "an undo
that could not be journalled does not happen". The same principle applies exactly: a ladder
transition that could not be journalled must not stand.

**Do not make `record_event` raise.** Its never-raising contract is load-bearing for capture,
extraction and auth, which must survive a journal failure. The asymmetry is the point — some
callers can lose a journal row and some cannot — so the signal has to be available to the
callers that care without changing what happens to the callers that do not.

**Done when:**
- [ ] A journal failure on a verification transition fails the transition, atomically — the
      status change and its `verified` row live or die together
- [ ] `record_event`'s never-raises contract is unchanged for every existing caller
- [ ] `ratify` carries the same guarantee as the machine journaller, or its exemption is argued
- [ ] The guarantee is pinned by a test that induces a real journal failure, not a mocked one —
      a mock proves the branch, not the property
- [ ] The operational cost is stated: a broken `events` partition now fails recomputes instead
      of degrading, and `events_ensure_partition`'s boot and maintenance arms are what bound it

**Verify.** `cd backend && python -m pytest tests/test_ladder_journaling.py tests/test_verification_ladder.py tests/test_events.py -q`

#### T2.110 — Grow the entailment gold past its contacted census

`Model: Fable 5` · `Effort: high` · `Size: L` · `Depends: T2.54` · `Doc: 17 §6, §11` · `Tag: target-new` · `Gate: G-D`

**Minted 2026-08-08 because T2.109 requires it and nothing owned it** — the same shape as
the measurement-corpus gap the gate-ordering analysis found in August: a precondition
written into one task's done-when and owned by no task.

**What.** Additional labelled pairs under T2.54's full discipline, so G-D's re-measure has
an uncontaminated surface to run on.

**Why growth, precisely.** Not for headroom — that reasoning is wrong and should not be
repeated. Three runs failed on an FP *rate* (7–13 false positives), and a larger gold with
the same rate fails identically; only the resolution improves. The reason is
**contamination**: this gold carries three `gold_touching_attempts`, and its false-positive
census is now public in the ledger, in T2.41's commits and in the resolution brief. A
prompt or design change measured against pairs whose failure modes are written down is
fitted to them, which is exactly the loop T2.26's plan review flagged as its one Critical.

**The authoring constraint that makes it worth doing.** The new pairs must be authored
**without reading the judge's recorded failure census.** That census lives in
`gate-ledger.md`'s G-D sections and in `briefs/2026-08-08-gd-resolution-spike.md`; it names
the failing pair ids and the slice-level profile, and this task deliberately **does not
reproduce them here** — the first version of this paragraph did, which made a document
stating a blindness requirement the fastest way to destroy it. An author who knows the judge
over-calls contradiction on non-exclusive reversals and writes more of them is building a
targeted test, not a gold. Separate owner, adversarial review, blind adjudication — the
T2.54 pattern, for the same reason it existed there.

**Blindness here is partial, and saying so is part of the task.** A gold author must read
`LABELLING.md` to author anything, and that file necessarily cites pair ids as worked
examples of its rules — one of which is also in the judge's failure set. So the achievable
property is not "the author has seen no failing pair" but **"the author has not seen the
judge's failure *profile*"**: which verdict it over-calls, on which relation classes, at
what rate. That is what makes targeted authoring possible, and that is what must stay
unread. Record the residual rather than claiming a blindness the task does not have.

**Composition still binds** (doc 17 §11): ≥ 50% `l2-fact` premises anchored to committed
manifest rows, verdict/slice lawfulness enforced by the loader, and the declared counts
recomputed rather than hand-maintained.

**If T2.109 lands first, the target composition changes.** Under the proposed redesign the
metric pair inverts — recall becomes truth-critical — so the `contradicted` census is the
population that needs growing most, not the `entailed` one. Read T2.109's ratified shape
before fixing the targets.

**Done when:**
- [ ] Pairs authored blind to the recorded failure census, by an owner who has not read it
- [ ] §11 composition holds on the grown set, recomputed not asserted
- [ ] The blind resample is **re-drawn** — the draw is pinned to `gold_sha256`, and growth
      moves it, so the recorded resample does not carry over
- [ ] `gold_touching_attempts` resets with the gold file, and the report says so
- [ ] The grown gold's own eligibility passes `judge_qualification.gate_eligibility`

**Verify.** `cd backend && python -m pytest scripts/benchlib/tests/test_entailment_gold.py scripts/benchlib/tests/test_judge_qualification.py -q`

#### T2.115 — Resize the never-contacted contradicted census

`Model: Fable 5` · `Effort: high` · `Size: L` · `Depends: T2.110` · `Doc: 17 §6, §11` · `Tag: target-new` · `Gate: G-D`

**Minted 2026-08-10, Tier-2 amendment: the plan had no task for a granularity finding the
2026-08-08 re-measure recorded and asked the owner to settle.** Rule B's never-contacted
subset holds 25 contradicted pairs, so its recall lattice is 1.00 / 0.96 / 0.92 — **0.95 is
not on it** — and "the gate verdict required to hold on both" therefore makes the subset
enforce ≥ 0.96 where the pooled census permits four misses in 80. It did not bite the last
run (23/25 fails either way); a run landing on 24/25 would be passed by the stated bar and
failed by the lattice.

**Owner ruling 2026-08-10: resize so 0.95 lands on the subset's lattice, then let it gate.**
Two derivations shape the round and are recorded in the plan: 0.95 cannot be exact on *both*
populations (contacted contradicted is 55, and `N ≡ 0` with `55 + N ≡ 0 (mod 20)` has no
solution), and the census cannot simply grow because the Layer-3 resample's first stratum is
a **full census** of `contradicted` at a ratified `n = 93`. So the only route that changes
nothing ratified is **retire-and-replace at a constant pooled census**: contacted 55 → 40,
never-contacted 25 → 40, pooled held at 80, resample unchanged.

**What.** Execute the step-level plan at
`docs/superpowers/plans/2026-08-10-entailment-gold-subset-resize.md` (runbook §3), whose
step 0 is the owner's ratification of a new **lattice-retirement** rule — retiring a
*correctly labelled* pair for census shape has no precedent, and the rule's whole content is
the four conditions that keep the act content-blind.

**The firewall is the part most likely to be got wrong.** The controller that wrote the plan
has read the G-D slice-level failure attribution and is therefore barred from authoring;
authoring runs in a sub-agent forbidden the ledger, the qualification reports and
`resample_runs/`, and the slice quotas are derived mechanically so the brief itself cannot
leak the failure.

**Done when:** the subset's contradicted census is 40 and pooled is still 80; the retirement
draw is reproducible from the recorded seed; every new pair is `adjudicated` or `owner`; a
fresh `n = 93` resample certifies the new sha; **the boundary constant does not move** —
only LABELLING.md's range *text* extends its end, which the pinned test recomputes.
*(Corrected 2026-08-10, branch review M-1. This clause read "`NEVER_CONTACTED_FIRST_ID` and
LABELLING.md's range move together", which owner ruling R3 reversed during execution: the
constant stays `eg-0242`, and it was renamed `RULE_B_FIRST_ID` because "never contacted"
stopped being true of that population. The done-when went on asserting the pre-ruling
behaviour, so the task text contradicted the ratified rule it was executed under.)*
*Deliberately excludes the G-D re-measure — it spends an attempt from a budget keyed on the
gold sha, and running it from the session that authored the pairs is the contamination this
round exists to escape.*

**Verify.** `cd backend && python -m pytest scripts/benchlib/tests/test_entailment_gold.py -q`
and `./scripts/gate.sh --full`

#### T2.111 — G-C re-measure under the veto's ratified shape

`Model: Fable 5` · `Effort: xhigh` · `Size: M` · `Depends: T2.108, T2.109, T2.110` · `Doc: 20 §4, 17 §5.1` · `Tag: target-new` · `Gate: G-C`

**Minted 2026-08-08 because T2.40 is closed and nothing owns re-running it.** T2.40
recorded the verdict *not evaluable* and carries three clauses binding "this re-measure" —
but a `done` task cannot be the thing that re-runs, so those clauses had no owner.

**What.** Re-run G-C's four probes and record a verdict, against T2.108's corpus and
whatever arm structure T2.109 ratifies.

**Rule on all three vacuity clauses before recording any verdict** (they are stated in
full under T2.40, and they are cumulative, not alternatives):
1. The false-promotion audit reads *decidable, clears* at 0.0000 while its numerator is
   structurally zero — `audit_clears` cannot distinguish precision from inoperability.
2. Probes 1–2 carry a weaker form: `blocked ≡ 0` is data-precluded, so `slice_clears`
   reads True with its failing direction unreachable.
3. The substrate itself may be incomplete: `record_event` never raises and
   `set_verification_status` never counts its rows back, so the ladder can move while the
   journal records nothing — degrading the *denominator* without announcing under-power.

**The redesign may change the audit's shape, not merely unblock it.** G-C's machine-dispute
arm counts `disputed` transitions. If T2.109 moves the LLM scan from disputing to opening
review, that arm's population changes at the source — the audit may need re-deriving rather
than re-running, and the human-rejection arm's relative weight rises. Establish which
before measuring; a probe carried over unexamined would be measuring the old architecture.

**Done when:**
- [ ] All three vacuity clauses ruled operable or vacuous, with the reasoning recorded
- [ ] The audit's numerator arms re-derived against the ratified arm structure
- [ ] Every metric from `events` by SQL; no hand-written journal rows
- [ ] The verdict recorded whether or not it clears — a miss is the result, not a failure
- [ ] `app/services/promotion_metrics_record.json` minted **only** on a cleared verdict,
      deliberately, never as a side effect of measuring
- [ ] The G-C→G-D cross-edge re-read and its ledger wording corrected if the redesign
      changed what it binds

**Verify.** `cd backend && python scripts/benchlib/run_promotion_metrics.py`

#### T2.114 — G-D third-vendor attempt

`Model: Fable 5` · `Effort: xhigh` · `Size: M` · `Depends: T2.109, **an owner-recorded argument**` · `Doc: 17 §6, 20 §4` · `Tag: target-new` · `Gate: G-D (produces)`

**Minted 2026-08-09 at the owner's instruction. It must not run until the
argument below is written down, and that is the whole point of the task.**

**What.** One further judge-qualification run against the **frozen** prompt on a
third vendor, scored by the existing runner on the existing gold.

**Attempted 2026-08-10 under an owner delegation, and NOT resolved — the
attempt itself is recorded because it sharpened the task.** The assistant
argued that no selection existed to make: attempt 1 on gold `98fc4b49` used
`deepseek-v4-flash`, only one other model carries a qualification record, so
"a different judge model" had one referent and a choice among one option cannot
be a fit. A Fable-tier review refuted it and the refutation was accepted. The
eligibility filter — *"already carries a qualification record"* — appears
neither here nor in doc 17 §6; it was invented, and it is precisely what
shrinks the set to one. **`deepseek-v4-pro` is a reachable, credentialed,
different model.** Excluding it is defensible (it sat the Layer-3 resample, so
judge and certifier would be one model) but making that argument *is* the
judgment the draft claimed did not exist — made by a party that had read both
judges' scores.

**So the option set is now known to be at least {`gpt-5.5`, `deepseek-v4-pro`},
with v4-pro carrying the resample-circularity objection.** That is the one thing
the failed attempt leaves behind, and it narrows the owner's three sentences
rather than supplying them. Note also that "the two measured judges" is the
honest phrase and "already-qualified" is not: **no judge has ever qualified** —
both carry failed records.

**OWNER RULING 2026-08-10: the model is `gpt-5.5`.** Recorded verbatim as the
owner's; this session may not embellish it into a rationale, because the whole
evidential value of the choice is that it was made by the party that had not
been reasoning from the scoreboard. What the record may state without supplying
the owner's reasons: `gpt-5.5` is one of the two models carrying a `verification`
qualification record, and the alternative reachable model, `deepseek-v4-pro`,
carries the objection that it sat the Layer-3 resample and would make judge and
certifier one model.

**Stopping rule, stated here in advance and binding regardless of outcome.**
This is the **final** judge attempt on this gold. On a miss, G-D is recorded NOT
CLEARED and no further model is tried on that sha; the only remaining moves are
a new gold justified on grounds that do not cite this result, or a bar argument
that does not cite it either. A maximally-binding stopping rule is the one part
of this a contaminated party may write, because it cannot be selected for its
effect on the outcome — it forecloses every branch equally.

**This session must not run it.** Contaminated for the fitting rule, and it
authored the surrounding work. Dispatch to a fresh session.

**~~A second gate now sits in front of this task (ruling R-B, 2026-08-10):~~
LIFTED 2026-08-12.** The owner ruled that census independence is handled by
**reporting** the duplicates rather than retiring them, because executing R-B
would have raised the binding contradiction-recall bar to 37/38 = 0.9737 by
arithmetic alone. Every run now discloses 80 rows over 78 independent
propositions, names the duplicates, and flags a row-pass the independent
reading would fail. The superseded text follows, for the record: no
judge attempt may run on `98fc4b49` until the two contradicted duplicate
propositions (`eg-0093`/`eg-0367`, `eg-0194`/`eg-0251`) are retired and the gold
re-certified. Rule B's attempt-1 pass was exactly 38/40 = 0.9500, and both
duplicates sit in its population, so spending the final attempt before the
repair is the one ordering that could manufacture an edge pass from a defect
already on the record.

**Why this needs a recorded argument before it runs.** T2.41 used doc 17 §6's
sanctioned remedy once (deepseek → gpt-5.5) and then **stopped at two on
purpose**: "an open-ended sweep until one clears is tuning-against-gold by
another route." A third attempt is not forbidden — it is the same sanctioned
remedy — but nothing distinguishes "a third vendor, for a stated reason" from
"the third draw of a sweep" except the reason, written before the run. So the
owner records: which vendor, why that one, and what result would end the search
rather than extend it. Without those three the task stays `blocked`; an agent
may not supply them, because supplying them is the fitting doc 17 §6 forbids.

**What must not move.** The prompt (`prompt_sha` is part of the judge identity —
editing it de-qualifies mechanically), the gold, and both bars. The two
measured judges' results are already public, so any bar moved after this run
would be a fit against three known outcomes rather than a derivation.

**What the run costs, stated so the decision is informed.**
`gold_touching_attempts` counts gold CONTACTS for this `gold_sha256` across all
judge identities — a warm verification rerun increments it too — so this
attempt is permanently visible in the ledger whatever it returns.

**An environmental precondition, not a formality.** This machine holds
credentials for DeepSeek and a LAN Ollama (embeddings only, no judge). Attempt
two ran on `gpt-5.5`. A third vendor needs a reachable endpoint and a key that
exists before the task is claimed; the seed rows are inline
`llm_purpose_configs`, so pointing `verification` at a new vendor is a config
write, not a code change — but a vendor whose `api_kind` has no quirk row is
the four-step rule in doc 11 §4, which is a code change.

**Done when:** the argument is recorded in this task's own row *before* the run;
the run is scored by the unmodified runner on the unmodified gold; the verdict —
cleared **or** a measured miss — is recorded in `gate-ledger.md` beside the
other two; and the search's stopping condition is stated as met or not.
**A miss is the result, not a failure, and does not authorise a fourth attempt.**

**Verify.** `cd backend && python scripts/benchlib/run_judge_qualification.py`

---

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

`Model: Fable 5` · `Effort: xhigh` · `Size: M` · `Depends: T2.06, T2.09, T2.10, T2.11, T2.24, T2.51, **T2.41 passing**` · `Doc: 20 §4` · `Tag: target-new` · `Gate: G-C`

**The false-promotion audit probe requires T2.41 to have *passed*, not merely run —
ratified into doc 20 §3 on 2026-08-07.** The audit's machine-dispute arm reaches
`VerificationJudge.judge()`, which refuses unconditionally without a qualification record
that only a cleared G-D mints, and the binding is to the *currently configured judge
identity*, so a G-D miss keeps the arm dark until a model or prompt change re-qualifies.
The dependency is narrow by design: it binds this one arm. The human-rejection arm is
live with no judge on its path (`human_adjudication.reject_fact` accepts any fact id and
journals `human_verdict`), and the other three probes need only a promotable corpus — so
a run before T2.41 passes can measure everything except a systematic false-promotion
number, and must not record a full G-C verdict on that basis.

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

**A decidable number is not automatically a meaningful one — established 2026-08-07 by
T2.108 and confirmed on data by its adversarial review.** With a corpus that actually
promotes (31 facts, all three gate buckets), the false-promotion audit reads *decidable,
clears* at rate 0.0000 — and that reading is **vacuous**, because the numerator is
structurally zero rather than measured. All three legs verified: no qualification record
exists so `VerificationJudge.judge()` raises unconditionally; `SINGLE_VALUED_RELATIONS`
is empty (`contradiction_veto.py:104`) and the corpus's stored `rel_type`s carry no
REPLACES-family edge, so the deterministic arm never arms; and there are zero
`human_verdict` events. `audit_clears(0.0, 31)` returns True and **cannot distinguish
precision from inoperability.**

The review sharpened it twice, and both sharpenings survive attack: the vacuity is a joint
bar-plus-corpus property — an inverse-REPLACES corpus could drive machine disputes
judge-free — but **no corpus in the 20–99 band can be both operable-numerator and passing
under the strict 1% bar**, so the defect attributes to the bar. Probes 1–2 carry a weaker
form of the same shape: `blocked ≡ 0` is data-precluded, so `slice_clears` reads True with
its failing direction unreachable. The asymmetry matters — probes 1–2's decidability
carries earned content (31 journaled promotions where the first run had zero), the audit's
carries none of its numerator's operability.

**This re-measure must rule on that before recording any verdict**, and rule on both
instances under one lens. A gate that clears on a number which cannot fail is the shape
doc 20 §4's "no layer advances on intuition" exists to forbid.

**A third instance, and the clause must absorb it (E2 whole-branch review, 2026-08-08,
silent-success lens).** The vacuity above is about the numerator; this one is about the
substrate. `record_event` never raises by design (`events.py`), and
`set_verification_status` — the journaller for every rung the ladder moves
(`knowledge_triples.py`) — never counts its row back. Every G-C metric is SQL over
`events` alone, and nothing reconciles rung state in `knowledge_triples` against the
journaled transitions. So a broken or missing monthly partition lets the ladder move
while the measurement substrate records nothing, and every probe reads clean over a
journal that is silently short. That is a second route to "the audit reads clean while
measuring nothing", independent of the numerator argument, and it degrades the *denominator*
rather than the numerator — so it does not announce itself as under-powered either.
**The re-measure must therefore prove its substrate complete before reading any number
off it**, not merely rule the numerator operable. The codebase already owns the pattern:
`dream_undo` counts its journal rows back and raises when short.

**Done when:** all three measured from the `events` journal by SQL; bars stated as
`config` before measuring, not after; **facts have actually flowed through the ladder**
(a 0/0 promotion rate is under-powered, not a pass); **each probe's decidability is ruled
operable or vacuous, with the reasoning recorded** (above); verdict in `gate-ledger.md`;
`CLAUDE.md` refreshed to the shipped L2 shape; a miss leaves G-C open and the deriver
lane (T2.27–T2.28) closed.
**Verify.** `cd backend && python scripts/benchlib/run_promotion_metrics.py`

#### T3.24 — Coverage-distribution runner

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: T3.03` · `Doc: 20 §4` · `Tag: target-new` · `Gate: G-E (produces)`

**What.** The plumbing behind T3.22's verify. Reports the **distribution** of per-article
claim-support coverage, not a mean — one well-covered article is not evidence.

**Done when:**
- [x] Distribution reported with percentiles, not a summary statistic
- [x] The production read is **read-only** (the sanctioned exception in runbook §8)
- [x] Runs against a named snapshot so the number is reproducible

**Verify.** `cd backend && python scripts/benchlib/run_coverage_distribution.py`

**Landed 2026-08-12.** `coverage_distribution.py` (the metric) plus
`run_coverage_distribution.py` (the runner), split the way `promotion_metrics`
splits for G-C: this states no verdict, because T3.22 owns G-E's. Percentiles
are **nearest-rank over actual observations** — an interpolated p90 at these
article counts is a coverage no article has, and G-E asks how many *articles*
clear the bar.

**Unmeasured is not zero** is the module's spine, inherited from T3.03 rather
than re-decided: `knowledge_articles.confidence` is the coverage column and is
written only on a measured outcome, so NULL means the entailment pass reached
no verdict — a refusing judge, an outage and an invalid verdict all land there,
and none is evidence an article is ungrounded. Unmeasured articles are counted
as their own population and never folded in as zeros. That is the standing case,
not a corner: G-D is open, so **every article on every install is unmeasured**,
and a first run says *not evaluable* exactly as T2.40 did for G-C.

The read-only claim is **proved, not asserted** — a bench-DB test attempts a
real INSERT through the same `default_transaction_read_only=on` connection and
asserts Postgres refuses it. Reproducibility rides a caller-named snapshot plus
a `population_sha256` over the (id, coverage) pairs, unmeasured articles
included, so two runs reporting the same share can be shown to have read the
same corpus.

**First run against production, 2026-08-12:** `darkmem`, schema present, **0
live articles**, not evaluable. Recorded at
`docs/eval/2026-08-12-coverage-distribution.md`.

#### T3.22 — G-E evidence run

`Model: Fable 5` · `Effort: xhigh` · `Size: M` · `Depends: T3.05, T3.06, T3.08, T3.23, T3.24` · `Doc: 20 §4` · `Tag: target-new` · `Gate: G-E (produces)`

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

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: TH1.01, T2.26` · `Doc: 17 §6` · `Tag: horizon` · `Gate: G-F (produces)`

**What.** The plumbing behind TH1.10's verify, built by Sonnet so the Fable gate task only
designs the bar and reads the number (runbook §2).

**Done when:** scores span-support coverage against block-span entailment gold; reports
per-slice; emits its cost twin.
**Verify.** `cd backend && python scripts/benchlib/run_faithfulness_gate.py`

---

#### TH1.10 — Faithfulness ship gate (G-F evidence)

`Model: Fable 5` · `Effort: xhigh` · `Size: M` · `Depends: TH1.09, TH1.17` · `Doc: 20 §4, 17 §6` · `Tag: horizon` · `Gate: G-F (produces)`

**What.** Double duty: TH1.09 is the per-answer runtime gate; this is the **ship** gate.
The metric defined in TH1.01 must clear its bar on a labelled gold set before H1 ships.

**Done when:** measured on block-span entailment gold; the bar was set in TH1.01, before
the build; verdict in `gate-ledger.md`; `CLAUDE.md` refreshed for the documents/blocks
tables and the new jobs H1 ships; a miss leaves H1 unshipped.
**Verify.** `cd backend && python scripts/benchlib/run_faithfulness_gate.py`

---

## Lane M — the per-role qualification split (v0.5)

Minted 2026-08-12 from
[`docs/superpowers/specs/2026-08-12-v0.5-per-role-qualification-and-corpus-design.md`](../../superpowers/specs/2026-08-12-v0.5-per-role-qualification-and-corpus-design.md),
owner-ratified rulings R1–R4, after an independent Fable review of the spec.

#### T2.121 — Correct the contradiction-recall derivation in the ledger

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: —` · `Doc: 17 §6` · `Tag: target-new` · `Gate: —`

**What.** Ruling R3. A session proposed re-deriving `contradiction_recall_bar` from 0.95
to 0.90 on the argument that a post-T2.109 recall miss costs an unopened review item
rather than a wrong belief. **That derivation is wrong and is rejected.** A recall miss is
a genuinely contradicted fact keeping `corroborated`, keeping a badge asserting no known
contradiction, and staying citable by articles — a standing wrong belief with no backstop,
since the human-verdict arm is the scan's only route into the audit and the deterministic
arm is corpus-vacuous. A precision miss is bounded by a reviewer's dismissal.

Record it rather than dropping it quietly, because at 0.90 the 2026-08-10 deepseek
attempt clears **all four bars on both populations** (contradiction recall 0.9375 pooled /
0.9500 Rule B; `gate-ledger.md:1123-1127`) — the proposal would have converted a recorded
miss into a retroactive pass, and the same derivation must not resurface at the next gold
looking new.

**Done when:** the gate ledger carries the rejection with the retroactive-pass arithmetic
shown; `gate-ledger.md:1344`'s loose phrase (*"the amendment is what made recall
truth-critical"*) is refined to what actually changed — **precision left** the
truth-critical class, leaving recall the only truth-side metric on that arm, same bar,
cleaner reason; no bar value moves anywhere.
**Verify.** `cd backend && python -m pytest tests/test_planning_docs.py -q`

---

#### T2.122 — The verdicts directory leaks synthetic files under real identities

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: —` · `Doc: 17 §6` · `Tag: target-new` · `Gate: —`

**What.** Measured 2026-08-12: `backend/scripts/benchlib/entailment/verdicts/` holds 80
files and **79 are synthetic residue**. Seven carry the real gold's exact shape (173
entailed / 80 contradicted), the real deepseek identity `4d886440`, and real gold shas
including the current `6eadba73` — one is named `2026-08-12-4d886440-6eadba73.json`,
precisely how a genuine deepseek run on today's gold would be named — with entailed
precision 0.3731 against deepseek's published 0.9938. Files accumulate across 08-10 (25),
08-11 (20) and 08-12 (36), so the leak is **active**. `VERDICTS_DIR` is a module-level
constant used directly at `run_judge_qualification.py:397` with no override, so anything
driving the runner to scoring completion writes into the live artifact directory under
real identities. The directory is gitignored (`.gitignore:29`) and no checksum of the
genuine artifact is recorded anywhere.

This is a precondition for T2.119, not housekeeping: a mint path whose input directory
cannot distinguish evidence from residue puts *"minted only by a cleared run, never by
hand"* one text-editor session from being violated undetectably.

**Corrected 2026-08-12 during execution (amendment log): a recursive audit found 16 more
residue files in a previously undocumented `verdicts/verdicts/` subdirectory. The real
count is 96 files, 95 residue, 1 genuine, not 80/79** — see
`docs/eval/2026-08-12-verdicts-directory-residue-removed.md` for the full identification.

**Done when:** the writer takes an output-directory override and every test path uses a
temporary one; a regression test fails if a test run can write into the real directory;
the 79 residue files are removed with their identification recorded (identity, gold sha,
pair count, measured metrics) so the deletion is auditable; the genuine artifact's sha256
is recorded outside the artifact — in its eval report and the ledger.
**Verify.** `cd backend && python -m pytest scripts/benchlib/tests/test_judge_qualification.py -q`

---

#### T2.118 — Duplicate/independence pass over the non-contradicted census

`Model: Fable 5` · `Effort: xhigh` · `Size: S` · `Depends: —` · `Doc: 17 §6` · `Tag: target-new` · `Gate: —`

**What.** Every census scrutiny this gold has received — Rule B, the duplicate findings
(`eg-0093`/`eg-0367`, `eg-0194`/`eg-0251`), the reproduced-retirement defect — examined
the **contradicted** side. Whether the 322 entailed/unsupported pairs (173 + 149, counted
from the per-pair artifact) carry comparable duplicate or independence defects is
**unknown**. R1 makes the entailment pair the thing G-D gates on, so that unknown moves
from a footnote onto the gate's critical path.

**Independence is a hard requirement:** this must be executed by an agent that did not
author the census. Run the same duplicate-detection pass the contradicted side received.

**Done when:** the 322 pairs are checked for full-text and near-duplicate reproduction and
for independent-proposition count the way the contradicted census was; the minimum passing
fraction is stated on both the rows reading and the independent-propositions reading, as
the ruled disclosure requires; findings are recorded in `gate-ledger.md` whether clean or
not — a clean report is the result that unblocks T2.119, and a defective one is a finding,
not a failure to finish.
**Verify.** the report lands in `gate-ledger.md` with per-pair evidence; no gold file is
edited by this task.

---

#### T2.120 — `SINGLE_VALUED_RELATIONS`: the per-relation argument

`Model: Fable 5` · `Effort: xhigh` · `Size: M` · `Depends: —` · `Doc: 08 §4.2` · `Tag: target-new` · `Gate: —`

**What.** Ruling R4. Eight of the nine pooled contradiction-recall misses are
`value-swap` — *a different value in a slot the premise fills exclusively* — at slice
recall 0.810. That is exactly the class the deterministic `single_valued` detector exists
for, disarmed today only because `SINGLE_VALUED_RELATIONS` is an empty frozenset
(`contradiction_veto.py:114`, reasoning at `:28-31`). Populating it adds true detection
capacity where the LLM judge measurably fails, with no model, no gold, no bar and no judge.

**That is also the whole risk.** This arm feeds the **absolute veto**, sanctioned only
because its precision is by construction. A relation belongs in the tuple only if the
taxonomy guarantees at most one object per subject; a wrong inclusion manufactures
near-permanent disputes on an unappealable instrument.

**Done when:** every relation in `RELATIONSHIP_TYPES` carries a recorded admit/reject
argument against the at-most-one-object-per-subject test; only survivors enter the
frozenset; rejections and their reasons are recorded with them;
**empty-after-analysis is a legitimate outcome** and must not be argued around; the
detector's existing guards are re-read before any admission.
**Verify.** `cd backend && python -m pytest tests/test_contradiction_veto.py -q`

---

#### T2.123 — The independence disclosure counts findings, not propositions

`Model: Sonnet 5` · `Effort: high` · `Size: S` · `Depends: —` · `Doc: 17 §6` · `Tag: target-new` · `Gate: —`

**What.** Found by T2.118. `census_independence` in
`backend/scripts/benchlib/judge_qualification.py` computes
`independent = len(rows) - len(dupes)`, where `dupes` are the **pairwise findings**
`find_duplicate_propositions` returns. A duplicate *component* of k rows yields
`k·(k-1)/2` findings but collapses only `k-1` rows, so the two agree only while every
component is exactly two rows wide — which is true of the contradicted census and **false
of the entailed one**, where T2.118 found a three-row component
(`eg-0094`/`eg-0279`/`eg-0323`). The entailed census prints 166 independent propositions
where the true count is 167.

The error is conservative — it under-reports independence, so the disclosed minimum pass
reads slightly harder than it is — which is the safe direction and is why this is a defect
rather than an incident. It is still wrong, and it sits on the disclosure path R2's mint
must print for a class whose components are not all two wide.

**Done when:** independence is counted by **connected component** (union-find or
equivalent over the findings), not by finding count; a regression test pins a three-row
component at `k-1`; the contradicted census's published figure (80 rows over 78
propositions) is unchanged by the fix, proving the correction is confined to the case that
was wrong; the entailed census prints 167.
**Verify.** `cd backend && python -m pytest scripts/benchlib/tests/test_judge_qualification.py -q`

---

#### T2.117 — Per-role qualification records

`Model: Opus 5` · `Effort: high` · `Size: M` · `Trigger: the owner's holdings on spec open questions 3 and 4` · `Doc: 17 §6, 20 §4` · `Tag: target-new` · `Gate: —`

**What.** Ruling R1. `VerificationJudge.judge()` is one gate over all four `BAR_METRICS`
(`verification_judge.py:222-227`, refusal at `:135-161`, bar loop at `:324-333`) serving
two consumers that ask different questions: claim entailment for articles
(`claim_entailment.py:222`, branching on `ENTAILED` alone at `:251`) and the Tier-C
contradiction scan (`contradiction_scan.py:754`, branching on `contradicted` alone at
`:774`). Each consumer's gate depends on a discrimination it never makes, in both
directions. Split the **record** by consumer role, keeping one judge identity.

The grounds are doc 20 §4's ratified registry — which already defines G-D as *"the
groundedness judge's precision/recall at distinguishing grounded from ungrounded
sentences"*, the contradiction pair having entered through one inheritance sentence at
`17-test-and-eval-harness.md:147` — and the code-forced pairing. **The amendment must be
writable from those two inputs alone**; if it reaches for a measured value it is not a
derivation.

**Waits on the owner, not on work.** Q3: is this a distinct structural move rather than a
third attempt in disguise? Q4: R1 composed with R2 makes the run recorded NOT CLEARED the
run whose verdicts mint the redefined gate's record — is that composition intended? Both
holdings are recorded *in* the amendment.

**Done when:** the split is symmetric — each role gated on the discrimination its consumer
makes; contradiction bars unchanged at 0.95 / 0.70 and that role left unqualified, so the
Tier-C scan keeps dead-ending; doc 17 §6 and doc 20 §4 amended, with §6's
rejected-alternatives clause (*"Per-consumer judges (three purposes, three models) … three
drift independently"*, `:161`) **named and distinguished** — R1 keeps one identity and
splits the record, but roles do now hold qualification state independently, and an
amendment silent on that is not honest; a **scan-enforced pin** that `claim_entailment`
consumes only the entailed discrimination and `contradiction_scan` only the contradicted
one, machine-checking the derivation's premise the way the second-RRF-constant scan does;
the owner's Q3/Q4 holdings recorded; the T2.114 stopping rule left intact — no model
touches pair set `4975c5cc`.
**Verify.** `cd backend && python -m pytest tests/test_verification_judge.py tests/test_claim_entailment.py -q`

---

#### T2.119 — Offline per-role re-score and mint

`Model: Fable 5` · `Effort: xhigh` · `Size: S` · `Depends: T2.117, T2.118, T2.122, T2.123` · `Doc: 17 §6` · `Tag: target-new` · `Gate: G-D (produces)`

**What.** Ruling R2. An evidence record is *"minted only by a cleared run, never by hand"*
(T2.95/T2.100), so R1 alone strands the entailment role. Amend
`run_judge_qualification.py` to re-score a recorded per-pair verdict artifact under a
named role and mint that role's record if its bars clear — zero live calls, zero gold
contact, the offline-replay precedent the G-D resolution spike set.

**Only one input is admissible.** No genuine deepseek per-pair artifact exists; every
deepseek-identity file in the directory is residue (T2.122). The admissible input is
`2026-08-12-fd39e7b2-6eadba73.json` (`gpt-5.5`, `fd39e7b2c47fa375`), and production's
`verification` purpose must carry that identity or `qualification_state` fails closed on
mismatch — doc 17 §6: *"re-qualification after a `verification`-purpose model swap is
mandatory."*

**Executed by a fresh session that did not author T2.117's split** — the separation-of-
powers norm binds a mint harder than a census pass — and reviewed adversarially at Fable
tier under runbook §6, since it feeds a gate claim.

**Carry T2.118's finding.** The entailed census is not clean: five duplicated
propositions over seven findings, one component three rows wide, and five of Rule B's 72
entailed rows restate propositions the judge met in the contacted population. None of it
threatens the verdict — measured entailed recall 0.9827 sits far above the minimum pass on
either reading (156/173 rows, 151/167 independent) — but the 2026-08-12 independence ruling
names only the **contradicted** class, so extending the disclosure to the entailment class
is this task's obligation and not an assumption T2.118 could make.

**Done when:** the input is **authenticated** — admissible only if it reproduces the
ledger's published metrics for that identity and gold (0.9884 entailed precision / 0.8875
contradiction recall), which every residue file fails by orders of magnitude; the minted
record names its input's sha256; the warm-replay caveat rides the record where the number
lives (338 of 402 verdicts are replays of the 2026-08-08 contact; only the 64 live ones
are a genuine 2026-08-12 sitting); the run makes zero live model calls; and the verdict —
G-D as redefined, cleared or not — lands in `gate-ledger.md` with the composed-question
holding cited.
**Verify.** `cd backend && python -m pytest scripts/benchlib/tests/test_judge_qualification.py -q`

---

## Lane D — proposition lifting (the vault bridge)

## Amendment log

| Date | Task | Tier | Change | Why |
|---|---|---|---|---|
| 2026-08-09 | T2.54, T2.110 | 1 | **Two minors parked from the 2026-08-09 delta review, both on the gold's eligibility lock, neither actioned.** (D-7) `gate_eligibility` validates that the embedded `resample` block *says* n ≥ 93 with ≤ 1 disagreement and carries its citation fields, and nothing binds that certification to the pair content it certified — a post-certification label flip keeps eligibility green on a certification of a different file. T2.110 handled exactly this correctly **by procedure**, stripping the carried-over block for that stated reason, so the protocol already understands what the code does not enforce; the slice-count pin catches appends, not flips. Fix shape when someone takes it: a pairs-only content hash recorded in the block and re-derived at eligibility time. (D-8) The sitting wrote its certification *into* `gold.json`, so the certified sha is not the measured sha — verified annotation-only, and the attempt counter treats the new sha as uncontacted | Parked rather than fixed because both are hardening on a lock whose current answer is correct: the gold *is* eligible, by a resample that did happen, on the file as it stands. Recorded here rather than only in the review report because the next person to touch the lock is the one who needs them, and the report is a dated artefact while this file is the task's own |
| 2026-08-06 | T2.40, T2.41, T2.54, T3.22, T3.24, TH1.10, TH1.17 | 2 | **Epic created; all seven evidence-and-gold tasks moved here from E2, E3 and EH1, ids unchanged.** Ids keep their original epic prefix deliberately — every gate-ledger row, analysis and commit message in the tree already cites them, and renumbering would break that trail to buy nothing | Controller decision: implementation must not queue behind datasets. One unlabelled gold (T2.54) was holding six E2 tasks and, through the epic entry gates, most of E3 and EH1 — while 89 of 96 E2 tasks had already closed without any gold at all, which is the measurement that the coupling was accidental. Moving them out makes the dependency explicit rather than structural: M1 consumes implementation, never gates it. Safety is preserved by `T2.95`'s serving gate, not by ordering |
| 2026-08-07 | T2.40, T2.108 | 2 | **T2.40 gains a clause: a decidable probe is not automatically a meaningful one, and this re-measure must rule on that before recording a verdict.** With T2.108's corpus the false-promotion audit reads *decidable, clears* at 0.0000 while its numerator is structurally zero — judge unqualified, `SINGLE_VALUED_RELATIONS` empty with no REPLACES-family edge in the corpus, no `human_verdict` events — and the committed predicate cannot distinguish precision from inoperability | Verified on data by T2.108's adversarial review, not inferred. The review's own attack sharpened rather than weakened it: the vacuity is joint bar-plus-corpus, but no corpus in the 20–99 band can be both operable-numerator and passing under the 1% bar, so it attributes to the bar. Probes 1–2 carry a weaker form (`blocked ≡ 0` data-precluded) that T2.108's report did not frame as the same shape. Recorded on T2.40 rather than fixed anywhere, because changing a bar after a measurement is exactly what the pre-statement rule forbids — the gate owner rules |
| 2026-08-10 | T2.115 | 2 | **Minted.** The 2026-08-08 G-D re-measure recorded a granularity finding — Rule B's never-contacted subset holds 25 contradicted pairs, so 0.95 is not on its recall lattice and "the verdict must hold on both" silently gates it at ≥ 0.96 — and asked the owner to settle it before a run landed on 24/25. The owner ruled 2026-08-10 (resize so 0.95 lands on it, then let it gate); no task owned the work | Same shape as T2.110's own minting: a precondition written into one task's findings and owned by no task. Recorded as Tier-2 rather than Tier-1 because it adds a task, changes what Rule B's second population means, and its step 0 asks the owner to ratify a **lattice-retirement** rule the protocol has no precedent for — LABELLING.md retires a pair only when its label is *wrong*, and this round retires correctly-labelled contacted pairs to hold the pooled census constant. Two derivations bound the route and are in the plan: 0.95 cannot be exact on both populations (`N ≡ 0` and `55 + N ≡ 0 (mod 20)` has no solution), and the census cannot grow because the Layer-3 resample's first stratum is a full contradicted census at a ratified n = 93 |
| 2026-08-10 | T2.115 | 1 | **Two execution deviations recorded after the fact, neither of which had an amendment when it landed** (branch review M-1, I-7). (M-1) The done-when said `NEVER_CONTACTED_FIRST_ID` and LABELLING.md's range "move together"; owner ruling R3 reversed that mid-round — the constant stays `eg-0242` and was renamed `RULE_B_FIRST_ID` — so the task text asserted the pre-ruling behaviour for the whole execution. Corrected in the done-when. (I-7) The 51 companions were drawn by the **cell-level** largest remainder where plan v2 §6, written to answer the plan review's own I7 and reviewed at Fable tier, states the **slice-marginal** one. Both re-derived from the pre-round file: slice-marginal gives temporal 7 / unrelated 6, cell-level gives temporal 6 / unrelated 7, and nothing else differs — one slot. Recorded at `ROUND3_SLICE_TARGETS` | Recorded rather than re-executed, because re-drawing is gold surgery: it moves the sha, voids the `58ac1a90` certification and the G-D attempt already spent against `98fc4b49`. Both deviations are bounded and content-blind — neither algorithm names a pair, and the precision floor is 0.70 against a measured 0.90 — but the variant was chosen by the **contaminated** controller and committed in `48ad7e8e` together with the authored pairs rather than before them, which is the plan review's own procedure-shopping channel. The round's "zero degrees of freedom" claim is overstated by exactly one slot, and a claim that is nearly true is the kind this corpus is built to catch |
| 2026-08-10 | T2.116 | 2 | **Minted** from the E3 branch review's triage of D-7 and D-8. The review ruled both "may stand" and then recorded that T2.115 had just paid their manual tax a third time; the fix shape it names — a pairs-only content hash in the `resample` block, re-derived at eligibility time — is now a task rather than a note in two amendment logs | Not a G-D blocker and not a correction: the gold is eligible today by a resample that happened, on the file as it stands. What changed is the evidence about cost. Twice-parked as hardening on a lock whose answer is right, it has now been executed correctly by hand three times (T2.110, T2.115, and T2.115's own re-certification), and a procedure re-executed correctly three times is one waiting to be executed incorrectly once — which here means a certification that names no pair set silently certifying a different file |
| 2026-08-12 | T2.116 | 3 | **ESCALATED, then RULED AND APPLIED the same day (owner ruled both halves: re-key, and record the analysis —  `docs/planning/analyses/2026-08-12-t2.116-attempt-counter-keying.md`): stamping the content basis silently zeroes `gold_touching_attempts` for the current pair set.** The counter (`run_judge_qualification.py`) keys on the gold's **file** sha, and T2.116's required stamp writes two fields into `gold.json`, moving it `98fc4b49 → 6eadba73`. Measured on the ledger: 5 attempt rows across 3 shas (`e6d5647a` ×3, `800d4d91` ×1, `98fc4b49` ×1), and the current file now counts **0**. The one at `98fc4b49` is a contact with pairs that are byte-identical to today's — proved by the strip-reconstruction above — so the next G-D run would report `gold_touching_attempts: 0` for a pair set that has already been judged once. **Ruled: key it on `pairs_sha256`.** Strictly more conservative — annotation churn, the certification's own insertion and any future stamp stop resetting it, and no reachable edit lowers the count, which is the direction that matters for an anti-tuning disclosure. Applied with legacy rows still credited by file sha (OR'd, never AND'd, so an un-backfilled ledger loses nothing), a git-history backfill that recovers pair identity without inventing it (5 rows resolved, 0 guessed), and a regression test written with the real shas. **The counter now reports 1 for the current pair set, which is deepseek-v4-flash's contact.** T2.114 is gpt-5.5's first contact with these pairs | The runbook's own test: "a gate's definition ... would have to change" stops an agent rather than licensing it. Recorded here because the count is wrong **the moment this commit lands**, not at some future date, and T2.114 is the run that would read it. Note the fragmentation is pre-existing — three shas already — so this does not introduce the defect, it adds one more fragment and makes the visible number 0 where the honest number for these pairs is 1 |
| 2026-08-12 | T2.122 | 1 | **The task text and its brief measured 80 files / 79 residue at the top level of `entailment/verdicts/`; a recursive audit found a second, previously undocumented population — 16 more residue files in a stray `verdicts/verdicts/` subdirectory, all dated 2026-08-10, consistent with an earlier, unfinished, unrecorded manual quarantine attempt. Total 96 files, 95 residue, 1 genuine, not 80/79** | Task-local reality found during execution: same defect category (synthetic residue under real judge identities), a more complete count. Corrected in the identification record (`docs/eval/2026-08-12-verdicts-directory-residue-removed.md`) before any deletion, per the task's own constraint |
