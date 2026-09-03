# G-F's precision miss is a premise-framing defect, not judge quality

**Date:** 2026-09-03. **Status:** analysis + pre-registration, written before any
prompt edit. **Outcome appended in §10 after the pre-registered re-measure ran.** **Bearing on:** G-F (open, measured and MISSED 2026-08-17, TH1.10).

**Nothing here moves a bar.** `faithfulness_gate_precision_bar` stays 0.95 and
`faithfulness_gate_recall_bar` stays 0.90. No gold pair is re-cut, re-labelled
or retired.

## 1. What was measured

TH1.10's run was replayed from its warm cache (`entailment/cache_span/`, 260
entries) under an orchestrator whose `_live_chat` raises, so the replay could
not contact a vendor. It reproduced the recorded numbers exactly:

    entailed_precision=0.8880  entailed_recall=0.9250   (260 pairs, 0 live calls)

The judge identity was solved for rather than assumed, by computing the cache
key under candidate configs until one matched a committed entry: `gpt-5.5`,
`https://api.openai.com/v1`, `api_kind=openai`, `params={"reasoning_effort":
"high"}` — the identity the ledger records.

## 2. The 14 false-accepts are one phenomenon, not six

Precision is damaged by 14 false-accepts (judge `entailed`, gold
`not-entailed`). Grouped by what the **cited span** is:

| Family | Count | Pair ids |
|---|---|---|
| Markdown `[ ]` checklist item | 11 | `sg-0110`, `sg-0111`, `sg-0113`, `sg-0114`, `sg-0115`, `sg-0207`, `sg-0208`, `sg-0209`, `sg-0210`, `sg-0216`, `sg-0241` |
| `Expected:` / `Verify` directive | 2 | `sg-0211`, `sg-0238` |
| Table row without its header | 1 | `sg-0108` |

Removing only the checkbox family lifts entailed precision to **0.9737**;
removing the directives too gives **0.9911**. Both clear the 0.95 bar. Only
`sg-0108` is a span-fidelity failure of the kind this gate was built to catch.

A representative pair, `sg-0209`:

- **span** — `[ ] Toasts auto-dismiss after ~4 seconds`
- **hypothesis** — *Toasts auto-dismiss after roughly four seconds.*
- **gold** — `not-entailed`; *"the unchecked checklist item rule: the span
  asserts a thing to verify, not a fact about the system"*
- **judge** — `entailed`; *"The hypothesis restates the premise that toasts
  auto-dismiss after approximately four seconds."*

## 3. Root cause: the instrument is asked a different question than it is scored on

`app/services/verification_judge.py` opens its system prompt with:

> You are a strict natural-language-inference judge. Given a PREMISE (a stored
> fact) and a HYPOTHESIS (a claim) …

The prompt **tells the judge the premise is an asserted fact.** In the
faithfulness role the premise is not a fact but a raw document span, which may
be a checklist item, a directive, an expectation, or a table fragment — text
that asserts nothing about the system. The gold's "unchecked checklist item"
rule then penalises the judge for a document convention the prompt never
conveys.

The codebase already knew the distributions differ. `FAITHFULNESS_ROLE` exists
as its own role for exactly this stated reason — *"the discrimination is the
same word and a different premise distribution — raw document span text, which
the claim/fact gold does not represent"*. The role was split; the prompt was
not.

**This argument cites no pair and no score.** It is derived from the prompt's
own text being false about its input in this role, which is why the repair
below is a specification defect being closed rather than a fit to a failing
run.

## 4. Two ledger claims do not survive

Recorded here rather than quietly corrected, per the standing rule that a
"here is the full list" sentence going stale is itself the finding:

1. The ledger says the miss is *"concentrated in `overreach`"* with *"six
   strengthened claims read as grounded"* and that the judge *"fails on
   ordinary strengthening"*. **No pair in the run supports this.** Five of
   `overreach`'s six errors are checkbox items and the sixth is an `Expected:`
   line; not one is a strengthened quantifier, added content or an upgraded
   hedge.
2. The ledger's table calls `structure-fragment` *"15/15 mixed"*. It holds 30
   verdicts, scores 24/30, and **all six of its errors are false-accepts** —
   the same direction, and the same checkbox cause. The false-accept problem is
   broader across slices and narrower in cause than the ledger describes.

## 5. The gold is not wrong

Citing an unchecked checklist item as grounding for "the system does X" is a
real ungrounded claim, and a grounded badge resting on one would be exactly the
failure the 0.95 bar exists to prevent. The gold caught a genuine defect. What
it caught is a defect in the **judge's specification**, not in the model's
discrimination — which is why the repair is the prompt and why a vendor swap
would not touch it.

**A vendor swap was considered and rejected on this evidence.** Any competent
NLI judge told the premise is a stored fact reads `[ ] Toasts auto-dismiss
after ~4 seconds` as asserting that toasts auto-dismiss. Gemini would have
reproduced these 12 errors, at the cost of a measurement attempt and a fresh
gold round.

## 6. The capability requirement (stated before the fix)

> **A faithfulness judge must not treat an unasserted span as an assertion.**
> Cited document text that records something to *verify*, to *do*, or to
> *expect* — an unchecked checklist item, an imperative instruction, an
> `Expected:` line — does not assert that the thing holds of the system. A
> hypothesis claiming the system exhibits the behaviour is `unsupported` by
> such a span, however exactly its words match.

This is the requirement the served faithfulness check must meet. It is stated
as a property of the role's input distribution, with no reference to a pair, a
slice or a score.

## 7. The repair, and what it must not disturb

`judge_identity` folds `prompt_sha` — a hash of `SYSTEM_PROMPT` and
`USER_TEMPLATE` — so **editing the shared prompt would move the judge identity
and silently un-qualify G-D's minted entailment record** (`fd39e7b2c47fa375`,
prompt_sha `f99151e4add69b31`, minted 2026-08-17 and expensive to re-mint). It
fails closed rather than serving wrong verdicts, but the clear would evaporate.

So the repair is **role-scoped**:

- `SYSTEM_PROMPT` and `USER_TEMPLATE` stay **byte-identical**. The entailment
  and contradiction roles are untouched, and the entailment identity must still
  hash to `fd39e7b2c47fa375` — already pinned by
  `tests/test_llm_seed_resolution_pin.py`.
- A faithfulness-role system prompt carries §6's requirement.
- `judge_identity` becomes role-aware and folds the prompt **actually used** for
  that role, preserving `test_the_judge_prompt_is_not_reachable_through_the_
  editable_module`'s invariant that the served prompt and the hashed prompt are
  the same object.

## 8. Pre-registration for the re-measure

Stated before the re-measure runs, so the result cannot be chosen after seeing
it:

1. **Bars.** 0.95 precision / 0.90 recall, unmoved, imported from
   `faithfulness_bars` and never restated.
2. **Gold.** The same 260 live pairs, unmodified. No pair is re-labelled or
   retired on the strength of this analysis.
3. **Stopping rule.** **One** re-measure on this prompt. If it misses, the miss
   is recorded and no third prompt is tried against this gold — a second edit
   after seeing a second number is tuning, whatever it is called.
4. **The fitting risk is disclosed, not argued away.** The requirement in §6
   was derived from reading the failures of this run. It is stated
   pair-independently and rests on the prompt being false about its input, but
   the honest statement is that a clean number here is **a repaired instrument
   measured on the gold that exposed it**, not an independent confirmation. A
   pass licenses the *serving* decision no more than the faithfulness role's
   absent qualification record already allows, and any G-F verdict quoting it
   must carry this paragraph.
5. **What a pass does not license.** The faithfulness role holds no
   qualification record; `faithfulness_gate` withholds without one. Clearing
   the bars here is a gate measurement, not a licensed grounded label.
6. **Per-slice reporting is mandatory.** `verbatim` scored 0.800 (five verbatim
   restatements read as *not* entailed) — false rejects, so they did not cause
   the miss, but the ledger already flags them as a judge doing something other
   than entailment. The re-measure reports every slice, and a `verbatim`
   still at 0.800 is a finding to record even under a clearing aggregate.

## 9. Reproduction

Both scripts are analysis-only and contact no vendor:

- the cache-only replay that recovered the per-pair verdicts, and
- the identity solver that confirmed which config wrote `cache_span/`.

Neither is committed to `backend/scripts/benchlib/`: they read the harness, add
no measurement surface, and the runner they characterise
(`run_faithfulness_gate.py`) is the committed instrument.

## 10. Outcome (appended 2026-09-03, after the re-measure)

The repair landed and the pre-registered re-measure ran once, as §8 allowed:

    entailed_precision=0.9825  entailed_recall=0.9333  clears_role_bars=True

against 0.95 / 0.90, on the same 260 pairs with no bar moved and no pair
re-labelled. Errors fell 23 → 10. `overreach` went 0.800 → **1.000**; all
eleven checkbox pairs flipped. **Only two false-accepts survive and both are
the genuine article** — `sg-0108` (table row citing uncited header semantics)
and `sg-0238` (sound implication against the exclusive-slot rule). The other
eight remaining errors are false rejects, which cost recall, not precision.

`verbatim` improved 0.800 → 0.880 but three restatements are still read as not
entailed (`sg-0128`, `sg-0129`, `sg-0143`), and `paraphrase` slipped 0.967 →
0.933. Both are recorded per §8.6 rather than smoothed.

**The §8.4 disclosure stands and travels with the number**: this is a repaired
instrument measured on the gold that exposed it. The §8.3 stopping rule is now
spent — a second prompt edit measured against this gold would be tuning. The
faithfulness role still holds no qualification record, so no grounded label is
licensed, and G-F's other three probes are untouched. Whether G-F's row moves
is the owner's ruling.

Full result, caveats and an adjacent latent hazard in
`run_judge_qualification.py` (a role-blind mint that could write a faithfulness
record off the claim/fact gold): the gate ledger's "G-F re-measured on the
repaired premise framing".
