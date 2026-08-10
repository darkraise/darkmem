# Duplicate-repair round — staged, not executed (2026-08-10)

Everything here is decided and reversible. **Nothing in it has touched
`gold.json`**; the sha is still `98fc4b49`, the `58ac1a90` certification stands
and the attempt budget is unspent. The round below is one dispatch away, and it
is written down so that whoever runs it does not re-derive it.

## Why the round exists

Ruling R-B: no further judge attempt may run on `98fc4b49` until the two
**contradicted** duplicate propositions are retired and the gold re-certified.
The hazard is not theoretical on this gold. A judge that *catches* a duplicated
proposition banks two correlated hits and then has 4/78 ≈ 5.13% per-item
tolerance against the intended 4/80 = 5.00%; attempt 1 scored Rule B at exactly
**38/40 = 0.9500** with both duplicates in its population, and pooled at 75/80
against a 76/80 bar. The edge case the artifact would decide is the case we are
actually in.

## The retirement, already determined mechanically

Applying the ratified inadmissible-duplicate ground (LABELLING.md) — *the
later-minted member retires, by id order, content-blind*:

| Keep | Retire | Slice | Verdict | Population of the retired |
|---|---|---|---|---|
| `eg-0093` | **`eg-0367`** | direction | contradicted | Rule B |
| `eg-0194` | **`eg-0251`** | direction | contradicted | Rule B |

No judgement is exercised here and none may be: id order is authoring order, so
the rule keeps the pair that was already in the slot and retires the one that
entered it.

## The replacement spec

Two pairs, authored **blind**, into the same slice and verdict and the same
population, so the census and both lattices are preserved:

- **2 × `direction` / `contradicted`**, landing in Rule B's population
  (id ≥ `eg-0242`).
- Census after: pooled contradicted **80** (40 contacted / 40 Rule B), both
  lattices exact, 0.95 representable on each — the property T2.115 exists for.
- The premises must **not** be facts that already carry a live `direction`
  pair. That is the condition round 3 violated three times; the committed check
  (`benchlib.duplicate_propositions`) is the mechanical test and must report no
  new finding before the round closes.

## Firewall, unchanged from T2.115

- Authors read the rulebook **above** the History section and nothing else — not
  the gate ledger, not the qualification reports, not `resample_runs/`.
- `entailment/cache/` and `entailment/verdicts/` are moved outside the
  repository before any authoring dispatch.
- **This session may not author and may not adjudicate**: it has read the
  slice-level failure attribution and both judges' results. It may dispatch,
  because dispatching a brief that names a slice and a verdict leaks nothing the
  quota does not already fix.
- Blind adjudication by two separately dispatched passes, as before.

## What the round costs, stated because it is the reason to pause

1. The sha moves. The `58ac1a90` certification is voided and a fresh `n = 93`
   resample must certify the new file — T2.115's took **three sittings**.
2. `gold_touching_attempts` re-mints on the new sha; the cumulative lineage is
   recorded under clause 6 so the reset is visible rather than silent.
3. Only then may the owner-ruled `gpt-5.5` attempt run, as the **final** attempt
   on that gold under the stopping rule recorded on T2.114.

## The alternative, stated fairly

Waive R-B's gate with a recorded argument and run `gpt-5.5` now against the
known census, accepting the disclosed artifact. It is cheap and it is not
absurd — the duplicates are documented, and the effect is bounded at two
correlated rows.

It is not recommended. G-D gates whether darkmem may **serve** a verification
label to a user, attempt 1 landed one pair from the bar, and a pass that lands
inside the artifact's width is a pass this corpus would have to disclose as
possibly manufactured — which is the outcome every rule in this file exists to
prevent.


---

## Execution log — three findings that change the plan (2026-08-10)

The round was started under the owner's instruction ("run the repair round, then
the gpt-5.5 attempt"). It stopped before touching `gold.json`. **The sha is
still `98fc4b49`, the `58ac1a90` certification stands and the attempt is
unspent.** Three things came out of the attempt that the staged plan did not
anticipate, and each changes what the round costs.

### 1. The premise draw was defective, and a blind author caught it

`replacement_premise_draw.py` filtered on *no live `direction` pair* and *an
exclusive reversal relation*, and **not** on the per-premise cap.
`l2_harvest.json`'s header fixes `pairs_per_premise_cap` at 4 and
`test_no_premise_supports_more_than_four_live_pairs` enforces it. Both drawn
premises already carried four live pairs, so both slots were infeasible as
dispatched.

The author of slot `eg-0418` checked the cap before writing, found the slot
infeasible and **recorded a skip instead of a pair** — the correct outcome, and
the firewall working in a direction nobody designs it for: the blind party
caught the contaminated party's mechanical error. The author of `eg-0419`
returned a well-formed pair that is unusable for the same reason, having not
checked the cap. Both are discarded; the module now filters on capacity and
reports exhaustion explicitly.

### 2. The l2-fact route is exhausted — the replacements must be hand-authored

With all three filters, the eligible pool is **zero**. Every harvest fact whose
reversal is exclusive and which carries no live `direction` pair is at the
4-pair cap, and the two retirements free no capacity (both sit on premises that
already carry a live `direction` pair, which filter 1 excludes anyway).

So the replacements take **hand-authored premises** under the frozen skip
mechanism, exactly as round 3 did for its own capacity skips. The consequence is
one declared count: `l2-fact` 238 → 236 and `hand-authored-synthetic-fact`
148 → 150. Doc 17 §11's ≥ 50% floor is unaffected — 236/402 = 58.7%.

### 3. `gpt-5.5` cannot be run from this machine

The owner-ruled judge is `gpt-5.5`. The 2026-08-08 run of it went to
`api.openai.com` (`resample_runs/2026-08-08-gpt-5-5.json`), and **no OpenAI
credential exists** — not in the environment, not in the repo, and CLAUDE.md's
live-endpoints section records only DeepSeek and a LAN Ollama. `run_judge_qualification`
takes the key as an argument, so the runner is ready; the credential is not
here.

**Sequencing consequence.** The repair is worth doing on its own merits — the
duplicates block *any* future attempt, not just this one. But completing it
means voiding the `58ac1a90` certification and spending a fresh `n = 93`
certification sitting (T2.115's took three), and the attempt it exists to enable
cannot follow until `OPENAI_API_KEY` is available. Doing the surgery now and
discovering the key never arrives leaves the gold re-certified and unmeasured —
no loss but the spend, and no gain either.
