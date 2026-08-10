# Plan — resize the never-contacted contradicted census so 0.95 lands on its lattice

**Status:** step-level plan, **v2 (2026-08-10)**, revised against the Fable plan review
(`docs/planning/reviews/2026-08-10-t2.115-plan-review.md`, verdict: *not safe to execute as
written*). v1's two Criticals and six lesser findings are addressed below; every change is
attributed to the finding that forced it.
**Task:** T2.115. **Owning gate:** G-D.
**Owning protocol:** `backend/scripts/benchlib/entailment/LABELLING.md`.
**Precedent round:** T2.110, whose History entry in that file is the template.

---

## 1. Why this round exists

G-D fails on **one bar, one slice, three pairs**: contradiction-recall 0.9125 pooled /
0.9200 never-contacted against 0.95. The other three bars pass on both populations.

Separately the 2026-08-08 re-measure recorded a granularity finding: Rule B's second
population holds **25** contradicted pairs, so its recall lattice is 1.00 / 0.96 / 0.92 —
**0.95 is not on it** — and "the gate verdict required to hold on both" therefore makes it
enforce ≥ 0.96 where the pooled census permits four misses in 80.

This round makes that bar representable. It does **not** re-measure G-D.

## 2. The four owner rulings this round executes

| # | Ruling (2026-08-10) | Consequence |
|---|---|---|
| R1 | Resize so 0.95 lands on the subset's lattice, then let it gate | the round exists |
| R2 | Route: **retire-and-replace at a constant pooled census** | §3, §4 |
| R3 | Rule B's second population is **redefined, not abolished**; the boundary stays `eg-0242` and the name stops overclaiming | §5 |
| R4 | The attempt budget is **reported by lineage, not blocked** | §6 |

## 3. Two derivations the route turns on

**(a) 0.95 cannot be exact on both populations by growth alone.** 0.95 sits on a recall
lattice of size *n* only when `n ≡ 0 (mod 20)`. Let *N* be the second population's
contradicted census. **For growth-only routes** pooled is `55 + N`, since 55 contacted
contradicted pairs exist; both exact then requires `N ≡ 0` and `55 + N ≡ 0 (mod 20)`, and as
`55 ≡ 15` the second reads `N ≡ 5`. No *N* satisfies both. *(Framing corrected per review
§1: this is an impossibility of **growth**, which is what makes retirement the remedy —
retiring changes the 55 and dissolves the contradiction.)*

**(b) The census cannot simply grow, because the resample's first stratum is a full
census.** Layer-3 certification is `n = 93`, strata *full census of `contradicted`*, then
`unsupported`, remainder `entailed` — the last draw was `80 + 6 + 7`. This is enforced in
code, not only in prose: `resample_draw.draw` raises when the contradicted census exceeds
`RESAMPLE_N`. Growing pooled contradicted to 95 overruns a ratified sample size.

**Therefore, retire-and-replace at constant pooled census:**

| Population | now | after | 0.95 exact? |
|---|---|---|---|
| contacted contradicted | 55 | **40** | — |
| second-population contradicted | 25 | **40** | yes — 38/40 |
| pooled contradicted | 80 | **80** | yes — 76/80 |
| Layer-3 resample `n` | 93 | **93** unchanged | — |

## 4. The lattice-retirement rule (step 0 ratifies this text)

`LABELLING.md` retires a pair only when its label is **wrong**. Retiring correctly-labelled
pairs to reshape a lattice has no precedent and must not become a licence to remove
inconvenient evidence. *(Rewritten per review I1/I3/I4/I5 — v1's version pinned the seed but
not the procedure, contradicted itself on slices, left the slice composition free, and said
nothing about the attempt budget.)*

> **Lattice retirement (ratified 2026-08-10).** A pair may be retired for *census shape*
> rather than label error, under all of the following, each recorded in the task report:
>
> 1. **Contacted only.** The pair is in the contacted population, so a round removes
>    contaminated evidence and never fresh evidence.
> 2. **Never the protected core.** None of the 41 T2.25 pairs Rule B keeps live.
> 3. **A committed, zero-degrees-of-freedom draw.** The selection procedure is landed in a
>    commit *before* it executes and has no free parameters: seed from
>    `resample_draw.derive_seed` over the pre-retirement file, eligible pool sorted by `id`,
>    strata processed in a fixed stated order, `rng.sample(pool, quota)`. The drawn ids and
>    a one-command reproduction go in the report. *Pinning a seed is not enough: the same
>    seed under a different algorithm yields a different set, and choosing among defensible
>    algorithms after seeing the seed is the aiming channel this clause closes.*
> 4. **Content-blind beyond the stated stratification.** Slice enters only as the
>    largest-remainder stratification of clause 5; no rationale, label, premise, hypothesis
>    or judge result may enter the selection.
> 5. **Composition preserved, not just size.** The pooled census of the affected verdict
>    class **and its largest-remainder slice distribution** are unchanged after replacement.
>    Size alone is insufficient: retiring 15 `value-swap` and authoring 15 `temporal` would
>    reshape the census's difficulty at constant size.
> 6. **Budget lineage recorded.** A reshape changes the gold sha and therefore mints a fresh
>    `gold_touching_attempts`. The round records cumulative attempts across gold generations
>    in the ledger and in every report, so a reset is visible rather than silent (R4).
>
> **Reconciliation with "labelling is judge-blind."** That clause forbids retiring a pair
> "on the basis of what any judge model answers", and this round is triggered by a gate
> failure. The two are compatible and the file must say so explicitly: the **trigger** is
> the lattice arithmetic, which was recorded on 2026-08-08 before it bit; the **selection**
> is seeded and content-blind by clauses 3–4. What is barred is choosing *which* pairs to
> retire from judge output, and clauses 3–4 make that unavailable.

## 5. R3 — what Rule B's second population now means

**The 2026-08-08 run contacted all 351 pairs with fresh inference** ("nothing replayed
warm"), so a literal never-contacted population has not existed since. The strict reading is
also unsustainable: every qualification run scores all live pairs, so it would empty after
every attempt and Rule B would mean "grow the gold before each attempt".

**Owner ruling R3:** the boundary stays `eg-0242`, `NEVER_CONTACTED_FIRST_ID` **does not
move** — the filter is `id >= …` and open-ended, so new pairs join automatically, which is
what makes the 25 → 40 arithmetic work. *(Review C1: v1's step 8 said to move it; moving it
would leave 15 contradicted pairs in the gated subset — off a 15-lattice, worse than the 25
this round exists to fix, and it would fail the boundary test outright.)*

The population is **renamed** in `LABELLING.md`, `judge_qualification.py` and the ledger to
what it is: pairs **not contacted before the grown-gold attempt, with the per-pair miss
census withheld**. The substance that keeps it meaningful is that the ledger deliberately
withheld the per-pair census, so one contact without published feedback is materially unlike
the 241 pairs' three contacts with a public failure census. This is a weakening of ratified
text and is ratified as such, not assumed.

## 6. Mechanical derivations (against gold sha `800d4d91…`)

**Retirement seed** `derive_seed` over the pre-retirement file = **2148355473**.
**Assignment seed**: `derive_seed` over the file **immediately after step 2** (336 pairs),
committed before authoring. *(Review I8b: "the file's own hash" was ambiguous once step 2
moves the sha. Each seed is pinned to the state that precedes the operation it drives.)*

**Retirement pool** 55 − 10 T2.25 core = **45 eligible**: `value-swap` 24, `direction` 13,
`temporal` 8. **Retirement quota**, largest remainder: **8 / 4 / 3**. No ties.

**Authoring quota — 66 pairs**, and the figure is exact rather than approximate:
25/110 = 40/176 = 5/22 identically.

| Class | n | Derivation |
|---|---|---|
| contradicted | **15** | restores pooled to 80; slices **8 value-swap / 4 direction / 3 temporal**, mirroring the retirement so clause 5 holds |
| companions | **51** | largest remainder over the pooled non-contradicted classes (146 entailed : 125 unsupported) → **27 entailed / 24 unsupported**; by slice → verbatim 6, paraphrase 10, weakening 8, temporal 7, direction 4, overreach 10, unrelated 6 |

*(Review §3 confirmed option 1 — matching the subset's base rate — is correct: base rate
moves precision, whose bar is a review-load floor at 0.70, and leaves recall untouched
because its denominator is the gold-contradicted census alone. Option 2's 32% subset base
rate would inflate subset precision and break comparability. Review I4/§3 required the
companion composition be mechanical rather than chosen; the above is a pure function of the
current file.)*

## 7. The contamination firewall

T2.110's author read none of the G-D material. **The controller writing this plan is
contaminated and must not author**: it has read the slice-level failure attribution,
including the mechanism. An author holding that aims every new pair at the known weakness.

**The brief is an allowlist, not a denylist** *(review I2c: a denylist loses to an
honest-but-curious agent following a link in a repo full of contaminated artifacts)*. The
authoring and adjudication dispatches may read **only**:

- their own brief;
- `LABELLING.md` **above `## History`** — the rulebook sections, per T2.110's blind-pass
  practice. *(Residual, recorded: History carries the eg-0018 model-error analysis and
  resample results, which is judge-adjacent; it is excluded for that reason.)*
- the committed round-3 assignment output.

**`backend/scripts/benchlib/entailment/cache/` is quarantined before any dispatch**
*(review I2a — the single most serious perimeter hole)*. It holds 1,110 untracked per-pair
judge verdicts; joined with `gold.json` it reconstructs the per-pair miss census the ledger
deliberately withheld. It is **moved outside the repo, not deleted** — it is also the
evidence for the overlap disclosure in §8.

**This plan file and the plan review are themselves contaminated surfaces** *(review I2b)*
and are outside the allowlist by construction.

**If any dispatch is found to have read outside the allowlist, its pairs are void and the
round restarts from step 3.** Cheaper than certifying a census that was aimed.

## 8. Steps

| # | Step | Output | Blocking? |
|---|---|---|---|
| 0 | Ratify §4's rule and R3's rename into `LABELLING.md` + the ledger; record R1–R4 and the budget lineage | protocol amendment | **owner (B1)** |
| 1 | Quarantine `entailment/cache/`; commit the round-3 assignment code and the committed draw procedure (§4 clause 3); record seeds, pool, quotas | committed tooling, report §derivations | no |
| 2 | Execute the seeded stratified retirement; regenerate `declared_*_counts`; **delete the stale `resample` block** | `gold.json` at 336, honestly ineligible | no |
| 3 | Author 66 pairs in a **firewalled sub-agent** (§7) under the committed assignment | new pairs, `label_source: author` | no |
| 4 | Regenerate the blind export, manifest and sheet against the new sha | stripped export | no |
| 5 | Layer-2 blind adjudication, two separately dispatched passes (Opus, Sonnet), **scoped to the new pairs only**; agreement rates recorded whatever they are | `adjudicated` flips + escalation queue | no |
| 6 | Owner sitting on escalations, **raised as they arise**; rule-then-pairs where the rulebook is ambiguous | rulings in `LABELLING.md` | **owner (B2)** |
| 7 | Fresh Layer-3 resample, `n = 93`, bar ≤ 1, draw pinned to the new sha, sat by a **non-Claude** model | `resample` block, eligibility green | no |
| 8 | `NEVER_CONTACTED_FIRST_ID` **stays `eg-0242`**; only LABELLING.md's range *text* extends its end, which the pinned test recomputes | docs only | no |
| 9 | Update pinned `DOCUMENTED_*_COUNTS` and the resample test; floor + `./scripts/gate.sh --full` | green gate | no |
| 10 | Write the round's **History entry** (seeds, quotas, retired count, agreement rates, resample record, R3's ruling) and the task report incl. the **overlap disclosure**; `progress.md` on `master` | protocol memory | no |

**Step 2 deletes the `resample` block** *(review C2)*: `_resample_reasons` checks `n`,
`disagreements`, `seed`, `performed_by`, `date` and **no gold sha**, so a retained block
would read `gate_eligible = True` on a certification of a different file — from step 2
through step 7, across an owner-blocking pause and a session boundary, with the re-measure
being a separate task that would check eligibility and find it green. T2.110 handled this by
deleting the block and said why; nothing in code enforces it.

**Step 1's assignment code must state** whether retired pairs' premise usage frees cap
capacity. LABELLING.md's cap is "≤ 4 **live** pairs per premise", so live-only is the
faithful reading; `_round2_existing_usage` counts by id threshold and needs changing
*(review I8a)*.

**Step 10's overlap disclosure** *(review I6)*: a blind draw over the eligible 45 will, in
expectation, retire some of attempt 1's misses, moving the next re-measure's recall for
census-content reasons rather than judge reasons. The report records the **aggregate**
("k of 15 retired pairs were attempt-1 misses") — computable by the already-contaminated
controller from the quarantined cache — with pair ids withheld from every authoring surface.

**Not in this plan, deliberately:** the G-D re-measure. It spends an attempt from a budget
keyed on the gold sha, and running it from the session that authored the pairs is the
contamination this round exists to escape.

## 9. Blockers

- **B1 — owner ratification of §4 and R3.** No pair moves first.
- **B2 — an escalation the rulebook cannot decide.** Raised immediately; rule-then-pairs;
  re-adjudicate the affected slice.
- **B3 — two consecutive resample failures stop the task** (inherited verbatim).
- **B4 — the firewall leaking.** Void and restart from step 3.

## 10. What this round claims

It makes the subset's bar **representable** and its gating **honest**, and it stops the
population overclaiming its own name. It does not make G-D more likely to clear: the judge's
`value-swap` weakness is untouched, and a 40-pair subset permits exactly two misses where 25
permitted one. It is a **stricter** surface, which is the correct direction for a gate.
