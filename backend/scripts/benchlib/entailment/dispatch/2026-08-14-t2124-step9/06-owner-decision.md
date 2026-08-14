# T2.124 step 9 — the decision this pass hands to the owner

Prepared by the step-9 controller. **Nothing here is decided.** The pass measured
a thing the plan did not anticipate, and the remedy is a frame question, which
§7 of the governing plan makes the owner's.

## The one-line version

The plan's step-9 authoring gate is **"zero within-class duplicate findings"**.
The instrument that produces that number returns **zero**. An exhaustive blind
adjudication of the population where duplicates can occur returns **at least
eight**. Both are correct; they measure different things. Which one is the gate
is the decision.

## What was measured

Twenty-four live pairs share a byte-identical premise *and* verdict — the only
shape in which two rows can assert one proposition. Two independent blind
adjudicators worked all 24. Neither was told which carried a prior label; both
recovered all five controls (3/3 known duplicates, 2/2 owner-ruled lawful).

| Outcome | Count | Class |
|---|---|---|
| Unanimous DUPLICATE | 8 | all `entailed` |
| Contested (1 says duplicate, 1 says distinct) | 6 | all `entailed` |
| Unanimous DISTINCT | 10 | incl. both lawful controls |

The three duplicates the authoring lineage found by reading are a **subset** of
the eight. The census carries at least five more than anyone knew.

**The contradicted class is clean** — 80 rows over 80 independent propositions,
its single shared-premise candidate unanimously distinct. The class carrying the
0.95 bar and the harder role is the one with nothing wrong with it. Unsupported
is clean too (7 candidates, all distinct).

## Why the mechanical gate cannot be repaired by tuning it

Both the duplicate gate and `census_independence` score hypotheses by
content-token Jaccard. Measured on this census:

| Pair | Jaccard | Truth |
|---|---|---|
| `eg-0424`/`eg-0558` | 0.8333 | duplicate |
| `eg-0463`/`eg-0590` | 0.3333 | duplicate |
| `eg-0425`/`eg-0559` | 0.2857 | duplicate |
| `eg-0486`/`eg-0614` | 0.2857 | **lawful** |
| `eg-0465`/`eg-0592` | 0.5714 | **lawful** |

A known duplicate and a ruled-lawful pair score **identically** at 0.2857. The
populations interleave completely, so no threshold separates them. Lowering the
number to catch the duplicates flags the lawful pairs and most of the corpus.
Jaccard is measuring wording; the question is meaning.

The same blindness is inside `census_independence`, which is the function
written specifically to disclose this hazard after the 2026-08-10 attempt was
spent against 80 rows over 78 independent propositions with no artifact saying
so. It currently reports the entailed class **110 independent of 110 rows**.
That is the same defect, one level down, in the instrument built to prevent it.

## The root cause is upstream, in the frame

Step 5's assignment excludes a premise from a slice **whose hypothesis the
premise determines** — but only for *direction* and *verbatim* reuse. Paraphrase
under entailment is equally determined and is not excluded. The frame does know
these slots collide: it stamps them `shared_note` and instructs authors to
differentiate. That instruction is satisfiable for `contradicted` and
`unsupported`, where there are many ways to contradict or fail to support a
premise, and close to unsatisfiable for `entailed`, where a premise licenses a
narrow set of claims and two blind authors converge.

That is exactly the observed distribution: **14 of 16 entailed shared-premise
pairs are duplicate or contested; 0 of 7 unsupported and 0 of 1 contradicted
are.** This is a property of entailment, not of the authors.

## Your existing precedent already speaks to the six contested cases

Both pairs you ruled lawful generalise **opposite slots** — one drops the
subject, the other drops the object — so neither entails the other:

> `clickhouse depends on ledger-02` → A: "ledger-02 has at least one component
> that depends on it." B: "clickhouse has at least one dependency."

In all six contested cases the generalisation runs **one way only**: one side is
the specific restatement, the other existentially generalises one of its slots,
so one entails the other:

> `auth-02 uses authelia` → A: "Authelia is used by at least one system."
> B: "Authelia is used by auth-02."

If opposite-direction generalisation is what made your two lawful, the six are
not lawful by the same rule, and the total is **14**. That reading is available
to you; it is not taken here.

## What each option costs

| | Independent propositions (entailed) | Min-pass | Effective bar vs stated 0.90 |
|---|---|---|---|
| As currently reported | 110 | 99 | 0.9000 |
| Minus 8 unanimous | 102 | 92 | 0.9020 |
| Minus all 14 | 96 | 87 | 0.9062 |

**Option A — re-author the affected slots.** Loop the 8 (or 14) back through
step 7. Cost: the frame is unchanged, so the assignment still hands shared
premises to entailed slots and re-authoring can reproduce the collision. It
treats the instances, not the generator. The ratified matrix survives untouched
(duplicates change proposition counts, never row counts, and T = 280 with
80/110/90 is unaffected either way).

**Option B — fix the frame, then re-author.** Extend step 5's premise exclusion
so a premise determining an entailed hypothesis is not assigned twice, regenerate
the assignment, re-author what moves. Cost: highest — it reopens the frame
commit-group, and the emitted matrix is what sitting 2 ratified, so anything
touching the assignment plausibly needs re-ratification. Buys the only fix that
stops this recurring in round 5.

**Option C — accept and disclose.** Keep the census; record the true
independent-proposition count and state the entailed bar against propositions
rather than rows. Cost: none in effort, and the distortion is genuinely small —
0.9000 → 0.9020 at eight duplicates. But it means shipping a gold whose known
duplicate count is non-zero, and the disclosure is only honest if
`census_independence` stops reporting 110/110, which needs the human verdicts
carried into the artifact somehow.

## Recommendation

**C now, B before round 5.** The measured distortion is 0.2 percentage points on
a class whose role is not the one G-D keeps failing; the contradicted census that
carries the 0.95 bar is clean and independently confirmed so. Re-authoring under
an unfixed frame (option A) spends the round's remaining budget to re-roll dice
that are loaded the same way. The thing actually worth fixing is the generator,
and that is a round-5 frame change made deliberately, not a patch applied under
time pressure to a census that is 96–102 propositions either way.

The part of C that is not free: `census_independence` must stop printing a
number it cannot support. Whatever you decide, that function reporting "110
independent of 110 rows" is now known-false and should not survive into a
qualification artifact.

## Screen status

This file fires the contamination screen and is **owner/controller material, not
blind-party material** — no author or labeller reads it, and the blind read-set
(`01-brief.md`, `02-cases.json`) is screen-clean. The hits are Jaccard
similarity scores from `duplicate_propositions` (which reads pair text only, so
nothing it reports can be a function of any model's performance), the two stated
class bars, and census arithmetic. **No measured judge result appears here.** A
hit outside those categories would be a finding.

## What a decision needs to say

1. Which count is the step-9 gate — the mechanical zero or the adjudicated 8/14.
2. Whether the six contested cases are duplicates under the opposite-slot rule.
3. Option A, B or C, and if C, how the true proposition count reaches the
   artifact.
