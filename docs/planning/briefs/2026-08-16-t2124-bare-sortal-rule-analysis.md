# Brief — the bare-sortal rule gap in T2.124's entailment gold

**You are producing an analysis and a recommendation, not a ruling.** The ruling
is the owner's under LABELLING.md's rule-then-pairs discipline. Your job is to
make the decision as easy and as well-grounded as it can be, and to say plainly
where the evidence does not reach.

**Do not change any file.** No gold edit, no LABELLING.md edit, no pair
relabelled. Read, reason, report.

## The situation

`backend/scripts/benchlib/entailment/gold.json` is a 280-pair entailment gold
for G-D's judge qualification (T2.124 → T2.125). Its Layer-3 seeded resample
(n = 93, bar ≤ 1 disagreement) was sat twice on 2026-08-16:

- `deepseek-v4-pro` — **2 disagreements, MISS**
- `gpt-5.5` — **1 disagreement**, numerically a pass, recorded as a diagnostic
  and deliberately **not banked** (a model swap with the rule gap still open is
  model-shopping; see `dispatch/2026-08-16-t2124-replacements/07-*.md`)

Both disagreements land on one construction.

## The gap

LABELLING.md's **Frame rule** (ruled 2026-08-15) distinguishes:

- a **universal discourse frame** — "the estate", "the stack", "the environment"
  — vacuous, moves no verdict, so an existential so framed is ordinary weakening
  and `entailed` when its witness is in the premise;
- a **proper-subset frame** — a named deployment or cluster — asserted content
  sitting in the restrictor, so `unsupported`.

The gold's commonest existential shape is **neither**: a **bare sortal** with no
frame phrase at all — "at least one **component**", "at least one **system**".
**29 live pairs** use it. The rule is silent on it, so those 29 rest on a
reading no committed file states.

## What the two sittings measured

| pair | premise → hypothesis | gold | v4-pro | gpt-5.5 |
|---|---|---|---|---|
| eg-0486 | "clickhouse depends on ledger-02" → "ledger-02 has at least one **component** that depends on it." | entailed | unsupported | unsupported |
| eg-0546 | "consul uses etcd" → "Consul uses at least one other **component**." | entailed | unsupported | entailed |
| eg-0650 | "alert storms deployed on lb-01" → "Alert storms are deployed on at least one **host**." | entailed | entailed | entailed |

Model-vs-model agreement across all 93 drawn pairs: **92/93**.

**The inference that matters.** Under a *fully permissive* bare-sortal reading —
the one the gold was authored under — eg-0486 **is** entailed: "at least one
component that depends on ledger-02" reduces to "at least one thing that depends
on ledger-02", which the premise gives. Both vendors rejected it anyway. So both
independently reject the reading the gold assumes.

## The candidate readings

1. **Permissive** — a bare sortal is vacuous like a universal frame. The gold
   needs no repair. The evidence above argues against it.
2. **Earned** — the sortal must be established by the premise, and a relation's
   own semantics can establish it (`DEPLOYED_ON` earns "host"; `DEPENDS_ON`
   earns "dependency"; `USES` earns nothing). Predicts all three sampled pairs
   correctly (3/3).
3. **Earned on the subject side only** — object-side generalisation ("one of the
   things Consul uses") is licensed by the relation; subject-side ("at least one
   component that depends on X") needs the sortal earned. This is the axis
   eg-0486 and eg-0546 differ on, and the one the two models split on.

## The evidence gathered for you

`backend/scripts/benchlib/entailment/probe_runs/2026-08-16-bare-sortal-*.json` —
a rule-discovery probe running **both models over all 29** bare-sortal pairs
under the same prompt, rulebook excerpt and per-pair independence the resample
uses. Not a resample, gated by nothing, written into no gold. Its
`summary_by_sortal` block groups by the *earned* / *unearned* classification,
which is reading 2's prediction made falsifiable. Script:
`backend/scripts/benchlib/bare_sortal_probe.py` (its `RELATION_EARNED_SORTALS`
constant is the hypothesis, not a rule the gold states).

## Constraints any recommendation must respect

- **`weakening` and `paraphrase` admit only `entailed`** (`SLICE_VERDICTS`), so
  a pair whose label flips cannot be relabelled in place — it is
  retire-and-replace.
- **`entailed` must stay ≡ 0 (mod 10)** (`round4_frame.ENTAILED_LATTICE_MODULUS`,
  the 0.90 lattice). It is 110 now. Replacing keeps it; retiring 16 lands on 94,
  off the lattice, forcing 100 or 90 and invoking T2.115's lattice-retirement
  clause to drop *correct* pairs.
- **`contradicted` is pinned at 80** (`CONTRADICTED_TARGET`), so `eg-0478`
  (`direction`/`contradicted`, bare sortal) must be replaced, never dropped.
- **≥ 200 live pairs** (`MIN_GOLD_PAIRS`).
- The **ratified matrix** (sitting 2, owner-ratified: contradicted 80 /
  entailed 110 / unsupported 90) is amendable only by the owner.
- Two consecutive resample failures **stop the task**. One has occurred.

## Return

1. **Which reading you recommend, and the argument** — on entailment semantics,
   not on which is cheapest to repair. If the probe's 29 points split the
   readings differently than the 3 sampled ones did, say so and lead with it.
2. **The repair set** the recommendation implies: which pair ids, which slices,
   how the matrix and the lattice come out, and whether replacements or
   retirements.
3. **The rule text you would put in LABELLING.md** — draft wording, so the owner
   is ruling on a sentence rather than on a direction.
4. **What your recommendation would get wrong** if the other reading is right,
   and what evidence would distinguish them that nobody has gathered.
5. **A view on whether the gold is repairable this round at all**, given that one
   of the two permitted failures is spent. Saying "this needs a fresh round" is
   an available answer if that is what the evidence supports.

---

## Evidence gathered after this brief was drafted — read this section first

### The probe over all 29 refutes the "earned sortal" hypothesis

| | deepseek-v4-pro | gpt-5.5 |
|---|---|---|
| Rejects, of 29 bare-sortal pairs | **14** | **3** |
| Of the 13 *earned* pairs | 3 rejected (all `DEPLOYED_ON`) | 1 |
| Of the 16 *unearned* pairs | 11 rejected | 2 |

Reading 2 predicted 3/3 of the pairs the resample happened to sample and
predicts far less on the population: a relation supplying the sortal does **not**
reliably rescue it. Directional signal survives (earned 10/13 agree against
unearned 5/16); a clean rule does not. **Do not adopt reading 2 on the strength
of the three sampled pairs — preventing exactly that is why this probe was run.**

### The instruments diverge exactly where the rulebook is silent

Model-vs-model agreement is **92/93** across the resample draw and **18/29**
across this construction. The rest of the gold is solid; the disagreement is
localised to the shape no rule covers. This is the strongest evidence the gap is
real rather than two unlucky pairs, and it is why the choice of resample model
decided the verdict.

### Instrument noise exists but is confined to the decision boundary

`deepseek-v4-pro`, same seed, same prompt, 5 calls each:

| pair | result |
|---|---|
| eg-0418 (control, clear) | `entailed` x5 — **stable** |
| eg-0474 (control, clear) | `entailed` x5 — **stable** |
| eg-0546 (bare sortal) | `unsupported` x5 — **stable** |
| eg-0650 (bare sortal) | `entailed` x3, `unsupported` x2 — **unstable** |

So `resample_llm.py`'s docstring claim that "`seed` is what buys reproducibility
on that line" is **false at the boundary and true away from it** — narrower than
a broken instrument, and it matters for the ruling:

**The v4-pro miss rests on stable disagreements, not luck.** Both of its
disagreements — eg-0486 and eg-0546 — reproduce 5/5. The one unstable pair,
eg-0650, went the *gold's* way in the resample and so contributed nothing to the
miss. Treat the MISS as a real measurement of a real defect.

### The pairs both instruments reject

- **eg-0486** — "clickhouse depends on ledger-02" -> "ledger-02 has at least one
  **component** that depends on it." Both reject; stable under repetition.
- **eg-0475** — "At least one **service** is deployed on spire-01."
- **eg-0699** — "grafana uses nginx" -> "nginx is one of the **pieces of
  software** Grafana employs." **Authored on 2026-08-16 as a replacement in this
  very round**, so the authoring reproduced the defect class it was repairing.
  Include it in the repair set and treat it as evidence of how readily the
  unwritten reading propagates to anyone authoring against the current rulebook.

`eg-0698`, the round's other replacement, carries an explicit universal frame, so
the Frame rule already covers it and the probe excludes it by construction. No
instrument has tested it.

### Consequences for question 5

One of the two permitted resample failures is spent, the repair set is larger
than three pairs, and the round's own replacements are implicated. Weigh whether
a repair inside this round is credible or whether the honest answer is a fresh
round with the rule written first.
