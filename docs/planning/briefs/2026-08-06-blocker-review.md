# Brief — adversarial review of every open E2 blocker

**Tier:** Fable 5, xhigh effort. **Type:** analysis only. **Deliverable:** one dated
document under `docs/planning/analyses/` that recommends and stops. **Change no code, no
task file, no tracker row.**

Twelve tasks remain in E2. They reduce to five blockers. Several of the findings below are
mine, produced while executing T2.32/T2.49/T2.94 today — **treat them as claims to refute,
not as premises.** Where you agree, say what evidence made it survive; where you disagree,
say so plainly and name what you read.

## Standing instruction

For each blocker: state the decision actually owed, who owns it, the options with their
real costs, a **recommendation**, and what would change your mind. Then, across all five,
give a **sequencing recommendation** — they interact, and the controller has finite
attention.

Rank each recommendation's confidence and say what evidence is missing. If a blocker turns
out not to be one, that is the most valuable finding you can return.

## The five

### 1. T2.54 — the labelling sitting (~3 h, owner-only). Blocks 7 of 12.

Chain: `T2.54 → T2.41 (G-D) → T2.11 → T2.40 (G-C) → T2.27 → T2.28 → T2.48`. Both remaining
gates sit behind it; every probe in both gate tables is empty.

Read `docs/planning/analyses/2026-08-05-t2.11-judge-bar.md`, T2.54's tracker note, and the
G-C/G-D sections of `gate-ledger.md`.

Questions worth attacking: is the ~3 h estimate real, or does the rule-then-pairs
adjudication the note demands make it longer? Can any part be split off and dispatched
without contaminating the owner's n=93 resample — the **first** independent accuracy
measurement this gold receives? Is there a defensible smaller sitting that unblocks G-D
alone, given G-C is transitively behind it anyway?

### 2. T2.85 — the belief-window ruling. Blocks 1.

`docs/planning/analyses/2026-08-05-t2.85-belief-window.md` recommends option 2 (a
`stated_expiry` column). Verify the four-index claim independently and check whether the
recommendation survives the fact that the baseline is a **single shared mutable file**
serialised through one owner per epic — does option 2's schema edit collide with anything
in flight, and is the freeze event close enough to matter?

### 3. T2.59 — the retention ruling. Blocks 1.

`docs/planning/analyses/2026-08-05-t2.59-retention.md` recommends option D (accept and
document). Its load-bearing argument is that the assistant's own unbounded
`messages.content` and the storage substrate sit *below* all four options. Check that
argument rather than the conclusion.

### 4. T2.31 / T2.35 / T2.50 — the measurement blockers. Blocks 3.

**My claims, all of which you should try to break:**

- **T2.31 is contaminated.** `arm_ablation` resets the bench DB once, runs both legs over
  one corpus with no reset between, and every gold query bumps `memory_access_stats`
  through `HybridSearchService._record_access`. So the on leg's heat is manufactured by
  the off leg's traversal of the gold set — the memories carrying heat are
  disproportionately the correct answers. See
  `docs/planning/briefs/2026-08-06-t2.31-heat-recency-signals.md` and
  `docs/eval/2026-08-06-retrieval-eval-arm-w_heat.md`. Is the contamination real and
  material, or have I overstated it? Which resolution — seed-and-freeze, reset-between-legs,
  or something I have not considered — and does it require touching a protocol
  `FROZEN.md` declares frozen?
- **T2.35 needs gold authoring.** `w_context_boost` is structurally inert because
  `run_retrieval` declares no context and the gold pairs carry no env/version/situation
  axis. Is there a cheaper honest path than authoring a context axis?
- **T2.50 cannot be judged by me.** I built both arms it measures (T2.32's PPR, T2.94's
  dual-level), and runbook §2 separates builder from judge. Both arms now produce real
  numbers — `docs/eval/2026-08-06-retrieval-eval-arm-w_ppr.md` and `-w_dual.md`. Is the
  separation-of-powers reading correct, and if so what is the minimum independent judge?
  **Do not judge the arms yourself in this document** — say who should and under what
  protocol.

Both graph arms show the same signature: multi-hop hit@K is the only slice that gains,
temporal collapses. Is that a real pattern or an artefact of the probe weight
(`LIST_PROBE_WEIGHT = 0.3`) or of the gold's own shape? Note
`backend/scripts/benchlib/retrieval/SLICES.md` records two different achievable ceilings
for the multi-hop slice (6/14 vs 14/14) depending on the arm's entity-linking semantics —
a T0.06a amendment T2.50 is bound by. **Does that make the multi-hop gain
uninterpretable as currently measured?** This is the question I most want attacked.

### 5. The ledger row from a vacuous run.

The first `--arm w_dual` run ranked against an empty `relation_embeddings` partition and
recorded an exact-zero delta plus a ledger row before I fixed the preparation gap. The
ledger is append-only. I named the row in
`docs/eval/2026-08-06-retrieval-eval-arm-w_dual.md` and said it should be disregarded,
rather than removing it. **Is naming-in-the-report sufficient, or does the ledger need an
explicit retraction row?** What does the ledger's own contract
(`backend/scripts/benchlib/ledger.py`, `FROZEN.md`, doc 17 §7) say about superseded rows,
and is there precedent?

## Context you will need

- `docs/planning/agent-runbook.md` §2 (separation of powers), §6, §7
- `docs/planning/gate-ledger.md` — G-C and G-D sections, and the arm activation log rules
- `CLAUDE.md` — feature flags, jobs, the retrieval section
- Today's five commits on `feat/e2-truth-core`: `db616cba`, `2b2dd99e`, `0e669cdd`,
  `7920c3bf`, `e4768c8f`, `3f67152a`

## What not to do

No code changes. No task-file or tracker edits. No gate verdict. Do not run the retrieval
eval or spend live model calls — every number you need is already recorded under
`docs/eval/`. If you believe a run is needed, say which and why.
