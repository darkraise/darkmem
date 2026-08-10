# Plan — resize the never-contacted contradicted census so 0.95 lands on its lattice

**Status:** step-level plan, written 2026-08-10 for Fable review before execution
(runbook §3: an `L` task may not be executed directly).
**Task:** T2.115 (to be minted, Tier-2 amendment — the plan had no task for this).
**Owning gate:** G-D. **Owning protocol:** `backend/scripts/benchlib/entailment/LABELLING.md`.
**Precedent round:** T2.110, whose History entry in that file is the template.

---

## 1. Why this round exists

G-D fails on **one bar, one slice, three pairs**: contradiction-recall 0.9125 pooled /
0.9200 never-contacted against 0.95. Three of the four bars pass on both populations.

Separately, the 2026-08-08 re-measure recorded a granularity finding the owner was asked to
settle: the never-contacted subset holds **25** contradicted pairs, so its recall lattice is
1.00 / 0.96 / 0.92 — **0.95 is not on it**, and Rule B's "the gate verdict required to hold
on both" therefore makes the subset enforce ≥ 0.96 where the pooled census permits four
misses in 80. It did not bite the last run (23/25 fails against 0.95 and 0.96 alike), but a
future run landing on 24/25 would be passed by the stated bar and failed by the lattice.

**Owner ruling, 2026-08-10: resize the subset so 0.95 lands on its lattice, then let it
gate.** This plan executes that ruling. It does **not** re-measure G-D; the re-measure is a
separate task under the two-attempt budget, and it must not be run from the same session
that authored the pairs.

## 2. Two derivations the ruling turned on, recorded because they are load-bearing

**(a) "0.95 exact on both populations" is impossible, and this is a proof, not a
difficulty.** 0.95 sits on a recall lattice of size *n* only when `n ≡ 0 (mod 20)`. Let *N*
be the never-contacted contradicted census; pooled is `55 + N`, since 55 contacted
contradicted pairs exist and contact is a historical fact that cannot be undone. Both exact
requires `N ≡ 0` and `55 + N ≡ 0 (mod 20)`; as `55 ≡ 15`, the second is `N ≡ 5`. No *N*
satisfies both.

**(b) The census cannot simply grow, because the resample's first stratum is a full
census.** `LABELLING.md`'s Layer-3 certification is `n = 93` with strata *full census of
`contradicted`*, then `unsupported`, remainder `entailed` — the last draw was literally
`80 + 6 + 7`. Growing pooled contradicted to 95 does not merely miss the lattice, it
overruns the ratified sample size. T2.110 chose 80 for exactly this: "the one multiple of
20 in (55, 93]".

**Therefore the only route that changes nothing ratified is retire-and-replace at constant
pooled census**, which the owner ruled on 2026-08-10:

| Population | now | after | 0.95 exact? |
|---|---|---|---|
| contacted contradicted | 55 | **40** | — |
| never-contacted contradicted | 25 | **40** | yes — 38/40 |
| pooled contradicted | 80 | **80** | yes — 76/80 |
| Layer-3 resample `n` | 93 | **93** (unchanged) | — |

## 3. The precedent this round sets, and the rule it needs

`LABELLING.md`'s Layer 3 retires a pair **only when its label is wrong**
("wrong label → retire-and-replace"). Retiring *correctly labelled* pairs to reshape a
lattice has no precedent, and it must not become a licence to remove inconvenient pairs.

**Step 0 therefore writes a rule into `LABELLING.md` before any pair moves**, for the
owner's ratification, whose whole content is that the act is content-blind:

> **Lattice retirement (ratified 2026-08-10).** A pair may be retired for *census shape*
> rather than for label error, under four conditions, all of which must hold and be
> recorded: (1) the pair is in the **contacted** population, so the round removes
> contaminated evidence and never fresh evidence; (2) it is not one of the 41 T2.25 pairs
> Rule B protects; (3) it is selected by a **seeded draw stratified by slice**, with the
> seed derived from the pre-round file's own sha256 so it is unchooseable; (4) the pooled
> census of the affected verdict class is **unchanged** after replacement. No rationale,
> label, slice or content property may enter the selection.

## 4. The contamination firewall — the part of this plan most likely to be got wrong

T2.110's authoring pass was run by an agent that "read neither the gate ledger's G-D
sections, the G-D resolution-spike brief, the judge-qualification reports, nor
`resample_runs/`". That is the discipline that makes the grown pairs a measurement surface
rather than a target.

**The controller writing this plan is contaminated and must not author.** It has read the
G-D sections in full this session, including the slice-level failure attribution — that all
seven recall misses are `value-swap`, and the mechanism ("the judge declines to treat a
differing value in a single-valued slot as exclusion"). An author holding that would aim
every new pair at the known weakness, and the resulting census would measure nothing.

Consequences, binding on execution:

- **Authoring runs in a sub-agent** whose brief carries `LABELLING.md`, the slice quotas and
  the assignment seed, and **nothing from** `docs/planning/gate-ledger.md`,
  `docs/eval/*judge-qualification*`, or `entailment/resample_runs/`. The brief must name
  those paths as forbidden reads.
- **The quotas must be derived mechanically** from the existing file (§5) and never chosen.
  A quota that said "author 15 `value-swap` contradicted pairs" would leak the failure
  through the brief itself even if the author read nothing.
- **The two blind adjudication passes** (§7) are separately dispatched, no shared context,
  and get the stripped export only — the existing `strip_for_blind` path.
- **The controller's own contamination is recorded in the task report**, as T2.110 recorded
  its residual. Honesty about the firewall's holes is the firewall.

## 5. Mechanical derivations (run 2026-08-10 against gold sha `800d4d91…`)

**Retirement seed.** `int(sha256(gold.json)[:8], 16)` = **2148355473**, T2.110's Rule-A
construction — derived from the pre-round file's own hash, so unchooseable by the author of
this plan.

**Retirement pool.** 55 contacted contradicted − 10 in the T2.25 core = **45 eligible**,
by slice: `value-swap` 24, `direction` 13, `temporal` 8.

**Retirement quota**, largest-remainder over those proportions for 15 retirements:
`value-swap` **8**, `direction` **4**, `temporal` **3**. (Derivation is a pure function of
the eligible pool's slice counts; no other input.)

**Authoring quota.** 15 new contradicted pairs restoring the pooled census to 80, with the
same slice proportions the retirement removed, so the pooled slice distribution is
unchanged end-to-end.

**Non-contradicted companions — the one open question this plan does not settle.** The
subset's contradicted base rate is 22.7% and pooled's is 22.8%. Two mutually exclusive ways
to keep a rate stable:

- *Match the subset's base rate*: author ~66 pairs (15 contradicted + ~51 others) so the
  subset reaches ~176 pairs at ~23% contradicted. Pooled then drifts to 80/402 = **19.9%**.
- *Match pooled's base rate*: author 15 pairs only. Pooled stays 351 at 22.8%; the subset
  becomes 125 pairs at **32%** contradicted.

Base rate moves **precision** (more contradicted pairs, more available true positives) and
leaves **recall** — the truth-critical bar — untouched, since recall's denominator is the
gold-contradicted count alone. Precision's bar is a review-load floor at 0.70, not a truth
number. **Recommendation: match the subset's base rate (~66 pairs), because the subset is
now the population the gate turns on; record the pooled drift.** Flagged for the reviewer to
overturn if the reasoning is wrong — it is the largest judgement call in this plan.

## 6. Steps

| # | Step | Output | Blocking? |
|---|---|---|---|
| 0 | Mint T2.115 on `master`; write §3's lattice-retirement rule and both owner rulings into `LABELLING.md` and the gate ledger's G-D section | task row, protocol amendment | owner ratification of §3 |
| 1 | Freeze the pre-round state: record sha, seed, retirement pool, quotas | task report §"derivations" | no |
| 2 | Execute the seeded stratified retirement of 15 pairs; regenerate `declared_*_counts` | `gold.json` at 336 pairs | no |
| 3 | Author the replacement pairs in a **firewalled sub-agent** (§4), premise assignment by `entailment_assignment` under the derived seed | new pairs, `label_source: author` | no |
| 4 | Regenerate the blind export, manifest and sheet against the new sha | `resample_*`, stripped export | no |
| 5 | Layer-2 blind adjudication, two separately dispatched passes (Opus, Sonnet), agreement rates recorded whatever they are | `adjudicated` flips + escalation queue | no |
| 6 | Owner sitting on escalations, **raised as they arise** per the 2026-08-10 ruling; rule-then-pairs where the rulebook is ambiguous | rulings in `LABELLING.md` | **yes** |
| 7 | Fresh Layer-3 resample, `n = 93`, bar ≤ 1, seeded draw pinned to the new sha, sat by a **non-Claude** model (`resample_llm.py`, needs `DEEPSEEK_API_KEY`) | `resample` block, eligibility green | no |
| 8 | Move `NEVER_CONTACTED_FIRST_ID` and the LABELLING.md range together; the test suite pins them | `judge_qualification.py` | no |
| 9 | Floor + `./scripts/gate.sh --full`; task report; `progress.md` on `master` | green gate, recorded numbers | no |

**Not in this plan, deliberately:** the G-D re-measure. It spends an attempt from a
two-attempt budget keyed on the gold sha, and running it from the session that authored the
pairs is the contamination this whole round exists to escape.

## 7. Blockers, stated in advance

- **B1 — owner ratification of §3.** No pair moves until the retirement rule is ratified;
  retiring correct labels without it is exactly the licence the rule exists to deny.
- **B2 — an escalation the rulebook cannot decide.** Raised immediately (owner's 2026-08-10
  preference), rule-then-pairs, then re-adjudicate the affected slice.
- **B3 — two consecutive resample failures stop the task** (`LABELLING.md`, plan blocker
  B4's existing rule, inherited verbatim).
- **B4 — the firewall leaking.** If any authoring dispatch is found to have read a
  forbidden path, its pairs are void and the round restarts from step 3. Cheaper to restart
  than to certify a census that was aimed.

## 8. What this round does and does not claim

It makes the subset's bar **representable** and its gating **honest**. It does not make G-D
more likely to clear — the judge's `value-swap` weakness is unchanged, and a 40-pair subset
permits exactly two misses where 25 permitted one. If anything it is a **stricter** surface,
and that is the correct direction for a gate.
