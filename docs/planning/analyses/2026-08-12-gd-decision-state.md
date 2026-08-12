# G-D — what actually blocks it, and what the owner's decision has to contain

**Written:** 2026-08-12, at the owner's request, to make the G-D decision
decidable. **Status:** analysis only. It rules nothing and deliberately makes
no argument the fitting rule reserves for an uncontaminated party.

---

## The finding that reorders everything

**T2.114 is blocked on two things, and the owner's decision is neither the
only one nor the first.**

The 2026-08-10 adjudication produced ruling **R-B**, an *ordering gate*:

> no further judge attempt may run on gold `98fc4b49` until the two
> contradicted duplicates are retired and the gold re-certified.

**That retirement has not happened.** Checked against the file today:
`eg-0367`, `eg-0093` and `eg-0251` are all `retired: false`, and the live
contradicted census is still 80. So the sanctioned final attempt cannot
lawfully run yet, whatever the owner decides about the model.

Everything below is downstream of that. A session that reads only
`progress.md` sees `T2.114 blocked` and one unruled decision; the real queue
has ruled-but-unexecuted work in front of it.

## The measured position, stated without inviting a fit

The last run (2026-08-10, `deepseek-v4-flash`, gold `98fc4b49`):

| Bar | Required | Pooled (402) | Rule B (176) |
|---|---|---|---|
| groundedness precision | 0.95 | 0.9938 PASS | 1.0000 PASS |
| groundedness recall | 0.90 | 0.9249 PASS | 0.9167 PASS |
| contradiction precision | 0.70 | 0.8065 PASS | 0.8837 PASS |
| contradiction recall | **0.95** | **0.9375 FAIL** | 0.9500 PASS |

**Seven of eight readings pass. The one failure is 75/80 — five misses where
four are permitted.** One pair.

Two things about that "one pair" that the number alone hides, both already on
the record:

1. **The census is 80 rows over 78 independent propositions.** Two duplicated
   propositions straddle the two populations. R-B's arithmetic: a judge that
   *catches* a correlated pair banks two correlated hits and may then miss four
   of the remaining 78, a per-item tolerance of 5.13% against the intended
   5.00%. The duplicate makes the bar **easier**, and at measured recall the
   catch is the common case.
2. **Rule B's population passed at exactly 38/40 = 0.9500** — a zero-margin
   pass whose independent-item reading falls *below* the bar.

So the honest reading of "failed by one pair" is not "nearly cleared". It is
"failed by one pair on a census known to be slightly too generous". Retiring
the duplicates could move the result in either direction, and predicting which
is not something this analysis should do.

## What R-B costs, and one thing nobody has decided

R-B's retirement is **content-forced by a deterministic finding** — two pairs
assert the same proposition — so clause 1 does not govern it and contamination
is not an obstacle. Anyone can do it. It is not a census-shape selection.

But "and the gold re-certified" is where the cost sits, and **T2.116 made this
concrete today in a way that has not been ruled on.**

Since T2.116 the eligibility lock binds the resample certification to the pairs
it certified, and retiring a live pair removes it from that basis — the lock
reports it as *removed since certification* and eligibility goes red. So
mechanically, R-B's retirement **voids the certification and demands a fresh
n = 93 blind sitting** from outside the labelling family. That is the expensive
human step T2.107 built the instrument for, and `deepseek-v4-pro` sat the last
one.

**The unmade decision: does a pure retirement require a full re-sitting?**
Retiring a duplicate changes no label. The certified label-error rate still
describes every pair that remains; what changes is the population it was
measured over. Two defensible readings:

- **Strict (what ships today).** Any change to the live set voids the
  certification. Safe, and expensive: a deterministic dedup costs a full
  93-pair sitting.
- **Narrowing.** A certification survives the *removal* of pairs, because the
  measurement of the remainder is unaffected; only additions and label changes
  void it.

The narrowing is not obviously safe — "removal only" is exactly the shape of a
census-shape selection, and permitting it silently would let someone retire
their way to a friendlier population without re-certifying. That argues for
keeping the strict rule and paying the sitting, or for permitting removal only
when the retirement is content-forced and recorded as such. **This is a Tier-3
call and it belongs to the owner.** I have not made it; the strict behaviour is
what the code does.

## What R-C's argument must contain, and why I must not write it

R-C is unchanged: three sentences — **which model, why that one, and what
result ends the search rather than extends it.** The option set is known to be
at least {`gpt-5.5`, `deepseek-v4-pro`}, with v4-pro carrying the recorded
objection that it sat the Layer-3 resample, so judge and certifier would be one
model.

**I am disqualified from making that argument, for exactly the reason the
previous session was.** Its whole evidential value is that it was made by
someone who had not seen the scoreboard. I have read the scoreboard — every
per-slice number, both vendors, all four attempts. Any case I built for a model
would be indistinguishable from score-chasing to a reader who knew nothing, and
the prior draft's failure mode is on the record as a warning: it invented an
eligibility filter ("already carries a qualification record") that appears
nowhere in T2.114 or doc 17 §6, and that filter did the work of shrinking the
choice to one.

What I can say without performing the judgment:

- **The stopping rule is the part a contaminated party may write**, because it
  forecloses every branch equally and cannot be selected for its effect. T2.114
  already carries one: this is the final attempt on this gold; on a miss, G-D
  is recorded NOT CLEARED and no further model is tried on that sha.
- **A bar argument is the other lawful move**, and it has a hard constraint:
  doc 17 §6 forbids choosing a bar while looking at the results it would judge.
  An argument for moving `contradiction_recall_bar` off 0.95 must stand on what
  the consumer does with the verdict, not on how close a run came. The bar's
  own derivation is on the record and its falsifier is live — the measured
  judge does not clear it, and a test pins that — so a re-derivation has to
  beat that check, not route around it.
- **Neither move is available until R-B is executed.**

## One interaction worth knowing before the retirement lands

After R-B's retirement the pair set changes, so `gold_pairs_sha256` changes,
and `gold_touching_attempts` will correctly report **0** for the new census —
while the ledger's own accounting (ruling R4's lineage) says one sanctioned
attempt is already spent on this gold's line. Both are right and they answer
different questions: the counter measures contacts with *these pairs*, lineage
measures attempts across a gold's ancestry.

They should not be reconciled by loosening the counter. The lineage sentence in
the ledger is what carries the history, and it should be restated in the same
breath as any post-retirement run so a reader never takes a fresh 0 for a fresh
gold.

## The queue, in order

1. **Retire the two contradicted duplicates** (R-B, already ruled, unowned,
   content-forced — no decision needed).
2. **Rule the re-certification question** above: strict void, or narrowing for
   content-forced removals. Tier 3, owner's.
3. **Re-certify the gold** per that ruling — a fresh n = 93 sitting if strict.
4. **Write R-C's three sentences** from an uncontaminated session.
5. **Run the final sanctioned attempt.**

Steps 1 and 3 are work; steps 2 and 4 are yours and nothing can proceed past
them. Step 5 is the only one that can clear G-D, and it can also record a
measured miss — which doc 17 and runbook §7 both treat as an outcome, not a
failure to finish.
