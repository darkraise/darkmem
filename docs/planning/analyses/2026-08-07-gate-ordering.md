# Tier-3 analysis — the G-C / G-D ordering (2026-08-07)

**Question.** T2.40's evidence run found that G-C's false-promotion audit structurally
requires G-D's qualified judge, while the roadmap orders G-C before G-D. Nothing recorded
that dependency before 2026-08-07. What should the owner do about the ordering?

**Method.** Analysis only — no code changed, no gate touched, no design doc edited. Every
factual claim below was re-established against the shipped code and the corpus documents,
not taken from T2.40's report; where this analysis *corrects* T2.40, it says so
explicitly. The owner ratifies or rejects; this document decides nothing.

**Verdict in one paragraph.** The dependency is real but narrower and stricter than
T2.40 recorded: it binds exactly one arm of one probe, and it binds to G-D *passing*,
not merely running. T2.40's claim that both audit arms dead-end without the judge is
wrong — the human-rejection arm is live in shipped code with no judge anywhere on its
path. Meanwhile the corpus problem, not the judge, is G-C's dominant blocker: it starves
all four probes, it is independent of both gates, and the only pre-cutover fix is a
purpose-built corpus nobody has minted a task for. The ordering itself turns out to be
narration rather than dependency — doc 20's own gate graphs draw G-C and G-D as parallel
edges off Phase 2, and no task or gate consumes G-C's clearance except the promotion
record. The recommendation is therefore not a reorder, a narrowing, or a merge: ratify
the discovered dependency into the corpus as stated preconditions, keep both gates'
claims whole, and mint the corpus-authoring task now, because it is the long pole under
every option.

---

## 1. The facts, established independently

### 1.1 The machine-dispute arm: a total dead-end, and stricter than T2.40 recorded

Doc 17 §5.1 defines the audit numerator as "corroborated facts later **disputed** or
**human-rejected**". The disputed arm's chain, traced in shipped code:

1. The audit counts `verified` events whose `after.verification_status = 'disputed'`
   landing after a corroboration (`_FALSE_PROMOTED_FACTS_SQL`, `disputed_after` CTE,
   `benchlib/promotion_metrics.py`).
2. `disputed` is written only by the ladder applier during recompute, driven by the
   standing contradiction verdict read back from the journal
   (`verification_ladder.py` — "the journal is where it has to be").
3. Contradiction verdicts are journaled only by `contradiction_scan`, whose docstring
   states its one-door rule: "`VerificationJudge.judge` is the only thing in this module
   that can produce a verdict — no similarity floor stands in for one, no string
   comparison, no fallback when the judge refuses," and the refusal aborts the run
   without advancing the watermark.
4. `VerificationJudge.judge()` raises `JudgeNotQualifiedError` unless
   `qualification_state` passes (`verification_judge.py:135–161`).

**The dead-end is stricter than "needs the judge qualified."** `qualification_state`
(`verification_judge.py:232–278`) requires *all* of: a record minted only by
`run_judge_qualification.py --gate` against the canonical gold (the recorder refuses the
canonical record path for any other gold — `judge_qualification.write_qualification_record`);
`gate_eligible: true`, which the eligibility lock grants only past the §11 composition
floor (≥ 200 live pairs, ≥ 50% `l2-fact` premises, zero author-labelled, resample block
present with ≤ 1 disagreement at n = 93); an identity-hash match to the currently
configured judge; and **every recorded metric at or above its bar, including
`contradiction_precision_bar` ≥ 0.95** — the metric whose interim measurement was
**0.818** (T2.26, two `unsupported` pairs judged `contradicted`).

So the precise dependency statement is: **G-C's machine-dispute arm is live only in a
world where G-D has already passed.** Not "G-D ran first" — passed, at the current judge
identity. A G-D miss keeps this arm dark until a model or prompt change re-qualifies.
This is stronger than what T2.40's report or the ledger row states, and it matters for
every option below.

### 1.2 The human-rejection arm: NOT a dead-end — T2.40's premise corrected

T2.40's report and the G-C ledger verdict both state: "human rejections flow only
through a review queue that only disputes and blocked holds can fill. Both numerator
arms dead-end today." **Both halves of that sentence are contradicted by the shipped
code.**

First, the rejection door does not require queue membership at all.
`app/services/human_adjudication.py` says so in its own docstring, as a design decision:

> "A rejectable fact is not necessarily a queued one, and that is deliberate. The audit
> counts *corroborated* facts a human later rejected, and a corroborated fact has no
> opener firing on it, so it is not on the queue at all. Requiring
> `review_state = 'open'` here would make doc 17 §5.1's audit structurally unable to
> count its own principal case. The door therefore accepts any fact id."

`reject_fact` journals a `human_verdict` event with `verdict = 'rejected'`, which is
exactly what the audit's `rejected_after` CTE and `_HUMAN_REJECTED_SQL` count. No judge,
no scan, no dispute appears anywhere on this path. A human who rejects a wrongly
promoted fact today produces a countable numerator entry.

Second, even the review queue's fill predicate is not judge-exclusive.
`verification_ladder.REVIEW_OPENERS` has two members: `_dispute_opens_review`
(judge-dependent, via the veto) and `_under_sourced_opens_review` — demotion hysteresis,
which fires when a corroborated fact's origin count falls below its N. That opener is
driven by source changes (expiry, supersession of an asserting memory), never by the
judge. The queue can surface facts, and a surfaced fact can be rejected, with the judge
dark.

**How much this weakens the premise — bounded, in the bar's own arithmetic.** The
audit's decidability floor is 20 in-window corroborations; below 100 corroborations one
false promotion breaches the 1% bar, so within the decidable band the bar demands zero
observed false promotions. With only the human arm alive, a zero means "no human noticed
a false promotion" — over a corpus where a false promotion sits quietly at `corroborated`
with no opener firing on it and no systematic detector running. The number is
**non-vacuous** (the counting door works; a rejection would land), but its *sensitivity*
is unknown and unmeasurable: nothing states what fraction of false promotions an
unprompted human would catch. A gate-strength claim of "promotion precision ≥ 99%"
cannot rest on it. So T2.40's conclusion survives in corrected form — clearing G-C's
audit before the judge qualifies would still certify the ladder with its only systematic
detector dark — but the supporting claim "both arms dead-end" is wrong and should be
amended in the ledger, because a future reader planning a fallback (see §3) needs to
know the human arm exists.

### 1.3 The dependency is partial across the four probes, not total

| Probe | Needs the qualified judge? | Needs a promotable corpus? | What a pre-judge number would mean |
|---|---|---|---|
| Promotion rate by source-kind diversity | No — promotions flow without the judge. The veto reads standing verdicts; absent verdicts, nothing vetoes. Measured evidence: T2.40's own bench run drove `verification_recompute` through 62 events with an unqualified judge and no error | Yes | A real number for a **veto-less ladder**: disputes are structurally 0, so eligible ≈ promote + supersession-blocked holds, the rate is inflated relative to the complete system, and the 0.5 floor — whose stated rationale watches for veto disputes — is trivially easier. The number expires the day the judge goes live |
| Promotion rate by which N fired | Same | Yes | Same |
| False-promotion audit | **Machine arm: yes, totally (§1.1). Human arm: no (§1.2), but sensitivity unquantifiable** | Yes (denominator: ≥ 20 in-window corroborations) | A non-vacuous but weak zero — "nothing was noticed", not "precision ≥ 99%" |
| Journal completeness | No — reconciliation SQL over `events` vs `knowledge_triples`, judge nowhere in it | Yes (0 transitions ⇒ vacuous 0/0, as measured) | Fully honest once transitions exist |

So the gate is not wholly blocked by the judge: three of four probes plus the audit's
denominator need only a corpus, and the fourth probe is split. But the one blocked arm
is the gate's **correctness** probe — T2.40's bar rationale says it plainly: "the
correctness bar is the audit, and the rate bars exist to refuse a gate claim built on an
unpowered, collapsed, or promotion-free window." A gate that clears its liveness probes
and defers its correctness probe has certified liveness, nothing more.

### 1.4 The corpus problem is independent, dominant, and the only part fixable today

Verified from T2.40's committed artifacts and reproducible by `run_gc_evidence.py`: the
only corpus in existence carries 62 facts over 62 `fact_sources` rows, every
`origin_key` NULL, one source kind. Rule 4 folds all of them into the reserved
anonymous-origin bucket, which counts once per fact and is excluded from both gates —
**no fact can reach N ∈ {2, 3}, structurally**. Consequences:

- The corpus starves **all four probes** (0 eligible, 0 promotions, 0 corroborations,
  0 transitions). The judge starves only the audit's machine arm. Fixing the judge
  without the corpus evaluates nothing; fixing the corpus without the judge powers
  probes 1, 2, 4 and the audit's denominator.
- The corpus fix is **independent of both gates**. Neither the gold sitting (T2.107 →
  T2.54) nor the judge run (T2.41) touches it, and it touches neither.
- **The passive alternative is circular.** The ledger's route (a) — a production journal
  window after the homelab cutover — cannot power G-C *before* G-C, because doc 17
  §11's own 2026-07-31 ruling records that "doc 20 sequences the homelab cutover
  *after* G-C and G-D". Pre-cutover, the purpose-built measurement corpus (route (b):
  designed origin/kind/time-gap structure, authored under the gold discipline —
  separate owner, adversarial review, T2.54's pattern) is the **only** route to a G-C
  verdict. No task exists for it. Whatever the owner decides about ordering, this task
  is on G-C's critical path and can be minted today.

### 1.5 The "ordering" itself is narration, not dependency

The question presupposes "the roadmap orders G-C before G-D." Checked against the
corpus, that ordering is thinner than it reads:

- **Both of doc 20's gate graphs draw the gates in parallel.** §2's mermaid:
  `P2 →(G-C)→ deriver` and `P2 →(G-D)→ P3` — two edges off the same node. §3's mermaid:
  identical shape off L2. No edge runs from G-C to G-D or to anything G-D guards.
- **The prose order is incidental to its own rationale.** §3's "the code deriver only
  after L2 is proven live, and Layer 3 (articles) last" reproduces the reshape spec §8
  sequence, but the *stated reasons* are "the deriver's born-corroborated facts need a
  working ladder to land on" and "articles synthesise only from non-disputed
  corroborated/confirmed facts" — both of which require **ladder-before-both**, neither
  of which requires deriver-before-L3. The G-C-before-G-D reading rests on the phase
  labels ("Phase 2 exit" vs "L2 → L3" with ordinal phases), not on any dependency the
  design argues for.
- **No task edge encodes it.** T2.41's Depends is `T2.26, T2.54`; T2.40's is
  `T2.06, T2.09, T2.10, T2.11, T2.24, T2.51`. Neither references the other. The M1
  epic (2026-08-06) already ruled that measurement consumes implementation and gates
  nothing.
- **The only consumer of G-C's clearance is the promotion record.**
  `claim_gates.corroboration_gate` fails closed while
  `PROMOTION_RECORD_PATH` is absent or not `gate_eligible: true`; nothing else in the
  tree changes behaviour on G-C clearing. The deriver's code is already merged (M1
  split); "closed" lives on the label.
- **One coupling runs the other way, and it bounds what any reorder can buy:**
  `corroboration_gate` withholds the `corroborated` label from **every** fact — ladder-
  promoted and born alike — until G-C's record exists (only human-ratified `confirmed`
  and the honest `candidate`/`disputed` pass through). Doc 09 §4.2 has articles
  synthesise only from non-disputed corroborated/confirmed facts. So even if G-D clears
  first and Phase 3 formally opens, the synthesis substrate is label-starved until G-C
  also clears (or facts are hand-ratified). Whether T3.02's eligibility query reads the
  served label or the disk column is not yet decided in code; if the corpus documents
  adopt any reordering, they must say which, because the honest reading (served label)
  makes L3 *content* wait on both gates regardless of formal order.

**Net:** G-D-before-G-C breaks nothing that the corpus actually argues for, and
G-C-before-G-D was never achievable once the audit's machine arm bound to the judge.
The discovered dependency does not contradict the design's rationale — only its
incidental narration.

---

## 2. The options, with their real costs

Doc 20 §4's standard applies to each: no layer advances on intuition; every advance is a
measured number against a bar stated before the run.

### Option A — Reorder: G-D before G-C

Rewrite doc 20 §3's narration and the phase-exit bookkeeping so G-D is sequenced first,
with G-C behind it.

- **What breaks:** nothing structural (§1.5) — no task, gate, or code consumes G-C's
  clearance except the promotion record, and the record can simply mint later.
- **Cost:** a Tier-3 roadmap amendment (phase-order change is explicitly Tier-3 in
  runbook §5) touching doc 20 §2–§4, the E2 header's advance-gate line, and the ledger.
- **Risk:** overstatement in the other direction. A hard "G-D then G-C" implies G-C's
  *whole* gate waits on the judge, which §1.3 shows is false — three probes and the
  audit's denominator wait only on the corpus, and corpus work should not be sequenced
  behind the gold sitting. A strict reorder would put G-C's long pole (corpus
  authoring) behind an unrelated precondition.
- **What it makes unmeasurable:** nothing.
- **What the corpus documents would say:** doc 20 §3's order becomes
  "L2 → judge qualification → deriver → L3", which is more sequence than the dependency
  supports — the true shape is a partial order, not a swapped total order.
- **Doc 20 §4 standard:** met — no number is claimed that was not measured.

### Option B — Narrow G-C's claim: clear on what it can measure, defer the audit

Split the gate: probes 1, 2, 4 (plus the audit's human arm with a stated sensitivity
caveat) can clear once a corpus exists; the machine-dispute arm is recorded as deferred
behind judge qualification.

- **Cost:** a gate-definition change — Tier-3 by the runbook's own list ("a gate's
  definition or bar would have to change") — plus a doc 17 §5.1 caveat and a restated
  ledger row.
- **The decisive dilemma — the narrowed gate is either pointless or unsafe.** G-C's
  clearance has exactly one consumer: the promotion record. If the narrowed clearance
  does **not** mint the record, it unlocks nothing — the deriver lane stays
  label-closed, and the "clearance" is bookkeeping. If it **does** mint the record, the
  `corroborated` badge lights system-wide (born rows included, per the ledger's point
  3) on the strength of a gate whose correctness probe could not have caught a failure
  — exactly the certification T2.40's verdict refuses, now with a narrower label on it.
- **A second cost the narrowing cannot escape:** probes 1–2 measured pre-judge describe
  a veto-less ladder (§1.3). The numbers expire when the judge goes live and the veto
  starts producing disputes; the promotion rate and its floor must be re-measured then.
  The narrowed clearance buys numbers with a built-in re-measurement obligation.
- **What it makes unmeasurable:** nothing new — but what it *certifies* is materially
  weaker than what the badge it unlocks asserts, which is the anti-conservative
  direction this corpus's every ruling refuses.
- **Doc 20 §4 standard:** formally met (numbers exist, bars pre-stated), substantively
  failed if the record mints — the *advance* (serving `corroborated`) would rest on a
  gate that measured liveness and called it precision.

### Option C — Merge the two gates

One combined L2 truth gate: judge qualification + promotion metrics + audit.

- **Cost:** the largest documentation rewrite of any option — doc 20 §4's registry,
  doc 17 §5/§6's split ownership, the ledger's two sections, both gates' bar modules'
  framing — for no new measurement.
- **Risk 1 — claim hygiene.** G-D's claim is about an *instrument* (the judge, at an
  identity); G-C's is about a *system over a corpus* (the ladder). Doc 17 §6 requires
  re-qualification on any `verification` model swap. Under a merged gate, a model swap
  would formally re-open the ladder's claim even though the ladder did not change — the
  merged gate would be perpetually re-openable for reasons orthogonal to half its
  content.
- **Risk 2 — consumer coupling.** The gates gate different things (deriver label vs
  Phase 3). `claim_gates` deliberately keeps two records so "one gate serving both
  would let either record light the other's label" — its own comment. A merged gate
  reintroduces at the roadmap level the exact coupling the serving layer was built to
  refuse.
- **What it makes unmeasurable:** nothing, but it makes two clean claims into one
  muddy one.
- **Doc 20 §4 standard:** met mechanically; the registry's per-gate "names its metric,
  its owner, and where its bar lives" clause is what the merge damages.

### Option D — Leave the order; accept G-C stays open until the gold set lands

- **Cost:** the deriver lane's label stays closed longer. Concretely: born-`corroborated`
  rows keep serving as `candidate` with the `verification_unmeasured` reason. Pre-cutover
  there are no users to see any label, so the operational cost today is zero.
- **Risk 1 — the false narration stands.** The roadmap would keep stating an order
  ("G-C, then G-D" via the phase labels) that is now known to be unachievable — the
  next planner reads it and re-discovers T2.40's finding the hard way. This is the one
  cost that compounds.
- **Risk 2 — "until the gold set lands" is not sufficient.** G-C needs the corpus too
  (§1.4), and passive waiting for production data is circular pre-cutover. Option D
  as stated quietly assumes the wrong long pole.
- **What it makes unmeasurable:** nothing new; it just fails to schedule the thing that
  would make G-C measurable.
- **Doc 20 §4 standard:** met — nothing advances.

### Option E — Ratify the dependency as stated preconditions; keep both claims whole; mint the corpus task (found better)

Not a reorder, a narrowing, or a merge: record what is now known, in the places the next
reader will look, and schedule the one independent long pole.

1. **Amend doc 20 §3's narration** (Tier-3, this document is the escalation): the §8
   sequence's rationale requires ladder-before-both, not deriver-before-L3; G-C and G-D
   are a partial order with one cross-edge — *G-C's false-promotion audit (machine arm)
   requires G-D to have passed at the current judge identity.* The gate graphs already
   draw this; only the prose and the "Phase 2 exit" reading change.
2. **Amend the ledger's G-C row** to correct T2.40's overstatement (§1.2): one arm
   dead-ends, not both; the human arm is live but of unquantifiable sensitivity, which
   is why the verdict's conclusion still stands.
3. **Add the dependency edges the task files miss:** T2.40's audit probe carries
   "after T2.41 passes" explicitly (T2.107's text already carries half of this).
4. **Mint the measurement-corpus task now** — designed origin/kind/time-gap structure
   sized to the pre-stated power floors (≥ 1 powered bucket per axis at ≥ 5 eligible,
   ≥ 20 distinct corroborated facts, ≥ 1 promote), authored under the gold discipline
   (separate owner, adversarial review), with the standing caveat that its promotion
   rate partially measures the corpus design. It runs in parallel with the gold sitting
   and is on G-C's critical path under every option.
5. **G-C stays open, whole, with its four probes intact** — cleared only when a powered
   corpus and a passed G-D both exist. No partial clearance, no record minting, no
   badge.

- **Cost:** the smallest of any active option — two doc amendments, one ledger
  correction, one new task. No gate definition changes; no bar moves.
- **Risk:** the hostage risk (§3 below) — shared with A, C, and D, because it is a
  property of the dependency, not of the response to it.
- **What it makes unmeasurable:** nothing. What it makes *measurable* is G-C itself,
  by scheduling the corpus.
- **Doc 20 §4 standard:** met throughout — nothing advances, and the two things that
  would let something advance honestly (corpus, judge pass) are both scheduled.

---

## 3. Recommendation

**Option E.** Ratify the dependency as a recorded precondition rather than reordering,
narrowing, or merging: amend doc 20 §3's narration and the G-C ledger row (including the
correction to T2.40's both-arms claim), add the explicit T2.41-pass precondition to
G-C's audit probe, and mint the purpose-built measurement-corpus task immediately — it
is independent of the judge, it is the only pre-cutover route to any G-C verdict, and it
is the long pole under every option on the table. Both gates keep their full claims;
nothing clears until its evidence exists; the effective order (G-D's pass before G-C's
full evaluation) falls out of the recorded dependency without rewriting the roadmap's
shape.

**The single strongest argument against it:** Option E makes G-C — and with it the
deriver lane's label — transitively hostage to G-D's hardest bar. The judge's interim
contradiction-precision is 0.818 against 0.95, and its failure mode (judging
`unsupported` direction pairs as `contradicted` — manufactured disputes) is a model
capability defect that growing and re-adjudicating the gold set does not obviously fix.
If the judge durably misses that bar at every identity the owner is willing to run, G-C
becomes permanently unevaluable in full, and Option E has no relief valve — whereas
Option B's narrowing, for all its flaws, names one: an audit whose stated instrument is
the human-rejection arm (§1.2) plus the under-sourced queue opener, cleared with an
explicit sensitivity caveat and **without** minting the promotion record until the
machine arm lives. The honest answer to this argument is that the relief valve is not
foreclosed, merely not adopted: if T2.41 records a durable miss, that measured miss is
exactly the evidence a future Tier-3 decision would need to weigh the narrowed audit —
with the number in hand rather than in anticipation. Adopting the narrowing now would
weaken the audit before the judge has been given its qualified attempt, on a bar the
gold growth is specifically designed to re-test.

---

*Facts verified against: `backend/app/services/verification_judge.py`,
`contradiction_scan.py`, `verification_ladder.py`, `human_adjudication.py`,
`claim_gates.py`, `backend/scripts/benchlib/promotion_metrics.py`, `promotion_bars.py`,
`judge_qualification.py`; `docs/planning/gate-ledger.md` (G-C, G-D),
`docs/planning/tasks/M1-measurement.md`, `docs/planning/reviews/2026-08-07-t2.40-gc-evidence.md`;
doc 17 §5.1/§6/§11, doc 20 §2–§4, runbook §5/§7.*
