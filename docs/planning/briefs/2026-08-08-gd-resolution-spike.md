# Brief — G-D resolution spike (T2.41 follow-on)

`Model: Fable 5` · `Effort: high` · `Gate: G-D` · `Branch: feat/e2-truth-core`

**Charter.** G-D has been measured three times and does not clear. Decide what the
honest resolution is and carry it as far as evidence allows. **"Resolve" does not
necessarily mean "make it pass."** A recorded, argued conclusion that the bar or the
veto's architecture is wrong is a valid — possibly the correct — outcome. A pass
manufactured by fitting the prompt to this gold is the failure mode, not the goal.

## The measured state

Bars (config defaults, stated 2026-07-31 before any run):
`groundedness_gate_precision_bar` 0.95 · `groundedness_gate_recall_bar` 0.90 ·
`contradiction_precision_bar` 0.95. Gold: 241 live pairs, `sha256 e6d5647a…`,
eligible since the resample landed 2026-08-08.

| run | judge | ent-P | ent-R | contra-P | contra-R | report |
|---|---|---|---|---|---|---|
| 1 | `deepseek-v4-flash`, prompt v1 | 0.9895 | 0.9307 | **0.7937** | — | `docs/eval/2026-08-08-judge-qualification-4d886440.md` |
| 2 | `gpt-5.5`, prompt v1 | 0.9806 | 1.0000 | **0.8814** | 0.945 | `…-1bb9d9ba.md` |
| 3 | `gpt-5.5`, prompt v2 (reverted) | 0.9806 | 1.0000 | **0.9020** | **0.836** | `…-7779f3dd.md` |

Entailed precision and recall clear comfortably every time. **Only contradiction
precision fails, and it fails on every judge tried.**

## What the failures actually are

Run 2's 7 false positives, recovered by replaying the cache (0 live calls — the cache
at `backend/scripts/benchlib/entailment/cache` holds both runs, so this costs nothing):

- **4 × `temporal`** (eg-0020, eg-0021, eg-0216, eg-0220) — "cert renewed 10 March,
  valid 90 days" vs "is currently valid". Gold says `unsupported` because the premise
  contains no evaluation date. **The prompt already states this rule verbatim**
  ("A time-anchored premise neither entails nor contradicts an un-anchored 'currently'
  claim unless the window decides it"). The judge was told and violated it.
- **3 × `direction`** (eg-0023 haproxy load-balancing, eg-0075 `USES`, eg-0163 `CAUSES`)
  — reversals of non-exclusive relations. The prompt says "a reversed relation **when
  the relation is exclusive in direction**" and never defines which relations qualify;
  `LABELLING.md`'s 16-row table does.

## Three findings to build on, not rediscover

1. **The window logic is already in SQL, correctly.** `contradiction_scan.py:248–262`
   filters temporally-disjoint pairs before the judge is called. Passing a reference
   time into `judge()` would duplicate a working guard and let the model override it.
   This was proposed and rejected on reading the code — do not re-propose without
   engaging that.
2. **A prompt fix was tried, measured and reverted (run 3).** Enumerating relation
   exclusivity took `direction` to a perfect 30/30 — the gap was real — and collapsed
   `value-swap` 0.897 → 0.690. Contradiction precision rose *only because the judge
   predicted contradiction less often*: FP 7→5 while TP 52→46. Local prompt edits have
   non-local effects; read the whole slice table before and after, never one metric.
3. **Contradiction recall has no bar.** It is computed every run and gated nowhere.
   The gate therefore rewards a judge that stays quiet, which is exactly what run 3
   produced by accident. An absolute veto gated on precision alone selects for silence.

## The architectural question, stated plainly

The veto is absolute — one non-echo contradiction beats any corroboration count, with no
config on its path — and it currently rests on a single LLM judgment at a 0.95 precision
bar. At 55 gold-contradicted pairs that bar permits **at most two** false positives in
241 pairs. Two frontier models from two vendors, same frozen prompt, miss it in the same
direction: over-calling contradiction where the premise merely fails to assert.

There is already a **deterministic arm** (`contradiction_veto.adjudicate_contradiction_finding`
→ `CONTRADICTION_DETECTORS`, judge-free, live, reached on every recompute; its
`inverse_replacement` rule fires without any qualification record). Whether the LLM arm
should *dispute* or merely *open review* is a live design question, not a settled one.

## Constraints — these are hard

- **No prompt-tuning against this gold.** It has been contacted 3 times
  (`gold_touching_attempts`). A prompt edit moves `prompt_sha` → the judge identity →
  de-qualifies mechanically, and fitting to observed errors is the contaminating loop
  T2.26's plan review flagged as its one Critical. Any prompt change must be justified
  independently of these specific failures **and** validated on pairs not in this gold.
- **No model-shopping.** Two attempts at a frozen prompt is doc 17 §6's remedy; an
  open-ended sweep until one clears is the same contamination by another route.
- **Bars are stated-before-measuring.** Moving `contradiction_precision_bar` is a bar
  change needing its own recorded argument; it is the owner's ratification, not yours.
  You may recommend it, with the argument written out.
- **Never mint on a miss.** `run_judge_qualification.py --gate` writes no qualification
  record unless every bar clears (fixed 2026-08-08). Use `--record-path` to a temp path
  for any exploratory run. `app/services/verification_qualification.json` must not exist
  unless a run genuinely cleared.
- **Invariant 15 and the closed taxonomies still apply.** `CLAUDE.md` is contract.

## Verify

`./scripts/gate.sh` must be green before you finish (backend 4685 / 19 skipped,
benchlib 700, frontend 738). Run tests in the foreground with an explicit `timeout`
**and** the Bash tool's own timeout parameter. Check `git branch --show-current` before
every commit — the shell cwd resets between calls. Leave no stray processes or
databases; the only lawful databases are `darkmem`, `darkmem_test`, `darkmem_bench`.

## Deliverable

A written verdict in `docs/planning/gate-ledger.md` under G-D, plus whatever code or
gold changes your conclusion actually justifies. State plainly which of these it is:

- G-D is clearable and here is the evidence; or
- the bar is wrong and here is the argument for a different one; or
- the veto's architecture is wrong and here is the design that needs less precision; or
- G-D is not resolvable now and here is precisely what would resolve it.

Say which, and why the other three are not it.
